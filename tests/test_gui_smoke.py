"""Tes lapisan GUI dengan Tkinter palsu (tanpa server X).

Fokus tes ini: seluruh kode pembangunan UI benar-benar dieksekusi pada semua
ukuran layar, alur tambah/ubah/hapus berjalan, dan ekspor menghasilkan file
nyata. Tidak menguji piksel.
"""

from __future__ import annotations

import os
from datetime import date, datetime

import pytest

from tests import fake_tk

fake_tk.install()

from activity_logger.core import timeutil  # noqa: E402
from activity_logger.core.settings import Settings  # noqa: E402
from activity_logger.core.storage import ActivityStore  # noqa: E402
from activity_logger.gui import app as app_module  # noqa: E402
from activity_logger.gui import icons, theme  # noqa: E402
from activity_logger.gui.app import ActivityApp  # noqa: E402
from activity_logger.gui.widgets import (  # noqa: E402
    ActivityRow,
    BarChart,
    Button,
    CheckboxRow,
    Chip,
    EmptyState,
    IconButton,
    Modal,
    ScrollArea,
    StatTile,
    TextField,
    Toast,
    Tooltip,
    confirm,
)

PAGE_KEYS = ("beranda", "lokasi", "catatan", "total", "export", "hapus", "pengaturan")


@pytest.fixture()
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("ACTIVITY_LOGGER_CONFIG_DIR", str(tmp_path / "cfg"))
    config = Settings(data_path=str(tmp_path / "data" / "kegiatan.json"))
    config.window_geometry = ""
    return config


@pytest.fixture()
def store(settings):
    instance = ActivityStore(settings.data_path)
    instance.add("Olahraga pagi", when=datetime(2026, 10, 26, 7, 30, 0))
    instance.add("Memorandum desain dashboard", when=datetime(2026, 10, 26, 6, 45, 0))
    instance.add("Rapat tim", when=datetime(2026, 10, 25, 14, 30, 0), done=True)
    instance.add("Bulan lalu", when=datetime(2026, 9, 20, 9, 0, 0))
    return instance


@pytest.fixture()
def app(settings, store):
    application = ActivityApp(settings=settings, store=store)
    yield application
    application.on_close()


# --------------------------------------------------------------------------- #
# Shell & routing
# --------------------------------------------------------------------------- #
def test_app_starts_on_dashboard(app):
    assert app.page_key in PAGE_KEYS
    assert app.page is not None
    assert app.root.title() == "Activity Logger"


def test_navigate_all_pages(app):
    for key in PAGE_KEYS:
        app.navigate(key)
        assert app.page_key == key
        assert app.page.outer.winfo_exists() == 1


@pytest.mark.parametrize(
    "width,expected_mode",
    [(1280, "expanded"), (980, "expanded"), (820, "collapsed"), (620, "hidden")],
)
def test_breakpoints(app, width, expected_mode):
    app.root.set_size(width)
    app._apply_breakpoint(force=True)
    assert app.sidebar_mode == expected_mode
    assert app.metrics["bp"] in ("lg", "md", "sm", "xs")
    for key in PAGE_KEYS:
        app.navigate(key)
        assert app.page.outer.winfo_exists() == 1


def test_pages_handle_extreme_widths(app):
    for key in PAGE_KEYS:
        app.navigate(key)
        app.page.on_width(320)
        app.page.on_width(1600)
        app.page.refresh()
        assert app.page.outer.winfo_exists() == 1


def test_content_width_matches_breakpoint(app):
    app.root.set_size(1280)
    app._apply_breakpoint(force=True)
    assert app.content_width == 1280 - app_module.SIDEBAR_WIDTH
    app.root.set_size(500)
    app._apply_breakpoint(force=True)
    assert app.content_width == 500


def test_navigation_remembers_page(settings, store):
    application = ActivityApp(settings=settings, store=store)
    application.navigate("catatan")
    assert application.settings.last_page == "catatan"
    application.on_close()

    reloaded = Settings.load()
    assert reloaded.last_page == "catatan"


# --------------------------------------------------------------------------- #
# Alur data
# --------------------------------------------------------------------------- #
def test_quick_add_from_dashboard(app):
    app.navigate("beranda")
    page = app.page
    page.field.set("Menulis laporan mingguan")
    page._submit()
    assert app.store.count() == 5
    assert page.field.get() == ""
    assert "Tersimpan" in app.toast_widget._label.cget("text")
    assert "Menulis laporan mingguan" in [item.text for item in app.store.all()]


def test_quick_add_empty_shows_error(app):
    app.navigate("beranda")
    app.page.field.set("")
    app.page._submit()
    assert "Ketik kegiatan" in app.toast_widget._label.cget("text")
    assert app.store.count() == 4


def test_toggle_edit_delete(app, monkeypatch):
    app.settings.confirm_delete = False
    app.navigate("catatan")
    activity = app.store.all()[0]

    app.toggle_activity(activity)
    assert app.store.get(activity.id).done is True

    monkeypatch.setattr(app_module, "prompt", lambda *a, **k: "  Teks hasil edit  ")
    app.edit_activity(activity)
    assert app.store.get(activity.id).text == "Teks hasil edit"

    app.delete_activity(activity)
    assert app.store.get(activity.id) is None
    assert app.store.count() == 3


def test_delete_requires_confirmation(app, monkeypatch):
    app.settings.confirm_delete = True
    activity = app.store.all()[0]
    monkeypatch.setattr(app_module, "confirm", lambda *a, **k: False)
    app.delete_activity(activity)
    assert app.store.count() == 4


def test_delete_all_with_backup(app, monkeypatch):
    monkeypatch.setattr(app_module, "confirm", lambda *a, **k: True)
    app.delete_all()
    assert app.store.count() == 0
    assert app.store.list_backups()
    assert app.page_key == "beranda"


def test_restore_backup(app, monkeypatch):
    app.store.backup("manual")
    app.store.add("Kegiatan sementara")
    assert app.store.count() == 5
    backup = app.store.list_backups()[0]
    monkeypatch.setattr(app_module, "confirm", lambda *a, **k: True)
    app.restore_backup(backup)
    assert app.store.count() == 4


def test_reload_store(app):
    app.store.add("Tambahan")
    app.reload_store()
    assert app.store.count() == 5


def test_change_location(app, tmp_path, monkeypatch):
    target = tmp_path / "lain" / "catatan.json"
    monkeypatch.setattr(
        app_module.filedialog, "asksaveasfilename", lambda **kwargs: str(target)
    )
    app.change_location()
    assert app.store.path == str(target)
    assert os.path.exists(target)
    assert app.settings.data_path == str(target)
    assert app.page is not None


def test_mirror_markdown_toggle(app):
    app.set_mirror_markdown(True)
    assert app.settings.mirror_markdown is True
    assert any(name.endswith(".md") for name in os.listdir(os.path.dirname(app.store.path)))
    app.set_mirror_markdown(False)


def test_preferences_callbacks(app):
    app.set_show_seconds(True)
    assert app.settings.show_seconds is True
    app.set_confirm_delete(False)
    assert app.settings.confirm_delete is False


# --------------------------------------------------------------------------- #
# Ekspor
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("kind,extension", [("csv", "csv"), ("md", "md"), ("json", "json")])
def test_export_all(app, kind, extension):
    path = app.export_all(kind)
    assert path is not None
    assert path.endswith("." + extension)
    assert os.path.getsize(path) > 0
    assert os.path.dirname(path) == app.exports_dir


def test_export_csv_has_bom_and_content(app):
    path = app.export_all("csv")
    raw = open(path, "rb").read()
    assert raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    assert text.startswith("No,Tanggal,Hari,Jam,Kegiatan,Status")
    assert "Rapat tim" in text


def test_export_month_and_range(app):
    assert app.export_month("csv") is not None
    assert app.export_month("md") is not None
    path = app.export_range("csv", (date(2026, 10, 1), date(2026, 10, 26)), "2026-10-01_2026-10-26")
    assert path is not None and os.path.exists(path)
    summary = app.export_summary_csv((date(2026, 10, 1), date(2026, 10, 31)), "2026-10")
    assert summary is not None
    assert "Jumlah Kegiatan" in open(summary, encoding="utf-8-sig").read()


def test_export_period_uses_stats_state(app):
    app.state["stats_period"] = "month"
    path = app.export_period("csv")
    assert path is not None


def test_export_empty_is_safe(app):
    app.store.clear(make_backup=False)
    assert app.export_all("csv") is None
    assert "Belum ada" in app.toast_widget._label.cget("text")


def test_month_slug(app):
    assert app.month_slug() == timeutil.month_key(timeutil.today())


def test_open_exports_folder(app, monkeypatch):
    opened = {}
    monkeypatch.setattr(app_module.os, "system", lambda command: opened.setdefault("cmd", command))
    app.open_exports_folder()
    assert os.path.isdir(app.exports_dir)


# --------------------------------------------------------------------------- #
# Tema & mobile
# --------------------------------------------------------------------------- #
def test_theme_switch_rebuilds_ui(app):
    app.navigate("total")
    app.set_theme("dark")
    assert app.mode == "dark"
    assert app.themes.mode == "dark"
    assert app.page_key == "total"
    assert app.pal["page"] == theme.DARK["page"]
    app.toggle_theme()
    assert app.mode == "light"
    assert app.pal["page"] == theme.LIGHT["page"]


def test_mobile_server_toggle(app):
    app._start_mobile(silent=True)
    assert app.mobile.running is True
    assert app.mobile.url().startswith("http://")
    app._stop_mobile()
    assert app.mobile.running is False


def test_copy_to_clipboard(app):
    app.copy_to_clipboard("halo dunia")
    assert app.root._clipboard == "halo dunia"


# --------------------------------------------------------------------------- #
# Halaman spesifik
# --------------------------------------------------------------------------- #
def test_log_page_search_and_filters(app):
    app.navigate("catatan")
    page = app.page

    page.search.set("rapat")
    assert app.state["log_query"] == "rapat"
    assert page.rows_host.winfo_children()

    page.search.set("")
    page._set_period("today")
    assert app.state["log_period"] == "today"

    page._set_period("custom")
    assert app.state["log_start"]
    page.start_field.set("bukan-tanggal")
    page._apply_custom()
    assert "YYYY-MM-DD" in app.toast_widget._label.cget("text")

    page.start_field.set("2026-10-01")
    page.end_field.set("2026-10-26")
    page._apply_custom()
    assert app.state["log_start"] == "2026-10-01"

    page._set_period("semua-hari")
    page._reset_filters()
    assert app.state["log_query"] == ""
    assert app.state["log_period"] == "month"


def test_log_page_pagination(app):
    for index in range(20):
        app.store.add("Kegiatan tambahan {}".format(index))
    app.navigate("catatan")
    page = app.page
    page._go_page(2)
    assert app.state["log_page"] == 2
    page._go_page(999)
    assert app.state["log_page"] >= 1


def test_stats_page_periods_and_custom(app):
    app.navigate("total")
    page = app.page
    for period in ("today", "week", "month", "last30", "all"):
        page._set_period(period)
        assert app.state["stats_period"] == period
    page._set_period("custom")
    assert app.state["stats_start"]
    page._start_field.set("2026-10-01")
    page._end_field.set("2026-10-26")
    page._apply_custom()
    assert app.state["stats_start"] == "2026-10-01"
    assert page._tiles[0].value_label.cget("text") != ""


def test_export_page_custom_range(app):
    app.navigate("export")
    page = app.page
    page._quick_range(7)
    assert app.state["export_start"]
    page._last_month()
    assert app.state["export_start"].startswith("2026-09")
    page._update_preview()
    assert "siap diekspor" in page._preview_label.cget("text")
    assert app.export_range("csv", page._range(), page._range_slug()) is not None


def test_location_page_actions(app):
    app.navigate("lokasi")
    page = app.page
    assert page._example_json().startswith("{")
    page._make_backup()
    assert app.store.list_backups()


def test_delete_page_builds_backups(app):
    app.store.backup("manual")
    app.navigate("hapus")
    assert app.page.outer.winfo_exists() == 1


def test_settings_page_builds(app):
    app.navigate("pengaturan")
    assert app.page.outer.winfo_exists() == 1


def test_unknown_page_falls_back(app):
    app.navigate("tidak-ada")
    assert app.page_key == "beranda"


# --------------------------------------------------------------------------- #
# Komponen
# --------------------------------------------------------------------------- #
def test_icons_paint_all_names():
    canvas = fake_tk.Canvas()
    for name in sorted(icons.ICON_NAMES):
        icons.paint(canvas, name, "#000000", size=18)
    icons.paint(canvas, "tidak-ada", "#000000")


def test_button_variants_and_hover(app):
    for variant in (
        "primary", "outline", "ghost", "subtle", "danger", "danger_outline", "link", "unknown"
    ):
        clicked = []
        button = Button(
            app.page.content,
            text="Aksi",
            command=lambda: clicked.append(1),
            variant=variant,
            pal=app.pal,
            fonts=app.fonts,
            icon="plus",
        )
        button.pack()
        button._on_enter()
        button._on_leave()
        button._on_click()
        button._on_release()
        button.invoke()
        assert clicked, variant
        button.set_text("Baru")
        button.set_state("disabled")
        button.invoke()
        assert button.state == "disabled"


def test_icon_button(app):
    calls = []
    button = IconButton(
        app.page.content, "gear", command=lambda: calls.append(1), pal=app.pal, tooltip="Set"
    )
    button.pack()
    button._on_enter()
    button._on_leave()
    button._on_click()
    assert calls == [1]
    button.set_icon("sun")


def test_text_field_placeholder(app):
    field = TextField(app.page.content, app.pal, app.fonts, placeholder="Cari...")
    assert field.get() == ""
    field.focus()
    assert field.get() == ""
    field.set("halo")
    assert field.get() == "halo"
    field.clear()
    assert field.get() == ""
    field._on_focus_out()
    assert field.get() == ""


def test_activity_row_layouts(app):
    activity = app.store.all()[0]
    for layout in ("table", "stack"):
        row = ActivityRow(
            app.page.content,
            activity,
            app.pal,
            app.fonts,
            layout=layout,
            on_toggle=lambda act: None,
            on_edit=lambda act: None,
            on_delete=lambda act: None,
        )
        row.pack()
        row._hover_on()
        row._hover_off()
        row.set_wraplength(300)
        assert row.when_label.cget("text")


def test_stat_tile_and_chip(app):
    tile = StatTile(
        app.page.content, app.pal, app.fonts, "list", "Total", "0", "caption",
        command=lambda: None,
    )
    tile.pack()
    tile.set("12")
    assert tile.value_label.cget("text") == "12"

    chip = Chip(app.page.content, "Hari ini", app.pal, app.fonts, command=lambda: None)
    chip.pack()
    chip._hover(True)
    chip._hover(False)
    chip.set_active(True)
    chip.set_active(False)
    chip.invoke()


def test_bar_chart_data(app):
    chart = BarChart(app.page.content, app.pal, app.fonts)
    chart.pack()
    chart.set_data([(date(2026, 10, 24), 0), (date(2026, 10, 25), 3), (date(2026, 10, 26), 5)])
    assert len(chart._bars) == 3
    chart._on_motion(type("E", (), {"x": int(chart._bars[1][0])})())
    chart._on_leave()
    chart.set_data([])


def test_scroll_area_and_thumb(app):
    area = ScrollArea(app.page.content, app.pal["page"])
    area.pack()
    area.scroll_steps(3)
    area.scroll_top()
    area._on_scroll("0.0", "0.5")
    area._draw_thumb()
    area._jump_to(0.2)
    assert area.view_fraction() >= 0.0


def test_toast_and_tooltip(app):
    toast = Toast(app.page.content, app.pal, app.fonts)
    toast.show("Halo")
    assert toast._label.cget("text") == "Halo"
    toast.show("Gagal", kind="error")
    toast.hide()

    label = fake_tk.Widget()
    tooltip = Tooltip(label, "Keterangan", app.pal)
    tooltip._show()
    tooltip._hide()


def test_empty_state_and_checkbox(app):
    empty = EmptyState(app.page.content, app.pal, app.fonts)
    empty.pack()
    values = []
    row = CheckboxRow(
        app.page.content, app.pal, app.fonts, "Aktif", "Deskripsi", True,
        command=values.append,
    )
    row.pack()
    row.toggle()
    assert values == [False]


def test_modal_dialog(app):
    dialog = Modal(app, "Judul", "Pesan", confirm_label="OK", entry_value="awal")
    assert dialog.entry is not None
    dialog.entry.insert("end", " tambahan")
    dialog._confirm()
    assert dialog.result.startswith("awal")
    assert dialog.winfo_exists() == 0


def test_confirm_and_prompt_helpers(app, monkeypatch):
    monkeypatch.setattr(Modal, "show", lambda self: "nilai")
    assert confirm(app, "Judul", "Pesan") is True
    from activity_logger.gui.widgets import prompt as prompt_helper

    assert prompt_helper(app, "Judul", "Pesan", value="x") == "nilai"


# --------------------------------------------------------------------------- #
# Helper internal
# --------------------------------------------------------------------------- #
def test_short_path_shortening(app):
    app.store.path = "/" + "sangat-panjang/" * 10 + "kegiatan.json"
    shortened = app._short_path()
    assert len(shortened) <= 46
    assert shortened.startswith("…")


def test_ellipsis_helper():
    assert app_module._ellipsis("pendek") == "pendek"
    assert app_module._ellipsis("x" * 100, 10).endswith("…")


def test_poll_mobile_is_safe(app):
    app._poll_mobile()
    assert app.page is not None


def test_close_stops_everything(app):
    app._start_mobile(silent=True)
    app.on_close()
    assert app.mobile.running is False


def test_geometry_width_parser():
    assert app_module._geometry_width("980x700+10+10") == 980
    assert app_module._geometry_width("500x400") == 500
    assert app_module._geometry_width("") == 1180
    assert app_module._geometry_width("rusak") == 1180


def test_startup_shows_load_error(tmp_path, monkeypatch):
    monkeypatch.setenv("ACTIVITY_LOGGER_CONFIG_DIR", str(tmp_path / "cfg"))
    path = tmp_path / "rusak.json"
    path.write_text('{"tanggal":"2026-10-26","waktu":"06:00:00","kegiatan":"ok"}\nrusak\n', encoding="utf-8")
    config = Settings(data_path=str(path))
    application = ActivityApp(settings=config)
    try:
        assert application.store.load_error is not None
        application.root.run_after()
        assert "baris" in application.toast_widget._label.cget("text")
    finally:
        application.on_close()


def test_bottom_nav_visible_only_when_narrow(app):
    app.root.set_size(1280)
    app._apply_breakpoint(force=True)
    assert app.bottom_nav._visible is False

    app.root.set_size(560)
    app._apply_breakpoint(force=True)
    assert app.bottom_nav._visible is True
    assert set(app._bottom_items) == {
        "beranda", "lokasi", "catatan", "total", "export"
    }
    app.navigate("total")
    assert app._bottom_items["total"][1]._item_options  # ikon digambar ulang
    assert app.toast_widget.bottom_offset == 66

    app.root.set_size(1280)
    app._apply_breakpoint(force=True)
    assert app.bottom_nav._visible is False
    assert app.toast_widget.bottom_offset == 0


def test_app_icon_is_valid_png(app):
    import base64

    from activity_logger.gui.appicon import ICON_PNG_BASE64, load_icon

    raw = base64.b64decode(ICON_PNG_BASE64)
    assert raw.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(raw) > 200
    assert load_icon(app.root) is not None


def test_keyboard_shortcuts_registered(app):
    sequences = getattr(app, "shortcut_sequences", [])
    for expected in (
        "<Control-n>", "<Control-f>", "<Control-Shift-E>", "<Control-Shift-A>",
        "<Control-Shift-D>", "<Control-Shift-M>", "<Control-1>", "<F5>", "<Escape>",
    ):
        assert expected in sequences, expected


def test_shortcut_callbacks_work(app, monkeypatch):
    app.root.set_size(1280)
    app._apply_breakpoint(force=True)
    root_bindings = app.root._all_bindings
    # Ctrl+N -> fokus kotak input cepat
    app.navigate("total")
    handler = root_bindings["<Control-n>"][-1]
    handler(type("E", (), {"widget": app.root})())
    assert app.page_key == "beranda"

    # Ctrl+3 -> halaman catatan, lalu Ctrl+F fokus ke pencarian
    root_bindings["<Control-3>"][-1](type("E", (), {"widget": app.root})())
    assert app.page_key == "catatan"
    root_bindings["<Control-f>"][-1](type("E", (), {"widget": app.root})())
    assert app.page.search is not None

    # Ctrl+Shift+D -> ganti tema
    before = app.mode
    root_bindings["<Control-Shift-D>"][-1](type("E", (), {"widget": app.root})())
    assert app.mode != before
