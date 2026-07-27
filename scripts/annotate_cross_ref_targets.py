#!/usr/bin/env python3
"""One-off migration: add explicit ``cross_ref_targets`` to news + solutions.

Before this, a news item pointed at a tracked bill or case by *naming it in
prose*, and the renderer found the link by substring-matching every known
display string against the sentence (``dashboard._linkify_refs``). That guesses:
it silently stops linking when a record is renamed, and on an overlapping name
it links the wrong one. PR #17's review flagged it; this executes the fix.

The mapping below is hand-adjudicated — an id is written only where the prose
names exactly one tracked record. Entries whose note points at a *scraper* or a
*section* rather than a record (the "Sources tab" / "Data tab" pointers) keep
the legacy prose path; there is no id to give them.

Run: ``python3 scripts/annotate_cross_ref_targets.py [--dry-run]``
Idempotent — re-running writes the same file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

NEWS_PATH = BASE_DIR / "data" / "reference" / "water_news.json"
SOLUTIONS_PATH = BASE_DIR / "data" / "reference" / "water_solutions.json"

# news id -> [target record ids]
NEWS_TARGETS = {
    "ny-responsible-dc-act-permit-moratorium-2026-06": ["NY S10642 / A11560"],
    "fayette-county-ga-qts-metering-2026-05": ["QTS-Fayette-GA-unbilled-water-2026"],
    "florida-sb484-effective-2026-07": ["FL SB 484"],
    "texas-puc-water-survey-ignored-2026-06": ["corpus-christi-sinton-tx"],
    "hill-county-rescinds-moratorium-2026-06": ["hood-county-granbury-tx"],
    "lake-anna-deq-hearing-2026-06": ["aws-lake-anna-va"],
    "nc-moratorium-wave-2026-06": ["charlotte-nc-moratorium"],
    "moratorium-bills-11-states-2026-06": ["NY S10642 / A11560"],
    "ny-s10642-passes-legislature-2026-06": ["NY S10642 / A11560"],
    "michigan-moratorium-2026-06": ["MI SB 1018-1020"],
    "illinois-pritzker-pauses-incentives-2026-06": ["IL SB 3830 (POWER Act)"],
    "google-s404-permits-2026-05": [
        "Google-ProjectRaspberry-VA-2026",
        "Google-LittleRock-AR-2026",
    ],
    "ut-eo-2026-03-signed-2026-05": ["UT EO 2026-03", "UT HB 76"],
    "virginia-hb496-enacted-2026-04": ["VA HB 496 / SB 553"],
    "maryland-veto-override-2026-04": ["MD HB 270 / SB 116"],
    "amazon-boardman-settlement-2026-03": ["amazon-boardman-umatilla-or"],
    "idaho-h895-enacted-2026-03": ["ID H 895"],
    "south-dakota-sb135-enacted-2026-03": ["SD SB 135"],
    "utah-hb76-enacted-2026-03": ["UT HB 76"],
    "california-ab2619-advancing-2026-05": ["CA AB 2619", "CA SB 887"],
    "amazon-water-disclosure-2026-06": ["wue-reporting"],
    "imperial-valley-iid-lawsuit-2026-06": [],  # site not tracked yet — prose stays
}

# Notes that were phrased *for* the substring linkifier — they spell the record
# out (sometimes as a raw id, sometimes as a caption that no longer matches the
# registry label) so the old matcher would find it. With an explicit target the
# link supplies the name, so the note goes back to being the sentence that
# explains *why* the two records are related. Without this the card renders the
# name twice, once as prose and once as a trailing link.
NOTE_REWRITES = {
    "amazon-water-disclosure-2026-06": "Substantiates the WUE-reporting solution entry",
    "ny-responsible-dc-act-permit-moratorium-2026-06": (
        "Clarifies that the mechanism is a DEC permit moratorium, not only a "
        "SEQRA review trigger"
    ),
    "fayette-county-ga-qts-metering-2026-05": "Same incident, tracked as a case",
    "google-s404-permits-2026-05": "The two §404 permit applications behind this story",
    "amazon-boardman-settlement-2026-03": "Full case record",
    "idaho-h895-closed-loop-mandate": "The two enacted closed-loop mandates",
    "ohio-epa-ohd000001": (
        "The draft general permit itself; discharge data will come from the "
        "oh_epa_general_permit scraper once it is finalized"
    ),
}

# solution id -> [target record ids]
SOLUTION_TARGETS = {
    "va-hb496-monthly-reporting": ["VA HB 496 / SB 553"],
    "idaho-h895-closed-loop-mandate": ["ID H 895", "SC HB 4583"],
    "sd-sb135-cost-causation": ["SD SB 135"],
    "utah-hb76-eo-disclosure": ["UT HB 76", "UT EO 2026-03"],
    "ohio-epa-ohd000001": ["OH EPA OHD000001 (draft general permit)"],
    "ny-s10642-seqra-review": ["NY S10642 / A11560"],
}


def _apply(entry: dict, targets: list[str], registry, report: list[str]) -> bool:
    """Set cross_ref_targets on ``entry``, refusing ids nothing claims."""
    if not targets:
        return False
    unknown = [t for t in targets if t not in registry]
    if unknown:
        report.append(f"  !! {entry.get('id')}: unknown target ids {unknown}")
        return False
    rewrite = NOTE_REWRITES.get(entry.get("id"))
    changed = False
    if rewrite and entry.get("cross_ref_note") != rewrite:
        entry["cross_ref_note"] = rewrite
        changed = True
    if entry.get("cross_ref_targets") != targets:
        entry["cross_ref_targets"] = targets
        changed = True
    if changed:
        report.append(f"  {entry.get('id')} -> {', '.join(targets)}")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from refdata.registry import build_registry

    registry = build_registry()
    report: list[str] = []

    news = json.loads(NEWS_PATH.read_text(encoding="utf-8"))
    news_changed = sum(
        _apply(item, NEWS_TARGETS.get(item.get("id"), []), registry, report)
        for item in news["items"]
    )

    solutions = json.loads(SOLUTIONS_PATH.read_text(encoding="utf-8"))
    sol_changed = 0
    for cat in solutions["categories"]:
        for sol in cat["solutions"]:
            sol_changed += _apply(
                sol, SOLUTION_TARGETS.get(sol.get("id"), []), registry, report
            )

    print(f"news items annotated:     {news_changed}")
    print(f"solutions annotated:      {sol_changed}")
    print("\n".join(report))

    if any(line.startswith("  !!") for line in report):
        print("\nAborted: unresolved target ids.", file=sys.stderr)
        return 1
    if args.dry_run:
        print("\n(dry run — nothing written)")
        return 0

    NEWS_PATH.write_text(
        json.dumps(news, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    SOLUTIONS_PATH.write_text(
        json.dumps(solutions, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("\nWrote water_news.json and water_solutions.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
