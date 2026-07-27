"""Append-only candidate queue and fingerprint state for the monitors.

Two files, deliberately separate:

* ``data/output/monitor_hits.json`` — the human work queue. Append-only, in the
  same spirit as ``results.csv`` (CLAUDE.md §3): a candidate is never removed by
  a later run, because "we noticed this and it turned out to be nothing" is
  itself a record worth keeping.
* ``data/state/monitor_fingerprints.json`` — the last fingerprint seen per
  record. Rewritten each run; it is a cache, not a history.

Kept out of ``scrapers/`` because it is storage, matching the existing split
between scrapers and ``storage/``.
"""

from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
QUEUE_PATH = BASE_DIR / "data" / "output" / "monitor_hits.json"
FINGERPRINT_PATH = BASE_DIR / "data" / "state" / "monitor_fingerprints.json"


def load_fingerprints(path: Path | None = None) -> dict[str, str]:
    """Last-seen fingerprint per record id; empty on first run.

    ``path`` resolves at call time rather than binding the module constant as a
    default, so a test (or a caller with its own data root) can redirect these
    writes. Binding it as a default made the constant unpatchable and let a
    test write to the real state file.
    """
    path = path or FINGERPRINT_PATH
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # A truncated cache must not stop a sweep — the cost is one round of
        # "first observation" candidates, which are labelled as such.
        return {}
    return data.get("fingerprints", {}) if isinstance(data, dict) else {}


def save_fingerprints(
    fingerprints: dict[str, str], last_run: str, path: Path | None = None
) -> None:
    path = path or FINGERPRINT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"last_run": last_run, "fingerprints": fingerprints},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def append_candidates(
    candidates: list[dict], last_run: str, path: Path | None = None
) -> int:
    """Append new candidates to the queue; returns how many were added.

    De-duplicated on ``(record_id, fingerprint)`` so re-running before a
    curator has triaged the queue does not pile up copies of the same finding.
    """
    path = path or QUEUE_PATH
    existing: list[dict] = []
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            existing = payload.get("candidates", [])
        except json.JSONDecodeError:
            existing = []

    seen = {(c.get("record_id"), c.get("fingerprint")) for c in existing}
    fresh = [
        c for c in candidates if (c.get("record_id"), c.get("fingerprint")) not in seen
    ]
    if not fresh:
        return 0

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "last_run": last_run,
                "note": (
                    "Monitor candidates awaiting human adjudication. Monitors "
                    "propose; a curator decides what reaches a dataset. "
                    "Append-only — triaged entries stay for the audit trail."
                ),
                "candidates": existing + fresh,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return len(fresh)
