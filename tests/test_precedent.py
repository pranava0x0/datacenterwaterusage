"""Check-a-project engine: facets on the record, the parser, the matcher, the payload.

The engine's whole promise is that its answer is explainable by facets in
common, so these tests pin (1) that every record carries facets from the
closed vocabulary and every facet is carried by something, (2) that the
parser reads the worked examples the way their curators did, (3) that the
scoring is the cosine it says it is, and (4) that the page's JavaScript
produces the same answer as this module on a fixture (run under node when
node is available, as it is in CI).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess

import pytest

import dashboard
from refdata import precedent
from refdata.loaders import (
    load_cwa_investigations,
    load_dc_water_conflicts,
    load_water_authorities,
)
from refdata.taxonomies import DC_ACTIVITY_LABELS, FACT_DIMENSION_LABELS, FACT_FACETS, OUTCOME_TYPE_LABELS


# --- Vocabulary -------------------------------------------------------------------


class TestFacetTaxonomy:
    def test_every_facet_has_a_dimension_label_and_triggers(self):
        for fid, facet in FACT_FACETS.items():
            assert facet["dimension"] in FACT_DIMENSION_LABELS, fid
            assert facet["label"] and facet["description"], fid
            assert facet["triggers"], fid

    def test_triggers_are_tokens_the_tokenizer_emits(self):
        """A trigger the tokenizer can never produce is a dead word: the
        browser re-tokenizes the pasted text with the same rules."""
        from refdata.graph import tokenize

        for fid, facet in FACT_FACETS.items():
            for word in facet["triggers"] + facet.get("blockers", []):
                assert word in tokenize(word), (fid, word)

    def test_every_facet_is_carried_by_a_record(self):
        """Same-commit rule: a facet nothing carries is a chip matching nothing."""
        carried = {
            f
            for c in load_cwa_investigations()["cases"]
            for f in c.get("fact_pattern", [])
        } | {f for s in load_dc_water_conflicts()["sites"] for f in s.get("fact_pattern", [])}
        assert set(FACT_FACETS) <= carried, sorted(set(FACT_FACETS) - carried)

    def test_every_record_carries_known_facets(self):
        for c in load_cwa_investigations()["cases"]:
            assert c.get("fact_pattern"), c["case_id"]
            assert set(c["fact_pattern"]) <= set(FACT_FACETS), c["case_id"]
            assert c["fact_pattern"] == [f for f in FACT_FACETS if f in c["fact_pattern"]], (
                c["case_id"],
                "facets are stored in taxonomy order",
            )
        for s in load_dc_water_conflicts()["sites"]:
            assert s.get("fact_pattern"), s["site_id"]
            assert set(s["fact_pattern"]) <= set(FACT_FACETS), s["site_id"]

    def test_every_reading_carries_triggers_and_none_carry_scale(self):
        for r in load_water_authorities()["readings"]:
            triggers = r.get("fact_triggers")
            assert triggers, r["reading_id"]
            assert set(triggers) <= set(FACT_FACETS), r["reading_id"]
            assert "scale-hyperscale" not in triggers, r["reading_id"]

    def test_evaporative_towers_alone_do_not_trigger_npdes(self):
        """Blowdown goes to a sewer unless the site has an outfall; the review
        override in scripts/annotate_fact_patterns.py exists for this."""
        readings = {r["reading_id"]: r for r in load_water_authorities()["readings"]}
        assert "cool-evaporative" not in readings["cwa-402-npdes"]["fact_triggers"]
        assert "cool-evaporative" in readings["cwa-307-pretreatment"]["fact_triggers"]


# --- Parser ------------------------------------------------------------------------


class TestParseProject:
    def test_reads_facets_state_and_size(self):
        text = (
            "A proposed 600 MW hyperscale campus in Maricopa County, Arizona would pump "
            "groundwater from on-site wells for evaporative cooling towers, using about "
            "3 million gallons per day, and send blowdown to the city sewer."
        )
        parsed = precedent.parse_project(text)
        assert parsed["state"] == "AZ"
        assert parsed["mw"] == 600.0 and parsed["mgd"] == 3.0
        for facet in ("src-wells", "cool-evaporative", "out-sewer", "scale-hyperscale"):
            assert facet in parsed["facets"], facet
        assert parsed["matched"]["src-wells"]  # the words that set it are kept

    def test_blocker_suppresses_a_facet(self):
        parsed = precedent.parse_project("non-evaporative closed-loop liquid cooling")
        assert "cool-evaporative" not in parsed["facets"]
        assert "cool-closed" in parsed["facets"]

    def test_size_alone_sets_the_scale_facet(self):
        assert "scale-hyperscale" in precedent.parse_project("a 250 MW site")["facets"]
        assert "scale-hyperscale" in precedent.parse_project("1,500,000 gallons a day")["facets"]
        assert "scale-hyperscale" not in precedent.parse_project("a 40 MW site")["facets"]

    def test_only_per_day_volumes_count(self):
        """'78 million gallons over two years' is not 78 MGD."""
        assert precedent.parse_project("78.2 million gallons over two years")["mgd"] is None
        assert precedent.parse_project("31 million gallons a year")["mgd"] is None
        assert precedent.parse_project("5 million gallons per day")["mgd"] == 5.0
        assert precedent.parse_project("2.4 MGD")["mgd"] == 2.4

    def test_facets_come_back_in_taxonomy_order(self):
        parsed = precedent.parse_project("sewer blowdown from wells in a drought")
        assert parsed["facets"] == [f for f in FACT_FACETS if f in parsed["facets"]]


class TestStateCode:
    @pytest.mark.parametrize(
        "text, code",
        [
            ("Henderson County, Texas, by a Kansas developer", "TX"),
            ("Port Washington, Wisconsin on the Lake Michigan shore", "WI"),
            ("water from the Lower Colorado River Authority in Wharton County, Texas", "TX"),
            ("West Virginia", "WV"),
            ("Pageland Lane corridor, Prince William County, Virginia", "VA"),
            ("Federal (US)", None),
            ("US EPA guidance", None),
            ("a site in AZ", "AZ"),
            ("", None),
        ],
    )
    def test_names_the_state_a_passage_is_about(self, text, code):
        assert precedent.state_code_for(text) == code

    def test_dashboard_delegates_to_the_pure_helper(self):
        assert dashboard._state_code_for is precedent.state_code_for


# --- Matching ------------------------------------------------------------------------


class TestMatchProject:
    @pytest.fixture(scope="class")
    def arizona(self):
        parsed = precedent.parse_project(
            "A proposed 600 MW hyperscale campus in Maricopa County, Arizona would pump "
            "groundwater from on-site wells for evaporative cooling towers, using about "
            "3 million gallons per day, and send blowdown to the city sewer. Residents "
            "worry about aquifer depletion and well interference during drought."
        )
        return precedent.match_project(parsed["facets"], parsed["state"], "Maricopa County Arizona")

    def test_results_are_explained_by_shared_facets(self, arizona):
        for row in arizona["readings"] + arizona["cases"] + arizona["sites"]:
            assert row["shared"] or row.get("lexical"), row["id"]
            assert set(row["shared"]) <= set(arizona["facets"])

    def test_groundwater_readings_lead_for_a_well_pumping_project(self, arizona):
        top = [r["id"] for r in arizona["readings"][:6]]
        assert "gwmgmt-az-ama" in top
        assert "gw-ownership-takings" in top
        assert "cwa-307-pretreatment" in [r["id"] for r in arizona["readings"]]
        assert "cwa-402-npdes" not in top  # no outfall was described

    def test_a_reading_for_another_state_is_demoted_and_flagged(self, arizona):
        rows = {r["id"]: r for r in arizona["readings"]}
        assert rows["gwmgmt-az-ama"]["elsewhere"] is False
        sgma = rows.get("gwmgmt-sgma")
        assert sgma is None or (sgma["elsewhere"] is True and sgma["score"] < rows["gwmgmt-az-ama"]["score"])

    def test_activities_follow_path_order(self, arizona):
        order = list(DC_ACTIVITY_LABELS)
        acts = arizona["activities"]
        assert acts == sorted(acts, key=order.index)
        assert "withdraw" in acts and "discharge" in acts

    def test_scores_are_the_weighted_cosine(self, arizona):
        recs = precedent._records()
        weights = precedent.facet_weights(recs["cases"], recs["sites"])
        case = next(c for c in recs["cases"] if c["id"] == arizona["cases"][0]["id"])
        score, shared = precedent.overlap(arizona["facets"], case["facets"], weights)
        assert arizona["cases"][0]["facet_score"] == score
        assert arizona["cases"][0]["shared"] == shared
        assert 0 < score <= 1

    def test_outcomes_are_a_tally_over_the_closest_cases(self, arizona):
        sample = arizona["cases"][: arizona["outcome_sample"]]
        expected = {}
        for c in sample:
            for o in c["outcome_type"]:
                expected[o] = expected.get(o, 0) + 1
        assert {o["outcome"]: o["count"] for o in arizona["outcomes"]} == expected
        assert all(o["outcome"] in OUTCOME_TYPE_LABELS for o in arizona["outcomes"])

    def test_state_rules_and_local_actions_need_a_state(self, arizona):
        assert arizona["state"] == "AZ"
        assert all(a["state"] == "AZ" for a in arizona["local_actions"])
        assert all(i["state"] == "AZ" for i in arizona["instruments"])
        texas = precedent.match_project(arizona["facets"], "TX")
        assert texas["local_actions"] and all(a["state"] == "TX" for a in texas["local_actions"])
        assert texas["instruments"] and texas["instruments"][0]["status"] == "enacted"
        assert all(i["state"] == "TX" for i in texas["instruments"])
        nowhere = precedent.match_project(arizona["facets"], None)
        assert nowhere["instruments"] == [] and nowhere["local_actions"] == []

    def test_no_facets_no_matches(self):
        empty = precedent.match_project([], None)
        assert empty["readings"] == [] and empty["cases"] == [] and empty["outcomes"] == []

    def test_lexical_term_is_bounded_and_optional(self):
        facets = ["src-wells", "ctx-drought"]
        plain = precedent.match_project(facets, None)
        worded = precedent.match_project(facets, None, "Tucson Pima County Project Blue")
        assert all(r["lexical"] == 0 for r in plain["cases"])
        blue = next((c for c in worded["cases"] if "ProjectBlue" in c["id"]), None)
        assert blue is not None and blue["lexical"] > 0
        assert blue["score"] <= blue["facet_score"] + precedent.LEXICAL_WEIGHT * blue["lexical"] + 1e-6


# --- Worked examples ----------------------------------------------------------------


class TestProjectExamples:
    @pytest.fixture(scope="class")
    def examples(self):
        return precedent.load_project_examples()["examples"]

    def test_schema(self, examples):
        assert len(examples) >= 5
        for e in examples:
            for key in ("id", "name", "operator", "location", "state", "status", "status_date", "description", "facets", "sources"):
                assert key in e, (e.get("id"), key)
            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["status_date"]), e["id"]
            assert set(e["facets"]) <= set(FACT_FACETS), e["id"]
            assert e["facets"] == [f for f in FACT_FACETS if f in e["facets"]], e["id"]
            assert len(e["sources"]) >= 1 and all(s["url"].startswith("https://") for s in e["sources"])
            assert 40 <= len(e["description"].split()) <= 140, e["id"]

    def test_ids_are_unique_and_not_tracked_records(self, examples):
        from refdata.registry import build_registry

        ids = [e["id"] for e in examples]
        assert len(ids) == len(set(ids))
        assert not set(ids) & set(build_registry())

    def test_parser_recovers_most_curated_facets(self, examples):
        """The description is what a reader would paste; if the parser could
        not read it, the example teaches the wrong lesson."""
        for e in examples:
            parsed = precedent.parse_project(e["description"])
            assert parsed["state"] == e["state"], e["id"]
            hit = len(set(parsed["facets"]) & set(e["facets"]))
            assert hit / len(e["facets"]) >= 0.5, (e["id"], parsed["facets"], e["facets"])

    def test_every_example_matches_something(self, examples):
        for e in examples:
            result = precedent.match_project(e["facets"], e["state"], e["description"])
            assert result["readings"] and result["cases"], e["id"]


# --- Payload ------------------------------------------------------------------------


class TestPayload:
    @pytest.fixture(scope="class")
    def payload(self):
        return json.loads(precedent.payload_json())

    def test_carries_vocabulary_records_and_constants(self, payload):
        assert set(payload["facets"]) == set(FACT_FACETS)
        assert all("weight" in f and f["weight"] >= 1 for f in payload["facets"].values())
        assert len(payload["cases"]) == len(load_cwa_investigations()["cases"])
        assert len(payload["sites"]) == len(load_dc_water_conflicts()["sites"])
        assert len(payload["readings"]) == len(load_water_authorities()["readings"])
        assert payload["examples"]
        assert payload["constants"]["lexical_weight"] == precedent.LEXICAL_WEIGHT
        assert payload["stopwords"] and payload["min_token_len"] == 2

    def test_records_link_to_their_cards(self, payload):
        for row in payload["cases"] + payload["sites"] + payload["readings"]:
            assert row["anchor"] and row["tab"], row["id"]

    def test_index_covers_cases_and_sites_only(self, payload):
        ids = {c["id"] for c in payload["cases"]} | {s["id"] for s in payload["sites"]}
        assert set(payload["index"]["docs"]) <= ids
        assert len(payload["index"]["vocab"]) == len(payload["index"]["df"])

    def test_payload_is_built_once_per_data_change(self):
        assert precedent.payload_json() is precedent.payload_json()

    def test_size_budget(self, payload):
        assert len(precedent.payload_json()) < 500_000


# --- Page parity ----------------------------------------------------------------------


FIXTURE = (
    "Project Jupiter would build a 1.2 GW AI campus outside Las Cruces, New Mexico, "
    "pumping groundwater from a wellfield in a desert basin already in overdraft, with "
    "evaporative cooling towers, blowdown to the city sewer, and gas turbines on site; "
    "the county signed a community agreement and residents filed a lawsuit."
)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_page_script_matches_the_engine_on_a_fixture(tmp_path):
    """The browser runs the same arithmetic from the same payload. This runs
    the page's own parser and scorer under node and compares facets, the
    ranked ids and the outcome tally with this module's answer."""
    js = dashboard._project_check_js()
    payload = precedent.payload_json()
    harness = (
        "const D = JSON.parse(process.argv[2]);\n"
        "const text = process.argv[3];\n"
        + js.replace("(function(){", "const __engine = (function(){", 1)
        + "\nconst parsed = __engine.parseProject(text, D);\n"
        "const m = __engine.matchProject(parsed.facets, parsed.state, text, D);\n"
        "process.stdout.write(JSON.stringify({facets: parsed.facets, state: parsed.state, "
        "readings: m.readings.map(r => r.id), cases: m.cases.map(c => c.id), "
        "sites: m.sites.map(s => s.id), outcomes: m.outcomes.map(o => [o.outcome, o.count])}));\n"
    )
    script = tmp_path / "harness.js"
    script.write_text(harness, encoding="utf-8")
    out = subprocess.run(
        ["node", str(script), payload, FIXTURE], capture_output=True, text=True, check=True
    )
    got = json.loads(out.stdout)
    parsed = precedent.parse_project(FIXTURE)
    want = precedent.match_project(parsed["facets"], parsed["state"], FIXTURE)
    assert got["facets"] == parsed["facets"]
    assert got["state"] == parsed["state"]
    assert got["readings"] == [r["id"] for r in want["readings"]]
    assert got["cases"] == [c["id"] for c in want["cases"]]
    assert got["sites"] == [s["id"] for s in want["sites"]]
    assert got["outcomes"] == [[o["outcome"], o["count"]] for o in want["outcomes"]]


# --- Site integration ---------------------------------------------------------------


class TestSiteIntegration:
    def test_tab_is_registered_second_and_writes_its_payload(self):
        import build_site

        names = [n for n, _l, _b in build_site._tab_specs()]
        assert names[:2] == ["overview", "check"]
        files = build_site.build_site_files()
        assert "tab-check.html" in files and "project-data.json" in files
        assert json.loads(files["project-data.json"])["examples"]

    def test_fragment_prerenders_every_example_and_fetches_lazily(self):
        import build_site

        page = build_site.build_site_files()["tab-check.html"]
        for e in precedent.load_project_examples()["examples"]:
            assert f'id="example-{e["id"]}"' in page, e["id"]
        assert 'id="project-data" data-src="project-data.json?v=' in page
        assert "pcheck-run" in page and "pcheck-facet-box" in page

    def test_streamlit_fragment_inlines_the_payload(self):
        fragment = dashboard._build_project_check_html()
        assert '<script type="application/json" id="project-data">{"facets"' in fragment

    def test_overview_routes_to_the_tab(self):
        html_ = dashboard._build_overview_html()
        assert 'href="#panel-check"' in html_

    def test_llms_txt_carries_the_examples(self):
        import build_site

        txt = build_site.build_llms_txt()
        assert "## Check a project (fact-pattern matching)" in txt
        for e in precedent.load_project_examples()["examples"]:
            assert e["name"] in txt, e["id"]

    def test_copy_is_modal(self):
        """The tracker maps exposure; it never says a project *will* face a suit."""
        fragment = dashboard._build_project_check_html()
        for banned in ("will be sued", "will face", "is liable", "you should sue"):
            assert banned not in fragment.lower()
        assert "could reach" in dashboard.PROJECT_CHECK_LEAD
