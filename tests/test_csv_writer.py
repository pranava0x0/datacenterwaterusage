"""Tests for storage.csv_writer — including CSV formula-injection defense."""

import csv

import pytest

from models.document import DocumentRecord, DocumentSource
from storage.csv_writer import CSVWriter, _neutralize_formula


class TestNeutralizeFormula:
    @pytest.mark.parametrize("lead", ["=", "+", "-", "@", "\t", "\r"])
    def test_dangerous_prefixes_get_quoted(self, lead):
        payload = lead + "cmd|'/C calc'!A1"
        assert _neutralize_formula(payload) == "'" + payload

    def test_safe_strings_unchanged(self):
        for safe in [
            "Amazon Data Services",
            "Flow: 6.4 MGD",
            "https://echo.epa.gov/x",
            "VA0091383",
            "",
        ]:
            assert _neutralize_formula(safe) == safe

    def test_internal_operators_are_safe(self):
        # Only the LEADING character matters to a spreadsheet parser.
        assert _neutralize_formula("a=b+c") == "a=b+c"

    def test_non_string_passthrough(self):
        assert _neutralize_formula(None) is None
        assert _neutralize_formula(0.85) == 0.85
        assert _neutralize_formula(5) == 5


class TestCSVWriterInjection:
    def test_malicious_cells_neutralized_on_write(self, tmp_path):
        out = tmp_path / "results.csv"
        rec = DocumentRecord(
            state="VA",
            municipality_agency="Test Agency",
            document_title='=HYPERLINK("http://evil","click")',
            source_url="https://example.test/doc",
            source_portal=DocumentSource.EPA_ECHO_DMR,
            company_llc_name="@SUM(1+1)",
            extracted_quote="-2+3+cmd|'/C calc'!A0",
        )
        CSVWriter(str(out)).write([rec])

        with open(out, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        r = rows[0]
        assert r["document_title"].startswith("'=HYPERLINK")
        assert r["company_llc_name"].startswith("'@SUM")
        assert r["extracted_quote"].startswith("'-2+3")
        # Safe fields are written verbatim.
        assert r["source_url"] == "https://example.test/doc"
        assert r["state"] == "VA"

    def test_normal_record_unmodified(self, tmp_path):
        out = tmp_path / "results.csv"
        rec = DocumentRecord(
            state="OH",
            municipality_agency="Columbus",
            document_title="Broad Run WRF Monthly Flow",
            source_url="https://echo.epa.gov/x",
            source_portal=DocumentSource.EPA_ECHO_DMR,
            extracted_water_metric="Flow: 6.4 MGD",
        )
        CSVWriter(str(out)).write([rec])
        with open(out, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["document_title"] == "Broad Run WRF Monthly Flow"
        assert rows[0]["extracted_water_metric"] == "Flow: 6.4 MGD"

    def test_append_preserves_neutralization(self, tmp_path):
        out = tmp_path / "results.csv"
        w = CSVWriter(str(out))
        safe = DocumentRecord(
            state="VA",
            municipality_agency="A",
            document_title="Normal title",
            source_url="https://x.test/1",
            source_portal=DocumentSource.VA_DEQ_ARCGIS,
        )
        bad = DocumentRecord(
            state="VA",
            municipality_agency="B",
            document_title="+1234567890",
            source_url="https://x.test/2",
            source_portal=DocumentSource.VA_DEQ_ARCGIS,
        )
        w.write([safe])
        w.write([bad])  # append
        with open(out, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        assert rows[0]["document_title"] == "Normal title"
        assert rows[1]["document_title"] == "'+1234567890"
