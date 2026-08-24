"""Tests for build_site.py — the static-site generator that replaced stlite.

These lock in the contract that made the redesign worth doing: the deployed
page must be plain static HTML (no Pyodide/WASM runtime), must embed every
record so it loads without extra fetches, and must keep visual/behavioral
parity with the Streamlit app (same cards, same filter counts, same SRI-pinned
chart lib).
"""

from __future__ import annotations

import json
import re

import build_site
import dashboard
from refdata import graph


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

    def test_content_tabs_present(self):
        html = _html()
        for tab in ("legislation", "states", "cwa", "news", "solutions", "sources"):
            assert f'data-tab="{tab}"' in html
        for pid in (
            "panel-legislation",
            "panel-states",
            "panel-cwa",
            "panel-news",
            "panel-solutions",
            "panel-sources",
        ):
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
        # Boundary-aware: conflict cards carry `class="bill-card dc-site"` so
        # the filter JS can select them, so an exact-attribute match drops all
        # 18 — but a bare prefix match also catches .bill-card-head and
        # friends. Require the class name to end at a quote or a space.
        assert len(re.findall(r'class="bill-card[" ]', html)) == (
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
        # ...with every theory row from BOTH tables reaching the page. The
        # doctrine table is a sibling, not a replacement: the CWA panel became
        # a minority view once the registry grew past five federal statutes.
        assert html.count('class="theory-rank"') == len(
            dashboard.CWA_APPLICATION_THEORIES
        ) + len(dashboard.DOCTRINE_APPLICATION_THEORIES)
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
        # Boundary-aware: conflict cards carry `class="bill-card dc-site"` so
        # the filter JS can select them, so an exact-attribute match drops all
        # 18 — but a bare prefix match also catches .bill-card-head and
        # friends. Require the class name to end at a quote or a space.
        assert len(re.findall(r'class="bill-card[" ]', html)) == (
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


class TestConflictIssueFilter:
    """Part 4's issue-type filter — the thing that makes the A1 taxonomy usable
    rather than merely visible."""

    def test_filter_controls_and_hooks_present(self):
        html = _html()
        sites = dashboard.load_dc_water_conflicts().get("sites", [])
        used = {t for s in sites for t in s["issue_types"]}
        # One checkbox per issue type actually in use, plus the count line and
        # the handler that drives them.
        assert len(re.findall(r'class="dc-issue"', html)) == len(used)
        assert 'id="conflict-count"' in html
        assert "applyIssueFilter" in html

    def test_every_site_is_reachable_through_some_filter(self):
        """A site whose tags are all absent from the control row can never be
        shown once the user touches the filter."""
        html = _html()
        offered = set(re.findall(r'class="dc-issue" value="([^"]+)"', html))
        for site in dashboard.load_dc_water_conflicts().get("sites", []):
            assert set(site["issue_types"]) & offered, site["site_id"]


class TestInstrumentFilter:
    """Spec B1's filter — makes the instrument_type data usable, not just visible."""

    def test_controls_and_hooks_present(self):
        html = _html()
        bills = dashboard.load_legislation().get("bills", [])
        used = {b.get("instrument_type", "bill") for b in bills}
        assert len(re.findall(r'class="leg-instrument"', html)) == len(used)
        # Every card carries the attribute the filter reads.
        assert len(re.findall(r"data-instrument=", html)) == len(bills)

    def test_every_instrument_type_in_use_is_offered(self):
        html = _html()
        offered = set(re.findall(r'class="leg-instrument" value="([^"]+)"', html))
        for bill in dashboard.load_legislation().get("bills", []):
            assert bill.get("instrument_type", "bill") in offered, bill["bill_id"]

    def test_count_line_says_instruments_not_bills(self):
        """15 of 67 entries are not bills; the old copy contradicted the data
        model B1 introduced."""
        html = _html()
        assert "' instruments'" in html or " instruments'" in html


class TestIssuesAndClaimsTab:
    """Spec A3 — one surface for 'what is the problem, and what do they say?'"""

    def test_tab_exists_with_both_halves(self):
        html = _html()
        assert 'data-tab="issues"' in html
        assert 'id="panel-issues"' in html
        panel = html[html.index('id="panel-issues"'):html.index('id="panel-news"')]
        sites = dashboard.load_dc_water_conflicts().get("sites", [])
        claims = dashboard.load_company_water_claims().get("claims", [])
        assert panel.count("dc-site") == len(sites)
        assert panel.count('class="claim-card"') == len(claims)

    def test_old_homes_no_longer_carry_the_moved_content(self):
        """A half-completed move leaves the content in two places, which is
        worse than either home alone."""
        html = _html()
        leg = html[html.index('id="panel-legislation"'):html.index('id="panel-cwa"')]
        cwa = html[html.index('id="panel-cwa"'):html.index('id="panel-issues"')]
        assert 'class="claim-card"' not in leg
        assert "dc-site" not in cwa
        assert "cwa-p4" not in html

    def test_says_vs_does_join_renders(self):
        """The product's sharpest feature: an operator's own pledge shown on
        the card describing what its campus is accused of."""
        html = _html()
        assert html.count('class="says-vs-does"') >= 8
        newton = html[html.index('id="site-meta-newton-county-ga"'):]
        newton = newton[: newton.index("</details>")]
        assert "says-vs-does" in newton
        assert "restoring more water than we consume" in newton

    def test_issue_summary_strip_present(self):
        html = _html()
        assert 'class="issue-summary"' in html
        assert "kinds of water problem" in html


class TestNoDanglingAnchors:
    """Closes a whole class of bug in one assertion.

    refdata.integrity proves a cross-reference id resolves *in the registry*;
    it never proves the generated page contains the anchor. A shipped
    `href="#solution-wue-reporting"` pointed at nothing, because the registry
    advertised `solution-*` anchors that no builder emitted — and the JS
    handler bails before preventDefault, so the click did nothing at all.
    """

    def test_every_internal_href_has_a_matching_id(self):
        html = _html()
        ids = set(re.findall(r'\bid="([^"]+)"', html))
        hrefs = {
            h for h in re.findall(r'href="#([^"]+)"', html) if h and h != "top"
        }
        dangling = sorted(hrefs - ids)
        assert not dangling, f"hrefs pointing at no element: {dangling}"

    def test_registry_anchor_kinds_are_all_emitted(self):
        """Every record kind the registry can hand out an anchor for must
        actually appear as an id on the page."""
        from refdata.registry import build_registry

        html = _html()
        ids = set(re.findall(r'\bid="([^"]+)"', html))
        by_kind: dict[str, list] = {}
        for ref in build_registry().values():
            by_kind.setdefault(ref.kind, []).append(ref.anchor)
        for kind, anchors in by_kind.items():
            present = sum(1 for a in anchors if a in ids)
            assert present, f"no {kind} anchor reaches the page (of {len(anchors)})"


class TestExploreTab:
    """Spec B — the graph and the similarity search reach the page intact."""

    def test_tab_button_and_panel_present(self):
        html = _html()
        assert 'data-tab="explore"' in html
        assert 'id="panel-explore"' in html
        assert ">Explore</button>" in html
        assert 'id="explore"' in html

    def test_graph_blob_is_embedded_and_parses(self):
        html = _html()
        match = re.search(
            r'<script type="application/json" id="graph-data">(.*?)</script>', html, re.S
        )
        assert match, "graph-data blob missing from the page"
        # The builder escapes "</" so a record quoting </script> cannot end the
        # element early; JSON.parse and json.loads both read \/ as /.
        data = json.loads(match.group(1))
        assert len(data["nodes"]) == len(graph.build_graph()["nodes"])
        assert len(data["edges"]) == len(graph.build_graph()["edges"])
        assert data["docs"] and data["vocab"] and data["df"]

    def test_blob_appears_exactly_once(self):
        """Two copies would double the page weight and give the JS an ambiguous
        `#graph-data` to read."""
        assert _html().count('id="graph-data"') == 1

    def test_tokenizer_parity_is_by_construction(self):
        """The JS tokenizer must not restate the Python rules — it reads the
        stopword list and the length floor out of the blob, and its splitting
        regex is the same pattern. A transcribed copy is the failure mode this
        blocks: it looks right and silently ranks differently."""
        js = dashboard._explore_js()
        assert "D.stopwords" in js and "D.min_token_len" in js
        # No literal stopword array anywhere in the script.
        assert not re.search(r"\[\s*'(?:the|and|of)'", js)
        assert f"/{graph._TOKEN_SPLIT_RE.pattern}/g" in js
        assert ".toLowerCase()" in js
        blob = json.loads(
            re.search(
                r'<script type="application/json" id="graph-data">(.*?)</script>',
                _html(),
                re.S,
            ).group(1)
        )
        assert blob["stopwords"] == sorted(graph.STOPWORDS)
        assert blob["min_token_len"] == graph.MIN_TOKEN_LEN

    def test_tokenizer_fixture_round_trip(self):
        """The Python half of the parity contract, pinned to a literal so a
        change to the splitting rules has to be deliberate."""
        fixture = "Fort Worth's §404 permit — PFAS/PFOA in the reservoir!"
        assert graph.tokenize(fixture) == [
            "fort",
            "worth",
            "404",
            "permit",
            "pfas",
            "pfoa",
            "reservoir",
            "fort worth",
            "worth 404",
            "404 permit",
            "permit pfas",
            "pfas pfoa",
            "pfoa reservoir",
        ]

    def test_controls_present(self):
        html = _html()
        assert 'id="explore-q"' in html          # paste-text box
        assert 'id="explore-family"' in html     # statute-family select
        assert 'id="explore-depth"' in html      # 1-2 hop toggle
        assert 'id="explore-scope"' in html      # restrict to neighbourhood
        assert 'id="explore-canvas"' in html
        assert 'id="explore-results"' in html
        # One kind checkbox per record kind that actually has records.
        kinds = {n["kind"] for n in graph.build_graph()["nodes"] if n["kind"] != "hub"}
        assert len(re.findall(r'class="explore-kind"', html)) == len(kinds)
        for kind in kinds:
            assert f'class="explore-kind" value="{kind}"' in html

    def test_edge_kind_toggles_cover_every_kind(self):
        """The checkboxes are built in JS from the blob, so what has to be
        present is a label for every kind the graph emits."""
        blob = json.loads(
            re.search(
                r'<script type="application/json" id="graph-data">(.*?)</script>',
                _html(),
                re.S,
            ).group(1)
        )
        assert len(blob["edge_kinds"]) == len(blob["edge_kind_labels"])
        assert set(blob["derived_edge_kinds"]) == set(graph.DERIVED_EDGE_KINDS)
        assert set(blob["derived_edge_kinds"]) <= set(blob["edge_kinds"])
        for label in blob["edge_kind_labels"]:
            assert label in graph.EDGE_KIND_LABELS.values()

    def test_results_link_to_registry_anchors(self):
        """A result row's link is the node's `anchor` field; if the builder
        stopped shipping anchors the links would silently become dead text."""
        blob = json.loads(
            re.search(
                r'<script type="application/json" id="graph-data">(.*?)</script>',
                _html(),
                re.S,
            ).group(1)
        )
        ids = set(re.findall(r'\bid="([^"]+)"', _html()))
        for node in blob["nodes"]:
            if node["kind"] == "hub" and not node["anchor"]:
                continue
            assert node["anchor"] in ids, node["id"]

    def test_empty_state_names_the_three_questions(self):
        html = _html()
        assert dashboard.EXPLORE_EMPTY_STATE in html
        for phrase in ("same language", "connects to", "narrowing results"):
            assert phrase in dashboard.EXPLORE_EMPTY_STATE

    def test_reduced_motion_is_honored(self):
        assert "prefers-reduced-motion" in dashboard._explore_js()

    def test_no_third_party_assets(self):
        """Standing security rule: the only CDN asset on this page is the
        SRI-pinned Chart.js. The graph must stay hand-rolled, so the fragment
        must not load anything. Curated record text can legitimately contain a
        url, so the data blob is excluded before looking."""
        fragment = re.sub(
            r'<script type="application/json".*?</script>',
            "",
            dashboard._build_explore_html(),
            flags=re.S,
        )
        assert "http://" not in fragment
        assert "https://" not in fragment
        assert "<script src" not in fragment
        assert "<link" not in fragment

    def test_progressive_enhancement_block(self):
        html = _html()
        assert 'class="explore-noscript"' in html
        assert "need JavaScript" in html
        # Without JS the tab buttons are inert, so every panel is unhidden
        # instead of five of seven being unreachable.
        assert "<noscript><style>.tabpanel[hidden]{display:block}</style></noscript>" in html

    def test_streamlit_and_static_share_one_fragment(self):
        """Two surfaces, one implementation — the whole reason the builder
        lives in dashboard.py rather than in build_site.py."""
        assert dashboard._build_explore_html() in build_site.build_explore_tab()

    def test_llms_txt_notes_the_tab(self):
        txt = build_site.build_llms_txt()
        assert "## Explore tab (connection graph + text search)" in txt
        # The index itself must not be dumped in there.
        assert "vocab" not in txt
        assert len(txt) < 400_000


class TestInfrastructureVisuals:
    """Spec E — the water-infrastructure visual language on the deployed page.

    The load-bearing piece is the header schematic: it is the only art on the
    page that carries information, and what it explains is the project's own
    architecture — the sewer leg is the metered one, which is why the pipeline
    reads EPA ECHO DMR data from receiving WWTPs. Losing a label or an
    annotation would quietly turn it back into decoration.
    """

    def test_schematic_present_with_every_station_label(self):
        html = _html()
        assert 'class="schematic"' in html
        for label in (
            "river / wellfield",
            "treatment plant",
            "data center hall",
            "closed chiller loop",
            "cooling tower",
            "wastewater plant",
            "treated effluent returns to the river",
        ):
            assert f">{label}</text>" in html, f"schematic label missing: {label}"
        # The arrow in this one is a numeric entity, so match around it.
        assert "blowdown &#8594; sewer" in html

    def test_schematic_carries_the_two_facts_it_exists_for(self):
        html = _html()
        assert "evaporation is the consumptive loss" in html
        assert "this water leaves the basin, not the sewer" in html
        assert "the sewer leg is metered on the receiving plant" in html
        assert "NPDES permit" in html
        assert "that is where the data shows up" in html

    def test_streamlit_and_static_share_one_schematic(self):
        """Same contract as the Explore fragment: one builder, two surfaces."""
        assert dashboard._build_water_loop_svg() in build_site.build_html()

    def test_schematic_is_labelled_for_screen_readers(self):
        svg = dashboard._build_water_loop_svg()
        assert 'role="img"' in svg
        assert 'aria-labelledby="wl-title wl-desc"' in svg
        assert 'id="wl-title"' in svg and 'id="wl-desc"' in svg

    def test_body_carries_the_inline_texture_and_print_drops_it(self):
        html = _html()
        body = re.search(r"\nbody\{(.*?)\n\}", html, re.S)
        assert body, "no body rule in the page CSS"
        rule = body.group(1)
        assert "url(\"data:image/svg+xml" in rule, "texture is not an inline data: URI"
        assert "background-attachment:fixed" in rule
        # Texture strokes/fills stay at texture strength (DESIGN.md §1).
        opacities = [float(v) for v in re.findall(r"opacity='([0-9.]+)'", rule)]
        assert opacities and max(opacities) <= 0.12, opacities
        # ...and no printer has to render any of it.
        assert "@media print{" in html
        assert "body{background-image:none" in html

    def test_one_animation_only_and_it_switches_itself_off(self):
        """DESIGN.md §12: the schematic's flow line is the only thing that
        moves. A second @keyframes block is the regression this catches."""
        html = _html()
        assert html.count("@keyframes") == 1
        assert "@keyframes wl-drift" in html
        svg = dashboard._build_water_loop_svg()
        assert "animation:" in svg
        assert "@media (prefers-reduced-motion:reduce)" in svg
        # The moving dashes stay under the ornament ceiling.
        assert 'class="wl-flow"' in svg and 'stroke-opacity="0.35"' in svg

    def test_active_tab_underline_is_a_pipe_with_end_fittings(self):
        html = _html()
        assert '.tab[aria-selected="true"]::after' in html
        assert '.tab[aria-selected="true"]::before' in html
        assert "height:2px;border-radius:999px;background:var(--blue)" in html
        assert html.count("radial-gradient(circle at 3px 3px,var(--blue)") == 1

    def test_section_headers_carry_a_pipe_fitting(self):
        html = _html()
        # Defined once, in assets/components.css, so both surfaces get it; the
        # element scope keeps it off the <span> variant that has no border.
        assert "h3.solution-cat-header::before" in html
        assert "h4.solution-cat-header::before" in html
        assert html.count("h4.solution-cat-header::before") == 1

    def test_footer_motif_is_ornament_strength_and_silent(self):
        html = _html()
        assert 'class="footer-motif"' in html
        motif = html[html.index('<svg class="footer-motif"'):]
        motif = motif[: motif.index("</svg>")]
        assert 'aria-hidden="true"' in motif
        assert "<text" not in motif, "the motif is ornament; it carries no labels"
        opacity = re.search(r"\.footer-motif\{[^}]*opacity:\.(\d+)\}", html)
        assert opacity and int(opacity.group(1)) <= 12

    def test_page_stays_under_the_weight_ceiling(self):
        """Every record is embedded, so the page is ~2.1 MB by design (the
        Explore graph blob is ~635 KB of it). This is a tripwire for an
        accidental order-of-magnitude regression — a second copy of the blob,
        an embedded raster, a duplicated tab — not a diet.

        Raised twice on 2026-08-24: 1.85 MB → 2 MB for the eight federal
        statute families, then 2 MB → 2.25 MB for the States & Localities tab
        (~135 KB: an 89-row county/city table, 41 state cards, the what's-new
        list) plus ~115 KB the news, claims and instrument additions added to
        the Explore blob. The county/city records stay out of the registry, so
        they cost table markup only and nothing in the graph. The ~140 KB of
        headroom left is still far more than any single visual addition."""
        assert len(_html().encode("utf-8")) < 2_250_000


class TestNoDuplicateClaimStyles:
    def test_lifecycle_classes_defined_once(self):
        """They were defined in build_site.py's CSS block AND (after the move)
        in assets/components.css, so the built page carried two competing
        definitions — the drift the move existed to end."""
        html = _html()
        for cls in (".claim-type-pill", ".claim-challenge-pill", ".claim-chips"):
            assert html.count(cls + "{") + html.count(cls + " {") == 1, cls


class TestStatesTab:
    """Spec D — the States & Localities tab on the static surface."""

    from datetime import datetime as _dt

    TODAY = _dt(2026, 8, 24)

    def test_tab_button_sits_between_legislation_and_water_cases(self):
        html = _html()
        order = [
            html.index('data-tab="legislation"'),
            html.index('data-tab="states"'),
            html.index('data-tab="cwa"'),
        ]
        assert order == sorted(order)
        assert ">States &amp; Localities</button>" in html

    def test_every_active_state_gets_a_card(self):
        tab = build_site.build_states_tab(self.TODAY)
        rollup = dashboard._state_rollup(
            dashboard.load_legislation()["bills"],
            dashboard.load_local_actions()["actions"],
            self.TODAY,
        )
        assert tab.count('class="state-card"') == len(rollup)
        assert ">Virginia<" in tab and ">Texas<" in tab

    def test_every_local_action_gets_a_row(self):
        tab = build_site.build_states_tab(self.TODAY)
        actions = dashboard.load_local_actions()["actions"]
        assert tab.count("<tr data-action-id=") == len(actions)
        assert f"window.LA_TOTAL = {len(actions)}" in tab

    def test_whats_new_renders_and_respects_the_frozen_date(self):
        """The window is computed from the argument, not the clock. Build the
        same tab a year later and the same records fall out of it."""
        now = build_site.build_states_tab(self.TODAY)
        assert 'class="whatsnew-row"' in now
        assert "movements</strong> in the last 120 days" in now

        later = build_site.build_states_tab(self._dt(2027, 12, 31))
        assert "Nothing tracked moved in the last 120 days" in later
        assert 'class="whatsnew-row"' not in later

    def test_filters_cover_state_status_type_and_water(self):
        tab = build_site.build_states_tab(self.TODAY)
        assert 'id="la-state"' in tab and 'id="la-water" checked' in tab
        for status in dashboard.LOCAL_ACTION_STATUS_LABELS:
            assert f'class="la-status" value="{status}" checked' in tab
        for kind in dashboard.LOCAL_ACTION_TYPE_LABELS:
            assert f'class="la-type" value="{kind}" checked' in tab
        # Every state in the data is selectable.
        for code in {a["state"] for a in dashboard.load_local_actions()["actions"]}:
            assert f'<option value="{code}">' in tab

    def test_filter_js_is_wired(self):
        js = build_site.build_js()
        assert "applyLocalActionFilter" in js
        assert "local-actions-table" in js

    def test_streamlit_and_static_share_the_builders(self):
        """Both surfaces call the same dashboard builders — the parity rule
        that keeps a change to one card from skipping the other."""
        tab = build_site.build_states_tab(self.TODAY)
        bills = dashboard.load_legislation()["bills"]
        actions = dashboard.load_local_actions()["actions"]
        rollup = dashboard._state_rollup(bills, actions, self.TODAY)
        assert dashboard._build_state_rollup_html(rollup) in tab
        assert dashboard._build_local_actions_table_html(actions) in tab

    def test_tab_follows_the_standard_anatomy(self):
        """DESIGN.md §5: title, one-liner, summary panel, filters, count line,
        content, last-updated caption."""
        tab = build_site.build_states_tab(self.TODAY)
        assert "<h2>States &amp; Localities</h2>" in tab
        assert 'class="lead"' in tab
        assert tab.count('class="metric-label"') == 3
        assert 'class="count-line" id="la-count"' in tab
        assert "Dataset last updated" in tab
        assert tab.count("<h2>") == 1, "one tab title only"

    def test_rollup_says_it_is_activity_based(self):
        """A per-state view invites 'my state is missing, so nothing is
        happening'. The tab has to say otherwise."""
        tab = build_site.build_states_tab(self.TODAY)
        assert "Activity-based, not exhaustive" in tab

    def test_llms_txt_carries_the_tab_and_what_is_new(self):
        txt = build_site.build_llms_txt()
        assert "## States and localities" in txt
        assert "Moved in the last 120 days" in txt
        assert "local_actions.json" in txt
        actions = dashboard.load_local_actions()["actions"]
        assert f"{len(actions)} county, city and town" in txt
