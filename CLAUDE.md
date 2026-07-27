# Data Center Water Use Tracker — Project Guide

## Project Overview

Python-based scraping and data extraction pipeline that finds documents related to data center water usage from public utility and environmental portals in Virginia and Ohio. Extracts water consumption metrics into structured CSV/JSON output.

## Core Principles

### 1. Resource-Efficient Scraping
- **Start small, test, iterate.** When building or running a scraper, test against a single page or a handful of documents first. Confirm the data looks correct before scaling up to full runs.
- Use `--limit N` flags or similar mechanisms to cap document fetches during development.
- Respect government servers: randomized 2-5 second delays between requests, never parallel-blast a single host.
- If a scraper doesn't need Playwright (e.g., direct file download or REST API), don't use Playwright.

### 2. Caching and Data Reuse
- All downloaded files are stored locally in `data/downloads/` organized by state and agency.
- The SQLite state database (`data/state/scraper_state.db`) tracks every fetched document by (scraper_name, document_id). Re-runs skip already-fetched documents automatically.
- Before downloading a file, check if it already exists at the expected local path. Only re-download if the remote version is newer or the local copy is corrupted.
- Extracted results are cached — don't re-extract text from a PDF that hasn't changed.

### 3. Append-Only Data, No Overwrites
- When writing to `results.csv` or `results.json`, **append** new records rather than overwriting the file.
- If a new scrape produces a record that conflicts with an existing one (same document_id/source_url), adjudicate: keep the **newer** version since government portals update documents over time.
- The state database tracks timestamps for this purpose. Use `scraped_at` to determine recency.
- Never delete raw downloaded files unless explicitly asked to clean up.

### 4. Source Attribution
- Every `DocumentRecord` must include the `source_url` pointing to the original document or portal page.
- PDF files stored locally must have their `local_file_path` recorded in the output.
- When extracting quotes or metrics, include enough context to trace back to the source section.
- The `source_portal` enum identifies which scraper produced the record.

### 5. Git Discipline
- Commit **often** at natural checkpoints — small, focused commits are better than large monolithic ones:
  - After creating the project structure and foundation modules
  - After each new module or scraper is implemented
  - After writing or updating tests for a module
  - After fixing a bug or resolving a failing test
  - After refactoring or cleanup
  - After updating documentation (CLAUDE.md, errors.md, backlog.md)
- Don't let work accumulate — if you've made a meaningful change, commit it.
- Write descriptive commit messages that explain *what* and *why*.
- Don't commit `data/downloads/` (large binary files) — add to `.gitignore`. Do commit `data/output/` samples if they're small.

### 6. Error Logging
- When errors occur during scraping, extraction, or testing, log them to `errors.md` with:
  - Date/time
  - Which scraper/module failed
  - Error message and traceback summary
  - **Root cause classification**: Is this a **code bug** (logic error in production code) or a **test bug** (incorrect assertion, wrong test setup, stale fixture)?
  - Resolution status (open / fixed)
- When an error is fixed or a failing test passes, **immediately** update the corresponding entry in `errors.md` with:
  - What the fix was
  - Whether it was a code fix or a test fix
  - The commit that resolved it (if applicable)
- Use structured logging (`structlog`) in code for runtime errors. `errors.md` is the human-readable audit trail.
- After every bug fix, check whether the fix needs a new test or an updated test to prevent regression.

### 7. Testing and Validation
- **Write tests alongside code, not as an afterthought.** Every new module, function, or bug fix should include corresponding tests.
  - New module → add `tests/test_<module>.py` in the same session.
  - Bug fix → add a regression test that would have caught the bug.
  - New extractor or scraper → test with sample data.
- Each extractor, storage module, and utility should have corresponding tests in `tests/`.
- Test against real sample data when possible (save a sample PDF or Excel snippet in `tests/fixtures/`).
- When a test fails:
  1. Determine root cause: **code bug** vs. **test bug** (bad assertion, stale fixture, wrong expectation).
  2. Document in `errors.md` with the classification.
  3. Fix the appropriate side (code or test), then update `errors.md` with the resolution.
- Validate output data: check that required fields are non-empty, dates parse correctly, URLs are valid.
- Run the full test suite before committing to catch regressions early.

### 8. Backlog Management
- When ideas come up for improvements, new scrapers, or enhancements, add them to `backlog.md` immediately.
- Each backlog item should include a sample prompt that could be used to generate a plan for implementing it.
- Prioritize backlog items periodically — mark items as low/medium/high priority.

### 9. Living Document
- Update this CLAUDE.md as the project evolves:
  - Add new scrapers to the architecture section below as they're built
  - Document any changed conventions or patterns
  - Record key decisions and their rationale

### 10. Security & Supply-Chain Hygiene
- **An external cross-repo security review is run periodically** (findings come from a separate audit repo and are pasted in as numbered items). **Check it frequently** — re-run/re-request it before any release and whenever dependencies, the Pages build, or data-writing code changes. Triage each finding, fix or log it, and record the disposition here.
- **Standing rules (don't regress these):**
  - **Pin dependencies with `==`** in `requirements.txt` (never float `>=` — that auto-pulls whatever patch is on PyPI at the next install, a supply-chain entry point). Follow-up: hash-locked installs (`pip-compile --generate-hashes` / `uv lock` + `--require-hashes`) to also catch same-version re-publishes — tracked in `backlog.md`.
  - **Subresource Integrity (SRI) on every third-party CDN asset.** As of June 2026 the live site is a **pre-rendered static page** (`build_site.py` → `pages/index.html`); the stlite/Pyodide WASM runtime is gone, so the only third-party CDN asset is **Chart.js**, pinned to `@4.4.6` with a `sha384` `integrity` on its `<script>` tag (the hash is `build_site.CHARTJS_SRI`). To regenerate a hash: `curl -sL <url> | openssl dgst -sha384 -binary | openssl base64 -A`, then re-verify it twice (a partial download yields a wrong hash that fails closed). NB: removing stlite also closed the old "15 MB Pyodide runtime not SRI-covered" gap — there is no longer any large third-party runtime in the trust path.
  - **Pin GitHub Actions to full commit SHAs + least privilege.** Every `uses:` in `.github/workflows/` is pinned to a 40-char commit SHA (not a moving `@vN` tag) with a `# vX.Y.Z` comment, so a retag/compromise of a tag can't inject code — critical for any workflow with `contents: write`/`pull-requests: write` or a cron schedule. Every workflow declares an explicit least-privilege top-level `permissions:` block. Re-pin with `gh api repos/<action>/commits/<tag> --jq .sha` and verify it twice.
  - **Neutralize CSV formula injection.** `storage/csv_writer.py` prefixes any string cell starting with `= + - @ \t \r` with `'` (`_neutralize_formula`) so a scraped value can't execute when the export is opened in Excel/Sheets.
  - **No secrets or PII in committed data.** `local_file_path` is stored repo-relative (see SEC-001 in `issues.md`); never commit absolute home paths, tokens, or credentials.
- When a security item is fixed, add a regression test (e.g., `tests/test_csv_writer.py`) and note it in `errors.md`/`issues.md` so it can't silently regress.

### 11. Agent-Use Accountability
- **Every session that spawns agents (research, Explore, or otherwise) must end by evaluating each run**: quality of results, token efficiency (subagent tokens per verified fact/entry is the working unit), and whether an agent was needed at all versus 1-3 direct WebSearch/Read/grep calls.
- **Save the evaluation**: append a dated entry to AGENTS.md § "Agent-use evaluation log" (the standing rule and scoring rubric live there), and mirror durable lessons into the assistant's persistent memory so they survive across sessions.
- Measured to date — anti-patterns: merge-conflict agents (~105k vs ~30k inline, 2026-06-24); Explore agents for questions CLAUDE.md already answers (~30-40% waste, 2026-06-25). Good pattern: parallel background research agents for multi-source verification (~4.6k tokens per verified entry, 2026-07-02).

---

## Architecture

### Tech Stack
- **Browser automation**: playwright (async)
- **HTML parsing**: beautifulsoup4 + lxml
- **HTTP client**: httpx (async, rate-limited via tenacity)
- **PDF extraction**: pdfplumber (tables) + PyMuPDF/fitz (text fallback)
- **Excel parsing**: openpyxl
- **State/resumability**: aiosqlite
- **Logging**: structlog
- **CLI**: click
- **Dashboard (authoring)**: streamlit + plotly — `dashboard.py` is the local-dev / source-of-truth app (`streamlit run dashboard.py`).
- **Dashboard (deployed)**: a **pre-rendered static site**. `build_site.py` imports `dashboard`'s pure `_build_*_html` builders + data constants and emits a single self-contained `pages/index.html` (vanilla-JS tabs/filters/collapsibles, Chart.js for the 2 quantitative charts, CSS-grid heatmap). This replaced the old stlite/Pyodide WASM deploy in June 2026 — first paint went from ~25–40 s to ~35 ms. Edit a card builder or the data and both the Streamlit app and the static site change together; regenerate with `python build_site.py` — which also emits **`pages/llms.txt`**, an LLM-friendly markdown mirror (llmstxt.org convention: project summary, key numbers, the cross-bill principles summary, one-liners for every bill and CWA case with sources). It is linked from the page (`<link rel="alternate">` + footer) and test-enforced to contain every bill_id/case_id, so it can never drift from the page.
- **Testing**: pytest + pytest-asyncio (507 tests)

### Curated-data layer (`refdata/`, added 2026-07-25)

The seven curated datasets are loaded, typed and cross-checked in one **pure**
package — no `streamlit` import anywhere in it, enforced by test — so
`dashboard.py`, `build_site.py`, `scripts/annotate_*.py` and the tests all
share one definition:

- `loaders.py` — the seven loaders. `functools.lru_cache(maxsize=2)` keyed on
  `(path, mtime_ns, size)`; same cache-busting as the old `@st.cache_data`,
  bounded so a long-running app doesn't retain every refresh. **Payloads are
  shared and must be treated read-only.**
- `taxonomies.py` — every closed taxonomy plus the palette. **A new value ships
  in the SAME commit as the records that use it** — a value with no records
  renders a filter chip matching nothing (caught in a build diff), and tests
  enforce membership in both directions.
- `registry.py` — one `id → Ref(kind, tab, anchor, label)` index over all
  datasets. This is what makes moving a section between tabs a change to
  `KIND_TABS` instead of a find-and-replace across three JSON files.
- `integrity.py` — walks every cross-reference edge; one test asserts the whole
  graph resolves and points at the right *kind* of record.

**Anchors:** `bill-<slug>`, `cwa-<case_id>`, `reading-<id>`, `site-<id>`,
`claim-<id>`, `news-<id>`, `solution-<id>`. A build test asserts every internal
`href="#x"` has a matching `id="x"` — registry-level integrity does not prove
the renderer emitted the anchor.

### Status monitors (`scrapers/monitors/`, added 2026-07-26)

`python3 -m scrapers.monitors.run [--dry-run] [--only ID]` — see `REFRESH.md`.
Runs weekly unattended via `.github/workflows/monitors.yml` (Mondays 07:23 UTC,
`workflow_dispatch` for a manual run). **State lives in git**: the workflow
commits the candidate queue, the fingerprints and the page snapshots. An earlier
version kept them in the actions cache with artifact fallbacks and a recovery
path — five steps of shell that produced defects in six consecutive review
rounds. Git is already this project's durable append-only store (§3), so the
workflow just commits. It has `contents: write` scoped to those three files and
refuses blanket `git add`, so it can never touch `data/reference/`.

- **Monitors propose; humans dispose.** Nothing here writes to a curated
  dataset; changes land in `data/output/monitor_hits.json` for adjudication. A
  test fails if `base_monitor.py` acquires a write call.
- **The watch list is derived** from records carrying a `monitor` block — no
  second list to drift.
- `legiscan` keys are a numeric LegiScan id or `"<STATE> <BILLNUM>"` (resolved
  via `getSearch`, matched exactly). `getBill` takes the *numeric* id only —
  passing a bill number returns an error payload, which is why the response
  `status` is validated rather than fingerprinted.
- Needs `LEGISCAN_API_KEY` in the environment; never committed.

### Sources that block automated clients (verified 2026-07-27)

Check before pointing a scraper or monitor at one:

| Source | Behaviour | Use instead |
|---|---|---|
| Justia | **403 to every automated request**, including valid URLs — a 403 tells you nothing about whether the page exists | WebSearch; never pattern-construct a citation URL and assume it resolves |
| CourtListener | serves a bot challenge; WebFetch reads blank | WebSearch |
| congress.gov, nysenate.gov | 403 | LegiScan API |
| deq.virginia.gov | 403 (WAF, see errors.md 2026-02-24) | Virginia Regulatory Town Hall |
| legislature.mi.gov, permitting.gov, federalregister.gov | 200 | direct |

### UAT note: the preview pane and `file://`

`pages/index.html` opened over `file://` renders as a **static snapshot**:
screenshots come back blank and geometry is unmeasurable (`clientWidth` reports
0, so any "horizontal overflow" reading there is an artifact). DOM state and
interaction *are* live — `javascript_tool` is the reliable verification channel.
Verify layout containment structurally (e.g. the element sits in
`.table-wrap{overflow-x:auto}`) rather than by measuring.

### Key Directories
- `scrapers/` — one module per government portal, organized by state
- `extractors/` — PDF text extraction, keyword matching, entity extraction
- `models/` — dataclasses for DocumentRecord
- `storage/` — CSV/JSON writers, SQLite state manager, file download manager
- `utils/` — HTTP client, Playwright browser manager, user-agent pool, logging config
- `data/downloads/` — raw downloaded files (gitignored)
- `data/output/` — structured CSV/JSON results
- `data/state/` — SQLite database for scraper state
- `dashboard.py` — Streamlit app for local authoring (source of truth for render logic)
- `build_site.py` — static-site generator; pre-renders `dashboard.py`'s output to `pages/index.html` for GitHub Pages (the deployed artifact)
- `pages/index.html` — the generated static dashboard served by Pages (regenerated, committed)

### Scraper Status
| Scraper | Portal | Status | Notes |
|---------|--------|--------|-------|
| deq_vpdes_excel | VA DEQ VPDES Excel | Built, blocked by WAF | 403 from DEQ site — see errors.md |
| deq_arcgis | VA DEQ ArcGIS REST | Working | Permit metadata only — no flow data in ArcGIS layers |
| deq_public_notices | VA DEQ Public Notices | Built | Playwright-based, needs testing |
| deq_peep_tableau | VA DEQ PEEP/VPT | Built | Power BI scraper, needs testing |
| loudoun_boarddocs | Loudoun Water BoardDocs | Built | BoardDocs JS rendering |
| loudoun_highbond | Loudoun Water Highbond | Built | Needs testing |
| pwc_eservices | Prince William County | Built | Dual HTTP + Playwright |
| epa_edocument | Ohio EPA eDocument | Built | ASP.NET WebForms, needs testing |
| columbus_legistar | Columbus Legistar API | Working | Municipal IT data center — no water data |
| columbus_utilities | Columbus Utilities Board | Built | Needs testing |
| new_albany | New Albany Council | Built | HTTP + Playwright fallback |
| **epa_echo** | **EPA ECHO DMR** | **Working** | **Primary water data source — flow MGD from treatment plants** |
| **epa_echo_naics** | **EPA ECHO NAICS** | **Working** | **Facility discovery — NAICS 518210 in VA/OH** |
| **loudoun_acfr** | **Loudoun Water ACFR** | **Built** | **Aggregate data center water sales (~1.6B gal/yr)** |
| **oh_epa_general_permit** | **Ohio EPA OHD000001** | **Built** | **Tracks first-ever DC wastewater general permit** |
| **fairfax_water** | **Fairfax Water** | **Built** | **Upstream wholesale supplier to Loudoun Water (~18 MGD)** |
| **central_ohio_study** | **Central Ohio Water Study** | **Built** | **Demand projections: 40 MGD (2030) → 90 MGD (2050)** |
| **oh_epa_npdes_arcgis** | **Ohio EPA NPDES ArcGIS** | **Built** | **SIC 7374 permit discovery, nightly updates** |
| **odnr_withdrawal** | **ODNR Water Withdrawal** | **Built** | **Historical annual withdrawal volumes, central OH** |
| **pwc_ius** | **Prince William Water IUS** | **Built** | **Data center ERU allocations (56 DCs, 2.7% avg demand)** |
| **deq_vwp** | **Virginia DEQ VWP** | **Built** | **Water withdrawal permits (ArcGIS layers 192/193)** |

### Key Architecture Decision: Water Data Source Strategy
Data centers discharge cooling water to municipal sewer systems, not directly to surface water.
Individual data center VPDES permits (e.g., Amazon's VAR052xxx) are stormwater-only permits
with no flow measurements. To track actual water usage, the pipeline monitors receiving
wastewater treatment plants via EPA ECHO DMR data. Target permits are configured in
`config.py` under `epa_echo_target_permits`.

### Data Source Tiers (identified Feb 2026, updated May 2026)

**Tier 1 — Direct water metrics (highest value):**
- EPA ECHO DMR flow data from receiving WWTPs (currently implemented)
- Loudoun Water ACFRs — aggregate data center water sales (~1.6B gal/yr in 2023)
- Ohio EPA General Permit OHD000001 — once finalized, requires DMR from data centers directly
- Prince William Water Industrial User Survey — data center ERU allocations
- ODNR Water Withdrawal Facility Viewer — annual facility-level withdrawal volumes
- **Virginia HB 496 / SB 553 (ENACTED 2026)** — utilities must report monthly aggregate water deliveries to data centers; effective ~July 1, 2026. Reporting channel (SWCB/DEQ vs. local zoning records) to be confirmed before scraper build-out — see backlog.

**Tier 2 — Permit metadata and facility discovery:**
- EPA ECHO NAICS 518210 search — discover data center regulatory footprints
- EPA FRS cross-referencing — link facilities across 90+ EPA databases
- Ohio EPA ArcGIS NPDES permits — searchable by SIC code 7374
- Virginia DEQ ArcGIS VWP layers 192/193 — water withdrawal permits

**Tier 3 — Context and projections:**
- Central Ohio Regional Water Study (2025) — demand projections to 2050
- JLARC Data Centers in Virginia report (2024)
- EIA Form 923 — power plant cooling water for indirect footprint
- USGS county-level water use estimates (every 5 years)

### Reference datasets (curated JSON, served by the dashboard)

The dashboard reads seven curated reference files independent of the scraper pipeline. Two were added July 2, 2026 to turn the CWA tab (now the **"Water Cases"** tab) into a full federal water-law mapping:
- `data/reference/water_authorities.json` — the **statutory-readings registry**: 20 "readings" (specific statutory hooks) across CWA, SDWA, TSCA, RCRA, and the Rivers & Harbors Act, each with `reading_id`, section/agency, what it historically covered, `dc_applicability` (how it could reach a data-center fact pattern), and `example_case_ids`. Every case in `cwa_investigations.json` carries an `authorities` list of reading_ids (overlap intentional — one fact pattern can trigger several readings); a case's statute pills are **derived** from those ids at render time (`_case_statutes`), never stored, so they can't drift. Rendered as the tab's Part 1 toolkit (anchors `#reading-<id>`); statute filter + pills in both apps. Migration script: `scripts/annotate_water_authorities.py` (historical, 2026-07-02) — new cases ship `authorities` inline. Schema/referential integrity is test-enforced (`TestWaterAuthoritiesSchema`). **Part 1 toolkit UX (2026-07-07):** 20 readings across 5 statutes was a long scroll to reach e.g. RHA at the bottom — each statute is now a collapsed-by-default `<details>` accordion (`.statute-group`), with a jump-nav row of statute pills above them (`.statute-jumpnav`/`.statute-jump`) that opens the target statute via `onclick` before the browser's native anchor-scroll lands on it, so any single act is one click away regardless of scroll position (`_build_authorities_html`).
- `data/reference/dc_water_conflicts.json` — **18 named data-center sites with documented water issues or community pushback** (The Dalles secrecy fight, xAI Memphis, Meta Newton County wells, Tucson Project Blue rejection, PW Digital Gateway (voided 2026), AWS Lake Anna, Amazon Boardman, Bessemer, Charlotte moratorium, …), each mapping the fact pattern to `applicable_readings` (reading_id + per-site "how" + analogous historical case_ids) plus `related_case_ids` and sources. Rendered as Part 4 of the Water Cases tab (anchors `#site-<site_id>`); web-verified July 2026 (`TestDcWaterConflictsSchema`).

The original three:
- `data/reference/legislation.json` — 53 state/federal/local entries (June 10, 2026 additions: ID H 895, the first enacted state law restricting consumptive data-center cooling water; NY S10642/A11560, the first statewide DC moratorium to pass a legislature, awaiting Hochul; Denver CB 26-0431 local moratorium; failed CO SB26-102, WI AB 840, and vetoed ME LD 307; VA SB 417 reclaimed-water grant condition, unverified. June 27, 2026 additions: IA HF 2690 — quarterly DNR water + IUC energy reporting and a separate data-center electric tariff, introduced, the first Iowa-HF2690 entry; CT SB 245 — would have repealed Connecticut's data-center tax incentives and added clean-energy/sustainability conditions, failed on the Senate calendar, the first Connecticut entry): bills (introduced/enacted/failed), agency rulemakings (OH EPA OHD000001 draft general permit), and major local zoning actions (Loudoun ZOAM 2025). Each enriched with timeline, recent news, public sentiment, and tagged general principles. Verified entries are flagged `verified: true`; lower-confidence entries carry a `status_detail` note to re-verify the bill number against the legislature's bill lookup. **Principle tags are a closed 13-value taxonomy** (keys of `dashboard.LEGISLATION_PRINCIPLE_DESCRIPTIONS`, test-enforced); the tab leads with a computed "Key principles across all bills" panel (`_legislation_principles_summary` / `_build_principles_summary_html` — counts + enacted counts + example-bill anchor links per tag) and filters by principle / status / level / scope in both the Streamlit app and the static site.
- `data/reference/cwa_investigations.json` — 93 cases across four categories (July 6, 2026 additions: 5 new cases — Google's Van Buren Township, MI §404/EGLE wetlands permit fight (Project Cannoli, 13.55 acres), MCEA v. Pine Island, MN's state-environmental-review TRO against Project Skyway (Google anchor tenant), the $450M multi-state Chemours PFAS consent decree (first joint CWA/TSCA/RCRA hyperscaler-adjacent chemical-supply-chain settlement), the Westchester Joint Water Works NY SDWA filtration consent decree, and the CJT Group GA SDWA §1431 emergency order — plus an outcome/sources update to `QTS-Fayetteville-GA-2024` tracking its May 2026 escalation to a formal §505(b) citizen-suit notice; prior count was 88) (July 2, 2026 expansion added 10 historical non-CWA cases — SDWA: Flint §1431, Trinity American v. EPA, US v. Alisal receivership, Edwards sole-source-aquifer designation, the 1999 UIC Class V rule; TSCA: DuPont Washington Works §8(e), 3M 2006, the §8(a)(7) PFAS reporting rule; RCRA: Interfaith v. Honeywell; RHA: US v. Republic Steel 1960 — and gave every case an `authorities` reading_ids list; prior count was 78) (second June 10, 2026 pass added: the 2026 §404 Nationwide Permit 39 reissuance expressly enumerating data centers, the SDC ATLA Douglas County GA §404/§401 with ~1 mile of stream impacts, the Homer City PA draft NPDES for the 4.4 GW DC power plant, Meta Richland Parish LA's unmonitored 23 MGD authorization, and the Bessemer AL capacity fight): `datacenter` (21 direct hyperscaler / contractor CWA actions and permit matters, anchored by the 2026 $20.5M Amazon Boardman nitrate settlement — the first eight-figure direct-hyperscaler water settlement — the Amazon/Walbridge New Carlisle IN §404/§401 wetlands cease-work, Google's §404 individual permit applications (Project Raspberry VA, Project Loch VA, Project Cannoli MI, Port of Little Rock AR — the AR application is the largest §404 wetland footprint in any active DC permit at 16.8 acres); June 10, 2026 additions: the **AWS Lake Anna VPDES cooling-discharge draft permit** — the first direct-to-surface-water hyperscaler cooling-water permit in VA, public hearing 2026-06-09 — the Quantum Loophole Frederick MD frac-out enforcement (escalated to MD AG referral), Google Fort Wayne IN isolated-wetland *state* permit (illustrating the post-Sackett federal-jurisdiction gap), and Microsoft Mount Pleasant WI wetland individual permitting), `adjacent` (16 — xAI Colossus / Memphis, state groundwater-withdrawal and zoning/recharge-area fights, the QTS Fayette GA unbilled-water metering gap, TransGas Adams Fork WV §404 citizen suit, MCEA v. Pine Island MN Project Skyway; June 10 additions: Meta Newton County GA well failures, Milwaukee Riverkeeper / Racine WI water-records suit, Corpus Christi–Sinton TX Evangeline Aquifer fight, Hood County TX failed moratoriums, Charlotte NC drought moratorium, Microsoft Caledonia WI rezoning withdrawal), `industrial` (39 cooling-water, pretreatment, PFAS, POTW consent-decree cases including Fort Smith AR §301(a), Greenidge Generation NY §316(a)/(b), and the July 2026 Chemours/Westchester JWW/CJT Group SDWA-TSCA additions), and `precedent` (17 — Sackett, Maui, Loper Bright, SF v EPA, Lewis v US, Port of Tacoma, CERF v. Naples). **Schema (since 2026-06-10):** every case also carries `case_type` (10-value project-type taxonomy = keys of `dashboard.CWA_CASE_TYPE_LABELS`, the primary filter axis), `cwa_applied` (applied / pending / not-applied), `cwa_instrument` (one-line header label), and — for every pending/not-applied case — `cwa_pathway` (how the statute(s) *could* reach the fact pattern) plus `analogous_cases` (case_ids of historic examples, rendered as in-page anchor links on the cards). Schema is enforced by tests in `tests/test_dashboard.py`; the original migration script is `scripts/annotate_cwa_schema.py`. The CWA tab leads with a computed "What this record tells data centers" panel (`_cwa_datacenter_insights` / `render_cwa_datacenter_insights`, computed over the `datacenter` subset) that surfaces the permittee-shield and construction-stormwater patterns and frames the operational exposure as the *receiving WWTP's* NPDES permit — the permits the pipeline already tracks via EPA ECHO. **Card UX (2026-07-06):** each card is collapsed by default to the head, classification pills, and takeaway; violation, outcome, the "How statutes could apply" breakdown (one link per mapped statutory reading, not a single blended sentence), full statute citation, and sources all live behind one `<details>` toggle, matching Part 4's conflict-site card density. **Insights-panel UX + statute breadth (2026-07-07):** the panel itself is now collapsed by default too (it was the largest always-visible block before the Part 1-4 sub-tabs) and gained a 5th bullet from a new `_cwa_statute_breadth_insight()` — every earlier bullet was CWA-only despite the tracker covering 5 statutes; the new one scans the *whole* datacenter+adjacent record (historical + potential, not just resolved enforcement) and finds SDWA — not the CWA — is the more common federal hook for supply-side fights (aquifer depletion, well failures, PWS strain) with no permitted discharge in the picture.
- `data/reference/company_water_claims.json` — 34 water-themed claims from 17 operators with delivered-vs-promised adjudication where independent assessments exist (June 27, 2026 additions: first-party water statements from Switch, EdgeConneX, Vantage, and Compass).
- `data/reference/water_news.json` — 34 curated headlines on data center water use, regulation, enforcement, and solutions (News tab), each with `date`/`outlet`/`summary`/`tags` (closed 6-value taxonomy: regulation, enforcement, solutions, research, data, policy) and an optional `cross_ref_tab`/`cross_ref_note` linking to a bill/case/site already tracked elsewhere. July 6, 2026 additions: Amazon's first-ever aggregate DC water-use disclosure (2.5B gal/yr, 2025), an ITIF report on direct-vs-indirect DC water consumption, Indiana's county-level moratorium wave, and the Spartanburg County SC and NY DEC-permit-moratorium stories.
- `data/reference/water_solutions.json` — 18 solutions to data-center water challenges (Solutions tab) grouped into three categories — `policy` (state/federal mandates), `utility` (utility/infrastructure programs), `technology` (industry cooling/operational practice) — each with `status` (deployed/pilot/proposed) and `actor_type` (state/federal/utility/industry). July 6, 2026 additions: Nvidia's Vera Rubin DSX near-zero-water cooling reference design (technology) and the AWS/Greater Western Water recycled-water connection in Melbourne (utility) — the first data-center recycled-water utility contract of its kind in Victoria, Australia.

### Legislative pressure to watch (not yet enacted)

Several pending federal bills would, if enacted, become Tier 1 data sources nationally:
- US S. 4214 (Sanders / AOC) — federal AI data center construction moratorium
- US S. 3682 (Van Hollen Power for the People Act) — FERC-mediated cost allocation and data-center load queues
- US HR 6984 (Menendez Data Center Transparency Act) — EPA + EIA semi-annual public reporting
- US HR 8488 (McIver) — 180-day pre-construction site disclosure with FTC enforcement

See `backlog.md` for detailed scraper plans, sample prompts for each source, and the May 2026 External Tracker Survey (10 top-priority ideas borrowed from existing trackers like WRI Aqueduct, FracTracker, PEC ArcGIS, and EIA Form 923).
