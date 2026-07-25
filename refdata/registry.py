"""One id → location index over every curated dataset.

Before this module, a cross-reference between datasets was expressed as prose
and resolved by substring-matching every known display string against every
card body (``dashboard._linkify_refs``). That works until two records share a
substring, or a record is renamed, or a section moves to another tab — all of
which the 2026-07 review flagged. The registry replaces it for *explicit*
references: a record cites another record's **id**, and the renderer asks here
where that id lives.

A ``Ref`` answers three questions about an id: which tab owns it, what in-page
anchor scrolls to it, and what to call it in link text. That indirection is
what makes moving a section between tabs (plan Spec A3) a one-constant change
instead of a find-and-replace across three datasets.

Purity rule: no ``streamlit`` import.
"""

from __future__ import annotations

import re
from typing import NamedTuple

from refdata.loaders import (
    file_signature,
    LEGISLATION_PATH,
    COMPANY_WATER_CLAIMS_PATH,
    CWA_INVESTIGATIONS_PATH,
    WATER_AUTHORITIES_PATH,
    DC_WATER_CONFLICTS_PATH,
    WATER_NEWS_PATH,
    WATER_SOLUTIONS_PATH,
    load_company_water_claims,
    load_cwa_investigations,
    load_dc_water_conflicts,
    load_legislation,
    load_water_authorities,
    load_water_news,
    load_water_solutions,
)


class Ref(NamedTuple):
    """Where a record lives and what to call it."""

    id: str
    kind: str  # instrument | reading | case | site | claim | news | solution
    tab: str  # data-tab attribute of the owning tab in pages/index.html
    anchor: str  # in-page anchor id, WITHOUT the leading '#'
    label: str  # human-readable link text


# Which tab currently owns each record kind. Section moves between tabs (Spec
# A3 moves conflict sites out of Water Cases) are edits to this dict plus the
# builders — every cross-link in every dataset follows automatically.
KIND_TABS = {
    "instrument": "legislation",
    "claim": "legislation",
    "reading": "cwa",
    "case": "cwa",
    "site": "cwa",
    "news": "news",
    "solution": "solutions",
}


def bill_anchor(bill_id: str) -> str:
    """Stable anchor slug for a policy-instrument card.

    'VA HB 496 / SB 553' → 'bill-va-hb-496-sb-553'.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", str(bill_id).lower()).strip("-")
    return f"bill-{slug}"


def _anchor_for(kind: str, record_id: str) -> str:
    if kind == "instrument":
        return bill_anchor(record_id)
    prefix = {
        "reading": "reading",
        "case": "cwa",
        "site": "site",
        "claim": "claim",
        "news": "news",
        "solution": "solution",
    }[kind]
    return f"{prefix}-{record_id}"


def case_caption(case_id: str) -> str:
    """Human-readable caption derived from a case_id.

    'County-of-Maui-v-Hawaii-Wildlife-Fund-2020' → 'County of Maui v Hawaii
    Wildlife Fund (2020)'. Derived from the id rather than read from the
    record's ``respondent`` field for two reasons: the caption never goes
    stale when respondent text is edited, and ``respondent`` is a full legal
    party description ("Quality Technology Services (QTS Realty Trust)
    data-center construction site") that reads badly as link text.
    """
    m = re.match(r"^(.*?)-(\d{4}(?:-\d{4})?)$", case_id)
    name, year = (m.group(1), m.group(2)) if m else (case_id, "")
    caption = name.replace("-", " ")
    return f"{caption} ({year})" if year else caption


def _iter_records():
    """Yield ``(kind, id, label)`` for every curated record, in tab order."""
    for bill in load_legislation().get("bills", []):
        if bill.get("bill_id"):
            yield "instrument", bill["bill_id"], bill["bill_id"]

    for reading in load_water_authorities().get("readings", []):
        if reading.get("reading_id"):
            label = reading.get("name") or reading["reading_id"]
            yield "reading", reading["reading_id"], label

    for case in load_cwa_investigations().get("cases", []):
        if case.get("case_id"):
            yield "case", case["case_id"], case_caption(case["case_id"])

    for site in load_dc_water_conflicts().get("sites", []):
        if site.get("site_id"):
            yield "site", site["site_id"], site.get("site") or site["site_id"]

    for claim in load_company_water_claims().get("claims", []):
        if claim.get("id"):
            yield "claim", claim["id"], claim.get("statement", claim["id"])[:80]

    for item in load_water_news().get("items", []):
        if item.get("id"):
            yield "news", item["id"], item.get("title") or item["id"]

    for cat in load_water_solutions().get("categories", []):
        for sol in cat.get("solutions", []):
            if sol.get("id"):
                yield "solution", sol["id"], sol.get("title") or sol["id"]


_REGISTRY_CACHE: dict = {"sig": None, "registry": {}, "collisions": []}


def _signature() -> tuple:
    return tuple(
        file_signature(p)
        for p in (
            LEGISLATION_PATH,
            WATER_AUTHORITIES_PATH,
            CWA_INVESTIGATIONS_PATH,
            DC_WATER_CONFLICTS_PATH,
            COMPANY_WATER_CLAIMS_PATH,
            WATER_NEWS_PATH,
            WATER_SOLUTIONS_PATH,
        )
    )


def build_registry() -> dict[str, Ref]:
    """``{record_id: Ref}`` across all seven datasets.

    Rebuilt only when a source file changes (same mtime/size signature the
    loaders use), because every card that renders a cross-link calls this.

    Ids are assumed globally unique. If two datasets ever claim the same id the
    first wins and the collision is recorded in :func:`registry_collisions` —
    which :mod:`refdata.integrity` turns into a test failure rather than a
    silently mis-pointed link.
    """
    sig = _signature()
    if _REGISTRY_CACHE["sig"] != sig:
        registry: dict[str, Ref] = {}
        collisions: list[tuple[str, str, str]] = []
        for kind, record_id, label in _iter_records():
            if record_id in registry:
                collisions.append((record_id, registry[record_id].kind, kind))
                continue
            registry[record_id] = Ref(
                id=record_id,
                kind=kind,
                tab=KIND_TABS[kind],
                anchor=_anchor_for(kind, record_id),
                label=label,
            )
        _REGISTRY_CACHE.update(sig=sig, registry=registry, collisions=collisions)
    return _REGISTRY_CACHE["registry"]


def registry_collisions() -> list[tuple[str, str, str]]:
    """``(id, first_kind, duplicate_kind)`` for every id claimed twice."""
    build_registry()
    return _REGISTRY_CACHE["collisions"]


def resolve(record_id: str) -> Ref | None:
    """The :class:`Ref` for ``record_id``, or ``None`` if nothing claims it."""
    return build_registry().get(record_id)
