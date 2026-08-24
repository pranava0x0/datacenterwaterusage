"""The upsert half of the datacentercommunitybenefits mirror (Spec F).

Two datasets in this tracker mirror the Data Center Community Benefits
project: `company_water_claims.json` (its `docs/data/claims.json`, filtered to
`theme == "water"`) and `local_actions.json` (its `docs/data/moratoriums.json`,
filtered to county/city/town scope). REFRESH.md documents the whole procedure;
this module is the mechanical half of it — the merge — so that the part with
no judgment in it is pinned by tests instead of redone by hand each time.

The judgment half stays out on purpose. Mapping a source moratorium record to
this schema means deciding whether a "permanent ban" the source still calls a
moratorium is an ordinance, whether an "enacted" pause whose term has lapsed is
expired or superseded, and whether the record's water reason describes a real
impact or is just a tag. Those calls are re-checked against primary sources,
which is why they are made by a person and then protected here.

**Two different merge rules, because the two datasets have different risks.**

Actions are a *pure upsert on action_id*: the incoming record wins, so a
correction upstream propagates. Corrections made HERE — the five documented in
`local_actions.json`'s own note — are therefore re-applied after a sync that
overwrites them, and the report this module returns names every field it
changed so nothing is silently lost.

Claims are *append-only, plus a `delivered` refresh*: a claim's `statement` is
a verbatim first-party quote and this project's `delivered` block is often a
newer adjudication than the source's. So a claim id that already exists keeps
every mirrored field it has, and only takes a `delivered` block that is
strictly newer by `assessed_at`.

Usage (both inputs already mapped to the target schema — see REFRESH.md):

    python3 scripts/sync_community_benefits.py --actions mapped_actions.json
    python3 scripts/sync_community_benefits.py --claims water_claims.json --write
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LOCAL_ACTIONS_PATH = BASE / "data" / "reference" / "local_actions.json"
CLAIMS_PATH = BASE / "data" / "reference" / "company_water_claims.json"

SOURCE_REPO = "pranava0x0/datacentercommunitybenefits"
RAW_BASE = f"https://raw.githubusercontent.com/{SOURCE_REPO}/main/docs/data"
CLAIMS_URL = f"{RAW_BASE}/claims.json"
MORATORIUMS_URL = f"{RAW_BASE}/moratoriums.json"

def upsert_actions(
    existing: list[dict], incoming: list[dict]
) -> tuple[list[dict], dict]:
    """Merge county/city actions by ``action_id``. Pure; inputs unmodified.

    Returns ``(actions, report)``. Existing order is preserved and new records
    append, so a re-sync of an unchanged source is a no-op — that is what makes
    the mirror safe to run repeatedly.
    """
    merged = [dict(a) for a in existing]
    by_id = {a.get("action_id"): i for i, a in enumerate(merged)}
    report: dict = {"added": [], "updated": [], "unchanged": 0}

    for record in incoming:
        action_id = record.get("action_id")
        if not action_id:
            continue
        if action_id not in by_id:
            by_id[action_id] = len(merged)
            merged.append(dict(record))
            report["added"].append(action_id)
            continue
        current = merged[by_id[action_id]]
        changed = {
            k: (current.get(k), v) for k, v in record.items() if current.get(k) != v
        }
        if not changed:
            report["unchanged"] += 1
            continue
        current.update(record)
        report["updated"].append({"action_id": action_id, "fields": sorted(changed)})
    return merged, report


def water_claims(payload: dict | list) -> list[dict]:
    """The ``theme == "water"`` slice of a source claims payload."""
    claims = payload.get("claims", []) if isinstance(payload, dict) else payload
    return [c for c in claims if c.get("theme") == "water"]


def upsert_claims(
    existing: list[dict], incoming: list[dict]
) -> tuple[list[dict], dict]:
    """Append new water claims; refresh only a strictly newer ``delivered``.

    Never edits an existing claim's verbatim text. ``statement``,
    ``source_url``, ``source_title`` and ``captured_at`` are what the tracker
    captured and dated, and a source that has since reworded a quote does not
    get to rewrite them. Returns ``(claims, report)``; inputs unmodified.
    """
    merged = [dict(c) for c in existing]
    by_id = {c.get("id"): i for i, c in enumerate(merged)}
    report: dict = {"added": [], "delivered_updated": [], "unchanged": 0}

    for record in incoming:
        claim_id = record.get("id")
        if not claim_id:
            continue
        if claim_id not in by_id:
            by_id[claim_id] = len(merged)
            merged.append(dict(record))
            report["added"].append(claim_id)
            continue
        current = merged[by_id[claim_id]]
        theirs = record.get("delivered") or {}
        ours = current.get("delivered") or {}
        if theirs and theirs.get("assessed_at", "") > ours.get("assessed_at", ""):
            current["delivered"] = dict(theirs)
            report["delivered_updated"].append(claim_id)
        else:
            report["unchanged"] += 1
    return merged, report


def _load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _save(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--actions",
        type=Path,
        help="JSON file of records already mapped to the local_actions schema",
    )
    parser.add_argument(
        "--claims",
        type=Path,
        help="JSON file of source claims (filtered to theme=water on load)",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the merged datasets; without it the run only reports",
    )
    args = parser.parse_args()
    if not args.actions and not args.claims:
        parser.error("give --actions, --claims, or both")

    if args.actions:
        payload = _load(LOCAL_ACTIONS_PATH)
        incoming = _load(args.actions)
        incoming = incoming.get("actions", incoming) if isinstance(incoming, dict) else incoming
        merged, report = upsert_actions(payload.get("actions", []), incoming)
        print(
            f"actions: +{len(report['added'])} new, {len(report['updated'])} updated, "
            f"{report['unchanged']} unchanged"
        )
        for entry in report["updated"]:
            print(f"  ! {entry['action_id']} — {', '.join(entry['fields'])}")
        if report["updated"]:
            print(
                "  Re-check the corrections listed in local_actions.json's note "
                "before accepting these."
            )
        if args.write:
            payload["actions"] = merged
            _save(LOCAL_ACTIONS_PATH, payload)

    if args.claims:
        payload = _load(CLAIMS_PATH)
        merged, report = upsert_claims(
            payload.get("claims", []), water_claims(_load(args.claims))
        )
        print(
            f"claims: +{len(report['added'])} new, "
            f"{len(report['delivered_updated'])} delivered refreshed, "
            f"{report['unchanged']} unchanged"
        )
        for claim_id in report["added"]:
            print(f"  + {claim_id} — needs a claim_type before the suite passes")
        if args.write:
            payload["claims"] = merged
            _save(CLAIMS_PATH, payload)

    if not args.write:
        print("Dry run — nothing written. Re-run with --write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
