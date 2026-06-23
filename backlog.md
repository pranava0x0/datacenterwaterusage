# Backlog

Items are ordered by priority (high / medium / low). Each includes a sample prompt for generating an implementation plan.

Last reviewed: 2026-05-28 (External Tracker Survey added — see section below the Low Priority list).

---

## Completed (March 2026)

### ✅ CWA Enforcement Reference + Data-Center Read-Across (June 2026)
**Status**: Added — `docs/cwa-enforcement-and-data-centers.md`. Primary-sourced (EPA/DOJ/CRS) catalog of energy/utility Clean Water Act enforcement (2015→present) mapped to data-center water/discharge exposure (§402 NPDES cooling-water blowdown, §311 on-site fuel storage, §404/§401 construction, *Sackett* jurisdiction). No data-center CWA case exists yet — the read-across is forward-looking. (Relocated from the FERC Audit Explorer project, where it was filed by mistake.)
**Follow-ups**: (1) monitor EPA ECHO by NAICS **518210** (data processing/hosting) to flag the first data-center CWA action automatically — extends `scrapers/epa_echo_naics.py`; (2) verify the 4 unconfirmed leads (Energy Transfer, ATP Infrastructure, Trans Energy, Xplor) against primary `.gov` pages; (3) optional all-sectors CWA sweep beyond energy/utility.

### ✅ Company Water Claims Panel (May 2026)
**Status**: Built — `data/reference/company_water_claims.json` (29 water-themed claims across 13 data-center operators, mirrored from `pranava0x0/datacentercommunitybenefits`) + `render_company_water_claims()` panel. Each claim is a verbatim first-party quote with source link; 5 have independent delivered-vs-promised assessments (Partial/Contested/etc.) with their own assessment source. 8 tests.
**Follow-ups**: scheduled refresh script that pulls the latest `docs/data/claims.json` from the sibling repo and re-filters theme=water (today the snapshot is manual). Optional: surface non-water themes (energy, infrastructure) the same way.

### ✅ National Data Center Water Legislation Tracker (May 2026)
**Status**: Built — `data/reference/legislation.json` (now **38** state + federal + local/regulatory entries) + `render_legislation_tracker()` dashboard panel (sorted by status, flags verified vs. unconfirmed entries). 10 tests in test_dashboard.py. VA HB 496/SB 553 and MN HF 16 confirmed enacted; remaining entries flagged "Unconfirmed" pending primary-source verification.
**June 2026 expansion (31 → 38)**: added the four 2026 state laws with newly *enacted* data-center water provisions — Idaho H 895 (closed-loop/non-consumptive cooling mandate, eff. July 1 2026), South Dakota SB 135 ("Data Center Bill of Rights," ≥10 MW cost-causation + water-supply compatibility), Utah HB 76 (Water Transparency Amendments; projected + actual water disclosure, 10,000-sq-ft threshold), West Virginia HB 4983 (Dept.-of-Commerce certification rule where binding water-protection amendments were rejected) — plus Maryland HB 270/SB 116 (veto-overridden impact study), failed Washington HB 2515 and Indiana SB 79, and upgraded the federal Durbin entry to its confirmed number **S. 4213**.
**Follow-ups**: confirm the remaining unconfirmed bill statuses against legislature records; add a scheduled re-verification monitor; optional US choropleth map. **Candidates to verify + add next pass** (surfaced June 2026, not yet primary-verified): Florida hyperscale data-center regulatory framework (proposed, per Holland & Knight Feb 2026 — get the bill number); Iowa HF 2261 (separate water-utility customer class for ≥20 MW loads); Virginia SB 417 (conditions Cloud Computing Cluster grant eligibility on reclaimed-water cooling; did not advance, 2027 carryover); Indiana HB 1043 (data-center water regulation — confirm contents/status).

### ✅ EPA ECHO NAICS Facility Discovery (Federal)
**Status**: Built — `scrapers/epa_echo_naics.py` (18 tests)

### ✅ Ohio EPA Data Center General Permit Tracker (OHD000001)
**Status**: Built — `scrapers/ohio/epa_general_permit.py` (20 tests)

### ✅ Loudoun Water ACFR Scraper (Virginia)
**Status**: Built — `scrapers/virginia/loudoun_acfr.py` (26 tests)

### ✅ Expand EPA ECHO DMR Target Permits
**Status**: Done — 8 target permits in config.py (VA0091383, VA0024988, VA0026301, VA0026271, OH0024651, OH0028061, OH0020494, OH0068071)

### ✅ Dashboard / Visualization (Phase 1)
**Status**: Built — `dashboard.py` Streamlit dashboard with flow time series, permit limit overlays, seasonal heatmap, cross-filtering, data download (20 tests). Run with `streamlit run dashboard.py`.

### ✅ Fairfax Water Financial Reports (Virginia)
**Status**: Built — `scrapers/virginia/fairfax_water.py` (tests in test_fairfax_water.py). Downloads ACFR/PAFR PDFs, extracts wholesale delivery volumes.

### ✅ Central Ohio Regional Water Study Analysis
**Status**: Built — `scrapers/federal/central_ohio_water_study.py`. Downloads and processes the 3 study PDFs.

### ✅ Ohio EPA ArcGIS NPDES Permits
**Status**: Built — `scrapers/ohio/epa_npdes_arcgis.py` (tests in test_ohio_epa_npdes.py). Queries Ohio EPA Open Data for NPDES permits by SIC 7374.

### ✅ ODNR Water Withdrawal Facility Viewer (Ohio)
**Status**: Built — `scrapers/ohio/odnr_water_withdrawal.py` (tests in test_odnr_water_withdrawal.py). Queries ArcGIS FeatureServer for withdrawal registrations in central Ohio counties.

### ✅ Prince William Water Industrial User Survey (Virginia)
**Status**: Built — `scrapers/virginia/pwc_ius.py` (tests in test_pwc_ius.py). Downloads IUS PDFs, extracts ERU allocations, GPD/MGD values, data center counts. ERU→GPD conversion (1 ERU = 400 GPD).

### ✅ Virginia DEQ Water Withdrawal Permits (VWP)
**Status**: Built — `scrapers/virginia/deq_vwp.py` (tests in test_deq_vwp.py). Queries ArcGIS EDMA MapServer layers 192 (individual) and 193 (general) for water withdrawal permits in Northern Virginia counties.

### ✅ Dashboard Panel 2: Local Context Card
**Status**: Built — `dashboard.py` renders "How does this compare?" cards for Loudoun (1.6B gal, ~22K homes equivalent, 15% of utility), PWC (56 DCs, 478M gal), and Central Ohio projections (40-90 MGD). 6 tests.

### ✅ Dashboard Panel 4: Per-Query Debate Explainer
**Status**: Built — `dashboard.py` static explainer card showing 0.26-519 mL range with four variance factors. 5 tests.

### ✅ Mobile Dashboard Improvements
**Status**: Built — Plotly theme=None fix for mobile stretching bug, touch-friendly CSS (44px min buttons), mobile download button, data freshness indicator, responsive context/explainer card styling. 6 tests.

### ✅ Dashboard Panel 3: Transparency Scorecard
**Status**: Built — `dashboard.py` renders a table of all 11 data sources rated by disclosure type (mandated/voluntary/inferred), geographic resolution, update frequency, and confidence. Lists 4 known transparency gaps (NDAs, SB 553, AB 93, federal gap). 8 tests.

### ✅ Dashboard Panel 5: Timeline of Disclosure Events
**Status**: Built — `dashboard.py` renders chronological timeline of 9 key events (2020-2026) across policy, data, research, and legal categories. Color-coded badges, responsive. 7 tests.

### ✅ Deduplication Engine
**Status**: Built — `utils/dedup.py` with 3-pass strategy: exact URL, permit+month, fuzzy title. Merges cross-source duplicates, picks most complete record, adds `sources` column. 15 tests.

---

## High Priority

### Dashboard Panel 1: The Two Water Footprints (highest impact, moderate effort)
Side-by-side view: direct on-site cooling water vs. indirect thermoelectric water from electricity generation. Sources: EPA ECHO DMR (already scraped) + EIA Form 923 (backlog). Headline framing: "80% of a data center's water footprint never touches the data center building."

**Sample prompt:**
> Add a "Two Footprints" panel to the Streamlit dashboard that shows, for each target WWTP permit, (1) the direct measured flow from EPA ECHO DMR, and (2) an estimated indirect thermoelectric water footprint calculated from the facility's electricity demand using EIA Form 923 state-level water intensity factors. Show as a stacked bar chart with a plain-English explainer of the methodology and a link to the EIA data source.

---

### EPA FRS Cross-Reference Module (Federal)
The EPA Facility Registry Service links facilities across 90+ EPA databases. Query FRS for all NAICS 518210 facilities in VA/OH to get FRS Registry IDs, then cross-reference against NPDES, RCRA, TRI, and other programs. API: `https://enviro.epa.gov/enviro/efservice/FRS_NAICS/NAICS_CODE/518210/rows/0:99/JSON`

**Data status:** Confirmed. FRS REST API is documented and available (exchangenetwork.net). The ER_NAICS dataset is also available as an Esri REST API endpoint on data.gov (`catalog.data.gov/dataset/epa-facility-registry-service-frs-er_naics7`). NAICS codes in FRS are represented as first 3 digits (i.e., query `518`), not full 6-digit code.

**Sample prompt:**
> Build a utility module `utils/frs_lookup.py` that queries the EPA Envirofacts REST API for facilities by NAICS code and state. For each facility, retrieve the FRS Registry ID, geographic coordinates, and linked program IDs (NPDES, RCRA, TRI, CAA). Use this to build a mapping of data center facilities to their regulatory footprints across EPA databases. Integrate with the existing scraper pipeline to auto-discover which WWTP service areas data center facilities fall within.

### Virginia DC Water Reporting Scraper (HB 496 / SB 553 — ENACTED 2026)
Virginia **enacted** data center water reporting in the 2026 session. HB 496 (signed by Gov. Spanberger) amends Code § 62.1-44.38 to require water utilities to report the total monthly volume of water provided to data centers, including reclaimed water; SB 553 was the Senate companion, reconciled with the House version in conference. This converts a hypothetical into a new **mandatory** reporting data source — the highest-value scrape target to come online since EPA ECHO DMR.

**URLs:** `https://lis.virginia.gov/bill-details/20261/SB553` · `https://legiscan.com/VA/bill/SB553/2026`

**Data status:** ENACTED 2026 (confirmed via B&D Law and Virginia Mercury 2026 session recaps). Effective ~July 1, 2026 (standard for VA regular-session bills). The conference reconciled a Senate version (report aggregate volumes to the State Water Control Board / DEQ) with a House version (water-use disclosure during local zoning), so **verify the exact reporting channel and first-report date before building** — reports may land at DEQ/SWCB, in a new portal, or in local rezoning filings. First monthly reports will follow once the mechanism is established.

**Sample prompt:**
> Virginia HB 496 / SB 553 (2026) now requires water utilities to report monthly data center water volumes. First, investigate where these reports are published (State Water Control Board, DEQ portal, or local zoning records). Until the first reports appear, build a lightweight status monitor (LegiScan API / Virginia LIS) that watches for the reporting portal going live and the first data drop. Then build a scraper for the reports following the BaseScraper pattern, map the new fields to DocumentRecord, and integrate with the dedup pipeline. Add the source to the dashboard Transparency Scorecard once data is flowing.

### Per-Query Reality-Check Panel (Andy Masley framing)
Extend the existing Per-Query Explainer (`render_per_query_explainer`) with Andy Masley's plain-English comparisons, which anchor the "skeptic" pole of the debate: an individual AI query's water use is trivial (~2 mL including electricity). The point isn't that AI water doesn't matter — it's *why this tracker measures facilities and aggregates, not chatbots*.

**Source:** Andy Masley, "The AI water issue is fake" (`blog.andymasley.com/p/the-ai-water-issue-is-fake`) and "How thirsty is AI?" (`andymasley.com/visuals/water`).

**Content to surface (verified figures only):**
- "X prompts = the same water as ___" table (using ~2 mL/prompt): warm bath ≈ 5,000 prompts; kettle ≈ 125; one sheet of paper ≈ 2,550; a 400-page book ≈ 1,000,000; a pair of jeans ≈ 5,400,000. One American's daily water footprint ≈ 800,000 prompts.
- "The 500 mL bottle myth" callout: the viral per-email/per-prompt figure was inflated ~50–250×; the underlying study meant ~500 mL per 20–50 prompts.
- Use ONLY his verified figures — the "microwave/hamburger" framings circulating online are not in his posts; his real energy analogy is a space heater.

**Sample prompt:**
> Extend `render_per_query_explainer` in dashboard.py with a "reality check" sub-panel: a table of "X prompts = same water as [everyday activity]" using Andy Masley's ~2 mL/prompt comparisons, plus a callout debunking the "500 mL bottle per prompt" claim (inflated 50–250×). Add a one-line bridge: "Per query is trivial — that's why we track facilities and utilities, where the aggregate impact is real and measurable." Cite Masley's posts and add tests asserting the comparison data renders and matches the sourced values.

### Narrative Balance: Skeptic vs. Critic Poles (landing framing)
The public debate has two poles, and the dashboard's data is the tiebreaker between them:
- **Andy Masley (skeptic):** a single AI query's water is negligible; the panic conflates per-query with aggregate.
- **Karen Hao, *Empire of AI* (critic):** the aggregate, local footprint is large and deliberately hidden ("a data center can use as much water as a town").
- **This tracker:** measures exactly the aggregate/facility number (WWTP DMR flows, utility sales) that settles the argument — per-query is tiny, but one facility ≈ a town's worth of water.

This "both numbers are true" spine could anchor the Phase 2 landing page / scrollytelling intro.

**Sample prompt:**
> Design a short "Why this tracker exists" intro section (Streamlit panel now, scrollytelling hero in Phase 2) that frames the two poles of the AI-water debate — Masley (per-query is trivial) vs. Hao (aggregate/local is severe and hidden) — and positions the tracker's facility-level data as the arbiter. Pull one verified figure from each side, link to sources, keep it neutral, and let the data adjudicate.

---

## Medium Priority

### JLARC Data Centers in Virginia Report
The December 2024 JLARC study found data center water use is sustainable but growing. Contains aggregate statistics, policy recommendations, and analysis of water impact. Reference material.

**URL:** `https://jlarc.virginia.gov/landing-2024-data-centers-in-virginia.asp`

**Data status:** Confirmed. Full report PDF available at `https://jlarc.virginia.gov/pdfs/reports/Rpt598-2.pdf`. Key water finding: "data center water use is currently sustainable, but use is growing and could be better managed." Recommends expressly authorizing localities to require water use estimates for proposed data center developments. Also covers energy (5 GW current demand, doubling in 15 years), economic impact ($9.1B GDP, 74K jobs), and sound/noise issues.

**Sample prompt:**
> Download the JLARC Data Centers in Virginia report and extract key findings: aggregate water consumption figures, growth projections, policy recommendations for local governments. Parse relevant tables and statistics. Store as reference data to provide context alongside scraped permit/DMR data.

### Fairfax County Data Centers Report
Fairfax County published a data centers report that includes water impact analysis.

**URL:** `https://www.fairfaxcounty.gov/planning-development/sites/planning-development/files/Assets/Documents/PDF/data-centers-report.pdf`

**Data status:** Not verified — URL not confirmed accessible. Attempt download before building a scraper.

**Sample prompt:**
> Download the Fairfax County data centers report PDF. Extract water usage estimates, zoning analysis, and infrastructure impact assessments. Useful as context for understanding data center water demand in the broader Northern Virginia region beyond Loudoun County.

### EIA Thermoelectric Cooling Water Data (Federal)
EIA Form 923 reports plant-level water withdrawal and consumption at power plants. While EIA doesn't track data centers directly, data centers drive ~4% of national electricity demand (projected 6.7-12% by 2028). Power plant cooling water data enables indirect water footprint calculations.

**URL:** `https://www.eia.gov/electricity/data/water/`

**Data status:** Confirmed. Final 2024 data was released September 18, 2025 and is downloadable from eia.gov. Covers all U.S. states (filter by VA or OH). Data includes generator type, fuel consumption, water consumption, cooling type, equipment status, and water source per plant. Next release (2025 early data) planned June 2026. Also available via data.gov and DOE OEDI.

**Sample prompt:**
> Build a module `extractors/eia_water.py` that downloads EIA thermoelectric cooling water spreadsheets (Form 923 data). Parse plant-level water withdrawal and consumption volumes for power plants in Virginia (PJM region) and Ohio. Cross-reference with data center electricity demand estimates to calculate the indirect water footprint (water used to generate electricity consumed by data centers). Store alongside direct water use data for a complete water footprint model.

### OCR for Scanned PDFs
Some government PDFs are scanned images with no text layer. pdfplumber and PyMuPDF return empty text for these.

**Sample prompt:**
> Add OCR support to the PDF extraction pipeline using pytesseract. When both pdfplumber and PyMuPDF return empty/minimal text from a PDF, fall back to OCR. Include preprocessing (deskewing, thresholding) for better accuracy on scanned government documents. Update requirements.txt and add tests with a sample scanned PDF.

### Dashboard / Visualization — Phase 2: Observable Framework
Phase 1 Streamlit dashboard is built (see `dashboard.py`). Phase 2 migrates the public-facing version to Observable Framework for static deployment, better data storytelling, and a scrollytelling landing page.

**UX research findings (March 2026):**
- California Drinking Water Tool: two-portal design (community vs. policy audience), GIS overlays with demographic data
- PJM LMP Map: contour heat map with 5-minute auto-refresh, brushable time selection
- EPA ECHO: Qlik-based cross-filtering, effluent charts with permit limit overlays
- WoodMac Lens: screen-on-map-then-benchmark workflow, scenario modeling
- Recommended tech: Observable Framework (static site, D3.js/deck.gl, pre-computed data from Python pipeline)

**Sample prompt:**
> Migrate the Streamlit dashboard to Observable Framework with a scrollytelling landing page (3-4 key findings with human-relatable comparisons like "equivalent to X households"), an interactive explorer with Leaflet map and cross-filtering, and facility detail pages with effluent-chart-style time series. Deploy as a static site on GitHub Pages. Use D3.js/Observable Plot for charts and deck.gl for the map.

### Global Context Panel: "One Facility = A Town" (Karen Hao)
A panel that benchmarks VA/OH facilities against well-documented global cases, giving readers scale and showing Data Center Alley is one node in a worldwide pattern.

**Source:** Karen Hao, *Empire of AI* (2025) and "AI Is Taking Water From the Desert," The Atlantic (Mar 2024). Use her **corrected** figures — she publicly revised the Chile number in Dec 2025 (`karendhao.com/20251217/empire-water-changes`).

**Content to surface (verified):**
- Goodyear/Phoenix, AZ (Microsoft): ~56M gal/yr ≈ ~670 families, during a record drought.
- Cerrillos, Chile (Google): permitted ~5.33B L/yr ≈ roughly the annual use of the town's ~88,000 residents (≈1.05×, NOT the "1,000×" that circulated).
- Set beside Loudoun (1.6B gal/yr ≈ ~22K homes) and PWC (478M gal, 56 DCs).
- Optional extraction map: Atacama (lithium/copper) → Arizona → Uruguay → Northern Virginia.

**Sample prompt:**
> Add a "Global Context" panel to the dashboard that places tracked VA/OH facility/utility numbers beside documented global cases (Goodyear AZ ~56M gal/yr ≈ 670 families; Chile Cerrillos ~5.33B L/yr ≈ a town of 88,000). Use Karen Hao's corrected figures, cite sources, and include her Dec 2025 correction as a note. Render relatable "≈ N households/town" equivalents consistent with the existing Local Context cards. Add tests for the comparison data.

---

## Low Priority

### USGS Water Use Data Integration (Federal)
USGS publishes county-level water use estimates every 5 years (latest: 2020). Too coarse for individual facility tracking but useful for regional trend analysis. The USWWD (United States Water Withdrawals Database) on CUAHSI HydroShare has facility-level data compiled from state reports (188,857 unique facilities).

**URLs:**
- NWIS: `https://waterdata.usgs.gov/nwis/wu`
- USWWD: `https://www.hydroshare.org/resource/11c91bde19864106a9e85b39ffcf0ff1/`
- New API: `https://api.waterdata.usgs.gov/`

**Data status:** Available but dated. Latest county-level data is 2020 (published every 5 years; next update expected 2025–2026). Coarse for individual facility tracking but useful for regional trend context.

**Sample prompt:**
> Build a module `extractors/usgs_water.py` that downloads USGS county-level water use estimates for Virginia and Ohio counties with data center clusters (Loudoun, Fairfax, Prince William, Franklin, Licking, Delaware). Parse the self-supplied industrial and public supply categories. Also check whether the USWWD HydroShare dataset includes facility-level records for Virginia and Ohio. Store as reference data for regional trend context.

### Email/Slack Notifications for New Documents
Alert when new documents are found on re-scrapes.

**Sample prompt:**
> Add a notification system that compares new scrape results against previous results and sends an alert (email via SMTP or Slack webhook) when new documents are found. Include the document title, source URL, and any extracted water metrics in the notification. Make the notification channel configurable in config.py.

### Scheduled Scraping via Cron/Airflow
Automate periodic re-scraping.

**Sample prompt:**
> Set up scheduled scraping using either cron jobs or Apache Airflow. Create a schedule that re-runs all scrapers weekly, with EPA ECHO DMR scraper running monthly (aligned with DMR reporting periods). Include error alerting if a scheduled run fails.

### Additional States (Option E)
Expand beyond Virginia and Ohio to other data center hub states. Texas, Oregon, and Georgia are the next biggest data center markets. Lower priority since the VA/OH pipeline isn't fully exploited yet, but this is the path to a national-scale dataset.

### CWA "watch list" — pre-enforcement data-center water permits (June 2026 research surfaced)
The June 2026 research pass found data-center water matters that are real and document-numbered but NOT yet enforcement actions, so they were deliberately kept out of `cwa_investigations.json` (which is an enforcement/legal tracker). Re-check these periodically; promote to a case if a violation, NOV, or suit attaches:
- **Oracle/OpenAI "Stargate" — Saline Township, Washtenaw County, MI.** Michigan EGLE wetlands permit WRP047686 (~9.12 ac wetland + temporary Saline River tributary impact) with a named cooling-water outfall to the Saline River (discharge may contain glycol); EGLE issued an Oct 17, 2025 pre-permit construction "waiver." Air permit issued Jan 13, 2026; wetlands permit Jan 16, 2026. Active suits are land-use/Open-Meetings, not water-pollution. (Sources: planetdetroit.org Feb 2026; fortune.com May 2026.)

**Sample prompt:**
> Re-verify the Saline Township MI Oracle/OpenAI data center water status: has Michigan EGLE issued any NOV or water-quality enforcement tied to permit WRP047686 or the Saline River glycol outfall since Jan 2026? If yes, add it to `data/reference/cwa_investigations.json` (category `datacenter` if EGLE cites a discharge violation, else `adjacent`) with verified sources and a regression test pinning the case_id.

**Target states and agencies:**
- Texas: TCEQ permits, TCEQ ArcGIS data, PUC water availability studies
- Oregon: DEQ permits, Portland Water Bureau data
- Georgia: EPD permits, Atlanta watershed data

**Sample prompt:**
> Research and add scrapers for data center water usage documents in Texas (TCEQ permits), Oregon (DEQ), and Georgia (EPD). Follow the same architecture as existing scrapers — identify the relevant portals, determine the technology stack, and implement using the BaseScraper pattern. Start with Texas TCEQ which has the most accessible ArcGIS-based permit data.

### FOIA Request Templates (Option F)
Create template FOIA requests targeting local water utilities for facility-level data center water consumption records. This is the most direct path to facility-specific data, especially given the Botetourt County court ruling (2024) where a judge ruled water usage data is NOT proprietary.

**Key targets:**
- Loudoun Water — facility-level commercial/industrial water delivery records (highest priority — they sell ~1.6B gal/yr to data centers but only publish aggregate figures)
- Prince William Water — same approach, 56 data centers in the county
- Western Virginia Water Authority — Google data center water contract records (citing the Botetourt County court precedent)
- Fairfax Water — wholesale supply data to Loudoun Water (indirect metric)

**Legal context:**
- Virginia FOIA (Section 2.2-3700) requires disclosure unless exempt
- 25 of 31 Virginia localities with data centers have signed NDAs — FOIA can challenge these
- Botetourt County precedent (2024): water usage data is public record, NOT proprietary trade secret

**Sample prompt:**
> Create a `docs/foia_templates/` directory with template FOIA request letters for: (1) Loudoun Water — facility-level commercial/industrial water delivery records, (2) Prince William Water — same, (3) Western Virginia Water Authority — Google data center water contract records (citing the Botetourt County court precedent). Include guidance on Virginia FOIA law (Section 2.2-3700) and how to counter proprietary information exemption claims. Include sample follow-up templates if initial request is denied.

### Map View — Facility Locations (Low)
Add a Plotly scatter_mapbox or deck.gl map showing data center and WWTP facility locations from ArcGIS scraper data. Map-first designs (Visual Capitalist, RS Metrics) are more intuitive on mobile than table-first. Use existing geocoded permit data.

**Sample prompt:**
> Add a map tab/section to the dashboard using Plotly scatter_mapbox (or st.map for simplicity). Plot all scraped facility locations from ArcGIS data with color-coding by state and size by flow volume. On mobile, show map as the first view; on desktop, show alongside the flow chart. Clicking a facility should filter the dashboard to that location.

### Streamlit Top Navigation for Multi-Panel Dashboard (Low)
As the dashboard grows (context, scorecard, timeline panels), use `st.navigation(position="top")` (new in Streamlit 2025) to replace sidebar page navigation. More mobile-friendly than slide-out panels.

**Sample prompt:**
> Refactor the dashboard to use `st.navigation(position="top")` for multi-page layout: "Overview" (current flow chart + metrics), "Context" (local context cards + per-query explainer), "Scorecard" (transparency), "Timeline" (disclosure events). Each page loads only its own content. Mobile users get top tabs instead of hidden sidebar.

### Transparency Quote Cards & Data-Integrity Examples (Karen Hao)
Small cards that reinforce *why* the project relies on ECHO DMR / ACFR / FOIA workarounds — and model good data hygiene.

**Source:** Karen Hao — The Open Notebook interview (May 2024); her Dec 2025 self-correction.

**Content:**
- Quote on buried data: Arizona's numbers surfaced only in city-council meeting footnotes after redacted FOIAs; "people within Microsoft don't even really know" because usage isn't fully tracked internally.
- Feature her published correction as a model: show how a key figure was revised (Chile "1,000×" → ~1.05×), reinforcing the Transparency Scorecard's confidence ratings.

**Sample prompt:**
> Add a "Why the workarounds?" callout to the Transparency Scorecard panel with 1–2 sourced quotes from Karen Hao on company stonewalling and buried data, plus a short "data-integrity" note showcasing her public correction of the Chile figure as a model for how this project flags uncertainty. Cite sources, keep it to a compact card, and add a test for the static content.

---

## External Tracker Survey (May 2026)

Survey of ~50 existing water-use trackers, datasets, and methodologies across academic, journalistic, NGO, open-source, industry, and government sources. Each item below is a candidate idea for this project; full inventory with URLs preserved in the agent research transcript. Ordered by actionable priority for incorporation.

### Top 10 actionable picks

#### 1. WRI Aqueduct 4.0 water-stress overlay (HIGH)
Add WRI Aqueduct as a base map layer behind facility markers. 13 baseline indicators + 2030/2050/2080 projections at HUC level; open data; peer-reviewed; free. Matches the layer pattern Bloomberg used in "The AI Boom Is Draining Water" (June 2025) and Ceres "Drained by Data."

**URLs:** `https://www.wri.org/aqueduct` · `https://www.wri.org/data/aqueduct-global-maps-40-data` · `https://github.com/wri/Aqueduct40`

**Sample prompt:**
> Add a WRI Aqueduct 4.0 water-stress choropleth as a base layer on the facility map in `dashboard.py`. Pull the HUC-12 (or country-level fallback) baseline-water-stress GeoTIFF from Aqueduct40 GitHub, render with Folium or st_pydeck, and overlay current facility markers sized by reported gpd. Cite WRI and add a short methodology note. Tests should verify the layer loads and color scale matches Aqueduct's published bins.

#### 2. EIA Form 923 Schedule 8D scraper for indirect water (HIGH)
Already flagged in Medium Priority but not built. Plant-level monthly water withdrawal/consumption/discharge at every U.S. thermoelectric plant. Combined with electricity-supplier mapping, lets us compute Scope 2 ("indirect") water for each tracked data center. Marston (Virginia Tech) found 75-90% of DC water footprint is indirect.

**URL:** `https://www.eia.gov/electricity/data/water/`

**Sample prompt:**
> Build `scrapers/federal/eia_form_923.py` following BaseScraper pattern. Download the annual EIA-923 cooling water Excel (Schedule 8D), parse the per-plant monthly withdrawal/consumption rows, store records keyed by EIA plant ID + month. Then add `extractors/indirect_water.py` that takes a facility's annual MWh consumption and its grid region (PJM RTO / MISO / etc.) and returns an indirect-water estimate using Marston's published EWIF tables. Surface as a second bar next to direct DMR flow on the dashboard.

#### 3. FracTracker open data center CSV ingest (HIGH)
FracTracker publishes 1,400+ U.S. data center sites with coordinates, MW, square footage, acreage, **cooling type/method**, EJ overlays, tribal-lands proximity, and chronic-disease overlays. CSV is freely downloadable. Cooling type is the single most-needed missing field in our records.

**URL:** `https://www.fractracker.org/data-centers/`

**Sample prompt:**
> Build `scrapers/federal/fractracker_data_centers.py` that pulls the FracTracker CSV/GeoJSON, normalizes to DocumentRecord (or a new ReferenceFacility record), and joins to our existing scraped records by name+county+state. Specifically pull through the `cooling_method` field — it's the field we most need and is absent from EPA ECHO and ODNR. Add to the dashboard's facility table.

#### 4. EPA FRS Registry ID cross-link utility (HIGH)
Already on backlog; this restates the priority. FRS gives every facility a stable `registryId` joining ECHO, TRI, SDWIS, RCRA, and air databases. Without it, cross-source dedup is brittle name-matching.

**URL:** `https://www.epa.gov/frs/facility-registry-service-frs-api`

**Sample prompt:**
> Build `utils/frs_lookup.py` (already in backlog as "EPA FRS Cross-Reference Module"). Replace manual name-based cross-source joins in `utils/dedup.py` with FRS registryId joins where available. Add a `frs_registry_id` field to DocumentRecord. Tests should verify joining a known data center across ECHO + TRI returns one merged record.

#### 5. PJM 2026 Load Forecast large-load disclosure scraper (HIGH)
PJM's 2026 Load Report (per its new transparency rule) discloses individual large loads ≥50 MW. This pierces some of the NDA secrecy our Transparency Scorecard flags, especially for Virginia (PJM territory).

**URL:** `https://www.pjm.com/-/media/DotCom/library/reports-notices/load-forecast/2026-load-report.pdf`

**Sample prompt:**
> Build `scrapers/federal/pjm_large_loads.py` that downloads the annual PJM Load Forecast Report PDF, extracts the new large-load disclosure tables (data center loads ≥50 MW by zone), and stores per-zone projected MW. Cross-reference with EPA ECHO permit locations to map disclosed load to identified facilities. Surface on the dashboard as "Disclosed large-load (PJM)" alongside our other sources.

#### 6. NOAA Drought Monitor overlay (HIGH)
Per-facility drought-condition badge (D0–D4). Strong contextual framing: "Facility X is operating in D2 (severe drought) as of [date]." Matches Bloomberg / Bay Journal coverage style.

**URL:** `https://www.drought.gov/data-download`

**Sample prompt:**
> Build `extractors/drought_status.py` that pulls the current week's U.S. Drought Monitor GeoTIFF/JSON, samples drought level at each facility's coordinates, and stores a D0–D4 badge in the facility record. Add a small badge to each facility card on the dashboard. Refresh weekly.

#### 7. AI prompts → liters calculator widget (HIGH)
Building on existing Per-Query Explainer + the planned Andy Masley reality-check. Add an interactive slider widget: "Enter queries per day [1 → 1,000,000] → estimated liters of water." Use Shaolei Ren's coefficients (UC Riverside) as defaults, with selectable model from ML.energy leaderboard.

**URLs:** `https://arxiv.org/pdf/2304.03271` (Ren) · `https://ml.energy/leaderboard` (per-model energy)

**Sample prompt:**
> Add `pages/ai_calculator.py` Streamlit page with a slider for queries/day, a model dropdown sourced from ML.energy leaderboard values, and a region selector. Output the estimated daily liters using Shaolei Ren's on-site WUE × off-site EWIF formula. Show as a small comparison to a tracked facility's monthly draw. Cite all source coefficients. Tests verify the formula output for a known input matches a published example.

#### 8. Per-facility disclosure-quality scorecard (HIGH)
Adapt Center for Secure Water (Illinois) gap matrix for VA. For each facility, score whether {withdrawal volume, timing, source, return flow, cooling type, monthly reporting} are disclosed. Display as a 6-cell badge row on each facility card.

**URL:** `https://securewater.illinois.edu/data-center-expansion-in-virginia-closing-critical-gaps-for-informed-water-planning-and-permitting/`

**Sample prompt:**
> Add `disclosure_score()` to `extractors/transparency.py` that takes a facility record and returns a 6-element list (volume/timing/source/return/cooling/monthly) of `True`/`False`/`Partial`. Render as a six-cell color-coded badge row on each facility card in the dashboard. Add a state-level "Disclosure Quality Index" tile that averages all facilities in the state. Tests verify that a fully-disclosing Loudoun ACFR facility scores 6/6 and an undisclosed NDA facility scores 0/6.

#### 9. Household-equivalent toggle on all volume displays (HIGH)
"This facility uses the equivalent of X households per day." Reusable on every gallons number across the dashboard. Use EPA's 300 gpd/household constant; offer pool / NYC-water-system-day toggles too.

**Sample prompt:**
> Add `utils/equivalents.py` with helpers `gpd_to_households(n, gpd_per_household=300)`, `gpd_to_olympic_pools(n)`, `gpd_to_nyc_supply_days(n)`. Add a session-state toggle in the dashboard header: "Show in [gallons | households | pools | NYC-days]". All volume metrics rewrite their label according to the toggle. Cite EPA WaterSense 300 gpd default. Tests verify rounding and unit-conversion correctness.

#### 10. Piedmont Environmental Council ArcGIS ingest (HIGH)
PEC publishes a crowd-sourced existing + proposed VA data centers ArcGIS layer that already covers VA — directly fills the "proposed but not yet built" gap our pipeline misses today.

**URL:** `https://pec-geohub-piedmont.hub.arcgis.com/datasets/virginia-data-centers`

**Sample prompt:**
> Build `scrapers/virginia/pec_data_centers.py` that queries the PEC ArcGIS REST endpoint, normalizes to DocumentRecord (with `status` field: existing/proposed/under-construction), and joins to our existing scraped records by parcel/county. Surface in the dashboard map as a separate layer with distinct iconography for proposed vs existing.

### Additional ideas (grouped, lower urgency)

#### Academic / methodology
- **Shaolei Ren (UC Riverside) on-site WUE + off-site EWIF formula** — adopt as our unified water metric; the canonical source for AI water accounting.
- **Landon Marston (Virginia Tech) dual-footprint methodology** — VT is local; consider reaching out for dataset reuse. Already structurally aligned with our existing EPA ECHO + planned EIA stack.
- **Berkeley Lab 2024 US Data Center Energy Report** — DOE-funded state-level projections for back-calculating indirect water.
- **Carnegie Mellon WaterWise (arXiv 2501.17944)** — adds a "carbon vs. water trade-off" metric column highlighting facilities that are "carbon-clean but water-thirsty."
- **UVA Environmental Institute Data Center Water project** — Lauren Bridges' qualitative framing; consider linking from VA case-study pages.
- **ICPRB Potomac basin projections (WMA DC water 4 → 16 MGD, share 8% → 25%)** — directly relevant to our VA scope; pursue data exchange.
- **IEA "Energy and AI" (April 2025)** — 100 MW DC = ~2 million L/day; cite as default conversion when only nameplate MW is disclosed.
- **OECD "Hidden Costs of AI"** — emphasis on publishing high/low bounds, not point estimates, to reflect disclosure-gap uncertainty.
- **Ceres / Bluerisk "Drained by Data" (Phoenix case)** — cumulative-impact-by-watershed methodology; implement HUC-8 / HUC-12 rollups on the map.

#### Journalistic / framing
- **Bloomberg "The AI Boom Is Draining Water" interactive map** — best benchmark for the visualization we want. Two-thirds-in-water-stress framing reusable.
- **The Markup "Secret Water Footprint of AI"** — open-methodology + publish-your-data ethos; reinforce our own methodology transparency.
- **MIT Technology Review "Power Hungry: AI and Our Energy Future"** — first to extract per-prompt Google numbers (Aug 2025); pair with our calculator.
- **SourceMaterial + Guardian global 632-facility roster** — cross-reference their global list with our VA/OH records.
- **Bay Journal Chesapeake DC water coverage** — seasonal/monthly water-share visualization (winter vs. summer cooling demand).
- **OPB "Google The Dalles" coverage** — "facility-as-share-of-municipal-supply" metric pattern.
- **ProPublica + Seattle Times "Power Hungry"** — methodology of cross-referencing tax incentives with environmental cost; add "subsidy received" column.

#### NGO / advocacy
- **FracTracker open data tracker** — already in top 10.
- **Piedmont Environmental Council ArcGIS** — already in top 10.
- **Sierra Club 2026 Data Centers policy guidance** — state-by-state policy recommendations as scoring rubric for our legislation tracker.
- **NAACP "Stop Dirty Data Centers" Community Report form** — model for our own community-submission workflow; add CEJST EJ overlays to the map.
- **Foxglove (UK) FOI-driven data acquisition** — template FOIA requests for VA/OH water utilities.
- **Coalition to Protect Prince William County** — ground-truth our PWC data; link to their commentary on each PWC facility.
- **Climate XChange dashboard state machine** — policy-state machine (enacted / in-progress / partial / not-enacted) for our legislation tracker.

#### Open-source / dev
- **Electricity Maps GitHub repo** — regional carbon-intensity values for grid-water conversion via published EWIF tables; could be `utils/grid_water_intensity.py`.
- **WattTime API** — marginal (not average) emissions for "indirect water cost of the next MWh."
- **ML.energy Leaderboard** — per-model inference energy benchmarks; powers the calculator widget.
- **Hugging Face AI Energy Score** — per-model energy/water badges alongside company self-claims.
- **Climate TRACE asset-level emissions API** — pull power plant emissions serving each DC to compute Scope 2 water.
- **Epoch AI Frontier Data Centers Hub** — model for publishing our own methodology page.
- **Cleanview US DC project explorer** — project-pipeline distinction (announced / permitted / construction / operating).
- **OpenStreetMap `telecom=data_center` tag via Overpass API** — building polygons for square-footage estimation when not disclosed.

#### Industry / operator data
- **Google 2024 Environmental Report** — site-level WUE table (Council Bluffs IA 1B gal, etc.). Cross-reference our Columbus-area scraper.
- **Microsoft 2024 Sustainability Report** — "% from water-stressed regions" metric paired with WRI Aqueduct.
- **Meta Sustainability** — net water = withdrawal − restoration; pair with Loudoun reservoir restoration credits if any.
- **AWS Water Stewardship** — AWS does not publish absolute volumes; explicitly call this out as the largest transparency gap in the sector.
- **Uptime Institute 2024 Survey** — industry-benchmark bars: "Median operator uses X gpd; this facility reports Y."
- **OCP Sustainability Metrics** — adopt `@geo @wue @load` tag format internally for cross-comparability.
- **Climate Neutral Data Centre Pact** — 0.4 L/kWh WUE benchmark line on per-facility WUE charts.

#### Government datasets
- **USGS NWIS real-time API** — per-facility downstream gauge baseflow context plot.
- **USGS National Water-Use Science Project HUC-12 totals** — denominator for "DC share of basin water use."
- **EPA TRI** — most DCs won't qualify, but flag those with on-site water treatment chemicals.
- **EPA SDWIS** — flag facilities whose municipal supplier has had SDWA violations (EJ signal).
- **Chesapeake Bay Watershed Data Dashboard** — embed/iframe for VA context.
- **Grid Status (gridstatus.io)** — Python lib `gridstatus`, real-time PJM load overlay during cooling season.

#### Visualization patterns
- **Sankey water-flow per facility** — Plotly `go.Sankey`: source → withdrawal → facility → consumption/discharge/restoration. Reference: PNNL water-energy Sankeys.
- **Time-series withdrawal vs. drought condition** — two-axis chart per facility.
- **Cumulative HUC-12 withdrawal heat map** — Ceres pattern for facility clusters.
- **Watershed-share stacked bar over time** — DC slice growing as % of basin use (ICPRB 8% → 25% framing).
- **Per-token / per-prompt slider widget** — calculator widget (in top 10).
- **Disclosure-quality 6-cell badge** — per-facility scorecard (in top 10).

---

## Performance & Infrastructure

Added 2026-06-01 after a dashboard performance pass + cross-viewport UAT. The dashboard is a single ~1900-line Streamlit file that reruns top-to-bottom on every interaction; these items target redundant work on that hot path and the slow stlite/WASM cold start on GitHub Pages. Ordered high → low impact.

### ✅ Perf-0: replace stlite/WASM deploy with a pre-rendered static site (HIGHEST impact) — DONE 2026-06-02
**Done.** The GitHub Pages cold start was ~25–40 s because the site ran Streamlit inside Pyodide/WASM (stlite), downloading ~15 MB of Python + Streamlit + Plotly before first paint. Since the data is static and the UI is mostly HTML the app already builds as strings, `build_site.py` now pre-renders the whole dashboard to a single self-contained `pages/index.html` at build time, reusing `dashboard.py`'s `_build_*_html` builders + data constants (one source of truth). Tabs/filters/collapsibles are vanilla JS; the two quantitative charts use **Chart.js** (SRI-pinned `@4.4.6`); the seasonal heatmap is a CSS grid. Measured first paint / DOMContentLoaded ≈ **35 ms** (down from ~30 s). Pages CI (`pages.yml`) installs only the build deps and runs `python build_site.py`. Tests: `tests/test_build_site.py` (12 — no WASM artifacts, all records embedded, SRI pinned, filter counts, collapse rule). **This supersedes the stlite cold-start motivation for the items below** (Perf-1/2/3 still help the local Streamlit app) **and resolves the SEC-4 self-hosting follow-up** — there is no third-party WASM runtime in the trust path anymore.

### ✅ Perf-1: mtime-based cache invalidation instead of fixed `ttl=300` (HIGH, low effort) — DONE 2026-06-01
**Done.** Added `_file_signature(path) -> (mtime_ns, size)` and split each of the four `load_*` functions into a private `@st.cache_data` worker keyed on `(path, signature)` plus a thin public wrapper that recomputes the signature each call (one cheap `os.stat`). The cache now busts the instant a file changes and otherwise serves from cache forever — no more 5-minute re-parse churn. Tests: `TestFileSignature` (missing→(0,0), changes on edit, stable when unchanged).

~~Replace the fixed `ttl=300` on the four `load_*` cache_data functions…~~

### ✅ Perf-2: vectorize `_extract_flow_mgd` extraction in `load_data` (HIGH, low effort) — DONE 2026-06-01
**Done.** `load_data` now derives `flow_mgd` with a single `Series.str.extract(r"([\d.]+)\s*MGD", flags=re.IGNORECASE)` + `pd.to_numeric(errors="coerce")` pass instead of `.apply(_extract_flow_mgd)`. `_extract_flow_mgd` stays as the scalar helper (still used by tests). Regression test `test_vectorized_extraction_matches_rowwise` asserts exact parity across 11 input shapes (NaN/None/empty/no-match/unparseable "3.2.1 MGD"/case-insensitive/whitespace). Verified live: metrics unchanged (6.7 avg / 7.5 peak).

~~Rewrite the flow-MGD derivation in `load_data` to use a vectorized `str.extract`…~~

### ✅ Perf-3: memoize device type in `st.session_state` (MEDIUM, low effort) — DONE 2026-06-01
**Done (with a deliberate scope call).** Extracted the breakpoint logic into a pure, unit-tested `_classify_width(width) -> DeviceInfo`, and `get_device_type()` now memoizes the resolved `DeviceInfo` in `st.session_state` after the first real width read, returning it on later reruns **without** re-issuing the `streamlit-js-eval` round-trip. The cold-start `None` frame is intentionally never cached, so detection keeps retrying until a real width arrives.

The original "keep listening so a rotate/resize still reclassifies" caveat was **dropped on purpose**: `uat.md` documents that a resize already requires a reload to reclassify today, and a reload starts a fresh session that clears the cache and re-detects — so skipping the JS on cached reruns preserves current behavior exactly while saving the round-trip on every interaction. Tests: `test_get_device_type_memoizes_after_resolution` (second call skips the width read), `test_get_device_type_does_not_cache_cold_none_frame`, `test_classify_width_breakpoints`.

~~In `utils/device.py`, after the first successful `streamlit-js-eval` width read, store the resolved width…~~

### ✅ Perf-4: collapse per-card markdown into one blob per panel (MEDIUM) — DONE 2026-06-01
**Done — reinterpreted toward the real cost.** The original framing (defer per-tab loads) is largely moot now that Perf-1 made the `load_*` cheap (cached on file signature), and it isn't cleanly achievable anyway: `st.tabs` renders all three bodies every run and exposes no server-side active-tab signal, so true per-tab deferral would require swapping the tab widget for a stateful selector (a user-visible UX change with its own switch-latency tradeoff on WASM — see the "Streamlit Top Navigation" low-pri item).

Instead I addressed the actual recurring cost: the Legislation and CWA panels each emitted **one `st.markdown` component per card** (31 + 49 ≈ 80 components rebuilt and reconciled on every rerun, for all tabs). Both now join their per-card HTML into a **single** `st.markdown` blob — **~80 components → 2**, verified live (`querySelectorAll('[data-testid="stMarkdown"]')` holding cards dropped to 2, one holding all 49 CWA cards). Output is byte-identical (each card is a self-contained `<div class="bill-card">`), the browser-native `<details>` toggles still work, and this helps the *active* tab too, not just inactive ones. Removed the now-redundant `_render_bill_card` wrapper.

### Perf-5: ~~shrink the stlite/WASM data bundle~~ — DEFERRED 2026-06-01 (measured negligible)
**Measured, not worth it.** Minifying all four shipped JSON files saves **40,142 bytes total (~8–18% each)** — but that is **0.27% of the ~15 MB cold-start download**, which is dominated by the pandas + plotly wheels, not the data. GitHub Pages already serves these with gzip, which compresses the pretty-print whitespace away over the wire, so the real saving is smaller still. Adding a build-time minification transform (and the pretty↔minified divergence between repo and deploy) is complexity for a sub-percent, mostly-already-captured gain. Revisit only if the data files grow by an order of magnitude or the runtime download shrinks.

### Perf-6: split monolithic `dashboard.py` into modules (LOW) — DEFERRED 2026-06-01 (risk > value)
**Held.** Value is maintainability / editor responsiveness / a modest WASM parse win — but the WASM deploy hardcodes the file manifest in **two** places (`pages/index.html` `files:{}` map **and** `.github/workflows/pages.yml` `cp` list), so a package split means maintaining a multi-file manifest in both, with a silent-deploy-break failure mode. LOW priority + runtime-neutral + real deploy fragility ⇒ not now. If pursued, first add a CI guard asserting the two manifests agree with what `dashboard.py` actually imports/reads. (Perf-4's consolidation already trimmed some of the render bulk that motivated this.)

### Perf-7: UAT automation harness via Preview MCP + launch.json (LOW)
A `.claude/launch.json` (added 2026-06-01) now lets the Preview MCP boot the dashboard and drive cross-viewport screenshots/DOM asserts. Codify the recurring UAT (the five critical flows in `uat.md`) as a repeatable checklist/script so each pass is consistent and regressions in the flow chart paint, device classification, and no-horizontal-scroll invariants are caught automatically.

**Sample prompt:**
> Write a small UAT runbook (or pytest-playwright script) that, for desktop/tablet/mobile, asserts: no horizontal scroll (`scrollWidth === innerWidth`), the Plotly flow chart draws ≥1 trace line and ≥1 point, no "new text" placeholder string is present, and the device-correct title renders. Wire it to the `.claude/launch.json` "dashboard" server.

---

## Security & Supply-Chain Hygiene (added 2026-06-01)

From an external cross-repo security review (re-run periodically — see CLAUDE.md §10). Items 4/5/6 below were fixed on 2026-06-01; the rest are follow-ups.

### ✅ SEC-4: SRI on CDN assets (DONE 2026-06-01) + self-hosting follow-up RESOLVED 2026-06-02
Originally: `pages/index.html` pinned `sha384` integrity for the stlite CSS + loader module, with a residual follow-up to self-host the ~15 MB Pyodide/Streamlit runtime chunks (then not SRI-covered). **That follow-up is now moot:** the June 2026 static-site migration (Perf-0) removed stlite/Pyodide entirely. The deployed `pages/index.html` is pre-rendered static HTML whose only third-party CDN asset is **Chart.js `@4.4.6`**, pinned with a `sha384` `<script integrity>`. No large third-party runtime remains in the trust path. A further hardening option remains available but low-priority: self-host Chart.js under `pages/vendor/` to drop the last CDN dependency.

### ✅ SEC-5: pin Python deps with `==` (DONE 2026-06-01)
`requirements.txt` pinned to exact installed/tested versions. **Follow-up (SEC-5b): hash-pinning.** `==` still can't detect a same-version re-publish on PyPI; generate a fully-resolved, hashed lockfile and install with `--require-hashes`.

> Sample prompt: Add `pip-compile --generate-hashes` (or `uv lock`) to produce `requirements.lock` with transitive deps + sha256 hashes, update the CI install step to `pip install --require-hashes -r requirements.lock`, and document the regen workflow in CLAUDE.md.

### ✅ SEC-6: CSV formula-injection defense (DONE 2026-06-01)
`storage/csv_writer.py:_neutralize_formula` prefixes any string cell starting with `= + - @ \t \r` with `'`. 12 regression tests in `tests/test_csv_writer.py`.

### ✅ SEC-3: SHA-pin GitHub Actions + least-privilege permissions (DONE 2026-06-01)
All six `uses:` across `ci.yml` + `pages.yml` pinned from moving `@vN` tags to full commit SHAs (checkout v4.3.1, setup-python v5.6.0, configure-pages v5.0.0, upload-pages-artifact v3.0.1, deploy-pages v4.0.5), each with a `# vX.Y.Z` comment. SHAs resolved + independently re-verified against `gh api` (the tag *and* the version-comment tag both point to the pinned SHA). Added explicit `permissions: contents: read` to `ci.yml` (was missing); `pages.yml` already least-privilege.

### ✅ SEC-3b: Dependabot to keep pins fresh (DONE 2026-06-01)
`.github/dependabot.yml` watches both `github-actions` and `pip` ecosystems (weekly, grouped to ≤1 PR each), so the SHA-pinned actions *and* the `==`-pinned Python deps get review-able update PRs instead of silently aging — closing the staleness downside of pinning for both SEC-3 and SEC-5. **Optional further hardening:** a `pinned-actions` lint (e.g. `zizmor`, or a grep CI check) that fails if any `uses:` references a non-SHA ref.

### SEC-7: dependency vulnerability + license scanning in CI (MEDIUM, follow-up)
Now that deps are pinned, add automated scanning so a pinned-but-vulnerable version is flagged. Wire `pip-audit` (CVE scan against the pinned set) into `.github/workflows/ci.yml`, failing on high-severity advisories.

> Sample prompt: Add a `pip-audit` step to ci.yml that runs against requirements.txt (and the hashed lockfile once SEC-5b lands), and a scheduled weekly run so new CVEs against already-pinned versions surface without a code change.

---

## New Data Sources (added 2026-06-01)

### Dominion Energy IRP + Virginia SCC large-load filings (MEDIUM)
Distinct from the PJM large-load scraper already in the External Tracker Survey: Dominion's Integrated Resource Plan and its data-center interconnection-queue / large-load tariff filings at the Virginia State Corporation Commission (SCC) carry VA-specific data center load forecasts and named interconnection requests that PJM's RTO-level report aggregates away. Load forecasts are a strong proxy for cooling-water demand when paired with a WUE assumption.

**Data status:** Not verified — confirm the SCC docket search endpoint and whether large-load filings are machine-readable (likely PDF) before building.

**Sample prompt:**
> Investigate the Virginia SCC docket search (scc.virginia.gov) for Dominion Energy IRP and data-center large-load / GT-class tariff filings. If a stable docket/document endpoint exists, build `scrapers/virginia/scc_dominion_irp.py` following BaseScraper: pull the filing PDFs, extract data-center MW load forecasts by year, and store as context records. Cross-reference disclosed MW with a published WUE to estimate indirect cooling-water demand.

### EPA ECHO receiving-WWTP auto-discovery (MEDIUM)
`config.py` hard-codes 8 `epa_echo_target_permits` (the WWTPs that receive data-center cooling-water blowdown). New data center clusters discharge to plants not in that list. Use the EPA ECHO/FRS geospatial APIs to auto-discover which POTW each known NAICS 518210 facility (from `epa_echo_naics`) is in the service area of, and feed those permits back into the ECHO DMR target list — closing the loop between facility discovery and flow measurement.

**Data status:** Confirmed APIs exist (ECHO + FRS, both already used in the codebase). The join (facility → receiving POTW) is the unproven piece — service-area boundaries may need a sewershed/UTILITY layer.

**Sample prompt:**
> Build a step that takes the facilities discovered by `epa_echo_naics`, finds the nearest/serving POTW NPDES permit (via ECHO geospatial search or a sewershed layer), and appends new receiving-plant permits to `epa_echo_target_permits` automatically (with a confidence flag). Surface newly-discovered receiving plants in the Transparency Scorecard. Add tests with a known facility→POTW pair (e.g., a Loudoun DC → Broad Run WRF VA0091383).

---

## CWA Enforcement Integration (added 2026-06-01)

Came out of the June 2026 CWA-investigations research pass. The CWA tab now leads with a computed "What this record tells data centers" panel whose closing point is *watch the receiving WWTP's compliance, not the data center's*. These items make that point live and add the highest-value missing watch targets.

### EPA ECHO CWA enforcement/compliance for tracked WWTP permits (HIGH)
The pipeline already pulls **DMR flow** from EPA ECHO for the 8 `epa_echo_target_permits`. ECHO's ICIS-NPDES layer also exposes the *enforcement/compliance* dimension for those same permits: Significant Non-Compliance (SNC) status, quarters in noncompliance, formal enforcement actions, and assessed penalties. Surfacing that turns the CWA tab from a national case list into a live answer to "are the plants receiving data-center cooling water actually in CWA compliance?" — directly operationalizing the insight panel's fourth bullet. (National context: EPA cut the NPDES SNC rate from 20.3% in FY2018 to 9.3% in FY2023, so a plant flagged SNC is a real outlier worth surfacing.)

**Data status:** Confirmed — ECHO/ICIS-NPDES compliance fields are documented (`echo.epa.gov`, Detailed Facility Report / `get_facilities` + compliance endpoints). Caveat: the same ECHO REST reliability issues logged in `errors.md` (intermittent 5xx) apply; mirror the DMR scraper's chart/download-endpoint workaround and cache results.

**Sample prompt:**
> Extend the EPA ECHO integration to pull CWA compliance/enforcement status for each permit in `epa_echo_target_permits`: current SNC flag, quarters in noncompliance (last 12), count of formal actions, and total assessed penalties (ICIS-NPDES via ECHO). Store on the facility record and render a compact "CWA compliance" strip on the dashboard CWA tab (green/amber/red per permit), with a link to each plant's ECHO Detailed Facility Report. Cache aggressively and degrade gracefully on ECHO 5xx. Tests: a known-compliant plant renders green; a synthetic SNC record renders red.

### Watch-items surfaced by the research (MEDIUM/LOW — monitor, not yet enforcement)
These are large data-center water stories with no formal CWA enforcement action *yet*; worth a lightweight monitor so they convert to `datacenter` cases the moment an NOV/consent order/settlement lands.
- **Meta Richland Parish, LA (Hyperion campus)** — Meta's largest global build (~4M sq ft, $10B+); pledged 100% water restoration to the Boeuf/Tensas/Lower Mississippi watersheds and $300M+ for local water/wastewater infrastructure. Operational discharges will need LDEQ LPDES permits. No enforcement yet; journalists (WWNO) are monitoring air/water. *Monitor LDEQ public notices + LPDES for the campus.*
- **xAI Colossus greywater plant / T.E. Maxson WWTP, Memphis (TDEC)** — now a `datacenter` case (permitted-but-paused). Watch for (a) the recycling plant un-pausing / coming online, or (b) any TDEC water enforcement, or (c) movement in the parallel CAA gas-turbine citizen suit. *Monitor TDEC Division of Water Resources + Earthjustice case page.*

**Sample prompt:**
> Add a lightweight `scrapers/` watch-monitor that polls LDEQ public notices (Meta Richland Parish) and TDEC Division of Water Resources (xAI Colossus greywater plant) for new permits, NOVs, or consent orders, and flags candidates for promotion into `cwa_investigations.json` (category `datacenter`). Keep it append-only and rate-limited; surface new hits in the dataset's `last_updated` note.

---

## Reference: Data Source Landscape

### Key findings from research (Feb 2026)

**Federal level:**
- EPA ECHO is the primary federal source for discharge data (DMR). No federal database tracks water *withdrawals* comprehensively — that's state-managed.
- EPA FRS cross-references facilities across 90+ databases by NAICS code — useful for discovering data center regulatory footprints.
- USGS data is county-level (too aggregated) except for the USWWD compilation.
- EIA tracks power plant cooling water, relevant for indirect water footprint calculations.

**Virginia:**
- Loudoun Water ACFRs and rate studies are the single best public source for aggregate data center water consumption (~1.6B gal/year in 2023, 250% increase from 2019).
- DEQ myDEQ portal has facility-level withdrawal data but requires account creation.
- 25 of 31 Virginia localities with data centers have signed NDAs complicating FOIA.
- SB 553 / HB 496 (2026) **ENACTED** — Gov. Spanberger signed the data center water reporting mandate (HB 496 amends Code § 62.1-44.38; monthly volumes delivered to data centers, incl. reclaimed). New mandatory source coming online; effective ~July 1, 2026. Reporting channel (SWCB/DEQ vs. local zoning) to be confirmed.
- VWP permits (ArcGIS layers 192/193) cover surface water withdrawals.

**Ohio:**
- Ohio EPA's draft General Permit OHD000001 for data center wastewater is a game-changer — will require DMR reporting for cooling water discharge. Public comment closed Jan 16, 2026; finalization pending.
- ODNR Water Withdrawal Facility Viewer has historical annual volumes by facility.
- Central Ohio Regional Water Study (March 2025) projects industrial water demand growing to >40 MGD by 2030, ~90 MGD by 2050. Intel's New Albany chip campus will need 6 MGD alone starting ~2030. Columbus building $1.6B fourth water treatment plant.
- New Albany/Licking County is the densest Ohio data center cluster (Google, Meta, Amazon).
