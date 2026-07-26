#!/usr/bin/env python3
"""Precedent engine batch 2: well review, common law, utility service, ESA.

Plan Spec C1/C2, continuing from batch 1 (EQAP / PTD / GW). These four
families cover the ways a water fight reaches a data center *without* a
federal discharge permit: the state agency reviewing a high-capacity well, the
neighbour suing in tort, the municipal utility deciding whether it must serve,
and the endangered species downstream.

Two corrections to the plan's seed list, both found during verification:

* The Michigan standing limit is the **2007 Michigan Supreme Court** decision
  (479 Mich. 280), not the 2005 Court of Appeals decision at 269 Mich. App. 25
  that the plan cited. The 2005 panel *found* standing; the Supreme Court
  reversed it two years later. Citing the Court of Appeals would have had the
  reading say the opposite of what the law is.
* Swanson is narrower than the plan's summary. The court did not announce a
  "continuing duty to augment supply"; it held that a would-be new user has no
  absolute right to service and that the district's moratorium is reviewable
  only for fraud, arbitrariness or caprice. The reading says that instead.

Run: ``python3 scripts/add_doctrine_families_batch2.py [--dry-run]``
Idempotent.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _doctrine_batch import apply_batch  # noqa: E402

NEW_STATUTES = {
    "WELL": {
        "name": "High-capacity well & withdrawal-permit review",
        "full_name": (
            "State review of high-capacity well and large-withdrawal permits — the "
            "agency's duty to consider cumulative and off-site impacts before issuing"
        ),
        "agencies": "State natural-resource agencies; state courts",
        "kind": "state-doctrine",
        "url": "https://www.law.cornell.edu/wex/water_rights",
    },
    "CL": {
        "name": "Common-law interference, nuisance & standing",
        "full_name": (
            "Common-law limits on groundwater withdrawal — negligence, subsidence, "
            "nuisance — and the standing rules that govern who may sue"
        ),
        "agencies": "State courts",
        "kind": "common-law",
        "url": "https://www.law.cornell.edu/wex/nuisance",
    },
    "UTIL": {
        "name": "Municipal utility service & shortage law",
        "full_name": (
            "The law governing whether a public water utility must serve a new "
            "large customer, and when it may refuse or impose a connection moratorium"
        ),
        "agencies": "Municipal utilities and districts; state courts",
        "kind": "state-doctrine",
        "url": "https://www.law.cornell.edu/wex/public_utility",
    },
    "ESA": {
        "name": "Endangered Species Act as a water constraint",
        "full_name": "Endangered Species Act, 16 U.S.C. §§1531–1544 (esp. §7 and §9 take)",
        "agencies": "U.S. Fish and Wildlife Service; NOAA Fisheries; federal courts",
        "kind": "federal-statute",
        "url": "https://www.law.cornell.edu/uscode/text/16/chapter-35",
    },
}

NEW_READINGS = [
    {
        "reading_id": "well-cumulative-impact",
        "statute": "WELL",
        "section": "State high-capacity well permitting — agency duty to consider harm to waters of the state",
        "name": "The permitting agency must weigh a well's off-site impact",
        "agency": "State natural-resource agencies",
        "what_it_covers": (
            "Whether an agency issuing a high-capacity well permit must look beyond the "
            "applicant's own parcel. Where the state holds navigable waters in trust and "
            "the permitting statute protects waters of the state generally, the agency "
            "has both authority and a general duty to consider whether the proposed well "
            "may harm those waters — but the duty is triggered by concrete scientific "
            "evidence of potential harm, not by objection alone."
        ),
        "dc_applicability": (
            "The most practically usable doctrine in the registry for an opponent, "
            "because it operates at the permit stage rather than after the damage. It "
            "also sets the price of admission: objections to a data-center well must "
            "arrive as hydrologic evidence, since generalized concern does not trigger "
            "the agency's duty. That is precisely the bind sites in this dataset "
            "describe — the evidence needs consumption data the operator holds."
        ),
        "example_case_ids": ["Lake-Beulah-v-DNR-2011"],
    },
    {
        "reading_id": "cl-negligent-subsidence",
        "statute": "CL",
        "section": "Negligence, willful waste and malicious injury as limits on the rule of capture",
        "name": "Capture shields depletion, not negligent harm",
        "agency": "State courts",
        "what_it_covers": (
            "In rule-of-capture states a landowner may generally pump without liability "
            "for draining a neighbour. That immunity is not total: where the *manner* of "
            "withdrawal is negligent, willfully wasteful or malicious and proximately "
            "causes damage to another's land — the classic case being subsidence from "
            "closely spaced high-volume wells — the pumper is liable."
        ),
        "dc_applicability": (
            "The opening in an otherwise closed door. A neighbour in a capture state "
            "cannot complain that a data center took the water, but can complain about "
            "how: well spacing, siting near a boundary, and pumping rates chosen despite "
            "engineering forecasts of subsidence. Coastal and alluvial settings are where "
            "this bites, because that is where measurable subsidence follows drawdown."
        ),
        "example_case_ids": ["Friendswood-v-Smith-Southwest-1978"],
    },
    {
        "reading_id": "cl-citizen-standing-limit",
        "statute": "CL",
        "section": "Standing under state environmental-protection statutes — particularized injury",
        "name": "The standing trap for opposition groups",
        "agency": "State courts",
        "what_it_covers": (
            "How far a statutory 'any person may sue' provision actually reaches. A "
            "citizens' group may sue over a withdrawal that injures its members' own "
            "recreational, aesthetic, economic or property interests, but not over harm "
            "to the environment at large — the injury must be concrete and "
            "particularized to identifiable members."
        ),
        "dc_applicability": (
            "Explains a pattern visible across this dataset: why data-center opposition "
            "succeeds through zoning votes, moratoriums and records requests far more "
            "often than through lawsuits. A group organized around a watershed rather "
            "than around injured members can be dismissed before the merits. It also "
            "says which plaintiff wins — the household whose well failed, not the "
            "coalition, which is why the Newton County fact pattern is legally stronger "
            "than a general-harm campaign."
        ),
        "example_case_ids": ["MCWC-v-Nestle-Waters-2007"],
    },
    {
        "reading_id": "util-shortage-moratorium",
        "statute": "UTIL",
        "section": "Municipal water service — no right to new service; moratorium review",
        "name": "A utility may refuse to serve a new large customer",
        "agency": "Municipal utilities and districts; state courts",
        "what_it_covers": (
            "A prospective new water user holds no absolute right to service and need "
            "not be treated like established customers. Where a utility faces a genuine "
            "imbalance between supply and demand it has a rational basis for a "
            "moratorium on new connections, and a court will disturb that decision only "
            "for fraud, arbitrariness or caprice."
        ),
        "dc_applicability": (
            "Runs the opposite way from how these fights are usually argued. The tracked "
            "conflicts assume the utility is under pressure to say yes; this reading says "
            "a utility facing real supply constraint is on strong legal ground saying no, "
            "and the data center has no entitlement to be served. Where a utility has "
            "already conceded on the record that it cannot serve the load without major "
            "upgrades — Bessemer being the clearest instance here — that admission is the "
            "rational basis a refusal would rest on."
        ),
        "example_case_ids": ["Swanson-v-Marin-MWD-1976"],
    },
    {
        "reading_id": "esa-proximate-cause-limit",
        "statute": "ESA",
        "section": "ESA §9 take, 16 U.S.C. §1538 — proximate cause between state permitting and downstream harm",
        "name": "State water permitting is usually too remote to be a take",
        "agency": "Federal courts; U.S. Fish and Wildlife Service",
        "what_it_covers": (
            "Whether a state agency's issuance of upstream withdrawal permits can be the "
            "proximate cause of downstream harm to a listed species. The Fifth Circuit "
            "held it cannot on the record before it: with multiple natural, independent "
            "and unpredictable forces acting on the habitat, the causal chain from permit "
            "to death of the animals was not reasonably foreseeable, and the injunction "
            "against further permitting was an abuse of discretion."
        ),
        "dc_applicability": (
            "Included as a *negative* reading, because knowing where a theory fails is "
            "worth as much as knowing where it works. ESA is the intuitive federal hook "
            "for a data center drying a river reach, and in the Fifth Circuit this is "
            "binding law that the hook will usually miss when the defendant is the state "
            "permitting authority. A §9 claim would need to run at the withdrawer "
            "directly, with a much shorter causal chain than 'permit issued, species "
            "died'."
        ),
        "example_case_ids": ["Aransas-Project-v-Shaw-2014"],
    },
]

NEW_CASES = [
    {
        "case_id": "Lake-Beulah-v-DNR-2011",
        "category": "precedent",
        "respondent": "Lake Beulah Management District v. Wisconsin Department of Natural Resources, 2011 WI 54",
        "year": "2011",
        "cwa_section": "Not a Clean Water Act case — Wisconsin high-capacity well permitting and the public trust doctrine",
        "violation_summary": (
            "The DNR issued the Village of East Troy a high-capacity well permit near "
            "Lake Beulah. The lake district argued the agency had to evaluate the well's "
            "effect on the lake before permitting it, and that it had failed to do so — "
            "an eight-year dispute over how far the agency's review obligation runs."
        ),
        "outcome": (
            "The Wisconsin Supreme Court held that the DNR has both the authority and a "
            "general duty, grounded in the public trust doctrine and the permitting "
            "statutes, to consider whether a proposed high-capacity well may harm waters "
            "of the state — but that the duty is triggered only when the agency is "
            "presented with sufficient concrete, scientific evidence of potential harm. "
            "On this record it had not been, so the permit stood."
        ),
        "takeaway": (
            "The most directly usable doctrine here for anyone contesting a data-center "
            "well, because it operates before the water is pumped rather than after the "
            "harm. It also states the price of admission plainly: objections must arrive "
            "as hydrologic evidence, not as concern. That is the bind these conflicts "
            "keep hitting — the evidence needed to trigger the duty depends on "
            "consumption and drawdown data the operator and the utility hold. Wisconsin "
            "makes this concrete for the tracker, since Microsoft's Mount Pleasant campus "
            "sits in the same permitting system."
        ),
        "analogous_cases": [
            "Microsoft-CaledoniaWI-rezoning-withdrawal-2025",
            "MilwaukeeRiverkeeper-RacineWI-water-records-suit-2025",
        ],
        "sources": [
            {
                "title": "Lake Beulah Management District v. DNR, 2011 WI 54 — Wisconsin Supreme Court opinion",
                "url": "https://www.wicourts.gov/sc/opinion/DisplayDocument.pdf?content=pdf&seqNo=67354",
                "type": "court ruling",
            },
            {
                "title": "Wisconsin Supreme Court Upholds Village of East Troy's High Capacity Well Permit; Finds WDNR Has a General Duty to Consider Impact to Waters of the State",
                "url": "https://www.natlawreview.com/article/wisconsin-supreme-court-upholds-village-east-troy-s-high-capacity-well-permit-finds-wdnr-has",
                "type": "law review",
            },
        ],
        "case_type": "groundwater",
        "cwa_applied": "not-applied",
        "cwa_instrument": "Wis. Supreme Court — agency duty to consider well impacts on waters of the state",
        "cwa_pathway": (
            "Reaches a data center at the well-permit stage: a challenge to the state "
            "agency for issuing without evaluating impact, which succeeds only if "
            "objectors put concrete hydrologic evidence in front of the agency first."
        ),
        "display_section": "historical",
        "authorities": ["well-cumulative-impact"],
    },
    {
        "case_id": "Friendswood-v-Smith-Southwest-1978",
        "category": "precedent",
        "respondent": "Friendswood Development Co. v. Smith-Southwest Industries, Inc., 576 S.W.2d 21 (Tex. 1978)",
        "year": "1978",
        "cwa_section": "Not a Clean Water Act case — Texas rule of capture; negligence and subsidence",
        "violation_summary": (
            "Friendswood drilled wells between 1964 and 1971 and pumped large volumes of "
            "groundwater for sale to industrial users, despite engineering reports "
            "predicting land subsidence. Neighbours alleged the wells were negligently "
            "spaced too closely and too near the property boundary, and that excessive "
            "production caused subsidence and flooding on their land."
        ),
        "outcome": (
            "The Texas Supreme Court held the ordinary duty not to use property so as to "
            "injure others does not apply to groundwater withdrawal, which remains an "
            "absolute right outside the reasonable-use rule — but announced a prospective "
            "exception: for wells drilled or produced after the decision, negligent, "
            "willfully wasteful or malicious withdrawal that proximately causes "
            "subsidence damage to another's land creates liability. The defendants, "
            "having relied on the prior rule, were not liable."
        ),
        "takeaway": (
            "The crack in the rule of capture, and the reason a neighbour's strongest "
            "claim against a data center in a capture state is about *how* it pumps "
            "rather than *that* it pumps. Well spacing, proximity to boundaries and rates "
            "chosen against engineering advice are all in scope. It matters most in "
            "coastal and alluvial settings where drawdown produces measurable subsidence "
            "— which is exactly the Gulf-coast hydrology of the Texas sites tracked here."
        ),
        "analogous_cases": [
            "CorpusChristi-SintonTX-EvangelineAquifer-wells-2026",
            "Sailfish-HoodCountyTX-ComancheCircle-aquifer-moratorium-2025-2026",
        ],
        "sources": [
            {
                "title": "Friendswood Devel. Co. v. Smith-Southwest Indus., Inc. (Tex. 1978) — full opinion",
                "url": "https://law.justia.com/cases/texas/supreme-court/1978/b-6682-0.html",
                "type": "court ruling",
            },
            {
                "title": "Friendswood Development Co. v. Smith-Southwest Industries, Inc., 576 S.W.2d 21 — opinion text",
                "url": "https://www.courtlistener.com/opinion/2363223/friendswood-devel-co-v-smith-southwest-indus-inc/",
                "type": "court ruling",
            },
            {
                "title": "Smith-Southwest Industries v. Friendswood Development Co. — Environmental Law Reporter case record",
                "url": "https://www.elr.info/sites/default/files/litigation/9.20452.htm",
                "type": "law review",
            },
        ],
        "case_type": "groundwater",
        "cwa_applied": "not-applied",
        "cwa_instrument": "Tex. Supreme Court — negligence exception to the rule of capture for subsidence",
        "cwa_pathway": (
            "A private tort claim by an adjoining landowner against the data center or "
            "its water supplier, pleading negligent well siting, spacing or pumping rate "
            "rather than the fact of withdrawal."
        ),
        "display_section": "historical",
        "authorities": ["cl-negligent-subsidence"],
    },
    {
        "case_id": "MCWC-v-Nestle-Waters-2007",
        "category": "precedent",
        "respondent": "Michigan Citizens for Water Conservation v. Nestlé Waters North America Inc., 479 Mich. 280, 737 N.W.2d 447 (2007)",
        "year": "2007",
        "cwa_section": "Not a Clean Water Act case — standing under the Michigan Environmental Protection Act",
        "violation_summary": (
            "A citizens' group challenged Nestlé's groundwater extraction at Sanctuary "
            "Springs in Mecosta County, arguing the pumping harmed the Dead Stream, "
            "Osprey Lake and surrounding wetlands, and relying on MEPA's provision "
            "allowing 'any person' to sue."
        ),
        "outcome": (
            "The Michigan Supreme Court reversed the Court of Appeals' holding that the "
            "group had standing over Osprey Lake and three wetlands. It held the group "
            "could sue under MEPA only for concrete, particularized injuries in fact "
            "suffered by its own members — extraction affecting members' recreational, "
            "aesthetic, economic or property interests — and not for harm to the "
            "environment in general, notwithstanding the statute's 'any person' language."
        ),
        "takeaway": (
            "The procedural reason so much data-center opposition in this dataset runs "
            "through zoning votes, moratoriums and records requests rather than "
            "litigation: a watershed coalition can lose before the merits are reached. It "
            "also identifies the right plaintiff. A household whose own well failed has "
            "the particularized injury a coalition lacks, which is why the Newton County "
            "fact pattern is a stronger case than a general-harm campaign against a "
            "larger withdrawal. Michigan matters directly here — its 2026 data-center "
            "bills would create the withdrawal permits such a suit would contest."
        ),
        "analogous_cases": [
            "Meta-NewtonCountyGA-well-failures-2018-2025",
            "MCEA-PineIsland-MN-ProjectSkyway-2026",
        ],
        "sources": [
            {
                "title": "Michigan Citizens for Water Conservation v. Nestlé Waters North America Inc. (2007) — Michigan Supreme Court opinion",
                "url": "https://law.justia.com/cases/michigan/supreme-court/2007/20070725-s130802-168-nestle130802-op.html",
                "type": "court ruling",
            },
            {
                "title": "Michigan Citizens for Water Conservation v. Bollman (2007) — full text",
                "url": "https://caselaw.findlaw.com/court/mi-supreme-court/1363710.html",
                "type": "court ruling",
            },
            {
                "title": "Court Limits Standing to Prevent Bottled Water Plant from Draining Wetlands",
                "url": "https://www.michiganlcv.org/case/court-limits-standing-prevent-bottled-water-plant-draining-wetlands/",
                "type": "advocacy",
            },
        ],
        "case_type": "legal-doctrine",
        "cwa_applied": "not-applied",
        "cwa_instrument": "Mich. Supreme Court — MEPA standing requires particularized injury",
        "cwa_pathway": (
            "Governs who may bring a state environmental claim against a data-center "
            "withdrawal at all. The pathway is defensive: it is the doctrine an operator "
            "invokes to dismiss an opposition group before the merits."
        ),
        "display_section": "historical",
        "authorities": ["cl-citizen-standing-limit"],
    },
    {
        "case_id": "Swanson-v-Marin-MWD-1976",
        "category": "precedent",
        "respondent": "Swanson v. Marin Municipal Water District, 56 Cal. App. 3d 512 (1976)",
        "year": "1976",
        "cwa_section": "Not a Clean Water Act case — California municipal water service and connection moratoria",
        "violation_summary": (
            "The district adopted a moratorium on new water connections after finding "
            "projected consumption would exceed its safe yield. Swanson, who had "
            "approvals to build a home, was refused a pipeline extension and sued; the "
            "trial court found the moratorium unsupported by an immediate shortage and "
            "unauthorized by statute."
        ),
        "outcome": (
            "The Court of Appeal reversed. A prospective water user has no absolute right "
            "to service and is not constitutionally entitled to be treated the same as "
            "established users. Facing a genuine imbalance between supply and demand, the "
            "district had a rational basis for the moratorium and had not acted "
            "fraudulently, arbitrarily or capriciously."
        ),
        "takeaway": (
            "Read in reverse, this is the utility's shield in a data-center fight — and "
            "it inverts how these disputes are usually framed. The assumption running "
            "through the tracked conflicts is that a utility is under pressure to serve a "
            "large new load; Swanson says a utility facing real supply constraint may "
            "refuse, and that the would-be customer has no entitlement to be served. "
            "Bessemer is the sharp case: the authority conceded on the record that it "
            "could not serve 2 MGD without significant upgrades, which is precisely the "
            "rational basis a refusal would stand on."
        ),
        "analogous_cases": [
            "Bessemer-AL-Hyperscale-WaterSupply-2025",
            "Charlotte-NC-drought-datacenter-moratorium-2026",
        ],
        "sources": [
            {
                "title": "Swanson v. Marin Mun. Water Dist., 56 Cal. App. 3d 512 (1976) — full opinion",
                "url": "https://law.justia.com/cases/california/court-of-appeal/3d/56/512.html",
                "type": "court ruling",
            },
            {
                "title": "Time to Dust Off California Water Law On Development Moratoria",
                "url": "https://www.swlaw.com/blogs/environmental-and-natural-resources/2014/10/01/time-to-dust-off-california-water-law-on-development-moratoria/",
                "type": "law review",
            },
        ],
        "case_type": "water-supply",
        "cwa_applied": "not-applied",
        "cwa_instrument": "Cal. Court of Appeal — no right to new service; moratorium upheld on rational basis",
        "cwa_pathway": (
            "Two uses: as the legal basis for a utility or municipality declining to "
            "serve a data-center load, and as the standard a developer must meet to "
            "overturn such a refusal — fraud, arbitrariness or caprice, not mere "
            "disagreement about capacity."
        ),
        "display_section": "historical",
        "authorities": ["util-shortage-moratorium"],
    },
    {
        "case_id": "Aransas-Project-v-Shaw-2014",
        "category": "precedent",
        "respondent": "The Aransas Project v. Shaw, 775 F.3d 641 (5th Cir. 2014)",
        "year": "2014",
        "cwa_section": "Not a Clean Water Act case — Endangered Species Act §9 take, 16 U.S.C. §1538",
        "violation_summary": (
            "After 23 endangered whooping cranes died in the winter of 2008-09, an "
            "environmental group sued the Texas Commission on Environmental Quality, "
            "arguing that its administration of water-withdrawal permits on the Guadalupe "
            "and San Antonio rivers reduced freshwater inflows to the birds' estuary and "
            "caused an unlawful take. The district court agreed and enjoined TCEQ from "
            "issuing new withdrawal permits."
        ),
        "outcome": (
            "The Fifth Circuit reversed. The district court had misapplied proximate "
            "cause: a state agency's licensing of private upstream withdrawals was not a "
            "foreseeable cause of downstream crane deaths given the multiple natural, "
            "independent and interrelated forces acting on the habitat. The court added "
            "that even had proximate cause been shown, the injunction was an abuse of "
            "discretion."
        ),
        "takeaway": (
            "Carried here as a *negative* precedent, because a registry that only "
            "collects theories that work will mislead. The Endangered Species Act is the "
            "intuitive federal hook when a data center's draw dries a river reach, and in "
            "the Fifth Circuit this is binding law that the hook will usually miss when "
            "the defendant is the permitting agency. A viable §9 claim has to target the "
            "withdrawer directly with a far shorter causal chain. It bears directly on "
            "the Texas Gulf-coast sites tracked here, which sit in the same hydrology and "
            "the same circuit."
        ),
        "analogous_cases": [
            "CorpusChristi-SintonTX-EvangelineAquifer-wells-2026",
            "Meta-RichlandParish-LA-WaterSupply-2025",
        ],
        "sources": [
            {
                "title": "The Aransas Project v. Shaw, 775 F.3d 641 (5th Cir. 2014) — opinion",
                "url": "https://www.ca5.uscourts.gov/opinions%5Cpub%5C13/13-40317-CV0.pdf",
                "type": "court ruling",
            },
            {
                "title": "Aransas Project v. Guadalupe-Blanco River Authority (2014) — full text",
                "url": "https://caselaw.findlaw.com/court/us-5th-circuit/1688805.html",
                "type": "court ruling",
            },
            {
                "title": "Litigating the 'butterfly effect': Proximate Cause, Imminent Harm and Endangered Whooping Cranes",
                "url": "https://acoel.org/litigating-the-butterfly-effect-proximate-cause-imminent-harm-and-endangered-whooping-cranes/",
                "type": "law review",
            },
        ],
        "case_type": "legal-doctrine",
        "cwa_applied": "not-applied",
        "cwa_instrument": "5th Cir. — state water permitting too remote to proximately cause an ESA take",
        "cwa_pathway": (
            "Marks where an ESA theory fails rather than where it works: suing the "
            "permitting agency for downstream species harm is foreclosed in this circuit. "
            "A claim would have to run against the withdrawing facility itself."
        ),
        "display_section": "historical",
        "authorities": ["esa-proximate-cause-limit"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return apply_batch(
        NEW_STATUTES,
        NEW_READINGS,
        NEW_CASES,
        last_updated="2026-07-25",
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
