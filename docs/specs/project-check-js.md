# Check a project — page-script contract (2026-10-08)

The Python engine is `refdata/precedent.py`; the fragment, CSS and the
server-side result renderer are in `dashboard.py` (`_build_project_check_html`,
`_project_check_css`, `_project_result_html`). The page script
`dashboard._project_check_js()` must reproduce the engine's arithmetic exactly,
from the payload the engine emits, and render results in the same shape the
Python renderer produces for the worked examples.

## Payload (`#project-data`, fetched from `data-src` on the static site, inline on Streamlit)

```
facets:      {facet_id: {dimension, label, description, triggers[], blockers[], weight}}
dimensions:  {dimension_id: label}            (ordered as the form's fieldsets)
activities:  {activity_id: label}            (path order)
roles:       {hook, limit}
statute_order: [codes]
outcomes:    {outcome_id: label}
states:      {code: name}
readings:    [{id,label,statute,section,activities[],role,trigger,triggers[],requires[],jurisdictions[],example_case_ids[],tab,anchor}]
cases:       [{id,label,facets[],outcome_type[],case_type,category,year,cwa_applied,instrument,takeaway,tab,anchor}]
sites:       [{id,label,facets[],issue_types[],location,state,status,tab,anchor}]
instruments: [{id,label,title,jurisdiction,state,level,status,triggers[],requires[],principles[],water_scoped,tab,anchor}]
local_actions: [{id,jurisdiction,state,action_type,status,date,water_related}]
examples:    [{id,name,operator,location,state,status,status_date,mw,mgd,description,facets[],sources[]}]
index:       {vocab[], df[], n_docs, docs:{record_id:{t:[vocab positions], w:[int weights]}}, weight_scale}
stopwords[], min_token_len
constants:   {hyperscale_mw, hyperscale_mgd, lexical_weight, outcome_sample, top_cases, top_sites, top_readings, score_decimals, elsewhere_factor}
```

## Functions the script must expose (the parity test calls them under node)

The IIFE must `return {parseProject, matchProject}` so the test can rewrite
`(function(){` to `const __engine = (function(){` and call:

- `parseProject(text, D)` → `{facets[], matched{facet:[words]}, state, mw, mgd}` —
  mirrors `precedent.parse_project`:
  - tokenize exactly as `refdata.graph.tokenize` (the Explore script already does
    this: non-`[A-Za-z0-9]` → space, lowercase, drop tokens shorter than
    `min_token_len` or in `stopwords`, then unigrams + adjacent bigrams of the
    *surviving* unigrams);
  - a facet fires when any trigger is in the token set and no blocker is;
  - MW: regex `(\d[\d,]*(?:\.\d+)?)\s*(gigawatts?|gw|megawatts?|mw)\b` (case-insensitive, GW ×1000, max of matches);
    MGD: `(\d[\d,]*(?:\.\d+)?)\s*(?:mgd|mg/d|million gallons?\s*(?:per|a|/|each)\s*day)\b`
    and gallons-per-day `(\d[\d,]*(?:\.\d+)?)\s*(gallons?|gal)\s*(?:per|a|/|each)\s*day\b` ÷ 1,000,000 (max);
  - `scale-hyperscale` is added when mw ≥ hyperscale_mw or mgd ≥ hyperscale_mgd;
  - `state`: implement `stateCodeFor(text)` exactly as `precedent.state_code_for`
    (full names, longest first, skip a name preceded by `port|fort|lake|mount|new|west|north|south|east` + space
    unless the name is itself one of the compound state names, skip a name followed by
    ` river| street| avenue| road| county water`; count mentions, a name right after a comma counts 2;
    most mentions wins, ties to the earliest; else a bare two-letter code);
  - facets are returned in payload (taxonomy) order.
- `matchProject(facets, state, text, D)` → the same keys as `precedent.match_project`:
  `facets, state, readings, activities, cases, sites, outcomes, outcome_sample, instruments, local_actions`.
  - `overlap(a, b)`: weighted cosine on binary facet vectors,
    `Σw(shared)/sqrt(Σw(a)·Σw(b))`, rounded to `score_decimals`; shared facets in taxonomy order.
  - cases/sites: `score = round(facet_score + lexical_weight × lexical, score_decimals)` where
    lexical is the TF-IDF cosine the Explore script's `runSearch` computes (query weight
    `count × ln(n_docs/df)`, L2-normalised, dotted with `w/weight_scale`), rounded to
    `score_decimals`, computed only when text is non-blank; keep rows with score > 0,
    sort by (−score, id), take `top_cases` / `top_sites`. Each row carries
    `score, facet_score, lexical, shared`.
  - readings: `overlap(facets, triggers)`; if `state` and `jurisdictions` non-empty and
    state ∉ jurisdictions, `score = round(score × elsewhere_factor)` and `elsewhere = true`;
    keep score > 0, sort by (−score, id), take `top_readings`.
  - activities: union of the kept readings' activities in `activities` key order.
  - outcomes: tally of `outcome_type` over the first `outcome_sample` cases, sorted by
    (−count, outcome id), as `[{outcome, label, count}]`; `outcome_sample = min(outcome_sample, cases.length)`.
  - instruments: those with `state === state`, enacted first then by id; local_actions:
    those in the state, newest `date` first. Both empty when no state.
  - JavaScript float sums must be rounded with the same `score_decimals` before sorting.

## UI behaviour

- The form (`#pcheck-text`, `#pcheck-state`, `#pcheck-mw`, `#pcheck-mgd`, the
  `.pcheck-facet-box` checkboxes, `#pcheck-run`, `#pcheck-clear`, `.pcheck-example`
  buttons) already exists in the fragment.
- Typing in the textarea (debounced ~250 ms) re-parses: tick the recognised facets,
  set the state select if the text names one and the select is still "Not stated",
  fill MW/MGD if parsed and the inputs are empty, and write a one-line summary into
  `#pcheck-read` ("We read: wells, groundwater → On-site groundwater wells; …") with the
  matched words. Manual unticks must survive the next re-parse of unchanged text
  (track which boxes the reader touched). When an edit stops naming the state, MW or
  MGD the parser had filled in, clear that control if it still holds the parsed value;
  a value the reader set by hand stays.
- `#pcheck-facets-n` shows "(n ticked)".
- "Check this project" (and Enter+Cmd/Ctrl in the textarea) runs `matchProject` with the
  ticked facets, the select's state, and the textarea text, then renders into
  `#pcheck-output`. Also auto-run after the first parse that yields ≥1 facet, so the
  reader does not have to find the button. "Clear" resets everything to the empty state.
- An example button loads that example: textarea ← description, state ← state,
  MW/MGD ← values, boxes ← the example's **curated** facets (not the parse), then runs.
  The curated facets are a baseline, not clicks: Run on the unedited description keeps
  them, an edit to the description re-parses as usual, and only boxes the reader
  clicks stay manual.
- Render the result as the Python renderer does (`_project_result_html` in
  dashboard.py — copy its structure and class names exactly: `.pcheck-result`,
  `.pcheck-sec` with `<h4>`, `.pcheck-dim-row`, `.pcheck-facet`, `.pcheck-activity`,
  `.pcheck-list`/`.pcheck-item`, `.pcheck-why`, `.pcheck-trigger`, `.pcheck-pills`/`.pcheck-outcome`,
  `.pcheck-take`, `.pcheck-flag-limit`/`.pcheck-flag-else`, `.pcheck-bars`, the rules section).
  Section titles come from the same strings (`PROJECT_CHECK_SECTIONS` — emit them into the
  fragment as data attributes or a JSON block rather than retyping them). Build DOM with
  `createElement`/`textContent`; never innerHTML with record text.
- Record links are `href="#" + anchor` — the page's anchor handler already opens the owning
  tab. Activity chips link to `#paths-<activity>`.
- Empty states: no facets → `#pcheck-status` text (already present); no readings/cases →
  the same "No …" sentences the Python renderer uses.
- Payload loading: identical pattern to the Explore script's `init()` — if `#project-data`
  has `data-src`, fetch on first activation of the tab (`tabpanel` becomes visible or the
  fragment is in the document on a standalone page), show a "Loading …" line in
  `#pcheck-status`, and a plain failure message with a link to `project-data.json` on error.
  Inline JSON (Streamlit) boots immediately.
- Must run on the standalone `tab-check.html` page too (scripts there are re-created on
  insertion into index.html; see the Explore script for how it finds its root and avoids
  double-boot).
- No third-party assets, no `innerHTML` with data, no `eval`, vanilla ES5-compatible style
  as the rest of the page (the Explore script is the model). Honour `prefers-reduced-motion`
  (nothing animates anyway).
