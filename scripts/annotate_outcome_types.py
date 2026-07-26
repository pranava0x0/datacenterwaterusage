#!/usr/bin/env python3
"""One-off migration: classify every case by outcome type.

Plan Spec C3 piece 2, executing the outcome-taxonomy backlog item designed in
``docs/cwa-outcome-taxonomy.md``. Without it the corpus can say what a case was
*about* (``case_type``) but not what actually *happened*, so "what usually
happens when a regulator finds this" is unanswerable across 107 cases.

Multi-label: a consent decree that also imposed a penalty carries both.

**Method, and its limits.** The classifier reads each case's ``outcome`` prose
with high-precision phrase rules. That is reliable for the explicit vocabulary
these records use — "consent decree", "civil penalty", "PENDING" — and
unreliable for anything requiring judgement, so:

* every phrase rule is anchored on wording that means one thing in this corpus;
* ``OVERRIDES`` takes precedence for any case the rules read wrong, and is the
  right place to record a human decision rather than bending a rule to fit;
* a case the rules cannot classify is reported and left for an override, never
  silently defaulted to "pending".

Re-run after editing rules or overrides; it rewrites every case's
``outcome_type`` from scratch, so the file always reflects current logic.

Run: ``python3 scripts/annotate_outcome_types.py [--dry-run] [--show]``
Idempotent.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

CASES_PATH = BASE_DIR / "data" / "reference" / "cwa_investigations.json"

# (outcome_type, [phrases]). Phrases are matched case-insensitively against the
# `outcome` text. Anchored on vocabulary that is unambiguous in this corpus.
RULES: list[tuple[str, list[str]]] = [
    (
        "monetary-penalty",
        [
            "civil penalty", "civil penalties", "monetary penalty", "penalty of",
            "assessing a $", "fine of", "in penalties", "penalty totaling",
            "stipulated penalt", "forfeiture of $", "criminal fine",
            "paid $", "pleaded guilty", "fines paid", "administrative settlement",
            "settlement: $",
        ],
    ),
    (
        "consent-decree",
        [
            "consent decree", "consent order", "agreed order", "consent judgment",
            "settlement agreement", "administrative order on consent",
            "settlement in force", "settlements approved", "settlement approved",
        ],
    ),
    (
        "injunction-stop-work",
        [
            "injunction", "enjoin", "restraining order", "stop-work", "stop work",
            "cease-and-desist", "cease and desist", "cease work", "halted construction",
        ],
    ),
    (
        "permit-issued",
        [
            "permit issued", "issued the permit", "issued a final", "final permit",
            "permit was issued", "permit granted", "granted the permit",
            "authorization issued", "coverage granted", "certification issued",
            "approval granted", "permits issued", "permit required a",
        ],
    ),
    (
        "permit-denied",
        [
            "permit denied", "denied the permit", "application withdrawn",
            "withdrew its application", "withdrew the application", "rezoning voided",
            "voided the", "vacated the approval", "rejected the", "application denied",
            "withdrew its rezoning", "project withdrawn",
            "moratorium in effect", "withdrawn as of",
        ],
    ),
    (
        "permit-conditioned",
        [
            "effluent limit", "monitoring requirement", "required installation",
            "conditions requiring", "subject to conditions", "required to install",
            "mitigation required", "compensatory mitigation",
        ],
    ),
    (
        "jurisdiction-narrowed",
        [
            "not a water of the united states", "narrowed", "lacked jurisdiction",
            "no longer jurisdictional", "outside cwa jurisdiction",
            "shrank federal", "not jurisdictional",
        ],
    ),
    (
        "jurisdiction-affirmed",
        [
            "affirmed jurisdiction", "within cwa jurisdiction", "upheld jurisdiction",
            "functional equivalent", "jurisdiction affirmed", "held jurisdictional",
        ],
    ),
    (
        "compliance-order",
        [
            "emergency order", "compliance order", "administrative order",
            "notice of violation", "unilateral order", "§1431 order", "1431 order",
            "significant non-compliance", "significant noncompliance",
            "order required", "upheld the order", "ordered to ", "closed by rule",
        ],
    ),
    (
        "dismissed-no-liability",
        [
            "dismissed", "no liability", "found no violation", "ruled for the defendant",
            "reversed the judgment", "abuse of discretion", "were not liable",
            "not liable", "denied certiorari",
        ],
    ),
    (
        "settled-nonmonetary",
        [
            "mooting", "records released", "no fine", "resolved on billing",
            "without penalty", "no penalty was", "steered toward",
        ],
    ),
    (
        "pending-undecided",
        [
            "pending", "ongoing", "active as of", "no decision", "awaiting",
            "out for comment", "accepting public comments", "unresolved",
            "not yet", "still under review", "has not issued", "could run for years",
            "no enforcement", "projects proceed", "rescinded it",
        ],
    ),
]

# case_id -> outcome_type list. Wins over the rules entirely. Use for cases
# whose prose defeats phrase matching, and say why in a comment.
OVERRIDES: dict[str, list[str]] = {
    # The holding narrowed WOTUS; the word "narrowed" appears, but so does
    # "unanimous ... reversing", which the dismissal rule would also catch.
    "Sackett-v-EPA-2023": ["jurisdiction-narrowed"],
    # Maui created the functional-equivalent test — jurisdiction affirmed in
    # principle and remanded, not a dismissal.
    "County-of-Maui-v-Hawaii-Wildlife-Fund-2020": ["jurisdiction-affirmed"],
    # Loper Bright is about deference, not water jurisdiction; its effect on
    # this corpus is procedural.
    "Loper-Bright-Enterprises-v-Raimondo-2024": ["jurisdiction-narrowed"],
    # Equitable apportionment held to reach groundwater (a doctrinal expansion)
    # even though Mississippi's own complaint was dismissed.
    "Mississippi-v-Tennessee-2021": ["jurisdiction-affirmed", "dismissed-no-liability"],
    # The reciprocity condition was struck down: a limit on state power, which
    # reads as jurisdiction narrowed for the STATE, not for a federal agency.
    "Sporhase-v-Nebraska-1982": ["jurisdiction-narrowed"],
    # Prospective rule announced; these defendants escaped liability.
    "Friendswood-v-Smith-Southwest-1978": ["dismissed-no-liability"],
    # Standing narrowed — the group lost before the merits.
    "MCWC-v-Nestle-Waters-2007": ["dismissed-no-liability"],
    # Moratorium upheld; the would-be user lost.
    "Swanson-v-Marin-MWD-1976": ["dismissed-no-liability"],
    # Injunction reversed for want of proximate cause.
    "Aransas-Project-v-Shaw-2014": ["dismissed-no-liability"],
    # Permit upheld, but the agency's duty to consider impacts was affirmed.
    "Lake-Beulah-v-DNR-2011": ["permit-issued", "jurisdiction-affirmed"],
    # The EIR approval was set aside — the project had to redo it.
    "Vineyard-v-Rancho-Cordova-2007": ["permit-denied"],
    # Reserved right declared; nothing was penalized or permitted.
    "Winters-v-United-States-1908": ["jurisdiction-affirmed"],
    "Agua-Caliente-v-CVWD-2017": ["jurisdiction-affirmed"],
    # Trust reopener: existing rights held reviewable, remanded.
    "National-Audubon-v-Superior-Court-1983": ["jurisdiction-affirmed"],
    "ELF-v-SWRCB-2018": ["jurisdiction-affirmed"],
    "Waiahole-Ditch-2000": ["jurisdiction-affirmed"],
    # Ownership in place recognized; regulation may be a taking.
    "Edwards-Aquifer-Authority-v-Day-2012": ["jurisdiction-affirmed"],
    # Fractured plurality vacating and remanding; its lasting effect was to
    # contract the jurisdictional test, later settled by Sackett.
    "Rapanos-v-United-States-2006": ["jurisdiction-narrowed"],
    # Upheld EPA's use of cost-benefit analysis under §316(b) — an agency
    # discretion holding, not a penalty or a permit decision.
    "Entergy-v-Riverkeeper-2009": ["jurisdiction-affirmed"],
    # The §401 certification was vacated for an inadequate reasonable-assurance
    # finding: the state's approval was undone, not a federal permit denied.
    "SierraClub-WVDEP-401-2023": ["permit-denied", "jurisdiction-affirmed"],
    # NPDES permit issued with drastic intake and thermal conditions, upheld
    # after litigation — the conditions are the outcome.
    "Brayton-Point-Dominion-2003-2007": ["permit-issued", "permit-conditioned"],
    # RHA §10/§13 held to reach the deposits — a jurisdictional expansion.
    "US-v-Republic-Steel-RHA-1960": ["jurisdiction-affirmed"],
    # Designation created a standing federal review gate rather than resolving
    # a dispute.
    "Edwards-Aquifer-SoleSource-Designation-1975": ["jurisdiction-affirmed"],
    # Rulemaking closing a well subclass — regulatory, not adjudicatory.
    "EPA-UIC-ClassV-MotorVehicleWells-1999": ["compliance-order"],
    # No enforcement, no litigation, residents absorbed the cost: nothing has
    # been decided, which is the honest reading rather than "no liability".
    "Meta-NewtonCountyGA-well-failures-2018-2025": ["pending-undecided"],
    "xAI-Colossus-Memphis-TN-2026": ["pending-undecided"],
    # Long-running CSO consent decrees under active modification: the decree is
    # the outcome, and the compliance schedule is still running.
    "Youngstown-OH-CSO-2025": ["consent-decree", "pending-undecided"],
    "MDC-Hartford-CT-CSO-2025": ["consent-decree", "pending-undecided"],
    # Court-imposed remediation plan with special-master oversight; the
    # proposed settlement was rejected, so nothing is settled.
    "Oklahoma-v-Tyson-IRW-2005-2025": ["compliance-order", "pending-undecided"],
    # Penalties plus a receivership — the receivership is the remedy that
    # mattered, and no phrase rule should try to infer that.
    "US-v-Alisal-Water-Corp-2005": ["monetary-penalty", "compliance-order"],
    # The compensatory mitigation in this record is what the DEVELOPER
    # proposes, not what a regulator imposed — no permit has been decided.
    "Google-VanBurenTownship-MI-wetlands-2026": ["pending-undecided"],
}


# Phrase matching cannot see negation, and this corpus negates constantly:
# "No formal CWA NOV or consent order issued" contains both "consent order" and,
# nearby, "civil penalty" — so a naive match reports a penalised consent decree
# for a case where nothing has happened. Two guards, both found in review:
#
# 1. Clauses that negate enforcement are removed before matching. Sentence-
#    scoped, so a negation cannot swallow a real finding elsewhere in the text.
# 2. These records open with "PENDING" when the matter is undecided. That is a
#    reliable convention (12 of 12 verified), so it forces the pending tag —
#    but only *adds* it, because several pending matters have real interim
#    events worth keeping (an NOV issued, a TRO in effect).
NEGATED_CLAUSE = re.compile(
    r"[^.;]*\bno (?:formal|cwa enforcement|enforcement action|enforcement or|"
    r"permit issued|decision|penalty|fine and no)\b[^.;]*(?:[.;]|$)",
    re.IGNORECASE,
)
LEADING_PENDING = re.compile(r"^\W*pending\b", re.IGNORECASE)


def classify(outcome: str) -> list[str]:
    text = outcome.lower()
    # "no fine", "no penalty" are themselves the signal for a non-monetary
    # resolution, so read them before the negated clause is stripped away.
    settled_early = any(
        p in text for p in ("no fine", "no penalty was", "resolved on billing")
    )

    body = NEGATED_CLAUSE.sub(" ", text)
    hits = [otype for otype, phrases in RULES if any(p in body for p in phrases)]
    if settled_early and "settled-nonmonetary" not in hits:
        hits.append("settled-nonmonetary")

    # A resolved enforcement action is not also "pending". If anything concrete
    # happened, drop the pending tag — these records often describe a resolved
    # action with some ancillary matter still open.
    concrete = [h for h in hits if h != "pending-undecided"]
    hits = concrete or hits

    if LEADING_PENDING.match(outcome.strip()) and "pending-undecided" not in hits:
        hits.append("pending-undecided")
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--show", action="store_true", help="print every assignment")
    args = parser.parse_args()

    from refdata.taxonomies import OUTCOME_TYPE_LABELS

    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    unclassified: list[str] = []
    problems: list[str] = []

    unknown_overrides = {
        cid for cid in OVERRIDES if cid not in {c["case_id"] for c in payload["cases"]}
    }
    if unknown_overrides:
        problems.append(f"OVERRIDES names absent cases: {sorted(unknown_overrides)}")

    for case in payload["cases"]:
        types = OVERRIDES.get(case["case_id"]) or classify(case.get("outcome", ""))
        for t in types:
            if t not in OUTCOME_TYPE_LABELS:
                problems.append(f"{case['case_id']}: unknown outcome type {t}")
            counts[t] = counts.get(t, 0) + 1
        if not types:
            unclassified.append(case["case_id"])
        case["outcome_type"] = types
        if args.show:
            print(f"{case['case_id'][:52]:<54} {','.join(types)}")

    print(f"\ncases: {len(payload['cases'])}")
    for t, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {t:<24} {n}")
    unused = sorted(set(OUTCOME_TYPE_LABELS) - set(counts))
    if unused:
        print(f"taxonomy values unused: {unused}")
    if unclassified:
        print(f"\nUNCLASSIFIED ({len(unclassified)}) — add an OVERRIDES entry for each:")
        for cid in unclassified:
            print(f"  {cid}")
        problems.append(f"{len(unclassified)} cases unclassified")

    if problems:
        print("\nAborted:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    if args.dry_run:
        print("\n(dry run — nothing written)")
        return 0

    CASES_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("\nWrote cwa_investigations.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
