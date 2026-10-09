"""One-off migration (2026-10-08): write fact_triggers onto water-scoped instruments.

Takes the Sonnet-drafted file (reviewed in the main session — the overrides
below are the review) and writes ``fact_triggers`` onto every instrument whose
scope includes water. Empty means "applies to every data center in its
jurisdiction regardless of how it uses water". Idempotent; new instruments ship
their triggers inline.

Usage: python3 scripts/annotate_instrument_triggers.py <instrument_triggers.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from refdata.loaders import LEGISLATION_PATH  # noqa: E402
from refdata.taxonomies import FACT_FACETS  # noqa: E402

# The scale facet means roughly 100 MW / 1 MGD and up. An instrument whose own
# threshold is far below that covers hyperscale campuses too, but the facet
# would then say "this only bites on large projects", which is backwards.
STRIP_SCALE = {
    "NY S6394 / A9086", "SD SB 135", "PA HB 2246", "MN HF 16", "NC HB 1063",
    "MA EO 658", "PA EO 2026-05", "US S. 5054",
}
# Community-benefit-agreement requirements and incentive conditions bite on a
# project that seeks the incentive or signs the agreement.
ADD_INCENTIVE = {
    "IL SB 4016 / HB 5513", "MI SB 1046-1050", "MA EO 658", "NV EO 2026-005", "CT SB 245", "US S. 5054",
}


def _ordered(facets) -> list[str]:
    return [f for f in FACT_FACETS if f in set(facets)]


def main(path: str) -> None:
    drafted = json.loads(Path(path).read_text(encoding="utf-8"))["instruments"]
    data = json.loads(LEGISLATION_PATH.read_text(encoding="utf-8"))
    ids = {b["bill_id"] for b in data["bills"]}
    missing = (STRIP_SCALE | ADD_INCENTIVE) - ids
    assert not missing, f"override names unknown ids: {sorted(missing)}"
    for bill in data["bills"]:
        if "water" not in (bill.get("scope") or []):
            bill.pop("fact_triggers", None)
            continue
        facets = set((drafted.get(bill["bill_id"]) or {}).get("fact_triggers", []))
        if bill["bill_id"] in STRIP_SCALE:
            facets.discard("scale-hyperscale")
        if bill["bill_id"] in ADD_INCENTIVE:
            facets.add("proc-incentive")
        bill["fact_triggers"] = _ordered(facets)
    LEGISLATION_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("done")


if __name__ == "__main__":
    main(sys.argv[1])
