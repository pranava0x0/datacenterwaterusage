# AGENTS.md — Data Center Water Use Tracker: how to work in this repo

> Companion to [CLAUDE.md](CLAUDE.md). CLAUDE.md is the *what* (project intent,
> architecture, scraping principles, security rules); this file is the *how*
> (concrete agent workflow inside this codebase). When they conflict on
> workflow detail, this file wins locally.

---

## This project: file map & commands

```
dashboard.py             Streamlit app — source of truth for ALL render logic
                         (the _build_*_html builders are pure and shared)
build_site.py            static-site generator; imports dashboard's builders +
                         data and emits pages/index.html (the deployed artifact)
pages/index.html         GENERATED. Never hand-edit; regenerate and commit.
data/reference/*.json    curated datasets (legislation, cwa_investigations,
                         company_water_claims) — append-only, schema-tested
scrapers/ extractors/    pipeline code (see CLAUDE.md architecture table)
storage/ models/ utils/
scripts/                 one-off migrations (e.g. annotate_cwa_schema.py)
tests/                   pytest — full suite runs in ~2s; no excuse to skip
```

| Goal | Command |
| --- | --- |
| Tests (~3s locally) | `python3 -m pytest -q` |
| Rebuild static site | `python3 build_site.py` |
| Local dashboard | `streamlit run dashboard.py` |
| Scraper dev run | `python3 main.py ... --limit N` (always start limited) |

**Project conflict cheatsheet:**

- **`python` is not on PATH** on this machine — always `python3`.
- **`pages/index.html` is generated.** Edit `dashboard.py` (builders/data) or
  `build_site.py` (shell/CSS/JS), then `python3 build_site.py`. Commit the
  source change and the regenerated page together — never split across
  commits. Streamlit "missing ScriptRunContext" warnings during the build are
  benign noise.
- **Curated JSON is schema-enforced.** Every CWA case needs `case_type`
  (key of `dashboard.CWA_CASE_TYPE_LABELS`), `cwa_applied`
  (applied/pending/not-applied), `cwa_instrument`, and — for pending/
  not-applied — `cwa_pathway` + `analogous_cases` whose ids must resolve.
  Tests in `tests/test_dashboard.py` reject violations; run them before
  committing data.
- **legislation.json field formats are non-obvious — match existing bills exactly.**
  `timeline`: list of `{date, milestone, detail?}` objects (not a dict of key→date).
  `general_principles`: list of `{tag, note}` dicts (not a list of strings).
  Using the wrong format silently builds incorrect JSON that only fails at
  `python3 build_site.py` time with a cryptic AttributeError. Always check one
  existing bill before adding new entries. (Error logged 2026-06-24 in errors.md.)
- **Append-only data.** Don't delete or rewrite existing records; adjudicate
  conflicts toward the newer version (CLAUDE.md § 3).
- **VA DEQ's website WAF-blocks scripted fetches (403).** Don't burn time
  "solving" it; see `errors.md`.
- **Commit identity:** commits are authored as `pranava0x0`
  (`2497510+pranava0x0@users.noreply.github.com`). **No AI co-author
  trailers, ever** — no `Co-Authored-By: Claude`, no "Generated with" links.

---

## Read these first, in order

1. **[CLAUDE.md](CLAUDE.md)** — principles (scraping etiquette, append-only
   data, source attribution, git discipline, security) + architecture.
2. **[DESIGN.md](DESIGN.md)** — visual system, before touching the dashboard.
3. **[backlog.md](backlog.md)** — what's next, incl. watch-items that convert
   into dataset entries when events land. Pick from here; don't invent work.
4. **[errors.md](errors.md) / [issues.md](issues.md)** — what's broken /
   known quirks. Check before reporting a bug as new.

---

## The Explore → Plan → Code → Verify loop

- **Explore.** `grep`/`Read` first. One read of `dashboard.py`'s relevant
  section + the JSON schema covers most dashboard tasks; `config.py` +
  the scraper module covers most pipeline tasks.
- **Plan.** Beyond a one-line fix, state the approach first. Schema changes
  to the curated datasets ALWAYS need a plan surface — they reshape the
  dataset and the filters built on it.
- **Code.** Edit existing files; match local idiom. No new helpers for
  one-shot operations — use `scripts/` for migrations worth keeping.
- **Verify.** Run the narrow tests, then the full suite (it's 2 seconds).
  For UI changes, rebuild the site and grep the output (or click through
  locally) — unit tests verify code, not the rendered feature.

**Per-item cadence in multi-item sessions:** tests + docs + commit per item,
not batched at the end (CLAUDE.md § 5). Clean bisect history.

---

## Verifying changes

| Change kind | Run |
| --- | --- |
| Curated JSON edit | `python3 -m pytest tests/test_dashboard.py -q` then rebuild site |
| Dashboard builder / filter | same + grep `pages/index.html` for the new markup |
| build_site.py shell/CSS/JS | rebuild + `pytest tests/test_build_site.py -q` |
| Scraper / extractor | module tests + a `--limit 1` live run |
| Anything substantial | `python3 -m pytest -q` (full, ~2s) |

For data changes, **skim the JSON diff before committing** — a 30-second skim
catches encoding drift, accidental field renames, and records dropped by a
careless rewrite.

---

## Common tasks

### Adding a CWA case (most common)

1. Append one record to `data/reference/cwa_investigations.json` with the
   full schema: `case_id` (`Org-Location-topic-year`), `category`,
   `respondent`, `year` (`YYYY` or `YYYY-YYYY`), `cwa_section`,
   `violation_summary`, `outcome`, `takeaway` (>80 chars), `case_type`,
   `cwa_applied`, `cwa_instrument`, `sources` (≥1 with real URLs), and for
   pending/not-applied: `cwa_pathway` + `analogous_cases`.
2. Adjacent-category cases must open `cwa_section` with a "No CWA action —"
   style disclaimer (a test enforces the framing).
3. Spot-check every source URL (`curl -s -o /dev/null -w "%{http_code}" -L
   -A "Mozilla/5.0..." <url>`). 403s from bot-blocking news sites are
   acceptable; 404s are not — drop or replace the source.
4. Bump `last_updated`, pin the addition in a regression test,
   `python3 -m pytest -q`, `python3 build_site.py`, commit data + page
   together.

### Running a research pass (seeding new cases)

The pattern that works (June 2026 passes): **two narrowly-scoped background
agents** — one per research track (e.g. formal enforcement vs. non-CWA
disputes) — each given (a) an explicit dedupe list of existing case_ids,
(b) named search angles, (c) a structured JSON output contract, (d) a
"verify with ≥2 sources, no fabrication" rule. Verify URLs and integrate in
the main session; agents never write to the dataset. Convert backlog
watch-items first — they're pre-researched.

**Calibration + prompt rules (measured across the four 2026-06-10 runs;
~12k subagent tokens per verified-and-integrated item is the benchmark):**

- **Cap search angles at ~6 and give a stop condition** ("stop after N
  verified cases, or when 2 consecutive angles surface nothing new"). The
  one run prompted with 12+ angles and no stop rule cost 27k tokens/item
  and 52 tool calls — 2.7× the other three runs (9-10k/item) for the same
  quality. Breadth of angles, not number of results, drove the waste.
- **Dedupe by name match, not by search.** Say "skip anything matching
  these orgs+locations — do not spend searches confirming a duplicate."
  The explicit dedupe list produced zero true duplicates across 25 items
  and got the one near-miss (a successor bill print) self-flagged because
  the prompt named the related existing entries.
- **Output contract must say:** plain UTF-8 (no HTML entities — one run
  returned `&amp;` throughout and needed an unescape pass), *omit*
  conditional keys entirely rather than emitting empty strings, and "your
  final message is parsed, not read" (held 4/4 when stated).
- **When asking for updates to existing records, paste the exact ids to
  echo back.** Describing the records in prose got invented slugs back,
  which then needed manual matching.
- **"Cite only URLs you successfully fetched."** Agents will otherwise
  cite from search-result snippets; ~5% of returned links were bad. Keep
  the main-session curl spot-check regardless (one bash call per batch;
  it caught a hard 404 that the agent missed; treat 403s from
  bot-blocking news sites as inconclusive, not dead).
- **Piggyback maintenance onto research:** folding the watch-item
  re-checks into one of the research agents (Task A / Task B structure)
  cost no extra agent and kept the backlog honest.
- **Assign `analogous_cases` at integration, not in the agent.** Linking
  new cases to historic ones needs whole-dataset judgment the agent
  doesn't have; the schema test then verifies every id resolves.

### Adding a vocabulary item (case_type, category, status)

Schema change — don't do it casually. Add to the canonical dict in
`dashboard.py` (labels + any color map), confirm `build_site.py` picks it up
(it imports the dicts — no mirror to sync), re-tag affected records, run the
schema tests, rebuild.

### Adding a scraper

Follow CLAUDE.md § 1–4 (rate limits, caching, append-only, attribution) and
the architecture table; register it there when built. Test with `--limit 1`
against a single document before any full run.

---

## Token economy — be judicious

Most tasks here are file edits over a small, well-tested codebase plus
curated JSON. Default to doing the work inline.

### The escalation ladder — always start at step 1

1. **A `python3 -c` one-liner or grep on the local JSON/code** — free.
   Check what's already in the dataset *before* going to the web.
2. **`Read` on a known path** — free.
3. **One targeted WebSearch / WebFetch** on a question you can name.
4. **A background agent** — only for genuinely parallel multi-step research
   (the two-track research-pass pattern above), a long-running task, or a
   broad read-only sweep where only the conclusion matters.

**Never spawn an agent for:** checking whether a case is already tracked
(one-liner), adding a single record, fixing a CSS/JS bug, or any bounded
lookup a single WebSearch answers. Sibling repos measured the failure mode:
~30k tokens per agent for lookups a 2-call search would have landed; a
full deep-research fan-out can burn millions of tokens and return nothing.
Deep-research / multi-agent workflows are **explicit user opt-in only**,
with a stated cost expectation.

**Check CLAUDE.md and AGENTS.md before spawning an Explore agent for a
"state of the project" question.** CLAUDE.md carries the scraper-status
table, architecture, and data-tier classification — most broad questions
about what's working/blocked/missing are already answered there. The
correct pattern for codebase-state questions:

1. Read CLAUDE.md architecture + scraper table (~1 Read call).
2. Read `errors.md` for open blockers (~1 Read call).
3. Read the relevant `backlog.md` section for what's missing (~1 Read call).
4. One `Bash` grep for a specific config value (e.g. `grep "target_permits" config.py`).

This covers ~90% of the information an Explore agent would return at ~15%
of the token cost. The Explore agent earns its cost only when the answer
space is **genuinely unknown across many files** (e.g. "find all callers
of this function I'm about to refactor"). Measured 2026-06-25: Explore
agent returned ~30–40% waste — test counts, completed backlog items, and
`DocumentRecord` field lists — for a "what's blocked and why" question
where the scraper-status table in CLAUDE.md already had the answer.

**Never spawn an agent to resolve merge conflicts in files you were just editing.**
Measured in this repo (2026-06-24): resolving 8-file merge conflict via agent
cost ~105k tokens (28.9k parent + 76.2k child, 59 tool uses). Correct cost
was ~25-35k inline. The failure mode: a ~1000-word agent prompt encoding the
solution + sub-agent spawning + re-reading files already in context = 3-4×
waste. The signal you're in this trap: if you can write a detailed prompt
explaining exactly how to resolve each conflict, you already have the context
to do it with 4-6 `Edit` calls yourself. Inline the edits, run
`python3 build_site.py && python3 -m pytest -q`, done.

### Token gate at 50K

If a turn has burned >50K tokens or clearly will, stop and present options:
(A) proceed at full depth, (B) do the highest-value subset and log the rest
in `backlog.md`, (C) switch to a lighter approach. Never silently burn a
large budget.

### Agent hygiene (when one IS warranted)

- Tight prompt, explicit dedupe list, structured output contract, stop
  condition.
- Two or three well-scoped agents beat a fleet.
- Verify agent-sourced claims (URLs, case numbers, dates) before they touch
  the dataset — agents return stale and unverifiable claims.
- Agents never write data or commit; integration happens in the main
  session where the schema and tests are in context.
- Agent's final report should state: what it found, what it couldn't verify,
  and what was deliberately excluded — absences matter as much as hits.

### Standing rule: evaluate and log every agent use

At the end of any session that spawned agents (research, Explore, or
otherwise), **evaluate each agent run and append the verdict to the
"Agent-use evaluation log" below** (and mirror durable lessons into the
assistant's persistent memory). This is not optional bookkeeping — the
measured entries in this file are what keep future sessions from repeating
the ~3-4× waste patterns. Score each run on:

1. **Quality** — did the output survive verification and get used? What did
   it correct or catch that inline work would have missed?
2. **Token efficiency** — subagent tokens vs. a realistic inline estimate
   (tokens per verified fact/entry is a good unit).
3. **Necessity** — could 1-3 direct WebSearch/Read/grep calls have landed
   the same result? If yes, log it as an anti-pattern with numbers.

### Agent-use evaluation log

**2026-08-24 — ten agents (3 Sonnet research, 5 Opus implementation, Haiku +
Sonnet checkers) through two usage-limit walls. Verdict: the fleet was
user-directed and every run survived scrutiny; the durable finds are the
resume pattern and the checker-tier calibration.**

- *Research (Sonnet, parallel, background):* news sweep 250.8k/90 tools →
  17 items + 6 ripples (~10.9k/unit — on the hybrid seed+sweep band);
  federal statutes 304.2k → 8 families / 12 readings / 14 cases / 3 mappings
  (~8.2k/unit); state-local + benefits mirror 291.4k → 7 instruments + 89
  actions + 10 claims (~2.7k/unit — mirror-transform work is the cheap end).
  Seeding with orchestrator WebSearch results first (4 searches) kept all
  three out of the 35k/entry open-discovery regime.
- *Implementation (Opus, serialized — all four touch `build_site.py` /
  `dashboard.py`):* graph 270k, visuals 222k, statutes merge 287k/144 tools,
  news+states integration 384k/178 tools, UX/perf pass 290k/186 tools. Zero
  merge conflicts because they never ran concurrently; the 2026-06-24
  merge-conflict anti-pattern stayed dead.
- *Orchestrator pre-validation pays for itself:* ~15k tokens of inline python
  schema checks over the research deliverables caught the `US S. 4213`
  semantic duplicate and two shape mismatches BEFORE the Opus integrators ran.
  Validation between research and implementation is now standard.
- *Checker tiers:* Haiku (92k/38 tools) is the right first pass for mechanical
  sweeps — it caught a real class bug (news tags had no membership test) — but
  produced **2 false blockers** (its own 2-min Bash timeout reported as "pytest
  hangs"; a file-changed claim on an untouched file). **Verify every Haiku
  blocker with one direct command before acting.** The Sonnet second pass
  (~620k across a limit-death resume) found what test-green could not: a
  `TypeError` crash in `render_states_tab` (nothing exercises the Streamlit
  render_* layer — see issues.md TEST-002), a time-of-day-dependent window
  boundary, a mobile overflow, and 2 real data errors in 15 source
  re-verifications. Different tiers, different failure classes; run both when
  a branch is this large.
- *Usage-limit deaths (two walls: ~01:45 and ~10:50):* 4 agents killed
  mid-flight the first time, 1 the second. **Every one resumed via SendMessage
  with full context intact** — zero respawns, zero re-research. The one agent
  that had written nothing before dying (statutes) lost no work only because
  its findings lived in its transcript; since then every research prompt says
  **write the deliverable file incrementally** so a death can't strand work in
  a context. The scheduled-task janitor (fireAt + liveness guard) is the
  correct backstop; the first one fired into the dead window exactly as
  designed and no-op'd.
and the cheapest defect-per-token of any agent run logged here.**

- *Agent — review the Python diff of PR #20:* 170k subagent tokens, 48 tool
  uses, ~8 min. Returned **8 defects, every one reproduced with an executable
  repro rather than inferred from reading** — including a critical API-key leak
  and a quadratic-regex stall it measured at three input sizes. ~21k tokens per
  verified defect. All 8 were real; zero false positives.
- **Why it beat doing it inline:** I had just written the code, and the two
  worst findings were bugs my own tests actively masked (a corrupt-queue test
  asserting the wrong half; an excerpt test whose 20-char fixture made the
  broken and correct implementations indistinguishable). Self-review re-reads
  the same assumptions. The agent ran the code instead.
- **Scoping that made it cheap:** the prompt excluded JSON data and generated
  `pages/*.html`, named the specific hazards to look for (streamlit purity,
  cache invalidation, ReDoS, secret-in-URL, escaping under `unsafe_allow_html`),
  and demanded `file:line` + a fix. Reviewing the full 12k-line diff
  undifferentiated would have cost far more and surfaced style noise.

**Free external review is complementary, not redundant — run both.** Codex
reviewed the same PR across two rounds: 5 findings, **3 overlapping my agent's
and 2 unique**, including the session's worst bug (LegiScan `getBill` takes a
numeric id, so with no response-status validation the watch hashed an error
payload into a *stable* fingerprint and could never have fired). The agent
missed it; Codex missed the key leak. Different blind spots, and Codex costs
nothing — **always `@codex review` before merging, and re-request after
pushing fixes.**

**Where reviewers concentrate is itself a signal.** 15 defects across three
rounds: **11 in `scrapers/monitors/`**, the only genuinely new subsystem, and
~0 in the much larger data-and-refactor surface. When a subsystem's
characteristic failure is one where broken and working look identical from
outside, most of its tests should exist to tell those two states apart.

**No research agents this session** (implementation, not discovery) —
consistent with the 2026-07-25 finding: delegate discovery, confirm inline.
Direct WebSearch verified ~20 URLs and caught 3 errors the plan carried.

**2026-07-25 — plan implementation (P0–P4 partial). Zero agents spawned;
verification done with ~10 direct WebSearch calls. Verdict: correct call for
this shape of work — log it as the counter-example to reflexive delegation.**

- The task was *implementing* an already-researched plan, not discovering
  facts. The research agents had run in the planning session (~447k tokens);
  re-delegating verification would have paid that cost twice for claims the
  plan already stated.
- What still needed checking was narrow and enumerable: a source URL per new
  record. Direct WebSearch, ~2 per response, produced **three material
  corrections** the plan had wrong — the Michigan standing case (2007 Supreme
  Court, not the 2005 Court of Appeals decision that was *reversed*), the
  Swanson holding (no "duty to augment supply"), and a stale CA AB 93 veto
  date. An agent would have found the same things at several times the cost
  and returned prose I'd have had to re-read.
- **Lesson:** delegate *discovery* (open-ended, unknown answer set); do
  *confirmation* inline (bounded, one lookup per known item). The tell is
  whether you can enumerate the questions before you start.
- **Infrastructure finding worth keeping:** Justia 403s all automated
  requests and CourtListener returns blank to WebFetch, so legal-citation
  URLs cannot be verified by fetching — and cannot be pattern-guessed either,
  since a wrong guess is indistinguishable from a blocked valid one. Search
  results are the only reliable channel. Any future case-law batch should
  budget ~1 search per 1–2 cases and hold back anything unsourced.

**2026-07-02 — two parallel background research agents (water-authorities
expansion). Verdict: both justified; keep this pattern.**

- *Agent A — verify 10 non-CWA historical cases (SDWA/TSCA/RCRA/RHA):*
  56.2k subagent tokens, 14 tool uses, ~3.5 min. 10/10 candidates
  adjudicated; correctly REJECTED one seeded candidate (W.R. Grace/Acton as
  a SDWA §1431 order — unsupported) and substituted a verified landmark
  (Trinity American v. EPA, 4th Cir. 1998); corrected two dates/figures
  (Interfaith affirmance is 2005, 3M penalty $1,521,481) and flagged the
  moved TSCA 8(a)(7) deadlines. All 10 became dataset entries.
- *Agent B — verify 18 DC sites with water pushback:* 71.7k subagent
  tokens, 22 tool uses, ~4.5 min. 17/18 verified plus 2 extras found;
  caught a factual error in the seeding prompt (West Des Moines "quarter of
  city water" is false — ~6% in July 2022; the "quarter" belongs to The
  Dalles) and corrected an existing dataset framing (Meta Richland Parish's
  23 MGD is a supply authorization, not a discharge limit). All entries
  became the dc_water_conflicts.json roster.
- *Efficiency:* ~128k combined subagent tokens for 28 verified,
  source-cited entries (~4.6k/entry). The inline equivalent was ~36
  serialized WebSearch/WebFetch calls dumping raw results into the main
  context — comparable-or-worse token cost with none of the parallelism
  (schema + migration code shipped while the agents ran).
- *Necessity:* yes for both — multi-step, many-source verification with
  only-the-conclusion-matters output is exactly the step-4 case on the
  escalation ladder. Neither was answerable from repo files or 1-3 direct
  calls.
- *Improvement for next time:* seed prompts with claim + entity and let the
  agent find the figures — two seeded numbers were wrong and were only
  caught because the prompt said "verify, don't confirm."

**2026-07-06 — four parallel open-discovery research agents (news, solutions,
general CWA cases, SDWA/TSCA cases). Verdict: justified, but materially less
token-efficient than the 2026-07-02 seeded-verification pattern — log the gap
so future sessions prefer seeding when a candidate list already exists.**

- *Agent A — news discovery:* 99.7k subagent tokens, 33 tool uses, ~3 min.
  Found 6 verified new items (dropped ~5 more as unverifiable — an Snopes-flagged
  Utah water-use claim, a paywalled SC outlet, a snippet-only AWWA reference —
  correctly excluded per "verify, don't confirm"). All 6 became `water_news.json`
  entries.
- *Agent B — solutions discovery:* 120.8k subagent tokens, 50 tool uses, ~5.6
  min. Found 2 verified new solutions, plus caught that Amazon's first-ever
  aggregate water disclosure substantiates (rather than duplicates) the
  existing `wue-reporting` entry, and flagged two backlog-worthy gaps (FL SB
  484, MN HF 16 have no `water_solutions.json` entry despite being tracked in
  `legislation.json`) instead of forcing weak new entries. Both new solutions
  used as-is.
- *Agent C — general CWA case discovery:* 145.9k subagent tokens, 35 tool
  uses, ~4 min. Found 3 candidates; correctly flagged one (QTS Fayetteville
  citizen-suit escalation) as the *same* dispute maturing rather than a new
  case — followed that recommendation and updated the existing
  `QTS-Fayetteville-GA-2024` entry instead of minting a duplicate. The other 2
  became new cases.
- *Agent D — SDWA/TSCA case discovery:* 130.7k subagent tokens, 46 tool uses,
  ~4.5 min. Found 3 verified cases (Chemours $450M multi-statute settlement,
  Westchester JWW SDWA consent decree, CJT Group §1431 order); explicitly
  excluded a real-but-weak candidate (Fort Mojave manganese order — no
  data-center nexus, single-source corroboration) rather than padding the count.
- *Efficiency:* ~497k combined subagent tokens for 13 new entries + 1 updated
  entry (~35.5k tokens/entry) — **~7-8x worse than the 2026-07-02 pattern's
  4.6k/entry.** Root cause: these agents did unconstrained discovery ("find
  anything new") rather than adjudicating a pre-seeded candidate list, so a
  large share of tokens went to searches that were correctly rejected rather
  than to verifying known claims. Each agent also paid a fixed cost reading
  the full existing dataset (88 cases, 20 authorities) for dedup before
  searching.
- *Necessity:* justified for the open-ended "what's new" asks (news, general
  cases) — multi-source discovery across an unbounded search space is exactly
  the delegate-it case. Less clearly justified for the SDWA/TSCA agent, which
  had a narrow, well-defined target (2 statutes, ~7 known reading_ids) and
  might have been tightened into a single more targeted agent rather than a
  fully independent parallel run.
- *Good inline decision (no agent used):* the same session also renamed a UI
  label, restructured a card into collapsed-by-default `<details>`, and fixed
  two tests — done by reading the exact functions/tests directly rather than
  delegating, since the scope was fully known upfront. Right call per the
  escalation ladder.
- *Improvement for next time:* when the ask is "find more like these 5
  existing failure modes" rather than pure open discovery, seed the agent with
  the existing category/date boundaries up front (as done here) but consider
  narrowing scope further (e.g. one agent per statute, not per broad topic) to
  cut the search-then-reject overhead that drove the 7-8x token gap.

**2026-07-25 — three parallel background research agents feeding the
issues/policy/precedent implementation plan (`docs/plan-2026-07-25-issues-policy-precedent.md`).
Verdict: all three justified; hybrid seed+sweep lands mid-band on cost, and
the correction yield is what paid for it.**

- *Agent A — issues/claims (seeded verify + 3-week news sweep):* 181.1k
  subagent tokens, 50 tool uses, ~8.5 min. All 7 seeds verified with 4
  substantive refinements (AWS suit is a *whistleblower* state
  consumer-protection action; Google silently dropped the "120%" figure its
  tracked claim still quotes; Microsoft's "90%" is two-decade fleet WUE, not
  new-facility marketing; heatwave/UT-Austin seeds predate the window). New:
  Meta Cheyenne WY pretreatment-SNC contamination, WVWA/Google Botetourt
  real contract numbers (2 MGD / 8 MGD ceiling vs the rejected 11 MGD),
  Brookhaven/Missoula/Albany/Spokane moratoria, xAI greywater restart, and a
  14-value issue-type taxonomy. Flagged 4 unverifiable specifics instead of
  asserting them (docket no., Snopes verdict, Meta 6B-gal figure).
- *Agent B — legislation/EO/policy (seeded verify + docket triage):* 128.6k
  tokens, 45 tool uses, ~7.6 min. Mapped the entire untracked federal
  executive layer (EO 14318 anatomy — §404-only, *no NPDES directive*,
  correcting the seed; NWP-39 chain; first FAST-41 data center QTS Richmond)
  and produced 5 status changes on tracked entries (NY EO 62 *instead of*
  signing/vetoing the bill; AWS Lake Anna permit final at 0.28 MGD; VA HB 496
  regs with concrete dates; WV HB 4832 dead with protections stripped on
  floor votes; MI 5-bill package). Killed 3 false seeds outright, including
  "Ohio enacted water provisions beyond the pledge" (energy-only) — which
  descoped Spec B2 before it was built wrong.
- *Agent C — precedent doctrines (seeded legal verification):* 137.8k tokens,
  42 tool uses, ~9.2 min. 20/20 anchor cases verified with 2 caption
  corrections (Sierra Club v. *Lujan*, not Babbitt, for the 1993 Edwards
  springflow order; Racine/Foxconn ALJ posture), 1 candidate family
  *affirmatively excluded* as non-additive (state antidegradation), 1 gap
  honestly flagged rather than filled (no litigated MI WWAT case), and 4 new
  families proposed that reshaped the design (SGMA/AZ-GMA → `GWMGMT`,
  area-of-origin + forfeiture → `XFER`). Also produced the site-by-site
  innovative-application mappings (Mount Pleasant double exposure, Sinton
  triple, Bessemer "Swanson in reverse", Imperial tribal-seniority angle) and
  *negative* mappings (ESA ∅ Memphis) that became a product feature.
- *Efficiency:* ~447.5k combined tokens for ~45 verified, plan-ready units
  (items, status changes, anchor cases, taxonomy) ≈ **~10k/unit** — between
  the 4.6k pure-seeded benchmark (2026-07-02) and the 35.5k open-discovery
  regime (2026-07-06), exactly where a hybrid seed+bounded-sweep design
  should land. The 3-week date window on sweeps is what kept discovery from
  drifting into the 35k regime.
- *Necessity:* yes — the deliverable was a plan whose specs would have baked
  in ~8 material errors without verification (wrong case caption, wrong EO
  scope, a "pending" bill that was actually superseded by an EO, an
  energy-only docket layer). Main-context inline equivalent was 50+
  serialized fetches with no parallelism; plan-writing proceeded while
  agents ran.
- *Improvement for next time:* asking agents to state "maps to <dataset> /
  does NOT fit current schema" turned research output directly into design
  input (the AWS suit's state-law theory forced the `SL` authority family) —
  keep that clause in every research-agent prompt for this repo.

---

## What NOT to do

- **Don't hand-edit `pages/index.html`.** Generated; regenerate via
  `build_site.py`.
- **Don't add a record without a real, checked `source_url`.**
- **Don't paraphrase quotes.** `company_water_claims.json` statements and
  legal language in CWA cases are verbatim-or-nothing.
- **Don't editorialize classifications.** `cwa_applied: not-applied` is a
  neutral fact, not a failure state; takeaways describe what the record
  shows, not a verdict on the company.
- **Don't float dependencies or unpinned CDN assets.** `==` pins, SRI
  hashes, SHA-pinned GitHub Actions (CLAUDE.md § 10).
- **Don't expand scope inside a fix.** Log follow-ups in `backlog.md`.
- **Don't loosen a tested invariant quietly.** The test exists because
  something broke; read the rationale first.
- **Don't add AI co-author trailers to commits.** See cheatsheet above.

---

## Escalate to a human when…

- A schema field on a curated dataset would change meaning (not just gain
  values) — it cross-cuts data + builders + filters + tests.
- A case's classification is genuinely contested (e.g. whether a state
  permit program "is" the CWA for `cwa_applied` purposes) and the existing
  taxonomy notes don't settle it.
- A canonical source 404s or paywalls — pause before substituting a
  less-canonical source.
- A scrape target adds a WAF/CAPTCHA — never work around it (CLAUDE.md
  § security; see the VA DEQ precedent in `errors.md`).
- An action is outward-facing: pushing, opening PRs, or anything that
  publishes data.

---

## When something unexpected happens

Append a concise note to `errors.md` (runtime/scraper/test failures, with
the code-bug vs. test-bug classification CLAUDE.md § 6 requires) or
`issues.md` (quirks, data-quality surprises):

1. **What I expected** — one sentence.
2. **What happened** — one sentence.
3. **Why** — root cause, not symptom.
4. **Next time** — the actionable lesson.

That growth — these files getting *slightly* more specific with each
session's surprises — is the asset. Don't rewrite from scratch; append.
