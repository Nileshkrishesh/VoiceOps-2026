"""Unit tests for business-day calculations."""
import sys
from pathlib import Path
from datetime import date

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import is_business_day, add_business_days, business_days_between, OFFICIAL_HOLIDAYS

def test_weekday_is_business_day():
    """Monday through Saturday are business days."""
    # Monday 2026-10-05
    assert is_business_day(date(2026, 10, 5)) == True
    # Tuesday 2026-10-06
    assert is_business_day(date(2026, 10, 6)) == True
    # Wednesday 2026-10-07
    assert is_business_day(date(2026, 10, 7)) == True
    # Thursday 2026-10-08
    assert is_business_day(date(2026, 10, 8)) == True
    # Friday 2026-10-09
    assert is_business_day(date(2026, 10, 9)) == True
    # Saturday 2026-10-10
    assert is_business_day(date(2026, 10, 10)) == True

def test_sunday_not_business_day():
    """Sunday is not a business day."""
    # Sunday 2026-10-04
    assert is_business_day(date(2026, 10, 4)) == False
    # Sunday 2026-10-11
    assert is_business_day(date(2026, 10, 11)) == False
    # Sunday 2026-10-18
    assert is_business_day(date(2026, 10, 18)) == False

def test_official_holidays_not_business_days():
    """Dates in holidays.csv are not business days."""
    # Independence Day: 2026-08-15 (Saturday)
    assert is_business_day(date(2026, 8, 15)) == False
    # Gandhi Jayanti: 2026-10-02 (Friday)
    assert is_business_day(date(2026, 10, 2)) == False
    # Warehouse closure: 2026-10-19 (Monday)
    assert is_business_day(date(2026, 10, 19)) == False
    # Warehouse closure: 2026-11-09 (Monday)
    assert is_business_day(date(2026, 11, 9)) == False

def test_holidays_loaded():
    """Verify OFFICIAL_HOLIDAYS contains expected dates."""
    assert date(2026, 8, 15) in OFFICIAL_HOLIDAYS
    assert date(2026, 10, 2) in OFFICIAL_HOLIDAYS
    assert date(2026, 10, 19) in OFFICIAL_HOLIDAYS
    assert date(2026, 11, 9) in OFFICIAL_HOLIDAYS
    assert len(OFFICIAL_HOLIDAYS) == 4

def test_add_business_days_simple():
    """Test adding business days without hitting holidays or weekends."""
    # Start on Monday 2026-10-05, add 3 business days -> Thursday 2026-10-08
    result = add_business_days(date(2026, 10, 5), 3)
    assert result == date(2026, 10, 8)

def test_add_business_days_over_weekend():
    """Test adding business days that span a weekend."""
    # Start on Friday 2026-10-09, add 2 business days -> Tuesday 2026-10-13
    # (skips Saturday 10-10, Sunday 10-11, Monday 10-12 is business day, Tuesday 10-13)
    result = add_business_days(date(2026, 10, 9), 2)
    assert result == date(2026, 10, 12)

def test_add_business_days_over_holiday():
    """Test adding business days that span an official holiday."""
    # Start on Friday 2026-10-16, add 2 business days
    # Skip Saturday 10-17, Sunday 10-18, Monday 10-19 (holiday), Tuesday 10-20, Wednesday 10-21
    result = add_business_days(date(2026, 10, 16), 2)
    assert result == date(2026, 10, 20)

def test_business_days_between():
    """Test counting business days between two dates."""
    # From Monday 2026-10-05 to Friday 2026-10-09: 4 business days
    count = business_days_between(date(2026, 10, 5), date(2026, 10, 9))
    assert count == 4

def test_business_days_between_with_weekend():
    """Test counting business days over a weekend."""
    # From Friday 2026-10-09 to Tuesday 2026-10-13: 2 business days (Mon, Tue)
    count = business_days_between(date(2026, 10, 9), date(2026, 10, 13))
    assert count == 3

def test_business_days_between_with_holiday():
    """Test counting business days that include a holiday."""
    # From Friday 2026-10-16 to Wednesday 2026-10-21
    # Excludes: Saturday 10-17, Sunday 10-18, Monday 10-19 (holiday)
    # Includes: Tuesday 10-20, Wednesday 10-21 = 2 business days
    count = business_days_between(date(2026, 10, 16), date(2026, 10, 21))
    assert count == 3

def test_add_zero_business_days():
    """Adding zero business days returns the same date."""
    start = date(2026, 10, 5)
    result = add_business_days(start, 0)
    assert result == start

def test_business_days_same_date():
    """Counting business days from a date to itself returns 0."""
    d = date(2026, 10, 5)
    count = business_days_between(d, d)
    assert count == 0

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
