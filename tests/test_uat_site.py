"""UAT gates reject an empty page, overflow, excessive depth and blocked interaction."""
from __future__ import annotations

import gzip
from pathlib import Path
import urllib.request

import pytest

from scripts.uat_site import budgets, geometry, idle_failures, search_while_graph_loads, serve_snapshot


def test_known_good_browser_row_passes() -> None:
    assert budgets({"content_chars": 120, "key_depth_screens": 0.8,
                    "overflow_px": 0, "interaction_ms": 45, "page_errors": []}) == []


@pytest.mark.parametrize("bad", [
    {"content_chars": 0}, {"key_depth_screens": None},
    {"key_depth_screens": 2.1}, {"key_depth_screens": 1.6, "depth_budget": 1.5},
    {"overflow_px": 20}, {"content_ms": 20001}, {"interaction_ms": 20001},
    {"page_errors": ["ReferenceError: missingEngine"]}, {"error": "click timeout"},
])
def test_known_bad_browser_rows_fail(bad: dict) -> None:
    assert budgets(bad)


def test_server_compression_and_snapshot(tmp_path: Path) -> None:
    original = b"<h1>Data Center Water Use Tracker</h1>" * 50
    (tmp_path / "index.html").write_bytes(original)
    with serve_snapshot(tmp_path) as (url, files):
        (tmp_path / "index.html").write_bytes(b"concurrent rebuild")
        request = urllib.request.Request(url, headers={"Accept-Encoding": "gzip"})
        with urllib.request.urlopen(request) as response:
            payload = response.read()
            assert response.headers["Content-Encoding"] == "gzip"
            assert response.headers["Content-Type"] == "text/html"
        assert gzip.decompress(payload) == files["index.html"] == original
        assert len(payload) < len(original)


def test_offscreen_animation_gate() -> None:
    assert idle_failures({"running_animations": []}, 812) == []
    assert idle_failures({"running_animations": [{"name": "wl-drift", "top": -585, "bottom": -546}]}, 812)
    assert idle_failures({"running_animations": [{"name": "wl-drift", "top": 215, "bottom": 254}]}, 812) == []


def test_browser_geometry_rejects_overflow_depth_and_missing_content() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as pw:
        if not Path(pw.chromium.executable_path).exists():
            pytest.skip("Playwright Chromium is not installed")
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 375, "height": 812})
        page.set_content('<main id="key">A visible project result with its source.</main>')
        assert budgets(geometry(page, "#key")) == []
        page.locator("#key").evaluate("e=>{e.style.marginTop='3000px'; e.style.width='1000px'}")
        failures = budgets(geometry(page, "#key"))
        assert any("overflow" in failure for failure in failures)
        assert any("depth" in failure for failure in failures)
        page.locator("#key").evaluate("e=>e.remove()")
        assert "key content missing" in budgets(geometry(page, "#key"))
        browser.close()


@pytest.fixture(scope="module")
def uat_rebuilt_pages(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from build_site import build_site_files
    root = tmp_path_factory.mktemp("uat-site")
    for name, content in build_site_files().items():
        (root / name).write_text(content, encoding="utf-8")
    return root


@pytest.mark.parametrize("viewport", ["mobile", "desktop"])
def test_search_entered_while_graph_loads(uat_rebuilt_pages: Path, viewport: str) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as pw:
        if not Path(pw.chromium.executable_path).exists():
            pytest.skip("Playwright Chromium is not installed")
        with serve_snapshot(uat_rebuilt_pages) as (base, _), pw.chromium.launch() as browser:
            result = search_while_graph_loads(browser, base, viewport)
            assert result["result_cards"] > 0 and result["first_result"]
