"""Volume → human-scale equivalents for dashboard labels.

Pure, dependency-free conversions so any gallons figure can be re-expressed in
terms a reader can feel: households served, Olympic-sized swimming pools, or
days of the New York City water system. Kept Streamlit-free so it is trivially
unit-testable and reusable by both the Streamlit app and the static-site
builder (``build_site.py``).

Constants are sourced and conservative:
- ``GPD_PER_HOUSEHOLD_EPA`` — EPA WaterSense puts average U.S. household use near
  300 gallons/day. The tracker's Virginia context cards historically used 200
  gpd (a lower regional figure), so the per-household rate is always a parameter
  with the EPA value as the default.
- ``OLYMPIC_POOL_GALLONS`` — a 50 m × 25 m × 2 m pool is ~2,500 m³ ≈ 660,000 gal.
- ``NYC_SYSTEM_GALLONS_PER_DAY`` — the NYC water system delivers ~1 billion
  gallons/day, a familiar "a whole big city for a day" yardstick.
"""

from __future__ import annotations

GPD_PER_HOUSEHOLD_EPA = 300
OLYMPIC_POOL_GALLONS = 660_000
NYC_SYSTEM_GALLONS_PER_DAY = 1_000_000_000

DAYS_PER_YEAR = 365


def gpd_to_households(
    gallons_per_day: float, gpd_per_household: int = GPD_PER_HOUSEHOLD_EPA
) -> int:
    """Households whose *daily* use equals ``gallons_per_day``.

    Returns 0 for a non-positive per-household rate (avoids divide-by-zero and
    nonsensical negatives). Rounded to the nearest household.
    """
    if gpd_per_household <= 0:
        return 0
    return round(gallons_per_day / gpd_per_household)


def annual_gallons_to_households(
    gallons_per_year: float, gpd_per_household: int = GPD_PER_HOUSEHOLD_EPA
) -> int:
    """Households served for a year by ``gallons_per_year``.

    Uses integer truncation (floor for non-negative inputs) so a partial
    household never rounds *up* to imply more service than the volume supports.
    This is the canonical math behind the dashboard's context cards.
    """
    if gpd_per_household <= 0:
        return 0
    return int(gallons_per_year / (gpd_per_household * DAYS_PER_YEAR))


def gallons_to_olympic_pools(
    gallons: float, pool_gallons: int = OLYMPIC_POOL_GALLONS
) -> float:
    """How many Olympic-sized swimming pools ``gallons`` would fill."""
    if pool_gallons <= 0:
        return 0.0
    return gallons / pool_gallons


def gallons_to_nyc_supply_days(
    gallons: float, nyc_gpd: int = NYC_SYSTEM_GALLONS_PER_DAY
) -> float:
    """How many days the NYC water system that volume of water would supply."""
    if nyc_gpd <= 0:
        return 0.0
    return gallons / nyc_gpd
