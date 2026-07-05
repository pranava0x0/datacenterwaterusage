"""HISTORICAL one-off migration (2026-07-02) — kept for provenance only.

Annotated the 78 cases that existed on 2026-07-02 with the statutory-
authority mapping introduced alongside data/reference/water_authorities.json:

authorities — list of reading_ids from water_authorities.json identifying
              which statutory hooks (CWA §402, SDWA §1431, TSCA §8(e), …)
              the case actually used or — for pending/not-applied cases —
              could plausibly be reached by. Overlap is intentional: one
              fact pattern can trigger several readings. The case's statute
              pills are DERIVED from these ids at render time (each
              reading_id carries its statute), so there is no separate
              per-case statutes field to drift.

Defaults come from case_type; OVERRIDES pins every case where the type-level
default is wrong or incomplete. Cases added after 2026-07-02 ship with
``authorities`` inline — the script refuses to run against a newer dataset.

Run once: python3 scripts/annotate_water_authorities.py
Idempotent — re-running just overwrites the same field.
"""

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CASES_PATH = BASE / "data" / "reference" / "cwa_investigations.json"
AUTHORITIES_PATH = BASE / "data" / "reference" / "water_authorities.json"

# The 78 case_ids present when this migration ran. Newer cases must carry
# their own ``authorities`` — refuse to guess for them.
EXPECTED_COUNT = 78

DEFAULTS_BY_TYPE = {
    "construction-stormwater": ["cwa-402-construction-stormwater"],
    "wetlands-streams": ["cwa-404-dredge-fill"],
    "cooling-water": ["cwa-316-cooling", "cwa-402-npdes"],
    "industrial-discharge": ["cwa-402-npdes"],
    "pretreatment": ["cwa-307-pretreatment"],
    "potw-sewer": ["cwa-402-npdes"],
    "groundwater": ["cwa-402-maui-groundwater"],
    "spills-contamination": ["cwa-311-spills"],
    "water-supply": ["sdwa-pws-compliance"],
    "legal-doctrine": ["cwa-505-citizen-suit"],
}

OVERRIDES = {
    # Construction cases with a second hook
    "JohnsHopkins-DSAI-Baltimore-2025": [
        "cwa-402-construction-stormwater", "cwa-311-spills"
    ],
    "QTS-Fayetteville-GA-2024": [
        "cwa-402-construction-stormwater", "cwa-505-citizen-suit"
    ],
    # §401 certification cases
    "SierraClub-WVDEP-401-2023": ["cwa-401-certification"],
    "SDC-ATLA-DouglasCounty-GA-404-401-2025": [
        "cwa-404-dredge-fill", "cwa-401-certification"
    ],
    "Amazon-NewCarlisle-IN-wetlands-2025": [
        "cwa-404-dredge-fill", "cwa-401-certification"
    ],
    "Microsoft-MountPleasantWI-wetland-individual-permit-2024": [
        "cwa-404-dredge-fill", "cwa-401-certification"
    ],
    "TransGas-AdamsFork-WV-2025": [
        "cwa-404-dredge-fill", "cwa-505-citizen-suit"
    ],
    # POTW / pretreatment interplay
    "PortOfMorrow-DEQ-OR-2024": ["cwa-402-npdes", "cwa-307-pretreatment"],
    "Reading-WWTP-2024": ["cwa-307-pretreatment", "cwa-402-npdes"],
    "Atlanta-RMClayton-CRK-2024-2026": [
        "cwa-402-npdes", "cwa-505-citizen-suit"
    ],
    # Groundwater cases whose real hooks are SDWA/RCRA, not Maui
    "Meta-MorganCo-GA-investigation-2026": [
        "sdwa-1431-emergency", "sdwa-source-water-protection"
    ],
    "Amazon-Boardman-OR-nitrate-2026": [
        "sdwa-1431-emergency", "rcra-7002-7003-endangerment"
    ],
    "QTS-CedarRapids-IA-2025": ["sdwa-source-water-protection"],
    "xAI-Colossus-Memphis-TN-2026": [
        "cwa-402-npdes", "cwa-307-pretreatment", "sdwa-source-water-protection"
    ],
    "Atlas-ProjectSail-Coweta-GA-2026": ["sdwa-source-water-protection"],
    "Google-Berkeley-SC-Middendorf-aquifer-2019": [
        "sdwa-source-water-protection"
    ],
    "Rowan-ProjectCinco-Medina-TX-2025": [
        "sdwa-source-water-protection", "sdwa-1424e-sole-source-aquifer"
    ],
    "CorpusChristi-SintonTX-EvangelineAquifer-wells-2026": [
        "sdwa-source-water-protection"
    ],
    "Sailfish-HoodCountyTX-ComancheCircle-aquifer-moratorium-2025-2026": [
        "sdwa-source-water-protection"
    ],
    "Meta-NewtonCountyGA-well-failures-2018-2025": [
        "sdwa-1431-emergency", "sdwa-source-water-protection"
    ],
    # Contamination cases that ran (or would run) under §402 not §311
    "Oklahoma-v-Tyson-IRW-2005-2025": ["cwa-402-npdes"],
    "QuantumLoophole-FrederickMD-boring-discharges-2022-2024": [
        "cwa-402-npdes"
    ],
    "Chemours-Washington-Works-PFAS-2023": [
        "cwa-402-npdes", "tsca-8a7-pfas-reporting"
    ],
    "Tyco-BASF-PFAS-AFFF-PWS-2024": [
        "sdwa-pws-compliance", "tsca-8e-substantial-risk"
    ],
    # Doctrine cases that aren't §505 doctrine
    "Loper-Bright-Enterprises-v-Raimondo-2024": [],
    "SF-EPA-end-result-2025": ["cwa-402-npdes"],
    # Cooling/permit stacks
    "AWS-LakeAnnaVA-VPDES-cooling-discharge-2026": [
        "cwa-316-cooling", "cwa-402-npdes", "cwa-303-wqs", "rha-10-structures"
    ],
    "Entergy-v-Riverkeeper-2009": ["cwa-316-cooling"],
}


def main() -> None:
    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = payload["cases"]
    if len(cases) != EXPECTED_COUNT:
        sys.exit(
            f"Refusing to run: dataset has {len(cases)} cases, expected "
            f"{EXPECTED_COUNT}. Cases added after 2026-07-02 must carry "
            "'authorities' inline."
        )

    registry = json.loads(AUTHORITIES_PATH.read_text(encoding="utf-8"))
    valid_ids = {r["reading_id"] for r in registry["readings"]}

    for case in cases:
        cid = case["case_id"]
        readings = OVERRIDES.get(cid, DEFAULTS_BY_TYPE.get(case["case_type"]))
        if readings is None:
            sys.exit(f"No authority mapping for {cid} ({case['case_type']})")
        unknown = [r for r in readings if r not in valid_ids]
        if unknown:
            sys.exit(f"Unknown reading_id(s) {unknown} on {cid}")
        case["authorities"] = readings

    CASES_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Annotated {len(cases)} cases with 'authorities'.")


if __name__ == "__main__":
    main()
