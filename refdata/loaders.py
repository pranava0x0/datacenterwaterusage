"""Loaders for the seven curated reference datasets.

Moved verbatim out of ``dashboard.py`` (2026-07-25) so both surfaces — the
Streamlit app and ``build_site.py`` — share one loading layer, and so the
registry/integrity helpers below can import data without importing Streamlit.

**Purity rule:** this module must never import ``streamlit``. The caching that
``@st.cache_data`` used to provide is reproduced with ``functools.lru_cache``
keyed on the same ``(path_str, signature)`` pair, so the cache still busts on
file change (mtime/size) rather than on a fixed clock. The reference JSON
changes only when a scraper or a curation edit runs, so a TTL would just force
needless re-parsing during an active session.

Callers must treat returned payloads as read-only — they are shared cached
objects, exactly as they were under ``st.cache_data``.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REFERENCE_DIR = BASE_DIR / "data" / "reference"

LEGISLATION_PATH = REFERENCE_DIR / "legislation.json"
COMPANY_WATER_CLAIMS_PATH = REFERENCE_DIR / "company_water_claims.json"
CWA_INVESTIGATIONS_PATH = REFERENCE_DIR / "cwa_investigations.json"
WATER_AUTHORITIES_PATH = REFERENCE_DIR / "water_authorities.json"
DC_WATER_CONFLICTS_PATH = REFERENCE_DIR / "dc_water_conflicts.json"
WATER_NEWS_PATH = REFERENCE_DIR / "water_news.json"
WATER_SOLUTIONS_PATH = REFERENCE_DIR / "water_solutions.json"


def file_signature(path) -> tuple:
    """A cheap change-detector for a file: ``(mtime_ns, size)``.

    Passed into the cached loaders below so a file is re-read only when it
    actually changes. Returns ``(0, 0)`` for a missing file so a later create
    still busts the cache.
    """
    try:
        s = os.stat(path)
        return (s.st_mtime_ns, s.st_size)
    except OSError:
        return (0, 0)


def _read_json(path_str: str, defaults: dict) -> dict:
    """Read a curated JSON payload, filling in ``defaults`` for absent keys.

    Tolerates a missing file by returning a copy of ``defaults`` — the
    dashboard renders an empty section rather than crashing.
    """
    p = Path(path_str)
    if not p.exists():
        return {"last_updated": None, **{k: v() for k, v in defaults.items()}}
    with open(p, encoding="utf-8") as f:
        payload = json.load(f)
    for key, factory in defaults.items():
        payload.setdefault(key, factory())
    return payload


@lru_cache(maxsize=None)
def _load_legislation_cached(path_str: str, signature: tuple) -> dict:
    p = Path(path_str)
    if p.exists():
        with open(p, encoding="utf-8") as f:
            payload = json.load(f)
        # Tolerate the pre-2026 bare-list shape.
        if isinstance(payload, list):
            return {"last_updated": None, "bills": payload}
    return _read_json(path_str, {"bills": list})


def load_legislation(path: Path = LEGISLATION_PATH) -> dict:
    """Load the data center water/energy policy-instrument dataset.

    Returns ``{"last_updated": str, "bills": [...]}``. Despite the key name
    the records are policy *instruments* — bills, executive orders, agency
    rules, commission dockets, local ordinances (see ``instrument_type``).
    """
    return _load_legislation_cached(str(path), file_signature(path))


@lru_cache(maxsize=None)
def _load_company_water_claims_cached(path_str: str, signature: tuple) -> dict:
    return _read_json(path_str, {"claims": list, "companies": dict})


def load_company_water_claims(path: Path = COMPANY_WATER_CLAIMS_PATH) -> dict:
    """Load the company water-claims dataset.

    Returns ``{"last_updated", "companies", "claims", ...}``.
    """
    return _load_company_water_claims_cached(str(path), file_signature(path))


@lru_cache(maxsize=None)
def _load_cwa_investigations_cached(path_str: str, signature: tuple) -> dict:
    return _read_json(path_str, {"cases": list})


def load_cwa_investigations(path: Path = CWA_INVESTIGATIONS_PATH) -> dict:
    """Load the water-law enforcement / permit-matter / precedent case corpus.

    Returns ``{"last_updated": str, "cases": [...], "note": Optional[str]}``.
    The ``cwa_*`` naming is legacy — the corpus spans the CWA, SDWA, TSCA,
    RCRA, RHA and (since Spec C1) state-law doctrine families.
    """
    return _load_cwa_investigations_cached(str(path), file_signature(path))


@lru_cache(maxsize=None)
def _load_water_authorities_cached(path_str: str, signature: tuple) -> dict:
    return _read_json(path_str, {"statutes": dict, "readings": list})


def load_water_authorities(path: Path = WATER_AUTHORITIES_PATH) -> dict:
    """Load the legal-authority "readings" registry.

    Returns ``{"last_updated", "statutes": {code: meta}, "readings": [...]}``.
    Each reading is one specific legal hook (CWA §404, the public-trust
    reopener, …) with its data-center applicability and example case_ids.
    """
    return _load_water_authorities_cached(str(path), file_signature(path))


@lru_cache(maxsize=None)
def _load_dc_water_conflicts_cached(path_str: str, signature: tuple) -> dict:
    return _read_json(path_str, {"sites": list})


def load_dc_water_conflicts(path: Path = DC_WATER_CONFLICTS_PATH) -> dict:
    """Load the roster of data-center sites with documented water conflicts."""
    return _load_dc_water_conflicts_cached(str(path), file_signature(path))


@lru_cache(maxsize=None)
def _load_water_news_cached(path_str: str, signature: tuple) -> dict:
    return _read_json(path_str, {"items": list})


def load_water_news(path: Path = WATER_NEWS_PATH) -> dict:
    """Load curated data center water news items."""
    return _load_water_news_cached(str(path), file_signature(path))


@lru_cache(maxsize=None)
def _load_water_solutions_cached(path_str: str, signature: tuple) -> dict:
    return _read_json(path_str, {"categories": list})


def load_water_solutions(path: Path = WATER_SOLUTIONS_PATH) -> dict:
    """Load data center water solutions by category."""
    return _load_water_solutions_cached(str(path), file_signature(path))


def clear_caches() -> None:
    """Drop every loader cache. Used by tests that write temp fixtures."""
    for fn in (
        _load_legislation_cached,
        _load_company_water_claims_cached,
        _load_cwa_investigations_cached,
        _load_water_authorities_cached,
        _load_dc_water_conflicts_cached,
        _load_water_news_cached,
        _load_water_solutions_cached,
    ):
        fn.cache_clear()
