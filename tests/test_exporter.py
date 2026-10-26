"""Tes ekspor CSV / Markdown / JSON."""

import csv
import io
import json
from datetime import datetime

from activity_logger.core.exporter import (
    build_export,
    csv_text,
    default_filename,
    json_text,
    markdown_by_month,
    markdown_document,
    write_text_file,
)
from activity_logger.core.models import Activity


def sample():
    return [
        Activity(text="Mengerjakan desain dashboard", ts=datetime(2026, 10, 26, 6, 45)),
        Activity(text="Olahraga pagi", ts=datetime(2026, 10, 26, 7, 30), done=True),
        Activity(text="Rapat | review, budget", ts=datetime(2026, 10, 25, 14, 30)),
    ]


def test_csv_has_headers_and_rows():
    rows = list(csv.reader(io.StringIO(csv_text(sample()))))
    assert len(rows) == 4
    assert rows[0][:6] == ["No", "Tanggal", "Hari", "Jam", "Kegiatan", "Status"]
    # urut dari yang paling lama
    assert rows[1][1] == "2026-10-25"
    assert rows[1][2] == "Minggu"
    assert rows[1][4] == "Rapat | review, budget"
    assert rows[3][2] == "Senin"


def test_csv_marks_done_status():
    rows = list(csv.reader(io.StringIO(csv_text(sample()))))
    statuses = {row[4]: row[5] for row in rows[1:]}
    assert statuses["Olahraga pagi"] == "Selesai"
    assert statuses["Mengerjakan desain dashboard"] == "Belum"


def test_csv_crlf_line_endings():
    assert csv_text(sample()).endswith("\r\n")


def test_markdown_document_contains_table_and_summary():
    text = markdown_document(sample(), title="Catatan Kegiatan", subtitle="Oktober 2026")
    assert text.startswith("# Catatan Kegiatan")
    assert "_Oktober 2026_" in text
    assert "**Total kegiatan:** 3" in text
    assert "| 2026-10-26 | Senin | 06:45 | Mengerjakan desain dashboard | Belum |" in text


def test_markdown_escapes_pipes():
    text = markdown_document([sample()[2]])
    assert "Rapat \\| review, budget" in text


def test_markdown_empty():
    text = markdown_document([])
    assert "Belum ada kegiatan" in text


def test_markdown_by_month_groups():
    chunks = markdown_by_month(sample())
    assert list(chunks) == ["2026-10"]
    assert "# Kegiatan Oktober 2026" in chunks["2026-10"]
    assert "- [x] `07:30` Olahraga pagi" in chunks["2026-10"]


def test_json_export_is_list():
    payload = json.loads(json_text(sample()))
    assert isinstance(payload, list)
    assert payload[0]["tanggal"] == "2026-10-25"
    assert payload[0]["kegiatan"] == "Rapat | review, budget"


def test_build_export_dispatch():
    assert build_export("csv", sample()).startswith("No,Tanggal")
    assert build_export("md", sample()).startswith("#")
    assert json.loads(build_export("json", sample()))
    try:
        build_export("xlsx", sample())
    except ValueError as error:
        assert "xlsx" in str(error)
    else:  # pragma: no cover
        raise AssertionError("format tidak dikenal harus ValueError")


def test_default_filename_sanitises():
    assert default_filename("csv", "csv", "2026-10") == "kegiatan-2026-10.csv"
    assert default_filename("csv", "csv", "26 Okt 2026/../x") == "kegiatan-26-Okt-2026-x.csv"
    assert default_filename("md", "md", "") == "kegiatan-semua.md"


def test_write_text_file_with_bom(tmp_path):
    target = tmp_path / "out.csv"
    write_text_file(str(target), "a,b\n1,2\n", excel_friendly=True)
    raw = target.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    assert "a,b" in raw.decode("utf-8-sig")


def test_write_text_file_plain_utf8(tmp_path):
    target = tmp_path / "out.md"
    write_text_file(str(target), "# Héllo")
    assert target.read_text(encoding="utf-8") == "# Héllo"
