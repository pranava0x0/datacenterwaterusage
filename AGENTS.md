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
| Tests (446, ~2s) | `python3 -m pytest -q` |
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
