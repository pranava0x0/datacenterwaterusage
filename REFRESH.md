# Data refresh playbook

How to bring this tracker's datasets current. Written for the `data-refresh`
skill and for a human doing it by hand.

The pipeline has two halves that work differently, and conflating them is the
main way a refresh goes wrong:

- **Scraped data** (`data/output/results.csv`) — 22 scrapers, append-only,
  re-runs skip already-fetched documents automatically.
- **Curated reference data** (`data/reference/*.json`) — seven hand-adjudicated
  datasets. **Nothing writes to these automatically.** Monitors and research
  propose; a person decides. That is the whole reason these records are worth
  more than a scrape, so don't automate it away.

---

## 1. Start from the monitor queue, not from scratch

```bash
python3 -m scrapers.monitors.run
```

Sweeps every record carrying a `monitor` block (7 today), fingerprints the
watched page, and appends anything that changed to
`data/output/monitor_hits.json`. Rate-limited 2–5 s, sequential.

**This also runs weekly on its own** (`.github/workflows/monitors.yml`, Mondays
07:23 UTC). Grab the `monitor-hits` artifact from the latest run instead of
sweeping locally, and read the run summary for the one-line verdict. Run it by
hand only when you want a sweep right now.

Read the queue before doing any research — it tells you what actually moved,
so you re-verify the two things that changed instead of the sixty that didn't.

| In the output | Means |
|---|---|
| `changed` | The watched page differs from last sweep. Triage it. |
| `baselined` | First observation. No change implied — the sweep just recorded a starting point. |
| `failed` | Could not fetch. **Usually means the page moved**, which is itself stale data. Fix the `monitor.key` in the record. |

`--dry-run` reports without writing. `--only "<record id>"` runs one watch.

Two monitor kinds need credentials and skip (loudly, as `failed`) without them:

```bash
export LEGISCAN_API_KEY=...     # legiscan watches
```

Federal Register needs no key. **Never commit either key** — CLAUDE.md §10.

## 2. Triage each candidate

For each entry in `monitor_hits.json`, open the `key` URL and decide:

- **Real status change** → update the record's `status` / `status_detail`, set
  `last_verified` to today, and add a `recent_news` entry with a source. If the
  change resolves an unverified claim, flip `verified` to `true`.
- **Cosmetic** → nothing to do. The candidate stays in the queue; it is
  append-only on purpose, so "we looked and it was nothing" is on the record.
- **Page moved** → update `monitor.key`.

The queue is never edited or pruned. The fingerprint cache
(`data/state/monitor_fingerprints.json`) advances automatically; a *failed*
fetch deliberately does not advance it, so the failure re-reports next run.

## 3. Verify sources before entering anything

- **Two independent sources per new case.** Anything that cannot be tied to a
  retrievable source is held back, not entered on a plausible-looking link.
- **Justia and CourtListener block automated fetch** — Justia 403s every URL
  including valid ones, CourtListener returns blank. A constructed citation URL
  cannot be verified, and a wrong guess is indistinguishable from a blocked
  valid one. **Use WebSearch**, which returns real resolvable URLs. Budget
  roughly one search per one or two cases.
- Anything unconfirmed ships `verified: false` plus a `status_detail` naming
  what to re-check.

## 4. Adding records

Use a migration script in `scripts/` rather than hand-editing across records —
it is reviewable, idempotent, and re-runnable. Recent examples:

| Script | Adds |
|---|---|
| `add_doctrine_families_batch3.py` | authority families + readings + anchor cases (via `_doctrine_batch.py`) |
| `add_policy_instruments_2026_07.py` | legislation entries + status updates |
| `annotate_outcome_types.py` | re-derives `outcome_type` for all cases |
| `annotate_site_doctrine_mappings.py` | site → doctrine mappings |

All take `--dry-run`. They abort rather than writing partial or unvalidated data.

**Taxonomy rule:** a new value in any closed taxonomy
(`refdata/taxonomies.py`) ships in the *same commit* as the records that use
it. A value with no records renders a filter chip matching nothing, and tests
enforce both directions.

## 5. Scrapers, when you need them

```bash
python3 main.py --scraper epa_echo_dmr --limit 5   # always test small first
python3 main.py --all-fed
```

`--limit` caps fetches while developing. Re-runs skip already-fetched
documents via `data/state/scraper_state.db`.

## 6. Before committing

```bash
python3 -m pytest -q          # must be green; ~620 tests, under 10s
python3 build_site.py         # regenerates pages/index.html + pages/llms.txt
```

Commit the regenerated `pages/` artifacts **with** the data change — they are
the deployed site, and a data commit without them ships stale HTML. The
`llms.txt` mirror is test-enforced to contain every record id, so a new entry
that never reaches it fails the suite.

## 7. Known upcoming decisions

Watched automatically (step 1), listed here so a human refresh doesn't miss them:

| What | Expected |
|---|---|
| VA DEQ first aggregate data-center water report | **2026-10-01** — unlocks the Tier-1 scraper build |
| VA categorized monthly reporting begins | 2027-01-01 |
| Ohio EPA OHD000001 general permit finalized | unscheduled — makes data centers direct DMR filers |
| NY EO 62 moratorium expiry / DEC withdrawal rulemaking | ~2027-07-14 |
| NY S10642 veto | unscheduled (superseded by EO 62) |
| Durbin transparency bill number assigned | unscheduled |
