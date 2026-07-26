#!/usr/bin/env python3
"""Spec C3 piece 1: map the doctrine families onto the tracked conflict sites.

The registry now holds 17 authority families, but before this every one of the
19 conflict sites mapped only to CWA/SDWA/TSCA/RCRA/RHA readings — the doctrine
half existed and nothing pointed at it. This is the join that makes the
precedent engine answer the actual question: *which doctrines could reach this
site, through what argument, and what does the historical record say happens?*

**Negative mappings are first-class.** Each entry may carry ``reaches: false``,
meaning the doctrine is the obvious one to reach for and does *not* work here.
A registry that only collects theories that work would mislead the journalists
and planners it is for, and the negatives are often the most useful lines on a
card — they stop an advocacy claim before it is made.

Copy discipline (plan §C3): modal language only. "Could reach", "has been
argued". The tracker maps legal exposure; it does not predict outcomes or
recommend suits.

Run: ``python3 scripts/annotate_site_doctrine_mappings.py [--dry-run]``
Idempotent — re-running replaces only the doctrine entries it manages.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

CONFLICTS_PATH = BASE_DIR / "data" / "reference" / "dc_water_conflicts.json"

# site_id -> list of {reading_id, how, analogous_cases, reaches?}
# `how` is written per site, not per doctrine: the same reading reaches Memphis
# and Corpus Christi by different arguments.
SITE_DOCTRINE_MAPPINGS: dict[str, list[dict]] = {
    "xai-colossus-memphis-tn": [
        {
            "reading_id": "eqap-interstate-aquifer",
            "how": (
                "The Memphis Sand is the same aquifer the Supreme Court held apportionable "
                "in 2021, so the question of who may complain about heavy pumping here is "
                "already answered: a neighbouring state, suing for an equitable "
                "apportionment. The obstacle is evidentiary rather than legal — an "
                "apportioning court needs clear and convincing proof of injury, which "
                "means aggregate withdrawal data of the kind utility reporting laws "
                "produce."
            ),
            "analogous_cases": ["Mississippi-v-Tennessee-2021"],
        },
        {
            "reading_id": "esa-proximate-cause-limit",
            "reaches": False,
            "how": (
                "No listed species depends on Memphis Sand springflow, and even where one "
                "did, suing the permitting authority for downstream harm is foreclosed on "
                "these facts. The Endangered Species Act is a natural instinct for a "
                "depleted aquifer and is not the hook here."
            ),
            "analogous_cases": ["Aransas-Project-v-Shaw-2014"],
        },
        {
            "reading_id": "tribal-winters",
            "reaches": False,
            "how": (
                "No federal reservation overlies or adjoins the Memphis Sand in this "
                "reach, so no senior reserved right competes for the water. Reserved "
                "rights are decisive in the arid Southwest and simply absent here."
            ),
            "analogous_cases": ["Winters-v-United-States-1908"],
        },
    ],
    "microsoft-racine-county-wi": [
        {
            "reading_id": "well-cumulative-impact",
            "how": (
                "Any high-capacity well permit for the campus would be reviewed by the "
                "same state agency, in the same court system, that was held to owe an "
                "affirmative duty to consider a well's effect on waters of the state. "
                "Objectors would have to put concrete hydrologic evidence in front of the "
                "agency to trigger that duty — which is what the water-records litigation "
                "over this campus was ultimately about."
            ),
            "analogous_cases": ["Lake-Beulah-v-DNR-2011"],
        },
        {
            "reading_id": "cl-citizen-standing-limit",
            "how": (
                "The pattern here — a rezoning defeated by residents while the adjacent "
                "campus expanded through permitting — is what the standing rule predicts. "
                "A watershed coalition can be dismissed before the merits; the community "
                "veto that actually worked was a zoning vote, not a suit."
            ),
            "analogous_cases": ["MCWC-v-Nestle-Waters-2007"],
        },
    ],
    "corpus-christi-sinton-tx": [
        {
            "reading_id": "gw-ownership-takings",
            "how": (
                "Ownership in place is why this fight runs through district permitting and "
                "emergency wellfield politics rather than a private suit to stop the "
                "pumping: a cap on withdrawal risks a compensation claim, so the state "
                "regulates by permit instead of prohibition."
            ),
            "analogous_cases": ["Edwards-Aquifer-Authority-v-Day-2012"],
        },
        {
            "reading_id": "cl-negligent-subsidence",
            "how": (
                "The sharper theory than the permit fight. Capture immunises taking the "
                "water but not the manner of taking it, so if Evangeline drawdown produces "
                "measurable Coastal Bend subsidence, negligent well spacing and pumping "
                "rates are actionable — and this is Gulf-coast hydrology, where drawdown "
                "and subsidence are known to travel together."
            ),
            "analogous_cases": ["Friendswood-v-Smith-Southwest-1978"],
        },
        {
            "reading_id": "esa-proximate-cause-limit",
            "reaches": False,
            "how": (
                "This site sits in the Aransas/San Antonio Bay hydrology where the Fifth "
                "Circuit's proximate-cause holding is binding law. A claim that upstream "
                "withdrawal permits harm downstream listed species is the most likely "
                "federal theory to be reached for here, and the most likely to fail."
            ),
            "analogous_cases": ["Aransas-Project-v-Shaw-2014"],
        },
        {
            "reading_id": "xfer-area-of-origin",
            "how": (
                "Insofar as supply is moved between basins to serve this demand, the "
                "transferred right is junior to every right granted in the basin of origin "
                "before the transfer was filed — so it is cut first in exactly the drought "
                "conditions that produced the emergency wellfield."
            ),
            "analogous_cases": ["Rowan-ProjectCinco-Medina-TX-2025"],
        },
    ],
    "meta-newton-county-ga": [
        {
            "reading_id": "cl-negligent-subsidence",
            "how": (
                "Georgia's reasonable-use approach to groundwater gives failed-well "
                "neighbours a direct common-law theory that a landowner in a strict "
                "rule-of-capture state would lack. The households nearest the campus are "
                "the strongest available plaintiffs precisely because their injury is "
                "concrete and individual."
            ),
            "analogous_cases": [
                "Friendswood-v-Smith-Southwest-1978",
                "MCWC-v-Nestle-Waters-2007",
            ],
        },
        {
            "reading_id": "ptd-groundwater-nexus",
            "how": (
                "Where campus drawdown measurably reduces flow in a connected navigable "
                "stream, the trust duty attaches to the well permit itself, and the duty "
                "sits with the permitting authority rather than the operator. Requires "
                "hydrologic evidence of the groundwater-to-surface connection."
            ),
            "analogous_cases": ["ELF-v-SWRCB-2018"],
        },
    ],
    "bessemer-al-hyperscale": [
        {
            "reading_id": "util-shortage-moratorium",
            "how": (
                "Swanson read in reverse. The authority's own statement that it cannot "
                "serve 2 MGD without significant upgrades is the rational basis a refusal "
                "would rest on, and a prospective customer has no right to service — so "
                "the doctrine runs for the utility saying no, not for the developer "
                "demanding yes."
            ),
            "analogous_cases": ["Swanson-v-Marin-MWD-1976"],
        }
    ],
    "charlotte-nc-moratorium": [
        {
            "reading_id": "util-shortage-moratorium",
            "how": (
                "A connection moratorium adopted during a genuine supply shortfall is the "
                "fact pattern courts have upheld, reviewable only for fraud, arbitrariness "
                "or caprice. The grandfathering of two projects already approved is the "
                "part most exposed to challenge, not the moratorium itself."
            ),
            "analogous_cases": ["Swanson-v-Marin-MWD-1976"],
        }
    ],
    "missouri-peculiar-stcharles": [
        {
            "reading_id": "util-shortage-moratorium",
            "how": (
                "With no state framework, these fights are decided municipally — and a "
                "municipal moratorium grounded in a real supply-and-demand imbalance is "
                "defensible, whereas one that reads as a no-growth policy is the "
                "vulnerable case."
            ),
            "analogous_cases": ["Swanson-v-Marin-MWD-1976"],
        }
    ],
    "project-blue-tucson-az": [
        {
            "reading_id": "gwmgmt-az-ama",
            "how": (
                "Inside an Active Management Area the assured-water-supply rules, not "
                "common-law pumping rights, are what the project answers to — which is why "
                "this was decided in a statutory supply process and local politics rather "
                "than in a nuisance suit."
            ),
            "analogous_cases": ["ProjectBlue-Tucson-AMES-2026"],
        },
        {
            "reading_id": "ptd-groundwater-nexus",
            "reaches": False,
            "how": (
                "Arizona has never extended the public trust doctrine to groundwater. The "
                "trust argument that succeeded in California is not available here, and the "
                "statutory AMA regime is the whole of the constraint."
            ),
            "analogous_cases": ["ELF-v-SWRCB-2018"],
        },
        {
            "reading_id": "tribal-groundwater",
            "how": (
                "Reserved rights are live across this basin and extend to groundwater, so "
                "quantification would reduce what the state has to allocate. The exposure "
                "runs through the supply contract rather than through any conduct by the "
                "project."
            ),
            "analogous_cases": ["Agua-Caliente-v-CVWD-2017"],
        },
    ],
    "meta-mesa-microsoft-goodyear-az": [
        {
            "reading_id": "gwmgmt-az-ama",
            "how": (
                "Every campus in this metro sits inside an Active Management Area, so "
                "growth is gated by assured-water-supply designation rather than by "
                "discretionary permitting — the constraint is statutory and quantitative."
            ),
            "analogous_cases": ["ProjectBlue-Tucson-AMES-2026"],
        },
        {
            "reading_id": "tribal-winters",
            "how": (
                "With Colorado River allocations facing deep cuts, senior reserved rights "
                "across this basin outrank most state-law entitlements. A campus supplied "
                "under a junior right holds less than its face value in a shortage, which "
                "is a due-diligence question rather than a litigation risk."
            ),
            "analogous_cases": ["Winters-v-United-States-1908"],
        },
    ],
    "hood-county-granbury-tx": [
        {
            "reading_id": "gw-ownership-takings",
            "how": (
                "Texas counties have no zoning power over unincorporated land and "
                "groundwater is owned in place, which together explain why residents were "
                "left with only district permitting: the tools that would work elsewhere "
                "either do not exist here or carry a compensation risk."
            ),
            "analogous_cases": ["Edwards-Aquifer-Authority-v-Day-2012"],
        },
        {
            "reading_id": "cl-negligent-subsidence",
            "how": (
                "The residual private theory once permitting is exhausted: not that the "
                "water was taken, but that the manner of taking it was negligent and "
                "caused measurable harm to neighbouring land."
            ),
            "analogous_cases": ["Friendswood-v-Smith-Southwest-1978"],
        },
    ],
    "google-the-dalles-or": [
        {
            "reading_id": "sl-greenwashing-udap",
            "how": (
                "The precedent that made every later water claim checkable. Litigation "
                "here forced release of a decade of figures and prompted Google to stop "
                "asserting site-level water use as a trade secret nationwide — the "
                "disclosure that consumer-protection theories now build on."
            ),
            "analogous_cases": ["Wangusi-v-Amazon-Web-Services-VA-2026"],
        }
    ],
    "pw-digital-gateway-va": [
        {
            "reading_id": "sepa-supply-adequacy",
            "how": (
                "The rezoning was voided on process after the county declined to wait for a "
                "water-quality study — the same defect the supply-adequacy line addresses, "
                "reached through Virginia procedure rather than a state review statute. "
                "Where such a statute exists, an approval that analyses one phase and "
                "defers the rest is directly vulnerable."
            ),
            "analogous_cases": ["Vineyard-v-Rancho-Cordova-2007"],
        },
        {
            "reading_id": "ptd-reopener",
            "how": (
                "Supply here would arrive through existing utility entitlements rather than "
                "a new permit. Where a state recognises the trust reopener, those settled "
                "rights remain reviewable if the resulting draw harms a trust resource — "
                "which is what makes the Occoquan Reservoir's role the durable issue."
            ),
            "analogous_cases": ["National-Audubon-v-Superior-Court-1983"],
        },
    ],
    "meta-richland-parish-la": [
        {
            "reading_id": "sepa-supply-adequacy",
            "how": (
                "A 23 MGD registration carrying no monitoring requirement is the "
                "documentary gap this line targets: the authorization assumes water without "
                "demonstrating it over the project's life."
            ),
            "analogous_cases": ["Vineyard-v-Rancho-Cordova-2007"],
        }
    ],
    "microsoft-west-des-moines-ia": [
        {
            "reading_id": "sl-greenwashing-udap",
            "how": (
                "Consumption here became public through reporting rather than disclosure, "
                "and the gap between published efficiency statements and a single month at "
                "roughly 6% of district supply is the kind of discrepancy a "
                "consumer-protection theory is built on."
            ),
            "analogous_cases": ["Wangusi-v-Amazon-Web-Services-VA-2026"],
        }
    ],
    "amazon-boardman-umatilla-or": [
        {
            "reading_id": "ptd-groundwater-nexus",
            "how": (
                "Nitrate concentration over a designated groundwater management area links "
                "the discharge to the aquifer, and where that aquifer feeds a navigable "
                "water the trust duty reaches the permitting decision as well as the "
                "discharge permit already in play."
            ),
            "analogous_cases": ["ELF-v-SWRCB-2018"],
        }
    ],
    "meta-cheyenne-wy": [
        {
            "reading_id": "util-shortage-moratorium",
            "how": (
                "The utility's categorical refusal to accept wastewater from closed-loop "
                "and fill-and-flush data-center systems is the service-law counterpart to "
                "the pretreatment finding: a utility may decline to serve, and a "
                "prospective discharger has no entitlement to be taken."
            ),
            "analogous_cases": ["Swanson-v-Marin-MWD-1976"],
        }
    ],
    "qts-fayette-county-ga": [
        {
            "reading_id": "sl-greenwashing-udap",
            "how": (
                "Unmetered, unbilled connections are the evidentiary situation these claims "
                "turn on. Where consumption is not measured, published figures cannot be "
                "checked — and utility billing records are the exhibit a "
                "consumer-protection claim would rest on."
            ),
            "analogous_cases": ["Wangusi-v-Amazon-Web-Services-VA-2026"],
        }
    ],
    "quantum-loophole-frederick-md": [
        {
            "reading_id": "cl-negligent-subsidence",
            "how": (
                "Frac-outs during boring are harm from the manner of the work rather than "
                "from any authorized discharge, which is the register common-law negligence "
                "operates in — and the escalation to the state attorney general reflects "
                "that the permit framework alone did not resolve it."
            ),
            "analogous_cases": ["Friendswood-v-Smith-Southwest-1978"],
        }
    ],
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from refdata.loaders import load_cwa_investigations, load_water_authorities

    readings = {r["reading_id"]: r for r in load_water_authorities()["readings"]}
    case_ids = {c["case_id"] for c in load_cwa_investigations()["cases"]}
    doctrine_families = {
        code
        for code in {r["statute"] for r in readings.values()}
        if code not in ("CWA", "SDWA", "TSCA", "RCRA", "RHA")
    }
    doctrine_readings = {
        rid for rid, r in readings.items() if r["statute"] in doctrine_families
    }

    payload = json.loads(CONFLICTS_PATH.read_text(encoding="utf-8"))
    by_site = {s["site_id"]: s for s in payload["sites"]}
    problems: list[str] = []

    for site_id in SITE_DOCTRINE_MAPPINGS:
        if site_id not in by_site:
            problems.append(f"mapping names an absent site: {site_id}")

    added = negatives = 0
    for site_id, mappings in SITE_DOCTRINE_MAPPINGS.items():
        site = by_site.get(site_id)
        if site is None:
            continue
        # Replace only the doctrine entries this script manages; the federal
        # statute mappings curated earlier are left untouched.
        kept = [
            m
            for m in site.get("applicable_readings", [])
            if m.get("reading_id") not in doctrine_readings
        ]
        for m in mappings:
            rid = m["reading_id"]
            if rid not in readings:
                problems.append(f"{site_id}: unknown reading {rid}")
                continue
            if rid not in doctrine_readings:
                problems.append(
                    f"{site_id}: {rid} is a federal-statute reading — "
                    "curate those in the site file, not here"
                )
                continue
            if len(m.get("how", "")) < 80:
                problems.append(f"{site_id}/{rid}: `how` is too thin to be useful")
            for cid in m.get("analogous_cases", []):
                if cid not in case_ids:
                    problems.append(f"{site_id}/{rid}: unknown analogous case {cid}")
            added += 1
            if m.get("reaches") is False:
                negatives += 1
        site["applicable_readings"] = kept + list(mappings)

    covered = sum(
        1
        for s in payload["sites"]
        if any(
            m.get("reading_id") in doctrine_readings
            for m in s.get("applicable_readings", [])
        )
    )
    fams = sorted(
        {
            readings[m["reading_id"]]["statute"]
            for s in payload["sites"]
            for m in s.get("applicable_readings", [])
            if m.get("reading_id") in doctrine_readings
        }
    )
    print(f"doctrine mappings written: {added} ({negatives} negative)")
    print(f"sites with at least one doctrine mapping: {covered} of {len(payload['sites'])}")
    print(f"doctrine families reaching a site: {len(fams)}  {fams}")
    unreached = sorted(doctrine_families - set(fams))
    if unreached:
        print(f"families not yet mapped to any site: {unreached}")

    if problems:
        print("\nAborted:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    if args.dry_run:
        print("\n(dry run — nothing written)")
        return 0

    payload["last_updated"] = "2026-07-26"
    CONFLICTS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("\nWrote dc_water_conflicts.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
