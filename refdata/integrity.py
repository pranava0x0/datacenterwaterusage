"""Referential-integrity walking over the cross-reference graph.

The curated datasets point at each other by id in a dozen places. A dangling
id renders as a link to nowhere — the failure is invisible in review and only
shows up when a reader clicks. This module enumerates every edge in one place
so a single test can assert the whole graph resolves, and so adding a new edge
type is one line here rather than a new bespoke test.

Each edge is ``(source_id, target_id, edge_kind)``. ``edge_kind`` names the
field it came from, so a failure message points at the exact JSON key.

Purity rule: no ``streamlit`` import.
"""

from __future__ import annotations

from typing import Iterator

from refdata.loaders import (
    load_company_water_claims,
    load_cwa_investigations,
    load_dc_water_conflicts,
    load_legislation,
    load_water_authorities,
    load_water_news,
    load_water_solutions,
)
from refdata.registry import build_registry

Edge = tuple[str, str, str]

# Which record kind each edge is allowed to point at. A `case.authorities`
# entry that resolves to a *site* is just as broken as one that resolves to
# nothing, and this catches it.
EDGE_TARGET_KINDS = {
    "case.authorities": {"reading"},
    "case.analogous_cases": {"case"},
    "case.related_claim_ids": {"claim"},
    "reading.example_case_ids": {"case"},
    "site.applicable_readings": {"reading"},
    "site.applicable_readings.analogous": {"case"},
    "site.related_case_ids": {"case"},
    "claim.related_site_ids": {"site"},
    "claim.challenged_in": {"case"},
    "instrument.related_case_ids": {"case"},
    "instrument.implements": {"instrument"},
    "news.cross_ref_targets": {"instrument", "case", "site", "claim", "solution"},
    "solution.cross_ref_targets": {"instrument", "case", "site", "claim", "news"},
}


def _ids(value) -> list[str]:
    """Normalize a possibly-absent id list field to a list of non-empty strings."""
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value if v]


def iter_edges() -> Iterator[Edge]:
    """Every explicit id→id reference across the seven curated datasets."""
    for case in load_cwa_investigations().get("cases", []):
        src = case.get("case_id", "")
        for target in _ids(case.get("authorities")):
            yield src, target, "case.authorities"
        for target in _ids(case.get("analogous_cases")):
            yield src, target, "case.analogous_cases"
        for target in _ids(case.get("related_claim_ids")):
            yield src, target, "case.related_claim_ids"

    for reading in load_water_authorities().get("readings", []):
        src = reading.get("reading_id", "")
        for target in _ids(reading.get("example_case_ids")):
            yield src, target, "reading.example_case_ids"

    for site in load_dc_water_conflicts().get("sites", []):
        src = site.get("site_id", "")
        for mapping in site.get("applicable_readings", []) or []:
            if mapping.get("reading_id"):
                yield src, mapping["reading_id"], "site.applicable_readings"
            for target in _ids(mapping.get("analogous_cases")):
                yield src, target, "site.applicable_readings.analogous"
        for target in _ids(site.get("related_case_ids")):
            yield src, target, "site.related_case_ids"

    for claim in load_company_water_claims().get("claims", []):
        src = claim.get("id", "")
        for target in _ids(claim.get("related_site_ids")):
            yield src, target, "claim.related_site_ids"
        for target in _ids(claim.get("challenged_in")):
            yield src, target, "claim.challenged_in"

    for bill in load_legislation().get("bills", []):
        src = bill.get("bill_id", "")
        for target in _ids(bill.get("related_case_ids")):
            yield src, target, "instrument.related_case_ids"
        for target in _ids(bill.get("implements")):
            yield src, target, "instrument.implements"

    for item in load_water_news().get("items", []):
        src = item.get("id", "")
        for target in _ids(item.get("cross_ref_targets")):
            yield src, target, "news.cross_ref_targets"

    for cat in load_water_solutions().get("categories", []):
        for sol in cat.get("solutions", []):
            src = sol.get("id", "")
            for target in _ids(sol.get("cross_ref_targets")):
                yield src, target, "solution.cross_ref_targets"


def dangling_edges() -> list[Edge]:
    """Edges whose target id no record claims."""
    registry = build_registry()
    return [e for e in iter_edges() if e[1] not in registry]


def miskinded_edges() -> list[tuple[str, str, str, str]]:
    """``(src, target, edge_kind, actual_kind)`` for edges pointing at the
    wrong kind of record — a resolvable id that still means the wrong thing."""
    registry = build_registry()
    bad = []
    for src, target, edge_kind in iter_edges():
        ref = registry.get(target)
        allowed = EDGE_TARGET_KINDS.get(edge_kind)
        if ref and allowed and ref.kind not in allowed:
            bad.append((src, target, edge_kind, ref.kind))
    return bad


def asymmetric_claim_case_edges() -> list[str]:
    """Claim↔case links declared on only one side.

    ``claim.challenged_in`` and ``case.related_claim_ids`` describe the same
    relationship. Declaring one without the other means one card shows the
    link and its counterpart doesn't — the kind of half-wired edge that reads
    as a data bug to a user.
    """
    forward = {
        (claim.get("id"), case_id)
        for claim in load_company_water_claims().get("claims", [])
        for case_id in _ids(claim.get("challenged_in"))
    }
    backward = {
        (claim_id, case.get("case_id"))
        for case in load_cwa_investigations().get("cases", [])
        for claim_id in _ids(case.get("related_claim_ids"))
    }
    problems = [
        f"claim '{c}' lists challenged_in '{k}' but that case has no related_claim_ids entry"
        for c, k in sorted(forward - backward)
    ]
    problems += [
        f"case '{k}' lists related_claim_ids '{c}' but that claim has no challenged_in entry"
        for c, k in sorted(backward - forward)
    ]
    return problems
