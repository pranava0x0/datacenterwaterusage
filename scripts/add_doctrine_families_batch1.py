#!/usr/bin/env python3
"""Precedent engine batch 1: interstate apportionment, public trust, groundwater property.

Plan Spec C1/C2. Until now the authorities registry spoke only five federal
statutes (CWA, SDWA, TSCA, RCRA, RHA). That is not how water law actually
reaches a data center: the Memphis fight turns on interstate aquifer
apportionment, Georgia well-interference on state common law, Tucson on an
Arizona groundwater-management regime. None of those have a federal permit in
the picture at all, so the registry could not express them.

This is the first of several batches. Families are added to
``WATER_STATUTE_ORDER`` only once their readings AND anchor cases land in the
same commit, because the schema tests require every listed family to have both
— adding a family early would mean a filter value that matches nothing.

Every case carries two independent sources. Cases whose citation could not be
confirmed against a retrievable source are held back for a later batch rather
than entered on a plausible-looking URL.

Run: ``python3 scripts/add_doctrine_families_batch1.py [--dry-run]``
Idempotent.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

AUTHORITIES_PATH = BASE_DIR / "data" / "reference" / "water_authorities.json"
CASES_PATH = BASE_DIR / "data" / "reference" / "cwa_investigations.json"

NEW_STATUTES = {
    "EQAP": {
        "name": "Interstate apportionment & compacts",
        "full_name": (
            "Equitable apportionment (U.S. Const. art. III original jurisdiction), "
            "interstate water compacts, and dormant Commerce Clause limits on water export"
        ),
        "agencies": "U.S. Supreme Court (original jurisdiction); compact councils",
        "kind": "interstate",
        "url": "https://www.law.cornell.edu/wex/equitable_apportionment",
    },
    "PTD": {
        "name": "Public trust doctrine",
        "full_name": (
            "The public trust doctrine — the state's continuing sovereign duty over "
            "navigable waters and the resources that feed them, as developed in state "
            "constitutional and common law"
        ),
        "agencies": "State courts; state water boards",
        "kind": "state-doctrine",
        "url": "https://www.law.cornell.edu/wex/public_trust_doctrine",
    },
    "GW": {
        "name": "Groundwater property & allocation doctrines",
        "full_name": (
            "State groundwater ownership and allocation rules — rule of capture, "
            "ownership in place, correlative rights, and reasonable use"
        ),
        "agencies": "State courts; groundwater conservation districts",
        "kind": "state-doctrine",
        "url": "https://www.law.cornell.edu/wex/water_rights",
    },
}

NEW_READINGS = [
    {
        "reading_id": "eqap-interstate-aquifer",
        "statute": "EQAP",
        "section": "U.S. Const. art. III, §2 original jurisdiction — equitable apportionment of an interstate aquifer",
        "name": "Equitable apportionment reaches groundwater",
        "agency": "U.S. Supreme Court (original jurisdiction)",
        "what_it_covers": (
            "Disputes between states over a shared water resource. Historically applied "
            "to rivers; in 2021 the Supreme Court held for the first time that "
            "groundwater in an interstate aquifer is equally subject to equitable "
            "apportionment — no state owns the water beneath it outright, and a state "
            "claiming injury must sue for an apportionment rather than for conversion."
        ),
        "dc_applicability": (
            "A data center pumping heavily from an aquifer that crosses a state line "
            "creates precisely the fact pattern this doctrine governs, and the injured "
            "party is the neighbouring *state*, not the neighbouring landowner. The "
            "practical barrier is evidentiary: an apportionment claim needs "
            "clear-and-convincing proof of real injury, which means utility-level "
            "aggregate withdrawal data — the class of data the HB 496-style reporting "
            "laws tracked in this dataset are starting to generate."
        ),
        "example_case_ids": ["Mississippi-v-Tennessee-2021"],
    },
    {
        "reading_id": "eqap-commerce-clause",
        "statute": "EQAP",
        "section": "Dormant Commerce Clause (U.S. Const. art. I, §8, cl. 3)",
        "name": "Groundwater is an article of interstate commerce",
        "agency": "Federal courts",
        "what_it_covers": (
            "Limits on a state's power to restrict the export of water across its "
            "borders. Groundwater is an article of commerce, so a state law blocking "
            "or conditioning its transfer out of state faces Commerce Clause scrutiny "
            "and must be genuinely tailored to conservation rather than to hoarding."
        ),
        "dc_applicability": (
            "Runs in the opposite direction from most doctrines here: it is the "
            "constraint on a *state* that tries to keep its water away from "
            "out-of-state data-center demand. A statute written to stop water leaving "
            "for a neighbouring state's campus is more vulnerable than one that limits "
            "large withdrawals regardless of where the user sits — which is why the "
            "durable instruments in this dataset regulate by volume and use, not by "
            "destination."
        ),
        "example_case_ids": ["Sporhase-v-Nebraska-1982"],
    },
    {
        "reading_id": "ptd-reopener",
        "statute": "PTD",
        "section": "Public trust doctrine — continuing supervision over allocated water",
        "name": "No water right is immune from trust reconsideration",
        "agency": "State courts; state water boards",
        "what_it_covers": (
            "The state holds navigable waters in trust and retains a continuing duty of "
            "supervision. A previously granted water right is not settled forever: it "
            "remains subject to reconsideration and adjustment where the diversion harms "
            "trust interests and a feasible alternative exists."
        ),
        "dc_applicability": (
            "The doctrine that makes an already-issued water allocation reviewable. A "
            "data center supplied under a long-standing municipal or appropriative right "
            "is not insulated by that right if the resulting draw damages a trust "
            "resource — which matters because most data-center supply arrives through "
            "existing utility entitlements rather than new permits, and those are exactly "
            "what this doctrine reopens."
        ),
        "example_case_ids": ["National-Audubon-v-Superior-Court-1983"],
    },
    {
        "reading_id": "ptd-groundwater-nexus",
        "statute": "PTD",
        "section": "Public trust doctrine as applied to groundwater extraction affecting navigable waters",
        "name": "The trust follows groundwater into surface flow",
        "agency": "State courts; counties issuing well permits",
        "what_it_covers": (
            "Groundwater pumping that measurably reduces flow in a navigable waterway "
            "falls within the public trust, and a comprehensive statutory groundwater "
            "regime does not displace that duty. The permitting authority — often a "
            "county — must consider trust resources when issuing well permits."
        ),
        "dc_applicability": (
            "Closes the gap a data center's hydrology usually falls into. Campus wells "
            "are rarely regulated as a surface-water diversion, but where drawdown "
            "depletes a connected stream the trust duty attaches to the well permit "
            "itself. It also means a state groundwater-management statute is a floor, "
            "not a ceiling: complying with the statute does not answer the trust claim."
        ),
        "example_case_ids": ["ELF-v-SWRCB-2018"],
    },
    {
        "reading_id": "ptd-precautionary",
        "statute": "PTD",
        "section": "Public trust doctrine — burden of proof and the precautionary principle",
        "name": "Uncertainty weighs toward protecting the resource",
        "agency": "State water commissions; state courts",
        "what_it_covers": (
            "The trust establishes a presumption in favour of its purposes. The burden "
            "sits on the party seeking water for private gain to justify the use and its "
            "impacts, not on the public to prove harm; and where the science is "
            "unresolved, that uncertainty counts in favour of protection rather than "
            "against it."
        ),
        "dc_applicability": (
            "Directly inverts the usual posture of a data-center water fight. The "
            "recurring complaint in this dataset is that opponents cannot prove harm "
            "because consumption figures are confidential — under this reading the "
            "applicant carries the burden, and unresolved hydrology argues for the "
            "resource. Its force is jurisdiction-specific: Hawai'i's constitutional water "
            "provisions are unusually strong, so this is the ceiling of the doctrine "
            "rather than its typical reach."
        ),
        "example_case_ids": ["Waiahole-Ditch-2000"],
    },
    {
        "reading_id": "gw-ownership-takings",
        "statute": "GW",
        "section": "Groundwater owned in place; regulation as a constitutional taking",
        "name": "Groundwater as a compensable property interest",
        "agency": "State courts; groundwater conservation districts",
        "what_it_covers": (
            "In states following ownership-in-place, a landowner holds a constitutionally "
            "protected interest in the groundwater beneath the surface before it is "
            "pumped. Regulation that restricts pumping can therefore support a takings "
            "claim requiring compensation."
        ),
        "dc_applicability": (
            "Cuts both ways, which is why it belongs in the registry. It is the doctrine "
            "a data center would invoke against a withdrawal cap imposed after it "
            "acquired the land — and equally the one a neighbouring landowner invokes "
            "when a regulator permits the campus to draw down the property interest "
            "under their own acreage. It also explains why states in this family "
            "regulate through districts and permits rather than by prohibition: outright "
            "restriction carries a compensation risk."
        ),
        "example_case_ids": ["Edwards-Aquifer-Authority-v-Day-2012"],
    },
]

NEW_CASES = [
    {
        "case_id": "Mississippi-v-Tennessee-2021",
        "analogous_cases": ["xAI-Colossus-Memphis-TN-2026", "CorpusChristi-SintonTX-EvangelineAquifer-wells-2026"],
        "category": "precedent",
        "respondent": "Mississippi v. Tennessee, 595 U.S. 15 (2021) (No. 143, Original)",
        "year": "2021",
        "cwa_section": "Not a Clean Water Act case — U.S. Const. art. III, §2 original jurisdiction; equitable apportionment",
        "violation_summary": (
            "Mississippi sued Tennessee directly in the Supreme Court, alleging that "
            "Memphis's municipal well field had forcibly drawn roughly 252 billion "
            "gallons of groundwater out from beneath Mississippi's sovereign territory "
            "by altering flow within the Middle Claiborne (Memphis Sand) Aquifer. "
            "Mississippi framed this as a taking of water it owned outright and sought "
            "damages, expressly declining to seek an equitable apportionment."
        ),
        "outcome": (
            "Unanimous. Chief Justice Roberts, writing for the Court on a question of "
            "first impression, held that groundwater in an interstate aquifer is subject "
            "to equitable apportionment just as an interstate river is. Because "
            "Mississippi had sued on an ownership theory rather than seeking an "
            "apportionment, its complaint was dismissed — and the Court declined to grant "
            "leave to amend."
        ),
        "takeaway": (
            "The single most directly applicable precedent to a US data-center water "
            "fight. The aquifer it governs is the same Memphis Sand that xAI's Colossus "
            "campus draws on, so the legal question of who may complain about heavy "
            "pumping there is already answered: the remedy is an interstate "
            "apportionment suit, brought by a state, not a damages claim for stolen "
            "water. The practical obstacle is evidentiary — an apportioning court needs "
            "clear and convincing proof of real injury, which requires exactly the "
            "aggregate withdrawal data that data-center water reporting laws produce."
        ),
        "sources": [
            {
                "title": "Mississippi v. Tennessee — case file and opinion",
                "url": "https://www.scotusblog.com/cases/case-files/mississippi-v-tennessee",
                "type": "court ruling",
            },
            {
                "title": "U.S. Supreme Court Holds that Groundwater in Interstate Aquifer Is Not Owned by States but Is Equitably Apportioned Among Them",
                "url": "https://www.argentco.com/post/mississippi-v-tennessee-u-s-supreme-court-holds-that-groundwater-in-interstate-aquifer-is-not-owned-by-states-but-is-equitably-apportioned-among-them/",
                "type": "law review",
            },
            {
                "title": "Science and the Supreme Court — Mississippi v. Tennessee",
                "url": "https://www.fjc.gov/content/376807/water-and-law-sidebar-science-and-supreme-court-mississippi-v-tennessee",
                "type": "agency",
            },
        ],
        "case_type": "groundwater",
        "cwa_applied": "not-applied",
        "cwa_instrument": "SCOTUS original jurisdiction — equitable apportionment extended to groundwater",
        "cwa_pathway": (
            "No federal water statute was involved. The pathway to a data-center fact "
            "pattern runs through a *state* suing another state over a shared aquifer "
            "that a large industrial user is drawing down — which requires a state "
            "willing to sue and aggregate withdrawal data adequate to prove injury."
        ),
        "display_section": "historical",
        "authorities": ["eqap-interstate-aquifer"],
    },
    {
        "case_id": "Sporhase-v-Nebraska-1982",
        "analogous_cases": ["Google-Berkeley-SC-Middendorf-aquifer-2019", "Rowan-ProjectCinco-Medina-TX-2025"],
        "category": "precedent",
        "respondent": "Sporhase v. Nebraska ex rel. Douglas, 458 U.S. 941 (1982)",
        "year": "1982",
        "cwa_section": "Not a Clean Water Act case — dormant Commerce Clause (U.S. Const. art. I, §8, cl. 3)",
        "violation_summary": (
            "Nebraska required a permit to move groundwater from a Nebraska well for use "
            "in an adjoining state, and would grant one only if that state offered "
            "reciprocal rights to Nebraska. Landowners with property straddling the "
            "Nebraska-Colorado line challenged the restriction."
        ),
        "outcome": (
            "The Court held that groundwater is an article of interstate commerce and "
            "struck down the reciprocity condition. The condition was an explicit barrier "
            "to interstate commerce and was not narrowly tailored to the conservation "
            "purpose Nebraska claimed for it, so it failed the strict scrutiny applied to "
            "facially discriminatory legislation."
        ),
        "takeaway": (
            "The constitutional ceiling on state water protectionism, and a live "
            "constraint on how the bills in this dataset can be written. A state may "
            "limit large withdrawals; it may not condition water on the user or the water "
            "staying inside its borders. For data centers this matters because campuses "
            "cluster near state lines and draw on shared basins — legislation aimed at "
            "keeping water away from a neighbouring state's data center is far more "
            "vulnerable than a volume-based cap that applies to everyone."
        ),
        "sources": [
            {
                "title": "Sporhase v. Nebraska ex rel. Douglas, 458 U.S. 941 (1982) — full opinion",
                "url": "https://caselaw.findlaw.com/court/us-supreme-court/458/941.html",
                "type": "court ruling",
            },
            {
                "title": "The Dormant Commerce Clause and Water Export (Klein) — Harvard Environmental Law Review",
                "url": "https://journals.law.harvard.edu/elr/2011/04/01/the-dormant-commerce-clause-and-water-export-toward-a-new-analytical-paradigm",
                "type": "law review",
            },
        ],
        "case_type": "groundwater",
        "cwa_applied": "not-applied",
        "cwa_instrument": "SCOTUS ruling — groundwater is an article of interstate commerce",
        "cwa_pathway": (
            "Applies defensively rather than offensively: it is the doctrine under which "
            "a data-center operator, or an out-of-state buyer, challenges a state water "
            "law that discriminates by destination."
        ),
        "display_section": "historical",
        "authorities": ["eqap-commerce-clause"],
    },
    {
        "case_id": "National-Audubon-v-Superior-Court-1983",
        "analogous_cases": ["ProjectBlue-Tucson-AMES-2026", "Bessemer-AL-Hyperscale-WaterSupply-2025"],
        "category": "precedent",
        "respondent": "National Audubon Society v. Superior Court, 33 Cal. 3d 419 (1983) (the Mono Lake case)",
        "year": "1983",
        "cwa_section": "Not a Clean Water Act case — California public trust doctrine",
        "violation_summary": (
            "Los Angeles held appropriative rights, granted decades earlier, to divert "
            "the streams feeding Mono Lake. The diversions dropped the lake's level "
            "severely and damaged its ecosystem. Audubon argued the state could not treat "
            "those rights as settled."
        ),
        "outcome": (
            "The California Supreme Court held that the public trust doctrine limits "
            "appropriative water rights: the state has a continuing duty of supervision "
            "over navigable waters, previously granted rights remain subject to "
            "reconsideration, and the state must consider trust uses and avoid or "
            "minimize harm to them where feasible."
        ),
        "takeaway": (
            "The foundational reopener. Its relevance to data centers is structural: "
            "campuses are almost always supplied through an existing municipal or "
            "appropriative entitlement rather than a new permit, and the usual assumption "
            "is that a settled right is beyond challenge. Audubon says otherwise — the "
            "allocation stays reviewable if the resulting draw harms a trust resource, "
            "which makes the utility's existing right, not the campus's absent permit, "
            "the point of legal leverage."
        ),
        "sources": [
            {
                "title": "National Audubon Society v. Superior Court, 33 Cal. 3d 419 (1983) — full opinion",
                "url": "https://law.justia.com/cases/california/supreme-court/3d/33/419.html",
                "type": "court ruling",
            },
            {
                "title": "The Public Trust Doctrine, Private Water Allocation, and Mono Lake: The Historic Saga of National Audubon Society v. Superior Court",
                "url": "https://ir.law.fsu.edu/articles/610/",
                "type": "law review",
            },
        ],
        "case_type": "legal-doctrine",
        "cwa_applied": "not-applied",
        "cwa_instrument": "California Supreme Court — public trust limits appropriative rights",
        "cwa_pathway": (
            "Reaches a data center through the *supplier*: a challenge to the utility's "
            "or district's existing entitlement on the ground that serving the new load "
            "harms a trust resource, rather than a challenge to the campus itself."
        ),
        "display_section": "historical",
        "authorities": ["ptd-reopener"],
    },
    {
        "case_id": "ELF-v-SWRCB-2018",
        "analogous_cases": ["Meta-NewtonCountyGA-well-failures-2018-2025", "County-of-Maui-v-Hawaii-Wildlife-Fund-2020"],
        "category": "precedent",
        "respondent": "Environmental Law Foundation v. State Water Resources Control Board, 26 Cal. App. 5th 844 (2018)",
        "year": "2018",
        "cwa_section": "Not a Clean Water Act case — California public trust doctrine; Sustainable Groundwater Management Act",
        "violation_summary": (
            "Siskiyou County issued well permits for groundwater extraction that reduced "
            "flows in the Scott River, a navigable waterway. The county and the state "
            "board argued the public trust had never applied to groundwater, and that in "
            "any event the 2014 Sustainable Groundwater Management Act had displaced it."
        ),
        "outcome": (
            "The Third District Court of Appeal rejected both arguments unanimously. The "
            "public trust doctrine applies to groundwater extraction that adversely "
            "affects navigable waterways, and SGMA did not occupy the field or abolish "
            "it. The county has a duty to consider the trust when permitting such wells, "
            "and the state board has authority and a duty to act."
        ),
        "takeaway": (
            "The reading that reaches the ordinary data-center hydrology. Campus wells "
            "are usually regulated, if at all, as groundwater — not as a diversion from "
            "the stream they actually deplete. ELF closes that gap wherever drawdown is "
            "connected to surface flow, and it puts the duty on the *county* issuing the "
            "well permit, which is the level of government most data-center siting fights "
            "are already being fought at. It also establishes that satisfying a state "
            "groundwater statute is a floor, not a defence."
        ),
        "sources": [
            {
                "title": "Environmental Law Foundation v. State Water Resources Control Bd. (2018) — full opinion",
                "url": "https://law.justia.com/cases/california/court-of-appeal/2018/c083239.html",
                "type": "court ruling",
            },
            {
                "title": "California Court Finds Public Trust Doctrine Applies to State Groundwater Resources",
                "url": "https://legal-planet.org/2018/08/29/california-court-finds-public-trust-doctrine-applies-to-state-groundwater-resources/",
                "type": "law review",
            },
            {
                "title": "California Court Holds Public Trust Doctrine Applies to Groundwater Impacts on Surface Streams",
                "url": "https://www.dwt.com/blogs/energy--environmental-law-blog/2018/09/california-court-holds-public-trust-doctrine-appli",
                "type": "law review",
            },
        ],
        "case_type": "groundwater",
        "cwa_applied": "not-applied",
        "cwa_instrument": "Cal. Court of Appeal — public trust reaches groundwater pumping",
        "cwa_pathway": (
            "A challenge to the county well permit behind a data-center campus, on the "
            "ground that drawdown depletes a connected navigable stream. Requires "
            "hydrologic evidence of the groundwater-to-surface-water connection."
        ),
        "display_section": "historical",
        "authorities": ["ptd-groundwater-nexus"],
    },
    {
        "case_id": "Waiahole-Ditch-2000",
        "analogous_cases": ["MCEA-PineIsland-MN-ProjectSkyway-2026", "Charlotte-NC-drought-datacenter-moratorium-2026"],
        "category": "precedent",
        "respondent": "In re Water Use Permit Applications (Waiāhole Ditch), 94 Haw. 97, 9 P.3d 409 (2000)",
        "year": "2000",
        "cwa_section": "Not a Clean Water Act case — Hawai'i constitutional public trust and State Water Code",
        "violation_summary": (
            "A contested-case proceeding over how to reallocate water from the Waiāhole "
            "Ditch after the plantation agriculture it was built for wound down, with "
            "competing claims from new commercial users and from windward stream "
            "restoration."
        ),
        "outcome": (
            "The Hawai'i Supreme Court set out the state's public trust framework: the "
            "trust establishes a presumption in favour of its purposes; the burden falls "
            "on those seeking or approving water for private gain to justify the use and "
            "account for its impacts; and the trust incorporates a precautionary "
            "principle under which unresolved science weighs toward protecting the "
            "resource rather than toward permitting the use."
        ),
        "takeaway": (
            "The strongest formulation of the trust in American water law, and the direct "
            "answer to the evidentiary problem that recurs throughout this dataset. Data "
            "center opponents routinely cannot prove harm because consumption figures are "
            "confidential and hydrologic effects are contested. Under Waiāhole the "
            "applicant carries the burden and uncertainty favours the resource. The "
            "caveat is jurisdictional: this rests on Hawai'i's unusually explicit "
            "constitutional water provisions, so it marks the doctrine's ceiling rather "
            "than a standard other states would apply."
        ),
        "sources": [
            {
                "title": "In re Water Use Permit Applications (Waiāhole Ditch) — Hawai'i Supreme Court opinion",
                "url": "http://oaoa.hawaii.gov/jud/21309op.htm",
                "type": "court ruling",
            },
            {
                "title": "In re: The Water Use Permit Applications (2000) — full text",
                "url": "https://caselaw.findlaw.com/hi-supreme-court/1387163.html",
                "type": "court ruling",
            },
        ],
        "case_type": "legal-doctrine",
        "cwa_applied": "not-applied",
        "cwa_instrument": "Hawai'i Supreme Court — trust presumption, burden shift and precautionary principle",
        "cwa_pathway": (
            "Persuasive rather than binding outside Hawai'i. Its use is as the argued "
            "standard in a state whose own trust doctrine is unsettled: that the "
            "data-center applicant, not the objecting public, must justify the draw."
        ),
        "display_section": "historical",
        "authorities": ["ptd-precautionary"],
    },
    {
        "case_id": "Edwards-Aquifer-Authority-v-Day-2012",
        "analogous_cases": ["Sailfish-HoodCountyTX-ComancheCircle-aquifer-moratorium-2025-2026", "CorpusChristi-SintonTX-EvangelineAquifer-wells-2026"],
        "category": "precedent",
        "respondent": "Edwards Aquifer Authority v. Day, 369 S.W.3d 814 (Tex. 2012)",
        "year": "2012",
        "cwa_section": "Not a Clean Water Act case — Texas groundwater ownership; state and federal takings clauses",
        "violation_summary": (
            "The Edwards Aquifer Authority capped Day's pumping permit far below his "
            "request, allocating on the basis of historical beneficial use. Day argued "
            "the restriction took a property interest he already owned in the groundwater "
            "beneath his land."
        ),
        "outcome": (
            "The Texas Supreme Court held unanimously that a landowner has a "
            "constitutionally protected interest in the groundwater in place beneath the "
            "surface — ownership does not wait for capture — and that a regulatory "
            "restriction on pumping can therefore support a takings claim requiring "
            "compensation."
        ),
        "takeaway": (
            "The doctrine that constrains how far a state can regulate data-center "
            "pumping in ownership-in-place jurisdictions, and it points both ways. An "
            "operator that bought land can assert a property interest against a "
            "withdrawal cap imposed afterwards; a neighbour whose water is drawn out from "
            "under them holds the same kind of interest against a regulator that "
            "permitted the campus. It also explains an otherwise puzzling pattern in this "
            "dataset — why Texas fights run through conservation-district permits and "
            "local politics rather than through outright prohibition, since prohibition "
            "carries a compensation bill."
        ),
        "sources": [
            {
                "title": "Edwards Aquifer Authority v. Day and McDaniel — decision summary and history",
                "url": "https://en.wikipedia.org/wiki/Edwards_Aquifer_Authority_v._Day_and_McDaniel",
                "type": "law review",
            },
            {
                "title": "Changes to Texas Groundwater Rights — Edwards Aquifer Authority v. Day",
                "url": "https://www.dykema.com/news-insights/changes-to-texas-groundwater-rights-edwards-aquifer-authority-v-day.html",
                "type": "law review",
            },
            {
                "title": "Liquid Assets: Groundwater in Texas (Torres) — Yale Law Journal",
                "url": "https://yalelawjournal.org/pdf/1118_kt9z6o78.pdf",
                "type": "law review",
            },
        ],
        "case_type": "groundwater",
        "cwa_applied": "not-applied",
        "cwa_instrument": "Tex. Supreme Court — groundwater owned in place; regulation may be a taking",
        "cwa_pathway": (
            "Two routes to a data-center fact pattern: as the operator's defence against "
            "a new withdrawal cap, and as an injured neighbour's theory against the "
            "district that permitted the drawdown."
        ),
        "display_section": "historical",
        "authorities": ["gw-ownership-takings"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from refdata.taxonomies import (
        AUTHORITY_KIND_LABELS,
        CWA_CASE_TYPE_LABELS,
        WATER_STATUTE_COLORS,
        WATER_STATUTE_ORDER,
    )

    authorities = json.loads(AUTHORITIES_PATH.read_text(encoding="utf-8"))
    cases_payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    problems = []
    for code, meta in NEW_STATUTES.items():
        if meta["kind"] not in AUTHORITY_KIND_LABELS:
            problems.append(f"{code}: bad kind {meta['kind']}")
        if code not in WATER_STATUTE_ORDER:
            problems.append(f"{code}: not in WATER_STATUTE_ORDER — add it in taxonomies.py")
        if code not in WATER_STATUTE_COLORS:
            problems.append(f"{code}: no colour in WATER_STATUTE_COLORS")

    # Back-fill `kind` on the five original families. They pre-date the field,
    # and every family needs one for the accordion to say what register the
    # reader is in — a federal permit statute and a state common-law doctrine
    # are not the same kind of authority.
    backfilled = []
    for code, meta in authorities["statutes"].items():
        if code not in NEW_STATUTES and "kind" not in meta:
            meta["kind"] = "federal-statute"
            backfilled.append(code)

    added_statutes = [c for c in NEW_STATUTES if c not in authorities["statutes"]]
    authorities["statutes"].update(NEW_STATUTES)

    existing_readings = {r["reading_id"] for r in authorities["readings"]}
    added_readings = []
    for reading in NEW_READINGS:
        if reading["reading_id"] in existing_readings:
            continue
        if reading["statute"] not in authorities["statutes"]:
            problems.append(f"{reading['reading_id']}: unknown family {reading['statute']}")
        authorities["readings"].append(reading)
        added_readings.append(reading["reading_id"])

    existing_cases = {c["case_id"] for c in cases_payload["cases"]}
    added_cases = []
    for case in NEW_CASES:
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

    # Every reading must name a case that exists once this batch is applied.
    all_case_ids = {c["case_id"] for c in cases_payload["cases"]}
    for reading in NEW_READINGS:
        for cid in reading["example_case_ids"]:
            if cid not in all_case_ids:
                problems.append(f"{reading['reading_id']}: example case {cid} not found")

    print(f"families added: {len(added_statutes)}  {added_statutes}")
    print(f"kind back-filled: {len(backfilled)}  {backfilled}")
    print(f"readings added: {len(added_readings)}")
    for r in added_readings:
        print(f"  + {r}")
    print(f"cases added:    {len(added_cases)}")
    for c in added_cases:
        print(f"  + {c}")
    print(
        f"totals -> families {len(authorities['statutes'])}, "
        f"readings {len(authorities['readings'])}, cases {len(cases_payload['cases'])}"
    )

    if problems:
        print("\nAborted:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    if args.dry_run:
        print("\n(dry run — nothing written)")
        return 0

    authorities["last_updated"] = "2026-07-25"
    cases_payload["last_updated"] = "2026-07-25"
    AUTHORITIES_PATH.write_text(
        json.dumps(authorities, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    CASES_PATH.write_text(
        json.dumps(cases_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("\nWrote water_authorities.json and cwa_investigations.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
