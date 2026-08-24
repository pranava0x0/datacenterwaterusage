"""Tests for the datacentercommunitybenefits mirror's merge half (Spec F).

Two rules are worth pinning with tests, because getting either wrong is
silent: a re-sync of an unchanged source must change nothing, and a re-sync
must never rewrite a mirrored first-party quote. Both are fixture-based —
nothing here touches the network or the committed datasets.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.sync_community_benefits import (  # noqa: E402
    upsert_actions,
    upsert_claims,
    water_claims,
)


def _action(action_id="dccb-x-2026-01", **overrides):
    action = {
        "action_id": action_id,
        "jurisdiction": "Example County",
        "state": "TX",
        "action_type": "moratorium",
        "status": "active",
        "date": "2026-01",
        "water_related": True,
        "water_angle": "Residents cited aquifer draw.",
        "summary": "A six-month pause on new data-center applications.",
        "source_url": "https://example.org/a",
    }
    action.update(overrides)
    return action


def _claim(claim_id="acme-water-pledge", **overrides):
    claim = {
        "id": claim_id,
        "company_slug": "acme",
        "theme": "water",
        "statement": "We will return more water than we use by 2030.",
        "source_url": "https://example.org/claim",
        "source_title": "Acme sustainability page",
        "captured_at": "2026-05-01",
        "claim_type": "water-positive-pledge",
    }
    claim.update(overrides)
    return claim


class TestActionUpsert:
    def test_syncing_the_same_source_twice_changes_nothing(self):
        existing = [_action("dccb-a-2026-01"), _action("dccb-b-2026-02")]
        incoming = [_action("dccb-b-2026-02"), _action("dccb-c-2026-03")]

        once, first_report = upsert_actions(existing, incoming)
        twice, second_report = upsert_actions(once, incoming)

        assert once == twice
        assert first_report["added"] == ["dccb-c-2026-03"]
        assert second_report["added"] == []
        assert second_report["updated"] == []
        assert second_report["unchanged"] == len(incoming)

    def test_new_records_append_and_existing_order_is_kept(self):
        existing = [_action("dccb-a-2026-01"), _action("dccb-b-2026-02")]
        merged, _ = upsert_actions(existing, [_action("dccb-c-2026-03")])
        assert [a["action_id"] for a in merged] == [
            "dccb-a-2026-01",
            "dccb-b-2026-02",
            "dccb-c-2026-03",
        ]

    def test_an_overwrite_is_reported_field_by_field(self):
        """The curated corrections in local_actions.json live where a naive
        re-sync would flatten them, so the merge has to say what it touched."""
        existing = [_action("dccb-a-2026-01", status="superseded")]
        merged, report = upsert_actions(
            existing, [_action("dccb-a-2026-01", status="active")]
        )
        assert merged[0]["status"] == "active"
        assert report["updated"] == [
            {"action_id": "dccb-a-2026-01", "fields": ["status"]}
        ]

    def test_records_absent_upstream_are_never_dropped(self):
        """The upstream snapshot shrank by one record between two captures.
        An upsert keeps ours; a replace would have deleted it."""
        existing = [_action("direct-verified-here-2026-08")]
        merged, report = upsert_actions(existing, [_action("dccb-new-2026-08")])
        assert "direct-verified-here-2026-08" in {a["action_id"] for a in merged}
        assert report["added"] == ["dccb-new-2026-08"]

    def test_inputs_are_not_mutated(self):
        existing = [_action("dccb-a-2026-01", status="superseded")]
        incoming = [_action("dccb-a-2026-01", status="active")]
        upsert_actions(existing, incoming)
        assert existing[0]["status"] == "superseded"

    def test_records_without_an_id_are_skipped(self):
        merged, report = upsert_actions([], [{"jurisdiction": "Nowhere"}])
        assert merged == [] and report["added"] == []


class TestClaimUpsert:
    def test_a_mirrored_statement_is_never_edited(self):
        """The dataset's contract: `statement` is a verbatim first-party
        quote. A source that later rewords it does not get to rewrite what
        this tracker captured and dated."""
        existing = [_claim()]
        reworded = _claim(
            statement="We are water positive.",
            source_title="Acme sustainability page (revised)",
            captured_at="2026-08-01",
        )
        merged, _ = upsert_claims(existing, [reworded])
        assert merged[0]["statement"] == "We will return more water than we use by 2030."
        assert merged[0]["source_title"] == "Acme sustainability page"
        assert merged[0]["captured_at"] == "2026-05-01"

    def test_new_claims_append_verbatim(self):
        merged, report = upsert_claims([_claim("a")], [_claim("b")])
        assert [c["id"] for c in merged] == ["a", "b"]
        assert report["added"] == ["b"]
        assert merged[1]["statement"] == _claim()["statement"]

    def test_a_strictly_newer_delivered_is_adopted(self):
        existing = [
            _claim(delivered={"status": "partial", "assessed_at": "2026-05-17"})
        ]
        incoming = [
            _claim(delivered={"status": "shortfall", "assessed_at": "2026-08-01"})
        ]
        merged, report = upsert_claims(existing, incoming)
        assert merged[0]["delivered"]["status"] == "shortfall"
        assert report["delivered_updated"] == ["acme-water-pledge"]

    def test_our_newer_adjudication_wins(self):
        """As of August 2026 this is the live case for three claims: the
        tracker's own assessment is ahead of the source's."""
        existing = [
            _claim(delivered={"status": "partial", "assessed_at": "2026-07-26"})
        ]
        incoming = [
            _claim(delivered={"status": "delivered", "assessed_at": "2026-05-17"})
        ]
        merged, report = upsert_claims(existing, incoming)
        assert merged[0]["delivered"]["status"] == "partial"
        assert report["delivered_updated"] == []

    def test_syncing_the_same_source_twice_changes_nothing(self):
        existing = [_claim("a")]
        incoming = [_claim("a"), _claim("b")]
        once, _ = upsert_claims(existing, incoming)
        twice, report = upsert_claims(once, incoming)
        assert once == twice
        assert report["added"] == []

    def test_inputs_are_not_mutated(self):
        existing = [_claim(delivered={"status": "partial", "assessed_at": "2026-07-26"})]
        upsert_claims(
            existing, [_claim(delivered={"status": "shortfall", "assessed_at": "2027-01-01"})]
        )
        assert existing[0]["delivered"]["status"] == "partial"


class TestWaterFilter:
    def test_only_water_themed_claims_are_mirrored(self):
        payload = {
            "claims": [
                _claim("w", theme="water"),
                _claim("e", theme="energy"),
                _claim("n", theme=None),
            ]
        }
        assert [c["id"] for c in water_claims(payload)] == ["w"]

    def test_a_bare_list_payload_also_works(self):
        assert water_claims([_claim("w")]) == [_claim("w")]
