"""Static-site generator for the Data Center Water Use Tracker dashboard.

WHY THIS EXISTS
---------------
The live site previously ran the Streamlit app inside Pyodide/WASM (stlite),
which downloads ~15 MB of Python + Streamlit + Plotly and boots an interpreter
in the browser before the first paint — a 25–40 s cold start. The data is
static (curated JSON + scraper output) and the UI is mostly HTML that the
Streamlit app already builds as strings, so there is no reason to ship a Python
runtime to the browser at all.

This script pre-renders the whole dashboard to a single self-contained static
``pages/index.html`` at build time, running natively (fast) in CI. It REUSES
the dashboard's pure HTML builders and data constants (``dashboard._build_*``,
``dashboard.CONTEXT_DATA``, …) so there is one source of truth: edit the data or
a card builder and both the local Streamlit app and this static site change
together. The only client-side dependency is Chart.js (SRI-pinned) for the two
quantitative charts; everything else is pre-rendered HTML + a little vanilla JS
for tabs, filters, and collapsible panels.

Run: ``python build_site.py`` → writes ``pages/index.html``.
"""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import markdown as md_lib
import pandas as pd

import dashboard as dash
from utils.device import _RESPONSIVE_CSS

BASE_DIR = Path(__file__).parent
OUT_PATH = BASE_DIR / "pages" / "index.html"

# The card/timeline/context component CSS that the dashboard's _build_*_html
# builders target (.bill-card, .cwa-*, .context-card, .explainer-card,
# .timeline-*, .range-bar, …) lives in utils/device.py and is shared verbatim
# so the static cards match the Streamlit app exactly. Its Streamlit-only
# selectors (.stApp, [data-testid=…], sidebar media queries) are simply inert
# no-ops in the static page.
COMPONENT_CSS = _RESPONSIVE_CSS.replace("<style>", "").replace("</style>", "")

# Chart.js 4.4.6 UMD, pinned + SRI (sha384). Regenerate with:
#   curl -sL <url> | openssl dgst -sha384 -binary | openssl base64 -A
# and verify the hash twice (a partial download yields a wrong hash that fails
# closed). See CLAUDE.md §10 (Security & Supply-Chain Hygiene).
CHARTJS_URL = "https://cdn.jsdelivr.net/npm/chart.js@4.4.6/dist/chart.umd.min.js"
CHARTJS_SRI = "sha384-Sse/HDqcypGpyTDpvZOJNnG0TT3feGQUkF9H+mnRvic+LjR+K1NhTt8f51KIQ3v3"

C = dash.COLORS

esc = html.escape


def md(text: str) -> str:
    """Render a small markdown blob to HTML (bold, links, lists, blockquotes)."""
    return md_lib.markdown(text, extensions=["extra", "sane_lists"])


# --------------------------------------------------------------------------
# Legislation tab
# --------------------------------------------------------------------------


def _principle_slug(tag: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")


def build_legislation_tab() -> str:
    payload = dash.load_legislation()
    bills = payload.get("bills", [])
    sorted_bills = sorted(
        bills,
        key=lambda b: (
            dash.LEGISLATION_STATUS_ORDER.get(b.get("status"), 9),
            b.get("jurisdiction", ""),
        ),
    )
    themes_html = dash._build_legislation_themes_html(bills)
    # Wrap each card with machine-readable attrs for client-side filtering.
    cards = "".join(
        f'<div class="leg-bill" data-status="{esc(b.get("status",""))}" '
        f'data-level="{esc(b.get("level",""))}" '
        f'data-scope="{esc(" ".join(b.get("scope", [])))}" '
        f'data-principles="{esc(" ".join(sorted({_principle_slug(p.get("tag","")) for p in b.get("general_principles", [])})))}" '
        f'data-instrument="{esc(b.get("instrument_type", "bill"))}">'
        f'{dash._build_bill_card_html(b)}</div>'
        for b in sorted_bills
    )
    last_updated = payload.get("last_updated") or "unknown"
    principles_panel = dash._build_principles_summary_html(bills)
    explainer = md(dash._legislation_explainer_md())

    tag_rows = dash._legislation_principles_summary(bills)
    principle_boxes = "".join(
        f'<label class="chip-check"><input type="checkbox" class="leg-principle" '
        f'value="{_principle_slug(r["tag"])}" checked> {esc(r["tag"])}</label>'
        for r in tag_rows
    )
    status_boxes = "".join(
        f'<label class="chip-check"><input type="checkbox" class="leg-status" '
        f'value="{k}" checked> {esc(v)}</label>'
        for k, v in dash.LEGISLATION_STATUS_LABELS.items()
        if k != "unknown"
    )
    level_boxes = "".join(
        f'<label class="chip-check"><input type="checkbox" class="leg-level" '
        f'value="{k}" checked> {esc(v)}</label>'
        for k, v in dash.LEGISLATION_LEVEL_LABELS.items()
    )
    scope_boxes = "".join(
        f'<label class="chip-check"><input type="checkbox" class="leg-scope" '
        f'value="{k}" checked> {esc(v)}</label>'
        for k, v in dash.LEGISLATION_SCOPE_LABELS.items()
    )
    instrument_counts: dict[str, int] = {}
    for b in bills:
        itype = b.get("instrument_type", "bill")
        instrument_counts[itype] = instrument_counts.get(itype, 0) + 1
    instrument_boxes = "".join(
        f'<label class="chip-check"><input type="checkbox" class="leg-instrument" '
        f'value="{k}" checked> {esc(dash.INSTRUMENT_TYPE_LABELS[k])} '
        f'({instrument_counts[k]})</label>'
        for k in dash.INSTRUMENT_TYPE_LABELS
        if k in instrument_counts
    )
    status_labels_json = json.dumps(dash.LEGISLATION_STATUS_LABELS)
    status_order_json = json.dumps(dash.LEGISLATION_STATUS_ORDER)

    return f"""
<section class="panel">
  <h2>Data Center Water Legislation Tracker</h2>
  <p class="lead">State, federal, and local action on data center water (and energy)
  disclosure — bills, signed laws, agency rulemakings, and major zoning ordinances.
  Enacted laws are the next mandatory data sources to come online.</p>
  {themes_html}
  {principles_panel}
  <details class="lazy">
    <summary>How to read this tracker — statuses, levels, principles</summary>
    <div class="explainer-md">{explainer}</div>
  </details>
  <div class="cwa-filters">
    <span class="filter-label">Principle:</span>
    <div class="cwa-types">{principle_boxes}</div>
  </div>
  <div class="cwa-filters">
    <span class="filter-label">Status:</span>{status_boxes}
    <span class="filter-label">Level:</span>{level_boxes}
    <span class="filter-label">Scope:</span>{scope_boxes}
  </div>
  <div class="cwa-filters">
    <span class="filter-label">Instrument:</span>
    <div class="cwa-types">{instrument_boxes}</div>
  </div>
  <p class="count-line" id="leg-count"></p>
  <div id="leg-bills">{cards}</div>
  <p class="src-note">Dataset last updated {esc(last_updated)}. Verification status for
  each entry is tracked in the underlying JSON; treat any not flagged verified=true
  there as secondary-sourced.</p>
</section>
<script>
  window.LEG_STATUS_LABELS = {status_labels_json};
  window.LEG_STATUS_ORDER = {status_order_json};
  window.LEG_TOTAL = {len(bills)};
</script>

<details class="lazy">
  <summary>Show Policy &amp; Disclosure Timeline</summary>
  {build_timeline()}
</details>
"""


def build_timeline() -> str:
    category_colors = {
        "policy": C["danger"], "data": C["primary"],
        "research": C["success"], "legal": C["warning"],
    }
    category_labels = {
        "policy": "Policy", "data": "Data Release",
        "research": "Research", "legal": "Legal",
    }
    events = sorted(dash.TIMELINE_EVENTS, key=lambda e: e["date"])
    rows = []
    for e in events:
        color = category_colors.get(e["category"], C["text"])
        label = category_labels.get(e["category"], e["category"].title())
        rows.append(
            f'<div class="timeline-event">'
            f'<div class="timeline-date">{esc(str(e["year"]))}</div>'
            f'<div class="timeline-body">'
            f'<span class="timeline-badge" style="background:{color}">{esc(label)}</span>'
            f'<strong>{esc(e["label"])}</strong><br>'
            f'<span class="timeline-detail">{esc(e["detail"])}</span>'
            f'</div></div>'
        )
    return (
        '<section class="panel"><h3>Policy &amp; Disclosure Timeline</h3>'
        '<p class="lead">Key events shaping data center water transparency — '
        'the data landscape is changing rapidly.</p>' + "".join(rows) + "</section>"
    )


def build_company_claims() -> str:
    payload = dash.load_company_water_claims()
    claims = payload.get("claims", [])
    companies = payload.get("companies", {})
    live_url = payload.get("live_dashboard", "")
    delivered_count = sum(1 for c in claims if c.get("delivered"))
    company_count = len({c.get("company_slug") for c in claims})

    intro = md(
        "Verbatim water-related commitments from data-center operators, mirrored "
        f"from [Data Center Community Benefits]({live_url}). Each quote links to its "
        "first-party source. Where independent assessment has been captured, a "
        "**delivered-vs-promised** badge appears beneath."
    )

    parts = [
        '<section class="panel">',
        intro,
        f'<p class="count-line"><strong>{len(claims)} claims</strong> · '
        f'{company_count} companies · {delivered_count} delivered-vs-promised '
        'assessments</p>',
    ]
    rendered: list[str] = []
    # Labels come from the shared taxonomy; only the CSS treatment is local.
    # This map previously duplicated the labels, so DELIVERED_STATUS_LABELS was
    # "shared" in name only and the two surfaces could drift on a rename —
    # the exact failure the constant was introduced to prevent.
    status_css = {
        "delivered": "delivered",
        "partial": "partial",
        "contested": "partial",
        "litigated": "shortfall",
        "shortfall": "shortfall",
    }
    status_map = {
        k: (dash.DELIVERED_STATUS_LABELS[k], status_css.get(k, "info"))
        for k in dash.DELIVERED_STATUS_LABELS
    }
    for claim in claims:
        slug = claim.get("company_slug", "unknown")
        if slug not in rendered:
            rendered.append(slug)
            parts.append(f'<h4 class="claim-company">{esc(companies.get(slug, slug))}</h4>')

        statement = esc(claim.get("statement", ""))
        src_url = claim.get("source_url", "")
        src_title = esc(claim.get("source_title", "source"))
        date_str = esc(str(claim.get("published_at") or claim.get("captured_at") or ""))
        project_id = claim.get("project_id")

        cap = []
        if src_url:
            cap.append(f'<a href="{esc(src_url)}" target="_blank" rel="noopener">{src_title}</a>')
        elif src_title:
            cap.append(src_title)
        if date_str:
            cap.append(date_str)
        if project_id:
            cap.append(f'Project: <code>{esc(str(project_id))}</code>')
        caption = f'<div class="claim-meta">{" · ".join(cap)}</div>' if cap else ""

        # Shared with the Streamlit card so the two surfaces cannot disagree
        # about a claim's lifecycle (dashboard._build_claim_lifecycle_html).
        chip_row = dash._build_claim_lifecycle_html(claim, companies)

        box = ""
        delivered = claim.get("delivered")
        if delivered:
            status = str(delivered.get("status", "")).lower()
            label, cls = status_map.get(status, (status.title() or "Unknown", "info"))
            d_summary = esc(delivered.get("summary", ""))
            d_url = delivered.get("source_url", "")
            d_title = esc(delivered.get("source_title", "assessment"))
            d_assessed = esc(delivered.get("assessed_at", ""))
            link = (
                f'<a href="{esc(d_url)}" target="_blank" rel="noopener">Assessment: {d_title}</a>'
                if d_url else f"Assessment: {d_title}"
            )
            box = (
                f'<div class="claim-status claim-status-{cls}">'
                f'<strong>Delivered vs. promised: {esc(label)}</strong> '
                f'<span class="claim-assessed">(assessed {d_assessed})</span>'
                f'<div class="claim-status-summary">{d_summary}</div>'
                f'<div class="claim-status-link">{link}</div>'
                f'</div>'
            )

        parts.append(
            f'<div class="claim-card" id="claim-{esc(claim.get("id", ""))}">'
            f'<p class="claim-quote">“{statement}”</p>'
            f'{caption}{chip_row}{box}</div>'
        )

    parts.append(
        f'<p class="src-note">Snapshotted from '
        f'{esc(payload.get("source_repo", "datacentercommunitybenefits"))} on '
        f'{esc(payload.get("last_updated", "unknown"))}. Quotes are verbatim — they '
        'reflect what each company has <em>claimed</em>, not independently verified '
        'water usage. See the Transparency Scorecard for what is actually measurable.</p>'
        '</section>'
    )
    return "".join(parts)


# --------------------------------------------------------------------------
# CWA tab
# --------------------------------------------------------------------------


def build_issues_claims_tab() -> str:
    """The Issues & Claims tab: what the problems are, and what operators say.

    Spec A3. This story used to be split across three places — conflict sites
    were Part 4 of a legal-record tab, operator claims were a collapsed
    disclosure at the bottom of Legislation, and nothing joined them. A reader
    asking "what is the problem here, and what does the company say about it?"
    had to know to look in two tabs and then do the join themselves.

    Section order answers that question in one pass: what kinds of problem
    exist → where → what the operator promised → which promises are contested.
    """
    conflicts_payload = dash.load_dc_water_conflicts()
    conflict_sites = conflicts_payload.get("sites", [])
    conflicts_updated = conflicts_payload.get("last_updated") or "unknown"

    authorities_payload = dash.load_water_authorities()
    readings_by_id = dash._readings_by_id(authorities_payload)
    cases = dash.load_cwa_investigations().get("cases", [])
    all_ids = {c.get("case_id") for c in cases}
    cases_by_id = {c["case_id"]: c for c in cases}

    claims_payload = dash.load_company_water_claims()
    claims = claims_payload.get("claims", [])
    companies = claims_payload.get("companies", {})
    claims_ctx = (claims, companies)

    summary_strip = dash._issue_type_summary_html(conflict_sites)
    doctrine_matrix = dash._build_site_doctrine_matrix_html(conflict_sites, readings_by_id)
    site_cards = "".join(
        dash._build_conflict_site_html(s, readings_by_id, all_ids, cases_by_id, claims_ctx)
        for s in conflict_sites
    )

    issue_counts: dict[str, int] = {}
    for s in conflict_sites:
        for t in s.get("issue_types", []):
            issue_counts[t] = issue_counts.get(t, 0) + 1
    issue_boxes = "".join(
        f'<label class="chip-check" title="{esc(dash.ISSUE_TYPE_DESCRIPTIONS[k])}">'
        f'<input type="checkbox" class="dc-issue" value="{esc(k)}" checked> '
        f'{esc(dash.ISSUE_TYPE_LABELS[k])} ({issue_counts[k]})</label>'
        # Unknown tags are skipped rather than raising: a schema test blocks
        # them from landing, but a render must not be the thing that fails.
        for k in sorted(issue_counts, key=lambda k: (-issue_counts[k], k))
        if k in dash.ISSUE_TYPE_LABELS
    )

    # Claims whose truth is now before a court or regulator. Small on purpose:
    # one entry today, and the callout exists so a second is impossible to miss.
    challenged = [c for c in claims if c.get("challenged_in")]
    challenge_rows = "".join(
        f'<li><strong>{esc(companies.get(c.get("company_slug", ""), ""))}</strong> — '
        f'&ldquo;{esc(c.get("statement", "")[:150])}&rdquo; '
        + " ".join(
            f'<a href="#{esc(ref.anchor)}">{esc(ref.label)}</a>'
            for ref in (dash.resolve_ref(cid) for cid in c["challenged_in"])
            if ref
        )
        + "</li>"
        for c in challenged
    )
    challenge_block = (
        '<div class="context-card"><h4>Claims currently under legal challenge</h4>'
        f"<ul>{challenge_rows}</ul>"
        "<p class=\"source-note\">Listed because the claim is being tested in a "
        "forum, not because it has been found false.</p></div>"
        if challenged
        else ""
    )

    return f"""
<section class="panel">
  <h2>Issues &amp; Claims — What Goes Wrong, and What Operators Say</h2>
  <p class="lead">Every tracked data-center site with a documented water problem or
  community pushback, classified by the kind of problem it is and mapped to the legal
  readings that could reach it — shown alongside the operating company's own public
  water claims, so the promise and the record sit on the same card.</p>

  {summary_strip}

  <h3>Sites with reported water issues or pushback ({len(conflict_sites)})</h3>
  <h4 class="solution-cat-header">Which doctrines are in play where</h4>
  {doctrine_matrix}
  <div class="cwa-filters">
    <span class="filter-label">Issue type:</span>
    <div class="cwa-types">{issue_boxes}</div>
  </div>
  <p class="count-line" id="conflict-count"></p>
  <div id="dc-conflicts">{site_cards}</div>
  <p class="src-note">Site roster last updated {esc(conflicts_updated)}.</p>

  <h3>Operator water claims ({len(claims)})</h3>
  {challenge_block}
  {build_company_claims()}
</section>
"""


def build_cwa_tab() -> str:
    payload = dash.load_cwa_investigations()
    cases = payload.get("cases", [])
    authorities_payload = dash.load_water_authorities()
    readings_by_id = dash._readings_by_id(authorities_payload)
    historical = [c for c in cases if c.get("display_section", "historical") == "historical"]
    potential = [c for c in cases if c.get("display_section") == "potential"]
    stats = dash._cwa_datacenter_insights(historical)
    total = stats["total"]
    breadth = dash._cwa_statute_breadth_insight(cases, readings_by_id)
    last_updated = payload.get("last_updated") or "unknown"

    insights = ""
    if total:
        breadth_li = ""
        if breadth["total"]:
            breadth_li = f"""
    <li><strong>Look beyond the CWA.</strong> Of {breadth['total']} data-center and adjacent
      water fights in this record, {breadth['sdwa']} carry an SDWA reading and {breadth['no_cwa']}
      have no CWA angle at all — including the Amazon Boardman settlement above, which resolved
      under state tort law and SDWA/RCRA, not the Clean Water Act. Aquifer depletion, well
      failures, and public-water-system strain are consistently an SDWA story, not a CWA one.</li>"""
        # Collapsed by default (2026-07-07): this was the largest always-visible
        # block between the tab title and the Part 1-4 sub-tabs.
        insights = f"""
<details class="lazy">
  <summary>What this record tells data centers</summary>
  <div class="insights">
  <ul>
    <li><strong>The permittee shield.</strong> {stats['contractor_permittee']} of {total}
      resolved data-center enforcement cases name a construction contractor or subcontractor —
      not the hyperscaler — as the party on the permit. Operators routinely sit one entity
      removed from the permittee, which is why direct enforcement against them is thin.</li>
    <li><strong>CWA risk is front-loaded into construction.</strong> Construction stormwater,
      sediment, and erosion under the §402 Construction General Permit is the most common
      touchpoint — it appears in {stats['construction_stormwater']} of {total} historical cases,
      far more than operational cooling-water discharge.</li>
    <li><strong>The liability frontier is moving.</strong> The 2026 Amazon Boardman settlement
      ($20.5M, Oregon nitrate) is the first eight-figure direct-hyperscaler water settlement —
      pushing exposure beyond stormwater into groundwater and nutrient contamination.</li>
    <li><strong>Why this tracker watches the WWTP, not the data center.</strong> Cooling-water
      blowdown goes to the municipal sewer, so the operational CWA exposure rides on the
      <em>receiving</em> treatment plant's NPDES permit — the very permits this project tracks
      via EPA ECHO. Watch the POTW's compliance status, not the data center's near-empty
      stormwater permit.</li>{breadth_li}
  </ul>
  </div>
</details>"""

    theories = dash._build_cwa_theories_html(dash.CWA_APPLICATION_THEORIES)
    doctrine_theories = dash._build_cwa_theories_html(dash.DOCTRINE_APPLICATION_THEORIES)
    explainer = md(dash._cwa_statute_explainer_md())

    # Section 1: historical cases — filter checkboxes (project type + category).
    # Adjacent cases all moved to section 2, so filters cover datacenter/industrial/precedent.
    hist_cats = sorted(
        {c.get("category") for c in historical if c.get("category")},
        key=lambda k: dash.CWA_CATEGORY_ORDER.get(k, 9),
    )
    # Primary axis: project type (what kind of water issue).
    type_boxes = "".join(
        f'<label class="chip-check"><input type="checkbox" class="cwa-type" '
        f'value="{k}" checked> {esc(v)}</label>'
        for k, v in dash.CWA_CASE_TYPE_LABELS.items()
    )
    cat_boxes = "".join(
        f'<label class="chip-check"><input type="checkbox" class="cwa-cat" '
        f'value="{k}" checked> {esc(dash.CWA_CATEGORY_LABELS.get(k, k))}</label>'
        for k in hist_cats
    )
    statute_boxes = "".join(
        f'<label class="chip-check"><input type="checkbox" class="cwa-statute" '
        f'value="{k}" checked> {esc(k)} — '
        f'{esc(authorities_payload.get("statutes", {}).get(k, {}).get("name", k))}'
        "</label>"
        for k in dash.WATER_STATUTE_ORDER
    )

    # Sort like the app: category order, then year descending; wrap each card in
    # a div carrying machine-readable category + type + end-year for filtering.
    all_ids = {c.get("case_id") for c in cases}
    cases_by_id = {c["case_id"]: c for c in cases}
    sorted_hist = sorted(
        historical,
        key=lambda c: (
            dash.CWA_CATEGORY_ORDER.get(c.get("category"), 9),
            -dash._cwa_year_end(c.get("year", "")),
        ),
    )
    hist_cards = "".join(
        f'<div class="cwa-case" data-category="{esc(c.get("category",""))}" '
        f'data-casetype="{esc(c.get("case_type",""))}" '
        f'data-statutes="{esc(" ".join(dash._case_statutes(c, readings_by_id)))}" '
        f'data-yearend="{dash._cwa_year_end(c.get("year",""))}">'
        f'{dash._build_cwa_case_html(c, all_ids, readings_by_id)}</div>'
        for c in sorted_hist
    )

    # Section 2: potential/active cases — no client-side filter needed.
    sorted_pot = sorted(
        potential,
        key=lambda c: (
            dash.CWA_CATEGORY_ORDER.get(c.get("category"), 9),
            -dash._cwa_year_end(c.get("year", "")),
        ),
    )
    pot_cards = "".join(
        f'<div class="cwa-potential-case">'
        f'{dash._build_cwa_case_html(c, all_ids, readings_by_id)}</div>'
        for c in sorted_pot
    )

    # Part 1: the statutory toolkit (reading cards grouped by statute).
    toolkit = dash._build_authorities_html(authorities_payload, all_ids)
    n_readings = len(authorities_payload.get("readings", []))
    n_families = len(authorities_payload.get("statutes", {}))

    cat_labels_json = json.dumps(dash.CWA_CATEGORY_LABELS)
    cat_order_json = json.dumps(dash.CWA_CATEGORY_ORDER)

    return f"""
<section class="panel">
  <h2>Federal Water Law &amp; Data Centers — Authorities, Record, Exposure</h2>
  <p class="lead">Three views on federal water law and data centers: the <strong>statutory
  toolkit</strong> ({n_families} authority families — federal discharge and supply
  statutes, interstate compacts, state doctrine — and how each could reach a
  data center), the
  <strong>historical record</strong> built under those authorities (penalties,
  settlements, court rulings), and the <strong>named sites</strong> where water
  conflicts are live. The mappings overlap by design — one fact pattern can trigger
  several readings.</p>
  {insights}
  <details class="lazy">
    <summary>Prioritized CWA-application theories — what could attach to a data center</summary>
    <section class="panel">{theories}
    <h4 class="solution-cat-header">Beyond the Clean Water Act — state and doctrine theories</h4>
    <p>Most tracked conflicts are about <em>getting</em> water, which the Clean Water Act
    barely addresses. Same merit-only scoring, applied to the non-CWA families in the
    Part&nbsp;1 toolkit.</p>
    {doctrine_theories}
    <p class="src-note">Full write-up with primary-source citations:
    docs/cwa-enforcement-and-data-centers.md</p></section>
  </details>
  <details class="lazy">
    <summary>What is a Clean Water Act investigation? — statute, authority, and why it's deployed</summary>
    <div class="explainer-md">{explainer}</div>
  </details>

  <div class="subtabs" role="tablist" aria-label="Water Cases sections">
    <button class="subtab" role="tab" data-subtab="cwa-p1" aria-selected="false">Part 1 · Toolkit ({n_readings})</button>
    <button class="subtab" role="tab" data-subtab="cwa-p2" aria-selected="true">Part 2 · Historical Record ({len(historical)})</button>
    <button class="subtab" role="tab" data-subtab="cwa-p3" aria-selected="false">Part 3 · Active/Potential Exposure ({len(potential)})</button>
  </div>

  <div class="subtabpanel" id="panel-cwa-p1" hidden>
    <h3>Part 1 — The Federal Water-Law Toolkit</h3>
    <p><strong>{n_readings} statutory readings</strong> across {n_families} authority
    families — the federal discharge statutes, the supply-side ones that govern storage,
    withdrawal and licensing, interstate compacts, and state water doctrine — each card
    explains what the authority historically
    covered, how it could apply to a data-center fact pattern, and which cases below show
    it in use. Case and site cards link back here via their <em>statute applicability</em> rows.</p>
    <div id="water-toolkit">{toolkit}</div>
  </div>

  <div class="subtabpanel" id="panel-cwa-p2">
    <h3>Part 2 — Historical Enforcement Record ({len(historical)} cases)</h3>
    <p><strong>{len(historical)} cases</strong> — enforcement actions, penalties, settlements,
    landmark court rulings, and standing rulemakings that have <strong>actually
    occurred</strong>, under the CWA and the other federal water authorities above.
    <strong>Industrial cases are legal analogs</strong> — the enforcement pattern for
    operations similar to data centers, but against other industries, not data centers.
    Precedent rulings define the legal scope for future enforcement.</p>
    <div class="cwa-filters">
      <span class="filter-label">Statute:</span>
      <div class="cwa-types">{statute_boxes}</div>
    </div>
    <div class="cwa-filters">
      <span class="filter-label">Project type:</span>
      <div class="cwa-types">{type_boxes}</div>
    </div>
    <div class="cwa-filters">
      <span class="filter-label">Case group:</span>
      <div class="cwa-cats">{cat_boxes}</div>
      <label class="chip-check"><input type="checkbox" id="cwa-recent"> 2020 onward only</label>
    </div>
    <p class="count-line" id="cwa-count"></p>
    <div id="cwa-cases">{hist_cards}</div>
  </div>

  <div class="subtabpanel" id="panel-cwa-p3" hidden>
    <h3>Part 3 — Active &amp; Potential CWA Exposure at Named Data Center Sites ({len(potential)})</h3>
    <p><strong>{len(potential)} named data center sites</strong> where regulatory proceedings
    are active (pending permit applications, ongoing investigations, active citizen suits)
    or where the factual circumstances match the historical enforcement patterns above —
    but <strong>no formal CWA enforcement action has been issued yet</strong>.
    Use the theories panel above to trace which CWA hook applies to each site.</p>
    <div id="cwa-potential">{pot_cards}</div>
  </div>


  <p class="src-note">Dataset last updated {esc(last_updated)}.
  Total: {len(cases)} entries ({len(historical)} historical enforcement,
  {len(potential)} active/potential).</p>
</section>
<script>
  window.CWA_CAT_LABELS = {cat_labels_json};
  window.CWA_CAT_ORDER = {cat_order_json};
  window.CWA_TOTAL = {len(historical)};
</script>
"""


# --------------------------------------------------------------------------
# Data tab
# --------------------------------------------------------------------------


def _heatmap_html(df: pd.DataFrame) -> str:
    flow = df[df["flow_mgd"].notna()].copy()
    if flow.empty:
        return ""
    flow["year"] = flow["document_date"].dt.year
    flow["month"] = flow["document_date"].dt.month
    pivot = flow.pivot_table(values="flow_mgd", index="month", columns="year", aggfunc="mean")
    if pivot.empty:
        return ""
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    vmin = float(pivot.min().min())
    vmax = float(pivot.max().max())

    def cell_color(v: float) -> str:
        # Interpolate light (#eff3ff) → dark (#08519c) blue by normalized value.
        if vmax <= vmin:
            t = 0.5
        else:
            t = (v - vmin) / (vmax - vmin)
        lo = (0xEF, 0xF3, 0xFF)
        hi = (0x08, 0x51, 0x9C)
        r = round(lo[0] + (hi[0] - lo[0]) * t)
        g = round(lo[1] + (hi[1] - lo[1]) * t)
        b = round(lo[2] + (hi[2] - lo[2]) * t)
        fg = "#fff" if t > 0.55 else "#1a1a2e"
        return f"background:rgb({r},{g},{b});color:{fg}"

    years = list(pivot.columns)
    head = "".join(f"<th>{esc(str(y))}</th>" for y in years)
    rows = []
    for m in pivot.index:
        cells = [f'<th class="hm-month">{month_names[m - 1]}</th>']
        for y in years:
            v = pivot.loc[m, y]
            if pd.isna(v):
                cells.append('<td class="hm-empty"></td>')
            else:
                cells.append(f'<td style="{cell_color(float(v))}">{v:.1f}</td>')
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return (
        '<table class="heatmap"><thead><tr><th></th>' + head + "</tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>"
        '<p class="src-note">Mean monthly WWTP flow (MGD). Darker = higher flow.</p>'
    )


def _chart_data(df: pd.DataFrame) -> dict:
    flow = df[(df["flow_mgd"].notna()) & (df["document_date"].notna())].copy()
    flow = flow.sort_values("document_date").drop_duplicates(
        subset=["permit_number", "document_date"], keep="last"
    )
    labels: list[str] = sorted(flow["monitoring_month"].dropna().unique().tolist())
    series = []
    for permit_id, group in flow.groupby("permit_number"):
        name = permit_id
        if not group["company_llc_name"].isna().all():
            name = f"{group['company_llc_name'].iloc[0]} ({permit_id})"
        by_month = group.groupby("monitoring_month")["flow_mgd"].mean().to_dict()
        data = [round(float(by_month[m]), 2) if m in by_month else None for m in labels]
        series.append({"name": str(name), "data": data})

    limit = 11.0 if "VA0091383" in flow["permit_number"].values else None

    source_counts = df["record_type"].value_counts()
    return {
        "flow": {"labels": labels, "series": series, "limit": limit},
        "source": {
            "labels": [str(s) for s in source_counts.index.tolist()],
            "values": [int(v) for v in source_counts.values.tolist()],
        },
    }


def build_data_tab() -> tuple[str, dict]:
    df = dash.load_data()
    if df.empty:
        return (
            '<section class="panel"><h2>Data</h2>'
            '<p class="lead">No data found. Run the scraping pipeline to populate '
            'measurements.</p></section>',
            {"flow": {"labels": [], "series": [], "limit": None},
             "source": {"labels": [], "values": []}},
        )

    chart_data = _chart_data(df)

    # Freshness line.
    freshness = ""
    if "scraped_at" in df.columns and not df["scraped_at"].isna().all():
        latest = df["scraped_at"].max()
        if pd.notna(latest):
            freshness = (
                f'<p class="src-note">Last updated: {esc(latest.strftime("%B %d, %Y"))} | '
                f'{len(df):,} records | {int(df["flow_mgd"].notna().sum())} with flow data</p>'
            )

    # Hero metrics.
    flow_records = df[df["flow_mgd"].notna()]
    avg_flow = f"{flow_records['flow_mgd'].mean():.1f}" if len(flow_records) else "—"
    peak_flow = f"{flow_records['flow_mgd'].max():.1f}" if len(flow_records) else "—"
    hero = "".join(
        f'<div class="metric"><div class="metric-label">{lbl}</div>'
        f'<div class="metric-value">{val}</div></div>'
        for lbl, val in [
            ("Avg Flow (MGD)", avg_flow),
            ("Peak Flow (MGD)", peak_flow),
            ("Records", f"{len(df):,}"),
            ("Permits", f"{df['permit_number'].dropna().nunique()}"),
        ]
    )

    local_ctx = build_local_context()
    heatmap = _heatmap_html(df)
    records_table = build_records_table(df)

    flow_panel = (
        '<div class="chart-wrap"><canvas id="flowChart"></canvas></div>'
        if chart_data["flow"]["series"]
        else '<p class="lead">No flow data yet. Run the EPA ECHO scraper to collect DMR data.</p>'
    )

    html_out = f"""
<section class="panel">
  <h2>Measurements</h2>
  {freshness}
  <div class="hero">{hero}</div>
  <h3>Monthly WWTP Flow — Data Center Corridors</h3>
  {flow_panel}
  {local_ctx}
</section>

<details class="lazy">
  <summary>Records by Source chart</summary>
  <section class="panel"><div class="chart-wrap"><canvas id="sourceChart"></canvas></div></section>
</details>

<details class="lazy">
  <summary>Seasonal Patterns heatmap</summary>
  <section class="panel"><h3>Seasonal Flow Patterns (MGD)</h3>{heatmap or "<p class='lead'>No flow data.</p>"}</section>
</details>

<details class="lazy">
  <summary>Transparency Scorecard</summary>
  {build_scorecard()}
</details>

<details class="lazy">
  <summary>Per-query water estimates explainer</summary>
  {build_per_query()}
</details>

<details class="lazy">
  <summary>Records table</summary>
  {records_table}
</details>
"""
    return html_out, chart_data


def build_local_context() -> str:
    parts = ['<section class="ctx-group"><h3>How Does This Compare?</h3>']
    for key in ("loudoun", "pwc"):
        ctx = dash.CONTEXT_DATA[key]
        if "dc_water_gallons" not in ctx:
            continue
        dc_gal = ctx["dc_water_gallons"]
        total_gal = ctx["utility_total_gallons"]
        homes = dash.compute_household_equivalent(dc_gal, ctx["avg_household_gpd"])
        pct = (dc_gal / total_gal * 100) if total_gal else 0
        parts.append(
            f'<div class="context-card"><h4>{esc(ctx["label"])}</h4>'
            f'<div class="big-number">{dc_gal / 1e9:.1f} billion gallons ({ctx["dc_water_year"]})</div>'
            f'<div class="comparison">Equivalent to serving <strong>{homes:,} homes</strong> '
            f'for a year — roughly <strong>{pct:.0f}%</strong> of the utility\'s total water sales.</div>'
            f'<div class="source-note">Source: {esc(ctx["source"])}</div></div>'
        )
    oh = dash.CONTEXT_DATA.get("central_ohio", {})
    if oh:
        parts.append(
            f'<div class="context-card"><h4>{esc(oh["label"])} — Projected Growth</h4>'
            f'<div class="big-number">{oh["projected_dc_mgd_2030"]} MGD by 2030 → '
            f'{oh["projected_dc_mgd_2050"]} MGD by 2050</div>'
            f'<div class="comparison">Industrial water demand projected to more than double in '
            f'20 years, driven by data centers and Intel\'s semiconductor campus.</div>'
            f'<div class="source-note">Source: {esc(oh["source"])}</div></div>'
        )
    parts.append("</section>")
    return "".join(parts)


def build_scorecard() -> str:
    disc = {"mandated": "Mandated", "voluntary": "Voluntary", "inferred": "Inferred"}
    conf = {"high": "High", "medium": "Medium", "low": "Low"}
    rows = []
    for s in dash.SCORECARD_DATA:
        rows.append(
            "<tr>"
            f'<td>{esc(s["source"])}</td>'
            f'<td>{esc(disc.get(s["disclosure"], s["disclosure"]))}</td>'
            f'<td>{esc(s["geo_resolution"].title())}</td>'
            f'<td>{esc(s["freshness"].title())}</td>'
            f'<td>{esc(conf.get(s["confidence"], s["confidence"]))}</td>'
            f'<td>{esc(s["notes"])}</td></tr>'
        )
    gaps = "".join(
        f'<li><strong>{esc(g["gap"])}</strong> — {esc(g["impact"])}<br>'
        f'<em>Status: {esc(g["status"])}</em></li>'
        for g in dash.TRANSPARENCY_GAPS
    )
    return (
        '<section class="panel"><h3>Transparency Scorecard</h3>'
        '<p class="lead">How transparent is data center water reporting? Each source rated by '
        'disclosure type, geographic detail, and confidence.</p>'
        '<div class="table-wrap"><table class="data-table"><thead><tr>'
        '<th>Source</th><th>Disclosure</th><th>Resolution</th><th>Frequency</th>'
        '<th>Confidence</th><th>Notes</th></tr></thead><tbody>'
        + "".join(rows) + "</tbody></table></div>"
        '<p class="count-line"><strong>Known Gaps &amp; Barriers:</strong></p>'
        f'<ul class="gap-list">{gaps}</ul></section>'
    )


def build_per_query() -> str:
    estimates = sorted(dash.PER_QUERY_ESTIMATES, key=lambda e: e["ml"])
    low, high = estimates[0], estimates[-1]
    masley_rows = "".join(
        f'<tr><td>{esc(c["activity"])}</td><td>{c["prompts"]:,}</td></tr>'
        for c in dash.MASLEY_COMPARISONS
    )
    detail = "".join(
        f'<li><strong>{e["ml"]} mL</strong> — {esc(e["label"])}<br>'
        f'<em>{esc(e["note"])}</em> | Source: {esc(e["source"])}</li>'
        for e in estimates
    )
    drivers = md(
        "**Four variables drive the variance:**\n\n"
        "1. **Inference vs. training** — Training a large model is a one-time cost amortized "
        "over billions of queries; inference is per-request.\n"
        "2. **Cooling technology** — Evaporative cooling consumes water; air-cooled or "
        "liquid-to-liquid systems use much less.\n"
        "3. **Direct vs. indirect water** — On-site cooling is ~20% of total footprint; "
        "thermoelectric cooling at power plants is ~80%.\n"
        "4. **Withdrawal vs. consumption** — Withdrawal counts water taken; consumption counts "
        "water not returned. Withdrawal numbers are 3-5x higher."
    )
    return f"""
<section class="panel">
  <h3>Per-Query Water: Why Estimates Vary by 2,000x</h3>
  <div class="explainer-card">
    <h4>How much water does one AI query use?</h4>
    <p>Estimates range from <strong>{low['ml']} mL</strong> to <strong>{high['ml']} mL</strong>
    per query. The huge range is not a mistake — it reflects fundamentally different accounting methods.</p>
    <div class="range-bar"></div>
    <div class="range-label"><span>{low['ml']} mL ({esc(low['label'])})</span>
    <span>{high['ml']} mL ({esc(high['label'])})</span></div>
  </div>
  {drivers}
  <p class="count-line"><strong>Reality check — per Andy Masley.</strong> Including the
  electricity-generation water, one query is ~2 mL. Translated into everyday terms:</p>
  <div class="table-wrap"><table class="data-table"><thead><tr>
  <th>Same water as…</th><th>= this many AI prompts</th></tr></thead>
  <tbody>{masley_rows}</tbody></table></div>
  <div class="callout"><strong>The 500 mL bottle myth.</strong> The viral 'one bottle per
  email/prompt' figure (Washington Post, 2023) was inflated 50–250×. The underlying research
  actually found ~500 mL per <em>20–50</em> prompts — not per single prompt.</div>
  <p><strong>Why this tracker measures facilities, not chatbots.</strong> Per query is trivial.
  That's why we track WWTP discharge volumes, utility sales to data centers, and policy mandates
  — where the <em>aggregate, local</em> impact is real and measurable.</p>
  <details><summary>Detailed estimates</summary><ul class="gap-list">{detail}</ul></details>
  <p class="src-note">Comparisons from Andy Masley, "The AI water issue is fake"
  (blog.andymasley.com/p/the-ai-water-issue-is-fake).</p>
</section>"""


def build_records_table(df: pd.DataFrame) -> str:
    cols = [
        ("state", "State"),
        ("company_llc_name", "Facility"),
        ("document_date", "Document Date"),
        ("extracted_water_metric", "Water Metric"),
        ("permit_number", "Permit #"),
    ]
    disp = df.copy()
    disp["document_date"] = disp["document_date"].dt.strftime("%Y-%m-%d")
    states = sorted(disp["state"].dropna().unique().tolist())
    state_boxes = "".join(
        f'<label class="chip-check"><input type="checkbox" class="rec-state" value="{esc(s)}" checked> {esc(s)}</label>'
        for s in states
    )

    def cell(v) -> str:
        if pd.isna(v) or str(v) in ("None", "nan", ""):
            return "—"
        return esc(str(v))

    body = []
    for _, row in disp.iterrows():
        tds = "".join(f"<td>{cell(row.get(c))}</td>" for c, _ in cols)
        body.append(f'<tr data-state="{esc(str(row.get("state", "")))}">{tds}</tr>')
    head = "".join(f"<th>{t}</th>" for _, t in cols)
    return (
        '<section class="panel"><h3>Records</h3>'
        f'<div class="cwa-filters"><span class="filter-label">Filter table:</span>{state_boxes}</div>'
        f'<p class="count-line" id="rec-count"></p>'
        '<div class="table-wrap"><table class="data-table" id="rec-table"><thead><tr>'
        + head + "</tr></thead><tbody>" + "".join(body) + "</tbody></table></div></section>"
    )


# --------------------------------------------------------------------------
# News tab
# --------------------------------------------------------------------------


def build_news_tab() -> str:
    payload = dash.load_water_news()
    items = payload.get("items", [])
    last_updated = payload.get("last_updated") or "unknown"

    all_tags: list[str] = sorted({t for item in items for t in item.get("tags", [])})
    tag_boxes = "".join(
        f'<label class="chip-check"><input type="checkbox" class="news-tag-filter" '
        f'value="{t}" checked> {esc(dash.NEWS_TAG_LABELS.get(t, t))}</label>'
        for t in all_tags
    )

    cards = "".join(dash._build_news_item_html(i) for i in items)

    return f"""
<section class="panel">
  <h2>Data Center Water News</h2>
  <p class="lead">Curated headlines on data center water regulation, enforcement,
  research, and solutions — linked to this tracker's datasets where applicable.
  Newest first.</p>
  <div class="cwa-filters">
    <span class="filter-label">Filter by topic:</span>{tag_boxes}
  </div>
  <p class="count-line" id="news-count">
    <strong>{len(items)} items</strong></p>
  <div id="news-cards">{cards}</div>
  <p class="src-note">Dataset last updated {esc(last_updated)}.</p>
</section>"""


# --------------------------------------------------------------------------
# Solutions tab
# --------------------------------------------------------------------------


def build_solutions_tab() -> str:
    payload = dash.load_water_solutions()
    categories = payload.get("categories", [])
    last_updated = payload.get("last_updated") or "unknown"

    all_sols = [s for cat in categories for s in cat.get("solutions", [])]
    n_deployed = sum(1 for s in all_sols if s.get("status") == "deployed")
    n_pilot    = sum(1 for s in all_sols if s.get("status") == "pilot")
    n_proposed = sum(1 for s in all_sols if s.get("status") == "proposed")
    n_mandate  = sum(1 for s in all_sols if s.get("actor_type") in ("state", "federal"))
    n_utility  = sum(1 for s in all_sols if s.get("actor_type") == "utility")
    n_industry = sum(1 for s in all_sols if s.get("actor_type") == "industry")
    pct = round(n_deployed / len(all_sols) * 100) if all_sols else 0

    stats_html = (
        f'<div class="hero" style="grid-template-columns:repeat(3,1fr)">'
        f'<div class="metric"><div class="metric-label">Deployed</div>'
        f'<div class="metric-value">{n_deployed}</div></div>'
        f'<div class="metric"><div class="metric-label">Pilot / in progress</div>'
        f'<div class="metric-value">{n_pilot}</div></div>'
        f'<div class="metric"><div class="metric-label">Proposed</div>'
        f'<div class="metric-value">{n_proposed}</div></div>'
        f'</div>'
        f'<div class="hero" style="grid-template-columns:repeat(3,1fr);margin-top:-.25rem">'
        f'<div class="metric"><div class="metric-label">State / federal mandate</div>'
        f'<div class="metric-value">{n_mandate}</div></div>'
        f'<div class="metric"><div class="metric-label">Utility-driven</div>'
        f'<div class="metric-value">{n_utility}</div></div>'
        f'<div class="metric"><div class="metric-label">Industry voluntary</div>'
        f'<div class="metric-value">{n_industry}</div></div>'
        f'</div>'
        f'<div class="insights">'
        f'<strong>Key patterns:</strong>'
        f'<ul>'
        f'<li>{pct}% of tracked solutions are already deployed somewhere — the tools exist; '
        f'the gap is mandate coverage and independent measurement.</li>'
        f'<li>All {n_mandate} state/federal mandates and all {n_utility} utility programs have '
        f'at least one deployed or active-pilot example. Voluntary industry solutions ({n_industry}) '
        f'have no independent verification path.</li>'
        f'<li>The critical unlock: OHD000001 direct DMRs (Ohio) and HB&nbsp;496 monthly utility '
        f'reports (Virginia, eff. July 2026) are the two pending mandates that would make '
        f'operator claims independently checkable.</li>'
        f'</ul></div>'
        f'<hr>'
    )

    status_order = {"deployed": 0, "pilot": 1, "proposed": 2}
    sections = []
    total_solutions = len(all_sols)
    for i, cat in enumerate(categories):
        label = cat.get("label", "")
        desc = cat.get("description", "")
        sols = sorted(
            cat.get("solutions", []),
            key=lambda s: status_order.get(s.get("status", "proposed"), 9),
        )
        cards_html = "".join(dash._build_solution_card_html(s) for s in sols)
        # Accordion per category (first open) — the tab was one long scroll.
        sections.append(
            f'<details class="lazy"{" open" if i == 0 else ""}>'
            f'<summary><span class="solution-cat-header" style="border:none;padding-left:0">'
            f'{esc(label)} ({len(sols)})</span></summary>'
            f'<p class="solution-cat-desc">{esc(desc)}</p>'
            f'{cards_html}'
            f'</details>'
        )

    return f"""
<section class="panel">
  <h2>Data Center Water Solutions</h2>
  <p class="lead">Solutions to data center water challenges documented across this tracker —
  organized by who is driving them: state and federal regulators, water utilities, and
  industry operators. Status badges indicate real-world deployment stage.</p>
  {stats_html}
  {"".join(sections)}
  <p class="src-note">Dataset last updated {esc(last_updated)}. Deployment status
  is as of the dataset date; check source links for current status.</p>
</section>"""


# --------------------------------------------------------------------------
# Sources tab
# --------------------------------------------------------------------------

_SRC_BADGE = {
    "working":    ("sb-green",  "Working"),
    "partial":    ("sb-amber",  "Partial"),
    "blocked":    ("sb-red",    "Blocked"),
    "coming":     ("sb-purple", "Coming"),
    "not_built":  ("sb-gray",   "Not built"),
    "policy_gap": ("sb-gray",   "Policy gap"),
}


def build_sources_tab() -> str:
    sc = dash.SOURCES_DATA["scorecard"]

    hero = "".join(
        f'<div class="metric"><div class="metric-label">{lbl}</div>'
        f'<div class="metric-value">{val}</div>'
        f'<div class="metric-sub">{sub}</div></div>'
        for lbl, val, sub in [
            ("Sources accessible", sc["accessible"], "active data pipelines"),
            ("Hard-blocked",       sc["blocked"],    "NDA · WAF · voluntary-only · no mandate"),
            ("Unlocking soon",     sc["coming"],     "HB 496 · OHD000001 · EIA 923"),
            ("Build queue",        sc["build_queue"], "data exists, scraper pending"),
        ]
    )

    current_level = None
    rows = []
    for src in dash.SOURCES_DATA["sources"]:
        if src["level"] != current_level:
            current_level = src["level"]
            rows.append(
                f'<tr class="src-level-hdr"><td colspan="4">{esc(src["level"])}</td></tr>'
            )
        badge_cls, badge_lbl = _SRC_BADGE.get(src["status"], ("sb-gray", src["status"]))
        rows.append(
            f'<tr>'
            f'<td class="src-dot src-dot-{esc(src["status"])}">●</td>'
            f'<td class="src-name">{esc(src["name"])}'
            f'<span class="src-note-inline"> — {esc(src["note"])}</span></td>'
            f'<td><span class="src-badge {esc(badge_cls)}">{esc(badge_lbl)}</span></td>'
            f'<td class="src-action">{esc(src["action"])}</td>'
            f'</tr>'
        )

    barriers = "".join(
        f'<div class="barrier-card barrier-{esc(b["kind"])}">'
        f'<div class="barrier-title">{esc(b["title"])}</div>'
        f'<div class="barrier-body">{esc(b["body"])}</div>'
        f'<div class="barrier-workaround">Workaround: {esc(b["workaround"])}</div>'
        f'</div>'
        for b in dash.SOURCES_DATA["barriers"]
    )

    tl_rows = "".join(
        f'<div class="tl-row">'
        f'<div class="tl-date">{esc(item["date"])}</div>'
        f'<div class="tl-spine">'
        f'<span class="tl-dot tl-dot-{esc(item["color"])}">●</span>'
        f'<span class="tl-line"></span></div>'
        f'<div><div class="tl-title">{esc(item["title"])}</div>'
        f'<div class="tl-desc">{esc(item["desc"])}</div></div>'
        f'</div>'
        for item in dash.SOURCES_DATA["timeline"]
    )

    return f"""
<section class="panel">
  <h2>Data Sources</h2>
  <p class="lead">Status of all known data pipelines for tracking data center water
  consumption — what's working, what's blocked, and what's coming.</p>
  <div class="hero src-hero">{hero}</div>
</section>

<section class="panel">
  <h3>Source status by level</h3>
  <div class="table-wrap">
    <table class="src-table"><tbody>{"".join(rows)}</tbody></table>
  </div>
</section>

<section class="panel">
  <h3>Structural barriers that scraping alone can't fix</h3>
  <div class="barrier-grid">{barriers}</div>
</section>

<section class="panel">
  <h3>Upcoming data unlocks</h3>
  <div class="tl">{tl_rows}</div>
</section>
"""


# --------------------------------------------------------------------------
# Explore tab
# --------------------------------------------------------------------------


def build_explore_tab() -> str:
    """The connection graph + text-similarity surface.

    All of the work is in ``dashboard._build_explore_html`` so the Streamlit
    app renders the identical fragment; this only supplies the tab chrome
    (title, lead, dataset note) the way every other tab does.
    """
    return f"""
<section class="panel">
  <h2>Explore — Connections and Text Search</h2>
  <p class="lead">{esc(dash.EXPLORE_LEAD)}</p>
  {dash._build_explore_html()}
  <p class="src-note">Lines are the cross-references the datasets declare, walked
  in both directions; taxonomy-membership lines (shared statute family, project
  type, or principle) are derived and off until you switch them on. Similarity is
  TF-IDF over each record's own text — it matches wording, not meaning, which is
  why the terms it matched on are shown. Everything runs in your browser.</p>
</section>
"""


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------

CSS = """
:root{--ink:#1a1a2e;--blue:#08519c;--blue2:#3182bd;--muted:#4b5563}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  color:var(--ink);line-height:1.55;
  /* Kept in sync with the .stApp rule in assets/components.css — see the
     comment there for the layer breakdown (highlight + depth wash + ripple
     tile). The static site has no .stApp wrapper, so it needs its own copy. */
  background-color:#eaf4fb;
  background-image:
    radial-gradient(120% 60% at 50% 0%, rgba(255,255,255,0.85) 0%, rgba(255,255,255,0) 65%),
    linear-gradient(180deg, #f2f9fd 0%, #e6f2fa 45%, #d8ebf6 100%),
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 240 120'><g fill='none' stroke-linecap='round'><path d='M0 20 Q 10 15,20 20 T 40 20 T 60 20 T 80 20 T 100 20 T 120 20 T 140 20 T 160 20 T 180 20 T 200 20 T 220 20 T 240 20' stroke='%2308519c' stroke-opacity='0.07' stroke-width='1.6'/><path d='M-20 60 Q -10 53,0 60 T 20 60 T 40 60 T 60 60 T 80 60 T 100 60 T 120 60 T 140 60 T 160 60 T 180 60 T 200 60 T 220 60 T 240 60 T 260 60' stroke='%233182bd' stroke-opacity='0.08' stroke-width='2'/><path d='M0 100 Q 10 93,20 100 T 40 100 T 60 100 T 80 100 T 100 100 T 120 100 T 140 100 T 160 100 T 180 100 T 200 100 T 220 100 T 240 100' stroke='%2308519c' stroke-opacity='0.06' stroke-width='1.4'/></g><g fill='%233182bd' fill-opacity='0.06'><circle cx='34' cy='42' r='2'/><circle cx='142' cy='12' r='1.6'/><circle cx='202' cy='84' r='2.4'/><circle cx='72' cy='104' r='1.8'/><circle cx='182' cy='50' r='1.4'/><circle cx='10' cy='90' r='1.5'/></g></svg>");
  background-repeat:no-repeat, no-repeat, repeat;
  background-position:center top, center top, left top;
  background-attachment:fixed, fixed, fixed;
}
.wrap{max-width:1040px;margin:0 auto;padding:1.25rem 1.25rem 4rem}
h1{font-size:1.9rem;margin:0 0 .2rem;padding-bottom:.4rem;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 80 8' preserveAspectRatio='none'><path d='M0 4 Q 10 0, 20 4 T 40 4 T 60 4 T 80 4' fill='none' stroke='%233182bd' stroke-width='1.5' stroke-opacity='0.65'/></svg>");
  background-repeat:repeat-x;background-position:left bottom;background-size:80px 8px}
hr{border:none;height:2px;background:linear-gradient(90deg,var(--blue) 0%,var(--blue2) 25%,#6baed6 60%,transparent 100%);margin:1rem 0;border-radius:1px}
.tagline{color:var(--muted);margin:0 0 1rem;font-size:.95rem}
h2{font-size:1.5rem;margin:.2rem 0 .5rem}
h3{font-size:1.2rem;margin:1rem 0 .5rem}
h4{margin:.2rem 0 .5rem}
a{color:var(--blue)}
.lead{color:#333;margin:.2rem 0 .8rem}
.count-line{margin:.4rem 0 .8rem}
.src-note{color:#888;font-size:.82rem;margin-top:.6rem}
.filter-label{font-weight:600;margin-right:.4rem}

/* Tabs */
.tabs{display:flex;gap:.25rem;border-bottom:2px solid #d6e2ee;margin:.5rem 0 1.25rem;flex-wrap:wrap}
.tab{appearance:none;border:0;background:none;font:inherit;cursor:pointer;position:relative;
  padding:.6rem 1rem;color:var(--muted);border-bottom:3px solid transparent;margin-bottom:-2px;
  font-weight:600;min-height:44px}
.tab[aria-selected="true"]{color:var(--blue)}
/* The active marker is a short pipe run rather than a slab underline: 2px with
   rounded caps (::after) and a fitting dot at each end (::before, two radial
   gradients so one pseudo-element carries both). rgba(...,0) rather than
   `transparent` — `transparent` is transparent BLACK and fringes the dot grey
   as it interpolates. */
.tab[aria-selected="true"]::after{content:"";position:absolute;left:.8rem;right:.8rem;
  bottom:-3px;height:2px;border-radius:999px;background:var(--blue)}
.tab[aria-selected="true"]::before{content:"";position:absolute;
  left:calc(.8rem - 3px);right:calc(.8rem - 3px);bottom:-5px;height:6px;background-repeat:no-repeat;
  background:radial-gradient(circle at 3px 3px,var(--blue) 0 2.4px,rgba(8,81,156,0) 2.6px),
             radial-gradient(circle at calc(100% - 3px) 3px,var(--blue) 0 2.4px,rgba(8,81,156,0) 2.6px)}
.tabpanel[hidden]{display:none}

/* Sub-tabs (e.g. Water Cases Part 1-4) — same mechanics as the top-level
   tabs, one visual size down, so a section is one click away instead of a
   scroll past every earlier part. */
.subtabs{display:flex;gap:.25rem;border-bottom:1px solid #d6e2ee;margin:.75rem 0 1rem;flex-wrap:wrap}
.subtab{appearance:none;border:0;background:#eef6ff;color:var(--muted);cursor:pointer;
  padding:.5rem .85rem;border-radius:.4rem .4rem 0 0;font:inherit;font-weight:600;
  font-size:.92rem;min-height:44px}
.subtab[aria-selected="true"]{color:#fff;background:var(--blue)}
.subtabpanel[hidden]{display:none}

.panel{margin-bottom:1.25rem}
details.lazy{border:1px solid #cbd5e1;border-radius:.5rem;background:#fff;margin:.6rem 0;
  box-shadow:0 1px 2px rgba(15,23,42,.04)}
details.lazy>summary{cursor:pointer;font-weight:600;color:var(--blue);padding:.75rem 1rem;
  list-style:none;min-height:44px;display:flex;align-items:center}
details.lazy>summary::-webkit-details-marker{display:none}
details.lazy>summary::before{content:"▸";margin-right:.5rem;transition:transform .15s}
details.lazy[open]>summary::before{transform:rotate(90deg)}
details.lazy>*:not(summary){padding:0 1rem 1rem}
/* Guarantee a closed panel occupies zero space and isn't painted, regardless
   of UA content-visibility quirks (a tall markdown body was reporting layout
   height while collapsed). */
details.lazy:not([open])>*:not(summary){display:none}
details.lazy .panel{margin:0}

/* Insights box */
.insights{border:1px solid #cbd5e1;border-radius:.5rem;background:#fff;padding:1rem 1.25rem;
  margin:.5rem 0 1rem;box-shadow:0 1px 3px rgba(15,23,42,.06)}
.insights ul{margin:.3rem 0 0;padding-left:1.2rem}
.insights li{margin:.4rem 0}

/* Filters */
.cwa-filters{display:flex;flex-wrap:wrap;gap:.5rem .9rem;align-items:center;margin:.6rem 0}
.cwa-types,.cwa-cats{display:flex;flex-wrap:wrap;gap:.4rem .6rem;align-items:center}
.chip-check{display:inline-flex;align-items:center;gap:.35rem;font-size:.9rem;
  background:#eff3ff;border:1px solid #bdd7e7;border-radius:999px;padding:.25rem .7rem;cursor:pointer}
.chip-check input{accent-color:var(--blue)}

/* Hero metrics */
.hero{display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem;margin:.5rem 0 1rem}
.metric{background:#fff;border:1px solid #e2e8f0;border-radius:.5rem;padding:.8rem 1rem;text-align:center}
.metric-label{color:var(--muted);font-size:.8rem}
.metric-value{font-size:1.8rem;font-weight:700;color:var(--ink)}

/* Charts */
.chart-wrap{position:relative;height:380px;background:#fff;border:1px solid #e2e8f0;
  border-radius:.5rem;padding:.75rem;margin:.5rem 0}

/* Tables */
.table-wrap{overflow-x:auto}
.data-table{width:100%;border-collapse:collapse;font-size:.88rem;background:#fff}
.data-table th,.data-table td{border:1px solid #e5e7eb;padding:.4rem .6rem;text-align:left;vertical-align:top}
.data-table thead th{background:#eff3ff;color:var(--blue);position:sticky;top:0}
.heatmap{border-collapse:collapse;font-size:.85rem;background:#fff}
.heatmap th,.heatmap td{border:1px solid #e5e7eb;padding:.35rem .55rem;text-align:center;min-width:48px}
.heatmap .hm-month{background:#eff3ff;color:var(--blue);text-align:right}
.heatmap .hm-empty{background:#fafafa}
.gap-list li{margin:.4rem 0}
.callout{background:#eef6ff;border-left:4px solid var(--blue2);padding:.6rem .9rem;border-radius:0 .25rem .25rem 0;margin:.6rem 0}

/* Company claim cards */
.claim-company{margin:1rem 0 .3rem;color:var(--blue)}
.claim-card{border:1px solid #e2e8f0;border-radius:.5rem;background:#fff;padding:.8rem 1rem;margin:.5rem 0}
.claim-quote{font-style:italic;margin:0 0 .4rem}
/* .claim-chips/.claim-*-pill/.claim-site-link live in assets/components.css
   so the Streamlit card and this page share one definition. */
.claim-meta{color:#666;font-size:.8rem}
.claim-status{margin-top:.6rem;padding:.6rem .8rem;border-radius:.35rem;font-size:.9rem}
.claim-status-summary{margin-top:.3rem}
.claim-status-link{margin-top:.3rem;font-size:.85rem}
.claim-assessed{color:#555;font-weight:400}
.claim-status-delivered{background:#eaf7ef;border:1px solid #b7e4c7}
.claim-status-partial{background:#fff7e6;border:1px solid #f3d99b}
.claim-status-shortfall{background:#fdecec;border:1px solid #f3b5b5}
.claim-status-info{background:#eef6ff;border:1px solid #bcd9f5}

.explainer-md h4{margin-top:1rem}
.explainer-md blockquote{border-left:3px solid var(--blue2);margin:.5rem 0;padding:.2rem .8rem;color:#333;background:#f6fafe}

/* Legislation themes grid */
.theme-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem;margin:.8rem 0 1rem}
.theme-card{background:#fff;border:1px solid #e2e8f0;border-radius:.5rem;padding:.8rem 1rem}
.theme-card-count{font-size:2.1rem;font-weight:700;line-height:1.1}
.theme-card-label{font-weight:700;font-size:.92rem;margin:.15rem 0}
.theme-card-desc{font-size:.83rem;color:#555;margin:.2rem 0 .3rem}
.theme-card-examples{font-size:.78rem;color:#999}

/* News tab — keep in sync with _build_news_item_html() in dashboard.py */
.news-card{border:1px solid #d6e4f0;border-radius:.5rem;background:#fff;padding:.9rem 1.1rem;margin-bottom:.75rem;box-shadow:0 1px 2px rgba(15,23,42,.04)}
.news-title{font-weight:700;font-size:1rem;display:block;margin-bottom:.3rem;color:var(--ink)}
a.news-title{color:var(--blue)}
.news-meta{font-size:.85rem;color:#4b5563;margin-bottom:.4rem}
.news-summary{font-size:.9rem;color:#1a1a2e;line-height:1.5;margin:.4rem 0}
.news-tags{display:flex;flex-wrap:wrap;gap:.3rem;margin-top:.35rem}
.news-tag{border-radius:999px;background:#eff3ff;border:1px solid #bdd7e7;padding:.1rem .5rem;font-size:.77rem;font-weight:600}
.news-crossref{font-size:.82rem;color:#08519c;margin-top:.3rem}

/* Solutions tab */
.solution-cat-header{font-size:1.15rem;font-weight:700;color:var(--blue);margin:1.2rem 0 .2rem;
  border-bottom:2px solid #d6e2ee;padding-bottom:.3rem}
.solution-cat-desc{font-size:.9rem;color:#555;margin:0 0 .6rem}
.solution-card{border:1px solid #e2e8f0;border-radius:.5rem;background:#fff;padding:.85rem 1rem;margin:.5rem 0}
.solution-badge{display:inline-block;border-radius:999px;padding:.15rem .65rem;font-size:.78rem;
  font-weight:700;margin-bottom:.35rem}
.solution-title{font-weight:700;font-size:.95rem;margin:.1rem 0 .2rem}
.solution-actor{font-size:.82rem;color:#666;margin-bottom:.35rem}
.solution-desc{font-size:.88rem;color:#333;margin:.2rem 0}
.solution-example{font-size:.84rem;background:#f8faff;border-left:3px solid var(--blue2);
  padding:.4rem .65rem;margin:.4rem 0;border-radius:0 .25rem .25rem 0;color:#333}
.solution-crossref{font-size:.82rem;color:#666;font-style:italic;margin-top:.35rem}

/* Sources tab */
.src-hero .metric-sub{font-size:.75rem;color:var(--muted);margin-top:.1rem}
.src-table{width:100%;border-collapse:collapse;font-size:.88rem}
.src-table tr{border-bottom:.5px solid #e5e7eb}
.src-level-hdr td{font-size:.78rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.06em;color:var(--muted);background:#f1f5f9;padding:.35rem .6rem}
.src-dot{width:1.5rem;text-align:center;font-size:.7rem;padding:.45rem .2rem}
.src-dot-working{color:#3B6D11}.src-dot-partial{color:#854F0B}
.src-dot-blocked{color:#A32D2D}.src-dot-coming{color:#534AB7}
.src-dot-not_built,.src-dot-policy_gap{color:#9ca3af}
.src-name{padding:.45rem .4rem;font-weight:600}
.src-note-inline{font-weight:400;color:var(--muted);font-size:.82rem}
.src-badge{display:inline-block;border-radius:999px;padding:.15rem .6rem;font-size:.75rem;font-weight:700}
.sb-green{background:#EAF3DE;color:#3B6D11}.sb-amber{background:#FAEEDA;color:#854F0B}
.sb-red{background:#FCEBEB;color:#A32D2D}.sb-purple{background:#EEEDFE;color:#534AB7}
.sb-gray{background:#F1EFE8;color:#5F5E5A}
.src-action{font-size:.8rem;color:var(--muted);white-space:nowrap;padding:.45rem .3rem}
.barrier-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem;margin:.5rem 0}
.barrier-card{padding:.9rem 1rem;border-radius:.5rem;border:1px solid #e2e8f0;border-left:3px solid}
.barrier-structural{border-left-color:#E24B4A;background:#fef2f2}
.barrier-legal{border-left-color:#EF9F27;background:#fffbeb}
.barrier-policy{border-left-color:#7F77DD;background:#EEEDFE}
.barrier-title{font-weight:700;font-size:.9rem;margin-bottom:.3rem}
.barrier-body{font-size:.85rem;color:#444;line-height:1.45;margin-bottom:.4rem}
.barrier-workaround{font-size:.8rem;color:#3B6D11;font-style:italic}
.tl{display:flex;flex-direction:column}
.tl-row{display:grid;grid-template-columns:90px 16px 1fr;gap:.6rem;align-items:start;padding-bottom:.9rem}
.tl-date{font-size:.8rem;color:var(--muted);text-align:right;padding-top:.1rem}
.tl-spine{display:flex;flex-direction:column;align-items:center}
.tl-dot{font-size:.65rem;line-height:1}.tl-dot-purple{color:#7F77DD}.tl-dot-green{color:#3B6D11}
.tl-line{width:1px;background:#e5e7eb;flex:1;min-height:24px;margin:.1rem 0}
.tl-title{font-weight:700;font-size:.9rem}
.tl-desc{font-size:.85rem;color:#444;margin:.15rem 0 0;line-height:1.4}

@media (max-width:760px){
  .wrap{padding:.75rem .75rem 3rem}
  h1{font-size:1.35rem}
  .hero{grid-template-columns:repeat(2,1fr)}
  .chart-wrap{height:300px}
  .theme-grid{grid-template-columns:repeat(2,1fr)}
  /* Tighter cards + chips so 70+ cards stay scannable on a phone. */
  .bill-card{padding:.65rem .75rem}
  .chip-check{font-size:.78rem;padding:.18rem .55rem}
  .cwa-filters{gap:.35rem .6rem}
  .principle-sum-row{font-size:.82rem}
  .principles-panel{padding:.7rem .8rem}
  .cwa-instrument{font-size:.75rem}
  /* Collapse long filter chip rows behind a scrollable strip instead of a
     half-screen wall of checkboxes. */
  .cwa-types{max-height:7.5rem;overflow-y:auto}
  .barrier-grid{grid-template-columns:1fr}
  .tl-row{grid-template-columns:70px 14px 1fr}
}

/* Footer pipe run — ornament, held at the 12% ceiling DESIGN.md §1 sets for
   anything that is not data. */
.footer-motif{display:block;width:100%;height:auto;margin:1.75rem 0 .25rem;opacity:.12}

/* Print. The page texture prints as grey mush and the footer motif is pure
   ornament, so both go. The schematic stays — it is the one piece of art here
   that carries information — but its screen-only minimum drawing width would
   run off the sheet, so that is dropped and it scales to the page. */
@media print{
  body{background-image:none;background-color:#fff}
  .footer-motif{display:none}
  .schematic{overflow-x:visible}
  .schematic svg{min-width:0}
}
"""


def build_js() -> str:
    return """
// --- Tabs ---
const tabs = document.querySelectorAll('.tab');
const panels = document.querySelectorAll('.tabpanel');
function activateTab(name){
  tabs.forEach(x => x.setAttribute('aria-selected', x.dataset.tab === name ? 'true' : 'false'));
  panels.forEach(p => p.hidden = (p.id !== 'panel-' + name));
}
tabs.forEach(t => t.addEventListener('click', () => activateTab(t.dataset.tab)));

// --- Sub-tabs (Water Cases Part 1-4) ---
const subtabs = document.querySelectorAll('.subtab');
const subpanels = document.querySelectorAll('.subtabpanel');
function activateSubtab(name){
  subtabs.forEach(x => x.setAttribute('aria-selected', x.dataset.subtab === name ? 'true' : 'false'));
  subpanels.forEach(p => p.hidden = (p.id !== 'panel-' + name));
}
subtabs.forEach(t => t.addEventListener('click', () => activateSubtab(t.dataset.subtab)));

// --- Legislation filtering ---
// Node lists are cached once at load: the cards are static, and re-querying
// the DOM on every checkbox change triggers needless reflow work on
// low-end mobile as the dataset grows.
const legCount = document.getElementById('leg-count');
const legBills = [...document.querySelectorAll('.leg-bill')];
const legChecks = [...document.querySelectorAll('.leg-status, .leg-level, .leg-scope, .leg-principle, .leg-instrument')];
function applyLegFilter(){
  const statuses = new Set(), levels = new Set(), scopes = new Set(),
        prins = new Set(), instruments = new Set();
  legChecks.forEach(c => {
    if (!c.checked) return;
    if (c.classList.contains('leg-status')) statuses.add(c.value);
    else if (c.classList.contains('leg-level')) levels.add(c.value);
    else if (c.classList.contains('leg-scope')) scopes.add(c.value);
    else if (c.classList.contains('leg-instrument')) instruments.add(c.value);
    else prins.add(c.value);
  });
  const counts = {};
  let shown = 0;
  legBills.forEach(el => {
    const sc = (el.dataset.scope || '').split(' ').filter(Boolean);
    const pr = (el.dataset.principles || '').split(' ').filter(Boolean);
    const ok = statuses.has(el.dataset.status) && levels.has(el.dataset.level) &&
      sc.some(s => scopes.has(s)) && pr.some(p => prins.has(p)) &&
      instruments.has(el.dataset.instrument || 'bill');
    el.hidden = !ok;
    if (ok){ shown++; counts[el.dataset.status] = (counts[el.dataset.status]||0)+1; }
  });
  const lOrder = window.LEG_STATUS_ORDER || {}, lLabels = window.LEG_STATUS_LABELS || {};
  const lSummary = Object.keys(counts).sort((a,b)=>(lOrder[a]??9)-(lOrder[b]??9))
    .map(k => counts[k] + ' ' + (lLabels[k]||k)).join(' · ');
  // "instruments", not "bills": 15 of these are executive orders, agency
  // rules, commission dockets and local ordinances.
  const legStrong = document.createElement('strong');
  legStrong.textContent = 'Showing ' + shown + ' of ' + window.LEG_TOTAL + ' instruments';
  legCount.replaceChildren(legStrong);
  if (lSummary) legCount.append(' — ' + lSummary);
}
legChecks.forEach(c => c.addEventListener('change', applyLegFilter));
if (legCount) applyLegFilter();

// --- Part 4 conflict-site filtering by issue type ---
const conflictCount = document.getElementById('conflict-count');
const dcSites = [...document.querySelectorAll('.dc-site')];
const issueChecks = [...document.querySelectorAll('.dc-issue')];
function applyIssueFilter(){
  const picked = new Set(issueChecks.filter(c => c.checked).map(c => c.value));
  let shown = 0;
  dcSites.forEach(el => {
    // A site carries 1-3 tags and matches if ANY is picked — the tags are
    // facets of one conflict, not alternatives, so requiring all of them
    // would hide a site the moment you narrowed to one of its own problems.
    const tags = (el.dataset.issues || '').split(' ').filter(Boolean);
    const ok = tags.some(t => picked.has(t));
    el.hidden = !ok;
    if (ok) shown++;
  });
  if (conflictCount){
    const strong = document.createElement('strong');
    strong.textContent = 'Showing ' + shown + ' of ' + dcSites.length + ' sites';
    conflictCount.replaceChildren(strong);
  }
}
issueChecks.forEach(c => c.addEventListener('change', applyIssueFilter));
if (conflictCount) applyIssueFilter();

// --- CWA filtering ---
const cwaCount = document.getElementById('cwa-count');
const cwaCases = [...document.querySelectorAll('.cwa-case')];
const cwaCatChecks = [...document.querySelectorAll('.cwa-cat')];
const cwaTypeChecks = [...document.querySelectorAll('.cwa-type')];
const cwaStatuteChecks = [...document.querySelectorAll('.cwa-statute')];
function applyCwaFilter(){
  const cats = new Set(cwaCatChecks.filter(c => c.checked).map(c => c.value));
  const types = new Set(cwaTypeChecks.filter(c => c.checked).map(c => c.value));
  const statutes = new Set(cwaStatuteChecks.filter(c => c.checked).map(c => c.value));
  const recent = document.getElementById('cwa-recent').checked;
  const counts = {};
  let shown = 0;
  cwaCases.forEach(el => {
    const cat = el.dataset.category;
    const ye = parseInt(el.dataset.yearend, 10) || 0;
    const caseStatutes = (el.dataset.statutes || '').split(' ');
    const ok = cats.has(cat) && types.has(el.dataset.casetype)
      && caseStatutes.some(s => statutes.has(s))
      && (!recent || ye >= 2020);
    el.hidden = !ok;
    if (ok){ shown++; counts[cat] = (counts[cat]||0)+1; }
  });
  const order = window.CWA_CAT_ORDER || {};
  const labels = window.CWA_CAT_LABELS || {};
  const summary = Object.keys(counts)
    .sort((a,b)=>(order[a]??9)-(order[b]??9))
    .map(k => counts[k] + ' ' + (labels[k]||k)).join(' · ');
  cwaCount.innerHTML = '<strong>Showing ' + shown + ' of ' + window.CWA_TOTAL +
    ' cases</strong>' + (summary ? ' — ' + summary : '');
}
[...cwaCatChecks, ...cwaTypeChecks, ...cwaStatuteChecks,
 document.getElementById('cwa-recent')].forEach(c =>
  c.addEventListener('change', applyCwaFilter));
if (cwaCount) applyCwaFilter();

// --- In-page anchor links: cross-tab deep links ---
// Bill / case / reading / site anchors can live on ANOTHER tab (e.g. a
// Solutions-card quote citing "SD SB 135" links into the Legislation tab),
// in another Water Cases sub-tab (Part 1-4), inside a collapsed <details>,
// or behind an active filter. On click: switch to the owning tab and
// sub-tab, open ancestor <details>, reset filters that hide the target,
// then scroll to it ourselves (the browser's default fragment jump can't
// cross a hidden tab panel).
document.addEventListener('click', e => {
  // Respect modifier/middle clicks (new tab, etc.) — let the browser handle them.
  if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  // Prefix-agnostic: any in-page anchor whose target exists gets the
  // cross-tab treatment, so new card families deep-link without JS changes.
  const a = e.target.closest('a[href^="#"]');
  if (!a || a.getAttribute('href').length < 2) return;
  const id = a.getAttribute('href').slice(1);
  const target = document.getElementById(id);
  if (!target) return;
  e.preventDefault();
  const panel = target.closest('.tabpanel');
  if (panel && panel.hidden) activateTab(panel.id.replace('panel-', ''));
  const subpanel = target.closest('.subtabpanel');
  if (subpanel && subpanel.hidden) activateSubtab(subpanel.id.replace('panel-', ''));
  // Anchors inside a collapsed <details> (e.g. a case's statute-citation
  // block) can't be scrolled to in all browsers — open the ancestors first.
  let det = target.closest('details');
  while (det) { det.open = true; det = det.parentElement && det.parentElement.closest('details'); }
  const wrap = target.closest('.leg-bill, .cwa-case, .dc-site');
  if (wrap && wrap.hidden) {
    if (wrap.classList.contains('leg-bill')) {
      legChecks.forEach(c => { c.checked = true; });
      applyLegFilter();
    } else if (wrap.classList.contains('dc-site')) {
      // Conflict cards are .bill-card.dc-site, so they fell through to the
      // CWA branch and were never unhidden — the handler scrolled to a hidden
      // element. Every doctrine-matrix row links here, and the matrix sits
      // directly above the filter that hides them.
      issueChecks.forEach(c => { c.checked = true; });
      applyIssueFilter();
    } else {
      cwaCatChecks.forEach(c => { c.checked = true; });
      cwaTypeChecks.forEach(c => { c.checked = true; });
      cwaStatuteChecks.forEach(c => { c.checked = true; });
      document.getElementById('cwa-recent').checked = false;
      applyCwaFilter();
    }
  }
  // Preserve fragment/history semantics the native jump would have given:
  // the URL is shareable and Back returns here.
  history.pushState(null, '', '#' + id);
  target.scrollIntoView({behavior: 'smooth', block: 'start'});
});

// --- Records table state filter ---
const recCount = document.getElementById('rec-count');
function applyRecFilter(){
  const states = new Set([...document.querySelectorAll('.rec-state:checked')].map(c => c.value));
  let shown = 0, total = 0;
  document.querySelectorAll('#rec-table tbody tr').forEach(tr => {
    total++;
    const ok = states.has(tr.dataset.state);
    tr.hidden = !ok;
    if (ok) shown++;
  });
  if (recCount) recCount.innerHTML = '<strong>' + shown + ' of ' + total + ' records</strong>';
}
document.querySelectorAll('.rec-state').forEach(c => c.addEventListener('change', applyRecFilter));
if (recCount) applyRecFilter();

// --- News tag filter ---
const newsCount = document.getElementById('news-count');
function applyNewsFilter(){
  const active = new Set([...document.querySelectorAll('.news-tag-filter:checked')].map(c => c.value));
  let shown = 0;
  document.querySelectorAll('#news-cards .news-card').forEach(el => {
    const tags = el.dataset.tags ? el.dataset.tags.split(',') : [];
    const ok = active.size === 0 || tags.some(t => active.has(t));
    el.hidden = !ok;
    if (ok) shown++;
  });
  if (newsCount) newsCount.innerHTML = '<strong>' + shown + ' items</strong>';
}
document.querySelectorAll('.news-tag-filter').forEach(c => c.addEventListener('change', applyNewsFilter));

"""
# Chart initialisation (initCharts, CHART_DATA, PALETTE) lives here when
# the live-map tab ships. Removed with the Data→Sources tab rename (2026-06-25).


LLMS_TXT_PATH = BASE_DIR / "pages" / "llms.txt"
SITE_URL = "https://pranava0x0.github.io/datacenterwaterusage/"
REPO_URL = "https://github.com/pranava0x0/datacenterwaterusage"


def build_llms_txt() -> str:
    """llms.txt — an LLM-friendly plain-markdown mirror of the site.

    Follows the llms.txt convention (llmstxt.org): H1 + blockquote summary,
    then sections. Regenerated by every build so it can never drift from the
    page; a test asserts every bill_id and case_id appears.
    """
    leg = dash.load_legislation()
    bills = leg.get("bills", [])
    cwa = dash.load_cwa_investigations()
    cases = cwa.get("cases", [])
    authorities = dash.load_water_authorities()
    readings = authorities.get("readings", [])
    readings_by_id = dash._readings_by_id(authorities)
    conflicts = dash.load_dc_water_conflicts()
    conflict_sites = conflicts.get("sites", [])
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        "# Data Center Water Use Tracker",
        "",
        "> Tracking data center water consumption in Virginia & Ohio via public "
        "regulatory data (EPA ECHO DMR flow at receiving wastewater treatment "
        "plants, state permit portals, utility financial reports), plus curated "
        "national datasets: data-center water legislation, water-law cases "
        "relevant to data centers mapped to a registry of statutory and "
        "doctrinal readings, data-center sites with "
        "documented water conflicts, and company water claims.",
        "",
        f"Static build {built}. Dashboard: {SITE_URL} · Source: {REPO_URL}",
        "",
        "## Key numbers",
        "",
        f"- {len(bills)} bills tracked — {dash._legislation_status_summary(bills)}",
        f"- {len(cases)} water enforcement and precedent cases across "
        f"{len(authorities.get('statutes', {}))} authority families — "
        f"{dash._cwa_summary(cases)}",
        "- Core finding: data centers rarely hold their own discharge permits; "
        "operational water shows up at the receiving municipal treatment plant, "
        "so the pipeline tracks WWTP NPDES permits via EPA ECHO.",
        "",
        "## Key principles across tracked legislation",
        "",
    ]
    for r in dash._legislation_principles_summary(bills):
        enacted = f", {r['enacted']} enacted" if r["enacted"] else ""
        examples = ", ".join(bid for bid, _ in r["example_bills"])
        lines.append(
            f"- **{r['tag']}** ({r['count']} bills{enacted}): {r['description']} "
            f"Examples: {examples}."
        )

    lines += ["", "## Legislation tracker", ""]
    for b in sorted(
        bills,
        key=lambda b: (
            dash.LEGISLATION_STATUS_ORDER.get(b.get("status"), 9),
            b.get("jurisdiction", ""),
        ),
    ):
        status = dash.LEGISLATION_STATUS_LABELS.get(b.get("status"), "?")
        lines.append(
            f"- {b.get('bill_id')} ({b.get('jurisdiction')}) — {status} — "
            f"{b.get('summary')} Source: {b.get('source_url')}"
        )

    lines += ["", "## Federal water-law toolkit (statutory readings)", ""]
    for r in readings:
        examples = ", ".join(r.get("example_case_ids", []))
        lines.append(
            f"- {r['reading_id']} — {r['statute']} {r.get('section', '')} "
            f"({r.get('name', '')}): {r.get('dc_applicability', '')}"
            + (f" Example cases: {examples}." if examples else "")
        )

    lines += ["", "## Water enforcement cases and precedent", ""]
    for c in sorted(
        cases,
        key=lambda c: (
            dash.CWA_CATEGORY_ORDER.get(c.get("category"), 9),
            -dash._cwa_year_end(c.get("year", "")),
        ),
    ):
        cat = dash.CWA_CATEGORY_LABELS.get(c.get("category"), "?")
        ctype = dash.CWA_CASE_TYPE_LABELS.get(c.get("case_type"), "?")
        status = dash.CWA_STATUS_LABELS.get(c.get("cwa_applied"), "?")
        statutes = "/".join(dash._case_statutes(c, readings_by_id))
        case_sources = c.get("sources") or []
        src = case_sources[0].get("url", "") if case_sources else ""
        line = (
            f"- {c.get('case_id')} ({c.get('year')}) — {statutes} — {cat} / {ctype} / {status} "
            f"— {c.get('cwa_instrument', '')}. {c.get('takeaway', '')}"
        )
        if c.get("cwa_pathway"):
            line += f" How {statutes} could apply: {c['cwa_pathway']}"
        if src:
            line += f" Source: {src}"
        lines.append(line)

    lines += ["", "## Data-center sites with documented water conflicts", ""]
    for s in conflict_sites:
        reading_ids = ", ".join(
            ar.get("reading_id", "") for ar in s.get("applicable_readings", [])
        )
        site_sources = s.get("sources") or []
        src = site_sources[0].get("url", "") if site_sources else ""
        line = (
            f"- {s.get('site_id')} — {s.get('site')} ({s.get('location')}): "
            f"{s.get('issue_summary', '')} Status: {s.get('status_2026', '')}"
            + (f" Applicable readings: {reading_ids}." if reading_ids else "")
        )
        if src:
            line += f" Source: {src}"
        lines.append(line)

    lines += [
        "",
        "## Explore tab (connection graph + text search)",
        "",
        "The dashboard's Explore tab renders every record above as one graph and "
        "ranks all of them against a pasted passage by TF-IDF cosine similarity, "
        "entirely in the browser. Nothing new is recorded there: nodes are the "
        "records listed in this file, edges are the id cross-references those "
        "records already declare (a case's statutory readings, a site's analogous "
        "cases, a claim's site, an instrument's related cases), plus optional "
        "derived edges joining records that share a statute family, project type "
        "or legislative principle. The full node and edge list is therefore "
        "derivable from the datasets linked below; the search index is a build "
        "artifact and is not reproduced here.",
        "",
        "## Data files",
        "",
        f"- Legislation dataset: {REPO_URL}/blob/main/data/reference/legislation.json",
        f"- Water cases dataset: {REPO_URL}/blob/main/data/reference/cwa_investigations.json",
        f"- Water authorities (statutory readings): {REPO_URL}/blob/main/data/reference/water_authorities.json",
        f"- DC water-conflict sites: {REPO_URL}/blob/main/data/reference/dc_water_conflicts.json",
        f"- Company water claims: {REPO_URL}/blob/main/data/reference/company_water_claims.json",
        "",
    ]
    return "\n".join(lines)


# A pipe run closing the page: fittings, a gate valve, three racks. Ornament,
# not information — it carries no labels and is aria-hidden, and the opacity
# that keeps it at texture strength lives in the .footer-motif CSS rule so the
# ceiling is auditable in one place.
FOOTER_MOTIF = """
<svg class="footer-motif" viewBox="0 0 960 26" xmlns="http://www.w3.org/2000/svg"
     aria-hidden="true" focusable="false">
<g fill="none" stroke="#08519c" stroke-width="2" stroke-linecap="round">
  <path d="M 4 16 H 956"/>
  <path d="M 380 16 V 5 M 368 5 H 392"/>
  <path d="M 560 16 V 3 H 586 V 16 M 565 7 H 581 M 565 11 H 581"/>
  <path d="M 604 16 V 3 H 630 V 16 M 609 7 H 625 M 609 11 H 625"/>
  <path d="M 648 16 V 3 H 674 V 16 M 653 7 H 669 M 653 11 H 669"/>
</g>
<g fill="#08519c">
  <circle cx="140" cy="16" r="4"/>
  <circle cx="300" cy="16" r="4"/>
  <circle cx="470" cy="16" r="4"/>
  <circle cx="720" cy="16" r="4"/>
  <circle cx="900" cy="16" r="4"/>
  <path d="M 366 9 L 380 16 L 366 23 Z"/>
  <path d="M 394 9 L 380 16 L 394 23 Z"/>
</g>
</svg>
"""


def build_html() -> str:
    legislation = build_legislation_tab()
    cwa = build_cwa_tab()
    issues = build_issues_claims_tab()
    news = build_news_tab()
    solutions = build_solutions_tab()
    sources_html = build_sources_tab()
    explore = build_explore_tab()
    js = build_js()
    # Shared with the Streamlit hero — one diagram, one definition.
    schematic = dash._build_water_loop_svg()
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Data Center Water Use Tracker</title>
<meta name="description" content="Tracking data center water consumption in Virginia &amp; Ohio via public regulatory data.">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="alternate" type="text/plain" href="llms.txt" title="LLM-friendly summary">
<style>{COMPONENT_CSS}{CSS}</style>
<!-- Tab switching is the one thing on this page that needs JavaScript. Without
     it five of the seven panels were unreachable — the `hidden` attribute does
     not care why the button never fired. Unhide everything instead, so a no-JS
     reader gets one long document rather than a truncated one. -->
<noscript><style>.tabpanel[hidden]{{display:block}}</style></noscript>
</head>
<body>
<div class="wrap">
  <h1>Data Center Water Use Tracker</h1>
  <p class="tagline">Tracking data center water consumption in <strong>Virginia</strong> &amp;
  <strong>Ohio</strong> via public regulatory data.</p>

  {schematic}

  <div class="tabs" role="tablist">
    <button class="tab" role="tab" data-tab="legislation" aria-selected="true">Legislation</button>
    <button class="tab" role="tab" data-tab="cwa" aria-selected="false">Water Cases</button>
    <button class="tab" role="tab" data-tab="issues" aria-selected="false">Issues &amp; Claims</button>
    <button class="tab" role="tab" data-tab="news" aria-selected="false">News</button>
    <button class="tab" role="tab" data-tab="solutions" aria-selected="false">Solutions</button>
    <button class="tab" role="tab" data-tab="sources" aria-selected="false">Sources</button>
    <button class="tab" role="tab" data-tab="explore" aria-selected="false">Explore</button>
  </div>

  <div class="tabpanel" id="panel-legislation" role="tabpanel">{legislation}</div>
  <div class="tabpanel" id="panel-cwa" role="tabpanel" hidden>{cwa}</div>
  <div class="tabpanel" id="panel-issues" role="tabpanel" hidden>{issues}</div>
  <div class="tabpanel" id="panel-news" role="tabpanel" hidden>{news}</div>
  <div class="tabpanel" id="panel-solutions" role="tabpanel" hidden>{solutions}</div>
  <div class="tabpanel" id="panel-sources" role="tabpanel" hidden>{sources_html}</div>
  <div class="tabpanel" id="panel-explore" role="tabpanel" hidden>{explore}</div>

  {FOOTER_MOTIF}
  <p class="src-note">Static build {built} · Sources: EPA ECHO DMR, VA DEQ, Ohio EPA,
  Loudoun Water. Data center cooling water tracked via receiving WWTP flow ·
  <a href="llms.txt">llms.txt</a> (LLM-friendly summary) ·
  <a href="{REPO_URL}" target="_blank" rel="noopener">source</a></p>
</div>
<script src="{CHARTJS_URL}" integrity="{CHARTJS_SRI}" crossorigin="anonymous"></script>
<script>{js}</script>
</body>
</html>
"""


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(build_html(), encoding="utf-8")
    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"Wrote {OUT_PATH} ({size_kb:.0f} KB)")
    LLMS_TXT_PATH.write_text(build_llms_txt(), encoding="utf-8")
    print(f"Wrote {LLMS_TXT_PATH} ({LLMS_TXT_PATH.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
