from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Optional


@dataclass
class Trip:
    """
    Represents a trip outside the UK.

    start: date you LEFT the UK
    end:   date you RETURNED to the UK
    note:  optional label / comment (e.g. "Xmas in Italy")

    Home Office rule: only whole days away count as absences.
    Departure and arrival days do NOT count.
    """
    start: date
    end: date
    note: str = ""

    def __post_init__(self):
        if self.end < self.start:
            raise ValueError("Trip end date cannot be before start date.")

    def full_absence_days(self) -> int:
        """
        Number of full absence days for this trip, i.e.
        days between (start + 1) and (end - 1), inclusive.
        """
        abs_start = self.start + timedelta(days=1)
        abs_end = self.end - timedelta(days=1)
        if abs_end < abs_start:
            return 0
        return (abs_end - abs_start).days + 1


def _overlap(a_start: date, a_end: date, b_start: date, b_end: date) -> Optional[tuple[date, date]]:
    """Return overlapping date range [start, end] inclusive, else None."""
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    if start > end:
        return None
    return start, end


def count_absent_days(trips: List[Trip], window_start: date, window_end: date) -> int:
    """
    Count full absence days within [window_start, window_end] inclusive.
    Following Home Office guidance:
    - Absence days = (start + 1) ... (end - 1)
    - If start+1 > end-1 → no full days abroad.
    """
    if window_end < window_start:
        return 0

    total = 0
    for trip in trips:
        trip_abs_start = trip.start + timedelta(days=1)
        trip_abs_end = trip.end - timedelta(days=1)

        if trip_abs_end < trip_abs_start:
            continue  # no full absence days

        overlap = _overlap(window_start, window_end, trip_abs_start, trip_abs_end)
        if overlap:
            o_start, o_end = overlap
            total += (o_end - o_start).days + 1

    return total


def is_full_absence_day(trips: List[Trip], d: date) -> bool:
    """Return True if d is a full absence day for any trip."""
    for trip in trips:
        abs_start = trip.start + timedelta(days=1)
        abs_end = trip.end - timedelta(days=1)
        if abs_start <= d <= abs_end:
            return True
    return False


@dataclass
class CandidateCheckResult:
    candidate_date: date
    days_12_months: int
    days_5_years: int
    presence_date_5y: date
    present_on_presence_date: bool
    meets_12m_rule: bool
    meets_5y_rule: bool
    fully_eligible: bool


def check_candidate_date(
    trips: List[Trip],
    candidate_date: date,
    max_12_month_absences: int = 90,
    max_5_year_absences: int = 450,
) -> CandidateCheckResult:
    """
    Check eligibility rules for one candidate application date:
    - ≤ 90 days in last 12 months
    - ≤ 450 days in last 5 years
    - physically present on the Home Office "5 years ago" test date

    Home Office example (Guide AN, Oct 2025):
    If application received on 05/01/2022, you should have been present
    on 06/01/2017. That corresponds to:

        presence_date = candidate_date - 5 years + 1 day
    """

    # 12-month window: [candidate_date - 1y, candidate_date - 1 day]
    start_12m = candidate_date - relativedelta(years=1)
    end_12m = candidate_date - timedelta(days=1)

    # 5-year window for absences: [candidate_date - 5y, candidate_date - 1 day]
    start_5y = candidate_date - relativedelta(years=5)
    end_5y = candidate_date - timedelta(days=1)

    days_12m = count_absent_days(trips, start_12m, end_12m)
    days_5y = count_absent_days(trips, start_5y, end_5y)

    # Presence date as per Home Office example: -5 years + 1 day
    presence_date = start_5y + timedelta(days=1)

    present_on_presence_date = not is_full_absence_day(trips, presence_date)

    meets_12m = days_12m <= max_12_month_absences
    meets_5y = days_5y <= max_5_year_absences

    fully_eligible = meets_12m and meets_5y and present_on_presence_date

    return CandidateCheckResult(
        candidate_date=candidate_date,
        days_12_months=days_12m,
        days_5_years=days_5y,
        presence_date_5y=presence_date,
        present_on_presence_date=present_on_presence_date,
        meets_12m_rule=meets_12m,
        meets_5y_rule=meets_5y,
        fully_eligible=fully_eligible,
    )


def find_earliest_application_date(
    trips: List[Trip],
    today: date,
    search_years: int = 10,
    max_12_month_absences: int = 90,
    max_5_year_absences: int = 450,
) -> Optional[CandidateCheckResult]:
    """
    Scan forward day-by-day from 'today' up to 'today + search_years'
    to find the first day that meets:
    - 12-month rule
    - 5-year rule
    - presence on the Home Office "5 years ago" test date
    """
    max_date = today + relativedelta(years=search_years)
    current = today

    while current <= max_date:
        result = check_candidate_date(
            trips,
            current,
            max_12_month_absences,
            max_5_year_absences,
        )
        if result.fully_eligible:
            return result

        current += timedelta(days=1)

    return None
