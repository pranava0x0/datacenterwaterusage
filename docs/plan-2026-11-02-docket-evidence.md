# Docket evidence and project review

## Scope

Extend the existing static project checker and publish a versioned dataset preview. Keep the current case IDs, curated source records and deterministic retrieval. A hosted ingestion service would support broader coverage but adds operating costs and source-access dependencies; a documentation-only schema would leave the export and user workflow untested.

The starting point is [PR 23](https://github.com/pranava0x0/datacenterwaterusage/pull/23) (statutory paths and graph), [PR 28](https://github.com/pranava0x0/datacenterwaterusage/pull/28) (security and graph controls), [PR 30](https://github.com/pranava0x0/datacenterwaterusage/pull/30) (lazy tabs and commitments), and [PR 32](https://github.com/pranava0x0/datacenterwaterusage/pull/32) (project matching). Remote base: `57bfa2f`. The existing local branch and its documentation commit are preserved separately.

## Dataset contract

One JSONL row per tracked case, with stable IDs, the original record, linked statutory readings, fact facets, record-level source references, and explicit gaps for docket identifiers, decision dates, claim-level citations and subsequent history. A record hash identifies the imported version. A source URL is not proof that each claim was checked. Unknown fields remain null or explicitly unassessed.

Keep applicability separate from retrieval: shared facets retrieve candidates; they do not establish legal elements. A small source-checked checklist pilot names the additional questions and authority behind selected readings. Project exports carry user input, selected facets, ranked records and unanswered questions; they never turn a similarity score into a legal probability. Scope, exceptions, current authority and project evidence require review.

The preview includes a machine-readable schema, a dataset card, a manifest with hashes and coverage counts, and deterministic regeneration through the existing site build. No upstream corpus or commercial-model service is copied or called. A benchmark release needs adjudicated labels, source-rights review, and project/docket-grouped splits before publishing model scores.

## Product and verification

1. Record baseline UAT at phone, tablet and desktop sizes: every tab, key project flows, deep links, no-JavaScript pages, payload, heap and idle work.
2. Add dataset downloads and cited applicability questions beside matching results. Keep these within the existing Check a project surface.
3. Integrate source-verified water investment examples, preserving announcement versus delivery and capacity versus measured consumption.
4. Fix measured interaction and graphics problems; retain the pipe schematic and system fonts. Measure the same journeys after changes.
5. Validate all exported records, known-bad fixtures, cross-references, Python/browser parity, build determinism and fresh-checkout reproduction. Run writing/design checks on changed surfaces.
6. Open the PR, complete two review passes, resolve findings, verify required CI checks, merge and check the published pages and downloads.

## Completion ledger

- Recent history: reviewed feature PRs linked above; dependency PRs remain separate.
- Comparative dataset research: in progress.
- Case schema, export and applicability workflow: planned.
- Water investment evidence: in progress.
- Responsive UAT and graphics: baseline in progress.
- Reviews, merge and live verification: pending.
