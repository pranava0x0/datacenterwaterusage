"""Shared apply/validate logic for the doctrine-family migration batches.

Spec C1/C2 lands the authority families in batches, because a family may only
enter ``WATER_STATUTE_ORDER`` once its readings *and* its anchor cases exist —
the schema tests require both, and a family listed early would render a filter
value that matches nothing. Each batch script supplies data; this supplies the
checks and the write, so batch 3 does not re-implement batch 2's guard rails.

Not a scraper and not imported by the app — a build-time curation tool.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
AUTHORITIES_PATH = BASE_DIR / "data" / "reference" / "water_authorities.json"
CASES_PATH = BASE_DIR / "data" / "reference" / "cwa_investigations.json"


def apply_batch(
    new_statutes: dict,
    new_readings: list[dict],
    new_cases: list[dict],
    *,
    last_updated: str,
    authority_additions: dict[str, list[str]] | None = None,
    dry_run: bool = False,
) -> int:
    """Validate and append one doctrine batch. Returns a process exit code.

    ``authority_additions`` maps an EXISTING case_id to reading_ids to add to
    its ``authorities`` list. Some doctrine families are best anchored on a
    matter the tracker already follows rather than on a new historical case —
    Arizona's assured-water-supply regime is better illustrated by the live
    Tucson fight than by a 1980s precedent — and a family only counts as
    represented when some case's ``authorities`` names one of its readings.

    Idempotent: a family, reading, case or authority link that is already
    present is skipped, so re-running a shipped batch is a no-op.
    """
    sys.path.insert(0, str(BASE_DIR))
    from refdata.taxonomies import (
        AUTHORITY_KIND_LABELS,
        CWA_CASE_TYPE_LABELS,
        WATER_STATUTE_COLORS,
        WATER_STATUTE_ORDER,
    )

    authorities = json.loads(AUTHORITIES_PATH.read_text(encoding="utf-8"))
    cases_payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    problems: list[str] = []

    for code, meta in new_statutes.items():
        if meta.get("kind") not in AUTHORITY_KIND_LABELS:
            problems.append(f"{code}: bad kind {meta.get('kind')}")
        if code not in WATER_STATUTE_ORDER:
            problems.append(f"{code}: add it to WATER_STATUTE_ORDER in taxonomies.py")
        if code not in WATER_STATUTE_COLORS:
            problems.append(f"{code}: no colour in WATER_STATUTE_COLORS")

    # Back-fill `kind` on any pre-existing family that lacks one. Every family
    # needs it so the accordion can say which register the reader is in.
    backfilled = [
        code
        for code, meta in authorities["statutes"].items()
        if code not in new_statutes and "kind" not in meta
    ]
    for code in backfilled:
        authorities["statutes"][code]["kind"] = "federal-statute"

    added_statutes = [c for c in new_statutes if c not in authorities["statutes"]]
    authorities["statutes"].update(new_statutes)

    existing_readings = {r["reading_id"] for r in authorities["readings"]}
    added_readings = []
    for reading in new_readings:
        if reading["reading_id"] in existing_readings:
            continue
        if reading["statute"] not in authorities["statutes"]:
            problems.append(f"{reading['reading_id']}: unknown family {reading['statute']}")
        authorities["readings"].append(reading)
        added_readings.append(reading["reading_id"])

    existing_cases = {c["case_id"] for c in cases_payload["cases"]}
    added_cases = []
    for case in new_cases:
        if case["case_id"] in existing_cases:
            continue
        if case["case_type"] not in CWA_CASE_TYPE_LABELS:
            problems.append(f"{case['case_id']}: bad case_type {case['case_type']}")
        if len(case.get("sources", [])) < 2:
            problems.append(f"{case['case_id']}: needs at least 2 sources")
        # A doctrine anchor earns its place by naming the tracked fact patterns
        # it reaches; without that it is a history entry, not a tool.
        if not case.get("analogous_cases"):
            problems.append(f"{case['case_id']}: needs analogous_cases")
        cases_payload["cases"].append(case)
        added_cases.append(case["case_id"])

    # Link new readings onto cases the tracker already follows.
    by_case_id = {c["case_id"]: c for c in cases_payload["cases"]}
    all_reading_ids = {r["reading_id"] for r in authorities["readings"]}
    linked = []
    for case_id, reading_ids in (authority_additions or {}).items():
        case = by_case_id.get(case_id)
        if case is None:
            problems.append(f"authority_additions names an absent case: {case_id}")
            continue
        for reading_id in reading_ids:
            if reading_id not in all_reading_ids:
                problems.append(f"{case_id}: unknown reading {reading_id}")
                continue
            if reading_id not in case.setdefault("authorities", []):
                case["authorities"].append(reading_id)
                linked.append(f"{case_id} += {reading_id}")

    all_case_ids = {c["case_id"] for c in cases_payload["cases"]}
    for reading in new_readings:
        for cid in reading["example_case_ids"]:
            if cid not in all_case_ids:
                problems.append(f"{reading['reading_id']}: example case {cid} not found")
    for case in new_cases:
        for cid in case.get("analogous_cases", []):
            if cid not in all_case_ids:
                problems.append(f"{case['case_id']}: unknown analog {cid}")

    print(f"families added:   {len(added_statutes)}  {added_statutes}")
    if backfilled:
        print(f"kind back-filled: {len(backfilled)}  {backfilled}")
    print(f"readings added:   {len(added_readings)}")
    for r in added_readings:
        print(f"  + {r}")
    print(f"cases added:      {len(added_cases)}")
    for c in added_cases:
        print(f"  + {c}")
    if linked:
        print(f"authorities linked onto existing cases: {len(linked)}")
        for line in linked:
            print(f"  ~ {line}")
    print(
        f"totals -> families {len(authorities['statutes'])}, "
        f"readings {len(authorities['readings'])}, cases {len(cases_payload['cases'])}"
    )

    if problems:
        print("\nAborted:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    if dry_run:
        print("\n(dry run — nothing written)")
        return 0

    authorities["last_updated"] = last_updated
    cases_payload["last_updated"] = last_updated
    AUTHORITIES_PATH.write_text(
        json.dumps(authorities, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    CASES_PATH.write_text(
        json.dumps(cases_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("\nWrote water_authorities.json and cwa_investigations.json")
    return 0
