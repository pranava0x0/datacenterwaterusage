# CWA case outcome taxonomy

> **Reference for the Data Center Water Use Tracker.** `data/reference/cwa_investigations.json`
> stores each case's outcome as free text (the `outcome` field) — accurate, but not filterable or
> comparable across cases. This doc reads all 76 historical (resolved) cases and groups their
> outcomes into a closed taxonomy of **outcome types**, the same pattern already used for
> `case_type` (`CWA_CASE_TYPE_LABELS`) and legislation `general_principles`
> (`LEGISLATION_PRINCIPLE_DESCRIPTIONS`) in `dashboard.py`. Compiled 2026-07-05.
>
> **This is the map, not the application.** Tagging individual cases in the dataset and using the
> map to predict/label outcomes at named data-center sites (`data/reference/dc_water_conflicts.json`,
> Water Cases Part 4) is tracked as a follow-up in `backlog.md` — deliberately not done here.

## Why a separate taxonomy from `case_type`

`case_type` (Construction stormwater, Wetlands & streams, Cooling water & thermal, etc.) describes
**what kind of water issue** a case involves. It says nothing about **how the case ended** — a
$20M consent decree and a case dismissed as moot are both plausibly "industrial discharge" cases
by type, but they mean very different things for predicting what could happen at a live conflict
site. The outcome type is the missing second axis.

## The 12 outcome types

| # | Outcome type | What it means | Representative cases |
|---|---|---|---|
| 1 | **Monetary penalty** | A civil, criminal, or administrative fine was paid — the headline remedy, whether or not paired with injunctive relief. | Smithfield-Pagan-River-1997 ($12.6M), Norfolk-Southern-East-Palestine-2024 ($15M CWA + ~$310M total), Amazon-Boardman-OR-nitrate-2026 ($20.5M private settlement), Energix-VA-2024 (fined 3 straight years) |
| 2 | **Injunctive relief / mandated upgrade** | No penalty, or a minor one — the real remedy is required capital improvements, monitoring, corrective actions, or a compliance protocol. | Chemours-Washington-Works-PFAS-2023 (AOC, sampling/treatment plan, no penalty), Guam-Waterworks-2024 (~$400M sewer upgrades, no penalty cited), Google-Stillwater-OK-stormwater-2025 (NOV closed on corrective action) |
| 3 | **Criminal prosecution** | Federal or state criminal charges, not just a civil/administrative track. | Tyson-Sedalia-2003 (guilty plea, 20 felony counts) |
| 4 | **Structural remedy (receivership, divestiture, or closure)** | The remedy changed who operates the facility, or the facility stopped operating — a step beyond money or upgrades. | US-v-Alisal-Water-Corp-2005 (receivership + ordered divestiture), Republic-Steel-OH-2024 (facilities permanently closed), Pactiv-Evergreen-Canton-NC-2023-2024 (mill closed) |
| 5 | **Permit granted with mitigation conditions** | The regulator approved the permit/application, typically with compensatory mitigation, monitoring, or offset conditions attached. | Google-FortWayneIN-isolated-wetland-permit-2025 (wetland mitigation credits required), Microsoft-MountPleasantWI-wetland-individual-permit-2024, USACE-NWP39-DataCenters-2026 (nationwide permit finalized) |
| 6 | **Permit denied, vacated, or application withdrawn** | The regulator rejected the permit, a court vacated an issued certification, or the applicant pulled the application under regulatory pressure. | SierraClub-WVDEP-401-2023 (§401 certification vacated), Amazon-NewCarlisle-IN-wetlands-2025 (application withdrawn) |
| 7 | **Referral to further/escalated enforcement** | A negotiated settlement was rescinded or the matter was kicked up to a tougher enforcement track (state AG, DOJ). | QuantumLoophole-FrederickMD-boring-discharges-2022-2024 (proposed settlement rescinded, referred to MD AG) |
| 8 | **Dismissed, mooted, or cert denied** | The case ended without a substantive remedy — mootness, procedural dismissal, or a cert denial that just leaves a lower ruling intact. | CERF-v-Naples-9thCir-2024 (dismissed as moot), PortOfTacoma-v-PugetSoundkeeper-9thCir-2024 (cert denied), MilwaukeeRiverkeeper-RacineWI-water-records-suit-2025 (mooted by disclosure) |
| 9 | **No formal action — dispute unresolved** | No enforcement action or permit decision exists at all; costs/impacts are borne by residents, or the underlying conflict just continues. | Meta-NewtonCountyGA-well-failures-2018-2025 (residents paid their own well repairs), Meta-RichlandParish-LA-WaterSupply-2025 (no binding oversight), Bessemer-AL-Hyperscale-WaterSupply-2025 |
| 10 | **Landmark legal-standard ruling** | A precedent-setting decision that changes the legal test or jurisdictional scope, rather than resolving one violation. | Sackett-v-EPA-2023, County-of-Maui-v-Hawaii-Wildlife-Fund-2020, Loper-Bright-Enterprises-v-Raimondo-2024, Rapanos-v-United-States-2006 |
| 11 | **Pending / ongoing proceeding** | The matter is still moving as of the dataset's last update — comment period open, litigation active, settlement rejected and continuing. | AWS-LakeAnnaVA-VPDES-cooling-discharge-2026 (final decision not yet announced), Oklahoma-v-Tyson-IRW-2005-2025 (settlement rejected, court-supervised remedy continues), QTS-CedarRapids-IA-2025 |
| 12 | **Mass tort / multi-district settlement** | A coordinated, multi-plaintiff settlement spanning many defendants/claims (typically PFAS drinking-water litigation), not a single-facility enforcement action. | Tyco-BASF-PFAS-AFFF-PWS-2024 (combined with 3M/DuPont settlements, >$12.5B total) |

Two smaller patterns didn't earn their own row because they're a local/non-CWA variant of an
existing type rather than a new kind of ending — noted here so they aren't lost:
- **Local moratorium or rezoning reversal (non-CWA)** — a city/county paused or withdrew approval
  under community pressure rather than a water-agency permit decision. Currently folds into
  *#9 No formal action*: Charlotte-NC-drought-datacenter-moratorium-2026,
  Microsoft-CaledoniaWI-rezoning-withdrawal-2025.
- Many industrial consent decrees combine **#1 Monetary penalty** and **#2 Injunctive relief** in
  one settlement (e.g., Yuengling-Pottsville-2016, Cleveland-Cliffs-Burns-Harbor-2022) — tag both
  when this taxonomy is actually applied to the dataset; don't force a single primary type.

## Coverage note

This map was built by reading all 76 historical-case `outcome` strings in
`data/reference/cwa_investigations.json` (2026-07-05 snapshot). The 12 cases in
`display_section: "potential"` (Water Cases Part 3) aren't separately typed here since they're
definitionally pre-resolution — most would land in **#11 Pending** or **#9 No formal action** once
tagged. If the case dataset grows materially, re-scan for outcome patterns this taxonomy doesn't
yet cover (e.g., no case here ends in an acquitted/no-violation-found finding — add a type if one
shows up) rather than force-fitting new cases into a stale set of 12.

## Follow-up

See `backlog.md` — "Apply the CWA outcome taxonomy to data-center conflict sites" for the concrete
next step: tagging `cwa_investigations.json` cases with `outcome_type` (this map's keys) and using
analogous historical outcomes to annotate `dc_water_conflicts.json` sites with a "likely next step"
based on the closest-matching historical pattern.
