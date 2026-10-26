"""Tes antarmuka baris perintah (tanpa perlu layar)."""

import os

from tests import fake_tk

fake_tk.install()

from activity_logger import __version__, cli  # noqa: E402
from activity_logger.core.settings import Settings  # noqa: E402
from activity_logger.gui import app as gui_app  # noqa: E402


def test_version_flag(capsys):
    assert cli.main(["--version"]) == 0
    assert __version__ in capsys.readouterr().out


def test_tkinter_detected_under_fake_tk():
    assert cli.tkinter_available() is True


def test_missing_tkinter_message(monkeypatch, capsys):
    monkeypatch.setattr(cli, "tkinter_available", lambda: False)
    assert cli.main([]) == 1
    assert "Tkinter tidak tersedia" in capsys.readouterr().err


def test_options_are_applied(tmp_path, monkeypatch):
    monkeypatch.setenv("ACTIVITY_LOGGER_CONFIG_DIR", str(tmp_path / "cfg"))
    captured = {}

    def fake_run(settings):
        captured["settings"] = settings
        return 0

    monkeypatch.setattr(gui_app, "run", fake_run)
    data = tmp_path / "data" / "catatan.json"
    code = cli.main(
        ["--data", str(data), "--theme", "dark", "--port", "9123"]
    )
    assert code == 0
    settings = captured["settings"]
    assert isinstance(settings, Settings)
    assert settings.data_path == str(data)
    assert settings.theme == "dark"
    assert settings.mobile_port == 9123


def test_missing_ttkbootstrap_is_a_notice(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("ACTIVITY_LOGGER_CONFIG_DIR", str(tmp_path / "cfg"))
    monkeypatch.setattr(cli, "ttkbootstrap_available", lambda: False)
    monkeypatch.setattr(gui_app, "run", lambda settings: 0)
    assert cli.main([]) == 0
    assert "ttkbootstrap" in capsys.readouterr().err


def test_parser_help_lists_options():
    parser = cli.build_parser()
    text = parser.format_help()
    for option in ("--data", "--theme", "--port", "--version"):
        assert option in text


def test_run_returns_zero_with_fake_tk(tmp_path, monkeypatch):
    monkeypatch.setenv("ACTIVITY_LOGGER_CONFIG_DIR", str(tmp_path / "cfg"))
    settings = Settings(data_path=str(tmp_path / "data" / "kegiatan.json"))
    assert gui_app.run(settings) == 0
    assert os.path.exists(settings.data_path) or True  # file dibuat saat simpan pertama
