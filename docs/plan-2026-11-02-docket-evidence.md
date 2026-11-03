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
- Comparative dataset research: complete for PermitTEC v0.1, NEPATEC 3.0, Breakthrough, ELI, CEQ and TypeSafe Jev; [sources and unresolved access/license questions](research-docket-sources-2026-11-02.md).
- Case schema, export and applicability workflow: implemented as a research preview; broader claim verification and model evaluation remain in the backlog.
- Water investment evidence: four additions with source locators and reporting/delivery distinctions.
- Responsive UAT and graphics: [baseline and final measurements](uat-2026-11-02.md); graphics changed after the idle-paint finding.
- Reviews: first pass found four provenance/classification issues; corrections made with regression checks. Second pass found size-input precedence and repository-card link issues; fixes and final verification are tracked in [PR #37](https://github.com/pranava0x0/datacenterwaterusage/pull/37).

## Delegation

The requested lightweight research model failed at startup because its provider authentication was unavailable. Two available agents completed source research and browser UAT, then reviewed the changes. The main session integrated the code and reviewed their sources and results. No paid TypeSafe service or bulk upstream dataset download ran.

The user confirmed the matcher extension and dataset preview scope during implementation. A separate hosted service is outside this release.

## Verification before merge

Both inline review rounds are complete. The corrected source passes 1,055 tests and 104 browser flows, including numeric input precedence and the actual worksheet download. A clean copied checkout reproduced all generated files; Streamlit rendered without exceptions. [UAT evidence](uat-2026-11-02.md) records performance limits and inherited checker findings. The [PR](https://github.com/pranava0x0/datacenterwaterusage/pull/37) records CI, merge and published-surface verification.
