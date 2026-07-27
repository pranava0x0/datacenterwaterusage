"""Append-only candidate queue and fingerprint state for the monitors.

Two files, deliberately separate:

* ``data/output/monitor_hits.json`` — the human work queue. Append-only, in the
  same spirit as ``results.csv`` (CLAUDE.md §3): a candidate is never removed by
  a later run, because "we noticed this and it turned out to be nothing" is
  itself a record worth keeping.
* ``data/state/monitor_fingerprints.json`` — per record, the last fingerprint
  seen and a normalized snapshot of the page it came from. Rewritten each run;
  it is a cache, not a history. The snapshot is what lets a candidate show the
  actual diff instead of the top of the page.

Kept out of ``scrapers/`` because it is storage, matching the existing split
between scrapers and ``storage/``.
"""

from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
QUEUE_PATH = BASE_DIR / "data" / "output" / "monitor_hits.json"
FINGERPRINT_PATH = BASE_DIR / "data" / "state" / "monitor_fingerprints.json"
# Snapshots are normalized page text, kept to diff the next run against. They
# live in their own file because they are much larger than the fingerprints and
# churn on every content change — but they ARE committed. An earlier version
# gitignored them on the reasoning that losing them only costs the excerpt;
# that assumed occasional loss, and on a fresh CI runner they are lost every
# single run, so the excerpt would never appear at all. Each is capped so one
# verbose page cannot bloat the repo.
SNAPSHOT_PATH = BASE_DIR / "data" / "state" / "monitor_snapshots.json"

# Per-record cap on stored page text. Enough to locate a change anywhere in a
# status page, bounded so a single verbose watch cannot bloat the repository
# week after week. A truncated snapshot still diffs correctly; at worst the
# excerpt is missing for a change past the cap.
MAX_SNAPSHOT_CHARS = 20_000


def _atomic_write(path: Path, text: str) -> None:
    """Write via a temp file + rename, so an interrupted run leaves either the
    old file or the new one — never a half-written queue."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


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


def load_snapshots(path: Path | None = None) -> dict[str, str]:
    """Last normalized body per record id, for diffing. Empty on first run.

    Losing these degrades gracefully: the next run still detects the change via
    the fingerprint, it just cannot show an excerpt. That is why they are safe
    to keep out of git while the fingerprints are not.
    """
    path = path or SNAPSHOT_PATH
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data.get("snapshots", {}) if isinstance(data, dict) else {}


def save_fingerprints(
    fingerprints: dict[str, str],
    last_run: str,
    path: Path | None = None,
    snapshots: dict[str, str] | None = None,
    snapshot_path: Path | None = None,
) -> None:
    path = path or FINGERPRINT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    capped = {
        k: v[:MAX_SNAPSHOT_CHARS] for k, v in (snapshots or {}).items()
    }
    _atomic_write(
        (snapshot_path or SNAPSHOT_PATH),
        json.dumps({"last_run": last_run, "snapshots": capped}, indent=2, sort_keys=True)
        + "\n",
    )
    _atomic_write(
        path,
        json.dumps(
            {
                "last_run": last_run,
                "fingerprints": fingerprints,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def append_candidates(
    candidates: list[dict], last_run: str, path: Path | None = None
) -> int:
    """Append new candidates to the queue; returns how many were added.

    De-duplicated on the *transition* — ``(record_id, previous, current)`` —
    rather than on the destination fingerprint alone. Keying on the destination
    loses real events: a page that goes A -> B -> back to A produces a
    fingerprint already in the queue, so the revert is dropped while the run
    still advances the baseline, and no later run can ever report it. Failures
    (empty fingerprint) additionally key on their summary, so a 500 followed by
    a 404 are two rows rather than one silently swallowed.
    """
    path = path or QUEUE_PATH
    existing: list[dict] = []
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            existing = payload.get("candidates", [])
        except json.JSONDecodeError:
            # Treating a truncated file as empty and then writing over it
            # destroys the whole audit trail — the opposite of append-only
            # (CLAUDE.md §3). Quarantine it and start a fresh queue, so the
            # damaged bytes survive for recovery and the operator is told.
            quarantine = path.with_suffix(path.suffix + ".corrupt")
            path.replace(quarantine)
            print(
                f"WARNING: {path.name} was unreadable; moved to "
                f"{quarantine.name} and started a new queue. Recover any "
                "untriaged candidates from it by hand."
            )
            existing = []

    def key(c: dict) -> tuple:
        fp = c.get("fingerprint") or ""
        return (
            c.get("record_id"),
            c.get("previous_fingerprint"),
            fp or c.get("summary", ""),
        )

    seen = {key(c) for c in existing}
    fresh = [c for c in candidates if key(c) not in seen]
    if not fresh:
        return 0

    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(
        path,
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
    )
    return len(fresh)
