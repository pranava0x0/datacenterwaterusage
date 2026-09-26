"""Statute paths: activity → reading → precedent → live site.

The paths view is only as honest as the three fields it joins, so most of
these tests pin the data contract (every reading says what triggers it, in a
closed vocabulary) rather than the rendering.
"""

from __future__ import annotations

import pytest

from refdata import paths as P
from refdata.loaders import (
    load_cwa_investigations,
    load_dc_water_conflicts,
    load_water_authorities,
)
from refdata.taxonomies import DC_ACTIVITY_DESCRIPTIONS, DC_ACTIVITY_LABELS, DC_ROLE_LABELS


def _readings():
    return load_water_authorities()["readings"]


class TestActivitySchema:
    def test_every_reading_names_its_activities(self):
        for r in _readings():
            acts = r.get("dc_activities")
            assert acts, f"{r['reading_id']} has no dc_activities"
            assert 1 <= len(acts) <= 3, r["reading_id"]
            assert len(set(acts)) == len(acts), r["reading_id"]
            unknown = set(acts) - set(DC_ACTIVITY_LABELS)
            assert not unknown, f"{r['reading_id']}: {unknown}"

    def test_activities_are_listed_in_taxonomy_order(self):
        order = list(DC_ACTIVITY_LABELS)
        for r in _readings():
            acts = r["dc_activities"]
            assert acts == sorted(acts, key=order.index), r["reading_id"]

    def test_every_activity_is_claimed_and_described(self):
        # A value no reading claims would render an empty path group — the
        # graph's version of a filter chip that matches nothing.
        claimed = {a for r in _readings() for a in r["dc_activities"]}
        assert claimed == set(DC_ACTIVITY_LABELS)
        assert set(DC_ACTIVITY_DESCRIPTIONS) == set(DC_ACTIVITY_LABELS)

    def test_every_reading_states_its_trigger_as_a_clause(self):
        for r in _readings():
            trig = r.get("dc_trigger", "")
            assert 40 <= len(trig) <= 200, f"{r['reading_id']}: {len(trig)} chars"
            # Rendered after "Triggered when", so it must read as a clause: a
            # lowercase opening word, or an acronym ("PFAS-containing …").
            first = trig.split()[0].split("-")[0]
            assert trig[0].islower() or first.isupper(), r["reading_id"]
            assert not trig.endswith("."), r["reading_id"]

    def test_roles_are_closed_and_hooks_are_implicit(self):
        for r in _readings():
            if "dc_role" in r:
                assert r["dc_role"] in DC_ROLE_LABELS, r["reading_id"]
                # Only limits are written; an explicit "hook" is noise that
                # would drift from the default.
                assert r["dc_role"] == "limit", r["reading_id"]

    def test_negative_readings_are_flagged_as_limits(self):
        limits = {r["reading_id"] for r in _readings() if r.get("dc_role") == "limit"}
        assert "esa-proximate-cause-limit" in limits
        assert "cl-citizen-standing-limit" in limits


class TestBuildStatutePaths:
    @pytest.fixture(scope="class")
    def groups(self):
        return P.build_statute_paths()

    def test_one_group_per_activity_in_order(self, groups):
        assert [g["activity"] for g in groups] == list(DC_ACTIVITY_LABELS)

    def test_every_reading_activity_pair_is_one_path(self, groups):
        expected = {(a, r["reading_id"]) for r in _readings() for a in r["dc_activities"]}
        got = [(g["activity"], p["reading_id"]) for g in groups for p in g["paths"]]
        assert len(got) == len(set(got)), "a reading appears twice in one activity"
        assert set(got) == expected

    def test_anchors_are_unique(self, groups):
        anchors = [p["anchor"] for g in groups for p in g["paths"]]
        anchors += [g["anchor"] for g in groups]
        assert len(anchors) == len(set(anchors))

    def test_precedents_lead_with_the_curated_examples(self, groups):
        by_id = {r["reading_id"]: r for r in _readings()}
        for g in groups:
            for p in g["paths"]:
                curated = by_id[p["reading_id"]]["example_case_ids"]
                shown = [c["case_id"] for c in p["precedents"]]
                assert shown == (curated + [c for c in shown if c not in curated])[: len(shown)]
                assert shown[: min(len(curated), P.MAX_PRECEDENTS)] == curated[: P.MAX_PRECEDENTS]

    def test_more_cases_counts_every_citing_case(self, groups):
        cases = load_cwa_investigations()["cases"]
        for g in groups:
            for p in g["paths"]:
                rid = p["reading_id"]
                curated = next(r for r in _readings() if r["reading_id"] == rid)["example_case_ids"]
                citing = {c["case_id"] for c in cases if rid in (c.get("authorities") or [])}
                total = len(set(curated) | citing)
                assert len(p["precedents"]) + p["more_cases"] == total, rid

    def test_sites_split_into_in_play_and_ruled_out(self, groups):
        sites = load_dc_water_conflicts()["sites"]
        for g in groups:
            for p in g["paths"]:
                rid = p["reading_id"]
                live = [s["site_id"] for s in sites
                        for m in s.get("applicable_readings", [])
                        if m.get("reading_id") == rid and m.get("reaches") is not False]
                out = [s["site_id"] for s in sites
                       for m in s.get("applicable_readings", [])
                       if m.get("reading_id") == rid and m.get("reaches") is False]
                assert len(p["sites"]) + p["more_sites"] == len(live), rid
                assert [s["site_id"] for s in p["ruled_out"]] == out, rid

    def test_memphis_is_ruled_out_not_in_play_for_the_esa_limit(self, groups):
        withdraw = next(g for g in groups if g["activity"] == "withdraw")
        esa = next(p for p in withdraw["paths"] if p["reading_id"] == "esa-proximate-cause-limit")
        assert "xai-colossus-memphis-tn" in {s["site_id"] for s in esa["ruled_out"]}
        assert "xai-colossus-memphis-tn" not in {s["site_id"] for s in esa["sites"]}
        assert esa["role"] == "limit"

    def test_paths_are_ordered_by_statute_family(self, groups):
        from refdata.taxonomies import WATER_STATUTE_ORDER

        for g in groups:
            ranks = [WATER_STATUTE_ORDER.index(p["statute"]) for p in g["paths"]]
            assert ranks == sorted(ranks), g["activity"]


class TestStatutePathsHtml:
    @pytest.fixture(scope="class")
    def fragment(self):
        import dashboard

        return dashboard._build_statute_paths_html()

    def test_every_class_is_styled_on_both_surfaces(self, fragment):
        """The fragment renders through st.markdown (page CSS = components.css)
        and inside the static page. A class styled only in build_site's CSS
        renders as bare text in Streamlit — the PR #28 .jumpnav lesson."""
        import re

        from refdata.loaders import BASE_DIR

        shared = (BASE_DIR / "assets" / "components.css").read_text()
        used = {c for attr in re.findall(r'class="([^"]+)"', fragment) for c in attr.split()}
        undefined = sorted(c for c in used if f".{c}" not in shared)
        assert not undefined, undefined

    def test_every_link_targets_a_registry_anchor(self, fragment):
        import re

        from refdata.registry import build_registry

        anchors = {ref.anchor for ref in build_registry().values()}
        anchors |= {g["anchor"] for g in P.build_statute_paths()}
        hrefs = set(re.findall(r'href="#([^"]+)"', fragment))
        assert hrefs, "no links rendered"
        assert not sorted(hrefs - anchors)

    def test_one_row_per_path_and_one_group_per_activity(self, fragment):
        groups = P.build_statute_paths()
        assert fragment.count('class="path-row') == sum(len(g["paths"]) for g in groups)
        assert fragment.count('<details class="path-group"') == len(groups)

    def test_first_group_opens_the_rest_collapse(self, fragment):
        import re

        heads = re.findall(r'<details class="path-group"[^>]*>', fragment)
        assert "data-collapsed" not in heads[0]
        assert all("data-collapsed" in h and " open" in h for h in heads[1:])

    def test_limits_are_marked(self, fragment):
        limits = [r for r in _readings() if r.get("dc_role") == "limit"]
        n_rows = sum(len(r["dc_activities"]) for r in limits)
        assert fragment.count('class="path-row is-limit"') == n_rows

    def test_reading_cards_link_back_to_their_paths(self):
        import dashboard

        payload = load_water_authorities()
        toolkit = dashboard._build_authorities_html(payload)
        for r in payload["readings"]:
            for a in r["dc_activities"]:
                assert f'href="#{P.path_anchor(a, r["reading_id"])}"' in toolkit


class TestStaticSurface:
    def test_water_cases_opens_on_the_paths(self):
        import build_site

        tab = build_site.build_cwa_tab()
        assert 'data-subtab="cwa-paths" aria-selected="true"' in tab
        assert '<div class="subtabpanel" id="panel-cwa-paths">' in tab
        for part in ("cwa-p1", "cwa-p2", "cwa-p3"):
            assert f'<div class="subtabpanel" id="panel-{part}" hidden>' in tab
        assert 'id="statute-paths"' in tab
