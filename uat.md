# UAT Baseline — Data Center Water Use Tracker

_Created: 2026-05-26_
_Last run: 2026-06-01_

## Project Info
- **Stack**: Streamlit dashboard (Python), `streamlit>=1.33`, plotly, pandas
- **Dev server**: `python3 -m streamlit run dashboard.py --server.port 8501 --server.headless true --browser.gatherUsageStats false`. As of 2026-06-01 a `.claude/launch.json` ("dashboard" config, port 8501) exists, so the Preview MCP can boot/reuse the server directly — free port 8501 of any Bash-launched instance first, since the launch.json pins the port.
- **Entry point**: `dashboard.py` (~1370 LOC, single-file Streamlit app)
- **Live URL**: <https://pranava0x0.github.io/datacenterwaterusage/> (stlite/WASM, slow cold start)
- **Key tabs / sections**:
  - **Legislation** (homepage / default tab)
    - Eager: Data Center Water Legislation Tracker (`st.dataframe`, 14 bills)
    - Lazy toggle: Policy & Disclosure Timeline (10 events)
    - Lazy toggle: Company Water Claims (29 verbatim quotes, 13 companies)
  - **Data**
    - Eager: data freshness, inline filter popover, hero metrics, flow chart (Plotly), Local Context cards
    - Lazy toggle: Records by Source chart, Seasonal Heatmap, Transparency Scorecard, Per-Query Explainer, Records table

## Critical Flows (run every time)
1. **Load Legislation tab (homepage)** → see Legislation Tracker render with all 14 bills.
2. **Toggle Timeline + Claims** → both panels render below the tracker.
3. **Switch to Data tab** → hero metrics + flow chart visible immediately; Local Context cards render eagerly.
4. **Toggle a Data tab lazy panel** (e.g., Transparency Scorecard) → content materializes; subsequent reruns (filter change) keep it visible.
5. **Resize to mobile/tablet** → reload; layout adapts without horizontal scroll.

## Sections & Last Tested
| Section | Last Tested | Notes |
|---------|-------------|-------|
| Legislation Tracker | 2026-05-26 | High-priority cleanup needed — columns / mobile cards (UAT-002..005, UAT-007) |
| Policy & Disclosure Timeline | 2026-05-26 | Renders cleanly when toggled on |
| Company Water Claims | 2026-05-26 | Cards bleed together (UAT-008..011) |
| Data tab Hero + Flow Chart | 2026-05-26 | Renders cleanly at desktop; verify mobile |
| Local Context cards | 2026-05-26 | Renders well at all viewports |
| Lazy toggles (general) | 2026-05-26 | Working as designed — eval confirms zero-render-until-toggled |

## Known Stable Areas
- Lazy-loading machinery (`st.toggle` gating) — confirmed via DOM diff before/after toggle.
- Plotly flow chart at desktop.
- Local Context household-equivalent cards.
- `st.tabs` switching.
- GitHub Pages deploy pipeline + CI workflow.

## Known Flaky / Unstable Areas
- **Device classification** — fixed in UAT-006 (`window.parent.innerWidth`); round 4 (2026-06-01) re-confirmed 375→mobile, 768→tablet, 1280→desktop after reload. Still the most reload-sensitive area: a resize needs a page reload before the class updates.
- **Plotly flow chart first paint** — on a freshly-switched Data tab the chart SVG mounts a frame before Plotly draws its traces, so the *first* screenshot can look blank. This is a screenshot-timing artifact, **not** a bug — verify by eval'ing for trace geometry (`path.js-line`, `path.point`) rather than trusting the first capture. Confirmed real geometry present at 375px in round 4.
- **Legislation tracker** — RESOLVED: now bordered HTML cards at every viewport (desktop included), not a dataframe. No horizontal scroll at any width (UAT-007, UAT-017).
- **Company Water Claims rendering** — custom HTML cards are dense and lack visual hierarchy (UAT-008..011).

## Exploration Notes
- The streamlit-js-eval component runs inside a same-origin iframe whose `window.parent.innerWidth` correctly returns the host viewport. Replacing `window.innerWidth` with `window.parent.innerWidth` (with a try/catch fallback) fixes both UAT-001 (the flicker) and UAT-006 (tablet misclassification) in one go.
- `_legislation_rows` returns all fields; the render function picks the display subset. This separation keeps the tests on the data shape unchanged when columns are dropped from the UI.
- 18 of 29 water claims have a `project_id` tied to a sibling-repo project; the sibling dashboard doesn't expose a deep-link by project_id today, so the easiest win is surfacing the id as a tag and trusting the user to recognize it.
- Streamlit's `st.container(border=True)` is the right primitive for the claim cards — it gives a subtle outlined box with built-in padding that we currently fake with custom CSS.
- Streamlit semantic boxes (`st.success` / `st.warning` / `st.error`) are the right primitive for the delivered-vs-promised status box — they carry color semantics consistent with the rest of the Streamlit ecosystem.
