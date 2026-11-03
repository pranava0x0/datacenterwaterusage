"""Versioned case exports and source-linked questions for project review.

The imported record remains intact. Missing docket metadata and unverified
claim citations remain visible instead of being inferred from a case caption.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from refdata.loaders import REFERENCE_DIR, load_cwa_investigations

SCHEMA_VERSION = "0.1.0"
CHECKLIST_PATH = REFERENCE_DIR / "applicability_checklists.json"
ANNOTATION_PATH = REFERENCE_DIR / "docket_annotations.json"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "docket-record.schema.json"


def canonical_hash(value: object) -> str:
    """Hash JSON values independent of object-key order and indentation."""
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_checklists() -> dict:
    """Read the checked-in pilot; a missing file is a build error."""
    return json.loads(CHECKLIST_PATH.read_text(encoding="utf-8"))


def build_docket_records() -> list[dict]:
    """Export every tracked case, with no synthetic docket IDs or dates."""
    corpus = load_cwa_investigations()
    checklists = load_checklists()["checklists"]
    annotations = json.loads(ANNOTATION_PATH.read_text(encoding="utf-8"))["annotations"]
    rows = []
    for case in corpus["cases"]:
        annotation = annotations.get(case["case_id"], {})
        rows.append({
            "schema_version": SCHEMA_VERSION,
            "record_id": case["case_id"],
            "record_kind": "case",
            "display_label": case["respondent"],
            "docket_number": annotation.get("docket_number"),
            "decision_date": annotation.get("decision_date"),
            "decision_maker": annotation.get("decision_maker"),
            "procedural_posture": annotation.get("procedural_posture", "not_normalized"),
            "jurisdiction": {"country": "US" if annotation else None, "binding_scope": "not_assessed"},
            "checked_annotation": deepcopy(annotation) or None,
            "facts": [{"facet_id": f, "basis": "curator_tag", "evidence_refs": []}
                      for f in case["fact_pattern"]],
            "reading_ids": list(case.get("authorities", [])),
            "outcome_tags": list(case.get("outcome_type", [])),
            "source_record": deepcopy(case),
            "source_refs": [
                {"source_id": f"source-{canonical_hash(s['url'])[:16]}",
                 "url": s["url"], "title": s.get("title", s["url"]),
                 "citation_scope": "record", "locator": None,
                 "retrieved_at": None, "content_sha256": None,
                 "verification": "not_reverified_for_export"}
                for s in case.get("sources", [])
            ],
            "applicability": {
                "status": "not_assessed",
                "checklist_ids": [c["checklist_id"] for c in checklists
                                  if c["reading_id"] in case.get("authorities", [])],
                "missing_evidence": ["project-specific facts", "jurisdiction and effective law",
                                     "claim-level source locators", "subsequent history"],
            },
            "lineage": {"dataset": "cwa_investigations.json", "record_id": case["case_id"],
                        "record_sha256": canonical_hash(case),
                        "dataset_updated_at": corpus.get("last_updated")},
        })
    if not rows:
        raise ValueError("Cannot publish an empty docket corpus")
    if len({r["record_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate docket record IDs")
    return rows


def project_assessment(result: dict, description: str, checklists: dict | None = None,
                       inputs: dict | None = None) -> dict:
    """Create a review worksheet; retrieval never satisfies a legal question."""
    catalog = checklists if checklists is not None else load_checklists()
    selected = {r["id"] for r in result.get("readings", [])}
    questions = [
        {"checklist_id": c["checklist_id"], "reading_id": c["reading_id"],
         "status": "not_assessed", "scope": c["scope"], "limitations": c["limitations"],
         "sources": deepcopy(c["sources"]),
         "questions": [{**q, "answer": "unknown", "project_evidence": []}
                       for q in c["questions"]]}
        for c in catalog["checklists"] if c["reading_id"] in selected
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "assessment_type": "retrieval_worksheet",
        "legal_applicability": "not_assessed",
        "project": {"description": description, "state": result.get("state"),
                    "facets": list(result.get("facets", [])), "evidence_status": "unverified_inputs",
                    "inputs": deepcopy(inputs)},
        "retrieval": deepcopy(result),
        "checklists": questions,
        "unreviewed_reading_ids": [r["id"] for r in result.get("readings", [])
                                   if not any(q["reading_id"] == r["id"] for q in questions)],
        "score_meaning": "Similarity for retrieval; not a probability or legal determination.",
    }


def dataset_files() -> dict[str, str]:
    """Flat public artifacts consumed by the existing site build and deploy."""
    records = build_docket_records()
    validator = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")), format_checker=FormatChecker())
    for record in records:
        validator.validate(record)
    corpus = "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in records)
    files = {
        "docket-records.jsonl": corpus,
        "docket-record.schema.json": SCHEMA_PATH.read_text(encoding="utf-8"),
        "applicability-checklists.json": CHECKLIST_PATH.read_text(encoding="utf-8"),
        "docket-dataset.md": (SCHEMA_PATH.parent.parent / "docs" / "docket-dataset.md").read_text(encoding="utf-8").replace("](../pages/", "]("),
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "release_status": "research_preview",
        "record_count": len(records),
        "checklist_count": len(load_checklists()["checklists"]),
        "normalized_docket_count": sum(r["docket_number"] is not None for r in records),
        "claim_verified_record_count": 0,
        "source_rights": "No blanket license for linked third-party source material. Rights review pending.",
        "splits": None,
        "files": {name: {"sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                          "bytes": len(content.encode("utf-8"))}
                  for name, content in files.items()},
    }
    files["docket-manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    return files
