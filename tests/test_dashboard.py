"""Tests for dashboard data processing and device detection.

Tests cover:
- Flow MGD extraction from metric strings
- Source type classification
- Device detection and chart configuration
- Local context data and household equivalent calculations
- Per-query estimates data integrity
- Edge cases for empty/malformed data
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from dashboard import (
    _extract_flow_mgd,
    _file_signature,
    _classify_source,
    compute_household_equivalent,
    load_legislation,
    load_company_water_claims,
    load_cwa_investigations,
    _legislation_rows,
    _legislation_status_summary,
    _cwa_summary,
    _cwa_year_end,
    _cwa_datacenter_insights,
    _build_cwa_case_html,
    _cwa_statute_explainer_md,
    _build_bill_card_html,
    CONTEXT_DATA,
    MASLEY_COMPARISONS,
    PER_QUERY_ESTIMATES,
    SCORECARD_DATA,
    TRANSPARENCY_GAPS,
    TIMELINE_EVENTS,
    CWA_CATEGORY_LABELS,
)
import utils.device as device_mod
from utils.device import (
    MOBILE_MAX,
    TABLET_MAX,
    DeviceInfo,
    DeviceType,
    _classify_width,
    get_chart_config,
    get_device_type,
)


# --- Tests for _extract_flow_mgd ---


class TestExtractFlowMGD:
    def test_standard_mgd_value(self):
        metric = "Flow, in conduit or thru treatment plant: Dmr Value Nmbr: 6.4 MGD"
        assert _extract_flow_mgd(metric) == 6.4

    def test_mgd_with_decimal(self):
        metric = "Flow: Dmr Value Nmbr: 12.53 MGD"
        assert _extract_flow_mgd(metric) == 12.53

    def test_mgd_integer(self):
        metric = "Flow: Quantity Avg: 5 MGD"
        assert _extract_flow_mgd(metric) == 5.0

    def test_no_mgd_in_string(self):
        metric = "Turbidity: Dmr Value Nmbr: .05 NTU"
        assert _extract_flow_mgd(metric) is None

    def test_none_input(self):
        assert _extract_flow_mgd(None) is None

    def test_empty_string(self):
        assert _extract_flow_mgd("") is None

    def test_non_string_input(self):
        assert _extract_flow_mgd(42) is None

    def test_mgd_case_insensitive(self):
        metric = "Flow: 7.1 mgd"
        assert _extract_flow_mgd(metric) == 7.1

    def test_multiple_numbers_takes_first_before_mgd(self):
        metric = "Flow: Permit Limit 11 Actual: 6.4 MGD"
        result = _extract_flow_mgd(metric)
        assert result is not None
        assert result == 6.4

    def test_vectorized_extraction_matches_rowwise(self):
        # load_data() now derives flow_mgd with a single vectorized regex pass
        # instead of .apply(_extract_flow_mgd). This guards parity: the column
        # math must equal the scalar helper for every input shape, incl. NaN,
        # None, no-match, and unparseable captures like "3.2.1 MGD".
        import math
        import numpy as np
        import pandas as pd

        samples = [
            "Flow: 6.7 MGD",
            "12 mgd avg",
            "no metric here",
            "3.2.1 MGD",          # unparseable -> None / NaN
            "0.26 MGD peak",
            "",
            None,
            float("nan"),
            "MGD only",            # keyword but no number
            "1000 gallons",        # number but no MGD
            "  9.9  MGD ",
        ]
        col = pd.Series(samples, dtype="object")
        vectorized = pd.to_numeric(
            col.astype(str).str.extract(
                r"([\d.]+)\s*MGD", flags=re.IGNORECASE, expand=False
            ),
            errors="coerce",
        )
        for raw, vec_val in zip(samples, vectorized.tolist()):
            scalar = _extract_flow_mgd(raw)
            vec_none = vec_val is None or (
                isinstance(vec_val, float) and math.isnan(vec_val)
            )
            if scalar is None:
                assert vec_none, f"{raw!r}: scalar None but vectorized {vec_val}"
            else:
                assert not vec_none and float(vec_val) == float(scalar), (
                    f"{raw!r}: vectorized {vec_val} != scalar {scalar}"
                )


# --- Tests for the file-signature cache key (mtime-based invalidation) ---


class TestFileSignature:
    def test_missing_file_is_zero(self):
        assert _file_signature("/nonexistent/definitely/not/here.json") == (0, 0)

    def test_signature_changes_when_file_changes(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text('{"a": 1}', encoding="utf-8")
        sig1 = _file_signature(p)
        assert sig1 != (0, 0)
        # Growing the file changes the size component immediately.
        p.write_text('{"a": 1, "b": 2, "c": 3}', encoding="utf-8")
        sig2 = _file_signature(p)
        assert sig2 != sig1, "signature must change when the file content changes"

    def test_signature_stable_for_unchanged_file(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text('{"a": 1}', encoding="utf-8")
        assert _file_signature(p) == _file_signature(p)


# --- Tests for _classify_source ---


class TestClassifySource:
    def test_echo_dmr(self):
        assert _classify_source("epa_echo_dmr") == "EPA ECHO Flow Data"

    def test_arcgis(self):
        assert _classify_source("va_deq_arcgis") == "Permit Metadata"

    def test_legistar(self):
        assert _classify_source("oh_columbus_legistar") == "Legislative Records"

    def test_acfr(self):
        assert _classify_source("va_loudoun_acfr") == "Financial Reports"

    def test_naics(self):
        assert _classify_source("epa_echo_naics") == "Facility Discovery"

    def test_general_permit(self):
        assert _classify_source("oh_epa_general_permit") == "General Permit Tracker"

    def test_unknown_source(self):
        assert _classify_source("something_else") == "Other"

    def test_none_source(self):
        assert _classify_source(None) == "Other"


# --- Data validation for flow extraction ---


class TestFlowDataValidation:
    """Validate flow extraction against real data patterns from results.csv."""

    REAL_METRICS = [
        ("Flow, in conduit or thru treatment plant: Dmr Value Nmbr: 6.4 MGD", 6.4),
        ("Flow, in conduit or thru treatment plant: Dmr Value Nmbr: 7.3 MGD", 7.3),
        ("Flow, in conduit or thru treatment plant: Dmr Value Nmbr: 6.8 MGD", 6.8),
        ("Flow, in conduit or thru treatment plant: Dmr Value Nmbr: 7.5 MGD", 7.5),
        ("Flow, in conduit or thru treatment plant: Dmr Value Nmbr: 6.3 MGD", 6.3),
        ("Flow, in conduit or thru treatment plant: Dmr Value Nmbr: 5 MGD", 5.0),
    ]

    def test_all_real_metrics_parse_correctly(self):
        """Every real metric from results.csv should parse to expected value."""
        for metric_str, expected_val in self.REAL_METRICS:
            result = _extract_flow_mgd(metric_str)
            assert result == expected_val, (
                f"Failed to parse '{metric_str}': got {result}, expected {expected_val}"
            )

    def test_turbidity_excluded(self):
        """Turbidity records should return None (not flow data)."""
        turbidity = "Turbidity: Dmr Value Nmbr: .05 NTU"
        assert _extract_flow_mgd(turbidity) is None

    def test_flow_values_are_reasonable(self):
        """Extracted flow values should be in a reasonable range for WWTPs."""
        for metric_str, val in self.REAL_METRICS:
            result = _extract_flow_mgd(metric_str)
            assert result is not None
            assert 0 < result < 1000, (
                f"Flow {result} MGD from '{metric_str}' is outside reasonable range"
            )


# --- Tests for device detection ---


class TestDeviceDetection:
    """Test device type classification and breakpoints."""

    def test_breakpoint_values(self):
        assert MOBILE_MAX == 768
        assert TABLET_MAX == 1024

    def test_device_info_construction(self):
        info = DeviceInfo(DeviceType.MOBILE, 375)
        assert info.device_type == DeviceType.MOBILE
        assert info.viewport_width == 375

    def test_device_info_none_width(self):
        info = DeviceInfo(DeviceType.DESKTOP, None)
        assert info.device_type == DeviceType.DESKTOP
        assert info.viewport_width is None

    def test_device_type_is_string_enum(self):
        assert DeviceType.MOBILE == "mobile"
        assert DeviceType.TABLET == "tablet"
        assert DeviceType.DESKTOP == "desktop"

    def test_classify_width_breakpoints(self):
        # Pure classifier — covers every breakpoint boundary exactly.
        assert _classify_width(None) == DeviceInfo(DeviceType.DESKTOP, None)
        assert _classify_width(375).device_type == DeviceType.MOBILE
        assert _classify_width(767).device_type == DeviceType.MOBILE
        assert _classify_width(768).device_type == DeviceType.TABLET  # not < 768
        assert _classify_width(1023).device_type == DeviceType.TABLET
        assert _classify_width(1024).device_type == DeviceType.DESKTOP  # not < 1024
        assert _classify_width(1280).device_type == DeviceType.DESKTOP

    def test_get_device_type_memoizes_after_resolution(self, monkeypatch):
        # Once a real width resolves, get_device_type caches the DeviceInfo and
        # reuses it without re-issuing the JS round-trip on later reruns.
        class FakeState(dict):
            pass

        state = FakeState()
        monkeypatch.setattr(device_mod.st, "session_state", state, raising=False)

        calls = {"n": 0}

        def fake_width():
            calls["n"] += 1
            return 375

        monkeypatch.setattr(device_mod, "get_viewport_width", fake_width)

        first = get_device_type()
        assert first.device_type == DeviceType.MOBILE
        assert calls["n"] == 1
        assert device_mod._DEVICE_CACHE_KEY in state

        # Second call returns the cached value WITHOUT calling get_viewport_width.
        second = get_device_type()
        assert second == first
        assert calls["n"] == 1, "cached path must skip the JS width read"

    def test_get_device_type_does_not_cache_cold_none_frame(self, monkeypatch):
        # The cold-start None frame must NOT be memoized, so detection keeps
        # retrying until a real width arrives.
        state = dict()
        monkeypatch.setattr(device_mod.st, "session_state", state, raising=False)
        monkeypatch.setattr(device_mod, "get_viewport_width", lambda: None)

        info = get_device_type()
        assert info.device_type == DeviceType.DESKTOP
        assert info.viewport_width is None
        assert device_mod._DEVICE_CACHE_KEY not in state, "cold None must not cache"


class TestChartConfig:
    """Test per-device chart configuration."""

    def test_all_device_types_have_config(self):
        for dt in DeviceType:
            cfg = get_chart_config(dt)
            assert isinstance(cfg, dict)

    def test_mobile_charts_shorter(self):
        mobile = get_chart_config(DeviceType.MOBILE)
        desktop = get_chart_config(DeviceType.DESKTOP)
        assert mobile["flow_height"] < desktop["flow_height"]
        assert mobile["heatmap_height"] < desktop["heatmap_height"]

    def test_mobile_hides_legend(self):
        assert get_chart_config(DeviceType.MOBILE)["show_legend"] is False
        assert get_chart_config(DeviceType.DESKTOP)["show_legend"] is True

    def test_config_has_required_keys(self):
        required = [
            "flow_height", "heatmap_height", "source_height", "table_height",
            "font_size", "title_font_size", "legend_y", "marker_size",
            "line_width", "show_legend", "hovermode", "margin",
        ]
        for dt in DeviceType:
            cfg = get_chart_config(dt)
            for key in required:
                assert key in cfg, f"Missing '{key}' in {dt} config"

    def test_tablet_between_mobile_and_desktop(self):
        mobile = get_chart_config(DeviceType.MOBILE)
        tablet = get_chart_config(DeviceType.TABLET)
        desktop = get_chart_config(DeviceType.DESKTOP)
        assert mobile["flow_height"] < tablet["flow_height"] < desktop["flow_height"]
        assert mobile["font_size"] < tablet["font_size"] < desktop["font_size"]


# --- Tests for household equivalent calculation ---


class TestHouseholdEquivalent:
    """Test the household-equivalent conversion used in context cards."""

    def test_standard_calculation(self):
        # 1 billion gallons / (200 GPD * 365) = ~13,699 homes
        result = compute_household_equivalent(1_000_000_000, gpd=200)
        assert result == 13698  # int truncation

    def test_loudoun_data(self):
        """Loudoun ACFR 2023: 1.635B gal should be ~22,000+ homes."""
        result = compute_household_equivalent(1_635_000_000, gpd=200)
        assert 22_000 < result < 23_000

    def test_zero_gallons(self):
        assert compute_household_equivalent(0) == 0

    def test_zero_gpd_returns_zero(self):
        assert compute_household_equivalent(1_000_000, gpd=0) == 0

    def test_negative_gpd_returns_zero(self):
        assert compute_household_equivalent(1_000_000, gpd=-100) == 0

    def test_default_gpd_is_200(self):
        result_default = compute_household_equivalent(73_000_000)
        result_explicit = compute_household_equivalent(73_000_000, gpd=200)
        assert result_default == result_explicit


# --- Tests for context data integrity ---


class TestContextData:
    """Validate the reference data used in Local Context cards."""

    def test_all_regions_have_required_fields(self):
        for key in ("loudoun", "pwc"):
            ctx = CONTEXT_DATA[key]
            assert "label" in ctx
            assert "dc_water_gallons" in ctx
            assert "dc_water_year" in ctx
            assert "utility_total_gallons" in ctx
            assert "avg_household_gpd" in ctx
            assert "source" in ctx

    def test_dc_water_less_than_total(self):
        """Data center water should be a fraction of total utility sales."""
        for key in ("loudoun", "pwc"):
            ctx = CONTEXT_DATA[key]
            assert ctx["dc_water_gallons"] < ctx["utility_total_gallons"]

    def test_percentages_are_reasonable(self):
        """DC share should be between 1% and 50% of total utility sales."""
        for key in ("loudoun", "pwc"):
            ctx = CONTEXT_DATA[key]
            pct = ctx["dc_water_gallons"] / ctx["utility_total_gallons"] * 100
            assert 1 < pct < 50, f"{ctx['label']}: {pct:.1f}% is outside expected range"

    def test_central_ohio_projections(self):
        oh = CONTEXT_DATA["central_ohio"]
        assert oh["projected_dc_mgd_2030"] < oh["projected_dc_mgd_2050"]
        assert oh["projected_dc_mgd_2030"] > 0

    def test_loudoun_water_year(self):
        assert CONTEXT_DATA["loudoun"]["dc_water_year"] == 2023

    def test_pwc_data_center_count(self):
        assert CONTEXT_DATA["pwc"]["dc_count"] == 56


# --- Tests for per-query estimates data ---


class TestPerQueryEstimates:
    """Validate the per-query water estimate data."""

    def test_at_least_three_estimates(self):
        assert len(PER_QUERY_ESTIMATES) >= 3

    def test_all_estimates_have_required_fields(self):
        for est in PER_QUERY_ESTIMATES:
            assert "label" in est
            assert "ml" in est
            assert "source" in est
            assert "note" in est

    def test_all_ml_values_positive(self):
        for est in PER_QUERY_ESTIMATES:
            assert est["ml"] > 0, f"Estimate '{est['label']}' has non-positive ml value"

    def test_range_spans_orders_of_magnitude(self):
        """The whole point is showing the 2000x variance."""
        values = [e["ml"] for e in PER_QUERY_ESTIMATES]
        assert max(values) / min(values) > 100

    def test_estimates_are_sorted_by_ml_when_sorted(self):
        """Verify sorting works for display."""
        sorted_est = sorted(PER_QUERY_ESTIMATES, key=lambda e: e["ml"])
        for i in range(len(sorted_est) - 1):
            assert sorted_est[i]["ml"] <= sorted_est[i + 1]["ml"]


# --- Tests for Transparency Scorecard data ---


class TestScorecardData:
    """Validate the scorecard reference data."""

    def test_at_least_ten_sources(self):
        assert len(SCORECARD_DATA) >= 10

    def test_all_entries_have_required_fields(self):
        required = ["source", "scraper", "disclosure", "geo_resolution", "freshness", "confidence", "notes"]
        for entry in SCORECARD_DATA:
            for field in required:
                assert field in entry, f"Missing '{field}' in {entry.get('source', '?')}"

    def test_valid_disclosure_types(self):
        valid = {"mandated", "voluntary", "inferred"}
        for entry in SCORECARD_DATA:
            assert entry["disclosure"] in valid, (
                f"{entry['source']}: invalid disclosure '{entry['disclosure']}'"
            )

    def test_valid_confidence_levels(self):
        valid = {"high", "medium", "low"}
        for entry in SCORECARD_DATA:
            assert entry["confidence"] in valid, (
                f"{entry['source']}: invalid confidence '{entry['confidence']}'"
            )

    def test_valid_geo_resolution(self):
        valid = {"facility", "county", "state", "national"}
        for entry in SCORECARD_DATA:
            assert entry["geo_resolution"] in valid, (
                f"{entry['source']}: invalid resolution '{entry['geo_resolution']}'"
            )

    def test_valid_freshness(self):
        valid = {"monthly", "quarterly", "annual", "one-time", "irregular"}
        for entry in SCORECARD_DATA:
            assert entry["freshness"] in valid, (
                f"{entry['source']}: invalid freshness '{entry['freshness']}'"
            )

    def test_echo_dmr_is_high_confidence(self):
        echo = [s for s in SCORECARD_DATA if s["scraper"] == "epa_echo_dmr"]
        assert len(echo) == 1
        assert echo[0]["confidence"] == "high"

    def test_no_duplicate_scrapers(self):
        scrapers = [s["scraper"] for s in SCORECARD_DATA]
        assert len(scrapers) == len(set(scrapers))


class TestTransparencyGaps:
    """Validate transparency gap data."""

    def test_at_least_three_gaps(self):
        assert len(TRANSPARENCY_GAPS) >= 3

    def test_all_gaps_have_required_fields(self):
        for gap in TRANSPARENCY_GAPS:
            assert "gap" in gap
            assert "impact" in gap
            assert "status" in gap

    def test_sb553_included(self):
        sb553 = [g for g in TRANSPARENCY_GAPS if "SB 553" in g["gap"]]
        assert len(sb553) == 1

    def test_nda_gap_included(self):
        nda = [g for g in TRANSPARENCY_GAPS if "NDA" in g["gap"]]
        assert len(nda) == 1


# --- Tests for Timeline data ---


class TestTimelineData:
    """Validate timeline event data."""

    def test_at_least_five_events(self):
        assert len(TIMELINE_EVENTS) >= 5

    def test_all_events_have_required_fields(self):
        required = ["date", "year", "label", "category", "detail"]
        for event in TIMELINE_EVENTS:
            for field in required:
                assert field in event, f"Missing '{field}' in {event.get('label', '?')}"

    def test_valid_categories(self):
        valid = {"policy", "data", "research", "legal"}
        for event in TIMELINE_EVENTS:
            assert event["category"] in valid, (
                f"{event['label']}: invalid category '{event['category']}'"
            )

    def test_dates_are_chronological_when_sorted(self):
        sorted_events = sorted(TIMELINE_EVENTS, key=lambda e: e["date"])
        for i in range(len(sorted_events) - 1):
            assert sorted_events[i]["date"] <= sorted_events[i + 1]["date"]

    def test_year_matches_date(self):
        for event in TIMELINE_EVENTS:
            year_from_date = int(event["date"][:4])
            assert event["year"] == year_from_date, (
                f"{event['label']}: year {event['year']} doesn't match date {event['date']}"
            )

    def test_sb553_vote_included(self):
        sb553 = [e for e in TIMELINE_EVENTS if "SB 553" in e["label"]]
        assert len(sb553) >= 1

    def test_multiple_categories_represented(self):
        categories = {e["category"] for e in TIMELINE_EVENTS}
        assert len(categories) >= 3


# --- Tests for the National Legislation Tracker ---

VALID_LEG_STATUS = {"enacted", "introduced", "failed", "unknown"}
VALID_LEG_CONFIDENCE = {"high", "medium", "low"}
VALID_LEG_SCOPE = {"water", "energy"}
VALID_LEG_LEVEL = {"state", "federal", "local"}


class TestLegislationTracker:
    def _bills(self):
        return load_legislation().get("bills", [])

    def test_dataset_loads(self):
        payload = load_legislation()
        assert payload.get("last_updated")
        assert len(payload.get("bills", [])) >= 10

    def test_missing_file_returns_empty(self):
        payload = load_legislation("/nonexistent/legislation.json")
        assert payload["bills"] == []

    def test_required_fields_present(self):
        required = {
            "bill_id",
            "jurisdiction",
            "level",
            "summary",
            "scope",
            "status",
            "source_url",
            "last_verified",
            "verified",
            "confidence",
        }
        for b in self._bills():
            missing = required - set(b)
            assert not missing, f"{b.get('bill_id')} missing {missing}"
            assert isinstance(b["scope"], list) and b["scope"]
            assert isinstance(b["verified"], bool)

    def test_valid_enums(self):
        for b in self._bills():
            assert b["status"] in VALID_LEG_STATUS, b["bill_id"]
            assert b["confidence"] in VALID_LEG_CONFIDENCE, b["bill_id"]
            assert set(b["scope"]) <= VALID_LEG_SCOPE, b["bill_id"]
            assert b["level"] in VALID_LEG_LEVEL, f"{b['bill_id']} bad level {b.get('level')!r}"

    def test_enacted_bills_are_verified(self):
        # Never assert a law is enacted without having verified it.
        for b in self._bills():
            if b["status"] == "enacted":
                assert b["verified"] is True, f"{b['bill_id']} enacted but unverified"

    def test_verified_bills_have_status_detail(self):
        for b in self._bills():
            if b["verified"]:
                assert b.get("status_detail"), f"{b['bill_id']} verified w/o detail"

    def test_source_urls_are_http(self):
        for b in self._bills():
            url = b.get("source_url", "")
            if url:
                assert url.startswith("http"), f"{b['bill_id']} bad url {url}"

    def test_known_enacted_laws_present(self):
        ids = {b["bill_id"] for b in self._bills() if b["status"] == "enacted"}
        assert any("HB 496" in i or "SB 553" in i for i in ids)  # Virginia
        assert any("HF 16" in i for i in ids)  # Minnesota

    def test_rows_match_bill_count(self):
        bills = self._bills()
        rows = _legislation_rows(bills)
        assert len(rows) == len(bills)
        assert {"Bill", "Status", "Verified", "Summary"} <= set(rows[0])

    def test_status_summary_is_string(self):
        summary = _legislation_status_summary(self._bills())
        assert isinstance(summary, str) and "Enacted" in summary

    # --- Enrichment fields (recent_news, public_sentiment, general_principles, timeline) ---
    # Enrichment is required for every bill so the expander never renders empty.
    # If a future bill genuinely has no public coverage, set the field to an empty
    # list/string explicitly so this test still catches accidental omissions.

    def test_every_bill_has_enrichment_keys(self):
        keys = {"recent_news", "public_sentiment", "general_principles", "timeline"}
        for b in self._bills():
            missing = keys - set(b)
            assert not missing, f"{b['bill_id']} missing {missing}"

    def test_recent_news_items_well_formed(self):
        required = {"date", "title", "source", "url", "takeaway"}
        for b in self._bills():
            for item in b["recent_news"]:
                missing = required - set(item)
                assert not missing, f"{b['bill_id']} news missing {missing}"
                # YYYY-MM-DD shape
                assert re.match(r"^\d{4}-\d{2}-\d{2}$", item["date"]), item
                assert item["url"].startswith("http"), item
                assert item["title"] and item["takeaway"]

    def test_general_principles_have_tag_and_note(self):
        for b in self._bills():
            principles = b["general_principles"]
            assert isinstance(principles, list) and principles, b["bill_id"]
            for p in principles:
                assert p.get("tag"), f"{b['bill_id']} principle missing tag"
                assert p.get("note"), f"{b['bill_id']} principle missing note"

    def test_timeline_entries_dated_and_labeled(self):
        for b in self._bills():
            timeline = b["timeline"]
            assert isinstance(timeline, list) and timeline, b["bill_id"]
            for ev in timeline:
                assert re.match(r"^\d{4}-\d{2}-\d{2}$", ev.get("date", "")), ev
                assert ev.get("milestone"), f"{b['bill_id']} timeline missing milestone"

    def test_public_sentiment_is_nontrivial_paragraph(self):
        for b in self._bills():
            sentiment = b["public_sentiment"]
            assert isinstance(sentiment, str)
            # Aim for at least a sentence of substance; anything shorter is a placeholder.
            assert len(sentiment) > 80, f"{b['bill_id']} sentiment too short"

    def test_bill_card_html_renders_for_every_bill(self):
        # Smoke test for the bill-card renderer. Catches accidental schema
        # mismatches (e.g., a new entry with status_calls typo, or a local /
        # regulatory entry that breaks the layout) before they hit the UI.
        import html as _html

        for b in self._bills():
            html_str = _build_bill_card_html(b)
            assert html_str.startswith('<div class="bill-card">'), b["bill_id"]
            # bill_id must round-trip through the renderer (HTML-escaped).
            assert _html.escape(b["bill_id"]) in html_str, b["bill_id"]
            # Status badge must show one of the four labelled statuses, not
            # a stray raw value.
            for label in ("Enacted", "Introduced", "Failed", "Unknown"):
                if label in html_str:
                    break
            else:
                raise AssertionError(f"{b['bill_id']} no status pill rendered")


# --- Tests for CWA investigations tracker ---

VALID_CWA_CATEGORIES = {"datacenter", "adjacent", "industrial", "precedent"}


class TestCWAInvestigations:
    def _cases(self):
        return load_cwa_investigations().get("cases", [])

    def test_dataset_loads(self):
        payload = load_cwa_investigations()
        assert payload.get("last_updated")
        # Want at least one case from each category so the tracker has
        # representational coverage.
        cases = payload.get("cases", [])
        assert len(cases) >= 8

    def test_missing_file_returns_empty(self):
        payload = load_cwa_investigations("/nonexistent/cwa.json")
        assert payload["cases"] == []

    def test_required_fields_present(self):
        required = {
            "case_id",
            "category",
            "respondent",
            "year",
            "cwa_section",
            "violation_summary",
            "outcome",
            "takeaway",
            "sources",
        }
        for c in self._cases():
            missing = required - set(c)
            assert not missing, f"{c.get('case_id')} missing {missing}"

    def test_categories_are_valid(self):
        for c in self._cases():
            assert c["category"] in VALID_CWA_CATEGORIES, c["case_id"]

    def test_case_type_classification(self):
        # Every case carries the project-type taxonomy used by the filters; a
        # value outside CWA_CASE_TYPE_LABELS would silently vanish from the
        # static site's checkbox filter.
        from dashboard import CWA_CASE_TYPE_LABELS, CWA_STATUS_LABELS

        for c in self._cases():
            assert c.get("case_type") in CWA_CASE_TYPE_LABELS, c["case_id"]
            assert c.get("cwa_applied") in CWA_STATUS_LABELS, c["case_id"]
            assert c.get("cwa_instrument"), f"{c['case_id']} missing cwa_instrument"

    def test_non_applied_cases_have_pathway_and_analogs(self):
        # The whole point of tracking pending / not-applied cases: each must
        # explain how the CWA *could* reach the fact pattern and point at
        # historic examples that resolve to real cases in this dataset.
        ids = {c["case_id"] for c in self._cases()}
        for c in self._cases():
            if c["cwa_applied"] in ("pending", "not-applied"):
                assert len(c.get("cwa_pathway", "")) > 60, (
                    f"{c['case_id']} needs a substantive cwa_pathway"
                )
                analogs = c.get("analogous_cases", [])
                assert analogs, f"{c['case_id']} needs analogous_cases"
                for a in analogs:
                    assert a in ids, f"{c['case_id']}: unknown analog {a}"
                assert c["case_id"] not in analogs, (
                    f"{c['case_id']} cannot be its own analog"
                )

    def test_card_renders_classification_and_pathway(self):
        # The card must answer (1) what type of case + did the CWA apply, and
        # (2) for non-applied cases, how it could apply with analog links.
        ids = {c["case_id"] for c in self._cases()}
        for c in self._cases():
            html_str = _build_cwa_case_html(c, ids)
            assert 'class="cwa-type-pill"' in html_str, c["case_id"]
            assert 'class="cwa-status-pill"' in html_str, c["case_id"]
            if c["cwa_applied"] in ("pending", "not-applied"):
                assert "How the CWA could apply" in html_str, c["case_id"]
                first_analog = c["analogous_cases"][0]
                assert f'href="#cwa-{first_analog}"' in html_str, c["case_id"]

    def test_every_category_represented(self):
        cats = {c["category"] for c in self._cases()}
        assert cats == VALID_CWA_CATEGORIES, f"missing categories: {VALID_CWA_CATEGORIES - cats}"

    def test_sources_well_formed(self):
        for c in self._cases():
            sources = c["sources"]
            assert isinstance(sources, list) and sources, c["case_id"]
            for s in sources:
                assert s.get("title"), f"{c['case_id']} source missing title"
                assert s.get("url", "").startswith("http"), f"{c['case_id']} bad source url"

    def test_year_is_string(self):
        # Year is a string (YYYY or YYYY-YYYY range), not int — flexible for
        # multi-year investigations.
        for c in self._cases():
            assert isinstance(c["year"], str) and c["year"], c["case_id"]
            assert re.match(r"^\d{4}(-\d{4})?$", c["year"]), c["year"]

    def test_takeaways_are_substantive(self):
        # Takeaway is the most important field for users — should be a real sentence.
        for c in self._cases():
            assert len(c["takeaway"]) > 80, f"{c['case_id']} takeaway too short"

    def test_summary_string(self):
        s = _cwa_summary(self._cases())
        assert isinstance(s, str)
        # Should mention at least one category label
        assert any(lbl in s for lbl in CWA_CATEGORY_LABELS.values())

    def test_card_html_renders_for_every_case(self):
        # Smoke test: ensure _build_cwa_case_html returns a non-empty bill-card div
        # for every real case in the dataset (catches HTML escape / missing-key bugs).
        # We compare against an HTML-escaped substring since the renderer escapes
        # respondent text (e.g., apostrophes → &#x27;).
        import html as _html

        for c in self._cases():
            html_str = _build_cwa_case_html(c)
            # Each card carries an id anchor so analog cross-links can target it.
            assert html_str.startswith(
                f'<div class="bill-card" id="cwa-{c["case_id"]}">'
            )
            prefix = c["respondent"].split(",")[0][:20]
            assert _html.escape(prefix) in html_str, (
                f"{c['case_id']}: respondent prefix not rendered"
            )

    def test_year_end_helper(self):
        # The recent-only filter relies on this helper. Cover the common shapes.
        assert _cwa_year_end("2024") == 2024
        assert _cwa_year_end("1991-1997") == 1997
        assert _cwa_year_end("2003-2007") == 2007
        assert _cwa_year_end("") == 0
        assert _cwa_year_end(None) == 0  # type: ignore[arg-type]
        assert _cwa_year_end("not a year") == 0
        # Trailing whitespace shouldn't break it.
        assert _cwa_year_end("2025 ") == 2025

    def test_statute_explainer_includes_primary_sources(self):
        # The explainer must lead with verbatim statute citations from
        # Cornell LII (the canonical free primary source) and EPA's own
        # plain-language summary. If any of these go missing, the section
        # has lost its "primary-source-first" framing.
        md = _cwa_statute_explainer_md()
        # Verbatim CWA Section 101 goal language (the most-cited CWA quote).
        assert "restore and maintain the chemical, physical, and biological" in md
        # The four statutory anchors we want surfaced.
        for usc in ("33 U.S.C. § 1251", "33 U.S.C. § 1319", "33 U.S.C. § 1342", "33 U.S.C. § 1365"):
            assert usc in md, f"missing statute citation {usc}"
        # The civil-penalty $25,000/day base figure, verbatim from § 1319(d).
        assert "$25,000 per day" in md
        # Cornell LII primary-source links and the EPA summary link.
        assert "law.cornell.edu/uscode/text/33/1251" in md
        assert "law.cornell.edu/uscode/text/33/1319" in md
        assert "law.cornell.edu/uscode/text/33/1342" in md
        assert "law.cornell.edu/uscode/text/33/1365" in md
        assert "epa.gov/laws-regulations/summary-clean-water-act" in md

    def test_statute_explainer_covers_required_sections(self):
        # User asked for: what the statute is, what the authority is, why
        # it's deployed. The expander headings must reflect that structure.
        md = _cwa_statute_explainer_md()
        assert "What the statute is" in md
        assert "What authority EPA and DOJ have" in md
        assert "Why investigations get deployed" in md

    def test_xai_memphis_case_present(self):
        # The xAI Colossus / Memphis greywater-plant case is the most prominent
        # AI-data-center water story; it must be in the datacenter category and
        # carry the aquifer-recycling framing.
        cases = {c["case_id"]: c for c in self._cases()}
        assert "xAI-Colossus-Memphis-TN-2026" in cases
        c = cases["xAI-Colossus-Memphis-TN-2026"]
        # Adjacent, not datacenter: the binding federal action is Clean Air Act
        # (gas turbines) and the water piece is a paused voluntary commitment —
        # no CWA enforcement attaches.
        assert c["category"] == "adjacent"
        # The water angle (greywater reuse / aquifer), not just the air-permit suit.
        blob = (c["violation_summary"] + c["takeaway"]).lower()
        assert "aquifer" in blob and "greywater" in blob

    def test_june_2026_research_additions_present(self):
        # Regression guard for the 2026-06-02 research pass: eight verified
        # cases were added (1 datacenter, 4 adjacent, 2 precedent, 1 industrial).
        # Pin the anchor case_ids and their categories so a future reshuffle
        # can't silently drop them.
        cases = {c["case_id"]: c for c in self._cases()}
        expected = {
            "Amazon-NewCarlisle-IN-wetlands-2025": "datacenter",
            "Atlas-ProjectSail-Coweta-GA-2026": "adjacent",
            "Google-Berkeley-SC-Middendorf-aquifer-2019": "adjacent",
            "Rowan-ProjectCinco-Medina-TX-2025": "adjacent",
            "QTS-Fayette-GA-unbilled-water-2026": "adjacent",
            "PortOfTacoma-v-PugetSoundkeeper-9thCir-2024": "precedent",
            "CERF-v-Naples-9thCir-2024": "precedent",
            "FortSmith-AR-sewer-CD-mod-2026": "industrial",
        }
        for cid, cat in expected.items():
            assert cid in cases, f"missing newly-added case {cid}"
            assert cases[cid]["category"] == cat, cid

    def test_june_10_2026_research_additions_present(self):
        # Regression guard for the 2026-06-10 research pass: ten verified
        # cases (4 datacenter, 6 adjacent). Pin the anchors so a reshuffle
        # can't silently drop them.
        cases = {c["case_id"]: c for c in self._cases()}
        expected = {
            "QuantumLoophole-FrederickMD-boring-discharges-2022-2024": ("datacenter", "applied"),
            "AWS-LakeAnnaVA-VPDES-cooling-discharge-2026": ("datacenter", "applied"),
            "Google-FortWayneIN-isolated-wetland-permit-2025": ("datacenter", "not-applied"),
            "Microsoft-MountPleasantWI-wetland-individual-permit-2024": ("datacenter", "pending"),
            "Meta-NewtonCountyGA-well-failures-2018-2025": ("adjacent", "not-applied"),
            "MilwaukeeRiverkeeper-RacineWI-water-records-suit-2025": ("adjacent", "not-applied"),
            "CorpusChristi-SintonTX-EvangelineAquifer-wells-2026": ("adjacent", "not-applied"),
            "Sailfish-HoodCountyTX-ComancheCircle-aquifer-moratorium-2025-2026": ("adjacent", "not-applied"),
            "Charlotte-NC-drought-datacenter-moratorium-2026": ("adjacent", "not-applied"),
            "Microsoft-CaledoniaWI-rezoning-withdrawal-2025": ("adjacent", "not-applied"),
        }
        for cid, (cat, status) in expected.items():
            assert cid in cases, f"missing newly-added case {cid}"
            assert cases[cid]["category"] == cat, cid
            assert cases[cid]["cwa_applied"] == status, cid

    def test_adjacent_cases_disclaim_cwa_enforcement(self):
        # The 'adjacent' category exists precisely because the binding action
        # sits OUTSIDE the CWA. Every adjacent case must say so in its
        # cwa_section so the framing can't drift into implying CWA enforcement.
        adjacent = [c for c in self._cases() if c["category"] == "adjacent"]
        assert len(adjacent) >= 5, "expected the expanded adjacent set"
        for c in adjacent:
            section = c["cwa_section"].lower()
            assert (
                "no cwa" in section
                or "not" in section
                or "outside" in section
                or "paused" in section
                or "clean air act" in section
            ), f"{c['case_id']} adjacent case should disclaim CWA enforcement"

    def test_datacenter_insights_shape_and_invariants(self):
        stats = _cwa_datacenter_insights(self._cases())
        # Keys the renderer depends on.
        for key in ("total", "contractor_permittee", "construction_stormwater"):
            assert key in stats, f"missing insight key {key}"
        dc_count = sum(1 for c in self._cases() if c["category"] == "datacenter")
        assert stats["total"] == dc_count
        # Every sub-count is a sane fraction of the total.
        for key in ("contractor_permittee", "construction_stormwater"):
            assert 0 <= stats[key] <= stats["total"], key
        # Both are real, non-trivial patterns in the current dataset: the
        # permittee shield and construction-stormwater dominance.
        assert stats["contractor_permittee"] >= 3
        assert stats["construction_stormwater"] >= 3

    def test_datacenter_insights_empty(self):
        # Degrades cleanly when there are no datacenter cases.
        stats = _cwa_datacenter_insights([{"category": "precedent"}])
        assert stats["total"] == 0
        assert stats["contractor_permittee"] == 0


# --- Tests for Andy Masley reality-check comparisons ---


class TestMasleyComparisons:
    def test_present_and_sized(self):
        assert len(MASLEY_COMPARISONS) >= 6

    def test_field_shapes(self):
        for c in MASLEY_COMPARISONS:
            assert isinstance(c.get("activity"), str) and c["activity"]
            assert isinstance(c.get("prompts"), int) and c["prompts"] > 0

    def test_known_anchors_match_masley_figures(self):
        # ~2 mL/prompt translations from "The AI water issue is fake"
        by_activity = {c["activity"]: c["prompts"] for c in MASLEY_COMPARISONS}
        assert by_activity.get("Heating a kettle") == 125
        assert by_activity.get("A warm bath") == 5_000

    def test_includes_everyday_and_aggregate_examples(self):
        # Need both the "trivial" appliance/object end and the "aggregate"
        # manufacturing/per-capita end for the panel to make Masley's point.
        activities = [c["activity"].lower() for c in MASLEY_COMPARISONS]
        assert any("kettle" in a or "bath" in a for a in activities)
        assert any(
            "jeans" in a or "t-shirt" in a or "book" in a or "american" in a
            for a in activities
        )


# --- Tests for Company Water Claims panel (mirrored from datacentercommunitybenefits) ---


VALID_DELIVERED_STATUS = {"delivered", "partial", "contested", "shortfall"}


class TestCompanyWaterClaims:
    def _payload(self):
        return load_company_water_claims()

    def _claims(self):
        return self._payload().get("claims", [])

    def test_dataset_loads(self):
        payload = self._payload()
        assert payload.get("last_updated")
        assert len(payload.get("claims", [])) >= 20

    def test_missing_file_returns_empty(self):
        empty = load_company_water_claims("/nonexistent/company_water_claims.json")
        assert empty["claims"] == []
        assert empty["companies"] == {}

    def test_all_claims_are_water_themed(self):
        for c in self._claims():
            # theme field may be absent (snapshot already filtered) — if present must be water
            if "theme" in c:
                assert c["theme"] == "water", c.get("id")

    def test_required_fields_present(self):
        required = {"id", "company_slug", "statement", "source_url", "source_title"}
        for c in self._claims():
            missing = required - set(c)
            assert not missing, f"{c.get('id')} missing {missing}"
            assert c["statement"].strip(), f"{c['id']} has empty statement"

    def test_company_slugs_resolve(self):
        companies = self._payload().get("companies", {})
        for c in self._claims():
            assert c["company_slug"] in companies, c["company_slug"]

    def test_source_urls_are_http(self):
        for c in self._claims():
            assert c["source_url"].startswith("http"), c.get("id")

    def test_delivered_status_valid_when_present(self):
        for c in self._claims():
            d = c.get("delivered")
            if not d:
                continue
            assert d.get("status") in VALID_DELIVERED_STATUS, c.get("id")
            assert d.get("summary"), f"{c['id']} delivered without summary"
            assert d.get("source_url", "").startswith("http"), c.get("id")

    def test_known_hyperscalers_represented(self):
        slugs = {c["company_slug"] for c in self._claims()}
        # The big four hyperscalers should each have at least one claim.
        for required in ("meta", "google", "microsoft", "amazon"):
            assert required in slugs, required
