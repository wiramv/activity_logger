"""Helper tanggal & waktu (locale Indonesia, tanpa dependensi eksternal).

Semua timestamp disimpan sebagai string ``YYYY-MM-DD HH:MM:SS`` dalam waktu
lokal mesin pengguna. Modul ini adalah satu-satunya tempat yang mengetahui
format tersebut sehingga bagian aplikasi lain cukup bekerja dengan
``datetime``.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterable, List, Optional, Tuple

TS_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

ID_DAYS = ("Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu")
ID_DAYS_SHORT = ("Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min")
ID_MONTHS = (
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
)
ID_MONTHS_SHORT = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "Mei",
    "Jun",
    "Jul",
    "Agu",
    "Sep",
    "Okt",
    "Nov",
    "Des",
)


# --------------------------------------------------------------------------- #
# Waktu sekarang
# --------------------------------------------------------------------------- #
def now() -> datetime:
    """Waktu lokal sekarang, dibulatkan ke detik (tanpa mikrodetik)."""
    return datetime.now().replace(microsecond=0)


def today() -> date:
    return now().date()


# --------------------------------------------------------------------------- #
# Format & parsing
# --------------------------------------------------------------------------- #
def fmt_ts(moment: datetime) -> str:
    """``datetime`` -> ``YYYY-MM-DD HH:MM:SS``."""
    return moment.strftime(TS_FORMAT)


def parse_ts(value: object) -> Optional[datetime]:
    """Parse timestamp yang toleran terhadap beberapa variasi format.

    Menerima ``YYYY-MM-DD HH:MM:SS``, ``YYYY-MM-DDTHH:MM:SS``, dengan/tanpa
    zona waktu, tanpa detik, atau hanya tanggal. Mengembalikan ``None`` bila
    benar-benar tidak bisa dibaca (baris rusak tidak boleh mematikan app).
    """
    if isinstance(value, datetime):
        return value.replace(microsecond=0, tzinfo=None)
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    # Python 3.11+ menerima "Z", tapi kita normalkan agar aman di 3.9/3.10.
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        for pattern in (
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y/%m/%d",
            "%d-%m-%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
        ):
            try:
                parsed = datetime.strptime(text, pattern)
                break
            except ValueError:
                continue
        else:
            return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed.replace(microsecond=0)


def parse_date(value: object) -> Optional[date]:
    """Parse ``YYYY-MM-DD`` (atau beberapa variasi) menjadi ``date``."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = parse_ts(value)
    return parsed.date() if parsed else None


# --------------------------------------------------------------------------- #
# Label siap-tampil
# --------------------------------------------------------------------------- #
def day_name(moment: date) -> str:
    return ID_DAYS[moment.weekday()]


def day_name_short(moment: date) -> str:
    return ID_DAYS_SHORT[moment.weekday()]


def month_name(month: int) -> str:
    if 1 <= month <= 12:
        return ID_MONTHS[month - 1]
    return ""


def month_name_short(month: int) -> str:
    if 1 <= month <= 12:
        return ID_MONTHS_SHORT[month - 1]
    return ""


def fmt_date_indonesian(moment: date, with_day: bool = False) -> str:
    """``26 Oktober 2026`` (opsional dengan nama hari di depan)."""
    base = "{} {}".format(moment.day, month_name(moment.month))
    base = "{} {}".format(base, moment.year)
    if with_day:
        return "{} , {}".format(day_name(moment), base).replace(" ,", ",")
    return base


def fmt_date_short(moment: date) -> str:
    """``26 Okt 2026``."""
    return "{} {} {}".format(moment.day, month_name_short(moment.month), moment.year)


def fmt_date_numeric(moment: date) -> str:
    return moment.strftime(DATE_FORMAT)


def fmt_clock(moment: datetime, seconds: bool = False) -> str:
    return moment.strftime("%H:%M:%S" if seconds else "%H:%M")


def month_label(year: int, month: int) -> str:
    return "{} {}".format(month_name(month), year)


def month_key(moment: date) -> str:
    """``2026-10`` untuk pengelompokan per bulan."""
    return "{:04d}-{:02d}".format(moment.year, moment.month)


def humanize(moment: datetime, reference: Optional[datetime] = None) -> str:
    """``baru saja``, ``5 menit lalu``, ``2 jam lalu``, ``kemarin``, tanggal."""
    reference = reference or now()
    delta = (reference - moment).total_seconds()
    if delta < 0:
        return fmt_date_short(moment.date())
    if delta < 60:
        return "baru saja"
    if delta < 3600:
        return "{} menit lalu".format(int(delta // 60))
    if delta < 6 * 3600:
        return "{} jam lalu".format(int(delta // 3600))
    if is_same_day(moment.date(), reference.date()):
        return "hari ini"
    if is_same_day(moment.date(), reference.date() - timedelta(days=1)):
        return "kemarin"
    return fmt_date_short(moment.date())


# --------------------------------------------------------------------------- #
# Rentang tanggal
# --------------------------------------------------------------------------- #
def is_same_day(first: date, second: date) -> bool:
    return first == second


def day_bounds(moment: date) -> Tuple[datetime, datetime]:
    """(awal hari, awal hari setelahnya) — batas setengah terbuka."""
    start = datetime.combine(moment, time.min)
    return start, start + timedelta(days=1)


def month_bounds(year: int, month: int) -> Tuple[datetime, datetime]:
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end


def week_bounds(moment: date) -> Tuple[date, date]:
    """Senin–Minggu pada minggu yang sama."""
    start = moment - timedelta(days=moment.weekday())
    return start, start + timedelta(days=6)


def shift_month(year: int, month: int, delta: int) -> Tuple[int, int]:
    index = (year * 12 + (month - 1)) + delta
    return index // 12, index % 12 + 1


def date_range(start: date, end: date) -> List[date]:
    """Daftar tanggal inklusif dari ``start`` sampai ``end``."""
    if end < start:
        start, end = end, start
    total = (end - start).days
    return [start + timedelta(days=offset) for offset in range(total + 1)]


def last_days_end(moment: date, days: int) -> Tuple[date, date]:
    """Rentang ``days`` hari yang berakhir di ``moment`` (inklusif)."""
    days = max(1, int(days))
    return moment - timedelta(days=days - 1), moment


def seconds_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds()


def ensure_dirname(path: str) -> str:
    from os.path import dirname, expanduser

    folder = dirname(expanduser(path))
    return folder or "."


def parse_month_key(value: str) -> Optional[Tuple[int, int]]:
    """``2026-10`` -> ``(2026, 10)``."""
    try:
        year_text, month_text = str(value).strip().split("-")[:2]
        year, month = int(year_text), int(month_text)
    except (TypeError, ValueError):
        return None
    if 1 <= month <= 12 and 1970 <= year <= 9999:
        return year, month
    return None


# --------------------------------------------------------------------------- #
# Iterasi
# --------------------------------------------------------------------------- #
def iter_days(start: date, end: date) -> Iterable[date]:
    for current in date_range(start, end):
        yield current
