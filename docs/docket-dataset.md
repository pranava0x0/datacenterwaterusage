# Water docket dataset

Research preview, schema version 0.1.0. [Manifest](../pages/docket-manifest.json) reports coverage and SHA-256 hashes. [JSONL](../pages/docket-records.jsonl) contains one row for each tracked case; [JSON Schema](../pages/docket-record.schema.json) describes the record contract. [Applicability checklists](../pages/applicability-checklists.json) supply source-linked questions for selected statutory readings.

## Intended use

Retrieve candidate precedents for a proposed water-intensive project, inspect their sources, and record the facts still needed for review. The Check a project page downloads a project worksheet containing its raw description and size fields, facet selections and origins, source example, retrieval payload hash, ranked candidates and unanswered questions. Computation stays in the browser; the download contains the description the user supplied.

Shared facts are retrieval signals. They do not establish jurisdiction, a violation, a permit obligation or the probability of an outcome. Every new-project assessment starts as `not_assessed`; unanswered questions remain `unknown` even when a case ranks first. A checklist is a scoped review aid, not an exhaustive statement of current law.

## Record contract

| Field | Meaning |
| --- | --- |
| `display_label` | Curated respondent description, not a normalized legal caption. |
| `record_id` | Stable tracker case ID; it is not a court docket number. |
| `docket_number`, `decision_date`, `decision_maker` | Null unless source-checked in the annotation file. |
| `checked_annotation` | A separately cited holding and disposition, with the exact review scope. Its review does not certify the legacy prose. |
| `facts` | Curator-assigned facets; empty evidence references disclose the lack of fact-level citations. |
| `reading_ids` | Links to the tracker's statutory readings. |
| `source_record` | Original curated record without field loss or reinterpretation. |
| `source_refs` | Record-level URLs. These are not claim-level evidence and were not rechecked merely by exporting them. |
| `applicability` | Unassessed status, checklist references and missing evidence. |
| `lineage` | Input dataset and record ID, canonical JSON hash and dataset update date. The update date is not a decision date. |

Court opinions, agency decisions, proposed settlements and community disputes remain distinguishable through their original classifications and descriptions. Most records lack normalized docket metadata. No absence of enforcement or legal inapplicability label should be inferred from a missing field.

## Sources and checks

The historical opinion pilot cites [County of Maui, opinion pp. 15–18](https://www.supremecourt.gov/opinions/19pdf/18-260_jifl.pdf) and [Sackett, opinion pp. 21–22](https://www.supremecourt.gov/opinions/22pdf/21-454_4g15.pdf). Construction screening cites [EPA's construction-stormwater guidance](https://www.epa.gov/npdes/stormwater-discharges-construction-activities). The checklist file records locators and retrieval dates; opinion hashes identify the downloaded PDFs. These reviews do not provide a subsequent-history search or an assessment of every jurisdiction's current permit terms.

The build validates every JSONL row against the schema and rejects empty or duplicate-ID exports. Tests check reference resolution, the preservation and hash of original records, unanswered questions, known-bad records and Python/browser worksheet parity. Regenerate with `python3 build_site.py`; run `python3 -m pytest -q` in an environment installed from `requirements.txt`.

## Release limits

The tracker is a curated, non-exhaustive sample with uneven geographic and case coverage. Retrieval scores and recorded outcome counts are unsuitable as outcome probabilities. No training/test split or expert-adjudicated gold labels are supplied. Linked third-party documents retain their own rights; no blanket dataset license is asserted for those sources. This preview does not redistribute the PermitTEC, NEPATEC or Breakthrough corpora.

Before a benchmark release: resolve redistribution rights; normalize proceedings separately from opinions; review subsequent history; add source passages for each labeled fact; group related projects and dockets in the same partition; and adjudicate an independent held-out sample. Include insufficient-evidence and contradicted examples. Model outputs belong in a separate annotation layer with model version, prompt, input hash and reviewer disposition.

## Jev evaluation

[TypeSafe's typed-question interface](https://docs.typesafe.ai/introduction) could classify whether a supplied passage supports, contradicts or leaves a factual criterion unresolved. That is a proposed experiment. No model service is called by this release, and no legal-accuracy or calibration result is claimed. Freeze the model version and compare it with a deterministic baseline on the held-out sample before using its labels. Missing project evidence must remain unknown regardless of a model's confidence.
