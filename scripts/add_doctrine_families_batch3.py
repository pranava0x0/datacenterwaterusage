#!/usr/bin/env python3
"""Precedent engine batch 3: statutory groundwater regimes, transfers, tribal, state review.

Plan Spec C1/C2, continuing from batches 1 and 2. Four families:

* ``GWMGMT`` — the statutory regimes that actually govern pumping in the arid
  West. Arizona's assured-water-supply rules, not common-law reasonable use,
  are what a Tucson data center answers to.
* ``XFER`` — moving water between basins, and the junior-priority penalty that
  attaches when you do.
* ``TRIBAL`` — federal reserved rights, which outrank state allocations
  regardless of when the tribe started using the water.
* ``SEPA`` — state environmental review of whether a project's claimed
  long-term water supply is real.

Two of these anchor on matters the tracker already follows rather than on new
historical cases, using the ``authority_additions`` hook: the Tucson fight
illustrates the Arizona AMA regime better than any 1980s precedent would, and
Pine Island is already the live state-environmental-review case. That is the
point of the registry — connecting doctrine to what is actually happening.

The fifth planned family, ``SL`` (state consumer-protection / greenwashing),
is deliberately held for Spec A2: its only anchor is the AWS water-claims
suit, so the family and its case belong in the same commit.

Run: ``python3 scripts/add_doctrine_families_batch3.py [--dry-run]``
Idempotent.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _doctrine_batch import apply_batch  # noqa: E402

NEW_STATUTES = {
    "GWMGMT": {
        "name": "Statutory groundwater-management regimes",
        "full_name": (
            "State statutory groundwater management — Arizona's Groundwater "
            "Management Act and Active Management Areas, California's Sustainable "
            "Groundwater Management Act, and comparable large-withdrawal regimes"
        ),
        "agencies": "State water resource departments; groundwater sustainability agencies",
        "kind": "state-doctrine",
        "url": "https://www.law.cornell.edu/wex/water_rights",
    },
    "XFER": {
        "name": "Water sourcing & inter-basin transfer law",
        "full_name": (
            "Statutory limits on moving water between basins and on holding rights "
            "unused — area-of-origin protection, junior-priority rules on transfer, "
            "and forfeiture or abandonment regimes"
        ),
        "agencies": "State environmental commissions; water courts",
        "kind": "state-doctrine",
        "url": "https://texas.public.law/statutes/tex._water_code_section_11.085",
    },
    "TRIBAL": {
        "name": "Federal & tribal reserved water rights",
        "full_name": (
            "Winters doctrine reserved rights — water impliedly reserved when the "
            "federal government sets land aside, senior to later state-law rights "
            "and extending to groundwater"
        ),
        "agencies": "Federal courts; Department of the Interior; tribal governments",
        "kind": "federal-doctrine",
        "url": "https://www.law.cornell.edu/wex/winters_doctrine",
    },
    "SEPA": {
        "name": "State environmental review & water-supply adequacy",
        "full_name": (
            "State environmental review statutes as applied to water — whether a "
            "project's environmental document must demonstrate a realistic long-term "
            "supply before approval"
        ),
        "agencies": "Lead agencies under state review statutes; state courts",
        "kind": "state-doctrine",
        "url": "https://www.law.cornell.edu/wex/environmental_law",
    },
}

NEW_READINGS = [
    {
        "reading_id": "gwmgmt-az-ama",
        "statute": "GWMGMT",
        "section": "Arizona Groundwater Management Act of 1980 — Active Management Areas and assured water supply",
        "name": "Assured-water-supply rules inside an Active Management Area",
        "agency": "Arizona Department of Water Resources",
        "what_it_covers": (
            "Inside an Active Management Area, groundwater is governed by statute "
            "rather than by common-law pumping rights: withdrawals are permitted and "
            "metered, and new development must demonstrate an assured supply — water "
            "physically and legally available for a century — before it can proceed."
        ),
        "dc_applicability": (
            "This, and not the common-law reasonable-use rule, is what an Arizona data "
            "center actually answers to, which is why Arizona fights look different "
            "from Georgia or Texas ones: the question is decided in a statutory "
            "supply-designation process rather than in a nuisance suit. It cuts both "
            "ways — the regime is a real constraint on new demand, and it also gives a "
            "project that clears it a defensible answer to critics."
        ),
        "example_case_ids": ["ProjectBlue-Tucson-AMES-2026"],
    },
    {
        "reading_id": "gwmgmt-sgma",
        "statute": "GWMGMT",
        "section": "California Sustainable Groundwater Management Act, Cal. Water Code §10720 et seq.",
        "name": "Basin sustainability plans, and what they do not displace",
        "agency": "Groundwater sustainability agencies; California Water Board",
        "what_it_covers": (
            "Requires local agencies in high- and medium-priority basins to adopt plans "
            "achieving sustainable yield and avoiding undesirable results including "
            "chronic lowering of groundwater levels. Critically, the statute is a floor "
            "rather than a ceiling: enacting it did not occupy the field or extinguish "
            "the public-trust duty that runs alongside it."
        ),
        "dc_applicability": (
            "Sets the numeric constraint a large new California groundwater user has to "
            "fit inside, and answers the compliance defence in advance. An operator "
            "pointing to its sustainability-plan allocation has not thereby answered a "
            "public-trust objection, because the two obligations coexist."
        ),
        "example_case_ids": ["ELF-v-SWRCB-2018"],
    },
    {
        "reading_id": "xfer-area-of-origin",
        "statute": "XFER",
        "section": "Tex. Water Code §11.085 — inter-basin transfers junior in priority",
        "name": "Moving water between basins costs you your seniority",
        "agency": "Texas Commission on Environmental Quality",
        "what_it_covers": (
            "No one may divert state water from one river basin to another without a "
            "water right or permit amendment authorizing the transfer, and any right "
            "transferred out of basin becomes junior in priority to every right granted "
            "in the basin of origin before the transfer application was filed. In a "
            "shortage the transferred water is cut first."
        ),
        "dc_applicability": (
            "The sharpest and least-used tool against a campus supplied by out-of-basin "
            "piping. Opposition to these projects is usually political — hearings, "
            "petitions, county votes — when the statute already imposes a structural "
            "penalty: the transferred supply sits at the back of the priority queue "
            "exactly when drought makes it matter. Worth checking wherever a project's "
            "water arrives from a reservoir in another basin."
        ),
        "example_case_ids": ["Rowan-ProjectCinco-Medina-TX-2025"],
    },
    {
        "reading_id": "tribal-winters",
        "statute": "TRIBAL",
        "section": "Winters doctrine — implied reservation of water, 207 U.S. 564 (1908)",
        "name": "Reserved rights are senior to everything that came after",
        "agency": "Federal courts; Department of the Interior",
        "what_it_covers": (
            "Setting land aside for a federal purpose impliedly reserves enough water to "
            "serve that purpose. The priority date is the date the reservation was "
            "created, not the date use began — so reserved rights are typically senior "
            "to nearly every state-law right in the basin, and are unaffected by a "
            "state's later admission to the Union or its own allocation scheme."
        ),
        "dc_applicability": (
            "Matters wherever a campus draws from a basin that also serves a "
            "reservation, which describes much of the arid Southwest. The exposure is "
            "not that a tribe sues the data center — it is that quantifying a senior "
            "reserved right shrinks the pool the state had been allocating, and junior "
            "users get cut in order. A supply contract resting on a junior state-law "
            "right is worth less than it appears in such a basin."
        ),
        "example_case_ids": ["Winters-v-United-States-1908"],
    },
    {
        "reading_id": "tribal-groundwater",
        "statute": "TRIBAL",
        "section": "Reserved rights extend to groundwater — Agua Caliente, 849 F.3d 1262 (9th Cir. 2017)",
        "name": "The reserved right reaches the aquifer, not just the river",
        "agency": "Federal courts",
        "what_it_covers": (
            "The Winters doctrine draws no line between surface water and groundwater. "
            "Where the United States reserved land in an arid region, it impliedly "
            "reserved the appurtenant water sources including groundwater; the tribe's "
            "not having historically pumped does not forfeit the right, and state water "
            "law is preempted where the two conflict."
        ),
        "dc_applicability": (
            "Closes the escape route. A project can be told a basin's surface water is "
            "fully claimed and turn to wells instead — this says the senior federal "
            "right follows it underground. In arid basins with a reservation overlying "
            "or adjoining the aquifer, groundwater is not the unencumbered alternative "
            "it is usually treated as."
        ),
        "example_case_ids": ["Agua-Caliente-v-CVWD-2017"],
    },
    {
        "reading_id": "sepa-supply-adequacy",
        "statute": "SEPA",
        "section": "State environmental review — long-term water supply must be realistic, not on paper",
        "name": "An environmental document must show water that actually exists",
        "agency": "Lead agencies under state environmental review statutes; state courts",
        "what_it_covers": (
            "An environmental impact document approving a large project must identify "
            "and analyse the water supply for the project's full life, not merely its "
            "first phase. Deferring the analysis to a future regional planning document, "
            "or relying on a mitigation measure that would curtail development if the "
            "water never materializes, is procedurally inadequate — as is leaving "
            "unexplained discrepancies between claimed supply and regional estimates."
        ),
        "dc_applicability": (
            "The most transferable procedural attack on a data-center approval, because "
            "it does not require proving hydrologic harm — only that the paperwork "
            "assumed water it could not demonstrate. Campus approvals routinely analyse "
            "phase one and defer the rest, which is the precise defect this reading "
            "names. It is also the doctrine that most often produces the outcome "
            "opponents actually want: the approval is vacated and redone, rather than "
            "damages awarded years later."
        ),
        "example_case_ids": ["Vineyard-v-Rancho-Cordova-2007"],
    },
    {
        "reading_id": "sepa-review-injunction",
        "statute": "SEPA",
        "section": "State environmental review — interim relief where water disclosure is inadequate",
        "name": "Inadequate water disclosure can stop the project now",
        "agency": "State courts",
        "what_it_covers": (
            "Where a challenger shows a state environmental review failed to disclose a "
            "project's water impacts adequately, courts have treated proceeding on that "
            "record as irreparable harm and granted interim relief rather than leaving "
            "the challenge to be resolved after construction."
        ),
        "dc_applicability": (
            "The timing half of the supply-adequacy reading, and the reason state "
            "environmental review outranks most federal theories in practice for these "
            "projects: it can halt work while the dispute is live. Data-center "
            "construction moves faster than litigation, so a remedy that only arrives "
            "after the campus is built is not much of a remedy."
        ),
        "example_case_ids": ["MCEA-PineIsland-MN-ProjectSkyway-2026"],
    },
]

NEW_CASES = [
    {
        "case_id": "Winters-v-United-States-1908",
        "category": "precedent",
        "respondent": "Winters v. United States, 207 U.S. 564 (1908)",
        "year": "1908",
        "cwa_section": "Not a Clean Water Act case — implied federal reservation of water rights",
        "violation_summary": (
            "Settlers upstream of the Fort Belknap Reservation in Montana built dams, "
            "ditches and canals diverting the Milk River for irrigation, cutting off the "
            "flow reaching the reservation. The United States sued on the tribes' behalf "
            "to enjoin the diversions."
        ),
        "outcome": (
            "The Supreme Court held that the 1888 agreement establishing the reservation "
            "impliedly reserved enough Milk River water to serve its purposes, and that "
            "Montana's admission to the Union the following year did not disturb that "
            "reservation. The reserved right dates from the creation of the reservation, "
            "making it senior to the settlers' later state-law claims."
        ),
        "takeaway": (
            "The oldest doctrine in this registry and, in the arid West, often the most "
            "consequential — because it operates on priority rather than on conduct. A "
            "data center never has to do anything wrong for this to matter: quantifying "
            "a senior reserved right shrinks the pool the state had been allocating, and "
            "junior users are cut in order of seniority. A campus whose supply contract "
            "rests on a junior state-law right in a basin serving a reservation holds "
            "something worth less than its face value, and that is a due-diligence "
            "question rather than a litigation risk."
        ),
        "analogous_cases": [
            "ProjectBlue-Tucson-AMES-2026",
            "Mississippi-v-Tennessee-2021",
        ],
        "sources": [
            {
                "title": "Winters v. United States, 207 U.S. 564 (1908) — full opinion",
                "url": "https://supreme.justia.com/cases/federal/us/207/564/",
                "type": "court ruling",
            },
            {
                "title": "Indian Reserved Water Rights Under the Winters Doctrine: An Overview (Congressional Research Service)",
                "url": "https://www.everycrsreport.com/reports/RL32198.html",
                "type": "law review",
            },
            {
                "title": "The Winters Doctrine: The Foundation of Tribal Water Rights",
                "url": "https://itcaonline.com/programs/tribal-leaders-water-policy-council/the-winters-doctrine-the-foundation-of-tribal-water-rights/",
                "type": "advocacy",
            },
        ],
        "case_type": "legal-doctrine",
        "cwa_applied": "not-applied",
        "cwa_instrument": "SCOTUS — water impliedly reserved with the reservation, senior to later state rights",
        "cwa_pathway": (
            "Reaches a data center indirectly and structurally: not as a claim against "
            "the operator, but as a senior right that reduces what the state can "
            "allocate to it, in any basin serving a federal reservation."
        ),
        "display_section": "historical",
        "authorities": ["tribal-winters"],
    },
    {
        "case_id": "Agua-Caliente-v-CVWD-2017",
        "category": "precedent",
        "respondent": "Agua Caliente Band of Cahuilla Indians v. Coachella Valley Water District, 849 F.3d 1262 (9th Cir. 2017)",
        "year": "2017",
        "cwa_section": "Not a Clean Water Act case — federal reserved water rights extended to groundwater",
        "violation_summary": (
            "The Agua Caliente Band sued two water districts in California's arid "
            "Coachella Valley, seeking a declaration that its reserved rights extend to "
            "the groundwater beneath the reservation. The districts argued the Winters "
            "doctrine covers surface water only, and that the tribe had never "
            "historically pumped."
        ),
        "outcome": (
            "The Ninth Circuit affirmed for the tribe. The Winters doctrine does not "
            "distinguish surface water from groundwater; the United States impliedly "
            "reserved appurtenant water sources including groundwater when it created "
            "the reservation in an arid region. Historical non-use does not defeat the "
            "right, and state water rights are preempted where they conflict. The "
            "Supreme Court denied certiorari."
        ),
        "takeaway": (
            "Removes the assumption that groundwater is the unencumbered fallback. A "
            "project told a basin's surface water is spoken for will look to wells; in "
            "the Ninth Circuit, a senior federal reserved right follows it there. That "
            "matters directly for the Southwest data-center corridor, where the surface "
            "supply is over-allocated, groundwater is the growth path, and reservations "
            "overlie or adjoin many of the aquifers involved. The exposure runs through "
            "the supply contract rather than through any conduct by the operator."
        ),
        "analogous_cases": [
            "ProjectBlue-Tucson-AMES-2026",
            "Winters-v-United-States-1908",
        ],
        "sources": [
            {
                "title": "Agua Caliente Band of Cahuilla Indians v. Coachella Valley Water District, No. 15-55896 (9th Cir. 2017)",
                "url": "https://law.justia.com/cases/federal/appellate-courts/ca9/15-55896/15-55896-2017-03-07.html",
                "type": "court ruling",
            },
            {
                "title": "Agua Caliente Band of Cahuilla Indians v. Coachella Valley Water District — Indian Law Bulletin",
                "url": "https://www.narf.org/nill/bulletins/federal/documents/agua_caliente_v_coachella_water.html",
                "type": "court ruling",
            },
            {
                "title": "A Tribe's Successful Fight for Federally Reserved Water Rights (American Indian Law Review)",
                "url": "https://digitalcommons.law.ou.edu/ailr/vol43/iss1/6/",
                "type": "law review",
            },
        ],
        "case_type": "groundwater",
        "cwa_applied": "not-applied",
        "cwa_instrument": "9th Cir. — reserved rights extend to groundwater; state law preempted",
        "cwa_pathway": (
            "Applies where a campus's groundwater supply sits in a basin with an "
            "overlying or adjoining reservation. The claim runs between the tribe and "
            "the water district, but the resulting quantification determines what is "
            "left for the district's industrial customers."
        ),
        "display_section": "historical",
        "authorities": ["tribal-groundwater"],
    },
    {
        "case_id": "Vineyard-v-Rancho-Cordova-2007",
        "category": "precedent",
        "respondent": "Vineyard Area Citizens for Responsible Growth, Inc. v. City of Rancho Cordova, 40 Cal. 4th 412 (2007)",
        "year": "2007",
        "cwa_section": "Not a Clean Water Act case — California Environmental Quality Act; long-term water supply analysis",
        "violation_summary": (
            "Residents challenged the environmental impact report for a 6,000-acre "
            "community plan and its first development phase, arguing it failed to "
            "identify and evaluate where the water for the full build-out would come "
            "from."
        ),
        "outcome": (
            "The California Supreme Court held the EIR's near-term supply analysis "
            "adequate but its long-term analysis both procedurally and factually "
            "deficient: it improperly purported to tier from a future regional planning "
            "document, leaned on a mitigation measure that would curtail development if "
            "water failed to materialize without analysing that curtailment's own "
            "impacts, and left unexplained discrepancies between its supply estimates "
            "and the regional water plan's. The approval was set aside. The decision "
            "drove CEQA Guidelines amendments requiring analysis of supply over a "
            "project's full life."
        ),
        "takeaway": (
            "The most transferable procedural attack on a data-center approval anywhere "
            "with a state environmental review statute, because it needs no proof of "
            "hydrologic harm — only that the document assumed water it could not "
            "demonstrate. Campus approvals routinely analyse the first phase and defer "
            "the rest to a future regional plan, which is exactly the defect named here. "
            "It also produces the remedy opponents usually want: the approval is vacated "
            "and redone before construction, rather than damages long afterward."
        ),
        "analogous_cases": [
            "MCEA-PineIsland-MN-ProjectSkyway-2026",
            "ProjectBlue-Tucson-AMES-2026",
        ],
        "sources": [
            {
                "title": "Vineyard Area Citizens for Responsible Growth, Inc. v. City of Rancho Cordova (2007) S132972",
                "url": "https://caselaw.findlaw.com/summary/opinion/ca-supreme-court/2007/02/01/147286.html",
                "type": "court ruling",
            },
            {
                "title": "Supreme Court Sets Aside Land Use Plan EIR For Failure To Adequately Assess Long-Term Water Supplies",
                "url": "https://kmtg.com/news/legal-alerts/supreme-court-sets-aside-land-use-plan-eir-for-failure-to-adequately-assess-long-term-water-supplies/",
                "type": "law review",
            },
            {
                "title": "Vineyard Area Citizens for Responsible Growth v. City of Rancho Cordova — case summary",
                "url": "https://www.rmmenvirolaw.com/vineyard-area-citizens-for-responsible-growth-v-city-of-rancho-cordova/",
                "type": "law review",
            },
        ],
        "case_type": "water-supply",
        "cwa_applied": "not-applied",
        "cwa_instrument": "Cal. Supreme Court — EIR must show a realistic long-term water supply",
        "cwa_pathway": (
            "A challenge to the environmental document behind a data-center approval on "
            "the ground that it analysed only near-term supply and deferred the rest. "
            "Requires a state environmental review statute with a supply-analysis "
            "requirement, not a federal hook."
        ),
        "display_section": "historical",
        "authorities": ["sepa-supply-adequacy"],
    },
]

# Existing tracked matters that now also illustrate a new doctrine family. The
# Tucson fight shows the Arizona AMA regime better than any historical case
# would, and Pine Island is already the live state-environmental-review matter.
AUTHORITY_ADDITIONS = {
    "ProjectBlue-Tucson-AMES-2026": ["gwmgmt-az-ama"],
    "ELF-v-SWRCB-2018": ["gwmgmt-sgma"],
    "Rowan-ProjectCinco-Medina-TX-2025": ["xfer-area-of-origin"],
    "MCEA-PineIsland-MN-ProjectSkyway-2026": ["sepa-review-injunction"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return apply_batch(
        NEW_STATUTES,
        NEW_READINGS,
        NEW_CASES,
        last_updated="2026-07-26",
        authority_additions=AUTHORITY_ADDITIONS,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
