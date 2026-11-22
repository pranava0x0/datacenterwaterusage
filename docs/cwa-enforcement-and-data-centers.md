# Clean Water Act enforcement & a data-center read-across

> **Research reference for the Data Center Water Use Tracker.** The Clean Water Act (CWA,
> 33 U.S.C. §1251 et seq.) is the federal statute governing pollutant discharges to U.S. waters —
> directly relevant to data-center **cooling-water discharge, stormwater, wetlands fill, and on-site
> fuel storage**. This note catalogs how the CWA has actually been *enforced* (energy/utility sector,
> **2015 → present**) and maps each statutory hook to data-center facts. It complements the project's
> VA/OH portal scraping (which captures *water-use* documents) with the *federal enforcement* angle.
> Web-sourced from primary `.gov` (EPA, DOJ) + the Congressional Research Service. Captured 2026-06-02;
> prioritized CWA-application theories section added 2026-06-23.
> **Data-center applications below are analysis. See the curated case registry for recorded enforcement actions.**

## Why this exists

Compiled while scoping the regulatory exposure around data-center water use. This note catalogs energy/utility CWA cases
and assesses how their statutory provisions may apply to data-center operations. The curated
case registry separately records actions involving data centers and their contractors. The case facts below are quoted from primary EPA/DOJ
sources; the data-center column is analysis, labeled as such.

## Enforcement actions — energy/utility, 2015–present

Type: **C** = criminal · **Civ** = civil judicial · **Adm** = administrative.

| Year | Defendant | Type | Violation / facts | Outcome | Source |
|---|---|---|---|---|---|
| 2015 | **Duke Energy** (3 subsidiaries) | C | 9 criminal CWA counts — Feb 2014 Dan River coal-ash spill (Eden, NC) + 4 other NC coal plants; failure to maintain equipment | Guilty plea May 14, 2015; **$102M** ($68M fine + $34M projects/conservation) | [DOJ](https://www.justice.gov/archives/opa/pr/duke-energy-subsidiaries-plead-guilty-and-sentenced-pay-102-million-clean-water-act-crimes) |
| 2015 | **Arch Coal / ICG** (+14 subs) | Civ | 1,200+ discharge-limit violations (aluminum, manganese, iron, TSS), coal mines in KY/PA/MD/VA/WV | Lodged Aug 6 / entered Oct 29, 2015; **$2M** civil penalty + compliance program | [EPA](https://www.epa.gov/wv/action-resolves-hundreds-coal-companies-violations) |
| 2015 | **Anadarko Petroleum** | Civ | CWA §311 — 25% lease owner, Deepwater Horizon | Ruling Nov 30, 2015; **$159.5M** civil penalty | [DOJ ENRD](https://www.justice.gov/enrd/deepwater-horizon) |
| 2015 | **ExxonMobil Pipeline / Mobil Pipeline** | Civ | CWA §311 — 2013 Pegasus pipeline rupture, ~3,190 bbl crude into Lake Conway, Mayflower, AR | Apr 22, 2015; **$3,190,000** federal civil penalty (Oil Spill Liability Trust Fund) | [EPA](https://www.epa.gov/enforcement/exxonmobil-mayflower-clean-water-settlement) |
| 2015* | **ExxonMobil Pipeline** | Civ | CWA §311 — 2012 North Line rupture, ~2,800 bbl crude, Torbert, LA | **$1,437,120** civil penalty (*date not independently confirmed — DOJ page 403'd*) | [DOJ](https://www.justice.gov/archives/opa/pr/exxonmobil-pipeline-company-pay-civil-penalty-under-proposed-settlement-torbert-louisiana-oil) |
| 2016 | **BP** (Deepwater Horizon) | Civ | CWA §311 — 2010 Gulf of Mexico blowout | Consent decree entered Apr 4, 2016; **$5.5B CWA penalty** (largest-ever environmental penalty), part of $20.8B total | [DOJ ENRD](https://www.justice.gov/enrd/deepwater-horizon) |
| 2016 | **Enbridge Energy** | Civ | 2010 oil spills — Marshall, MI (Kalamazoo R.) + Romeoville, IL | July 2016; **$62M** civil penalties + ~$110M injunctive | [EPA](https://www.epa.gov/enforcement/enbridge-clean-water-act-settlement) |
| 2016 | **Sunoco Pipeline, L.P.** | Civ | Crude spills — Barbers Hill, TX (2009) + Cromwell, OK (2011) | July 2016; **$850K** federal civil penalty | [EPA](https://www.epa.gov/enforcement/sunoco-pipeline-lp-clean-water-act-settlement) |
| 2017 | **Magellan Pipeline, L.P.** | Civ | Gasoline/diesel/jet-fuel spills — TX, NE, KS | Jan 2017; **$2M** penalty + ~$16M injunctive | [DOJ](https://www.justice.gov/archives/opa/pr/magellan-pipeline-settles-alleged-clean-water-act-violations-related-spills-texas-nebraska) |
| 2021 | **Summit Midstream Partners** | C+Civ | 700,000+ bbl produced-water spill over 143 days, Blacktail Creek, ND (largest inland spill); failure to report | **$15M criminal + $20M civil** + $1.25M NRD | [DOJ](https://www.justice.gov/opa/pr/pipeline-company-sentenced-largest-ever-inland-oil-spill) |
| 2021–22 | **Amplify Energy** (+2 subs) | C | Negligent oil discharge — Oct 2021 San Pedro Bay offshore spill, CA | Pleas Aug 2022; **~$13M** ($7.1M fine + ~$5.8M response costs) + probation | [DOJ](https://www.justice.gov/usao-cdca/pr/three-companies-agree-plead-guilty-federal-offense-and-pay-nearly-13-million-federal) |
| 2022 | **West Penn Power** | Civ | Boron limit exceedances (NPDES), 2 coal-ash landfills (Mingo + Springdale, PA) | Jan 12, 2022; **$610K** (split US/PA DEP) | [EPA](https://www.epa.gov/newsreleases/west-penn-power-pay-610000-penalty-federal-state-settlement-over-discharge-violations) |
| 2024 | **Holly Energy / Osage Pipe Line** | Civ | CWA §311(b) — July 2022 crude rupture near Cushing, OK (~300K gal) on Sac & Fox Nation land | Jan 30, 2024; **$7.4M** civil penalty | [EPA](https://www.epa.gov/newsreleases/oil-companies-pay-74-million-civil-penalties-resolve-us-claims-pipeline-spill-allotted) |
| 2025 | **SFPP, L.P.** (Kinder Morgan) | Adm | CWA Class II administrative penalty — gasoline pipeline discharge, Walnut Creek, CA | Docket CWA-09-2025-0109 (~July 2025) | [EPA](https://www.epa.gov/ca/CWA-09-2025-0109) |
| 2025 | **Plantation Pipe Line Co.** | Civ | Jet fuel & gasoline discharges — VA/GA/NC | **$725K** penalty + **$1.3M** spill-prevention upgrades | [EPA](https://www.epa.gov/enforcement/plantation-pipe-line-company-clean-water-act-settlement) |

**Landmark / jurisdiction:** *Sackett v. EPA* (decided May 25, 2023) narrowed CWA "waters of the
United States" to relatively permanent waters + the "continuous surface connection" wetlands test,
rejecting the *Rapanos* "significant nexus" standard; EPA/Army amended the 2023 WOTUS rule to
conform. [CRS LSB10981](https://crsreports.congress.gov/product/pdf/LSB/LSB10981)

## Civil/administrative coverage — the long tail

Criminal CWA prosecutions in this sector are **near-comprehensive** above. Civil/administrative is
**representative, not exhaustive**: EPA's ECHO database returned **~1,626 CWA case rows** in a single
slice — the bulk are small facility-level administrative penalties that don't generate national press
releases and aren't individually notable. The authoritative places to go exhaustive:

- **EPA Civil Cases and Settlements** (notable federal tier, filterable by statute): <https://cfpub.epa.gov/enforcement/cases/>
- **EPA ECHO** (every facility-level action, filterable by statute + NAICS, bulk export): <https://echo.epa.gov/>
- **DOJ ENRD** press releases / cases: <https://www.justice.gov/enrd>

When the project starts tracking data-center facilities directly, ECHO can be filtered by the facility's
own NAICS (**518210** data processing/hosting) and by the **551114 / 221** codes of any co-located
generation, to catch a data-center NPDES or §311 action the moment one is brought.

### Leads surfaced but NOT yet confirmed against a primary source
- **Energy Transfer** — reportedly ~$7M federal CWA penalty for three Louisiana releases (+ ~$1M LA state, Caddo Parish). Couldn't locate the primary `.gov` page.
- **ATP Infrastructure Partners, LP** — ~$1M CWA settlement (Gulf offshore oil/gas). Date unverified.
- **Trans Energy Inc.** — ~$3M, WV §404 stream/wetland fill at gas well sites (~2015). Date/amount unverified.
- **Xplor Energy** — felony CWA, U.S. v. (E.D. La.). Date unverified.

### Verified pre-2015 → excluded
**XTO Energy** ($100K, §301 fracking flowback, PA, **2013**) · **Patriot Coal** ($6.5M, WV, **2009**) ·
**Colonial Pipeline** ($34M, **2003**) · **Pacific Pipeline Systems** ($1.3M, **2010**) ·
**Transocean** ($1.4B Deepwater Horizon plea, **2013**) · **Anadarko** 2009 CWA settlement (>$1M; distinct from the 2015 DWH $159.5M penalty) ·
**Louisiana Generating** ($3.5M — Clean *Air* Act, wrong statute, 2009) · **Koch** refinery/oil-spill CWA (pre-2015).

## The CWA hooks, and how they map to data centers

Because **no data-center CWA case exists yet**, the data-center column is a forward-looking read-across
from the statutory hooks the energy cases turned on — analysis, not enforcement.

| CWA provision (U.S. Code) | What it prohibits / requires | Cases above | Data-center read-across (analytical) |
|---|---|---|---|
| **§301(a)** (33 U.S.C. §1311) | Master rule: no discharge of any pollutant from a point source except per permit | underlies every civil case | Any data-center point-source discharge to a water of the U.S. needs authorization |
| **§402 — NPDES** (33 U.S.C. §1342) | Permit; numeric effluent limits; includes industrial + construction **stormwater** | West Penn (boron), Arch (mine metals), coal-ash impoundments | **Cooling-water blowdown** (biocides, heat) and **construction/industrial stormwater** are the likeliest triggers |
| **§311** (33 U.S.C. §1321) | Oil/hazardous-substance **spill** liability; per-barrel penalties; gross-negligence multiplier; **SPCC** plans (§311(j)); duty to report | BP, Anadarko, ExxonMobil, Holly/Osage, Summit, Amplify, Enbridge, Sunoco, Magellan, SFPP, Plantation | **On-site diesel generator fuel farms & deliveries** — a fuel release reaching a creek is the *same* violation as the pipeline cases; SPCC already attaches to large fuel storage |
| **§309(c)** (33 U.S.C. §1319) | Criminal: (c)(1) negligent, (c)(2) knowing, (c)(4) false statements | Duke, Summit, Amplify (negligent pleas) | Criminal exposure needs no intent — **negligent operation/maintenance** of fuel or cooling systems suffices |
| **§404** (33 U.S.C. §1344) | Army Corps permit to dredge/fill wetlands & waters | jurisdictional backdrop (*Sackett*) | **Greenfield site grading** near wetlands — the classic large-construction CWA risk |
| **§401** (33 U.S.C. §1341) | State water-quality certification of federally permitted activity | jurisdictional backdrop | A state veto/condition point on §404 or NPDES authorizations for new builds |
| **§502(6)/§316** | Heat is a regulated "pollutant"; §316(b) cooling-water intake structures | power-plant thermal context (Duke) | Water-cooled hyperscale builds — and **co-located/behind-the-meter generation** — pull thermal-discharge & intake obligations |
| **§502(7) "waters of the U.S."** | Defines federal jurisdictional reach | *Sackett* (2023) narrowed it | Determines whether a given on-site wetland/stream is **federally** regulated at all |

### Recurring fact patterns that triggered enforcement
1. **Spills from stored/transported petroleum** (the dominant pattern). The violation is the *discharge event*.
2. **Exceeding numeric NPDES limits** in routine operational discharges (West Penn boron; Arch mine metals).
3. **Failure to maintain equipment / negligent operation** — elevated to *criminal* in Duke and Summit.
4. **Failure to report a spill promptly** — a separate criminal count (Summit).
5. **Gross negligence** as a penalty multiplier — the mechanism behind BP's record $5.5B.
6. **Construction/stormwater & sediment** during large land disturbance (the mining-site analog in Arch).

### Data-center exposure map
- **Cooling/process water (the §402 NPDES analog) — most relevant to this project.** Evaporative-cooling
  **blowdown** carries biocides, anti-scalants, and **heat** (a regulated pollutant); discharging to
  surface water (or some POTWs) implicates NPDES numeric limits — the *West Penn* pattern. This is the
  direct overlap with the water-use metrics the tracker scrapes.
- **Construction phase (highest near-term risk).** Hyperscale campuses disturb hundreds of acres;
  sediment-laden stormwater is the most-enforced CWA violation against large construction →
  **§402 Construction General Permit** + **§404/§401** if wetlands/streams are touched. (The *Arch* analog.)
- **Backup power & fuel storage (the §311 analog).** Large diesel generator fleets + on-site fuel farms =
  SPCC-regulated oil storage; a release reaching a water of the U.S. is legally identical to the pipeline
  cases — including negligence-criminal exposure, the gross-negligence multiplier, and the duty-to-report trap.
- **Co-located / behind-the-meter generation.** On-site gas turbines / fuel cells / co-located plants carry
  the **full** power-plant CWA profile — §316(b) intake, thermal discharge, combustion-residual wastewater
  (the *Duke* profile).

### The *Sackett* wrinkle
*Sackett* (2023) **shrank federal jurisdiction**, so some on-site wetlands/ephemeral streams a data
center fills may no longer require a federal §404 permit. But (1) **§402 (stormwater/discharge) and §311
(spills) don't depend on the wetland question** — they bite regardless; and (2) **many states retained
broader-than-federal water programs** (relevant for the project's VA/OH focus — both run their own
programs), so a "no federal jurisdiction" wetland can still be fully state-regulated. Net: *Sackett*
narrows the §404/§401 wetlands path, not the operational-discharge or spill paths that drove most cases.

## Potential CWA applications and evidence requirements

The table lists potential CWA applications and evidence sources. Scores are editorial
estimates for research planning, not predictions of enforcement or litigation outcomes.
**Impact** estimates the community/environmental harm that compliance could avert;
**Viability** estimates legal support after *Sackett* and *Maui*;
**Tractability** estimates evidence availability through ECHO DMR/SNC records, public permits,
and FOIA. Scores run from 1 to 5. The existing research order and scores are retained.
Applicability depends on the permit, jurisdiction, site facts, and statutory prerequisites.

| Priority | Theory (CWA hook) | Impact | Viab. | Tract. | Why it matters / how to source it | Dataset analog |
|---|---|:--:|:--:|:--:|---|---|
| **1** | **Citizen suit (§505, 33 U.S.C. §1365) against the *receiving* POTW** for ongoing NPDES violations / SNC while loaded by DC cooling blowdown | 5 | 5 | 5 | ECHO SNC/DMR records can help identify ongoing NPDES violations at a treatment plant receiving data-center cooling blowdown. A citizen suit requires the applicable notice, standing, and other statutory conditions. | Port of Morrow (WWTP receiving DC wastewater) |
| **2** | **Pretreatment / Industrial User (§307 + §403, 33 U.S.C. §1317/§1318)** — DC as a significant industrial user discharging blowdown to a POTW; local limits, slug control, IU permit, pass-through/interference | 5 | 5 | 4 | Data-center blowdown discharged to a municipal treatment plant may be subject to industrial-user permits and local pretreatment limits. Pass-through or interference can affect plant compliance and treatment costs. | Port of Morrow; industrial pretreatment consent decrees |
| **3** | **Construction stormwater (§402 CGP)** — sediment/erosion across multi-hundred-acre site clears | 4 | 5 | 4 | Construction runoff can carry sediment into nearby waters. Construction general-permit notices, inspection records, and notices of violation document applicable controls and compliance. | (Arch Coal mining-site analog) |
| **4** | **§402 cooling-tower blowdown direct to surface water** — thermal, chlorine, biocides, anti-scalants, conductivity | 4 | 5 | 4 | Direct discharges may be subject to numeric limits for heat, chlorine, biocides, or other constituents. Permits and discharge monitoring reports provide compliance evidence. | (West Penn Power) |
| **5** | **On-site package WWTP / greywater-recycle plant effluent (§402)** — large campuses building their own treatment/reuse plant | 4 | 4 | 4 | An on-site treatment or reuse plant may hold a separate NPDES permit. Its discharge monitoring reports can provide data distinct from the data-center building. | xAI Colossus greywater plant (Memphis) |
| **6** | **§404 wetlands dredge-and-fill + §401 state certification** for the campus footprint | 5 | 3 | 4 | Wetland fill can affect habitat and flood storage. Federal jurisdiction depends on Sackett; applicable state wetland programs and certification requirements also need review. Permit applications are public. | New Carlisle IN; Project Raspberry/Loch VA; Port of Little Rock AR |
| **7** | **§316(a) thermal variance + §316(b) cooling-water intake** — surface-water-sourced cooling or co-located/behind-the-meter generation | 4 | 4 | 3 | Thermal discharges and cooling-water intakes may trigger separate requirements. Applicability depends on the cooling system, intake, discharge, and any associated generating plant. | Greenidge Generation NY (§316 thermal/intake) |
| **8** | **Antidegradation / Tier 2 review (§303(d)/state WQS)** of a new or expanded discharge into high-quality waters | 4 | 4 | 3 | State antidegradation rules may require alternatives analysis before a new or expanded discharge into high-quality waters is permitted. Review requirements vary by state and receiving water. | — |
| **9** | **County of Maui "functional equivalent" (§402)** — cooling discharge, injection well, or land application that reaches surface water *via groundwater* | 4 | 3 | 2 | A discharge reaching surface water through groundwater may require a permit under the County of Maui functional-equivalent test. Applicability depends on site-specific transport and hydrologic evidence. | (*County of Maui v. HWF*, 2020) |
| **10** | **PFAS in discharge (§402)** — AFFF fire-suppression systems + cooling-chemistry additives, as NPDES PFAS limits tighten | 4 | 3 | 2 | PFAS monitoring and discharge limits depend on the permit and applicable rules. Potential sources include fire-suppression systems and cooling additives; effluent data are needed to assess a particular facility. | (industrial PFAS cases) |
| **11** | **§311 SPCC / oil spill (33 U.S.C. §1321)** — large backup-diesel fuel farms; release to a water of the U.S.; missing SPCC/FRP | 3 | 5 | 3 | An oil release from backup-fuel storage reaching covered waters may trigger Section 311 liability and reporting duties. Applicability depends on the release and facility circumstances. | (BP/Enbridge/Summit §311 line) |
| **12** | **Industrial stormwater (§402 MSGP)** — exposed equipment yards, chemical/fuel storage areas | 3 | 4 | 3 | Exposed equipment yards and chemical or fuel storage may require industrial stormwater coverage. Permit coverage and benchmark monitoring records document applicable requirements. | — |

**Evidence sources:** receiving-treatment-plant DMR/SNC records and industrial-user permits
can document discharge and pretreatment compliance. A *Maui* analysis requires additional
site-specific transport evidence. Wetland and cooling-intake applications require the relevant
permit and project records. A recorded exceedance or SNC flag does not by itself establish
that every prerequisite for a citizen suit is satisfied.

## Primary sources
- DOJ ENRD — Deepwater Horizon (BP, Anadarko): <https://www.justice.gov/enrd/deepwater-horizon>
- DOJ — Duke Energy: <https://www.justice.gov/archives/opa/pr/duke-energy-subsidiaries-plead-guilty-and-sentenced-pay-102-million-clean-water-act-crimes>
- DOJ — Summit Midstream: <https://www.justice.gov/opa/pr/pipeline-company-sentenced-largest-ever-inland-oil-spill>
- DOJ — Amplify Energy: <https://www.justice.gov/usao-cdca/pr/three-companies-agree-plead-guilty-federal-offense-and-pay-nearly-13-million-federal>
- DOJ — Magellan (2017): <https://www.justice.gov/archives/opa/pr/magellan-pipeline-settles-alleged-clean-water-act-violations-related-spills-texas-nebraska>
- EPA — ExxonMobil Mayflower: <https://www.epa.gov/enforcement/exxonmobil-mayflower-clean-water-settlement>
- EPA — Enbridge: <https://www.epa.gov/enforcement/enbridge-clean-water-act-settlement>
- EPA — Sunoco: <https://www.epa.gov/enforcement/sunoco-pipeline-lp-clean-water-act-settlement>
- EPA — Arch Coal/ICG: <https://www.epa.gov/wv/action-resolves-hundreds-coal-companies-violations>
- EPA — West Penn Power: <https://www.epa.gov/newsreleases/west-penn-power-pay-610000-penalty-federal-state-settlement-over-discharge-violations>
- EPA — Holly/Osage: <https://www.epa.gov/newsreleases/oil-companies-pay-74-million-civil-penalties-resolve-us-claims-pipeline-spill-allotted>
- EPA — SFPP (CWA-09-2025-0109): <https://www.epa.gov/ca/CWA-09-2025-0109>
- EPA — Plantation Pipe Line: <https://www.epa.gov/enforcement/plantation-pipe-line-company-clean-water-act-settlement>
- CRS — Sackett / WOTUS (LSB10981): <https://crsreports.congress.gov/product/pdf/LSB/LSB10981>
- CRS — data centers & federal permitting (R48762): <https://www.congress.gov/crs-product/R48762>
- Supreme Court — *County of Maui v. Hawaii Wildlife Fund* (2020, "functional equivalent"): <https://www.supremecourt.gov/opinions/19pdf/18-260_i4dk.pdf>
- EPA — National Pretreatment Program (§307/§403, industrial users & POTWs): <https://www.epa.gov/npdes/national-pretreatment-program>
- EPA — CWA §505 citizen suits (statute, 33 U.S.C. §1365): <https://www.epa.gov/enforcement/clean-water-act-cwa-and-federal-facilities>
