#!/usr/bin/env python3
"""Spec A2: give every operator claim a type, and wire the claims→litigation edge.

Until 2026 an operator's water claim was something to fact-check. It is now
also legal exposure — a former AWS water-sustainability manager is suing over
the company's published figures — so a claim needs a lifecycle, not just a
verdict: **made → assessed → challenged → resolved**.

Three additive changes:

* ``claim_type`` on every claim (closed taxonomy). A 2030 pledge, a measured
  WUE number and a site-specific promise fail in different ways and should not
  sit in one undifferentiated list.
* ``challenged_in`` — case_ids where the claim's truth is now before a court or
  regulator. Paired with ``related_claim_ids`` on the case; an integrity test
  walks both directions, because a half-wired edge shows the link on one card
  and not its counterpart.
* ``related_site_ids`` where a claim is about a specific tracked site, so a
  conflict card can show what the operator said about that place.

Also records three verified 2026 claim developments. One correction to the
plan's research: Google did **not** drop the 120% figure. The public
commitment was reframed as "replenish more water than we consume", and 120%
remains in the supporting technical documentation — a change of emphasis, not
of target.

Run: ``python3 scripts/annotate_claim_lifecycle.py [--dry-run]``
Idempotent.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

CLAIMS_PATH = BASE_DIR / "data" / "reference" / "company_water_claims.json"

# claim id -> claim_type. Every claim needs one.
CLAIM_TYPES = {
    "google-water-replenish-120": "water-positive-pledge",
    "meta-water-positive-2030": "water-positive-pledge",
    "ms-water-positive-2030": "water-positive-pledge",
    "aws-water-positive-2030": "water-positive-pledge",
    "switch-water-net-positive-2x": "water-positive-pledge",
    "edgeconnex-water-neutral-2030": "water-positive-pledge",
    "vantage-water-positivity-near-zero": "water-positive-pledge",
    "ms-water-replenish-2026": "water-positive-pledge",
    "qts-water-water-free-design": "zero-water-design",
    "anthropic-water-cooling-framework": "zero-water-design",
    "coreweave-water-uk-closedloop-intrator": "zero-water-design",
    "crusoe-water-abilene-closed-loop": "zero-water-design",
    "nebius-water-closed-loop": "zero-water-design",
    "openai-water-stargate-community-2026": "zero-water-design",
    "oracle-water-closed-loop-2026": "zero-water-design",
    "oracle-abilene-water-magouyrk-2025": "zero-water-design",
    "compass-water-zero-airside-mandate": "zero-water-design",
    "amazon-clinton-water-wehner-2026": "site-specific-promise",
    "aws-loudoun-va-water-recycled": "site-specific-promise",
    "xai-memphis-tn-water-recycling-80m": "site-specific-promise",
    "xai-memphis-water-recommit-2026": "site-specific-promise",
    "xai-memphis-water-musk-sequencing-2026": "site-specific-promise",
    "google-council-bluffs-ia-water-grade-stabilization": "site-specific-promise",
    "google-mesa-az-water-srp-donation": "site-specific-promise",
    "google-mesa-az-water-stewardship": "site-specific-promise",
    "meta-prineville-or-water-stewardship-pdf": "site-specific-promise",
    "meta-newton-ga-water-onsite-efficiency": "efficiency-wue",
    "meta-richland-la-water-restoration-watersheds": "site-specific-promise",
    "meta-beaver-dam-water-davis-2025": "site-specific-promise",
    "ms-quincy-wa-water-reuse": "site-specific-promise",
    "ms-mt-pleasant-wi-water-modest": "efficiency-wue",
    "switch-water-100-percent-recycled": "replenishment-milestone",
    "wonder-valley-water-oleary-salt-lake-2026": "disclosure-transparency",
    "wonder-valley-water-oleary-env-studies-2026": "disclosure-transparency",
}

# claim id -> tracked conflict sites the claim is about.
RELATED_SITES = {
    "aws-loudoun-va-water-recycled": ["pw-digital-gateway-va"],
    "xai-memphis-tn-water-recycling-80m": ["xai-colossus-memphis-tn"],
    "xai-memphis-water-recommit-2026": ["xai-colossus-memphis-tn"],
    "xai-memphis-water-musk-sequencing-2026": ["xai-colossus-memphis-tn"],
    "meta-newton-ga-water-onsite-efficiency": ["meta-newton-county-ga"],
    "meta-richland-la-water-restoration-watersheds": ["meta-richland-parish-la"],
    "ms-mt-pleasant-wi-water-modest": ["microsoft-racine-county-wi"],
    "google-mesa-az-water-stewardship": ["meta-mesa-microsoft-goodyear-az"],
    "google-mesa-az-water-srp-donation": ["meta-mesa-microsoft-goodyear-az"],
    "meta-water-positive-2030": ["meta-cheyenne-wy", "meta-newton-county-ga"],
}

# claim id -> case_ids where the claim's truth is now contested in a forum.
CHALLENGED_IN = {
    "aws-water-positive-2030": ["Wangusi-v-Amazon-Web-Services-VA-2026"],
}

# Verified claim developments, 2026-07-26.
CLAIM_UPDATES = {
    "aws-water-positive-2030": {
        "delivered": {
            "status": "litigated",
            "summary": (
                "AWS's published Northern Virginia water figures are now before the "
                "Circuit Court of Arlington County. A former AWS water sustainability "
                "program manager alleges, on FOIA'd utility billing records for "
                "2023-2026, that the company's '42% year-over-year reduction' and "
                "'ninety-seven percent of the year ... not using any water' statements "
                "are materially misleading. AWS denies wrongdoing and says its water "
                "data is independently assured by a third party. No ruling as of "
                "2026-07-26 — this records that the claim is contested in a forum, not "
                "that it is false."
            ),
            "source_url": "https://www.theregister.com/on-prem/2026/07/15/aws-sustainability-claims-dont-hold-water-lawsuit-alleges/5269723",
            "source_title": "The Register — AWS sustainability claims don't hold water, lawsuit alleges",
            "assessed_at": "2026-07-26",
        },
    },
    "google-water-replenish-120": {
        "delivered": {
            "status": "partial",
            "summary": (
                "Reframed rather than retired. Google's June 2026 announcement leads "
                "with replenishing 'more water than we consume' across data centers by "
                "2030; the 120% figure remains in the supporting technical "
                "documentation, so the target stands while the headline softened. "
                "Progress is real and large — 165 projects across 97 watersheds, "
                "$17M committed across seven states, and projects expected to replenish "
                "over 19 billion gallons a year by 2030, roughly double 2024 "
                "consumption — but replenishment is watershed-level and does not by "
                "itself answer local strain where a campus actually draws."
            ),
            "source_url": "https://blog.google/company-news/outreach-and-initiatives/sustainability/new-water-stewardship-commitments/",
            "source_title": "Google — New water stewardship commitments (June 2026)",
            "assessed_at": "2026-07-26",
        },
    },
    "ms-water-positive-2030": {
        "delivered": {
            "status": "partial",
            "summary": (
                "Microsoft reported in June 2026 that in FY25 it replenished more water "
                "than it withdrew — the 2030 pledge met roughly five years early, but "
                "as a GLOBAL AGGREGATE. Replenishment credited in one basin does not "
                "reach a community where a campus draws, so the milestone is real at "
                "company scale and unverified at the scale communities experience. "
                "Independent basin-level adjudication does not exist."
            ),
            "source_url": "https://blogs.microsoft.com/blog/2026/06/24/inside-microsofts-two-decade-push-to-cut-water-intensity-while-scaling-for-growth/",
            "source_title": "Microsoft — Inside Microsoft's two-decade push to cut water intensity",
            "assessed_at": "2026-07-26",
        },
    },
}

# New claims recording the 2026 statements themselves.
NEW_CLAIMS = [
    {
        "id": "ms-water-wue-90-percent-2026",
        "company_slug": "microsoft",
        "theme": "water",
        "claim_type": "efficiency-wue",
        "statement": (
            "Through continuous innovation and advancements in cooling technologies, "
            "Microsoft has improved its water use effectiveness by nearly 90% since its "
            "first generation of datacenters in the early 2000s."
        ),
        "source_url": "https://blogs.microsoft.com/blog/2026/06/24/inside-microsofts-two-decade-push-to-cut-water-intensity-while-scaling-for-growth/",
        "source_title": "Microsoft — Inside Microsoft's two-decade push to cut water intensity",
        "captured_at": "2026-07-26",
        "delivered": {
            "status": "partial",
            "summary": (
                "The figure is fleet-average water use effectiveness falling from 2.3 to "
                "0.27 L/kWh, measured against Microsoft's earliest 2000s facilities — a "
                "two-decade intensity improvement, not a claim about how much water "
                "current data centers use. Intensity per kilowatt-hour can fall while "
                "total withdrawal rises, and AI load is rising fast; Microsoft's own "
                "nearer-term target is a 40% intensity improvement by 2030, 25% achieved "
                "as of 2025."
            ),
            "source_url": "https://www.geekwire.com/2026/microsoft-says-its-data-centers-use-90-less-water-than-its-earliest-facilities-as-public-concern-grows/",
            "source_title": "GeekWire — Microsoft says its data centers use 90% less water than its earliest facilities",
            "assessed_at": "2026-07-26",
        },
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from refdata.taxonomies import CLAIM_TYPE_LABELS, DELIVERED_STATUS_COLORS

    payload = json.loads(CLAIMS_PATH.read_text(encoding="utf-8"))
    problems: list[str] = []

    existing = {c["id"] for c in payload["claims"]}
    for claim in NEW_CLAIMS:
        if claim["id"] not in existing:
            payload["claims"].append(claim)

    known = {c["id"] for c in payload["claims"]}
    for mapping, label in (
        (CLAIM_TYPES, "CLAIM_TYPES"),
        (RELATED_SITES, "RELATED_SITES"),
        (CHALLENGED_IN, "CHALLENGED_IN"),
        (CLAIM_UPDATES, "CLAIM_UPDATES"),
    ):
        for cid in mapping:
            if cid not in known:
                problems.append(f"{label} names an absent claim: {cid}")

    typed = linked = challenged = updated = 0
    for claim in payload["claims"]:
        cid = claim["id"]
        ctype = claim.get("claim_type") or CLAIM_TYPES.get(cid)
        if ctype is None:
            problems.append(f"{cid}: no claim_type — every claim needs one")
        elif ctype not in CLAIM_TYPE_LABELS:
            problems.append(f"{cid}: unknown claim_type {ctype}")
        else:
            if claim.get("claim_type") != ctype:
                typed += 1
            claim["claim_type"] = ctype

        if cid in RELATED_SITES and claim.get("related_site_ids") != RELATED_SITES[cid]:
            claim["related_site_ids"] = RELATED_SITES[cid]
            linked += 1
        if cid in CHALLENGED_IN and claim.get("challenged_in") != CHALLENGED_IN[cid]:
            claim["challenged_in"] = CHALLENGED_IN[cid]
            challenged += 1
        if cid in CLAIM_UPDATES:
            for key, value in CLAIM_UPDATES[cid].items():
                if claim.get(key) != value:
                    claim[key] = value
                    updated += 1

    for claim in payload["claims"]:
        status = (claim.get("delivered") or {}).get("status")
        if status and status not in DELIVERED_STATUS_COLORS:
            problems.append(f"{claim['id']}: unknown delivered.status {status}")

    counts: dict[str, int] = {}
    for claim in payload["claims"]:
        ctype = claim.get("claim_type", "<untyped>")
        counts[ctype] = counts.get(ctype, 0) + 1

    print(f"claims: {len(payload['claims'])} (typed {typed}, site-linked {linked}, "
          f"challenged {challenged}, assessments updated {updated})")
    for t, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {t:<26} {n}")
    unused = sorted(set(CLAIM_TYPE_LABELS) - set(counts))
    if unused:
        problems.append(f"claim types with no claims: {unused}")

    if problems:
        print("\nAborted:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    if args.dry_run:
        print("\n(dry run — nothing written)")
        return 0

    payload["last_updated"] = "2026-07-26"
    CLAIMS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("\nWrote company_water_claims.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
