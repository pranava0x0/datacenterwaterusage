"""Data Center Water Use Tracker — Insights Dashboard

Responsive Streamlit dashboard for tracking data center water consumption.
Adapts layout for mobile, tablet, and desktop viewports.

Run with: streamlit run dashboard.py
"""

from __future__ import annotations

import html
import json
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

# --- Config ---

BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "data" / "output" / "results.csv"
JSON_PATH = BASE_DIR / "data" / "output" / "results.json"
LEGISLATION_PATH = BASE_DIR / "data" / "reference" / "legislation.json"
COMPANY_WATER_CLAIMS_PATH = BASE_DIR / "data" / "reference" / "company_water_claims.json"
CWA_INVESTIGATIONS_PATH = BASE_DIR / "data" / "reference" / "cwa_investigations.json"

COLORS = {
    "primary": "#08519c",
    "secondary": "#3182bd",
    "tertiary": "#6baed6",
    "light": "#bdd7e7",
    "bg": "#eff3ff",
    "danger": "#c41e3a",
    "warning": "#d4a017",
    "success": "#2e8b57",
    "text": "#1a1a2e",
}

COLOR_SEQUENCE = ["#08519c", "#3182bd", "#6baed6", "#9ecae1", "#c6dbef"]


# --- Data Loading ---


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    """Load and clean results data from CSV."""
    if not CSV_PATH.exists():
        return pd.DataFrame()

    df = pd.read_csv(CSV_PATH)

    df["document_date"] = pd.to_datetime(df["document_date"], errors="coerce")
    df["scraped_at"] = pd.to_datetime(df["scraped_at"], errors="coerce")
    df["flow_mgd"] = df["extracted_water_metric"].apply(_extract_flow_mgd)

    date_mask = df["document_date"].notna()
    df["monitoring_month"] = ""
    df.loc[date_mask, "monitoring_month"] = (
        df.loc[date_mask, "document_date"].dt.to_period("M").astype(str)
    )

    df["record_type"] = df["source_portal"].apply(_classify_source)
    return df


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


@st.cache_data(ttl=300)
def load_legislation(path: Path = LEGISLATION_PATH) -> dict:
    """Load the data center water/energy legislation dataset.

    Returns a payload dict of the form {"last_updated": str, "bills": [...]}.
    Tolerates a missing file (returns an empty payload) or a bare list.
    Cached because Streamlit reruns the whole script on every interaction;
    the enriched legislation.json is ~57 KB and parses on every rerun otherwise.
    """
    if not Path(path).exists():
        return {"last_updated": None, "bills": []}
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, list):
        return {"last_updated": None, "bills": payload}
    payload.setdefault("bills", [])
    return payload


@st.cache_data(ttl=300)
def load_company_water_claims(path: Path = COMPANY_WATER_CLAIMS_PATH) -> dict:
    """Load the company water-claims dataset (mirrored from datacentercommunitybenefits).

    Returns a payload dict {"last_updated", "companies", "claims", ...}.
    Tolerates a missing file by returning an empty payload.
    """
    if not Path(path).exists():
        return {"last_updated": None, "companies": {}, "claims": []}
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    payload.setdefault("claims", [])
    payload.setdefault("companies", {})
    return payload


@st.cache_data(ttl=300)
def load_cwa_investigations(path: Path = CWA_INVESTIGATIONS_PATH) -> dict:
    """Load historic Clean Water Act enforcement / precedent dataset.

    Returns {"last_updated": str, "cases": [...], "note": Optional[str]}.
    Tolerates a missing file by returning an empty payload.
    """
    if not Path(path).exists():
        return {"last_updated": None, "cases": []}
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    payload.setdefault("cases", [])
    return payload


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


def compute_household_equivalent(gallons_per_year: int, gpd: int = 200) -> int:
    """Convert annual gallons to equivalent number of households served."""
    if gpd <= 0:
        return 0
    return int(gallons_per_year / (gpd * 365))


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

LEGISLATION_STATUS_ORDER = {"enacted": 0, "introduced": 1, "failed": 2, "unknown": 3}
LEGISLATION_STATUS_LABELS = {
    "enacted": "Enacted",
    "introduced": "Introduced",
    "failed": "Failed / Vetoed",
    "unknown": "Unknown",
}


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


LEGISLATION_STATUS_BADGE_COLORS = {
    "enacted": COLORS["success"],
    "introduced": COLORS["primary"],
    "failed": COLORS["danger"],
    "unknown": COLORS["secondary"],
}


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

    st.markdown(
        f"**{len(bills)} bills tracked** — {_legislation_status_summary(bills)}"
    )

    sorted_bills = sorted(
        bills,
        key=lambda b: (
            LEGISLATION_STATUS_ORDER.get(b.get("status"), 9),
            b.get("jurisdiction", ""),
        ),
    )
    for bill in sorted_bills:
        _render_bill_card(bill)

    last_updated = payload.get("last_updated") or "unknown"
    st.caption(
        f"Dataset last updated {last_updated}. Verification status for each "
        "entry is tracked in the underlying JSON; treat any not flagged "
        "verified=true there as secondary-sourced."
    )


def _render_bill_card(bill: dict):
    """Render one legislation entry as a single HTML blob via one st.markdown call.

    Streamlit reruns the whole script on every interaction, and each st.markdown
    call ships a separate component over the WebSocket. The earlier
    implementation used ~20 markdown calls per bill (14 bills × 20 = ~280
    components) and `st.expander`, which renders its body eagerly. This version
    emits one HTML string per bill (~14 components total) and uses the
    browser-native `<details>` element so the expander state is purely
    client-side — no re-render needed to open or close it.
    """
    st.markdown(_build_bill_card_html(bill), unsafe_allow_html=True)


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

    return f'<div class="bill-card">{head}{body}{meta}{details}</div>'


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


# --- Clean Water Act Investigations Tracker ---

CWA_CATEGORY_ORDER = {
    "datacenter": 0,
    "adjacent": 1,
    "industrial": 2,
    "precedent": 3,
}
CWA_CATEGORY_LABELS = {
    "datacenter": "Data Center",
    "adjacent": "Data-Center Adjacent",
    "industrial": "Industrial Water",
    "precedent": "Landmark Precedent",
}


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


def render_cwa_datacenter_insights():
    """Headline 'what this record tells data centers' panel.

    Computed live from the dataset so the counts move with the cases, then
    framed around the tracker's mission: the operational CWA exposure for a
    data center lands on the *receiving* WWTP permit — which is exactly what
    this project monitors via EPA ECHO DMR.
    """
    payload = load_cwa_investigations()
    stats = _cwa_datacenter_insights(payload.get("cases", []))
    total = stats["total"]
    if not total:
        return
    with st.container(border=True):
        st.markdown("#### What this record tells data centers")
        st.markdown(
            f"- **The permittee shield.** {stats['contractor_permittee']} of "
            f"{total} direct data-center cases name a construction contractor "
            "or subcontractor — not the hyperscaler — as the party on the "
            "permit. Operators routinely sit one entity removed from the "
            "permittee, which is why direct enforcement against them is thin."
        )
        st.markdown(
            f"- **CWA risk is front-loaded into construction.** Construction "
            "stormwater, sediment, and erosion under the §402 Construction "
            f"General Permit is the most common touchpoint — it appears in "
            f"{stats['construction_stormwater']} of {total} cases, far more "
            "than operational cooling-water discharge."
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


def render_cwa_tracker():
    """Render the Clean Water Act historic investigations panel.

    Three categories: direct data-center cases (rare), large-industrial-user
    enforcement (closest practical analogs), and landmark precedent cases that
    set the legal doctrines for what CWA actually reaches. Cases are sorted
    most-recent-first within each category so the freshest enforcement bubbles
    to the top.
    """
    st.subheader("Clean Water Act Investigations")
    st.markdown(
        "Enforcement actions and landmark court rulings under the Clean Water "
        "Act, organized by what they actually tell us about how the law applies "
        "to data center water use and cooling discharges."
    )

    payload = load_cwa_investigations()
    cases = payload.get("cases", [])
    if not cases:
        note = payload.get("note") or "Dataset not found or empty."
        st.info(note)
        return

    # Headline synthesis — the computed "so what" before the case list.
    render_cwa_datacenter_insights()

    with st.expander(
        "What is a Clean Water Act investigation? — statute, authority, "
        "and why it's deployed"
    ):
        st.markdown(_cwa_statute_explainer_md())

    # Filter controls — category multiselect + 2020+ toggle. Defaults show
    # everything so first-time visitors see the full dataset.
    filter_cols = st.columns([3, 1])
    with filter_cols[0]:
        selected_categories = st.multiselect(
            "Filter by category",
            options=list(CWA_CATEGORY_LABELS.keys()),
            default=list(CWA_CATEGORY_LABELS.keys()),
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

    filtered = [c for c in cases if c.get("category") in selected_categories]
    if recent_only:
        filtered = [c for c in filtered if _cwa_year_end(c.get("year", "")) >= 2020]

    if not filtered:
        st.info("No cases match the current filter. Try widening the category or year selection.")
        return

    st.markdown(
        f"**Showing {len(filtered)} of {len(cases)} cases** — {_cwa_summary(filtered)}"
    )

    # Sort: category order, then year descending (most recent first).
    sorted_cases = sorted(
        filtered,
        key=lambda c: (
            CWA_CATEGORY_ORDER.get(c.get("category"), 9),
            -_cwa_year_end(c.get("year", "")),
        ),
    )
    for case in sorted_cases:
        st.markdown(_build_cwa_case_html(case), unsafe_allow_html=True)

    last_updated = payload.get("last_updated") or "unknown"
    note = payload.get("note", "")
    caption = f"Dataset last updated {last_updated}."
    if note:
        caption += " " + note
    st.caption(caption)


def _build_cwa_case_html(case: dict) -> str:
    """Build the complete HTML for one CWA case card as a single markdown blob."""
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

    section_line = (
        f'<div class="cwa-section-line">{cwa_section}</div>' if cwa_section else ""
    )

    sections = []
    if violation:
        sections.append(
            '<div class="bill-section-label">Violation</div>'
            f'<p class="bill-sentiment">{violation}</p>'
        )
    if outcome:
        sections.append(
            '<div class="bill-section-label">Outcome</div>'
            f'<p class="bill-sentiment">{outcome}</p>'
        )
    if takeaway:
        sections.append(
            '<div class="bill-section-label">Relevance to data centers</div>'
            f'<p class="cwa-takeaway">{takeaway}</p>'
        )
    if sources:
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
        sections.append(
            '<div class="bill-section-label">Sources</div>'
            f'<div class="cwa-sources">{" · ".join(items)}</div>'
        )

    body = "".join(sections)
    return f'<div class="bill-card">{head}{section_line}{body}</div>'


# --- Company Water Claims ---

DELIVERED_STATUS_COLORS = {
    "delivered": "success",
    "partial": "warning",
    "contested": "warning",
    "shortfall": "danger",
}


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

        delivered = claim.get("delivered")
        if delivered:
            status = str(delivered.get("status", "")).lower()
            status_label = {
                "delivered": "Delivered",
                "partial": "Partial",
                "contested": "Contested",
                "shortfall": "Shortfall",
            }.get(status, status.title() or "Unknown")
            d_summary = delivered.get("summary", "")
            d_url = delivered.get("source_url", "")
            d_title = delivered.get("source_title", "assessment")
            d_assessed = delivered.get("assessed_at", "")
            box_fn = {
                "delivered": st.success,
                "partial": st.warning,
                "contested": st.warning,
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

    # Three tabs — Legislation is the homepage, CWA Cases is the enforcement
    # history, Data is the measurements side.
    tab_legislation, tab_cwa, tab_data = st.tabs(
        ["Legislation", "CWA Cases", "Data"]
    )

    # --- CWA Cases tab ---
    with tab_cwa:
        render_cwa_tracker()

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

        st.markdown("---")
        if st.toggle(
            "Show Company Water Claims (29 verbatim operator quotes)",
            value=False,
            key="lazy_claims",
        ):
            render_company_water_claims()

    # --- Data tab ---
    with tab_data:
        df = load_data()
        if df.empty:
            st.warning(
                "No data found. Run the scraping pipeline first:\n\n"
                "```bash\npython main.py --scraper epa_echo --limit 50\n```"
            )
            return

        # Eager: freshness, filters, hero, flow chart, local context.
        render_data_freshness(df)
        filtered_df = render_inline_filters(df)

        if is_mobile or is_tablet:
            render_hero_compact(filtered_df)
        else:
            render_hero(filtered_df)

        render_flow_chart(filtered_df, cfg)

        if is_mobile:
            with st.expander("How does this compare?"):
                render_local_context(is_mobile=True)
        else:
            render_local_context(is_mobile=False)

        # Lazy panels — toggle to load. Skipped during cold start to keep
        # first paint fast; each render_* call is the heavy work.
        st.markdown("---")
        st.caption("Optional views — toggle to load:")

        if not is_mobile and not is_tablet:
            if st.toggle(
                "Records by Source chart",
                value=False,
                key="lazy_breakdown",
            ):
                render_source_breakdown(filtered_df, cfg)

        if not is_mobile:
            if st.toggle(
                "Seasonal Patterns heatmap",
                value=False,
                key="lazy_heatmap",
            ):
                render_seasonal_heatmap(filtered_df, cfg)

        if st.toggle(
            "Transparency Scorecard",
            value=False,
            key="lazy_scorecard",
        ):
            render_transparency_scorecard()

        if st.toggle(
            "Per-query water estimates explainer",
            value=False,
            key="lazy_perquery",
        ):
            render_per_query_explainer()

        if st.toggle(
            "Records table",
            value=False,
            key="lazy_table",
        ):
            render_data_table(filtered_df, compact=(is_mobile or is_tablet))

        # Mobile download button (sidebar not visible on mobile).
        if is_mobile and not filtered_df.empty:
            st.download_button(
                "Download CSV",
                filtered_df.to_csv(index=False),
                "dc_water_data.csv",
                "text/csv",
            )


if __name__ == "__main__":
    main()
