"""Check a project: apply the tracked record to a described data-center proposal.

WHY THIS EXISTS
---------------
The Explore tab answers "which records use the same words as this text?".
That is wording, not law: a paragraph about an Arizona campus matches every
record that says "Arizona" and nothing that says "groundwater management
area". What a reader with a project in front of them actually wants is the
chain the Water Cases tab draws by hand for nineteen sites — *this fact
pattern → these statutory readings could reach it → these cases are the
closest history → this is what usually happened* — computed for a project
the tracker has never seen.

The computation is deliberately shallow and showable. Every case and
conflict site carries ``fact_pattern``, a list of facets from the closed
:data:`refdata.taxonomies.FACT_FACETS` vocabulary (where the water comes
from, how it is used, where it goes, what the site is, what powers it, what
chemicals it holds, how the approval runs). Every statutory reading carries
``fact_triggers``: the facets whose presence makes it potentially reach a
project. A project is parsed into the same facets — trigger words in a
pasted description, or chips a reader ticks — and matched by weighted
overlap, so the result is always explained by the facets in common. No
embeddings, no model call, no server: the browser runs the same arithmetic
this module does, from a payload this module emits, and a build test holds
the two to the same answer on a fixture.

Copy discipline carries into the code: nothing here predicts an outcome.
``outcomes`` is a tally of what the closest tracked cases recorded, and the
page says so.

Purity rule: no ``streamlit`` import.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter

from refdata.graph import (
    MIN_TOKEN_LEN,
    STOPWORDS,
    build_search_index,
    tokenize,
)
from functools import lru_cache

from refdata.loaders import (
    REFERENCE_DIR,
    _read_json,
    file_signature,
    load_cwa_investigations,
    load_dc_water_conflicts,
    load_legislation,
    load_local_actions,
    load_water_authorities,
)
from refdata.registry import build_registry
from refdata.taxonomies import (
    DC_ACTIVITY_LABELS,
    DC_ROLE_LABELS,
    FACT_DIMENSION_LABELS,
    FACT_FACETS,
    OUTCOME_TYPE_LABELS,
    US_STATE_NAMES,
    WATER_STATUTE_ORDER,
)

PROJECT_EXAMPLES_PATH = REFERENCE_DIR / "project_examples.json"

# --- Tunables (mirrored into the page's JavaScript from the payload) ---------

# A stated size at or above either figure sets the hyperscale facet even when
# no trigger word does. 100 MW is where a single campus starts to move a
# utility's planning numbers; 1 MGD is a small city's demand.
HYPERSCALE_MW = 100.0
HYPERSCALE_MGD = 1.0
# How much the wording similarity (TF-IDF cosine over the record's own text)
# adds to the facet similarity for cases and sites. Facets carry the legal
# meaning; wording catches the names — an operator, a county, an aquifer —
# that no facet encodes. Readings get no lexical term: a reading's prose is
# about doctrine, and matching a project's words against it rewards nothing.
LEXICAL_WEIGHT = 0.35
# How many of the closest cases feed the outcome tally.
OUTCOME_SAMPLE = 10
TOP_CASES = 12
TOP_SITES = 6
TOP_READINGS = 12
SCORE_DECIMALS = 6
# A reading that names its jurisdictions (Arizona's AMA regime, California's
# SGMA) still appears for a project elsewhere — as the analogy it is — but
# scored down and flagged, so a Texas reader is not told SGMA reaches them.
ELSEWHERE_FACTOR = 0.25

_NUMBER = r"(\d[\d,]*(?:\.\d+)?)"
MW_RE = re.compile(_NUMBER + r"\s*(gigawatts?|gw|megawatts?|mw)\b", re.IGNORECASE)
# A per-day figure only. "78 million gallons over two years" and "31 million
# gallons a year" say nothing about daily demand, and "mgd" already means it.
MGD_RE = re.compile(
    _NUMBER + r"\s*(?:mgd|mg/d|million gallons?\s*(?:per|a|/|each)\s*day)\b", re.IGNORECASE
)
# "5,000,000 gallons a day" / "750,000 gallons per day" — read in gallons, then
# scaled to MGD. Only a per-day figure counts; "per year" says little about
# peak demand and "per minute" belongs to well permits (gpm), not campuses.
GALLONS_PER_DAY_RE = re.compile(
    _NUMBER + r"\s*(gallons?|gal)\s*(?:per|a|/|each)\s*day\b", re.IGNORECASE
)


def _number(text: str) -> float:
    return float(text.replace(",", ""))


# A state name that is really part of a place or river name: "Port Washington",
# "Fort Worth"-style prefixes, "Colorado River" (Texas has one of its own).
_NOT_A_STATE_BEFORE = re.compile(r"(?:\b(?:port|fort|lake|mount|new|west|north|south|east)\s+)$", re.IGNORECASE)
_NOT_A_STATE_AFTER = re.compile(r"^\s+(?:river|street|avenue|road|county\s+water)\b", re.IGNORECASE)
_STATE_EXACT = {"New York", "New Mexico", "New Jersey", "New Hampshire", "West Virginia",
                "North Carolina", "North Dakota", "South Carolina", "South Dakota"}


def state_code_for(text: str | None) -> str | None:
    """The state a passage is about, as a two-letter code, or ``None``.

    Full names count, and the name mentioned most often wins, a name after a
    comma counting double — a passage on a campus in "Henderson County, Texas"
    by "a Kansas developer" is about Texas. A name that is part
    of another place's name ("Port Washington", "Colorado River") is skipped.
    Ties go to the earliest mention. A bare two-letter token counts only when
    nothing else does, and only if it is a real code, so "US EPA" names no
    state.
    """
    text = (text or "").strip()
    if not text or text in ("Federal (US)", "United States"):
        return None
    by_name = {name: code for code, name in US_STATE_NAMES.items()}
    if text in by_name:
        return by_name[text]
    counts: dict[str, int] = {}
    first: dict[str, int] = {}
    taken: list[tuple[int, int]] = []
    for name in sorted(by_name, key=len, reverse=True):
        for m in re.finditer(r"\b" + re.escape(name) + r"\b", text, re.IGNORECASE):
            if any(a <= m.start() < b for a, b in taken):
                continue  # inside a longer name already counted (West Virginia)
            if name not in _STATE_EXACT and _NOT_A_STATE_BEFORE.search(text[: m.start()]):
                continue
            if _NOT_A_STATE_AFTER.search(text[m.end():]):
                continue
            taken.append((m.start(), m.end()))
            code = by_name[name]
            # "Henderson County, Texas" is a location; "a Kansas developer" is
            # an adjective. The comma is worth a second mention.
            counts[code] = counts.get(code, 0) + (2 if text[: m.start()].rstrip().endswith(",") else 1)
            first.setdefault(code, m.start())
    if counts:
        return min(counts, key=lambda c: (-counts[c], first[c]))
    for token in re.findall(r"\b([A-Z]{2})\b", text):
        if token in US_STATE_NAMES:
            return token
    return None


# --- Parsing a description -----------------------------------------------------


def parse_project(text: str) -> dict:
    """Read a pasted description into facets, a state and a size.

    ``matched`` records which trigger words set each facet, so the page can
    say "we read *groundwater* and *wells* as On-site groundwater wells" and
    the reader can untick it. Facets come back in taxonomy order.
    """
    tokens = set(tokenize(text))
    matched: dict[str, list[str]] = {}
    for facet_id, facet in FACT_FACETS.items():
        if any(b in tokens for b in facet.get("blockers", [])):
            continue
        hits = [t for t in facet["triggers"] if t in tokens]
        if hits:
            matched[facet_id] = hits

    mw = None
    for value, unit in MW_RE.findall(text or ""):
        n = _number(value) * (1000.0 if unit.lower().startswith("g") else 1.0)
        mw = n if mw is None else max(mw, n)
    mgd = None
    for value in MGD_RE.findall(text or ""):
        n = _number(value)
        mgd = n if mgd is None else max(mgd, n)
    for value, _unit in GALLONS_PER_DAY_RE.findall(text or ""):
        n = _number(value) / 1_000_000.0
        mgd = n if mgd is None else max(mgd, n)

    if (mw is not None and mw >= HYPERSCALE_MW) or (mgd is not None and mgd >= HYPERSCALE_MGD):
        matched.setdefault("scale-hyperscale", []).append(
            f"{mw:g} MW" if mw is not None and mw >= HYPERSCALE_MW else f"{mgd:g} MGD"
        )

    return {
        "facets": [f for f in FACT_FACETS if f in matched],
        "matched": matched,
        "state": state_code_for(text),
        "mw": mw,
        "mgd": mgd,
    }


# --- Records ----------------------------------------------------------------------


def _short(text: str, limit: int = 260) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut + "…"


def _records() -> dict:
    """Cases, sites and readings with the fields the engine and the page use."""
    reg = build_registry()
    cases = []
    for c in load_cwa_investigations().get("cases", []):
        ref = reg.get(c.get("case_id", ""))
        if ref is None:
            continue
        cases.append(
            {
                "id": c["case_id"],
                "label": ref.label,
                "facets": list(c.get("fact_pattern") or []),
                "outcome_type": list(c.get("outcome_type") or []),
                "case_type": c.get("case_type", ""),
                "category": c.get("category", ""),
                "year": str(c.get("year", "")),
                "cwa_applied": c.get("cwa_applied", ""),
                "instrument": _short(c.get("cwa_instrument", ""), 120),
                "takeaway": _short(c.get("takeaway", "")),
                "tab": ref.tab,
                "anchor": ref.anchor,
            }
        )
    sites = []
    for s in load_dc_water_conflicts().get("sites", []):
        ref = reg.get(s.get("site_id", ""))
        if ref is None:
            continue
        sites.append(
            {
                "id": s["site_id"],
                "label": ref.label,
                "facets": list(s.get("fact_pattern") or []),
                "issue_types": list(s.get("issue_types") or []),
                "location": s.get("location", ""),
                "state": state_code_for(s.get("location", "")),
                "status": _short(s.get("status_2026", "")),
                "tab": ref.tab,
                "anchor": ref.anchor,
            }
        )
    readings = []
    for r in load_water_authorities().get("readings", []):
        ref = reg.get(r.get("reading_id", ""))
        if ref is None:
            continue
        readings.append(
            {
                "id": r["reading_id"],
                "label": r.get("name", ref.label),
                "statute": r.get("statute", ""),
                "section": r.get("section", ""),
                "activities": list(r.get("dc_activities") or []),
                "role": r.get("dc_role", "hook"),
                "trigger": r.get("dc_trigger", ""),
                "triggers": list(r.get("fact_triggers") or []),
                "jurisdictions": list(r.get("jurisdictions") or []),
                "example_case_ids": list(r.get("example_case_ids") or []),
                "tab": ref.tab,
                "anchor": ref.anchor,
            }
        )
    return {"cases": cases, "sites": sites, "readings": readings}


def facet_weights(cases: list[dict], sites: list[dict]) -> dict[str, float]:
    """``1 + ln(N / df)`` over cases and sites — a facet half the record shares
    separates less than one three records share. Never below 1, so a rare
    facet in common always counts for something."""
    docs = [r["facets"] for r in cases + sites]
    n = len(docs) or 1
    df = Counter(f for facets in docs for f in set(facets))
    return {
        f: round(1.0 + math.log(n / max(1, df.get(f, 0))), SCORE_DECIMALS) for f in FACT_FACETS
    }


def overlap(a: list[str], b: list[str], weights: dict[str, float]) -> tuple[float, list[str]]:
    """Weighted cosine between two facet sets, plus the facets in common.

    Binary vectors weighted by :func:`facet_weights`: ``Σw(shared) /
    √(Σw(a)·Σw(b))``. Cosine rather than Jaccard so a one-facet site is not
    penalised against a nine-facet project for the facets the project has
    and the site's record never mentioned.
    """
    sa, sb = set(a), set(b)
    shared = [f for f in FACT_FACETS if f in sa and f in sb]
    if not shared:
        return 0.0, []
    num = sum(weights.get(f, 1.0) for f in shared)
    na = sum(weights.get(f, 1.0) for f in sa)
    nb = sum(weights.get(f, 1.0) for f in sb)
    return round(num / math.sqrt(na * nb), SCORE_DECIMALS), shared


def _lexical_scores(text: str, index: dict, doc_ids: set[str]) -> dict[str, float]:
    """TF-IDF cosine of ``text`` against the records in ``doc_ids`` — the same
    arithmetic as the Explore search, restricted to cases and sites."""
    if not (text or "").strip():
        return {}
    counts = Counter(t for t in tokenize(text) if t in index["df"])
    if not counts:
        return {}
    n_docs = index["n_docs"]
    qw = {t: c * math.log(n_docs / index["df"][t]) for t, c in counts.items()}
    norm = math.sqrt(sum(w * w for w in qw.values())) or 1.0
    out = {}
    for doc_id in doc_ids:
        vec = index["docs"].get(doc_id) or {}
        total = sum((qw[t] / norm) * w for t, w in vec.items() if t in qw)
        if total > 0:
            out[doc_id] = round(total, SCORE_DECIMALS)
    return out


def match_project(
    facets: list[str],
    state: str | None = None,
    text: str = "",
    records: dict | None = None,
    index: dict | None = None,
) -> dict:
    """Rank the record against a project's facets (and, optionally, its words).

    Returns the pieces the page renders, each already sorted and already
    carrying its explanation (``shared`` facets, matched activities):

    ``readings``
        statutory readings whose ``fact_triggers`` overlap the project, best
        first, with ``role`` so a limit is never shown as a route and
        ``elsewhere`` when the reading's regime belongs to another state;
    ``activities``
        the data-center activities those readings belong to, in path order;
    ``cases`` / ``sites``
        the closest tracked cases and conflict sites, facet cosine plus
        :data:`LEXICAL_WEIGHT` × wording cosine when a description was given;
    ``outcomes``
        a tally of ``outcome_type`` over the :data:`OUTCOME_SAMPLE` closest
        cases — what was recorded, not what will happen;
    ``instruments`` / ``local_actions``
        the tracked instruments in the named state (enacted first) and the
        county and city actions there — empty without a state.
    """
    recs = records or _records()
    weights = facet_weights(recs["cases"], recs["sites"])
    facets = [f for f in FACT_FACETS if f in set(facets)]

    def ranked(items: list[dict], top: int, lexical: dict[str, float]) -> list[dict]:
        rows = []
        for item in items:
            score, shared = overlap(facets, item["facets"], weights)
            lex = lexical.get(item["id"], 0.0)
            total = round(score + LEXICAL_WEIGHT * lex, SCORE_DECIMALS)
            if total > 0:
                rows.append({**item, "score": total, "facet_score": score, "lexical": lex, "shared": shared})
        rows.sort(key=lambda r: (-r["score"], r["id"]))
        return rows[:top]

    lexical: dict[str, float] = {}
    if (text or "").strip():
        idx = index or build_search_index()
        ids = {r["id"] for r in recs["cases"]} | {r["id"] for r in recs["sites"]}
        lexical = _lexical_scores(text, idx, ids)

    cases = ranked(recs["cases"], TOP_CASES, lexical)
    sites = ranked(recs["sites"], TOP_SITES, lexical)

    readings = []
    for r in recs["readings"]:
        score, shared = overlap(facets, r["triggers"], weights)
        if score > 0:
            elsewhere = bool(state and r["jurisdictions"] and state not in r["jurisdictions"])
            if elsewhere:
                score = round(score * ELSEWHERE_FACTOR, SCORE_DECIMALS)
            readings.append({**r, "score": score, "shared": shared, "elsewhere": elsewhere})
    readings.sort(key=lambda r: (-r["score"], r["id"]))
    readings = readings[:TOP_READINGS]

    activity_order = list(DC_ACTIVITY_LABELS)
    activities = sorted(
        {a for r in readings for a in r["activities"]},
        key=lambda a: activity_order.index(a) if a in activity_order else 99,
    )

    tally = Counter(o for c in cases[:OUTCOME_SAMPLE] for o in c["outcome_type"])
    outcomes = [
        {"outcome": o, "label": OUTCOME_TYPE_LABELS.get(o, o), "count": n}
        for o, n in sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))
    ]

    instruments, local_actions = [], []
    if state:
        instruments = [i for i in _instruments() if i["state"] == state]
        instruments.sort(key=lambda i: (0 if i["status"] == "enacted" else 1, i["id"]))
        local_actions = sorted(
            (a for a in _local_actions() if a["state"] == state),
            key=lambda a: (a["date"] or ""),
            reverse=True,
        )

    return {
        "facets": facets,
        "state": state,
        "readings": readings,
        "activities": activities,
        "cases": cases,
        "sites": sites,
        "outcomes": outcomes,
        "outcome_sample": min(OUTCOME_SAMPLE, len(cases)),
        "instruments": instruments,
        "local_actions": local_actions,
    }


def _instruments() -> list[dict]:
    reg = build_registry()
    out = []
    for b in load_legislation().get("bills", []):
        ref = reg.get(b.get("bill_id", ""))
        if ref is None:
            continue
        out.append(
            {
                "id": b["bill_id"],
                "label": ref.label,
                "title": _short(b.get("title", ""), 140),
                "jurisdiction": b.get("jurisdiction", ""),
                "state": state_code_for(b.get("jurisdiction", "")),
                "level": b.get("level", ""),
                "status": b.get("status", ""),
                "tab": ref.tab,
                "anchor": ref.anchor,
            }
        )
    return out


def _local_actions() -> list[dict]:
    return [
        {
            "id": a.get("action_id", ""),
            "jurisdiction": a.get("jurisdiction", ""),
            "state": a.get("state", ""),
            "action_type": a.get("action_type", ""),
            "status": a.get("status", ""),
            "date": a.get("date", ""),
            "water_related": bool(a.get("water_related")),
        }
        for a in load_local_actions().get("actions", [])
    ]


# --- Worked examples -----------------------------------------------------------------


@lru_cache(maxsize=2)
def _load_project_examples_cached(path_str: str, signature: tuple) -> dict:
    return _read_json(path_str, {"examples": list})


def load_project_examples() -> dict:
    """``project_examples.json`` — real 2026 proposals the tab offers as
    one-click inputs. Each carries a curated facet list; the description's
    parse is a convenience, the curated list is the record."""
    return _load_project_examples_cached(str(PROJECT_EXAMPLES_PATH), file_signature(PROJECT_EXAMPLES_PATH))


# --- Payload ---------------------------------------------------------------------------


def build_payload() -> dict:
    """Everything the page needs, in one same-origin JSON file.

    Shipped: the facet vocabulary with its trigger words and weights, the
    records with their facets and the short lines the result cards show, the
    state's instruments and local actions, the worked examples, and a
    TF-IDF index over cases and sites in the Explore payload's shape (vocab
    positions, integer weights) so the page can reuse that code path. The
    constants travel too, so the JavaScript is parametrised rather than
    transcribed.
    """
    recs = _records()
    weights = facet_weights(recs["cases"], recs["sites"])
    index = build_search_index()
    wanted = {r["id"] for r in recs["cases"]} | {r["id"] for r in recs["sites"]}
    docs_raw = {rid: vec for rid, vec in index["docs"].items() if rid in wanted and vec}
    vocab = sorted({t for vec in docs_raw.values() for t in vec})
    position = {t: i for i, t in enumerate(vocab)}
    from refdata.graph import WEIGHT_SCALE  # noqa: PLC0415 — keeps the import graph acyclic at module load

    docs = {
        rid: {
            "t": [position[t] for t in vec],
            "w": [round(w * WEIGHT_SCALE) for w in vec.values()],
        }
        for rid, vec in sorted(docs_raw.items())
    }
    return {
        "facets": {
            fid: {
                "dimension": f["dimension"],
                "label": f["label"],
                "description": f["description"],
                "triggers": list(f["triggers"]),
                "blockers": list(f.get("blockers", [])),
                "weight": weights[fid],
            }
            for fid, f in FACT_FACETS.items()
        },
        "dimensions": dict(FACT_DIMENSION_LABELS),
        "activities": dict(DC_ACTIVITY_LABELS),
        "roles": dict(DC_ROLE_LABELS),
        "statute_order": list(WATER_STATUTE_ORDER),
        "outcomes": dict(OUTCOME_TYPE_LABELS),
        "states": dict(US_STATE_NAMES),
        "readings": recs["readings"],
        "cases": recs["cases"],
        "sites": recs["sites"],
        "instruments": _instruments(),
        "local_actions": _local_actions(),
        "examples": load_project_examples().get("examples", []),
        "index": {
            "vocab": vocab,
            "df": [index["df"][t] for t in vocab],
            "n_docs": index["n_docs"],
            "docs": docs,
            "weight_scale": WEIGHT_SCALE,
        },
        "stopwords": sorted(STOPWORDS),
        "min_token_len": MIN_TOKEN_LEN,
        "constants": {
            "hyperscale_mw": HYPERSCALE_MW,
            "hyperscale_mgd": HYPERSCALE_MGD,
            "lexical_weight": LEXICAL_WEIGHT,
            "outcome_sample": OUTCOME_SAMPLE,
            "top_cases": TOP_CASES,
            "top_sites": TOP_SITES,
            "top_readings": TOP_READINGS,
            "score_decimals": SCORE_DECIMALS,
            "elsewhere_factor": ELSEWHERE_FACTOR,
        },
    }


_PAYLOAD_CACHE: dict = {"sig": None, "json": ""}


def _signature() -> tuple:
    from refdata.registry import _signature as registry_signature

    return (registry_signature(), file_signature(PROJECT_EXAMPLES_PATH), file_signature(REFERENCE_DIR / "local_actions.json"))


def payload_json() -> str:
    """The payload as bytes on the wire, memoised on its inputs' signatures."""
    sig = _signature()
    if _PAYLOAD_CACHE["sig"] != sig:
        _PAYLOAD_CACHE["json"] = json.dumps(build_payload(), separators=(",", ":")).replace("</", "<\\/")
        _PAYLOAD_CACHE["sig"] = sig
    return _PAYLOAD_CACHE["json"]
