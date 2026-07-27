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
        """The excerpt must be the DIFF, not the head of the page.

        The earlier version of this test used a 20-character fixture, so the
        top of the page and the changed region were the same substring — it
        passed while the code returned body[0:240] regardless. The boilerplate
        prefix here makes head != diff, so only a real diff satisfies it.
        """
        boiler = "<p>Status: introduced. " + ("Nothing to see here. " * 40) + "</p>"
        old_body = boiler + "<b>Nothing new here</b>"
        new_body = boiler + "<b>PASSED SENATE 2026-07-20</b>"
        out = MonitorRun(
            fetch=lambda w: new_body,
            previous={"rec-1": fingerprint(old_body)},
            snapshots={"rec-1": normalize(old_body)},
            now="t",
        ).run([W])
        assert len(out) == 1
        assert out[0].summary == "watched page changed since last run"
        assert "PASSED SENATE" in out[0].excerpt
        assert "Status: introduced" not in out[0].excerpt

    def test_excerpt_is_empty_rather_than_misleading_without_a_snapshot(self):
        """A first run has nothing to diff against. An empty excerpt is honest;
        the head of the page labelled as the change is not."""
        long_body = "<p>" + ("filler " * 100) + "CHANGED</p>"
        out = MonitorRun(
            fetch=lambda w: long_body,
            previous={"rec-1": "stale-fp"},
            snapshots={},
            now="t",
        ).run([W])
        assert out[0].excerpt == ""

    def test_snapshots_are_updated_for_the_next_run(self):
        run = MonitorRun(fetch=lambda w: "<p>v2</p>", previous={}, snapshots={}, now="t")
        run.run([W])
        assert run.snapshots["rec-1"] == "v2"

    @pytest.mark.parametrize(
        "label,body",
        [
            ("unterminated openers", "<script>" * 40000),
            ("unterminated comments", "<!--" * 30000),
            ("large well-formed", "<div><script>var x=1</script><p>hi</p></div>" * 40000),
        ],
    )
    def test_normalize_stays_linear_on_hostile_input(self, label, body):
        """A lazy DOTALL `<script>.*?</script>` rescans to end-of-string at every
        unterminated opener — 40k of them took ~56s, and input is arbitrary
        third-party HTML. Block stripping is a linear str.find scan now."""
        import time

        t0 = time.monotonic()
        normalize(body)
        assert time.monotonic() - t0 < 1.0, label

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

    def test_a_reverted_page_is_not_silently_dropped(self, tmp_path):
        """A -> B -> A. Keying dedupe on the destination fingerprint alone made
        the revert collide with the original baseline, so it was dropped
        permanently while the run still advanced the stored fingerprint."""
        path = tmp_path / "hits.json"
        assert monitor_queue.append_candidates(
            [{"record_id": "r", "previous_fingerprint": None, "fingerprint": "A"}],
            "t1", path,
        ) == 1
        assert monitor_queue.append_candidates(
            [{"record_id": "r", "previous_fingerprint": "A", "fingerprint": "B"}],
            "t2", path,
        ) == 1
        assert monitor_queue.append_candidates(
            [{"record_id": "r", "previous_fingerprint": "B", "fingerprint": "A"}],
            "t3", path,
        ) == 1, "the revert back to A must be queued"

    def test_distinct_failures_are_distinct_rows(self, tmp_path):
        """Every failure has an empty fingerprint, so keying on it alone made a
        500 followed by a 404 dedupe into one row — a dying watch going quiet."""
        path = tmp_path / "hits.json"
        base = {"record_id": "r", "previous_fingerprint": None, "fingerprint": ""}
        assert monitor_queue.append_candidates(
            [dict(base, summary="fetch failed: 500")], "t1", path
        ) == 1
        assert monitor_queue.append_candidates(
            [dict(base, summary="fetch failed: 404")], "t2", path
        ) == 1
        assert monitor_queue.append_candidates(
            [dict(base, summary="fetch failed: 500")], "t3", path
        ) == 0

    def test_snapshots_roundtrip(self, tmp_path):
        path = tmp_path / "fp.json"
        assert monitor_queue.load_snapshots(path) == {}
        monitor_queue.save_fingerprints({"r": "1"}, "t", path, snapshots={"r": "body"})
        assert monitor_queue.load_snapshots(path) == {"r": "body"}
        assert monitor_queue.load_fingerprints(path) == {"r": "1"}

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


class TestPathsAreRedirectable:
    """Regression guard. These paths were module-constant DEFAULT ARGUMENTS,
    which bind at import — monkeypatching the constant did nothing and a test
    wrote to the real data/state file. Resolving at call time fixes it."""

    def test_queue_and_cache_honour_a_patched_constant(self, tmp_path, monkeypatch):
        monkeypatch.setattr(monitor_queue, "QUEUE_PATH", tmp_path / "q.json")
        monkeypatch.setattr(monitor_queue, "FINGERPRINT_PATH", tmp_path / "fp.json")
        monitor_queue.append_candidates([{"record_id": "r", "fingerprint": "1"}], "t")
        monitor_queue.save_fingerprints({"r": "1"}, "t")
        assert (tmp_path / "q.json").exists()
        assert (tmp_path / "fp.json").exists()

    def test_real_paths_are_gitignored(self):
        """Both are runtime artifacts of an ops sweep, not curated data."""
        import pathlib

        ignore = (pathlib.Path(monitor_queue.BASE_DIR) / ".gitignore").read_text()
        assert "monitor_hits.json" in ignore
        assert "monitor_fingerprints.json" in ignore


class TestNoAutomaticWrites:
    def test_monitors_never_import_a_dataset_writer(self):
        """The curated layer's value is that a person checked it. A monitor
        that could write to it would trade that away silently."""
        import pathlib

        import scrapers.monitors.base_monitor as bm

        source = pathlib.Path(bm.__file__).read_text()
        for forbidden in ("json.dump", "write_text", "open(", "w+"):
            assert forbidden not in source, forbidden


class TestClients:
    """The three fetchers. No network: `get` is a stub throughout."""

    @staticmethod
    def _fetch(pages, kind, key):
        from scrapers.monitors.clients import make_fetcher

        return make_fetcher(lambda url: pages[url])(
            Watch(record_id="r", dataset="legislation", kind=kind, key=key)
        )

    def test_url_watch_passes_the_page_through(self):
        out = self._fetch({"https://x/1": "<p>hi</p>"}, "url-watch", "https://x/1")
        assert out == "<p>hi</p>"

    def test_legiscan_canonicalization_ignores_churn(self):
        """The full payload carries vote rosters and text hashes that move
        independently of status; fingerprinting them all would fire every run."""
        from scrapers.monitors.clients import canonical_legiscan

        base = {"bill": {"status": 4, "status_date": "2026-07-01",
                         "last_action": "Passed", "last_action_date": "2026-07-01",
                         "bill_number": "S10642"}}
        noisy = {"bill": dict(base["bill"], votes=[1, 2, 3], texts=["hash-a"],
                              sponsors=[{"name": "X"}])}
        assert canonical_legiscan(base) == canonical_legiscan(noisy)

    def test_legiscan_detects_a_real_status_move(self):
        from scrapers.monitors.clients import canonical_legiscan

        a = {"bill": {"status": 4, "last_action": "Passed Senate"}}
        b = {"bill": {"status": 5, "last_action": "Vetoed"}}
        assert canonical_legiscan(a) != canonical_legiscan(b)

    def test_federal_register_is_order_independent(self):
        from scrapers.monitors.clients import canonical_federal_register

        d1 = {"document_number": "1", "title": "A", "publication_date": "2026-01-01"}
        d2 = {"document_number": "2", "title": "B", "publication_date": "2026-02-01"}
        assert canonical_federal_register({"results": [d1, d2]}) == (
            canonical_federal_register({"results": [d2, d1]})
        )

    def test_federal_register_detects_a_new_document(self):
        from scrapers.monitors.clients import canonical_federal_register

        d1 = {"document_number": "1", "title": "A", "publication_date": "2026-01-01"}
        d2 = {"document_number": "2", "title": "B", "publication_date": "2026-02-01"}
        assert canonical_federal_register({"results": [d1]}) != (
            canonical_federal_register({"results": [d1, d2]})
        )

    def test_missing_credential_is_raised_not_swallowed(self, monkeypatch):
        """A watch that silently stops running looks exactly like one
        reporting no change — the failure the monitors exist to prevent."""
        from scrapers.monitors.clients import MissingCredential

        monkeypatch.delenv("LEGISCAN_API_KEY", raising=False)
        with pytest.raises(MissingCredential):
            self._fetch({}, "legiscan", "NY S10642")

    def test_missing_credential_surfaces_as_a_candidate(self, monkeypatch):
        """MonitorRun catches fetch errors, so the sweep must still report the
        unrun watch rather than dropping it."""
        from scrapers.monitors.clients import make_fetcher

        monkeypatch.delenv("LEGISCAN_API_KEY", raising=False)
        w = Watch(record_id="r", dataset="legislation", kind="legiscan", key="NY S1")
        out = MonitorRun(fetch=make_fetcher(lambda u: ""), previous={}, now="t").run([w])
        assert len(out) == 1 and "fetch failed" in out[0].summary

    def test_api_key_never_reaches_the_candidate_or_the_queue(self, monkeypatch):
        """httpx puts the request URL in its error text, MonitorRun formats that
        into a Candidate, and the Candidate is printed and written to disk. A
        single 403 from LegiScan would otherwise burn the key into logs."""
        import httpx

        from scrapers.monitors.clients import make_fetcher

        monkeypatch.setenv("LEGISCAN_API_KEY", "SUPERSECRET123")

        def get(url):
            raise httpx.HTTPStatusError(
                f"Client error '403 Forbidden' for url '{url}'",
                request=None,
                response=None,
            )

        w = Watch(record_id="r", dataset="legislation", kind="legiscan", key="NY S1")
        out = MonitorRun(fetch=make_fetcher(get), previous={}, now="t").run([w])
        blob = json.dumps(out[0].as_dict())
        assert "SUPERSECRET123" not in blob
        assert "***" in blob

    def test_unknown_kind_is_rejected(self):
        with pytest.raises(ValueError):
            self._fetch({}, "carrier-pigeon", "x")


class TestRunner:
    def test_dry_run_writes_nothing(self, tmp_path, monkeypatch, capsys):
        from scrapers.monitors import run as runner

        monkeypatch.setattr(runner.monitor_queue, "QUEUE_PATH", tmp_path / "q.json")
        monkeypatch.setattr(runner, "_polite_get", lambda *a, **k: (lambda url: "<p>x</p>"))
        assert runner.main(["--dry-run"]) == 0
        assert not (tmp_path / "q.json").exists()
        assert "dry run" in capsys.readouterr().out

    def test_failed_fetch_does_not_advance_the_baseline(self, tmp_path, monkeypatch):
        """Baselining a watch that never fetched would make the next run report
        no change — the failure would silently heal itself."""
        from scrapers.monitors import run as runner

        q, fp = tmp_path / "q.json", tmp_path / "fp.json"
        monkeypatch.setattr(runner.monitor_queue, "QUEUE_PATH", q)
        monkeypatch.setattr(runner.monitor_queue, "FINGERPRINT_PATH", fp)

        def boom(url):
            raise ConnectionError("down")

        monkeypatch.setattr(runner, "_polite_get", lambda *a, **k: boom)
        assert runner.main([]) == 0
        saved = json.loads(fp.read_text())["fingerprints"]
        assert saved == {}, "a failed fetch must not be baselined"

    def test_unknown_only_target_exits_nonzero(self, monkeypatch):
        from scrapers.monitors import run as runner

        monkeypatch.setattr(runner, "_polite_get", lambda *a, **k: (lambda url: ""))
        assert runner.main(["--only", "no-such-record"]) == 1
