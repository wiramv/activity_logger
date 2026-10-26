"""Tes penyimpanan: format file, kompatibilitas, dan operasi CRUD."""

import json
import os
from datetime import datetime

import pytest

from activity_logger.core.storage import ActivityStore, parse_activities


def make_store(tmp_path, name="kegiatan.json", **kwargs):
    return ActivityStore(str(tmp_path / name), **kwargs)


def test_add_writes_json_lines(tmp_path):
    store = make_store(tmp_path)
    store.add("Olahraga pagi", when=datetime(2026, 10, 26, 6, 45, 0))
    store.add("Membaca buku", when=datetime(2026, 10, 25, 22, 40, 0))

    raw = (tmp_path / "kegiatan.json").read_text(encoding="utf-8").strip().splitlines()
    assert len(raw) == 2
    first = json.loads(raw[0])
    assert first == {
        "id": first["id"],
        "tanggal": "2026-10-25",
        "waktu": "22:40:00",
        "kegiatan": "Membaca buku",
        "selesai": False,
    }


def test_reload_keeps_data_and_order(tmp_path):
    store = make_store(tmp_path)
    store.add("A", when=datetime(2026, 10, 26, 8, 0, 0))
    store.add("B", when=datetime(2026, 10, 26, 20, 0, 0))

    fresh = make_store(tmp_path)
    texts = [item.text for item in fresh.all()]
    assert texts == ["B", "A"]  # terbaru dulu


def test_add_strips_and_rejects_empty(tmp_path):
    store = make_store(tmp_path)
    activity = store.add("  Menulis   catatan  \n")
    assert activity.text == "Menulis catatan"
    with pytest.raises(ValueError):
        store.add("   ")


def test_update_toggle_delete(tmp_path):
    store = make_store(tmp_path)
    activity = store.add("Belajar Python")

    updated = store.update(activity.id, text="Belajar Python lanjutan")
    assert updated.text == "Belajar Python lanjutan"
    assert updated.updated_at is not None

    toggled = store.toggle_done(activity.id)
    assert toggled.done is True
    assert toggled.status_label == "Selesai"

    assert store.delete(activity.id) is True
    assert store.delete(activity.id) is False
    assert store.count() == 0


def test_clear_creates_backup(tmp_path):
    store = make_store(tmp_path)
    store.add("Satu")
    store.add("Dua")
    removed = store.clear()
    assert removed == 2
    backups = store.list_backups()
    assert len(backups) == 1
    assert "sebelum-hapus-semua" in os.path.basename(backups[0])
    assert store.count() == 0


def test_load_legacy_array_with_english_keys(tmp_path):
    payload = [
        {"text": "Design dashboard", "date": "2026-10-26", "time": "06:45"},
        {"activity": "Morning run", "timestamp": "2026-10-25 22:40:00", "done": "yes"},
    ]
    path = tmp_path / "kegiatan.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    store = make_store(tmp_path)
    items = store.all()
    assert len(items) == 2
    assert items[0].text == "Design dashboard"
    assert items[1].done is True
    assert items[1].ts == datetime(2026, 10, 25, 22, 40)


def test_load_object_with_activities_list(tmp_path):
    path = tmp_path / "kegiatan.json"
    path.write_text(
        json.dumps({"activities": [{"kegiatan": "Rapat tim", "tanggal": "2026-10-26", "waktu": "14:30:00"}]}),
        encoding="utf-8",
    )
    store = make_store(tmp_path)
    assert [item.text for item in store.all()] == ["Rapat tim"]


def test_parse_skips_broken_lines():
    raw = (
        '{"tanggal":"2026-10-26","waktu":"06:45:00","kegiatan":"Valid"}\n'
        "bukan json\n"
        '{"tanggal":"2026-10-26","waktu":"07:45:00"}\n'
        '{"tanggal":"2026-10-26","waktu":"08:45:00","kegiatan":"Juga valid"}\n'
    )
    activities, skipped = parse_activities(raw)
    assert len(activities) == 2
    assert skipped == 2


def test_empty_and_missing_file(tmp_path):
    store = make_store(tmp_path)
    assert store.all() == []
    assert store.load_error is None
    (tmp_path / "kegiatan.json").write_text("", encoding="utf-8")
    assert store.all() == []


def test_backup_creates_file(tmp_path):
    store = make_store(tmp_path)
    store.add("Halo")
    backup = store.backup("manual")
    assert os.path.exists(backup)
    assert "manual" in os.path.basename(backup)


def test_mirror_markdown(tmp_path):
    store = make_store(tmp_path, mirror_markdown=True)
    store.add("Menulis laporan", when=datetime(2026, 10, 26, 9, 0, 0))
    mirror = tmp_path / "kegiatan-2026-10.md"
    assert mirror.exists()
    content = mirror.read_text(encoding="utf-8")
    assert "# Kegiatan Oktober 2026" in content
    assert "Menulis laporan" in content


def test_relocate_merges_target(tmp_path):
    store = make_store(tmp_path)
    store.add("Lama", when=datetime(2026, 10, 20, 9, 0, 0))

    target = tmp_path / "lain" / "data.json"
    target.parent.mkdir()
    target.write_text(
        json.dumps([{"kegiatan": "Dari file tujuan", "tanggal": "2026-10-21", "waktu": "10:00:00"}]),
        encoding="utf-8",
    )

    store.relocate(str(target))
    assert store.path == str(target)
    texts = sorted(item.text for item in store.all())
    assert texts == ["Dari file tujuan", "Lama"]

    fresh = ActivityStore(str(target))
    assert fresh.count() == 2


def test_between_filters_half_open(tmp_path):
    store = make_store(tmp_path)
    store.add("A", when=datetime(2026, 10, 26, 0, 0, 0))
    store.add("B", when=datetime(2026, 10, 26, 23, 59, 59))
    store.add("C", when=datetime(2026, 10, 27, 0, 0, 0))
    items = store.between(datetime(2026, 10, 26), datetime(2026, 10, 27))
    assert [item.text for item in items] == ["B", "A"]


def test_save_is_atomic_no_tmp_left(tmp_path):
    store = make_store(tmp_path)
    store.add("Satu")
    store.add("Dua")
    leftovers = [name for name in os.listdir(tmp_path) if name.endswith(".tmp")]
    assert leftovers == []


def test_unicode_preserved(tmp_path):
    store = make_store(tmp_path)
    store.add("Menulis résumé & desain — versi 2 🚀")
    raw = (tmp_path / "kegiatan.json").read_text(encoding="utf-8")
    assert "résumé" in raw and "🚀" in raw


def test_text_length_limit(tmp_path):
    from activity_logger.core.storage import MAX_TEXT_LENGTH

    store = make_store(tmp_path)
    assert store.add("x" * MAX_TEXT_LENGTH).text == "x" * MAX_TEXT_LENGTH
    with pytest.raises(ValueError):
        store.add("x" * (MAX_TEXT_LENGTH + 1))


def test_add_uses_append_path_and_stays_sorted(tmp_path):
    import time

    store = make_store(tmp_path)
    started = time.perf_counter()
    for index in range(120):
        store.add("Kegiatan {}".format(index))
    elapsed = time.perf_counter() - started
    # 120 penyimpanan harus jauh di bawah 3 detik (append, bukan tulis ulang)
    assert elapsed < 3.0

    fresh = make_store(tmp_path)
    items = fresh.all()
    assert len(items) == 120
    timestamps = [item.ts for item in items]
    assert timestamps == sorted(timestamps, reverse=True)


def test_backdated_add_falls_back_to_rewrite(tmp_path):
    store = make_store(tmp_path)
    store.add("Terbaru", when=datetime(2026, 10, 26, 12, 0, 0))
    store.add("Mundur", when=datetime(2026, 10, 1, 12, 0, 0))

    raw = (tmp_path / "kegiatan.json").read_text(encoding="utf-8").strip().splitlines()
    assert "Terbaru" in raw[1] and "Mundur" in raw[0]  # tetap urut naik


def test_append_requires_trailing_newline(tmp_path):
    path = tmp_path / "kegiatan.json"
    path.write_text(
        json.dumps(
            {"tanggal": "2026-10-01", "waktu": "09:00:00", "kegiatan": "Tanpa newline"}
        ),
        encoding="utf-8",
    )
    store = make_store(tmp_path)
    store.add("Kegiatan baru", when=datetime(2026, 10, 20, 9, 0, 0))
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    json.loads(lines[0])  # keduanya tetap JSON valid
    json.loads(lines[1])


def test_array_file_is_rewritten_as_lines(tmp_path):
    path = tmp_path / "kegiatan.json"
    path.write_text(
        json.dumps([{"kegiatan": "Dari array", "tanggal": "2026-10-01", "waktu": "09:00:00"}]),
        encoding="utf-8",
    )
    store = make_store(tmp_path)
    store.add("Baru", when=datetime(2026, 10, 20, 9, 0, 0))
    text = path.read_text(encoding="utf-8")
    assert text.lstrip().startswith('{"')
    assert len(text.strip().splitlines()) == 2
