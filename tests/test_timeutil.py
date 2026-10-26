"""Tes helper tanggal/waktu."""

from datetime import date, datetime, timedelta

from activity_logger.core import timeutil


def test_fmt_and_parse_roundtrip():
    moment = datetime(2026, 10, 26, 6, 45, 12)
    text = timeutil.fmt_ts(moment)
    assert text == "2026-10-26 06:45:12"
    assert timeutil.parse_ts(text) == moment


def test_parse_ts_variants():
    expected = datetime(2026, 10, 26, 6, 45)
    for raw in (
        "2026-10-26 06:45:00",
        "2026-10-26T06:45:00",
        "2026-10-26 06:45",
        "2026/10/26 06:45:00",
        "26-10-2026 06:45:00",
    ):
        assert timeutil.parse_ts(raw) == expected, raw


def test_parse_ts_handles_timezone_suffix():
    parsed = timeutil.parse_ts("2026-10-26T06:45:00Z")
    assert parsed is not None
    assert parsed.year == 2026


def test_parse_ts_invalid():
    assert timeutil.parse_ts("") is None
    assert timeutil.parse_ts("bukan tanggal") is None
    assert timeutil.parse_ts(None) is None


def test_parse_date_accepts_date_and_string():
    assert timeutil.parse_date("2026-10-26") == date(2026, 10, 26)
    assert timeutil.parse_date(date(2026, 10, 26)) == date(2026, 10, 26)


def test_labels():
    day = date(2026, 10, 26)
    assert timeutil.day_name(day) == "Senin"
    assert timeutil.month_name(10) == "Oktober"
    assert timeutil.fmt_date_indonesian(day) == "26 Oktober 2026"
    assert timeutil.fmt_date_indonesian(day, with_day=True) == "Senin, 26 Oktober 2026"
    assert timeutil.fmt_date_short(day) == "26 Okt 2026"
    assert timeutil.month_label(2026, 10) == "Oktober 2026"
    assert timeutil.month_key(day) == "2026-10"


def test_bounds():
    start, end = timeutil.day_bounds(date(2026, 10, 26))
    assert start == datetime(2026, 10, 26)
    assert end == datetime(2026, 10, 27)

    start, end = timeutil.month_bounds(2026, 12)
    assert start == datetime(2026, 12, 1)
    assert end == datetime(2027, 1, 1)


def test_week_bounds_starts_monday():
    # 26 Oktober 2026 adalah Senin
    start, end = timeutil.week_bounds(date(2026, 10, 26))
    assert start == date(2026, 10, 26)
    assert end == date(2026, 11, 1)
    start, _ = timeutil.week_bounds(date(2026, 11, 1))  # Minggu
    assert start == date(2026, 10, 26)


def test_shift_month():
    assert timeutil.shift_month(2026, 12, 1) == (2027, 1)
    assert timeutil.shift_month(2026, 1, -1) == (2025, 12)
    assert timeutil.shift_month(2026, 10, 3) == (2027, 1)


def test_date_range_and_iter_days():
    days = timeutil.date_range(date(2026, 10, 1), date(2026, 10, 5))
    assert len(days) == 5
    assert days[0] == date(2026, 10, 1)
    assert days[-1] == date(2026, 10, 5)
    assert list(timeutil.iter_days(date(2026, 10, 5), date(2026, 10, 1)))[0] == date(2026, 10, 1)


def test_humanize():
    reference = datetime(2026, 10, 26, 12, 0, 0)
    assert timeutil.humanize(reference - timedelta(seconds=20), reference) == "baru saja"
    assert timeutil.humanize(reference - timedelta(minutes=5), reference) == "5 menit lalu"
    assert timeutil.humanize(reference - timedelta(hours=2), reference) == "2 jam lalu"
    assert timeutil.humanize(reference - timedelta(days=1), reference) == "kemarin"
    assert timeutil.humanize(reference - timedelta(days=4), reference) == "22 Okt 2026"


def test_parse_month_key():
    assert timeutil.parse_month_key("2026-10") == (2026, 10)
    assert timeutil.parse_month_key("2026-13") is None
    assert timeutil.parse_month_key("bukan") is None
