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
    cards = "".join(dash._build_bill_card_html(b) for b in sorted_bills)
    summary = dash._legislation_status_summary(bills)
    last_updated = payload.get("last_updated") or "unknown"

    return f"""
<section class="panel">
  <h2>Data Center Water Legislation Tracker</h2>
  <p class="lead">State, federal, and local action on data center water (and energy)
  disclosure — bills, signed laws, agency rulemakings, and major zoning ordinances.
  Enacted laws are the next mandatory data sources to come online.</p>
  <p class="count-line"><strong>{len(bills)} bills tracked</strong> — {esc(summary)}</p>
  {cards}
  <p class="src-note">Dataset last updated {esc(last_updated)}. Verification status for
  each entry is tracked in the underlying JSON; treat any not flagged verified=true
  there as secondary-sourced.</p>
</section>

<details class="lazy">
  <summary>Show Policy &amp; Disclosure Timeline</summary>
  {build_timeline()}
</details>

<details class="lazy">
  <summary>Show Company Water Claims (29 verbatim operator quotes)</summary>
  {build_company_claims()}
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
        '<section class="panel"><h3>Company Water Claims</h3>',
        intro,
        f'<p class="count-line"><strong>{len(claims)} claims</strong> · '
        f'{company_count} companies · {delivered_count} delivered-vs-promised '
        'assessments</p>',
    ]
    rendered: list[str] = []
    status_map = {
        "delivered": ("Delivered", "delivered"),
        "partial": ("Partial", "partial"),
        "contested": ("Contested", "partial"),
        "shortfall": ("Shortfall", "shortfall"),
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
            f'<div class="claim-card"><p class="claim-quote">“{statement}”</p>'
            f'{caption}{box}</div>'
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


def build_cwa_tab() -> str:
    payload = dash.load_cwa_investigations()
    cases = payload.get("cases", [])
    historical = [c for c in cases if c.get("display_section", "historical") == "historical"]
    potential = [c for c in cases if c.get("display_section") == "potential"]
    stats = dash._cwa_datacenter_insights(historical)
    total = stats["total"]
    last_updated = payload.get("last_updated") or "unknown"

    insights = ""
    if total:
        insights = f"""
<div class="insights">
  <h4>What this record tells data centers</h4>
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
      stormwater permit.</li>
  </ul>
</div>"""

    theories = dash._build_cwa_theories_html(dash.CWA_APPLICATION_THEORIES)
    explainer = md(dash._cwa_statute_explainer_md())

    # Section 1: historical cases — category filter checkboxes.
    # Adjacent cases all moved to section 2, so filters cover datacenter/industrial/precedent.
    hist_cats = sorted(
        {c.get("category") for c in historical if c.get("category")},
        key=lambda k: dash.CWA_CATEGORY_ORDER.get(k, 9),
    )
    cat_boxes = "".join(
        f'<label class="chip-check"><input type="checkbox" class="cwa-cat" '
        f'value="{k}" checked> {esc(dash.CWA_CATEGORY_LABELS.get(k, k))}</label>'
        for k in hist_cats
    )

    sorted_hist = sorted(
        historical,
        key=lambda c: (
            dash.CWA_CATEGORY_ORDER.get(c.get("category"), 9),
            -dash._cwa_year_end(c.get("year", "")),
        ),
    )
    hist_cards = "".join(
        f'<div class="cwa-case" data-category="{esc(c.get("category",""))}" '
        f'data-yearend="{dash._cwa_year_end(c.get("year",""))}">'
        f'{dash._build_cwa_case_html(c)}</div>'
        for c in sorted_hist
    )

    # Section 2: potential/active cases — no client-side filter needed (12 cards).
    sorted_pot = sorted(
        potential,
        key=lambda c: (
            dash.CWA_CATEGORY_ORDER.get(c.get("category"), 9),
            -dash._cwa_year_end(c.get("year", "")),
        ),
    )
    pot_cards = "".join(
        f'<div class="cwa-potential-case">'
        f'{dash._build_cwa_case_html(c)}</div>'
        for c in sorted_pot
    )

    cat_labels_json = json.dumps(dash.CWA_CATEGORY_LABELS)
    cat_order_json = json.dumps(dash.CWA_CATEGORY_ORDER)

    return f"""
<section class="panel">
  <h2>Clean Water Act — Historical Record &amp; Potential Exposure</h2>
  <p class="lead">Two views on the CWA and data centers: the enforcement record that has
  actually built (penalties, settlements, court rulings), and specific named sites where
  active proceedings or matching circumstances suggest CWA exposure is next.</p>
  {insights}
  <details class="lazy">
    <summary>Prioritized CWA-application theories — what could attach to a data center</summary>
    <section class="panel">{theories}
    <p class="src-note">Full write-up with primary-source citations:
    docs/cwa-enforcement-and-data-centers.md</p></section>
  </details>
  <details class="lazy">
    <summary>What is a Clean Water Act investigation? — statute, authority, and why it's deployed</summary>
    <div class="explainer-md">{explainer}</div>
  </details>

  <h3>Part 1 — Historical CWA Enforcement Record</h3>
  <p><strong>{len(historical)} cases</strong> — enforcement actions, penalties, settlements,
  and landmark court rulings that have <strong>actually occurred</strong>.
  <strong>Industrial cases are legal analogs</strong> — the enforcement pattern for
  operations similar to data centers, but against other industries, not data centers.
  Precedent rulings define CWA's legal scope for future enforcement.</p>
  <div class="cwa-filters">
    <div class="cwa-cats">{cat_boxes}</div>
    <label class="chip-check"><input type="checkbox" id="cwa-recent"> 2020 onward only</label>
  </div>
  <p class="count-line" id="cwa-count"></p>
  <div id="cwa-cases">{hist_cards}</div>

  <hr>
  <h3>Part 2 — Active &amp; Potential CWA Exposure at Named Data Center Sites</h3>
  <p><strong>{len(potential)} named data center sites</strong> where regulatory proceedings
  are active (pending permit applications, ongoing investigations, active citizen suits)
  or where the factual circumstances match the historical enforcement patterns above —
  but <strong>no formal CWA enforcement action has been issued yet</strong>.
  Use the theories panel above to trace which CWA hook applies to each site.</p>
  <div id="cwa-potential">{pot_cards}</div>

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
# Assembly
# --------------------------------------------------------------------------

CSS = """
:root{--ink:#1a1a2e;--blue:#08519c;--blue2:#3182bd;--muted:#4b5563}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  color:var(--ink);line-height:1.55;
  background-color:#f5f9fc;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 120'><g fill='%2308519c' fill-opacity='0.055'><ellipse cx='22' cy='18' rx='2' ry='3'/><ellipse cx='88' cy='42' rx='1.6' ry='2.4'/><ellipse cx='55' cy='78' rx='2.2' ry='3.3'/><ellipse cx='100' cy='100' rx='1.4' ry='2.1'/></g></svg>");
  background-attachment:fixed;
}
.wrap{max-width:1040px;margin:0 auto;padding:1.25rem 1.25rem 4rem}
h1{font-size:1.9rem;margin:0 0 .2rem;padding-bottom:.4rem;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 60 6' preserveAspectRatio='none'><path d='M0 3 Q 15 0, 30 3 T 60 3' fill='none' stroke='%233182bd' stroke-width='1.2' stroke-opacity='0.55'/></svg>");
  background-repeat:repeat-x;background-position:left bottom;background-size:60px 6px}
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
.tab{appearance:none;border:0;background:none;font:inherit;cursor:pointer;
  padding:.6rem 1rem;color:var(--muted);border-bottom:3px solid transparent;margin-bottom:-2px;
  font-weight:600;min-height:44px}
.tab[aria-selected="true"]{color:var(--blue);border-bottom-color:var(--blue)}
.tabpanel[hidden]{display:none}

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

@media (max-width:760px){
  .wrap{padding:.75rem .75rem 3rem}
  h1{font-size:1.35rem}
  .hero{grid-template-columns:repeat(2,1fr)}
  .chart-wrap{height:300px}
}
"""


def build_js(chart_data: dict) -> str:
    return """
// --- Tabs ---
const tabs = document.querySelectorAll('.tab');
const panels = document.querySelectorAll('.tabpanel');
tabs.forEach(t => t.addEventListener('click', () => {
  tabs.forEach(x => x.setAttribute('aria-selected', x === t ? 'true' : 'false'));
  panels.forEach(p => p.hidden = (p.id !== 'panel-' + t.dataset.tab));
  if (t.dataset.tab === 'data') initCharts();
}));

// --- CWA filtering ---
const cwaCount = document.getElementById('cwa-count');
function applyCwaFilter(){
  const cats = new Set([...document.querySelectorAll('.cwa-cat:checked')].map(c => c.value));
  const recent = document.getElementById('cwa-recent').checked;
  const counts = {};
  let shown = 0;
  document.querySelectorAll('.cwa-case').forEach(el => {
    const cat = el.dataset.category;
    const ye = parseInt(el.dataset.yearend, 10) || 0;
    const ok = cats.has(cat) && (!recent || ye >= 2020);
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
document.querySelectorAll('.cwa-cat, #cwa-recent').forEach(c =>
  c.addEventListener('change', applyCwaFilter));
if (cwaCount) applyCwaFilter();

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

// --- Charts (lazy: only build once the Data tab is shown) ---
const CHART_DATA = __CHART_DATA__;
let chartsBuilt = false;
const PALETTE = ['#08519c','#3182bd','#6baed6','#9ecae1','#c6dbef'];
function initCharts(){
  if (chartsBuilt || typeof Chart === 'undefined') return;
  chartsBuilt = true;
  const flow = CHART_DATA.flow;
  const flowEl = document.getElementById('flowChart');
  if (flowEl && flow.series.length){
    const ds = flow.series.map((s,i) => ({
      label: s.name, data: s.data, borderColor: PALETTE[i % PALETTE.length],
      backgroundColor: PALETTE[i % PALETTE.length], tension:.2, spanGaps:true, pointRadius:3
    }));
    if (flow.limit != null){
      ds.push({label:'Permit Limit ('+flow.limit+' MGD)',
        data: flow.labels.map(()=>flow.limit), borderColor:'#c41e3a', borderDash:[6,4],
        pointRadius:0, borderWidth:1.5});
    }
    new Chart(flowEl, {type:'line', data:{labels:flow.labels, datasets:ds},
      options:{responsive:true, maintainAspectRatio:false,
        plugins:{legend:{position:'bottom'}},
        scales:{y:{title:{display:true,text:'Flow (MGD)'}},
                x:{title:{display:true,text:'Monitoring Period'}}}}});
  }
  const src = CHART_DATA.source;
  const srcEl = document.getElementById('sourceChart');
  if (srcEl && src.labels.length){
    new Chart(srcEl, {type:'bar',
      data:{labels:src.labels, datasets:[{label:'Records', data:src.values,
        backgroundColor:'#3182bd'}]},
      options:{indexAxis:'y', responsive:true, maintainAspectRatio:false,
        plugins:{legend:{display:false}, title:{display:true, text:'Records by Source'}}}});
  }
}
// Charts inside <details> need a resize nudge when first opened.
document.querySelectorAll('details.lazy').forEach(d =>
  d.addEventListener('toggle', () => { if (d.open) initCharts(); }));
""".replace("__CHART_DATA__", json.dumps(chart_data))


def build_html() -> str:
    legislation = build_legislation_tab()
    cwa = build_cwa_tab()
    data_html, chart_data = build_data_tab()
    js = build_js(chart_data)
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Data Center Water Use Tracker</title>
<meta name="description" content="Tracking data center water consumption in Virginia &amp; Ohio via public regulatory data.">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<style>{COMPONENT_CSS}{CSS}</style>
</head>
<body>
<div class="wrap">
  <h1>Data Center Water Use Tracker</h1>
  <p class="tagline">Tracking data center water consumption in <strong>Virginia</strong> &amp;
  <strong>Ohio</strong> via public regulatory data.</p>

  <div class="tabs" role="tablist">
    <button class="tab" role="tab" data-tab="legislation" aria-selected="true">Legislation</button>
    <button class="tab" role="tab" data-tab="cwa" aria-selected="false">CWA Cases</button>
    <button class="tab" role="tab" data-tab="data" aria-selected="false">Data</button>
  </div>

  <div class="tabpanel" id="panel-legislation" role="tabpanel">{legislation}</div>
  <div class="tabpanel" id="panel-cwa" role="tabpanel" hidden>{cwa}</div>
  <div class="tabpanel" id="panel-data" role="tabpanel" hidden>{data_html}</div>

  <p class="src-note">Static build {built} · Sources: EPA ECHO DMR, VA DEQ, Ohio EPA,
  Loudoun Water. Data center cooling water tracked via receiving WWTP flow.</p>
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


if __name__ == "__main__":
    main()
