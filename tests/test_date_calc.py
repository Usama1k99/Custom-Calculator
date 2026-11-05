"""
Unit Tests for Date Calculation Engine.
Covers leap years, month boundaries, business days, and inverted dates.
"""

import unittest
from datetime import date
from src.core.date_engine import (
    clamp_day, add_months, add_years, count_business_days,
    calculate_date_difference, add_subtract_duration
)


class TestDateCalculationEngine(unittest.TestCase):
    def test_same_date(self):
        d = date(2026, 11, 5)
        res = calculate_date_difference(d, d)
        self.assertTrue(res.is_same_date)
        self.assertEqual(res.total_days, 0)
        self.assertEqual(res.formatted_summary, "Same date")

    def test_day_and_week_difference(self):
        d1 = date(2026, 1, 1)
        d2 = date(2026, 1, 24)
        res = calculate_date_difference(d1, d2)
        self.assertFalse(res.is_same_date)
        self.assertEqual(res.total_days, 23)
        self.assertEqual(res.formatted_summary, "3 weeks, 2 days")

    def test_multi_year_difference(self):
        d1 = date(2024, 1, 1)
        d2 = date(2026, 3, 10)
        res = calculate_date_difference(d1, d2)
        self.assertEqual(res.years, 2)
        self.assertEqual(res.months, 2)
        self.assertIn("2 years, 2 months", res.formatted_summary)

    def test_inverted_date_range(self):
        d1 = date(2026, 5, 20)
        d2 = date(2026, 5, 10)
        res = calculate_date_difference(d1, d2)
        self.assertTrue(res.is_inverted)
        self.assertEqual(res.total_days, 10)
        self.assertIn("earlier", res.formatted_summary)

    def test_leap_year_feb_29_handling(self):
        # 2024 is a leap year; 2025 is not.
        d = date(2024, 2, 29)
        plus_1_yr = add_years(d, 1)
        self.assertEqual(plus_1_yr, date(2025, 2, 28))

        plus_4_yr = add_years(d, 4)
        self.assertEqual(plus_4_yr, date(2028, 2, 29))

        plus_1_mo = add_months(d, 1)
        self.assertEqual(plus_1_mo, date(2024, 3, 29))

    def test_month_boundary_clamping(self):
        # Jan 31 + 1 month in non-leap year -> Feb 28
        d = date(2025, 1, 31)
        self.assertEqual(add_months(d, 1), date(2025, 2, 28))

        # March 31 - 1 month in leap year -> Feb 29
        d_leap = date(2024, 3, 31)
        self.assertEqual(add_months(d_leap, -1), date(2024, 2, 29))

    def test_add_subtract_duration(self):
        start = date(2026, 11, 5)
        # Add 1 year, 2 months, 10 days
        res_add = add_subtract_duration(start, years=1, months=2, days=10, add=True)
        self.assertEqual(res_add, date(2028, 1, 15))

        # Subtract 1 year, 1 month, 5 days
        res_sub = add_subtract_duration(start, years=1, months=1, days=5, add=False)
        self.assertEqual(res_sub, date(2025, 9, 30))

    def test_business_days_counting(self):
        # Friday Nov 6, 2026 to Monday Nov 9, 2026 -> 1 business day (Mon), 2 weekend days (Sat, Sun)
        d_fri = date(2026, 11, 6)
        d_mon = date(2026, 11, 9)
        work, wknd = count_business_days(d_fri, d_mon)
        self.assertEqual(work, 1)
        self.assertEqual(wknd, 2)


if __name__ == "__main__":
    unittest.main()

