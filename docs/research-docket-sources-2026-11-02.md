# Docket source research

Reviewed 2026-11-02. Research only; production reference data unchanged. Candidate names were checked against `water_commitments.json`, `dc_water_conflicts.json`, and `project_examples.json`. The water examples below have no corresponding record in those three files. Source dates and operating status describe the cited evidence.

## Dataset inventory

### PermitTEC v0.1

The likely match for “Permit Tech V01” is PNNL's **PermitTEC v0.1**. Its card lists CC0-1.0, 761 cases, and a Hugging Face access gate requiring account-information sharing. The visible schema has `case_uuid`, `case_metadata`, and `linked_to`; case fields carry `value` and `source`. Provenance distinguishes reviewed, corrected, and unreviewed LLM extraction. The loader example uses `train`; the card supplies no evaluation partition. These are card observations; gated records were not downloaded. [PNNL card, Dataset Structure, Usage, License](https://huggingface.co/datasets/PNNL/PermitTECv0.1).

The documented join is `linked_to.nepatec_project_uuid` to **NEPATEC v2.0** `project.project_ID.value`. A false `in_nepatec` conflates absence of a challenged NEPA document with a missing project match. The card warns that fields require conversion from strings despite its typed example. Its statistics table reports 341 unmatched NEPA challenges, or 44.8%; Known Limitations says 41.9%, an internal inconsistency requiring record-level review before reuse. `prevailing_party` supports Agency, Challenger, or Cannot be determined; it does not supply a complete procedural outcome. [PNNL card, Field Notes, Linkage Breakdown, Relationship to NEPATEC, Known Limitations](https://huggingface.co/datasets/PNNL/PermitTECv0.1).

### NEPATEC 3.0

The likely match for “NEPA Tech 3.0” is **NEPATEC3.0**, released August 2026. PNNL reports preliminary totals of 81,347 projects and 188,330 files under CC0. JSONL records nest project → process → documents → files → pages; the project identifier is `project.project_id`. File metadata includes a hash/provider, and summaries carry source-file identifiers. This differs from the v2 field path above; identifier continuity across versions remains unverified. [PNNL card, Dataset Structure, Version History](https://huggingface.co/datasets/PNNL/NEPATEC3.0).

The card separates agency-organized metadata (1.83 GB), metadata with text (25.59 GB), and GIS assets (about 2.278 TB). Its streaming example labels all selected files `train`; it documents no held-out evaluation split. Files are gated. Its loader also acknowledges inconsistent field types, including dictionaries versus empty strings. Raw-row schema validation remains pending access. [PNNL card, Usage and access notice](https://huggingface.co/datasets/PNNL/NEPATEC3.0).

### Breakthrough litigation data

The July 11, 2024 study, produced with Holland & Knight, covers 387 appellate cases from 2013–2022. [Breakthrough, Executive Summary](https://thebreakthrough.org/issues/energy/understanding-nepa-litigation). The July 24, 2025 report expands coverage to district-court cases. [Breakthrough, opening discussion](https://thebreakthrough.org/issues/energy/the-procedural-hangover).

The linked [Navigating NEPA export](https://navigatingnepa.com/data/nepa-export.csv) was fetched and parsed during this review: **1,821 rows and 31 columns**, including court/docket/citation, project category, document type, ROD/FONSI and litigation dates, prevailing party, case disposition, injunction, and remand fields. Those counts describe rows and columns, not unique projects or lawsuits. No split column appears in the header. The [publisher's explorer](https://navigatingnepa.com/) supplies the download under “Explore the Data.” The reviewed pages did not establish a dataset version tag, reuse license, or train/test protocol. Preserve the export hash and retrieval date if ingestion is later approved; resolve licensing before redistribution.

### Environmental Law Institute match

The identified source is Michael Bennon and Devon Wilson's October 2023 *Environmental Law Reporter* article, **NEPA Litigation Over Large Energy and Transport Infrastructure Projects**. It studies 355 projects selected from CEQ's 1,161-EIS timeline dataset, with final EISs from 2010 to mid-2018. Authors added sector, supplemental-EIS, dashboard, state-law, litigation, and development-status variables. Litigation searches used Nexis Uni, LexisNexis, and Westlaw; development status was coded in 2022. [Article, printed pp. 10836 and 10849; PDF pp. 1 and 14](https://www.elr.info/sites/default/files/files-general/53.10836.pdf).

The opened article carries ELI copyright. A separately downloadable row-level dataset, reuse license, version tag, and evaluation split were not established by this review. Treat this as a methodological reference pending an author-hosted data release. Its EIS infrastructure sample supplies a different denominator from an opinions-only litigation collection. [Article, Data and Methodology, printed p. 10849](https://www.elr.info/sites/default/files/files-general/53.10836.pdf).

### CEQ standard

“CQ” likely refers to the **Council on Environmental Quality (CEQ)**. Version 1.2 of its NEPA and Permitting Data and Technology Standard was published August 18, 2025. CEQ describes crosswalking existing agency systems and says it requires no new data requests or reporting. [CEQ standard, introduction and implementation guidance](https://permitting.innovation.gov/resources/data-standard/).

The official repository provides JSON Schema, a CSV crosswalk, SQL migrations, and OpenAPI examples. Version 1.2 adds record-version, source-agency/system, owner, update-time, and retrieval-time properties. Its sample data is expressly fictional; it supplies no empirical evaluation split. The repository dedicates its contents to the public domain through CC0. [GSA-TTS repository, Toolkit, Changelog, Public domain](https://github.com/GSA-TTS/pic-standards).

### TypeSafe Jev

Official documentation uses state plus independent typed questions: Choice returns an option and probabilities; Score evaluates a rubric; Noul returns a probability. It recommends decomposing broad judgments into narrow questions combined in code. [TypeSafe Introduction, TypeSafe primitives and Atomic questions](https://docs.typesafe.ai/introduction).

As reviewed, `jev-1.14.0` is the current release, dated October 14, 2026; `jev-latest` resolves to it. Versioned IDs support reproducibility because aliases move. TypeSafe says customer data does not fine-tune or LoRA-adapt Jev. The reviewed documentation does not establish downloadable weights, an open model license, training-data provenance, or training/evaluation splits. [TypeSafe Models, Current models, Aliases, Customizing Jev](https://docs.typesafe.ai/models).

The vendor's version-specific Jev 1.13 limitations identify numeric/date comparisons, irrelevant context, adversarial input, and option ordering as test targets. These findings apply to 1.13; evaluate 1.14 separately. [TypeSafe, Jev 1.13 jaggedness, reviewed October 2, 2026](https://docs.typesafe.ai/model-jaggedness/jev-1.13).

## Water candidates

### Quincy, Washington

**Operating; cost allocation and reuse.** EPA dates Quincy Water Reuse Utility operation to June 30, 2021. A 30-year city/Microsoft agreement assigns Microsoft the $31 million capital cost and operating costs while the city owns and operates the utility. Future connecting companies must cover their share of construction, upgrades, and operations. [EPA case study, Solution and Financial and Contractual Agreements](https://www.epa.gov/waterreuse/water-reuse-case-study-quincy-washington).

EPA gives **138 million gallons/year as estimated savings**, not metered consumption. Blowdown treatment addresses dissolved solids; the utility still needs make-up water. EPA describes a Department of Ecology grace period allowing construction of separate treatment to meet municipal groundwater-permit TDS limits. [EPA case study, Solution, Make-up Water Sources, Managing TDS Levels](https://www.epa.gov/waterreuse/water-reuse-case-study-quincy-washington).

Proposed use: a site example and infrastructure commitment; retain the estimated qualifier and obtain the agreement itself before quoting individual contract clauses.

### Loudoun County, Virginia

**Operating; reuse and wastewater connections.** The county reports that Loudoun Water's reuse system, established in 2010, delivered over **750 million gallons to roughly 40 customers in 2025**. This is reported annual delivery across customers. The county also says data centers with wastewater flows exceeding nearby infrastructure capacity constructed connections to mains able to handle those flows. [Loudoun County, Water Use and Conservation; Wastewater Management](https://www.loudoun.gov/6402/Water-Considerations).

Proposed use: a utility-level example. The opened source does not name the affected facilities, report construction costs, or provide a service-agreement obligation; keep those fields unknown.

### Fort Wayne, Indiana

**Under construction; public infrastructure funding.** City Utilities' page, updated October 12, 2026, says construction is underway on approximately **22,000 feet of 30-inch transmission main**, fully funded by Google. The main will become publicly owned after completion and acceptance. The utility says the project replaces a planned utility-funded main and will add public connection points at four locations. [City Utilities, 30-Inch Water Transmission Main and Public Ownership and Oversight](https://utilities.cityoffortwayne.org/projects/east-transmission-main/).

Proposed use: an infrastructure-funding example. Diameter and length describe the asset; the source supplies no measured use or hydraulic capacity figure. Community benefits remain described as expected until completion.

### Douglas County, Georgia

**Operating; municipal wastewater reuse.** Google dates the start of recycled industrial-water cooling to **2012**. [Google Georgia location page, Milestones of progress](https://datacenters.google/locations/georgia/). Its June 3, 2026 announcement describes the partnership with the county water and sewer authority to use treated wastewater for cooling. [Google, commitment 5](https://blog.google/company-news/outreach-and-initiatives/sustainability/new-water-stewardship-commitments/).

Proposed use: a reuse example attributed to the operator. The opened sources do not establish site-specific spending, reclaimed-water volume, or contractual cost allocation. Google's aggregate infrastructure commitments must stay outside site-level financial fields.

## Existing record mapping

Use the existing `water_commitments.json` list and existing term types. Each candidate can retain `level: local`, `dc_specific: true`, `summary`, `terms`, `sources`, `confidence`, and a note explaining what was checked. The current status vocabulary contains only `in-force` and `rejected`; those describe the commitment. Keep construction/operation status explicit in the summary.

| Candidate | Existing term types | Evidence for binding/status | Date handling |
| --- | --- | --- | --- |
| Quincy | `infrastructure-funding`, `reclaimed-source`, `closed-loop` | EPA expressly describes an agreement allocating costs; `binding`, `in-force` is supported as an account of that agreement. | `2021-06-30` is the operation milestone; identify its meaning in the note. Agreement execution date remains unknown. |
| Loudoun | `reclaimed-source`, `infrastructure-funding` | An operating utility program is documented. An enforceable developer commitment is unverified; use `strategy` if retained as a program. | Only 2010 is established for the investment; the current month-required date validator needs a precision-preserving change or this row should wait. |
| Fort Wayne | `infrastructure-funding` | Google funding and construction are documented. Contract enforceability is unverified; a `voluntary` classification would describe the reported undertaking. | October 12, 2026 is a page-update date. Preserve it as source metadata; undertaking date remains unknown. |
| Douglas County | `reclaimed-source` | Operating reuse and an operator commitment are documented; `voluntary` avoids asserting a binding agreement. | 2012 is the start year. June 3, 2026 dates the later published commitment and must be labeled accordingly. |

These mappings are implementation recommendations based on the cited candidate sources and the current taxonomy/tests. Do not invent an execution month or replace it silently with a retrieval date. Omit `cross_ref_targets` until the target exists in the registry. A `medium` confidence record needs a note under the existing test contract.

## DMR measurement scope

EPA organizes DMR measurements by permitted facility, outfall, monitoring location, limit set, and reporting period. Its data dictionary explicitly distinguishes the discharge point and sampling location. [EPA ECHO, Download File Structure and Data Dictionary](https://echo.epa.gov/help/loading-tool/monitoring-data-download-help).

Consequent interpretation: flow measured at a receiving wastewater plant's combined outfall cannot by itself isolate a connected data center's sewer contribution or consumption. That allocation needs site meters or other separately identified measurements. A safe schematic label is “WWTP outfall flow: combined effluent”; the site leg can say “Site water use: separate metering needed.” This is an inference from the measurement scope, not an EPA claim that every permit has identical monitoring locations.

## Proposed pilot

Start with a reviewed sample of water-related documents from the existing project records. Store the source URL, exact locator, document date, retrieval date, file hash, extraction method, and reviewer decision beside each fact. Use separate entities for projects, documents, proceedings, and observations, with many-to-many links.

A bounded classification task can identify whether an excerpt states a proposed commitment, executed obligation, approval, construction milestone, or operating result. Include “insufficient evidence” and conflicting-source cases. Keep capacity, measured use, estimated savings, and limits in separate fields; calculate conversions and date intervals in code. Ask a reviewer to approve every public factual addition.

Build development and held-out sets by project family and proceeding so related opinions, drafts, and amended permits stay together. Include positive and negative examples of each category and record category counts. Choose acceptance thresholds on development data, then freeze them before held-out evaluation. Evaluate the named model version against deterministic keyword/rule baselines. This is a proposed evaluation design; none of the reviewed corpus cards supplies this split.

Priority: add the four evidence-backed water examples first. Use PermitTEC and Breakthrough to discover source opinions; verify each source before publishing a case claim. Defer bulk NEPATEC import until access, identifier continuity, and a water-specific sample justify it. ELI row-level data access and redistribution rights for the non-CC0 sources remain unresolved.
