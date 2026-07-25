#!/usr/bin/env python3
"""One-off migration: give every legislation.json entry an ``instrument_type``.

``legislation.json`` has quietly held non-bills since early 2026 — the Ohio EPA
draft general permit is an agency rulemaking, the Loudoun ZOAM and Denver
CB 26-0431 are local ordinances, UT EO 2026-03 is an executive order. Nothing
in the schema said so, so the tab implied everything was a bill and the federal
executive layer had no obvious place to land (plan gap G1).

Everything not named below is a bill, which is the honest default: the
overwhelming majority are, and a wrong guess on a named entry is a data error a
reviewer can see, whereas a wrong guess spread across 50 entries is not.

Run: ``python3 scripts/annotate_instrument_types.py [--dry-run]``
Idempotent.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

LEGISLATION_PATH = BASE_DIR / "data" / "reference" / "legislation.json"

# bill_id -> instrument_type, for every entry that is NOT a bill.
NON_BILL_TYPES = {
    "OH EPA OHD000001 (draft general permit)": "agency-rule",
    "Loudoun County ZOAM 2025": "local-ordinance",
    "Denver CB 26-0431": "local-ordinance",
    "UT EO 2026-03": "executive-order",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from refdata.taxonomies import INSTRUMENT_TYPE_LABELS

    payload = json.loads(LEGISLATION_PATH.read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    changed = 0

    for entry in payload["bills"]:
        bill_id = entry.get("bill_id", "")
        itype = NON_BILL_TYPES.get(bill_id, "bill")
        assert itype in INSTRUMENT_TYPE_LABELS, itype
        if entry.get("instrument_type") != itype:
            changed += 1
        entry["instrument_type"] = itype
        counts[itype] = counts.get(itype, 0) + 1

    unknown = set(NON_BILL_TYPES) - {e.get("bill_id") for e in payload["bills"]}
    if unknown:
        print(f"Aborted: NON_BILL_TYPES names absent entries: {unknown}", file=sys.stderr)
        return 1

    print(f"entries annotated: {changed} of {len(payload['bills'])}")
    for itype, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {itype:<20} {n}")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return 0

    LEGISLATION_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("\nWrote legislation.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
