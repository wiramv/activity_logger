"""Ekspor kegiatan ke CSV, Markdown, dan JSON (teks siap simpan)."""

from __future__ import annotations

import csv
import io
import json
import os
from collections import OrderedDict
from datetime import date
from typing import Dict, Iterable, List, Optional, Sequence

from . import timeutil
from .models import Activity

CSV_HEADERS = ("No", "Tanggal", "Hari", "Jam", "Kegiatan", "Status", "Timestamp", "ID")


# --------------------------------------------------------------------------- #
# CSV
# --------------------------------------------------------------------------- #
def csv_text(items: Sequence[Activity]) -> str:
    """CSV dengan header Indonesia, urut dari yang paling lama."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(CSV_HEADERS)
    for number, item in enumerate(sorted(items, key=lambda act: act.ts), start=1):
        writer.writerow(
            (
                number,
                timeutil.fmt_date_numeric(item.date),
                item.day_name,
                item.clock(seconds=True),
                item.text,
                item.status_label,
                timeutil.fmt_ts(item.ts),
                item.id,
            )
        )
    return buffer.getvalue()


def csv_daily_summary(items: Sequence[Activity]) -> str:
    """CSV ringkasan per hari (tanggal, hari, jumlah kegiatan)."""
    counts = daily_counts(items)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(("Tanggal", "Hari", "Jumlah Kegiatan"))
    for day in sorted(counts):
        writer.writerow((timeutil.fmt_date_numeric(day), timeutil.day_name(day), counts[day]))
    return buffer.getvalue()


def daily_counts(items: Iterable[Activity]) -> Dict[date, int]:
    counts: Dict[date, int] = {}
    for item in items:
        counts[item.date] = counts.get(item.date, 0) + 1
    return counts


# --------------------------------------------------------------------------- #
# Markdown
# --------------------------------------------------------------------------- #
def markdown_document(
    items: Sequence[Activity],
    title: str = "Catatan Kegiatan",
    subtitle: Optional[str] = None,
    include_summary: bool = True,
) -> str:
    """Dokumen Markdown lengkap (judul, ringkasan, tabel kegiatan)."""
    ordered = sorted(items, key=lambda act: act.ts)
    lines: List[str] = ["# {}".format(title), ""]
    if subtitle:
        lines += ["_{}_".format(subtitle), ""]

    if include_summary:
        days = daily_counts(ordered)
        total = len(ordered)
        lines += [
            "**Total kegiatan:** {}  ".format(total),
            "**Hari aktif:** {}  ".format(len(days)),
            "**Rata-rata per hari aktif:** {:.1f}  ".format(
                (total / len(days)) if days else 0.0
            ),
            "",
        ]

    if not ordered:
        lines += ["_Belum ada kegiatan pada rentang ini._", ""]
        return "\n".join(lines) + "\n"

    lines += [
        "| Tanggal | Hari | Jam | Kegiatan | Status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in ordered:
        lines.append(
            "| {} | {} | {} | {} | {} |".format(
                timeutil.fmt_date_numeric(item.date),
                item.day_name,
                item.clock(),
                _escape_cell(item.text),
                item.status_label,
            )
        )
    lines.append("")
    return "\n".join(lines)


def markdown_by_month(items: Sequence[Activity]) -> "OrderedDict[str, str]":
    """Kelompokkan Markdown per bulan (dipakai untuk cermin ``YYYY-MM.md``)."""
    grouped: Dict[str, List[Activity]] = {}
    for item in items:
        grouped.setdefault(item.month_key, []).append(item)
    result: "OrderedDict[str, str]" = OrderedDict()
    for key in sorted(grouped):
        year, month = (int(part) for part in key.split("-"))
        chunk = grouped[key]
        title = "Kegiatan {}".format(timeutil.month_label(year, month))
        result[key] = _month_markdown(chunk, title, year, month)
    return result


def _month_markdown(items: Sequence[Activity], title: str, year: int, month: int) -> str:
    grouped: "OrderedDict[date, List[Activity]]" = OrderedDict()
    for item in sorted(items, key=lambda act: act.ts):
        grouped.setdefault(item.date, []).append(item)

    lines: List[str] = ["# {}".format(title), ""]
    lines.append(
        "> Total **{}** kegiatan pada **{}**.".format(
            len(items), timeutil.month_label(year, month)
        )
    )
    lines.append("")
    for day, entries in grouped.items():
        lines.append(
            "## {} — {} ({})".format(
                timeutil.fmt_date_indonesian(day), timeutil.day_name(day), len(entries)
            )
        )
        lines.append("")
        for entry in entries:
            mark = "x" if entry.done else " "
            lines.append("- [{}] `{}` {}".format(mark, entry.clock(), entry.text))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _escape_cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


# --------------------------------------------------------------------------- #
# JSON
# --------------------------------------------------------------------------- #
def json_text(items: Sequence[Activity], pretty: bool = True) -> str:
    payload = [item.to_dict() for item in sorted(items, key=lambda act: act.ts)]
    if pretty:
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


# --------------------------------------------------------------------------- #
# Nama file & penulisan
# --------------------------------------------------------------------------- #
def default_filename(kind: str, extension: str, slug: str) -> str:
    """``kegiatan-2026-10.csv`` — semua karakter aman untuk semua OS."""
    safe = "".join(ch if (ch.isalnum() or ch in "-_") else "-" for ch in slug)
    while "--" in safe:
        safe = safe.replace("--", "-")
    safe = safe.strip("-_") or "semua"
    return "kegiatan-{}.{}".format(safe, extension)


def write_text_file(path: str, content: str, excel_friendly: bool = False) -> str:
    """Tulis teks ke file; CSV diberi BOM agar rapi saat dibuka di Excel."""
    folder = os.path.dirname(os.path.abspath(path))
    if folder:
        os.makedirs(folder, exist_ok=True)
    encoding = "utf-8-sig" if excel_friendly else "utf-8"
    with open(path, "w", encoding=encoding, newline="") as handle:
        handle.write(content)
    return path


def build_export(
    kind: str,
    items: Sequence[Activity],
    title: str = "Catatan Kegiatan",
    subtitle: Optional[str] = None,
) -> str:
    """Kembalikan isi file sesuai ``kind``: ``csv`` / ``md`` / ``json``."""
    kind = (kind or "").lower().strip()
    if kind == "csv":
        return csv_text(items)
    if kind == "md":
        return markdown_document(items, title=title, subtitle=subtitle)
    if kind == "json":
        return json_text(items)
    raise ValueError("Format ekspor tidak dikenal: {}".format(kind))


EXTENSIONS = {"csv": "csv", "md": "md", "json": "json"}
