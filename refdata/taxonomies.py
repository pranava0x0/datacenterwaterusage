"""Closed taxonomies and the palette they colour themselves with.

Extracted from ``dashboard.py`` (2026-07-25) so the Streamlit app, the static
site generator, the migration scripts, and the schema tests all read one
definition. ``dashboard.py`` re-exports every name here, so existing
``dashboard.CWA_CASE_TYPE_LABELS``-style references keep working.

**The closed-taxonomy rule** (CLAUDE.md / plan §0.6-3): adding a *record* is a
data-only change; adding a *value* to any dict below is a code change that must
ship in the same commit as (a) its one-line description/label and (b) the
schema test that enforces membership. That is what keeps a typo in a JSON file
from silently dropping a record out of the filters.

Purity rule: no ``streamlit`` import, ever.
"""

from __future__ import annotations

# --- Palette -----------------------------------------------------------------

COLORS = {
    "primary": "#08519c",
    "secondary": "#3182bd",
    "tertiary": "#6baed6",
    "light": "#bdd7e7",
    "bg": "#eff3ff",
    "danger": "#c41e3a",
    "warning": "#d4a017",
    "success": "#2e8b57",
    "text": "#1a1a2e",
}

COLOR_SEQUENCE = ["#08519c", "#3182bd", "#6baed6", "#9ecae1", "#c6dbef"]


# --- Policy instruments (legislation.json) -----------------------------------

LEGISLATION_STATUS_ORDER = {"enacted": 0, "introduced": 1, "failed": 2, "unknown": 3}
LEGISLATION_STATUS_LABELS = {
    "enacted": "Enacted",
    "introduced": "Introduced",
    "failed": "Failed / Vetoed",
    "unknown": "Unknown",
}
LEGISLATION_STATUS_BADGE_COLORS = {
    "enacted": COLORS["success"],
    "introduced": COLORS["primary"],
    "failed": COLORS["danger"],
    "unknown": COLORS["secondary"],
}

LEGISLATION_LEVEL_LABELS = {
    "federal": "Federal",
    "state": "State",
    "local": "Local",
}
LEGISLATION_SCOPE_LABELS = {
    "water": "Water",
    "energy": "Energy",
}

# Canonical principle taxonomy — every general_principles tag in the dataset
# must be one of these (a test enforces it, same pattern as the case_type
# vocabulary). The one-liners power the cross-bill summary panel.
LEGISLATION_PRINCIPLE_DESCRIPTIONS = {
    "Transparency": "Make data-center water/energy use publicly visible instead of proprietary.",
    "Disclosure": "Require operators or utilities to file specific consumption reports.",
    "Cost allocation": "Make data centers pay the infrastructure and rate costs they cause.",
    "Permit oversight": "Give regulators or localities approval leverage over siting and use.",
    "Conservation": "Mandate or incentivize lower water/energy consumption outright.",
    "Federal coordination": "Standardize metrics and oversight across states at the federal level.",
    "Preemptive review": "Force evaluation of impacts before construction, not after.",
    "Anti-corporate-welfare": "Condition or repeal subsidies and tax exemptions.",
    "Best-practice guidance": "Codify model standards and guidance rather than hard mandates.",
    "NDA prohibition": "Ban the non-disclosure agreements that hide water deals from the public.",
    "Closed-loop cooling": "Require sealed cooling systems with minimal net water draw.",
    "Strict liability": "Attach direct, non-waivable liability for violations or harms.",
    "Moratorium": "Pause new data-center development until safeguards exist.",
    # Added with the federal executive layer (2026-07-25). Every principle
    # above conditions or slows data-center water use; nothing captured a
    # government speeding water permitting *up*, which is what the 2025-26
    # federal executive actions do.
    "Permitting acceleration": "Speed water permitting up for data centers, not slow it down.",
}

# What KIND of government lever a record is. `legislation.json` has quietly
# held non-bills since 2026 (the Ohio EPA draft general permit, the Loudoun
# ZOAM, Utah EO 2026-03); this names that instead of implying everything is a
# bill. The key stays `bill_id` — a stable id whose display semantics widened.
INSTRUMENT_TYPE_LABELS = {
    "bill": "Bill",
    "executive-order": "Executive order",
    "agency-rule": "Agency rule",
    "commission-docket": "Commission docket",
    "local-ordinance": "Local ordinance",
}

# Outline-chip colours for the instrument chip. Executive orders reuse the
# purple already reserved in DESIGN.md for "regulatory / upcoming"; nothing new
# enters the palette.
INSTRUMENT_TYPE_COLORS = {
    "bill": COLORS["primary"],
    "executive-order": "#7c3aed",
    "agency-rule": "#b45309",
    "commission-docket": "#1a7a8a",
    "local-ordinance": "#475569",
}


# --- News (water_news.json) --------------------------------------------------

NEWS_TAG_LABELS = {
    "regulation": "Regulation",
    "enforcement": "Enforcement",
    "solutions": "Solutions",
    "research": "Research",
    "data": "Data & Reports",
    "policy": "Policy",
}
NEWS_TAG_COLORS = {
    "regulation": "#08519c",
    "enforcement": "#c41e3a",
    "solutions": "#2e8b57",
    "research": "#6b3fa0",
    "data": "#1a7a8a",
    "policy": "#d4a017",
}


# --- Solutions (water_solutions.json) ----------------------------------------

SOLUTION_STATUS_LABELS = {
    "deployed": "Deployed",
    "pilot": "Pilot / In Progress",
    "proposed": "Proposed",
}
SOLUTION_STATUS_COLORS = {
    "deployed": ("#2e8b57", "#eaf7ef", "#b7e4c7"),
    "pilot": ("#9a6700", "#fff7e6", "#f3d99b"),
    "proposed": ("#08519c", "#eef6ff", "#bcd9f5"),
}
SOLUTION_ACTOR_LABELS = {
    "state": "State",
    "federal": "Federal",
    "utility": "Utility",
    "industry": "Industry",
}


# --- Cases (cwa_investigations.json) -----------------------------------------

CWA_CATEGORY_ORDER = {
    "datacenter": 0,
    "adjacent": 1,
    "industrial": 2,
    "precedent": 3,
}
CWA_CATEGORY_LABELS = {
    "datacenter": "Data Center",
    "adjacent": "Data-Center Adjacent",
    "industrial": "Industrial Water",
    "precedent": "Landmark Precedent",
}

# Project-type ("what kind of water issue is this?") taxonomy — the primary
# filter axis. Every case carries exactly one case_type from this dict; a
# schema test enforces it so a typo in the JSON can't silently drop a case
# from the filters.
CWA_CASE_TYPE_LABELS = {
    "construction-stormwater": "Construction stormwater",
    "wetlands-streams": "Wetlands & streams (§404/§401)",
    "cooling-water": "Cooling water & thermal (§316)",
    "industrial-discharge": "Industrial discharge (§402)",
    "pretreatment": "Sewer pretreatment (§307)",
    "potw-sewer": "Treatment plants & sewers (POTW)",
    "groundwater": "Groundwater & aquifers",
    "spills-contamination": "Spills, PFAS & contamination",
    "water-supply": "Water supply & drinking water",
    "legal-doctrine": "Citizen suits & court doctrine",
    # Added with the AWS claims suit (2026-07-26): consumer-protection theories
    # attacking an operator's published water figures. No existing type fits —
    # the defendant's own statements are the alleged violation.
    "greenwashing-litigation": "Greenwashing & claims litigation",
}

# Did the Clean Water Act actually get used in this case? ("not-applied" also
# covers cases that ran under a different water authority — the statute pills
# derived from `authorities` say which one.)
CWA_STATUS_LABELS = {
    "applied": "CWA applied",
    "pending": "CWA potential",
    "not-applied": "No CWA action",
}
CWA_STATUS_COLORS = {
    "applied": COLORS["success"],
    "pending": "#b45309",  # amber — between applied and not-applied
    "not-applied": "#6b7280",  # neutral gray — explicitly not a failure state
}


# --- Legal authorities (water_authorities.json) ------------------------------

# What kind of law a family is. Federal statutes read differently from state
# doctrines (no agency, no permit, litigated in state court) and the accordion
# summary row shows this so users know which register they are in.
AUTHORITY_KIND_LABELS = {
    "federal-statute": "federal statute",
    "federal-doctrine": "federal doctrine",
    "state-doctrine": "state doctrine",
    "common-law": "common law",
    "interstate": "interstate / compact",
    "constitutional": "constitutional",
}

# Display order for authority families. Every family listed here must have at
# least one reading AND at least one case in the corpus — a schema test
# enforces both, which is why families are added here in the same commit as
# their data (the doctrine families of plan Spec C1 arrive in P2), never ahead
# of it.
# Federal statutes first, then the doctrine families in rough legal-hierarchy
# order (interstate/constitutional → public trust → property).
WATER_STATUTE_ORDER = [
    "CWA",
    "SDWA",
    "TSCA",
    "RCRA",
    "RHA",
    "EQAP",
    "PTD",
    "GW",
    "WELL",
    "GWMGMT",
    "XFER",
    "ESA",
    "TRIBAL",
    "SEPA",
    "CL",
    "UTIL",
    "SL",
]

# Family pill colours. Colour carries *family identity* here — a lookup aid,
# like a map legend — not status, so the decorative-colour rule is satisfied.
WATER_STATUTE_COLORS = {
    "CWA": "#08519c",
    "SDWA": "#2e8b57",
    "TSCA": "#7c3aed",
    "RCRA": "#b45309",
    "RHA": "#475569",
    "EQAP": "#1a4f8a",
    "PTD": "#1a7a8a",
    "GW": "#8a6d1f",
    "WELL": "#3182bd",
    "GWMGMT": "#6b7f2a",
    "XFER": "#9a6700",
    "ESA": "#2f7a4f",
    "TRIBAL": "#8a4f2a",
    "SEPA": "#5b6b8a",
    "CL": "#6b7280",
    "UTIL": "#6b3fa0",
    "SL": "#c41e3a",
}


# --- Conflict sites (dc_water_conflicts.json) --------------------------------

# What KIND of water problem a site represents. 1–3 per site. Answers "show me
# all the aquifer fights" — impossible against the prose summaries alone — and
# gives legislation principles, solutions and doctrine readings a join key for
# "which problem does this address?".
ISSUE_TYPE_LABELS = {
    "aquifer-depletion": "Aquifer depletion",
    "supply-strain": "Municipal supply strain",
    "supply-secrecy": "Secrecy & FOIA fights",
    "supply-contract-dispute": "Water-contract dispute",
    "rate-cost-shift": "Rate & cost shifting",
    "discharge-quality": "Discharge quality",
    "construction-impacts": "Construction impacts",
    "moratorium-pause": "Moratorium / pause",
    "siting-zoning-defeat": "Siting & zoning defeat",
    "disclosure-gap": "Disclosure gap",
    "alt-source-adoption": "Alternative-source adoption",
    "pretreatment-potw": "Pretreatment / POTW contamination",
}

ISSUE_TYPE_DESCRIPTIONS = {
    "aquifer-depletion": "Groundwater drawdown beyond sustainable yield; neighbouring wells failing.",
    "supply-strain": "Municipal or utility capacity strained, competing with residents and agriculture in drought.",
    "supply-secrecy": "NDAs, redacted agreements and contested FOIA requests hiding water figures.",
    "supply-contract-dispute": "Fights over the terms of a utility↔data-center water-sale agreement.",
    "rate-cost-shift": "Water and sewer infrastructure costs socialized onto other ratepayers.",
    "discharge-quality": "Direct discharge under a permit — cooling blowdown, thermal load, nitrate.",
    "construction-impacts": "Wetland and stream fill, frac-outs, sediment — harm from building, not operating.",
    "moratorium-pause": "A government halting new development pending study, at any level.",
    "siting-zoning-defeat": "Rezoning losses, siting rejections and the process fights around them.",
    "disclosure-gap": "Absent or non-standard facility-level reporting of actual water use.",
    "alt-source-adoption": "Shifts to greywater, reclaimed water or air cooling — the solutions edge of a conflict.",
    "pretreatment-potw": "Contamination introduced into a municipal sewer or reclaimed-water system.",
}


# --- Operator claims (company_water_claims.json) -----------------------------

DELIVERED_STATUS_COLORS = {
    "delivered": "success",
    "partial": "warning",
    "contested": "warning",
    "shortfall": "danger",
    # Added with the AWS claims suit (2026-07-26). Distinct from "contested",
    # where independent assessors merely disagree: here a case_id, a forum and
    # a decision date exist. The label records that the claim is being tested,
    # not that it is false.
    "litigated": "danger",
}

# Display labels for delivered.status. Both surfaces read this; the Streamlit
# card previously carried its own literal copy, which silently lacked
# "litigated" and fell back to a generic Unknown/info treatment.
DELIVERED_STATUS_LABELS = {
    "delivered": "Delivered",
    "partial": "Partial",
    "contested": "Contested",
    "litigated": "Contested in court",
    "shortfall": "Shortfall",
}

# What kind of promise the claim is. Drives the claim-type chip and lets the
# Claims section separate a 2030 pledge from a measured WUE figure.
CLAIM_TYPE_LABELS = {
    "water-positive-pledge": "Water-positive pledge",
    "efficiency-wue": "Efficiency / WUE",
    "replenishment-milestone": "Replenishment milestone",
    "site-specific-promise": "Site-specific promise",
    "zero-water-design": "Zero-water design",
    "disclosure-transparency": "Disclosure & transparency",
}


# --- Case outcomes -----------------------------------------------------------

# Promoted from docs/cwa-outcome-taxonomy.md into enforced data (plan Spec C3).
# A case may carry several — a consent decree that also imposed a penalty.
OUTCOME_TYPE_LABELS = {
    "monetary-penalty": "Monetary penalty",
    "consent-decree": "Consent decree",
    "injunction-stop-work": "Injunction / stop-work",
    "permit-issued": "Permit issued",
    "permit-denied": "Permit denied or withdrawn",
    "permit-conditioned": "Permit conditioned",
    "jurisdiction-narrowed": "Jurisdiction narrowed",
    "jurisdiction-affirmed": "Jurisdiction affirmed",
    "compliance-order": "Compliance / emergency order",
    "dismissed-no-liability": "Dismissed / no liability",
    "settled-nonmonetary": "Settled, non-monetary",
    "pending-undecided": "Pending / undecided",
}
