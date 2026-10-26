"""Filter periode, ringkasan statistik, dan data grafik."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import timeutil
from .models import Activity

PERIODS = ("today", "week", "month", "last30", "all", "custom")

PERIOD_LABELS = {
    "today": "Hari ini",
    "week": "Minggu ini",
    "month": "Bulan ini",
    "last30": "30 hari",
    "all": "Semua",
    "custom": "Custom",
}


@dataclass
class Period:
    """Rentang waktu yang sudah terselesaikan (batas setengah terbuka)."""

    key: str
    start: Optional[datetime]
    end: Optional[datetime]
    label: str
    slug: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    def contains(self, moment: datetime) -> bool:
        if self.start is not None and moment < self.start:
            return False
        if self.end is not None and moment >= self.end:
            return False
        return True


@dataclass
class Summary:
    total: int = 0
    today: int = 0
    this_month: int = 0
    active_days: int = 0
    range_days: int = 0
    avg_per_day: float = 0.0
    current_streak: int = 0
    longest_streak: int = 0
    best_day: Optional[date] = None
    best_day_count: int = 0
    busiest_hour: Optional[int] = None
    busiest_hour_count: int = 0
    per_day: Dict[date, int] = field(default_factory=dict)
    per_hour: Dict[int, int] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Periode
# --------------------------------------------------------------------------- #
def resolve_period(
    key: str = "month",
    reference: Optional[date] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> Period:
    """Terjemahkan pilihan periode menjadi rentang tanggal konkret."""
    reference = reference or timeutil.today()
    key = key if key in PERIODS else "month"

    if key == "today":
        begin, finish = reference, reference
    elif key == "week":
        begin, finish = timeutil.week_bounds(reference)
    elif key == "month":
        begin = reference.replace(day=1)
        finish = _month_end(begin)
    elif key == "last30":
        begin, finish = timeutil.last_days_end(reference, 30)
    elif key == "custom":
        begin = start or reference.replace(day=1)
        finish = end or reference
        if finish < begin:
            begin, finish = finish, begin
    else:  # all
        return Period(key="all", start=None, end=None, label="Semua waktu", slug="semua")

    start_dt = datetime.combine(begin, datetime.min.time())
    end_dt = datetime.combine(finish + timedelta(days=1), datetime.min.time())
    label = _period_label(key, begin, finish)
    slug = _period_slug(key, begin, finish)
    return Period(
        key=key,
        start=start_dt,
        end=end_dt,
        label=label,
        slug=slug,
        start_date=begin,
        end_date=finish,
    )


def _month_end(first_day: date) -> date:
    year, month = first_day.year, first_day.month
    next_year, next_month = timeutil.shift_month(year, month, 1)
    return date(next_year, next_month, 1) - timedelta(days=1)


def _period_label(key: str, begin: date, finish: date) -> str:
    if key == "today":
        return "Hari ini, {}".format(timeutil.fmt_date_indonesian(begin))
    if key == "week":
        return "{} – {}".format(timeutil.fmt_date_short(begin), timeutil.fmt_date_short(finish))
    if key == "month":
        return timeutil.month_label(begin.year, begin.month)
    if key == "last30":
        return "{} – {}".format(timeutil.fmt_date_short(begin), timeutil.fmt_date_short(finish))
    if key == "custom":
        return "{} – {}".format(timeutil.fmt_date_short(begin), timeutil.fmt_date_short(finish))
    return "Semua waktu"


def _period_slug(key: str, begin: date, finish: date) -> str:
    if key == "today":
        return timeutil.month_key(begin) + "-" + begin.strftime("%d")
    if key == "month":
        return timeutil.month_key(begin)
    if key == "all":
        return "semua"
    return "{}_{}".format(begin.strftime("%Y%m%d"), finish.strftime("%Y%m%d"))


# --------------------------------------------------------------------------- #
# Filter
# --------------------------------------------------------------------------- #
def filter_activities(
    items: Iterable[Activity],
    period: Optional[Period] = None,
    query: str = "",
    status: Optional[str] = None,
) -> List[Activity]:
    """Saring berdasarkan periode, kata kunci, dan status.

    ``status``: ``None`` (semua), ``"done"``, atau ``"pending"``.
    """
    result: List[Activity] = []
    needle = (query or "").strip().lower()
    for item in items:
        if period is not None and not period.contains(item.ts):
            continue
        if status == "done" and not item.done:
            continue
        if status == "pending" and item.done:
            continue
        if needle and needle not in item.text.lower():
            continue
        result.append(item)
    result.sort(key=lambda act: act.ts, reverse=True)
    return result


# --------------------------------------------------------------------------- #
# Ringkasan
# --------------------------------------------------------------------------- #
def summarize(
    items: Sequence[Activity],
    period: Optional[Period] = None,
    reference: Optional[date] = None,
) -> Summary:
    reference = reference or timeutil.today()
    summary = Summary(total=len(items))
    for item in items:
        summary.per_day[item.date] = summary.per_day.get(item.date, 0) + 1
        summary.per_hour[item.ts.hour] = summary.per_hour.get(item.ts.hour, 0) + 1
        if item.date == reference:
            summary.today += 1
        if item.date.year == reference.year and item.date.month == reference.month:
            summary.this_month += 1

    if summary.per_day:
        best_day = max(sorted(summary.per_day), key=lambda day: summary.per_day[day])
        summary.best_day = best_day
        summary.best_day_count = summary.per_day[best_day]
    if summary.per_hour:
        busiest = max(sorted(summary.per_hour), key=lambda hour: summary.per_hour[hour])
        summary.busiest_hour = busiest
        summary.busiest_hour_count = summary.per_hour[busiest]

    summary.active_days = len(summary.per_day)
    if period is not None and period.start_date and period.end_date:
        summary.range_days = (period.end_date - period.start_date).days + 1
    elif summary.per_day:
        summary.range_days = (max(summary.per_day) - min(summary.per_day)).days + 1
    summary.avg_per_day = (
        summary.total / summary.range_days if summary.range_days > 0 else float(summary.total)
    )
    summary.current_streak = current_streak(summary.per_day, reference)
    summary.longest_streak = longest_streak(summary.per_day)
    return summary


def current_streak(per_day: Dict[date, int], reference: Optional[date] = None) -> int:
    """Jumlah hari berurutan yang ada kegiatannya, dihitung mundur dari hari ini."""
    reference = reference or timeutil.today()
    streak = 0
    cursor = reference
    if cursor not in per_day:
        cursor = cursor - timedelta(days=1)  # hari ini belum mencatat tidak memutus streak
    while cursor in per_day:
        streak += 1
        cursor = cursor - timedelta(days=1)
    return streak


def longest_streak(per_day: Dict[date, int]) -> int:
    if not per_day:
        return 0
    best = 0
    run = 0
    previous: Optional[date] = None
    for day in sorted(per_day):
        if previous is not None and (day - previous).days == 1:
            run += 1
        else:
            run = 1
        best = max(best, run)
        previous = day
    return best


# --------------------------------------------------------------------------- #
# Data grafik
# --------------------------------------------------------------------------- #
def daily_series(
    items: Sequence[Activity],
    start: date,
    end: date,
) -> List[Tuple[date, int]]:
    """Jumlah kegiatan per hari untuk setiap hari pada rentang (termasuk nol)."""
    counts: Dict[date, int] = {}
    for item in items:
        counts[item.date] = counts.get(item.date, 0) + 1
    return [(day, counts.get(day, 0)) for day in timeutil.date_range(start, end)]


def hourly_series(items: Sequence[Activity]) -> List[Tuple[int, int]]:
    counts = [0] * 24
    for item in items:
        counts[item.ts.hour] += 1
    return list(enumerate(counts))


def chart_series_for_period(
    items: Sequence[Activity],
    period: Period,
    reference: Optional[date] = None,
) -> List[Tuple[date, int]]:
    """Data grafik yang selalu "masuk akal" untuk periode apa pun."""
    reference = reference or timeutil.today()
    if period.start_date and period.end_date:
        span = (period.end_date - period.start_date).days + 1
        if span <= 62:
            return daily_series(items, period.start_date, period.end_date)
    # Rentang panjang: tampilkan 30 hari terakhir yang ada datanya.
    if items:
        last_day = max(item.date for item in items)
    else:
        last_day = reference
    start, end = timeutil.last_days_end(last_day, 30)
    return daily_series(items, start, end)


def monthly_totals(items: Sequence[Activity]) -> List[Tuple[str, int]]:
    """``[("2026-10", 42), ...]`` urut dari bulan terlama."""
    counts: Dict[str, int] = {}
    for item in items:
        counts[item.month_key] = counts.get(item.month_key, 0) + 1
    return sorted(counts.items())


def available_months(items: Sequence[Activity]) -> List[str]:
    return [key for key, _ in monthly_totals(items)]


def group_by_day(items: Sequence[Activity]) -> List[Tuple[date, List[Activity]]]:
    """Kelompokkan (terbaru dulu) untuk tampilan bertanggal."""
    grouped: Dict[date, List[Activity]] = {}
    for item in items:
        grouped.setdefault(item.date, []).append(item)
    result = []
    for day in sorted(grouped, reverse=True):
        entries = sorted(grouped[day], key=lambda act: act.ts, reverse=True)
        result.append((day, entries))
    return result


def greeting(moment: Optional[datetime] = None) -> str:
    moment = moment or timeutil.now()
    hour = moment.hour
    if hour < 11:
        return "Selamat pagi"
    if hour < 15:
        return "Selamat siang"
    if hour < 18:
        return "Selamat sore"
    return "Selamat malam"
