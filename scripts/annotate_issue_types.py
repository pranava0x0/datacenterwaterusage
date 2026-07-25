#!/usr/bin/env python3
"""One-off migration: classify every conflict site by issue type.

Plan Spec A1. The 18 sites carry good prose but no closed classification of
*what kind* of water problem each is, so the tab cannot answer "show me the
aquifer fights" — a reader has to open and read all 18 summaries. The taxonomy
is also the join key that lets a legislation principle, a solution or a
doctrine reading say which problem it addresses.

Each classification below is drawn from the site's own ``issue_summary`` and
``pushback_summary``, not from outside knowledge, so it can be checked against
the record it labels. One to three tags per site: the dominant problem first.

Run: ``python3 scripts/annotate_issue_types.py [--dry-run]``
Idempotent.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

CONFLICTS_PATH = BASE_DIR / "data" / "reference" / "dc_water_conflicts.json"

# site_id -> (issue_types, one-line justification tied to the record's own text)
SITE_ISSUE_TYPES = {
    "google-the-dalles-or": (
        ["supply-secrecy", "supply-strain", "disclosure-gap"],
        "City sued a newspaper (Google paying its fees) to keep water figures secret as a trade secret, while Google's draw passed a quarter of city supply.",
    ),
    "xai-colossus-memphis-tn": (
        ["aquifer-depletion", "alt-source-adoption"],
        "~3 MGD of cooling water from the Memphis Sand sole-source aquifer, with a greywater recycling plant as the mitigation.",
    ),
    "meta-newton-county-ga": (
        ["aquifer-depletion"],
        "Well-dependent households nearest the campus lost water after construction — the clearest neighbour-well-failure fact pattern in the record.",
    ),
    "project-blue-tucson-az": (
        ["siting-zoning-defeat", "supply-strain"],
        "~2,000 acre-feet/yr would have made it Tucson Water's largest customer; the project was rejected.",
    ),
    "meta-mesa-microsoft-goodyear-az": (
        ["supply-strain", "aquifer-depletion"],
        "~91 metro Phoenix data centers against a potential 77% cut to Arizona's Colorado River allocation.",
    ),
    "pw-digital-gateway-va": (
        ["siting-zoning-defeat", "supply-strain"],
        "Rezoning voided on appeal; the corridor drains to the Occoquan Reservoir supplying ~40% of Northern Virginia drinking water.",
    ),
    "aws-lake-anna-va": (
        ["discharge-quality"],
        "A VPDES individual permit for cooling-water discharge to Sedges Creek — the direct-discharge fact pattern.",
    ),
    "amazon-boardman-umatilla-or": (
        ["discharge-quality", "aquifer-depletion"],
        "Cooling evaporation concentrates nitrate in Port of Morrow wastewater over a designated groundwater management area.",
    ),
    "corpus-christi-sinton-tx": (
        ["aquifer-depletion", "supply-strain"],
        "A 22-well emergency Evangeline Aquifer field built with reservoirs below 10% full.",
    ),
    "hood-county-granbury-tx": (
        ["aquifer-depletion", "moratorium-pause"],
        "Aquifer concerns around proposed AI campuses drove a county moratorium (later rescinded).",
    ),
    "charlotte-nc-moratorium": (
        ["moratorium-pause", "supply-strain"],
        "A citywide moratorium adopted during the worst drought since 2007, with a facility's peak draw as the trigger.",
    ),
    "microsoft-racine-county-wi": (
        ["siting-zoning-defeat", "supply-secrecy", "supply-contract-dispute"],
        "Caledonia rezoning withdrawn after opposition; Riverkeeper groups sued for water records; Mount Pleasant sits inside the contested Foxconn-era Great Lakes diversion.",
    ),
    "qts-fayette-county-ga": (
        ["rate-cost-shift", "disclosure-gap"],
        "Two high-capacity connections ran unmetered and unbilled — other ratepayers carried the cost of water nobody measured.",
    ),
    "meta-richland-parish-la": (
        ["supply-strain", "disclosure-gap"],
        "Registered for up to 23 MGD (8.4B gal/yr) with no monitoring requirement attached.",
    ),
    "quantum-loophole-frederick-md": (
        ["construction-impacts"],
        "At least four frac-outs boring the Q-LOOP conduit under the Potomac and Monocacy — harm from building, not operating.",
    ),
    "microsoft-west-des-moines-ia": (
        ["supply-strain", "disclosure-gap"],
        "11.5M gallons in a single month, ~6% of the district's supply, surfaced only through reporting.",
    ),
    "bessemer-al-hyperscale": (
        ["supply-strain", "rate-cost-shift"],
        "A 2 MGD request against a third of the authority's capacity, with the utility conceding it could not serve without significant upgrades.",
    ),
    "missouri-peculiar-stcharles": (
        ["siting-zoning-defeat", "rate-cost-shift", "moratorium-pause"],
        "A project defeated on water-rate grounds, then one of the first US municipal data-center moratoriums driven partly by water supply.",
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from refdata.taxonomies import ISSUE_TYPE_LABELS

    payload = json.loads(CONFLICTS_PATH.read_text(encoding="utf-8"))
    problems, changed = [], 0
    counts: dict[str, int] = {}

    known = {s["site_id"] for s in payload["sites"]}
    for site_id in SITE_ISSUE_TYPES:
        if site_id not in known:
            problems.append(f"SITE_ISSUE_TYPES names an absent site: {site_id}")

    for site in payload["sites"]:
        entry = SITE_ISSUE_TYPES.get(site["site_id"])
        if entry is None:
            problems.append(f"{site['site_id']}: unclassified — every site needs ≥1 issue type")
            continue
        tags, rationale = entry
        for tag in tags:
            if tag not in ISSUE_TYPE_LABELS:
                problems.append(f"{site['site_id']}: unknown issue type {tag}")
            counts[tag] = counts.get(tag, 0) + 1
        if site.get("issue_types") != tags:
            changed += 1
        site["issue_types"] = tags
        site["issue_types_rationale"] = rationale

    print(f"sites classified: {len(payload['sites'])} ({changed} changed)")
    for tag, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {tag:<26} {n}")
    unused = sorted(set(ISSUE_TYPE_LABELS) - set(counts))
    print(f"taxonomy values not yet used by any site: {unused}")

    if problems:
        print("\nAborted:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    if args.dry_run:
        print("\n(dry run — nothing written)")
        return 0

    CONFLICTS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("\nWrote dc_water_conflicts.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
