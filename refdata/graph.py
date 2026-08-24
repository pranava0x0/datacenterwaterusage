"""One graph and one lexical index over every curated record.

WHY THIS EXISTS
---------------
The tabs answer "what is in this dataset?" well and "what connects to this?"
not at all. The connections are already in the data — a case names its
statutory readings, a site names analogous cases, a claim names the site it
was made about — but each tab renders only the edges that leave *its own*
records, so following a thread means clicking through three tabs and holding
the trail in your head. Nothing anywhere lets a reader arrive with a
paragraph of text (a news story, a draft ordinance, a permit notice) and ask
which tracked records it resembles.

This module builds both answers at generation time, in pure Python, so the
reader's browser needs no network call and the page needs no server:

- :func:`build_graph` — nodes from :func:`refdata.registry.build_registry`
  (the same id → tab/anchor index every cross-link already resolves through),
  edges from :func:`refdata.integrity.iter_edges` (the same walker the
  referential-integrity test uses). Neither is re-derived here: a relationship
  the datasets do not declare is not an edge. The only additions are
  *taxonomy hubs* — one node per statute family, case type and legislative
  principle — which turn a shared classification into a walkable connection.
  They are marked ``derived`` and carry their own edge kinds so the UI can
  show curated cross-references alone, which is the honest default.
- :func:`build_search_index` — a TF-IDF vector per record over the fields a
  reader would call the record's substance. Lexical, not semantic: embeddings
  would need API tokens at build time, so they are backlog. The pay-off of
  lexical is that the *reason* for a match is showable — the matched terms
  are right there in the vector.

The tokenizer is the load-bearing part: the browser re-tokenizes the pasted
query and must produce exactly the tokens this module keyed the index by.
:data:`STOPWORDS` and the two regex rules are therefore emitted into the page's
JavaScript from these constants rather than transcribed, so parity is by
construction and a build test round-trips a fixture through both.

Purity rule: no ``streamlit`` import.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter

from refdata.integrity import iter_edges
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
from refdata.taxonomies import (
    COLORS,
    CWA_CASE_TYPE_LABELS,
    LEGISLATION_PRINCIPLE_DESCRIPTIONS,
    WATER_STATUTE_ORDER,
)

# --- Node styling ------------------------------------------------------------

# Colour encodes record *kind* here — a legend, the same job it does in
# WATER_STATUTE_COLORS — not status, so the "no decorative colour" rule holds.
# Every value is already in the project palette; nothing new enters it.
KIND_COLORS = {
    "instrument": COLORS["primary"],   # #08519c
    "reading": "#7c3aed",
    "case": "#b45309",
    "site": COLORS["danger"],          # #c41e3a
    "claim": COLORS["success"],        # #2e8b57
    "news": COLORS["secondary"],       # #3182bd
    "solution": "#6b7f2a",
    "hub": "#6b7280",                  # neutral — a hub is a label, not a record
}

KIND_LABELS = {
    "instrument": "Policy instrument",
    "reading": "Statutory reading",
    "case": "Water case",
    "site": "Conflict site",
    "claim": "Operator claim",
    "news": "News item",
    "solution": "Solution",
    "hub": "Taxonomy hub",
}


# --- Taxonomy hubs -----------------------------------------------------------

# Membership in a closed taxonomy is a real connection between records — two
# cases sharing a case_type are related in a way the curated id-edges never
# state — but it is a *different* kind of connection, so it gets its own node
# ids, its own edge kinds, and its own toggle. Hub ids are namespaced so they
# can never collide with a record id (which would silently re-point a link).
HUB_ID_PREFIX = "hub:"

# derived edge kind → the hub group (and id segment) it points into
DERIVED_EDGE_KINDS = {
    "reading.family": "statute",
    "case.type": "case-type",
    "instrument.principle": "principle",
}

# What each edge kind means in a sentence a reader can act on. The edge-kind
# toggles are the graph's only vocabulary, so a raw JSON key ("site.
# applicable_readings.analogous") would make the control row unusable. Closed
# like every other taxonomy here: a test asserts every emitted kind has a label.
EDGE_KIND_LABELS = {
    "case.authorities": "Case → statutory reading",
    "case.analogous_cases": "Case → analogous case",
    "case.related_claim_ids": "Case → operator claim",
    "reading.example_case_ids": "Reading → example case",
    "site.applicable_readings": "Site → statutory reading",
    "site.applicable_readings.analogous": "Site → analogous case",
    "site.related_case_ids": "Site → related case",
    "claim.related_site_ids": "Claim → site",
    "claim.challenged_in": "Claim → case challenging it",
    "instrument.related_case_ids": "Instrument → case",
    "instrument.implements": "Instrument → what it implements",
    "news.cross_ref_targets": "News → tracked record",
    "solution.cross_ref_targets": "Solution → tracked record",
    "reading.family": "Reading → statute family",
    "case.type": "Case → project type",
    "instrument.principle": "Instrument → principle",
}


def hub_id(group: str, value: str) -> str:
    """Namespaced id for a taxonomy hub node, e.g. ``hub:statute:CWA``."""
    return f"{HUB_ID_PREFIX}{group}:{value}"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


# --- Tokenization ------------------------------------------------------------

# Deliberately small and closed. A big stopword list would need the same
# maintenance discipline as a taxonomy for no ranking gain — the df < 60%
# pruning below already removes the domain words ("water", "data", "center")
# that would otherwise dominate every vector.
STOPWORDS = frozenset(
    """
    about after all also among an and any are as at be because been before
    being between both but by can could did do does during each either for
    from further had has have he her him his how however if in into is it
    its just many may more most much must neither no not of on one only or
    other our out over said same she should so some still such than that the
    their them then there these they this those through to under until up
    upon very was we well were what when where which while who will with
    within without would you your
    """.split()
)

# Everything outside [A-Za-z0-9] becomes a separator BEFORE lowercasing, so the
# rule is pure ASCII and cannot diverge between Python's str.lower() and
# JavaScript's toLowerCase() on exotic input (§, curly quotes, accents).
_TOKEN_SPLIT_RE = re.compile(r"[^A-Za-z0-9]+")

# Single characters are noise ("§ 404" → "404", "U.S." → "u", "s").
MIN_TOKEN_LEN = 2


def tokenize(text: str) -> list[str]:
    """Unigrams plus adjacent bigrams, in the order they occur.

    Bigrams are formed from *surviving* unigrams, not from the raw stream, so
    "reporting of water withdrawals" yields "reporting water" — the phrase a
    reader would search for — rather than the stopword pair.
    """
    words = [
        w
        for w in _TOKEN_SPLIT_RE.sub(" ", str(text or "")).lower().split()
        if len(w) >= MIN_TOKEN_LEN and w not in STOPWORDS
    ]
    return words + [f"{a} {b}" for a, b in zip(words, words[1:])]


# --- Index shape -------------------------------------------------------------

# Tuned against the blob budget in the spec (~600 KB). 60 tokens is roughly the
# top third of a typical record's vector and costs ~2% of retrieval quality on
# the paste-a-paragraph cases; the tail is overwhelmingly hapax bigrams that
# only ever match themselves.
MAX_TOKENS_PER_RECORD = 60
# A token in more than 60% of records separates nothing — it is a stopword the
# corpus invented ("water", "data center", "permit").
DF_CUTOFF = 0.6
WEIGHT_DECIMALS = 3


def _records_by_kind() -> dict[str, dict[str, dict]]:
    """``{kind: {record_id: record}}`` — the payloads behind the registry ids."""
    solutions: dict[str, dict] = {}
    for cat in load_water_solutions().get("categories", []):
        for sol in cat.get("solutions", []):
            if sol.get("id"):
                # Category lives on the wrapper, not the solution; carry it in
                # so the node attrs do not need the wrapper again.
                solutions[sol["id"]] = {**sol, "_category": cat.get("id", "")}
    return {
        "instrument": {
            b["bill_id"]: b for b in load_legislation().get("bills", []) if b.get("bill_id")
        },
        "reading": {
            r["reading_id"]: r
            for r in load_water_authorities().get("readings", [])
            if r.get("reading_id")
        },
        "case": {
            c["case_id"]: c
            for c in load_cwa_investigations().get("cases", [])
            if c.get("case_id")
        },
        "site": {
            s["site_id"]: s
            for s in load_dc_water_conflicts().get("sites", [])
            if s.get("site_id")
        },
        "claim": {
            c["id"]: c for c in load_company_water_claims().get("claims", []) if c.get("id")
        },
        "news": {i["id"]: i for i in load_water_news().get("items", []) if i.get("id")},
        "solution": solutions,
    }


def _statutes_for(kind: str, record: dict, statute_of: dict[str, str]) -> list[str]:
    """Statute families a record touches, via the readings it cites.

    Display ordering and pill rendering stay in ``dashboard._case_statutes``;
    this only needs set membership for the family filter, so it is deliberately
    a plain lookup rather than a second copy of that function.
    """
    if kind == "reading":
        codes = {record.get("statute", "")}
    elif kind == "case":
        codes = {statute_of.get(r, "") for r in record.get("authorities") or []}
    elif kind == "site":
        codes = {
            statute_of.get(m.get("reading_id", ""), "")
            for m in record.get("applicable_readings") or []
        }
    else:
        return []
    order = {code: i for i, code in enumerate(WATER_STATUTE_ORDER)}
    return sorted((c for c in codes if c), key=lambda c: (order.get(c, 99), c))


def _node_attrs(kind: str, record: dict, statute_of: dict[str, str]) -> dict:
    """The grouping fields the Explore filters and the graph legend read.

    Only what the UI actually filters or labels by — the full record is one
    click away on its own card, and every field copied here is a field that can
    go stale in the blob.
    """
    statutes = _statutes_for(kind, record, statute_of)
    if kind == "instrument":
        return {
            "status": record.get("status", ""),
            "level": record.get("level", ""),
            "jurisdiction": record.get("jurisdiction", ""),
            "principles": sorted(
                {p.get("tag", "") for p in record.get("general_principles", []) if p.get("tag")}
            ),
        }
    if kind == "reading":
        return {"statutes": statutes, "section": record.get("section", "")}
    if kind == "case":
        return {
            "statutes": statutes,
            "category": record.get("category", ""),
            "case_type": record.get("case_type", ""),
            "year": record.get("year", ""),
        }
    if kind == "site":
        return {
            "statutes": statutes,
            "issue_types": list(record.get("issue_types", [])),
            "location": record.get("location", ""),
        }
    if kind == "claim":
        return {
            "company": record.get("company_slug", ""),
            "delivered": (record.get("delivered") or {}).get("status", ""),
        }
    if kind == "news":
        return {"tags": list(record.get("tags", [])), "date": record.get("date", "")}
    if kind == "solution":
        return {
            "category": record.get("_category", ""),
            "status": record.get("status", ""),
        }
    return {}


def _record_text(kind: str, record: dict) -> str:
    """The prose a reader would call this record's substance.

    Ids, urls and dates are left out on purpose: they match on nothing a person
    would paste, and a url tokenizes into a dozen junk unigrams that crowd real
    terms out of the per-record top-60.
    """
    if kind == "instrument":
        fields = ["bill_id", "title", "summary", "status_detail", "jurisdiction"]
    elif kind == "reading":
        fields = ["name", "section", "what_it_covers", "dc_applicability"]
    elif kind == "case":
        fields = [
            "respondent",
            "cwa_section",
            "cwa_instrument",
            "violation_summary",
            "outcome",
            "takeaway",
            "cwa_pathway",
        ]
    elif kind == "site":
        fields = [
            "site",
            "operator",
            "location",
            "issue_summary",
            "pushback_summary",
            "status_2026",
        ]
    elif kind == "claim":
        parts = [record.get("statement", ""), record.get("company_slug", "").replace("-", " ")]
        parts.append((record.get("delivered") or {}).get("summary", ""))
        return " ".join(p for p in parts if p)
    elif kind == "news":
        fields = ["title", "summary", "outlet"]
    elif kind == "solution":
        fields = ["title", "description", "example", "actor"]
    else:
        fields = []
    return " ".join(str(record.get(f) or "") for f in fields)


def build_graph() -> dict:
    """``{"nodes": [...], "edges": [...]}`` over every curated record.

    Nodes carry the registry's ``tab``/``anchor`` verbatim, which is what lets
    a search result open the exact card on the owning tab — the registry's
    whole point, reused rather than re-derived.

    Edges are directed as declared, but the UI walks them undirected: "what
    connects to this" does not care which side wrote the id down.
    """
    reg = build_registry()
    by_kind = _records_by_kind()
    statute_of = {
        r["reading_id"]: r.get("statute", "")
        for r in load_water_authorities().get("readings", [])
        if r.get("reading_id")
    }

    nodes = [
        {
            "id": record_id,
            "kind": ref.kind,
            "label": ref.label,
            "tab": ref.tab,
            "anchor": ref.anchor,
            "attrs": _node_attrs(ref.kind, by_kind[ref.kind].get(record_id, {}), statute_of),
        }
        for record_id, ref in reg.items()
    ]

    # A dangling edge is a test failure (refdata.integrity), never a render
    # failure: drawing a line to a node that does not exist would crash the
    # layout, so the graph drops it and lets the test be the thing that shouts.
    seen: set[tuple[str, str, str]] = set()
    edges = []
    for source, target, kind in iter_edges():
        key = (source, target, kind)
        if source in reg and target in reg and key not in seen:
            seen.add(key)
            edges.append({"source": source, "target": target, "kind": kind})

    hub_nodes, hub_edges = _taxonomy_hubs(by_kind)
    return {"nodes": nodes + hub_nodes, "edges": edges + hub_edges}


def _taxonomy_hubs(by_kind: dict[str, dict[str, dict]]) -> tuple[list[dict], list[dict]]:
    """Hub nodes for the three closed taxonomies, plus the edges into them.

    A hub is created only when at least one record claims it — an empty hub is
    the graph's version of a filter chip that matches nothing.
    """
    members: dict[tuple[str, str], list[str]] = {}

    for reading_id, reading in by_kind["reading"].items():
        statute = reading.get("statute")
        if statute:
            members.setdefault(("statute", statute), []).append(reading_id)
    for case_id, case in by_kind["case"].items():
        case_type = case.get("case_type")
        if case_type:
            members.setdefault(("case-type", case_type), []).append(case_id)
    for bill_id, bill in by_kind["instrument"].items():
        for principle in sorted(
            {p.get("tag", "") for p in bill.get("general_principles", []) if p.get("tag")}
        ):
            members.setdefault(("principle", principle), []).append(bill_id)

    statute_names = load_water_authorities().get("statutes", {})
    edge_kind_of = {group: kind for kind, group in DERIVED_EDGE_KINDS.items()}
    statute_rank = {code: i for i, code in enumerate(WATER_STATUTE_ORDER)}

    def sort_key(item):
        (group, value), _ = item
        rank = statute_rank.get(value, 99) if group == "statute" else 0
        return (group, rank, value)

    nodes, edges = [], []
    for (group, value), member_ids in sorted(members.items(), key=sort_key):
        node_id = hub_id(group, value)
        if group == "statute":
            label = value
            title = statute_names.get(value, {}).get("name", value)
            # The toolkit renders one <details id="statute-CODE"> per family, so
            # a statute hub can open its own section like any record node.
            tab, anchor = "cwa", f"statute-{value}"
        elif group == "case-type":
            label = CWA_CASE_TYPE_LABELS.get(value, value)
            title = label
            tab, anchor = "", ""
        else:
            label = value
            title = LEGISLATION_PRINCIPLE_DESCRIPTIONS.get(value, value)
            tab, anchor = "", ""
        nodes.append(
            {
                "id": node_id,
                "kind": "hub",
                "label": label,
                "tab": tab,
                "anchor": anchor,
                "attrs": {
                    "hub_group": group,
                    "value": value,
                    "title": title,
                    "count": len(member_ids),
                    "statutes": [value] if group == "statute" else [],
                },
            }
        )
        edges += [
            {
                "source": member_id,
                "target": node_id,
                "kind": edge_kind_of[group],
                "derived": True,
            }
            for member_id in sorted(member_ids)
        ]
    return nodes, edges


def build_search_index() -> dict:
    """TF-IDF vectors over every record, keyed by the tokens :func:`tokenize` emits.

    Returns ``{"n_docs", "df": {token: count}, "docs": {record_id: {token:
    weight}}}``. Weights are ``tf × log(n_docs / df)``, the surviving top
    :data:`MAX_TOKENS_PER_RECORD` of each record L2-normalized so a long case
    narrative cannot outrank a short news item on length alone.

    ``df`` ships rather than ``idf`` because the browser has to weight the
    *query* the same way for the cosine to mean anything, and integer counts
    survive JSON at a third of the bytes of the logarithms they imply.

    Deterministic throughout — sorted record ids, sorted tokens, ties in the
    top-N broken by token — so a rebuild with unchanged data is a no-op diff.
    """
    by_kind = _records_by_kind()
    reg = build_registry()

    counts: dict[str, Counter] = {}
    for record_id, ref in reg.items():
        record = by_kind[ref.kind].get(record_id, {})
        text = f"{ref.label} {_record_text(ref.kind, record)}"
        counts[record_id] = Counter(tokenize(text))

    n_docs = len(counts) or 1
    df = Counter()
    for c in counts.values():
        df.update(c.keys())
    max_df = DF_CUTOFF * n_docs
    idf = {token: math.log(n_docs / d) for token, d in df.items() if d < max_df}

    docs: dict[str, dict[str, float]] = {}
    for record_id in sorted(counts):
        weighted = {
            token: tf * idf[token] for token, tf in counts[record_id].items() if token in idf
        }
        top = sorted(weighted.items(), key=lambda kv: (-kv[1], kv[0]))[:MAX_TOKENS_PER_RECORD]
        norm = math.sqrt(sum(w * w for _, w in top)) or 1.0
        kept = {}
        for token, weight in sorted(top):
            rounded = round(weight / norm, WEIGHT_DECIMALS)
            if rounded:  # a weight that rounds to zero scores nothing
                kept[token] = rounded
        docs[record_id] = kept

    kept_tokens = {token for vec in docs.values() for token in vec}
    return {
        "n_docs": n_docs,
        "df": {token: df[token] for token in sorted(kept_tokens)},
        "docs": docs,
    }


# Weights ride the wire as integers: "874" instead of "0.874" over ~19k values
# is ~40 KB, and the third decimal is already the rounding floor above.
WEIGHT_SCALE = 10**WEIGHT_DECIMALS


def build_payload() -> dict:
    """The single blob the Explore tab embeds: graph + index + tokenizer rules.

    This is the **wire format**, not the model. :func:`build_graph` and
    :func:`build_search_index` return the readable shapes that tests assert
    against; here edges become index triples into ``nodes`` and vectors become
    index/int-weight arrays into ``vocab``, which is the difference between a
    ~740 KB blob and a ~580 KB one. Every id string in an 919-edge list is
    written twice otherwise, and every bigram once per record that carries it.

    The tokenizer constants travel with the data so the page's JavaScript is
    generated from them instead of restating them — the only way a parity bug
    between the two tokenizers becomes impossible rather than merely tested.
    """
    graph = build_graph()
    nodes = graph["nodes"]
    node_index = {node["id"]: i for i, node in enumerate(nodes)}

    edge_kinds = sorted({e["kind"] for e in graph["edges"]})
    kind_index = {kind: i for i, kind in enumerate(edge_kinds)}
    edges = [
        [node_index[e["source"]], node_index[e["target"]], kind_index[e["kind"]]]
        for e in graph["edges"]
    ]

    index = build_search_index()
    vocab = sorted(index["df"])
    position = {token: i for i, token in enumerate(vocab)}
    docs = {}
    for record_id, vec in index["docs"].items():
        if not vec:
            continue
        docs[str(node_index[record_id])] = {
            "t": [position[token] for token in vec],
            "w": [round(weight * WEIGHT_SCALE) for weight in vec.values()],
        }

    return {
        "nodes": nodes,
        "edge_kinds": edge_kinds,
        "edge_kind_labels": [EDGE_KIND_LABELS.get(k, k) for k in edge_kinds],
        "edges": edges,
        "derived_edge_kinds": sorted(DERIVED_EDGE_KINDS),
        "vocab": vocab,
        "df": [index["df"][token] for token in vocab],
        "n_docs": index["n_docs"],
        "docs": docs,
        "weight_scale": WEIGHT_SCALE,
        "kind_colors": KIND_COLORS,
        "kind_labels": KIND_LABELS,
        "stopwords": sorted(STOPWORDS),
        "min_token_len": MIN_TOKEN_LEN,
    }


def payload_json() -> str:
    """The blob as it is embedded, so the size guard measures the real bytes.

    ``</`` is escaped because the blob sits in a ``<script>`` element and a
    record quoting ``</script>`` would otherwise end it early.
    """
    return json.dumps(build_payload(), separators=(",", ":")).replace("</", "<\\/")
