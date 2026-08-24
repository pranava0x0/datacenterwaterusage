# Spec C — News refresh: May–August 2026 + tracked-thread status updates

## Purpose

`water_news.json` stops in early July 2026; several tracked stories have unresolved statuses. Bring the News tab current through 2026-08-24 and adjudicate every stale status the new reporting touches — news items are cheap, but a bill card still saying "awaits signature" two months after the decision is a correctness bug.

## Research (orchestrator WebSearch pass first, then one Sonnet agent)

The orchestrator runs its own searches to map the window, then hands the agent seeds. Two workstreams:

**1. Thread continuations (claims to verify, not numbers to confirm):**
- NY S10642/A11560 — did Hochul sign, veto, or let it lapse?
- Ohio EPA OHD000001 draft general permit — finalized? First DMRs?
- AWS Lake Anna VPDES cooling-discharge draft permit — decision after the June 9 hearing?
- VA HB 496 / SB 553 — monthly aggregate water-delivery reporting effective ~July 1; did the first reports or a reporting channel materialize in Aug?
- Fort Worth / Cedar Creek Lake proposal — advanced, paused, or rejected?
- Indiana county restriction wave — count changed? statewide response?
- Tucson Project Blue — post-rejection developments?
- xAI Memphis — new water/permit developments?
- QTS Fayetteville §505(b) citizen-suit notice — suit filed?
- Amazon 2.5B gal/yr disclosure — follow-on disclosures from other operators?
- ID H 895 (enacted consumptive-cooling restriction) — implementation news?
- Georgia (SDC ATLA, Meta Newton County wells), Memphis, Great Lakes states — new fights?

**2. Open discovery, 2026-05-01 → 2026-08-24:** state/federal regulation, enforcement actions, litigation, moratoriums, big disclosures, cooling-technology and reuse deals, research reports with numbers. Target 12–18 verified items; drop anything that can't get outlet + date + working URL.

## Data changes

1. `data/reference/water_news.json` — append items in the existing shape: `id` (`slug-YYYY-MM`), `date` (`YYYY-MM`), `title` (headline register, no clickbait), `outlet`, `source_url`, `summary` (2–3 sentences: who, what, the number if there is one, why it matters to the tracker), `tags` (closed 6-value set), `cross_ref_targets` where the story touches a tracked bill/case/site/claim/solution (ids must resolve — integrity tests enforce). Bump `last_updated`.
2. Ripple updates (newer-version-wins, per CLAUDE.md §3): `legislation.json` statuses/timelines/`recent_news`/`last_verified` for decided threads; `cwa_investigations.json` outcomes for decided cases; `dc_water_conflicts.json` `status_2026` where a site's fight moved. Every ripple cites a source in the record it touches.
3. New records the research surfaces that are *instruments* or *cases* rather than news (e.g., a filed lawsuit) get full records in their home dataset plus a news item cross-referencing them — same pattern the corpus already uses.

## Render changes

None — the News tab is data-driven. If the item count passes ~50, add a year divider in `build_news_tab` (small-caps, per DESIGN.md §4).

## Tests

Existing schema/integrity tests cover the additions. Update any asserted counts. Add ids to llms.txt automatically via its loops (verify the coverage test still passes).

## Writing register (binding for the agent)

Match the corpus: "Amazon's first-ever aggregate DC water-use disclosure (2.5B gal/yr, 2025)". Dates, actors, numbers, outcomes. Banned: "landscape", "delve", "rapidly evolving", "underscores", "highlights the importance", "game-changer", "crucial", em-dash chains, rhetorical questions.
