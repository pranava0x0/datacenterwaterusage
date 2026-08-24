"""Data Center Water Use Tracker — Insights Dashboard

Responsive Streamlit dashboard for tracking data center water consumption.
Adapts layout for mobile, tablet, and desktop viewports.

Run with: streamlit run dashboard.py
"""

from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.device import (
    DeviceType,
    get_chart_config,
    get_device_type,
    inject_responsive_css,
)
from utils.equivalents import annual_gallons_to_households

# The curated-reference layer lives in `refdata/` (extracted 2026-07-25) so the
# Streamlit app, build_site.py, the migration scripts and the tests share one
# definition of the data, its taxonomies and its cross-reference graph. Names
# are re-exported here, so `dashboard.load_legislation` and
# `dashboard.CWA_CASE_TYPE_LABELS` still resolve for existing callers.
from refdata.loaders import (  # noqa: F401
    COMPANY_WATER_CLAIMS_PATH,
    CWA_INVESTIGATIONS_PATH,
    DC_WATER_CONFLICTS_PATH,
    LEGISLATION_PATH,
    WATER_AUTHORITIES_PATH,
    WATER_NEWS_PATH,
    WATER_SOLUTIONS_PATH,
    file_signature as _file_signature,
    load_company_water_claims,
    load_cwa_investigations,
    load_dc_water_conflicts,
    load_legislation,
    load_water_authorities,
    load_water_news,
    load_water_solutions,
)
from refdata.graph import (  # noqa: F401
    EDGE_KIND_LABELS,
    KIND_COLORS as GRAPH_KIND_COLORS,
    build_graph,
    payload_json as graph_payload_json,
)
from refdata.registry import (  # noqa: F401
    KIND_TABS,
    Ref,
    bill_anchor as _bill_anchor,
    build_registry,
    case_caption as _cwa_case_caption,
    resolve as resolve_ref,
)
from refdata.taxonomies import (  # noqa: F401
    AUTHORITY_KIND_LABELS,
    CLAIM_TYPE_LABELS,
    COLOR_SEQUENCE,
    COLORS,
    CWA_CASE_TYPE_LABELS,
    CWA_CATEGORY_LABELS,
    CWA_CATEGORY_ORDER,
    CWA_STATUS_COLORS,
    CWA_STATUS_LABELS,
    DELIVERED_STATUS_COLORS,
    DELIVERED_STATUS_LABELS,
    INSTRUMENT_TYPE_COLORS,
    INSTRUMENT_TYPE_LABELS,
    ISSUE_TYPE_DESCRIPTIONS,
    ISSUE_TYPE_LABELS,
    LEGISLATION_LEVEL_LABELS,
    LEGISLATION_PRINCIPLE_DESCRIPTIONS,
    LEGISLATION_SCOPE_LABELS,
    LEGISLATION_STATUS_BADGE_COLORS,
    LEGISLATION_STATUS_LABELS,
    LEGISLATION_STATUS_ORDER,
    NEWS_TAG_COLORS,
    NEWS_TAG_LABELS,
    OUTCOME_TYPE_LABELS,
    SOLUTION_ACTOR_LABELS,
    SOLUTION_STATUS_COLORS,
    SOLUTION_STATUS_LABELS,
    WATER_STATUTE_COLORS,
    WATER_STATUTE_ORDER,
)

# --- Config ---

BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "data" / "output" / "results.csv"
JSON_PATH = BASE_DIR / "data" / "output" / "results.json"


# --- Data Loading ---
#
# The seven curated-reference loaders live in refdata.loaders (imported above).
# Only the results.csv loader stays here: it is the scraper pipeline's output,
# it returns a DataFrame, and it is the one loader Streamlit's cache still
# serves better than a plain memo (the parse is ~100× the cost of a JSON read).


@st.cache_data
def _load_data_cached(signature: tuple) -> pd.DataFrame:
    """Parse and clean results.csv. Keyed on the file signature so the cache
    busts on change (the ``signature`` arg is part of the cache key)."""
    if not CSV_PATH.exists():
        return pd.DataFrame()

    df = pd.read_csv(CSV_PATH)

    df["document_date"] = pd.to_datetime(df["document_date"], errors="coerce")
    df["scraped_at"] = pd.to_datetime(df["scraped_at"], errors="coerce")
    # Vectorized MGD extraction — one regex pass over the whole column instead
    # of a per-row Python call. Mirrors _extract_flow_mgd (kept as the scalar
    # helper for tests): non-matches and unparseable captures coerce to NaN,
    # exactly what the row-wise version returns as None.
    df["flow_mgd"] = pd.to_numeric(
        df["extracted_water_metric"]
        .astype(str)
        .str.extract(r"([\d.]+)\s*MGD", flags=re.IGNORECASE, expand=False),
        errors="coerce",
    )

    date_mask = df["document_date"].notna()
    df["monitoring_month"] = ""
    df.loc[date_mask, "monitoring_month"] = (
        df.loc[date_mask, "document_date"].dt.to_period("M").astype(str)
    )

    df["record_type"] = df["source_portal"].apply(_classify_source)
    return df


def load_data() -> pd.DataFrame:
    """Load and clean results data from CSV (cached; re-reads only on change)."""
    return _load_data_cached(_file_signature(CSV_PATH))


def _extract_flow_mgd(metric_str: str) -> float | None:
    """Extract MGD flow value from metric string."""
    if not isinstance(metric_str, str):
        return None
    if "MGD" not in metric_str.upper():
        return None

    match = re.search(r"([\d.]+)\s*MGD", metric_str, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None


def _classify_source(portal: str) -> str:
    """Classify record source into human-readable categories."""
    if "echo_dmr" in str(portal):
        return "EPA ECHO Flow Data"
    if "arcgis" in str(portal):
        return "Permit Metadata"
    if "legistar" in str(portal):
        return "Legislative Records"
    if "acfr" in str(portal):
        return "Financial Reports"
    if "naics" in str(portal):
        return "Facility Discovery"
    if "general_permit" in str(portal):
        return "General Permit Tracker"
    return "Other"



# --- Page Config ---

st.set_page_config(
    page_title="Data Center Water Use Tracker",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# --- Filtering ---


def _apply_filters(
    df: pd.DataFrame,
    selected_states: list[str],
    selected_sources: list[str] | None = None,
    date_range: tuple | None = None,
    flow_range: tuple[float, float] | None = None,
) -> pd.DataFrame:
    """Apply filter selections to dataframe."""
    filtered = df.copy()
    if selected_states:
        filtered = filtered[filtered["state"].isin(selected_states)]
    if selected_sources:
        filtered = filtered[filtered["record_type"].isin(selected_sources)]
    if date_range and len(date_range) == 2:
        start, end = date_range
        filtered = filtered[
            (filtered["document_date"].isna())
            | (
                (filtered["document_date"].dt.date >= start)
                & (filtered["document_date"].dt.date <= end)
            )
        ]
    if flow_range:
        filtered = filtered[
            (filtered["flow_mgd"].isna())
            | (
                (filtered["flow_mgd"] >= flow_range[0])
                & (filtered["flow_mgd"] <= flow_range[1])
            )
        ]
    return filtered


def render_inline_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Inline filter popover used inside the Data tab on all viewports."""
    with st.popover("Filter data"):
        states = sorted(df["state"].dropna().unique().tolist())
        selected_states = st.multiselect(
            "State", states, default=states, key="data_state_filter"
        )

        date_range = None
        if df["document_date"].notna().any():
            min_date = df["document_date"].min()
            max_date = df["document_date"].max()
            if pd.notna(min_date) and pd.notna(max_date):
                date_range = st.date_input(
                    "Date Range",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date,
                    key="data_date_filter",
                )

    return _apply_filters(df, selected_states, date_range=date_range)


def render_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    """Sidebar filters for tablet/desktop."""
    st.sidebar.title("Filters")

    states = sorted(df["state"].dropna().unique().tolist())
    selected_states = st.sidebar.multiselect(
        "State", states, default=states, help="Filter by state"
    )

    sources = sorted(df["record_type"].dropna().unique().tolist())
    selected_sources = st.sidebar.multiselect("Data Source", sources, default=sources)

    date_range = None
    if df["document_date"].notna().any():
        min_date = df["document_date"].min()
        max_date = df["document_date"].max()
        if pd.notna(min_date) and pd.notna(max_date):
            date_range = st.sidebar.date_input(
                "Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
            )

    flow_range = None
    if df["flow_mgd"].notna().any():
        min_flow = float(df["flow_mgd"].min())
        max_flow = float(df["flow_mgd"].max())
        flow_range = st.sidebar.slider(
            "Flow Range (MGD)",
            min_value=min_flow,
            max_value=max_flow,
            value=(min_flow, max_flow),
        )

    filtered = _apply_filters(
        df, selected_states, selected_sources, date_range, flow_range
    )

    n_filtered = len(filtered)
    n_total = len(df)
    if n_filtered < n_total:
        st.sidebar.info(f"Showing {n_filtered} of {n_total} records")

    # Source breakdown (text summary in sidebar)
    st.sidebar.markdown("---")
    source_counts = filtered["record_type"].value_counts().head(5)
    for source, count in source_counts.items():
        st.sidebar.caption(f"{source}: **{count}**")

    # Downloads
    st.sidebar.markdown("---")
    if not filtered.empty:
        csv_data = filtered.to_csv(index=False)
        st.sidebar.download_button(
            "Download CSV", csv_data, "dc_water_data.csv", "text/csv"
        )

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "**Sources:** EPA ECHO DMR, VA DEQ, Ohio EPA, Loudoun Water. "
        "Data center cooling water tracked via receiving WWTP flow."
    )
    st.sidebar.caption(
        f"Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} · "
        f"{len(df)} records"
    )

    return filtered


# --- Header water-loop schematic (shared with build_site.py) ---

# One diagram, two surfaces. It answers the question every visitor asks before
# the first card ("how does a data center use water, and where is it measured?")
# and, in the same picture, explains why this project's primary source is EPA
# ECHO DMR data from *receiving* wastewater plants rather than anything filed
# by the operator: the sewer leg is the only leg with a permit on it.
#
# Drawing notes:
#  - Coordinates are a 960x124 box, so 1 unit ~= 1 px at the site's content
#    width and label sizes can be reasoned about directly (11 units ~= 0.7rem).
#  - The pipe run is an OPEN path (intake -> outfall -> back up into the river),
#    not a closed rectangle: the river closes the loop, not a pipe.
#  - Everything except the flow animation uses presentation attributes rather
#    than the <style> block, so the diagram still renders correctly on any
#    surface that strips <style> — it just stops moving.
_WL_PIPE_PATH = "M 50 54 H 856 V 96 H 20 V 72"
_WL_FONT = (
    "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
)

# The one sanctioned animation on either surface (DESIGN.md §3/§12): pale
# dashes drifting along the pipe. The offset is a whole number of dash periods
# (28 = 6 + 22) so the loop has no visible jump, and 24 s over ~1,700 units is
# roughly a slow walk — present in peripheral vision, never competing with the
# data. Reduced-motion parks it as static direction ticks.
_WL_ANIM_CSS = (
    ".wl-flow{stroke-dasharray:6 22;animation:wl-drift 24s linear infinite}"
    "@keyframes wl-drift{to{stroke-dashoffset:-1680}}"
    "@media (prefers-reduced-motion:reduce){.wl-flow{animation:none}}"
)


def _build_water_loop_svg() -> str:
    """The header water-loop schematic, as a self-contained SVG fragment.

    Pure: no Streamlit, no data access — ``build_site.py`` inlines the same
    string it returns, so the deployed page and the local app cannot drift.
    """
    return f"""<div class="schematic">
<svg viewBox="0 0 960 124" role="img" aria-labelledby="wl-title wl-desc"
     xmlns="http://www.w3.org/2000/svg" font-family="{_WL_FONT}">
<title id="wl-title">How water moves through a data center</title>
<desc id="wl-desc">River or wellfield intake, drinking-water treatment, the data
center hall, a closed chiller loop, a cooling tower where evaporation leaves the
basin, then blowdown to the sewer, the wastewater plant, and treated effluent
back to the river.</desc>
<style>{_WL_ANIM_CSS}</style>
<g fill="none" stroke-linecap="round" stroke-linejoin="round">
  <!-- Sewer main drawn under the pipe run so the flow dashes ride over it:
       heavier stroke because this leg is the metered one. -->
  <path d="M 640 54 H 740" stroke="#08519c" stroke-width="5.5"/>
  <path d="{_WL_PIPE_PATH}" stroke="#3182bd" stroke-width="3"/>
  <path class="wl-flow" d="{_WL_PIPE_PATH}" stroke="#ffffff" stroke-width="1.6"
        stroke-opacity="0.35"/>
  <!-- River / wellfield, with a screened intake standing in it. The label sits
       above this glyph, not below it like every other station: the return leg
       runs underneath, discharging back into the same water. -->
  <path d="M 6 40 Q 14 34 22 40 T 38 40 T 54 40 T 70 40" stroke="#6baed6" stroke-width="1.6"/>
  <path d="M 6 54 Q 14 48 22 54 T 38 54" stroke="#3182bd" stroke-width="1.8"/>
  <path d="M 6 68 Q 14 62 22 68 T 38 68 T 54 68 T 70 68" stroke="#6baed6" stroke-width="1.6"/>
  <rect x="38" y="46" width="12" height="16" fill="#ffffff" stroke="#3182bd" stroke-width="1.4"/>
  <path d="M 41 51 H 47 M 41 57 H 47" stroke="#6baed6" stroke-width="1.2"/>
  <path d="M 16 77 L 20 70 L 24 77 Z" fill="#3182bd" stroke="none"/>
  <!-- Drinking-water treatment: two clarifiers and a filter bed. -->
  <rect x="120" y="38" width="80" height="32" rx="2" fill="#ffffff" stroke="#3182bd" stroke-width="1.6"/>
  <circle cx="142" cy="54" r="7" stroke="#6baed6" stroke-width="1.2"/>
  <circle cx="166" cy="54" r="7" stroke="#6baed6" stroke-width="1.2"/>
  <rect x="180" y="46" width="12" height="16" stroke="#6baed6" stroke-width="1.2"/>
  <!-- Data center hall: three slotted racks. -->
  <rect x="246" y="32" width="154" height="44" rx="3" fill="#ffffff" stroke="#08519c" stroke-width="1.8"/>
  <rect x="262" y="39" width="32" height="30" fill="#eff3ff" stroke="#3182bd" stroke-width="1.2"/>
  <path d="M 267 46 H 289 M 267 52 H 289 M 267 58 H 289 M 267 64 H 289" stroke="#6baed6" stroke-width="1.5"/>
  <rect x="306" y="39" width="32" height="30" fill="#eff3ff" stroke="#3182bd" stroke-width="1.2"/>
  <path d="M 311 46 H 333 M 311 52 H 333 M 311 58 H 333 M 311 64 H 333" stroke="#6baed6" stroke-width="1.5"/>
  <rect x="350" y="39" width="32" height="30" fill="#eff3ff" stroke="#3182bd" stroke-width="1.2"/>
  <path d="M 355 46 H 377 M 355 52 H 377 M 355 58 H 377 M 355 64 H 377" stroke="#6baed6" stroke-width="1.5"/>
  <!-- Closed chiller loop: the water inside recirculates, so only makeup in
       and blowdown out ever cross this boundary. Arrows show circulation. -->
  <rect x="428" y="36" width="88" height="36" rx="18" fill="#ffffff" stroke="#3182bd" stroke-width="1.6"/>
  <path d="M 466 32 L 476 36 L 466 40 Z" fill="#3182bd" stroke="none"/>
  <path d="M 478 68 L 468 72 L 478 76 Z" fill="#3182bd" stroke="none"/>
  <!-- Cooling tower, hyperboloid silhouette, with the drift rising off it. -->
  <path d="M 556 76 C 566 62 566 46 562 34 L 610 34 C 606 46 606 62 616 76 Z"
        fill="#ffffff" stroke="#08519c" stroke-width="1.8"/>
  <path d="M 550 76 H 622 M 556 68 H 616" stroke="#08519c" stroke-width="1.6"/>
  <path d="M 568 32 C 564 26 572 22 568 16 C 565 11 570 9 568 6" stroke="#6baed6" stroke-width="1.5"/>
  <path d="M 586 32 C 582 25 590 20 586 13 C 583 9 588 7 586 4" stroke="#6baed6" stroke-width="1.5"/>
  <path d="M 604 32 C 600 26 608 22 604 16 C 601 11 606 9 604 6" stroke="#6baed6" stroke-width="1.5"/>
  <path d="M 630 20 H 612" stroke="#6baed6" stroke-width="1.2"/>
  <!-- Wastewater plant: clarifiers plus an aeration basin. -->
  <rect x="750" y="38" width="92" height="32" rx="2" fill="#ffffff" stroke="#08519c" stroke-width="1.8"/>
  <circle cx="770" cy="54" r="8" stroke="#6baed6" stroke-width="1.2"/>
  <circle cx="794" cy="54" r="8" stroke="#6baed6" stroke-width="1.2"/>
  <rect x="810" y="46" width="24" height="16" stroke="#6baed6" stroke-width="1.2"/>
  <path d="M 813 55 q 3 -4 6 0 t 6 0 t 6 0" stroke="#6baed6" stroke-width="1.2"/>
  <!-- Fittings at the joints, the same motif the page texture carries. -->
  <circle cx="640" cy="54" r="4" fill="#08519c" stroke="none"/>
  <circle cx="740" cy="54" r="4" fill="#08519c" stroke="none"/>
  <circle cx="856" cy="54" r="4" fill="#3182bd" stroke="none"/>
  <circle cx="20" cy="96" r="4" fill="#3182bd" stroke="none"/>
</g>
<g font-size="11" fill="#4b5563" text-anchor="middle">
  <text x="46" y="30">river / wellfield</text>
  <text x="160" y="86">treatment plant</text>
  <text x="323" y="86">data center hall</text>
  <text x="472" y="86">closed chiller loop</text>
  <text x="586" y="86">cooling tower</text>
  <text x="690" y="86">blowdown &#8594; sewer</text>
  <text x="796" y="86">wastewater plant</text>
  <text x="230" y="113" font-size="10">treated effluent returns to the river</text>
</g>
<g font-size="10" fill="#08519c" font-weight="600">
  <text x="634" y="16">evaporation is the consumptive loss &#8212;</text>
  <text x="634" y="28">this water leaves the basin, not the sewer</text>
  <circle cx="422" cy="110" r="3" fill="#08519c"/>
  <text x="432" y="113">the sewer leg is metered on the receiving plant&#8217;s NPDES permit &#8212; that is where the data shows up</text>
</g>
</svg>
</div>"""


# --- Hero Metrics ---


def render_hero(df: pd.DataFrame):
    """Full 4-metric hero row for desktop."""
    flow_records = df[df["flow_mgd"].notna()]
    total_records = len(df)
    unique_permits = df["permit_number"].dropna().nunique()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if len(flow_records) > 0:
            st.metric("Avg Flow (MGD)", f"{flow_records['flow_mgd'].mean():.1f}")
        else:
            st.metric("Avg Flow", "---")

    with col2:
        if len(flow_records) > 0:
            st.metric("Peak Flow (MGD)", f"{flow_records['flow_mgd'].max():.1f}")
        else:
            st.metric("Peak Flow", "---")

    with col3:
        st.metric("Records", f"{total_records:,}")

    with col4:
        st.metric("Permits", f"{unique_permits}")


def render_hero_compact(df: pd.DataFrame):
    """2-metric hero for mobile/tablet — only the key numbers."""
    flow_records = df[df["flow_mgd"].notna()]

    col1, col2 = st.columns(2)
    with col1:
        if len(flow_records) > 0:
            st.metric("Avg Flow (MGD)", f"{flow_records['flow_mgd'].mean():.1f}")
        else:
            st.metric("Avg Flow", "---")
    with col2:
        if len(flow_records) > 0:
            st.metric("Peak Flow (MGD)", f"{flow_records['flow_mgd'].max():.1f}")
        else:
            st.metric("Peak Flow", "---")


# --- Charts ---


def render_flow_chart(df: pd.DataFrame, cfg: dict):
    """WWTP flow time series with permit limit overlay."""
    flow_df = df[
        (df["flow_mgd"].notna()) & (df["document_date"].notna())
    ].copy()

    if flow_df.empty:
        st.info("No flow data yet. Run the EPA ECHO scraper to collect DMR data.")
        return

    flow_df = flow_df.sort_values("document_date")
    flow_df = flow_df.drop_duplicates(
        subset=["permit_number", "document_date"], keep="last"
    )

    fig = go.Figure()

    for permit_id, group in flow_df.groupby("permit_number"):
        facility_name = (
            group["company_llc_name"].iloc[0]
            if not group["company_llc_name"].isna().all()
            else permit_id
        )
        fig.add_trace(
            go.Scatter(
                x=group["document_date"],
                y=group["flow_mgd"],
                mode="lines+markers",
                name=f"{facility_name} ({permit_id})",
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Date: %{x|%B %Y}<br>"
                    "Flow: %{y:.1f} MGD<br>"
                    "<extra></extra>"
                ),
                text=[facility_name] * len(group),
                line=dict(width=cfg["line_width"]),
                marker=dict(size=cfg["marker_size"]),
            )
        )

    if "VA0091383" in flow_df["permit_number"].values:
        # Build hline kwargs conditionally so we never pass annotation_text=None,
        # which Plotly silently replaces with the placeholder string "new text"
        # (visibly rendered in the chart corner on mobile prior to this fix).
        hline_kwargs = {
            "y": 11.0,
            "line_dash": "dash",
            "line_color": COLORS["danger"],
        }
        if cfg["show_legend"]:
            hline_kwargs["annotation_text"] = "Permit Limit (11 MGD)"
            hline_kwargs["annotation_position"] = "top right"
        fig.add_hline(**hline_kwargs)

    title = (
        "Monthly WWTP Flow"
        if cfg["font_size"] <= 10
        else "Monthly WWTP Flow — Data Center Corridors"
    )

    fig.update_layout(
        title=title,
        xaxis_title="Monitoring Period",
        yaxis_title="Flow (MGD)",
        template="plotly_white",
        height=cfg["flow_height"],
        font=dict(size=cfg["font_size"]),
        title_font_size=cfg["title_font_size"],
        showlegend=cfg["show_legend"],
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=cfg["legend_y"],
            xanchor="center",
            x=0.5,
        ),
        hovermode=cfg["hovermode"],
        margin=cfg["margin"],
    )

    st.plotly_chart(fig, use_container_width=True, theme=None)


def render_source_breakdown(df: pd.DataFrame, cfg: dict):
    """Horizontal bar chart of records by source type."""
    source_counts = df["record_type"].value_counts().reset_index()
    source_counts.columns = ["Source", "Records"]

    fig = px.bar(
        source_counts,
        x="Records",
        y="Source",
        orientation="h",
        color="Records",
        color_continuous_scale=["#bdd7e7", "#08519c"],
        title="Records by Source",
    )
    fig.update_layout(
        template="plotly_white",
        height=cfg["source_height"],
        showlegend=False,
        coloraxis_showscale=False,
        font=dict(size=cfg["font_size"]),
        margin=cfg["margin"],
    )
    st.plotly_chart(fig, use_container_width=True, theme=None)


def render_seasonal_heatmap(df: pd.DataFrame, cfg: dict):
    """Month-by-year heatmap of flow data."""
    flow_df = df[df["flow_mgd"].notna()].copy()
    if flow_df.empty:
        return

    flow_df["year"] = flow_df["document_date"].dt.year
    flow_df["month"] = flow_df["document_date"].dt.month

    pivot = flow_df.pivot_table(
        values="flow_mgd", index="month", columns="year", aggfunc="mean"
    )

    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=[str(c) for c in pivot.columns],
            y=[month_names[i - 1] for i in pivot.index],
            colorscale="Blues",
            hovertemplate="Year: %{x}<br>Month: %{y}<br>Flow: %{z:.1f} MGD<extra></extra>",
        )
    )

    fig.update_layout(
        title="Seasonal Flow Patterns (MGD)",
        xaxis_title="Year",
        yaxis_title="Month",
        template="plotly_white",
        height=cfg["heatmap_height"],
        font=dict(size=cfg["font_size"]),
        margin=cfg["margin"],
    )

    st.plotly_chart(fig, use_container_width=True, theme=None)


# --- Context & Education Panels ---


# Reference data for local context comparisons.
# Sources are cited inline — these are from published reports already scraped.
CONTEXT_DATA = {
    "loudoun": {
        "label": "Loudoun County, Virginia",
        "dc_water_gallons": 1_635_000_000,  # 899M potable + 736M reclaimed, ACFR 2023
        "dc_water_year": 2023,
        "utility_total_gallons": 10_700_000_000,  # ~29.3 MGD avg, Loudoun Water ACFR 2023
        "avg_household_gpd": 200,  # VA avg residential per-household
        "source": "Loudoun Water ACFR 2023",
        "source_url": "https://www.loudounwater.org/about/comprehensive-annual-financial-reports",
    },
    "pwc": {
        "label": "Prince William County, Virginia",
        "dc_count": 56,
        "dc_eru_total": 3_276,  # Total ERUs allocated to data centers
        "avg_eru_gpd": 400,  # 1 ERU = 400 GPD per PWC definition
        "dc_water_gallons": 478_296_000,  # 3276 ERU * 400 GPD * 365
        "dc_water_year": 2024,
        "utility_total_gallons": 6_500_000_000,  # ~17.8 MGD avg
        "avg_household_gpd": 200,
        "source": "PWC Industrial User Survey 2024",
        "source_url": "https://www.pwcsa.org/",
    },
    "central_ohio": {
        "label": "Central Ohio",
        "projected_dc_mgd_2030": 40,
        "projected_dc_mgd_2050": 90,
        "source": "Central Ohio Regional Water Study (March 2025)",
        "source_url": "https://epa.ohio.gov/",
    },
}

# Transparency Scorecard — metadata about each data source in the pipeline.
# disclosure_type: "mandated" (required by law), "voluntary" (published willingly),
#                  "inferred" (derived from other data)
# geo_resolution: "facility", "county", "state", "national"
# freshness: "monthly", "quarterly", "annual", "one-time", "irregular"
# confidence: "high" (direct measurement), "medium" (official but indirect),
#             "low" (estimated or projected)
SCORECARD_DATA = [
    {
        "source": "EPA ECHO DMR",
        "scraper": "epa_echo_dmr",
        "disclosure": "mandated",
        "geo_resolution": "facility",
        "freshness": "monthly",
        "confidence": "high",
        "notes": "Federal NPDES discharge monitoring reports from WWTPs",
    },
    {
        "source": "Loudoun Water ACFR",
        "scraper": "va_loudoun_acfr",
        "disclosure": "mandated",
        "geo_resolution": "county",
        "freshness": "annual",
        "confidence": "high",
        "notes": "Aggregate data center water sales (~1.6B gal/yr)",
    },
    {
        "source": "EPA ECHO NAICS",
        "scraper": "epa_echo_naics",
        "disclosure": "mandated",
        "geo_resolution": "facility",
        "freshness": "quarterly",
        "confidence": "medium",
        "notes": "Facility discovery by NAICS 518210; no water volumes",
    },
    {
        "source": "PWC Industrial User Survey",
        "scraper": "va_pwc_ius",
        "disclosure": "voluntary",
        "geo_resolution": "county",
        "freshness": "annual",
        "confidence": "medium",
        "notes": "ERU allocations for 56 data centers; GPD estimated from ERU",
    },
    {
        "source": "VA DEQ ArcGIS",
        "scraper": "va_deq_arcgis",
        "disclosure": "mandated",
        "geo_resolution": "facility",
        "freshness": "irregular",
        "confidence": "medium",
        "notes": "Permit metadata only — no flow measurements",
    },
    {
        "source": "VA DEQ VWP",
        "scraper": "va_deq_vwp",
        "disclosure": "mandated",
        "geo_resolution": "facility",
        "freshness": "irregular",
        "confidence": "medium",
        "notes": "Water withdrawal permits (ArcGIS layers 192/193)",
    },
    {
        "source": "Ohio EPA General Permit",
        "scraper": "oh_epa_general_permit",
        "disclosure": "mandated",
        "geo_resolution": "state",
        "freshness": "one-time",
        "confidence": "medium",
        "notes": "OHD000001 — first DC wastewater permit; pending finalization",
    },
    {
        "source": "Ohio EPA NPDES ArcGIS",
        "scraper": "oh_epa_npdes_arcgis",
        "disclosure": "mandated",
        "geo_resolution": "facility",
        "freshness": "quarterly",
        "confidence": "medium",
        "notes": "SIC 7374 permit discovery; nightly updates",
    },
    {
        "source": "ODNR Water Withdrawal",
        "scraper": "oh_odnr_water_withdrawal",
        "disclosure": "mandated",
        "geo_resolution": "facility",
        "freshness": "annual",
        "confidence": "medium",
        "notes": "Historical withdrawal volumes in central OH counties",
    },
    {
        "source": "Central Ohio Water Study",
        "scraper": "oh_central_water_study",
        "disclosure": "voluntary",
        "geo_resolution": "county",
        "freshness": "one-time",
        "confidence": "low",
        "notes": "Demand projections: 40 MGD (2030) to 90 MGD (2050)",
    },
    {
        "source": "Fairfax Water Reports",
        "scraper": "va_fairfax_water",
        "disclosure": "mandated",
        "geo_resolution": "county",
        "freshness": "annual",
        "confidence": "medium",
        "notes": "Wholesale supplier to Loudoun Water (~18 MGD)",
    },
]

# Known data transparency gaps — NDAs, vetoed bills, missing data.
TRANSPARENCY_GAPS = [
    {
        "gap": "25 of 31 VA localities signed data center NDAs",
        "impact": "Facility-level water data blocked by non-disclosure agreements",
        "status": "ongoing",
    },
    {
        "gap": "Virginia DC water reporting (HB 496 / SB 553)",
        "impact": "ENACTED 2026 — water utilities must report monthly DC water volumes; data not yet published",
        "status": "signed by Gov. Spanberger 2026; first reports pending",
    },
    {
        "gap": "California AB 93 — vetoed Oct 2024",
        "impact": "Would have required annual water use disclosure by data centers",
        "status": "vetoed by Gov. Newsom",
    },
    {
        "gap": "No federal facility-level DC water reporting",
        "impact": "EPA tracks WWTPs, not individual data center connections",
        "status": "no legislation pending",
    },
]

# Timeline of key disclosure and policy events.
TIMELINE_EVENTS = [
    {
        "date": "2020-01-01",
        "year": 2020,
        "label": "USGS Water Use Estimates Published",
        "category": "data",
        "detail": "Latest county-level water use data (every 5 years). "
        "Too coarse for facility tracking but useful for regional context.",
    },
    {
        "date": "2023-06-01",
        "year": 2023,
        "label": "UC Riverside: 'Making AI Less Thirsty'",
        "category": "research",
        "detail": "First major study quantifying AI water footprint. "
        "Estimated 0.5L per 10-50 ChatGPT queries.",
    },
    {
        "date": "2023-10-01",
        "year": 2023,
        "label": "Loudoun Water ACFR: 1.6B gal to DCs",
        "category": "data",
        "detail": "Annual report reveals data centers consumed 1.635 billion gallons "
        "(899M potable + 736M reclaimed) — 15% of utility sales.",
    },
    {
        "date": "2024-05-01",
        "year": 2024,
        "label": "Botetourt County Court Ruling",
        "category": "legal",
        "detail": "Judge rules water usage data is NOT a proprietary trade secret. "
        "Key precedent for FOIA requests.",
    },
    {
        "date": "2024-10-12",
        "year": 2024,
        "label": "California AB 93 Vetoed",
        "category": "policy",
        "detail": "Gov. Newsom vetoes bill that would have required annual "
        "data center water use disclosure.",
    },
    {
        "date": "2024-12-01",
        "year": 2024,
        "label": "JLARC: Data Centers in Virginia",
        "category": "research",
        "detail": "Virginia legislative study finds DC water use 'sustainable but growing.' "
        "Recommends localities require water use estimates for new DCs.",
    },
    {
        "date": "2025-01-16",
        "year": 2025,
        "label": "Ohio EPA OHD000001 Comment Period Closes",
        "category": "policy",
        "detail": "Public comment closes on first-ever data center wastewater "
        "general permit. Will require DMR reporting from DCs directly.",
    },
    {
        "date": "2025-03-01",
        "year": 2025,
        "label": "Central Ohio Regional Water Study",
        "category": "data",
        "detail": "Projects industrial water demand growing to 40 MGD by 2030, "
        "90 MGD by 2050. Intel needs 6 MGD alone.",
    },
    {
        "date": "2026-02-09",
        "year": 2026,
        "label": "Virginia SB 553 Passes Senate 25-15",
        "category": "policy",
        "detail": "Monthly DC water reporting bill passes Senate. "
        "Sponsor: Sen. Srinivasan (D-Loudoun). Companion to House HB 496.",
    },
    {
        "date": "2026-04-13",
        "year": 2026,
        "label": "Virginia Enacts DC Water Reporting (HB 496)",
        "category": "policy",
        "detail": "Gov. Spanberger signs HB 496 (SB 553 companion), amending "
        "Code § 62.1-44.38 to require monthly reporting of water volumes "
        "delivered to data centers — Virginia's first mandatory DC water-disclosure law.",
    },
]

# Per-query water estimates — sourced from published research.
PER_QUERY_ESTIMATES = [
    {
        "label": "Google Gemini (self-reported)",
        "ml": 0.26,
        "source": "Google Environmental Report 2024",
        "note": "Direct on-site cooling only",
    },
    {
        "label": "Shaolei Ren / UC Riverside (median)",
        "ml": 10,
        "source": "Making AI Less Thirsty (2023)",
        "note": "Includes server-room cooling",
    },
    {
        "label": "Andy Masley estimate",
        "ml": 1.0,
        "source": "Substack analysis, 2024",
        "note": "Direct cooling, calibrated to Google disclosure",
    },
    {
        "label": "UC Riverside (upper bound, with power plant)",
        "ml": 519,
        "source": "Making AI Less Thirsty (2023)",
        "note": "Includes thermoelectric cooling for electricity generation",
    },
]

# Andy Masley everyday-activity comparisons; ~2 mL per prompt (on-site + electricity).
# Source: "The AI water issue is fake" — blog.andymasley.com/p/the-ai-water-issue-is-fake
MASLEY_COMPARISONS = [
    {"activity": "Heating a kettle", "prompts": 125},
    {"activity": "PS5 for 1 hour", "prompts": 200},
    {"activity": "One sheet of paper", "prompts": 2_550},
    {"activity": "A warm bath", "prompts": 5_000},
    {"activity": "One American's daily water footprint", "prompts": 800_000},
    {"activity": "Reading a 400-page book", "prompts": 1_000_000},
    {"activity": "Manufacturing a T-shirt", "prompts": 1_300_000},
    {"activity": "Manufacturing a pair of jeans", "prompts": 5_400_000},
]


SOURCES_DATA: dict = {
    "scorecard": {
        "accessible": 7,
        "blocked": 4,
        "coming": 3,
        "build_queue": 6,
    },
    "sources": [
        # Federal
        {"level": "Federal", "name": "EPA ECHO DMR", "note": "8 WWTP permits · aggregate, not per-facility", "status": "working", "action": "Add permits"},
        {"level": "Federal", "name": "EPA ECHO NAICS", "note": "NAICS 518210 facility discovery · intermittent 500s", "status": "working", "action": "Monitor"},
        {"level": "Federal", "name": "EIA Form 923 §8D", "note": "Plant-level thermoelectric cooling · indirect footprint", "status": "not_built", "action": "Build scraper"},
        {"level": "Federal", "name": "EPA FRS cross-reference", "note": "Links facilities across 90+ EPA databases", "status": "not_built", "action": "Build utility"},
        {"level": "Federal", "name": "HR 6984 / S. 4213", "note": "Federal DC water disclosure mandate · not enacted", "status": "policy_gap", "action": "Monitor"},
        # Virginia
        {"level": "Virginia", "name": "Loudoun Water ACFR", "note": "~1.6B gal/yr aggregate · annual only · no per-DC breakdown", "status": "working", "action": "Expand utilities"},
        {"level": "Virginia", "name": "PWC Water IUS", "note": "56 DCs · ERU proxy, not metered consumption", "status": "working", "action": "Annual update"},
        {"level": "Virginia", "name": "HB 496 / SB 553 reports", "note": "Monthly utility DC volumes · reporting channel unconfirmed", "status": "coming", "action": "Watch SWCB / DEQ"},
        {"level": "Virginia", "name": "DEQ ArcGIS / VWP", "note": "Permit metadata only · no flow in ArcGIS layers", "status": "partial", "action": "Metadata only"},
        {"level": "Virginia", "name": "DEQ VPDES Excel", "note": "WAF 403 block · stormwater-only permits anyway", "status": "blocked", "action": "Wait / retry"},
        # Ohio
        {"level": "Ohio", "name": "EPA ECHO DMR (OH)", "note": "4 Columbus-area WWTP permits · same aggregation limit", "status": "working", "action": "Add permits"},
        {"level": "Ohio", "name": "OHD000001 DMRs", "note": "First per-DC direct mandate · public comment closed", "status": "coming", "action": "Awaiting finalization"},
        {"level": "Ohio", "name": "Central OH Water Study", "note": "Demand projections 40 → 90 MGD (2030 → 2050)", "status": "working", "action": "Annual update"},
        # Local / Utility
        {"level": "Local / Utility", "name": "Water service contracts", "note": "Per-DC monthly volumes · NDA-blocked in 25 of 31 VA localities", "status": "blocked", "action": "No FOIA path"},
        {"level": "Local / Utility", "name": "Zoning applications", "note": "Pre-construction water estimates · variable quality", "status": "partial", "action": "Expand coverage"},
        # Private (voluntary)
        {"level": "Private (voluntary)", "name": "Operator water claims", "note": "29 verbatim quotes · 5 independently assessed", "status": "working", "action": "Annual refresh"},
        {"level": "Private (voluntary)", "name": "CDP questionnaires", "note": "Structured water security filings · MSFT / GOOG / META file", "status": "not_built", "action": "Build ingest"},
        {"level": "Private (voluntary)", "name": "FracTracker DC database", "note": "1,400+ sites · cooling type (air / evaporative / hybrid)", "status": "not_built", "action": "Build ingest"},
        {"level": "Private (voluntary)", "name": "PJM Large Loads 2026", "note": "≥50 MW DC loads in PJM territory · electricity proxy", "status": "not_built", "action": "Build ingest"},
    ],
    "barriers": [
        {
            "title": "WWTP aggregation",
            "body": (
                "EPA ECHO measures flow at receiving wastewater treatment plants. "
                "All dischargers — Amazon, hospitals, hotels — sum into one monthly "
                "number. No federal mechanism disaggregates per data center."
            ),
            "workaround": "Add WWTP permits as DC clusters grow; long-term unlock is OHD000001 direct DMRs.",
            "kind": "structural",
        },
        {
            "title": "NDA wall (VA local)",
            "body": (
                "25 of 31 Virginia localities signed NDAs. Water volumes, cooling "
                "targets, and rate structures are contractually shielded. FOIA "
                "exemptions apply in Virginia."
            ),
            "workaround": "Utility ACFRs (aggregate) + HB 496 / SB 553 monthly reports (aggregate, July 2026).",
            "kind": "legal",
        },
        {
            "title": "Voluntary-only private",
            "body": (
                "All private water data is self-reported national/global totals. "
                "No SEC rule requires facility-level water reporting for tech "
                "companies. No independent verification path exists."
            ),
            "workaround": "CDP questionnaires + FracTracker cooling type + PJM electricity proxy.",
            "kind": "policy",
        },
    ],
    "timeline": [
        {
            "date": "Jul 2026",
            "title": "HB 496 / SB 553 effective",
            "desc": (
                "VA utilities must report monthly DC water volumes. First reports expected "
                "Aug–Sept. Confirm channel (SWCB vs. DEQ) before building scraper."
            ),
            "color": "purple",
        },
        {
            "date": "TBD 2026",
            "title": "Ohio OHD000001 finalized",
            "desc": (
                "First state mandate requiring DMR from data centers directly. "
                "Add new permit numbers to epa_echo_target_permits when published."
            ),
            "color": "purple",
        },
        {
            "date": "Buildable now",
            "title": "EIA Form 923 §8D — indirect water",
            "desc": (
                "2024 data published Sept 2025. Unlocks indirect thermoelectric "
                "footprint (~80% of DC total). High-priority build."
            ),
            "color": "green",
        },
        {
            "date": "Buildable now",
            "title": "EPA FRS cross-reference + CDP ingest",
            "desc": (
                "Both APIs confirmed. FRS stabilizes facility dedup; CDP adds "
                "structured voluntary disclosures from MSFT / GOOG / META."
            ),
            "color": "green",
        },
    ],
}


def compute_household_equivalent(gallons_per_year: int, gpd: int = 200) -> int:
    """Convert annual gallons to equivalent number of households served.

    Thin wrapper over ``utils.equivalents.annual_gallons_to_households`` so the
    gpd→households math lives in one place. Default 200 gpd is the lower
    Virginia regional figure the context cards use (vs. EPA's 300 gpd national
    default); behavior (int truncation, 0 for non-positive gpd) is unchanged.
    """
    return annual_gallons_to_households(gallons_per_year, gpd)


def render_local_context(is_mobile: bool = False):
    """Render the Local Context panel — puts water numbers in perspective."""
    st.subheader("How Does This Compare?")

    for key in ("loudoun", "pwc"):
        ctx = CONTEXT_DATA[key]
        dc_gal = ctx["dc_water_gallons"]
        total_gal = ctx["utility_total_gallons"]
        homes = compute_household_equivalent(dc_gal, ctx["avg_household_gpd"])
        pct = (dc_gal / total_gal * 100) if total_gal > 0 else 0

        dc_gal_b = dc_gal / 1_000_000_000
        label = ctx["label"]
        year = ctx["dc_water_year"]

        st.markdown(
            f"""<div class="context-card">
<h4>{label}</h4>
<div class="big-number">{dc_gal_b:.1f} billion gallons ({year})</div>
<div class="comparison">
Equivalent to serving <strong>{homes:,} homes</strong> for a year
&mdash; roughly <strong>{pct:.0f}%</strong> of the utility's total water sales.
</div>
<div class="source-note">Source: {ctx['source']}</div>
</div>""",
            unsafe_allow_html=True,
        )

    # Ohio projections
    oh = CONTEXT_DATA["central_ohio"]
    st.markdown(
        f"""<div class="context-card">
<h4>{oh['label']} — Projected Growth</h4>
<div class="big-number">{oh['projected_dc_mgd_2030']} MGD by 2030 &rarr; {oh['projected_dc_mgd_2050']} MGD by 2050</div>
<div class="comparison">
Industrial water demand projected to more than double in 20 years, driven by data centers
and Intel's semiconductor campus.
</div>
<div class="source-note">Source: {oh['source']}</div>
</div>""",
        unsafe_allow_html=True,
    )


def render_per_query_explainer():
    """Render the Per-Query Water Debate explainer card."""
    st.subheader("Per-Query Water: Why Estimates Vary by 2,000x")

    estimates = sorted(PER_QUERY_ESTIMATES, key=lambda e: e["ml"])
    low = estimates[0]
    high = estimates[-1]

    st.markdown(
        f"""<div class="explainer-card">
<h4>How much water does one AI query use?</h4>
<p>Estimates range from <strong>{low['ml']} mL</strong> to <strong>{high['ml']} mL</strong>
per query. The huge range is not a mistake &mdash; it reflects
fundamentally different accounting methods.</p>
<div class="range-bar"></div>
<div class="range-label">
    <span>{low['ml']} mL ({low['label']})</span>
    <span>{high['ml']} mL ({high['label']})</span>
</div>
</div>""",
        unsafe_allow_html=True,
    )

    st.markdown("**Four variables drive the variance:**")
    st.markdown(
        "1. **Inference vs. training** — Training a large model is a one-time cost "
        "amortized over billions of queries; inference is per-request.\n"
        "2. **Cooling technology** — Evaporative cooling consumes water; "
        "air-cooled or liquid-to-liquid systems use much less.\n"
        "3. **Direct vs. indirect water** — On-site cooling is ~20% of total footprint; "
        "thermoelectric cooling at power plants is ~80%.\n"
        "4. **Withdrawal vs. consumption** — Withdrawal counts water taken; "
        "consumption counts water not returned. Withdrawal numbers are 3-5x higher."
    )

    st.markdown("---")
    st.markdown(
        "**Reality check — per Andy Masley.** Including the electricity-generation "
        "water, one query is ~2 mL. Translated into everyday terms:"
    )
    masley_df = pd.DataFrame(
        [
            {
                "Same water as…": c["activity"],
                "= this many AI prompts": f"{c['prompts']:,}",
            }
            for c in MASLEY_COMPARISONS
        ]
    )
    st.dataframe(
        masley_df,
        use_container_width=True,
        hide_index=True,
        height=35 * len(MASLEY_COMPARISONS) + 40,
    )

    st.info(
        "**The 500 mL bottle myth.** The viral 'one bottle per email/prompt' figure "
        "(Washington Post, 2023) was inflated 50–250×. The underlying research "
        "actually found ~500 mL per *20–50* prompts — not per single prompt."
    )

    st.markdown(
        "**Why this tracker measures facilities, not chatbots.** Per query is "
        "trivial. That's why we track WWTP discharge volumes, utility sales to data "
        "centers, and policy mandates — where the *aggregate, local* impact is "
        "real and measurable."
    )

    st.caption(
        "Comparisons from Andy Masley, \"The AI water issue is fake\" "
        "(blog.andymasley.com/p/the-ai-water-issue-is-fake)."
    )

    with st.expander("Detailed estimates"):
        for est in estimates:
            st.markdown(
                f"- **{est['ml']} mL** — {est['label']}  \n"
                f"  _{est['note']}_ | Source: {est['source']}"
            )


def render_transparency_scorecard():
    """Render the Transparency Scorecard panel — rates each data source."""
    st.subheader("Transparency Scorecard")

    st.markdown(
        "How transparent is data center water reporting? "
        "Each source rated by disclosure type, geographic detail, and confidence."
    )

    # Build a dataframe for display
    rows = []
    for src in SCORECARD_DATA:
        confidence_icon = {
            "high": "High",
            "medium": "Medium",
            "low": "Low",
        }.get(src["confidence"], src["confidence"])

        disclosure_label = {
            "mandated": "Mandated",
            "voluntary": "Voluntary",
            "inferred": "Inferred",
        }.get(src["disclosure"], src["disclosure"])

        rows.append(
            {
                "Source": src["source"],
                "Disclosure": disclosure_label,
                "Resolution": src["geo_resolution"].title(),
                "Frequency": src["freshness"].title(),
                "Confidence": confidence_icon,
                "Notes": src["notes"],
            }
        )

    scorecard_df = pd.DataFrame(rows)
    st.dataframe(
        scorecard_df,
        use_container_width=True,
        hide_index=True,
        height=min(400, 35 * len(rows) + 40),
    )

    # Transparency gaps
    st.markdown("**Known Gaps & Barriers:**")
    for gap in TRANSPARENCY_GAPS:
        status_color = {
            "ongoing": COLORS["warning"],
            "vetoed by Gov. Newsom": COLORS["danger"],
            "no legislation pending": COLORS["text"],
        }
        color = status_color.get(gap["status"], COLORS["secondary"])
        st.markdown(
            f"- **{gap['gap']}** — {gap['impact']}  \n"
            f"  _Status: {gap['status']}_"
        )


def render_timeline():
    """Render the Policy & Disclosure Timeline panel."""
    st.subheader("Policy & Disclosure Timeline")

    st.markdown(
        "Key events shaping data center water transparency — "
        "the data landscape is changing rapidly."
    )

    category_colors = {
        "policy": COLORS["danger"],
        "data": COLORS["primary"],
        "research": COLORS["success"],
        "legal": COLORS["warning"],
    }

    category_labels = {
        "policy": "Policy",
        "data": "Data Release",
        "research": "Research",
        "legal": "Legal",
    }

    events = sorted(TIMELINE_EVENTS, key=lambda e: e["date"])

    for event in events:
        cat = event["category"]
        color = category_colors.get(cat, COLORS["text"])
        cat_label = category_labels.get(cat, cat.title())

        st.markdown(
            f"""<div class="timeline-event">
<div class="timeline-date">{event['year']}</div>
<div class="timeline-body">
<span class="timeline-badge" style="background:{color}">{cat_label}</span>
<strong>{event['label']}</strong><br>
<span class="timeline-detail">{event['detail']}</span>
</div>
</div>""",
            unsafe_allow_html=True,
        )


# --- National Legislation Tracker ---

def _legislation_status_summary(bills: list[dict]) -> str:
    """Build a '2 Enacted · 10 Introduced · ...' summary string."""
    counts: dict[str, int] = {}
    for b in bills:
        status = b.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    ordered = sorted(counts, key=lambda s: LEGISLATION_STATUS_ORDER.get(s, 9))
    return " · ".join(
        f"{counts[s]} {LEGISLATION_STATUS_LABELS.get(s, s.title())}" for s in ordered
    )


def _legislation_rows(bills: list[dict]) -> list[dict]:
    """Flatten legislation records into display rows, sorted by status then place."""
    ordered = sorted(
        bills,
        key=lambda b: (
            LEGISLATION_STATUS_ORDER.get(b.get("status"), 9),
            b.get("jurisdiction", ""),
        ),
    )
    rows = []
    for b in ordered:
        rows.append(
            {
                "Bill": b.get("bill_id", ""),
                "Jurisdiction": b.get("jurisdiction", ""),
                "Scope": ", ".join(s.title() for s in b.get("scope", [])),
                "Status": LEGISLATION_STATUS_LABELS.get(
                    b.get("status"), str(b.get("status", ""))
                ),
                "Verified": "Yes" if b.get("verified") else "Unconfirmed",
                "Summary": b.get("summary", ""),
                "Source": b.get("source_url", ""),
            }
        )
    return rows


def _bill_anchor(bill_id: str) -> str:
    """Stable in-page anchor slug for a bill card ('VA HB 496 / SB 553' →
    'bill-va-hb-496-sb-553')."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(bill_id).lower()).strip("-")
    return f"bill-{slug}"


def _legislation_principles_summary(bills: list[dict]) -> list[dict]:
    """Aggregate general_principles tags across all bills.

    Returns one row per tag, ordered by bill count desc:
    {tag, description, count, enacted, example_bills: [(bill_id, status), ...]}
    Example bills prefer enacted ones (the principles that actually became
    law matter most), then introduced, capped at 3 per tag.
    """
    by_tag: dict[str, list[dict]] = {}
    for b in bills:
        seen_tags = set()
        for p in b.get("general_principles", []):
            tag = p.get("tag", "")
            if not tag or tag in seen_tags:
                continue
            seen_tags.add(tag)
            by_tag.setdefault(tag, []).append(b)

    rows = []
    for tag, tagged in by_tag.items():
        ranked = sorted(
            tagged, key=lambda b: LEGISLATION_STATUS_ORDER.get(b.get("status"), 9)
        )
        rows.append(
            {
                "tag": tag,
                "description": LEGISLATION_PRINCIPLE_DESCRIPTIONS.get(tag, ""),
                "count": len(tagged),
                "enacted": sum(1 for b in tagged if b.get("status") == "enacted"),
                "example_bills": [
                    (b.get("bill_id", ""), b.get("status", "")) for b in ranked[:3]
                ],
            }
        )
    rows.sort(key=lambda r: (-r["count"], r["tag"]))
    return rows


def _build_principles_summary_html(bills: list[dict]) -> str:
    """Cross-bill 'what do these bills actually ask for?' panel.

    Pure HTML builder shared by the Streamlit app and the static site. Each
    row: tag chip + N bills (M enacted) + one-line description + example
    bill links (in-page anchors to the cards below).
    """
    rows = _legislation_principles_summary(bills)
    if not rows:
        return ""
    esc = html.escape
    items = []
    for r in rows:
        examples = " · ".join(
            f'<a href="#{_bill_anchor(bid)}">{esc(bid)}</a>'
            + (" ✓" if status == "enacted" else "")
            for bid, status in r["example_bills"]
        )
        enacted_note = f", {r['enacted']} enacted" if r["enacted"] else ""
        items.append(
            '<div class="principle-sum-row">'
            f'<span class="bill-principle-chip">{esc(r["tag"])}</span>'
            f'<span class="principle-sum-count">{r["count"]} bills{enacted_note}</span>'
            f'<span class="principle-sum-desc">{esc(r["description"])}</span>'
            f'<span class="principle-sum-examples">e.g. {examples}</span>'
            '</div>'
        )
    return (
        '<div class="principles-panel">'
        '<div class="principles-panel-title">Key principles across all bills</div>'
        '<p class="principles-panel-sub">What this wave of legislation actually '
        'asks for, ranked by how many tracked bills carry each idea. '
        '✓ marks an enacted example.</p>'
        f'{"".join(items)}'
        '</div>'
    )


def _legislation_explainer_md() -> str:
    """Short 'how to read this tracker' explainer for the legislation tab."""
    return (
        "**Status.** *Enacted* = signed into law (these become mandatory data "
        "sources for this project — e.g. VA HB 496's monthly water-delivery "
        "reports). *Introduced* = filed and somewhere between first reading "
        "and a floor vote; most die quietly in committee. *Failed / Vetoed* = "
        "formally dead this session, but failed bills are leading indicators — "
        "the same text routinely returns a session later with a new number.\n\n"
        "**Levels.** *Federal* bills set national floors (EPA/EIA reporting, "
        "FERC queue rules); *state* bills carry most of the real activity "
        "(disclosure mandates, rate classes, permit gates); *local* entries "
        "are zoning actions with outsized practical effect in data-center "
        "alley (e.g. Loudoun's ZOAM).\n\n"
        "**Scope.** *Water* and *energy* tags mark which resource a bill "
        "regulates; many cover both because cooling water and grid load are "
        "two faces of the same buildout.\n\n"
        "**Principles.** Each bill is tagged with the general ideas it "
        "embodies (transparency, cost allocation, NDA prohibition, …) — the "
        "summary panel above ranks those ideas across the whole record, and "
        "you can filter the cards by principle.\n\n"
        "**Verification.** Entries flagged `verified` were checked against "
        "the legislature's own bill-status page on the `last_verified` date; "
        "unverified entries are secondary-sourced — confirm the bill number "
        "before citing."
    )


def render_legislation_tracker(is_mobile: bool = False, is_tablet: bool = False):
    """Render the National Legislation Tracker panel.

    Renders a vertical list of bordered bill cards at every viewport — cards
    scan more cleanly than the previous dataframe (no cell truncation, the
    summary always reads as a paragraph, status carries a colored badge).
    Same primitive works at mobile, tablet, and desktop without per-viewport
    branching.
    """
    # is_mobile / is_tablet kept on the signature for forward compatibility
    # (callers in main() still pass them), but the card layout is shared.
    del is_mobile, is_tablet

    st.subheader("Data Center Water Legislation Tracker")
    st.markdown(
        "State, federal, and local action on data center water (and energy) "
        "disclosure — bills, signed laws, agency rulemakings, and major "
        "zoning ordinances. Enacted laws are the next mandatory data sources "
        "to come online."
    )

    payload = load_legislation()
    bills = payload.get("bills", [])
    if not bills:
        st.info("Legislation dataset not found or empty.")
        return

    # Cross-bill principles synthesis — the "so what" before the card list,
    # mirroring the CWA tab's insight panel.
    st.markdown(_build_principles_summary_html(bills), unsafe_allow_html=True)

    with st.expander("How to read this tracker — statuses, levels, principles"):
        st.markdown(_legislation_explainer_md())

    # Filters: principle (primary), then status / level / scope.
    all_tags = [r["tag"] for r in _legislation_principles_summary(bills)]
    selected_tags = st.multiselect(
        "Filter by principle",
        options=all_tags,
        default=all_tags,
        key="leg_principle_filter",
    )
    fcols = st.columns(3)
    with fcols[0]:
        selected_status = st.multiselect(
            "Status",
            options=list(LEGISLATION_STATUS_LABELS.keys())[:3],
            default=list(LEGISLATION_STATUS_LABELS.keys())[:3],
            format_func=lambda k: LEGISLATION_STATUS_LABELS.get(k, k.title()),
            key="leg_status_filter",
        )
    with fcols[1]:
        selected_levels = st.multiselect(
            "Level",
            options=list(LEGISLATION_LEVEL_LABELS.keys()),
            default=list(LEGISLATION_LEVEL_LABELS.keys()),
            format_func=lambda k: LEGISLATION_LEVEL_LABELS.get(k, k.title()),
            key="leg_level_filter",
        )
    with fcols[2]:
        selected_scopes = st.multiselect(
            "Scope",
            options=list(LEGISLATION_SCOPE_LABELS.keys()),
            default=list(LEGISLATION_SCOPE_LABELS.keys()),
            format_func=lambda k: LEGISLATION_SCOPE_LABELS.get(k, k.title()),
            key="leg_scope_filter",
        )

    tag_set, status_set = set(selected_tags), set(selected_status)
    level_set, scope_set = set(selected_levels), set(selected_scopes)
    filtered = [
        b
        for b in bills
        if b.get("status") in status_set
        and b.get("level") in level_set
        and (scope_set & set(b.get("scope", [])))
        and (tag_set & {p.get("tag") for p in b.get("general_principles", [])})
    ]
    if not filtered:
        st.info("No bills match the current filter. Try widening the selection.")
        return

    st.markdown(
        f"**Showing {len(filtered)} of {len(bills)} bills** — "
        f"{_legislation_status_summary(filtered)}"
    )

    # Key themes grid + emerging solutions box
    st.markdown(_build_legislation_themes_html(bills), unsafe_allow_html=True)

    sorted_bills = sorted(
        filtered,
        key=lambda b: (
            LEGISLATION_STATUS_ORDER.get(b.get("status"), 9),
            b.get("jurisdiction", ""),
        ),
    )
    # Emit ALL bill cards as a single markdown blob — one component instead of
    # one per bill (31 → 1). Streamlit reruns the whole script on every
    # interaction and ships each st.markdown as a separate component; each card
    # is already a self-contained <div class="bill-card"> with a browser-native
    # <details> toggle, so concatenating them is visually identical while
    # slashing the component count the frontend reconciles every rerun.
    st.markdown(
        "".join(_build_bill_card_html(bill) for bill in sorted_bills),
        unsafe_allow_html=True,
    )

    last_updated = payload.get("last_updated") or "unknown"
    st.caption(
        f"Dataset last updated {last_updated}. Verification status for each "
        "entry is tracked in the underlying JSON; treat any not flagged "
        "verified=true there as secondary-sourced."
    )


def _build_bill_card_html(bill: dict) -> str:
    """Build the complete HTML for one bill card, including the collapsible details."""
    esc = html.escape

    bill_id = esc(bill.get("bill_id", ""))
    status = (bill.get("status") or "").lower()
    status_label = LEGISLATION_STATUS_LABELS.get(status, status.title() or "Unknown")
    badge_color = LEGISLATION_STATUS_BADGE_COLORS.get(status, COLORS["secondary"])
    summary = esc(bill.get("summary", ""))
    source_url = bill.get("source_url", "")
    sponsor = esc(bill.get("sponsor", ""))

    # Header row: bill ID + colored status pill.
    head = (
        '<div class="bill-card-head">'
        f'<span class="bill-card-id">{bill_id}</span>'
        f'<span class="bill-card-pill" style="background:{badge_color}">'
        f'{esc(status_label)}</span>'
        '</div>'
    )

    # Classification row — jurisdiction, level, scope, and the bill's
    # principle tags at a glance (mirrors the CWA cards' cwa-class-row).
    level = (bill.get("level") or "").lower()
    class_bits = []
    # Instrument type leads the row: whether a record is a bill, an executive
    # order or an agency rule changes how a reader should weigh it far more
    # than its jurisdiction does. Only non-bills get a chip — bills are the
    # overwhelming default and a chip on all 50 would be noise.
    instrument_type = bill.get("instrument_type", "bill")
    if instrument_type != "bill" and instrument_type in INSTRUMENT_TYPE_LABELS:
        class_bits.append(
            f'<span class="instrument-pill" style="color:'
            f'{INSTRUMENT_TYPE_COLORS[instrument_type]};border-color:'
            f'{INSTRUMENT_TYPE_COLORS[instrument_type]}">'
            f'{esc(INSTRUMENT_TYPE_LABELS[instrument_type])}</span>'
        )
    jurisdiction = esc(bill.get("jurisdiction", ""))
    if jurisdiction:
        class_bits.append(f'<span class="cwa-type-pill">{jurisdiction}</span>')
    if (
        level in LEGISLATION_LEVEL_LABELS
        and level != "state"
        and level not in (bill.get("jurisdiction") or "").lower()
    ):
        # State is the default and jurisdictions like "Federal (US)" or
        # "Local (Loudoun County)" already say it — only add the level pill
        # when it adds information.
        class_bits.append(
            f'<span class="cwa-type-pill">{esc(LEGISLATION_LEVEL_LABELS[level])}</span>'
        )
    for s in bill.get("scope", []):
        label = LEGISLATION_SCOPE_LABELS.get(s, s.title())
        class_bits.append(f'<span class="bill-scope-pill">{esc(label)}</span>')
    tags = [p.get("tag", "") for p in bill.get("general_principles", []) if p.get("tag")]
    if tags:
        class_bits.append(
            f'<span class="cwa-instrument">{esc(" · ".join(dict.fromkeys(tags)))}</span>'
        )
    class_row = (
        f'<div class="cwa-class-row">{"".join(class_bits)}</div>' if class_bits else ""
    )

    body = f'<p class="bill-card-summary">{summary}</p>' if summary else ""

    meta_bits = []
    if sponsor:
        meta_bits.append(sponsor)
    if source_url:
        meta_bits.append(
            f'<a href="{esc(source_url)}" target="_blank" rel="noopener">Source</a>'
        )
    meta = (
        f'<div class="bill-card-meta">{" · ".join(meta_bits)}</div>' if meta_bits else ""
    )

    details = _build_bill_details_html(bill)

    anchor = _bill_anchor(bill.get("bill_id", ""))
    return (
        f'<div class="bill-card" id="{anchor}">'
        f'{head}{class_row}{body}{meta}{details}</div>'
    )


def _build_bill_details_html(bill: dict) -> str:
    """Build the collapsible `<details>` block. Returns '' if nothing to show."""
    sections = []
    timeline_html = _build_timeline_html(bill.get("timeline", []))
    if timeline_html:
        sections.append(timeline_html)
    news_html = _build_news_html(bill.get("recent_news", []))
    if news_html:
        sections.append(news_html)
    sentiment_html = _build_sentiment_html(bill.get("public_sentiment", ""))
    if sentiment_html:
        sections.append(sentiment_html)
    principles_html = _build_principles_html(bill.get("general_principles", []))
    if principles_html:
        sections.append(principles_html)

    if not sections:
        return ""

    return (
        '<details class="bill-card-details">'
        '<summary>Details — timeline, news, sentiment, principles</summary>'
        f'{"".join(sections)}'
        '</details>'
    )


def _build_timeline_html(timeline: list[dict]) -> str:
    if not timeline:
        return ""
    esc = html.escape
    rows = []
    for event in timeline:
        date = esc(event.get("date", ""))
        milestone = esc(event.get("milestone", ""))
        detail = event.get("detail", "")
        detail_html = (
            f' <span class="bill-mini-detail">— {esc(detail)}</span>' if detail else ""
        )
        rows.append(
            f'<div class="bill-mini-event">'
            f'<div class="bill-mini-date">{date}</div>'
            f'<div class="bill-mini-body"><strong>{milestone}</strong>{detail_html}</div>'
            f'</div>'
        )
    return (
        '<div class="bill-section-label">Timeline</div>' + "".join(rows)
    )


def _build_news_html(news: list[dict]) -> str:
    if not news:
        return ""
    esc = html.escape
    items = []
    for item in news:
        date = esc(item.get("date", ""))
        title = esc(item.get("title", ""))
        source = esc(item.get("source", ""))
        url = item.get("url", "")
        takeaway = esc(item.get("takeaway", ""))
        if url:
            headline_html = (
                f'<a href="{esc(url)}" target="_blank" rel="noopener">{title}</a>'
            )
        else:
            headline_html = title
        meta_html = " · ".join(b for b in (date, source) if b)
        takeaway_html = (
            f'<div class="bill-news-takeaway">{takeaway}</div>' if takeaway else ""
        )
        items.append(
            f'<div class="bill-news-item">'
            f'<div>{headline_html}</div>'
            f'<div class="bill-news-meta">{meta_html}</div>'
            f'{takeaway_html}'
            f'</div>'
        )
    return '<div class="bill-section-label">Recent news</div>' + "".join(items)


def _build_sentiment_html(sentiment: str) -> str:
    if not sentiment:
        return ""
    return (
        '<div class="bill-section-label">Public sentiment</div>'
        f'<p class="bill-sentiment">{html.escape(sentiment)}</p>'
    )


def _build_principles_html(principles: list[dict]) -> str:
    if not principles:
        return ""
    esc = html.escape
    rows = []
    for p in principles:
        tag = esc(p.get("tag", ""))
        note = esc(p.get("note", ""))
        rows.append(
            f'<div class="bill-principle-row">'
            f'<span class="bill-principle-chip">{tag}</span>{note}'
            f'</div>'
        )
    return (
        '<div class="bill-section-label">General principles</div>' + "".join(rows)
    )


# --- Legislation Themes ---

# Each theme card aggregates one or more tags from the closed principle
# taxonomy (keys of LEGISLATION_PRINCIPLE_DESCRIPTIONS). The grid counts
# unique bills carrying ANY of the card's tags. `tags` must stay a subset of
# the taxonomy — test-enforced, because a tag that drifts out of the taxonomy
# silently renders a 0 (that exact bug shipped: 5 of 6 cards showed 0 while
# the dataset held 22 cost-allocation and ~21 permit/moratorium bills).
LEGISLATION_THEME_DEFINITIONS = [
    {
        "tags": ("Transparency", "Disclosure", "NDA prohibition"),
        "label": "Transparency & Disclosure",
        "color": "#08519c",
        "description": "Require data centers to publicly report actual or projected water consumption to regulators and the public.",
    },
    {
        "tags": ("Preemptive review",),
        "label": "Pre-Construction Review",
        "color": "#2e8b57",
        "description": "Force evaluation of water-supply and environmental impacts before construction is approved, not after.",
    },
    {
        "tags": ("Closed-loop cooling", "Conservation"),
        "label": "Technology & Conservation Mandates",
        "color": "#c41e3a",
        "description": "Require closed-loop, reclaimed-water, or non-consumptive cooling, or mandate lower consumption outright.",
    },
    {
        "tags": ("Cost allocation",),
        "label": "Cost Allocation",
        "color": "#d4a017",
        "description": "Ensure data centers bear the marginal cost of water-supply infrastructure they trigger, not residential ratepayers.",
    },
    {
        "tags": ("Permit oversight", "Moratorium"),
        "label": "Permit Reform & Moratoria",
        "color": "#6b3fa0",
        "description": "Impose construction moratoria or approval leverage over siting before new permits, giving regulators time to assess cumulative demand.",
    },
    {
        "tags": ("Anti-corporate-welfare",),
        "label": "Subsidy Conditions & Repeal",
        "color": "#1a7a8a",
        "description": "Condition or repeal the tax exemptions and subsidies that currently socialize data-center infrastructure costs.",
    },
]


def _build_legislation_themes_html(bills: list[dict]) -> str:
    """Build the 6-card theme grid + emerging solutions box for the top of the legislation tab."""
    from collections import defaultdict
    esc = html.escape

    # Count bills per theme tag, collecting example IDs
    tag_bills: dict[str, list[str]] = defaultdict(list)
    for bill in bills:
        seen: set[str] = set()
        for p in bill.get("general_principles", []):
            if not isinstance(p, dict):
                continue
            tag = p.get("tag", "")
            if tag and tag not in seen:
                seen.add(tag)
                tag_bills[tag].append(bill.get("bill_id", ""))

    cards = []
    for theme in LEGISLATION_THEME_DEFINITIONS:
        # Unique bills carrying ANY of the theme's taxonomy tags, keeping
        # dataset order and de-duplicating bills tagged with several of them.
        ids = list(
            dict.fromkeys(
                bid for tag in theme["tags"] for bid in tag_bills.get(tag, [])
            )
        )
        count = len(ids)
        examples = ", ".join(ids[:3])
        if len(ids) > 3:
            examples += f" +{len(ids) - 3} more"
        cards.append(
            f'<div class="theme-card" style="border-top:3px solid {theme["color"]}">'
            f'<div class="theme-card-count" style="color:{theme["color"]}">{count}</div>'
            f'<div class="theme-card-label">{esc(theme["label"])}</div>'
            f'<div class="theme-card-desc">{esc(theme["description"])}</div>'
            f'<div class="theme-card-examples">{esc(examples) if examples else "—"}</div>'
            f'</div>'
        )

    solutions_box = (
        '<div class="insights" style="margin-top:.8rem">'
        '<h4>What solutions are emerging</h4><ul>'
        '<li><strong>Utility-level monthly reporting</strong> — Virginia HB 496 (enacted April 2026) '
        'is the first state law requiring utilities to report monthly water volumes to data centers. '
        'Several states are watching for the first published data, expected late 2026.</li>'
        '<li><strong>Closed-loop cooling mandates</strong> — Idaho H895 (enacted) and South Carolina '
        'HB 4583 (pending) are first movers on banning open evaporative cooling for new facilities, '
        'eliminating the largest consumptive water-loss pathway.</li>'
        '<li><strong>Environmental review triggers</strong> — New York S10642 (passed legislature, '
        'awaiting governor) would require SEQRA review before any facility exceeds 50 MW — the '
        'broadest state environmental-review trigger yet proposed for data centers.</li>'
        '<li><strong>Direct DC water permits</strong> — Ohio EPA OHD000001 would be the first '
        'federal permit requiring data centers to file discharge monitoring reports directly, '
        'closing the gap where DC cooling water routes through municipal WWTPs with no '
        'facility-level accounting.</li>'
        '</ul></div>'
    )

    return '<div class="theme-grid">' + ''.join(cards) + '</div>' + solutions_box


# --- Water News Tab ---

def _cross_ref_link_map() -> list[tuple[str, str]]:
    """(display text, in-page anchor) pairs for linkifying cross-references.

    Bill ids → #bill-<slug>, conflict-site names/ids → #site-<id>, case ids →
    #cwa-<id>. Sorted longest-first so a compiled alternation prefers the most
    specific match ('VA HB 496 / SB 553' before any shorter overlap).
    """
    pairs: list[tuple[str, str]] = []
    for b in load_legislation().get("bills", []):
        bid = b.get("bill_id", "")
        if bid:
            pairs.append((bid, f"#{_bill_anchor(bid)}"))
    for s in load_dc_water_conflicts().get("sites", []):
        if s.get("site"):
            pairs.append((s["site"], f"#site-{s['site_id']}"))
    for c in load_cwa_investigations().get("cases", []):
        cid = c.get("case_id", "")
        if cid:
            pairs.append((cid, f"#cwa-{cid}"))
            # Also match the human-readable caption ('Amazon Boardman OR
            # nitrate (2026)') so prose cross-references read naturally.
            pairs.append((_cwa_case_caption(cid), f"#cwa-{cid}"))
    return sorted(pairs, key=lambda p: -len(p[0]))


# Manual memo for the linkify matcher: the map spans three datasets and the
# compiled alternation regex has ~250 branches, so rebuilding per card (~48
# calls per build/rerun) measurably slows rendering. Keyed on the source
# files' signatures so edits still bust it, mirroring the loader caches.
_CROSS_REF_MATCHER_CACHE: dict = {"sig": None, "by_display": {}, "pattern": None}


def _cross_ref_matcher() -> tuple[dict, "re.Pattern | None"]:
    """(escaped display → anchor, compiled alternation) built once per data change."""
    sig = (
        _file_signature(LEGISLATION_PATH),
        _file_signature(DC_WATER_CONFLICTS_PATH),
        _file_signature(CWA_INVESTIGATIONS_PATH),
    )
    if _CROSS_REF_MATCHER_CACHE["sig"] != sig:
        link_map = _cross_ref_link_map()
        by_display = {html.escape(d): a for d, a in link_map}
        # link_map is longest-first; alternation is leftmost-first, so the
        # most specific reference wins.
        pattern = (
            re.compile("|".join(re.escape(html.escape(d)) for d, _ in link_map))
            if link_map
            else None
        )
        _CROSS_REF_MATCHER_CACHE.update(
            sig=sig, by_display=by_display, pattern=pattern
        )
    return _CROSS_REF_MATCHER_CACHE["by_display"], _CROSS_REF_MATCHER_CACHE["pattern"]


def _linkify_refs(text: str) -> str:
    """HTML-escape ``text`` and turn known bill/site/case references into
    in-page anchor links (single pass, so already-linked text is never
    re-matched). The static site's anchor handler switches to the owning tab.

    This is the *legacy* fallback for prose that names a record without
    declaring its id. It guesses by substring, so it silently misses a renamed
    record and can match the wrong one on an overlap — prefer
    ``cross_ref_targets`` (see :func:`_crossref_html`) on new entries.
    """
    escaped = html.escape(text)
    by_display, pattern = _cross_ref_matcher()
    if pattern is None:
        return escaped
    return pattern.sub(
        lambda m: f'<a href="{by_display[m.group(0)]}">{m.group(0)}</a>',
        escaped,
    )


def _crossref_html(entry: dict, css_class: str, style: str = "") -> str:
    """Render an entry's '→ …' cross-reference line.

    Two paths, deliberately:

    * ``cross_ref_targets: [id, ...]`` — the explicit path. Ids resolve through
      the registry, so a link is either correct or a test failure; there is no
      third outcome. The note prose is linkified **only** against the declared
      targets, and any target whose label doesn't appear in the prose is
      appended, so the line always renders exactly one link per target.
    * ``cross_ref_tab`` + ``cross_ref_note`` alone — the legacy prose path,
      kept so the pre-2026-07 entries keep working while they migrate.

    An id that resolves to nothing is dropped from the render rather than
    emitting a dead anchor; ``tests/test_refdata.py`` fails the build for it.
    """
    note = entry.get("cross_ref_note", "")
    target_ids = entry.get("cross_ref_targets") or []
    # The Streamlit app renders these cards as raw HTML without the static
    # site's stylesheet, so callers whose class isn't styled there pass the
    # equivalent inline declarations.
    attrs = f'class="{css_class}"' + (f' style="{style}"' if style else "")

    if not target_ids:
        if entry.get("cross_ref_tab") and note:
            return f"<div {attrs}>→ {_linkify_refs(note)}</div>"
        return ""

    refs = [r for r in (resolve_ref(t) for t in target_ids) if r is not None]
    if not refs:
        return ""

    body = html.escape(note)
    linked, trailing = set(), []
    # Longest label first: 'VA HB 496 / SB 553' must win over any shorter
    # reference it contains.
    for ref in sorted(refs, key=lambda r: -len(r.label)):
        needle = html.escape(ref.label)
        anchor = f'<a href="#{html.escape(ref.anchor)}">{needle}</a>'
        if needle and needle in body and ref.id not in linked:
            body = body.replace(needle, anchor, 1)
            linked.add(ref.id)
        else:
            trailing.append((ref, anchor))

    if trailing:
        links = " · ".join(a for _, a in trailing)
        body = f"{body} — {links}" if body else links
    return f"<div {attrs}>→ {body}</div>"


def _build_news_item_html(item: dict) -> str:
    """Build one news card for the News tab (distinct from _build_news_html for bill cards)."""
    esc = html.escape
    title = esc(item.get("title", ""))
    outlet = esc(item.get("outlet", ""))
    date_str = esc(item.get("date", ""))
    summary = esc(item.get("summary", ""))
    url = item.get("source_url") or ""
    tags = item.get("tags", [])

    _title_style = "font-weight:700;font-size:1rem;display:block;margin-bottom:0.3rem;"
    headline = (
        f'<a href="{esc(url)}" target="_blank" rel="noopener" class="news-title"'
        f' style="{_title_style}color:#08519c;text-decoration:none;">{title}</a>'
        if url else
        f'<span class="news-title" style="{_title_style}color:#1a1a2e;">{title}</span>'
    )
    meta = " · ".join(b for b in (outlet, date_str) if b)
    tags_html = "".join(
        f'<span class="news-tag" style="color:{NEWS_TAG_COLORS.get(t, "#555")};'
        f'font-size:0.78rem;font-weight:600;padding:1px 8px;border-radius:999px;'
        f'background:#eff3ff;margin-right:4px;display:inline-block;">'
        f'{esc(NEWS_TAG_LABELS.get(t, t))}</span>'
        for t in tags
    )
    cross_html = _crossref_html(
        item, "news-crossref", "color:#08519c;font-size:0.82rem;margin-top:0.3rem;"
    )
    tags_str = ",".join(tags)
    # meta is already html-escaped (outlet + date_str were individually escaped above);
    # do not wrap in esc() again or &#x27; becomes &amp;#x27; and renders as literal text.
    return (
        f'<div class="news-card" id="news-{esc(item.get("id", ""))}" '
        f'data-tags="{esc(tags_str)}" style="'
        f'border:1px solid #d6e4f0;border-radius:0.5rem;padding:0.9rem 1.1rem;'
        f'margin-bottom:0.75rem;background:#fff;'
        f'box-shadow:0 1px 2px rgba(15,23,42,.04);">'
        f'{headline}'
        f'<div class="news-meta" style="color:#4b5563;font-size:0.85rem;margin-bottom:0.4rem;">{meta}</div>'
        f'<div class="news-summary" style="color:#1a1a2e;font-size:0.9rem;margin-bottom:0.4rem;line-height:1.5;">{summary}</div>'
        f'<div class="news-tags" style="display:flex;flex-wrap:wrap;gap:4px;margin-top:0.35rem;">{tags_html}</div>'
        f'{cross_html}'
        f'</div>'
    )


def render_water_news():
    """Render the Data Center Water News tab (Streamlit)."""
    st.subheader("Data Center Water News")
    st.markdown(
        "Curated headlines on data center water use, regulation, enforcement, and solutions — "
        "linked to this tracker's datasets where applicable. Newest first."
    )
    payload = load_water_news()
    items = payload.get("items", [])
    if not items:
        st.info("No news items loaded.")
        return

    all_tags = sorted({t for item in items for t in item.get("tags", [])})
    recent_date = max(
        (item.get("date", "") for item in items if item.get("date")), default="—"
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Headlines", len(items))
    c2.metric("Topics", len(all_tags))
    c3.metric("Most recent", recent_date)
    st.divider()

    selected = st.multiselect(
        "Filter by topic",
        options=all_tags,
        default=all_tags,
        format_func=lambda t: NEWS_TAG_LABELS.get(t, t),
        key="news_tag_filter",
    )
    selected_set = set(selected)
    filtered = [i for i in items if any(t in selected_set for t in i.get("tags", []))]
    st.markdown(f"**Showing {len(filtered)} of {len(items)} items**")
    st.markdown(
        "".join(_build_news_item_html(i) for i in filtered),
        unsafe_allow_html=True,
    )
    last_updated = payload.get("last_updated") or "unknown"
    st.caption(f"Dataset last updated {last_updated}.")


# --- Water Solutions Tab ---

def _build_solution_card_html(sol: dict) -> str:
    esc = html.escape
    title = esc(sol.get("title", ""))
    status = (sol.get("status") or "proposed").lower()
    actor_type = (sol.get("actor_type") or "").lower()
    actor = esc(sol.get("actor", ""))
    description = esc(sol.get("description", ""))
    example = sol.get("example", "")
    url = sol.get("source_url") or ""

    status_label = SOLUTION_STATUS_LABELS.get(status, status.title())
    color, bg, border = SOLUTION_STATUS_COLORS.get(status, ("#555", "#f5f5f5", "#ccc"))
    actor_label = SOLUTION_ACTOR_LABELS.get(actor_type, actor_type.title())

    badge = (
        f'<span class="solution-badge" '
        f'style="color:{color};background:{bg};border:1px solid {border}">'
        f'{esc(status_label)}</span>'
    )
    source_link = (
        f' · <a href="{esc(url)}" target="_blank" rel="noopener">Source</a>' if url else ""
    )
    # The cross-reference is the quote's attribution: linkified (bill/site/
    # case ids become in-page anchors that switch tabs on the static site)
    # and rendered INSIDE the example/quote box so the reference travels with
    # the quoted text instead of dangling below the card.
    cross_html = _crossref_html(sol, "solution-crossref")
    if example:
        example_html = (
            f'<div class="solution-example">{_linkify_refs(example)}'
            f'{cross_html}</div>'
        )
        cross_html = ""
    else:
        example_html = ""
    return (
        f'<div class="solution-card" id="solution-{esc(sol.get("id", ""))}">'
        f'{badge}'
        f'<div class="solution-title">{title}</div>'
        f'<div class="solution-actor">{esc(actor_label)}: {actor}{source_link}</div>'
        f'<div class="solution-desc">{description}</div>'
        f'{example_html}'
        f'{cross_html}'
        f'</div>'
    )


def render_water_solutions():
    """Render the Water Solutions tab (Streamlit)."""
    st.subheader("Data Center Water Solutions")
    st.markdown(
        "Solutions to data center water challenges documented across this tracker — "
        "organized by who is driving them: state/federal regulators, utilities, or industry."
    )
    payload = load_water_solutions()
    categories = payload.get("categories", [])
    if not categories:
        st.info("Solutions dataset not loaded.")
        return

    all_sols = [s for cat in categories for s in cat.get("solutions", [])]
    n_deployed = sum(1 for s in all_sols if s.get("status") == "deployed")
    n_pilot    = sum(1 for s in all_sols if s.get("status") == "pilot")
    n_proposed = sum(1 for s in all_sols if s.get("status") == "proposed")
    n_mandate  = sum(1 for s in all_sols if s.get("actor_type") in ("state", "federal"))
    n_utility  = sum(1 for s in all_sols if s.get("actor_type") == "utility")
    n_industry = sum(1 for s in all_sols if s.get("actor_type") == "industry")

    c1, c2, c3 = st.columns(3)
    c1.metric("Deployed", n_deployed, help="Operating at scale in at least one jurisdiction")
    c2.metric("Pilot / in progress", n_pilot, help="Signed into law or actively under way, not yet at scale")
    c3.metric("Proposed", n_proposed, help="Pending legislation or emerging best practice")

    c4, c5, c6 = st.columns(3)
    c4.metric("State / federal mandate", n_mandate, help="Legally required by a state or federal regulator")
    c5.metric("Utility-driven", n_utility, help="Water utility programs and policies")
    c6.metric("Industry voluntary", n_industry, help="Self-imposed by operators; no independent verification path")

    pct_deployed = round(n_deployed / len(all_sols) * 100) if all_sols else 0
    st.markdown(
        f'<div style="background:#eff3ff;border-left:4px solid #3182bd;border-radius:0 .5rem .5rem 0;'
        f'padding:.75rem 1rem;margin:.5rem 0 1rem;">'
        f'<strong>Key patterns:</strong>'
        f'<ul style="margin:.35rem 0 0;padding-left:1.2rem;color:#1a1a2e;">'
        f'<li>{pct_deployed}% of tracked solutions are already deployed somewhere — the tools exist; '
        f'the gap is mandate coverage and independent measurement.</li>'
        f'<li>All {n_mandate} state/federal mandates and all {n_utility} utility programs have at least '
        f'one deployed or active-pilot example. Voluntary industry solutions ({n_industry}) have no '
        f'independent verification path.</li>'
        f'<li>The critical unlock is closing the measurement gap: OHD000001 direct DMRs (Ohio) '
        f'and HB 496 monthly utility reports (Virginia, eff. July 2026) are the two pending mandates '
        f'that would make operator claims checkable.</li>'
        f'</ul></div>',
        unsafe_allow_html=True,
    )
    st.divider()

    # One accordion per category (first open) — the tab was a long scroll.
    for i, cat in enumerate(categories):
        solutions = cat.get("solutions", [])
        with st.expander(
            f"{cat.get('label', '')} ({len(solutions)})", expanded=(i == 0)
        ):
            st.markdown(
                f'<p class="solution-cat-desc">{html.escape(cat.get("description", ""))}</p>',
                unsafe_allow_html=True,
            )
            st.markdown(
                "".join(_build_solution_card_html(s) for s in solutions),
                unsafe_allow_html=True,
            )

    last_updated = payload.get("last_updated") or "unknown"
    st.caption(f"Dataset last updated {last_updated}.")


# --- Clean Water Act Investigations Tracker ---

# Forward-looking, merit-scored menu of Clean Water Act theories that could
# realistically attach to a data center. Scoring (1–5, 5 = strongest) is on
# public-interest merit ONLY — Impact (community/environmental harm averted),
# Viability (legal strength post-Sackett/Maui), Tractability (can THIS tracker
# source the evidence via ECHO DMR/SNC, public permits, FOIA). No data-center
# CWA enforcement case exists yet; full write-up with primary-source citations
# lives in docs/cwa-enforcement-and-data-centers.md. Kept module-level so the
# builder stays pure and unit-testable, and so build_site.py reuses one source
# of truth.
CWA_APPLICATION_THEORIES = [
    {
        "rank": 1,
        "theory": "Citizen suit against the receiving POTW",
        "hook": "CWA §505 (33 U.S.C. §1365)",
        "impact": 5, "viability": 5, "tractability": 5,
        "why": "Turns the tracker's existing ECHO SNC/DMR pull into the predicate "
               "for a citizen suit against the plant that actually carries data-center "
               "cooling blowdown — not the DC's near-empty stormwater permit.",
        "analog": "Port of Morrow, OR (WWTP receiving DC wastewater)",
    },
    {
        "rank": 2,
        "theory": "Pretreatment / Industrial-User loading",
        "hook": "CWA §307 + §403",
        "impact": 5, "viability": 5, "tractability": 4,
        "why": "Where DC blowdown actually goes; loading can force POTW pass-through "
               "(putting the plant in violation) and raise every other ratepayer's "
               "costs. Industrial-user permits and local limits are FOIA-able.",
        "analog": "Port of Morrow, OR; industrial pretreatment consent decrees",
    },
    {
        "rank": 3,
        "theory": "Construction stormwater",
        "hook": "CWA §402 (Construction General Permit)",
        "impact": 4, "viability": 5, "tractability": 4,
        "why": "The single most-enforced real CWA violation against large "
               "construction; acute turbidity and habitat impact during the "
               "multi-hundred-acre build-out. NOIs and NOVs are ECHO-visible.",
        "analog": "Arch Coal mining-site analog",
    },
    {
        "rank": 4,
        "theory": "Cooling-tower blowdown direct to surface water",
        "hook": "CWA §402 (NPDES numeric limits)",
        "impact": 4, "viability": 5, "tractability": 4,
        "why": "The classic numeric-limit-exceedance pattern (thermal, chlorine, "
               "biocides, conductivity); directly overlaps the flow metrics the "
               "tracker already scrapes. Permit + DMR via ECHO.",
        "analog": "West Penn Power (boron exceedance)",
    },
    {
        "rank": 5,
        "theory": "On-site package WWTP / greywater-recycle plant effluent",
        "hook": "CWA §402 (NPDES)",
        "impact": 4, "viability": 4, "tractability": 4,
        "why": "Large campuses building their own treatment/reuse plant give it its "
               "OWN NPDES permit + DMR — a clean, trackable point source distinct "
               "from the data-center building.",
        "analog": "xAI Colossus greywater plant, Memphis",
    },
    {
        "rank": 6,
        "theory": "Wetlands dredge-and-fill + state certification",
        "hook": "CWA §404 + §401",
        "impact": 5, "viability": 3, "tractability": 4,
        "why": "Permanent habitat / flood-storage loss; the live enforcement edge. "
               "Sackett narrowed FEDERAL reach, but §401 and retained VA/OH state "
               "programs remain. Permit applications are public.",
        "analog": "New Carlisle IN; Project Raspberry/Loch VA; Port of Little Rock AR",
    },
    {
        "rank": 7,
        "theory": "Thermal discharge + cooling-water intake",
        "hook": "CWA §316(a)/(b)",
        "impact": 4, "viability": 4, "tractability": 3,
        "why": "Heat is a regulated pollutant; intake impingement/entrainment. Bites "
               "hardest where a DC pairs with on-site gas turbines (full power-plant "
               "profile).",
        "analog": "Greenidge Generation, NY (§316 thermal/intake)",
    },
    {
        "rank": 8,
        "theory": "Antidegradation / Tier 2 review of a new outfall",
        "hook": "CWA §303 / state water-quality standards",
        "impact": 4, "viability": 4, "tractability": 3,
        "why": "A procedural lever that forces an alternatives analysis (e.g., dry or "
               "closed-loop cooling) before a new or expanded discharge into "
               "high-quality waters is permitted — high leverage at the siting stage.",
        "analog": "—",
    },
    {
        "rank": 9,
        "theory": "County of Maui “functional equivalent” discharge",
        "hook": "CWA §402 (Maui, 2020)",
        "impact": 4, "viability": 3, "tractability": 2,
        "why": "The most novel theory: a cooling discharge, injection well, or land "
               "application that reaches surface water VIA groundwater can still need "
               "a permit. Closes a common DC discharge loophole; fact-intensive.",
        "analog": "County of Maui v. Hawaii Wildlife Fund",
    },
    {
        "rank": 10,
        "theory": "PFAS in discharge",
        "hook": "CWA §402 (NPDES)",
        "impact": 4, "viability": 3, "tractability": 2,
        "why": "AFFF fire-suppression systems + cooling-chemistry additives, as NPDES "
               "PFAS limits tighten. Strong regulatory tailwind; sourceable once "
               "effluent PFAS monitoring is permit-required.",
        "analog": "Industrial PFAS cases",
    },
    {
        "rank": 11,
        "theory": "Oil spill / SPCC from backup-diesel fuel farms",
        "hook": "CWA §311 (33 U.S.C. §1321)",
        "impact": 3, "viability": 5, "tractability": 3,
        "why": "A release reaching a water of the U.S. is legally identical to the "
               "pipeline-spill cases (incl. negligence-criminal exposure and the "
               "duty-to-report trap); event-driven, so a lower base rate but settled law.",
        "analog": "BP / Enbridge / Summit Midstream §311 line",
    },
    {
        "rank": 12,
        "theory": "Industrial stormwater",
        "hook": "CWA §402 (Multi-Sector General Permit)",
        "impact": 3, "viability": 4, "tractability": 3,
        "why": "Exposed equipment yards and chemical/fuel storage areas; lower "
               "per-event impact but routine. MSGP benchmark monitoring is public.",
        "analog": "—",
    },
]


# Sibling to CWA_APPLICATION_THEORIES: the same merit-only scoring applied to
# the non-CWA doctrine families. The CWA table was the whole panel until the
# 2026-07 registry expansion, which quietly made it a minority view — most
# tracked conflicts are about GETTING water, and the Clean Water Act has very
# little to say about that. Scored on the same three axes: Impact (harm
# averted), Viability (legal strength today), Tractability (can this tracker
# source the evidence).
DOCTRINE_APPLICATION_THEORIES = [
    {
        "rank": 1,
        "theory": "State environmental review — long-term supply not demonstrated",
        "hook": "State review statutes (CEQA-style); see sepa-supply-adequacy",
        "impact": 5, "viability": 5, "tractability": 5,
        "why": "Needs no hydrologic proof — only that the approval document analysed "
               "phase one and deferred build-out, which campus approvals routinely do. "
               "The record is public by definition, and the remedy is the one opponents "
               "actually want: approval vacated before construction, not damages after.",
        "analog": "Vineyard v. Rancho Cordova (Cal. 2007); MCEA v. Pine Island (Minn. 2026)",
    },
    {
        "rank": 2,
        "theory": "High-capacity well permit — agency failed to weigh off-site impact",
        "hook": "State withdrawal permitting; see well-cumulative-impact",
        "impact": 5, "viability": 4, "tractability": 4,
        "why": "Operates before the water is pumped rather than after the harm. The "
               "catch is the trigger: the duty attaches only once concrete hydrologic "
               "evidence is put in front of the agency, so it rewards exactly the "
               "monitoring data this tracker collects.",
        "analog": "Lake Beulah Mgmt. Dist. v. DNR (Wis. 2011)",
    },
    {
        "rank": 3,
        "theory": "Public trust — groundwater pumping depleting a connected stream",
        "hook": "State public trust doctrine; see ptd-groundwater-nexus",
        "impact": 5, "viability": 4, "tractability": 3,
        "why": "Reaches ordinary campus-well hydrology, which is otherwise regulated as "
               "groundwater and never as the surface diversion it functionally is. Puts "
               "the duty on the county issuing the permit — the level these fights are "
               "already being fought at. Needs a demonstrated aquifer-stream connection.",
        "analog": "ELF v. SWRCB (Cal. App. 2018); Nat'l Audubon (Cal. 1983)",
    },
    {
        "rank": 4,
        "theory": "Consumer protection — published water claims are misleading",
        "hook": "State deceptive-trade-practices law; see sl-greenwashing-udap",
        "impact": 4, "viability": 4, "tractability": 5,
        "why": "The most tractable theory in either table: the evidence is FOIA'd "
               "utility billing records, not expert hydrology. Gets more available every "
               "time a disclosure law adds reporting. Impact is reputational and "
               "corrective rather than a limit on withdrawal.",
        "analog": "Wangusi v. AWS (Va. Cir. Ct. 2026)",
    },
    {
        "rank": 5,
        "theory": "Utility declines to serve a large new load",
        "hook": "Municipal service & shortage law; see util-shortage-moratorium",
        "impact": 4, "viability": 5, "tractability": 4,
        "why": "The only entry here that runs FOR the defending institution. A utility "
               "facing genuine supply constraint may refuse, reviewable only for fraud "
               "or caprice — and a capacity admission already on the record is the "
               "rational basis. Depends entirely on the utility choosing to say no.",
        "analog": "Swanson v. Marin MWD (Cal. App. 1976); Bessemer AL (2025-26)",
    },
    {
        "rank": 6,
        "theory": "Common-law negligence — subsidence or well interference",
        "hook": "State common law; see cl-negligent-subsidence",
        "impact": 4, "viability": 3, "tractability": 3,
        "why": "The opening in rule-of-capture states: liability attaches to the manner "
               "of withdrawal, not the fact of it. Strongest where drawdown produces "
               "measurable subsidence. Needs an injured neighbour as plaintiff — a "
               "coalition will hit the standing bar.",
        "analog": "Friendswood Dev. v. Smith-Southwest (Tex. 1978)",
    },
    {
        "rank": 7,
        "theory": "Interstate apportionment of a shared aquifer",
        "hook": "SCOTUS original jurisdiction; see eqap-interstate-aquifer",
        "impact": 5, "viability": 3, "tractability": 2,
        "why": "Highest ceiling, hardest to reach. Settled law since 2021 and directly "
               "on point for the Memphis Sand, but it needs a state willing to sue and "
               "clear-and-convincing proof of injury — which is why utility-level "
               "reporting laws are the precondition rather than a side issue.",
        "analog": "Mississippi v. Tennessee (2021)",
    },
    {
        "rank": 8,
        "theory": "Inter-basin transfer junior-priority challenge",
        "hook": "Area-of-origin statutes; see xfer-area-of-origin",
        "impact": 3, "viability": 4, "tractability": 4,
        "why": "Underused and statutory rather than litigated: water piped out of basin "
               "is junior to every right granted there first, so it is cut first in "
               "drought. Applies only where supply actually crosses a basin line.",
        "analog": "Tex. Water Code §11.085",
    },
]


def _theory_score_cell(value: int) -> str:
    """Render one Impact/Viability/Tractability score cell, clamped to 1–5."""
    v = max(1, min(5, int(value)))
    return f'<td class="theory-score theory-s{v}">{v}</td>'


def _build_cwa_theories_html(theories: list[dict]) -> str:
    """Pure HTML for the prioritized CWA-application theories table.

    Shared by the Streamlit panel (``render_cwa_application_theories``) and the
    static site (``build_site``) so the scored ranking has a single source of
    truth. Forward-looking analysis — scoring is merit-only (Impact / Viability
    / Tractability), deliberately not keyed to any operator's or official's
    identity or politics.
    """
    rows = []
    for t in sorted(theories, key=lambda x: x["rank"]):
        analog = t.get("analog", "")
        analog_html = (
            f'<div class="theory-analog">Analog: {html.escape(analog)}</div>'
            if analog and analog != "—"
            else ""
        )
        rows.append(
            "<tr>"
            f'<td class="theory-rank">{int(t["rank"])}</td>'
            f'<td><strong>{html.escape(t["theory"])}</strong>'
            f'<div class="theory-hook">{html.escape(t["hook"])}</div></td>'
            f'{_theory_score_cell(t["impact"])}'
            f'{_theory_score_cell(t["viability"])}'
            f'{_theory_score_cell(t["tractability"])}'
            f'<td>{html.escape(t["why"])}{analog_html}</td>'
            "</tr>"
        )
    return (
        '<p class="theory-note">Forward-looking analysis — <strong>no data-center CWA '
        "enforcement case exists yet</strong>. Scored on public-interest merit only: "
        "<strong>I</strong>mpact (community/environmental harm averted), "
        "<strong>V</strong>iability (legal strength post-<em>Sackett</em>/<em>Maui</em>), "
        "<strong>T</strong>ractability (can this tracker source the evidence via ECHO "
        "DMR/SNC, public permits, FOIA). 5 = strongest; sorted by priority.</p>"
        '<div class="table-wrap"><table class="theory-table"><thead><tr>'
        "<th>#</th><th>Theory (CWA hook)</th><th>I</th><th>V</th><th>T</th>"
        "<th>Why it matters</th></tr></thead>"
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def render_cwa_application_theories():
    """Prioritized, merit-scored menu of CWA theories that could attach to a DC.

    The forward-looking companion to ``render_cwa_datacenter_insights``: that
    panel reads what the *record* shows; this one ranks where enforcement could
    realistically go next, scored by impact, legal viability, and how readily
    this project can source the evidence.
    """
    with st.expander(
        "Prioritized application theories — what could attach to a data center"
    ):
        st.markdown(
            _build_cwa_theories_html(CWA_APPLICATION_THEORIES),
            unsafe_allow_html=True,
        )
        st.markdown("##### Beyond the Clean Water Act — state and doctrine theories")
        st.caption(
            "Most tracked conflicts are about *getting* water, which the Clean "
            "Water Act barely addresses. Same merit-only scoring, applied to the "
            "non-CWA families in the Part 1 toolkit."
        )
        st.markdown(
            _build_cwa_theories_html(DOCTRINE_APPLICATION_THEORIES),
            unsafe_allow_html=True,
        )
        st.caption(
            "Full write-up with primary-source citations: "
            "docs/cwa-enforcement-and-data-centers.md"
        )


def _cwa_statute_explainer_md() -> str:
    """Markdown body for the 'What is a CWA investigation?' expander.

    Leads with verbatim statute language from the U.S. Code (via Cornell LII,
    the canonical free primary source) and EPA's plain-language summary,
    then layers reputable secondary context. Kept in its own function so the
    text can be unit-tested for the presence of the primary-source citations.
    """
    return (
        "#### 1. What the statute is\n\n"
        "The Clean Water Act is the common name for the **Federal Water "
        "Pollution Control Act**, codified at 33 U.S.C. §§ 1251–1389. Its "
        "stated objective, in the words of the statute itself:\n\n"
        "> \"The objective of this chapter is to restore and maintain the "
        "chemical, physical, and biological integrity of the Nation's "
        "waters.\" — **33 U.S.C. § 1251(a)**\n\n"
        "EPA's own plain-language summary describes the law this way: "
        "\"The Clean Water Act (CWA) establishes the basic structure for "
        "regulating discharges of pollutants into the waters of the United "
        "States and regulating quality standards for surface waters.\" "
        "— **EPA, *Summary of the Clean Water Act***\n\n"
        "#### 2. What authority EPA and DOJ have\n\n"
        "Two operative sections do most of the work in the cases tracked "
        "here:\n\n"
        "- **Section 301 / 33 U.S.C. § 1311** makes the discharge of any "
        "pollutant from a point source to a water of the United States "
        "**unlawful** unless authorized by a permit.\n"
        "- **Section 402 / 33 U.S.C. § 1342** creates the National "
        "Pollutant Discharge Elimination System (NPDES), the permit "
        "program that authorizes lawful discharges and sets numeric "
        "effluent limits. Per EPA: \"The CWA made it unlawful to discharge "
        "any pollutant from a point source into navigable waters, unless a "
        "permit was obtained\" through the NPDES program.\n\n"
        "When a permittee violates those limits, **Section 309 / 33 U.S.C. "
        "§ 1319** gives EPA escalating enforcement authority — "
        "administrative orders, civil judicial action, and criminal "
        "referral. The statute's civil-penalty cap was originally set at:\n\n"
        "> \"…shall be subject to a civil penalty not to exceed $25,000 per "
        "day for each violation.\" — **33 U.S.C. § 1319(d)**\n\n"
        "That figure is adjusted annually for inflation under the Federal "
        "Civil Penalties Inflation Adjustment Act; the 2024-adjusted "
        "maximum is approximately **$66,712 per day per violation**, which "
        "is the per-day exposure referenced in EPA Region 5 cases such as "
        "Republic Steel in this dataset.\n\n"
        "EPA can also commence civil litigation directly: \"The "
        "Administrator is authorized to commence a civil action for "
        "appropriate relief, including a permanent or temporary "
        "injunction, for any violation…\" — **33 U.S.C. § 1319(b)**\n\n"
        "Beyond agency action, **Section 505 / 33 U.S.C. § 1365** lets "
        "private parties sue dischargers directly when EPA and the state "
        "do not act:\n\n"
        "> \"…any citizen may commence a civil action on his own behalf — "
        "(1) against any person…who is alleged to be in violation of (A) "
        "an effluent standard or limitation under this chapter…\" "
        "— **33 U.S.C. § 1365(a)**\n\n"
        "Several entries in this dataset (e.g., the Atlanta R.M. Clayton "
        "consent decree and the QTS Fayetteville matter) originated as "
        "Section 505 citizen-suit notices from groups like Chattahoochee "
        "Riverkeeper and Flint Riverkeeper.\n\n"
        "#### 3. Why investigations get deployed\n\n"
        "EPA frames day-to-day water enforcement as: \"EPA's day-to-day "
        "enforcement actions aim at returning facilities to compliance "
        "with existing laws…\" The agency organizes its work into six "
        "focus areas, each of which appears in the cases we track:\n\n"
        "1. **Wastewater management** — POTW consent decrees (Jersey "
        "City MUA, Cahokia Heights, Guam Waterworks, Reading WWTP, "
        "Youngstown, MDC Hartford).\n"
        "2. **Pretreatment** — industrial users discharging to municipal "
        "sewers (Yuengling, Swift Beef, Agri Star). This is the "
        "regulatory regime that most directly governs data-center "
        "cooling-tower blowdown.\n"
        "3. **Stormwater** — construction general-permit enforcement "
        "(Microsoft Boydton, Google Stillwater, Energix VA, Johns "
        "Hopkins DSAI) — the primary touch point for data-center "
        "construction sites.\n"
        "4. **CAFOs** — concentrated animal feeding operations (Wynja "
        "Feedlot) — useful as a per-day-violation precedent for any "
        "unpermitted industrial discharge.\n"
        "5. **Oil & hazardous spills** — Section 311 / SPCC (Plains "
        "Pipeline, Norfolk Southern, Johns Hopkins diesel) — relevant "
        "to data-center backup-generator fuel storage.\n"
        "6. **Wetlands** — Section 404 dredge-and-fill (Sackett, "
        "Rapanos, Lewis) — affects site-grading at large campuses.\n\n"
        "#### 4. Why this matters for data centers\n\n"
        "Data centers themselves rarely hold direct NPDES discharge "
        "permits — they typically buy potable water from a utility and "
        "discharge cooling-water blowdown to a municipal POTW. That "
        "structure puts most of their CWA exposure into the pretreatment "
        "program (the receiving POTW enforces locally-issued industrial-"
        "user permits) and into the construction-stormwater program "
        "(general contractor liability during build-out). The "
        "\"datacenter\" category here captures the rare direct cases; the "
        "\"industrial\" category is the closest practical analog for what "
        "post-build enforcement looks like; \"precedent\" captures the "
        "Supreme Court and federal appellate rulings (Sackett, Maui, "
        "Loper Bright, SF v. EPA) that set how aggressively any of this "
        "can be enforced against a data center going forward.\n\n"
        "**Primary sources:** "
        "[33 U.S.C. § 1251 (Cornell LII)]"
        "(https://www.law.cornell.edu/uscode/text/33/1251) · "
        "[33 U.S.C. § 1319 (Cornell LII)]"
        "(https://www.law.cornell.edu/uscode/text/33/1319) · "
        "[33 U.S.C. § 1342 (Cornell LII)]"
        "(https://www.law.cornell.edu/uscode/text/33/1342) · "
        "[33 U.S.C. § 1365 (Cornell LII)]"
        "(https://www.law.cornell.edu/uscode/text/33/1365) · "
        "[EPA — Summary of the Clean Water Act]"
        "(https://www.epa.gov/laws-regulations/summary-clean-water-act) · "
        "[EPA — Water Enforcement]"
        "(https://www.epa.gov/enforcement/water-enforcement)"
    )


def _cwa_category_colors() -> dict:
    """Map category → pill color, sourced from the shared COLORS palette."""
    return {
        "datacenter": COLORS["primary"],
        "adjacent": COLORS["tertiary"],
        "industrial": COLORS["warning"],
        "precedent": COLORS["secondary"],
    }


def _cwa_summary(cases: list[dict]) -> str:
    """'2 Data Center · 5 Industrial Water · 4 Landmark Precedent' summary string."""
    counts: dict[str, int] = {}
    for c in cases:
        cat = c.get("category", "other")
        counts[cat] = counts.get(cat, 0) + 1
    ordered = sorted(counts, key=lambda k: CWA_CATEGORY_ORDER.get(k, 9))
    return " · ".join(
        f"{counts[c]} {CWA_CATEGORY_LABELS.get(c, c.title())}" for c in ordered
    )


def _cwa_year_end(year_str: str) -> int:
    """Return the end year as int from a 'YYYY' or 'YYYY-YYYY' string. 0 on failure."""
    if not year_str:
        return 0
    m = re.search(r"(\d{4})\s*$", str(year_str))
    return int(m.group(1)) if m else 0


# Heuristics for the computed data-center insight panel. Kept module-level so
# the pure helper below stays testable without Streamlit.
_CWA_HYPERSCALERS = ("amazon", "google", "microsoft", "meta", "xai")
_CWA_CONTRACTOR_KW = (
    "construction",
    "contractor",
    "subcontractor",
    "dewatering",
    "aldinger",
    "consigli",
)
# True construction-stormwater signals — kept strict so the count reflects
# CWA §402 erosion/sediment touchpoints, not any mention of "construction".
_CWA_CONSTRUCTION_KW = ("stormwater", "sediment", "erosion", "silt")


def _cwa_datacenter_insights(cases: list[dict]) -> dict:
    """Compute structural patterns across the *data-center* CWA cases.

    These are the "so what" the tracker exists to surface: who actually holds
    the permit (the operator usually sits one entity removed) and what triggers
    CWA scrutiny in the first place (overwhelmingly construction stormwater,
    not operational cooling discharge). Pure function over the dataset so the
    numbers stay correct as cases are added and it can be unit-tested without
    Streamlit.
    """
    dc = [c for c in cases if c.get("category") == "datacenter"]
    total = len(dc)

    def _is_contractor_led(c: dict) -> bool:
        # Test the *leading* name (before the first comma), not a substring —
        # a contractor's parenthetical often mentions the hyperscaler it works
        # for (e.g. "Walbridge Aldinger LLC (Microsoft contractor)"), so an
        # "in" check would wrongly read that as operator-led. Shielded == the
        # respondent leads with a contractor, not the operator.
        lead = c.get("respondent", "").split(",")[0].lower().strip()
        if any(lead.startswith(h) for h in _CWA_HYPERSCALERS):
            return False
        return any(k in lead for k in _CWA_CONTRACTOR_KW)

    def _is_construction_stormwater(c: dict) -> bool:
        blob = (
            c.get("cwa_section", "") + " " + c.get("violation_summary", "")
        ).lower()
        return any(k in blob for k in _CWA_CONSTRUCTION_KW)

    return {
        "total": total,
        "contractor_permittee": sum(1 for c in dc if _is_contractor_led(c)),
        "construction_stormwater": sum(
            1 for c in dc if _is_construction_stormwater(c)
        ),
    }


def _cwa_statute_breadth_insight(cases: list[dict], readings_by_id: dict) -> dict:
    """How the *whole* datacenter+adjacent record spreads across statutes.

    Unlike `_cwa_datacenter_insights` (historical enforcement only, datacenter
    category only), this scans historical AND active/potential cases across
    both datacenter and adjacent categories — the question here is which
    statute the problem space maps to, not just already-resolved enforcement.
    Added 2026-07-07 because every existing insight bullet was CWA-only, even
    though the record now covers SDWA/TSCA/RCRA/RHA too. Pure + testable
    without Streamlit.
    """
    scoped = [c for c in cases if c.get("category") in ("datacenter", "adjacent")]
    total = len(scoped)
    sdwa = sum(1 for c in scoped if "SDWA" in _case_statutes(c, readings_by_id))
    no_cwa = sum(1 for c in scoped if "CWA" not in _case_statutes(c, readings_by_id))
    return {"total": total, "sdwa": sdwa, "no_cwa": no_cwa}


def render_cwa_datacenter_insights(
    cases: list[dict] | None = None,
    all_cases: list[dict] | None = None,
    readings_by_id: dict | None = None,
):
    """Headline 'what this record tells data centers' panel.

    Pass ``cases`` to scope the first three bullets (e.g., historical-only
    subset). When omitted, loads the full dataset — kept for backward
    compatibility. Pass ``all_cases`` + ``readings_by_id`` to add the
    statute-breadth bullet, which deliberately scans the *whole* record
    (historical + potential, datacenter + adjacent) rather than the possibly
    narrower ``cases`` scope. Computed live so counts move with the dataset.

    Collapsed by default (2026-07-07): this was the largest always-visible
    block between the tab title and the Part 1-4 sub-tabs — an expander gets
    a reader to the substantive tabs immediately, with the analysis one click
    away rather than a scroll away.
    """
    if cases is None:
        payload = load_cwa_investigations()
        cases = payload.get("cases", [])
    stats = _cwa_datacenter_insights(cases)
    total = stats["total"]
    if not total:
        return
    with st.expander("What this record tells data centers", expanded=False):
        st.markdown(
            f"- **The permittee shield.** {stats['contractor_permittee']} of "
            f"{total} resolved data-center enforcement cases name a construction "
            "contractor or subcontractor — not the hyperscaler — as the party "
            "on the permit. Operators routinely sit one entity removed from the "
            "permittee, which is why direct enforcement against them is thin."
        )
        st.markdown(
            f"- **CWA risk is front-loaded into construction.** Construction "
            "stormwater, sediment, and erosion under the §402 Construction "
            f"General Permit is the most common touchpoint — it appears in "
            f"{stats['construction_stormwater']} of {total} historical cases, "
            "far more than operational cooling-water discharge."
        )
        st.markdown(
            "- **The liability frontier is moving.** The 2026 Amazon Boardman "
            "settlement ($20.5M, Oregon nitrate) is the first eight-figure "
            "direct-hyperscaler water settlement — pushing exposure beyond "
            "stormwater into groundwater and nutrient contamination."
        )
        st.markdown(
            "- **Why this tracker watches the WWTP, not the data center.** "
            "Cooling-water blowdown goes to the municipal sewer, so the "
            "operational CWA exposure rides on the *receiving* treatment "
            "plant's NPDES permit — the very permits this project tracks via "
            "EPA ECHO. Watch the POTW's compliance status, not the data "
            "center's near-empty stormwater permit."
        )
        if all_cases is not None and readings_by_id is not None:
            breadth = _cwa_statute_breadth_insight(all_cases, readings_by_id)
            if breadth["total"]:
                st.markdown(
                    "- **Look beyond the CWA.** Of "
                    f"{breadth['total']} data-center and adjacent water fights in "
                    f"this record, {breadth['sdwa']} carry an SDWA reading and "
                    f"{breadth['no_cwa']} have no CWA angle at all — including the "
                    "Amazon Boardman settlement above, which resolved under state "
                    "tort law and SDWA/RCRA, not the Clean Water Act. Aquifer "
                    "depletion, well failures, and public-water-system strain are "
                    "consistently an SDWA story, not a CWA one."
                )


def render_cwa_tracker():
    """Render the Clean Water Act investigations panel.

    Split into two sections:
    1. Historical enforcement record — enforcement actions, penalties,
       settlements, and landmark rulings that have actually occurred.
       Industrial cases are the closest legal analogs to data center
       operations; precedent rulings define CWA's legal scope.
    2. Active & potential exposure — named data center sites where
       proceedings are pending or circumstances match historical patterns
       but no formal CWA enforcement has been issued yet.
    """
    st.subheader("Federal Water Law & Data Centers — Authorities, Record, Exposure")
    st.markdown(
        "Three views on federal water law and data centers: the **statutory "
        "toolkit** (every EPA / Army Corps water authority — CWA, SDWA, TSCA, "
        "RCRA, Rivers & Harbors Act — and how each could reach a data center), "
        "the **historical record** that has actually built under those "
        "authorities (penalties, settlements, court rulings), and the **named "
        "sites** where water conflicts are live. The mappings overlap by "
        "design — one fact pattern can trigger several readings."
    )

    payload = load_cwa_investigations()
    cases = payload.get("cases", [])
    if not cases:
        note = payload.get("note") or "Dataset not found or empty."
        st.info(note)
        return

    authorities_payload = load_water_authorities()
    readings_by_id = _readings_by_id(authorities_payload)

    historical = [c for c in cases if c.get("display_section", "historical") == "historical"]
    potential = [c for c in cases if c.get("display_section") == "potential"]

    # Headline synthesis — first three bullets computed over historical
    # enforcement only; the statute-breadth bullet scans the full record.
    render_cwa_datacenter_insights(historical, all_cases=cases, readings_by_id=readings_by_id)

    # Forward-looking bridge from historical record to potential exposure.
    render_cwa_application_theories()

    with st.expander(
        "What is a Clean Water Act investigation? — statute, authority, "
        "and why it's deployed"
    ):
        st.markdown(_cwa_statute_explainer_md())

    all_ids = {c.get("case_id") for c in cases}
    conflicts_payload = load_dc_water_conflicts()
    sites = conflicts_payload.get("sites", [])
    n_readings = len(authorities_payload.get("readings", []))

    # Sub-tabs instead of stacked expanders: Part 2 (the historical record
    # most users want) no longer sits behind Part 1's content in the scroll
    # order — each part is one click away. Mirrors the static site's
    # .subtab/.subtabpanel pair (build_site.py). Conflict sites moved to the
    # Issues & Claims tab (Spec A3), leaving this a purely legal record.
    st.markdown("---")
    tab_labels = [
        f"Part 1 · Toolkit ({n_readings})",
        f"Part 2 · Historical Record ({len(historical)})",
        f"Part 3 · Active/Potential Exposure ({len(potential)})",
    ]
    part_tabs = st.tabs(tab_labels)

    with part_tabs[0]:
        st.markdown(
            f"**{n_readings} statutory readings** "
            "across the CWA, SDWA, TSCA, RCRA, and the Rivers & Harbors Act — each "
            "card explains what the authority historically covered, how it could "
            "apply to a data-center fact pattern, and which cases below show it in "
            "use. Case and site cards link back here via the *statute applicability* rows. "
            "Jump straight to an act with the pills below instead of scrolling — each "
            "statute is collapsed until you open it."
        )
        st.markdown(
            _build_authorities_html(authorities_payload, all_ids),
            unsafe_allow_html=True,
        )

    with part_tabs[1]:
        st.markdown(
            f"**{len(historical)} cases** — enforcement actions, penalties, settlements, "
            "landmark court rulings, and standing rulemakings that have **actually "
            "occurred**, under the CWA and the other federal water authorities above. "
            "**Industrial cases are legal analogs** — they show the enforcement pattern "
            "for operations similar to data centers, but are enforcement against *other* "
            "industries, not data centers themselves. "
            "Precedent rulings define the legal scope for future enforcement."
        )

        # Filter controls. Primary axis: project type (what kind of water issue);
        # secondary: statute + case group (who it involves) + 2020+ toggle.
        selected_statutes = st.multiselect(
            "Filter by statute",
            options=WATER_STATUTE_ORDER,
            default=WATER_STATUTE_ORDER,
            format_func=lambda k: f"{k} — "
            + authorities_payload.get("statutes", {}).get(k, {}).get("name", k),
            key="cwa_statute_filter",
        )
        selected_types = st.multiselect(
            "Filter by project type",
            options=list(CWA_CASE_TYPE_LABELS.keys()),
            default=list(CWA_CASE_TYPE_LABELS.keys()),
            format_func=lambda k: CWA_CASE_TYPE_LABELS.get(k, k.title()),
            key="cwa_case_type_filter",
        )
        # Adjacent cases all moved to section 2 (potential), so only
        # datacenter/industrial/precedent remain here.
        hist_cats = sorted(
            {c.get("category") for c in historical if c.get("category")},
            key=lambda k: CWA_CATEGORY_ORDER.get(k, 9),
        )
        filter_cols = st.columns([3, 1])
        with filter_cols[0]:
            selected_categories = st.multiselect(
                "Filter by case group",
                options=hist_cats,
                default=hist_cats,
                format_func=lambda k: CWA_CATEGORY_LABELS.get(k, k.title()),
                key="cwa_category_filter",
            )
        with filter_cols[1]:
            recent_only = st.toggle(
                "2020 onward only",
                value=False,
                key="cwa_recent_only",
                help="Show only cases with an end year of 2020 or later.",
            )

        filtered_hist = [
            c
            for c in historical
            if c.get("category") in selected_categories
            and c.get("case_type") in selected_types
            and any(
                s in selected_statutes for s in _case_statutes(c, readings_by_id)
            )
        ]
        if recent_only:
            filtered_hist = [
                c for c in filtered_hist if _cwa_year_end(c.get("year", "")) >= 2020
            ]

        if filtered_hist:
            st.markdown(
                f"**Showing {len(filtered_hist)} of {len(historical)} historical cases** "
                f"— {_cwa_summary(filtered_hist)}"
            )
            sorted_hist = sorted(
                filtered_hist,
                key=lambda c: (
                    CWA_CATEGORY_ORDER.get(c.get("category"), 9),
                    -_cwa_year_end(c.get("year", "")),
                ),
            )
            st.markdown(
                "".join(
                    _build_cwa_case_html(case, all_ids, readings_by_id)
                    for case in sorted_hist
                ),
                unsafe_allow_html=True,
            )
        else:
            st.info("No cases match the current filter. Try widening the category or year selection.")

    with part_tabs[2]:
        st.markdown(
            f"**{len(potential)} named data center sites** where regulatory proceedings "
            "are active (pending permit applications, ongoing investigations, active "
            "citizen suits) or where the factual circumstances match the historical "
            "enforcement patterns above — but **no formal CWA enforcement action has "
            "been issued yet**. Use the theories panel above to trace which CWA hook "
            "applies to each site."
        )

        sorted_pot = sorted(
            potential,
            key=lambda c: (
                CWA_CATEGORY_ORDER.get(c.get("category"), 9),
                -_cwa_year_end(c.get("year", "")),
            ),
        )
        # One markdown blob for all case cards — each card is a self-contained
        # <div class="bill-card">, so the joined output renders identically.
        st.markdown(
            "".join(
                _build_cwa_case_html(case, all_ids, readings_by_id)
                for case in sorted_pot
            ),
            unsafe_allow_html=True,
        )

    last_updated = payload.get("last_updated") or "unknown"
    st.caption(
        f"Dataset last updated {last_updated}. "
        f"Total: {len(cases)} entries "
        f"({len(historical)} historical enforcement, {len(potential)} active/potential)."
    )




def _readings_by_id(payload: dict | None = None) -> dict:
    """reading_id → reading dict from the water-authorities registry."""
    if payload is None:
        payload = load_water_authorities()
    return {r["reading_id"]: r for r in payload.get("readings", [])}


def _ordered_statutes(statutes: set[str]) -> list[str]:
    """Order a statute set by WATER_STATUTE_ORDER, unknown codes last."""
    return [s for s in WATER_STATUTE_ORDER if s in statutes] + sorted(
        statutes - set(WATER_STATUTE_ORDER)
    )


def _case_statutes(case: dict, readings_by_id: dict) -> list[str]:
    """Derive a case's statute list from its `authorities` reading_ids.

    Ordered by WATER_STATUTE_ORDER, de-duplicated. Falls back to ["CWA"] for
    cases with no mapped authorities (e.g. pure administrative-law precedent
    like Loper Bright, carried in this record for its CWA consequences).
    """
    statutes = {
        readings_by_id[a]["statute"]
        for a in case.get("authorities", [])
        if a in readings_by_id
    }
    if not statutes:
        return ["CWA"]
    return _ordered_statutes(statutes)


def _statute_pill_html(statute: str, css_class: str = "cwa-status-pill") -> str:
    color = WATER_STATUTE_COLORS.get(statute, COLORS["secondary"])
    return (
        f'<span class="{css_class}" style="background:{color}">'
        f"{html.escape(statute)}</span>"
    )


def _case_links_html(case_ids_to_link: list[str], case_ids: set[str] | None) -> str:
    """' · '-joined case captions, each an in-page #cwa-<id> anchor when the
    target card exists in the dataset. The single source of the anchor/caption
    format used by reading cards, case cards, and conflict-site cards."""
    links = []
    for cid in case_ids_to_link:
        caption = html.escape(_cwa_case_caption(cid))
        if case_ids is not None and cid in case_ids:
            links.append(f'<a href="#cwa-{html.escape(cid)}">{caption}</a>')
        else:
            links.append(caption)
    return " · ".join(links)


def _sources_html(sources: list[dict]) -> str:
    """Labeled 'Sources' block shared by case and conflict-site cards."""
    if not sources:
        return ""
    esc = html.escape
    items = []
    for s in sources:
        title = esc(s.get("title", "Source"))
        url = s.get("url", "")
        stype = esc(s.get("type", ""))
        link = (
            f'<a href="{esc(url)}" target="_blank" rel="noopener">{title}</a>'
            if url
            else title
        )
        if stype:
            link += f' <span class="cwa-source-type">({stype})</span>'
        items.append(link)
    return (
        '<div class="bill-section-label">Sources</div>'
        f'<div class="cwa-sources">{" · ".join(items)}</div>'
    )


def _reading_link_html(reading: dict) -> str:
    """In-page anchor link to one reading card in the authorities section."""
    esc = html.escape
    return (
        f'<a href="#reading-{esc(reading["reading_id"])}">'
        f'{esc(reading["statute"])} — {esc(reading["name"])}</a>'
    )


def _case_hooks_html(case: dict, readings_by_id: dict) -> str:
    """'Statutory hooks' cross-link row for a case card (may be empty)."""
    links = [
        _reading_link_html(readings_by_id[a])
        for a in case.get("authorities", [])
        if a in readings_by_id
    ]
    if not links:
        return ""
    return (
        '<div class="cwa-analogs">Statute applicability: '
        f'{" · ".join(links)}</div>'
    )


def _build_reading_card_html(
    reading: dict, case_ids: set[str] | None = None,
) -> str:
    """One statutory-reading card for the water-law toolkit section.

    Anchored as #reading-<reading_id> so case cards and conflict-site cards
    can cross-link to it. Example cases link back to their #cwa-<id> anchors
    when the case exists in the dataset.
    """
    esc = html.escape
    statute = reading.get("statute", "")
    head = (
        '<div class="bill-card-head">'
        f'<span class="bill-card-id">{esc(reading.get("name", ""))}</span>'
        f'{_statute_pill_html(statute, css_class="bill-card-pill")}'
        "</div>"
    )
    class_bits = [
        f'<span class="cwa-instrument">{esc(reading.get("section", ""))}</span>',
        f'<span class="cwa-type-pill">{esc(reading.get("agency", ""))}</span>',
    ]
    class_row = f'<div class="cwa-class-row">{"".join(class_bits)}</div>'
    sections = [
        '<div class="bill-section-label">What it covers — historical use</div>'
        f'<p class="bill-sentiment">{esc(reading.get("what_it_covers", ""))}</p>',
        '<div class="bill-section-label">How it could apply to a data center</div>'
        f'<p class="cwa-takeaway">{esc(reading.get("dc_applicability", ""))}</p>',
    ]
    examples = reading.get("example_case_ids", [])
    if examples:
        sections.append(
            '<div class="cwa-analogs">Cases in this record using this hook: '
            f'{_case_links_html(examples, case_ids)}</div>'
        )
    return (
        f'<div class="bill-card" id="reading-{esc(reading["reading_id"])}">'
        f'{head}{class_row}{"".join(sections)}</div>'
    )


def _build_authorities_html(payload: dict, case_ids: set[str] | None = None) -> str:
    """The full water-law toolkit: reading cards grouped by statute.

    Each statute is a collapsed-by-default <details> accordion (20 readings
    across 5 statutes was a long scroll to reach e.g. RHA at the bottom), and
    a jump-nav row of statute pills sits above them — clicking one scrolls
    straight to that statute's summary AND opens it in one click via the
    inline onclick, so reaching any single act never requires scrolling past
    the others first (2026-07-07).
    """
    esc = html.escape
    statutes_meta = payload.get("statutes", {})
    readings = payload.get("readings", [])
    order = {s: i for i, s in enumerate(WATER_STATUTE_ORDER)}
    seen = []
    for r in readings:
        if r["statute"] not in seen:
            seen.append(r["statute"])
    seen.sort(key=lambda s: order.get(s, 99))
    counts = {s: sum(1 for r in readings if r["statute"] == s) for s in seen}

    nav_links = "".join(
        f'<a class="statute-jump" href="#statute-{esc(s)}" '
        f'style="background:{WATER_STATUTE_COLORS.get(s, COLORS["secondary"])}" '
        f"onclick=\"var d=document.getElementById('statute-{esc(s)}'); "
        'if(d) d.open=true;">'
        f"{esc(s)} <span class=\"statute-jump-count\">({counts[s]})</span></a>"
        for s in seen
    )
    blocks = [f'<div class="statute-jumpnav">{nav_links}</div>']

    for statute in seen:
        meta = statutes_meta.get(statute, {})
        title = esc(meta.get("name", statute))
        full = esc(meta.get("full_name", ""))
        agencies = esc(meta.get("agencies", ""))
        url = meta.get("url", "")
        full_html = (
            f'<a href="{esc(url)}" target="_blank" rel="noopener">{full}</a>'
            if url
            else full
        )
        cards = "".join(
            _build_reading_card_html(r, case_ids)
            for r in readings
            if r["statute"] == statute
        )
        blocks.append(
            f'<details class="statute-group" id="statute-{esc(statute)}">'
            f'<summary class="statute-head">{_statute_pill_html(statute)} '
            f'{title} <span class="statute-count">'
            f'({counts[statute]})</span></summary>'
            f'<p class="statute-meta">{full_html}'
            f'{" · Administered by: " + agencies if agencies else ""}</p>'
            f"{cards}"
            "</details>"
        )
    return "".join(blocks)


def _site_outcome_profile(site: dict, cases_by_id: dict) -> list[tuple[str, int]]:
    """Outcome types across every case a site points at, commonest first.

    Derived at render rather than stored, so it can never drift from the
    ``outcome_type`` values it summarizes — the same rule the statute pills
    follow. Counts each case once even where several readings cite it, so a
    heavily cross-referenced precedent does not dominate the profile.
    """
    seen: set[str] = set()
    for mapping in site.get("applicable_readings", []):
        # Negative mappings say a doctrine does NOT reach the site; their
        # historical cases are counter-examples, not the site's likely path.
        if mapping.get("reaches") is False:
            continue
        seen.update(mapping.get("analogous_cases", []) or [])
    seen.update(site.get("related_case_ids", []) or [])

    counts: dict[str, int] = {}
    for case_id in seen:
        case = cases_by_id.get(case_id)
        if not case:
            continue
        for otype in case.get("outcome_type", []):
            counts[otype] = counts.get(otype, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def _build_site_outcome_note_html(site: dict, cases_by_id: dict) -> str:
    """'What has happened in comparable matters' line for a conflict-site card.

    Reports the historical record's shape without predicting this site's
    outcome — the distinction the copy rule in the plan turns on.
    """
    profile = _site_outcome_profile(site, cases_by_id)
    if not profile:
        return ""
    top = profile[:3]
    parts = [
        f"{OUTCOME_TYPE_LABELS.get(otype, otype).lower()} ({n})" for otype, n in top
    ]
    listed = ", ".join(parts[:-1]) + (f" and {parts[-1]}" if len(parts) > 1 else parts[-1])
    total = sum(n for _, n in profile)
    return (
        '<div class="conflict-outcome-note">'
        f"<strong>How comparable matters resolved:</strong> across the cases this "
        f"site maps to, the recorded outcomes were most often {html.escape(listed)}"
        f" — {total} outcome tags in total. Historical pattern only; it does not "
        "predict what happens here."
        "</div>"
    )


# Operator strings in the conflict registry are free text ("Amazon Web
# Services", "Meta (campus built by Goat Systems LLC)", "QTS and Compass
# (rezoning applicants)"), so the join to company_slug needs aliases the
# display names do not supply.
_COMPANY_ALIASES = {
    "amazon": ("amazon", "aws"),
    "meta": ("meta", "facebook"),
    "google": ("google", "alphabet"),
    "microsoft": ("microsoft",),
    "xai": ("xai", "colossus"),
    "qts": ("qts",),
    "compass": ("compass",),
    "oracle": ("oracle",),
    "openai": ("openai",),
    "crusoe": ("crusoe",),
    "coreweave": ("coreweave",),
    "nebius": ("nebius",),
    "switch": ("switch",),
    "edgeconnex": ("edgeconnex",),
    "vantage": ("vantage",),
    "wonder-valley": ("wonder valley",),
    "anthropic": ("anthropic",),
}


def _site_company_slugs(site: dict) -> list[str]:
    """Company slugs named in a site's free-text operator field."""
    operator = str(site.get("operator", "")).lower()
    return [
        slug
        for slug, aliases in _COMPANY_ALIASES.items()
        if any(alias in operator for alias in aliases)
    ]


def _build_says_vs_does_html(site: dict, claims: list[dict], companies: dict) -> str:
    """The operator's own water claims, shown on the conflict-site card.

    The sharpest thing this dataset can do is put the two next to each other:
    a company's water-positive pledge alongside the dried wells its campus is
    accused of causing. Both halves already existed; nothing joined them,
    because the claims lived in another tab entirely.

    Company-level pledges are included as well as site-specific promises — a
    global commitment is exactly what a local failure tests.
    """
    slugs = _site_company_slugs(site)
    if not slugs:
        return ""
    site_id = site.get("site_id")
    matched = [
        c
        for c in claims
        if c.get("company_slug") in slugs
        and (
            site_id in (c.get("related_site_ids") or [])
            or c.get("claim_type") in ("water-positive-pledge", "efficiency-wue")
        )
    ]
    if not matched:
        return ""

    rows = []
    for claim in matched[:3]:
        status = (claim.get("delivered") or {}).get("status", "")
        badge = (
            f'<span class="svd-status svd-{html.escape(status)}">'
            f"{html.escape(status.title())}</span>"
            if status
            else ""
        )
        company = companies.get(claim.get("company_slug", ""), claim.get("company_slug", ""))
        rows.append(
            f'<li><span class="svd-company">{html.escape(company)}</span> '
            f"&ldquo;{html.escape(claim.get('statement', '')[:180])}&rdquo; {badge}</li>"
        )
    return (
        '<div class="says-vs-does">'
        '<div class="bill-section-label">What the operator says about water</div>'
        f'<ul class="svd-list">{"".join(rows)}</ul></div>'
    )


def _issue_type_summary_html(sites: list[dict]) -> str:
    """Count-by-issue-type strip. Answers 'what kinds of problem are these?'
    before the reader opens a single card."""
    counts: dict[str, int] = {}
    for site in sites:
        for tag in site.get("issue_types", []):
            counts[tag] = counts.get(tag, 0) + 1
    if not counts:
        return ""
    # Filter to known tags ONCE, before both the chips and the headline. The
    # chips used to guard while the headline below did an unguarded lookup on
    # the same data, so an unknown tag raised KeyError mid-render.
    ordered = sorted(
        ((t, n) for t, n in counts.items() if t in ISSUE_TYPE_LABELS),
        key=lambda kv: (-kv[1], kv[0]),
    )
    if not ordered:
        return ""
    chips = "".join(
        f'<span class="issue-pill" title="{html.escape(ISSUE_TYPE_DESCRIPTIONS[t])}">'
        f"{html.escape(ISSUE_TYPE_LABELS[t])} <strong>{n}</strong></span>"
        for t, n in ordered
    )
    top = ordered[0]
    return (
        '<div class="issue-summary">'
        f"<p class=\"count-line\"><strong>{len(sites)} tracked sites</strong> across "
        f"{len(ordered)} kinds of water problem &mdash; most commonly "
        f"{html.escape(ISSUE_TYPE_LABELS[top[0]].lower())} ({top[1]} sites).</p>"
        f'<div class="cwa-class-row">{chips}</div></div>'
    )


def _build_site_doctrine_matrix_html(sites: list[dict], readings_by_id: dict) -> str:
    """Site x authority-family matrix — which doctrines are in play where.

    The precedent engine's product face: one glance answers "what kind of law
    is this fight actually about?" across the whole roster, which no amount of
    reading individual cards gives you. Cells count mapped readings; a cell
    marked with a dash is a doctrine explicitly recorded as NOT reaching that
    site, which is information rather than absence.
    """
    if not sites:
        return ""

    grid: dict[str, dict[str, int]] = {}
    negatives: dict[str, set[str]] = {}
    for site in sites:
        row: dict[str, int] = {}
        neg: set[str] = set()
        for mapping in site.get("applicable_readings", []):
            reading = readings_by_id.get(mapping.get("reading_id"))
            if not reading:
                continue
            family = reading["statute"]
            if mapping.get("reaches") is False:
                neg.add(family)
            else:
                row[family] = row.get(family, 0) + 1
        grid[site["site_id"]] = row
        negatives[site["site_id"]] = neg

    families = _ordered_statutes(
        {f for row in grid.values() for f in row} | {f for n in negatives.values() for f in n}
    )
    if not families:
        return ""

    head = "".join(
        f'<th title="{html.escape(load_water_authorities()["statutes"].get(f, {}).get("name", f))}">'
        f"{html.escape(f)}</th>"
        for f in families
    )
    rows = []
    for site in sites:
        sid = site["site_id"]
        cells = []
        for family in families:
            count = grid[sid].get(family, 0)
            if count:
                cells.append(f'<td class="dm-hit">{count}</td>')
            elif family in negatives[sid]:
                cells.append('<td class="dm-neg" title="recorded as NOT reaching this site">&ndash;</td>')
            else:
                cells.append('<td class="dm-none"></td>')
        rows.append(
            f'<tr><th class="dm-site"><a href="#site-{html.escape(sid)}">'
            f'{html.escape(site.get("site", sid))}</a></th>{"".join(cells)}</tr>'
        )

    return (
        '<div class="doctrine-matrix"><div class="table-wrap">'
        '<table class="data-table"><thead><tr><th>Site</th>'
        f"{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        '<p class="src-note">Cells count the legal readings mapped to each site. '
        "&ndash; marks a doctrine explicitly recorded as <em>not</em> reaching that "
        "site. Family codes are the accordions in Part 1.</p></div>"
    )


def _build_conflict_site_html(
    site: dict,
    readings_by_id: dict,
    case_ids: set[str] | None = None,
    cases_by_id: dict | None = None,
    claims_ctx: tuple[list[dict], dict] | None = None,
) -> str:
    """One data-center conflict-site card: fact pattern → readings → cases."""
    esc = html.escape
    head = (
        f'<div class="bill-card-head">'
        f'<span class="bill-card-id">{esc(site.get("site", ""))}</span>'
        f'<span class="bill-card-pill" style="background:{COLORS["primary"]}">'
        "DC site</span>"
        "</div>"
    )
    class_bits = []
    if site.get("location"):
        class_bits.append(
            f'<span class="cwa-type-pill">{esc(site["location"])}</span>'
        )
    statutes = _ordered_statutes(
        {
            readings_by_id[ar["reading_id"]]["statute"]
            for ar in site.get("applicable_readings", [])
            if ar.get("reading_id") in readings_by_id
        }
    )
    class_bits.extend(_statute_pill_html(s) for s in statutes)
    # Issue types answer "what kind of water problem is this?" — the question
    # the prose summaries could only answer by being read. Outline chips per
    # DESIGN.md §8: filled pills stay reserved for status.
    for tag in site.get("issue_types", []):
        if tag in ISSUE_TYPE_LABELS:
            class_bits.append(
                f'<span class="issue-pill" title="{esc(ISSUE_TYPE_DESCRIPTIONS[tag])}">'
                f'{esc(ISSUE_TYPE_LABELS[tag])}</span>'
            )
    if site.get("status_2026"):
        class_bits.append(
            f'<span class="cwa-instrument">{esc(site["status_2026"])}</span>'
        )
    class_row = f'<div class="cwa-class-row">{"".join(class_bits)}</div>'

    sections = []
    if site.get("issue_summary"):
        sections.append(
            '<div class="bill-section-label">Water issue</div>'
            f'<p class="bill-sentiment">{esc(site["issue_summary"])}</p>'
        )
    if site.get("pushback_summary"):
        sections.append(
            '<div class="bill-section-label">Pushback & response</div>'
            f'<p class="bill-sentiment">{esc(site["pushback_summary"])}</p>'
        )
    readings = site.get("applicable_readings", [])
    if readings:

        def _reading_item(ar: dict, negative: bool) -> str:
            reading = readings_by_id.get(ar.get("reading_id"))
            label = (
                _reading_link_html(reading)
                if reading
                else esc(ar.get("reading_id", ""))
            )
            analogs = ar.get("analogous_cases", [])
            analog_html = (
                '<div class="cwa-analogs">Historical cases: '
                f'{_case_links_html(analogs, case_ids)}</div>'
                if analogs
                else ""
            )
            body_class = "cwa-pathway cwa-pathway-negative" if negative else "cwa-pathway"
            return (
                f'<div class="conflict-reading"><strong>{label}</strong>'
                f'<div class="{body_class}">{esc(ar.get("how", ""))}'
                f"{analog_html}</div></div>"
            )

        # Split positive from negative mappings. A doctrine that does NOT reach
        # a site is genuinely useful — it stops an advocacy claim before it is
        # made — but it must never be mistaken for one that does, so the two
        # get separate headings and separate treatment.
        applies = [ar for ar in readings if ar.get("reaches") is not False]
        does_not = [ar for ar in readings if ar.get("reaches") is False]
        if applies:
            sections.append(
                '<div class="bill-section-label">'
                "Which legal readings could apply</div>"
                f'{"".join(_reading_item(ar, False) for ar in applies)}'
            )
        if does_not:
            sections.append(
                '<div class="bill-section-label">'
                "Doctrines that do NOT reach this site</div>"
                f'{"".join(_reading_item(ar, True) for ar in does_not)}'
            )
    if claims_ctx:
        says = _build_says_vs_does_html(site, claims_ctx[0], claims_ctx[1])
        if says:
            sections.append(says)

    if cases_by_id:
        note = _build_site_outcome_note_html(site, cases_by_id)
        if note:
            sections.append(note)

    detail_sections = []
    related = site.get("related_case_ids", [])
    if related:
        detail_sections.append(
            '<div class="cwa-analogs">Tracked case entries for this site: '
            f'{_case_links_html(related, case_ids)}</div>'
        )
    sources_block = _sources_html(site.get("sources", []))
    if sources_block:
        detail_sections.append(sources_block)
    if detail_sections:
        sections.append(
            '<details class="bill-card-details">'
            "<summary>Details — tracked cases, sources</summary>"
            f'{"".join(detail_sections)}'
            "</details>"
        )
    anchor = esc(site.get("site_id", ""))
    return (
        f'<div class="bill-card dc-site" id="site-{anchor}"'
        # The static site filters on this attribute; the Streamlit app filters
        # in Python before calling this builder. Same data, one source.
        f' data-issues="{esc(" ".join(site.get("issue_types", [])))}">'
        f'{head}{class_row}{"".join(sections)}</div>'
    )


def _build_cwa_case_html(
    case: dict,
    case_ids: set[str] | None = None,
    readings_by_id: dict | None = None,
) -> str:
    """Build the complete HTML for one CWA case card as a single markdown blob.

    case_ids, when given, is the set of all case_ids in the dataset — used to
    render analogous_cases as in-page anchors (#cwa-<id>) only when the target
    card actually exists. readings_by_id, when given, adds derived statute
    pills and 'Statutory hooks' anchor links into the authorities toolkit.
    """
    esc = html.escape
    cat_colors = _cwa_category_colors()

    respondent_raw = case.get("respondent", "")
    respondent = esc(respondent_raw)
    year_raw = str(case.get("year", ""))
    year = esc(year_raw)
    category = (case.get("category") or "").lower()
    cat_label = CWA_CATEGORY_LABELS.get(category, category.title() or "Other")
    cat_color = cat_colors.get(category, COLORS["secondary"])
    cwa_section = esc(case.get("cwa_section", ""))
    violation = esc(case.get("violation_summary", ""))
    outcome = esc(case.get("outcome", ""))
    takeaway = esc(case.get("takeaway", ""))
    sources = case.get("sources", [])

    # Skip the trailing "(YYYY)" if the year is already embedded in the
    # respondent (e.g., precedent case captions like "Rapanos v. US (2006)").
    year_already_in_caption = year_raw and (
        f"({year_raw})" in respondent_raw
        or (
            "-" in year_raw
            and any(part and f"({part})" in respondent_raw for part in year_raw.split("-"))
        )
    )
    year_html = (
        f' <span class="cwa-year">({year})</span>'
        if year and not year_already_in_caption
        else ""
    )
    head = (
        '<div class="bill-card-head">'
        f'<span class="bill-card-id">{respondent}{year_html}</span>'
        f'<span class="bill-card-pill" style="background:{cat_color}">'
        f'{esc(cat_label)}</span>'
        '</div>'
    )

    # Classification row — the at-a-glance answer to "what kind of case is
    # this, and did the CWA actually get used?"
    case_type = (case.get("case_type") or "").lower()
    type_label = CWA_CASE_TYPE_LABELS.get(case_type, "")
    status = (case.get("cwa_applied") or "").lower()
    status_label = CWA_STATUS_LABELS.get(status, "")
    status_color = CWA_STATUS_COLORS.get(status, COLORS["secondary"])
    instrument = esc(case.get("cwa_instrument", ""))
    class_bits = []
    if readings_by_id is not None:
        class_bits.extend(
            _statute_pill_html(s) for s in _case_statutes(case, readings_by_id)
        )
    if type_label:
        class_bits.append(f'<span class="cwa-type-pill">{esc(type_label)}</span>')
    if status_label:
        class_bits.append(
            f'<span class="cwa-status-pill" style="background:{status_color}">'
            f'{esc(status_label)}</span>'
        )
    if instrument:
        class_bits.append(f'<span class="cwa-instrument">{instrument}</span>')
    class_row = (
        f'<div class="cwa-class-row">{"".join(class_bits)}</div>' if class_bits else ""
    )

    # Visible by default: only the head, classification pills, and the
    # takeaway (the precomputed "why this matters here" sentence) — mirrors
    # how the Part 4 conflict-site cards stay scannable at a glance. The full
    # narrative (violation, outcome, statute applicability + pathway, full
    # statute citation, sources) lives behind one <details> toggle so a page
    # of 87+ cards doesn't read as a wall of always-open text (2026-07-06).
    sections = []
    detail_sections = []
    if violation:
        detail_sections.append(
            '<div class="bill-section-label">Violation</div>'
            f'<p class="bill-sentiment">{violation}</p>'
        )
    if outcome:
        detail_sections.append(
            '<div class="bill-section-label">Outcome</div>'
            f'<p class="bill-sentiment">{outcome}</p>'
        )
    if takeaway:
        sections.append(
            '<div class="bill-section-label">Relevance to data centers</div>'
            f'<p class="cwa-takeaway">{takeaway}</p>'
        )
    hooks = ""
    if readings_by_id is not None:
        hooks = _case_hooks_html(case, readings_by_id)
    # For cases where the statute was NOT applied (or is only potential): how
    # each mapped statute could apply, with cross-links to the historic cases
    # that show the path. The hooks row (one link per authority) is folded
    # into this section — right under the header — so "how statutes could
    # apply" actually enumerates each one, instead of a single blended
    # sentence with no per-statute breakdown.
    pathway = case.get("cwa_pathway", "")
    if pathway:
        analog_html = ""
        analogs = case.get("analogous_cases", [])
        if analogs:
            analog_html = (
                '<div class="cwa-analogs">Historic examples in this record: '
                f'{_case_links_html(analogs, case_ids)}</div>'
            )
        detail_sections.append(
            '<div class="bill-section-label">How statutes could apply</div>'
            f'{hooks}'
            f'<div class="cwa-pathway">{esc(pathway)}{analog_html}</div>'
        )
    elif hooks:
        detail_sections.append(hooks)
    if cwa_section:
        detail_sections.append(f'<div class="cwa-section-line">{cwa_section}</div>')
    sources_block = _sources_html(sources)
    if sources_block:
        detail_sections.append(sources_block)

    if detail_sections:
        # Native <details> is ideal on the static page. Known limitation in
        # the Streamlit app: every widget interaction reruns the script and
        # re-renders this markdown, so an expanded card collapses back to
        # closed when the user touches a filter. Accepted trade-off — the
        # deployed artifact is the static site.
        sections.append(
            '<details class="bill-card-details">'
            '<summary>Details — violation, outcome, statute applicability &amp; sources</summary>'
            f'{"".join(detail_sections)}'
            '</details>'
        )

    body = "".join(sections)
    anchor = esc(case.get("case_id", ""))
    return (
        f'<div class="bill-card" id="cwa-{anchor}">'
        f'{head}{class_row}{body}</div>'
    )


# --- Company Water Claims ---

def render_issues_and_claims():
    """Issues & Claims tab — the problems, and what the operators say about them.

    Spec A3. Previously this was two disconnected halves: conflict sites as
    Part 4 of the legal-record tab, operator claims as a collapsed disclosure
    at the bottom of Legislation. A reader wanting "what is the problem here
    and what does the company say?" had to visit two tabs and join by hand.
    """
    st.subheader("Issues & Claims")

    conflicts_payload = load_dc_water_conflicts()
    sites = conflicts_payload.get("sites", [])
    authorities_payload = load_water_authorities()
    readings_by_id = _readings_by_id(authorities_payload)
    cases = load_cwa_investigations().get("cases", [])
    all_ids = {c.get("case_id") for c in cases}
    cases_by_id = {c["case_id"]: c for c in cases}
    claims_payload = load_company_water_claims()
    claims_ctx = (claims_payload.get("claims", []), claims_payload.get("companies", {}))

    if sites:
        st.markdown(_issue_type_summary_html(sites), unsafe_allow_html=True)
        st.markdown(f"#### Sites with reported water issues or pushback ({len(sites)})")
        st.markdown("##### Which doctrines are in play where")
        st.markdown(
            _build_site_doctrine_matrix_html(sites, readings_by_id),
            unsafe_allow_html=True,
        )
        st.markdown(
            "".join(
                _build_conflict_site_html(
                    s, readings_by_id, all_ids, cases_by_id, claims_ctx
                )
                for s in sites
            ),
            unsafe_allow_html=True,
        )
        conflicts_updated = conflicts_payload.get("last_updated")
        if conflicts_updated:
            st.caption(f"Site roster last updated {conflicts_updated}.")

    st.markdown("---")
    render_company_water_claims()


def render_company_water_claims():
    """Render the Company Water Claims panel — verbatim operator commitments."""
    st.subheader("Company Water Claims")

    payload = load_company_water_claims()
    claims = payload.get("claims", [])
    if not claims:
        st.info("Company water-claims dataset not found or empty.")
        return

    companies = payload.get("companies", {})
    delivered_count = sum(1 for c in claims if c.get("delivered"))
    company_count = len({c.get("company_slug") for c in claims})
    live_url = payload.get("live_dashboard", "")

    st.markdown(
        "Verbatim water-related commitments from data-center operators, "
        f"mirrored from [Data Center Community Benefits]({live_url}). "
        "Each quote links to its first-party source. Where independent assessment "
        "has been captured, a **delivered-vs-promised** badge appears beneath."
    )
    st.markdown(
        f"**{len(claims)} claims** · {company_count} companies · "
        f"{delivered_count} delivered-vs-promised assessments"
    )

    rendered_companies: list[str] = []
    for claim in claims:
        slug = claim.get("company_slug", "unknown")
        if slug not in rendered_companies:
            rendered_companies.append(slug)
            st.markdown(f"#### {companies.get(slug, slug)}")
        _render_water_claim_card(claim)

    st.caption(
        f"Snapshotted from {payload.get('source_repo', 'datacentercommunitybenefits')} "
        f"on {payload.get('last_updated', 'unknown')}. "
        "Quotes are verbatim — they reflect what each company has *claimed*, "
        "not independently verified water usage. See the Transparency Scorecard "
        "for what's actually measurable."
    )


def _build_claim_lifecycle_html(
    claim: dict, companies: dict | None = None, *, link_anchors: bool = True
) -> str:
    """Claim-type chip, court-challenge badge and site cross-links.

    Shared by the static site and the Streamlit card. This lived inline in
    build_site.py, so the Streamlit app rendered the pre-lifecycle card: no
    claim type, no "challenged in court" badge, no site links. Two surfaces
    disagreeing about the same record is precisely what the shared-builder rule
    in CLAUDE.md exists to prevent, and it had already drifted.

    ``link_anchors=False`` renders the same information without hyperlinks.
    Only the static site has the JS that activates a fragment's owning tab; in
    Streamlit an ``#cwa-…`` href just rewrites the hash and leaves the reader
    on Issues & Claims with nothing visibly happening — worse than plain text,
    because it looks clickable. The badge instead names where the record lives.
    """
    esc = html.escape
    chips = []
    ctype = claim.get("claim_type")
    if ctype in CLAIM_TYPE_LABELS:
        chips.append(
            f'<span class="claim-type-pill">{esc(CLAIM_TYPE_LABELS[ctype])}</span>'
        )
    for case_id in claim.get("challenged_in", []) or []:
        ref = resolve_ref(case_id)
        if not ref:
            continue
        if link_anchors:
            chips.append(
                f'<a class="claim-challenge-pill" href="#{esc(ref.anchor)}">'
                "&#9878; Challenged in court</a>"
            )
        else:
            chips.append(
                '<span class="claim-challenge-ref">&#9878; Challenged in court '
                f"&middot; see Water Cases: {esc(ref.label)}</span>"
            )
    for site_id in claim.get("related_site_ids", []) or []:
        ref = resolve_ref(site_id)
        if not ref:
            continue
        if link_anchors:
            chips.append(
                f'<a class="claim-site-link" href="#{esc(ref.anchor)}">'
                f"&rarr; {esc(ref.label)}</a>"
            )
        else:
            chips.append(
                f'<span class="claim-site-ref">&rarr; {esc(ref.label)}</span>'
            )
    return f'<div class="claim-chips">{"".join(chips)}</div>' if chips else ""


def _render_water_claim_card(claim: dict):
    """Render one claim as a bordered card with native Streamlit components.

    Uses st.container(border=True) for clear card boundaries, st.caption for
    the attribution line, and semantic st.success/warning/error boxes for the
    delivered-vs-promised assessment so status reads at a glance. Surfaces
    `project_id` when present so site-specific commitments aren't anonymous.
    """
    statement = claim.get("statement", "")
    source_url = claim.get("source_url", "")
    source_title = claim.get("source_title", "source")
    date_str = claim.get("published_at") or claim.get("captured_at") or ""
    project_id = claim.get("project_id")

    with st.container(border=True):
        # Verbatim quote — italic, curly quotes, no blockquote markup.
        st.markdown(f"*“{statement}”*")

        # Attribution: source · date · project (when applicable).
        caption_parts = []
        if source_url:
            caption_parts.append(f"[{source_title}]({source_url})")
        elif source_title:
            caption_parts.append(source_title)
        if date_str:
            caption_parts.append(str(date_str))
        if project_id:
            caption_parts.append(f"Project: `{project_id}`")
        if caption_parts:
            st.caption(" · ".join(caption_parts))

        # Streamlit has no cross-tab fragment handler; see the builder docstring.
        lifecycle = _build_claim_lifecycle_html(claim, link_anchors=False)
        if lifecycle:
            st.markdown(lifecycle, unsafe_allow_html=True)

        delivered = claim.get("delivered")
        if delivered:
            status = str(delivered.get("status", "")).lower()
            status_label = DELIVERED_STATUS_LABELS.get(
                status, status.title() or "Unknown"
            )
            d_summary = delivered.get("summary", "")
            d_url = delivered.get("source_url", "")
            d_title = delivered.get("source_title", "assessment")
            d_assessed = delivered.get("assessed_at", "")
            box_fn = {
                "delivered": st.success,
                "partial": st.warning,
                "contested": st.warning,
                "litigated": st.error,
                "shortfall": st.error,
            }.get(status, st.info)
            box_fn(
                f"**Delivered vs. promised: {status_label}** "
                f"_(assessed {d_assessed})_\n\n"
                f"{d_summary}\n\n"
                f"[Assessment: {d_title}]({d_url})"
            )


def render_data_freshness(df: pd.DataFrame):
    """Show when data was last updated."""
    if "scraped_at" not in df.columns or df["scraped_at"].isna().all():
        return

    latest = df["scraped_at"].max()
    if pd.isna(latest):
        return

    latest_str = latest.strftime("%B %d, %Y")
    total = len(df)
    flow_count = df["flow_mgd"].notna().sum()

    st.caption(
        f"Last updated: {latest_str} | "
        f"{total:,} records | {flow_count} with flow data"
    )


# --- Data Table ---


def render_data_table(df: pd.DataFrame, compact: bool = False):
    """Render data table — compact mode shows fewer columns."""
    if compact:
        display_cols = ["company_llc_name", "document_date", "flow_mgd", "permit_number"]
        height = 250
    else:
        display_cols = [
            "state",
            "company_llc_name",
            "document_date",
            "extracted_water_metric",
            "permit_number",
        ]
        height = 400

    available_cols = [c for c in display_cols if c in df.columns]
    display_df = df[available_cols].copy()

    if "document_date" in display_df.columns:
        display_df["document_date"] = display_df["document_date"].dt.strftime("%Y-%m-%d")

    # Replace NaN / None / empty / literal "None" with an em-dash so the table
    # doesn't show the string "None" in cells that simply don't have data.
    display_df = display_df.fillna("—")
    for col in display_df.columns:
        if display_df[col].dtype == object:
            display_df[col] = display_df[col].replace(
                {"None": "—", "nan": "—", "": "—"}
            )

    # Friendly column titles for EVERY visible column — the previous config
    # only renamed three of them, leaving snake_case headers like
    # `state` / `document_date` / `permit_number` next to "Facility" and
    # "Water Metric".
    column_titles = {
        "state": "State",
        "company_llc_name": "Facility",
        "document_date": "Document Date",
        "extracted_water_metric": "Water Metric",
        "flow_mgd": "Flow (MGD)",
        "permit_number": "Permit #",
    }
    column_config = {}
    for col in available_cols:
        title = column_titles.get(col, col.replace("_", " ").title())
        if col == "flow_mgd":
            column_config[col] = st.column_config.NumberColumn(title, format="%.1f")
        elif col == "extracted_water_metric":
            column_config[col] = st.column_config.TextColumn(title, width="medium")
        elif col == "company_llc_name":
            column_config[col] = st.column_config.TextColumn(title, width="large")
        elif col == "state":
            column_config[col] = st.column_config.TextColumn(title, width="small")
        elif col == "permit_number":
            column_config[col] = st.column_config.TextColumn(title, width="small")
        else:
            column_config[col] = st.column_config.TextColumn(title)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=height,
        column_config=column_config,
    )


# --- Sources tab ---

_STATUS_DOT = {
    "working":    "🟢",
    "partial":    "🟡",
    "blocked":    "🔴",
    "coming":     "🟣",
    "not_built":  "⚪",
    "policy_gap": "⚪",
}
_STATUS_LABEL = {
    "working":    "Working",
    "partial":    "Partial",
    "blocked":    "Blocked",
    "coming":     "Coming",
    "not_built":  "Not built",
    "policy_gap": "Policy gap",
}
_STATUS_BADGE = {
    "working":    ("color:#2e8b57;background:#f0fdf4;border:1px solid #86efac", "Working"),
    "partial":    ("color:#b45309;background:#fffbeb;border:1px solid #fde68a", "Partial"),
    "blocked":    ("color:#c41e3a;background:#fff1f2;border:1px solid #fecaca", "Blocked"),
    "coming":     ("color:#7c3aed;background:#f5f3ff;border:1px solid #ddd6fe", "Coming"),
    "not_built":  ("color:#6b7280;background:#f9fafb;border:1px solid #e5e7eb", "Not built"),
    "policy_gap": ("color:#6b7280;background:#f9fafb;border:1px solid #e5e7eb", "Policy gap"),
}
_BARRIER_COLORS = {
    "structural": ("#c41e3a", "#fff1f2"),
    "legal":      ("#b45309", "#fffbeb"),
    "policy":     ("#3182bd", "#eff3ff"),
}


def render_sources_tab():
    st.subheader("Data Access & Coverage")
    st.markdown(
        "Where this tracker gets its data, what's blocked, and what's coming. "
        "Every entry traces back to a public portal or regulatory dataset."
    )

    sc = SOURCES_DATA["scorecard"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Sources accessible", sc["accessible"], help="Active data pipelines returning records")
    col2.metric("Hard-blocked", sc["blocked"], help="NDA · WAF · voluntary-only · no mandate")
    col3.metric("Unlocking soon", sc["coming"], help="HB 496 · OHD000001 · EIA 923")
    col4.metric("Build queue", sc["build_queue"], help="Data available, scraper not yet built")

    st.divider()
    st.markdown('<h3 class="solution-cat-header">Source status by level</h3>', unsafe_allow_html=True)

    # Build source table as one HTML block so badge styling is consistent with
    # the rest of the app (pills, not backtick code marks).
    rows = []
    current_level = None
    for src in SOURCES_DATA["sources"]:
        lvl = src["level"]
        if lvl != current_level:
            current_level = lvl
            rows.append(
                f'<div style="font-weight:700;color:#08519c;font-size:.83rem;'
                f'text-transform:uppercase;letter-spacing:.06em;'
                f'padding:.55rem 0 .15rem;margin-top:.6rem;'
                f'border-bottom:1px solid #e5e7eb;">{html.escape(lvl)}</div>'
            )
        badge_style, badge_label = _STATUS_BADGE.get(
            src["status"], ("color:#555;background:#f9fafb;border:1px solid #e5e7eb", src["status"])
        )
        dot = _STATUS_DOT.get(src["status"], "⚪")
        rows.append(
            f'<div style="display:flex;align-items:baseline;gap:.75rem;'
            f'padding:.45rem 0;border-bottom:1px solid #f1f5f9;">'
            f'<span style="font-size:.85rem;flex:0 0 1.1rem;">{dot}</span>'
            f'<div style="flex:1;min-width:0;">'
            f'<span style="font-weight:600;color:#1a1a2e;font-size:.9rem;">{html.escape(src["name"])}</span>'
            f'<span style="color:#6b7280;font-size:.82rem;margin-left:.4rem;">{html.escape(src["note"])}</span>'
            f'</div>'
            f'<span style="{badge_style};border-radius:999px;padding:.12rem .55rem;'
            f'font-size:.75rem;font-weight:700;white-space:nowrap;">{badge_label}</span>'
            f'<span style="color:#6b7280;font-size:.78rem;flex:0 0 8rem;'
            f'text-align:right;">{html.escape(src["action"])}</span>'
            f'</div>'
        )
    st.markdown("".join(rows), unsafe_allow_html=True)

    st.divider()
    st.markdown(
        '<h3 class="solution-cat-header">Structural barriers scraping alone can\'t fix</h3>',
        unsafe_allow_html=True,
    )

    b_cols = st.columns(3)
    for col, barrier in zip(b_cols, SOURCES_DATA["barriers"]):
        color, bg = _BARRIER_COLORS.get(barrier["kind"], ("#555", "#f5f5f5"))
        with col:
            st.markdown(
                f'<div style="border-left:3px solid {color};background:{bg};'
                f'padding:.65rem .9rem;border-radius:0 .4rem .4rem 0;margin-bottom:.4rem;">'
                f'<strong style="color:#1a1a2e;">{html.escape(barrier["title"])}</strong>'
                f'<p style="margin:.35rem 0;font-size:.88rem;color:#1a1a2e;">{html.escape(barrier["body"])}</p>'
                f'<p style="margin:0;font-size:.82rem;color:#555;font-style:italic;">'
                f'Workaround: {html.escape(barrier["workaround"])}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.divider()
    st.markdown('<h3 class="solution-cat-header">Upcoming data unlocks</h3>', unsafe_allow_html=True)

    timeline_html = []
    for item in SOURCES_DATA["timeline"]:
        date_color = "#7c3aed" if item["color"] == "purple" else "#2e8b57"
        timeline_html.append(
            f'<div class="timeline-event">'
            f'<div class="timeline-date" style="min-width:7rem;color:{date_color};">'
            f'{html.escape(item["date"])}</div>'
            f'<div class="timeline-body">'
            f'<strong>{html.escape(item["title"])}</strong>'
            f'<div class="timeline-detail">{html.escape(item["desc"])}</div>'
            f'</div></div>'
        )
    st.markdown("".join(timeline_html), unsafe_allow_html=True)

    df = load_data()
    if not df.empty:
        st.divider()
        st.download_button(
            "Download raw records (CSV)",
            df.to_csv(index=False),
            "dc_water_data.csv",
            "text/csv",
        )
    st.caption("Reference dataset — updated as new sources come online.")


# --- Explore tab (connection graph + text similarity) ---
#
# One builder, two surfaces: build_site.py drops the fragment straight into the
# Explore tabpanel, and render_explore() hands the same string to
# st.components.v1.html. That is why the fragment carries its own <style> and
# <script> — inside the Streamlit iframe there is no page stylesheet to inherit
# and no parent JS to rely on.

EXPLORE_LEAD = (
    "Every curated record in one graph, plus a text search across all of them. "
    "Click a dot to see what a record connects to, or paste a paragraph — a news "
    "story, a permit notice, a draft ordinance — to find the records that use the "
    "same language."
)

EXPLORE_EMPTY_STATE = (
    "Nothing searched yet. Paste a paragraph above to find the records that use "
    "the same language, click any dot to see what a record connects to, or "
    "combine the two by narrowing results to a record kind, a statute family, or "
    "the neighbourhood around the record you clicked."
)


def _explore_css() -> str:
    """Scoped styles for the Explore fragment.

    Everything is under ``.explore`` because this string is injected into two
    very different documents: the static page (where it must not touch the
    card CSS) and a bare Streamlit iframe (where nothing else is defined, so
    even the body font has to be stated here).
    """
    return """
.explore{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  color:#1a1a2e;line-height:1.5;font-size:.92rem}
.explore-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.1fr);gap:1rem;align-items:start}
@media (max-width:900px){.explore-grid{grid-template-columns:minmax(0,1fr)}}
.explore-side,.explore-main{min-width:0}
.explore-label{display:block;font-weight:600;font-size:.88rem;margin:0 0 .3rem}
.explore textarea{width:100%;font:inherit;font-size:.88rem;padding:.55rem .7rem;border:1px solid #cbd5e1;
  border-radius:.4rem;background:#fff;resize:vertical}
.explore select{font:inherit;font-size:.84rem;padding:.25rem .4rem;border:1px solid #bdd7e7;
  border-radius:.4rem;background:#fff;color:#1a1a2e}
.explore-controls{display:flex;flex-wrap:wrap;gap:.4rem .7rem;align-items:center;margin:.6rem 0}
.explore-controls-label{font-weight:600;font-size:.84rem}
.explore-chip{display:inline-flex;align-items:center;gap:.35rem;font-size:.82rem;background:#eff3ff;
  border:1px solid #bdd7e7;border-radius:999px;padding:.2rem .6rem;cursor:pointer}
.explore-chip input{accent-color:#08519c;margin:0}
.explore-btn{appearance:none;font:inherit;font-size:.8rem;font-weight:600;color:#08519c;background:#eff3ff;
  border:1px solid #bdd7e7;border-radius:.35rem;padding:.25rem .55rem;cursor:pointer;min-height:32px}
.explore-btn:hover{background:#dfeafb}
.explore-count{font-size:.84rem;color:#4b5563;margin:.5rem 0 .4rem}
.explore-results{max-height:26rem;overflow-y:auto;padding-right:.2rem}
.explore-empty{border:1px solid #cbd5e1;border-radius:.5rem;background:#fff;padding:.75rem .9rem;
  font-size:.86rem;color:#333}
.explore-result{border:1px solid #e2e8f0;border-radius:.5rem;background:#fff;padding:.55rem .7rem;margin:0 0 .45rem;
  box-shadow:0 1px 2px rgba(15,23,42,.04)}
.explore-result-head{display:flex;align-items:baseline;gap:.4rem;flex-wrap:wrap}
.explore-dot{width:.6rem;height:.6rem;border-radius:50%;display:inline-block;flex:none}
.explore-result a{color:#08519c;font-weight:600;text-decoration:none;font-size:.88rem}
.explore-result a:hover{text-decoration:underline}
.explore-kindtag{font-size:.72rem;font-weight:600;color:#4b5563;border:1px solid #e2e8f0;
  border-radius:999px;padding:.02rem .45rem;background:#f8fafc}
.explore-bar{height:.35rem;border-radius:999px;background:#eff3ff;margin:.35rem 0 .3rem;overflow:hidden}
.explore-bar span{display:block;height:100%;background:#3182bd}
.explore-terms{font-size:.76rem;color:#4b5563}
.explore-term{background:#eff3ff;border:1px solid #bdd7e7;border-radius:999px;padding:.02rem .4rem;margin-right:.25rem}
.explore-toolbar{display:flex;flex-wrap:wrap;gap:.4rem .6rem;align-items:center;justify-content:space-between;
  margin:0 0 .4rem}
.explore-focus{font-size:.84rem;color:#1a1a2e;min-width:0}
.explore-focus a{color:#08519c}
.explore-tools{display:flex;gap:.35rem;align-items:center;font-size:.8rem;color:#4b5563}
.explore-canvas{width:100%;height:520px;display:block;background:#fff;border:1px solid #cbd5e1;
  border-radius:.5rem;touch-action:none;cursor:grab}
.explore-canvas:active{cursor:grabbing}
@media (max-width:900px){.explore-canvas{height:380px}}
.explore-hint{font-size:.76rem;color:#6b7280;margin:.3rem 0 .5rem}
.explore-legend{display:flex;flex-wrap:wrap;gap:.3rem .7rem;font-size:.76rem;color:#4b5563;margin-bottom:.5rem}
.explore-legend span.explore-dot{margin-right:.25rem}
.explore-edges{border:1px solid #cbd5e1;border-radius:.5rem;background:#fff}
.explore-edges>summary{cursor:pointer;font-weight:600;color:#08519c;padding:.5rem .7rem;font-size:.85rem;
  list-style:none;min-height:36px;display:flex;align-items:center}
.explore-edges>summary::-webkit-details-marker{display:none}
.explore-edges>summary::before{content:"\\25B8";margin-right:.4rem}
.explore-edges[open]>summary::before{content:"\\25BE"}
.explore-edgelist{display:flex;flex-wrap:wrap;gap:.3rem .5rem;padding:0 .7rem .7rem}
.explore-noscript{border-left:3px solid #b45309;background:#fffbeb;padding:.65rem .9rem;
  border-radius:0 .4rem .4rem 0;margin-bottom:.8rem}
.explore-noscript ul{margin:.4rem 0 0;padding-left:1.1rem;font-size:.86rem}
"""


def _explore_noscript_html(counts: dict[str, int]) -> str:
    """What a reader without JavaScript gets: the honest version.

    The graph and the cosine search are both client-side computation, so there
    is no degraded rendering of them to offer — saying so and pointing at the
    tabs that hold the same records is more useful than an empty canvas.
    """
    rows = "".join(
        f'<li><a href="#panel-{html.escape(KIND_TABS[kind])}">'
        f"{html.escape(EXPLORE_KIND_LABELS[kind])}</a> — {count} records</li>"
        for kind, count in counts.items()
    )
    return (
        '<noscript><div class="explore-noscript">'
        "<p><strong>The graph and the text search need JavaScript.</strong> Both run "
        "entirely in your browser — there is no server to fall back on — so with "
        "scripting off this tab can only point you at the records themselves, which "
        "are all on the page already:</p>"
        f"<ul>{rows}</ul></div></noscript>"
    )


# Plural, reader-facing names for the record kinds. graph.KIND_LABELS holds the
# singular form, which is what a single result chip needs ("Water case"); the
# kind filter, the legend and the noscript list all label *groups*, so they read
# as plurals ("Water cases (109)").
EXPLORE_KIND_LABELS = {
    "instrument": "Policy instruments",
    "reading": "Statutory readings",
    "case": "Water cases",
    "site": "Conflict sites",
    "claim": "Operator claims",
    "news": "News items",
    "solution": "Solutions",
}


def _build_explore_html() -> str:
    """The whole Explore surface as one self-contained HTML fragment.

    Returns markup + the graph/index blob + scoped CSS + the vanilla-JS
    force layout and search. Pure: no Streamlit, no I/O beyond the cached
    loaders, so ``build_site.py`` and the tests can call it directly.
    """
    payload = graph_payload_json()
    nodes = build_graph()["nodes"]

    counts: dict[str, int] = {}
    for node in nodes:
        if node["kind"] != "hub":
            counts[node["kind"]] = counts.get(node["kind"], 0) + 1
    ordered_counts = {k: counts[k] for k in EXPLORE_KIND_LABELS if k in counts}

    kind_boxes = "".join(
        f'<label class="explore-chip"><input type="checkbox" class="explore-kind" '
        f'value="{k}" checked> {html.escape(EXPLORE_KIND_LABELS[k])} ({n})</label>'
        for k, n in ordered_counts.items()
    )

    statutes = load_water_authorities().get("statutes", {})
    family_options = "".join(
        f'<option value="{html.escape(code)}">{html.escape(code)} — '
        f'{html.escape(statutes.get(code, {}).get("name", code))}</option>'
        for code in WATER_STATUTE_ORDER
        if code in statutes
    )

    legend = "".join(
        f'<span><span class="explore-dot" style="background:{GRAPH_KIND_COLORS[k]}"></span>'
        f"{html.escape(EXPLORE_KIND_LABELS[k])}</span>"
        for k in ordered_counts
    )
    legend += (
        '<span><span class="explore-dot" style="background:'
        f'{GRAPH_KIND_COLORS["hub"]};border-radius:2px"></span>'
        "Taxonomy hub (statute, project type, principle)</span>"
    )

    return f"""<div class="explore" id="explore">
{_explore_noscript_html(ordered_counts)}
<div class="explore-grid">
  <div class="explore-side">
    <label class="explore-label" for="explore-q">Paste any text — a news story, a
    permit notice, a bill summary</label>
    <textarea id="explore-q" rows="5" placeholder="Paste a paragraph here to rank every tracked record by how much of its language it shares."></textarea>
    <div class="explore-controls">
      <span class="explore-controls-label">Kinds:</span>{kind_boxes}
    </div>
    <div class="explore-controls">
      <label class="explore-controls-label" for="explore-family">Statute family:</label>
      <select id="explore-family">
        <option value="">Any</option>{family_options}
      </select>
      <label class="explore-chip"><input type="checkbox" id="explore-scope">
      Only near the focused record</label>
    </div>
    <p class="explore-count" id="explore-count"></p>
    <div class="explore-results" id="explore-results">
      <div class="explore-empty">{html.escape(EXPLORE_EMPTY_STATE)}</div>
    </div>
  </div>
  <div class="explore-main">
    <div class="explore-toolbar">
      <span class="explore-focus" id="explore-focus">No record focused — click a dot,
      or use <em>Show connections</em> on a result.</span>
      <span class="explore-tools">
        <label for="explore-depth">Hops</label>
        <select id="explore-depth">
          <option value="1">1</option>
          <option value="2" selected>2</option>
        </select>
        <button type="button" class="explore-btn" id="explore-zoom-in" aria-label="Zoom in">+</button>
        <button type="button" class="explore-btn" id="explore-zoom-out" aria-label="Zoom out">&minus;</button>
        <button type="button" class="explore-btn" id="explore-reset">Reset</button>
      </span>
    </div>
    <canvas class="explore-canvas" id="explore-canvas" role="img" aria-label="Connection graph of every tracked record. The results list carries the same records as text."></canvas>
    <p class="explore-hint">Drag to pan, scroll to zoom, click a dot to focus its
    neighbourhood. Lines are connections the datasets declare.</p>
    <div class="explore-legend">{legend}</div>
    <details class="explore-edges">
      <summary>Connection types</summary>
      <div class="explore-edgelist" id="explore-edgelist"></div>
    </details>
  </div>
</div>
<script type="application/json" id="graph-data">{payload}</script>
<style>{_explore_css()}</style>
<script>{_explore_js()}</script>
</div>"""


def _explore_js() -> str:
    """The client half: tokenizer, cosine search, force layout, canvas renderer.

    The tokenizer here is the only piece that MUST agree with Python. It reads
    its stopword list and minimum token length out of the embedded blob rather
    than restating them, so the two cannot drift; a build test round-trips a
    fixture string through both to prove the surrounding regex rules match too.
    """
    return r"""
(function(){
  var root = document.getElementById('explore');
  var blob = root && root.querySelector('#graph-data');
  var canvas = root && root.querySelector('#explore-canvas');
  if (!root || !blob || !canvas) return;
  var D = JSON.parse(blob.textContent);

  // --- Tokenizer: mirrors refdata.graph.tokenize, constants from the blob ---
  var STOP = {}, i;
  for (i = 0; i < D.stopwords.length; i++) STOP[D.stopwords[i]] = 1;
  function tokenize(text){
    var raw = String(text == null ? '' : text)
      .replace(/[^A-Za-z0-9]+/g, ' ').toLowerCase().split(' ');
    var words = [];
    for (var j = 0; j < raw.length; j++){
      if (raw[j].length >= D.min_token_len && !STOP[raw[j]]) words.push(raw[j]);
    }
    var out = words.slice();
    for (var k = 0; k + 1 < words.length; k++) out.push(words[k] + ' ' + words[k + 1]);
    return out;
  }

  // --- Index lookup tables ---
  var vocabPos = {};
  for (i = 0; i < D.vocab.length; i++) vocabPos[D.vocab[i]] = i;
  var idf = D.df.map(function(d){ return Math.log(D.n_docs / d); });
  var docs = [];
  for (var key in D.docs){
    if (!Object.prototype.hasOwnProperty.call(D.docs, key)) continue;
    docs.push({node: parseInt(key, 10), t: D.docs[key].t, w: D.docs[key].w});
  }

  var nodes = D.nodes;
  var derived = {};
  for (i = 0; i < D.derived_edge_kinds.length; i++) derived[D.derived_edge_kinds[i]] = 1;
  // Curated cross-references are on by default; taxonomy membership is a
  // different claim about the data and the reader opts into it.
  var activeKinds = D.edge_kinds.map(function(k){ return !derived[k]; });

  // --- Adjacency, rebuilt whenever the edge-kind toggles change ---
  var adj = [];
  function rebuildAdjacency(){
    adj = nodes.map(function(){ return []; });
    for (var e = 0; e < D.edges.length; e++){
      var edge = D.edges[e];
      if (!activeKinds[edge[2]]) continue;
      // Walked undirected: "what connects to this" does not care which record
      // wrote the id down.
      adj[edge[0]].push(edge[1]);
      adj[edge[1]].push(edge[0]);
    }
  }

  function neighbourhood(start, depth){
    var seen = {}, frontier = [start], d;
    seen[start] = 0;
    for (d = 1; d <= depth; d++){
      var next = [];
      for (var f = 0; f < frontier.length; f++){
        var list = adj[frontier[f]];
        for (var n = 0; n < list.length; n++){
          if (seen[list[n]] === undefined){ seen[list[n]] = d; next.push(list[n]); }
        }
      }
      frontier = next;
    }
    return seen;
  }

  // --- Force-directed layout (Fruchterman-Reingold, no library) ---
  var W = 900, H = 700;
  var pos = nodes.map(function(_, idx){
    // Deterministic ring start: same input data always settles the same way,
    // so a rebuild does not reshuffle the picture for no reason.
    var a = idx * 2.399963229728653;  // golden angle
    var r = 40 + 300 * Math.sqrt(idx / nodes.length);
    return {x: W / 2 + r * Math.cos(a), y: H / 2 + r * Math.sin(a), dx: 0, dy: 0};
  });
  var reduceMotion = window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function step(temperature){
    var k = Math.sqrt((W * H) / nodes.length);
    var a, b, dx, dy, dist, force;
    for (a = 0; a < nodes.length; a++){ pos[a].dx = 0; pos[a].dy = 0; }
    for (a = 0; a < nodes.length; a++){
      for (b = a + 1; b < nodes.length; b++){
        dx = pos[a].x - pos[b].x; dy = pos[a].y - pos[b].y;
        dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
        force = (k * k) / dist;
        dx = (dx / dist) * force; dy = (dy / dist) * force;
        pos[a].dx += dx; pos[a].dy += dy;
        pos[b].dx -= dx; pos[b].dy -= dy;
      }
    }
    for (var e = 0; e < D.edges.length; e++){
      if (!activeKinds[D.edges[e][2]]) continue;
      a = D.edges[e][0]; b = D.edges[e][1];
      dx = pos[a].x - pos[b].x; dy = pos[a].y - pos[b].y;
      dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
      force = (dist * dist) / k;
      dx = (dx / dist) * force; dy = (dy / dist) * force;
      pos[a].dx -= dx; pos[a].dy -= dy;
      pos[b].dx += dx; pos[b].dy += dy;
    }
    for (a = 0; a < nodes.length; a++){
      // Gravity keeps disconnected records from drifting off the canvas.
      pos[a].dx += (W / 2 - pos[a].x) * 0.012;
      pos[a].dy += (H / 2 - pos[a].y) * 0.012;
      var mag = Math.sqrt(pos[a].dx * pos[a].dx + pos[a].dy * pos[a].dy) || 0.01;
      var move = Math.min(mag, temperature);
      pos[a].x += (pos[a].dx / mag) * move;
      pos[a].y += (pos[a].dy / mag) * move;
    }
  }

  var ITERATIONS = 120;
  function runLayout(){
    var t = 0, temp0 = W / 12;
    if (reduceMotion){
      for (t = 0; t < ITERATIONS; t++) step(temp0 * (1 - t / ITERATIONS));
      draw();
      return;
    }
    // Animated: chunks per frame so a slow phone stays responsive instead of
    // freezing for the whole simulation.
    (function frame(){
      for (var c = 0; c < 6 && t < ITERATIONS; c++, t++) step(temp0 * (1 - t / ITERATIONS));
      draw();
      if (t < ITERATIONS) requestAnimationFrame(frame);
    })();
  }

  // --- Canvas ---
  var ctx = canvas.getContext('2d');
  var view = {scale: 0.62, ox: 0, oy: 0};
  var focused = -1, near = null;

  function sizeCanvas(){
    var ratio = window.devicePixelRatio || 1;
    // clientWidth is 0 when the page is opened over file:// — fall back so the
    // canvas is still drawn rather than collapsing to nothing.
    var cw = canvas.clientWidth || 640;
    var ch = canvas.clientHeight || 520;
    canvas.width = cw * ratio;
    canvas.height = ch * ratio;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  }

  function toScreen(p){
    var cw = canvas.clientWidth || 640, ch = canvas.clientHeight || 520;
    return {
      x: (p.x - W / 2) * view.scale + cw / 2 + view.ox,
      y: (p.y - H / 2) * view.scale + ch / 2 + view.oy
    };
  }

  function nodeRadius(idx){
    return nodes[idx].kind === 'hub' ? 4.5 : 3.6;
  }

  function draw(){
    var cw = canvas.clientWidth || 640, ch = canvas.clientHeight || 520;
    ctx.clearRect(0, 0, cw, ch);
    var dim = focused >= 0;
    var e, a, b, pa, pb;
    for (e = 0; e < D.edges.length; e++){
      if (!activeKinds[D.edges[e][2]]) continue;
      a = D.edges[e][0]; b = D.edges[e][1];
      var lit = !dim || (near[a] !== undefined && near[b] !== undefined);
      ctx.strokeStyle = lit ? 'rgba(49,130,189,0.45)' : 'rgba(148,163,184,0.10)';
      ctx.lineWidth = lit ? 1 : 0.6;
      pa = toScreen(pos[a]); pb = toScreen(pos[b]);
      ctx.beginPath(); ctx.moveTo(pa.x, pa.y); ctx.lineTo(pb.x, pb.y); ctx.stroke();
    }
    var labelled = [];
    for (a = 0; a < nodes.length; a++){
      var p = toScreen(pos[a]);
      var inFocus = !dim || near[a] !== undefined;
      ctx.globalAlpha = inFocus ? 1 : 0.18;
      ctx.fillStyle = D.kind_colors[nodes[a].kind] || '#6b7280';
      var r = nodeRadius(a) * (a === focused ? 2 : 1);
      if (nodes[a].kind === 'hub'){
        ctx.fillRect(p.x - r, p.y - r, r * 2, r * 2);
      } else {
        ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, Math.PI * 2); ctx.fill();
      }
      if (a === focused){
        ctx.strokeStyle = '#1a1a2e'; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(p.x, p.y, r + 3, 0, Math.PI * 2); ctx.stroke();
      }
      // Labelling all 362 nodes is unreadable; label the focused neighbourhood
      // only, and cap it so a hub with 100 members does not turn to mud.
      if (dim && near[a] !== undefined && labelled.length < 26) labelled.push([a, p]);
      ctx.globalAlpha = 1;
    }
    ctx.font = '11px -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif';
    ctx.fillStyle = '#1a1a2e';
    for (var m = 0; m < labelled.length; m++){
      var text = nodes[labelled[m][0]].label;
      if (text.length > 34) text = text.slice(0, 33) + '…';
      ctx.fillText(text, labelled[m][1].x + 7, labelled[m][1].y + 3);
    }
  }

  // --- Pan / zoom ---
  var dragging = false, dragged = false, lastX = 0, lastY = 0;
  function pointerDown(x, y){ dragging = true; dragged = false; lastX = x; lastY = y; }
  function pointerMove(x, y){
    if (!dragging) return;
    if (Math.abs(x - lastX) + Math.abs(y - lastY) > 3) dragged = true;
    view.ox += x - lastX; view.oy += y - lastY;
    lastX = x; lastY = y;
    draw();
  }
  function zoom(factor){
    view.scale = Math.min(4, Math.max(0.2, view.scale * factor));
    draw();
  }
  canvas.addEventListener('mousedown', function(e){ pointerDown(e.clientX, e.clientY); });
  window.addEventListener('mousemove', function(e){ pointerMove(e.clientX, e.clientY); });
  window.addEventListener('mouseup', function(){ dragging = false; });
  canvas.addEventListener('touchstart', function(e){
    if (e.touches.length === 1) pointerDown(e.touches[0].clientX, e.touches[0].clientY);
  }, {passive: true});
  canvas.addEventListener('touchmove', function(e){
    if (e.touches.length === 1){
      e.preventDefault();
      pointerMove(e.touches[0].clientX, e.touches[0].clientY);
    }
  }, {passive: false});
  canvas.addEventListener('touchend', function(){ dragging = false; });
  canvas.addEventListener('wheel', function(e){
    e.preventDefault();
    zoom(e.deltaY < 0 ? 1.12 : 1 / 1.12);
  }, {passive: false});

  // --- Focus ---
  function setFocus(idx){
    focused = idx;
    var box = root.querySelector('#explore-focus');
    if (idx < 0){
      near = null;
      box.textContent = 'No record focused — click a dot, or use Show connections on a result.';
    } else {
      var depth = parseInt(root.querySelector('#explore-depth').value, 10) || 1;
      near = neighbourhood(idx, depth);
      var count = 0;
      for (var key2 in near){ if (near[key2] > 0) count++; }
      var node = nodes[idx];
      box.replaceChildren();
      var strong = document.createElement('strong');
      strong.textContent = node.label;
      box.appendChild(strong);
      box.appendChild(document.createTextNode(
        ' · ' + (D.kind_labels[node.kind] || node.kind) +
        ' · ' + count + ' connected within ' + depth + (depth === 1 ? ' hop' : ' hops')));
      if (node.anchor){
        box.appendChild(document.createTextNode(' · '));
        var link = document.createElement('a');
        link.href = '#' + node.anchor;
        link.textContent = 'open card';
        box.appendChild(link);
      }
    }
    draw();
    runSearch();
  }

  canvas.addEventListener('click', function(ev){
    if (dragged) return;
    var rect = canvas.getBoundingClientRect();
    var mx = ev.clientX - rect.left, my = ev.clientY - rect.top;
    var best = -1, bestDist = 12 * 12;
    for (var a = 0; a < nodes.length; a++){
      var p = toScreen(pos[a]);
      var d2 = (p.x - mx) * (p.x - mx) + (p.y - my) * (p.y - my);
      if (d2 < bestDist){ bestDist = d2; best = a; }
    }
    setFocus(best);
  });

  root.querySelector('#explore-zoom-in').addEventListener('click', function(){ zoom(1.2); });
  root.querySelector('#explore-zoom-out').addEventListener('click', function(){ zoom(1 / 1.2); });
  root.querySelector('#explore-reset').addEventListener('click', function(){
    view = {scale: 0.62, ox: 0, oy: 0};
    setFocus(-1);
  });
  root.querySelector('#explore-depth').addEventListener('change', function(){
    if (focused >= 0) setFocus(focused);
  });

  // --- Edge-kind toggles ---
  var edgeList = root.querySelector('#explore-edgelist');
  D.edge_kinds.forEach(function(kind, idx){
    var label = document.createElement('label');
    label.className = 'explore-chip';
    var box2 = document.createElement('input');
    box2.type = 'checkbox';
    box2.checked = activeKinds[idx];
    box2.addEventListener('change', function(){
      activeKinds[idx] = box2.checked;
      rebuildAdjacency();
      runLayout();
      if (focused >= 0) setFocus(focused); else draw();
    });
    label.appendChild(box2);
    label.appendChild(document.createTextNode(
      ' ' + D.edge_kind_labels[idx] + (derived[kind] ? ' (derived)' : '')));
    edgeList.appendChild(label);
  });

  // --- Search ---
  var qBox = root.querySelector('#explore-q');
  var resultsBox = root.querySelector('#explore-results');
  var countLine = root.querySelector('#explore-count');
  var familySel = root.querySelector('#explore-family');
  var scopeBox = root.querySelector('#explore-scope');
  var kindBoxes = [].slice.call(root.querySelectorAll('.explore-kind'));
  var TOP_N = 12;
  var emptyCopy = resultsBox.textContent.trim();

  function passesFilters(nodeIdx){
    var node = nodes[nodeIdx];
    var kinds = {};
    kindBoxes.forEach(function(c){ if (c.checked) kinds[c.value] = 1; });
    if (!kinds[node.kind]) return false;
    var family = familySel.value;
    if (family){
      var list = (node.attrs && node.attrs.statutes) || [];
      if (list.indexOf(family) < 0) return false;
    }
    if (scopeBox.checked && focused >= 0 && (!near || near[nodeIdx] === undefined)) return false;
    return true;
  }

  function runSearch(){
    var text = qBox.value;
    var counts = {}, any = false;
    tokenize(text).forEach(function(tok){
      var p = vocabPos[tok];
      if (p === undefined) return;
      counts[p] = (counts[p] || 0) + 1;
      any = true;
    });
    if (!any){
      countLine.textContent = '';
      resultsBox.replaceChildren(emptyState(text));
      return;
    }
    var qw = {}, norm = 0;
    for (var p in counts){
      var w = counts[p] * idf[p];
      qw[p] = w; norm += w * w;
    }
    norm = Math.sqrt(norm) || 1;
    var scored = [];
    for (var d = 0; d < docs.length; d++){
      var doc = docs[d];
      if (!passesFilters(doc.node)) continue;
      var total = 0, hits = [];
      for (var j = 0; j < doc.t.length; j++){
        var q = qw[doc.t[j]];
        if (q === undefined) continue;
        var part = (q / norm) * (doc.w[j] / D.weight_scale);
        total += part;
        hits.push([part, D.vocab[doc.t[j]]]);
      }
      if (total > 0){
        hits.sort(function(x, y){ return y[0] - x[0]; });
        scored.push({node: doc.node, score: total, terms: hits.slice(0, 3)});
      }
    }
    scored.sort(function(x, y){ return y.score - x.score; });
    render(scored.slice(0, TOP_N), scored.length);
  }

  function emptyState(text){
    var div = document.createElement('div');
    div.className = 'explore-empty';
    div.textContent = text && text.trim()
      ? 'No tracked record shares any term with that text. Try a longer passage, or ' +
        'widen the kind and statute-family filters.'
      : emptyCopy;
    return div;
  }

  function render(rows, totalMatched){
    if (!rows.length){
      countLine.textContent = '';
      resultsBox.replaceChildren(emptyState(qBox.value));
      return;
    }
    countLine.textContent = 'Showing the closest ' + rows.length + ' of ' +
      totalMatched + ' records that share language with this text.';
    var top = rows[0].score || 1;
    var frag = document.createDocumentFragment();
    rows.forEach(function(row){
      var node = nodes[row.node];
      var card = document.createElement('div');
      card.className = 'explore-result';

      var head = document.createElement('div');
      head.className = 'explore-result-head';
      var dot = document.createElement('span');
      dot.className = 'explore-dot';
      dot.style.background = D.kind_colors[node.kind] || '#6b7280';
      head.appendChild(dot);
      if (node.anchor){
        var a = document.createElement('a');
        a.href = '#' + node.anchor;
        a.textContent = node.label;
        head.appendChild(a);
      } else {
        var strong2 = document.createElement('strong');
        strong2.textContent = node.label;
        head.appendChild(strong2);
      }
      var tag = document.createElement('span');
      tag.className = 'explore-kindtag';
      tag.textContent = D.kind_labels[node.kind] || node.kind;
      head.appendChild(tag);
      card.appendChild(head);

      var bar = document.createElement('div');
      bar.className = 'explore-bar';
      var fill = document.createElement('span');
      fill.style.width = Math.max(3, Math.round((row.score / top) * 100)) + '%';
      bar.appendChild(fill);
      card.appendChild(bar);

      var terms = document.createElement('div');
      terms.className = 'explore-terms';
      terms.appendChild(document.createTextNode('matched '));
      row.terms.forEach(function(t){
        var chip = document.createElement('span');
        chip.className = 'explore-term';
        chip.textContent = t[1];
        terms.appendChild(chip);
      });
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'explore-btn';
      btn.textContent = 'Show connections';
      btn.addEventListener('click', function(){ setFocus(row.node); });
      terms.appendChild(btn);
      card.appendChild(terms);
      frag.appendChild(card);
    });
    resultsBox.replaceChildren(frag);
  }

  var debounce;
  qBox.addEventListener('input', function(){
    clearTimeout(debounce);
    debounce = setTimeout(runSearch, 180);
  });
  kindBoxes.forEach(function(c){ c.addEventListener('change', runSearch); });
  familySel.addEventListener('change', runSearch);
  scopeBox.addEventListener('change', runSearch);

  // --- Boot ---
  var started = false;
  function start(){
    if (started) return;
    started = true;
    sizeCanvas();
    rebuildAdjacency();
    runLayout();
  }
  window.addEventListener('resize', function(){
    if (!started) return;
    sizeCanvas();
    draw();
  });
  // On the static site the panel is hidden until its tab is clicked, and a
  // hidden canvas measures 0 — so defer the simulation until it is visible
  // rather than burning ~7M force computations on every page load.
  var panel = root.closest ? root.closest('.tabpanel') : null;
  if (!panel || !panel.hidden){
    start();
  } else {
    var tabBtn = document.querySelector('.tab[data-tab="' + panel.id.replace('panel-', '') + '"]');
    if (tabBtn) tabBtn.addEventListener('click', function(){ setTimeout(start, 0); });
  }
})();
"""


def render_explore():
    """Streamlit surface for the Explore tab.

    The fragment is the same string ``build_site.py`` inlines, handed to an
    iframe because the graph needs a canvas and its own event handlers —
    neither of which survives ``st.markdown``'s sanitiser. Cross-tab "open
    card" links cannot cross the iframe boundary; the static site is where
    those resolve.
    """
    import streamlit.components.v1 as components

    st.subheader("Explore")
    st.markdown(EXPLORE_LEAD)
    components.html(_build_explore_html(), height=800, scrolling=True)
    st.caption(
        "Graph edges are the cross-references the datasets declare, plus shared "
        "taxonomy values (off by default). Similarity is TF-IDF over each record's "
        "own text — lexical, not semantic."
    )


# --- Main App ---


def main():
    inject_responsive_css()
    device = get_device_type()
    cfg = get_chart_config(device.device_type)
    is_mobile = device.device_type == DeviceType.MOBILE
    is_tablet = device.device_type == DeviceType.TABLET

    # Title (above tabs, consistent across views)
    if is_mobile:
        st.title("DC Water Tracker")
    else:
        st.title("Data Center Water Use Tracker")
        st.caption(
            "Tracking data center water consumption in **Virginia** & **Ohio** "
            "via public regulatory data."
        )

    # The same schematic the static site puts under its h1: what happens to the
    # water, and which leg of it carries a permit.
    st.markdown(_build_water_loop_svg(), unsafe_allow_html=True)

    (
        tab_legislation,
        tab_cwa,
        tab_issues,
        tab_news,
        tab_solutions,
        tab_sources,
        tab_explore,
    ) = st.tabs(
        [
            "Legislation",
            "Water Cases",
            "Issues & Claims",
            "News",
            "Solutions",
            "Sources",
            "Explore",
        ]
    )

    # --- CWA Cases tab ---
    with tab_cwa:
        render_cwa_tracker()

    # --- Issues & Claims tab ---
    with tab_issues:
        render_issues_and_claims()

    # --- News tab ---
    with tab_news:
        render_water_news()

    # --- Solutions tab ---
    with tab_solutions:
        render_water_solutions()

    # --- Legislation tab (homepage) ---
    with tab_legislation:
        # Headline panel — eager. Pass device flags so it can switch from the
        # dataframe layout (desktop) to a vertical card list (mobile/tablet).
        render_legislation_tracker(is_mobile=is_mobile, is_tablet=is_tablet)

        # Lazy panels — toggle-gated so the cold-start render skips the
        # heavy markdown construction below the fold. (st.expander still
        # executes its content eagerly; only st.toggle / st.checkbox
        # actually defer.)
        st.markdown("---")
        if st.toggle(
            "Show Policy & Disclosure Timeline",
            value=False,
            key="lazy_timeline",
        ):
            render_timeline()


    # --- Sources tab ---
    with tab_sources:
        render_sources_tab()

    # --- Explore tab ---
    with tab_explore:
        render_explore()

    # --- Flow data (developer preview, hidden until live map tab ships) ---
    # render_data_freshness, render_inline_filters, render_hero,
    # render_flow_chart, render_local_context, render_source_breakdown,
    # render_seasonal_heatmap, render_transparency_scorecard,
    # render_per_query_explainer, render_data_table are all preserved;
    # wire them to the live-map tab when it is built.


if __name__ == "__main__":
    main()
