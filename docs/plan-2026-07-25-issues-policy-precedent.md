# Implementation Plan — Issues & Claims, Policy Instruments, Precedent Engine

**Date:** 2026-07-25 · **Branch:** `jam/datacenter-water-research-c13263` (synced even with `origin/main` @ 9e36879)
**Status:** PLAN — approved specs move to `backlog.md` as executable items; nothing in this doc changes code by itself.

This plan answers three product questions and turns each into build-ready specs:

1. **Issues & Claims** — capture *all* the ways data-center water use becomes a problem (site conflicts, lawsuits, community pushback) and *all* operator claims (water-positive pledges, WUE numbers), with delivered-vs-promised adjudication.
2. **Policy Instruments** — track *every* government lever: state/local/federal bills, **executive orders** (a layer the tracker currently misses entirely), agency rulemakings, and utility-commission dockets.
3. **Precedent Engine** — expand the historic-precedent database beyond the 5 federal statutes to the full water-law doctrine universe (public trust, equitable apportionment, groundwater property doctrines, ESA, tribal reserved rights, …) and systematically map innovative applications onto current data-center fact patterns.

Research basis: a direct WebSearch pass (2026-07-25) plus three parallel Sonnet-4.5-class research agents (issues/claims sweep; legislation/EO/policy sweep; doctrine + precedent verification). Verified findings are inlined in each spec's "Seed data" section with sources. Existing plans considered: `backlog.md` (Data Tab redesign, External Tracker Survey top-10, CWA watch-list, outcome-taxonomy follow-on, cross_ref_targets item from PR #17), `docs/cwa-outcome-taxonomy.md`, CLAUDE.md data-source tiers.

---

## 0. Current state and the gaps this plan closes

**What exists (strong foundation):**

- 7 curated reference datasets, schema-tested, append-only: `legislation.json` (54), `cwa_investigations.json` (93), `water_authorities.json` (20 readings / 5 statutes), `dc_water_conflicts.json` (18 sites), `company_water_claims.json` (34), `water_news.json` (34), `water_solutions.json` (18).
- One render pipeline, two surfaces: pure `_build_*_html` builders in `dashboard.py` feed both the Streamlit app and `build_site.py` → `pages/index.html` + `pages/llms.txt` (35 ms first paint).
- Closed, test-enforced taxonomies: 13 legislation principles, 10 case types, 6 news tags, 3 solution categories; referential-integrity tests on every cross-reference edge that exists today.
- A scraper pipeline (22 scrapers) feeding quantitative DMR/withdrawal data — *not* the subject of this plan, but the ontology below gives curated records stable join keys to it.

**Gaps (validated 2026-07-25):**

| # | Gap | Evidence |
|---|-----|----------|
| G1 | **No federal executive-action layer.** EO 14318 (Jul 2025, "Accelerating Federal Permitting of Data Center Infrastructure") drove the §404 NWP 39 reissuance the tracker *does* record — but the EO itself, its companion AI orders, the AI Action Plan, and agency implementing actions are absent. The only EO tracked is state-level (UT EO 2026-03). | `legislation.json` bill_id scan; WebSearch |
| G2 | **Claims and cases don't connect.** A July 15, 2026 lawsuit alleges AWS's sustainability/water claims are misleading — a *claim* becoming a *case*. The schema has no edge for that, and the 3 big new claim events (Google water-positive pledge June 2026, Microsoft "90% less water" + first replenishment-positive year, WVWA's public correction of the Google/Roanoke 11 MGD figure) post-date the dataset. | WebSearch; `company_water_claims.json` scan |
| G3 | **No issue-type taxonomy.** The 18 conflict sites have prose summaries but no closed classification of *what kind* of water problem each is (aquifer depletion vs. secrecy vs. rate-shifting vs. discharge…), so the tab can't answer "show me all the aquifer fights." | schema scan |
| G4 | **Precedent universe is 5 federal statutes.** Nothing covers public trust (Mono Lake, ELF v. SWRCB), interstate equitable apportionment (Mississippi v. Tennessee 2021 — the Memphis Sand aquifer that xAI's Memphis site draws on), groundwater property doctrines (Edwards Aquifer Auth. v. Day), ESA water cases, tribal reserved rights (Agua Caliente), state environmental-review water-supply adequacy (Vineyard), dormant-commerce-clause limits on water-export bans (Sporhase), or the Great Lakes Compact diversion precedent (Racine/Foxconn — the same Mount Pleasant WI site now hosting Microsoft). | `water_authorities.json` statutes dict; WebSearch |
| G5 | **Cross-references resolve by prose-substring matching** (`_linkify_refs`), already flagged in PR #17 review as fragile. Every new dataset multiplies the cost of not fixing it. | `backlog.md` low-pri item |
| G6 | **Monitors are manual.** Status changes (NY moratorium signature, OHD000001 finalization, AWS Lake Anna decision, VA HB 496 first reports ~Aug 2026) are discovered by hand-run research passes. | `backlog.md` watch-items |

**A note on timing:** the `dashboard.py` module split deferred in Perf-6 (2026-06-01) was blocked by the stlite/WASM dual file-manifest — that blocker died with the June 2026 static-site migration. A *modest* extraction (Spec 0.3) is now low-risk.

---

## Spec 0 — Shared foundation: ontology, registry, cross-reference graph

Everything in Specs A/B/C keys off this. Build it first; it is small.

### 0.1 Purpose / job

One typed identity system across all curated datasets so that (a) every record can point at every related record with a stable key, (b) both surfaces render those links identically, (c) tests can enforce referential integrity mechanically, and (d) future datasets join for free.

### 0.2 Data ontology — entities, keys, taxonomies

**Entity registry (all existing — formalized, not invented):**

| Entity | Key | File | Key format convention |
|---|---|---|---|
| Policy instrument (bill / EO / rule / docket / ordinance) | `bill_id` | `legislation.json` | jurisdiction-prefixed human id (`VA HB 496 / SB 553`, `US EO 14318`) |
| Legal authority "reading" | `reading_id` | `water_authorities.json` | `<family>-<section-slug>` (`cwa-402-npdes`, `ptd-navigable-harm`) |
| Case (enforcement / permit matter / precedent) | `case_id` | `cwa_investigations.json` | `<Party>-<Place>-<subject>-<year>` |
| Conflict site | `site_id` | `dc_water_conflicts.json` | `<place>-<operator>` slug |
| Operator claim | `id` (claim) | `company_water_claims.json` | `<company>-<topic>-<qualifier>` |
| News item | `id` (news) | `water_news.json` | `<topic>-<yyyy>-<mm>` |
| Solution | `id` (solution) | `water_solutions.json` | slug |
| Company | `company_slug` | `company_water_claims.json:companies` | slug |
| Facility / permit (quantitative pipeline) | `npdes_permit_no`, future `frs_registry_id` | `config.py`, `results.csv` | agency-issued |

**Closed taxonomies (test-enforced; changes require updating the enforcing test + description map in the same commit):**

| Taxonomy | Values | Where enforced | Status |
|---|---|---|---|
| Legislation principles | 13 tags | `LEGISLATION_PRINCIPLE_DESCRIPTIONS` | exists |
| Case `case_type` | 10 | `CWA_CASE_TYPE_LABELS` | exists |
| Case `category` | datacenter / adjacent / industrial / precedent | tests | exists |
| Authority family (was "statute") | CWA, SDWA, TSCA, RCRA, RHA **+ new doctrine families (Spec C)** | `WATER_STATUTE_ORDER` | extend |
| Authority `kind` | `federal-statute` / `state-doctrine` / `common-law` / `interstate` / `constitutional` | **new** (Spec C) | new |
| Instrument `instrument_type` | `bill` / `executive-order` / `agency-rule` / `commission-docket` / `local-ordinance` | **new** (Spec B) | new |
| Issue type | 10–14 values | **new** (Spec A) | new |
| Outcome type | 12 (already mapped in `docs/cwa-outcome-taxonomy.md`) | promote to data + test (Spec C3) | designed |
| News tags | 6 | `NEWS_TAG_LABELS` | exists |
| Claim assessment | Delivered / Partial / Contested / Shortfall / Unassessed (+ **`Litigated`**, Spec A2) | `DELIVERED_STATUS_COLORS` | extend |

**Cross-reference edge catalog** (the graph; every edge type gets one referential-integrity test):

```
case.authorities            -> reading_id[]        (exists, tested)
reading.example_case_ids    -> case_id[]           (exists, tested)
site.applicable_readings    -> reading_id + case_id[] (exists, tested)
site.related_case_ids       -> case_id[]           (exists, tested)
case.analogous_cases        -> case_id[]           (exists, tested)
news.cross_ref_*            -> prose               (exists — REPLACE, 0.4)
claim.related_site_ids      -> site_id[]           (NEW, Spec A)
claim.challenged_in         -> case_id[]           (NEW, Spec A2)
instrument.related_case_ids -> case_id[]           (NEW, Spec B — e.g. EO 14318 -> NWP-39 case)
instrument.implements       -> bill_id[]           (NEW, Spec B — agency rule -> enabling act/EO)
site.issue_types            -> issue-type taxonomy (NEW, Spec A)
case.outcome_type           -> outcome taxonomy    (NEW, Spec C3)
solution/news cross_ref_targets -> any id          (NEW, 0.4)
```

### 0.3 Architecture & modules

Extract a small package — the *only* structural refactor in this plan:

```
refdata/
  __init__.py      # re-exports; dashboard.py keeps working via `from refdata import ...`
  loaders.py       # the seven _load_*_cached/load_* pairs (mtime-signature caching, moved verbatim)
  registry.py      # NEW: build_registry() -> {id: Ref(kind, tab, anchor, display_label)}
                   #      one dict over all datasets; collision check at load time
  taxonomies.py    # the closed-taxonomy constants (principles, case types, statute order/colors,
                   #      NEW kind/instrument_type/issue_type/outcome_type maps)
  integrity.py     # edge-walking helpers used by tests (resolve_edges(dataset) -> [(src,dst,kind)])
```

Rules: modules are **pure** (no `streamlit` import — same rule the `_build_*_html` builders already follow); `dashboard.py` and `build_site.py` both import from `refdata`; builder functions stay in `dashboard.py` for now (moving them is churn without payoff). ~400 lines move, no behavior change, test suite is the guard.

### 0.4 Kill prose-substring cross-linking (PR #17 follow-through)

Add optional `cross_ref_targets: [<any id>]` to news + solutions entries. Renderers resolve ids through `registry.py` into `→` deep links (tab + anchor). `_linkify_refs` stays as fallback for legacy prose. Test: any entry with `cross_ref_targets` renders exactly len(targets) links in built HTML; unknown id fails the integrity test. (Direct lift from backlog "Explicit cross_ref_targets" item — this plan is its execution vehicle.)

### 0.5 Data flows (system-level)

```
curated JSON (7 files, append-only)          scrapers (22) --> results.csv/json
        │  refdata.loaders (mtime cache)              │
        ▼                                             ▼
   refdata.registry ──────────────┐          load_data() / dedup
        │                         │                   │
        ▼                         ▼                   ▼
  dashboard.py pure builders  (shared)         Data-tab charts
        │                         │
   Streamlit app          build_site.py ──> pages/index.html + pages/llms.txt
                                             (regenerated + committed together)
   monitors (Spec B3) ──> refresh candidates ──> human-curated JSON appends (REFRESH.md loop)
```

The curated layer stays **human-adjudicated**: monitors *propose*, humans *append*. That is a deliberate design principle (provenance + verification quality), not a missing automation.

### 0.6 SW design principles applied (recurring in every spec)

1. **Single source of truth** — data constants + pure builders shared by both surfaces; derived values (statute pills, principle counts) computed at render, never stored.
2. **Stable ids as foreign keys; display strings free to change.**
3. **Closed taxonomies, open records** — adding a record is data-only; adding a *category* is a code+test+description change, reviewed.
4. **Append-only with migration scripts** — schema changes ship as `scripts/annotate_*.py` one-offs (precedent: `annotate_cwa_schema.py`, `annotate_water_authorities.py`), never hand-edits across 90 records.
5. **Additive-first** — extend `statutes`/readings/fields before renaming anything; legacy `cwa_*` field names are documented debt, not a prerequisite (see C4 for the rename decision).
6. **Every edge tested** — a cross-reference that can dangle will dangle; integrity tests are cheaper than broken anchors.
7. **Fail-closed curation** — unverified research lands with `verified: false` + `status_detail`, mirroring legislation.json's existing convention.

---

## Section A — Issues & Claims (user ask #1: "all the data center water usage issues / claims")

Three product specs: **A1** issue-type taxonomy over the conflict registry, **A2** claims lifecycle with adjudication + litigation edge, **A3** the unified Issues & Claims UX.

### Spec A1 — Issue-type taxonomy over the conflict-site registry

**Purpose / job.** Answer "what *kinds* of water problems do data centers cause, and where is each happening?" in one glance — today that requires reading 18 prose summaries. The taxonomy is also the join key that lets legislation principles, solutions, and precedent readings say *which problem they address*.

**Data ontology.** New closed taxonomy `ISSUE_TYPE_LABELS` (in `refdata/taxonomies.py`), applied as `issue_types: [tag, ...]` (1–3 per site) on every `dc_water_conflicts.json` entry, plus optionally on cases (category datacenter/adjacent) where classification is obvious. Final 14-value set (merged from the direct pass + agent-A's verified proposal; each with a 1-line description map; example items agent-verified 2026-07-25):

| tag | covers | verified examples |
|---|---|---|
| `aquifer-depletion` | groundwater drawdown beyond sustainable yield, neighbor well failures | Meta Newton County GA; Corpus Christi-Sinton Evangeline; Ogallala buildout (Fermi "Project Matador" Amarillo) |
| `supply-strain` | municipal/utility capacity + drought competition with residents/agriculture | Jul 2026 heatwave; Carvins Cove drought restrictions during the Google-Botetourt fight |
| `supply-secrecy` | NDAs, redactions, contested FOIA | WVWA/Google Botetourt (Gendreau v. McEvoy FOIA ruling, Nov 2025); The Dalles |
| `supply-contract-dispute` | fights over utility↔DC water-sale agreement terms | WVWA/Google USA (2 MGD actual vs 11 MGD rejected ask); Loudoun aggregate sales |
| `rate-cost-shift` | water/sewer infrastructure costs socialized to ratepayers | PWC IUS ERU allocations; MI SB 1047/1050 CBA demands |
| `discharge-quality` | direct NPDES/blowdown, thermal, nitrate | AWS Lake Anna (final permit); Amazon Boardman nitrate; Homer City PA |
| `pretreatment-potw` | contamination introduced into municipal/reclaimed systems | **Meta Cheyenne WY** reclaimed-system bacterium (federal pretreatment SNC classification, Meta appealing) |
| `construction-impacts` | §404 wetlands/streams, frac-outs, sediment | New Carlisle IN; Google Fort Wayne; Quantum Loophole MD |
| `moratorium-pause` | government halts pending study (any level) | NY EO 62; Brookhaven NY (sole-source aquifer); Missoula MT; Charlotte NC |
| `siting-zoning-defeat` | rezoning losses, siting rejections, process fights | Tucson Project Blue; PW Digital Gateway (voided); Caledonia WI |
| `greenwashing-claims` | challenges to water-positive/efficiency claims as unverifiable | AWS Wangusi suit; Latitude Media peak-capacity critique of Google |
| `indirect-power-water` | water embedded in the facility's electricity | UT Austin TX white paper direct+indirect framing; KHI LCA range |
| `disclosure-gap` | absent/non-standard facility-level reporting | Amazon first-ever aggregate disclosure; Google site-level lead vs peers' opacity |
| `alt-source-adoption` | greywater/reclaimed/air-cooling shifts (the "solutions" edge of issues) | xAI Memphis greywater plant (construction resuming, target Q1 2027); AWS Melbourne recycled contract |

**Back end / architecture.** Migration script `scripts/annotate_issue_types.py` (one-off, prints a diff summary, follows `annotate_cwa_schema.py` conventions); new entries ship tags inline afterward. Schema test mirrors the principle-tag test: every site has ≥1 tag, every tag is a taxonomy member.

**Front end / UX.** Part 4 site cards get an outline-chip row (per DESIGN.md §8 — outline chips for type tags, filled pills stay reserved for status); Part 4 gains an issue-type filter (multiselect, `key="conflict_issue_filter"`) and the Part 4 summary line becomes a computed count-by-issue-type strip. Static site mirrors via the existing filter-JS pattern.

**Data flow.** JSON → loader → `_build_conflict_site_html` (chip row) + new `_conflict_issue_summary()` pure builder → both surfaces + llms.txt one-liners gain `[issue-type]` prefixes.

**Tests.** Taxonomy membership; ≥1 tag/site; filter renders count; llms.txt contains tags.

### Spec A2 — Claims lifecycle: adjudication + the claims→litigation edge

**Purpose / job.** Operator claims are no longer just marketing to fact-check — they are becoming *legal exposure* (the July 2026 AWS suit pleads the company's own sustainability statements). The tracker should show each claim's full lifecycle: **made → assessed (delivered/partial/shortfall) → challenged (litigation/regulatory) → resolved**.

**Data ontology.**
- `company_water_claims.json` entries gain: `claim_type` (closed: `water-positive-pledge` / `efficiency-wue` / `replenishment-milestone` / `site-specific-promise` / `zero-water-design` / `disclosure-transparency`), `related_site_ids: []`, `challenged_in: [case_id]` (usually empty).
- `delivered.assessment` vocabulary gains **`Litigated`** (claim's truth is now before a court/regulator) — added to `DELIVERED_STATUS_COLORS` with the amber "contested" treatment, distinct label.
- Greenwashing suits enter `cwa_investigations.json` as cases (`category: datacenter`, `case_type: greenwashing-litigation` — **new 11th case_type**, since consumer-protection/securities theories over water claims fit no existing type) with `authorities` pointing at a new reading (Spec C adds `sl-consumer-protection` under a `State-law` family) — or, conservatively, `case_type: water-supply-conflict` if we choose not to open the taxonomy; decide at build time, default to the new type.
- The claim↔case edge is **bidirectional by construction**: `claim.challenged_in` ↔ case listed with the claim id in a new optional `related_claim_ids`. Integrity test walks both directions.

**Seed data (agent-verified 2026-07-25; sources in research appendix):**

| item | verified facts | maps to |
|---|---|---|
| **AWS whistleblower suit** (filed ~2026-07-15, Arlington County Circuit Court, VA) | Dr. Nathan Wangusi — AWS's *former water sustainability program manager* — sued AWS + lobbying group Virginia Connects under Virginia deceptive-trade-practices law, using FOIA'd utility billing records to challenge AWS's "42% YoY reduction," "75% of the way to water positive," and "97% of the year without water cooling" claims; seeks declaratory judgment + forced water accounting to VA regulators. AWS: data "independently assured." (Docket number single-sourced — re-verify before dataset entry.) The state-consumer-protection theory **does not fit the current 5-statute authorities schema** — the concrete forcing function for Spec C1's state-law family | new case + `challenged_in` on `aws-water-positive-2030` + news |
| **Google pledge language change** (2026-06-03, blog.google — Koley/Townsend) | New commitment: "replenish more water than we consume at our sites by 2030" — the **120% figure is gone** from the pledge the tracker captured in May. 2025: >7B gal replenished, 165 projects/97 watersheds; projects projected >19B gal/yr by 2030. Latitude Media flags VA development agreements listing peak capacity to 8M gal/day | update `google-water-replenish-120` + new claim entry (superseding language, `claim_type: water-positive-pledge`) |
| **Microsoft water claims** (2026-06-24 blog) | "90%" = fleet-average WUE improvement over two decades (2.3 → 0.27 L/kWh, 2025) from the cooling-method shift, *not* a newest-facilities-only figure; FY25 first year replenishment > withdrawal — a **global aggregate**, not basin-level, ~5 years early | update `ms-water-positive-2030` (self-reported "achieved"; independent adjudication pending) + new WUE claim |
| **WVWA/Google Botetourt correction** (2026-07-20/22, WDBJ7) | WVWA never authorized 11 MGD — that figure came from *rejected 2024 negotiations*; the executed Utility Service Agreement (board 2025-09-10, executed 2025-10-14) caps initial supply at **2 MGD** with a requestable **8 MGD ceiling**. Context: Nov 2025 *Gendreau v. McEvoy* Roanoke Circuit Court FOIA ruling forced release of the redacted water figures (WVWA signaled appeal); public open house 2026-08-25; active Carvins Cove drought restrictions since 2026-07-09 | **new conflict site** (`roanoke-botetourt-google`) — issue types: supply-secrecy, supply-contract-dispute, supply-strain; links the Botetourt FOIA precedent already cited in backlog's FOIA-templates item |
| **Meta Cheyenne WY contamination** (surfaced 2026-07, traced to Feb 2026 discovery) | Contractor's cooling-pipe "fill-and-flush" discharge introduced rare *Cupriavidus gilardii* into Cheyenne's reclaimed irrigation system; BOPU permanently terminated the contractor's discharge privileges, banned fill-and-flush discharges, drained/disinfected the system, classified it **"significant non-compliance with federal pretreatment regulations"** (CWA §307(b)/40 CFR 403); Meta appealing; Rep. Hageman demanding answers | **new conflict site + new `cwa_investigations` case** (industrial/pretreatment; first DC-driven reclaimed-system contamination in the record) |
| **xAI Memphis greywater plant resumes** | ~$80M recycling plant un-paused, completion target ≤Q1 2027; Colossus still drawing ~1.3M gal/day from Memphis Sand per environmental-group estimates | update tracked xAI Memphis site + the tracked paused-plant case |
| **New moratoria with aquifer rationale** | Brookhaven NY 18-mo (sole-source aquifer, ~7/17); Missoula MT approved (~7/16); Albany GA weighing 6–18-mo (Sowega Aquifer Alliance); Spokane WA considering 9-mo | news (grouped wave item) + legislation entries where adopted |
| **KHI report** (July 2026, read directly) | 183 TWh (2024) → 426 TWh (2030, +133%, LBNL-sourced); 17B gal direct water 2023, "could double or quadruple by 2028"; catalogs 12 local + 27 state 2025-26 policy actions (incl. Marana AZ potable-cooling ban, Lancaster PA 20k gal/day cap — both new to the tracker) | news (research tag); Marana/Lancaster → legislation candidates |
| **AWS adds water-withdrawal reporting to its customer Sustainability console** (July 2026, back to Jan 2022 data) | transparency counter-move amid the suit | news + solutions candidate |

**Back end.** Loader change is nil (fields are additive); `render_company_water_claims`/`_render_water_claim_card` + `build_company_claims` read the new fields; claims-refresh script from the existing backlog item ("scheduled refresh from sibling repo") extended to carry the new fields through.

**Front end / UX.** Claim cards gain: claim-type outline chip; "⚖ Challenged in court" badge (danger-tint pill) linking to the case card when `challenged_in` is non-empty; site links (`→ <site>`) when `related_site_ids` set. The Claims tab summary panel becomes a 2×3 matrix: claims by company × {assessed, unassessed, litigated} counts.

**Data flow.** claims JSON ↔ (bidirectional integrity) cases JSON → registry-resolved deep links both directions → both surfaces.

**Tests.** New-taxonomy membership; bidirectional edge integrity; `Litigated` renders with correct colors; case card shows claim backlink.

### Spec A3 — Unified "Issues & Claims" surface

**Purpose / job.** Today the story is split across four tabs (Water Cases Part 4, Claims, News, and prose in Legislation notes). One surface should answer, for a journalist/advocate/planner: *"What's the problem, who's involved, what do the companies say, and did they deliver?"*

**Design decision (recommended: restructure, don't add a tab).** Tab count is already high; instead:
- Rename the **Claims** tab → **"Issues & Claims"**.
- Move Part 4 (conflict sites) from Water Cases into it, becoming its first section — Water Cases sheds its least-legal section and becomes a pure legal-record tab (Parts 1–3), which also resolves its length problem. Anchors keep working via registry-generated cross-tab links (`#site-*` anchors move; the registry makes the move a one-constant change).
- Section order: ① issue-type summary strip → ② conflict sites (filterable by issue type / state / operator) → ③ operator claims (filterable by company / claim type / assessment) → ④ "claims under challenge" callout listing every `challenged_in` edge.
- Every conflict-site card cross-links its operator's claims (`company_slug` join) — the "says vs. does" juxtaposition is the product's sharpest feature: *Meta Newton County card shows Meta's water-positive claim chip right next to the dry-wells narrative.*

**Front-end conventions:** all per DESIGN.md — one `st.subheader`, summary panel first, `h3.solution-cat-header` section heads, outline chips for types, filled pills for status, left-border callouts for the challenge box; no new colors beyond the existing semantic palette.

**Back end.** Pure reorganization of existing builders + new `_build_says_vs_does_html(site, claims)` builder; `build_site.py` tab list updated; llms.txt section moves with it.

**Tests.** Tab composition test (site cards render in new tab, not in CWA tab); says-vs-does join renders for a known operator; anchor-move regression (old `#site-` anchors present in new tab).


## Section B — Policy Instruments (user ask #2: legislation, EOs, policy changes)

Three product specs: **B1** instrument-type generalization + the federal executive layer, **B2** utility-commission docket tracking, **B3** the status-monitor pipeline that keeps it all current.

### Spec B1 — From "legislation" to "policy instruments" (+ the missing executive layer)

**Purpose / job.** The dataset already quietly holds non-bills (OH EPA draft general permit, Loudoun ZOAM, UT EO 2026-03) — formalize that: one registry of *every lever government pulls on DC water*, with the federal executive-action layer (EOs, agency implementing actions) added, because that layer currently *shapes the §404/§402 permitting terrain the rest of the tracker records* and is wholly absent.

**Data ontology.**
- `legislation.json` entries gain `instrument_type`: `bill` / `executive-order` / `agency-rule` / `commission-docket` / `local-ordinance`. Migration script back-fills the 54 existing entries (52 bills, 1 rule, 1 ordinance, 1 state EO — mechanical). `bill_id` stays the key name (stable-ids principle; documented as semantically "instrument id").
- New edges: `related_case_ids` (EO 14318 → the NWP-39 reissuance case already tracked) and `implements` (agency rule → its enabling bill/EO: VA DEQ reporting regs → `VA HB 496 / SB 553`; NWP 39 → `US EO 14318`). Both registry-resolved, integrity-tested.
- Principles taxonomy: add one tag — `permitting-acceleration` (the federal EO layer's defining principle; nothing in the current 13 captures *speeding water permitting up*, only slowing/conditioning it). Requires the usual taxonomy-change trio: description map + test + summary panel handles it automatically.

**Seed data (agent-verified 2026-07-25; primary sources in the research appendix):**

*New entries:*

| entry | instrument_type | status | water relevance (verified) |
|---|---|---|---|
| **US EO 14318** — Accelerating Federal Permitting of Data Center Infrastructure (signed 2025-07-23, 90 FR 142) | executive-order | in force, substantially implemented | §404/RHA §10 NWP review in 180 days (→ produced the 2026 NWP 39 reissuance naming data centers, already tracked — link via `related_case_ids`); NEPA CEs; ESA §7 *programmatic* consultation for 10-yr construction windows; brownfield/federal-land siting; FAST-41 expansion; >100 MW "Data Center Project" + $500M/national-security "Qualifying Project" definitions. **No NPDES directive — §404 only** (seed corrected) |
| **NY Executive Order No. 62** (signed 2026-07-14) | executive-order | in force | **First statewide DC moratorium in effect, via EO not statute**: 1-year pause on DEC discretionary permits at ≥50 MW (vs. the bill's 20 MW); DPS ordered to report on impacts incl. water use/quality; DEC ordered to assess whether the water-withdrawal program needs new large-user rules (12-month deadline). Supersedes the "awaiting Hochul" framing on tracked NY S10642/A11560 — a competing-instrument dynamic, likely eventual veto |
| **America's AI Action Plan** ("Winning the Race," 2025-07-23) | executive-order (policy blueprint) | in force | called for a data-center-tailored §404 nationwide permit + CWA/CAA burden reduction + FAST-41 expansion — the blueprint EO 14318 implements (`implements` edge: EO 14318 → Action Plan) |
| **QTS Richmond Technology Park DC5 FAST-41 designation** (2026-04-02) | agency-rule (FAST-41 covered-project action) | in force | first-ever data center under FAST-41 transparency/permitting coordination; Army Corps federal lead; in-state (VA) |
| **VA DEQ waterworks reporting regulations** (implementing HB 496/SB 553; adopted, press 2026-06-25/26) | agency-rule | adopted; first aggregate report due **2026-10-01**, categorized monthly reporting begins **2027-01-01** | waterworks operators report monthly sales categorized: DC-with-air-permit / domestic / industrial-commercial / other, potable vs non-potable split; individual facilities stay trade-secret-protected — resolves the backlog's open "reporting channel" question (DEQ/SCC coordinated, aggregate-only public data; scraper target = the categorical reports) |
| **MI SB 1046–1050 package** (~2026-07) | bill | introduced | SB 1046: permit for ≥550k gal/day users, 2 MGD consumptive cap, ≥3 pre-application hearings, annual reporting from 2027, revocation for reporting failures; SB 1049 bars NDAs where tax incentives received; SB 1050 mandates CBAs covering water. Reconcile against tracked MI SB 762 / SB 1018-1020 |
| **WV HB 4832** (introduced 2026-01-26, Del. Hansen) | bill | died in committee (sine die 2026-03-14); its water protections also **voted down** as HB 2014 floor amendments | DEP authority to limit water use on adverse impact + water-resource assessments for "high-impact data centers" — a documented case of water protections being affirmatively stripped from an enacted DC framework; strong contrast entry |
| **Local moratoria wave with water rationale (Jul 2026)**: Prince George's Co MD (2-yr, 7/7), Montgomery Co MD (18-mo + >25 MW zoning ban, final vote 7/28 — *pending*), Washington Co MD (1-yr, 7/2, farm-well/drought rationale), Santa Fe Co NM (18-mo, 7/2, 1 MW threshold, groundwater/acequias), York Co SC (9-mo, groundwater + waste-heat study) | local-ordinance | adopted (except Montgomery pending) | groundwater/supply rationales explicitly cited; adjacent to tracked Loudoun ZOAM + Denver CB 26-0431 pattern |

*Status changes to existing entries:* **AWS Lake Anna case** — DEQ issued the **final 5-year VPDES permit** (~effective 2026-08-01): 0.28 MGD noncontact cooling to Sedges Creek, daily temp/pH/TRC monitoring, monthly metals, toxicity testing — the first direct hyperscaler cooling-water NPDES-family permit in VA is now *live* and becomes an EPA ECHO DMR target when reporting starts. **US S. 4213** — title/content is explicitly water *and* energy (tracked label undersells water). **CA SB 887** — passed Senate 29-9, in Assembly Appropriations 6/29. **S. 4214** — no floor action. **OHD000001** — still not finalized (no change).

**Back end / architecture.** Additive fields + migration script; `_legislation_rows`/`_build_bill_card_html` read `instrument_type` for a new outline chip; summary panel gains an instruments-by-type count line. The federal executive layer is data, not new code.

**Front end / UX.** Legislation tab renamed **"Policy"** (title + tab label only; anchors preserved). New instrument-type filter pill row (5 values) beside the existing status/level/scope/principle filters. Executive-order cards carry a distinct outline chip ("EO") in the existing purple coming-soon/notice hue — purple already signals "regulatory/upcoming" in DESIGN.md's semantics and is not repurposed. `implements`/`related_case_ids` render as the standard `→` cross-links.

**Data flows.** No new pipelines; the entries flow through the existing loader → builders → both surfaces → llms.txt (test-enforced inclusion).

**Tests.** instrument_type membership + back-fill completeness (every entry has one); edge integrity for `implements`/`related_case_ids`; EO chip renders; filter counts.

### Spec B2 — Utility-commission (PUC/PSC) docket layer

**Purpose / job.** Rate design is becoming *the* water-adjacent battleground (who funds infrastructure; whether DCs get special water/sewer classes). These live in commission dockets, not legislatures — a structurally different source with docket numbers, intervenors, and orders. Tracking them closes the "policy changes" gap between bills (B1) and outcomes.

**Data ontology.** Same file, `instrument_type: commission-docket`; `bill_id` convention `"<STATE> PUC <docket-no>"`; `status` maps naturally (open docket = `introduced`, order issued = `enacted`, dismissed = `failed`) with `status_detail` carrying docket-specific nuance.

**Scope correction from verification (important):** the marquee DC rate dockets are **energy-only** — AEP Ohio's data-center tariff (PUCO Case 24-508-EL-ATA, order Jul 2025), the GA PSC large-load tariff/investigation, and the Dominion SCC large-load proceedings all carry **no water provisions** (agent-verified against commission fact sheets). A water tracker should not dilute itself with them. In-scope water-relevant docket seeds (verified):
- **TX PUC + ERCOT + Texas Water Development Board joint voluntary DC water survey** — the only water-specific PUC action found nationally; 28 companies / 92 facilities responded (low compliance, already a tracked news item); Gov. Abbott now pushing mandatory PUCT/ERCOT registration — track the registration mandate as it forms.
- **NY DPS environmental-impact report** ordered by EO 62 (water use/quality explicitly in scope; 12-month deadline) — the docket-shaped implementation edge of the EO entry (`implements` edge: DPS report → NY EO 62).
- Future water-utility commission cases creating DC water classes (IA HF 2447's implementation path; any state following). The energy-only dockets get one *note* line in the Sources tab context, not entries.

**Why same-file, not a new dataset:** dockets share the full bill lifecycle (introduced→decided, sponsors→parties, timeline, principles) and the UI treats them identically with one chip. A separate file would duplicate schema+loader+tests for zero rendering difference. (Design principle 3: closed taxonomies, open records.)

**Front end.** Nothing beyond B1's chip + filter. Docket cards' timeline entries use filing/order dates.

**Tests.** Convention test: every commission-docket entry's `bill_id` contains a docket number; timeline non-empty.

### Spec B3 — Status-monitor pipeline (make freshness a system property)

**Purpose / job.** Six pending decisions are known to flip soon (NY moratorium signature, OHD000001, AWS Lake Anna VPDES, VA first HB 496 reports ~Aug/Sep 2026, MI SB 1046, Durbin bill number). Today each is a manual re-research. Build the *watch* half of the append-only loop: monitors that detect change and emit refresh candidates; humans adjudicate and append (per 0.5's fail-closed curation).

**Architecture & modules.**

```
scrapers/monitors/
  base_monitor.py        # BaseScraper subclass: fetch → extract status signal → diff vs. state DB
  legiscan_bills.py      # LegiScan API: status of every legislation.json entry with a legiscan id
  federal_register.py    # FR API: EO/rule search terms ("data center" + water/permitting)
  va_deq_hb496.py        # watches the DEQ/SWCB reporting portal for first monthly reports (unlocks the
                         #   Tier-1 scraper build in backlog the moment data exists)
  decision_watch.py      # small config-driven page watchers for the named pending decisions
                         #   (OHD000001 page, DEQ Lake Anna notice page, NY governor actions page)
storage/monitor_state    # reuse scraper_state.db (scraper_name, document_id) dedup pattern
output: data/output/monitor_hits.json  (append-only candidate queue with source URLs + diff summary)
```

Runs manual or scheduled (existing backlog cron item); `REFRESH.md`/data-refresh skill consumes `monitor_hits.json` as its work queue. Rate limits + randomized delays per CLAUDE.md scraping principles; LegiScan needs an API key → config.py, never committed.

**Data ontology.** Monitored entries carry `monitor: {kind, key}` in their JSON (e.g. `{kind: legiscan, key: "NY S10642"}`, `{kind: url-watch, key: "<page>"}`) so the monitor set is *derived from the dataset* — no second list to drift (single-source-of-truth principle).

**Front end.** Sources-tab "Coming data" rows get live status dots fed by the latest monitor run's timestamp file — deliberately minimal; monitors are ops, not UX.

**Tests.** Monitor diffing against fixture snapshots (changed/unchanged/new); candidate-queue append-only writer; `monitor` field schema.


## Section C — Precedent Engine (user ask #3: expand historic precedent + innovative applications)

Three product specs: **C1** generalize the authorities registry beyond federal statutes, **C2** the expanded precedent case corpus, **C3** the application-mapping engine (fact pattern → doctrines → likely outcomes). This section's core insight: the existing architecture (readings registry + `authorities` edges + derived pills) **already generalizes** — the expansion is almost entirely *data plus taxonomy constants*, which is the strongest possible validation of the June/July schema work.

### Spec C1 — Authorities registry: from 5 federal statutes to the water-law doctrine universe

**Purpose / job.** A data-center water fight in Memphis turns on interstate aquifer law; in Georgia on well-interference and public-trust arguments; in Texas on capture/takings doctrine; in Wisconsin on the Great Lakes Compact. None of that is CWA/SDWA/TSCA/RCRA/RHA — the registry must speak state allocation law, common law, interstate law, and constitutional law to cover how water law actually reaches data centers.

**Data ontology.**
- `water_authorities.json:statutes` (dict keyed by short code — the key design decision made in July holds up) gains new families, each entry gaining a `kind` field (`federal-statute` for the existing 5; new kinds per 0.2). Verified family set:

All anchors below are **agent-verified 2026-07-25** (Justia/CourtListener/official sources; two seed captions corrected in verification — see appendix). 12 families:

| code | family (kind) | verified anchor readings (`reading_id` slugs) |
|---|---|---|
| `EQAP` | Interstate apportionment & compacts (interstate) | `eqap-interstate-aquifer` (Mississippi v. Tennessee, No. 143 Orig., 2021 — Memphis Sand subject to equitable apportionment, unanimous; Florida v. Georgia 2021 sets the clear-and-convincing injury bar), `eqap-compact-diversion` (Racine/Foxconn 7-MGD Lake Michigan diversion approved 2018, MEA challenge, WI ALJ upheld 2019 — the *same* diversion now supplying Microsoft Mount Pleasant), `eqap-commerce-clause` (Sporhase v. Nebraska, 458 U.S. 941 (1982) — groundwater is an article of interstate commerce; limits state water-export bans) |
| `PTD` | Public trust doctrine (state-doctrine) | `ptd-reopener` (Nat'l Audubon Soc'y v. Superior Court, 33 Cal. 3d 419 (1983) — no appropriative right immune from trust reconsideration), `ptd-groundwater-nexus` (ELF v. SWRCB, 26 Cal. App. 5th 844 (2018) — trust reaches groundwater pumping harming navigable waters; survives SGMA), `ptd-precautionary` (Waiāhole Ditch, 9 P.3d 409 (Haw. 2000) — affirmative protective duty over all state water) |
| `GW` | Groundwater property & allocation doctrines (state-doctrine) | `gw-capture-limits` (Sipriano v. Great Spring Waters, 1 S.W.3d 75 (Tex. 1999) — capture reaffirmed vs a commercial bottler), `gw-ownership-takings` (EAA v. Day, 369 S.W.3d 814 (Tex. 2012) — groundwater owned in place; regulation can be a taking), `gw-correlative` (Katz v. Walkinshaw, 141 Cal. 116 (1903)), `gw-reasonable-use` (Bristor v. Cheatham, 75 Ariz. 227 (1953)), `gw-beneficial-waste` (A-B Cattle Co. (Colo. 1978) — anti-waste limit on beneficial use) |
| `WELL` | High-capacity-well & withdrawal-permit review (state-doctrine) | `well-cumulative-impact` (Lake Beulah Mgmt. Dist. v. DNR, 2011 WI 54 — affirmative duty to weigh well impacts on trust waters), `well-regulated-riparian` (VA VWP ≥10k gpd regime + grandfathered-exclusion gap; MI WWAT registration — flagged: **no litigated MI case yet**, tracked as a doctrinal gap, not an anchor) |
| `GWMGMT` | Statutory groundwater-management regimes (state-doctrine) | `gwmgmt-sgma` (Cal. SGMA 2014, §10720 et seq. — high-priority-basin sustainability plans; coexists with PTD per ELF), `gwmgmt-az-ama` (AZ Groundwater Management Act 1980 — AMA assured-water-supply rules; what actually governs Tucson Project Blue inside an AMA), `gwmgmt-mi-wwat` (MI large-quantity-withdrawal prescreen) |
| `XFER` | Water sourcing & transfer law (state-doctrine) | `xfer-area-of-origin` (Tex. Water Code §11.085 junior-priority-on-interbasin-transfer — on point for Cedar Creek Lake / Lake Texana-style out-of-basin piping), `xfer-forfeiture` (CO decennial abandonment regime, C.R.S. §37-92-401 et seq. — "use it or lose it" risk in acquiring senior agricultural rights for DCs) |
| `ESA` | Endangered Species Act as water constraint (federal-statute) | `esa-springflow-mandate` (**Sierra Club v. Lujan**, 1993 WL 151353 (W.D. Tex. 1993) — §9 take from failure to set Edwards springflow limits; ordered the regime that became the EAA. *Seed caption corrected: "Babbitt" (5th Cir. 1993) was only intervenor standing*), `esa-proximate-cause-limit` (Aransas Project v. Shaw, 775 F.3d 641 (5th Cir. 2014) — state permitting too causally remote from downstream take; deliberate counter-precedent) |
| `TRIBAL` | Federal & tribal reserved rights (federal-doctrine) | `tribal-winters` (Winters v. United States, 207 U.S. 564 (1908)), `tribal-groundwater` (Agua Caliente Band v. CVWD, 849 F.3d 1262 (9th Cir. 2017), cert. denied — reserved rights extend to groundwater) |
| `SEPA` | State environmental review / water-supply adequacy (state-doctrine) | `sepa-paper-water` (Vineyard Area Citizens v. Rancho Cordova, 40 Cal. 4th 412 (2007) — EIR must show a *realistic* long-term supply; codified via SB 610/221 WSAs), `sepa-review-injunction` (MCEA v. Pine Island TRO, Goodhue Co. Minn. 2026 — already tracked; inadequate water disclosure in review = irreparable harm) |
| `CL` | Common-law interference, nuisance & standing (common-law) | `cl-negligent-subsidence` (Friendswood Dev. v. Smith-Southwest, 576 S.W.2d 21 (Tex. 1978) — capture shields depletion, not negligent subsidence), `cl-citizen-standing-limit` (Mich. Citizens for Water Conservation v. Nestlé, 269 Mich. App. 25 (2005) — MEPA standing needs particularized injury; the standing trap for DC opposition groups) |
| `UTIL` | Municipal utility service & shortage law (state-doctrine) | `util-shortage-pretext` (Swanson v. Marin MWD, 56 Cal. App. 3d 512 (1976) — genuine shortage moratoria lawful; pretextual no-growth policy is not; + continuing duty to augment supply), `util-reasonable-use` (Cal. Const. art. X §2 reasonable-and-beneficial-use mandate) |
| `SL` | State consumer-protection / claims law (state-doctrine) | `sl-greenwashing-udap` (state deceptive-trade-practices statutes — first DC-water application: the Wangusi v. AWS suit, Spec A2; the reading the current 5-statute registry cannot express) |

  Notes from verification: a candidate "state antidegradation/thermal" family was **affirmatively excluded** as non-additive (Ohio's rule implements the same federal §316/131.12 framework the CWA registry already covers); the registry keeps *negative* applicability honest — e.g. ESA doesn't reach Memphis (no listed species on Memphis Sand springflow) and TRIBAL doesn't reach VA/Memphis (no overlying reservation) — negative examples render as "why this doctrine does NOT apply here" notes, which is product-valuable (it disciplines advocacy claims).
- Each new reading follows the existing schema exactly (`reading_id`, `statute` → family code, `section` → doctrine/cite line, `agency` → forum ("state courts", "SCOTUS original jurisdiction", "compact council"), `what_it_covers`, `dc_applicability`, `example_case_ids`).
- `dashboard.py` constants: `WATER_STATUTE_ORDER` extended (federal statutes first, then doctrine families — display order = legal-hierarchy order); `WATER_STATUTE_COLORS` gains muted differentiations within the DESIGN.md blue family + existing semantic hues (no new palette entries: reuse the 5-blue sequence + neutral gray for common-law; colors carry *family* identity, not status, so decorative-color rule is satisfied by the pill's semantic function).
- **Naming debt decision (C4 candidata):** keep `cwa_investigations.json` filename and `cwa_*` case fields. They already hold SDWA/TSCA/RCRA/RHA content; renaming (`legal_basis`, `instrument_status`…) touches ~40 call sites + tests + docs for zero user-visible gain. Document the legacy naming in CLAUDE.md; revisit only if the file is ever split. This is additive-first (principle 5) applied honestly.

**Back end.** Data + constants only; `_build_authorities_html` (accordion + jump-nav) scales to 16–17 families by construction — the 2026-07-07 collapsed-accordion + jump-nav UX shipped exactly so family count could grow without a scroll problem (the jump-nav pill row wraps; verify at tablet width in UAT); `_case_statutes` derives pills from `authorities` unchanged.

**Front end / UX.** Part 1 toolkit: new families appear as new collapsed accordions with jump-nav pills — zero new interaction patterns. One addition: a `kind` micro-label ("state doctrine", "compact", "common law") right-aligned in each accordion summary row, so users see *why* the family reads differently from a federal statute. Statute filter in Parts 1/3 picks up new families automatically (derived from data).

**Tests.** Existing `TestWaterAuthoritiesSchema` extends: `kind` membership; every family in `WATER_STATUTE_ORDER` has ≥1 reading; every reading's `example_case_ids` resolve; color map covers every family.

### Spec C2 — Expanded precedent corpus

**Purpose / job.** Give every new reading its historic record: the ~15–25 canonical cases that established each doctrine, so a user (or the Part-4 mapping) can walk from a 2026 fact pattern to the 1908–2021 case law that governs it.

**Data ontology.** New cases append to `cwa_investigations.json` with `category: precedent`, `case_type: judicial-precedent` (existing type), `authorities: [new reading_ids]`, `cwa_applied: not-applied` + `cwa_pathway` describing the doctrine's reach (the field names are legacy; the *content* is the doctrine mapping — per C1's naming decision). Fields `respondent` (full caption + cite), `violation_summary` (the dispute), `outcome` (the holding), `takeaway` (what it means for DCs) — same anatomy as `Sackett-v-EPA-2023`.

**Seed corpus — 20 verified anchors (agent-verified 2026-07-25 against Justia/CourtListener/official sources; each dataset entry still requires 2 cited sources at append time):**
Mississippi v. Tennessee, No. 143 Orig. (2021) · Florida v. Georgia, No. 142 Orig. (2021) · Sporhase v. Nebraska, 458 U.S. 941 (1982) · Racine/Foxconn Lake Michigan diversion (WI DNR 2018; ALJ upheld 2019, unappealed) · National Audubon Soc'y v. Superior Court, 33 Cal. 3d 419 (1983) · ELF v. SWRCB, 26 Cal. App. 5th 844 (2018) · In re Waiāhole Ditch, 9 P.3d 409 (Haw. 2000) · EAA v. Day, 369 S.W.3d 814 (Tex. 2012) · Sipriano v. Great Spring Waters, 1 S.W.3d 75 (Tex. 1999) · Katz v. Walkinshaw, 141 Cal. 116 (1903) · Bristor v. Cheatham, 75 Ariz. 227 (1953) · A-B Cattle Co. v. United States (Colo. 1978) · Lake Beulah Mgmt. Dist. v. DNR, 2011 WI 54 · **Sierra Club v. Lujan**, 1993 WL 151353 (W.D. Tex. 1993) *(seed said "Babbitt" — corrected)* · Aransas Project v. Shaw, 775 F.3d 641 (5th Cir. 2014) · Winters v. United States, 207 U.S. 564 (1908) · Agua Caliente Band v. CVWD, 849 F.3d 1262 (9th Cir. 2017) · Vineyard Area Citizens v. Rancho Cordova, 40 Cal. 4th 412 (2007) · Friendswood Dev. v. Smith-Southwest, 576 S.W.2d 21 (Tex. 1978) · Mich. Citizens for Water Conservation v. Nestlé, 269 Mich. App. 25 (2005) · Swanson v. Marin MWD, 56 Cal. App. 3d 512 (1976). Statutory-regime readings (SGMA, AZ GMA, Tex. §11.085, C.R.S. §37-92-401, MI WWAT) cite the statute as the anchor — the registry schema's `section` field already supports statute-only readings.

**Back end / process.** Pure data appends; `python3 build_site.py` regenerates; llms.txt inclusion is automatic + test-enforced. Cases land in batches of ~5 per commit (git-discipline: small commits) with `verified: true` semantics carried in sources.

**Front end.** None beyond C1 — Part 3's category sections already render precedent cases; the statute filter now slices them by doctrine family.

**Tests.** Corpus-size floor per family (≥1 case); citation-format spot tests; all `authorities` resolve.

### Spec C3 — Application mapping: fact pattern → doctrine → likely outcome

**Purpose / job.** This is the "innovative ways to apply those to current data center cases/issues" half of the ask, made systematic instead of essayistic: for each tracked conflict site, *which doctrine families could reach it, through what argument, and what does the historic record say usually happens?*

**Data ontology.** Three additive pieces:
1. **Site → new readings:** extend each `dc_water_conflicts.json` site's `applicable_readings` with the new doctrine readings + per-site `how` lines (agent-verified mappings, human-adjudicated at append time). Highest-value verified applications:
   - **xAI Memphis ↔ `eqap-interstate-aquifer`**: the Memphis Sand is the *same aquifer* SCOTUS held apportionable in 2021; Florida v. Georgia's clear-and-convincing bar means a Mississippi refiling would need utility-level aggregate data — exactly the class of data HB 496-style reporting laws generate (readings cross-link to Spec B entries).
   - **Microsoft Mount Pleasant WI — double exposure**: `eqap-compact-diversion` (its water arrives via the contested 2018 Foxconn diversion; a fresh Compact challenge is live if the DC load pushes the use-mix further from "public water supply") **and** `well-cumulative-impact` (any DNR high-capacity well permits face the Lake Beulah affirmative-duty standard in the same court system).
   - **Corpus Christi–Sinton TX — triple**: `gw-capture-limits` (capture is *why* the fight runs through district permits, not private suits), `cl-negligent-subsidence` (Friendswood is binding if Evangeline drawdown causes measurable Coastal Bend subsidence — sharper than the current permit fight), and `esa-proximate-cause-limit` (the site sits in Aransas/San Antonio Bay hydrology where Aransas Project is *binding* 5th Cir. law — a negative-exposure note).
   - **Meta Newton County GA ↔ `gw-reasonable-use` + `cl-negligent-subsidence` analog**: Georgia's reasonable-use substance gives failed-well neighbors a direct common-law theory a Texas neighbor would lack; injured neighbors as plaintiffs sidestep the Michigan-Citizens standing trap.
   - **Bessemer AL ↔ `util-shortage-pretext` (Swanson in reverse)**: the utility's own "cannot serve without significant upgrades" admission means approving invites a duty-to-existing-ratepayers theory while denying would survive a pretext challenge — the doctrine cuts *for* the utility saying no.
   - **Tucson Project Blue ↔ `gwmgmt-az-ama`** (the AMA assured-water-supply regime, not Bristor common law, is what actually governs inside the AMA — and explains the project's pivot) + `ptd` marked **negative** (AZ has never extended trust to groundwater).
   - **Imperial Valley IID ↔ `tribal-groundwater`/`tribal-winters` (novel)**: senior tribal rights in the same Colorado River reach outrank IID's entitlements — if the IVCM suit succeeds, under-delivered senior tribal claims are the stronger follow-on nobody has raised.
   - **Fort Worth Cedar Creek Lake ↔ `xfer-area-of-origin`** (Tex. §11.085 junior-priority-on-transfer is the sharp legal tool the political campaign never used); **Saline Township MI ↔ `gwmgmt-mi-wwat` + `cl-citizen-standing-limit`** (Michigan Citizens narrows exactly the standing an opposition group needs).
   - **Negative mappings render too**: ESA ∅ Memphis (no listed species on Memphis Sand springflow); TRIBAL ∅ Memphis/NoVA (no overlying reservation) — displayed as "doctrines that do NOT reach this site," which disciplines both advocacy and reporting.
2. **`outcome_type` promotion** (executes the existing backlog item): every case gains `outcome_type: []` from the 12-value taxonomy in `docs/cwa-outcome-taxonomy.md`; script `scripts/annotate_outcome_types.py`; schema test.
3. **`analogous_outcome_note`** per site (also from that backlog item): one sentence naming closest historical case(s) by outcome type — now *computable* as a candidate (mode of `outcome_type` across the site's linked cases) with human-written final text.

**Back end / architecture.** One new pure builder `_build_site_doctrine_matrix_html(sites, readings)` → compact matrix (site × family, cells = linked reading count) used as the section summary panel; `_conflict_outcome_note_html` renders piece 3. Both surfaces via the standard path.

**Front end / UX.** In the Issues & Claims tab (A3), each site card's reading list groups by family with family pills; the matrix panel leads the section ("which doctrines are in play where" at a glance — the precedent engine's product face). In Water Cases Part 2, the theories table (`CWA_APPLICATION_THEORIES`) gains a sibling: doctrine-family theories with the same Impact/Viability/Tractability scoring — scored rows for `eqap-interstate-aquifer`, `ptd-navigable-harm`, `cl-well-interference`, `sepa-supply-adequacy` at minimum, so the panel stops being CWA-only (continues the 2026-07-07 statute-breadth direction).
- **Copy discipline:** applications render with explicitly modal language ("could reach", "has been argued") — the tracker maps *legal exposure*, it does not predict outcomes or advocate suits. Scoring stays merit-only per the existing theories-panel rule.

**Data flows.** agent research → human adjudication → JSON appends → derived matrix/pills at render → both surfaces + llms.txt.

**Tests.** Matrix counts = edge counts; outcome_type membership + coverage; note renders; theories table row count includes doctrine rows.


## Build status (updated 2026-07-25, branch `jam/issues-policy-precedent-plan-9d7d05`)

| Phase | State | Commits |
|---|---|---|
| **P0 Foundation** | ✅ done — `refdata/` extracted (pure, no Streamlit), registry + integrity suite, 27 entries migrated to `cross_ref_targets` | `1bcd55e` |
| **P1 Policy data** | ✅ done — `instrument_type` back-filled over 54, +13 new entries (67 total), federal executive layer, first commission dockets | `2d4fd38` |
| **P2 Precedent** | 🟡 3 of 4 batches — **16 of 17 families**, 38 readings, 107 cases. C3 piece 2 (`outcome_type`) done across all 107. **Remaining:** the `SL` family (held for A2 — its only anchor is the AWS claims suit); C3 pieces 1 and 3 (site→doctrine mappings, `analogous_outcome_note`) | `9d03727`, `25fb6ee`, `9e597ec`, `9b91560` |
| **P3 Issues/Claims** | 🟡 A1 done (issue types + filter). **Remaining:** A2 claims lifecycle, A3 tab restructure | `c462a24` |
| **P4 UX** | 🟡 chips + Part 4 issue filter done. **Remaining:** instrument-type filter, C3 doctrine matrix, doctrine rows in the theories table | `75994e3`, `14f6091` |
| **P5 Automation** | ⬜ not started | — |

**Decisions taken during the build that amend this plan:**

1. **Taxonomy values ship with their data.** A value is added to a taxonomy in the same commit as the records that use it, never ahead of them — otherwise a filter offers a category nothing is in (caught in the P0 build diff). This is why `WATER_STATUTE_ORDER` grew 5→8→12 rather than jumping to 17, the issue taxonomy shipped 11 of the drafted 14, and `greenwashing-litigation` / `litigated` / `pretreatment-potw` / `greenwashing-claims` / `indirect-power-water` are still pending their Spec A2 records.
2. **Source verification is search-only.** Justia and CourtListener both block automated requests — Justia 403s every URL including valid ones, CourtListener returns blank to WebFetch — so citation URLs cannot be pattern-guessed and confirmed. Every case ships with 2+ search-verified sources; anything that could not be tied to a retrievable source is held for a later batch.
3. **Corrections to the seed research** (each would otherwise have been baked in): the Michigan standing limit is the **2007 Michigan Supreme Court** decision (479 Mich. 280), not the 2005 Court of Appeals decision at 269 Mich. App. 25 — the 2005 panel *found* standing and was reversed; **Swanson** announced no "continuing duty to augment supply", only that a new user has no right to service and a moratorium is reviewable for fraud/arbitrariness/caprice; **CA AB 93** was vetoed 2025-10-11 (the record said October 2024) by Assemblymember Papan's bill, and had no source URL at all.
4. **`_doctrine_batch.py`** holds the shared validation for every C1/C2 batch (family/kind/colour registration, ≥2 sources, mandatory `analogous_cases`, referential checks), so batches 3–4 are data-only.
5. **UAT note:** screenshots of `pages/index.html` over `file://` come back blank — the pane renders it as a static snapshot. `javascript_tool` DOM inspection is live and is the reliable verification channel on that surface.

6. **Anchoring a family on a live matter beats inventing a historical one.** `_doctrine_batch.py` grew an `authority_additions` hook so a new reading can attach to a case the tracker already follows — the Tucson fight illustrates Arizona's AMA regime better than any 1980s precedent, and Pine Island was already the state-environmental-review case. Connecting doctrine to what is actually happening is the product, so the tooling should make that the easy path.
7. **Phrase-classifying prose needs negation and tense guards.** The `outcome_type` pass initially recorded two matters as penalised consent decrees off the sentence "No formal CWA NOV or consent order issued", and read an applicant's *proposed* mitigation as an imposed permit condition. Both are now guarded (negated-clause stripping; leading-`PENDING` forcing). Any future prose classifier over this corpus should assume both failure modes are present.

Test count: 513 at plan time → **569**.

## Phasing, sequencing, and acceptance

Order minimizes rework: foundation → data → UX → automation. Each phase is independently shippable and committed in small increments (CLAUDE.md §5); every phase ends with full suite + `python3 build_site.py` + regenerated page committed together.

| Phase | Contents | Depends on | Rough size |
|---|---|---|---|
| **P0 Foundation** | 0.3 `refdata/` extraction · 0.4 `cross_ref_targets` · registry + integrity tests | — | 1 session |
| **P1 Data — Policy** | B1 instrument_type + federal executive layer entries + status updates (NY, OHD000001, Lake Anna, IA) · B2 docket seeds | P0 (registry for edges) | 1–2 sessions |
| **P2 Data — Precedent** | C1 families + readings · C2 corpus (batched appends) · C3 pieces 2–3 (outcome_type, notes) | P0 | 2–3 sessions |
| **P3 Data — Issues/Claims** | A1 issue_types + migration · A2 claim lifecycle fields + new claims/cases (AWS suit, Google/Microsoft claims) | P0 | 1–2 sessions |
| **P4 UX** | A3 Issues & Claims tab restructure · C3 matrix + doctrine theories · B1 Policy tab chips/filters | P1–P3 data present | 2 sessions |
| **P5 Automation** | B3 monitors (LegiScan, Federal Register, VA HB 496 portal watch, decision watchers) · claims-refresh script | independent of P4 | 2 sessions |

**Acceptance criteria (plan-level):**
1. Every dataset entry reachable through the registry; zero dangling edges (integrity suite green).
2. A user can answer, without leaving the site: "What did EO 14318 change about water permitting?" (B1) · "Which conflicts are aquifer-depletion fights and what doctrine reaches them?" (A1+C3) · "What did AWS promise, and who is suing over it?" (A2) · "What happened historically when a region fought over an interstate aquifer?" (C2).
3. llms.txt carries every new entry id (existing test pattern extended).
4. No DESIGN.md violations (chips/pills semantics, palette, tab anatomy).
5. Test count grows with every data schema addition; suite stays under ~5 s.

**Risks & mitigations:**
- *Research rot* — statuses verified today flip (NY signature, OHD000001). Mitigation: `last_verified` on changed entries + P5 monitors make staleness detectable.
- *Taxonomy sprawl* — issue types / instrument types / kinds all tempt growth. Mitigation: closed-taxonomy rule (code+test+description per change) keeps additions deliberate.
- *Legal-accuracy exposure* — doctrine mappings are interpretations. Mitigation: modal copy rule (C3), 2-source minimum per case, `verified` flags, and the existing merit-only scoring rule.
- *Tab-move anchor breakage* (A3). Mitigation: registry-driven anchors + regression test on old anchor ids.

---

## Appendix — Research log (2026-07-25)

Direct pass (9 WebSearch queries + dataset gap-scan) verified: EO 14318 existence/date/§404 directive; VA HB 496 implementing-regs news (2026-06-25); MI SB 1046 / WV HB 4832 / IL SB 4016 activity; AWS greenwashing suit coverage (2026-07-15); Google water-positive pledge (2026-06-03); Microsoft efficiency/replenishment claims; WVWA 11-MGD correction (2026-07-22); Mississippi v. Tennessee holding; ELF v. SWRCB holding; EAA v. Day holding; Aransas Project v. Shaw reversal; VA VWP 10k-gpd threshold + grandfathered-exclusion gap.

**Agent pass (3 parallel Sonnet research agents, ~8–9 min each; full outputs in session transcript; evaluation logged in AGENTS.md):**

- *Issues/claims agent* (181k tokens, 50 tool uses): verified all 7 seeds with corrections — AWS suit is a **whistleblower** consumer-protection action (Wangusi, Arlington Co. Cir. Ct., vs AWS + Virginia Connects), Google **dropped the 120% figure** from its pledge, Microsoft's "90%" is a two-decade fleet WUE improvement and its water-positive year is a global aggregate. New finds: Meta Cheyenne WY reclaimed-system contamination (federal pretreatment SNC), WVWA/Google Botetourt contract truth (2 MGD actual / 8 MGD ceiling / 11 MGD was a rejected ask; *Gendreau v. McEvoy* FOIA ruling), Brookhaven NY + Missoula MT + Albany GA + Spokane WA moratoria, xAI greywater plant resuming (≤Q1 2027), KHI report read directly, AWS console water-data addition.
- *Legislation/EO agent* (129k tokens, 45 tool uses): full EO 14318 anatomy (§404/RHA-only — **no NPDES directive**, seed corrected; NEPA CEs; ESA §7 programmatic; FAST-41) + implementation chain through NWP 39, EPA brownfield guidance, DOE/Air Force land actions, and the **first FAST-41 data center (QTS Richmond, 2026-04-02)**; **NY EO 62** (2026-07-14) as the actual moratorium instrument (bill unsigned — competing-instrument dynamic); VA HB 496 regs concrete dates (first aggregate report 2026-10-01, categorized reporting 2027-01-01, facility data trade-secret-shielded); AWS Lake Anna permit **final** (0.28 MGD); WV HB 4832 died + protections stripped from HB 2014 on floor votes; MI SB 1046–1050 package; 6 local moratoria; PUC dockets triaged (energy-only vs the TX water survey).
- *Precedent agent* (138k tokens, 42 tool uses): 20 anchor cases verified; 2 seed corrections (Sierra Club v. **Lujan**; Racine ALJ posture); 1 family affirmatively excluded as non-additive (state antidegradation); 1 gap honestly flagged instead of filled (no litigated MI WWAT case); 4 additional families proposed (SGMA, AZ GMA, area-of-origin transfer, forfeiture) — folded into the final 12-family design (`GWMGMT`, `XFER`).

**Consolidated unverified list (carry `verified: false` + `status_detail` if entered before re-verification):** AWS suit docket number CL26002535-00 + the "0.8%/32.1%" FOIA-derived figures (single-sourced); Snopes verdict on Meta Cheyenne (paywalled); Meta "6B gal restoration portfolio" figure (unconfirmed date); WV HB 4832 precise procedural death (inferred from session-end reporting; wvlegislature.gov unreachable); Hamilton Co FL moratorium (proposed only); Montgomery Co MD final vote (scheduled 2026-07-28 — after this plan's date; monitor).

