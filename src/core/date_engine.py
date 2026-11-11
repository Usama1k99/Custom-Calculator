"""
Date Calculation Engine with Exhaustive Edge-Case Handling.
Handles leap years, variable month lengths, inverted date ranges,
working/business days, and multi-year arithmetic accurately.
"""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Tuple


@dataclass
class DateDifferenceResult:
    years: int
    months: int
    weeks: int
    days: int
    total_days: int
    working_days: int
    weekend_days: int
    is_same_date: bool
    is_inverted: bool
    formatted_summary: str
    total_days_summary: str
    business_summary: str


def clamp_day(year: int, month: int, day: int) -> int:
    """Clamps day to the maximum valid day in that month/year (e.g., Feb 29 on non-leap years -> Feb 28)."""
    max_days = calendar.monthrange(year, month)[1]
    return min(day, max_days)


def add_months(d: date, delta_months: int) -> date:
    """Safely adds or subtracts months, handling month/year boundaries and clamping within valid years."""
    total_m = (d.year * 12 + (d.month - 1)) + delta_months
    new_year = total_m // 12
    if new_year > 9999:
        return date(9999, 12, 31)
    if new_year < 1:
        return date(1, 1, 1)
    new_month = (total_m % 12) + 1
    new_day = clamp_day(new_year, new_month, d.day)
    return date(new_year, new_month, new_day)


def add_years(d: date, delta_years: int) -> date:
    """Safely adds or subtracts years, handling leap year Feb 29 clamping and year bounds [1..9999]."""
    new_year = d.year + delta_years
    if new_year > 9999:
        return date(9999, 12, 31)
    if new_year < 1:
        return date(1, 1, 1)
    new_day = clamp_day(new_year, d.month, d.day)
    return date(new_year, d.month, new_day)


def count_business_days(d1: date, d2: date) -> Tuple[int, int]:
    """
    Counts working days (Monday-Friday) and weekend days (Saturday-Sunday)
    between two dates in O(1) time complexity.
    """
    if d1 == d2:
        return 0, 0
    start, end = (d2, d1) if d1 > d2 else (d1, d2)
    total_days = (end - start).days

    full_weeks = total_days // 7
    working_days = full_weeks * 5
    curr = start + timedelta(days=full_weeks * 7 + 1)
    while curr <= end:
        if curr.weekday() < 5:  # Monday is 0, Friday is 4
            working_days += 1
        curr += timedelta(days=1)

    weekend_days = total_days - working_days
    return working_days, weekend_days


def calculate_date_difference(d1: date, d2: date) -> DateDifferenceResult:
    """
    Computes exact difference between two dates broken down into:
    Years, Months, Weeks, Days, and Total Days.
    Includes business/working days calculation and inverted range detection.
    """
    if d1 == d2:
        return DateDifferenceResult(
            years=0,
            months=0,
            weeks=0,
            days=0,
            total_days=0,
            working_days=0,
            weekend_days=0,
            is_same_date=True,
            is_inverted=False,
            formatted_summary="Same date",
            total_days_summary="0 days",
            business_summary="0 working days"
        )

    is_inverted = d1 > d2
    start, end = (d2, d1) if is_inverted else (d1, d2)
    total_days = (end - start).days

    # Calculate years
    curr = start
    years = 0
    while curr.year < end.year:
        nxt = add_years(curr, 1)
        if nxt <= end and nxt > curr:
            curr = nxt
            years += 1
        else:
            break

    # Calculate months
    months = 0
    while (curr.year, curr.month) < (end.year, end.month):
        nxt = add_months(curr, 1)
        if nxt <= end and nxt > curr:
            curr = nxt
            months += 1
        else:
            break

    # Remaining days
    rem_days = (end - curr).days
    weeks = 0
    days = 0

    parts = []
    if years > 0:
        parts.append(f"{years} year" + ("s" if years > 1 else ""))
    if months > 0:
        parts.append(f"{months} month" + ("s" if months > 1 else ""))

    if years == 0 and months == 0:
        weeks = rem_days // 7
        days = rem_days % 7
        if weeks > 0:
            parts.append(f"{weeks} week" + ("s" if weeks > 1 else ""))
        if days > 0:
            parts.append(f"{days} day" + ("s" if days > 1 else ""))
    else:
        if rem_days >= 7:
            weeks = rem_days // 7
            days = rem_days % 7
            parts.append(f"{weeks} week" + ("s" if weeks > 1 else ""))
            if days > 0:
                parts.append(f"{days} day" + ("s" if days > 1 else ""))
        elif rem_days > 0:
            days = rem_days
            parts.append(f"{days} day" + ("s" if days > 1 else ""))

    summary = ", ".join(parts) if parts else "Same date"
    if is_inverted:
        summary += " earlier"

    total_str = f"{total_days} day" + ("s" if total_days != 1 else "")
    if is_inverted:
        total_str += " earlier"

    work_days, wknd_days = count_business_days(start, end)
    biz_str = f"{work_days} working days ({wknd_days} weekend days)"

    return DateDifferenceResult(
        years=years,
        months=months,
        weeks=weeks,
        days=days,
        total_days=total_days,
        working_days=work_days,
        weekend_days=wknd_days,
        is_same_date=False,
        is_inverted=is_inverted,
        formatted_summary=summary,
        total_days_summary=total_str,
        business_summary=biz_str
    )


MIN_DATE = date(1900, 1, 1)
MAX_DATE = date(9999, 12, 31)


def add_subtract_duration(start: date, years: int, months: int, days: int, add: bool = True) -> date:
    """
    Adds or subtracts years, months, and days from a given date.
    Maintains month-end clamping, leap-year rules, and clamps within [1900-01-01, 9999-12-31]
    to prevent Year out of range errors and calendar overflows.
    """
    sign = 1 if add else -1
    target_year = start.year + sign * years
    if target_year < 1900:
        return MIN_DATE
    if target_year > 9999:
        return MAX_DATE
    
    d = add_years(start, sign * years)
    
    total_m = (d.year * 12 + (d.month - 1)) + sign * months
    ny = total_m // 12
    if ny < 1900:
        return MIN_DATE
    if ny > 9999:
        return MAX_DATE
    
    d = add_months(d, sign * months)
    
    try:
        d = d + timedelta(days=sign * days)
    except (OverflowError, ValueError):
        return MAX_DATE if sign > 0 else MIN_DATE
        
    if d < MIN_DATE:
        return MIN_DATE
    if d > MAX_DATE:
        return MAX_DATE
    return d

