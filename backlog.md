# Backlog

Items are ordered by priority (high / medium / low). Each includes a sample prompt for generating an implementation plan.

Last reviewed: 2026-05-25.

---

## Completed (March 2026)

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

### National Data Center Water Legislation Tracker
Extend the Policy Timeline / Transparency Scorecard from VA-centric to a multi-state + federal view of who *mandates* water/energy disclosure. Shows where the next mandatory data sources will appear (especially Ohio, which this project already covers).

**Bills to track (verify each status before publishing — several unconfirmed):**
- **Enacted:** Minnesota HF 16 (signed Jun 2025 — water-appropriation permits + disclosure); Virginia HB 496 / SB 553 (2026).
- **Introduced / in committee:** Georgia SB 421 (anti-NDA "Data Center Transparency Act"); Ohio SB 378 / HB 784 (water-consumption reports); South Carolina HB 4583 (closed-loop); California AB 1577; Iowa HF 2447; Michigan SB 762; Kansas SB 400.
- **Federal:** HR 6984 (Data Center Transparency Act — EIA energy data); HR 5332 (Liquid Cooling for AI Act); a Durbin water/energy disclosure bill (Senate number unconfirmed).

**Sample prompt:**
> Build a `data/reference/legislation.json` dataset of state + federal data center water/energy disclosure bills (number, jurisdiction, sponsor, one-line summary, status, source URL, last-verified date) and a dashboard panel that renders it as a US "disclosure map" or sortable table color-coded by enacted / introduced / failed. Seed it with the bills above, verifying each status via LegiScan/state legislature pages first and flagging unverified entries explicitly. Add a lightweight monitor to re-check statuses on a schedule.

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
