"""Preferensi aplikasi (disimpan di folder config standar per OS)."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

APP_NAME = "ActivityLogger"
DEFAULT_PORT = 8765
DEFAULT_PAGE = "beranda"


def config_directory() -> str:
    """Folder konfigurasi sesuai konvensi OS (tanpa dependensi eksternal)."""
    override = os.environ.get("ACTIVITY_LOGGER_CONFIG_DIR")
    if override:
        return os.path.abspath(os.path.expanduser(override))
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, APP_NAME)
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/" + APP_NAME)
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "activity-logger")


def default_data_path() -> str:
    """``Documents/Activity Logger/kegiatan.json`` (fallback ke home)."""
    home = os.path.expanduser("~")
    documents = os.path.join(home, "Documents")
    base = documents if os.path.isdir(documents) else home
    return os.path.join(base, "Activity Logger", "kegiatan.json")


def data_path_candidates() -> list:
    """Pilihan lokasi cepat untuk dialog "Ubah Lokasi"."""
    home = os.path.expanduser("~")
    documents = os.path.join(home, "Documents")
    base = documents if os.path.isdir(documents) else home
    candidates = [
        os.path.join(base, "Activity Logger", "kegiatan.json"),
        os.path.join(home, "kegiatan.json"),
        os.path.join(home, "activity.json"),
        os.path.join(home, "Documents", "kegiatan.json"),
        os.path.join(home, "activity_logger", "data", "kegiatan.json"),
    ]
    # Buang duplikat sambil mempertahankan urutan.
    seen = set()
    unique = []
    for item in candidates:
        key = os.path.normcase(item)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


@dataclass
class Settings:
    data_path: str = field(default_factory=default_data_path)
    theme: str = "light"  # light | dark
    mirror_markdown: bool = False
    window_geometry: str = ""
    last_page: str = DEFAULT_PAGE
    show_seconds: bool = False
    mobile_port: int = DEFAULT_PORT
    mobile_autostart: bool = False
    confirm_delete: bool = True

    # -- konversi -------------------------------------------------------- #
    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Settings":
        settings = cls()
        if not isinstance(payload, dict):
            return settings
        for key in (
            "data_path",
            "theme",
            "mirror_markdown",
            "window_geometry",
            "last_page",
            "show_seconds",
            "mobile_port",
            "mobile_autostart",
            "confirm_delete",
        ):
            if key in payload:
                try:
                    setattr(settings, key, payload[key])
                except (TypeError, ValueError):
                    pass
        settings.normalize()
        return settings

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def normalize(self) -> None:
        if not isinstance(self.data_path, str) or not self.data_path.strip():
            self.data_path = default_data_path()
        self.data_path = os.path.abspath(os.path.expanduser(self.data_path.strip()))
        if self.theme not in ("light", "dark"):
            self.theme = "light"
        self.mirror_markdown = bool(self.mirror_markdown)
        self.show_seconds = bool(self.show_seconds)
        self.mobile_autostart = bool(self.mobile_autostart)
        self.confirm_delete = bool(self.confirm_delete)
        try:
            port = int(self.mobile_port)
        except (TypeError, ValueError):
            port = DEFAULT_PORT
        self.mobile_port = port if 1024 <= port <= 65535 else DEFAULT_PORT
        if not isinstance(self.last_page, str) or not self.last_page:
            self.last_page = DEFAULT_PAGE
        if not isinstance(self.window_geometry, str):
            self.window_geometry = ""

    # -- penyimpanan ----------------------------------------------------- #
    @property
    def config_path(self) -> str:
        return os.path.join(config_directory(), "config.json")

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Settings":
        target = path or os.path.join(config_directory(), "config.json")
        try:
            with open(target, "r", encoding="utf-8", errors="replace") as handle:
                payload = json.load(handle)
        except (OSError, ValueError):
            return cls()
        return cls.from_dict(payload)

    def save(self, path: Optional[str] = None) -> None:
        target = path or self.config_path
        folder = os.path.dirname(target)
        try:
            if folder:
                os.makedirs(folder, exist_ok=True)
            tmp = target + ".tmp"
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(self.to_dict(), handle, ensure_ascii=False, indent=2)
            os.replace(tmp, target)
        except OSError:
            # Preferensi bukan data kritis: gagal menyimpan tidak boleh crash.
            pass
