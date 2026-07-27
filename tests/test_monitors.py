"""Tests for the status-monitor pipeline (plan Spec B3).

No network. The fetch layer is injected, so every case here exercises the
diffing and queueing logic against fixtures — which is the part that can be
wrong in a way nobody notices, since a monitor that never fires and a monitor
that always fires both look like "no news".
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from scrapers.monitors.base_monitor import (
    MONITOR_KINDS,
    Candidate,
    MonitorRun,
    Watch,
    first_difference,
    fingerprint,
    invalid_watches,
    iter_watches,
    normalize,
)
from storage import monitor_queue

W = Watch(record_id="rec-1", dataset="legislation", kind="url-watch", key="https://x/1")


def _run(pages: dict[str, str], previous=None, watches=(W,)):
    return MonitorRun(
        fetch=lambda w: pages[w.key],
        previous=dict(previous or {}),
        now="2026-07-26T00:00:00Z",
    ).run(watches)


class TestNormalization:
    def test_ignores_render_timestamps_and_session_tokens(self):
        """The failure that makes a monitor useless: a page embeds a clock or a
        CSRF token, every run reports a change, and the queue gets ignored."""
        a = "<html><body>Permit status: draft <span>3:04 pm</span> "
        a += "<input value='a1b2c3d4e5f60718'></body></html>"
        b = "<html><body>Permit status: draft <span>9:47 am</span> "
        b += "<input value='ffee0011223344556'></body></html>"
        assert fingerprint(a) == fingerprint(b)

    def test_ignores_markup_and_whitespace_churn(self):
        a = "<div><p>Report  due   October 1</p></div>"
        b = "<section>\n  <p>Report due October 1</p>\n</section>"
        assert fingerprint(a) == fingerprint(b)

    def test_detects_a_real_status_change(self):
        a = "<p>Permit status: <b>draft</b></p>"
        b = "<p>Permit status: <b>final</b></p>"
        assert fingerprint(a) != fingerprint(b)

    def test_script_and_style_are_stripped(self):
        a = "<p>Text</p><script>var t=1</script>"
        b = "<p>Text</p><script>var t=2</script><style>p{color:red}</style>"
        assert fingerprint(a) == fingerprint(b)

    def test_normalize_leaves_readable_text(self):
        assert normalize("<h1>Draft</h1><p>Due Oct 1</p>") == "Draft Due Oct 1"


class TestDiffing:
    def test_first_observation_is_labelled_not_a_change(self):
        """A cold start would otherwise report every watched page as changed,
        which teaches a curator to ignore the first real hit too."""
        out = _run({"https://x/1": "<p>draft</p>"})
        assert len(out) == 1
        assert "first observation" in out[0].summary
        assert out[0].previous_fingerprint is None

    def test_unchanged_page_emits_nothing(self):
        page = "<p>draft</p>"
        out = _run({"https://x/1": page}, {"rec-1": fingerprint(page)})
        assert out == []

    def test_change_emits_a_candidate_with_context(self):
        """The excerpt must be the DIFF, not the head of the page.

        The earlier version of this test used a 20-character fixture, so the
        top of the page and the changed region were the same substring — it
        passed while the code returned body[0:240] regardless. The boilerplate
        prefix here makes head != diff, so only a real diff satisfies it.
        """
        boiler = "<p>Status: introduced. " + ("Nothing to see here. " * 40) + "</p>"
        old_body = boiler + "<b>Nothing new here</b>"
        new_body = boiler + "<b>PASSED SENATE 2026-07-20</b>"
        out = MonitorRun(
            fetch=lambda w: new_body,
            previous={"rec-1": fingerprint(old_body)},
            snapshots={"rec-1": normalize(old_body)},
            now="t",
        ).run([W])
        assert len(out) == 1
        assert out[0].summary == "watched page changed since last run"
        assert "PASSED SENATE" in out[0].excerpt
        assert "Status: introduced" not in out[0].excerpt

    def test_excerpt_is_empty_rather_than_misleading_without_a_snapshot(self):
        """A first run has nothing to diff against. An empty excerpt is honest;
        the head of the page labelled as the change is not."""
        long_body = "<p>" + ("filler " * 100) + "CHANGED</p>"
        out = MonitorRun(
            fetch=lambda w: long_body,
            previous={"rec-1": "stale-fp"},
            snapshots={},
            now="t",
        ).run([W])
        assert out[0].excerpt == ""

    def test_snapshots_are_updated_for_the_next_run(self):
        run = MonitorRun(fetch=lambda w: "<p>v2</p>", previous={}, snapshots={}, now="t")
        run.run([W])
        assert run.snapshots["rec-1"] == "v2"

    @pytest.mark.parametrize(
        "label,body",
        [
            ("unterminated openers", "<script>" * 40000),
            ("unterminated comments", "<!--" * 30000),
            ("large well-formed", "<div><script>var x=1</script><p>hi</p></div>" * 40000),
        ],
    )
    def test_normalize_stays_linear_on_hostile_input(self, label, body):
        """A lazy DOTALL `<script>.*?</script>` rescans to end-of-string at every
        unterminated opener — 40k of them took ~56s, and input is arbitrary
        third-party HTML. Block stripping is a linear str.find scan now."""
        import time

        t0 = time.monotonic()
        normalize(body)
        assert time.monotonic() - t0 < 1.0, label

    def test_fetch_failure_is_surfaced_not_swallowed(self):
        """An unreachable page usually means it moved, which is exactly the
        kind of staleness the monitors exist to catch."""

        def boom(_w):
            raise ConnectionError("host unreachable")

        out = MonitorRun(fetch=boom, previous={}, now="t").run([W])
        assert len(out) == 1
        assert "fetch failed" in out[0].summary
        assert out[0].fingerprint == ""

    def test_one_bad_page_does_not_abort_the_sweep(self):
        good = Watch(record_id="rec-2", dataset="legislation", kind="url-watch", key="https://x/2")

        def fetch(w):
            if w.key.endswith("/1"):
                raise TimeoutError("slow")
            return "<p>ok</p>"

        out = MonitorRun(fetch=fetch, previous={}, now="t").run([W, good])
        assert {c.record_id for c in out} == {"rec-1", "rec-2"}

    def test_first_difference_returns_empty_when_identical(self):
        assert first_difference("<p>same</p>", "<p>same</p>") == ""


class TestWatchListDerivation:
    def test_watches_come_from_the_datasets(self):
        """Single source of truth: the watch list is whatever carries a
        `monitor` block, so it cannot drift from the records it watches."""
        watches = list(iter_watches())
        assert len(watches) >= 5
        assert {w.record_id for w in watches} <= set(_all_record_ids())

    def test_every_watch_is_actionable(self):
        assert invalid_watches() == []

    def test_kinds_are_from_the_closed_set(self):
        for w in iter_watches():
            assert w.kind in MONITOR_KINDS

    def test_each_watch_explains_what_it_is_waiting_for(self):
        """A monitor with no note is a page that changed for reasons nobody
        recorded — the curator has to re-derive why it was watched."""
        for w in iter_watches():
            assert len(w.note) > 20, w.record_id

    def test_the_known_pending_decisions_are_watched(self):
        watched = {w.record_id for w in iter_watches()}
        for expected in (
            "OH EPA OHD000001 (draft general permit)",
            "VA DEQ waterworks data-center reporting regulations",
            "NY EO 62",
        ):
            assert expected in watched, expected


def _all_record_ids():
    from refdata.loaders import (
        load_cwa_investigations,
        load_dc_water_conflicts,
        load_legislation,
    )

    return (
        [b["bill_id"] for b in load_legislation()["bills"]]
        + [c["case_id"] for c in load_cwa_investigations()["cases"]]
        + [s["site_id"] for s in load_dc_water_conflicts()["sites"]]
    )


class TestQueue:
    def test_append_is_additive_and_deduplicated(self, tmp_path):
        path = tmp_path / "hits.json"
        c = {"record_id": "r", "fingerprint": "abc", "summary": "changed"}
        assert monitor_queue.append_candidates([c], "t1", path) == 1
        # Re-running before triage must not pile up copies.
        assert monitor_queue.append_candidates([c], "t2", path) == 0
        assert monitor_queue.append_candidates(
            [{"record_id": "r", "fingerprint": "def", "summary": "changed again"}],
            "t3",
            path,
        ) == 1
        payload = json.loads(path.read_text())
        assert len(payload["candidates"]) == 2

    def test_a_reverted_page_is_not_silently_dropped(self, tmp_path):
        """A -> B -> A. Keying dedupe on the destination fingerprint alone made
        the revert collide with the original baseline, so it was dropped
        permanently while the run still advanced the stored fingerprint."""
        path = tmp_path / "hits.json"
        assert monitor_queue.append_candidates(
            [{"record_id": "r", "previous_fingerprint": None, "fingerprint": "A"}],
            "t1", path,
        ) == 1
        assert monitor_queue.append_candidates(
            [{"record_id": "r", "previous_fingerprint": "A", "fingerprint": "B"}],
            "t2", path,
        ) == 1
        assert monitor_queue.append_candidates(
            [{"record_id": "r", "previous_fingerprint": "B", "fingerprint": "A"}],
            "t3", path,
        ) == 1, "the revert back to A must be queued"

    def test_distinct_failures_are_distinct_rows(self, tmp_path):
        """Every failure has an empty fingerprint, so keying on it alone made a
        500 followed by a 404 dedupe into one row — a dying watch going quiet."""
        path = tmp_path / "hits.json"
        base = {"record_id": "r", "previous_fingerprint": None, "fingerprint": ""}
        assert monitor_queue.append_candidates(
            [dict(base, summary="fetch failed: 500")], "t1", path
        ) == 1
        assert monitor_queue.append_candidates(
            [dict(base, summary="fetch failed: 404")], "t2", path
        ) == 1
        assert monitor_queue.append_candidates(
            [dict(base, summary="fetch failed: 500")], "t3", path
        ) == 0

    def test_snapshots_live_in_their_own_file(self, tmp_path):
        """Snapshots are whole pages — an order of magnitude larger than the
        fingerprints and useless to a reader. They stay out of git; losing them
        only costs the excerpt, since the fingerprint still detects the change."""
        fp = tmp_path / "fp.json"
        monitor_queue.save_fingerprints({"r": "1"}, "t", fp, snapshots={"r": "body"})
        snap = monitor_queue.snapshot_path_for(fp)
        assert monitor_queue.load_fingerprints(fp) == {"r": "1"}
        assert monitor_queue.load_snapshots(snap) == {"r": "body"}
        assert "body" not in fp.read_text(), "committed file must not carry page text"

    def test_triaged_entries_are_never_dropped(self, tmp_path):
        """Append-only per CLAUDE.md §3: 'we looked and it was nothing' is a
        record worth keeping."""
        path = tmp_path / "hits.json"
        monitor_queue.append_candidates(
            [{"record_id": "old", "fingerprint": "1"}], "t1", path
        )
        monitor_queue.append_candidates(
            [{"record_id": "new", "fingerprint": "2"}], "t2", path
        )
        ids = {c["record_id"] for c in json.loads(path.read_text())["candidates"]}
        assert ids == {"old", "new"}

    def test_fingerprint_cache_roundtrips(self, tmp_path):
        path = tmp_path / "fp.json"
        assert monitor_queue.load_fingerprints(path) == {}
        monitor_queue.save_fingerprints({"r": "abc"}, "t1", path)
        assert monitor_queue.load_fingerprints(path) == {"r": "abc"}

    def test_corrupt_cache_degrades_to_a_cold_start(self, tmp_path):
        """A truncated cache must cost one round of labelled 'first
        observation' candidates, not a failed sweep."""
        path = tmp_path / "fp.json"
        path.write_text("{not json")
        assert monitor_queue.load_fingerprints(path) == {}

    def test_corrupt_queue_is_quarantined_not_overwritten(self, tmp_path, capsys):
        """Found by Codex. Treating a truncated queue as empty and then writing
        over it destroys the entire append-only audit trail. My original test
        asserted only that the NEW candidate survived — never that the prior
        ones did, which is precisely what was being lost."""
        path = tmp_path / "hits.json"
        path.write_text('{"candidates": [{"record_id": "old", "fingerprint": "9"}]')  # truncated
        assert monitor_queue.append_candidates(
            [{"record_id": "r", "fingerprint": "1"}], "t", path
        ) == 1
        quarantine = path.with_suffix(path.suffix + ".corrupt")
        assert quarantine.exists(), "damaged bytes must survive for recovery"
        assert "old" in quarantine.read_text()
        assert "unreadable" in capsys.readouterr().out

    def test_writes_are_atomic(self, tmp_path):
        """An interrupted write is what produces the corrupt file above."""
        path = tmp_path / "hits.json"
        monitor_queue.append_candidates([{"record_id": "r", "fingerprint": "1"}], "t", path)
        assert not list(tmp_path.glob("*.tmp")), "temp file left behind"
        assert json.loads(path.read_text())["candidates"]


class TestPathsAreRedirectable:
    """Regression guard. These paths were module-constant DEFAULT ARGUMENTS,
    which bind at import — monkeypatching the constant did nothing and a test
    wrote to the real data/state file. Resolving at call time fixes it."""

    def test_queue_and_cache_honour_a_patched_constant(self, tmp_path, monkeypatch):
        monkeypatch.setattr(monitor_queue, "QUEUE_PATH", tmp_path / "q.json")
        monkeypatch.setattr(monitor_queue, "FINGERPRINT_PATH", tmp_path / "fp.json")
        monitor_queue.append_candidates([{"record_id": "r", "fingerprint": "1"}], "t")
        monitor_queue.save_fingerprints({"r": "1"}, "t")
        assert (tmp_path / "q.json").exists()
        assert (tmp_path / "fp.json").exists()

    def test_state_files_are_tracked_not_ignored(self):
        """Reversed deliberately. I first gitignored these as "ops artifacts,
        not curated data", then spent six review rounds building cache and
        artifact machinery to stop losing them. The queue is an append-only
        audit trail; git is the durable append-only store this project already
        uses for exactly that."""
        import pathlib

        ignore = (pathlib.Path(monitor_queue.BASE_DIR) / ".gitignore").read_text()
        assert "monitor_hits.json" not in ignore
        assert "monitor_fingerprints.json" not in ignore


class TestNoAutomaticWrites:
    def test_monitors_never_import_a_dataset_writer(self):
        """The curated layer's value is that a person checked it. A monitor
        that could write to it would trade that away silently."""
        import pathlib

        import scrapers.monitors.base_monitor as bm

        source = pathlib.Path(bm.__file__).read_text()
        for forbidden in ("json.dump", "write_text", "open(", "w+"):
            assert forbidden not in source, forbidden


class TestClients:
    """The three fetchers. No network: `get` is a stub throughout."""

    @staticmethod
    def _fetch(pages, kind, key):
        from scrapers.monitors.clients import make_fetcher

        return make_fetcher(lambda url: pages[url])(
            Watch(record_id="r", dataset="legislation", kind=kind, key=key)
        )

    def test_url_watch_passes_the_page_through(self):
        out = self._fetch({"https://x/1": "<p>hi</p>"}, "url-watch", "https://x/1")
        assert out == "<p>hi</p>"

    def test_legiscan_canonicalization_ignores_churn(self):
        """The full payload carries vote rosters and text hashes that move
        independently of status; fingerprinting them all would fire every run."""
        from scrapers.monitors.clients import canonical_legiscan

        base = {"status": "OK",
                "bill": {"status": 4, "status_date": "2026-07-01",
                         "last_action": "Passed", "last_action_date": "2026-07-01",
                         "bill_number": "S10642"}}
        noisy = {"status": "OK",
                 "bill": dict(base["bill"], votes=[1, 2, 3], texts=["hash-a"],
                              sponsors=[{"name": "X"}])}
        assert canonical_legiscan(base) == canonical_legiscan(noisy)

    def test_legiscan_detects_a_real_status_move(self):
        from scrapers.monitors.clients import canonical_legiscan

        a = {"status": "OK", "bill": {"status": 4, "last_action": "Passed Senate"}}
        b = {"status": "OK", "bill": {"status": 5, "last_action": "Vetoed"}}
        assert canonical_legiscan(a) != canonical_legiscan(b)

    def test_federal_register_is_order_independent(self):
        from scrapers.monitors.clients import canonical_federal_register

        d1 = {"document_number": "1", "title": "A", "publication_date": "2026-01-01"}
        d2 = {"document_number": "2", "title": "B", "publication_date": "2026-02-01"}
        assert canonical_federal_register({"results": [d1, d2]}) == (
            canonical_federal_register({"results": [d2, d1]})
        )

    def test_federal_register_detects_a_new_document(self):
        from scrapers.monitors.clients import canonical_federal_register

        d1 = {"document_number": "1", "title": "A", "publication_date": "2026-01-01"}
        d2 = {"document_number": "2", "title": "B", "publication_date": "2026-02-01"}
        assert canonical_federal_register({"results": [d1]}) != (
            canonical_federal_register({"results": [d1, d2]})
        )

    def test_missing_credential_is_raised_not_swallowed(self, monkeypatch):
        """A watch that silently stops running looks exactly like one
        reporting no change — the failure the monitors exist to prevent."""
        from scrapers.monitors.clients import MissingCredential

        monkeypatch.delenv("LEGISCAN_API_KEY", raising=False)
        with pytest.raises(MissingCredential):
            self._fetch({}, "legiscan", "NY S10642")

    def test_missing_credential_surfaces_as_a_candidate(self, monkeypatch):
        """MonitorRun catches fetch errors, so the sweep must still report the
        unrun watch rather than dropping it."""
        from scrapers.monitors.clients import make_fetcher

        monkeypatch.delenv("LEGISCAN_API_KEY", raising=False)
        w = Watch(record_id="r", dataset="legislation", kind="legiscan", key="NY S1")
        out = MonitorRun(fetch=make_fetcher(lambda u: ""), previous={}, now="t").run([w])
        assert len(out) == 1 and "fetch failed" in out[0].summary

    def test_api_key_never_reaches_the_candidate_or_the_queue(self, monkeypatch):
        """httpx puts the request URL in its error text, MonitorRun formats that
        into a Candidate, and the Candidate is printed and written to disk. A
        single 403 from LegiScan would otherwise burn the key into logs."""
        import httpx

        from scrapers.monitors.clients import make_fetcher

        monkeypatch.setenv("LEGISCAN_API_KEY", "SUPERSECRET123")

        def get(url):
            raise httpx.HTTPStatusError(
                f"Client error '403 Forbidden' for url '{url}'",
                request=None,
                response=None,
            )

        w = Watch(record_id="r", dataset="legislation", kind="legiscan", key="NY S1")
        out = MonitorRun(fetch=make_fetcher(get), previous={}, now="t").run([w])
        blob = json.dumps(out[0].as_dict())
        assert "SUPERSECRET123" not in blob
        assert "***" in blob

    def test_unknown_kind_is_rejected(self):
        with pytest.raises(ValueError):
            self._fetch({}, "carrier-pigeon", "x")


class TestRunner:
    def test_dry_run_writes_nothing(self, tmp_path, monkeypatch, capsys):
        from scrapers.monitors import run as runner

        monkeypatch.setattr(runner.monitor_queue, "QUEUE_PATH", tmp_path / "q.json")
        monkeypatch.setattr(runner, "_polite_get", lambda *a, **k: (lambda url: "<p>x</p>"))
        assert runner.main(["--dry-run"]) == 0
        assert not (tmp_path / "q.json").exists()
        assert "dry run" in capsys.readouterr().out

    def test_failed_fetch_does_not_advance_the_baseline(self, tmp_path, monkeypatch):
        """Baselining a watch that never fetched would make the next run report
        no change — the failure would silently heal itself."""
        from scrapers.monitors import run as runner

        q, fp = tmp_path / "q.json", tmp_path / "fp.json"
        monkeypatch.setattr(runner.monitor_queue, "QUEUE_PATH", q)
        monkeypatch.setattr(runner.monitor_queue, "FINGERPRINT_PATH", fp)

        def boom(url):
            raise ConnectionError("down")

        monkeypatch.setattr(runner, "_polite_get", lambda *a, **k: boom)
        assert runner.main([]) == 0
        saved = json.loads(fp.read_text())["fingerprints"]
        assert saved == {}, "a failed fetch must not be baselined"

    def test_unknown_only_target_exits_nonzero(self, monkeypatch):
        from scrapers.monitors import run as runner

        monkeypatch.setattr(runner, "_polite_get", lambda *a, **k: (lambda url: ""))
        assert runner.main(["--only", "no-such-record"]) == 1


class TestLegiScanIdResolution:
    """Codex P1 on the re-review: `getBill` takes LegiScan's internal numeric
    id, not a bill number. Passing "NY S10642" returns an error payload, and
    because nothing validated the response status that payload canonicalized
    to a stable all-null fingerprint — a watch that looks healthy forever and
    can never fire."""

    def test_error_payload_raises_instead_of_fingerprinting_nulls(self):
        from scrapers.monitors.clients import canonical_legiscan

        with pytest.raises(RuntimeError, match="ERROR"):
            canonical_legiscan({"status": "ERROR", "alert": {"message": "Unknown id"}})

    def test_an_error_payload_would_otherwise_look_stable(self):
        """Demonstrates the bug being guarded: two DIFFERENT errors reduce to
        the same fields, so without validation they hash identically and the
        watch reports 'no change' forever."""
        from scrapers.monitors.clients import canonical_legiscan

        for payload in (
            {"status": "ERROR", "alert": {"message": "Unknown id"}},
            {"status": "ERROR", "alert": {"message": "Rate limit"}},
        ):
            with pytest.raises(RuntimeError):
                canonical_legiscan(payload)

    def test_numeric_key_is_used_directly(self):
        from scrapers.monitors.clients import resolve_legiscan_bill_id

        called = []
        assert resolve_legiscan_bill_id("4213", lambda u: called.append(u), "k") == "4213"
        assert not called, "a numeric id needs no search round-trip"

    def test_bill_number_resolves_by_exact_match(self):
        """A fuzzy relevance hit must not silently select the wrong bill."""
        from scrapers.monitors.clients import resolve_legiscan_bill_id

        body = json.dumps({
            "status": "OK",
            "searchresult": {
                "summary": {"count": 2},
                "0": {"bill_number": "S1064", "bill_id": 111},
                "1": {"bill_number": "S10642", "bill_id": 999},
            },
        })
        assert resolve_legiscan_bill_id("NY S10642", lambda u: body, "k") == "999"

    def test_unresolvable_bill_fails_loudly(self):
        from scrapers.monitors.clients import resolve_legiscan_bill_id

        body = json.dumps({"status": "OK", "searchresult": {"summary": {"count": 0}}})
        with pytest.raises(RuntimeError, match="no bill numbered"):
            resolve_legiscan_bill_id("NY S99999", lambda u: body, "k")

    def test_malformed_key_is_rejected(self):
        from scrapers.monitors.clients import resolve_legiscan_bill_id

        with pytest.raises(ValueError):
            resolve_legiscan_bill_id("S10642", lambda u: "", "k")

    def test_watch_keys_in_the_dataset_are_resolvable_shapes(self):
        for w in iter_watches():
            if w.kind == "legiscan":
                assert w.key.strip().isdigit() or len(w.key.split()) == 2, w.record_id


class TestStepSummary:
    """Codex: once the queue persists across runs, anything summarizing the
    FILE re-reports the first change it ever saw as current, every week."""

    def test_summary_reports_only_this_runs_candidates(self):
        from scrapers.monitors.run import build_step_summary

        c = Candidate(
            record_id="rec-now", dataset="legislation", kind="url-watch",
            key="k", previous_fingerprint="a", fingerprint="b",
            summary="watched page changed since last run", detected_at="t2",
            note="Ohio permit finalization",
        )
        out = build_step_summary([c], [], [], total_queued=1)
        assert "rec-now" in out
        assert "**1 changed**" in out
        # It is handed candidates, never the queue file, so history cannot leak.
        import inspect
        import scrapers.monitors.run as runner
        assert "monitor_hits" not in inspect.getsource(runner.build_step_summary)

    def test_quiet_run_says_so(self):
        from scrapers.monitors.run import build_step_summary

        assert "nothing to triage" in build_step_summary([], [], [], 0)

    def test_workflow_does_not_reparse_the_queue(self):
        import pathlib

        raw = (
            pathlib.Path(monitor_queue.BASE_DIR) / ".github/workflows/monitors.yml"
        ).read_text()
        assert "monitor_hits.json" in raw, "artifact upload should still reference it"
        # ...but no step may re-derive the summary by READING that file. Check
        # the parsed run blocks, not prose — the comments legitimately discuss
        # candidates (a raw grep here would repeat the contents:-write mistake).
        import yaml

        # The intent is "no step DERIVES the summary from the queue file", not
        # "no step may mention the path" — the recovery step legitimately
        # ls-checks it. Three versions of this assertion have now been too
        # broad; assert the mechanism instead.
        wf = yaml.safe_load(raw)
        for step in wf["jobs"]["sweep"]["steps"]:
            body = step.get("run", "")
            assert "GITHUB_STEP_SUMMARY" not in body, (
                f"{step.get('name')} writes the summary; run.py owns it"
            )
            assert "json.loads" not in body, f"{step.get('name')} parses the queue"


class TestSharedClaimStyles:
    def test_lifecycle_classes_are_in_the_shared_stylesheet(self):
        """Sharing the markup without the styles is only half a shared
        component: Streamlit injects assets/components.css and would otherwise
        render the chips as bare text."""
        import pathlib

        css = (
            pathlib.Path(monitor_queue.BASE_DIR) / "assets" / "components.css"
        ).read_text()
        for cls in (".claim-chips", ".claim-type-pill", ".claim-challenge-pill",
                    ".claim-site-link"):
            assert cls in css, cls


class TestSurfaceAwareClaimLinks:
    """Codex round 5: only the static site has the JS that activates a
    fragment's owning tab. In Streamlit an `#cwa-…` href rewrites the hash and
    leaves the reader where they were — worse than plain text, because it
    looks clickable."""

    @staticmethod
    def _claim():
        from refdata.loaders import load_company_water_claims

        return next(
            c for c in load_company_water_claims()["claims"] if c.get("challenged_in")
        )

    def test_static_surface_keeps_the_hyperlinks(self):
        import dashboard as dash

        out = dash._build_claim_lifecycle_html(self._claim())
        assert 'href="#cwa-' in out

    def test_streamlit_surface_emits_no_fragment_hrefs(self):
        import dashboard as dash

        out = dash._build_claim_lifecycle_html(self._claim(), link_anchors=False)
        assert 'href="#' not in out
        # Same information, still reachable by hand.
        assert "Challenged in court" in out
        assert "Water Cases" in out

    def test_both_surfaces_carry_the_same_claim_type(self):
        import dashboard as dash

        claim = self._claim()
        for linked in (True, False):
            out = dash._build_claim_lifecycle_html(claim, link_anchors=linked)
            assert "claim-type-pill" in out


class TestNoDeadAffordances:
    """Codex round 9: removing the href but keeping .claim-site-link left the
    text link-blue and underlined on hover — still advertising a click that
    does nothing, which is exactly what link_anchors=False exists to remove."""

    @staticmethod
    def _claim():
        from refdata.loaders import load_company_water_claims

        return next(
            c for c in load_company_water_claims()["claims"]
            if c.get("challenged_in") or c.get("related_site_ids")
        )

    def test_unlinked_surface_uses_non_link_classes(self):
        import dashboard as dash

        out = dash._build_claim_lifecycle_html(self._claim(), link_anchors=False)
        assert "claim-site-link" not in out
        assert "claim-challenge-pill" not in out

    def test_link_styling_is_scoped_to_real_anchors(self):
        """Even if a hrefless span ever reuses the class, the CSS must not
        make it look clickable."""
        import pathlib

        css = (
            pathlib.Path(monitor_queue.BASE_DIR) / "assets" / "components.css"
        ).read_text()
        assert "a.claim-site-link {" in css
        assert "a.claim-site-link:hover" in css


class TestScheduledSweepWorkflow:
    """The weekly routine.

    State lives in git rather than the actions cache. The cache design needed
    five steps and ~56 lines of shell to avoid losing one small JSON file, and
    six consecutive review rounds found defects in it. These tests pin the
    properties that made the replacement worth making.
    """

    @staticmethod
    def _wf():
        import pathlib

        import yaml

        return yaml.safe_load(
            (pathlib.Path(monitor_queue.BASE_DIR) / ".github/workflows/monitors.yml")
            .read_text()
        )

    def test_state_is_committed_not_cached(self):
        """Git is durable and append-only; the actions cache is neither."""
        wf = self._wf()
        steps = wf["jobs"]["sweep"]["steps"]
        assert not any("cache@" in s.get("uses", "") for s in steps), "state is in git now"
        assert not any("artifact" in s.get("uses", "") for s in steps)
        commit = next(s for s in steps if "Commit" in s.get("name", ""))
        for path in ("monitor_hits.json", "monitor_fingerprints.json"):
            assert path in commit["run"], path

    def test_only_ops_state_can_be_committed(self):
        """Monitors propose; humans dispose. The sweep must be incapable of
        committing a curated dataset even if some future change writes one."""
        commit = next(
            s for s in self._wf()["jobs"]["sweep"]["steps"] if "Commit" in s.get("name", "")
        )
        body = commit["run"]
        assert "data/reference" not in body
        # No blanket adds — every staged path is named explicitly.
        for blanket in ("git add .", "git add -A\n", "git add --all", "git commit -a"):
            assert blanket not in body, blanket

    def test_missing_state_file_does_not_abort_the_commit(self):
        """`git add` on a missing path fails under `set -e`, and a sweep with
        nothing to queue writes no queue."""
        commit = next(
            s for s in self._wf()["jobs"]["sweep"]["steps"] if "Commit" in s.get("name", "")
        )
        assert '[ -f "$f" ]' in commit["run"]

    def test_push_rebases_first(self):
        """Concurrency prevents overlapping sweeps, not a human committing a
        triage edit while one runs."""
        commit = next(
            s for s in self._wf()["jobs"]["sweep"]["steps"] if "Commit" in s.get("name", "")
        )
        body = commit["run"]
        assert "--rebase" in body
        assert body.index("--rebase") < body.index("git push")

    def test_write_scope_is_the_only_permission(self):
        """Assert the property, not an exact dict — an earlier version pinned
        `{"contents": "read"}` and broke on a legitimate read-only addition."""
        perms = self._wf()["permissions"]
        assert perms == {"contents": "write"} or set(perms) <= {"contents", "actions"}
        assert perms.get("contents") == "write", "committing state needs write"

    def test_actions_are_sha_pinned(self):
        for step in self._wf()["jobs"]["sweep"]["steps"]:
            uses = step.get("uses")
            if uses:
                assert len(uses.split("@")[1]) == 40, f"{uses} is not SHA-pinned"

    def test_run_py_owns_the_summary(self):
        """No step may re-derive the summary from the append-only queue file,
        which carries every prior run's history."""
        for step in self._wf()["jobs"]["sweep"]["steps"]:
            body = step.get("run", "")
            assert "GITHUB_STEP_SUMMARY" not in body, step.get("name")
            assert "json.loads" not in body, step.get("name")


class TestSnapshotsPersist:
    """Codex round 11. I gitignored snapshots reasoning that losing them "only
    costs the excerpt" — but that assumed EXCEPTIONAL loss. Every CI run starts
    on a fresh runner, so an ignored file is lost every single time and the
    excerpt would never appear at all."""

    def test_snapshots_are_committed(self):
        import pathlib

        ignore = (pathlib.Path(monitor_queue.BASE_DIR) / ".gitignore").read_text()
        assert "monitor_fingerprints_snapshots.json" not in ignore

    def test_workflow_commits_all_three_state_files(self):
        import pathlib

        import yaml

        wf = yaml.safe_load(
            (pathlib.Path(monitor_queue.BASE_DIR) / ".github/workflows/monitors.yml")
            .read_text()
        )
        commit = next(
            s for s in wf["jobs"]["sweep"]["steps"] if "Commit" in s.get("name", "")
        )
        for f in ("monitor_hits.json", "monitor_fingerprints.json",
                  "monitor_fingerprints_snapshots.json"):
            assert f in commit["run"], f

    def test_snapshots_are_capped(self, tmp_path):
        """Committed weekly, so one verbose page must not bloat the repo."""
        fp, snap = tmp_path / "fp.json", tmp_path / "snap.json"
        monitor_queue.save_fingerprints(
            {"r": "1"}, "t", fp,
            snapshots={"r": "x" * (monitor_queue.MAX_SNAPSHOT_CHARS + 5000)},
            snapshot_path=snap,
        )
        stored = monitor_queue.load_snapshots(snap)["r"]
        assert len(stored) == monitor_queue.MAX_SNAPSHOT_CHARS


class TestDocsMatchTheWorkflow:
    def test_refresh_does_not_reference_a_removed_artifact(self):
        """REFRESH.md is the canonical instruction; it told curators to
        download a `monitor-hits` artifact that the git-backed workflow no
        longer produces."""
        import pathlib

        base = pathlib.Path(monitor_queue.BASE_DIR)
        refresh = (base / "REFRESH.md").read_text()
        wf = (base / ".github/workflows/monitors.yml").read_text()
        if "upload-artifact" not in wf:
            # Scoped to the MONITOR artifact by name. A bare "artifact" match
            # also hits the unrelated pages/ build artifacts — the sixth
            # over-broad assertion in this PR, and the same mistake each time:
            # matching an incidental word instead of the specific thing.
            assert "monitor-hits" not in refresh, (
                "REFRESH.md still points curators at the removed monitor-hits artifact"
            )
        assert "data/output/monitor_hits.json" in refresh


class TestRedirectionIsAtomic:
    """Codex round 12, and a REPEAT of the class this module already fixed:
    a test redirecting one state path while another silently wrote to the
    repository. Running the suite destroyed 22KB of real snapshots, replacing
    them with a 60-byte test payload."""

    def test_redirecting_fingerprints_also_redirects_snapshots(self, tmp_path):
        real_before = (
            monitor_queue.SNAPSHOT_PATH.read_bytes()
            if monitor_queue.SNAPSHOT_PATH.exists()
            else None
        )
        fp = tmp_path / "fp.json"
        monitor_queue.save_fingerprints({"r": "1"}, "t", fp, snapshots={"r": "body"})

        assert monitor_queue.snapshot_path_for(fp).exists()
        real_after = (
            monitor_queue.SNAPSHOT_PATH.read_bytes()
            if monitor_queue.SNAPSHOT_PATH.exists()
            else None
        )
        assert real_after == real_before, "redirected write touched repository state"

    def test_omitting_snapshots_leaves_the_file_alone(self, tmp_path):
        """`None` = not managing snapshots; `{}` = legitimately clearing them.
        Conflating them let a caller that never mentioned snapshots wipe them."""
        fp = tmp_path / "fp.json"
        snap = monitor_queue.snapshot_path_for(fp)
        monitor_queue.save_fingerprints({"r": "1"}, "t", fp, snapshots={"r": "keep"})
        monitor_queue.save_fingerprints({"r": "2"}, "t", fp)  # no snapshots kwarg
        assert monitor_queue.load_snapshots(snap) == {"r": "keep"}

    def test_default_paths_stay_paired(self):
        assert monitor_queue.snapshot_path_for(monitor_queue.FINGERPRINT_PATH) == (
            monitor_queue.SNAPSHOT_PATH
        )


class TestSuiteDoesNotDirtyTheCheckout:
    """The class of bug this module has now shipped TWICE: a test redirecting
    one state path while another silently wrote to the repository. First as
    default arguments bound at import, then as a special case in the path
    derivation that read the module global a test had just patched.

    This asserts the invariant directly rather than any particular mechanism,
    so a third variation cannot slip through.
    """

    def test_no_state_write_escapes_a_redirect(self, tmp_path):
        import itertools

        real = [
            monitor_queue.QUEUE_PATH,
            monitor_queue.FINGERPRINT_PATH,
            monitor_queue.SNAPSHOT_PATH,
        ]
        before = {p: (p.read_bytes() if p.exists() else None) for p in real}

        # Every shape a caller might use, none of which names SNAPSHOT_PATH.
        fp = tmp_path / "fp.json"
        for snaps in ({"r": "body"}, {}, None):
            monitor_queue.save_fingerprints({"r": "1"}, "t", fp, snapshots=snaps)
        monitor_queue.append_candidates(
            [{"record_id": "r", "fingerprint": "1"}], "t", tmp_path / "q.json"
        )

        after = {p: (p.read_bytes() if p.exists() else None) for p in real}
        changed = [p.name for p in real if before[p] != after[p]]
        assert not changed, f"redirected calls wrote to repository state: {changed}"

    def test_derivation_has_no_special_case_for_the_default(self):
        """A branch on `== FINGERPRINT_PATH` reads the module global, which a
        monkeypatching test has already replaced — so the special case fires
        exactly when redirection was requested."""
        import inspect

        src = inspect.getsource(monitor_queue.snapshot_path_for)
        assert "== FINGERPRINT_PATH" not in src
        assert "SNAPSHOT_PATH" not in src.split('"""')[-1], (
            "derivation must not reference the module-level default"
        )
