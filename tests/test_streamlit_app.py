"""Boot the Streamlit app headlessly and render every tab (closes TEST-002).

Every other test drives the pure builders or the static build; nothing called
a ``render_*`` function, which is how a TypeError in ``render_states_tab``
shipped past an 800-test suite (issues.md BUG-110). ``AppTest`` runs the whole
script in ~1-2 s, so one boot per suite run covers the render layer.
"""

from __future__ import annotations

import pytest

pytest.importorskip("streamlit.testing.v1")

from streamlit.testing.v1 import AppTest  # noqa: E402


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file("dashboard.py", default_timeout=120)
    at.run()
    return at


def test_the_app_renders_without_an_exception(app):
    assert not app.exception, [str(e.value)[:300] for e in app.exception]


def test_every_top_level_tab_renders(app):
    labels = [t.label for t in app.tabs]
    for expected in (
        "Overview",
        "Legislation",
        "States & Localities",
        "Commitments",
        "Water Cases",
        "Issues & Claims",
        "News",
        "Solutions",
        "Security",
        "Sources",
        "Explore",
    ):
        assert expected in labels, expected


def test_water_cases_opens_on_the_statute_paths(app):
    labels = [t.label for t in app.tabs]
    paths = next(i for i, label in enumerate(labels) if label.startswith("How statutes apply"))
    toolkit = next(i for i, label in enumerate(labels) if label.startswith("Part 1"))
    assert paths < toolkit


def test_each_tab_titles_itself_once(app):
    heads = [h.value for h in app.subheader]
    for expected in ("Overview", "Water Commitments", "States & Localities"):
        assert heads.count(expected) == 1, expected
