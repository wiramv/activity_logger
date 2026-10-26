"""Tes preferensi aplikasi."""

import json
import os

from activity_logger.core.settings import (
    DEFAULT_PORT,
    Settings,
    config_directory,
    data_path_candidates,
    default_data_path,
)


def test_defaults_are_sane():
    settings = Settings()
    assert settings.theme == "light"
    assert settings.mobile_port == DEFAULT_PORT
    assert settings.data_path.endswith("kegiatan.json")
    assert os.path.isabs(settings.data_path)


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("ACTIVITY_LOGGER_CONFIG_DIR", str(tmp_path / "cfg"))
    settings = Settings(data_path=str(tmp_path / "data" / "catatan.json"), theme="dark")
    settings.mirror_markdown = True
    settings.save()

    assert os.path.exists(tmp_path / "cfg" / "config.json")
    loaded = Settings.load()
    assert loaded.data_path == str(tmp_path / "data" / "catatan.json")
    assert loaded.theme == "dark"
    assert loaded.mirror_markdown is True


def test_load_missing_or_broken_returns_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("ACTIVITY_LOGGER_CONFIG_DIR", str(tmp_path / "cfg"))
    assert Settings.load().theme == "light"

    folder = tmp_path / "cfg"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "config.json").write_text("{rusak", encoding="utf-8")
    assert Settings.load().theme == "light"


def test_normalize_rejects_bad_values(tmp_path):
    settings = Settings.from_dict(
        {
            "theme": "neon",
            "mobile_port": 99999,
            "data_path": "  ",
            "window_geometry": 123,
            "last_page": "",
        }
    )
    assert settings.theme == "light"
    assert settings.mobile_port == DEFAULT_PORT
    assert settings.data_path.endswith(".json")
    assert settings.window_geometry == ""
    assert settings.last_page == "beranda"


def test_data_path_candidates_unique():
    candidates = data_path_candidates()
    assert candidates
    assert len(candidates) == len(set(os.path.normcase(item) for item in candidates))
    assert default_data_path() in candidates


def test_config_directory_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("ACTIVITY_LOGGER_CONFIG_DIR", str(tmp_path / "custom"))
    assert config_directory() == str(tmp_path / "custom")


def test_to_dict_is_json_serialisable(tmp_path):
    payload = Settings(data_path=str(tmp_path / "a.json")).to_dict()
    assert json.loads(json.dumps(payload))["data_path"] == str(tmp_path / "a.json")
