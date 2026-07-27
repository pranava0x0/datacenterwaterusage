"""Tests for the status-monitor pipeline (plan Spec B3).

No network. The fetch layer is injected, so every case here exercises the
diffing and queueing logic against fixtures — which is the part that can be
wrong in a way nobody notices, since a monitor that never fires and a monitor
that always fires both look like "no news".
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from scrapers.monitors.base_monitor import (
    MONITOR_KINDS,
    MonitorRun,
    Watch,
    first_difference,
    fingerprint,
    invalid_watches,
    iter_watches,
    normalize,
)
from storage import monitor_queue

W = Watch(record_id="rec-1", dataset="legislation", kind="url-watch", key="https://x/1")


def _run(pages: dict[str, str], previous=None, watches=(W,)):
    return MonitorRun(
        fetch=lambda w: pages[w.key],
        previous=dict(previous or {}),
        now="2026-07-26T00:00:00Z",
    ).run(watches)


class TestNormalization:
    def test_ignores_render_timestamps_and_session_tokens(self):
        """The failure that makes a monitor useless: a page embeds a clock or a
        CSRF token, every run reports a change, and the queue gets ignored."""
        a = "<html><body>Permit status: draft <span>3:04 pm</span> "
        a += "<input value='a1b2c3d4e5f60718'></body></html>"
        b = "<html><body>Permit status: draft <span>9:47 am</span> "
        b += "<input value='ffee0011223344556'></body></html>"
        assert fingerprint(a) == fingerprint(b)

    def test_ignores_markup_and_whitespace_churn(self):
        a = "<div><p>Report  due   October 1</p></div>"
        b = "<section>\n  <p>Report due October 1</p>\n</section>"
        assert fingerprint(a) == fingerprint(b)

    def test_detects_a_real_status_change(self):
        a = "<p>Permit status: <b>draft</b></p>"
        b = "<p>Permit status: <b>final</b></p>"
        assert fingerprint(a) != fingerprint(b)

    def test_script_and_style_are_stripped(self):
        a = "<p>Text</p><script>var t=1</script>"
        b = "<p>Text</p><script>var t=2</script><style>p{color:red}</style>"
        assert fingerprint(a) == fingerprint(b)

    def test_normalize_leaves_readable_text(self):
        assert normalize("<h1>Draft</h1><p>Due Oct 1</p>") == "Draft Due Oct 1"


class TestDiffing:
    def test_first_observation_is_labelled_not_a_change(self):
        """A cold start would otherwise report every watched page as changed,
        which teaches a curator to ignore the first real hit too."""
        out = _run({"https://x/1": "<p>draft</p>"})
        assert len(out) == 1
        assert "first observation" in out[0].summary
        assert out[0].previous_fingerprint is None

    def test_unchanged_page_emits_nothing(self):
        page = "<p>draft</p>"
        out = _run({"https://x/1": page}, {"rec-1": fingerprint(page)})
        assert out == []

    def test_change_emits_a_candidate_with_context(self):
        out = _run(
            {"https://x/1": "<p>Permit status: final</p>"},
            {"rec-1": fingerprint("<p>Permit status: draft</p>")},
        )
        assert len(out) == 1
        assert out[0].summary == "watched page changed since last run"
        # A bare "it changed" costs the curator the click the monitor saved.
        assert "final" in out[0].excerpt

    def test_fetch_failure_is_surfaced_not_swallowed(self):
        """An unreachable page usually means it moved, which is exactly the
        kind of staleness the monitors exist to catch."""

        def boom(_w):
            raise ConnectionError("host unreachable")

        out = MonitorRun(fetch=boom, previous={}, now="t").run([W])
        assert len(out) == 1
        assert "fetch failed" in out[0].summary
        assert out[0].fingerprint == ""

    def test_one_bad_page_does_not_abort_the_sweep(self):
        good = Watch(record_id="rec-2", dataset="legislation", kind="url-watch", key="https://x/2")

        def fetch(w):
            if w.key.endswith("/1"):
                raise TimeoutError("slow")
            return "<p>ok</p>"

        out = MonitorRun(fetch=fetch, previous={}, now="t").run([W, good])
        assert {c.record_id for c in out} == {"rec-1", "rec-2"}

    def test_first_difference_returns_empty_when_identical(self):
        assert first_difference("<p>same</p>", "<p>same</p>") == ""


class TestWatchListDerivation:
    def test_watches_come_from_the_datasets(self):
        """Single source of truth: the watch list is whatever carries a
        `monitor` block, so it cannot drift from the records it watches."""
        watches = list(iter_watches())
        assert len(watches) >= 5
        assert {w.record_id for w in watches} <= set(_all_record_ids())

    def test_every_watch_is_actionable(self):
        assert invalid_watches() == []

    def test_kinds_are_from_the_closed_set(self):
        for w in iter_watches():
            assert w.kind in MONITOR_KINDS

    def test_each_watch_explains_what_it_is_waiting_for(self):
        """A monitor with no note is a page that changed for reasons nobody
        recorded — the curator has to re-derive why it was watched."""
        for w in iter_watches():
            assert len(w.note) > 20, w.record_id

    def test_the_known_pending_decisions_are_watched(self):
        watched = {w.record_id for w in iter_watches()}
        for expected in (
            "OH EPA OHD000001 (draft general permit)",
            "VA DEQ waterworks data-center reporting regulations",
            "NY EO 62",
        ):
            assert expected in watched, expected


def _all_record_ids():
    from refdata.loaders import (
        load_cwa_investigations,
        load_dc_water_conflicts,
        load_legislation,
    )

    return (
        [b["bill_id"] for b in load_legislation()["bills"]]
        + [c["case_id"] for c in load_cwa_investigations()["cases"]]
        + [s["site_id"] for s in load_dc_water_conflicts()["sites"]]
    )


class TestQueue:
    def test_append_is_additive_and_deduplicated(self, tmp_path):
        path = tmp_path / "hits.json"
        c = {"record_id": "r", "fingerprint": "abc", "summary": "changed"}
        assert monitor_queue.append_candidates([c], "t1", path) == 1
        # Re-running before triage must not pile up copies.
        assert monitor_queue.append_candidates([c], "t2", path) == 0
        assert monitor_queue.append_candidates(
            [{"record_id": "r", "fingerprint": "def", "summary": "changed again"}],
            "t3",
            path,
        ) == 1
        payload = json.loads(path.read_text())
        assert len(payload["candidates"]) == 2

    def test_triaged_entries_are_never_dropped(self, tmp_path):
        """Append-only per CLAUDE.md §3: 'we looked and it was nothing' is a
        record worth keeping."""
        path = tmp_path / "hits.json"
        monitor_queue.append_candidates(
            [{"record_id": "old", "fingerprint": "1"}], "t1", path
        )
        monitor_queue.append_candidates(
            [{"record_id": "new", "fingerprint": "2"}], "t2", path
        )
        ids = {c["record_id"] for c in json.loads(path.read_text())["candidates"]}
        assert ids == {"old", "new"}

    def test_fingerprint_cache_roundtrips(self, tmp_path):
        path = tmp_path / "fp.json"
        assert monitor_queue.load_fingerprints(path) == {}
        monitor_queue.save_fingerprints({"r": "abc"}, "t1", path)
        assert monitor_queue.load_fingerprints(path) == {"r": "abc"}

    def test_corrupt_cache_degrades_to_a_cold_start(self, tmp_path):
        """A truncated cache must cost one round of labelled 'first
        observation' candidates, not a failed sweep."""
        path = tmp_path / "fp.json"
        path.write_text("{not json")
        assert monitor_queue.load_fingerprints(path) == {}

    def test_corrupt_queue_does_not_lose_the_new_candidate(self, tmp_path):
        path = tmp_path / "hits.json"
        path.write_text("{truncated")
        assert monitor_queue.append_candidates(
            [{"record_id": "r", "fingerprint": "1"}], "t", path
        ) == 1


class TestNoAutomaticWrites:
    def test_monitors_never_import_a_dataset_writer(self):
        """The curated layer's value is that a person checked it. A monitor
        that could write to it would trade that away silently."""
        import pathlib

        import scrapers.monitors.base_monitor as bm

        source = pathlib.Path(bm.__file__).read_text()
        for forbidden in ("json.dump", "write_text", "open(", "w+"):
            assert forbidden not in source, forbidden
