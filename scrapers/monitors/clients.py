"""Fetchers for the three monitor kinds.

Each turns a :class:`Watch` into a text blob the base monitor fingerprints. The
kinds differ in what "the page" means:

* ``url-watch`` — the HTML of a page a curator would otherwise re-read.
* ``legiscan`` — a bill's status fields, rendered as a small canonical string
  so a cosmetic API change (a new field, reordered keys) does not read as a
  status change.
* ``federal-register`` — the titles and publication dates of documents matching
  a search, so a new rule or notice appears as a diff.

The two API kinds need credentials, which live in the environment and are never
committed (CLAUDE.md §10). A watch whose key is unavailable degrades to a
labelled skip rather than a crash or, worse, a silent no-change.
"""

from __future__ import annotations

import json
import os
from typing import Callable

from scrapers.monitors.base_monitor import Watch

LEGISCAN_API = "https://api.legiscan.com/"
FEDERAL_REGISTER_API = "https://www.federalregister.gov/api/v1/documents.json"


class MissingCredential(RuntimeError):
    """Raised when a monitor kind needs an API key that is not configured.

    Surfaced as a candidate by the sweep rather than swallowed: a watch that
    silently stops running is indistinguishable from one reporting no change,
    which is the exact failure the monitors exist to prevent.
    """


def _require(env_var: str) -> str:
    key = os.environ.get(env_var, "").strip()
    if not key:
        raise MissingCredential(
            f"{env_var} is not set — this watch did not run. Export the key or "
            "switch the record's monitor kind to url-watch."
        )
    return key


def canonical_legiscan(payload: dict) -> str:
    """Reduce a LegiScan bill payload to the fields a status change moves.

    The full response carries vote rosters, sponsor metadata and text hashes
    that churn independently of status; fingerprinting all of it would report a
    change on nearly every run.
    """
    bill = payload.get("bill", payload) or {}
    fields = {
        "status": bill.get("status"),
        "status_date": bill.get("status_date"),
        "last_action": bill.get("last_action"),
        "last_action_date": bill.get("last_action_date"),
        "bill_number": bill.get("bill_number"),
    }
    return json.dumps(fields, sort_keys=True)


def canonical_federal_register(payload: dict) -> str:
    """Titles + publication dates of matching documents, newest first.

    Deliberately excludes the result count and the API's own pagination URLs,
    which move without any new document appearing.
    """
    docs = payload.get("results", []) or []
    rows = sorted(
        f"{d.get('publication_date', '')} {d.get('document_number', '')} {d.get('title', '')}"
        for d in docs
    )
    return "\n".join(rows)


def make_fetcher(get: Callable[[str], str]) -> Callable[[Watch], str]:
    """Build the ``fetch`` callable :class:`MonitorRun` expects.

    ``get`` maps a URL to response text and is supplied by the caller — in
    production a rate-limited client honouring the project's 2-5s delays, in
    tests a stub. Keeping it a parameter is what lets the whole pipeline be
    exercised offline.
    """

    def fetch(watch: Watch) -> str:
        if watch.kind == "url-watch":
            return get(watch.key)

        if watch.kind == "legiscan":
            key = _require("LEGISCAN_API_KEY")
            url = f"{LEGISCAN_API}?key={key}&op=getBill&id={watch.key}"
            return canonical_legiscan(json.loads(get(url)))

        if watch.kind == "federal-register":
            url = (
                f"{FEDERAL_REGISTER_API}?per_page=20&order=newest"
                f"&conditions[term]={watch.key.replace(' ', '+')}"
            )
            return canonical_federal_register(json.loads(get(url)))

        raise ValueError(f"unsupported monitor kind: {watch.kind!r}")

    return fetch
