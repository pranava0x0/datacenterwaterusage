#!/usr/bin/env python3
"""Append the 2026-07-25 policy-instrument entries to legislation.json.

Adds the layer the tracker was missing entirely (plan gap G1): federal
executive actions. EO 14318 is the reason the §404 nationwide permit the
tracker already records was reissued naming data centers, so the record had the
*consequence* without the *cause*. Also adds NY EO 62 — the instrument that
actually imposed New York's moratorium, which matters because the tracked
NY S10642/A11560 was never signed or vetoed; the Governor superseded it.

Plus the first commission-docket entries (Spec B2) and the July 2026 local
moratoria whose stated rationale is water.

Every entry is written append-only with sources. Where a fact could not be
confirmed against a primary or second independent source it carries
``verified: false`` and a ``status_detail`` naming what to re-check, per the
fail-closed curation rule.

Run: ``python3 scripts/add_policy_instruments_2026_07.py [--dry-run]``
Idempotent — an entry whose bill_id already exists is skipped.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

LEGISLATION_PATH = BASE_DIR / "data" / "reference" / "legislation.json"

NEW_ENTRIES = [
    {
        "bill_id": "US EO 14318",
        "instrument_type": "executive-order",
        "jurisdiction": "United States",
        "level": "federal",
        "title": "Accelerating Federal Permitting of Data Center Infrastructure",
        "sponsor": "President Trump (Executive Order 14318, 90 FR 142)",
        "summary": (
            "Directs the Army Corps to identify or develop a data-center-specific "
            "nationwide permit under CWA §404 and Rivers and Harbors Act §10, "
            "establishes NEPA categorical exclusions for data-center infrastructure, "
            "provides for programmatic ESA §7 consultation covering multi-year "
            "construction windows, and expands FAST-41 coverage to qualifying data "
            "centers. Sets the >100 MW 'Data Center Project' and $500M / "
            "national-security 'Qualifying Project' thresholds the implementing "
            "actions key off."
        ),
        "scope": ["water", "energy"],
        "status": "enacted",
        "status_detail": (
            "Signed 2025-07-23; in force and substantially implemented — the Army "
            "Corps' 2026 reissuance of Nationwide Permit 39 expressly enumerating "
            "data centers is the §404 directive carried out. NB: the order reaches "
            "§404 dredge-and-fill and RHA §10 only; it contains no NPDES (§402) "
            "directive, so operational discharge permitting is untouched by it."
        ),
        "source_url": "https://www.whitehouse.gov/presidential-actions/2025/07/accelerating-federal-permitting-of-data-center-infrastructure/",
        "last_verified": "2026-07-25",
        "verified": True,
        "confidence": "high",
        "related_case_ids": ["USACE-NWP39-DataCenters-2026"],
        "implements": ["US AI Action Plan 2025"],
        "general_principles": [
            {
                "tag": "Permitting acceleration",
                "note": (
                    "The defining federal instrument on the deregulatory side: it "
                    "directs agencies to find faster §404/§10 pathways for data "
                    "centers rather than to condition them."
                ),
            },
            {
                "tag": "Federal coordination",
                "note": (
                    "Centralizes data-center permitting through FAST-41 and "
                    "programmatic consultations instead of project-by-project review."
                ),
            },
        ],
        "timeline": [
            {
                "date": "2025-07-23",
                "milestone": "Signed",
                "detail": "Issued alongside America's AI Action Plan; published at 90 FR 142",
            },
            {
                "date": "2026-04-02",
                "milestone": "First FAST-41 data center",
                "detail": "QTS Richmond Technology Park DC5 becomes the first data center covered",
            },
        ],
        "recent_news": [
            {
                "date": "2025-07-23",
                "title": "Accelerating Federal Permitting of Data Center Infrastructure",
                "source": "The White House",
                "url": "https://www.whitehouse.gov/presidential-actions/2025/07/accelerating-federal-permitting-of-data-center-infrastructure/",
                "takeaway": (
                    "Directs the Army Corps to apply or develop a data-center "
                    "nationwide permit under CWA §404 and RHA §10."
                ),
            },
            {
                "date": "2025-07-28",
                "title": "White House Aims To Accelerate Environmental Permitting For Data Centers",
                "source": "Allen Matkins",
                "url": "https://www.allenmatkins.com/real-ideas/white-house-aims-to-accelerate-environmental-permitting-for-data-centers.html",
                "takeaway": (
                    "Practitioner read of the order's scope: NEPA categorical "
                    "exclusions, §404/§10 nationwide permit, FAST-41 expansion."
                ),
            },
        ],
        "public_sentiment": (
            "Sharply split. Industry and permitting-reform advocates treat it as "
            "removing a genuine bottleneck; water and conservation groups read the "
            "§404 nationwide-permit route as replacing individual wetland review "
            "with a checkbox precisely as data-center footprints grow."
        ),
    },
    {
        "bill_id": "US AI Action Plan 2025",
        "instrument_type": "executive-order",
        "jurisdiction": "United States",
        "level": "federal",
        "title": "Winning the Race: America's AI Action Plan",
        "sponsor": "White House Office of Science and Technology Policy",
        "summary": (
            "The policy blueprint EO 14318 implements. Calls for a data-center-tailored "
            "Clean Water Act §404 nationwide permit, new NEPA categorical exclusions, "
            "FAST-41 expansion, and streamlining or reduction of Clean Air Act, Clean "
            "Water Act and CERCLA requirements for AI infrastructure."
        ),
        "scope": ["water", "energy"],
        "status": "enacted",
        "status_detail": (
            "Released 2025-07-23, the same day as EO 14318. A blueprint rather than a "
            "legal instrument — it binds nobody directly, but it is the stated source "
            "of the §404 and FAST-41 directives that do."
        ),
        "source_url": "https://www.whitehouse.gov/wp-content/uploads/2025/07/Americas-AI-Action-Plan.pdf",
        "last_verified": "2026-07-25",
        "verified": True,
        "confidence": "high",
        "general_principles": [
            {
                "tag": "Permitting acceleration",
                "note": (
                    "Names the CWA, CAA and CERCLA as burdens to reduce for AI "
                    "infrastructure — the clearest statement of the federal posture."
                ),
            }
        ],
        "timeline": [
            {
                "date": "2025-07-23",
                "milestone": "Released",
                "detail": "Published alongside EO 14318",
            }
        ],
        "recent_news": [
            {
                "date": "2025-07-28",
                "title": "New Federal AI Action Plan Prioritizes Deregulation, Infrastructure, and Global Leadership",
                "source": "Morrison Foerster",
                "url": "https://www.mofo.com/resources/insights/250728-new-federal-ai-action-plan-prioritizes-deregulation",
                "takeaway": (
                    "Confirms the plan's environmental-permitting asks, including the "
                    "data-center §404 nationwide permit later reissued as NWP 39."
                ),
            }
        ],
        "public_sentiment": (
            "Received as the administration's clearest statement that AI-infrastructure "
            "buildout outranks incremental environmental review."
        ),
    },
    {
        "bill_id": "NY EO 62",
        "instrument_type": "executive-order",
        "jurisdiction": "New York",
        "level": "state",
        "title": "Temporary Moratorium on Data Centers While the State Develops Standards",
        "sponsor": "Gov. Kathy Hochul",
        "summary": (
            "One-year pause on DEC discretionary permits for data centers at or above "
            "50 MW. Orders the Department of Public Service to report on data-center "
            "impacts including water use and water quality, and directs DEC to assess "
            "within 12 months whether the state's water-withdrawal program needs new "
            "rules for very large users."
        ),
        "scope": ["water", "energy"],
        "status": "enacted",
        "status_detail": (
            "Signed 2026-07-14; in force. This — not the tracked NY S10642/A11560 — is "
            "the instrument that actually imposed New York's moratorium. The Governor "
            "neither signed nor vetoed the bill; she superseded it with an executive "
            "order at a higher threshold (50 MW vs the bill's 20 MW), which is a "
            "materially narrower pause than the bill would have imposed."
        ),
        "source_url": "https://www.governor.ny.gov/executive-order/no-62-establishing-temporary-moratorium-data-centers-new-york-while-state-develops",
        "last_verified": "2026-07-25",
        "verified": True,
        "confidence": "high",
        "general_principles": [
            {
                "tag": "Moratorium",
                "note": "First statewide data-center moratorium actually in effect anywhere in the US.",
            },
            {
                "tag": "Permit oversight",
                "note": "Pauses DEC discretionary permitting rather than banning construction outright.",
            },
            {
                "tag": "Preemptive review",
                "note": (
                    "Orders the DEC water-withdrawal-program assessment and the DPS "
                    "impact report before standards are set."
                ),
            },
        ],
        "timeline": [
            {
                "date": "2026-06-17",
                "milestone": "Legislature passes S10642/A11560",
                "detail": "First statewide data-center moratorium bill to clear a legislature",
            },
            {
                "date": "2026-07-14",
                "milestone": "EO 62 signed",
                "detail": "1-year DEC permit moratorium at ≥50 MW; DPS and DEC studies ordered",
            },
        ],
        "recent_news": [
            {
                "date": "2026-07-14",
                "title": "No. 62: Establishing a Temporary Moratorium on Data Centers in New York While the State Develops Standards",
                "source": "Office of the Governor of New York",
                "url": "https://www.governor.ny.gov/executive-order/no-62-establishing-temporary-moratorium-data-centers-new-york-while-state-develops",
                "takeaway": (
                    "Sets the 50 MW threshold and orders the DEC water-withdrawal "
                    "rulemaking assessment within 12 months."
                ),
            }
        ],
        "public_sentiment": (
            "Advocates who pushed S10642 read the 50 MW threshold and one-year clock as "
            "a dilution of the bill they passed; industry treats the executive route as "
            "the more workable outcome because it expires without further action."
        ),
    },
    {
        "bill_id": "NY DPS Data Center Impact Report (EO 62)",
        "instrument_type": "commission-docket",
        "jurisdiction": "New York",
        "level": "state",
        "title": "Department of Public Service data-center impact report",
        "sponsor": "NY Department of Public Service, on order of EO 62",
        "summary": (
            "The proceeding EO 62 orders: a DPS report on data-center impacts with water "
            "use and water quality expressly in scope, running alongside DEC's assessment "
            "of whether the water-withdrawal permitting program needs large-user rules."
        ),
        "scope": ["water", "energy"],
        "status": "introduced",
        "status_detail": (
            "Ordered 2026-07-14 with a 12-month deadline; no docket number published as "
            "of 2026-07-25. Re-verify the DPS case number once the proceeding opens."
        ),
        "source_url": "https://www.governor.ny.gov/executive-order/no-62-establishing-temporary-moratorium-data-centers-new-york-while-state-develops",
        "last_verified": "2026-07-25",
        "verified": False,
        "confidence": "medium",
        "implements": ["NY EO 62"],
        "general_principles": [
            {
                "tag": "Preemptive review",
                "note": "Studies water impacts during the pause rather than after buildout.",
            },
            {
                "tag": "Disclosure",
                "note": "The report is the mechanism that would make New York data-center water use public.",
            },
        ],
        "timeline": [
            {
                "date": "2026-07-14",
                "milestone": "Ordered",
                "detail": "EO 62 directs DPS to report on impacts including water use and quality",
            }
        ],
        "recent_news": [],
        "public_sentiment": (
            "Watched as the test of whether the moratorium produces enforceable water "
            "standards or expires with a report on a shelf."
        ),
    },
    {
        "bill_id": "VA DEQ waterworks data-center reporting regulations",
        "instrument_type": "agency-rule",
        "jurisdiction": "Virginia",
        "level": "state",
        "title": "Waterworks reporting regulations implementing HB 496 / SB 553",
        "sponsor": "Virginia Department of Environmental Quality",
        "summary": (
            "Requires waterworks operators to report monthly water sales categorized as "
            "data-center-with-air-permit, domestic, industrial-commercial, or other, each "
            "split potable vs non-potable. Individual facility figures remain "
            "trade-secret protected; the published data is aggregate."
        ),
        "scope": ["water"],
        "status": "enacted",
        "status_detail": (
            "Adopted mid-2026. First aggregate report due 2026-10-01; categorized monthly "
            "reporting begins 2027-01-01. This resolves the tracker's open question about "
            "HB 496's reporting channel: it runs through waterworks operators to DEQ, and "
            "what becomes public is aggregate, not facility-level — so the scraper target "
            "is the categorical report, not a per-data-center filing."
        ),
        "source_url": "https://www.whro.org/environment/2026-06-26/new-regulations-beef-up-data-centers-required-water-use-reporting-in-virginia",
        "last_verified": "2026-07-25",
        "verified": True,
        "confidence": "high",
        "implements": ["VA HB 496 / SB 553"],
        "general_principles": [
            {
                "tag": "Disclosure",
                "note": "Turns the statute's reporting mandate into a specific monthly filing with named categories.",
            },
            {
                "tag": "Transparency",
                "note": (
                    "Partial: category-level aggregates become public, but the "
                    "trade-secret shield keeps individual facilities out of the data."
                ),
            },
        ],
        "timeline": [
            {
                "date": "2026-06-26",
                "milestone": "Regulations reported adopted",
                "detail": "Categories and potable/non-potable split fixed",
            },
            {
                "date": "2026-10-01",
                "milestone": "First aggregate report due",
                "detail": "The first Tier-1 data this tracker can ingest under HB 496",
            },
            {
                "date": "2027-01-01",
                "milestone": "Categorized monthly reporting begins",
                "detail": "Ongoing monthly series starts",
            },
        ],
        "recent_news": [
            {
                "date": "2026-06-26",
                "title": "New regulations beef up data centers' required water use reporting in Virginia",
                "source": "WHRO",
                "url": "https://www.whro.org/environment/2026-06-26/new-regulations-beef-up-data-centers-required-water-use-reporting-in-virginia",
                "takeaway": (
                    "Sets the reporting categories and the October 2026 / January 2027 "
                    "effective dates, and confirms facility-level data stays shielded."
                ),
            }
        ],
        "public_sentiment": (
            "Transparency advocates call the aggregate-only publication the compromise "
            "that keeps the data too coarse to hold any single campus accountable."
        ),
    },
    {
        "bill_id": "QTS Richmond Technology Park DC5 (FAST-41)",
        "instrument_type": "agency-rule",
        "jurisdiction": "Virginia",
        "level": "federal",
        "title": "First data center designated a FAST-41 covered project",
        "sponsor": "Federal Permitting Improvement Steering Council; sponsor QTS Richmond V, LLC",
        "summary": (
            "The first data center ever granted FAST-41 coverage, putting its federal "
            "environmental review on a published, coordinated schedule with the Army "
            "Corps as lead agency. Covers two additional buildings at an existing "
            "four-building Henrico County campus."
        ),
        "scope": ["water"],
        "status": "enacted",
        "status_detail": (
            "Announced 2026-04-02. Environmental review and permitting scheduled to "
            "complete 2027-06-11; construction anticipated to begin by January 2028. "
            "In-state for this tracker, and the concrete first instance of EO 14318's "
            "FAST-41 expansion reaching a specific campus."
        ),
        "source_url": "https://www.permitting.gov/newsroom/press-releases/first-data-center-project-gains-permitting-councils-fast-41-coverage",
        "last_verified": "2026-07-25",
        "verified": True,
        "confidence": "high",
        "implements": ["US EO 14318"],
        "general_principles": [
            {
                "tag": "Permitting acceleration",
                "note": "The mechanism is schedule coordination and deadline pressure on the reviewing agencies.",
            },
            {
                "tag": "Transparency",
                "note": (
                    "Cuts the other way from the rest of the order: FAST-41 requires a "
                    "public permitting timetable, so this project's federal review is "
                    "more visible than an ordinary Corps permit, not less."
                ),
            },
        ],
        "timeline": [
            {
                "date": "2026-04-02",
                "milestone": "FAST-41 coverage granted",
                "detail": "First data center project ever covered; Army Corps is lead agency",
            },
            {
                "date": "2027-06-11",
                "milestone": "Target completion of review",
                "detail": "Published target date on the Permitting Dashboard",
            },
        ],
        "recent_news": [
            {
                "date": "2026-04-02",
                "title": "First Data Center Project Gains Permitting Council's FAST-41 Coverage",
                "source": "Federal Permitting Improvement Steering Council",
                "url": "https://www.permitting.gov/newsroom/press-releases/first-data-center-project-gains-permitting-councils-fast-41-coverage",
                "takeaway": "Names QTS Richmond Technology Park DC5 as the first covered data center.",
            }
        ],
        "public_sentiment": (
            "Local attention has focused on the campus's scale in Henrico County rather "
            "than on the federal designation itself."
        ),
    },
    {
        "bill_id": "MI SB 1046-1050",
        "instrument_type": "bill",
        "jurisdiction": "Michigan",
        "level": "state",
        "title": "Data center water permitting, NDA ban and community benefits package",
        "sponsor": "Michigan Senate (5-bill package)",
        "summary": (
            "SB 1046 would require a permit for water users at or above 550,000 gallons "
            "per day, cap consumptive use at 2 MGD, mandate at least three "
            "pre-application public hearings, require annual reporting from 2027 and "
            "allow permit revocation for reporting failures. SB 1049 would bar "
            "non-disclosure agreements where tax incentives were received. SB 1050 would "
            "require community benefit agreements covering water."
        ),
        "scope": ["water", "energy"],
        "status": "introduced",
        "status_detail": (
            "Introduced July 2026. Distinct from the tracked MI SB 762 and MI SB 1018-1020 "
            "— this package is the first to pair a hard consumptive-use cap with an NDA "
            "ban and a community-benefit mandate. Re-verify individual bill numbers "
            "against the Michigan Legislature bill lookup before treating any single "
            "number as settled."
        ),
        "source_url": "https://www.multistate.us/insider/2026/7/15/michigan-data-center-legislation-targets-energy-use-and-community-benefits",
        "last_verified": "2026-07-25",
        "verified": False,
        "confidence": "medium",
        "general_principles": [
            {
                "tag": "Permit oversight",
                "note": "A withdrawal permit at 550k gal/day with revocation as the enforcement lever.",
            },
            {
                "tag": "Conservation",
                "note": "The 2 MGD consumptive cap is a hard ceiling, not a reporting requirement.",
            },
            {
                "tag": "NDA prohibition",
                "note": "Ties the NDA ban to receipt of tax incentives rather than banning them outright.",
            },
            {
                "tag": "Disclosure",
                "note": "Annual reporting from 2027, enforceable by permit revocation.",
            },
        ],
        "timeline": [
            {
                "date": "2026-07-15",
                "milestone": "Package reported introduced",
                "detail": "Five bills covering water permitting, NDAs and community benefits",
            }
        ],
        "recent_news": [
            {
                "date": "2026-07-15",
                "title": "Michigan Data Center Legislation Targets Energy Use and Community Benefits",
                "source": "MultiState",
                "url": "https://www.multistate.us/insider/2026/7/15/michigan-data-center-legislation-targets-energy-use-and-community-benefits",
                "takeaway": "Summarizes the package's water-permitting, NDA and CBA provisions.",
            }
        ],
        "public_sentiment": (
            "Michigan's Great Lakes context makes consumptive-use caps unusually salient; "
            "the NDA provision responds directly to secrecy complaints around recent siting fights."
        ),
    },
    {
        "bill_id": "WV HB 4832",
        "instrument_type": "bill",
        "jurisdiction": "West Virginia",
        "level": "state",
        "title": "High-impact data center water use reporting and withdrawal limits",
        "sponsor": "Del. Hansen and eight co-sponsors",
        "summary": (
            "Would have designated data centers high-volume water users, required them to "
            "submit water quantity and quality impact analyses to DEP, mandated public "
            "notice and hearings before approval, and authorized DEP to prohibit or limit "
            "withdrawals where adverse impacts to a state water resource would occur."
        ),
        "scope": ["water"],
        "status": "failed",
        "status_detail": (
            "Introduced 2026-01-26 and referred to Energy and Public Works; did not "
            "advance before sine die. The contrast entry in this dataset: West Virginia "
            "enacted a data-center framework in the same session while these water "
            "protections were separately voted down as floor amendments to HB 2014. "
            "UNVERIFIED: the precise procedural death is inferred from session-end "
            "reporting — re-verify against the WV Legislature bill-status page."
        ),
        "source_url": "https://www.wvlegislature.gov/Bill_Text_HTML/2026_SESSIONS/RS/bills/hb4832%20intr.pdf",
        "last_verified": "2026-07-25",
        "verified": False,
        "confidence": "medium",
        "general_principles": [
            {
                "tag": "Permit oversight",
                "note": "Would have given DEP authority to refuse withdrawals on adverse-impact findings.",
            },
            {
                "tag": "Preemptive review",
                "note": "Impact analysis and public hearings required before approval, not after.",
            },
            {
                "tag": "Disclosure",
                "note": "Would have required disclosure of withdrawal volumes and expected regulated pollutants.",
            },
        ],
        "timeline": [
            {
                "date": "2026-01-26",
                "milestone": "Introduced",
                "detail": "Referred to the Committee on Energy and Public Works",
            },
            {
                "date": "2026-02-18",
                "milestone": "Water protections rejected separately",
                "detail": "WV House passed its data-center rules bill without local-control or water provisions",
            },
            {
                "date": "2026-03-14",
                "milestone": "Session adjourned sine die",
                "detail": "Bill did not advance",
            },
        ],
        "recent_news": [
            {
                "date": "2026-02-18",
                "title": "WV House passes new data center development rules without local control, water protection provisions",
                "source": "West Virginia Watch",
                "url": "https://westvirginiawatch.com/2026/02/18/wv-house-passes-new-data-center-development-rules-without-local-control-water-protection-provisions/",
                "takeaway": (
                    "Documents water protections being affirmatively stripped from the "
                    "enacted framework rather than simply omitted."
                ),
            }
        ],
        "public_sentiment": (
            "Conservation groups treat the session as the clearest example of a state "
            "choosing data-center recruitment over water safeguards explicitly on the record."
        ),
    },
    {
        "bill_id": "TX PUC Energy and Water Use Survey (data centers)",
        "instrument_type": "commission-docket",
        "jurisdiction": "Texas",
        "level": "state",
        "title": "PUCT / TWDB energy and water use survey for data centers and crypto mining",
        "sponsor": "Public Utility Commission of Texas with the Texas Water Development Board",
        "summary": (
            "A survey directed by the Legislature in the 2025 budget, collecting "
            "electricity and water use from data centers and virtual-currency mining "
            "facilities. The only water-specific utility-commission action found "
            "nationally — the marquee data-center rate dockets elsewhere (PUCO 24-508-EL-ATA, "
            "the Georgia PSC large-load tariff, Dominion's SCC proceedings) are energy-only "
            "and carry no water provisions."
        ),
        "scope": ["water", "energy"],
        "status": "introduced",
        "status_detail": (
            "Open and voluntary, with response rates the Legislature has called "
            "inadequate: about a third of surveyed data centers responded in 2024 and "
            "17% in 2025; the most recent round drew 28 companies covering 92 facilities. "
            "PUCT reopened the survey 2026-07-01 with responses due 2026-07-10. The "
            "Texas Water Development Board's own water-consumption surveys have been "
            "mandatory since 2023. Watch for a mandatory PUCT/ERCOT registration "
            "requirement replacing the voluntary survey."
        ),
        "source_url": "https://www.puc.texas.gov/industry/water/utilities/energy-and-water-use-survey/faq/",
        "last_verified": "2026-07-25",
        "verified": True,
        "confidence": "high",
        "general_principles": [
            {
                "tag": "Disclosure",
                "note": "Asks for facility-level water use directly from operators rather than through utilities.",
            },
            {
                "tag": "Transparency",
                "note": (
                    "The instructive failure in this dataset: a disclosure mechanism with "
                    "no compulsion produced a 17% response rate."
                ),
            },
        ],
        "timeline": [
            {
                "date": "2025-06-01",
                "milestone": "Directed by the Legislature",
                "detail": "2025 budget directs PUCT and TWDB to collect data-center energy and water use",
            },
            {
                "date": "2026-06-23",
                "milestone": "Low response rate reported",
                "detail": "28 companies covering 92 facilities responded; lawmakers demand answers",
            },
            {
                "date": "2026-07-01",
                "milestone": "Survey reopened",
                "detail": "Responses due 2026-07-10",
            },
        ],
        "recent_news": [
            {
                "date": "2026-06-23",
                "title": "Most data centers ignore Texas surveys about their water use",
                "source": "The Texas Tribune",
                "url": "https://www.texastribune.org/2026/06/23/texas-data-centers-puc-water-survey/",
                "takeaway": "Documents the response rates and the legislative reaction.",
            },
            {
                "date": "2026-06-26",
                "title": "Texas asked data centers to report water use. Most didn't respond",
                "source": "KUT",
                "url": "https://www.kut.org/energy-environment/2026-06-26/texas-data-center-water-use-survey-legislature",
                "takeaway": "Confirms the voluntary design and the reopening of the survey window.",
            },
        ],
        "public_sentiment": (
            "Cited on both sides of the mandatory-reporting debate: as proof that "
            "voluntary disclosure does not work, and by industry as evidence the "
            "questions are burdensome."
        ),
    },
    {
        "bill_id": "Prince George's County MD CB-2026 data center moratorium",
        "instrument_type": "local-ordinance",
        "jurisdiction": "Prince George's County, Maryland",
        "level": "local",
        "title": "Two-year moratorium on hyperscale data center development",
        "sponsor": "Prince George's County Council",
        "summary": (
            "A two-year pause on hyperscale data-center development — the longest in "
            "Maryland — adopted with unanswered questions about the facilities' effect "
            "on county water among the stated reasons."
        ),
        "scope": ["water", "energy"],
        "status": "enacted",
        "status_detail": (
            "Adopted 2026-07-07. Part of a Maryland cluster: Montgomery, Frederick and "
            "Baltimore counties have also paused data-center development."
        ),
        "source_url": "https://marylandmatters.org/2026/07/08/prince-georges-county-extends-pause-on-hyperscale-data-center-development/",
        "last_verified": "2026-07-25",
        "verified": True,
        "confidence": "high",
        "general_principles": [
            {"tag": "Moratorium", "note": "Two years, the longest local pause in Maryland."},
            {
                "tag": "Preemptive review",
                "note": "Explicitly framed as buying time to answer water and infrastructure questions.",
            },
        ],
        "timeline": [
            {
                "date": "2026-07-07",
                "milestone": "Adopted",
                "detail": "Council votes a two-year moratorium on hyperscale data centers",
            }
        ],
        "recent_news": [
            {
                "date": "2026-07-08",
                "title": "Prince George's County extends pause on hyperscale data centers",
                "source": "Maryland Matters",
                "url": "https://marylandmatters.org/2026/07/08/prince-georges-county-extends-pause-on-hyperscale-data-center-development/",
                "takeaway": "Council member Blegay cites unresolved questions about county water among the reasons.",
            }
        ],
        "public_sentiment": (
            "Organized resident opposition preceded the vote, with protests at the council "
            "as it considered the measure."
        ),
    },
    {
        "bill_id": "Washington County MD data center moratorium",
        "instrument_type": "local-ordinance",
        "jurisdiction": "Washington County, Maryland",
        "level": "local",
        "title": "One-year moratorium on data center development",
        "sponsor": "Washington County Board of Commissioners",
        "summary": (
            "A one-year pause on data-center development in western Maryland, with farm "
            "wells and drought conditions among the stated rationales."
        ),
        "scope": ["water"],
        "status": "enacted",
        "status_detail": "Approved 2026-07-01.",
        "source_url": "https://thedailyrecord.com/2026/07/01/washington-county-approves-yearlong-data-center-moratorium/",
        "last_verified": "2026-07-25",
        "verified": True,
        "confidence": "medium",
        "general_principles": [
            {"tag": "Moratorium", "note": "One-year pause pending study."},
            {
                "tag": "Conservation",
                "note": "Agricultural well drawdown and drought are the water rationale, not discharge.",
            },
        ],
        "timeline": [
            {
                "date": "2026-07-01",
                "milestone": "Approved",
                "detail": "Yearlong moratorium adopted",
            }
        ],
        "recent_news": [
            {
                "date": "2026-07-01",
                "title": "Western MD county approves data center moratorium",
                "source": "Maryland Daily Record",
                "url": "https://thedailyrecord.com/2026/07/01/washington-county-approves-yearlong-data-center-moratorium/",
                "takeaway": "Confirms the one-year term and adoption date.",
            }
        ],
        "public_sentiment": (
            "Rural and agricultural water users have been the most visible constituency, "
            "a different coalition from the suburban ratepayer opposition elsewhere in Maryland."
        ),
    },
    {
        "bill_id": "Santa Fe County NM data center moratorium",
        "instrument_type": "local-ordinance",
        "jurisdiction": "Santa Fe County, New Mexico",
        "level": "local",
        "title": "18-month moratorium on data center development",
        "sponsor": "Santa Fe County Board of County Commissioners",
        "summary": (
            "An 18-month pause adopted unanimously, extended from the 12 months "
            "originally proposed, with the regulatory threshold lowered from 100 MW to "
            "1 MW — by far the lowest trigger of any tracked moratorium."
        ),
        "scope": ["water", "energy"],
        "status": "enacted",
        "status_detail": (
            "Adopted 2026-07-02. The 1 MW threshold means it reaches essentially any "
            "data center, not just hyperscale ones — a materially different instrument "
            "from the 20-50 MW state thresholds."
        ),
        "source_url": "https://www.santafecountynm.gov/news/detail/santa-fe-county-approves-18-month-moratorium-on-data-centers",
        "last_verified": "2026-07-25",
        "verified": True,
        "confidence": "high",
        "general_principles": [
            {"tag": "Moratorium", "note": "18 months at a 1 MW threshold — the broadest local pause tracked."},
            {
                "tag": "Preemptive review",
                "note": "Adopted before any project application rather than in response to one.",
            },
        ],
        "timeline": [
            {
                "date": "2026-07-02",
                "milestone": "Adopted unanimously",
                "detail": "Term extended to 18 months and threshold lowered to 1 MW during deliberation",
            }
        ],
        "recent_news": [
            {
                "date": "2026-07-02",
                "title": "Santa Fe County approves 18-month moratorium on data centers",
                "source": "Santa Fe County",
                "url": "https://www.santafecountynm.gov/news/detail/santa-fe-county-approves-18-month-moratorium-on-data-centers",
                "takeaway": "Confirms the unanimous vote, the 18-month term and the 1 MW threshold.",
            }
        ],
        "public_sentiment": (
            "Arid-region water scarcity and acequia water rights shape the debate here in "
            "a way they do not in the eastern moratoria."
        ),
    },
    {
        "bill_id": "York County SC data center moratorium",
        "instrument_type": "local-ordinance",
        "jurisdiction": "York County, South Carolina",
        "level": "local",
        "title": "Nine-month moratorium on data center development",
        "sponsor": "York County Council",
        "summary": (
            "A nine-month pause in unincorporated York County directing staff to examine "
            "groundwater, noise, utility rates, energy infrastructure, waste heat and "
            "impacts on neighbouring properties, and to recommend whether independent "
            "experts should be retained."
        ),
        "scope": ["water", "energy"],
        "status": "enacted",
        "status_detail": (
            "Passed third reading and took effect 2026-07-13, expiring April 2027. "
            "Applies only to unincorporated areas and does not halt already-permitted "
            "construction at the QTS project near Lake Wylie, though it blocks new "
            "unpermitted structures there. Part of a wider South Carolina county wave."
        ),
        "source_url": "https://www.wrhi.com/2026/07/york-county-council-approves-nine-month-data-center-moratorium-214184",
        "last_verified": "2026-07-25",
        "verified": True,
        "confidence": "high",
        "general_principles": [
            {"tag": "Moratorium", "note": "Nine months, unincorporated areas only."},
            {
                "tag": "Preemptive review",
                "note": "Names groundwater and waste heat as specific study subjects, not general 'impacts'.",
            },
        ],
        "timeline": [
            {
                "date": "2026-06-17",
                "milestone": "First reading",
                "detail": "Council takes up a nine-month moratorium",
            },
            {
                "date": "2026-07-13",
                "milestone": "Adopted on third reading",
                "detail": "Effective immediately; expires April 2027",
            },
        ],
        "recent_news": [
            {
                "date": "2026-07-13",
                "title": "York County Council approves nine month data center moratorium",
                "source": "WRHI",
                "url": "https://www.wrhi.com/2026/07/york-county-council-approves-nine-month-data-center-moratorium-214184",
                "takeaway": "Confirms adoption, the study scope including groundwater and waste heat, and the carve-out for permitted QTS work.",
            },
            {
                "date": "2026-06-26",
                "title": "SC counties enacting data center moratoriums",
                "source": "SC Daily Gazette",
                "url": "https://scdailygazette.com/2026/06/26/sc-counties-enacting-data-center-moratoriums/",
                "takeaway": "Places York County in a wider South Carolina county-level wave.",
            },
        ],
        "public_sentiment": (
            "Scrutiny intensified around the existing QTS construction, which the "
            "moratorium deliberately does not stop — a limit opponents have noted."
        ),
    },
]

# bill_id -> {field: new value} for entries whose status moved, or whose record
# was wrong. CA AB 93 was surfaced by the new source_url schema test: it was the
# only entry in the dataset with no source at all, and re-verifying it also
# corrected the veto year (2025, not 2024) and filled in the author.
STATUS_UPDATES = {
    "CA AB 93": {
        "sponsor": "Assemblymember Diane Papan (D–San Mateo)",
        "status_detail": (
            "Vetoed by Gov. Newsom on 2025-10-11, who cited an incomplete "
            "understanding of the impact on businesses and consumers. Would have "
            "required data centers to report expected water use to their supplier "
            "before applying for a business license, certify that disclosure at "
            "application, and certify actual annual use at renewal. (Corrected "
            "2026-07-25: the record previously dated the veto to October 2024.)"
        ),
        "summary": (
            "Would have required data centers to disclose projected water use to "
            "their water supplier at business-license application and certify "
            "actual annual water use at license renewal."
        ),
        "source_url": "https://calmatters.digitaldemocracy.org/bills/ca_202520260ab93",
        "last_verified": "2026-07-25",
    },
    "NY S10642 / A11560": {
        "status_detail": (
            "Passed both chambers June 2026 — the first statewide data-center moratorium "
            "bill to clear a legislature. Gov. Hochul neither signed nor vetoed it; on "
            "2026-07-14 she superseded it with Executive Order 62, which imposes a "
            "one-year DEC permit moratorium at a 50 MW threshold rather than the bill's "
            "20 MW. Track NY EO 62 for the operative instrument; an eventual veto of this "
            "bill is the expected outcome."
        ),
        "last_verified": "2026-07-25",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from refdata.taxonomies import (
        INSTRUMENT_TYPE_LABELS,
        LEGISLATION_PRINCIPLE_DESCRIPTIONS,
        LEGISLATION_STATUS_LABELS,
    )

    payload = json.loads(LEGISLATION_PATH.read_text(encoding="utf-8"))
    existing = {e["bill_id"] for e in payload["bills"]}

    added, skipped, problems = [], [], []
    for entry in NEW_ENTRIES:
        if entry["bill_id"] in existing:
            skipped.append(entry["bill_id"])
            continue
        if entry["instrument_type"] not in INSTRUMENT_TYPE_LABELS:
            problems.append(f"{entry['bill_id']}: bad instrument_type {entry['instrument_type']}")
        if entry["status"] not in LEGISLATION_STATUS_LABELS:
            problems.append(f"{entry['bill_id']}: bad status {entry['status']}")
        for principle in entry.get("general_principles", []):
            if principle["tag"] not in LEGISLATION_PRINCIPLE_DESCRIPTIONS:
                problems.append(f"{entry['bill_id']}: unknown principle {principle['tag']}")
        payload["bills"].append(entry)
        added.append(entry["bill_id"])

    updated = []
    by_id = {e["bill_id"]: e for e in payload["bills"]}
    for bill_id, fields in STATUS_UPDATES.items():
        target = by_id.get(bill_id)
        if target is None:
            problems.append(f"STATUS_UPDATES names an absent entry: {bill_id}")
            continue
        if any(target.get(k) != v for k, v in fields.items()):
            target.update(fields)
            updated.append(bill_id)

    print(f"added:   {len(added)}")
    for b in added:
        print(f"  + {b}")
    print(f"updated: {len(updated)}  {updated}")
    print(f"skipped (already present): {len(skipped)}  {skipped}")
    print(f"total entries: {len(payload['bills'])}")

    if problems:
        print("\nAborted:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    if args.dry_run:
        print("\n(dry run — nothing written)")
        return 0

    payload["last_updated"] = "2026-07-25"
    LEGISLATION_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("\nWrote legislation.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
