"""Penyimpanan kegiatan ke file JSON (JSON Lines) atau Markdown.

Desain:

* Format default adalah **JSON Lines** — satu objek JSON per baris, mis.::

      {"id": "a1b2c3", "tanggal": "2026-10-26", "waktu": "06:45:00",
       "kegiatan": "Mengerjakan desain dashboard", "selesai": false}

  Satu baris = satu kegiatan, sehingga file mudah dibaca manusia, mudah
  di-append, dan aman untuk versi kontrol. File yang berisi satu array JSON
  tetap bisa dibaca.

* Setiap perubahan langsung disimpan (autosave) dengan teknik *atomic write*
  (tulis ke file sementara lalu ``os.replace``) agar data tidak korup bila
  aplikasi ditutup paksa.

* Opsional: cermin Markdown per bulan (``kegiatan-2026-10.md``) supaya file
  enak dibaca di editor / GitHub.
"""

from __future__ import annotations

import functools
import glob
import json
import os
import shutil
import threading
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence

from . import timeutil
from .models import Activity, normalize_text

DEFAULT_FILENAME = "kegiatan.json"
ENCODING = "utf-8"


MAX_TEXT_LENGTH = 1000


def validate_text(text: Any) -> str:
    """Rapikan dan validasi teks kegiatan (tidak kosong, tidak kepanjangan)."""
    clean = normalize_text(text)
    if not clean:
        raise ValueError("Kegiatan tidak boleh kosong")
    if len(clean) > MAX_TEXT_LENGTH:
        raise ValueError(
            "Kegiatan terlalu panjang (maksimal {} karakter)".format(MAX_TEXT_LENGTH)
        )
    return clean


class StorageError(OSError):
    """Kesalahan penyimpanan yang layak ditampilkan ke pengguna.

    Mewarisi ``OSError`` agar pemanggil yang sudah menangani error I/O ikut
    menangkap kegagalan tulis (mis. folder tanpa izin akses).
    """


def _sync(method):
    """Serialise akses penyimpanan (UI thread + thread server mobile)."""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper


class ActivityStore:
    """Sumber kebenaran tunggal untuk daftar kegiatan."""

    def __init__(self, path: str, mirror_markdown: bool = False) -> None:
        self.path = os.path.abspath(os.path.expanduser(path))
        self.mirror_markdown = bool(mirror_markdown)
        self._activities: List[Activity] = []
        self._loaded = False
        self._lock = threading.RLock()
        self._max_ts: Optional[datetime] = None
        self._can_append = False
        self.load_error: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Lokasi file
    # ------------------------------------------------------------------ #
    @property
    def directory(self) -> str:
        return os.path.dirname(self.path) or "."

    @property
    def markdown_path(self) -> str:
        root, _ = os.path.splitext(self.path)
        return root + ".md"

    def month_markdown_path(self, moment: date) -> str:
        root, _ = os.path.splitext(self.path)
        return "{}-{}.md".format(root, timeutil.month_key(moment))

    # ------------------------------------------------------------------ #
    # Baca / tulis
    # ------------------------------------------------------------------ #
    @_sync
    def load(self) -> List[Activity]:
        """Muat file dari disk (tidak pernah melempar error untuk file rusak)."""
        self._activities = []
        self.load_error = None
        self._loaded = True
        if not os.path.exists(self.path):
            return self._activities

        try:
            with open(self.path, "r", encoding=ENCODING, errors="replace") as handle:
                raw = handle.read()
        except OSError as error:  # pragma: no cover - tergantung OS
            self.load_error = "Tidak bisa membaca file: {}".format(error)
            return self._activities

        activities, skipped = parse_activities(raw)
        self._activities = activities
        self._refresh_index(raw)
        if skipped:
            self.load_error = "{} baris tidak bisa dibaca dan dilewati.".format(skipped)
        return self._activities

    @_sync
    def ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    # ------------------------------------------------------------------ #
    # Indeks internal
    # ------------------------------------------------------------------ #
    def _refresh_index(self, raw: str = "") -> None:
        """Perbarui timestamp terbesar + apakah file bisa di-append."""
        self._max_ts = max((item.ts for item in self._activities), default=None)
        stripped = raw.lstrip("\ufeff").strip()
        looks_like_lines = not stripped.startswith("[") or stripped == "["
        self._can_append = (not raw) or (raw.endswith("\n") and looks_like_lines)

    def _append_line(self, activity: Activity) -> bool:
        """Tulis satu baris di akhir file (jauh lebih cepat untuk file besar)."""
        if not self._can_append:
            return False
        if not os.path.exists(self.path):
            return False
        try:
            with open(self.path, "a+b") as handle:
                handle.seek(0, os.SEEK_END)
                if handle.tell() > 0:
                    handle.seek(-1, os.SEEK_END)
                    if handle.read(1) != b"\n":
                        return False
                line = json.dumps(
                    activity.to_dict(), ensure_ascii=False, separators=(",", ":")
                )
                handle.seek(0, os.SEEK_END)
                handle.write((line + "\n").encode(ENCODING))
                handle.flush()
                os.fsync(handle.fileno())
        except OSError:
            return False
        return True

    @_sync
    def save(self) -> None:
        """Simpan seluruh daftar secara atomik, plus cermin Markdown bila aktif."""
        self.ensure_loaded()
        os.makedirs(self.directory, exist_ok=True)
        payload = "".join(
            json.dumps(item.to_dict(), ensure_ascii=False, separators=(",", ":")) + "\n"
            for item in sorted(self._activities, key=lambda act: act.ts)
        )
        tmp_path = self.path + ".tmp"
        try:
            with open(tmp_path, "w", encoding=ENCODING, newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, self.path)
        except OSError as error:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise StorageError("Gagal menyimpan file: {}".format(error)) from error

        self._max_ts = max((item.ts for item in self._activities), default=None)
        self._can_append = True
        if self.mirror_markdown:
            try:
                self.write_markdown()
            except (OSError, StorageError):
                pass  # cermin Markdown bersifat opsional

    # ------------------------------------------------------------------ #
    # Query
    # ------------------------------------------------------------------ #
    @_sync
    def all(self) -> List[Activity]:
        """Semua kegiatan, terbaru di atas."""
        self.ensure_loaded()
        return sorted(self._activities, key=lambda act: act.ts, reverse=True)

    @_sync
    def between(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[Activity]:
        """Kegiatan pada rentang setengah terbuka ``[start, end)``."""
        items = self.all()
        if start is not None:
            items = [item for item in items if item.ts >= start]
        if end is not None:
            items = [item for item in items if item.ts < end]
        return items

    @_sync
    def get(self, activity_id: str) -> Optional[Activity]:
        for item in self._activities:
            if item.id == activity_id:
                return item
        return None

    @_sync
    def count(self) -> int:
        self.ensure_loaded()
        return len(self._activities)

    # ------------------------------------------------------------------ #
    # Mutasi
    # ------------------------------------------------------------------ #
    @_sync
    def add(
        self,
        text: Any,
        when: Optional[datetime] = None,
        done: bool = False,
    ) -> Activity:
        """Tambah kegiatan baru pada waktu sekarang (default)."""
        clean = validate_text(text)
        activity = Activity(text=clean, ts=(when or timeutil.now()), done=done)
        self.ensure_loaded()
        newest_first_possible = self._max_ts is None or activity.ts >= self._max_ts
        self._activities.append(activity)
        if not (newest_first_possible and self._append_line(activity)):
            self.save()
            return activity
        # Jalur cepat berhasil: cukup perbarui indeks & cermin Markdown.
        self._max_ts = activity.ts if self._max_ts is None else max(self._max_ts, activity.ts)
        if self.mirror_markdown:
            try:
                self.write_markdown()
            except (OSError, StorageError):
                pass
        return activity

    @_sync
    def update(
        self,
        activity_id: str,
        text: Optional[str] = None,
        when: Optional[datetime] = None,
        done: Optional[bool] = None,
    ) -> Activity:
        self.ensure_loaded()
        for index, item in enumerate(self._activities):
            if item.id != activity_id:
                continue
            changes: Dict[str, Any] = {"updated_at": timeutil.now()}
            if text is not None:
                clean = normalize_text(text)
                if not clean:
                    raise ValueError("Kegiatan tidak boleh kosong")
                changes["text"] = clean
            if when is not None:
                changes["ts"] = when.replace(microsecond=0)
            if done is not None:
                changes["done"] = bool(done)
            updated = item.copy_with(**changes)
            self._activities[index] = updated
            self.save()
            return updated
        raise StorageError("Kegiatan tidak ditemukan (mungkin sudah dihapus)")

    @_sync
    def toggle_done(self, activity_id: str) -> Activity:
        item = self.get(activity_id)
        if item is None:
            raise StorageError("Kegiatan tidak ditemukan")
        return self.update(activity_id, done=not item.done)

    @_sync
    def delete(self, activity_id: str) -> bool:
        self.ensure_loaded()
        before = len(self._activities)
        self._activities = [item for item in self._activities if item.id != activity_id]
        if len(self._activities) == before:
            return False
        self.save()
        return True

    @_sync
    def clear(self, make_backup: bool = True) -> int:
        """Hapus semua kegiatan (dengan cadangan otomatis)."""
        self.ensure_loaded()
        removed = len(self._activities)
        if removed and make_backup:
            self.backup(tag="sebelum-hapus-semua")
        self._activities = []
        self.save()
        return removed

    # ------------------------------------------------------------------ #
    # Pindah file & cadangan
    # ------------------------------------------------------------------ #
    @_sync
    def relocate(self, new_path: str, import_existing: bool = True) -> None:
        """Pindahkan penyimpanan ke file lain.

        Bila file tujuan sudah berisi data dan ``import_existing`` aktif, isi
        file tersebut digabung dengan data di memori (berdasarkan ``id``).
        """
        self.ensure_loaded()
        target = os.path.abspath(os.path.expanduser(new_path))
        if target == self.path:
            return
        merged: Dict[str, Activity] = {item.id: item for item in self._activities}
        if import_existing and os.path.exists(target):
            try:
                with open(target, "r", encoding=ENCODING, errors="replace") as handle:
                    others, _ = parse_activities(handle.read())
            except OSError as error:
                raise StorageError("Tidak bisa membaca file tujuan: {}".format(error)) from error
            for item in others:
                merged.setdefault(item.id, item)
        self.path = target
        self._activities = sorted(merged.values(), key=lambda act: act.ts)
        self.save()

    @_sync
    def backup(self, tag: str = "manual") -> str:
        """Salin file data saat ini ke folder ``backups/``."""
        self.ensure_loaded()
        folder = os.path.join(self.directory, "backups")
        os.makedirs(folder, exist_ok=True)
        stamp = timeutil.now().strftime("%Y%m%d-%H%M%S")
        safe_tag = "".join(ch for ch in tag if ch.isalnum() or ch in "-_") or "backup"
        root, ext = os.path.splitext(os.path.basename(self.path))
        target = os.path.join(folder, "{}-{}-{}{}".format(root, safe_tag, stamp, ext or ".json"))
        if os.path.exists(self.path):
            shutil.copy2(self.path, target)
        else:
            with open(target, "w", encoding=ENCODING) as handle:
                handle.write("")
        return target

    def list_backups(self, limit: int = 20) -> List[str]:
        pattern = os.path.join(self.directory, "backups", "*.json")
        files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
        return files[:limit]

    # ------------------------------------------------------------------ #
    # Markdown
    # ------------------------------------------------------------------ #
    @_sync
    def render_markdown(self, items: Optional[Sequence[Activity]] = None) -> str:
        from .exporter import markdown_document

        self.ensure_loaded()
        data = list(items) if items is not None else self.all()
        return markdown_document(data, title="Catatan Kegiatan")

    @_sync
    def write_markdown(self, items: Optional[Sequence[Activity]] = None) -> str:
        from .exporter import markdown_by_month

        data = list(items) if items is not None else self.all()
        chunks = markdown_by_month(data)
        written: List[str] = []
        os.makedirs(self.directory, exist_ok=True)
        for key, text in chunks.items():
            year, month = (int(part) for part in key.split("-"))
            target = self.month_markdown_path(date(year, month, 1))
            with open(target, "w", encoding=ENCODING, newline="\n") as handle:
                handle.write(text)
            written.append(target)
        if not chunks:  # tetap buat satu file kosong agar terlihat
            with open(self.markdown_path, "w", encoding=ENCODING, newline="\n") as handle:
                handle.write("# Catatan Kegiatan\n\nBelum ada kegiatan.\n")
            written.append(self.markdown_path)
        return written[0]


# ---------------------------------------------------------------------- #
# Parsing file
# ---------------------------------------------------------------------- #
def parse_activities(raw: str) -> tuple:
    """Ubah isi file (JSON Lines / JSON array) menjadi ``(activities, skipped)``."""
    text = (raw or "").lstrip("\ufeff").strip()
    items: List[Any] = []
    skipped = 0
    if not text:
        return [], 0

    # 1) Coba JSON utuh (array atau objek tunggal / objek berisi "activities").
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        parsed = None

    if parsed is not None:
        if isinstance(parsed, dict):
            for key in ("activities", "kegiatan", "data", "items", "logs"):
                if isinstance(parsed.get(key), list):
                    items = list(parsed[key])
                    break
            else:
                items = [parsed]
        elif isinstance(parsed, list):
            items = list(parsed)
        else:
            return [], 1
    else:
        # 2) JSON Lines: satu objek per baris.
        for line in text.splitlines():
            line = line.strip().rstrip(",")
            if not line or line in ("[", "]", "{", "}"):
                continue
            try:
                value = json.loads(line)
            except ValueError:
                skipped += 1
                continue
            if isinstance(value, list):
                items.extend(value)
            else:
                items.append(value)

    activities: List[Activity] = []
    for entry in items:
        try:
            activities.append(Activity.from_dict(entry))
        except (ValueError, TypeError, KeyError):
            skipped += 1
    activities.sort(key=lambda act: act.ts)
    return activities, skipped
