# Issues Log

_Last updated: 2026-06-01_

UAT round 1 (2026-05-26) covered desktop / tablet / mobile and found UAT-001..UAT-012. UAT round 2 (2026-05-26) focused on the Data tab and surfaced UAT-013 / UAT-014. UAT round 3 (2026-05-26) tested interactions and mobile depth, surfacing UAT-015 / UAT-016. UAT round 4 (2026-06-01) re-ran all three viewports via the Preview MCP and found **no new functional bugs** — Legislation (cards at every viewport), Data (hero + flow chart), and the three tabs all render cleanly with no horizontal scroll at 375 / 768 / 1280 px. One documentation drift (UAT-017) was corrected. All 17 issues are resolved.

---

## Open Issues

_None._ SEC-001 (the home-directory PII leak) is now **fully resolved and verified** — a fresh clone of the public repo on 2026-06-01 found zero occurrences of the leaked path in reachable history (details in the SEC-001 entry below).

---

## Resolved Issues

### [UAT-017] uat.md baseline stale — claimed desktop legislation renders a dataframe
- **Severity**: low (documentation drift, not a user-facing bug)
- **Page/Section**: `uat.md` baseline vs. `dashboard.py:render_legislation_tracker`
- **Discovered**: 2026-06-01 (round 4)
- **Resolved**: 2026-06-01
- **Status**: resolved
- **Description**: `uat.md` described the Legislation Tracker as a horizontal-scroll `st.dataframe` on desktop with card layout only on mobile/tablet. The code was since unified — `render_legislation_tracker` does `del is_mobile, is_tablet` and renders bordered HTML `<details>` cards at **every** viewport. A round-4 eval confirmed no `stDataFrame` element on the Legislation tab at 1280 px and no horizontal scroll at any width. Risk was a future UAT run "expecting" a dataframe and flagging a false regression.
- **Fix**: Updated `uat.md` to describe the unified card layout, added the Plotly async-paint screenshot caveat (a freshly-switched Data tab can screenshot blank for one frame before Plotly draws — verify trace geometry via eval, not the first screenshot), and recorded that `.claude/launch.json` now exists so the Preview MCP can boot the dashboard for UAT.

### [SEC-001] Developer home-directory path leaked into committed dataset
- **Severity**: medium (no credentials; mild PII — exposed macOS username + iCloud Drive layout)
- **Page/Section**: `data/output/results.csv` and `data/output/results.json`
- **Discovered**: 2026-05-26 (security audit)
- **Resolved**: 2026-05-26 (HEAD scrub + code fix); history rewrite completed and **verified clean 2026-06-01**.
- **Status**: resolved — verified against the public remote.
- **Description**: The `local_file_path` column in scraped records was being stored as the absolute path on disk — e.g. `<home>/Library/Mobile Documents/com~apple~CloudDocs/<projects-dir>/data/downloads/ohio/columbus/RFQ…`. Rows from the `oh_columbus_legistar` scraper carried this prefix, exposing the developer's home-directory username, the fact that the repo lived on iCloud Drive at one point, and the local working-directory name. Not a credential, but personally identifiable.
- **Fix**:
  - `scrapers/base.py`: added `_to_repo_relative_path()` helper. `_build_record` now normalizes any absolute `local_path` to a project-relative path before it lands in `DocumentRecord.local_file_path`. Falls back to stripping everything before `data/downloads/` for paths that aren't anchored under the project root (e.g., the historical iCloud paths).
  - `data/output/results.csv` / `results.json`: scrubbed the affected rows in-place (`<home>/.../data/downloads/...` → `data/downloads/...`).
  - **History rewrite: done.** The old pre-rewrite HEAD `99c8bba` is no longer an ancestor of `main` and is absent from a fresh clone — the classic signature of a completed filter/force-push.
- **Verification (2026-06-01)** — fresh `git clone` of `pranava0x0/datacenterwaterusage` + pickaxe (`git log --all -S`) across all 44 commits, all refs, all tags:
  - `/Users/pranava` and `/Users/` → **0 occurrences anywhere** in history (the real username path is gone everywhere).
  - `com~apple` / `CloudDocs` / `Mobile Documents` in `data/output/` → **0 commits**. The data files are clean across their entire history.
  - The sole repo-wide hit for those markers is **this issues.md file** (commit `3ac1a38`), where the iCloud fragment is quoted with a `<home>` placeholder as documentation — it never contained the real username, so it is not itself a leak.
  - `99c8bba` is **not present** in a fresh clone (fully orphaned / not served).
  - **Residual (optional, low value):** GitHub may still resolve a dangling commit by its exact 40-char SHA from server-side cache until it GCs. Those SHAs are not enumerable and the repo has no forks, so practical exposure is ~nil. If desired, a GitHub Support request can force server-side GC; otherwise no action needed.

### [UAT-016] Vestigial `mobile_state` / `mobile_date` widget keys
- **Severity**: low (code smell)
- **Page/Section**: Data tab → Filter popover
- **Discovered**: 2026-05-26 (round 3)
- **Resolved**: 2026-05-26
- **Status**: resolved
- **Description**: The state multiselect and date-range picker inside `render_inline_filters` had keys named `mobile_state` and `mobile_date` — leftover from when inline filters were used only on mobile. Since the tab restructure moved this popover into the Data tab for all viewports, the names were misleading.
- **Fix**: Renamed the keys to `data_state_filter` / `data_date_filter` to reflect their actual scope. Also updated the function's docstring.

### [UAT-015] Flow chart shows "new text" placeholder annotation on mobile
- **Severity**: high
- **Page/Section**: Data tab → Monthly WWTP Flow chart, mobile (and any layout where `cfg["show_legend"]` is False)
- **Discovered**: 2026-05-26 (round 3)
- **Resolved**: 2026-05-26
- **Status**: resolved
- **Description**: `render_flow_chart` called `fig.add_hline(..., annotation_text=None, annotation_position="top right")` on mobile. Plotly does not treat `annotation_text=None` as "no annotation" — it still creates the annotation and silently fills the text with its internal placeholder string `"new text"`. End users saw "new text" rendered in the top-right corner of the chart on every mobile cold load.
- **Fix**: Build the `add_hline` kwargs conditionally — only attach `annotation_text` and `annotation_position` when there is actual text to show. Mobile now renders the dashed permit-limit line with no annotation label. Verified at 375px: no "new text" string anywhere in the page (`document.body.innerText.includes('new text') === false`).

### [UAT-014] Records table cells show literal "None" for missing values
- **Severity**: medium
- **Page/Section**: Data tab → Records table (when toggled on)
- **Discovered**: 2026-05-26 (round 2)
- **Resolved**: 2026-05-26
- **Status**: resolved
- **Description**: Many records have NULL Facility / document_date / Water Metric, which `st.dataframe` was rendering as the string "None" — looked like data-quality noise. e.g. multiple OH rows displayed "None" in three of five columns.
- **Fix**: `render_data_table` now `fillna("—")` + replaces "None"/"nan"/"" with em-dash before rendering. `dashboard.py:render_data_table`.

### [UAT-013] Records table column headers inconsistent (snake_case mixed with Title Case)
- **Severity**: high
- **Page/Section**: Data tab → Records table
- **Discovered**: 2026-05-26 (round 2)
- **Resolved**: 2026-05-26
- **Status**: resolved
- **Description**: Only three columns had friendly names via `column_config` ("Facility", "Water Metric", "Flow (MGD)"). The other three (`state`, `document_date`, `permit_number`) showed their raw snake_case schema names next to the renamed ones. Inconsistent and amateurish.
- **Fix**: `render_data_table` now applies `column_config` to every visible column from a single `column_titles` dict (State / Facility / Document Date / Water Metric / Flow (MGD) / Permit #), with sensible width hints per column. Also adds `hide_index=True` so the integer-index column no longer renders.

### [UAT-001] Title flickers mobile → desktop on cold render
- **Severity**: low
- **Page/Section**: All tabs, all viewports
- **Discovered**: 2026-05-26
- **Resolved**: 2026-05-26
- **Status**: resolved
- **Description**: On initial render the title briefly showed "DC Water Tracker" before streamlit-js-eval reported the host viewport, then snapped to "Data Center Water Use Tracker" on desktop.
- **Fix**: Resolved as a side-effect of UAT-006 — `window.parent.innerWidth` reports the host viewport directly so the classification is correct from the first JS callback. (`utils/device.py`)

### [UAT-002] "Verified" column visible in UI
- **Severity**: high
- **Page/Section**: Legislation tab → Legislation Tracker table
- **Discovered**: 2026-05-26
- **Resolved**: 2026-05-26
- **Status**: resolved
- **Description**: Table showed a Yes/Unconfirmed Verified column.
- **Fix**: Display projection in `render_legislation_tracker` builds only `{Bill, Status, Summary, Source}`. The `verified` field stays in `legislation.json` and in `_legislation_rows` (which is what tests check) — backend-only.

### [UAT-003] "Jurisdiction" column redundant
- **Severity**: high
- **Page/Section**: Legislation tab → Legislation Tracker table
- **Discovered**: 2026-05-26
- **Resolved**: 2026-05-26
- **Status**: resolved
- **Description**: bill_id already encodes the state ("VA HB 496", "US HR 6984"), so Jurisdiction was duplicated.
- **Fix**: Dropped from display projection. (`dashboard.py:render_legislation_tracker`)

### [UAT-004] "Scope" column redundant
- **Severity**: high
- **Page/Section**: Legislation tab → Legislation Tracker table
- **Discovered**: 2026-05-26
- **Resolved**: 2026-05-26
- **Status**: resolved
- **Description**: All bills include water; the column added no signal.
- **Fix**: Dropped from display projection.

### [UAT-005] "Summary" column truncated to ~50 chars
- **Severity**: high
- **Page/Section**: Legislation tab → Legislation Tracker table
- **Discovered**: 2026-05-26
- **Resolved**: 2026-05-26
- **Status**: resolved
- **Description**: Default 35px row height clipped the Summary cell to roughly one line.
- **Fix**: Added `row_height=70` to `st.dataframe` and widened the Summary column. Two+ lines of summary now visible per row.

### [UAT-006] Tablet viewport misclassified as MOBILE
- **Severity**: high
- **Page/Section**: All tabs, tablet viewport
- **Discovered**: 2026-05-26
- **Resolved**: 2026-05-26
- **Status**: resolved
- **Description**: streamlit-js-eval was returning the component iframe's own `window.innerWidth` (~600px), causing the classifier to flip to MOBILE at 768×1024.
- **Fix**: Changed the `js_expressions` in `utils/device.py:get_viewport_width()` to an IIFE: `(()=>{try{return window.parent.innerWidth;}catch(e){return window.innerWidth;}})()`. Bumped the component `key` from `"viewport_width"` to `"viewport_width_parent_v1"` to force streamlit-js-eval to remount the iframe with the new expression (the old key was reusing the cached iframe URL). Verified at all three viewports: 1280 → desktop, 768 → tablet, 375 → mobile.

### [UAT-007] Mobile table requires horizontal scroll
- **Severity**: high
- **Page/Section**: Legislation tab → Legislation Tracker, mobile
- **Discovered**: 2026-05-26
- **Resolved**: 2026-05-26
- **Status**: resolved
- **Description**: 7-column dataframe overflowed horizontally at 375px.
- **Fix**: `render_legislation_tracker(is_mobile, is_tablet)` now branches: mobile/tablet renders each bill as a `st.container(border=True)` card (bill_id + status header row, summary body, sponsor + Source link caption). Desktop keeps the trimmed dataframe. Added `_render_bill_card` helper.

### [UAT-008] Company Water Claims cards bleed into each other
- **Severity**: high
- **Page/Section**: Legislation tab → Company Water Claims
- **Discovered**: 2026-05-26
- **Resolved**: 2026-05-26
- **Status**: resolved
- **Description**: 29 claims rendered with no visual card boundary.
- **Fix**: `_render_water_claim_card` now wraps each claim in `st.container(border=True)`. Clear separation between claims; tight internal spacing.

### [UAT-009] Tiny attribution text under each claim
- **Severity**: medium
- **Page/Section**: Legislation tab → Company Water Claims
- **Discovered**: 2026-05-26
- **Resolved**: 2026-05-26
- **Status**: resolved
- **Description**: Custom HTML span with explicit font-size/color overrode Streamlit's native typography.
- **Fix**: Replaced the span with `st.caption()` for native muted-text styling.

### [UAT-010] Claims lack project / site context
- **Severity**: medium
- **Page/Section**: Legislation tab → Company Water Claims
- **Discovered**: 2026-05-26
- **Resolved**: 2026-05-26
- **Status**: resolved
- **Description**: 18 of 29 claims had a `project_id` (e.g., `oracle-abilene-tx`) but it was never displayed.
- **Fix**: When `project_id` is present, the attribution caption appends `Project: <id>` so the site context is visible per-claim.

### [UAT-011] Delivered-vs-promised box visual treatment unclear
- **Severity**: medium
- **Page/Section**: Legislation tab → Company Water Claims
- **Discovered**: 2026-05-26
- **Resolved**: 2026-05-26
- **Status**: resolved
- **Description**: Custom HTML div with a thin left border didn't telegraph status at a glance.
- **Fix**: Status is now rendered via semantic Streamlit boxes — `st.success` (delivered), `st.warning` (partial/contested), `st.error` (shortfall), `st.info` (anything else). Status word is bold and capitalized. Visually unmistakable.

### [UAT-012] Mobile Legislation tab too long
- **Severity**: medium
- **Page/Section**: Legislation tab, mobile
- **Discovered**: 2026-05-26
- **Resolved**: 2026-05-26
- **Status**: resolved
- **Description**: Eager 14-row horizontal-scroll dataframe was bulky on mobile.
- **Fix**: Resolved by UAT-007 — the vertical card layout is more compact per bill, eliminates the horizontal scroll, and scans naturally. Verified at 375×812: no horizontal scroll (`document.body.scrollWidth === window.innerWidth`).
