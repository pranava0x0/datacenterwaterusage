# Spec D — States & Localities tab: new state/county/city laws, policies, proposals

## Purpose

The Legislation tab answers "what instruments exist"; nothing answers "what is my state doing, and what just changed". New tab (label "States & Localities", `data-tab="states"`) with three sections:

1. **What's new** — instruments and local actions with movement in the last 120 days, newest first: jurisdiction, instrument/action, status pill, one-line summary, date of latest action, link to the full card (registry anchor for instruments).
2. **State rollup** — one card per state that has any tracked activity: counts by status (enacted / introduced / failed), principle chips (top 2–3), newest-action date, links into the Legislation tab filtered cards. Rendered as a responsive CSS grid ordered by newest action. States with no activity are absent, and a one-line note says the map is activity-based, not exhaustive.
3. **County & city actions** — the layer the Legislation tab underweights (6 local instruments today). Backed by a new mirrored dataset (Spec F) of county/city moratoriums, ordinances, and zoning actions that touch water, rendered as a filterable table: jurisdiction, state, action type, status, date, water angle, source link.

## Data changes

1. `data/reference/legislation.json` — new state/local instruments the research sweep verifies (existing schema; `instrument_type: local-ordinance` for county/city measures significant enough to track as instruments — the enacted, the litigated, the first-of-kind).
2. New `data/reference/local_actions.json` (Spec F defines provenance): `{last_updated, source_repo, note, actions: [...]}` where each action has `action_id`, `jurisdiction`, `state` (two-letter), `action_type` (closed taxonomy: `moratorium`, `ordinance`, `zoning-amendment`, `resolution`, `permit-denial`), `status` (`active`, `expired`, `proposed`, `rejected`, `superseded`), `date` (YYYY-MM), `water_related` (bool) + `water_angle` (one line, empty allowed when false), `summary`, `source_url`. Only water-relevant actions render on this tab by default with a toggle to show all mirrored actions.
   - v1 keeps these records **out of the registry** (no anchors, no cross-ref targets) — they're a mirrored table, not curated records. Promotion to a registry kind is a backlog item with the integrity work it implies.
3. `refdata/loaders.py` + `taxonomies.py`: loader with the same signature-cache pattern; `LOCAL_ACTION_TYPE_LABELS` + `LOCAL_ACTION_STATUS_LABELS` closed taxonomies shipping in the same commit as the data.

## Render changes

- `build_site.py`: new `build_states_tab()`; tab button after Legislation. "What's new" computes from instrument `timeline`/`last_verified` dates + action dates — pure function, unit-tested with a frozen `today` argument (no `datetime.now()` in render logic; pass the date in from the callers).
- `dashboard.py`: matching `render_states_tab()` reusing the same `_build_*` fragments.
- Tab anatomy per DESIGN.md §5: title, one-liner, summary panel (states active / local actions tracked / newest action), filters (state, status, action type), count line, content, last-updated caption.
- llms.txt: one-liner per state rollup entry is too much; add the tab summary + the what's-new list.

## Tests

- Schema tests for `local_actions.json` (taxonomy membership both directions, required fields, state codes valid, dates parse).
- `build_states_tab` emits: every active state card, the what's-new section honoring the 120-day window (frozen-date test both sides of the boundary), the local-actions table rows.
- Both-surface parity: builders shared, no streamlit import in shared paths.

## Out of scope → backlog

- Choropleth/map rendering (needs a geo library or hand SVG map — real work, separate item).
- Registry promotion of local actions (anchors + cross-refs + llms.txt coverage).
- A monitors watch for county agendas (new scraper class).
