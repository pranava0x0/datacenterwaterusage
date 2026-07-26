#!/usr/bin/env python3
"""Spec A2 data: the claims→litigation edge, and the last doctrine family.

Two 2026 developments the tracker had no shape for:

* **An operator's water claims became the cause of action.** A former AWS water
  sustainability program manager sued the company under Virginia consumer-
  protection law over its published water figures. Nothing in the schema could
  express that — the case is not about a discharge, and the legal hook is state
  consumer-protection law, which the five-federal-statute registry could not
  reach. This adds the ``SL`` family (the seventeenth and last planned), the
  ``greenwashing-litigation`` case type, and the case itself.
* **A data-center contractor contaminated a municipal reclaimed-water system.**
  Cheyenne traced a rare bacterium in its reuse system to the entity building
  Meta's campus, found significant noncompliance with federal pretreatment
  rules, and permanently barred the discharge. First of its kind in the record,
  and it unlocks the ``pretreatment-potw`` issue type held back from Spec A1.

Both search-verified 2026-07-26. Claims still made only by their maker are left
as claims; nothing here asserts that a challenged claim is false.

Run: ``python3 scripts/add_claims_litigation_2026_07.py [--dry-run]``
Idempotent.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))
sys.path.insert(0, str(BASE_DIR))

from _doctrine_batch import apply_batch  # noqa: E402

CONFLICTS_PATH = BASE_DIR / "data" / "reference" / "dc_water_conflicts.json"

NEW_STATUTES = {
    "SL": {
        "name": "State consumer-protection & claims law",
        "full_name": (
            "State deceptive-trade-practices and consumer-protection statutes as "
            "applied to environmental and water-sustainability claims"
        ),
        "agencies": "State attorneys general; state courts; private plaintiffs",
        "kind": "state-doctrine",
        "url": "https://www.law.cornell.edu/wex/deceptive_trade_practices",
    },
}

NEW_READINGS = [
    {
        "reading_id": "sl-greenwashing-udap",
        "statute": "SL",
        "section": "State deceptive-trade-practices / consumer-protection statutes",
        "name": "Water claims as a deceptive trade practice",
        "agency": "State attorneys general; state courts; private plaintiffs",
        "what_it_covers": (
            "Statements a company makes to the public about its environmental "
            "performance, where those statements are alleged to be materially "
            "misleading. The subject of the claim is the company's own published "
            "figures rather than any discharge, withdrawal or permit, and the remedy "
            "sought is typically corrective disclosure and an accounting."
        ),
        "dc_applicability": (
            "The one reading in this registry that does not require a permit, a "
            "discharge or an aquifer. It reaches the water-positive pledges and "
            "efficiency percentages that operators publish — which is significant "
            "because those figures are the industry's main public answer on water, and "
            "until 2026 nothing in the tracker connected a claim to a legal "
            "consequence. Its evidentiary base is utility billing records obtained by "
            "FOIA, so it is unusually available to outsiders compared with the "
            "hydrologic proof most other readings demand."
        ),
        "example_case_ids": ["Wangusi-v-Amazon-Web-Services-VA-2026"],
    },
]

NEW_CASES = [
    {
        "case_id": "Wangusi-v-Amazon-Web-Services-VA-2026",
        "category": "datacenter",
        "respondent": (
            "Amazon Web Services, Inc. and Virginia Connects (Circuit Court of "
            "Arlington County, Virginia)"
        ),
        "year": "2026",
        "cwa_section": (
            "Not a Clean Water Act case — Virginia consumer-protection / "
            "deceptive-trade-practices law"
        ),
        "violation_summary": (
            "Dr. Nathan Wangusi, AWS's water sustainability program manager for nearly "
            "three years until September 2024, sued the company and the data-center "
            "industry group Virginia Connects, alleging its published Northern Virginia "
            "water claims were materially misleading. Using water billing and "
            "consumption records obtained by FOIA from local utilities for 2023-2026, "
            "the complaint targets AWS's statements that it had 'dropped water use by 42 "
            "percent year-over-year' and that its Northern Virginia data centers operate "
            "'ninety-seven percent of the year by pulling outside air and not using any "
            "water' — the utility records, it alleges, show withdrawals in every month "
            "including winter. Virginia Connects is alleged to have run a public "
            "advertising campaign carrying the same claims on the day AWS published the "
            "42 percent figure."
        ),
        "outcome": (
            "PENDING — filed mid-July 2026; no ruling. AWS denies wrongdoing and says "
            "its reported water data has been independently assured by a third party."
        ),
        "takeaway": (
            "The first case in this record where an operator's own water claims, rather "
            "than any discharge or withdrawal, are the alleged violation — and it "
            "arrives by a route the tracker's federal-statute framing could not see. "
            "Two features make it a template rather than a one-off: the plaintiff is an "
            "insider who ran the program he is now contradicting, and the evidence is "
            "FOIA'd utility billing records, which any resident of a jurisdiction with "
            "public utility records can obtain. That is a far lower evidentiary bar than "
            "the hydrologic proof nearly every other reading in this registry requires, "
            "and it points at the disclosure laws this tracker follows: the more "
            "utilities are required to report data-center deliveries, the more checkable "
            "every published water claim becomes."
        ),
        "analogous_cases": [
            "QTS-Fayette-GA-unbilled-water-2026",
            "Google-Berkeley-SC-Middendorf-aquifer-2019",
        ],
        "related_claim_ids": ["aws-water-positive-2030"],
        "sources": [
            {
                "title": "AWS sustainability claims don't hold water, lawsuit alleges",
                "url": "https://www.theregister.com/on-prem/2026/07/15/aws-sustainability-claims-dont-hold-water-lawsuit-alleges/5269723",
                "type": "news",
            },
            {
                "title": "AWS faces lawsuit over alleged misleading water sustainability claims",
                "url": "https://www.computing.co.uk/news/2026/aws-lawsuit-misleading-water-sustainability-claims",
                "type": "news",
            },
        ],
        "case_type": "greenwashing-litigation",
        "cwa_applied": "not-applied",
        "cwa_instrument": "State consumer-protection suit over published water claims",
        "cwa_pathway": (
            "No federal water statute is implicated. The pathway runs through state "
            "deceptive-trade-practices law: published sustainability figures are "
            "commercial statements, and utility billing records obtained by FOIA are the "
            "evidence used to test them."
        ),
        "display_section": "potential",
        "authorities": ["sl-greenwashing-udap"],
    },
    {
        "case_id": "Meta-Cheyenne-WY-reclaimed-contamination-2026",
        "category": "datacenter",
        "respondent": (
            "Goat Systems LLC (the entity building Meta's Cheyenne campus) — "
            "Cheyenne Board of Public Utilities, Wyoming"
        ),
        "year": "2026",
        "cwa_section": "CWA §307(b) pretreatment / 40 CFR Part 403 (municipal pretreatment program)",
        "violation_summary": (
            "In February 2026 Cheyenne's Board of Public Utilities detected the rare "
            "metal-resistant bacterium Cupriavidus gilardii in the city's reclaimed-water "
            "system and traced it to wastewater from construction and commissioning of "
            "Meta's 715,000 sq ft data center — a closed-loop cooling 'fill-and-flush' "
            "discharge by Goat Systems LLC, the entity Meta uses to build the campus. "
            "The discharge interfered with two water reclamation plants; BOPU's published "
            "timeline puts 801,475 gallons of affected wastewater into the system."
        ),
        "outcome": (
            "BOPU classified the discharge as significant noncompliance with federal "
            "pretreatment regulations, suspended the reclaimed-water irrigation program, "
            "permanently terminated the discharge privileges, and adopted a policy "
            "barring wastewater discharges from data centers using closed-loop cooling "
            "and fill-and-flush systems. Follow-up testing found no remaining Cupriavidus "
            "gilardii and the reclaimed system is back in operation under continued "
            "routine sampling."
        ),
        "takeaway": (
            "The first data-center contamination of a municipal reclaimed-water system in "
            "this record, and it inverts the usual framing. Reclaimed water is the "
            "industry's headline answer to consumption criticism and appears throughout "
            "this tracker's Solutions dataset — here the reuse system itself was the "
            "casualty, and the harm came from commissioning rather than operation, a "
            "phase almost nothing regulates specifically. It also confirms where the "
            "operational hook actually sits: not on the data center's own permit, but on "
            "the receiving utility's pretreatment authority, which is exactly the "
            "framing the CWA insights panel has argued. Note the defendant is the build "
            "entity, not Meta itself — corporate structure matters for who is on the "
            "hook."
        ),
        "analogous_cases": [
            "Amazon-Boardman-OR-nitrate-2026",
            "QuantumLoophole-FrederickMD-boring-discharges-2022-2024",
        ],
        "sources": [
            {
                "title": "Cheyenne BOPU traces rare bacteria discharge to Meta data center contractor",
                "url": "https://www.wyomingnews.com/news/local_news/cheyenne-bopu-traces-rare-bacteria-discharge-to-meta-data-center-contractor/article_1c538467-06ec-427d-9a6f-33797cd3c6ce.html",
                "type": "news",
            },
            {
                "title": "Cheyenne BOPU releases wastewater contamination timeline; over 800K gallons affected",
                "url": "https://capcity.news/community/city/2026/07/20/cheyenne-bopu-releases-wastewater-contamination-timeline-over-800k-gallons-affected/",
                "type": "news",
            },
            {
                "title": "Cheyenne Won't Take Data Center Wastewater After Meta Contractor Contaminated System",
                "url": "https://cowboystatedaily.com/2026/07/02/cheyenne-wont-take-data-center-wastewater-after-meta-company-contaminated-system/",
                "type": "news",
            },
        ],
        "case_type": "pretreatment",
        "cwa_applied": "applied",
        "cwa_instrument": "Municipal pretreatment program — significant noncompliance; discharge privileges terminated",
        "display_section": "historical",
        "authorities": ["cwa-307-pretreatment"],
    },
]

NEW_SITE = {
    "site_id": "meta-cheyenne-wy",
    "site": "Meta — Cheyenne, WY",
    "location": "Cheyenne, Laramie County, Wyoming",
    "operator": "Meta (campus built by Goat Systems LLC)",
    "issue_summary": (
        "Commissioning discharges from Meta's 715,000 sq ft campus introduced the rare "
        "metal-resistant bacterium Cupriavidus gilardii into Cheyenne's reclaimed-water "
        "system in February 2026, interfering with two reclamation plants and affecting "
        "801,475 gallons of wastewater. The city's utility board classified it as "
        "significant noncompliance with federal pretreatment regulations."
    ),
    "pushback_summary": (
        "BOPU suspended the reclaimed-water irrigation program, permanently terminated "
        "the discharge privileges, and adopted a standing policy refusing wastewater "
        "from data centers using closed-loop cooling and fill-and-flush systems — a "
        "categorical restriction on an entire cooling practice rather than a penalty "
        "against one project. Follow-up testing found the bacterium cleared and the "
        "reuse system is operating again under continued sampling."
    ),
    "status_2026": "Discharge privileges terminated; reuse system restored under new policy",
    "issue_types": ["pretreatment-potw", "discharge-quality"],
    "issue_types_rationale": (
        "Contamination introduced into a municipal reclaimed-water system by a "
        "commissioning discharge, resolved through the utility's pretreatment authority "
        "rather than any data-center permit."
    ),
    "applicable_readings": [
        {
            "reading_id": "cwa-307-pretreatment",
            "how": (
                "The operative authority was the receiving utility's federally delegated "
                "pretreatment program, not any permit held by the data center — the "
                "utility could bar the discharge outright without an enforcement action "
                "against the operator."
            ),
            "analogous_cases": ["Meta-Cheyenne-WY-reclaimed-contamination-2026"],
        }
    ],
    "related_case_ids": ["Meta-Cheyenne-WY-reclaimed-contamination-2026"],
    "sources": [
        {
            "title": "Cheyenne BOPU traces rare bacteria discharge to Meta data center contractor",
            "url": "https://www.wyomingnews.com/news/local_news/cheyenne-bopu-traces-rare-bacteria-discharge-to-meta-data-center-contractor/article_1c538467-06ec-427d-9a6f-33797cd3c6ce.html",
        },
        {
            "title": "Cheyenne BOPU releases wastewater contamination timeline; over 800K gallons affected",
            "url": "https://capcity.news/community/city/2026/07/20/cheyenne-bopu-releases-wastewater-contamination-timeline-over-800k-gallons-affected/",
        },
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rc = apply_batch(
        NEW_STATUTES,
        NEW_READINGS,
        NEW_CASES,
        last_updated="2026-07-26",
        dry_run=args.dry_run,
    )
    if rc != 0:
        return rc

    from refdata.taxonomies import ISSUE_TYPE_LABELS

    conflicts = json.loads(CONFLICTS_PATH.read_text(encoding="utf-8"))
    if any(s["site_id"] == NEW_SITE["site_id"] for s in conflicts["sites"]):
        print(f"site already present: {NEW_SITE['site_id']}")
        return 0
    for tag in NEW_SITE["issue_types"]:
        if tag not in ISSUE_TYPE_LABELS:
            print(f"Aborted: unknown issue type {tag}", file=sys.stderr)
            return 1

    conflicts["sites"].append(NEW_SITE)
    print(f"conflict site added: {NEW_SITE['site_id']} ({len(conflicts['sites'])} total)")
    if args.dry_run:
        print("(dry run — site not written)")
        return 0
    conflicts["last_updated"] = "2026-07-26"
    CONFLICTS_PATH.write_text(
        json.dumps(conflicts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("Wrote dc_water_conflicts.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
