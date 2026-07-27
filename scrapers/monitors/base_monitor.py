"""Watch tracked records for status changes and emit refresh candidates.

Plan Spec B3. Six decisions in this dataset are known to flip soon — the Ohio
general permit finalizing, Virginia's first HB 496 aggregate report due
2026-10-01, the Michigan package moving, the Montgomery County vote. Today each
is found by a human re-running research and reading pages by hand, which means
staleness is invisible until someone goes looking.

**Monitors propose; humans dispose.** A monitor never edits a curated dataset.
It detects that a watched page changed and appends a candidate to a queue that
a curator adjudicates. That is deliberate — the curated layer's value is that a
person checked it, and an automated writer would quietly trade that away (plan
§0.5, fail-closed curation).

**The watch list is derived, not maintained.** Any record carrying a ``monitor``
block is watched; there is no second list to fall out of sync with the data.

The network layer is injected rather than imported, so the diffing logic is
testable without touching the wire — and so a caller can supply a client that
honours the project's rate-limit and delay conventions (CLAUDE.md §1).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Callable, Iterable

from refdata.loaders import (
    load_cwa_investigations,
    load_dc_water_conflicts,
    load_legislation,
)

# Recognised monitor kinds. `url-watch` fingerprints a page's meaningful text;
# `legiscan` and `federal-register` are API-backed and need a key in config.
MONITOR_KINDS = {"url-watch", "legiscan", "federal-register"}


@dataclass(frozen=True)
class Watch:
    """One watched record, derived from the dataset that owns it."""

    record_id: str
    dataset: str  # legislation | cases | sites
    kind: str
    key: str  # a URL for url-watch; an external id otherwise
    note: str = ""


@dataclass
class Candidate:
    """A detected change, awaiting human adjudication."""

    record_id: str
    dataset: str
    kind: str
    key: str
    previous_fingerprint: str | None
    fingerprint: str
    summary: str
    detected_at: str
    note: str = ""
    excerpt: str = ""

    def as_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "dataset": self.dataset,
            "kind": self.kind,
            "key": self.key,
            "previous_fingerprint": self.previous_fingerprint,
            "fingerprint": self.fingerprint,
            "summary": self.summary,
            "detected_at": self.detected_at,
            "note": self.note,
            "excerpt": self.excerpt,
        }


_DATASET_LOADERS: dict[str, tuple[Callable[[], dict], str, str]] = {
    "legislation": (load_legislation, "bills", "bill_id"),
    "cases": (load_cwa_investigations, "cases", "case_id"),
    "sites": (load_dc_water_conflicts, "sites", "site_id"),
}


def iter_watches() -> Iterable[Watch]:
    """Every record carrying a ``monitor`` block, across all datasets."""
    for dataset, (loader, list_key, id_key) in _DATASET_LOADERS.items():
        for record in loader().get(list_key, []):
            monitor = record.get("monitor")
            if not monitor:
                continue
            yield Watch(
                record_id=record.get(id_key, ""),
                dataset=dataset,
                kind=monitor.get("kind", ""),
                key=monitor.get("key", ""),
                note=monitor.get("note", ""),
            )


def invalid_watches() -> list[str]:
    """Watches a monitor could not act on — bad kind, or a missing key."""
    problems = []
    for w in iter_watches():
        if w.kind not in MONITOR_KINDS:
            problems.append(f"{w.record_id}: unknown monitor kind {w.kind!r}")
        if not w.key:
            problems.append(f"{w.record_id}: monitor has no key")
        if w.kind == "url-watch" and not w.key.startswith("http"):
            problems.append(f"{w.record_id}: url-watch key is not a URL ({w.key!r})")
    return problems


# Boilerplate that changes on every page load and would otherwise report a
# change on every run: timestamps, session ids, CSRF tokens, cache-busting
# query strings. Stripped before fingerprinting.
_NOISE = re.compile(
    r"""(?xi)
    <script\b.*?</script>            # inline JS
    | <style\b.*?</style>            # inline CSS
    | <!--.*?-->                     # comments
    | \b[0-9a-f]{16,}\b              # session/CSRF hex blobs
    | \b\d{1,2}:\d{2}(:\d{2})?\s*(am|pm)?\b   # clock times
    | [?&](?:_|cb|v|ts|nocache)=[^\s"'&<>]+   # cache-busters
    """,
    re.DOTALL,
)
_TAGS = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def normalize(body: str) -> str:
    """Reduce a page to the text a curator would actually read.

    Without this, a monitor reports a change every run because the page
    embedded a render timestamp — and a watcher that always fires is a watcher
    nobody reads.
    """
    text = _NOISE.sub(" ", body or "")
    text = _TAGS.sub(" ", text)
    return _WS.sub(" ", text).strip()


def fingerprint(body: str) -> str:
    """Stable digest of a page's meaningful content."""
    return hashlib.sha256(normalize(body).encode("utf-8")).hexdigest()[:16]


def first_difference(old: str, new: str, width: int = 240) -> str:
    """A short excerpt around the first divergence, for the candidate queue.

    A curator triaging the queue needs to see *what* changed without opening
    the page; a bare "it changed" costs the same click the monitor saved.
    """
    a, b = normalize(old), normalize(new)
    if a == b:
        return ""
    i = 0
    for i, (ca, cb) in enumerate(zip(a, b)):
        if ca != cb:
            break
    else:
        i = min(len(a), len(b))
    start = max(0, i - width // 4)
    return b[start : start + width].strip()


@dataclass
class MonitorRun:
    """One pass over the watch list.

    ``fetch`` maps a key to page text and is injected: the caller supplies a
    rate-limited client in production and a dict-backed stub in tests.
    ``previous`` maps record_id to the last fingerprint seen.
    """

    fetch: Callable[[Watch], str]
    previous: dict[str, str] = field(default_factory=dict)
    now: str = "1970-01-01T00:00:00Z"

    def run(self, watches: Iterable[Watch] | None = None) -> list[Candidate]:
        candidates: list[Candidate] = []
        for watch in list(watches if watches is not None else iter_watches()):
            try:
                body = self.fetch(watch)
            except Exception as exc:  # noqa: BLE001 - one bad page must not
                # abort the sweep; an unreachable source is itself worth
                # surfacing, since it usually means the page moved.
                candidates.append(
                    Candidate(
                        record_id=watch.record_id,
                        dataset=watch.dataset,
                        kind=watch.kind,
                        key=watch.key,
                        previous_fingerprint=self.previous.get(watch.record_id),
                        fingerprint="",
                        summary=f"fetch failed: {type(exc).__name__}: {exc}",
                        detected_at=self.now,
                        note=watch.note,
                    )
                )
                continue

            current = fingerprint(body)
            prior = self.previous.get(watch.record_id)
            if prior == current:
                continue
            summary = (
                "first observation — baseline recorded, no change implied"
                if prior is None
                else "watched page changed since last run"
            )
            candidates.append(
                Candidate(
                    record_id=watch.record_id,
                    dataset=watch.dataset,
                    kind=watch.kind,
                    key=watch.key,
                    previous_fingerprint=prior,
                    fingerprint=current,
                    summary=summary,
                    detected_at=self.now,
                    note=watch.note,
                    excerpt="" if prior is None else first_difference("", body),
                )
            )
        return candidates
