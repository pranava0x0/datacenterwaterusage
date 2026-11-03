"""Docket preview: lossless imports, honest evidence gaps, and browser parity."""

import copy
import hashlib
import json
import shutil
import subprocess

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

import dashboard
from refdata import dockets, precedent
from refdata.loaders import load_cwa_investigations
from refdata.registry import build_registry


def test_every_case_exports_and_validates():
    rows = dockets.build_docket_records()
    source = {c["case_id"]: c for c in load_cwa_investigations()["cases"]}
    schema = json.loads(dockets.SCHEMA_PATH.read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    assert rows and {r["record_id"] for r in rows} == set(source)
    for row in rows:
        validator.validate(row)
        assert row["source_record"] == source[row["record_id"]]
        assert row["display_label"] == source[row["record_id"]]["respondent"]
        assert "caption" not in row
        if row["checked_annotation"]:
            for key in ("docket_number", "decision_date", "decision_maker", "procedural_posture"):
                assert row[key] == row["checked_annotation"][key]
        assert row["lineage"]["record_sha256"] == dockets.canonical_hash(row["source_record"])
        assert row["applicability"]["status"] == "not_assessed"
        assert all(not f["evidence_refs"] for f in row["facts"])
        assert all(s["verification"] == "not_reverified_for_export" for s in row["source_refs"])


@pytest.mark.parametrize("field,value", [
    ("schema_version", "99"),
    ("jurisdiction", {"country": "ZZ", "binding_scope": "not_assessed"}), ("docket_number", "made-up"),
    ("decision_date", "2026-01-01"), ("decision_maker", "fictional"),
    ("procedural_posture", "vacated_and_remanded"), ("decision_date", "2026-02-30"),
    ("facts", [{"facet_id": "src-wells", "basis": "verified", "evidence_refs": []}]),
    ("applicability", {"status": "applies", "checklist_ids": [], "missing_evidence": []}),
])
def test_bad_export_fails(field, value):
    row = copy.deepcopy(dockets.build_docket_records()[0])
    row[field] = value
    validator = Draft202012Validator(json.loads(dockets.SCHEMA_PATH.read_text()), format_checker=FormatChecker())
    with pytest.raises(ValidationError):
        validator.validate(row)


def test_annotations_do_not_certify_other_records_or_legacy_prose():
    rows = {r["record_id"]: r for r in dockets.build_docket_records()}
    maui = rows["County-of-Maui-v-Hawaii-Wildlife-Fund-2020"]
    assert maui["docket_number"] == "18-260"
    assert maui["decision_date"] == "2020-04-23"
    assert maui["procedural_posture"] == "vacated_and_remanded"
    assert "Legacy source_record prose" in maui["checked_annotation"]["scope"]
    unreviewed = [r for r in rows.values() if r["checked_annotation"] is None]
    assert unreviewed
    assert all(r["decision_date"] is None and r["docket_number"] is None for r in unreviewed)


def test_checklist_sources_and_links_resolve():
    reg = build_registry()
    checks = dockets.load_checklists()["checklists"]
    assert checks and len({c["checklist_id"] for c in checks}) == len(checks)
    for c in checks:
        assert reg[c["reading_id"]].kind == "reading"
        sources = {s["source_id"]: s for s in c["sources"]}
        assert sources and c["scope"] and c["limitations"]
        for q in c["questions"]:
            assert q["source_ids"] and set(q["source_ids"]) <= set(sources)
        for s in sources.values():
            assert s["locator"] and s["retrieved_at"] and s["url"].startswith("https://")


def test_export_hashes_and_determinism():
    files = dockets.dataset_files()
    assert files == dockets.dataset_files()
    manifest = json.loads(files["docket-manifest.json"])
    assert manifest["record_count"] == len(files["docket-records.jsonl"].splitlines())
    assert manifest["claim_verified_record_count"] == 0
    for name, metadata in manifest["files"].items():
        raw = files[name].encode()
        assert len(raw) == metadata["bytes"]
        assert hashlib.sha256(raw).hexdigest() == metadata["sha256"]


@pytest.mark.parametrize("facets,state", [(["out-ground", "src-wells"], "VA"), (["ctx-wetlands", "out-stormwater"], None), ([], "TX")])
def test_browser_worksheet_matches_python_and_keeps_unknowns(tmp_path, facets, state):
    assert shutil.which("node"), "Node is required to check the public browser export"
    payload = precedent.build_payload()
    result = precedent.match_project(facets, state)
    inputs = {"mw": "350", "mgd": "2", "state": "AZ", "source_example": None}
    expected = dockets.project_assessment(result, "Project description", inputs=inputs)
    assert expected["legal_applicability"] == "not_assessed"
    assert all(q["answer"] == "unknown" and not q["project_evidence"]
               for c in expected["checklists"] for q in c["questions"])
    data = tmp_path / "input.json"
    data.write_text(json.dumps({"result": result, "payload": payload, "inputs": inputs}))
    script = "const engine = " + dashboard._project_check_js().strip().removeprefix("const ")
    # The shipped script is an IIFE expression; test its real export function.
    script += "\nconst d=JSON.parse(require('fs').readFileSync(process.argv[1], 'utf8'));"
    script += "\nprocess.stdout.write(JSON.stringify(engine.projectAssessment(d.result, 'Project description', d.payload, d.inputs)));"
    actual = subprocess.run(["node", "-e", script, str(data)], capture_output=True, text=True, check=True)
    assert json.loads(actual.stdout) == expected


def test_payload_version_identifies_exact_content():
    payload = precedent.build_payload()
    digest = payload.pop("payload_sha256")
    assert digest == dockets.canonical_hash(payload)
    payload["examples"][0]["description"] += " edited"
    assert digest != dockets.canonical_hash(payload)


def test_dataset_card_links_resolve_in_repo_and_published_directory():
    import re
    card_path = dockets.SCHEMA_PATH.parent.parent / "docs" / "docket-dataset.md"
    repo_links = re.findall(r"\]\((\.\./pages/[^)]+)\)", card_path.read_text())
    assert len(repo_links) == 4
    files = dockets.dataset_files()
    public_card = files["docket-dataset.md"]
    for link in repo_links:
        assert (card_path.parent / link).is_file()
        assert "](" + link.removeprefix("../pages/") + ")" in public_card
        assert link.removeprefix("../pages/") in files


def test_pretreatment_worksheet_needs_an_industrial_sewer_route():
    def worksheets(facets):
        matches = precedent.match_project(facets, None)
        return {c["reading_id"]: c for c in dockets.project_assessment(matches, "")["checklists"]}

    for description in ("Cooling tower blowdown to the river", "A storm sewer carries runoff",
                        "An on-site wastewater treatment plant reuses the blowdown"):
        assert "out-sewer" not in precedent.parse_project(description)["facets"]
    assert "out-sewer" in precedent.parse_project("Tower blowdown goes to the city sewer")["facets"]
    facts = ["cool-evaporative", "chem-treatment"]
    assert "cwa-307-pretreatment" not in worksheets(facts)
    checklist = worksheets(facts + ["out-sewer"])["cwa-307-pretreatment"]
    assert {q["id"] for q in checklist["questions"]} == {"industrial-route", "local-controls", "significant-user"}
    assert all(q["answer"] == "unknown" for q in checklist["questions"])
