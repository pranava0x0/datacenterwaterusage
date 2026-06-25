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
from pathlib import Path
from typing import NamedTuple

import streamlit as st

# Breakpoints
MOBILE_MAX = 768
TABLET_MAX = 1024

# session_state key under which the resolved DeviceInfo is memoized for the
# rest of the session (see get_device_type).
_DEVICE_CACHE_KEY = "_resolved_device_info"


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


def _classify_width(width: int | None) -> DeviceInfo:
    """Pure viewport-width → DeviceInfo classification.

    Defaults to DESKTOP when width is unavailable (first render); CSS media
    queries handle styling until JS reports back. Kept JS- and
    session_state-free so the breakpoint logic is directly unit-testable.
    """
    if width is None:
        return DeviceInfo(DeviceType.DESKTOP, None)
    if width < MOBILE_MAX:
        return DeviceInfo(DeviceType.MOBILE, width)
    if width < TABLET_MAX:
        return DeviceInfo(DeviceType.TABLET, width)
    return DeviceInfo(DeviceType.DESKTOP, width)


def get_device_type() -> DeviceInfo:
    """Classify the client device, memoizing the result for the session.

    Streamlit reruns the whole script on every interaction, and each run
    otherwise re-issues the ``streamlit-js-eval`` component round-trip to read
    the viewport width. Once a real width has resolved we cache the resulting
    DeviceInfo in ``st.session_state`` and reuse it, so routine interactions
    (filter changes, tab switches, toggles) skip the JS round-trip entirely.

    We deliberately do NOT cache the cold-start ``None`` frame, so detection
    keeps retrying until a real width arrives. A browser resize takes effect on
    reload, which starts a fresh session and clears this cache, so the device
    is re-detected then — consistent with the prior behavior.
    """
    try:
        cached = st.session_state.get(_DEVICE_CACHE_KEY)
    except Exception:
        cached = None
    if isinstance(cached, DeviceInfo):
        return cached

    info = _classify_width(get_viewport_width())

    # Only memoize once a real width resolved — never lock in the cold default.
    if info.viewport_width is not None:
        try:
            st.session_state[_DEVICE_CACHE_KEY] = info
        except Exception:
            pass
    return info


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


# Shared component CSS lives in assets/components.css (a real .css file
# gets IDE highlighting/formatting). Loaded once at import and wrapped for
# st.markdown; build_site.py strips the <style> wrapper.
_RESPONSIVE_CSS = (
    "<style>\n"
    + (Path(__file__).resolve().parents[1] / "assets" / "components.css").read_text()
    + "</style>\n"
)


def inject_responsive_css():
    """Inject CSS media queries for immediate responsive styling."""
    st.markdown(_RESPONSIVE_CSS, unsafe_allow_html=True)
