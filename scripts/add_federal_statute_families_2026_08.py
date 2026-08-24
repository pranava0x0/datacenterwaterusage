#!/usr/bin/env python3
"""Spec A: the federal water-statute families beyond the CWA's neighbours.

The toolkit's federal layer stopped at the CWA, SDWA, TSCA, RCRA, RHA and the
ESA — every one of them a *discharge* or *species* statute. A data center's
water problem just as often runs through supply: storage in a Corps reservoir,
a basin commission's withdrawal docket, a hydropower licence's flow terms, a
Reclamation delivery contract, a NEPA review of the federal financing behind a
plant built to power the campus. This batch adds the eight families that carry
those fact patterns, each with its readings and at least one verified
historical case, because a family with no case is a reading list rather than a
tool (the schema tests enforce the pairing).

Three candidate families were considered and dropped: WRDA/33 U.S.C. §408 has
no citable standalone case law, so the alteration permission rides inside the
WSA reading; the Oil Pollution Act's Facility Response Plan duty is codified at
CWA §311(j)(5) and already covered by ``cwa-311-spills``; and the Fish and
Wildlife Coordination Act generates no litigation independent of the NEPA or
§404 action it rides on.

Families enter ``WATER_STATUTE_ORDER`` in the same commit as their readings and
cases — a family listed early renders a filter value that matches nothing.

Run: ``python3 scripts/add_federal_statute_families_2026_08.py [--dry-run]``
Idempotent.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
AUTHORITIES_PATH = BASE_DIR / "data" / "reference" / "water_authorities.json"
CASES_PATH = BASE_DIR / "data" / "reference" / "cwa_investigations.json"
CONFLICTS_PATH = BASE_DIR / "data" / "reference" / "dc_water_conflicts.json"

LAST_UPDATED = "2026-08-24"

# Each file's note carries its own running history; these sentences are
# appended once (the append is skipped if the sentence is already there, so a
# re-run stays a no-op).
AUTHORITIES_NOTE = (
    " August 24, 2026: eight supply-side families — NEPA, CERCLA, the Water Supply "
    "Act (with the 33 U.S.C. §408 alteration permission folded into its reading), the "
    "Wild and Scenic Rivers Act, the Federal Power Act, Reclamation law, EPCRA, and "
    "the ratified interstate basin compacts (Great Lakes, Delaware, Susquehanna). "
    "These reach a data center through storage, withdrawal and licensing rather than "
    "through a discharge permit. WRDA, the Oil Pollution Act and the Fish and "
    "Wildlife Coordination Act were considered and dropped — §408 has no citable "
    "standalone case law and rides inside the WSA reading, OPA's Facility Response "
    "Plan duty is codified at CWA §311(j)(5) and already sits under cwa-311-spills, "
    "and FWCA generates no litigation independent of the NEPA or §404 action it "
    "rides on."
)
CASES_NOTE = (
    " August 24, 2026 additions: 14 cases anchoring the supply-side federal and "
    "interstate families — NEPA (Hughes River Watershed Conservancy v. Glickman; the "
    "Crane Clean Energy Center restart bundle behind Constellation's Microsoft power "
    "deal), CERCLA (Bestfoods, CTS Corp. v. Waldburger), the Water Supply Act's "
    "authorized-purposes ceiling on Lake Lanier (Southeastern Federal Power Customers "
    "v. Geren; In re MDL-1824 Tri-State Water Rights), interstate basin compacts (the "
    "Foxconn/Racine Great Lakes diversion at the site Microsoft now occupies, the SRBC "
    "Panda Power withdrawal penalty, the DRBC fracking ban), the Wild and Scenic "
    "Rivers Act (the Blue Ridge Project), the Federal Power Act (California v. FERC), "
    "Reclamation contract law (United States v. Klamath Drainage District) and EPCRA "
    "(Steel Co.; Nidec Elesys). Most are typed 'water-supply': those statutes govern "
    "allocation, storage and licensing rather than discharge. Prior count was 109."
)
CONFLICTS_NOTE = (
    " August 24, 2026: three supply-side mappings added with the federal-statute "
    "families — Microsoft Mount Pleasant WI to the Great Lakes Compact's "
    "straddling-community diversion it inherited from Foxconn, QTS Fayette County GA "
    "to the Corps' authorized-purposes ceiling in the ACF basin, and Project Blue "
    "Tucson to Reclamation contract law behind its Central Arizona Project offsets."
)

NEW_STATUTES = {
    "NEPA": {
        "name": "National Environmental Policy Act",
        "full_name": "National Environmental Policy Act of 1969, 42 U.S.C. §§4321–4370m",
        "agencies": "Council on Environmental Quality (CEQ); whichever federal agency is taking the action (Corps, NRC, DOE, etc.)",
        "url": "https://www.law.cornell.edu/uscode/text/42/chapter-55",
        "kind": "federal-statute"
    },
    "CERCLA": {
        "name": "Comprehensive Environmental Response, Compensation, and Liability Act",
        "full_name": "Comprehensive Environmental Response, Compensation, and Liability Act of 1980 (Superfund), 42 U.S.C. §§9601–9675",
        "agencies": "EPA",
        "url": "https://www.law.cornell.edu/uscode/text/42/chapter-103",
        "kind": "federal-statute"
    },
    "WSA": {
        "name": "Water Supply Act / Corps reallocation and alteration authority",
        "full_name": "Water Supply Act of 1958, 43 U.S.C. §390b, and the permission-to-alter provision at 33 U.S.C. §408, as periodically amended by Water Resources Development Acts",
        "agencies": "U.S. Army Corps of Engineers; Congress (for major reallocations)",
        "url": "https://www.law.cornell.edu/uscode/text/43/390b",
        "kind": "federal-statute"
    },
    "BASIN": {
        "name": "Interstate basin compacts and commissions",
        "full_name": "Congressionally ratified interstate basin compacts — the Great Lakes–St. Lawrence River Basin Water Resources Compact (2008), the Delaware River Basin Compact (1961), and the Susquehanna River Basin Compact (1970) — each creating a commission with direct regulatory authority over water use in its basin",
        "agencies": "Great Lakes Compact Council / member-state agencies; Delaware River Basin Commission; Susquehanna River Basin Commission",
        "url": "https://www.srbc.gov/",
        "kind": "interstate"
    },
    "WSR": {
        "name": "Wild and Scenic Rivers Act",
        "full_name": "Wild and Scenic Rivers Act, 16 U.S.C. §§1271–1287 (§7, 16 U.S.C. §1278)",
        "agencies": "National Park Service, U.S. Forest Service, Bureau of Land Management, U.S. Fish and Wildlife Service (river-administering agencies); FERC",
        "url": "https://www.law.cornell.edu/uscode/text/16/1278",
        "kind": "federal-statute"
    },
    "FPA": {
        "name": "Federal Power Act (hydropower licensing)",
        "full_name": "Federal Power Act, 16 U.S.C. §§791a–828c (Part I, FERC hydropower licensing)",
        "agencies": "Federal Energy Regulatory Commission",
        "url": "https://www.law.cornell.edu/uscode/text/16/chapter-12",
        "kind": "federal-statute"
    },
    "RECL": {
        "name": "Federal Reclamation law",
        "full_name": "Reclamation Act of 1902 and subsequent reclamation laws, 43 U.S.C. ch. 12 §371 et seq. (including Warren Act contracts, 43 U.S.C. §523 et seq.)",
        "agencies": "U.S. Bureau of Reclamation",
        "url": "https://www.law.cornell.edu/uscode/text/43/chapter-12",
        "kind": "federal-statute"
    },
    "EPCRA": {
        "name": "Emergency Planning and Community Right-to-Know Act",
        "full_name": "Emergency Planning and Community Right-to-Know Act of 1986, 42 U.S.C. §§11001–11050",
        "agencies": "EPA; State Emergency Response Commissions; Local Emergency Planning Committees",
        "url": "https://www.law.cornell.edu/uscode/text/42/chapter-116",
        "kind": "federal-statute"
    }
}

NEW_READINGS = [
    {
        "reading_id": "nepa-hard-look-seis",
        "statute": "NEPA",
        "section": "§102(2)(C), 42 U.S.C. §4332(2)(C) — the ‘hard look’ doctrine and supplemental EIS requirement",
        "name": "Environmental review must take a real ‘hard look,’ and supplement when the picture changes",
        "agency": "CEQ; the acting federal agency; reviewing courts",
        "what_it_covers": "Hughes River Watershed Conservancy v. Glickman (4th Cir. 1996) held the Army Corps and Natural Resources Conservation Service violated NEPA on a West Virginia dam project by using an inflated recreational-benefit estimate that skewed the EIS's cost-benefit picture, and by failing to seriously analyze zebra-mussel infestation risk before declining to prepare a supplemental EIS. On remand the agencies recalculated benefits using net rather than gross figures and commissioned species-impact studies; the Fourth Circuit's 1999 sequel (Hughes River Watershed Conservancy v. Johnson) held the corrected analysis satisfied NEPA's hard-look standard.",
        "dc_applicability": "A data center's own construction is rarely a 'major federal action,' but the federal actions clustered around one often are — a DOE loan guarantee, an NRC license amendment, a Corps permit, or federal financing for supporting transmission or water infrastructure. Hughes River sets what those reviews must actually do: real analysis (not inflated benefit figures or a boilerplate species screen), and a duty to go back and supplement if a materially different picture — a changed water-supply or grid-reliability forecast, for instance — emerges before the agency acts.",
        "example_case_ids": [
            "Hughes-River-Watershed-Conservancy-v-Glickman-1996"
        ]
    },
    {
        "reading_id": "nepa-federal-financing-review",
        "statute": "NEPA",
        "section": "§102(2)(C); DOE and NRC implementing procedures (10 C.F.R. Part 1021; 10 C.F.R. Part 51)",
        "name": "Federal financing and licensing actions trigger their own NEPA review",
        "agency": "DOE; NRC",
        "what_it_covers": "Restarting a shuttered nuclear plant runs through at least two independent federal actions, each carrying its own NEPA review. For the Crane Clean Energy Center (Three Mile Island Unit 1) restart, DOE's Loan Programs Office issued a final EIS in August 2025 covering its loan-guarantee decision, while NRC separately released a draft environmental assessment and finding of no significant impact in June 2026 for the license-reauthorization decision — NRC staff determined a full EIS was unnecessary for that action, a threshold call that is itself reviewable.",
        "dc_applicability": "The live, current version of a federal-financing NEPA trigger in the AI build-out: hyperscalers are underwriting nuclear and gas-plant restarts and new generation to meet data-center power demand, and every dollar of federal loan support or every NRC license action on those plants is an independently NEPA-reviewable action — even though the resulting EIS or EA typically analyzes only the plant's own radiological and environmental footprint, not the data-center deal driving the restart. Whether an EA-plus-FONSI is legally adequate, versus requiring a full EIS, is exactly the adequacy question Hughes River's hard-look standard was built to answer.",
        "example_case_ids": [
            "Constellation-CraneCleanEnergy-SRBC-NRC-PA-2026"
        ]
    },
    {
        "reading_id": "cercla-107-operator-liability",
        "statute": "CERCLA",
        "section": "§107(a)(2), 42 U.S.C. §9607(a)(2)",
        "name": "Owner/operator liability, and when a corporate parent is on the hook",
        "agency": "EPA; federal courts",
        "what_it_covers": "United States v. Bestfoods (1998) held CERCLA §107(a)(2) reaches whoever actually operated a contaminated facility. A parent corporation is not automatically liable just because its subsidiary owned or ran the polluting site — ordinary corporate separateness survives — but a parent that itself actively managed, directed, or made compliance decisions specifically about the facility's pollution-generating operations can be directly liable as an operator in its own right, independent of any veil-piercing theory.",
        "dc_applicability": "Relevant to how hyperscalers structure campus ownership — sites are frequently held in special-purpose subsidiaries or leased from developers, while the parent's facilities or sustainability group makes centralized decisions about cooling-system chemistry, generator fuel storage, or remediation at a site with legacy contamination. Bestfoods says centralized parent-level control over the environmentally sensitive decisions, not the corporate org chart, is what determines CERCLA exposure if a plume later turns up under or near the campus.",
        "example_case_ids": [
            "US-v-Bestfoods-1998"
        ]
    },
    {
        "reading_id": "cercla-repose-preemption",
        "statute": "CERCLA",
        "section": "§309, 42 U.S.C. §9658",
        "name": "CERCLA revives late-discovered claims — but not past a state's repose deadline",
        "agency": "Federal courts; state courts",
        "what_it_covers": "CTS Corp. v. Waldburger (2014) held that CERCLA §9658 — which overrides state statutes of limitations so a contamination claim's clock starts at discovery rather than at the polluting act — does not also override state statutes of repose, which cut off claims after a fixed number of years regardless of when the harm was discovered. North Carolina property owners who learned of TCE groundwater contamination from EPA in 2009, decades after the polluting plant closed, had their state nuisance claims barred by the state's 10-year repose period.",
        "dc_applicability": "A data center that later discovers its water supply well or campus soil is contaminated by a decades-old industrial release nearby may still have CERCLA's own federal cleanup remedies available, but a separate state-law tort claim against the original polluter (nuisance, trespass, diminished property value) can be time-barred by a state repose statute no matter how recently the contamination was actually discovered — a real limit on what an operator, or a neighboring landowner, can recover once EPA's own process is not in play.",
        "example_case_ids": [
            "CTS-Corp-v-Waldburger-2014"
        ]
    },
    {
        "reading_id": "wsa-reallocation-and-alteration",
        "statute": "WSA",
        "section": "Water Supply Act §301(d), 43 U.S.C. §390b(d); alteration permission at 33 U.S.C. §408",
        "name": "A federal reservoir's storage is finite, and Congress guards the ceiling",
        "agency": "U.S. Army Corps of Engineers; Congress",
        "what_it_covers": "Metro Atlanta's decades-long 'water wars' defined this ceiling. Southeastern Federal Power Customers v. Geren (D.C. Cir. 2008) held that a 2003 Corps settlement letting water utilities draw far more municipal/industrial supply from Lake Lanier's storage — at hydropower's expense — was a 'major operational change' that §301(d) does not let the Corps make unilaterally; it needs specific congressional authorization. In re Tri-State Water Rights Litigation (11th Cir. 2011) then held, on a related piece of the same fight, that water supply was in fact one of the Buford Project's originally authorized purposes under its 1946 authorization — giving the Corps more room than the district court had allowed, but still bounded by that authorized-purposes ceiling. A physical alteration of a Corps project — an intake, an outfall, a pipeline crossing a levee — needs its own, separate permission under 33 U.S.C. §408, evaluated against the same question of whether it impairs the project's authorized purposes.",
        "dc_applicability": "A hyperscale-driven metro utility asking the Corps for more storage out of a reservoir built for flood control, hydropower and navigation runs directly into this ceiling — exactly what the 2026 Water Resources Development Act (H.R. 9497, ordered reported July 2026) responds to: it would direct the Corps to report within a year on how 'new commercial and industrial water users' — a category the accompanying Congressional Research Service analysis (R49057, July 2026) says data centers fit — are affecting reservoirs authorized for water supply. Separately, a campus's own cooling-water intake structure built into or near a Corps flood-control or navigation project needs §408 permission independent of any NPDES or §404 permit it also holds.",
        "example_case_ids": [
            "Southeastern-Fed-Power-Customers-v-Geren-2008",
            "InRe-MDL1824-TriState-WaterRights-2011"
        ]
    },
    {
        "reading_id": "basin-glc-diversion",
        "statute": "BASIN",
        "section": "Great Lakes–St. Lawrence River Basin Water Resources Compact, Art. 4.9 (straddling-community exception)",
        "name": "The Compact bars diversion out of the Great Lakes basin except through narrow exceptions",
        "agency": "State DNRs; the Great Lakes Compact Council",
        "what_it_covers": "The 2008 Compact bans new or increased diversion of Great Lakes water outside the basin, with narrow exceptions including supply to a 'straddling community' that sits astride the basin line. Wisconsin approved exactly that exception in 2018 to let Racine Water Utility pipe up to 7 million gallons per day of Lake Michigan water to the Foxconn campus in Mount Pleasant, most of it (5.8 MGD) for that single industrial customer. Environmental groups argued the diversion was not really for 'public water supply' and violated the Compact's terms; a Wisconsin administrative law judge rejected that argument in June 2019 and upheld the approval, and the challengers chose not to appeal further.",
        "dc_applicability": "The Foxconn site is now Microsoft's Mount Pleasant data-center campus, so this is not hypothetical: any further increase in the Racine diversion to serve additional data-center buildings runs through the same straddling-community approval and the same 'is this really public water supply' argument that already lost once. Any other Great Lakes-basin hyperscale campus that is not itself inside the basin faces the same Compact gate before a single gallon can leave the lake.",
        "example_case_ids": [
            "Foxconn-Racine-GreatLakesCompact-Diversion-2019"
        ]
    },
    {
        "reading_id": "basin-drbc-srbc-withdrawal-authority",
        "statute": "BASIN",
        "section": "Delaware River Basin Compact §3.8; Susquehanna River Basin Compact §3.10 (direct withdrawal approval and enforcement)",
        "name": "DRBC and SRBC approve, condition, fine, or ban large withdrawals directly",
        "agency": "Delaware River Basin Commission; Susquehanna River Basin Commission",
        "what_it_covers": "Unlike most of the country, any withdrawal above a threshold in these two basins needs the commission's own approval, independent of state permitting. SRBC has used that authority both to approve large industrial withdrawals with conditions — its June 4, 2026 approval letting the Crane Clean Energy Center (the restarting Three Mile Island Unit 1, explicitly tied to Constellation's data-center power agreement with Microsoft) draw up to 73.2 million gallons a day, conditioned on curtailing withdrawals during low-flow periods — and to fine violators, as in its 2016 proposed penalties (roughly $97,000, including $44,250 for the Patriot plant in Lycoming County and $22,750 for Hummel Station in Snyder County) against Panda Power Funds for drawing from unapproved sources and exceeding limits while commissioning two Pennsylvania gas plants. DRBC has gone further still, voting in February 2021 to permanently ban high-volume hydraulic fracturing basin-wide — an outright prohibition on an entire water-intensive industrial activity, not just a permit condition.",
        "dc_applicability": "A data center, or a power plant built to supply one, sitting inside either basin does not go through a normal state-only withdrawal permit — it goes through a public commission docket that can approve with drought conditions attached (the SRBC/Crane model), fine for taking more than authorized (the Panda Power model), or, in the most basin-protective posture, decide the activity is not compatible with the basin at all (the DRBC fracking-ban model). That full range of outcomes is on the table for any large new water user in either basin, and the dockets themselves are public.",
        "example_case_ids": [
            "Constellation-CraneCleanEnergy-SRBC-NRC-PA-2026",
            "Panda-Power-Funds-SRBC-Penalty-2016",
            "DRBC-Fracking-Ban-2021"
        ]
    },
    {
        "reading_id": "wsr-7-hydropower-bar",
        "statute": "WSR",
        "section": "§7, 16 U.S.C. §1278(a)",
        "name": "A Wild and Scenic designation can override an already-issued federal license",
        "agency": "River-administering federal agencies (NPS, USFS, BLM, FWS); FERC",
        "what_it_covers": "Section 7 bars FERC from licensing a dam, water conduit, reservoir, or other project works 'on or directly affecting' a designated Wild and Scenic river, and bars other federal agencies from assisting a water-resources project with a direct and adverse effect on the values the designation protects. The clearest historical demonstration: after a decade of fighting Appalachian Power's proposed Blue Ridge Project — a two-reservoir pumped-storage hydro complex the Federal Power Commission had licensed in 1974 on the upper New River — Congress placed 26.5 miles of the river into the National Wild and Scenic Rivers System in September 1976, and the dam was never built.",
        "dc_applicability": "Narrow but absolute where it applies: a data-center campus, or the power or water infrastructure built to serve one, that would touch a designated Wild and Scenic river corridor cannot get a FERC hydropower license or most other federally assisted water-resources authorization for that reach — no matter how far along the project already is, since a designation can moot a license that has already been granted. Due diligence on any western or Appalachian site with river-adjacent power or cooling infrastructure should check the designated and study-river lists before assuming a federal water permit is available.",
        "example_case_ids": [
            "BlueRidgeProject-NewRiver-WSR-1976"
        ]
    },
    {
        "reading_id": "fpa-license-flow-preemption",
        "statute": "FPA",
        "section": "Federal Power Act §10(a), 16 U.S.C. §803(a)",
        "name": "FERC's licensed flow and reservoir terms preempt conflicting state rules",
        "agency": "Federal Energy Regulatory Commission",
        "what_it_covers": "California v. FERC (1990) held the Federal Power Act preempts a state's attempt to impose its own, different minimum stream-flow requirements on a FERC-licensed hydroelectric project — FERC's license terms occupy that field, because letting a state layer on stricter or different flow rules would hand it a veto over federally licensed projects that the FPA does not give it.",
        "dc_applicability": "Matters wherever a data center, or the power feeding one, sits at or draws from a FERC-licensed hydropower reservoir — increasingly real, since cheap hydro basins in the Pacific Northwest have already drawn large computing loads (crypto-mining operations at Chelan and Grant County PUD dams in Washington are the existing precedent for large computing co-locating at hydro facilities). The reservoir's water levels and release schedule are set by the FERC license, not by state water law, so a data center's cooling-water draw or a utility's request to hold water back for it has to work within license terms that only FERC, through relicensing or a license amendment, can change.",
        "example_case_ids": [
            "California-v-FERC-1990"
        ]
    },
    {
        "reading_id": "recl-contract-controls-delivery",
        "statute": "RECL",
        "section": "Reclamation contract law generally; individual repayment/water-service contracts under 43 U.S.C. §371 et seq.",
        "name": "A Reclamation contract's terms control, even against a district's own separate water right",
        "agency": "U.S. Bureau of Reclamation; federal courts",
        "what_it_covers": "United States v. Klamath Drainage District (9th Cir., decided Jan. 2025, No. 23-3404) held that a 1946 repayment contract let Reclamation control how much water the Klamath Drainage District could divert through the federal irrigation project — and that Reclamation's authority reached even a separate, later-acquired 1977 state water right the district tried to exercise through its own canal, because the contract's 'reasonable rules and regulations' language gave Reclamation that scope. The Ninth Circuit affirmed a 2023 injunction against the district's unauthorized diversions.",
        "dc_applicability": "Any western data-center campus — or the agricultural water right it buys, leases, or offsets against — that ultimately traces back to a federal Reclamation project takes that water subject to the delivery contract's terms, not just the nominal water right. The Central Arizona Project water that Tucson-area operators are relying on for offset credits is the live example. Reclamation can enforce the contract directly, by injunction, against a water user who diverts more than allocated, even where that user also holds an independent state-law right to the same water.",
        "example_case_ids": [
            "US-v-Klamath-Drainage-District-2025"
        ]
    },
    {
        "reading_id": "epcra-312-past-violation-standing",
        "statute": "EPCRA",
        "section": "§325(c) citizen suit, 42 U.S.C. §11046(c); §312 Tier II inventory, 42 U.S.C. §11022",
        "name": "A citizen suit can't be used to punish a violation that's already been fixed",
        "agency": "Private citizen plaintiffs in federal court",
        "what_it_covers": "Steel Co. v. Citizens for a Better Environment (1998) held a citizen group lacked Article III standing to sue over a company's years of missed Tier II hazardous-chemical inventory filings once the company filed everything late but before the suit was brought — because none of the relief EPCRA's citizen-suit provision offers (civil penalties payable to the U.S. Treasury, cost recovery) would redress a purely past, already-cured violation.",
        "dc_applicability": "A data center, or its fuel-farm or chemical-storage contractor, that misses a Tier II filing deadline for backup diesel or cooling-treatment chemicals faces real exposure to a citizen-suit notice letter — but Steel Co. means filing the overdue report before litigation is filed can moot the suit entirely, leaving state regulators or EPA's own enforcement discretion, not a community group, as the only route to a penalty for the historical lapse.",
        "example_case_ids": [
            "SteelCo-v-CitizensForBetterEnvironment-1998"
        ]
    },
    {
        "reading_id": "epcra-313-tri-reporting",
        "statute": "EPCRA",
        "section": "§313, 42 U.S.C. §11023 (Toxic Release Inventory / Form R)",
        "name": "Toxic Release Inventory reporting reaches ordinary processing, not just storage",
        "agency": "EPA",
        "what_it_covers": "EPCRA §313 requires facilities that manufacture, process, or otherwise use a listed toxic chemical above threshold quantities to file an annual public Form R disclosing releases and waste management — separate from, and in addition to, Tier II's hazardous-chemical-storage inventory. EPA's July 2024 enforcement sweep against several Georgia manufacturers, including a $34,730 penalty against Nidec Elesys Americas for failing to file Form R for lead compounds processed at its Suwanee facility in 2021–2022, shows the agency still actively enforces routine TRI non-filing with real penalties, not just Tier II lapses.",
        "dc_applicability": "TRI reporting reaches chemical processing that Tier II's storage-threshold framing can miss — a data-center campus's on-site water-treatment system, biocide dosing, or backup-power battery operations could cross a TRI processing threshold for a listed chemical even where storage volumes alone would not trigger Tier II. The resulting public Form R database is one more FOIA-free source, alongside this tracker's own EPA ECHO pulls, for tracing a campus's chemical footprint without a records request.",
        "example_case_ids": [
            "NidecElesys-Americas-EPCRA-TRI-GA-2024"
        ]
    }
]

NEW_CASES = [
    {
        "case_id": "Hughes-River-Watershed-Conservancy-v-Glickman-1996",
        "category": "precedent",
        "respondent": "Hughes River Watershed Conservancy v. Glickman, 81 F.3d 437 (4th Cir. 1996), and its sequel Hughes River Watershed Conservancy v. Johnson, 165 F.3d 283 (4th Cir. 1999) — North Fork Hughes River multipurpose dam, Ritchie County, WV",
        "year": "1996-1999",
        "cwa_section": "Not a Clean Water Act case — National Environmental Policy Act §102(2)(C), 42 U.S.C. §4332(2)(C) (EIS hard-look and supplementation requirement)",
        "violation_summary": "The Army Corps of Engineers and the Natural Resources Conservation Service planned a multipurpose dam on the North Fork of the Hughes River in northwestern West Virginia, creating a 305-acre lake. Hughes River Watershed Conservancy and other groups challenged the EIS, arguing the agencies inflated the project's recreational-benefit estimate and gave only a cursory look at the risk that the new reservoir would be colonized by invasive zebra mussels.",
        "outcome": "In 1996 the Fourth Circuit agreed on both points: the EIS's use of gross rather than net recreation benefits skewed the cost-benefit analysis in a way that could 'impair the agency's consideration of the adverse environmental effects,' and the agencies had not taken a sufficient 'hard look' at zebra-mussel risk before declining to prepare a supplemental EIS. On remand, the agencies recalculated benefits using net figures and commissioned species-impact studies; in 1999 the Fourth Circuit held the corrected analysis now satisfied NEPA and affirmed summary judgment for the agencies.",
        "takeaway": "NEPA is a forcing mechanism, not an automatic project-killer: an agency that low-balls adverse analysis or inflates benefits will be sent back to do it properly, but a genuinely corrected analysis on remand can satisfy the statute and let the project proceed. For any DC-adjacent federal action (a loan guarantee, a license amendment, a Corps permit), the real question is whether the environmental review is asking the hard questions the first time, not whether NEPA can be satisfied at all.",
        "sources": [
            {
                "title": "Hughes River Watershed Conservancy v. Johnson (4th Cir. 1999) — quotes and describes the 1996 holding on remand (FindLaw)",
                "url": "https://caselaw.findlaw.com/court/us-4th-circuit/1436325.html",
                "type": "court"
            },
            {
                "title": "Potential Impacts of the North Fork Hughes River Project, Ritchie County, West Virginia, on Freshwater Mussels (Unionidae) — Defense Technical Information Center archive",
                "url": "https://apps.dtic.mil/sti/html/tr/ADA373815/index.html",
                "type": "government"
            }
        ],
        "case_type": "water-supply",
        "cwa_applied": "not-applied",
        "cwa_instrument": "NEPA §102(2)(C) — 4th Cir. hard-look/supplemental-EIS requirement, dam EIS remanded then cured",
        "cwa_pathway": "NEPA runs alongside the CWA rather than through it — a §404 permit or a federally financed project still needs its own NEPA review even where the CWA analysis is otherwise complete. Hughes River sets how rigorous that separate review has to be.",
        "display_section": "historical",
        "authorities": [
            "nepa-hard-look-seis"
        ],
        "analogous_cases": [
            "MCEA-PineIsland-MN-ProjectSkyway-2026",
            "Google-ProjectRaspberry-VA-2026",
            "USACE-NWP39-DataCenters-2026"
        ],
        "outcome_type": [
            "compliance-order"
        ]
    },
    {
        "case_id": "Constellation-CraneCleanEnergy-SRBC-NRC-PA-2026",
        "category": "adjacent",
        "respondent": "Constellation Energy Generation, LLC — Christopher M. Crane Clean Energy Center (formerly Three Mile Island Unit 1), Londonderry Township, PA",
        "year": "2025-2026",
        "cwa_section": "Not a Clean Water Act case — NEPA review of an NRC license reauthorization and a DOE loan guarantee; water withdrawal approved under the Susquehanna River Basin Compact",
        "violation_summary": "Not an enforcement action — a bundle of federal and interstate approvals for restarting a shuttered nuclear plant to power a 20-year electricity deal with Microsoft for its data centers. DOE's Loan Programs Office issued a final EIS in August 2025 covering its decision to guarantee financing for the restart. Separately, Constellation sought NRC reauthorization of the plant's operating license (and a name change to the Crane Clean Energy Center); NRC released a draft environmental assessment and finding of no significant impact for public comment in June 2026, having determined a full EIS was not required. On June 4, 2026 the Susquehanna River Basin Commission approved Constellation's request to withdraw up to 73.2 million gallons per day from the Susquehanna River for the plant's cooling and generation needs, conditioned on curtailing or halting withdrawals during drought/low-flow periods.",
        "outcome": "SRBC's withdrawal approval is final, with the drought-curtailment condition attached; commissioners found the volume (about 0.3% of the river's average daily flow) would not cause significant adverse impact. NRC's EA/FONSI was still in the public-comment stage as of July 2026 (comment period closed July 8, 2026); final NRC action on the license reauthorization is unconfirmed and should be re-verified before it is treated as decided. DOE's EIS-0574 (a republication of NRC's 2009 SEIS as a DOE document) is final for the loan-guarantee environmental review. The restart remains on track for a 2027 reopening.",
        "takeaway": "The clearest current example of a data-center power deal running through three separate federal/interstate water-and-environmental gates at once — a basin commission's withdrawal docket, an NRC license review, and a DOE financing EIS — none of which is a CWA action. For any hyperscaler underwriting new or restarted generation, each of these reviews is a public process with its own record, timeline, and conditions, and the basin commission's drought-curtailment condition is a direct water-availability risk to the power (and therefore the data centers) it enables.",
        "sources": [
            {
                "title": "PA Environment Digest Blog: Susquehanna River Basin Commission Approves Constellation Energy Water Withdrawal Requests For Three Mile Island Nuclear Data Center Power Plant Restart",
                "url": "http://paenvironmentdaily.blogspot.com/2026/06/susquehanna-river-basin-commission.html",
                "type": "news"
            },
            {
                "title": "Three Mile Island approved to use 73.2M gallons of water daily from Susquehanna River — Local21News",
                "url": "https://local21news.com/news/local/three-mile-island-approved-to-use-732m-gallons-of-water-daily-from-susquehanna-river-crane-clean-energy-center-nuclear-reactor-data-center-pennsylvania-pa",
                "type": "news"
            },
            {
                "title": "Three Mile Island reactor restart progresses through environmental review, public comments — WITF",
                "url": "https://www.witf.org/2026/07/28/three-mile-island-reactor-restart-progresses-through-environmental-review-public-comments/",
                "type": "news"
            },
            {
                "title": "DOE/EIS-0574: Final Environmental Impact Statement (August 2025) — Department of Energy",
                "url": "https://www.energy.gov/nepa/articles/doeeis-0574-final-environmental-impact-statement-august-2025",
                "type": "government"
            }
        ],
        "case_type": "water-supply",
        "cwa_applied": "not-applied",
        "cwa_instrument": "SRBC withdrawal docket + NRC EA/FONSI + DOE loan-guarantee EIS — nuclear restart to power Microsoft data centers",
        "cwa_pathway": "No CWA discharge action is involved — this is a withdrawal approval under the Susquehanna River Basin Compact plus two federal licensing/financing NEPA reviews. The closest CWA-side analog is the §316 cooling-water-intake reading, which would apply if the plant separately needs its own NPDES thermal permit.",
        "display_section": "historical",
        "authorities": [
            "nepa-federal-financing-review",
            "basin-drbc-srbc-withdrawal-authority"
        ],
        "analogous_cases": [
            "AWS-LakeAnnaVA-VPDES-cooling-discharge-2026",
            "HomerCity-IndianaCounty-PA-NPDES-2026"
        ],
        "outcome_type": [
            "permit-conditioned",
            "pending-undecided"
        ]
    },
    {
        "case_id": "CTS-Corp-v-Waldburger-2014",
        "category": "precedent",
        "respondent": "CTS Corp. v. Waldburger, 573 U.S. 1 (2014) — TCE groundwater contamination, Asheville, NC",
        "year": "2014",
        "cwa_section": "Not a Clean Water Act case — CERCLA §309, 42 U.S.C. §9658 (preemption of state statutes of limitations, and its limit)",
        "violation_summary": "CTS Corporation manufactured electronics on a North Carolina property from 1959 to 1985, then sold it. Owners of the former CTS property and neighboring parcels learned from EPA in 2009 — 24 years after the plant closed — that their groundwater was contaminated with trichloroethylene (TCE), and filed state-law nuisance and property-damage claims in 2011. North Carolina's statute of repose barred property-damage suits filed more than 10 years after the defendant's last act.",
        "outcome": "The Supreme Court held CERCLA §9658 preempts only state statutes of limitations (which run from discovery of the injury), not state statutes of repose (which run from the defendant's last act regardless of discovery). Congress understood and chose that distinction when it wrote §9658 in 1986. The North Carolina plaintiffs' state nuisance claims were accordingly barred, notwithstanding that they could not have discovered the contamination within the repose period.",
        "takeaway": "CERCLA's own federal cleanup authority is unaffected by this ruling, but a data center's (or a neighboring landowner's) separate state-law tort claim over decades-old contamination discovered late can still be time-barred by a state repose statute — a real limit on private recovery that exists independent of, and can be harsher than, the discovery-rule protection CERCLA gives to statutes of limitations.",
        "sources": [
            {
                "title": "Supreme Court Decides CTS Corp. v. Waldburger Evaluating Whether CERCLA Precludes State-Law Statutes of Repose — National Law Review",
                "url": "https://natlawreview.com/article/supreme-court-decides-cts-corp-v-waldburger-evaluating-whether-cercla-precludes-stat",
                "type": "law firm analysis"
            },
            {
                "title": "Supreme Court Decides CTS Corp. v. Waldburger — Faegre Drinker Biddle & Reath",
                "url": "https://www.faegredrinker.com/en/insights/publications/2014/6/supreme-court-decides-cts-corp-v-waldburger",
                "type": "law firm analysis"
            }
        ],
        "case_type": "groundwater",
        "cwa_applied": "not-applied",
        "cwa_instrument": "SCOTUS — CERCLA §9658 preempts limitations periods, not repose periods",
        "cwa_pathway": "CERCLA and any CWA-side remedy (e.g., a citizen suit against an ongoing discharge) can run in parallel, but this reading is about a separate, non-CWA state tort claim a contaminated neighbor might bring — and its own hard time limit.",
        "display_section": "historical",
        "authorities": [
            "cercla-repose-preemption"
        ],
        "analogous_cases": [
            "Amazon-Boardman-OR-nitrate-2026"
        ],
        "outcome_type": [
            "jurisdiction-narrowed",
            "dismissed-no-liability"
        ]
    },
    {
        "case_id": "US-v-Bestfoods-1998",
        "category": "precedent",
        "respondent": "United States v. Bestfoods, 524 U.S. 51 (1998) — Ott Chemical Co. plant, Muskegon, MI",
        "year": "1998",
        "cwa_section": "Not a Clean Water Act case — CERCLA §107(a)(2), 42 U.S.C. §9607(a)(2) (owner/operator liability)",
        "violation_summary": "The United States sued CPC International, the parent corporation of the defunct Ott Chemical Co., for CERCLA cleanup costs at Ott's contaminated Michigan chemical plant, arguing the parent should be liable as an 'operator' of the facility its subsidiary ran.",
        "outcome": "The Supreme Court held a parent corporation is not automatically liable merely because its subsidiary owned or operated the polluting facility — normal corporate separateness controls unless the corporate veil is pierced. But a parent that actively participates in and exercises control over the facility's operations — specifically managing, directing, or deciding on pollution-related compliance — can be held directly liable as an operator under §107(a)(2), independent of any veil-piercing theory. The Court vacated the Sixth Circuit's more sweeping rule and remanded for application of this standard.",
        "takeaway": "Sets the test for when a data-center parent company (rather than the special-purpose subsidiary that formally holds a campus) can be reached for CERCLA liability if legacy contamination is found under or near the site: the question is whether the parent's own personnel actively controlled the environmentally sensitive decisions, not how the ownership chart is drawn.",
        "sources": [
            {
                "title": "United States v. Bestfoods — opinion text (Cornell LII)",
                "url": "https://www.law.cornell.edu/supct/html/97-454.ZO.html",
                "type": "court"
            },
            {
                "title": "United States v. Bestfoods — ‘a Relaxed, CERCLA-specific Rule of Derivative Liability’ (JRank legal encyclopedia)",
                "url": "https://law.jrank.org/pages/25094/United-States-v-Bestfoods--Relaxed-CERCLA-Specific-Rule-Derivative-Liability.html",
                "type": "legal analysis"
            }
        ],
        "case_type": "groundwater",
        "cwa_applied": "not-applied",
        "cwa_instrument": "SCOTUS — CERCLA operator liability requires actual control, not mere ownership",
        "cwa_pathway": "Relevant to who is liable, not what conduct is prohibited — it determines whether a data-center parent (versus its site-level subsidiary) can be reached for a CERCLA cleanup, independent of any CWA permit question.",
        "display_section": "historical",
        "authorities": [
            "cercla-107-operator-liability"
        ],
        "analogous_cases": [
            "Interfaith-v-Honeywell-RCRA-2003-2005"
        ],
        "outcome_type": [
            "jurisdiction-narrowed"
        ]
    },
    {
        "case_id": "Southeastern-Fed-Power-Customers-v-Geren-2008",
        "category": "precedent",
        "respondent": "Southeastern Federal Power Customers, Inc. v. Geren, 514 F.3d 1316 (D.C. Cir. 2008) — Lake Lanier / Buford Dam storage reallocation, GA",
        "year": "2008",
        "cwa_section": "Not a Clean Water Act case — Water Supply Act of 1958 §301(d), 43 U.S.C. §390b(d)",
        "violation_summary": "A consortium of electric utilities that buy hydropower generated at Buford Dam sued the Corps after it signed a 2003 settlement agreement with Georgia and regional water-supply providers letting them draw substantially more municipal and industrial water supply out of Lake Lanier's storage — water that would otherwise pass through the dam's turbines. The power customers argued the reallocation exceeded the Corps' authority under the Water Supply Act.",
        "outcome": "The D.C. Circuit reversed the district court and held the 2003 agreement's reallocation was a 'major operational change' to the project, which §301(d) does not let the Corps make on its own — it requires specific congressional authorization. The settlement's implementation was vacated, reopening the underlying allocation fight for years.",
        "takeaway": "A Corps reservoir's storage is legally partitioned among congressionally authorized purposes, and shifting the balance toward municipal/industrial water supply — exactly what a hyperscale-driven metro region needs as it grows — cannot be done informally by contract or settlement once the shift is 'major.' That ceiling is a real, practical limit on how much data-center-driven regional demand a federal reservoir can absorb without an Act of Congress.",
        "sources": [
            {
                "title": "Southeastern Federal Power Customers, Inc. v. Geren — case note, Tulane Environmental Law Journal",
                "url": "https://journals.tulane.edu/elj/article/view/2215/2049",
                "type": "law review"
            },
            {
                "title": "Reallocation of Water Storage at Federal Water Projects for Municipal and Industrial Use (Congressional Research Service R42805, mirrored by EveryCRSReport)",
                "url": "https://www.everycrsreport.com/files/20121031_R42805_3b0a018c0fad3da3ba58cbad90c4ba045b23e700.pdf",
                "type": "government"
            }
        ],
        "case_type": "water-supply",
        "cwa_applied": "not-applied",
        "cwa_instrument": "WSA §301(d) — D.C. Cir. vacates Lake Lanier storage-reallocation settlement as an unauthorized 'major operational change'",
        "cwa_pathway": "The CWA has no role in how much of a reservoir's storage goes to water supply versus hydropower — that allocation question sits entirely inside the Water Supply Act / RHA authorized-purposes framework this reading covers.",
        "display_section": "historical",
        "authorities": [
            "wsa-reallocation-and-alteration"
        ],
        "analogous_cases": [
            "InRe-MDL1824-TriState-WaterRights-2011",
            "Meta-RichlandParish-LA-WaterSupply-2025",
            "Bessemer-AL-Hyperscale-WaterSupply-2025"
        ],
        "outcome_type": [
            "jurisdiction-narrowed"
        ]
    },
    {
        "case_id": "InRe-MDL1824-TriState-WaterRights-2011",
        "category": "precedent",
        "respondent": "In re MDL-1824 Tri-State Water Rights Litigation, 644 F.3d 1160 (11th Cir. 2011) — Lake Lanier / Buford Dam authorized purposes, GA-AL-FL",
        "year": "2011",
        "cwa_section": "Not a Clean Water Act case — Water Supply Act of 1958 / Rivers and Harbors Act authorized-purposes question, 43 U.S.C. §390b",
        "violation_summary": "Consolidating more than two decades of litigation among Georgia, Alabama, Florida and local water providers, the central question was whether municipal and industrial water supply from Lake Lanier was ever an authorized purpose of the Buford Project in the first place. The district court had held it was not, giving the parties roughly three years to get congressional authorization or face drastic cuts to metro Atlanta's withdrawals.",
        "outcome": "The Eleventh Circuit reversed, holding the Corps and the district court erred: water supply was in fact one of the purposes Congress authorized for the Buford Project under its original 1946 authorization, and is not subordinate to hydropower. The ruling gave Georgia and the Corps a firmer legal basis to continue municipal/industrial withdrawals, feeding into the Corps' 2017 update of the ACF basin's water control manual (itself unsuccessfully challenged by Alabama).",
        "takeaway": "Shows the other side of the Geren coin: courts will recognize water supply as a legitimate, foundational purpose of a Corps reservoir where the original authorization supports it — but that recognition still operates inside the authorized-purposes ceiling, not outside it. A region's ability to keep drawing growth-driven demand from a federal reservoir depends on how that reservoir's authorizing legislation was written decades before anyone anticipated data centers.",
        "sources": [
            {
                "title": "MDL-1824 Tri-State Water Rights Litigation — case summary, Environmental Law Reporter",
                "url": "https://elr.info/litigation/41/20217/mdl-1824-tri-state-water-rights-litigation",
                "type": "law review"
            },
            {
                "title": "11th Circuit Court Of Appeals Weighs In On Army Corps' Statutory Authority For Lake Lanier Operations — Mondaq",
                "url": "https://www.mondaq.com/unitedstates/environment/146306/11th-circuit-court-of-appeals-weighs-in-on-army-corps-statutory-authority-for-lake-lanier-operations",
                "type": "law firm analysis"
            }
        ],
        "case_type": "water-supply",
        "cwa_applied": "not-applied",
        "cwa_instrument": "WSA / RHA authorized-purposes doctrine — 11th Cir. holds water supply was an authorized Buford Project purpose",
        "cwa_pathway": "Same non-CWA allocation question as Geren — whether and how much of a federal reservoir's storage can serve municipal/industrial demand is answered entirely within the Water Supply Act / RHA framework, not the CWA.",
        "display_section": "historical",
        "authorities": [
            "wsa-reallocation-and-alteration"
        ],
        "analogous_cases": [
            "Southeastern-Fed-Power-Customers-v-Geren-2008"
        ],
        "outcome_type": [
            "jurisdiction-affirmed"
        ]
    },
    {
        "case_id": "Foxconn-Racine-GreatLakesCompact-Diversion-2019",
        "category": "industrial",
        "respondent": "Racine Water Utility / Wisconsin DNR — Great Lakes Compact straddling-community diversion for the Foxconn campus, Mount Pleasant, WI",
        "year": "2018-2019",
        "cwa_section": "Not a Clean Water Act case — Great Lakes-St. Lawrence River Basin Water Resources Compact, Art. 4.9 straddling-community exception",
        "violation_summary": "Wisconsin approved Racine Water Utility's application in April 2018 to divert up to 7 million gallons per day of Lake Michigan water to serve the Village of Mount Pleasant, most of it (5.8 MGD) earmarked for the Foxconn LCD manufacturing campus, under the Compact's exception for a utility serving a 'straddling community' that sits partly inside and partly outside the Great Lakes basin. Midwest Environmental Advocates, FLOW, and other groups challenged the approval, arguing the diversion was not really for 'public water supply' since the overwhelming majority would go to one private industrial customer, and so violated the Compact's terms.",
        "outcome": "A Wisconsin administrative law judge rejected the challengers' arguments in June 2019, reasoning that a public water supply can serve industrial as well as residential customers, and upheld the DNR's approval of the diversion. Midwest Environmental Advocates and its co-petitioners chose not to appeal further; the matter never reached state or federal court.",
        "takeaway": "Establishes that the Compact's straddling-community exception can support a diversion overwhelmingly destined for one large industrial user, so long as it nominally runs through a public utility's system — the same legal structure by which the site now hosting Microsoft's Mount Pleasant data centers already receives Lake Michigan water outside the Compact's default no-diversion rule.",
        "sources": [
            {
                "title": "Monitoring the Implementation of the Great Lakes Compact in Racine — Midwest Environmental Advocates",
                "url": "https://midwestadvocates.org/our-work/legal-action/racine-diversion-challenge/",
                "type": "advocacy"
            },
            {
                "title": "Approval For Foxconn Great Lakes Water Diversion Upheld — Wisconsin Public Radio",
                "url": "https://www.wpr.org/economy/approval-foxconn-great-lakes-water-diversion-upheld",
                "type": "news"
            }
        ],
        "case_type": "water-supply",
        "cwa_applied": "not-applied",
        "cwa_instrument": "Great Lakes Compact straddling-community exception — ALJ upholds 7 MGD Racine-to-Foxconn diversion",
        "cwa_pathway": "Great Lakes withdrawals are governed by the Compact rather than the CWA — the same gap the Microsoft Mount Pleasant WI wetland-permit case in this dataset already flags in its own pathway note.",
        "display_section": "historical",
        "authorities": [
            "basin-glc-diversion"
        ],
        "analogous_cases": [
            "Microsoft-MountPleasantWI-wetland-individual-permit-2024",
            "MilwaukeeRiverkeeper-RacineWI-water-records-suit-2025"
        ],
        "outcome_type": [
            "permit-issued"
        ]
    },
    {
        "case_id": "Panda-Power-Funds-SRBC-Penalty-2016",
        "category": "industrial",
        "respondent": "Panda Power Funds — Patriot (Lycoming Co.) and Hummel Station (Snyder Co.) natural gas power plants, PA",
        "year": "2016",
        "cwa_section": "Not a Clean Water Act case — Susquehanna River Basin Compact §3.10, water withdrawal approval and enforcement",
        "violation_summary": "During construction and commissioning of two new natural gas power plants, Panda Power Funds used water sources SRBC had not approved and exceeded its approved daily withdrawal limits from a public water supply source. SRBC staff identified the violations and proposed penalties.",
        "outcome": "SRBC and Panda reached a proposed settlement totaling roughly $97,000 across the affected plants — including $44,250 for the Patriot plant's unapproved-source and over-withdrawal violations and $22,750 for similar issues at Hummel Station. Panda's spokesman said the company worked with SRBC on the resolution, attributing some of the problem to permits obtained by a prior developer that did not match the plants' actual requirements.",
        "takeaway": "A concrete demonstration that SRBC enforces its withdrawal-approval authority with real penalties against power-plant developers, not just paperwork conditions — the same commission, and the same enforcement posture, that now governs the Crane Clean Energy Center's water supply for Microsoft's data centers.",
        "sources": [
            {
                "title": "Gas power plants face $97,000 in fines for water use — StateImpact Pennsylvania (NPR)",
                "url": "https://stateimpact.npr.org/pennsylvania/2016/12/01/gas-power-plants-face-97000-in-fines-for-water-use",
                "type": "news"
            },
            {
                "title": "Panda Power facing fines for water usage at PA plants — WKOK Newsradio",
                "url": "https://www.wkok.com/panda-power-facing-fines-for-water-usage-at-pa-plants/",
                "type": "news"
            }
        ],
        "case_type": "water-supply",
        "cwa_applied": "not-applied",
        "cwa_instrument": "SRBC withdrawal-approval enforcement — ~$97,000 proposed penalty for unapproved sources and over-withdrawal",
        "cwa_pathway": "A withdrawal-side violation (unapproved sources, exceeding limits), not a discharge — the CWA's NPDES program has no equivalent gate on how much water a facility takes out of the river in the first place.",
        "display_section": "historical",
        "authorities": [
            "basin-drbc-srbc-withdrawal-authority"
        ],
        "analogous_cases": [
            "HomerCity-IndianaCounty-PA-NPDES-2026"
        ],
        "outcome_type": [
            "monetary-penalty"
        ]
    },
    {
        "case_id": "DRBC-Fracking-Ban-2021",
        "category": "industrial",
        "respondent": "Delaware River Basin Commission — basin-wide ban on high-volume hydraulic fracturing",
        "year": "2021",
        "cwa_section": "Not a Clean Water Act case — Delaware River Basin Compact §3.8, Comprehensive Plan amendment",
        "violation_summary": "Not an enforcement action — a regulatory decision. Natural gas production in the Marcellus Shale had been under DRBC review since 2009 because of concerns about the water withdrawals fracking requires and its water-quality impacts; the Commission had held draft fracking regulations in limbo for over a decade.",
        "outcome": "On February 25, 2021 the four voting commissioners (with the federal government abstaining) adopted final regulations permanently banning high-volume hydraulic fracturing throughout the Delaware River Basin, by amending the Compact's Comprehensive Plan. A December 2022 follow-on rule separately banned the discharge of fracking wastewater within the basin and the export of basin water for use in fracking elsewhere, without banning transport and disposal of fracking waste itself.",
        "takeaway": "The clearest available demonstration that an interstate basin commission's water authority extends to prohibiting an entire water-intensive industrial activity outright, not just permitting or conditioning it — the most protective end of the range of outcomes a large new water user (including a data center) can face inside a compact basin.",
        "sources": [
            {
                "title": "Delaware River Basin Commission votes to ban fracking in the watershed — WHYY",
                "url": "https://whyy.org/articles/delaware-river-basin-commission-votes-to-ban-fracking-in-the-watershed/",
                "type": "news"
            },
            {
                "title": "Fracking Banned in the Delaware River Basin! — NRDC",
                "url": "https://www.nrdc.org/bio/marisa-guerrero/fracking-banned-delaware-river-basin",
                "type": "advocacy"
            }
        ],
        "case_type": "water-supply",
        "cwa_applied": "not-applied",
        "cwa_instrument": "DRBC Comprehensive Plan amendment — permanent basin-wide fracking ban",
        "cwa_pathway": "A basin-wide prohibition on an activity because of its water demand, not its discharges — illustrates that a compact commission's authority over withdrawal is broader than anything the CWA grants EPA over intake.",
        "display_section": "historical",
        "authorities": [
            "basin-drbc-srbc-withdrawal-authority"
        ],
        "analogous_cases": [
            "Rowan-ProjectCinco-Medina-TX-2025"
        ],
        "outcome_type": [
            "permit-denied"
        ]
    },
    {
        "case_id": "BlueRidgeProject-NewRiver-WSR-1976",
        "category": "precedent",
        "respondent": "Appalachian Power Company — proposed Blue Ridge Project pumped-storage hydro complex, New River, VA/NC",
        "year": "1976",
        "cwa_section": "Not a Clean Water Act case — Wild and Scenic Rivers Act §7, 16 U.S.C. §1278(a)",
        "violation_summary": "Appalachian Power Company spent over a decade seeking approval for the Blue Ridge Project, a massive two-reservoir pumped-storage hydroelectric facility spanning Grayson County, VA and Ashe/Alleghany Counties, NC. The Federal Power Commission granted a license for the project in June 1974. Opponents pushed instead for federal protection of the free-flowing river.",
        "outcome": "In April 1976 the Secretary of the Interior designated the relevant 26.5-mile segment of the New River as part of the National Wild and Scenic Rivers System; Congress reaffirmed that designation by statute, and President Ford signed the bill into law on September 11, 1976. Construction of the dam and reservoirs was thereby prohibited under §7's bar on water-resources projects affecting a designated river. The Blue Ridge Project was never built.",
        "takeaway": "Section 7 is not just a screen against new proposals — it can nullify a hydropower license that has already been granted once Congress designates the affected river. Any DC-adjacent power or water infrastructure proposed near a river that is designated, or under active study, for Wild and Scenic status carries this override risk regardless of how far permitting has already progressed.",
        "sources": [
            {
                "title": "Saving the New River — Appalachian Voices",
                "url": "https://appvoices.org/2007/04/18/2808/",
                "type": "advocacy"
            },
            {
                "title": "The Appalachian Power Company Along the New River: The Defeat of the Blue Ridge Project in Historical Perspective — Virginia Tech VTechWorks",
                "url": "https://vtechworks.lib.vt.edu/items/0e6df976-2259-4bcd-a55a-05e250484a30",
                "type": "academic"
            }
        ],
        "case_type": "water-supply",
        "cwa_applied": "not-applied",
        "cwa_instrument": "WSR §7 — 1976 Wild and Scenic designation bars the already-FPC-licensed Blue Ridge Project",
        "cwa_pathway": "The CWA's §404/§401 gates apply to a hydro project's construction impacts; §7 is a separate, prior question of whether the project can be licensed at all on a designated river — it can moot CWA permitting entirely by blocking the license first.",
        "display_section": "historical",
        "authorities": [
            "wsr-7-hydropower-bar"
        ],
        "analogous_cases": [
            "HomerCity-IndianaCounty-PA-NPDES-2026",
            "Constellation-CraneCleanEnergy-SRBC-NRC-PA-2026"
        ],
        "outcome_type": [
            "permit-denied"
        ]
    },
    {
        "case_id": "California-v-FERC-1990",
        "category": "precedent",
        "respondent": "California v. Federal Energy Regulatory Commission, 495 U.S. 490 (1990) — Rock Creek hydroelectric project, CA",
        "year": "1990",
        "cwa_section": "Not a Clean Water Act case — Federal Power Act §10(a), 16 U.S.C. §803(a) (preemption of state minimum-flow conditions)",
        "violation_summary": "FERC licensed a hydroelectric project on California's Rock Creek and set an interim minimum instream flow rate for the bypassed stream reach. California's State Water Resources Control Board issued a state permit initially matching FERC's interim rate but reserved the right to set stricter permanent minimum flows later. When the state board moved toward permanent flow requirements well above FERC's rate, the licensee asked FERC to declare its own jurisdiction exclusive.",
        "outcome": "The Supreme Court held the Federal Power Act preempts a state from imposing minimum stream-flow requirements beyond what FERC's license allows for a licensed hydroelectric project — letting a state layer on different or stricter flow rules would effectively give it a veto over the FERC licensing process the FPA does not grant.",
        "takeaway": "Water flow and reservoir-level decisions at a FERC-licensed hydro facility are made through the FERC license itself, not through state water law — relevant to any data center that would draw cooling water from, or co-locate power supply at, a FERC-licensed dam. Getting more water for such a use runs through a license amendment or relicensing at FERC, not a state permit.",
        "sources": [
            {
                "title": "California v. Federal Energy Regulatory Commission — opinion text (Cornell LII)",
                "url": "https://www.law.cornell.edu/supremecourt/text/495/490",
                "type": "court"
            },
            {
                "title": "California v. Federal Energy Regulatory Commission — case brief summary, Studicata",
                "url": "https://www.studicata.com/case-briefs/case/california-v-federal-energy-regulatory-commission",
                "type": "legal analysis"
            }
        ],
        "case_type": "water-supply",
        "cwa_applied": "not-applied",
        "cwa_instrument": "SCOTUS — FPA preempts state minimum-flow rules on a FERC-licensed hydro project",
        "cwa_pathway": "Distinct from the CWA §401 certification reading — §401 lets a state condition or deny certification of a federally licensed project up front, while this doctrine holds a state cannot also impose independent minimum-flow rules once the license issues. The two operate at different stages of the same project.",
        "display_section": "historical",
        "authorities": [
            "fpa-license-flow-preemption"
        ],
        "analogous_cases": [
            "Constellation-CraneCleanEnergy-SRBC-NRC-PA-2026",
            "AWS-LakeAnnaVA-VPDES-cooling-discharge-2026"
        ],
        "outcome_type": [
            "jurisdiction-affirmed"
        ]
    },
    {
        "case_id": "US-v-Klamath-Drainage-District-2025",
        "category": "precedent",
        "respondent": "United States v. Klamath Drainage District, No. 23-3404 (9th Cir., decided Jan. 2025) — Klamath Reclamation Project, OR/CA border",
        "year": "2025",
        "cwa_section": "Not a Clean Water Act case — Reclamation contract law; 1946 repayment contract under 43 U.S.C. §371 et seq.",
        "violation_summary": "The United States sued Klamath Drainage District (KDD) in 2022 for breach of its 1946 contract with the Bureau of Reclamation, alleging KDD diverted water through the federal Klamath Project's canal system in a year when Reclamation had determined no water was allocated to the district. KDD argued it could instead divert water through its own separate canal under a 1977 state-law water right it held independent of the federal project.",
        "outcome": "The district court granted summary judgment for the United States and entered a 2023 injunction barring KDD's unauthorized diversions; the Ninth Circuit affirmed in January 2025, holding the 1946 contract's plain language authorized Reclamation to control KDD's diversions from the Klamath River and to administer the project through 'reasonable rules and regulations' — reaching even the district's separately held 1977 water right, because it was exercised through works covered by the federal contract.",
        "takeaway": "A federal Reclamation contract's delivery terms can control a water user's diversions even against a water right the user holds independently of the federal project. Any western data-center water supply that traces back to a Reclamation project or its infrastructure inherits the contract's limits, and Reclamation can enforce them directly by injunction.",
        "sources": [
            {
                "title": "Ruling: Federal contract controls non-federal Klamath water diversions — Capital Press",
                "url": "https://capitalpress.com/2025/01/28/ruling-federal-contract-controls-non-federal-klamath-water-diversions/",
                "type": "news"
            },
            {
                "title": "Court rules BOR can regulate Klamath water use — Western Livestock Journal",
                "url": "https://www.wlj.net/court-rules-bor-can-regulate-klamath-water-use/",
                "type": "news"
            }
        ],
        "case_type": "water-supply",
        "cwa_applied": "not-applied",
        "cwa_instrument": "9th Cir. — Reclamation contract controls district's diversions, injunction affirmed",
        "cwa_pathway": "No CWA issue in the ruling itself — it concerns who controls delivery volumes under a federal water contract, upstream of any question about discharge from the water once delivered.",
        "display_section": "historical",
        "authorities": [
            "recl-contract-controls-delivery"
        ],
        "analogous_cases": [
            "ProjectBlue-Tucson-AMES-2026"
        ],
        "outcome_type": [
            "jurisdiction-affirmed",
            "injunction-stop-work"
        ]
    },
    {
        "case_id": "SteelCo-v-CitizensForBetterEnvironment-1998",
        "category": "precedent",
        "respondent": "Steel Co. v. Citizens for a Better Environment, 523 U.S. 83 (1998) — Tier II hazardous-chemical reporting, IL",
        "year": "1998",
        "cwa_section": "Not a Clean Water Act case — EPCRA §325(c) citizen suit, 42 U.S.C. §11046(c) (Article III standing)",
        "violation_summary": "Citizens for a Better Environment sent Steel Company a 60-day notice of intent to sue over years of allegedly missed EPCRA Tier II and related hazardous-chemical reporting filings. Steel Company filed all its overdue forms before the citizen suit was filed, then argued the case was moot because there was no ongoing violation left to remedy.",
        "outcome": "The Supreme Court held the citizen group lacked Article III standing: none of the relief EPCRA's citizen-suit provision authorizes (civil penalties payable to the U.S. Treasury, litigation cost recovery) would redress a purely past, already-cured violation, so there was no live case or controversy for a federal court to hear. The Seventh Circuit's contrary holding, that EPCRA authorized suits for wholly past violations, was reversed.",
        "takeaway": "A citizen group's practical leverage against a data center's or fuel-farm contractor's Tier II reporting lapse largely evaporates once the missing reports are filed, before a notice-triggered suit is actually brought — curing the paperwork quickly is a complete defense to citizen litigation over the historical gap, leaving only EPA's or a state's own enforcement discretion in play.",
        "sources": [
            {
                "title": "Steel Co. v. Citizens for a Better Environment — opinion text (Cornell LII)",
                "url": "https://www.law.cornell.edu/supct/html/96-643.ZO.html",
                "type": "court"
            },
            {
                "title": "Steel Co. v. Citizens for a Better Environment — case brief summary, Studicata",
                "url": "https://www.studicata.com/case-briefs/case/steel-co-v-citizens-for-better-env-t",
                "type": "legal analysis"
            }
        ],
        "case_type": "spills-contamination",
        "cwa_applied": "not-applied",
        "cwa_instrument": "SCOTUS — no Article III standing for EPCRA citizen suit over wholly past, cured violations",
        "cwa_pathway": "EPCRA's citizen-suit provision is structured like the CWA's §505 (60-day notice, penalties to the Treasury), but Steel Co.'s redressability holding limits it more sharply than courts have limited CWA citizen suits over ongoing violations.",
        "display_section": "historical",
        "authorities": [
            "epcra-312-past-violation-standing"
        ],
        "analogous_cases": [
            "QTS-Fayetteville-GA-2024",
            "TransGas-AdamsFork-WV-2025"
        ],
        "outcome_type": [
            "dismissed-no-liability",
            "jurisdiction-narrowed"
        ]
    },
    {
        "case_id": "NidecElesys-Americas-EPCRA-TRI-GA-2024",
        "category": "industrial",
        "respondent": "Nidec Elesys Americas Corporation — automotive electronics facility, Suwanee, GA",
        "year": "2024",
        "cwa_section": "Not a Clean Water Act case — EPCRA §313, 42 U.S.C. §11023 (Toxic Release Inventory reporting)",
        "violation_summary": "EPA alleged Nidec Elesys Americas failed to submit the required annual Form R under EPCRA §313 for lead compounds processed at its Suwanee, Georgia facility during calendar years 2021 and 2022, as part of a broader July 2024 enforcement sweep against several Georgia manufacturers for EPCRA Tier II and Toxic Release Inventory reporting gaps (including a $82,700 penalty against Purafil Inc. of Doraville and a $74,123 penalty against Hussmann Corp., also in Suwanee).",
        "outcome": "EPA and Nidec Elesys resolved the matter through a Consent Agreement and Final Order filed July 8, 2024, requiring the company to pay a $34,730 civil penalty.",
        "takeaway": "EPA continues to actively enforce routine EPCRA §313 non-filing with real, if modest, penalties across ordinary manufacturing operations — illustrating the exposure a data-center campus's on-site chemical processing (water treatment, biocide dosing, battery operations) could face if it crosses a TRI threshold and does not file, independent of whether the same chemicals ever reach a permitted discharge.",
        "sources": [
            {
                "title": "EPA Fines Companies for Alleged Violations of the Emergency Planning and Community Right-to-Know Act — EPA newsroom",
                "url": "https://www.epa.gov/newsreleases/epa-fines-companies-alleged-violations-emergency-planning-and-community-right-know-act",
                "type": "government"
            },
            {
                "title": "'Citizens have a right to know': EPA fines 4 Georgia companies, others — WSAV-TV",
                "url": "https://www.wsav.com/environmental-news/citizens-have-a-right-to-know-epa-fines-4-georgia-companies-others/",
                "type": "news"
            }
        ],
        "case_type": "spills-contamination",
        "cwa_applied": "not-applied",
        "cwa_instrument": "EPCRA §313 — $34,730 CAFO penalty for unfiled Form R (lead compounds)",
        "cwa_pathway": "Independent of any CWA permit — a processing-and-reporting duty that applies regardless of whether the same chemicals are ever discharged under an NPDES or pretreatment permit.",
        "display_section": "historical",
        "authorities": [
            "epcra-313-tri-reporting"
        ],
        "analogous_cases": [
            "QTS-Fayette-GA-unbilled-water-2026",
            "MilwaukeeRiverkeeper-RacineWI-water-records-suit-2025"
        ],
        "outcome_type": [
            "monetary-penalty"
        ]
    }
]

SITE_MAPPINGS = [
    {
        "site_id": "microsoft-racine-county-wi",
        "reading_id": "basin-glc-diversion",
        "how": "The campus draws Lake Michigan water through the Racine Water Utility's straddling-community diversion approved in 2018 for the Foxconn campus it now occupies — the same Compact exception, upheld on the same 'is this really public water supply' argument the site's expansion would face again if the diversion volume needs to grow.",
        "analogous_cases": [
            "Foxconn-Racine-GreatLakesCompact-Diversion-2019"
        ]
    },
    {
        "site_id": "qts-fayette-county-ga",
        "reading_id": "wsa-reallocation-and-alteration",
        "how": "The campus sits in the Flint River headwaters — part of the ACF basin whose interstate storage and allocation fights (the Lake Lanier reallocation litigation) established the basin-wide ceiling on how much new municipal/industrial demand a Corps reservoir can absorb. This particular incident was a local metering failure rather than a reservoir-storage dispute, but growing unmetered data-center draws in this basin add to the same supply picture the reallocation fight was about.",
        "analogous_cases": [
            "Southeastern-Fed-Power-Customers-v-Geren-2008",
            "InRe-MDL1824-TriState-WaterRights-2011"
        ]
    },
    {
        "site_id": "project-blue-tucson-az",
        "reading_id": "recl-contract-controls-delivery",
        "how": "Project Blue's public water-positivity offset plan includes purchasing additional Central Arizona Project water and supporting CAP-linked recharge — a Bureau of Reclamation project — to offset its own groundwater pumping, tying its water math to Reclamation-delivered supply even though its physical withdrawal is through private wells under state ADWR permits, not a Reclamation contract directly.",
        "analogous_cases": [
            "US-v-Klamath-Drainage-District-2025"
        ]
    }
]


def _append_note(payload: dict, sentence: str) -> None:
    """Append a sentence to a file-level note unless it is already there."""
    note = payload.get("note", "")
    if sentence.strip() not in note:
        payload["note"] = note.rstrip() + sentence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sys.path.insert(0, str(BASE_DIR))
    from refdata.taxonomies import (
        AUTHORITY_KIND_LABELS,
        CWA_CASE_TYPE_LABELS,
        CWA_CATEGORY_ORDER,
        CWA_STATUS_LABELS,
        OUTCOME_TYPE_LABELS,
        WATER_STATUTE_COLORS,
        WATER_STATUTE_ORDER,
    )

    authorities = json.loads(AUTHORITIES_PATH.read_text(encoding="utf-8"))
    cases_payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    conflicts = json.loads(CONFLICTS_PATH.read_text(encoding="utf-8"))
    problems: list[str] = []

    for code, meta in NEW_STATUTES.items():
        if meta.get("kind") not in AUTHORITY_KIND_LABELS:
            problems.append(f"{code}: bad kind {meta.get('kind')}")
        if code not in WATER_STATUTE_ORDER:
            problems.append(f"{code}: add it to WATER_STATUTE_ORDER in taxonomies.py")
        if code not in WATER_STATUTE_COLORS:
            problems.append(f"{code}: no colour in WATER_STATUTE_COLORS")
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
        if case["category"] not in CWA_CATEGORY_ORDER:
            problems.append(f"{case['case_id']}: bad category {case['category']}")
        if case["case_type"] not in CWA_CASE_TYPE_LABELS:
            problems.append(f"{case['case_id']}: bad case_type {case['case_type']}")
        if case["cwa_applied"] not in CWA_STATUS_LABELS:
            problems.append(f"{case['case_id']}: bad cwa_applied {case['cwa_applied']}")
        for otype in case["outcome_type"]:
            if otype not in OUTCOME_TYPE_LABELS:
                problems.append(f"{case['case_id']}: bad outcome_type {otype}")
        if len(case.get("sources", [])) < 2:
            problems.append(f"{case['case_id']}: needs at least 2 sources")
        # A case the CWA never touched has to say which tracked matters its
        # pathway would run through, or the reader is left with a doctrine and
        # nothing to point it at.
        if case["cwa_applied"] in ("pending", "not-applied") and not case.get(
            "analogous_cases"
        ):
            problems.append(f"{case['case_id']}: needs analogous_cases")
        cases_payload["cases"].append(case)
        added_cases.append(case["case_id"])

    all_case_ids = {c["case_id"] for c in cases_payload["cases"]}
    all_reading_ids = {r["reading_id"] for r in authorities["readings"]}
    for reading in NEW_READINGS:
        for cid in reading["example_case_ids"]:
            if cid not in all_case_ids:
                problems.append(f"{reading['reading_id']}: example case {cid} not found")
    for case in NEW_CASES:
        for rid in case["authorities"]:
            if rid not in all_reading_ids:
                problems.append(f"{case['case_id']}: unknown reading {rid}")
        for cid in case.get("analogous_cases", []):
            if cid not in all_case_ids:
                problems.append(f"{case['case_id']}: unknown analog {cid}")

    sites_by_id = {s["site_id"]: s for s in conflicts["sites"]}
    added_mappings = []
    for mapping in SITE_MAPPINGS:
        site = sites_by_id.get(mapping["site_id"])
        if site is None:
            problems.append(f"unknown site {mapping['site_id']}")
            continue
        if mapping["reading_id"] not in all_reading_ids:
            problems.append(
                f"{mapping['site_id']}: unknown reading {mapping['reading_id']}"
            )
            continue
        if len(mapping.get("how", "")) < 80:
            problems.append(
                f"{mapping['site_id']}/{mapping['reading_id']}: `how` is too thin"
            )
        for cid in mapping.get("analogous_cases", []):
            if cid not in all_case_ids:
                problems.append(f"{mapping['site_id']}: unknown analog {cid}")
        existing = {m["reading_id"] for m in site.get("applicable_readings", [])}
        if mapping["reading_id"] in existing:
            continue
        entry = {k: v for k, v in mapping.items() if k != "site_id"}
        site.setdefault("applicable_readings", []).append(entry)
        added_mappings.append(f"{mapping['site_id']} += {mapping['reading_id']}")

    print(f"families added:   {len(added_statutes)}  {added_statutes}")
    print(f"readings added:   {len(added_readings)}")
    for r in added_readings:
        print(f"  + {r}")
    print(f"cases added:      {len(added_cases)}")
    for c in added_cases:
        print(f"  + {c}")
    print(f"site mappings:    {len(added_mappings)}")
    for m in added_mappings:
        print(f"  ~ {m}")
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

    for payload, path, sentence in (
        (authorities, AUTHORITIES_PATH, AUTHORITIES_NOTE),
        (cases_payload, CASES_PATH, CASES_NOTE),
        (conflicts, CONFLICTS_PATH, CONFLICTS_NOTE),
    ):
        payload["last_updated"] = LAST_UPDATED
        _append_note(payload, sentence)
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print("\nWrote water_authorities.json, cwa_investigations.json, dc_water_conflicts.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
