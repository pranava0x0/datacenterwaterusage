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
  - **Subresource Integrity (SRI) on every third-party CDN asset.** `pages/index.html` pins `sha384` hashes for the stlite CSS (`<link integrity>`) and the stlite loader module (import-map `integrity`, enforced on Chromium 127+, gracefully ignored elsewhere). Caveat: the stlite loader is a small stub that pulls the ~15 MB Pyodide/Streamlit runtime from the CDN at runtime — those chunks are version-pinned (`@1.7.3`, immutable) but not yet SRI-covered; full coverage means self-hosting (backlog). To regenerate a hash: `curl -sL <url> | openssl dgst -sha384 -binary | openssl base64 -A`, then re-verify it twice (a partial download yields a wrong hash that fails closed and blanks the live site).
  - **Neutralize CSV formula injection.** `storage/csv_writer.py` prefixes any string cell starting with `= + - @ \t \r` with `'` (`_neutralize_formula`) so a scraped value can't execute when the export is opened in Excel/Sheets.
  - **No secrets or PII in committed data.** `local_file_path` is stored repo-relative (see SEC-001 in `issues.md`); never commit absolute home paths, tokens, or credentials.
- When a security item is fixed, add a regression test (e.g., `tests/test_csv_writer.py`) and note it in `errors.md`/`issues.md` so it can't silently regress.

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
- **Dashboard**: streamlit + plotly (Phase 1), Observable Framework planned (Phase 2)
- **Testing**: pytest + pytest-asyncio (406 tests)

### Key Directories
- `scrapers/` — one module per government portal, organized by state
- `extractors/` — PDF text extraction, keyword matching, entity extraction
- `models/` — dataclasses for DocumentRecord
- `storage/` — CSV/JSON writers, SQLite state manager, file download manager
- `utils/` — HTTP client, Playwright browser manager, user-agent pool, logging config
- `data/downloads/` — raw downloaded files (gitignored)
- `data/output/` — structured CSV/JSON results
- `data/state/` — SQLite database for scraper state

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

The dashboard reads three curated reference files independent of the scraper pipeline:
- `data/reference/legislation.json` — 31 state/federal/local entries: bills (introduced/enacted/failed), agency rulemakings (OH EPA OHD000001 draft general permit), and major local zoning actions (Loudoun ZOAM 2025). Each enriched with timeline, recent news, public sentiment, and tagged general principles. Verified entries are flagged `verified: true`; lower-confidence entries carry a `status_detail` note to re-verify the bill number against the legislature's bill lookup.
- `data/reference/cwa_investigations.json` — 49 cases across four categories: `datacenter` (9 direct hyperscaler / contractor CWA actions, anchored by the 2026 $20.5M Amazon Boardman nitrate settlement — the first eight-figure direct-hyperscaler water settlement), `adjacent` (water-relevant data-center actions where the binding enforcement sits *outside* the CWA — e.g. the xAI Colossus / Memphis greywater-plant case, where the active federal suit is Clean Air Act and the water piece is a paused voluntary commitment), `industrial` (cooling-water, pretreatment, PFAS, POTW consent decrees), and `precedent` (Sackett, Maui, Loper Bright, SF v EPA, and the Lewis v US 5th Circuit Sackett-application). The CWA tab leads with a computed "What this record tells data centers" panel (`_cwa_datacenter_insights` / `render_cwa_datacenter_insights`, computed over the `datacenter` subset) that surfaces the permittee-shield and construction-stormwater patterns and frames the operational exposure as the *receiving WWTP's* NPDES permit — the permits the pipeline already tracks via EPA ECHO.
- `data/reference/company_water_claims.json` — 29 water-themed claims from 13 operators with delivered-vs-promised adjudication where independent assessments exist.

### Legislative pressure to watch (not yet enacted)

Several pending federal bills would, if enacted, become Tier 1 data sources nationally:
- US S. 4214 (Sanders / AOC) — federal AI data center construction moratorium
- US S. 3682 (Van Hollen Power for the People Act) — FERC-mediated cost allocation and data-center load queues
- US HR 6984 (Menendez Data Center Transparency Act) — EPA + EIA semi-annual public reporting
- US HR 8488 (McIver) — 180-day pre-construction site disclosure with FTC enforcement

See `backlog.md` for detailed scraper plans, sample prompts for each source, and the May 2026 External Tracker Survey (10 top-priority ideas borrowed from existing trackers like WRI Aqueduct, FracTracker, PEC ArcGIS, and EIA Form 923).
