import csv
from pathlib import Path

from models.document import DocumentRecord


# Leading characters that make a spreadsheet treat a cell as a formula on open.
# Per OWASP "CSV Injection" — includes tab and carriage return, which some
# clients also honor as formula starters.
_CSV_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _neutralize_formula(value):
    """Defuse spreadsheet formula injection in a CSV cell.

    Scraped free text (document titles, company names, quotes) can begin with
    ``=``, ``+``, ``-``, ``@`` (or tab/CR), which Excel and Google Sheets
    interpret as a live formula when the export is opened — a code-execution
    vector. Prefix any such *string* cell with a single quote so the client
    treats it as literal text. Non-string values pass through unchanged.
    """
    if isinstance(value, str) and value.startswith(_CSV_INJECTION_PREFIXES):
        return "'" + value
    return value


FIELDNAMES = [
    "state",
    "municipality_agency",
    "document_title",
    "document_date",
    "company_llc_name",
    "extracted_water_metric",
    "extracted_quote",
    "source_url",
    "document_url",
    "local_file_path",
    "source_portal",
    "permit_number",
    "match_term",
    "matched_company",
    "keyword_matches",
    "relevance_score",
    "scraped_at",
]


class CSVWriter:
    """Append DocumentRecords to a CSV file."""

    def __init__(self, output_path: str):
        self.output_path = Path(output_path)

    def write(self, records: list[DocumentRecord]):
        """Append records to CSV. Creates file with headers if it doesn't exist."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = self.output_path.exists() and self.output_path.stat().st_size > 0

        with open(self.output_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            if not file_exists:
                writer.writeheader()
            for rec in records:
                row = rec.to_dict()
                writer.writerow(
                    {k: _neutralize_formula(v) for k, v in row.items()}
                )
