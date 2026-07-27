#!/usr/bin/env python3
"""Run one monitor sweep and append any candidates to the queue.

    python3 -m scrapers.monitors.run [--dry-run] [--only RECORD_ID]

Prints a summary and exits 0 even when candidates are found — a hit is normal
output, not an error, and a non-zero exit would make a scheduled run look
broken every time it did its job.

Rate limiting follows CLAUDE.md §1: randomized 2-5s delays between requests,
sequential rather than parallel, since these are government pages.
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from datetime import datetime, timezone

import httpx

from scrapers.monitors.base_monitor import MonitorRun, invalid_watches, iter_watches
from scrapers.monitors.clients import make_fetcher
from storage import monitor_queue

USER_AGENT = (
    "datacenter-water-tracker/1.0 (+https://github.com/pranava0x0/datacenterwaterusage) "
    "status monitor; contact via repo issues"
)


def _polite_get(min_delay: float = 2.0, max_delay: float = 5.0):
    """A sequential, rate-limited GET. One host at a time, always delayed."""
    client = httpx.Client(
        timeout=30.0, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    )

    def get(url: str) -> str:
        time.sleep(random.uniform(min_delay, max_delay))
        response = client.get(url)
        response.raise_for_status()
        return response.text

    return get


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report, write nothing")
    parser.add_argument("--only", help="run a single record id")
    args = parser.parse_args(argv)

    problems = invalid_watches()
    if problems:
        print("Aborted — unactionable watches:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1

    watches = list(iter_watches())
    if args.only:
        watches = [w for w in watches if w.record_id == args.only]
        if not watches:
            print(f"No watch for record id {args.only!r}", file=sys.stderr)
            return 1

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    previous = monitor_queue.load_fingerprints()
    run = MonitorRun(fetch=make_fetcher(_polite_get()), previous=previous, now=now)
    candidates = run.run(watches)

    changed = [c for c in candidates if c.previous_fingerprint and c.fingerprint]
    baselines = [c for c in candidates if c.previous_fingerprint is None and c.fingerprint]
    failures = [c for c in candidates if not c.fingerprint]

    print(f"watches: {len(watches)}")
    print(f"  changed:   {len(changed)}")
    print(f"  baselined: {len(baselines)}")
    print(f"  failed:    {len(failures)}")
    for c in changed:
        print(f"  ! {c.record_id} — {c.note or c.summary}")
    for c in failures:
        print(f"  x {c.record_id} — {c.summary}")

    if args.dry_run:
        print("\n(dry run — queue and fingerprints untouched)")
        return 0

    added = monitor_queue.append_candidates([c.as_dict() for c in candidates], now)
    # Only advance the baseline for watches that actually fetched; a failed
    # fetch must stay un-baselined so the next run still reports it.
    fingerprints = dict(previous)
    for c in candidates:
        if c.fingerprint:
            fingerprints[c.record_id] = c.fingerprint
    monitor_queue.save_fingerprints(fingerprints, now)

    print(f"\nqueued {added} new candidate(s) -> {monitor_queue.QUEUE_PATH}")
    if changed:
        print("Review them, then update the curated JSON by hand — monitors propose.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
