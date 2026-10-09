# Check a project — second pass (backlog follow-ups, 2026-10-08)

Three additions to the engine, the page script and the server-side renderer.
The contract in `project-check-js.md` still holds; this extends it. Python
engine (`refdata/precedent.py`), renderer (`dashboard._project_result_html`),
page script (`dashboard._project_check_js`), llms.txt lines
(`build_site._llms_project_check_lines`) and tests
(`tests/test_precedent.py`, node parity included) all change together.

## 1. Instruments rank like readings

Data: every water-scoped instrument in `legislation.json` now carries
`fact_triggers` (a list, possibly empty — empty means "applies to every data
center in its jurisdiction regardless of how it uses water").

Engine (`match_project`):
- `_instruments()` carries `triggers` (from `fact_triggers`, default `[]`),
  `principles` (the general_principles tags) and `level`.
- New result key `instruments` keeps its meaning (the named state's instruments,
  enacted first) but each row gains `score` and `shared` from
  `overlap(facets, triggers)` (0 and [] when triggers are empty) and the list is
  ordered by (enacted first, −score, id).
- New result key `federal_instruments`: federal-level instruments (jurisdiction
  "Federal (US)") whose triggers overlap the project (score > 0), ordered by
  (−score, id), top 6 (`TOP_FEDERAL = 6`, exported in `constants`). Shown
  regardless of state; empty when nothing overlaps.
- Payload: instruments rows gain `triggers`, `principles`; `constants.top_federal`.

Renderer + script: in the rules section, each state instrument shows its
`shared` facets as "Because: …" when non-empty, or the text "Applies to every
data center in the state" when its triggers are empty. (Superseded in review:
the line is now status-keyed and modal, `PROJECT_CHECK_APPLIES_TO_ALL`, and an
instrument marked `fact_scope: "narrow"` gets none.) Below the state list a
sub-list "Federal instruments that could apply" renders `federal_instruments`
the same way; when there is no state, the rules section still renders if
`federal_instruments` is non-empty, titled "Federal instruments that could
apply". llms.txt example lines add "Instruments that could apply: …" (state +
federal, top 5).

Tests: every water-scoped instrument has a `fact_triggers` list of known facets
(both-ways membership is not required for instruments — an instrument facet
nothing else carries is fine, but every facet used must exist); a non-water
instrument has none; the Idaho H 895 record (consumptive cooling) carries
`cool-evaporative` and ranks first for an evaporative project in Idaho;
federal results are empty for an empty facet list; parity test compares
`instruments` and `federal_instruments` ids and scores.

## 2. Negative doctrine mappings surface

Data already has them: `dc_water_conflicts.json` sites carry
`applicable_readings[].reaches: false` with a per-site `how` (xAI Memphis ×2,
Project Blue, Corpus Christi).

Engine: payload `sites` rows gain `negatives: [{reading_id, how}]` (only
`reaches: false` entries; `how` shortened to 260 chars). `match_project` adds
result key `negatives`: for the top 3 sites, every negative mapping, as
`{site_id, site_label, reading_id, reading_label, statute, anchor, how}`,
de-duplicated by (site_id, reading_id), in site-rank order. Empty when none.

Renderer + script: a section "Assessed as NOT reaching a similar site" (key
`negatives` in `PROJECT_CHECK_SECTIONS`) listing each row as
"<statute pill> <reading link> — at <site link>: <how>", rendered in neutral
grey (reuse `.pcheck-flag-else` styling for the statute label or add
`.pcheck-neg` with #6b7280 text), placed after the sites section. Modal copy:
the heading says *a similar site*, not *this project*.

Tests: the Arizona well-pumping fixture (`TestMatchProject.arizona`) yields a
negative for Project Blue's `ptd-groundwater-nexus`; negatives never include a
`reaches: true`/absent mapping; parity compares the negative (site_id,
reading_id) pairs.

## 3. Promote `proc-incentive` (and `out-zero` only if Q4 of the research lands)

`FACT_FACETS` gains `proc-incentive` back (label "Tax incentive or
community-benefit agreement", dimension process, triggers: tax abatement,
abatement, incentive, incentives, tax incremental, tif, tax exemption, tax
break, community benefit, benefits agreement, cba, pilot agreement,
development agreement, mou) and the site/case records the research sourced
carry it in `fact_pattern` — the main session supplies which records, with
the sourced sentence appended to the record's `issue_summary` or
`pushback_summary`. Same-commit rule: the facet enters only with ≥1 record.
Do NOT add `out-zero` unless told a record carries it.
