"""Statute paths: from what a data center is doing to the law that reaches it.

WHY THIS EXISTS
---------------
The Water Cases toolkit answers "what does §404 cover?" — organized by
statute, the lawyer's axis. The question readers actually arrive with runs the
other way: *the campus is about to pump groundwater (or fill a wetland, or
restart a power plant) — which laws touch that, has any of them ever worked,
and where is it being tried right now?* Answering it used to mean reading 51
reading cards, following their example-case links, then searching the
conflict sites for the same reading id.

Every piece of that chain is already declared in the data:

- ``reading.dc_activities``  — which activities trigger the reading (closed
  taxonomy :data:`refdata.taxonomies.DC_ACTIVITY_LABELS`), and
  ``reading.dc_trigger`` — the one-line condition, condensed from the
  reading's own ``dc_applicability`` so no new legal claim enters here;
- ``reading.example_case_ids`` — the curated precedents that show it working;
- ``case.authorities`` — every other case in the record that invoked it;
- ``site.applicable_readings`` — the tracked conflict sites where it is in
  play, each with a one-line "how" written for that site.

This module joins them into one structure, once, so the static page, the
Streamlit app and llms.txt render the same paths — and nothing here is a new
claim about the law: a path exists only where the datasets already say so.

Purity rule: no ``streamlit`` import.
"""

from __future__ import annotations

import re

from refdata.loaders import (
    load_cwa_investigations,
    load_dc_water_conflicts,
    load_water_authorities,
)
from refdata.registry import case_caption
from refdata.taxonomies import (
    DC_ACTIVITY_DESCRIPTIONS,
    DC_ACTIVITY_LABELS,
    WATER_STATUTE_COLORS,
    WATER_STATUTE_ORDER,
)

# How many of each link kind a path row shows before summarizing the rest as
# a count. The full lists are one click away on the reading card; a row that
# names eleven sites stops being a path and becomes a table.
MAX_PRECEDENTS = 3
MAX_SITES = 4

def path_anchor(activity: str, reading_id: str) -> str:
    """In-page id of one path row. A reading appears once per activity that
    triggers it, so the activity is part of the id."""
    return f"path-{activity}-{reading_id}"


def activity_anchor(activity: str) -> str:
    """In-page id of an activity's group of paths."""
    return f"paths-{activity}"


def _statute_rank(code: str) -> int:
    try:
        return WATER_STATUTE_ORDER.index(code)
    except ValueError:
        return len(WATER_STATUTE_ORDER)


def build_statute_paths() -> list[dict]:
    """One entry per activity, in taxonomy order, each carrying its paths.

    Shape::

        [{"activity", "label", "description", "anchor",
          "n_families", "n_sites",
          "paths": [{"reading_id", "name", "section", "statute", "statute_name",
                     "color", "when", "role", "anchor",
                     "precedents": [{"case_id", "caption", "instrument"}],
                     "more_cases": int,
                     "sites": [{"site_id", "label", "how"}],
                     "more_sites": int,
                     "ruled_out": [{"site_id", "label", "how"}]}]}]

    ``precedents`` are the reading's curated ``example_case_ids`` first, then
    any other case whose ``authorities`` cite the reading — curated before
    derived, because the curator chose those as the clearest demonstrations.
    An activity no reading claims is omitted rather than rendered empty.
    """
    authorities = load_water_authorities()
    statutes = authorities.get("statutes", {})
    readings = [r for r in authorities.get("readings", []) if r.get("reading_id")]

    cases = {
        c["case_id"]: c for c in load_cwa_investigations().get("cases", []) if c.get("case_id")
    }
    citing: dict[str, list[str]] = {}
    for case_id, case in cases.items():
        for reading_id in case.get("authorities") or []:
            citing.setdefault(reading_id, []).append(case_id)

    # A mapping with ``reaches: false`` is a site where the curator checked the
    # reading and found it does NOT apply (no reservation over the Memphis
    # Sand, no groundwater trust in Arizona). That is a finding about the path
    # — where it dead-ends — so it rides separately instead of being dropped or,
    # worse, listed as a place the law is "in play".
    sites_for: dict[str, list[dict]] = {}
    ruled_out_for: dict[str, list[dict]] = {}
    for site in load_dc_water_conflicts().get("sites", []):
        for mapping in site.get("applicable_readings") or []:
            reading_id = mapping.get("reading_id")
            if reading_id and site.get("site_id"):
                bucket = ruled_out_for if mapping.get("reaches") is False else sites_for
                bucket.setdefault(reading_id, []).append(
                    {
                        "site_id": site["site_id"],
                        "label": site.get("site") or site["site_id"],
                        "how": " ".join(str(mapping.get("how") or "").split()),
                    }
                )

    def precedents_for(reading: dict) -> tuple[list[dict], int]:
        curated = [cid for cid in reading.get("example_case_ids") or [] if cid in cases]
        derived = sorted(
            (cid for cid in citing.get(reading["reading_id"], []) if cid not in curated),
            # Newest first: the most recent application of a reading is the
            # one a reader is likeliest to be able to cite.
            key=lambda cid: (-_year_end(cases[cid].get("year", "")), cid),
        )
        ordered = curated + derived
        shown = [
            {
                "case_id": cid,
                "caption": case_caption(cid),
                "instrument": str(cases[cid].get("cwa_instrument") or ""),
            }
            for cid in ordered[:MAX_PRECEDENTS]
        ]
        return shown, max(0, len(ordered) - MAX_PRECEDENTS)

    out = []
    for activity, label in DC_ACTIVITY_LABELS.items():
        members = [r for r in readings if activity in (r.get("dc_activities") or [])]
        if not members:
            continue
        members.sort(key=lambda r: (_statute_rank(r.get("statute", "")), r["reading_id"]))
        paths = []
        site_ids: set[str] = set()
        for reading in members:
            code = reading.get("statute", "")
            shown, more = precedents_for(reading)
            sites = sites_for.get(reading["reading_id"], [])
            site_ids.update(s["site_id"] for s in sites)
            paths.append(
                {
                    "reading_id": reading["reading_id"],
                    "name": reading.get("name") or reading["reading_id"],
                    "section": reading.get("section", ""),
                    "statute": code,
                    "statute_name": statutes.get(code, {}).get("name", code),
                    "color": WATER_STATUTE_COLORS.get(code, "#6b7280"),
                    "when": reading.get("dc_trigger", ""),
                    "role": reading.get("dc_role", "hook"),
                    "anchor": path_anchor(activity, reading["reading_id"]),
                    "precedents": shown,
                    "more_cases": more,
                    "sites": sites[:MAX_SITES],
                    "more_sites": max(0, len(sites) - MAX_SITES),
                    "ruled_out": ruled_out_for.get(reading["reading_id"], []),
                }
            )
        out.append(
            {
                "activity": activity,
                "label": label,
                "description": DC_ACTIVITY_DESCRIPTIONS.get(activity, ""),
                "anchor": activity_anchor(activity),
                "n_families": len({p["statute"] for p in paths}),
                "n_sites": len(site_ids),
                "paths": paths,
            }
        )
    return out


def _year_end(year: str) -> int:
    """Last four-digit year in a ``YYYY`` / ``YYYY-YYYY`` string, else 0."""
    years = re.findall(r"\d{4}", str(year or ""))
    return int(years[-1]) if years else 0
