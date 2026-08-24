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
**Follow-ups**: confirm the remaining unconfirmed bill statuses against legislature records; add a scheduled re-verification monitor; optional US choropleth map. **Resolved 2026-07-05**: Florida hyperscale data-center regulatory framework confirmed as **FL SB 484** — enacted (signed May 7, 2026, effective July 1, 2026), added to `data/reference/legislation.json`. **Candidates to verify + add next pass** (surfaced June 2026, not yet primary-verified): Iowa HF 2261 (separate water-utility customer class for ≥20 MW loads); Virginia SB 417 (conditions Cloud Computing Cluster grant eligibility on reclaimed-water cooling; did not advance, 2027 carryover); Indiana HB 1043 (data-center water regulation — confirm contents/status).

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

### Execute the 2026-07-25 implementation plan: Issues & Claims / Policy Instruments / Precedent Engine (NEW — planned, research-verified)

Full plan with product specs, ontology, phasing: **`docs/plan-2026-07-25-issues-policy-precedent.md`**. Built from a direct research pass + 3 verified agent sweeps (see AGENTS.md eval log 2026-07-25). Twelve specs across 4 groups; phases P0→P5 are independently shippable. Highest-signal contents: the untracked federal executive layer (EO 14318, NY EO 62, first FAST-41 data center), the AWS whistleblower greenwashing suit + claim-lifecycle schema (`challenged_in`), a 14-value issue-type taxonomy, 12 new legal-authority families with 20 verified anchor cases (Mississippi v. Tennessee → xAI Memphis; Lake Beulah + Racine diversion → Microsoft Mount Pleasant; Swanson → Bessemer), and a status-monitor pipeline. Time-sensitive statuses already verified: AWS Lake Anna VPDES **final** (eff. ~2026-08-01); VA HB 496 first aggregate report due **2026-10-01**; Montgomery Co MD moratorium vote **2026-07-28**.

**Sample prompt (P0):**
> Execute Phase P0 of docs/plan-2026-07-25-issues-policy-precedent.md: extract the `refdata/` package (loaders, registry, taxonomies, integrity) from dashboard.py with zero behavior change, add `cross_ref_targets` support to news+solutions rendering via the registry, and add the edge-integrity test suite. Run the full test suite and `python3 build_site.py` before/after to prove byte-stable output, then commit.

### Data Tab Redesign — 4-Section Data Access Map (highest priority, 2026-06-25)

The Data tab needs a full redesign. The current flow-chart view is preserved behind a developer toggle (`dev_flow_data`) until the new layout ships. The new design frames **data access opacity itself** as the story, not just the data we have.

**Context:** Analysis session 2026-06-25 mapped all 20+ sources across five levels. The core finding: the fundamental precision ceiling is structural (WWTP aggregation, NDA wall), not technical — the redesign should make that legible to users.

**Four-section structure:**

**A — Data Access Map (new hero)**
Replace the flow chart as the first thing users see. A compact matrix: data source × status (working / partial / blocked / coming / missing). Key headline: "X of Y possible sources are accessible today." Makes the access problem the story.
- Sources to show: EPA ECHO DMR (working, WWTP aggregate), EIA 923 (missing — build), EPA FRS (missing — build), HB 496/SB 553 (coming July 2026), OHD000001 (coming), ArcGIS layers (partial — metadata only), ACFR utilities (working), NDA contracts (blocked), CDP questionnaires (partial), FracTracker (missing), PJM Large Loads (missing).

**B — What We Can Measure (current data, reframed)**
The EPA ECHO DMR flow chart and utility aggregates — but with explicit framing: *"These are WWTP totals, not individual data center readings."* Show the precision gap alongside the data. Seasonal heatmap and local context cards stay here.

**C — What's Blocked and Why (new)**
Named blockers at each level with plain-English explanation and best available workaround:
- Federal: WWTP aggregation (workaround: add more permits; long-term: OHD000001 direct DMRs)
- Virginia: NDA wall in 25/31 localities (workaround: utility ACFRs + HB 496 aggregate reports)
- Ohio: OHD000001 not yet final (workaround: receiving WWTP permits, ODNR withdrawal)
- Private: no independent verification path (workaround: CDP + FracTracker cooling type)

**D — Coming Data (new)**
Timeline of confirmed upcoming unlocks:
- HB 496/SB 553 monthly reports — est. Aug/Sept 2026 (monitor SWCB/DEQ portal)
- Ohio OHD000001 finalization — pending (watch EPA ECHO for new permit numbers)
- EIA Form 923 §8D indirect water — buildable now (2024 data available)
- EPA FRS cross-reference — buildable now (API confirmed)

**Dependencies before building:**
1. Confirm HB 496/SB 553 reporting channel (SWCB vs. DEQ vs. local zoning) — first step
2. Build EIA 923 scraper (backlog: "Dashboard Panel 1: The Two Water Footprints")
3. Build EPA FRS utility (backlog: "EPA FRS Cross-Reference Module")
4. FracTracker CSV ingest for cooling type field

**Static site note:** `build_site.py` will also need a `_build_data_access_map_html()` builder and updated `_build_data_tab_html()` to mirror the 4-section structure. The current flow chart HTML builders stay in place (used by Section B).

**Sample prompt:**
> Redesign the Data tab in dashboard.py using a 4-section layout: (A) a data-access map showing all 20+ sources by status (working/partial/blocked/coming/missing) as a compact table with color-coded badges, (B) the existing EPA ECHO flow chart and ACFR utility data reframed as "WWTP aggregates, not individual DC readings" with an explicit precision-gap note, (C) a "What's blocked and why" section with named blockers at federal/state/local/private levels and their best available workarounds, and (D) a "Coming data" timeline anchored to confirmed unlock dates (HB 496 Aug 2026, OHD000001, EIA 923). Mirror the new structure in build_site.py. The existing flow-data toggle (key="dev_flow_data") should remain as a developer escape hatch throughout the transition.

---

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

### States & Localities tab — follow-ups from the 2026-08-24 Spec D/F pass

The tab shipped with 89 mirrored county/city actions, a 41-state rollup, and a
120-day what's-new window. These were deliberately left out of it.

1. **Promote `local_actions.json` into the registry.** Spec D v1 keeps it out:
   the records get no anchors, no `cross_ref_targets` and no graph nodes, which
   is why 89 rows cost table markup only. Promotion means an `action-<id>`
   anchor kind, a `KIND_TABS` entry, integrity-edge coverage, and llms.txt
   one-liners — and it lets other datasets cite a specific county action instead
   of describing it. **Sample prompt**: "Promote local_actions.json to a
   registry kind: add `action` to `refdata.registry.KIND_TABS` and
   `_anchor_for`, emit `id="action-<action_id>"` on each table row, extend
   `EDGE_TARGET_KINDS` so cases and sites may cite an action, and add the
   llms.txt loop plus tests in both directions. Report the page-size delta."
2. **Cross-link mirrored actions to the conflict sites they sit under.** Four
   pairs already match by jurisdiction and are documented but unrendered:
   `charlotte-nc-moratorium` ↔ `dccb-charlotte-city-2026-06`,
   `hood-county-granbury-tx` ↔ `dccb-hood-county-tx-2026-02`,
   `missouri-peculiar-stcharles` ↔ `dccb-st-charles-city-2025-08` and
   `dccb-st-charles-county-mo-2026-07`, `meta-cheyenne-wy` ↔
   `dccb-cheyenne-wy-2026-06`. Spec F item 3 called for display-only context
   lines; item 1 above would make them real edges instead.
3. **A monitor for the benefits repo.** Fits `scrapers/monitors/` — fingerprint
   `docs/data/claims.json` and `docs/data/moratoriums.json`, propose-don't-dispose
   into `monitor_hits.json`. Today §4b of REFRESH.md is entirely by hand.
4. **Re-check the stale `proposed` records.** Five mirrored records sit at
   `proposed` past their own named vote date and could not be confirmed in the
   research window: `dccb-hernando-county-fl-2026-06`,
   `dccb-lake-county-fl-2026-06`, `dccb-greenwood-county-sc-2026-06`,
   `dccb-spartanburg-county-sc-2026-06`, and `dccb-indio-ca-2026-06` (whose
   45-day term lapsed; check whether Indio adopted the permanent ban).
5. **Monterey Park Measure NDC as a `legislation.json` instrument.** It is in
   `local_actions.json` today, but it is genuinely first-of-kind — the first US
   data-center ban enacted by public referendum rather than a council vote —
   which is the threshold Spec D sets for a local measure to become a tracked
   instrument. Needs the `instrument_type` question answered first: the
   taxonomy has no `ballot-measure`, and `local-ordinance` undersells what makes
   it notable.
6. **Dedupe `SC H 4583` and `SC HB 4583`.** Two `bill_id`s for what appears to
   be one South Carolina bill (introduced 2026-01-13). Flagged during the
   2026-08-24 sweep, not altered — confirm against the SC Statehouse bill lookup
   and merge, the same way the Durbin duplicate was folded into US S. 4213.
7. **Tucson's August 2026 data-center zoning amendments as a local action.**
   Verified in the news pass (half-mile residential setback, ~1,000-foot
   commercial setback, 50-foot height cap for 25,000+ sq ft / 20+ MW) and
   recorded in the `project-blue-tucson-az` site's `status_2026`, but not
   entered as a record. It would be the first `zoning-amendment` action, which
   is the taxonomy value Spec D named and this pass held back for want of data.


### Water-authority registry — follow-ups from the 2026-08-24 federal-statute batch

Surfaced while adding the eight supply-side federal/interstate families (`scripts/add_federal_statute_families_2026_08.py`). Each is verified enough to act on but was outside that spec's scope (new federal-statute families only).

1. **Florida v. Georgia, 592 U.S. ___ (2021) for the existing EQAP family.** The ACF/Flint equitable-apportionment case — Florida's claim that Georgia's Flint River withdrawals were harming Apalachicola Bay oyster fisheries failed on redressability — would give EQAP a surface-river companion to Mississippi v. Tennessee's groundwater angle, and would strengthen the `qts-fayette-county-ga` (Flint headwaters) site mapping, which currently reaches only the Corps' authorized-purposes reading.
2. **DOE federal-land AI data-center leasing as a NEPA fact pattern.** Requests for offer issued 2025-26 at Oak Ridge, Paducah, Portsmouth, Idaho National Laboratory and Savannah River Site, explicitly using "NEPA streamlining tools" — a live and growing federal-review pipeline squarely on `nepa-federal-financing-review`. No site mapping was added because none of the 19 tracked conflict sites sits on DOE land; add one once a specific leased project reaches a public water or environmental dispute.
3. **A `hydropower-flow` (or `water-resource-development`) `case_type`.** Ten of the 14 new cases are typed `water-supply` because the 11-value taxonomy has no value for reservoir storage, hydropower licensing or river designation. `water-supply` is a workable fit, not a precise one. Per the closed-taxonomy rule the new value must ship in the same commit as the records retyped onto it.
4. **CRS R49057, "Data Centers and Water: Frequently Asked Questions" (July 31, 2026)** — mirrored at everycrsreport.com since congress.gov blocks automated fetches. A strong general overview, and it confirms the WRDA 2026 (H.R. 9497) provision directing the Corps to report within a year on how "new commercial and industrial water users" affect its water-supply projects (the report says data centers likely fall in that category; the bill text does not name them). Candidate `legislation.json` entry plus a maintainer read.
5. **Render the authority `kind`.** `AUTHORITY_KIND_LABELS` has been defined since the doctrine batches and is re-exported by `dashboard.py` but rendered nowhere, so the accordion never tells a reader whether they are looking at a federal statute, an interstate compact or a state doctrine. Related: at 25 families the Part 1 jump-nav wraps to exactly 3 lines at the 1000px content width — group the pills by `kind` when a later batch pushes it past 3.

**Sample prompt:**
> Add Florida v. Georgia (2021) to `data/reference/cwa_investigations.json` under the existing EQAP family with two independent verified sources (WebSearch only — never construct a Justia or CourtListener URL), map it onto the `eqap-interstate-aquifer` reading's `example_case_ids`, and extend the `qts-fayette-county-ga` site with an EQAP `applicable_readings` entry whose `how` explains the Flint-headwaters connection. Then surface `AUTHORITY_KIND_LABELS` in the Part 1 accordion summary row in both `dashboard.py` and `build_site.py`. Run `python3 build_site.py` and the full test suite before committing.

### UX table / layout issues noted 2026-06-25 (cross-tab audit)

During the Solutions redesign session the following UX issues were catalogued but not fixed. Fix in order of user-facing impact.

**1. Sources tab column squish (medium)**
`render_sources_tab()` uses `st.columns([0.25, 3.5, 1.25, 1.5])` for each source row. On screens ≤ 900 px (tablets, iPad landscape) all four columns collapse to near-zero width, making the badge and action columns unreadable. Fix: replace the per-row `st.columns` layout with a single `st.markdown` HTML table rendered via `unsafe_allow_html=True`, matching the static site's `.src-table` pattern.

**2. CWA tab — 78+ cards all at full height (medium)**
As the case count grows, the CWA tab becomes an unbroken scroll. Users can't skim case headings without reading every card. Fix: add a "compact view" toggle (`st.toggle("Compact view")`) that collapses cards to heading + pill row only, with an expand-all button. The static site uses `<details class="lazy">` natively; the Streamlit app should mirror it.

**3. News tab — filter resets on every tab switch (low)**
The `st.multiselect("Filter by topic", default=all_tags)` re-selects every tag whenever the user switches away and back. Streamlit persists widget state by `key=`; adding `key="news_tag_filter"` is already in place but the `default=all_tags` overrides it on re-render. Fix: store selection in `st.session_state` and only initialize once.

**4. Legislation tab — default shows all 8+ tags simultaneously (low)**
Opening the filter defaults to every tag checked, so the filter chip row provides no visual hierarchy signal. Consider defaulting to empty (show all, no chips checked) or to the top 3 most-common tags. Needs user research first — log it but don't change defaults without a clear preference signal.

**Sample prompt for item 1:**
> In `dashboard.py`, replace the `st.columns` layout in `render_sources_tab()` with a single `st.markdown` block emitting an HTML table (class `src-table`). Table columns: dot (12px) / source name + note / status badge / action. Rows are grouped by level using `<tr class="src-level-hdr">` spanning all columns. Add `.src-table` CSS to `assets/components.css` mirroring the existing static-site styles. Run `python3 -m pytest -q` before and after.

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

#### 9. Household-equivalent toggle on all volume displays (HIGH) — ⚙️ CORE BUILT 2026-06-23
"This facility uses the equivalent of X households per day." Reusable on every gallons number across the dashboard. Use EPA's 300 gpd/household constant; offer pool / NYC-water-system-day toggles too.

**Status (2026-06-23):** the reusable core shipped — `utils/equivalents.py` with `gpd_to_households(n, gpd_per_household=300)`, `annual_gallons_to_households(...)`, `gallons_to_olympic_pools(n)`, and `gallons_to_nyc_supply_days(n)` (EPA WaterSense 300 gpd default; Olympic pool ≈ 660K gal; NYC system ≈ 1B gal/day). `dashboard.compute_household_equivalent` now delegates to it (one source of truth; exact legacy behavior preserved). 15 tests in `tests/test_equivalents.py`. **Remaining follow-up:** the session-state header toggle that rewrites every volume label across the dashboard (UI-only; the math is done).

**Sample prompt (remaining toggle):**
> Add a session-state toggle in the dashboard header: "Show in [gallons | households | pools | NYC-days]" backed by the existing `utils/equivalents.py` helpers. All volume metrics rewrite their label according to the toggle. Mirror the change into `build_site.py` so the static site offers the same toggle. Tests verify each unit renders.

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
- **Meta Richland Parish, LA (Hyperion campus)** — **PROMOTED 2026-06-10** to a tracked `adjacent` case (`Meta-RichlandParish-LA-WaterSupply-2025`): authorized up to 23 MGD with no state monitoring regime, the largest permitted water envelope of any US data center. Still watch: operational discharges will need LDEQ LPDES permits; convert exposure to `datacenter` if an LPDES permit or enforcement lands. *Monitor LDEQ public notices + LPDES for the campus.*
- **xAI Colossus greywater plant / T.E. Maxson WWTP, Memphis (TDEC)** — now a `datacenter` case (permitted-but-paused). Watch for (a) the recycling plant un-pausing / coming online, or (b) any TDEC water enforcement, or (c) movement in the parallel CAA gas-turbine citizen suit. *Monitor TDEC Division of Water Resources + Earthjustice case page.*
- **AWS Lake Anna VPDES individual permit (VA DEQ)** — added 2026-06-10 as a `datacenter` case (`AWS-LakeAnnaVA-VPDES-cooling-discharge-2026`). *Re-checked later on 2026-06-10: still no final decision; DEQ's published comment responses confirm no PFAS-testing mandate in the draft (a special condition reserves the right to add it).* When DEQ decides: update the case's `outcome`, and if granted, the permit number becomes a *direct* hyperscaler NPDES permit to track via EPA ECHO DMR — the first one that isn't a receiving-WWTP proxy. *Monitor VA DEQ public notices / Town Hall for the final VPDES action.*
- **Quantum Loophole / Frederick MD AG enforcement** — added 2026-06-10 (`QuantumLoophole-FrederickMD-boring-discharges-2022-2024`). *Re-checked later on 2026-06-10: no filed MD AG action or consent decree surfaced in OAG news, MDE consent-decree pages, or coverage; Catellus (TPG) has assumed full developer control, which may complicate who answers for the legacy violations.* Watch for the filed action and update `outcome` + penalty when it lands.
- **Microsoft Mount Pleasant WI wetland permit MKE 09-14** — final disposition not confirmed (case flagged `cwa_applied: pending`). *Re-checked 2026-06-10: WI DNR's online permit tracker for the site shows only air permits; no WT decision document found. Construction proceeding implies issuance or avoidance — confirm via DNR's water-permit (WT) decision database before changing case status.*
- **Homer City PA NPDES draft permit PAD320011** — added 2026-06-10 as an `adjacent` case (`HomerCity-IndianaCounty-PA-NPDES-2026`). Draft NPDES permit for the 4.4 GW data-center power plant publicly noticed 2026-05-12; Ch. 105 wetland/stream permit pending; NGOs already appealing on the air side. *Watch PA DEP's Homer City permitting page for the final NPDES action and any EHB appeal of it.*
- **NY S10642 / A11560 (one-year statewide DC moratorium)** — passed both chambers June 4-5, 2026, awaiting Gov. Hochul. If signed, it's the first statewide data center moratorium in the nation → flip status to enacted and re-verify whether tracked S9144/A10141 (three-year version) is dead.

**Sample prompt:**
> Add a lightweight `scrapers/` watch-monitor that polls LDEQ public notices (Meta Richland Parish) and TDEC Division of Water Resources (xAI Colossus greywater plant) for new permits, NOVs, or consent orders, and flags candidates for promotion into `cwa_investigations.json` (category `datacenter`). Keep it append-only and rate-limited; surface new hits in the dataset's `last_updated` note.

### ✅ Prioritized CWA-application theories → dashboard panel (added 2026-06-23, BUILT 2026-06-23)
`docs/cwa-enforcement-and-data-centers.md` carries a **scored, forward-looking menu of 12 CWA theories** that could attach to a data center, ranked on public-interest merit — Impact (community/environmental harm averted), Viability (legal strength post-*Sackett*/*Maui*), and Tractability (can this tracker source the evidence). Top picks: (1) **§505 citizen suit against the *receiving* POTW** in SNC while loaded by DC blowdown and (2) **§307/§403 pretreatment / Industrial-User** loading — both turn the existing ECHO DMR/SNC pull into an actionable community-cost finding against the permit that actually carries the operational discharge. Highest-novelty legal theory: (9) **County of Maui "functional equivalent"** for discharge-to-groundwater-reaching-surface-water. Scoring is merit-only (impact/viability/tractability), deliberately **not** keyed to any operator's or official's identity or politics.

**Status (2026-06-23):** BUILT. `dashboard.CWA_APPLICATION_THEORIES` (the 12 scored theories) + pure `_build_cwa_theories_html()` builder + `render_cwa_application_theories()` panel, wired into the Streamlit CWA tab (after the insights panel) and the static site (`build_site.build_cwa_tab`, in a collapsible). `.theory-table` CSS added to `_RESPONSIVE_CSS` so both surfaces match. 7 tests in `test_dashboard.py` + 2 in `test_build_site.py` (panel renders, all 12 rows, distinct classes so card/case counts are unaffected). **Optional follow-up:** hyperlink each theory's `analog` to the matching `cwa_investigations.json` case, and add client-side sorting by I/V/T.

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

## Explicit cross_ref_targets for news/solution cross-references (from PR #17 code review)
- **Priority**: low
- **What**: `_linkify_refs` resolves cross-references by prose-substring matching against canonical bill ids / case captions / site names. Rewording a note or renaming a caption silently un-links it, and authors must embed exact canonical strings. Replace with an explicit `cross_ref_targets: [bill_id|case_id|site_id]` field on news/solution items, rendered as links directly; keep linkify only as a fallback. Add a test that every cross_ref_note containing a canonical id actually produced a link in the built page.
- **Sample prompt**: "Add cross_ref_targets fields to water_news.json and water_solutions.json entries, render them as deep links in _build_news_item_html/_build_solution_card_html, and test that no cross-reference silently un-links."

## Apply the CWA outcome taxonomy to data-center conflict sites
- **Priority**: medium
- **What**: `docs/cwa-outcome-taxonomy.md` (added 2026-07-05) reads all 76 historical `cwa_investigations.json` cases and groups their free-text `outcome` field into a closed 12-type taxonomy (Monetary penalty, Injunctive relief/mandated upgrade, Criminal prosecution, Structural remedy, Permit granted w/ conditions, Permit denied/vacated/withdrawn, Referral to escalated enforcement, Dismissed/mooted/cert denied, No formal action, Landmark ruling, Pending/ongoing, Mass tort settlement) — the same pattern as the existing `case_type` and `general_principles` taxonomies in `dashboard.py`. Not yet wired into any code or data field; this is the map only. Two follow-on steps: (1) add an `outcome_type` field (list, since consent decrees often mix penalty + injunctive relief) to each case in `cwa_investigations.json`, test-enforced against the taxonomy same as `case_type`/principle tags; (2) for each site in `data/reference/dc_water_conflicts.json` (Water Cases Part 4), use the closest-matching historical case(s) already listed in its `applicable_readings`/`related_case_ids` to infer and display a "likely outcome pattern" — e.g. a site resembling Amazon-Boardman-OR-nitrate-2026 suggests a monetary-settlement trajectory, one resembling Meta-NewtonCountyGA-well-failures-2018-2025 suggests "no formal action likely" rather than assuming enforcement is coming.
- **Sample prompt**: "Read docs/cwa-outcome-taxonomy.md's 12-type taxonomy. Add an `outcome_type` (array) field to every case in data/reference/cwa_investigations.json using that taxonomy — most historical cases take 1-2 types (e.g. Monetary penalty + Injunctive relief), precedent cases take Landmark ruling, potential-section cases take Pending or No formal action. Add a schema test (mirror TestLegislationTracker's principle-tag test) enforcing outcome_type values are taxonomy members and every historical case has at least one. Then, for each site in data/reference/dc_water_conflicts.json, add an `analogous_outcome_note` field: one sentence naming the closest-matching historical case(s) by outcome type and what that implies for the site. Render the taxonomy definitions plus the note in `_build_conflict_site_html` (Part 4 cards)."


## Supply a LEGISCAN_API_KEY and do one live monitor run
- **Priority**: high
- **What**: Two watches (`US S. 4213`, `NY S10642 / A11560`) use the `legiscan`
  kind because congress.gov and nysenate.gov both 403 automated clients. The
  bill-number strings (`US SB4213`, `NY S10642`) are **not verified against the
  live API** — no key was available when they were written. A wrong string now
  fails loudly (`getSearch` matches exactly and raises `no bill numbered X`)
  rather than silently never firing, so one keyed run settles it.
- **Sample prompt**: "Export LEGISCAN_API_KEY, run `python3 -m scrapers.monitors.run --only 'US S. 4213'` then the NY watch, and correct the `monitor.key` strings in legislation.json if getSearch reports no match."

## Retire or regenerate the stale annotate_issue_types.py migration
- **Priority**: low
- **What**: `scripts/annotate_issue_types.py` covers 18 sites; the dataset now has
  19 (Meta Cheyenne). It fails closed — aborts before writing — so it is harmless,
  but re-running it is a dead end. Decide whether one-off migrations should be
  archived read-only once applied, or kept re-runnable against current data. The
  same question applies to every `scripts/add_*_2026_07.py`.
- **Sample prompt**: "Decide a convention for applied one-off migration scripts in scripts/ — archive vs keep-current — and apply it, starting with annotate_issue_types.py which is now stale by one site."

## Add LEGISCAN_API_KEY to repo secrets
- **Priority**: medium
- **What**: The weekly `Status monitors` workflow runs without it — the two
  LegiScan watches simply report as failed, loudly, which is the intended
  degraded mode rather than a silent skip. Adding the secret activates them.
  Pairs with the live-verification item above: the first keyed run is also what
  confirms the bill-number strings.
- **Sample prompt**: "Add LEGISCAN_API_KEY to the repo secrets and trigger the Status monitors workflow manually to confirm both LegiScan watches resolve."

## Embedding-based semantic search for the Explore tab
- **Priority**: medium (deferred 2026-08-24 — needs API tokens)
- **What**: Spec B's similarity is TF-IDF cosine, fully offline. True semantic matching ("aquifer drawdown" ≈ "wells going dry") needs embeddings computed at build time via an embedding API and shipped as vectors in the graph blob. Explicitly deferred because the user's rule for this session was: anything needing live tokens goes here, not in the build. Design note: embed at generation time (one API pass per record, cached by record content hash in data/state/), never at page runtime; page-side scoring stays pure JS (dot products).
- **Sample prompt**: "Add a build-time embedding pass to refdata/graph.py: for each registry record, embed its index text via the Claude/voyage embedding API (cache by content hash under data/state/embeddings.sqlite), ship float16-quantized vectors in the graph blob behind a size guard, and blend cosine(embedding) with the existing TF-IDF score in the Explore tab's ranking. Keep the no-key path working: if no API key is present, build falls back to TF-IDF-only and the page says so."

## "Ask the record" natural-language querying over the knowledge graph
- **Priority**: low (deferred 2026-08-24 — needs runtime tokens or a server)
- **What**: A question box ("which cases could reach a Georgia county moratorium fight?") answered by an LLM given the graph JSON as context. Needs either a hosted endpoint or user-supplied API key at page runtime; both out of scope for a static Pages site today.
- **Sample prompt**: "Prototype an 'ask the record' mode for the Explore tab: a small hosted endpoint (or claude.ai artifact capability) that receives the question plus the graph blob's relevant neighborhood (selected via the existing TF-IDF search) and returns an answer with record ids, rendered as links. Gate it behind a config flag so the static site never depends on it."

## Saved searches / pinned nodes on the Explore tab
- **Priority**: low (deferred 2026-08-24)
- **What**: Pin records and save query text across visits. localStorage gets 90% of it with no backend; cross-device sync would need storage. Start with localStorage.
- **Sample prompt**: "Add localStorage-backed pins and saved searches to the Explore tab: pin a node from focus mode, list pins in the left column, restore last query on load. No backend."

## US choropleth for the States & Localities tab
- **Priority**: medium
- **What**: The tab ships as a rollup grid (Spec D). A state-shaded map (activity count or newest-action recency) reads faster. Needs a US states SVG (public domain, inline — no new CDN asset) wired to the same rollup data.
- **Sample prompt**: "Add an inline public-domain US states SVG to the States & Localities tab, shade states by tracked-activity recency buckets from the existing rollup builder, tooltip = counts by status, click = scroll to that state's card. Both surfaces, size-budgeted, no external assets."

## Promote local_actions records into the registry
- **Priority**: low
- **What**: Spec D v1 keeps the moratorium mirror out of the registry (no anchors/cross-refs). Promotion means: a `local-<id>` anchor kind, KIND_TABS entry, llms.txt coverage, integrity edges from news/sites to actions, and dedupe rules against legislation.json local-ordinance instruments.
- **Sample prompt**: "Promote data/reference/local_actions.json into refdata's registry as kind 'local-action' with anchors on the States & Localities tab, add news/site cross-ref edge kinds to integrity.EDGE_TARGET_KINDS, extend llms.txt coverage tests, and define the dedupe rule vs legislation.json local-ordinance instruments."

## Monitor the datacentercommunitybenefits source files
- **Priority**: medium
- **What**: The claims mirror and the new moratorium mirror (Spec F) refresh by hand. A monitors watch fingerprinting `docs/data/claims.json` and `docs/data/moratoriums.json` in the sibling repo would propose refreshes weekly (propose-don't-dispose, like every monitor).
- **Sample prompt**: "Add a scrapers/monitors watch that fingerprints raw.githubusercontent.com/pranava0x0/datacentercommunitybenefits/main/docs/data/{claims,moratoriums}.json and files a monitor hit when either changes, with the diff summary in the hit payload."

## DRBC/SRBC docket-calendar watch
- **Priority**: medium
- **What**: Basin commissions approve large withdrawals directly — a data-center docket would be a Tier 1 source the day it appears. Their meeting/docket pages are public; a monitor fingerprinting the docket lists (filtered to data-center-ish applicants) closes the gap Spec A's BASIN readings describe.
- **Sample prompt**: "Add monitors watching the DRBC and SRBC docket/meeting pages for new water-withdrawal dockets, fingerprint the docket lists, and flag applicants matching data-center/NAICS-518210 patterns. Confirm both sites tolerate automated clients first (CLAUDE.md blocked-sources table)."

## Per-tab line-art icon set (racks / pipes / droplet / tower)
- **Priority**: low (design-gated, deferred from Spec E)
- **What**: Small inline SVG icons next to tab labels. Only worth doing if it survives a pass against DESIGN.md §12 ("no emoji in headers" spirit — icons must read as wayfinding, not decoration).
- **Sample prompt**: "Design a 5-icon inline-SVG set (server rack, pipe run, droplet, cooling tower, scale) at 16px stroke style for the static site's tab strip; apply DESIGN.md §12 and drop the idea if it reads as decoration."

## Per-site water-flow visualization on the Data tab
- **Priority**: low (design-gated, deferred from Spec E)
- **What**: The header schematic is generic — one diagram for the whole industry. A per-site version (this campus, this WWTP, these volumes) would turn it into data. Blocked on two things: the flow data being per-site rather than per-receiving-plant, and DESIGN.md §12's one-animation rule — a second moving element needs a better argument than "the first one looked good".
- **Sample prompt**: "Extend dashboard._build_water_loop_svg() into a per-site variant that takes a site's measured volumes and labels the legs with them; reuse the same geometry, keep it static (DESIGN.md §12 sanctions exactly one animation), and only ship it for sites where the numbers are real."

## International/treaty water layer
- **Priority**: low (deferred from Spec A)
- **What**: Boundary Waters Treaty/IJC, Columbia River Treaty, US-Mexico 1944 Treaty — relevant to border-region siting (an El Paso or Great Lakes fact pattern). Needs its own `kind` and at least one anchoring case each; none verified yet.
- **Sample prompt**: "Research whether the Boundary Waters Treaty/IJC or the 1944 US-Mexico Water Treaty has a verifiable case anchoring a data-center-relevant reading; if yes, add a 'treaty' kind family to water_authorities.json with the same reading+case pairing rules."
