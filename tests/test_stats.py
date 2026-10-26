"""Tes filter periode, ringkasan, dan data grafik."""

from datetime import date, datetime

from activity_logger.core import stats
from activity_logger.core.models import Activity


def act(text, when, done=False):
    return Activity(text=text, ts=when, done=done)


REFERENCE = date(2026, 10, 26)  # Senin


def sample():
    return [
        act("A", datetime(2026, 10, 26, 6, 45)),
        act("B", datetime(2026, 10, 26, 7, 30)),
        act("C", datetime(2026, 10, 25, 22, 40)),
        act("D", datetime(2026, 10, 20, 15, 0), done=True),
        act("E", datetime(2026, 9, 30, 9, 0)),
        act("F", datetime(2026, 1, 2, 9, 0)),
    ]


def test_resolve_period_today():
    period = stats.resolve_period("today", reference=REFERENCE)
    assert period.start_date == REFERENCE
    assert period.end_date == REFERENCE
    assert "Hari ini" in period.label
    assert period.slug == "2026-10-26"


def test_resolve_period_month_is_full_calendar_month():
    period = stats.resolve_period("month", reference=REFERENCE)
    assert period.start_date == date(2026, 10, 1)
    assert period.end_date == date(2026, 10, 31)
    assert period.label == "Oktober 2026"
    assert period.slug == "2026-10"


def test_resolve_period_week_and_last30():
    week = stats.resolve_period("week", reference=REFERENCE)
    assert week.start_date == date(2026, 10, 26)
    assert week.end_date == date(2026, 11, 1)

    last30 = stats.resolve_period("last30", reference=REFERENCE)
    assert last30.start_date == date(2026, 9, 27)
    assert last30.end_date == REFERENCE


def test_resolve_period_custom_swaps_when_reversed():
    period = stats.resolve_period(
        "custom", start=date(2026, 10, 20), end=date(2026, 10, 10), reference=REFERENCE
    )
    assert period.start_date == date(2026, 10, 10)
    assert period.end_date == date(2026, 10, 20)


def test_resolve_period_all_has_no_bounds():
    period = stats.resolve_period("all", reference=REFERENCE)
    assert period.start is None and period.end is None
    assert period.contains(datetime(1999, 1, 1))


def test_filter_by_period_and_query():
    items = sample()
    month = stats.resolve_period("month", reference=REFERENCE)
    # filter selalu mengembalikan urutan terbaru dulu
    assert [item.text for item in stats.filter_activities(items, period=month)] == ["B", "A", "C", "D"]

    found = stats.filter_activities(items, period=stats.resolve_period("all"), query="d")
    assert [item.text for item in found] == ["D"]

    done = stats.filter_activities(items, period=stats.resolve_period("all"), status="done")
    assert [item.text for item in done] == ["D"]
    pending = stats.filter_activities(items, period=stats.resolve_period("all"), status="pending")
    assert len(pending) == 5


def test_summarize_counts():
    month = stats.resolve_period("month", reference=REFERENCE)
    items = stats.filter_activities(sample(), period=month)
    summary = stats.summarize(items, period=month, reference=REFERENCE)
    assert summary.total == 4
    assert summary.today == 2
    assert summary.active_days == 3
    assert summary.range_days == 31
    assert round(summary.avg_per_day, 2) == 0.13
    assert summary.best_day == date(2026, 10, 26)
    assert summary.best_day_count == 2
    assert summary.busiest_hour == 9 or summary.busiest_hour in range(24)


def test_current_streak_allows_gap_today():
    per_day = {date(2026, 10, 24): 1, date(2026, 10, 25): 2}
    assert stats.current_streak(per_day, REFERENCE) == 2

    per_day[date(2026, 10, 26)] = 1
    assert stats.current_streak(per_day, REFERENCE) == 3

    per_day.pop(date(2026, 10, 25))
    assert stats.current_streak(per_day, REFERENCE) == 1


def test_longest_streak():
    per_day = {
        date(2026, 10, 1): 1,
        date(2026, 10, 2): 1,
        date(2026, 10, 3): 1,
        date(2026, 10, 10): 1,
    }
    assert stats.longest_streak(per_day) == 3
    assert stats.longest_streak({}) == 0


def test_daily_series_includes_zero_days():
    items = sample()
    series = stats.daily_series(items, date(2026, 10, 24), date(2026, 10, 27))
    assert series == [
        (date(2026, 10, 24), 0),
        (date(2026, 10, 25), 1),
        (date(2026, 10, 26), 2),
        (date(2026, 10, 27), 0),
    ]


def test_chart_series_limits_long_ranges():
    month = stats.resolve_period("month", reference=REFERENCE)
    series = stats.chart_series_for_period(sample(), month, reference=REFERENCE)
    assert len(series) == 31


def test_monthly_totals_and_grouping():
    items = sample()
    assert stats.monthly_totals(items) == [("2026-01", 1), ("2026-09", 1), ("2026-10", 4)]
    grouped = stats.group_by_day(items)
    assert grouped[0][0] == date(2026, 10, 26)
    assert [item.text for item in grouped[0][1]] == ["B", "A"]


def test_greeting():
    assert stats.greeting(datetime(2026, 10, 26, 8)) == "Selamat pagi"
    assert stats.greeting(datetime(2026, 10, 26, 13)) == "Selamat siang"
    assert stats.greeting(datetime(2026, 10, 26, 17)) == "Selamat sore"
    assert stats.greeting(datetime(2026, 10, 26, 21)) == "Selamat malam"
