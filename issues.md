# Issues Log

_Last updated: 2026-05-26_

UAT run 2026-05-26 covered desktop (1280×900), tablet (768×1024), and mobile (375×812) on the local Streamlit preview. All 12 issues found in that run have been resolved in the same session.

---

## Open Issues

_None._

---

## Resolved Issues

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
