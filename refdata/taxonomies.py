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


# --- US states ---------------------------------------------------------------

# The `state` field of local_actions.json is validated against these keys, and
# the States & Localities rollup uses the names to join a county/city action
# ("TX") to a state instrument whose jurisdiction is spelled out ("Texas").
# Fifty states plus DC; territories arrive with their first record.
US_STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana",
    "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}


# --- County & city actions (local_actions.json) ------------------------------

# What KIND of measure a county or city passed. Only the three values the
# mirrored table actually uses ship here: Spec D also names `zoning-amendment`
# and `permit-denial`, but a taxonomy value with no records renders a filter
# chip that matches nothing, so those two arrive with their first record and
# a schema test fails loudly on a value that is not listed yet.
LOCAL_ACTION_TYPE_LABELS = {
    "moratorium": "Moratorium / pause",
    "ordinance": "Permanent ordinance",
    "resolution": "Resolution",
}

# Where the measure stands. `superseded` is the one that needs saying out
# loud: a pause replaced by permanent zoning and a pause rescinded under a
# developer lawsuit both land here, and neither is "expired".
LOCAL_ACTION_STATUS_LABELS = {
    "active": "In force",
    "proposed": "Proposed",
    "expired": "Expired",
    "superseded": "Superseded",
    "rejected": "Rejected",
}

# Reuses the semantic status colours of DESIGN.md §8 — nothing new enters the
# palette. In force reads as the enacted green, proposed as the introduced
# blue, rejected as the failed red; expired and superseded are outcomes that
# are neither wins nor losses, so they take the amber and neutral greys.
LOCAL_ACTION_STATUS_COLORS = {
    "active": COLORS["success"],
    "proposed": COLORS["primary"],
    "expired": "#b45309",
    "superseded": "#6b7280",
    "rejected": COLORS["danger"],
}

# Display order for the rollup counts and the filter row: in force first,
# then what is still moving, then the three ways a measure stops mattering.
LOCAL_ACTION_STATUS_ORDER = {
    "active": 0,
    "proposed": 1,
    "superseded": 2,
    "expired": 3,
    "rejected": 4,
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
# The 2026-08-24 federal batch sits between RHA and EQAP: the discharge
# statutes, then the supply-side ones (review → liability → storage →
# designation → licensing → contract → reporting). BASIN follows EQAP because
# both are interstate.
WATER_STATUTE_ORDER = [
    "CWA",
    "SDWA",
    "TSCA",
    "RCRA",
    "RHA",
    "NEPA",
    "CERCLA",
    "WSA",
    "WSR",
    "FPA",
    "RECL",
    "EPCRA",
    "EQAP",
    "BASIN",
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
    # 2026-08-24 federal batch. The blue/green/earth bands were already
    # crowded, so these sit in the indigo→magenta arc the palette had left
    # open; each clears ΔE≈25 from every other family pill and 5:1 contrast
    # against the white pill text. No turquoise/aqua/teal (DESIGN.md §12).
    "NEPA": "#242bb2",
    "CERCLA": "#7f1a24",
    "WSA": "#5a532b",
    "WSR": "#1a7f1a",
    "FPA": "#553267",
    "RECL": "#9624b2",
    "EPCRA": "#b2248e",
    "EQAP": "#1a4f8a",
    "BASIN": "#79204d",
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


# --- Data-center activities (water_authorities.json readings) ----------------

# What a data center is DOING when a reading reaches it. The toolkit is
# organized by statute — the lawyer's axis — but a resident, a local official
# or an operator arrives with "the campus is about to do X; which laws touch
# that?". Every reading carries 1-3 of these in ``dc_activities``; the "How
# statutes apply" paths and the Explore activity hubs are both derived from
# that one field, so the two can never disagree about what triggers a law.
#
# The split between ``withdraw`` and ``supply`` is the self-supplied vs.
# utility-supplied fork every conflict site in this dataset sits on one side
# of: a campus with its own wells answers to groundwater doctrine directly; a
# campus on city water reaches it only through the utility's entitlements.
# Keys are in path order (build → water in → water out → site risk → power →
# public record) — the order the view presents them in.
DC_ACTIVITY_LABELS = {
    "build": "Building the campus",
    "withdraw": "Pumping or diverting water",
    "supply": "Buying water from a utility",
    "discharge": "Discharging cooling water",
    "chemicals": "Storing fuel & chemicals",
    "power": "Powering the campus",
    "disclose": "Claims & disclosures",
}
DC_ACTIVITY_DESCRIPTIONS = {
    "build": (
        "Grading, wetland and stream crossings, construction runoff, structures "
        "in navigable water, and the federal permits or financing that trigger "
        "environmental review."
    ),
    "withdraw": (
        "On-site wells and surface intakes — and the water rights, compacts and "
        "doctrines that decide who may take how much, and who can object."
    ),
    "supply": (
        "Service from a public water system: capacity, drinking-water "
        "compliance, reservoir storage and the entitlements behind the tap."
    ),
    "discharge": (
        "Cooling-tower blowdown and wastewater sent to a sewer, a stream or the "
        "ground, plus heat and stormwater from an operating campus."
    ),
    "chemicals": (
        "Backup-generator diesel, cooling-treatment biocides, PFAS in coolants "
        "and fire suppression, and legacy contamination on or under the site."
    ),
    "power": (
        "Generation built or restarted to serve the load — power-plant cooling, "
        "hydropower licences and the federal approvals behind a restart."
    ),
    "disclose": (
        "What an operator publishes or must file — water pledges, efficiency "
        "figures and chemical inventories — and when a claim becomes a liability."
    ),
}

# Whether a reading opens a door or marks where one closes. Most readings are
# hooks; a handful exist to say where a theory fails (the ESA take limit, the
# standing trap, dormant-Commerce-Clause limits on keeping water in-state).
# ``dc_role`` is omitted on hooks — only "limit" is ever written — and the
# paths view flags limits so a reader does not mistake a dead end for a route.
DC_ROLE_LABELS = {
    "hook": "Hook",
    "limit": "Limit",
}


# --- Water commitments (water_commitments.json) ------------------------------

# What a commitment actually obliges, one value per term. Typed so the view
# can say "three local agreements cap water use" instead of paraphrasing
# eleven documents, and closed so a new kind of promise is a decision.
COMMITMENT_TERM_LABELS = {
    "disclosure": "Disclosure & reporting",
    "efficiency": "Efficiency target",
    "reclaimed-source": "Reclaimed or non-potable water",
    "closed-loop": "Closed-loop or dry cooling",
    "use-cap": "Water-use cap",
    "infrastructure-funding": "Developer-funded water infrastructure",
    "restoration": "Restoration & replenishment",
    "permit-condition": "Approval condition",
    "study": "Study or assessment",
}

# Where the commitment sits. State commitments are not a level here — they
# are derived from legislation.json, which already holds every state order.
COMMITMENT_LEVEL_LABELS = {
    "federal": "U.S. federal",
    "international": "Other countries",
    "local": "Local agreements",
}

# How hard the promise is. A reader comparing a Singapore target to a county
# memorandum needs this before anything else.
COMMITMENT_BINDING_LABELS = {
    "binding": "Binding",
    "reporting": "Reporting duty",
    "voluntary": "Voluntary",
    "strategy": "Strategy",
    "study": "Study only",
}

COMMITMENT_STATUS_LABELS = {
    "in-force": "In force",
    "rejected": "Rejected",
}
COMMITMENT_STATUS_COLORS = {
    "in-force": COLORS["success"],
    "rejected": COLORS["danger"],
}

# How the state-commitments matrix reads legislation.json. Each column is a
# plain-language commitment; each maps to the principle tags that express it.
# Every principle a state instrument can carry lands in exactly one column or
# is deliberately left out (Federal coordination and Permitting acceleration
# are federal-layer ideas; Strict liability has no state instrument yet).
STATE_COMMITMENT_COLUMNS = {
    "disclose": ("Disclose water use", ("Disclosure", "Transparency", "NDA prohibition")),
    "review": ("Review before building", ("Preemptive review", "Permit oversight")),
    "pay": ("Pay its own way", ("Cost allocation",)),
    "conserve": ("Use less water", ("Conservation", "Closed-loop cooling")),
    "incentives": ("Condition incentives", ("Anti-corporate-welfare",)),
    "pause": ("Pause development", ("Moratorium",)),
    # "Issue guidance", not "Guidance only": a state lands here whenever any
    # enacted instrument carries guidance, even beside binding commitments.
    "guidance": ("Issue guidance", ("Best-practice guidance",)),
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


# --- Fact-pattern facets (cases, conflict sites, statutory readings) ---------

# What a project IS, as a closed vocabulary, so "apply the record to this
# proposal" can be computed instead of essayed. A case or site carries the
# facets its fact pattern exhibits (``fact_pattern``); a statutory reading
# carries the facets that make it potentially reach a project
# (``fact_triggers``). The Check-a-project engine (refdata.precedent) scores a
# reader's project against both — the overlap is the explanation, which is why
# this is a vocabulary and not an embedding.
#
# Every facet carries the trigger words the parser looks for in a pasted
# description. Triggers are tokens exactly as ``refdata.graph.tokenize`` emits
# them (lower-case unigrams or two-word bigrams) so the browser's parser and
# this module's agree by construction; a build test round-trips a fixture
# through both. ``blockers`` suppress a facet when a negating phrase is present
# ("non evaporative" must not read as evaporative cooling).
#
# A facet with no record carrying it is a chip matching nothing, so a value
# enters here in the same commit as the records that use it (both-ways
# membership is tested, as for every taxonomy in this module). A drafted
# zero-liquid-discharge value was held back on 2026-10-08 for exactly that
# reason: no case, site or dispute on record involves a ZLD campus (a search
# found operating examples, no matters). proc-incentive entered the same day
# with the Pima County Project Blue agreement on the site record and the
# community-benefit and incentive-condition instruments that trigger on it.
FACT_DIMENSION_LABELS = {
    "source": "Where the water comes from",
    "cooling": "How the campus uses it",
    "discharge": "Where the water goes",
    "site": "The site and its watershed",
    "power": "Power for the campus",
    "chemicals": "Fuel, chemicals and contamination",
    "process": "How the approval or dispute runs",
    "scale": "Scale",
}

FACT_FACETS = {
    # -- source --
    "src-wells": {
        "dimension": "source",
        "label": "On-site groundwater wells",
        "description": "The campus pumps its own wells or a dedicated wellfield.",
        "triggers": ["wells", "wellfield", "groundwater", "aquifer", "high capacity", "pump groundwater", "borehole"],
    },
    "src-surface": {
        "dimension": "source",
        "label": "Surface-water intake",
        "description": "A river, lake or reservoir intake, on site or through a new raw-water line.",
        "triggers": ["intake", "river", "lake", "reservoir", "surface water", "raw water", "withdrawal", "withdraw"],
    },
    "src-utility": {
        "dimension": "source",
        "label": "Water bought from a public water system",
        "description": "Service from a municipal, district or investor-owned water utility.",
        "triggers": ["water utility", "utility water", "municipal water", "city water", "public water", "water system", "potable", "water district", "water authority", "water service", "water plant", "water contract", "water supplier"],
    },
    "src-reclaimed": {
        "dimension": "source",
        "label": "Reclaimed or recycled water",
        "description": "Treated effluent, greywater or other non-potable supply.",
        "triggers": ["reclaimed", "recycled", "reuse", "greywater", "gray water", "purple pipe", "non potable", "nonpotable", "effluent reuse"],
    },
    "src-transfer": {
        "dimension": "source",
        "label": "Water moved from another basin or state",
        "description": "An inter-basin diversion, a Great Lakes diversion, or a pipeline from a distant source.",
        "triggers": ["interbasin", "inter basin", "diversion", "divert", "diverted", "water transfer", "transfer water", "imported water"],
    },
    # -- cooling --
    "cool-evaporative": {
        "dimension": "cooling",
        "label": "Evaporative cooling towers",
        "description": "Open cooling towers or adiabatic systems that consume water by evaporation.",
        "triggers": ["evaporative", "evaporation", "evaporate", "evaporates", "cooling towers", "cooling tower", "towers", "adiabatic", "consumptive"],
        "blockers": ["non evaporative", "zero evaporation"],
    },
    "cool-closed": {
        "dimension": "cooling",
        "label": "Closed-loop or liquid cooling",
        "description": "Recirculating, direct-to-chip or immersion cooling with little make-up water.",
        "triggers": ["closed loop", "non evaporative", "liquid cooling", "immersion", "recirculating", "direct chip", "chip cooling", "closed system"],
    },
    "cool-air": {
        "dimension": "cooling",
        "label": "Air (dry) cooling",
        "description": "Dry coolers or free cooling with no process water.",
        "triggers": ["air cooled", "air cooling", "dry cooling", "dry coolers", "free cooling", "waterless"],
    },
    "cool-once-through": {
        "dimension": "cooling",
        "label": "Once-through cooling",
        "description": "Water passes through once and returns warmer — the power-plant pattern.",
        "triggers": ["thermal discharge", "heated water", "return flow", "condenser water"],
    },
    # -- discharge --
    "out-sewer": {
        "dimension": "discharge",
        "label": "Blowdown to a sewer or treatment plant",
        "description": "Cooling blowdown and process water go to a publicly owned treatment works.",
        "triggers": ["sewer", "sewers", "potw", "wastewater treatment", "treatment plant", "sanitary", "pretreatment", "blowdown", "wastewater plant", "sewage"],
    },
    "out-surface": {
        "dimension": "discharge",
        "label": "Direct discharge to surface water",
        "description": "An outfall to a river, lake or stream under an NPDES-type permit.",
        "triggers": ["outfall", "npdes", "vpdes", "tpdes", "spdes", "direct discharge", "discharge permit", "effluent limits", "effluent limit", "surface discharge"],
    },
    "out-ground": {
        "dimension": "discharge",
        "label": "Discharge to the ground or injection wells",
        "description": "Infiltration, land application, septic or injection — reaching groundwater, not a pipe.",
        "triggers": ["injection", "infiltration", "septic", "land application", "drain field", "uic", "percolation", "leach"],
    },
    "out-stormwater": {
        "dimension": "discharge",
        "label": "Construction or site stormwater",
        "description": "Runoff, sediment and erosion from grading or from the built campus.",
        "triggers": ["stormwater", "storm water", "sediment", "erosion", "runoff", "swppp", "grading", "silt"],
    },
    # -- site --
    "ctx-wetlands": {
        "dimension": "site",
        "label": "Wetlands or streams on the site",
        "description": "Fill, crossings or buffers that bring in §404, state wetland law and §401.",
        "triggers": ["wetland", "wetlands", "stream", "streams", "tributary", "404", "wetland fill", "floodway", "riparian", "bog", "marsh"],
    },
    "ctx-stressed-aquifer": {
        "dimension": "site",
        "label": "Stressed or declining aquifer",
        "description": "Documented drawdown, overdraft, subsidence or failing neighbouring wells.",
        "triggers": ["depletion", "depleted", "drawdown", "declining", "overdraft", "subsidence", "dry wells", "wells dry", "interference", "went dry", "ran dry", "water table", "cone depression", "recharge"],
    },
    "ctx-drought": {
        "dimension": "site",
        "label": "Drought-prone or arid region",
        "description": "A basin under drought declarations, curtailment or shortage rules.",
        "triggers": ["drought", "arid", "desert", "scarce", "scarcity", "shortage", "curtailment", "water stressed", "water stress", "dry region"],
    },
    "ctx-small-system": {
        "dimension": "site",
        "label": "Small town or small water system",
        "description": "A community where one campus is a large share of the system's capacity.",
        "triggers": ["small town", "rural", "small city", "village", "township", "small community", "small utility", "small system"],
    },
    "ctx-city-reservoir": {
        "dimension": "site",
        "label": "Supply that a city drinks from",
        "description": "The source is a reservoir, lake or aquifer that supplies a city's drinking water.",
        "triggers": ["drinking water", "water supply", "supplies city", "drinking supply", "municipal supply", "sole source", "water source"],
    },
    "ctx-interstate": {
        "dimension": "site",
        "label": "Interstate river, aquifer or compact waters",
        "description": "A shared aquifer, an apportioned river or compact-governed basin.",
        "triggers": ["interstate", "compact", "great lakes", "lake michigan", "delaware river", "susquehanna", "memphis sand", "apportionment", "shared aquifer", "basin commission"],
    },
    "ctx-coastal": {
        "dimension": "site",
        "label": "Coastal plain, subsidence or saltwater intrusion",
        "description": "Coastal aquifers where pumping causes intrusion or land subsidence.",
        "triggers": ["coastal", "saltwater", "salt water", "intrusion", "sea level", "coastal plain", "subsiding"],
    },
    "ctx-tribal": {
        "dimension": "site",
        "label": "Tribal lands or reserved water rights",
        "description": "A reservation or senior tribal water right in the same source.",
        "triggers": ["tribal", "tribe", "tribes", "reservation", "pueblo", "indigenous", "tribal nation"],
    },
    "ctx-endangered": {
        "dimension": "site",
        "label": "Protected species habitat downstream",
        "description": "Listed species or critical habitat that depend on the flows at issue.",
        "triggers": ["endangered", "threatened species", "species", "habitat", "salmon", "mussel", "mussels", "sturgeon", "whooping", "critical habitat", "esa"],
    },
    "ctx-navigable": {
        "dimension": "site",
        "label": "Navigable water, floodplain or dam",
        "description": "Structures, dredging or storage in a navigable river, harbor or federal reservoir.",
        "triggers": ["navigable", "floodplain", "dam", "levee", "harbor", "corps reservoir", "federal reservoir", "dredge", "dredging", "barge"],
    },
    # -- power --
    "pwr-onsite-gas": {
        "dimension": "power",
        "label": "On-site gas turbines or generation",
        "description": "Behind-the-meter gas turbines, fuel cells or a dedicated power plant.",
        "triggers": ["gas turbines", "turbines", "turbine", "natural gas", "gas fired", "gas plant", "site generation", "onsite generation", "behind meter", "power plant", "fuel cells", "generation plant", "peaker"],
    },
    "pwr-diesel": {
        "dimension": "power",
        "label": "Diesel backup generators",
        "description": "Banks of diesel generators and their fuel.",
        "triggers": ["diesel", "backup generators", "generators", "generator", "standby"],
    },
    "pwr-nuclear": {
        "dimension": "power",
        "label": "Nuclear restart or new reactor",
        "description": "A restarted or new reactor, with its cooling water and federal approvals.",
        "triggers": ["nuclear", "reactor", "reactors", "smr", "uprate", "nuclear restart"],
    },
    "pwr-hydro": {
        "dimension": "power",
        "label": "Hydropower",
        "description": "Hydroelectric supply, a dam licence or flows governed by a federal licence.",
        "triggers": ["hydropower", "hydroelectric", "hydro", "ferc", "ferc license", "ferc licence", "dams"],
    },
    "pwr-thermo-cooling": {
        "dimension": "power",
        "label": "Power-plant cooling water",
        "description": "Cooling water drawn or discharged by generation built or restarted for the load.",
        "triggers": ["thermoelectric", "water intake", "316", "plant cooling", "condenser", "steam"],
    },
    # -- chemicals --
    "chem-pfas": {
        "dimension": "chemicals",
        "label": "PFAS in coolant or fire suppression",
        "description": "Fluorinated coolants, foams and the reporting and liability they carry.",
        "triggers": ["pfas", "pfoa", "pfos", "forever chemicals", "fluorinated", "afff", "fluorosurfactant", "genx"],
    },
    "chem-fuel": {
        "dimension": "chemicals",
        "label": "Fuel storage and spills",
        "description": "Diesel and oil storage, spill plans and spill events.",
        "triggers": ["fuel storage", "fuel tanks", "fuel tank", "storage tanks", "spill", "spills", "spcc", "petroleum", "leak", "leaked"],
    },
    "chem-treatment": {
        "dimension": "chemicals",
        "label": "Cooling-water treatment chemicals",
        "description": "Biocides, scale and corrosion inhibitors, nitrate and salts in blowdown.",
        "triggers": ["biocide", "biocides", "chlorine", "bromine", "corrosion inhibitor", "corrosion inhibitors", "nitrate", "nitrates", "salts", "tds", "treatment chemicals", "chemicals"],
    },
    "chem-legacy": {
        "dimension": "chemicals",
        "label": "Legacy contamination on the site",
        "description": "A brownfield, a plume, or a former industrial or federal site.",
        "triggers": ["brownfield", "superfund", "contaminated", "contamination", "remediation", "plume", "cleanup", "legacy contamination", "former plant", "former mill"],
    },
    # -- process --
    "proc-secrecy": {
        "dimension": "process",
        "label": "NDA, code name or trade-secret claims",
        "description": "Water figures withheld as confidential, or a project negotiated under a code name.",
        "triggers": ["nda", "ndas", "secrecy", "secret", "confidential", "trade secret", "code name", "codename", "non disclosure", "undisclosed", "unnamed", "redacted"],
    },
    "proc-pledge": {
        "dimension": "process",
        "label": "Water-positive or efficiency pledge",
        "description": "A replenishment, water-positive, WUE or closed-loop promise by the operator.",
        "triggers": ["water positive", "replenish", "replenishment", "pledge", "pledged", "wue", "net positive", "water commitment", "promise", "promised", "stewardship"],
    },
    "proc-zoning": {
        "dimension": "process",
        "label": "Rezoning or special-use permit",
        "description": "The fight runs through a rezoning, conditional-use or comprehensive-plan decision.",
        "triggers": ["rezoning", "rezone", "rezoned", "zoning", "special use", "conditional use", "land use", "comprehensive plan", "planning commission", "county commission", "city council", "board supervisors", "site plan"],
    },
    "proc-moratorium": {
        "dimension": "process",
        "label": "Moratorium or pause",
        "description": "A temporary halt on approvals while rules are written.",
        "triggers": ["moratorium", "moratoriums", "pause", "paused", "temporary ban", "interim ordinance"],
    },
    "proc-incentive": {
        "dimension": "process",
        "label": "Tax incentive or community-benefit agreement",
        "description": "Abatements, exemptions or a negotiated benefits agreement with water terms.",
        "triggers": ["tax abatement", "abatement", "incentive", "incentives", "tax incremental", "tif", "tax exemption", "tax break", "community benefit", "benefits agreement", "cba", "pilot agreement", "development agreement", "mou", "memorandum"],
    },
    "proc-lawsuit": {
        "dimension": "process",
        "label": "Litigation or citizen suit",
        "description": "A suit, petition or enforcement action already filed.",
        "triggers": ["lawsuit", "lawsuits", "sued", "suit", "complaint", "citizen suit", "injunction", "litigation", "appeal", "notice intent", "consent decree", "enforcement"],
    },
    "proc-records": {
        "dimension": "process",
        "label": "Public-records or disclosure fight",
        "description": "Records requests, reporting mandates and the fight over what gets published.",
        "triggers": ["public records", "foia", "records request", "disclosure", "disclose", "transparency", "reporting", "publish", "withheld"],
    },
    # -- scale --
    "scale-hyperscale": {
        "dimension": "scale",
        "label": "Large water user (hyperscale, or 1 MGD and up)",
        "description": "Roughly 100 MW or 1 MGD and up — the size at which one user moves a utility's numbers. On a historical case it marks an industrial user of that size. Also set from a stated MW or MGD figure.",
        "triggers": ["hyperscale", "hyperscaler", "gigawatt", "gigawatts", "mega campus", "ai campus", "billion gallons"],
    },
}

# Readings never carry scale; it ranks cases and sites only.
FACT_FACET_LABELS = {fid: f["label"] for fid, f in FACT_FACETS.items()}
