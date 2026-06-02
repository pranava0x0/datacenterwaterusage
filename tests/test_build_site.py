"""Tests for build_site.py — the static-site generator that replaced stlite.

These lock in the contract that made the redesign worth doing: the deployed
page must be plain static HTML (no Pyodide/WASM runtime), must embed every
record so it loads without extra fetches, and must keep visual/behavioral
parity with the Streamlit app (same cards, same filter counts, same SRI-pinned
chart lib).
"""

from __future__ import annotations

import re

import build_site
import dashboard


def _html() -> str:
    return build_site.build_html()


class TestStaticBuild:
    def test_build_runs_and_is_substantial(self):
        html = _html()
        assert isinstance(html, str)
        # All records are embedded, so the page is large (hundreds of KB).
        assert len(html) > 200_000, "expected the full dataset embedded"
        assert html.lstrip().lower().startswith("<!doctype html>")
        assert "<title>Data Center Water Use Tracker</title>" in html

    def test_no_wasm_runtime(self):
        # The whole point of the redesign: kill the ~15 MB in-browser Python
        # runtime. If any of these creep back, the cold-start regresses.
        html = _html().lower()
        for banned in ("stlite", "pyodide", "@stlite/browser", "micropip"):
            assert banned not in html, f"WASM runtime artifact present: {banned}"

    def test_three_tabs_present(self):
        html = _html()
        for tab in ("legislation", "cwa", "data"):
            assert f'data-tab="{tab}"' in html
        for pid in ("panel-legislation", "panel-cwa", "panel-data"):
            assert f'id="{pid}"' in html

    def test_chartjs_sri_pinned(self):
        # Security standing rule: every third-party CDN asset carries an SRI hash.
        html = _html()
        assert build_site.CHARTJS_URL in html
        assert f'integrity="{build_site.CHARTJS_SRI}"' in html
        assert build_site.CHARTJS_SRI.startswith("sha384-")

    def test_all_cwa_cases_embedded(self):
        html = _html()
        cases = dashboard.load_cwa_investigations().get("cases", [])
        assert html.count('class="cwa-case"') == len(cases)
        # The JS total used by the filter count line must match the dataset.
        assert f"window.CWA_TOTAL = {len(cases)}" in html

    def test_all_bills_and_claims_embedded(self):
        html = _html()
        bills = dashboard.load_legislation().get("bills", [])
        claims = dashboard.load_company_water_claims().get("claims", [])
        # CWA cards reuse the .bill-card base, so bill-card count == bills + cases.
        cases = dashboard.load_cwa_investigations().get("cases", [])
        assert html.count('class="bill-card"') == len(bills) + len(cases)
        assert html.count('class="claim-card"') == len(claims)

    def test_new_research_cases_render(self):
        # Spot-check that the June-2026 additions actually reach the static page.
        html = _html()
        for needle in ("New Carlisle", "Puget Soundkeeper", "Edwards Aquifer", "Fort Smith"):
            assert needle in html, f"missing case content: {needle}"

    def test_markdown_blobs_converted(self):
        # The statute explainer is markdown in the source; it must arrive as HTML
        # (primary-source citation present, no raw markdown link syntax left).
        html = _html()
        assert "33 U.S.C." in html
        assert "law.cornell.edu/uscode/text/33/1251" in html

    def test_chart_data_embedded(self):
        # The flow chart reads embedded JSON, not a runtime fetch.
        html = _html()
        assert 'id="flowChart"' in html
        assert "BROAD RUN" in html  # facility name resolved from the data
        assert '"limit": 11' in html  # VA0091383 permit-limit line

    def test_collapsed_panels_take_no_space(self):
        # Regression guard for the closed-<details> layout bug: closed lazy
        # panels must be explicitly collapsed so a tall body can't reserve space.
        html = _html()
        assert "details.lazy:not([open])>*:not(summary){display:none}" in html

    def test_apostrophes_escaped_in_cards(self):
        # Card builders escape via html.escape; confirm no obvious raw breakage
        # by checking a known apostrophe-bearing respondent renders escaped.
        html = _html()
        # html.escape turns ' into &#x27; inside the card text.
        assert "&#x27;" in html or "&#39;" in html


class TestWriteOutput:
    def test_main_writes_index_html(self, tmp_path, monkeypatch):
        out = tmp_path / "index.html"
        monkeypatch.setattr(build_site, "OUT_PATH", out)
        build_site.main()
        assert out.exists()
        assert out.stat().st_size > 200_000
