"""Tests for build_site.py — the static-site generator that replaced stlite.

These lock in the contract that made the redesign worth doing: the deployed
page must be plain static HTML (no Pyodide/WASM runtime, and since August 2026
no third-party asset of any kind), must carry every record so the page needs no
network to be read, and must keep visual/behavioral parity with the Streamlit
app (same cards, same filter counts, same builders).

The one file the page does fetch is ``graph-data.json`` — the Explore graph and
text index — and only when a reader opens that tab.
"""

from __future__ import annotations

import json
import re

import build_site
import dashboard
from refdata import graph


def _html() -> str:
    return build_site.build_html()


def _blob() -> dict:
    """The Explore payload as the browser gets it: parsed from the file the
    page fetches, not from an element inside the page."""
    return json.loads(build_site.build_graph_data_json())


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

    def test_no_third_party_origin_at_all(self):
        """Security standing rule, strengthened 2026-08-24.

        The rule used to be "every third-party CDN asset carries an SRI hash",
        and the only such asset was a Chart.js tag with zero call sites — the
        Data tab it drew for was renamed away in June 2026. Removing it left the
        page with no third-party origin to pin, which is a stronger position
        than a correct hash. This asserts nothing loads from anywhere else:
        no external script, stylesheet, font, image, iframe or preconnect.
        Curated record text legitimately contains https:// links, so this looks
        at loading attributes rather than at the text.
        """
        html = _html()
        assert "chart.js" not in html.lower()
        assert not hasattr(build_site, "CHARTJS_URL")
        assert not hasattr(build_site, "CHARTJS_SRI")
        for attr in ("<script src", "<iframe", "<embed", "<object"):
            assert attr not in html.lower(), f"external resource tag: {attr}"
        # Every <link> and <img> must be same-origin/relative, and no
        # stylesheet may pull one in.
        for url in re.findall(r'<(?:link|img)\b[^>]*?(?:href|src)="([^"]+)"', html):
            assert not url.startswith(("http:", "https:", "//")), url
        for url in re.findall(r"@import\s+(?:url\()?[\"']([^\"']+)", html):
            assert not url.startswith(("http:", "https:", "//")), url
        # CSS url() references are all inline data: URIs (the water texture,
        # the h1 wave). A remote one would be an uncovered third-party fetch.
        for url in re.findall(r"url\(\"?'?([^\"')]+)", html):
            assert not url.startswith(("http:", "https:", "//")), url

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
    def test_main_writes_all_three_outputs(self, tmp_path, monkeypatch):
        out = tmp_path / "index.html"
        monkeypatch.setattr(build_site, "OUT_PATH", out)
        monkeypatch.setattr(build_site, "GRAPH_DATA_PATH", tmp_path / "graph-data.json")
        monkeypatch.setattr(build_site, "LLMS_TXT_PATH", tmp_path / "llms.txt")
        build_site.main()
        assert out.exists()
        assert out.stat().st_size > 200_000
        assert (tmp_path / "llms.txt").exists()
        blob = tmp_path / "graph-data.json"
        assert blob.exists() and blob.stat().st_size > 100_000
        assert json.loads(blob.read_text())["nodes"]

    def test_pages_workflow_deploys_everything_the_build_writes(self):
        """The page references graph-data.json and llms.txt by relative URL.
        A deploy step that copies index.html alone 404s both — which is exactly
        what it did until 2026-08-24, silently breaking the llms.txt link."""
        from pathlib import Path

        wf = (Path(build_site.__file__).parent / ".github/workflows/pages.yml").read_text()
        assert "cp pages/*.* _site/" in wf
        for name in ("index.html", "graph-data.json", "llms.txt"):
            assert name in wf, f"deploy does not mention {name}"


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

    def test_graph_blob_is_a_separate_file_that_parses(self):
        data = _blob()
        assert len(data["nodes"]) == len(graph.build_graph()["nodes"])
        assert len(data["edges"]) == len(graph.build_graph()["edges"])
        assert data["docs"] and data["vocab"] and data["df"]

    def test_blob_is_not_inline_in_the_page(self):
        """It was ~620 KB of a ~2.1 MB page and only one of eight tabs reads
        it. The element stays (it is what carries the URL); its body must not."""
        html = _html()
        assert html.count('id="graph-data"') == 1
        match = re.search(
            r'<script type="application/json" id="graph-data"([^>]*)>(.*?)</script>',
            html,
            re.S,
        )
        assert match, "graph-data element missing from the page"
        assert f'data-src="{build_site.GRAPH_DATA_URL}"' in match.group(1)
        assert match.group(2).strip() == "", "graph blob is still inline"

    def test_page_fetches_the_blob_on_first_explore_activation(self):
        html = _html()
        js = build_site.build_js()
        # The tab handler kicks the loader, and the loader is what fetches.
        assert "window.exploreInit" in js
        assert "if (name === 'explore' && window.exploreInit) window.exploreInit();" in js
        assert "window.exploreInit = init;" in dashboard._explore_js()
        assert "fetch(src)" in html
        # A loading state and a plain failure message, not a silent blank canvas.
        assert "Loading the connection graph" in html
        assert "The connection graph could not be loaded" in html

    def test_streamlit_still_gets_the_blob_inline(self):
        """Inside a components.html iframe there is no origin to fetch from, so
        the Streamlit fragment keeps the payload in the element."""
        fragment = dashboard._build_explore_html()
        match = re.search(
            r'<script type="application/json" id="graph-data"[^>]*>(.*?)</script>',
            fragment,
            re.S,
        )
        assert match and len(match.group(1)) > 100_000
        assert "data-src" not in match.group(0)
        assert json.loads(match.group(1))["nodes"]

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
        blob = _blob()
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
        blob = _blob()
        assert len(blob["edge_kinds"]) == len(blob["edge_kind_labels"])
        assert set(blob["derived_edge_kinds"]) == set(graph.DERIVED_EDGE_KINDS)
        assert set(blob["derived_edge_kinds"]) <= set(blob["edge_kinds"])
        for label in blob["edge_kind_labels"]:
            assert label in graph.EDGE_KIND_LABELS.values()

    def test_results_link_to_registry_anchors(self):
        """A result row's link is the node's `anchor` field; if the builder
        stopped shipping anchors the links would silently become dead text."""
        blob = _blob()
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
        """Standing security rule: this page loads nothing from a third party.
        The graph must stay hand-rolled, so the fragment must not load anything
        either — the one thing it fetches is its own same-origin blob. Curated
        record text can legitimately contain a url, so the data blob is
        excluded before looking."""
        for fragment in (
            dashboard._build_explore_html(),
            dashboard._build_explore_html(build_site.GRAPH_DATA_URL),
        ):
            fragment = re.sub(
                r'<script type="application/json".*?</script>', "", fragment, flags=re.S
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
        lives in dashboard.py rather than in build_site.py. They differ only in
        where the payload comes from, which is the builder's one argument."""
        assert (
            dashboard._build_explore_html(build_site.GRAPH_DATA_URL)
            in build_site.build_explore_tab()
        )

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
        """Every record is in the markup, so the page is ~1.45 MB by design.
        This is a tripwire for an accidental order-of-magnitude regression — a
        second copy of a dataset, an embedded raster, a duplicated tab — not a
        diet.

        Raised twice earlier on 2026-08-24 (1.85 → 2 → 2.25 MB) as the statute
        families and the States & Localities tab landed, then **lowered to
        1.6 MB** the same day when the ~620 KB Explore graph blob moved out to
        pages/graph-data.json: the page went 2.11 MB → 1.46 MB. The ceiling
        tracks the page, so re-inlining the blob has to fail here rather than
        quietly costing every reader 620 KB again."""
        assert len(_html().encode("utf-8")) < 1_600_000


class TestNavigationAndScrollControl:
    """The 2026-08-24 UX pass: a sticky tab strip, anchors that clear it, a
    back-to-top control, and collapse structures on the long tabs."""

    def test_tab_strip_is_sticky_and_outlined(self):
        html = _html()
        # Sticky, at the top, above the cards.
        assert ".tabs-bar{position:sticky;top:0;z-index:30" in html
        assert "border-bottom:2px solid #d6e2ee" in html
        # One non-wrapping scrollable row, not four wrapped ones.
        assert "flex-wrap:nowrap;overflow-x:auto" in html
        assert "scroll-snap-type:x proximity" in html
        # Every tab carries its own outline (DESIGN.md §8's outline chip).
        assert "border:1px solid #bdd7e7;background:#fff;border-radius:999px" in html
        # The buttons live inside the sticky wrapper.
        assert '<div class="tabs-bar">' in html
        assert html.index('<div class="tabs-bar">') < html.index('data-tab="legislation"')

    def test_every_anchor_target_clears_the_sticky_bar(self):
        """Without this a cross-tab deep link lands under the nav — the exact
        regression a sticky bar introduces."""
        html = _html()
        assert "--navh:54px" in html
        assert "[id]{scroll-margin-top:calc(var(--navh) + .6rem)}" in html
        # ...and the phone bar is shorter, so the reserve tracks it.
        assert ":root{--navh:50px}" in html

    def test_back_to_top_button(self):
        html = _html()
        assert 'id="to-top"' in html
        assert 'aria-label="Back to top"' in html
        # Appears after two viewport heights and honours reduced motion.
        assert "window.scrollY > window.innerHeight * 2" in build_site.build_js()
        assert "prefers-reduced-motion" in build_site.build_js()
        # No emoji in the control (DESIGN.md §12) — it draws a caret.
        button = html[html.index('<button type="button" class="to-top"'):]
        button = button[: button.index("</button>")]
        assert "<svg" in button
        assert button.isascii()

    def test_long_lists_are_grouped_or_folded(self):
        html = _html()
        bills = dashboard.load_legislation().get("bills", [])
        cases = dashboard.load_cwa_investigations().get("cases", [])
        historical = [c for c in cases if c.get("display_section", "historical") == "historical"]
        # Legislation: one group per status in use, only "enacted" open.
        statuses = {b.get("status") for b in bills}
        for status in statuses:
            assert f'data-group="{status}"' in html
            collapsed = f'data-group="{status}" data-collapsed="1"' in html
            assert collapsed == (status != "enacted"), status
        # Water Cases Part 2: one group per case group, the two data-center
        # ones open and the 83 analog/precedent cards behind a summary.
        for cat in {c.get("category") for c in historical}:
            assert f'data-group="{cat}"' in html
            collapsed = f'data-group="{cat}" data-collapsed="1"' in html
            assert collapsed == (cat not in ("datacenter", "adjacent")), cat
        # Folds where there is no grouping axis worth inventing.
        assert 'id="news-fold"' in html
        assert 'id="sites-fold"' in html
        assert "older headlines" in html
        assert "Show water claims from the other" in html

    def test_grouping_does_not_drop_or_duplicate_a_card(self):
        """The whole risk of splitting a list: a card that lands in no group,
        or in two."""
        html = _html()
        bills = dashboard.load_legislation().get("bills", [])
        cases = dashboard.load_cwa_investigations().get("cases", [])
        historical = [c for c in cases if c.get("display_section", "historical") == "historical"]
        assert html.count('class="leg-bill"') == len(bills)
        assert html.count('class="cwa-case"') == len(historical)

    def test_collapsed_groups_are_open_without_javascript(self):
        """Progressive enhancement, and the reason the markup looks inverted:
        <details> ships open, CSS hides the body once the head script has
        stamped html.js, and the load script closes it for real. Emitting them
        closed would hide ~150 cards from a reader with scripting off, and no
        CSS can force a closed <details> open."""
        html = _html()
        assert "<script>document.documentElement.classList.add('js')</script>" in html
        assert ".js details[data-collapsed]>*:not(summary){display:none}" in html
        assert "d.removeAttribute('data-collapsed');" in build_site.build_js()
        # Never emitted closed.
        assert 'class="card-group"' in html
        assert not re.search(r'<details class="card-(group|fold)"(?![^>]*\bopen\b)', html)

    def test_filters_keep_the_groups_honest(self):
        """A filter that empties a group must hide it, and one narrow enough to
        fit on a screen must open what is left — otherwise narrowing to a
        status leaves every match behind a closed summary."""
        js = build_site.build_js()
        assert "function syncCardGroups(" in js
        assert "syncCardGroups('#leg-bills .card-group', '.leg-bill')" in js
        assert "syncCardGroups('#cwa-cases .card-group', '.cwa-case')" in js
        assert "g.el.hidden = g.n === 0" in js
        assert "GROUP_AUTO_OPEN_MAX" in js
        # The two folds open themselves when their filter narrows.
        assert "if (sitesFold && picked.size < issueChecks.length) sitesFold.open = true;" in js
        assert "if (newsFold && active.size < newsBoxes.length) newsFold.open = true;" in js

    def test_per_tab_jump_rows(self):
        html = _html()
        assert html.count('class="jumpnav"') >= 3
        for anchor in ("states-whatsnew", "states-rollup", "states-local",
                       "issues-sites", "issues-claims"):
            assert f'id="{anchor}"' in html
            assert f'href="#{anchor}"' in html

    def test_offscreen_cards_are_skipped(self):
        """~10,700 elements; content-visibility:auto keeps the ones outside the
        viewport out of layout and paint. contain-intrinsic-size gives the
        scrollbar something honest to work with in the meantime."""
        html = _html()
        assert (
            ".leg-bill,.cwa-case,.cwa-potential-case"
            "{content-visibility:auto;contain-intrinsic-size:auto 260px}" in html
        )
        for sel in ("#news-cards .news-card", ".claim-card", "#dc-conflicts .dc-site"):
            assert f"{sel}{{content-visibility:auto" in html
        # Print has to render all of them.
        assert "content-visibility:visible" in html


class TestTagline:
    """One sentence, one definition, four surfaces."""

    def test_tagline_is_current_and_shared(self):
        html = _html()
        assert "Virginia &amp; Ohio via public regulatory data" not in html
        assert "draw, discharge, and disclose cooling water" in dashboard.TAGLINE
        assert f'<meta name="description" content="{dashboard.TAGLINE}">' in html
        assert f'<p class="tagline">{dashboard.TAGLINE}</p>' in html

    def test_llms_txt_blockquote_matches(self):
        txt = build_site.build_llms_txt()
        assert txt.splitlines()[2].startswith(f"> {dashboard.TAGLINE}")
        assert "Virginia & Ohio via public regulatory data" not in txt


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
        assert dashboard._build_state_rollup_html(rollup, fold_after=12) in tab
        assert dashboard._build_local_actions_table_html(actions) in tab

    def test_rollup_folds_after_twelve_states(self):
        """41 stacked cards is most of the tab's scroll depth on a phone, and
        the sort order already puts the states that moved most recently first."""
        rollup = dashboard._state_rollup(
            dashboard.load_legislation()["bills"],
            dashboard.load_local_actions()["actions"],
            self.TODAY,
        )
        folded = dashboard._build_state_rollup_html(rollup, fold_after=12)
        assert folded.count('class="state-card"') == len(rollup)
        assert f"Show the remaining {len(rollup) - 12} states" in folded
        # Ships open so a reader with no JavaScript sees the whole roll-up.
        assert '<details class="card-fold" data-collapsed="1" open>' in folded
        # Under the fold threshold there is no fold at all.
        assert "card-fold" not in dashboard._build_state_rollup_html(rollup[:5], fold_after=12)

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
