# Spec F — datacentercommunitybenefits sync: claims refresh + moratorium mirror

## Purpose

`company_water_claims.json` already mirrors the benefits repo's claims (theme=water). That repo has grown datasets this tracker can use: `docs/data/moratoriums.json` (~150 KB of county/city/state actions — exactly what Spec D's third section needs) and newer claims than the July capture. Sync both, by the same mirror rules the claims file already documents.

## Changes

1. **Claims refresh.** Fetch `docs/data/claims.json` from `pranava0x0/datacentercommunitybenefits` (raw.githubusercontent.com), filter `theme == "water"`, diff against the 35 mirrored claims by id. Append new claims verbatim (first-party quotes stay verbatim — that's the dataset's contract); carry the curator's `delivered` adjudications as-is; never edit existing mirrored text, only append or update `delivered` status to the source's newer version. Update `last_updated` and the companies list if new operators appear.
2. **Moratorium mirror → `local_actions.json`** (schema in Spec D). Mapping: keep records whose scope is county/city/town (state-level moratorium bills stay in `legislation.json` — several already are; the research agent flags overlaps instead of double-entering). Mark `water_related: true` where the source record's text mentions water/aquifer/sewer/cooling draw, plus a `water_angle` line; other actions mirror with `water_related: false` so the tab's toggle can show the full moratorium picture. Preserve source ids in `action_id` (prefixed `dccb-`) so re-syncs are idempotent — the sync is a pure upsert on `action_id`, and a `note` field documents provenance + refresh command, same pattern as the claims file.
3. **Cross-links.** Where a mirrored action's jurisdiction matches a tracked conflict site or instrument (e.g., a county moratorium where a tracked site fight happened), the research agent proposes `related` context lines in the rendered table (display-only in v1 — no registry edges per Spec D).
4. **REFRESH.md** gains a short section: how to re-run both syncs by hand (fetch URL, filter, upsert), until/unless a monitor is built.

## Tests

- Upsert idempotence: syncing the same source twice changes nothing (unit test with a fixture payload).
- Mirrored-claim protection: a test asserts mirrored claim `statement` fields are never edited by the sync path (fixture-based).
- `local_actions.json` schema tests per Spec D.

## Out of scope → backlog

- Mirroring `projects.json` / `rate_cases.json` / `responses.json` / `tariffs.json` (energy-side; revisit if a water angle shows up).
- A weekly monitor for the benefits repo (fits `scrapers/monitors/` — fingerprint the two source files; propose-don't-dispose rules apply).
