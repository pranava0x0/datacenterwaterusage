"""Tests for utils/equivalents.py — volume → human-scale conversions."""

from utils.equivalents import (
    GPD_PER_HOUSEHOLD_EPA,
    NYC_SYSTEM_GALLONS_PER_DAY,
    OLYMPIC_POOL_GALLONS,
    annual_gallons_to_households,
    gallons_to_nyc_supply_days,
    gallons_to_olympic_pools,
    gpd_to_households,
)


class TestGpdToHouseholds:
    def test_default_rate_is_epa_300(self):
        # 300,000 gpd / 300 gpd-per-home = 1,000 homes
        assert gpd_to_households(300_000) == 1_000
        assert GPD_PER_HOUSEHOLD_EPA == 300

    def test_custom_rate(self):
        assert gpd_to_households(200_000, gpd_per_household=200) == 1_000

    def test_rounds_to_nearest(self):
        # 1,499 / 300 = 4.99… → 5;  1,350 / 300 = 4.5 → 4 (banker's rounding)
        assert gpd_to_households(1_499) == 5
        assert gpd_to_households(0) == 0

    def test_nonpositive_rate_returns_zero(self):
        assert gpd_to_households(1_000_000, gpd_per_household=0) == 0
        assert gpd_to_households(1_000_000, gpd_per_household=-5) == 0


class TestAnnualGallonsToHouseholds:
    def test_matches_legacy_truncation(self):
        # The figure the dashboard pinned: 1B gal / (200 * 365) = 13,698 (floor).
        assert annual_gallons_to_households(1_000_000_000, 200) == 13_698

    def test_default_rate_is_epa_300(self):
        # 1B gal / (300 * 365) = 9,132 (floor)
        assert annual_gallons_to_households(1_000_000_000) == 9_132

    def test_truncates_not_rounds(self):
        # Just under a full household-year must not round up.
        almost = 300 * 365 * 2 - 1  # 2 homes' worth, minus a gallon
        assert annual_gallons_to_households(almost) == 1

    def test_zero_and_nonpositive_rate(self):
        assert annual_gallons_to_households(0) == 0
        assert annual_gallons_to_households(1_000_000, 0) == 0
        assert annual_gallons_to_households(1_000_000, -1) == 0


class TestOlympicPools:
    def test_one_pool(self):
        assert gallons_to_olympic_pools(OLYMPIC_POOL_GALLONS) == 1.0

    def test_half_pool(self):
        assert gallons_to_olympic_pools(OLYMPIC_POOL_GALLONS / 2) == 0.5

    def test_billion_gallons(self):
        # ~1,515 pools per billion gallons.
        pools = gallons_to_olympic_pools(1_000_000_000)
        assert 1_500 < pools < 1_530

    def test_nonpositive_pool_size(self):
        assert gallons_to_olympic_pools(1_000_000, pool_gallons=0) == 0.0


class TestNycSupplyDays:
    def test_one_day(self):
        assert gallons_to_nyc_supply_days(NYC_SYSTEM_GALLONS_PER_DAY) == 1.0

    def test_fractional_day(self):
        assert gallons_to_nyc_supply_days(NYC_SYSTEM_GALLONS_PER_DAY / 4) == 0.25

    def test_nonpositive_rate(self):
        assert gallons_to_nyc_supply_days(1_000_000, nyc_gpd=0) == 0.0
