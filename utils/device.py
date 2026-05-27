"""Device detection utility for Streamlit dashboards.

Provides viewport width detection, device type classification,
responsive CSS injection, and per-device chart configuration.

Usage:
    from utils.device import get_device_type, inject_responsive_css, get_chart_config, DeviceType

    device = get_device_type()  # DeviceInfo(device_type, viewport_width)
    inject_responsive_css()
    chart_cfg = get_chart_config(device.device_type)
"""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple

import streamlit as st

# Breakpoints
MOBILE_MAX = 768
TABLET_MAX = 1024


class DeviceType(str, Enum):
    MOBILE = "mobile"
    TABLET = "tablet"
    DESKTOP = "desktop"


class DeviceInfo(NamedTuple):
    device_type: DeviceType
    viewport_width: int | None


def get_viewport_width() -> int | None:
    """Get the client viewport width via JavaScript.

    Returns None on first render before JS executes, or when the reported
    value is implausibly small. Some streamlit-js-eval versions return 0
    as a placeholder before the real width arrives — without this guard
    the classifier would treat 0 < MOBILE_MAX as mobile on every first
    render.
    """
    try:
        from streamlit_js_eval import streamlit_js_eval

        # streamlit-js-eval runs inside its own component iframe, so
        # `window.innerWidth` reports the iframe's own viewport (sized to the
        # Streamlit content column, ~600px even on a 1280px host page). Reach
        # for `window.parent.innerWidth` to escape the iframe and get the host
        # viewport. Falls back to inner-width if cross-origin blocks access.
        width = streamlit_js_eval(
            js_expressions=(
                "(()=>{try{return window.parent.innerWidth;}"
                "catch(e){return window.innerWidth;}})()"
            ),
            # Key change forces streamlit-js-eval to remount the component
            # iframe with the new js_expressions string (the previous key was
            # cached with the old `window.innerWidth` expression).
            key="viewport_width_parent_v1",
        )
        if width is None:
            return None
        try:
            w = int(width)
        except (TypeError, ValueError):
            return None
        if w < 200:
            return None
        return w
    except ImportError:
        pass
    return None


def get_device_type() -> DeviceInfo:
    """Classify client device based on viewport width.

    Defaults to DESKTOP when width is unavailable (first render).
    CSS media queries handle styling until JS reports back.
    """
    width = get_viewport_width()

    if width is None:
        return DeviceInfo(DeviceType.DESKTOP, None)
    if width < MOBILE_MAX:
        return DeviceInfo(DeviceType.MOBILE, width)
    if width < TABLET_MAX:
        return DeviceInfo(DeviceType.TABLET, width)
    return DeviceInfo(DeviceType.DESKTOP, width)


def get_chart_config(device_type: DeviceType) -> dict:
    """Return Plotly layout overrides per device type."""
    configs = {
        DeviceType.DESKTOP: {
            "flow_height": 450,
            "heatmap_height": 350,
            "source_height": 300,
            "table_height": 400,
            "font_size": 12,
            "title_font_size": 16,
            "legend_y": -0.3,
            "marker_size": 6,
            "line_width": 2,
            "show_legend": True,
            "hovermode": "x unified",
            "margin": dict(l=60, r=30, t=60, b=60),
        },
        DeviceType.TABLET: {
            "flow_height": 380,
            "heatmap_height": 280,
            "source_height": 250,
            "table_height": 300,
            "font_size": 11,
            "title_font_size": 14,
            "legend_y": -0.35,
            "marker_size": 5,
            "line_width": 2,
            "show_legend": True,
            "hovermode": "x unified",
            "margin": dict(l=50, r=20, t=50, b=50),
        },
        DeviceType.MOBILE: {
            "flow_height": 300,
            "heatmap_height": 250,
            "source_height": 200,
            "table_height": 250,
            "font_size": 10,
            "title_font_size": 12,
            "legend_y": -0.45,
            "marker_size": 4,
            "line_width": 1.5,
            "show_legend": False,
            "hovermode": "closest",
            "margin": dict(l=40, r=15, t=40, b=40),
        },
    }
    return configs[device_type]


_RESPONSIVE_CSS = """
<style>
/* --- Defensive rendering hardening ---
   Some Streamlit versions dim content during script reruns by setting
   data-stale="true" with low opacity, which makes text look ghostly while
   the page rebuilds. Keep content fully opaque so it stays readable. Also
   force text colors and link colors so they survive any theme override
   (Streamlit Cloud, system dark-mode auto-detection, etc.). */
[data-stale="true"],
.element-container[data-stale="true"],
[data-testid="stElementContainer"][data-stale="true"],
.stApp [data-stale="true"] {
    opacity: 1 !important;
    filter: none !important;
    pointer-events: auto !important;
}
.stApp {
    color: #1a1a2e;
}
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
    color: #1a1a2e !important;
}
.stApp p, .stApp li, .stApp [data-testid="stMarkdownContainer"] {
    color: #1a1a2e;
}
.stApp a {
    color: #08519c;
}
/* Belt-and-suspenders: even if a theme override hits the text, this keeps
   the bill/CWA card content readable. */
.bill-card,
.bill-card * {
    color: #1a1a2e;
}
.bill-card a,
.bill-card .bill-card-details > summary {
    color: #08519c !important;
}

/* --- Water aesthetic: page surface + droplet texture + wave underline --- */
/* See DESIGN.md for the rules. Pattern uses an inline SVG of four teardrop
   ellipses per 120x120 tile at ~5% opacity over a near-white #f5f9fc surface.
   background-attachment: fixed so the texture doesn't shear during scroll. */
[data-testid="stAppViewContainer"] > .main,
.stApp {
    background-color: #f5f9fc;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 120 120'><g fill='%2308519c' fill-opacity='0.055'><ellipse cx='22' cy='18' rx='2' ry='3'/><ellipse cx='88' cy='42' rx='1.6' ry='2.4'/><ellipse cx='55' cy='78' rx='2.2' ry='3.3'/><ellipse cx='100' cy='100' rx='1.4' ry='2.1'/></g></svg>");
    background-repeat: repeat;
    background-attachment: fixed;
}
/* Single hint-of-motion wave underline beneath the h1 title only. */
.stApp h1 {
    padding-bottom: 0.4rem;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 60 6' preserveAspectRatio='none'><path d='M0 3 Q 15 0, 30 3 T 60 3' fill='none' stroke='%233182bd' stroke-width='1.2' stroke-opacity='0.55'/></svg>");
    background-repeat: repeat-x;
    background-position: left bottom;
    background-size: 60px 6px;
}

/* --- Base: tighten default Streamlit padding --- */
.stMainBlockContainer {
    padding-top: 1rem;
}

/* --- MOBILE: < 768px --- */
@media (max-width: 767px) {
    /* Hide sidebar entirely on mobile */
    section[data-testid="stSidebar"],
    button[data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }

    .stMainBlockContainer {
        padding-left: 0.5rem;
        padding-right: 0.5rem;
        padding-top: 0.5rem;
    }

    [data-testid="stMetric"] {
        padding: 0.4rem 0;
    }
    [data-testid="stMetric"] label {
        font-size: 0.75rem;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }

    h1 {
        font-size: 1.3rem !important;
    }

    hr {
        margin: 0.5rem 0;
    }

    .stDataFrame {
        overflow-x: auto;
    }

    /* Touch-friendly buttons and controls */
    button, .stButton > button, .stDownloadButton > button {
        min-height: 44px;
        min-width: 44px;
    }

    /* Popover filter button: full width on mobile */
    [data-testid="stPopover"] > button {
        width: 100%;
    }

    /* Context cards: tighter padding */
    .context-card {
        padding: 0.75rem !important;
        font-size: 0.9rem;
    }

    /* Expanders: larger tap target */
    [data-testid="stExpander"] summary {
        min-height: 44px;
        display: flex;
        align-items: center;
    }
}

/* --- TABLET: 768px - 1024px --- */
@media (min-width: 768px) and (max-width: 1024px) {
    .stMainBlockContainer {
        padding-left: 1rem;
        padding-right: 1rem;
    }

    [data-testid="stMetric"] label {
        font-size: 0.85rem;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.8rem;
    }
}

/* --- Context card styling --- */
.context-card {
    background: #f8f9fa;
    border-left: 4px solid #08519c;
    padding: 1rem;
    border-radius: 0 0.5rem 0.5rem 0;
    margin-bottom: 0.75rem;
}
.context-card h4 {
    margin: 0 0 0.5rem 0;
    color: #08519c;
}
.context-card .big-number {
    font-size: 1.8rem;
    font-weight: 700;
    color: #1a1a2e;
    line-height: 1.2;
}
.context-card .comparison {
    color: #555;
    font-size: 0.95rem;
    margin-top: 0.25rem;
}
.context-card .source-note {
    color: #888;
    font-size: 0.8rem;
    margin-top: 0.5rem;
}

/* --- Explainer card styling --- */
.explainer-card {
    background: #fffbf0;
    border: 1px solid #e8d5a3;
    padding: 1.25rem;
    border-radius: 0.5rem;
    margin-bottom: 0.75rem;
}
.explainer-card h4 {
    margin: 0 0 0.75rem 0;
    color: #6b4c00;
}
.range-bar {
    background: linear-gradient(90deg, #bdd7e7 0%, #08519c 100%);
    height: 12px;
    border-radius: 6px;
    position: relative;
    margin: 1rem 0;
}
.range-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.8rem;
    color: #555;
}
/* --- Timeline styling --- */
.timeline-event {
    display: flex;
    gap: 1rem;
    padding: 0.75rem 0;
    border-bottom: 1px solid #eee;
}
.timeline-date {
    min-width: 3rem;
    font-weight: 700;
    color: #08519c;
    font-size: 0.9rem;
}
.timeline-body {
    flex: 1;
}
.timeline-badge {
    display: inline-block;
    color: white;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 0.1rem 0.4rem;
    border-radius: 3px;
    margin-right: 0.3rem;
    text-transform: uppercase;
}
.timeline-detail {
    color: #555;
    font-size: 0.9rem;
}
/* --- Bill card (single-emit, native <details>) styling --- */
/* Explicit colors throughout so cards remain readable during any Streamlit
   stale-content overlay or theme variation. Box-shadow gives visual
   separation even if the border color fails to render. */
.bill-card {
    border: 1px solid #cbd5e1;
    border-radius: 0.5rem;
    padding: 1rem;
    margin-bottom: 0.75rem;
    background: #ffffff;
    color: #1a1a2e;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.06);
}
.bill-card-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-bottom: 0.35rem;
}
.bill-card-id {
    font-weight: 700;
    font-size: 1.05rem;
    color: #1a1a2e;
}
.bill-card-pill {
    color: #ffffff;
    padding: 0.15rem 0.7rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    white-space: nowrap;
}
.bill-card-summary {
    margin: 0 0 0.4rem 0;
    line-height: 1.5;
    color: #1a1a2e;
}
.bill-card-meta {
    color: #4b5563;
    font-size: 0.85rem;
    margin-bottom: 0.4rem;
}
.bill-card-meta a {
    color: #08519c;
    text-decoration: none;
}
.bill-card-meta a:hover {
    text-decoration: underline;
}
.bill-card-details {
    margin-top: 0.5rem;
    border-top: 1px dashed #e5e7eb;
    padding-top: 0.4rem;
}
.bill-card-details > summary {
    cursor: pointer;
    color: #08519c;
    font-weight: 600;
    font-size: 0.88rem;
    padding: 0.35rem 0;
    list-style: none;
}
.bill-card-details > summary::marker,
.bill-card-details > summary::-webkit-details-marker {
    display: none;
}
.bill-card-details > summary::before {
    content: "▸ ";
    display: inline-block;
    transition: transform 0.15s ease;
    margin-right: 0.25rem;
}
.bill-card-details[open] > summary::before {
    transform: rotate(90deg);
}
.bill-sentiment {
    margin: 0.2rem 0 0.6rem 0;
    line-height: 1.55;
    color: #1f2937;
}
/* --- Bill detail (expander contents) styling --- */
.bill-section-label {
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 0.72rem;
    font-weight: 700;
    color: #08519c;
    margin: 0.5rem 0 0.35rem 0;
}
.bill-mini-event {
    display: flex;
    gap: 0.75rem;
    padding: 0.3rem 0;
    border-bottom: 1px dashed #eef2f7;
    font-size: 0.85rem;
}
.bill-mini-event:last-child {
    border-bottom: none;
}
.bill-mini-date {
    min-width: 5.5rem;
    color: #08519c;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}
.bill-mini-body {
    flex: 1;
    color: #1a1a2e;
}
.bill-mini-detail {
    color: #555;
}
.bill-news-item {
    padding: 0.4rem 0;
    border-bottom: 1px dashed #eef2f7;
    font-size: 0.88rem;
}
.bill-news-item:last-child {
    border-bottom: none;
}
.bill-news-meta {
    color: #666;
    font-size: 0.78rem;
}
.bill-news-takeaway {
    color: #333;
    margin-top: 0.15rem;
}
.bill-principle-chip {
    display: inline-block;
    background: #eff3ff;
    color: #08519c;
    border: 1px solid #bdd7e7;
    padding: 0.1rem 0.55rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-right: 0.4rem;
}
.bill-principle-row {
    padding: 0.25rem 0;
    font-size: 0.85rem;
    color: #333;
}
/* --- CWA case card variant (reuses .bill-card base) --- */
.cwa-year {
    color: #4b5563;
    font-weight: 400;
    font-size: 0.95rem;
}
.cwa-section-line {
    color: #08519c;
    font-weight: 600;
    font-size: 0.85rem;
    margin-bottom: 0.5rem;
    font-style: italic;
}
.cwa-takeaway {
    background: #f0fdf4;
    border-left: 3px solid #2e8b57;
    padding: 0.5rem 0.75rem;
    margin: 0.2rem 0 0.6rem 0;
    color: #1a1a2e;
    line-height: 1.5;
    border-radius: 0 0.25rem 0.25rem 0;
}
.cwa-sources {
    font-size: 0.82rem;
    color: #4b5563;
    line-height: 1.6;
}
.cwa-sources a {
    color: #08519c;
}
.cwa-source-type {
    color: #6b7280;
    font-size: 0.75rem;
}
</style>
"""


def inject_responsive_css():
    """Inject CSS media queries for immediate responsive styling."""
    st.markdown(_RESPONSIVE_CSS, unsafe_allow_html=True)
