"""The Overview landing tab: numbers, question cards, the 30-day feed."""

from __future__ import annotations

import re
from datetime import datetime

import pytest

import build_site
import dashboard

FROZEN = datetime(2026, 9, 26)


class TestOverviewFeed:
    @pytest.fixture(scope="class")
    def feed(self):
        return dashboard._overview_feed(FROZEN)

    def test_newest_first_and_within_the_window(self, feed):
        dates = [r["date"] for r in feed]
        assert dates == sorted(dates, reverse=True)
        assert all(d >= "2026-08" for d in dates)
        assert len(feed) <= dashboard.OVERVIEW_FEED_LIMIT

    def test_a_headline_absorbs_the_instruments_it_cites(self, feed):
        ca = next(r for r in feed if r["kind"] == "news" and "California" in r["links"][0][0])
        assert {label for label, _a, _u in ca["related"]} >= {"CA AB 2469", "CA AB 2619"}
        # ...so the same signing is not listed again as its own rows.
        standalone = {label for r in feed if r["kind"] == "instrument" for label, _a, _u in r["links"]}
        assert not standalone & {"CA AB 2469", "CA AB 2619", "CA AB 1577", "CA SB 887"}

    def test_instruments_attach_only_to_the_headline_that_cites_them(self, feed):
        """Regression: two governors signed orders on 2026-09-18; Virginia's
        order was first attached to Nevada's headline."""
        for r in feed:
            if r["kind"] == "news" and r["related"]:
                cited = set(r.get("targets", []))
                assert {label for label, _a, _u in r["related"]} <= cited, r["links"][0][0]

    def test_future_milestones_do_not_count_as_movement(self):
        feed = dashboard._overview_feed(FROZEN)
        assert all(r["date"] <= "2026-09-26" for r in feed)

    def test_a_different_today_moves_the_window(self):
        earlier = dashboard._overview_feed(datetime(2026, 7, 1))
        assert all(r["date"] < "2026-07-02" for r in earlier)


class TestOverviewLocalWave:
    def test_month_precision_window(self):
        wave = dashboard._overview_local_wave(FROZEN)
        assert wave, "the Aug-Sep 2026 moratorium wave should appear"
        assert all(a["date"] >= "2026-08" for a in wave)
        assert any(a["action_id"] == "direct-palm-beach-county-fl-2026-09" for a in wave)


class TestOverviewHtml:
    @pytest.fixture(scope="class")
    def fragment(self):
        return dashboard._build_overview_html(FROZEN)

    def test_every_class_is_styled_on_both_surfaces(self, fragment):
        from refdata.loaders import BASE_DIR

        shared = (BASE_DIR / "assets" / "components.css").read_text()
        used = {c for attr in re.findall(r'class="([^"]+)"', fragment) for c in attr.split()}
        undefined = sorted(c for c in used if f".{c}" not in shared)
        assert not undefined, undefined

    def test_every_link_lands_somewhere_on_the_site(self, fragment):
        files = build_site.build_site_files()
        ids = set()
        for name, content in files.items():
            if name.endswith(".html"):
                ids |= set(re.findall(r'\bid="([^"]+)"', content))
        for target in re.findall(r'href="#([^"]+)"', fragment):
            assert target in ids, target

    def test_one_card_per_question(self, fragment):
        assert fragment.count('class="ov-card"') == len(dashboard.OVERVIEW_QUESTIONS)

    def test_tiles_count_the_live_datasets(self, fragment):
        bills = dashboard.load_legislation()["bills"]
        assert f'<span class="ov-tile-n">{len(bills)}</span>' in fragment

    def test_overview_is_the_default_and_inline(self):
        assert build_site.DEFAULT_TAB == "overview"
        index = build_site.build_site_files()["index.html"]
        assert 'data-tab="overview" aria-selected="true"' in index
        assert 'id="panel-overview" role="tabpanel">' in index
        assert "tab-overview.html" not in build_site.build_site_files()
