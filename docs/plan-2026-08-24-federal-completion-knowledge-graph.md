# Plan — Federal completion, knowledge graph, news refresh, state/local page, infrastructure visuals

**Date:** 2026-08-24 · **Branch:** `jam/datacenter-water-knowledge-graph-64c4ba`
**Status:** APPROVED — the user pre-authorized implementation, merge, and branch cleanup in the same session. Specs live in `docs/specs/2026-08-24/`, one file per feature.

## What this plan covers

Six features, each with its own spec:

| Spec | Feature | Research | Implementation |
|---|---|---|---|
| A | Finish the federal water-statute universe + the historical cases that anchor it | Sonnet agent | Opus agent |
| B | Knowledge-graph Explore tab: search + text similarity + relation traversal over every curated record | none (pure build) | Opus agent |
| C | News refresh, May–Aug 2026, plus status updates to tracked threads | WebSearch + Sonnet agent | Opus agent |
| D | States & Localities tab: new state/county/city laws, policies, proposals | Sonnet agent | Opus agent (same run as C) |
| E | Water-infrastructure visual language on the static site | none | Opus agent |
| F | datacentercommunitybenefits sync: claims mirror refresh + moratorium data | folded into C/D research | folded into D |

Checks: Haiku comprehensive pass over the finished branch, then Sonnet if Haiku's findings warrant a deeper look. Then `/learnings`, `/ship`, merge, branch cleanup.

## Current state (verified 2026-08-24 against the working tree, which is ahead of CLAUDE.md's July 27 snapshot)

- 7 curated datasets: legislation 66 instruments (50 state / 10 federal / 6 local), cases 109 (1908–2026), authorities 39 readings across 17 families, sites 19, claims 35, news 34 (latest 2026-07), solutions 3 categories.
- `refdata/` already provides the graph substrate: `registry.build_registry()` is the node set (id → kind/tab/anchor/label), `integrity.iter_edges()` is the edge set with 13 typed edge kinds. Spec B builds on these instead of inventing a parallel structure.
- Statute families with `kind: federal-statute`: CWA, SDWA, TSCA, RCRA, RHA, ESA. TRIBAL is federal-doctrine, EQAP is interstate. Everything else is state doctrine or common law — the July 25 plan (Spec C1) built the state layer; the federal layer stopped at six statutes.
- `company_water_claims.json` already mirrors `pranava0x0/datacentercommunitybenefits` (`docs/data/claims.json`, theme=water). That repo also holds `moratoriums.json` (~150 KB of county/city actions), `projects.json`, `rate_cases.json`, `responses.json` — unmined here until now.
- Tabs: Legislation, Water Cases, Issues & Claims, News, Solutions, Sources. Static site is a pre-rendered single page; only third-party asset is Chart.js (SRI-pinned).
- Tests: 507+ across the suite; schema tests enforce closed taxonomies, family→reading→case pairing, cross-reference integrity, anchor emission.

## Gaps this plan closes

| # | Gap | Evidence |
|---|---|---|
| G1 | Federal statutes that govern water for a data-center fact pattern but have no family, reading, or case: NEPA, CERCLA, the Water Supply Act of 1958 (Corps storage reallocation — the Lake Lanier fights are the closest historical analog to a metro area growing into its reservoir), WRDA/§408, the ratified basin compacts (Great Lakes Compact; DRBC/SRBC dockets that already regulate large withdrawals directly), CZMA, Wild & Scenic Rivers Act §7, Federal Power Act reservoir operations, Reclamation contract law, EPCRA cooling-chemical reporting, OPA facility response plans for backup-fuel tanks. | `water_authorities.json` statutes dict |
| G2 | No way to search the record. 300+ records across 7 datasets are reachable only by tab + filter + scroll. Nothing answers "here is a paragraph describing a new conflict — which readings, cases, and sites look like it?" The registry and integrity edges exist but are invisible to the reader. | `refdata/` module review |
| G3 | News stops at early July 2026; tracked threads (NY S10642 signature, OHD000001, AWS Lake Anna, VA HB 496 first monthly reports due ~Aug, Fort Worth/Cedar Creek, Indiana county wave) have unresolved statuses that are now ~2 months stale. | `water_news.json` date scan |
| G4 | State/county/city actions are filterable inside the Legislation tab but have no surface of their own: no per-state rollup, no "what's new", no county/city moratorium coverage beyond 6 local instruments. The benefits repo's moratorium dataset is unmined. | tab review; `gh api` listing |
| G5 | The infrastructure visual language (pipe texture, wave underline, pipe-flow dividers) exists only in the Streamlit app; `pages/index.html` — the surface people actually see — has none of it, and nothing on either surface shows how water actually moves through a data center. | DESIGN.md §3 note |

## Constraints carried into every spec

- **No live tokens at runtime.** Anything needing an API call from the published page (embeddings, LLM ranking) goes to `backlog.md`, not into the build. Spec B's similarity is lexical (TF-IDF built in pure Python at generation time).
- **Closed taxonomies ship with their records** — a new family lands in the same commit as its readings, cases, order entry, and color.
- **Append-only data**; status changes adjudicate to the newer version with `last_verified` updates, never silent rewrites.
- **Case-law verification via WebSearch only** — Justia 403s every automated request; never pattern-construct a citation URL.
- **Both surfaces stay in sync** — builders shared through `dashboard.py`/`refdata`, regenerated via `python build_site.py`, llms.txt coverage tests keep the mirror honest.
- **Plain writing.** Records read like the existing corpus: dates, actors, numbers, outcomes. No filler adjectives, no "landscape", no "delve", no breathless verbs.
- **Agent accountability** — every agent run is scored in AGENTS.md's evaluation log at session end.

## Sequencing

1. Plan + specs committed (this commit).
2. Orchestrator WebSearch pass → seeds for research agents.
3. Three Sonnet research agents in parallel (news; federal statutes + cases; state/local + benefits repo). Outputs land in the session scratchpad as JSON drafts + source lists.
4. Opus implementation, serialized (all four touch `build_site.py`/`dashboard.py`): B (graph) → E (visuals) → A (statutes, once research lands) → C+D (news + states tab).
5. `python build_site.py`, full pytest, commit per feature.
6. Haiku comprehensive check → fix; Sonnet check if needed → fix.
7. `/learnings`, `/ship`: PR, review, address comments, merge to main, delete branch, prune worktree, remove the 02:30 retry timer.
