"""Water commitments: the dataset, the derived state matrix and company
scorecard, and the Commitments tab on both surfaces."""

from __future__ import annotations

import re

import pytest

import dashboard
from refdata import loaders, taxonomies
from refdata.registry import build_registry


def _records():
    return loaders.load_water_commitments()["commitments"]


class TestCommitmentsDataset:
    def test_loads_with_a_note(self):
        payload = loaders.load_water_commitments()
        assert payload["last_updated"]
        assert "legislation.json" in payload["note"]  # says what is NOT duplicated here
        assert len(_records()) >= 10

    def test_missing_file_returns_empty(self):
        assert loaders.load_water_commitments("/nonexistent.json")["commitments"] == []

    def test_required_fields(self):
        required = {"id", "level", "actor", "jurisdiction", "instrument", "date", "status",
                    "binding", "summary", "terms", "sources", "confidence"}
        ids = []
        for rec in _records():
            missing = required - set(rec)
            assert not missing, (rec.get("id"), missing)
            ids.append(rec["id"])
            assert re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", rec["date"]), rec["id"]
            assert rec["terms"], rec["id"]
            assert all(s["url"].startswith("http") for s in rec["sources"]), rec["id"]
            assert rec["confidence"] in {"high", "medium"}, rec["id"]
            if rec["confidence"] == "medium":
                # A lower-confidence record says why, in the record.
                assert rec.get("note"), rec["id"]
        assert len(ids) == len(set(ids))

    @pytest.mark.parametrize(
        "field,labels",
        [
            ("level", taxonomies.COMMITMENT_LEVEL_LABELS),
            ("binding", taxonomies.COMMITMENT_BINDING_LABELS),
            ("status", taxonomies.COMMITMENT_STATUS_LABELS),
        ],
    )
    def test_closed_taxonomies_both_ways(self, field, labels):
        used = {rec[field] for rec in _records()}
        assert used <= set(labels), used - set(labels)
        # A value no record uses renders a label that describes nothing.
        assert used == set(labels), set(labels) - used

    def test_term_types_closed_both_ways(self):
        used = {t["type"] for rec in _records() for t in rec["terms"]}
        assert used == set(taxonomies.COMMITMENT_TERM_LABELS), used ^ set(taxonomies.COMMITMENT_TERM_LABELS)

    def test_status_has_a_colour(self):
        assert set(taxonomies.COMMITMENT_STATUS_COLORS) == set(taxonomies.COMMITMENT_STATUS_LABELS)

    def test_cross_refs_resolve(self):
        reg = build_registry()
        for rec in _records():
            for target in rec.get("cross_ref_targets") or []:
                assert target in reg, (rec["id"], target)

    def test_stays_out_of_the_registry_and_graph(self):
        from refdata import graph

        reg = build_registry()
        node_ids = {n["id"] for n in graph.build_graph()["nodes"]}
        for rec in _records():
            assert rec["id"] not in reg and rec["id"] not in node_ids

    def test_no_state_records_here(self):
        """State commitments are derived from legislation.json; a state record
        here would be the same instrument twice."""
        assert {rec["level"] for rec in _records()} <= {"federal", "international", "local"}

    def test_the_rejected_agreement_is_not_counted_as_a_commitment(self):
        frederick = next(r for r in _records() if r["id"] == "frederick-county-md-quantum-cba-2026")
        assert frederick["status"] == "rejected"


class TestStateMatrix:
    def test_every_state_with_an_enacted_water_instrument_has_a_row(self):
        bills = loaders.load_legislation()["bills"]
        expected = set()
        tagged = {t for _label, tags in taxonomies.STATE_COMMITMENT_COLUMNS.values() for t in tags}
        for b in bills:
            if b["level"] == "state" and b["status"] == "enacted" and "water" in b["scope"]:
                if {p["tag"] for p in b["general_principles"]} & tagged:
                    expected.add(b["jurisdiction"])
        rows = {r["state"] for r in dashboard._state_commitment_matrix()}
        assert rows == expected

    def test_only_enacted_instruments_fill_cells(self):
        by_id = {b["bill_id"]: b for b in loaders.load_legislation()["bills"]}
        for row in dashboard._state_commitment_matrix():
            for ids in row["cells"].values():
                for bill_id in ids:
                    assert by_id[bill_id]["status"] == "enacted", bill_id

    def test_columns_cover_principles_without_overlap(self):
        seen = []
        for _label, tags in taxonomies.STATE_COMMITMENT_COLUMNS.values():
            seen.extend(tags)
        assert len(seen) == len(set(seen)), "a principle counts in two columns"
        assert set(seen) <= set(taxonomies.LEGISLATION_PRINCIPLE_DESCRIPTIONS)

    def test_virginia_order_lands_in_use_less(self):
        va = next(r for r in dashboard._state_commitment_matrix() if r["state"] == "Virginia")
        assert "VA EO 22 (2026)" in va["cells"]["conserve"]


class TestCompanyScorecard:
    def test_every_pledge_claim_appears_once(self):
        claims = loaders.load_company_water_claims()["claims"]
        pledges = [c["id"] for c in claims if c["claim_type"] in dashboard.PLEDGE_CLAIM_TYPES]
        shown = [c["id"] for row in dashboard._company_pledges() for c in row["pledges"]]
        assert sorted(shown) == sorted(pledges)

    def test_site_specific_promises_stay_on_issues(self):
        assert "site-specific-promise" not in dashboard.PLEDGE_CLAIM_TYPES


class TestCommitmentsTab:
    @pytest.fixture(scope="class")
    def fragment(self):
        return dashboard._build_commitments_html()

    def test_every_class_is_styled_on_both_surfaces(self, fragment):
        from refdata.loaders import BASE_DIR

        shared = (BASE_DIR / "assets" / "components.css").read_text()
        used = {c for attr in re.findall(r'class="([^"]+)"', fragment) for c in attr.split()}
        undefined = sorted(c for c in used if f".{c}" not in shared)
        assert not undefined, undefined

    def test_every_record_renders_with_its_anchor(self, fragment):
        for rec in _records():
            assert f'id="commitment-{rec["id"]}"' in fragment

    def test_links_resolve_to_registry_anchors_or_sections(self, fragment):
        anchors = {ref.anchor for ref in build_registry().values()}
        sections = {"commitments-national", "commitments-states", "commitments-local", "commitments-companies"}
        for href in set(re.findall(r'href="#([^"]+)"', fragment)):
            assert href in anchors or href in sections, href

    def test_the_finding_leads(self, fragment):
        assert "No U.S. national water strategy addresses data centers" in fragment

    def test_static_tab_and_llms(self):
        import build_site

        files = build_site.build_site_files()
        page = files[build_site.tab_file("commitments")]
        assert "<h2>Water Commitments</h2>" in page
        assert 'data-tab="commitments"' in files["index.html"]
        llms = files["llms.txt"]
        assert "## Water commitments" in llms
        for rec in _records():
            assert rec["id"] in llms, rec["id"]


def test_guidance_column_does_not_claim_exclusivity():
    """PR #30 review: 'Guidance only' mislabelled states with binding
    commitments in other columns (Virginia's EO 22)."""
    label, _tags = taxonomies.STATE_COMMITMENT_COLUMNS["guidance"]
    assert "only" not in label.lower()
