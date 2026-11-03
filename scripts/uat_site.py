#!/usr/bin/env python3
"""Measure the built static site with Chromium; exits nonzero on failed budgets.

Run with a Python environment containing Playwright and installed Chromium:
python3 scripts/uat_site.py --out docs/uat-2026-11-02-baseline.json
The server snapshots pages in memory so a concurrent rebuild cannot mix versions.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import gzip
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import mimetypes
from pathlib import Path
import threading
from typing import Any, Iterator
from urllib.parse import unquote, urlsplit

VIEWPORTS = {"tablet": (768, 1024), "mobile": (375, 812), "desktop": (1440, 900)}
KEY_CONTENT = {
    "overview": "#overview", "check": ".pcheck-input", "legislation": ".theme-grid",
    "states": ".hero", "commitments": ".commit-metrics", "cwa": "#statute-paths",
    "issues": ".issue-summary", "news": "#news-cards .news-card", "solutions": ".hero",
    "security": ".security-callout", "sources": ".hero", "explore": ".explore-side",
}
INIT = """(() => {
window.__uat={longtasks:[],lcp:0,clickStart:0,mutations:0};
new PerformanceObserver(l=>l.getEntries().forEach(e=>__uat.longtasks.push({start:e.startTime,duration:e.duration}))).observe({type:'longtask',buffered:true});
new PerformanceObserver(l=>l.getEntries().forEach(e=>__uat.lcp=e.startTime)).observe({type:'largest-contentful-paint',buffered:true});
document.addEventListener('click',()=>{__uat.clickStart=performance.now()},true);
document.addEventListener('input',()=>{__uat.clickStart=performance.now()},true);
document.addEventListener('DOMContentLoaded',()=>new MutationObserver(l=>__uat.mutations+=l.length).observe(document.body,{subtree:true,attributes:true,childList:true,characterData:true}));
})();"""


@contextmanager
def serve_snapshot(root: Path) -> Iterator[tuple[str, dict[str, bytes]]]:
    """Serve an immutable, compressed snapshot on an OS-assigned local port."""
    files = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            name = unquote(urlsplit(self.path).path).lstrip("/") or "index.html"
            if name == "favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            if name not in files:
                self.send_error(404)
                return
            body = files[name]
            compressed = "gzip" in self.headers.get("Accept-Encoding", "")
            if compressed:
                body = gzip.compress(body, mtime=0)
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if compressed:
                self.send_header("Content-Encoding", "gzip")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/", files
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def budgets(row: dict[str, Any]) -> list[str]:
    """Shared validation for recorded browser rows and deliberately bad fixtures."""
    failures = []
    if row.get("error"):
        failures.append(row["error"])
    for field, limit in (("overflow_px", 1), ("content_ms", 20000), ("interaction_ms", 20000)):
        if row.get(field, 0) > limit:
            failures.append(f"{field}={row[field]} exceeds {limit}")
    if "key_depth_screens" in row:
        depth = row["key_depth_screens"]
        if depth is None:
            failures.append("key content missing")
        elif depth > row.get("depth_budget", 2):
            failures.append(f"key depth {depth} exceeds {row.get('depth_budget', 2)} screens")
    if "content_chars" in row and row["content_chars"] < 20:
        failures.append("content is empty or too short")
    if row.get("page_errors"):
        failures.append(f"page errors: {row['page_errors']}")
    return failures


def idle_failures(profile: dict[str, Any], viewport_height: int) -> list[str]:
    """Offscreen animations must stop; visible diagrams are measured separately."""
    return [f"Offscreen animation continues: {animation['name']}"
            for animation in profile["running_animations"]
            if animation["bottom"] <= 0 or animation["top"] >= viewport_height]


def geometry(page: Any, selector: str) -> dict[str, Any]:
    return page.evaluate("""sel=>{const e=document.querySelector(sel),r=e?.getBoundingClientRect();
      return {key_depth_screens:r&&r.width&&r.height?+(Math.max(0,r.top+scrollY)/innerHeight).toFixed(3):null,
        key_viewport_top:r?.top,overflow_px:Math.max(0,document.documentElement.scrollWidth-innerWidth),
        page_screens:+(document.documentElement.scrollHeight/innerHeight).toFixed(3),
        content_chars:e?.textContent?.trim().length||0,dom_nodes:document.querySelectorAll('*').length};}""", selector)


def resources(page: Any) -> list[dict[str, Any]]:
    return page.evaluate("""()=>[...performance.getEntriesByType('navigation'),...performance.getEntriesByType('resource')].map(r=>({
      path:new URL(r.name).pathname,transfer_bytes:r.transferSize,encoded_bytes:r.encodedBodySize,decoded_bytes:r.decodedBodySize,duration_ms:r.duration}))""")


def metrics(cdp: Any) -> dict[str, float]:
    return {item["name"]: item["value"] for item in cdp.send("Performance.getMetrics")["metrics"]}


def idle_profile(page: Any, cdp: Any, seconds: int = 10) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    cdp.on("Tracing.dataCollected", lambda event: events.extend(event["value"]))
    cdp.send("Tracing.start", {"categories": "devtools.timeline", "transferMode": "ReportEvents"})
    before = metrics(cdp)
    mutations = page.evaluate("__uat.mutations")
    page.wait_for_timeout(seconds * 1000)
    after = metrics(cdp)
    cdp.send("Tracing.end")
    page.wait_for_timeout(150)
    names = Counter(e["name"] for e in events if e.get("ph") == "X")
    duration = {name: round(sum(e.get("dur", 0) for e in events if e.get("ph") == "X" and e["name"] == name) / 1000, 3)
                for name in ("Paint", "PrePaint", "Layout", "UpdateLayoutTree", "FunctionCall", "FireAnimationFrame")}
    return {"seconds": seconds, "task_ms": round((after["TaskDuration"] - before["TaskDuration"]) * 1000, 3),
            "script_ms": round((after["ScriptDuration"] - before["ScriptDuration"]) * 1000, 3),
            "heap_bytes": after["JSHeapUsedSize"], "trace_counts": dict(names), "trace_duration_ms": duration,
            "dom_mutations": page.evaluate("__uat.mutations") - mutations,
            "running_animations": page.evaluate("document.getAnimations().filter(a=>a.playState==='running').map(a=>({name:a.animationName,target:a.effect.target?.tagName,top:a.effect.target?.getBoundingClientRect().top,bottom:a.effect.target?.getBoundingClientRect().bottom}))")}


def click(page: Any, selector: str, ready: str) -> dict[str, Any]:
    control = page.locator(selector).first
    start_y = page.evaluate("scrollY")
    control.click(trial=True)
    control.click()
    page.wait_for_function(ready)
    row = page.evaluate("""()=>({interaction_ms:performance.now()-__uat.clickStart,
      longtasks:__uat.longtasks,scroll_y:scrollY})""")
    row["automated_scroll_screens"] = round(abs(row.pop("scroll_y") - start_y) / page.viewport_size["height"], 3)
    row["clicks"] = 1
    return row


def worksheet_download(page: Any) -> tuple[dict[str, Any], str]:
    with page.expect_download() as download_event:
        page.locator("#pcheck-export").click()
    download = download_event.value
    assert download.failure() is None, "Assessment download failed"
    return json.loads(Path(download.path()).read_text()), download.suggested_filename


def check_downloaded_inputs(page: Any, worksheet: dict[str, Any], expected_hash: str,
                            source_example: dict[str, Any] | None) -> dict[str, str]:
    """Match the exported worksheet to what the reader actually saw and selected."""
    project = worksheet["project"]
    assert project["evidence_status"] == "unverified_inputs"
    inputs = project["inputs"]
    assert inputs["source_example"] == source_example, "Example record or lineage changed"
    assert inputs["retrieval_payload_sha256"] == expected_hash, "Worksheet references a different retrieval corpus"
    for field, selector in (("state", "state"), ("description", "text"), ("mw", "mw"), ("mgd", "mgd")):
        assert inputs[field] == page.locator(f"#pcheck-{selector}").input_value(), f"Wrong raw input: {field}"
    checkboxes = page.locator(".pcheck-facet-box").evaluate_all("es=>Object.fromEntries(es.map(e=>[e.value,e.checked]))")
    assert checkboxes, "Missing project facet controls"
    selections = inputs["facet_selections"]
    assert len(selections) == len(checkboxes), "Missing or duplicate facet selections"
    assert {s["facet_id"]: s["selected"] for s in selections} == checkboxes
    return {s["facet_id"]: s["origin"] for s in selections}


def run(root: Path, out: Path, screenshot_dir: Path | None = None) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright
    result: dict[str, Any] = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "rows": [], "profiles": {},
        "method": "Headless Chromium; immutable localhost gzip HTTP snapshot; fresh contexts per viewport; one sample per flow. Click clocks start in capture listeners and end at asserted DOM state. Reading/typing time and manual scroll gestures excluded.",
        "limitations": ["Local transfer includes browser-reported headers; gzip file bytes are a separate estimate. Production CDN transfer is not measured.", "JS heap is not total browser RAM. GPU memory, compositor process CPU and field INP are not measured.", "Trace paint duration is renderer work, not GPU memory or visual frame correctness.", "All top-level tabs and named critical flows are exercised; this is not every control or every content record."]}

    def record(name: str, viewport: str, operation: Any) -> None:
        try:
            row = operation()
        except Exception as exc:
            row = {"error": f"{type(exc).__name__}: {exc}"}
        row.update(name=name, viewport=viewport, depth_budget=1.5 if viewport == "desktop" else 2)
        row["failures"] = budgets(row)
        result["rows"].append(row)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + "\n")
        logging.info("%s/%s: %s", viewport, name, row["failures"] or "pass")

    with serve_snapshot(root) as (base, files), sync_playwright() as pw:
        result["files"] = {name: {"raw_bytes": len(body), "gzip_bytes": len(gzip.compress(body, mtime=0)),
                                  "sha256": hashlib.sha256(body).hexdigest()}
                           for name, body in files.items() if name.endswith((".html", ".css", ".js", ".json", ".jsonl", ".md"))}
        browser = pw.chromium.launch()
        result["browser_version"] = browser.version
        payload = json.loads(files["project-data.json"])
        published_hash = payload.pop("payload_sha256", None)
        canonical_bytes = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        expected_hash = hashlib.sha256(canonical_bytes).hexdigest()
        example_by_id = {e["id"]: e for e in payload["examples"]}
        for viewport, (width, height) in VIEWPORTS.items():
            context = browser.new_context(viewport={"width": width, "height": height})
            context.add_init_script(INIT)
            page = context.new_page()
            page.set_default_timeout(20000)
            errors: list[str] = []
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            cdp = context.new_cdp_session(page)
            cdp.send("Performance.enable")
            page.goto(base, wait_until="domcontentloaded")
            page.locator("#panel-overview h2").wait_for(state="visible")
            content_ms = page.evaluate("performance.now()")
            page.wait_for_load_state("networkidle")
            assert "Data Center Water" in page.title()
            tabs = page.locator("button[data-tab]").evaluate_all("es=>es.map(e=>e.dataset.tab)")
            assert tabs, "No tabs found"
            assert set(tabs) == set(KEY_CONTENT), "Update key-content selectors for changed tabs"
            result["tabs"] = tabs
            cold = geometry(page, "#panel-overview")
            cold.update(content_ms=content_ms, resources=resources(page),
                        fcp_ms=page.evaluate("performance.getEntriesByName('first-contentful-paint')[0]?.startTime"),
                        lcp_ms=page.evaluate("__uat.lcp"), heap_bytes=metrics(cdp)["JSHeapUsedSize"], page_errors=list(errors))
            record("cold-overview", viewport, lambda: cold)
            if viewport == "mobile":
                result["profiles"]["mobile-overview-idle"] = idle_profile(page, cdp)
            for tab in tabs:
                def tab_flow(tab: str = tab) -> dict[str, Any]:
                    page.evaluate("scrollTo(0,0)")
                    row = click(page, f'button[data-tab="{tab}"]',
                                f"document.querySelector('#panel-{tab} h2') && !document.querySelector('#panel-{tab}').hidden && !document.querySelector('#panel-{tab}').hasAttribute('data-src')")
                    row.update(geometry(page, f"#panel-{tab} {KEY_CONTENT[tab]}"))
                    row["key_selector"] = KEY_CONTENT[tab]
                    row["content_chars"] = len(page.locator(f"#panel-{tab}").inner_text())
                    row["page_errors"] = list(errors)
                    if screenshot_dir:
                        if tab in ("check", "explore"):
                            payload_name = "project-data.json" if tab == "check" else "graph-data.json"
                            page.wait_for_function("name=>performance.getEntriesByType('resource').some(e=>new URL(e.name).pathname.endsWith('/'+name))", arg=payload_name)
                        screenshot_dir.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(screenshot_dir / f"{viewport}-{tab}.png"))
                    return row
                record(f"tab-{tab}", viewport, tab_flow)
            click(page, 'button[data-tab="check"]', "!!document.querySelector('#pcheck-text')")
            page.wait_for_function("!document.querySelector('#pcheck-run').disabled")
            record("assessment-initial-disabled", viewport, lambda: {
                "error": "Assessment export enabled before a run" if not page.locator("#pcheck-export").is_disabled() else None})
            examples = page.locator(".pcheck-example").evaluate_all("es=>es.map(e=>e.dataset.example)")
            assert examples, "No Check examples"
            for example in examples:
                def example_flow(example: str = example) -> dict[str, Any]:
                    before = metrics(cdp)
                    row = click(page, f'[data-example="{example}"]', "!!document.querySelector('#pcheck-output .pcheck-sec')")
                    after = metrics(cdp)
                    row.update(geometry(page, "#pcheck-output"))
                    row["clicks_from_overview"] = 2
                    row["heap_bytes"] = after["JSHeapUsedSize"]
                    row["renderer_task_ms"] = round((after["TaskDuration"] - before["TaskDuration"]) * 1000, 3)
                    row["script_ms"] = round((after["ScriptDuration"] - before["ScriptDuration"]) * 1000, 3)
                    return row
                record(f"check-example-{example}", viewport, example_flow)

            def loaded_example_flow() -> dict[str, Any]:
                assert published_hash == expected_hash, "Published retrieval digest does not identify the served payload"
                original = example_by_id[examples[-1]]
                worksheet, _ = worksheet_download(page)
                origins = check_downloaded_inputs(page, worksheet, expected_hash, original)
                selected = {s["facet_id"] for s in worksheet["project"]["inputs"]["facet_selections"] if s["selected"]}
                assert selected == set(original["facets"]), "Loaded example differs from its curated facts"
                assert all(origins[facet] == "curated_example" for facet in selected)
                return {"source_example": original["id"], "curated_facets": len(selected), "payload_digest_verified": True}
            record("assessment-example-provenance", viewport, loaded_example_flow)

            def edit_flow() -> dict[str, Any]:
                page.locator("#pcheck-text").fill("A 300 MW Arizona campus pumps groundwater wells for evaporative cooling and discharges blowdown to city sewer.")
                page.locator("#pcheck-state").select_option("AZ")
                row = click(page, "#pcheck-run", "document.querySelector('#pcheck-state').value==='AZ' && !!document.querySelector('#pcheck-output .pcheck-sec')")
                row.update(geometry(page, "#pcheck-output"))
                row["interactions_from_overview"] = 4
                worksheet, _ = worksheet_download(page)
                origins = check_downloaded_inputs(page, worksheet, expected_hash, example_by_id[examples[-1]])
                assert set(origins.values()) == {"derived_from_inputs"}, "Edited prose still carries curated origins"
                row["source_example_retained_after_edit"] = True
                return row
            record("check-edit-run", viewport, edit_flow)

            def link_flow() -> dict[str, Any]:
                old_hash = page.evaluate("location.hash")
                link = page.locator('#pcheck-output a[href^="#"]').first
                href = link.get_attribute("href")
                row = click(page, '#pcheck-output a[href^="#"]', f"location.hash==={json.dumps(href)} && !!document.querySelector({json.dumps(href)}) && document.querySelector({json.dumps(href)}).getBoundingClientRect().height>0")
                row["target"] = href
                row["target_top_px"] = page.locator(href).evaluate("e=>e.getBoundingClientRect().top")
                page.go_back()
                page.wait_for_function(f"location.hash==={json.dumps(old_hash)} && !document.querySelector('#panel-check').hidden")
                row["back_restored"] = True
                return row
            record("cross-tab-link-back", viewport, link_flow)
            record("check-clear", viewport, lambda: click(page, "#pcheck-clear", "document.querySelector('#pcheck-text').value==='' && !document.querySelector('#pcheck-output .pcheck-sec') && document.querySelector('#pcheck-output').textContent.includes('Nothing checked')"))

            def assessment_flow() -> dict[str, Any]:
                assert page.locator("#pcheck-export").is_disabled(), "Clear must invalidate export"
                page.locator("#pcheck-text").fill("A data center uses injection wells into groundwater.")
                click(page, "#pcheck-run", "!document.querySelector('#pcheck-export').disabled")
                assessment, download_name = worksheet_download(page)
                check_downloaded_inputs(page, assessment, expected_hash, None)
                assert assessment["legal_applicability"] == "not_assessed"
                assert assessment["assessment_type"] == "retrieval_worksheet"
                assert assessment["checklists"], "Maui input must yield an evidence checklist"
                assert any(c["reading_id"] == "cwa-402-maui-groundwater" for c in assessment["checklists"])
                questions = [q for c in assessment["checklists"] for q in c["questions"]]
                assert questions and all(q["answer"] == "unknown" and q["project_evidence"] == [] for q in questions)
                assert assessment["unreviewed_reading_ids"], "Readings without a checklist must be disclosed"
                for checklist in assessment["checklists"]:
                    for source in checklist["sources"]:
                        assert page.locator(f'#pcheck-output .pcheck-evidence a[href="{source["url"]}"]').count() > 0
                evidence = page.locator("#pcheck-output .pcheck-evidence").first
                evidence.locator("summary").click()
                assert evidence.locator("a").first.is_visible()
                mutations = [
                    lambda: page.locator("#pcheck-text").fill("A campus uses injection wells into groundwater."),
                    lambda: page.locator("#pcheck-state").select_option("AZ"),
                    lambda: page.locator("#pcheck-mw").fill("350"),
                    lambda: page.locator("#pcheck-mgd").fill("2"),
                    lambda: page.locator('.pcheck-facet-box[value="src-wells"]').set_checked(not page.locator('.pcheck-facet-box[value="src-wells"]').is_checked()),
                ]
                if not page.locator("#pcheck-facets").evaluate("e=>e.open"):
                    page.locator("#pcheck-facets summary").click()
                for mutate in mutations:
                    mutate()
                    assert page.locator("#pcheck-export").is_disabled(), "Input change left stale export enabled"
                    click(page, "#pcheck-run", "!document.querySelector('#pcheck-export').disabled")
                manual, _ = worksheet_download(page)
                origins = check_downloaded_inputs(page, manual, expected_hash, None)
                inputs = manual["project"]["inputs"]
                assert (inputs["mw"], inputs["mgd"], inputs["state"]) == ("350", "2", "AZ")
                assert origins["src-wells"] == "manual_selection", "Manual facet edit lost its provenance"
                click(page, "#pcheck-clear", "document.querySelector('#pcheck-export').disabled")
                return {"download_filename": download_name, "unknown_questions": len(questions),
                        "manual_export_values": {"mw": inputs["mw"], "mgd": inputs["mgd"], "state": inputs["state"]},
                        "unreviewed_readings": len(assessment["unreviewed_reading_ids"]), "stale_mutations_checked": len(mutations)}
            record("assessment-export-evidence-stale", viewport, assessment_flow)

            def example_size_flow() -> dict[str, Any]:
                original = example_by_id["big-sky-broadview-mt-2026"]
                scale = "scale-hyperscale"
                assert scale not in original["facets"], "Big Sky must start below the size threshold"
                click(page, f'[data-example="{original["id"]}"]', "!document.querySelector('#pcheck-export').disabled")
                page.locator("#pcheck-mw").fill("350")
                page.locator("#pcheck-mgd").fill("2")
                click(page, "#pcheck-run", "!document.querySelector('#pcheck-export').disabled")
                worksheet, _ = worksheet_download(page)
                origins = check_downloaded_inputs(page, worksheet, expected_hash, original)
                assert set(worksheet["retrieval"]["facets"]) == set(original["facets"]) | {scale}, "Manual size must update only the size facet"
                assert origins[scale] == "derived_from_inputs"
                assert all(origin == "curated_example" for facet, origin in origins.items() if facet != scale)
                if not page.locator("#pcheck-facets").evaluate("e=>e.open"):
                    page.locator("#pcheck-facets summary").click()
                page.locator(f'.pcheck-facet-box[value="{scale}"]').uncheck()
                page.locator("#pcheck-mw").fill("400")
                click(page, "#pcheck-run", "!document.querySelector('#pcheck-export').disabled")
                overridden, _ = worksheet_download(page)
                origins = check_downloaded_inputs(page, overridden, expected_hash, original)
                assert origins[scale] == "manual_selection" and scale not in overridden["retrieval"]["facets"]
                click(page, "#pcheck-clear", "document.querySelector('#pcheck-export').disabled")
                page.locator("#pcheck-text").fill("A 300 MW Arizona campus pumps groundwater from wells.")
                click(page, "#pcheck-run", "!document.querySelector('#pcheck-export').disabled")
                assert page.locator(f'.pcheck-facet-box[value="{scale}"]').is_checked()
                page.locator("#pcheck-mw").fill("10")
                page.locator("#pcheck-mgd").fill("0.2")
                click(page, "#pcheck-run", "!document.querySelector('#pcheck-export').disabled")
                smaller, _ = worksheet_download(page)
                origins = check_downloaded_inputs(page, smaller, expected_hash, None)
                assert origins[scale] == "derived_from_inputs" and scale not in smaller["retrieval"]["facets"], "Manual size below threshold must supersede the number in the prose"
                click(page, "#pcheck-clear", "document.querySelector('#pcheck-export').disabled")
                return {"example": original["id"], "size_updated_without_prose_edit": True, "explicit_checkbox_precedence": True,
                        "smaller_manual_size_overrides_description": True}
            record("assessment-size-override", viewport, example_size_flow)
            click(page, 'button[data-tab="explore"]', "!!document.querySelector('#explore-q')")

            def explore_flow() -> dict[str, Any]:
                page.locator("#explore-q").fill("groundwater aquifer cooling discharge permit")
                page.wait_for_function("document.querySelectorAll('.explore-result').length>0")
                row = {"interaction_ms": page.evaluate("performance.now()-__uat.clickStart"), "clicks_from_overview": 1, "interactions_from_overview": 2}
                row.update(geometry(page, "#explore-results"))
                row["graph_fold_open"] = page.locator("#explore-graph-fold").evaluate("e=>e.open")
                assert row["graph_fold_open"] == (width > 760)
                return row
            record("explore-search", viewport, explore_flow)
            if viewport == "mobile":
                page.evaluate("scrollTo(0,800)")
                result["profiles"]["mobile-explore-folded-idle"] = idle_profile(page, cdp)
                record("offscreen-idle", viewport, lambda: {"error": "; ".join(idle_failures(result["profiles"]["mobile-explore-folded-idle"], height)) or None})
                record("explore-open-graph", viewport, lambda: click(page, "#explore-graph-fold summary", "document.querySelector('#explore-graph-fold').open"))
            record("explore-zoom", viewport, lambda: click(page, "#explore-zoom-in", "true"))
            result["profiles"][f"{viewport}-after-all"] = {"heap_bytes": metrics(cdp)["JSHeapUsedSize"], "resources": resources(page), "longtasks": page.evaluate("__uat.longtasks")}
            def lazy_flow() -> dict[str, Any]:
                requests = Counter(r["path"] for r in resources(page))
                assert all(count == 1 for count in requests.values()), f"Duplicate fetches: {requests}"
                assert not any("project-data" in r["path"] or "graph-data" in r["path"] for r in cold["resources"])
                assert requests["/project-data.json"] == requests["/graph-data.json"] == 1
                assert not errors, errors
                return {"request_count": sum(requests.values()), "resource_paths": list(requests)}
            record("lazy-payloads-once", viewport, lazy_flow)
            context.close()

        def dataset_flow() -> dict[str, Any]:
            from jsonschema import Draft202012Validator
            context = browser.new_context()
            page = context.new_page()
            page.goto(base + "tab-check.html")
            manifest = context.request.get(base + "docket-manifest.json").json()
            for name in ("docket-manifest.json", "docket-record.schema.json", "docket-records.jsonl", "docket-dataset.md"):
                assert page.locator(f'a[href="{name}"]').count() > 0, f"Missing download link: {name}"
            downloaded = {}
            for name, metadata in manifest["files"].items():
                response = context.request.get(base + name)
                assert response.status == 200
                body = response.body()
                assert len(body) == metadata["bytes"]
                assert hashlib.sha256(body).hexdigest() == metadata["sha256"]
                downloaded[name] = body
            validator = Draft202012Validator(json.loads(downloaded["docket-record.schema.json"]))
            records = [json.loads(line) for line in downloaded["docket-records.jsonl"].splitlines()]
            assert len(records) == manifest["record_count"] > 0
            for record in records:
                validator.validate(record)
            context.close()
            return {"records_validated": len(records), "files_verified": len(downloaded)}
        record("dataset-downloads", "desktop", dataset_flow)

        nojs = browser.new_context(java_script_enabled=False, viewport={"width": 375, "height": 812})
        page = nojs.new_page()
        for tab in result["tabs"]:
            def nojs_flow(tab: str = tab) -> dict[str, Any]:
                response = page.goto(base + ("index.html" if tab == "overview" else f"tab-{tab}.html"))
                assert response.status == 200
                page.locator(f"#panel-{tab} h2").wait_for(state="visible")
                row = geometry(page, f"#panel-{tab} h2")
                row["content_chars"] = len(page.locator(f"#panel-{tab}").inner_text())
                if tab == "check":
                    card = page.locator(".pcheck-example-card").first
                    card.locator("summary").click()
                    assert card.locator(".pcheck-sec").count() > 0
                    assert card.locator(".pcheck-sec").first.is_visible()
                if tab == "explore":
                    assert page.locator(".explore-noscript").is_visible()
                return row
            record(f"nojs-{tab}", "mobile", nojs_flow)
        nojs.close()

        context = browser.new_context(viewport={"width": 375, "height": 812})
        context.add_init_script(INIT)
        page = context.new_page()
        page.set_default_timeout(20000)
        cdp = context.new_cdp_session(page)
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        cdp.send("Network.enable")
        cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 150, "downloadThroughput": 200000, "uploadThroughput": 93750, "connectionType": "cellular4g"})

        def throttled_flow() -> dict[str, Any]:
            page.goto(base, wait_until="load")
            page.locator("#panel-overview h2").wait_for(state="visible")
            return {**geometry(page, "#panel-overview h2"), "content_ms": page.evaluate("performance.now()"),
                    "content_chars": len(page.locator("#panel-overview").inner_text()),
                    "fcp_ms": page.evaluate("performance.getEntriesByName('first-contentful-paint')[0]?.startTime"),
                    "resources": resources(page), "longtasks": page.evaluate("__uat.longtasks"),
                    "throttle": "4x CPU; 150ms latency; 1.6Mbps down / 0.75Mbps up"}
        record("throttled-cold-overview", "mobile", throttled_flow)
        context.close()

        context = browser.new_context(viewport={"width": 375, "height": 812})
        context.add_init_script(INIT)
        page = context.new_page()
        page.set_default_timeout(20000)
        page.route("**/tab-news.html*", lambda route: route.fulfill(status=503, body="Injected UAT failure"))
        page.goto(base)

        def retry_flow() -> dict[str, Any]:
            row = click(page, 'button[data-tab="news"]', "!!document.querySelector('#panel-news .tab-failed')")
            assert page.locator('#panel-news .tab-failed a').get_attribute('href') == 'tab-news.html'
            page.unroute("**/tab-news.html*")
            row["retry"] = click(page, 'button[data-tab="news"]', "!!document.querySelector('#panel-news h2')")
            return row
        record("lazy-failure-retry", "mobile", retry_flow)
        context.close()
        browser.close()
    result["failures"] = [f"{row['viewport']}/{row['name']}: {failure}" for row in result["rows"] for failure in row["failures"]]
    if not result["rows"]:
        result["failures"].append("No flows measured")
    for name, file in result["files"].items():
        cap = 250000 if name == "index.html" else 1000000 if name.startswith("tab-") and name.endswith(".html") else None
        if cap and file["raw_bytes"] >= cap:
            result["failures"].append(f"{name}: raw bytes {file['raw_bytes']} exceeds existing build budget {cap}")
    result["status"] = "failed" if result["failures"] else "passed"
    out.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, default=Path(__file__).resolve().parents[1] / "pages")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    result = run(args.pages, args.out, args.screenshots)
    logging.info("Measured %s flows; %s failures; result %s", len(result["rows"]), len(result["failures"]), result["status"])
    return int(bool(result["failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
