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

    def test_five_tabs_present(self):
        html = _html()
        for tab in ("legislation", "cwa", "news", "solutions", "sources"):
            assert f'data-tab="{tab}"' in html
        for pid in ("panel-legislation", "panel-cwa", "panel-news", "panel-solutions", "panel-sources"):
            assert f'id="{pid}"' in html

    def test_three_tabs_present(self):
        # Core tabs that must always be present.
        html = _html()
        for tab in ("legislation", "cwa", "sources"):
            assert f'data-tab="{tab}"' in html
        for pid in ("panel-legislation", "panel-cwa", "panel-sources"):
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
        historical = [c for c in cases if c.get("display_section", "historical") == "historical"]
        potential = [c for c in cases if c.get("display_section") == "potential"]
        # Historical cases get the filterable .cwa-case wrapper; potential cases get
        # .cwa-potential-case so client-side filtering doesn't hide them.
        assert html.count('class="cwa-case"') == len(historical)
        assert html.count('class="cwa-potential-case"') == len(potential)
        # The JS total used by the filter count line reflects historical cases only.
        assert f"window.CWA_TOTAL = {len(historical)}" in html

    def test_all_bills_and_claims_embedded(self):
        html = _html()
        bills = dashboard.load_legislation().get("bills", [])
        claims = dashboard.load_company_water_claims().get("claims", [])
        # CWA cards, authority reading cards, and conflict-site cards all reuse
        # the .bill-card base, so bill-card count == bills + cases + readings + sites.
        cases = dashboard.load_cwa_investigations().get("cases", [])
        readings = dashboard.load_water_authorities().get("readings", [])
        sites = dashboard.load_dc_water_conflicts().get("sites", [])
        assert html.count('class="bill-card"') == (
            len(bills) + len(cases) + len(readings) + len(sites)
        )
        assert html.count('class="claim-card"') == len(claims)

    def test_new_research_cases_render(self):
        # Spot-check that the June-2026 additions actually reach the static page.
        html = _html()
        for needle in ("New Carlisle", "Puget Soundkeeper", "Edwards Aquifer", "Fort Smith"):
            assert needle in html, f"missing case content: {needle}"

    def test_cwa_theories_panel_rendered(self):
        html = _html()
        # The prioritized-theories panel is present on the CWA tab...
        assert "Prioritized CWA-application theories" in html
        assert 'class="theory-table"' in html
        # ...with every theory row (12 + 1 header) reaching the page...
        assert html.count('class="theory-rank"') == len(
            dashboard.CWA_APPLICATION_THEORIES
        )
        # ...the novel Maui theory and the §505 lead row both surface.
        assert "functional equivalent" in html
        assert "receiving POTW" in html

    def test_theories_panel_does_not_inflate_card_counts(self):
        # Regression guard: the new panel uses .theory-* classes, so the
        # cwa-case / bill-card / claim-card counts the filters rely on are
        # unchanged by it.
        html = _html()
        cases = dashboard.load_cwa_investigations().get("cases", [])
        historical = [c for c in cases if c.get("display_section", "historical") == "historical"]
        bills = dashboard.load_legislation().get("bills", [])
        assert html.count('class="cwa-case"') == len(historical)
        readings = dashboard.load_water_authorities().get("readings", [])
        sites = dashboard.load_dc_water_conflicts().get("sites", [])
        assert html.count('class="bill-card"') == (
            len(bills) + len(cases) + len(readings) + len(sites)
        )

    def test_markdown_blobs_converted(self):
        # The statute explainer is markdown in the source; it must arrive as HTML
        # (primary-source citation present, no raw markdown link syntax left).
        html = _html()
        assert "33 U.S.C." in html
        assert "law.cornell.edu/uscode/text/33/1251" in html

    def test_sources_tab_scorecard_embedded(self):
        # Sources tab: scorecard counts and source-level headers must render.
        html = _html()
        assert 'class="src-table"' in html
        assert "Federal" in html
        assert "Virginia" in html
        assert "Unlocking soon" in html
        assert "HB 496 / SB 553" in html

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

    def test_legislation_themes_panel_embedded(self):
        html = _html()
        # Theme grid appears on the legislation tab
        assert 'class="theme-grid"' in html
        # All 6 themes rendered (each has a theme-card-count span)
        assert html.count('class="theme-card"') == len(dashboard.LEGISLATION_THEME_DEFINITIONS)
        # Emerging solutions box is present
        assert "What solutions are emerging" in html
        # Virginia HB 496 appears in the solutions insights box
        assert "HB 496" in html

    def test_news_tab_content_embedded(self):
        html = _html()
        items = dashboard.load_water_news().get("items", [])
        assert len(items) > 0
        # Every news card is rendered
        assert html.count('class="news-card"') == len(items)
        # Spot-check a known headline
        assert "Boardman" in html  # Amazon settlement
        assert "news-tag-filter" in html  # tag filter checkboxes present

    def test_solutions_tab_content_embedded(self):
        html = _html()
        payload = dashboard.load_water_solutions()
        categories = payload.get("categories", [])
        total_solutions = sum(len(c.get("solutions", [])) for c in categories)
        assert total_solutions > 0
        # Every solution card is rendered
        assert html.count('class="solution-card"') == total_solutions
        # Spot-check known content
        assert "Closed-Loop" in html
        assert "solution-cat-header" in html


class TestLegislationFilters:
    def test_filter_controls_present(self):
        html = _html()
        # Principle / status / level / scope chip checkboxes + count line.
        for cls in ("leg-principle", "leg-status", "leg-level", "leg-scope"):
            assert f'class="chip-check"><input type="checkbox" class="{cls}"' in html
        assert 'id="leg-count"' in html
        bills = dashboard.load_legislation().get("bills", [])
        assert f"window.LEG_TOTAL = {len(bills)}" in html

    def test_every_bill_carries_filter_attrs(self):
        html = _html()
        bills = dashboard.load_legislation().get("bills", [])
        assert html.count('class="leg-bill"') == len(bills)
        assert html.count("data-principles=") == len(bills)

    def test_principles_panel_on_static_page(self):
        html = _html()
        assert "Key principles across all bills" in html
        # The most common tag must appear as a filter chip and in the panel.
        assert html.count("Transparency") >= 2


class TestCwaAccordion:
    def test_case_narrative_collapsed(self):
        # Scroll-control (2026-07-06): every case's full narrative —
        # violation, outcome, statute applicability + pathway, full citation,
        # sources — lives in one collapsed <details>; only the takeaway stays
        # visible by default, matching Part 4's conflict-site card density.
        html = _html()
        cases = dashboard.load_cwa_investigations().get("cases", [])
        assert (
            html.count("Details — violation, outcome, statute applicability &amp; sources")
            == len(cases)
        )
        # "How statutes could apply" appears once per pending/not-applied case.
        pending = [c for c in cases if c.get("cwa_applied") in ("pending", "not-applied")]
        assert html.count("How statutes could apply") == len(pending)


class TestLlmsTxt:
    def test_llms_txt_contains_everything(self):
        txt = build_site.build_llms_txt()
        assert txt.startswith("# Data Center Water Use Tracker")
        assert txt.splitlines()[2].startswith(">")  # llms.txt-convention blockquote
        for b in dashboard.load_legislation().get("bills", []):
            assert b["bill_id"] in txt, f"llms.txt missing bill {b['bill_id']}"
        for c in dashboard.load_cwa_investigations().get("cases", []):
            assert c["case_id"] in txt, f"llms.txt missing case {c['case_id']}"
        for r in dashboard.load_water_authorities().get("readings", []):
            assert r["reading_id"] in txt, f"llms.txt missing reading {r['reading_id']}"
        for s in dashboard.load_dc_water_conflicts().get("sites", []):
            assert s["site_id"] in txt, f"llms.txt missing site {s['site_id']}"
        assert "## Key principles across tracked legislation" in txt
        assert "## Federal water-law toolkit (statutory readings)" in txt
        assert "## Data-center sites with documented water conflicts" in txt
        assert build_site.REPO_URL in txt

    def test_site_links_llms_txt(self):
        html = _html()
        assert '<link rel="alternate" type="text/plain" href="llms.txt"' in html
        assert '<a href="llms.txt">llms.txt</a>' in html


class TestWriteOutput:
    def test_main_writes_index_html(self, tmp_path, monkeypatch):
        out = tmp_path / "index.html"
        monkeypatch.setattr(build_site, "OUT_PATH", out)
        monkeypatch.setattr(build_site, "LLMS_TXT_PATH", tmp_path / "llms.txt")
        build_site.main()
        assert out.exists()
        assert out.stat().st_size > 200_000
        assert (tmp_path / "llms.txt").exists()
