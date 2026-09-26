"""Explore graph: the activity layer, the build-time layout, legal-paths mode.

The layout tests exist because the old in-browser layout looked fine and was
not: 167 of 445 records sat thousands of units off-canvas, where nobody could
see or click them, and nothing noticed. Broken and working were
indistinguishable from outside, so these assert the geometry directly.
"""

from __future__ import annotations

import math
import re

import pytest

import dashboard
from refdata import graph
from refdata.taxonomies import DC_ACTIVITY_LABELS


@pytest.fixture(scope="module")
def payload():
    return graph.build_payload()


class TestActivityHubs:
    def test_one_hub_per_activity_opening_its_path_group(self):
        hubs = {
            n["attrs"]["value"]: n
            for n in graph.build_graph()["nodes"]
            if n["kind"] == "hub" and n["attrs"]["hub_group"] == "activity"
        }
        assert list(hubs) == list(DC_ACTIVITY_LABELS)
        for activity, hub in hubs.items():
            assert hub["label"] == DC_ACTIVITY_LABELS[activity]
            assert hub["tab"] == "cwa"
            assert hub["anchor"] == f"paths-{activity}"

    def test_activity_edges_are_derived_and_labelled(self, payload):
        assert "reading.activity" in graph.DERIVED_EDGE_KINDS
        assert "reading.activity" in payload["derived_edge_kinds"]
        assert "reading.activity" in graph.EDGE_KIND_LABELS

    def test_cases_and_sites_inherit_activities_from_their_readings(self):
        nodes = {n["id"]: n for n in graph.build_graph()["nodes"]}
        # The ESA limit is ruled out at Memphis — reaches:false must not
        # hand the site the reading's activity.
        memphis = nodes["xai-colossus-memphis-tn"]["attrs"]
        assert "withdraw" in memphis["activities"]  # via its other readings
        smithfield = nodes["Smithfield-Pagan-River-1997"]["attrs"]
        assert smithfield["activities"] == ["discharge", "power"]  # cwa-402-npdes

    def test_limit_readings_carry_their_role(self):
        nodes = {n["id"]: n for n in graph.build_graph()["nodes"]}
        assert nodes["esa-proximate-cause-limit"]["attrs"]["role"] == "limit"
        assert nodes["cwa-402-npdes"]["attrs"]["role"] == "hook"


class TestPrecomputedLayout:
    def test_every_node_is_placed(self, payload):
        assert len(payload["layout"]) == len(payload["nodes"])
        for x, y in payload["layout"]:
            assert math.isfinite(x) and math.isfinite(y)

    def test_nothing_is_flung_off_canvas(self, payload):
        """The regression this layout exists for: every record within a frame
        the auto-fit can show at a legible zoom."""
        cx, cy = graph.LAYOUT_W / 2, graph.LAYOUT_H / 2
        radii = [math.hypot(x - cx, y - cy) for x, y in payload["layout"]]
        assert max(radii) < 1200, max(radii)

    def test_unconnected_records_sit_on_one_outer_ring(self, payload):
        default = {
            i for i, k in enumerate(payload["edge_kinds"]) if k not in graph.DERIVED_EDGE_KINDS
        }
        degree = [0] * len(payload["nodes"])
        for a, b, k in payload["edges"]:
            if k in default:
                degree[a] += 1
                degree[b] += 1
        cx, cy = graph.LAYOUT_W / 2, graph.LAYOUT_H / 2
        lone = [math.hypot(x - cx, y - cy) for (x, y), d in zip(payload["layout"], degree) if not d]
        core = [math.hypot(x - cx, y - cy) for (x, y), d in zip(payload["layout"], degree) if d]
        assert lone, "expected some records without a curated edge"
        assert max(lone) - min(lone) < 1.0, "the ring is not one circle"
        assert min(lone) > max(core), "the ring overlaps the connected core"

    def test_deterministic(self, payload):
        assert graph.build_payload()["layout"] == payload["layout"]

    def test_page_runs_the_same_constants(self):
        """The page re-runs this loop when a reader toggles edge kinds; with
        different constants the picture would jump on the first toggle."""
        js = dashboard._explore_js()
        match = re.search(
            r"var W = (\d+), H = (\d+), GRAVITY = ([\d.]+), CUTOFF = ([\d.]+), RING_GAP = (\d+);", js
        )
        assert match, "layout constants line not found in the Explore JS"
        w, h, gravity, cutoff, gap = match.groups()
        assert (int(w), int(h)) == (graph.LAYOUT_W, graph.LAYOUT_H)
        assert float(gravity) == graph.LAYOUT_GRAVITY
        assert float(cutoff) == graph.LAYOUT_CUTOFF
        assert int(gap) == graph.LAYOUT_RING_GAP
        assert f"var ITERATIONS = {graph.LAYOUT_ITERATIONS};" in js

    def test_first_open_draws_instead_of_simulating(self):
        js = dashboard._explore_js()
        assert "if (precomputed){ fitView(); draw(); }" in js


class TestLegalPathsMode:
    @pytest.fixture(scope="class")
    def fragment(self):
        return dashboard._build_explore_html()

    def test_layout_control_offers_both_views(self, fragment):
        assert 'id="explore-layout"' in fragment
        assert '<option value="paths">Legal paths</option>' in fragment

    def test_activity_filter_lists_every_activity(self, fragment):
        assert 'id="explore-activity"' in fragment
        for activity, label in DC_ACTIVITY_LABELS.items():
            assert f'<option value="{activity}">' in fragment, activity

    def test_columns_follow_the_order_of_a_legal_argument(self):
        js = dashboard._explore_js()
        match = re.search(r"var PATH_COLUMN = \{(.*?)\};", js, re.S)
        cols = dict(
            (k.strip().strip("'\""), int(v))
            for k, v in (pair.split(":") for pair in match.group(1).replace("\n", " ").split(","))
        )
        assert cols["activity"] < cols["statute"] < cols["reading"] < cols["case"] < cols["site"]

    def test_switching_to_paths_turns_on_the_links_it_needs(self):
        js = dashboard._explore_js()
        assert "var PATH_KINDS = ['reading.activity', 'reading.family'];" in js
        # Visibly: the connection-type checkboxes are updated, not bypassed.
        assert "kindBoxesByIndex[k2].checked = true" in js

    def test_draw_never_runs_paths_without_a_layout(self):
        """Regression: the first paths draw ran before the column layout
        existed and threw, aborting the layout switch (2026-09-26)."""
        js = dashboard._explore_js()
        assert "if (!pathPos) layoutPaths();" in js


def test_toolbar_controls_wrap_on_a_phone():
    """Regression: with the Layout selector added, the non-wrapping tools row
    pushed the Reset button past a 375px viewport (page scroll-width 412)."""
    css = dashboard._explore_css()
    rule = next(line for line in css.splitlines() if line.startswith(".explore-tools{"))
    assert "flex-wrap:wrap" in rule


def test_relayout_keeps_the_readers_camera():
    """PR #30 review: re-layout frames re-fit only if the reader has not
    panned or zoomed, and paths mode defers the network re-layout."""
    js = dashboard._explore_js()
    assert "if (!cameraMoved) fitView();" in js
    assert "if (mode === 'paths'){ layoutStale = true; return; }" in js
    assert "if (layoutStale) runLayout();" in js


def test_payload_is_built_once_per_data_change():
    """PR #30 review: the build needed the blob twice (URL hash + file)."""
    graph._PAYLOAD_CACHE.update(sig=None, json="")
    first = graph.payload_json()
    calls = []
    original = graph.build_payload
    graph.build_payload = lambda: calls.append(1) or original()
    try:
        assert graph.payload_json() == first
    finally:
        graph.build_payload = original
    assert calls == []
