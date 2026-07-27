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


def _legiscan_ok(payload: dict, context: str) -> dict:
    """Reject a LegiScan error payload instead of fingerprinting it.

    LegiScan answers every request 200 with a body carrying its own
    ``status`` field. Without this check an error body — which has none of the
    fields :func:`canonical_legiscan` reads — canonicalizes to a stable
    all-null string. That fingerprint never changes, so the watch looks
    perfectly healthy and can never report a status move: the silent-failure
    mode this whole subsystem exists to prevent. Raise instead, so the sweep
    reports it as a failed fetch.
    """
    if payload.get("status") != "OK":
        raise RuntimeError(
            f"LegiScan {context} returned status={payload.get('status')!r}: "
            f"{payload.get('alert', {}).get('message', payload)}"
        )
    return payload


def resolve_legiscan_bill_id(key: str, get: Callable[[str], str], api_key: str) -> str:
    """Map a human bill reference to LegiScan's internal numeric bill id.

    ``getBill`` takes LegiScan's own integer id, NOT a bill number — passing
    "NY S10642" returns an error payload rather than the bill. Keys may be
    given either as a numeric id (used directly) or as "<STATE> <BILLNUM>",
    which is resolved through ``getSearch`` and matched on the exact bill
    number so a fuzzy relevance hit cannot silently select the wrong bill.
    """
    key = key.strip()
    if key.isdigit():
        return key

    parts = key.split(None, 1)
    if len(parts) != 2:
        raise ValueError(
            f"legiscan key {key!r} must be a numeric bill id or '<STATE> <BILLNUM>'"
        )
    state, bill_number = parts[0], parts[1].replace(" ", "")
    url = f"{LEGISCAN_API}?key={api_key}&op=getSearch&state={state}&query={bill_number}"
    payload = _legiscan_ok(json.loads(get(url)), "getSearch")

    results = payload.get("searchresult", {}) or {}
    for value in results.values():
        if not isinstance(value, dict):
            continue  # 'summary' block
        found = str(value.get("bill_number", "")).replace(" ", "").upper()
        if found == bill_number.upper():
            return str(value["bill_id"])
    raise RuntimeError(
        f"LegiScan getSearch found no bill numbered {bill_number!r} in {state}"
    )


def canonical_legiscan(payload: dict) -> str:
    """Reduce a LegiScan bill payload to the fields a status change moves.

    The full response carries vote rosters, sponsor metadata and text hashes
    that churn independently of status; fingerprinting all of it would report a
    change on nearly every run.
    """
    _legiscan_ok(payload, "getBill")
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


def _redacting(key: str, exc: Exception) -> RuntimeError:
    """Re-raise a fetch error with the credential scrubbed out.

    httpx puts the full request URL in its error messages, and MonitorRun
    formats fetch errors verbatim into a Candidate that gets printed and
    written to the queue file. Any 4xx from an API whose key travels in the
    query string would otherwise burn that key into logs on disk (CLAUDE.md
    §10). Redacting at the throw site is the only place that catches every
    path, since callers do not know a secret was involved.
    """
    return RuntimeError(f"{type(exc).__name__}: {str(exc).replace(key, '***')}")


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
            try:
                bill_id = resolve_legiscan_bill_id(watch.key, get, key)
                url = f"{LEGISCAN_API}?key={key}&op=getBill&id={bill_id}"
                return canonical_legiscan(json.loads(get(url)))
            except Exception as exc:  # noqa: BLE001 - redact, then re-raise
                raise _redacting(key, exc) from None

        if watch.kind == "federal-register":
            url = (
                f"{FEDERAL_REGISTER_API}?per_page=20&order=newest"
                f"&conditions[term]={watch.key.replace(' ', '+')}"
            )
            return canonical_federal_register(json.loads(get(url)))

        raise ValueError(f"unsupported monitor kind: {watch.kind!r}")

    return fetch
