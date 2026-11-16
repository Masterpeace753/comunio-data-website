from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

SEASON = "2026/27"
MATCHDAYS = (
    (date(2026, 8, 28), date(2026, 8, 30)),
    (date(2026, 9, 4), date(2026, 9, 6)),
    (date(2026, 9, 11), date(2026, 9, 13)),
    (date(2026, 9, 18), date(2026, 9, 20)),
    (date(2026, 10, 9), date(2026, 10, 11)),
    (date(2026, 10, 16), date(2026, 10, 18)),
    (date(2026, 10, 23), date(2026, 10, 25)),
    (date(2026, 10, 30), date(2026, 11, 1)),
    (date(2026, 11, 6), date(2026, 11, 8)),
    (date(2026, 11, 20), date(2026, 11, 22)),
    (date(2026, 11, 27), date(2026, 11, 29)),
    (date(2026, 12, 4), date(2026, 12, 6)),
    (date(2026, 12, 11), date(2026, 12, 13)),
    (date(2026, 12, 18), date(2026, 12, 20)),
    (date(2027, 1, 8), date(2027, 1, 10)),
    (date(2027, 1, 12), date(2027, 1, 14)),
    (date(2027, 1, 15), date(2027, 1, 17)),
    (date(2027, 1, 22), date(2027, 1, 24)),
    (date(2027, 1, 29), date(2027, 1, 31)),
    (date(2027, 2, 5), date(2027, 2, 7)),
    (date(2027, 2, 12), date(2027, 2, 14)),
    (date(2027, 2, 19), date(2027, 2, 21)),
    (date(2027, 2, 26), date(2027, 2, 28)),
    (date(2027, 3, 2), date(2027, 3, 4)),
    (date(2027, 3, 5), date(2027, 3, 7)),
    (date(2027, 3, 12), date(2027, 3, 14)),
    (date(2027, 3, 19), date(2027, 3, 21)),
    (date(2027, 4, 2), date(2027, 4, 4)),
    (date(2027, 4, 9), date(2027, 4, 11)),
    (date(2027, 4, 16), date(2027, 4, 18)),
    (date(2027, 4, 23), date(2027, 4, 25)),
    (date(2027, 5, 7), date(2027, 5, 9)),
    (date(2027, 5, 14), date(2027, 5, 16)),
    (date(2027, 5, 22), date(2027, 5, 22)),
)


def safe_capture_date(start: datetime, end: datetime) -> date | None:
    # German local time is at most two hours ahead of UTC. Exclude ambiguous
    # late-UTC captures rather than guessing which calendar day they belong to.
    start = start.astimezone(UTC)
    end = end.astimezone(UTC)
    if start > end:
        return None
    day = start.date()
    if (start + timedelta(hours=2)).date() != day or end.date() != day or (end + timedelta(hours=2)).date() != day:
        return None
    return day


def matchday_for_capture(start: datetime, end: datetime, run_type: str) -> int | None:
    today = safe_capture_date(start, end)
    if today is None:
        return None
    for index, (_, matchday_end) in enumerate(MATCHDAYS):
        next_start = MATCHDAYS[index + 1][0] if index + 1 < len(MATCHDAYS) else matchday_end + timedelta(days=8)
        if matchday_end < today < next_start:
            return index + 1
        if today == next_start == matchday_end + timedelta(days=1) and run_type == "scheduled":
            start_utc = start.astimezone(UTC)
            end_utc = end.astimezone(UTC)
            if start_utc.hour == 6 and end_utc.hour == 6:
                return index + 1
    return None
