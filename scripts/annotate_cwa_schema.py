"""One-off migration: add case_type / cwa_applied / cwa_instrument /
cwa_pathway / analogous_cases to every case in cwa_investigations.json.

case_type      — the water-issue ("project type") taxonomy used by the new
                 dashboard filters; values must be keys of
                 dashboard.CWA_CASE_TYPE_LABELS.
cwa_applied    — "applied" (CWA or a state-delegated CWA program was formally
                 used: enforcement, citizen suit, court ruling, or permit
                 proceeding), "pending" (investigation/potential only), or
                 "not-applied" (a non-CWA vehicle, or none).
cwa_instrument — short header label for the card ("§402 construction
                 stormwater — state NOV").
cwa_pathway    — for pending/not-applied cases only: how the CWA *could*
                 reach the fact pattern.
analogous_cases— case_ids of historic examples backing the pathway.

Run once: python3 scripts/annotate_cwa_schema.py
Idempotent — re-running just overwrites the same fields.
"""

import json
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "data" / "reference" / "cwa_investigations.json"

# case_id -> (case_type, cwa_applied, cwa_instrument)
ANNOTATIONS = {
    # --- datacenter ---
    "Google-Stillwater-OK-stormwater-2025": ("construction-stormwater", "applied", "§402 construction stormwater — state NOV (closed)"),
    "Meta-MorganCo-GA-investigation-2026": ("groundwater", "pending", "EPA investigation pledged — no enforcement action yet"),
    "Microsoft-Boydton-VA-2023": ("construction-stormwater", "applied", "§402 construction stormwater — VA DEQ enforcement"),
    "QTS-Fayetteville-GA-2024": ("construction-stormwater", "applied", "§402 construction GP — citizen monitoring + GA EPD"),
    "QTS-CedarRapids-IA-2025": ("groundwater", "not-applied", "County well-permit enforcement (no CWA)"),
    "Nscale-MasonCounty-WV-2026": ("construction-stormwater", "pending", "Potential §402 construction stormwater — WV DEP"),
    "Amazon-Boardman-OR-nitrate-2026": ("groundwater", "not-applied", "State-law class action — $20.5M settlement (no CWA)"),
    "ProjectBlue-Tucson-AMES-2026": ("water-supply", "not-applied", "Municipal water denial + CAA dust NOV (no CWA)"),
    "JohnsHopkins-DSAI-Baltimore-2025": ("construction-stormwater", "applied", "§402 construction stormwater + §311 oil — MDE"),
    "Amazon-NewCarlisle-IN-wetlands-2025": ("wetlands-streams", "applied", "§404/§401 wetlands — IDEM cease-work order"),
    "PortOfMorrow-DEQ-OR-2024": ("potw-sewer", "applied", "§402 (delegated) — $727K penalty at receiving WWTP"),
    "Google-ProjectRaspberry-VA-2026": ("wetlands-streams", "applied", "§404 individual permit application (in federal review)"),
    "Google-ProjectLoch-VA-2026": ("wetlands-streams", "applied", "§404 individual permit application (in federal review)"),
    "Google-LittleRock-AR-2026": ("wetlands-streams", "applied", "§404 individual permit application (in federal review)"),
    # --- adjacent ---
    "xAI-Colossus-Memphis-TN-2026": ("groundwater", "not-applied", "State operating permit; no CWA discharge action"),
    "Atlas-ProjectSail-Coweta-GA-2026": ("groundwater", "not-applied", "State-court rezoning challenge (no CWA)"),
    "Google-Berkeley-SC-Middendorf-aquifer-2019": ("groundwater", "not-applied", "State withdrawal permit + private settlement (no CWA)"),
    "Rowan-ProjectCinco-Medina-TX-2025": ("groundwater", "not-applied", "Texas groundwater law / voluntary offsets (no CWA)"),
    "QTS-Fayette-GA-unbilled-water-2026": ("water-supply", "not-applied", "Utility metering / billing dispute (no CWA)"),
    "TransGas-AdamsFork-WV-2025": ("wetlands-streams", "applied", "§404 allegation via §505 citizen suit (pending)"),
    # --- industrial ---
    "Smithfield-Pagan-River-1997": ("industrial-discharge", "applied", "§402 NPDES — $12.6M civil judgment"),
    "Tyson-Sedalia-2003": ("industrial-discharge", "applied", "§309(c) criminal — felony plea"),
    "Brayton-Point-Dominion-2003-2007": ("cooling-water", "applied", "§316(a)/(b) — NPDES forced closed-cycle retrofit"),
    "Swift-Beef-Grand-Island-2011": ("pretreatment", "applied", "§307 pretreatment — consent decree"),
    "Yuengling-Pottsville-2016": ("pretreatment", "applied", "§307 pretreatment — consent decree"),
    "American-Zinc-Recycling-Palmerton-2021": ("cooling-water", "applied", "§402 NPDES contact cooling water — settlement"),
    "Cleveland-Cliffs-Burns-Harbor-2022": ("cooling-water", "applied", "§402 NPDES — penalty after cooling-loop failure"),
    "Norfolk-Southern-East-Palestine-2024": ("spills-contamination", "applied", "§311 spill — $15M CWA penalty"),
    "Chemours-Washington-Works-PFAS-2023": ("spills-contamination", "applied", "§402 NPDES PFAS effluent limits — consent agreement"),
    "Hanover-Foods-2025": ("industrial-discharge", "applied", "§402 NPDES — >$1M penalty, chronic exceedances"),
    "Plains-Pipeline-Santa-Barbara-2020": ("spills-contamination", "applied", "§311 oil spill — ~$24M federal penalty"),
    "Jersey-City-MUA-2025": ("potw-sewer", "applied", "§301/§402 CSO consent decree"),
    "Cahokia-Heights-2024": ("potw-sewer", "applied", "§301 unpermitted SSOs — consent decree"),
    "Guam-Waterworks-2024": ("potw-sewer", "applied", "§402 SSO/NPDES consent decree"),
    "Denali-Water-Solutions-2024": ("potw-sewer", "applied", "§405 sludge + §301 — judicial action"),
    "Reading-WWTP-2024": ("pretreatment", "applied", "§402 + §307 pretreatment-program consent decree"),
    "Republic-Steel-OH-2024": ("industrial-discharge", "applied", "§402 NPDES — joint federal-state action"),
    "Energix-VA-2024": ("construction-stormwater", "applied", "§402 VAR10 construction GP — escalating DEQ fines"),
    "Pactiv-Evergreen-Canton-NC-2023-2024": ("industrial-discharge", "applied", "§402 NPDES — NC DEQ civil penalties"),
    "Pacific-Seafood-OR-2026": ("industrial-discharge", "applied", "§402 NPDES — OR DEQ penalties w/ economic benefit"),
    "SpaceX-Starbase-TX-2024": ("industrial-discharge", "applied", "§402/TPDES unpermitted discharge — TCEQ + EPA"),
    "Hailiang-Copper-TX-2023": ("industrial-discharge", "applied", "§402/TPDES unauthorized discharge — TCEQ penalty"),
    "Agri-Star-Postville-IA-2024-2025": ("pretreatment", "applied", "§402 NPDES + pretreatment — state enforcement"),
    "Hyponex-Scotts-OH-2024": ("industrial-discharge", "applied", "§402 NPDES — EPA Region 5 + Ohio EPA"),
    "Atlanta-RMClayton-CRK-2024-2026": ("potw-sewer", "applied", "§505 citizen suit — numeric effluent violations"),
    "Youngstown-OH-CSO-2025": ("potw-sewer", "applied", "§301/§402 CSO consent decree (modified)"),
    "MDC-Hartford-CT-CSO-2025": ("potw-sewer", "applied", "§301/§402 SSO consent decree (modified)"),
    "Wynja-Feedlot-IA-CAFO-2025": ("industrial-discharge", "applied", "§301(a) unpermitted CAFO discharge — penalty"),
    "Oklahoma-v-Tyson-IRW-2005-2025": ("spills-contamination", "not-applied", "State public-nuisance judgment (no CWA)"),
    "Tyco-BASF-PFAS-AFFF-PWS-2024": ("spills-contamination", "not-applied", "Mass-tort drinking-water settlements (no CWA)"),
    "FortSmith-AR-sewer-CD-mod-2026": ("potw-sewer", "applied", "§301(a) SSO consent decree — 2026 modification"),
    "Greenidge-SenecaLake-NY-2025": ("cooling-water", "applied", "§316(a)/(b) + SPDES — thermal/intake findings"),
    # --- precedent ---
    "Sackett-v-EPA-2023": ("wetlands-streams", "applied", "SCOTUS ruling — §404/WOTUS jurisdiction narrowed"),
    "County-of-Maui-v-Hawaii-Wildlife-Fund-2020": ("groundwater", "applied", "SCOTUS ruling — §402 'functional equivalent' test"),
    "Entergy-v-Riverkeeper-2009": ("cooling-water", "applied", "SCOTUS ruling — §316(b) cost-benefit allowed"),
    "Rapanos-v-United-States-2006": ("wetlands-streams", "applied", "SCOTUS ruling — WOTUS plurality (pre-Sackett)"),
    "SF-EPA-end-result-2025": ("legal-doctrine", "applied", "SCOTUS ruling — bars 'end-result' NPDES permit terms"),
    "Maui-remand-DHaw-2021": ("groundwater", "applied", "§402 functional-equivalent test applied on remand"),
    "SierraClub-WVDEP-401-2023": ("wetlands-streams", "applied", "§401 state certification vacated (4th Cir.)"),
    "Loper-Bright-Enterprises-v-Raimondo-2024": ("legal-doctrine", "not-applied", "APA ruling — not itself a CWA case"),
    "Lewis-v-United-States-5th-Cir-2023": ("wetlands-streams", "applied", "§404 jurisdiction — Sackett applied (5th Cir.)"),
    "PortOfTacoma-v-PugetSoundkeeper-9thCir-2024": ("legal-doctrine", "applied", "§505 citizen-suit scope (9th Cir.)"),
    "CERF-v-Naples-9thCir-2024": ("legal-doctrine", "applied", "§505 mootness (9th Cir.)"),
}

# case_id -> (cwa_pathway, [analogous case_ids]) — only pending / not-applied cases.
PATHWAYS = {
    "Meta-MorganCo-GA-investigation-2026": (
        "If construction runoff or blasting sediment reaches streams or wetlands, the §402 "
        "construction general permit applies — the Stillwater and Boydton template. If "
        "contaminants are migrating to wells via groundwater that ultimately reaches surface "
        "water, Maui's 'functional equivalent' test could require an NPDES permit; the wells "
        "themselves are Safe Drinking Water Act territory, outside the CWA.",
        ["Google-Stillwater-OK-stormwater-2025", "Microsoft-Boydton-VA-2023",
         "County-of-Maui-v-Hawaii-Wildlife-Fund-2020"],
    ),
    "Nscale-MasonCounty-WV-2026": (
        "A silt-fence/retention failure that discharges sediment off-site is the classic §402 "
        "construction-stormwater violation — WV DEP can issue an NOV under its delegated "
        "construction general permit, and downstream residents could serve a §505 citizen-suit "
        "notice.",
        ["Microsoft-Boydton-VA-2023", "Google-Stillwater-OK-stormwater-2025", "Energix-VA-2024"],
    ),
    "QTS-CedarRapids-IA-2025": (
        "Construction dewatering that pumps groundwater to a surface water needs §402 dewatering "
        "authorization under the construction general permit; an unpermitted discharge to a "
        "stream would violate §301(a) regardless of pollutant concentrations.",
        ["Wynja-Feedlot-IA-CAFO-2025", "County-of-Maui-v-Hawaii-Wildlife-Fund-2020"],
    ),
    "Amazon-Boardman-OR-nitrate-2026": (
        "Under Maui, land-applied process water whose nitrate migrates through groundwater to "
        "the Columbia River could be the 'functional equivalent' of a direct discharge requiring "
        "a §402 NPDES permit — the same theory the Maui remand court applied to injection wells.",
        ["County-of-Maui-v-Hawaii-Wildlife-Fund-2020", "Maui-remand-DHaw-2021",
         "Oklahoma-v-Tyson-IRW-2005-2025"],
    ),
    "ProjectBlue-Tucson-AMES-2026": (
        "The CWA has no handle on a municipal water-service denial. The construction site itself "
        "still carries §402 stormwater obligations — sediment or dust-suppression runoff leaving "
        "the site would be enforceable the way Stillwater and Boydton were.",
        ["Google-Stillwater-OK-stormwater-2025", "Microsoft-Boydton-VA-2023"],
    ),
    "xAI-Colossus-Memphis-TN-2026": (
        "Aquifer withdrawal volume is outside the CWA. But if the greywater plant (or the campus) "
        "ever discharges treated effluent to surface water it needs a §402 NPDES permit, and "
        "pollutants reaching the Mississippi via the aquifer could trigger Maui's "
        "functional-equivalent test.",
        ["County-of-Maui-v-Hawaii-Wildlife-Fund-2020", "Google-Berkeley-SC-Middendorf-aquifer-2019"],
    ),
    "Atlas-ProjectSail-Coweta-GA-2026": (
        "If the parcel's omitted wetlands are jurisdictional (post-Sackett: a continuous surface "
        "connection to relatively permanent waters), grading them would need a §404 permit — the "
        "lever used at Amazon New Carlisle. Siting over a recharge area, by itself, is beyond "
        "the CWA.",
        ["Sackett-v-EPA-2023", "Amazon-NewCarlisle-IN-wetlands-2025"],
    ),
    "Google-Berkeley-SC-Middendorf-aquifer-2019": (
        "Pure consumption — the CWA regulates discharges, not withdrawals, and §316(b) intake "
        "rules only reach facilities pulling >2 MGD directly from surface waters. A CWA hook "
        "would require a discharge: blowdown to surface water (§402) or to the sewer (§307 "
        "pretreatment).",
        ["Entergy-v-Riverkeeper-2009", "Swift-Beef-Grand-Island-2011"],
    ),
    "Rowan-ProjectCinco-Medina-TX-2025": (
        "Groundwater pumping under the Rule of Capture is invisible to the CWA. Discharge-side "
        "hooks appear only if the campus obtains a TPDES permit for blowdown and then exceeds "
        "it — the SpaceX and Hailiang TCEQ actions show what Texas enforcement looks like.",
        ["SpaceX-Starbase-TX-2024", "Hailiang-Copper-TX-2023",
         "Google-Berkeley-SC-Middendorf-aquifer-2019"],
    ),
    "QTS-Fayette-GA-unbilled-water-2026": (
        "None plausible — metering and billing are utility-contract matters with no discharge, "
        "so no CWA section reaches them. The nearest water-accountability analog in this record "
        "is the same operator's construction-stormwater fight at Fayetteville.",
        ["QTS-Fayetteville-GA-2024"],
    ),
    "Oklahoma-v-Tyson-IRW-2005-2025": (
        "The agricultural-stormwater exemption keeps land-applied litter runoff out of §402. "
        "Land application of *industrial* or municipal-reuse water enjoys no such exemption — "
        "under Maui, nutrient migration to streams could require an NPDES permit, which is why "
        "this nuisance route matters for reclaimed-water cooling programs.",
        ["County-of-Maui-v-Hawaii-Wildlife-Fund-2020", "Amazon-Boardman-OR-nitrate-2026",
         "Denali-Water-Solutions-2024"],
    ),
    "Tyco-BASF-PFAS-AFFF-PWS-2024": (
        "AFFF releases reaching surface water are actionable as §311 hazardous-substance spills, "
        "and Chemours shows PFAS in effluent is already enforceable under §402 NPDES limits; "
        "EPA's pending PFAS effluent guidelines would make this routine.",
        ["Chemours-Washington-Works-PFAS-2023", "Norfolk-Southern-East-Palestine-2024"],
    ),
    "Loper-Bright-Enterprises-v-Raimondo-2024": (
        "Not a water case — but every CWA permit writer now loses Chevron deference, so each "
        "NPDES, §404, or WOTUS interpretation in the cases here is reviewable de novo. It "
        "applies to the CWA through every other case in this record.",
        ["Sackett-v-EPA-2023", "SF-EPA-end-result-2025"],
    ),
}


def main():
    payload = json.loads(PATH.read_text())
    cases = payload["cases"]
    ids = {c["case_id"] for c in cases}

    missing = ids - set(ANNOTATIONS)
    extra = set(ANNOTATIONS) - ids
    assert not missing, f"cases without annotation: {missing}"
    assert not extra, f"annotations without case: {extra}"

    for c in cases:
        ctype, status, instrument = ANNOTATIONS[c["case_id"]]
        c["case_type"] = ctype
        c["cwa_applied"] = status
        c["cwa_instrument"] = instrument
        if status in ("pending", "not-applied"):
            pathway, analogs = PATHWAYS[c["case_id"]]
            bad = [a for a in analogs if a not in ids]
            assert not bad, f"{c['case_id']}: unknown analogs {bad}"
            c["cwa_pathway"] = pathway
            c["analogous_cases"] = analogs

    PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"annotated {len(cases)} cases")


if __name__ == "__main__":
    main()
