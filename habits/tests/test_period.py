import pytest
from datetime import datetime, timezone as dt_timezone  

from habits.services.period import get_period_bounds, get_period_key, generate_periods


def utc(y, m, d, h=0, minute=0):
    return datetime(y, m, d, h, minute, tzinfo=dt_timezone.utc)


# -------------------
# Boundary tests
# -------------------

def test_daily_bounds_midday():
    dt = utc(2026, 3, 11, 14)
    start, end = get_period_bounds(dt, "DAILY")

    assert start == utc(2026, 3, 11)
    assert end == utc(2026, 3, 11, 23, 59).replace(second=59, microsecond=999999)


def test_weekly_bounds_wednesday():
    dt = utc(2026, 3, 11)  # Wednesday
    start, end = get_period_bounds(dt, "WEEKLY")

    assert start == utc(2026, 3, 9)  # Monday
    assert end.date().isoformat() == "2026-03-15"


def test_monthly_bounds_midmonth():
    dt = utc(2026, 3, 15)
    start, end = get_period_bounds(dt, "MONTHLY")

    assert start == utc(2026, 3, 1)
    assert end.date().isoformat() == "2026-03-31"


def test_boundary_midnight():
    dt = utc(2026, 3, 11)
    start, end = get_period_bounds(dt, "DAILY")

    assert start == utc(2026, 3, 11)
    assert end.date().isoformat() == "2026-03-11"


# -------------------
# Period key tests
# -------------------

def test_daily_key():
    dt = utc(2026, 3, 11)
    assert get_period_key(dt, "DAILY") == "2026-03-11"


def test_weekly_key():
    dt = utc(2026, 3, 11)
    assert get_period_key(dt, "WEEKLY").startswith("2026-W")


def test_monthly_key():
    dt = utc(2026, 3, 11)
    assert get_period_key(dt, "MONTHLY") == "2026-03"


# -------------------
# ISO week boundary
# -------------------

def test_iso_week_boundary():
    dt = utc(2024, 12, 30)
    key = get_period_key(dt, "WEEKLY")

    assert key == "2025-W01"


# -------------------
# generate_periods
# -------------------

def test_generate_daily_periods():
    start = utc(2026, 3, 1)
    end = utc(2026, 3, 3)

    periods = generate_periods(start, end, "DAILY")

    assert len(periods) == 3


def test_generate_weekly_periods():
    start = utc(2026, 3, 2)
    end = utc(2026, 3, 15)

    periods = generate_periods(start, end, "WEEKLY")

    assert len(periods) == 2


def test_generate_monthly_periods():
    start = utc(2026, 1, 1)
    end = utc(2026, 3, 31)

    periods = generate_periods(start, end, "MONTHLY")

    assert len(periods) == 3


def test_same_period_single_result():
    start = utc(2026, 3, 11, 10)
    end = utc(2026, 3, 11, 18)

    periods = generate_periods(start, end, "DAILY")

    assert len(periods) == 1