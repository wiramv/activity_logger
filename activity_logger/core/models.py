"""Model data utama: satu baris catatan kegiatan."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from . import timeutil


def new_id() -> str:
    """ID pendek yang tetap unik (dipakai untuk edit/hapus)."""
    return uuid.uuid4().hex[:12]


@dataclass
class Activity:
    """Satu kegiatan yang dicatat pengguna."""

    text: str
    ts: datetime
    id: str = field(default_factory=new_id)
    done: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        self.text = normalize_text(self.text)
        if not isinstance(self.ts, datetime):
            parsed = timeutil.parse_ts(self.ts)
            self.ts = parsed or timeutil.now()
        self.ts = self.ts.replace(microsecond=0)
        if self.created_at is None:
            self.created_at = self.ts
        if not isinstance(self.id, str) or not self.id.strip():
            self.id = new_id()

    # -- turunan -------------------------------------------------------- #
    @property
    def date(self) -> date:
        return self.ts.date()

    @property
    def month_key(self) -> str:
        return timeutil.month_key(self.date)

    @property
    def day_name(self) -> str:
        return timeutil.day_name(self.date)

    @property
    def status_label(self) -> str:
        return "Selesai" if self.done else "Belum"

    def clock(self, seconds: bool = False) -> str:
        return timeutil.fmt_clock(self.ts, seconds=seconds)

    # -- serialisasi ---------------------------------------------------- #
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tanggal": timeutil.fmt_date_numeric(self.date),
            "waktu": self.clock(seconds=True),
            "kegiatan": self.text,
            "selesai": bool(self.done),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Activity":
        """Membaca satu objek JSON dengan banyak nama kunci alternatif.

        File lama/manual sering memakai nama kunci berbeda (``activity``,
        ``text``, ``tanggal``/``date``). Kita terima semuanya agar file tidak
        pernah gagal dimuat hanya karena perbedaan penamaan.
        """
        if not isinstance(payload, dict):
            raise ValueError("Baris kegiatan harus berupa objek JSON")

        text = _first(payload, ("kegiatan", "text", "activity", "catatan", "task", "title", "isi"))
        raw_date = _first(payload, ("tanggal", "date", "tgl")) or ""
        raw_time = _first(payload, ("waktu", "time", "jam")) or ""
        raw_ts = _first(payload, ("timestamp", "ts", "datetime", "waktu_lengkap"))

        moment: Optional[datetime] = None
        if raw_ts:
            moment = timeutil.parse_ts(raw_ts)
        if moment is None and raw_date:
            day = timeutil.parse_date(raw_date)
            if day is not None:
                clock_text = str(raw_time).strip() or "00:00:00"
                clock = timeutil.parse_ts("2000-01-01 " + clock_text)
                moment = datetime.combine(day, clock.time() if clock else datetime.min.time())
        if moment is None:
            moment = timeutil.parse_ts(raw_date)

        if moment is None:
            raise ValueError("Kegiatan tanpa tanggal/waktu yang valid")
        if not text or not str(text).strip():
            raise ValueError("Kegiatan tanpa teks")

        done_value = _first(payload, ("selesai", "done", "completed", "status"), default=False)
        return cls(
            text=str(text),
            ts=moment,
            id=str(_first(payload, ("id", "uuid", "key"), default="") or ""),
            done=_as_bool(done_value),
            created_at=timeutil.parse_ts(_first(payload, ("created_at", "dibuat"))),
            updated_at=timeutil.parse_ts(_first(payload, ("updated_at", "diubah"))),
        )

    def copy_with(self, **changes: Any) -> "Activity":
        data = {
            "text": self.text,
            "ts": self.ts,
            "id": self.id,
            "done": self.done,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        data.update(changes)
        return Activity(**data)


def normalize_text(text: Any) -> str:
    """Rapikan teks masukan: buang spasi/newline berlebih dan baris kosong."""
    if text is None:
        return ""
    cleaned = " ".join(str(text).replace("\r", " ").replace("\n", " ").split())
    return cleaned.strip()


def _first(payload: Dict[str, Any], keys, default: Any = "") -> Any:
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key]
    return default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "ya", "y", "selesai", "done"}
    return False
