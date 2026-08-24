# Spec B — Explore tab: knowledge graph + text similarity over the whole record

## Purpose

One place to ask three questions the tabs can't answer:

1. **"What connects to this?"** — pick any record (case, reading, bill, site, claim, news, solution) and walk its neighborhood along the typed edges that already exist.
2. **"What looks like this text?"** — paste a paragraph (a news story, a draft ordinance, a permit notice) and get the closest records by lexical similarity, with the matching terms shown, so the user can see *why* something ranked.
3. **"Both at once"** — restrict similarity results to a chosen node's neighborhood, or to record kinds / statute families the user selects.

Everything runs in the reader's browser with no network calls. Similarity is TF-IDF cosine computed from an index built in pure Python at generation time. Embedding-based semantics and LLM-assisted querying need live tokens → backlog.

## Architecture

New module `refdata/graph.py` (pure, no streamlit, same rules as the rest of the package):

- `build_graph() -> dict` — nodes from `registry.build_registry()` (id, kind, label, tab, anchor) enriched per kind with grouping attributes: statute family (readings), category/case_type/year (cases), status/level/jurisdiction (instruments), issue_types (sites), company + delivered status (claims), tags + date (news), category/status (solutions). Edges verbatim from `integrity.iter_edges()` as `(source, target, edge_kind)` — the graph never invents relationships; it renders the ones the datasets declare. Plus derived *family membership* edges (reading → its statute family node, case → its case_type node, instrument → its principle nodes) so taxonomy values become hub nodes; mark these `derived: true` and give them their own edge kinds (`reading.family`, `case.type`, `instrument.principle`) so the UI can toggle them separately from curated cross-references.
- `build_search_index() -> dict` — per record: tokenized text from the fields a reader would consider the record's substance (label + summary/violation/outcome/takeaway/what_it_covers/dc_applicability/pushback text, per kind). Lowercase, strip punctuation, drop a small stopword list, keep unigrams + adjacent bigrams. Store `{token: weight}` per record with weights = TF × IDF, records L2-normalized, vocabulary pruned to tokens appearing in ≥1 record with document frequency < 60% of records. Deterministic ordering (sorted keys) so regeneration is diff-stable.
- Both serialize to one JSON blob embedded in the page (`<script type="application/json" id="graph-data">`). Budget: keep the blob under ~600 KB pretty-unminified; if larger, round weights to 3 decimals and cap per-record vocabulary at the top 60 tokens.

## Static-site UI (`build_site.py` — new tab `explore`, label "Explore")

- **Layout:** left column = controls + results list; right column = canvas graph. Stacks vertically under 900 px.
- **Graph:** vanilla-JS force-directed layout on `<canvas>` (repulsion + spring along edges + centering gravity, ~120 iterations then settle; no external library). Nodes colored by kind using existing palette hues; taxonomy hub nodes rendered as small squares. Click node → focus mode: show its 1–2-hop neighborhood (depth toggle), dim everything else, render the record's label + kind + "open card" link (tab anchor — the registry's whole point). Drag to pan, wheel/buttons to zoom. Cap initial render to the curated-edge subgraph; derived taxonomy edges appear when toggled on.
- **Search box:** textarea ("paste any text — a news story, a permit notice, a bill summary") + kind checkboxes + statute-family select + optional "within N hops of the focused node" toggle. On input (debounced), tokenize with the same rules as Python (implemented once in JS; a build test round-trips a fixture string through both tokenizers and asserts identical output), score cosine against the index, render top 12 with: label, kind chip, score bar, top 3 matching terms, link to the record's card.
- **Relation controls:** edge-kind checkboxes (the 13 curated kinds + 3 derived kinds) filter which edges the layout and neighborhood traversal use.
- **Empty state** explains the three questions above in two sentences, plain register.
- Honors `prefers-reduced-motion` (layout settles instantly instead of animating). Canvas + JS inline; no new third-party assets, no SRI surface change.

## Streamlit surface

`dashboard.py` gets a matching "Explore" tab that embeds the same generated HTML fragment via `st.components.v1.html` (height ~800). The builder (`_build_explore_html`) lives with the other shared builders so both surfaces render one implementation. Keep it pure (returns a string).

## llms.txt

Add one section noting the Explore tab exists and that the full node/edge list is derivable from the datasets; do not dump the index into llms.txt.

## Tests

- `tests/test_refdata.py`: graph nodes exactly equal registry ids plus declared taxonomy hubs; every edge in `build_graph()` either comes from `iter_edges()` or is a declared derived kind; index is deterministic (two builds byte-equal); stopwords absent; weights normalized (‖v‖≈1); blob size guard (< 900 KB hard ceiling).
- `tests/test_build_site.py`: page contains the `graph-data` JSON blob and it parses; tokenizer parity fixture (Python output == expected list literal also asserted against the JS source by regex-extracting the JS stopword list, or simpler: generate the JS stopword list *from* Python at build time so parity is by construction — prefer this); Explore tab button + panel + anchors emitted.
- A build-diff sanity check: adding a record changes the blob (guards against a stale cached index).

## Acceptance

- Paste the Fort Worth/Cedar Creek news summary → the similar-records list surfaces supply-strain sites and water-supply cases above unrelated PFAS records.
- Click `AWS-Lake-Anna` (or any case) → neighborhood shows its readings, analogous cases, and any sites that reference it; "open card" lands on the exact card in Water Cases.
- Page still loads with JS disabled: the Explore panel shows a static explanation + link list (progressive enhancement; graph and search require JS and say so).

## Out of scope → backlog (needs live tokens or a server)

- Build-time or runtime embeddings for true semantic similarity (API tokens).
- "Ask the graph" natural-language Q&A over records (LLM at runtime).
- Cross-session saved queries/pins (needs storage beyond the static page).
