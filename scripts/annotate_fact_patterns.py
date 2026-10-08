"""One-off migration (2026-10-08): write fact-pattern facets onto the record.

Takes the Sonnet-drafted facet file (reviewed in the main session — the
overrides below are the review) and writes ``fact_pattern`` onto every case
and conflict site and ``fact_triggers`` onto every statutory reading. Idempotent:
re-running with the same input is a no-op diff. New records ship their facets
inline; this script exists as the audit trail for the first batch.

Usage: python3 scripts/annotate_fact_patterns.py <facets.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from refdata.loaders import (  # noqa: E402
    CWA_INVESTIGATIONS_PATH,
    DC_WATER_CONFLICTS_PATH,
    WATER_AUTHORITIES_PATH,
)
from refdata.taxonomies import FACT_FACETS  # noqa: E402

# Review overrides (main session, 2026-10-08). Evaporative towers alone do not
# put a campus under §402 — their blowdown goes to a sewer unless the site has
# an outfall — so the NPDES reading keys on the outfall, not the tower.
READING_OVERRIDES = {
    "cwa-402-npdes": ["out-surface", "pwr-thermo-cooling", "cool-once-through"],
}


def _ordered(facets: list[str]) -> list[str]:
    known = [f for f in FACT_FACETS if f in set(facets)]
    unknown = sorted(set(facets) - set(FACT_FACETS))
    if unknown:
        print(f"  dropping unknown facets {unknown}")
    return known


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(facets_path: str) -> None:
    drafted = json.loads(Path(facets_path).read_text(encoding="utf-8"))

    cwa = json.loads(CWA_INVESTIGATIONS_PATH.read_text(encoding="utf-8"))
    for case in cwa["cases"]:
        entry = drafted["cases"].get(case["case_id"])
        if entry:
            case["fact_pattern"] = _ordered(entry["fact_pattern"])
    _write(CWA_INVESTIGATIONS_PATH, cwa)

    conflicts = json.loads(DC_WATER_CONFLICTS_PATH.read_text(encoding="utf-8"))
    for site in conflicts["sites"]:
        entry = drafted["sites"].get(site["site_id"])
        if entry:
            site["fact_pattern"] = _ordered(entry["fact_pattern"])
    _write(DC_WATER_CONFLICTS_PATH, conflicts)

    authorities = json.loads(WATER_AUTHORITIES_PATH.read_text(encoding="utf-8"))
    for reading in authorities["readings"]:
        rid = reading["reading_id"]
        entry = drafted["readings"].get(rid)
        triggers = READING_OVERRIDES.get(rid) or (entry and entry["fact_triggers"])
        if triggers:
            reading["fact_triggers"] = _ordered(triggers)
    _write(WATER_AUTHORITIES_PATH, authorities)
    print("done")


if __name__ == "__main__":
    main(sys.argv[1])
