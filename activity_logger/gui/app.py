"""Aplikasi utama: shell (sidebar + topbar), routing halaman, dan aksi global."""

from __future__ import annotations

import os
import shutil
import sys
import tkinter as tk
from tkinter import filedialog
from typing import Dict, List, Optional, Tuple

from ..core import exporter, stats, timeutil
from ..core.mobile_server import MobileServer
from ..core.models import Activity
from ..core.settings import Settings
from ..core.storage import ActivityStore, StorageError
from . import icons
from .appicon import load_icon
from .theme import FontBook, ThemeManager
from .widgets import (
    IconButton,
    NavItem,
    Toast,
    confirm,
    install_wheel_support,
    prompt,
)

APP_TITLE = "Activity Logger"
SIDEBAR_WIDTH = 236
SIDEBAR_COLLAPSED = 70

BOTTOM_NAV_ITEMS = [
    ("beranda", "Beranda", "home"),
    ("lokasi", "Lokasi", "folder"),
    ("catatan", "Catatan", "list"),
    ("total", "Total", "chart"),
    ("export", "Export", "download"),
]

NAV_ITEMS = [
    ("beranda", "Beranda", "home"),
    ("lokasi", "Lokasi JSON", "folder"),
    ("catatan", "Catatan Kegiatan", "list"),
    ("total", "Total Kegiatan", "chart"),
    ("export", "Export", "download"),
    ("hapus", "Hapus Semua", "trash"),
]


def _page_classes():
    """Impor halaman secara malas agar startup tetap ringan."""
    from .pages.dashboard import DashboardPage
    from .pages.delete_page import DeletePage
    from .pages.export_page import ExportPage
    from .pages.location_page import LocationPage
    from .pages.log_page import LogPage
    from .pages.settings_page import SettingsPage
    from .pages.stats_page import StatsPage

    return {
        "beranda": DashboardPage,
        "lokasi": LocationPage,
        "catatan": LogPage,
        "total": StatsPage,
        "export": ExportPage,
        "hapus": DeletePage,
        "pengaturan": SettingsPage,
    }


class ActivityApp:
    """Jendela utama aplikasi Activity Logger."""

    def __init__(self, settings: Optional[Settings] = None, store: Optional[ActivityStore] = None) -> None:
        self.settings = settings or Settings.load()
        self.settings.normalize()
        self.store = store or ActivityStore(
            self.settings.data_path, mirror_markdown=self.settings.mirror_markdown
        )
        if store is None:
            self.store.load()

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title(APP_TITLE)
        self.root.minsize(430, 560)
        self.icon_image = load_icon(self.root)

        self.mode = self.settings.theme
        self.themes = ThemeManager(self.root, self.mode)
        self.pal: Dict[str, str] = self.themes.pal
        self.fonts: FontBook = self.themes.fonts

        self.mobile = MobileServer(self.store, self.settings.mobile_port)
        self._mobile_revision = 0

        self.pages = _page_classes()
        self.page = None
        self.page_key: Optional[str] = None
        self.sidebar_mode = "expanded"
        self.sidebar: Optional[tk.Frame] = None
        self.drawer: Optional[tk.Frame] = None
        self.scrim: Optional[tk.Frame] = None
        self.toast_widget: Optional[Toast] = None
        self.last_export: Optional[str] = None
        self.focus_quick_add_on_load = False

        self.state: Dict[str, object] = {
            "log_query": "",
            "log_period": "month",
            "log_status": "all",
            "log_page": 1,
            "log_start": "",
            "log_end": "",
            "stats_period": "month",
            "stats_start": "",
            "stats_end": "",
            "export_start": "",
            "export_end": "",
        }
        self.metrics: Dict[str, object] = {
            "bp": "lg",
            "pad": 28,
            "gap": 16,
            "card_pad": 18,
            "narrow": False,
        }
        self.content_width = 900

        self._resize_job: Optional[str] = None
        install_wheel_support(self.root)
        self._restore_geometry()
        self._bind_shortcuts()

        self.shell = tk.Frame(self.root, bg=self.pal["page"])
        self.shell.pack(fill="both", expand=True)
        self._build_shell()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self._apply_breakpoint(force=True)
        start_page = self.settings.last_page if self.settings.last_page in self.pages else "beranda"
        if start_page not in self.pages:
            start_page = "beranda"
        self.navigate(start_page, save=False)
        self.root.deiconify()
        self.root.after(140, self._poll_mobile)
        self.root.after(60, lambda: self.root.focus_force())
        if self.store.load_error:
            message = self.store.load_error
            self.root.after(600, lambda: self.toast(message, kind="error"))
        if self.settings.mobile_autostart:
            self.root.after(300, lambda: self._start_mobile(silent=True))

    # ------------------------------------------------------------------ #
    # Jendela
    # ------------------------------------------------------------------ #
    def _restore_geometry(self) -> None:
        geometry = (self.settings.window_geometry or "").strip()
        restored = False
        if geometry:
            try:
                self.root.geometry(geometry)
                restored = True
            except tk.TclError:
                restored = False
        if not restored:
            width, height = 1180, 780
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            width = min(width, max(430, screen_w - 80))
            height = min(height, max(560, screen_h - 120))
            x = max(0, (screen_w - width) // 2)
            y = max(0, (screen_h - height) // 2 - 20)
            geometry = "{}x{}+{}+{}".format(width, height, x, y)
            self.root.geometry(geometry)
        self._initial_width = _geometry_width(geometry)

    def _save_geometry(self) -> None:
        try:
            self.settings.window_geometry = self.root.wm_geometry()
        except tk.TclError:  # pragma: no cover
            pass

    # ------------------------------------------------------------------ #
    # Shell
    # ------------------------------------------------------------------ #
    def _build_shell(self) -> None:
        self.pal = self.themes.pal
        self.fonts = self.themes.fonts
        self.root.configure(bg=self.pal["page"])

        self.content = None
        self.sidebar = self._build_sidebar(self.shell, collapsed=False)
        self.sidebar.pack(side="left", fill="y")

        self.main = tk.Frame(self.shell, bg=self.pal["page"])
        self.main.pack(side="left", fill="both", expand=True)

        self._build_topbar()

        self.content = tk.Frame(self.main, bg=self.pal["page"])
        self.content.pack(fill="both", expand=True)

        self.toast_widget = Toast(self.main, self.pal, self.fonts)
        self.bottom_nav = self._build_bottom_nav()
        self.drawer = None
        self.scrim = None

    def _build_sidebar(self, parent: tk.Misc, collapsed: bool, drawer: bool = False) -> tk.Frame:
        pal = self.pal
        width = 252 if drawer else (SIDEBAR_COLLAPSED if collapsed else SIDEBAR_WIDTH)
        sidebar = tk.Frame(parent, bg=pal["sidebar"], width=width, bd=0)
        sidebar.pack_propagate(False)

        # -- logo ------------------------------------------------------- #
        brand = tk.Frame(sidebar, bg=pal["sidebar"])
        brand.pack(fill="x", pady=(16, 14))
        logo = tk.Canvas(
            brand, width=30, height=30, bg=pal["sidebar"],
            highlightthickness=0, bd=0, takefocus=0,
        )
        if collapsed and not drawer:
            logo.pack()
        else:
            logo.pack(side="left", padx=(18, 10))
        logo.create_rectangle(0, 0, 30, 30, fill=pal["primary"], outline=pal["primary"])
        icons.paint(logo, "calendar", pal["primary_text"], size=18)
        if not collapsed or drawer:
            name_box = tk.Frame(brand, bg=pal["sidebar"])
            name_box.pack(side="left", fill="x", expand=True)
            tk.Label(
                name_box,
                text=APP_TITLE,
                bg=pal["sidebar"],
                fg=pal["sidebar_text_active"],
                font=self.fonts.get(12, "bold"),
                anchor="w",
            ).pack(fill="x")
            tk.Label(
                name_box,
                text="Pencatat kegiatan harian",
                bg=pal["sidebar"],
                fg=pal["sidebar_muted"],
                font=self.fonts.get(8),
                anchor="w",
            ).pack(fill="x")
        if drawer:
            close = IconButton(
                brand,
                "x",
                command=self._close_drawer,
                pal=pal,
                size=14,
                pad=6,
                bg=pal["sidebar"],
                fg=pal["sidebar_text"],
                hover_bg=pal["sidebar_soft"],
                hover_fg=pal["sidebar_text_active"],
            )
            close.pack(side="right", padx=(0, 12))

        # -- navigasi --------------------------------------------------- #
        nav = tk.Frame(sidebar, bg=pal["sidebar"])
        nav.pack(fill="x", pady=(2, 0))
        items = {}
        for key, label, icon in NAV_ITEMS:
            item = NavItem(
                nav,
                pal,
                self.fonts,
                icon=icon,
                label=label,
                command=lambda k=key: self.navigate(k),
                active=(key == self.page_key),
                collapsed=collapsed and not drawer,
            )
            item.pack(fill="x", padx=(8, 8), pady=1)
            items[key] = item
        if not drawer:
            self._nav_items = items

        # -- footer ----------------------------------------------------- #
        footer = tk.Frame(sidebar, bg=pal["sidebar"])
        footer.pack(side="bottom", fill="x", pady=(0, 10))

        gear_row = tk.Frame(footer, bg=pal["sidebar"])
        gear_row.pack(fill="x", padx=(14, 10), pady=(0, 8))
        if not collapsed or drawer:
            dot = tk.Canvas(
                gear_row, width=10, height=10, bg=pal["sidebar"],
                highlightthickness=0, bd=0, takefocus=0,
            )
            dot.pack(side="left")
            dot.create_oval(1, 1, 9, 9, fill=pal["primary"], outline=pal["primary"])
            tk.Label(
                gear_row,
                text="Data tersimpan di:",
                bg=pal["sidebar"],
                fg=pal["sidebar_muted"],
                font=self.fonts.get(8),
                anchor="w",
            ).pack(side="left", padx=(6, 0))
        IconButton(
            gear_row,
            "gear",
            command=lambda: self.navigate("pengaturan"),
            pal=pal,
            size=15,
            pad=5,
            bg=pal["sidebar"],
            fg=pal["sidebar_text"],
            hover_bg=pal["sidebar_soft"],
            hover_fg=pal["sidebar_text_active"],
            tooltip="Pengaturan",
        ).pack(side="right")

        if not collapsed or drawer:
            path = tk.Label(
                footer,
                text=self._short_path(),
                bg=pal["sidebar"],
                fg=pal["sidebar_text"],
                font=self.fonts.mono(8),
                anchor="w",
                justify="left",
                wraplength=width - 30,
            )
            path.pack(fill="x", padx=16, pady=(0, 2))
        return sidebar

    def _build_bottom_nav(self) -> tk.Frame:
        """Bilah navigasi bawah untuk layar sempit (gaya aplikasi HP)."""
        pal = self.pal
        border = tk.Frame(self.main, bg=pal["border"], height=1)
        bar = tk.Frame(self.main, bg=pal["surface"], height=58)
        bar.pack_propagate(False)
        bar._border = border  # type: ignore[attr-defined]

        items = {}
        for key, label, icon in BOTTOM_NAV_ITEMS:
            cell = tk.Frame(bar, bg=pal["surface"], cursor="hand2")
            cell.pack(side="left", fill="both", expand=True, pady=6)
            canvas = tk.Canvas(
                cell,
                width=20,
                height=20,
                bg=pal["surface"],
                highlightthickness=0,
                bd=0,
                takefocus=0,
            )
            canvas.pack()
            text = tk.Label(
                cell,
                text=label,
                bg=pal["surface"],
                fg=pal["text_muted"],
                font=self.fonts.get(8),
            )
            text.pack(pady=(1, 0))
            for widget in (cell, canvas, text):
                widget.bind("<Button-1>", lambda _event, k=key: self.navigate(k))
            items[key] = (cell, canvas, text, icon)
        bar._items = items  # type: ignore[attr-defined]
        bar._visible = False  # type: ignore[attr-defined]
        self._bottom_items = items
        return bar

    def _refresh_bottom_nav(self) -> None:
        pal = self.pal
        for key, (cell, canvas, text, icon) in getattr(self, "_bottom_items", {}).items():
            active = key == self.page_key
            fg = pal["primary"] if active else pal["text_muted"]
            try:
                cell.configure(bg=pal["surface"])
                canvas.configure(bg=pal["surface"])
                text.configure(bg=pal["surface"], fg=fg)
            except tk.TclError:  # pragma: no cover
                continue
            icons.paint(canvas, icon, fg, size=20)
            try:
                text.configure(font=self.fonts.get(8, "bold" if active else "normal"))
            except tk.TclError:  # pragma: no cover
                pass

    def _show_bottom_nav(self, visible: bool) -> None:
        bar = getattr(self, "bottom_nav", None)
        if bar is None:
            return
        try:
            if visible and not getattr(bar, "_visible", False):
                bar._border.pack(side="bottom", fill="x")  # type: ignore[attr-defined]
                bar.pack(side="bottom", fill="x")
                bar._visible = True  # type: ignore[attr-defined]
                self._refresh_bottom_nav()
                if self.toast_widget is not None:
                    self.toast_widget.bottom_offset = 66
                    self.toast_widget.lift()
            elif not visible and getattr(bar, "_visible", False):
                bar.pack_forget()
                bar._border.pack_forget()  # type: ignore[attr-defined]
                bar._visible = False  # type: ignore[attr-defined]
                if self.toast_widget is not None:
                    self.toast_widget.bottom_offset = 0
        except tk.TclError:  # pragma: no cover
            pass

    def _short_path(self, limit: int = 46) -> str:
        path = self.store.path
        home = os.path.expanduser("~")
        if path.startswith(home):
            path = "~" + path[len(home) :]
        if len(path) > limit:
            path = "…" + path[-(limit - 1) :]
        return path

    def _build_topbar(self) -> None:
        pal = self.pal
        for child in list(self.main.winfo_children()):
            if getattr(child, "_is_topbar", False):
                child.destroy()

        topbar = tk.Frame(self.main, bg=pal["page"], height=58)
        topbar._is_topbar = True  # type: ignore[attr-defined]
        if getattr(self, "content", None) is not None and self.content.winfo_exists():
            topbar.pack(fill="x", before=self.content)
        else:
            topbar.pack(fill="x")
        topbar.pack_propagate(False)

        left = tk.Frame(topbar, bg=pal["page"])
        left.pack(side="left", fill="x", expand=True, padx=(int(self.metrics["pad"]), 0))
        page = self.pages.get(self.page_key or "beranda")
        title = getattr(page, "title", "Beranda") if page else "Beranda"
        self._topbar_title = tk.Label(
            left,
            text=title,
            bg=pal["page"],
            fg=pal["text"],
            font=self.fonts.get(12, "bold"),
            anchor="w",
        )
        self._topbar_title.pack(side="top", pady=(12, 0), fill="x")
        self._topbar_sub = tk.Label(
            left,
            text="Aktivitas tersimpan otomatis ke file JSON",
            bg=pal["page"],
            fg=pal["text_faint"],
            font=self.fonts.get(8),
            anchor="w",
        )
        self._topbar_sub.pack(side="top", fill="x")

        right = tk.Frame(topbar, bg=pal["page"])
        right.pack(side="right", padx=(0, int(self.metrics["pad"]) - 6))

        if self.sidebar_mode == "hidden":
            IconButton(
                right,
                "menu",
                command=self._open_drawer,
                pal=pal,
                size=17,
                pad=7,
                bg=pal["page"],
                fg=pal["text_muted"],
                hover_bg=pal["surface_hover"],
                hover_fg=pal["text"],
                tooltip="Menu",
            ).pack(side="left", padx=2)

        IconButton(
            right,
            "wifi" if not self.mobile.running else "wifi",
            command=self.toggle_mobile,
            pal=pal,
            size=17,
            pad=7,
            bg=pal["page"],
            fg=pal["primary"] if self.mobile.running else pal["text_muted"],
            hover_bg=pal["surface_hover"],
            hover_fg=pal["primary"],
            tooltip="Akses dari HP: aktif" if self.mobile.running else "Akses dari HP: nonaktif",
        ).pack(side="left", padx=2)

        IconButton(
            right,
            "moon" if self.mode == "light" else "sun",
            command=self.toggle_theme,
            pal=pal,
            size=17,
            pad=7,
            bg=pal["page"],
            fg=pal["text_muted"],
            hover_bg=pal["surface_hover"],
            hover_fg=pal["text"],
            tooltip="Mode gelap" if self.mode == "light" else "Mode terang",
        ).pack(side="left", padx=2)

        IconButton(
            right,
            "gear",
            command=lambda: self.navigate("pengaturan"),
            pal=pal,
            size=17,
            pad=7,
            bg=pal["page"],
            fg=pal["text_muted"],
            hover_bg=pal["surface_hover"],
            hover_fg=pal["text"],
            tooltip="Pengaturan",
        ).pack(side="left", padx=2)

        border = tk.Frame(self.main, bg=pal["border"], height=1)
        border._is_topbar = True  # type: ignore[attr-defined]
        if getattr(self, "content", None) is not None and self.content.winfo_exists():
            border.pack(fill="x", before=self.content)
        else:
            border.pack(fill="x")

    # ------------------------------------------------------------------ #
    # Navigasi
    # ------------------------------------------------------------------ #
    def navigate(self, key: str, save: bool = True) -> None:
        if key not in self.pages:
            key = "beranda"
        if self.page is not None:
            self.page.destroy()
            self.page = None
        self.page_key = key
        if save:
            self.settings.last_page = key
            self.settings.save()
        page_class = self.pages[key]
        self.content_width = self._content_width()
        self.page = page_class(self, self.content)
        self._refresh_nav()
        if hasattr(self, "_topbar_title") and self._topbar_title.winfo_exists():
            title = getattr(page_class, "title", "")
            self._topbar_title.configure(text=title)
        self.page.on_width(self.content_width)
        if self.drawer is not None:
            self._close_drawer()

    def _content_width(self) -> int:
        width = self.root.winfo_width()
        if width <= 1:  # pragma: no cover - jendela belum dipetakan
            width = 1180
        sidebar_width = {
            "expanded": SIDEBAR_WIDTH,
            "collapsed": SIDEBAR_COLLAPSED,
            "hidden": 0,
        }.get(self.sidebar_mode, SIDEBAR_WIDTH)
        return max(300, width - sidebar_width)

    def _refresh_nav(self) -> None:
        for key, item in getattr(self, "_nav_items", {}).items():
            item.active = key == self.page_key
            item._paint()
        self._refresh_bottom_nav()

    def _open_drawer(self) -> None:
        if self.drawer is not None:
            return
        pal = self.pal
        self.scrim = tk.Frame(self.shell, bg=pal["overlay"], bd=0)
        self.scrim.place(x=0, y=0, relwidth=1, relheight=1)
        self.scrim.bind("<Button-1>", lambda _event: self._close_drawer())

        self.drawer = self._build_sidebar(self.shell, collapsed=False, drawer=True)
        self.drawer.place(x=0, y=0, width=252, relheight=1)
        self.drawer.lift()

    def _close_drawer(self) -> None:
        for widget in (self.drawer, self.scrim):
            if widget is not None:
                try:
                    widget.destroy()
                except tk.TclError:  # pragma: no cover
                    pass
        self.drawer = None
        self.scrim = None

    # ------------------------------------------------------------------ #
    # Responsif
    # ------------------------------------------------------------------ #
    def _on_configure(self, _event=None) -> None:
        if self._resize_job is not None:
            try:
                self.root.after_cancel(self._resize_job)
            except (tk.TclError, ValueError):  # pragma: no cover
                pass
        self._resize_job = self.root.after(90, self._apply_breakpoint)

    def _breakpoint_for(self, width: int) -> Tuple[str, str]:
        if width >= 1060:
            return "lg", "expanded"
        if width >= 860:
            return "md", "expanded"
        if width >= 700:
            return "sm", "collapsed"
        return "xs", "hidden"

    def _apply_breakpoint(self, force: bool = False) -> None:
        self._resize_job = None
        width = self.root.winfo_width()
        if width <= 1:  # pragma: no cover - jendela belum dipetakan
            width = getattr(self, "_initial_width", 1180)
        bp, sidebar_mode = self._breakpoint_for(width)
        changed = force or bp != self.metrics.get("bp") or sidebar_mode != self.sidebar_mode

        presets = {
            "lg": {"pad": 28, "gap": 16, "card_pad": 18, "narrow": False},
            "md": {"pad": 22, "gap": 14, "card_pad": 16, "narrow": False},
            "sm": {"pad": 18, "gap": 12, "card_pad": 14, "narrow": True},
            "xs": {"pad": 14, "gap": 12, "card_pad": 12, "narrow": True},
        }
        self.metrics = dict(presets[bp])
        self.metrics["bp"] = bp

        sidebar_width = {
            "expanded": SIDEBAR_WIDTH,
            "collapsed": SIDEBAR_COLLAPSED,
            "hidden": 0,
        }[sidebar_mode]
        self.content_width = max(300, width - sidebar_width)

        if changed:
            previous_page = self.page
            if previous_page is not None:
                previous_page.destroy()
                self.page = None
            if self.sidebar is not None:
                try:
                    self.sidebar.destroy()
                except tk.TclError:  # pragma: no cover
                    pass
            self.sidebar_mode = sidebar_mode
            self.sidebar = self._build_sidebar(
                self.shell, collapsed=sidebar_mode == "collapsed"
            )
            if sidebar_mode == "hidden":
                self.sidebar.pack_forget()
            else:
                self.sidebar.pack(side="left", fill="y", before=self.main)
            self._build_topbar()
            self._show_bottom_nav(sidebar_mode == "hidden")
            if previous_page is not None:
                key = self.page_key
                self.page_key = None
                self.navigate(key or "beranda", save=False)
        elif self.page is not None:
            self.page.on_width(self.content_width)
            if hasattr(self, "_topbar_sub") and self._topbar_sub.winfo_exists():
                self._topbar_sub.configure(
                    text="" if self.metrics["narrow"] else "Aktivitas tersimpan otomatis ke file JSON"
                )

    # ------------------------------------------------------------------ #
    # Tema
    # ------------------------------------------------------------------ #
    def set_theme(self, mode: str) -> None:
        if mode == self.mode:
            return
        self.mode = mode if mode in ("light", "dark") else "light"
        self.settings.theme = self.mode
        self.settings.save()
        self.themes.switch(self.mode)
        self._rebuild_ui()

    def toggle_theme(self) -> None:
        self.set_theme("dark" if self.mode == "light" else "light")

    def _rebuild_ui(self) -> None:
        key = self.page_key or "beranda"
        if self.page is not None:
            self.page.destroy()
            self.page = None
        try:
            self.shell.destroy()
        except tk.TclError:  # pragma: no cover
            pass
        self.page_key = None
        self.shell = tk.Frame(self.root, bg=self.pal["page"])
        self.shell.pack(fill="both", expand=True)
        self._build_shell()
        self._apply_breakpoint(force=True)
        self.navigate(key, save=False)

    # ------------------------------------------------------------------ #
    # Umpan balik
    # ------------------------------------------------------------------ #
    def toast(self, message: str, kind: str = "success") -> None:
        if self.toast_widget is not None:
            self.toast_widget.show(message, kind=kind)

    def copy_to_clipboard(self, text: str, message: str = "Disalin ke clipboard") -> None:
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update_idletasks()
            self.toast(message)
        except tk.TclError:  # pragma: no cover
            self.toast("Tidak bisa menyalin ke clipboard", kind="error")

    def after(self, delay: int, callback=None):
        return self.root.after(delay, callback)

    # ------------------------------------------------------------------ #
    # Aksi data
    # ------------------------------------------------------------------ #
    def after_save(self, activity: Activity) -> None:
        """Hook setelah kegiatan baru tersimpan."""
        self._refresh_current(refresh_only=True)

    def _refresh_current(self, refresh_only: bool = True) -> None:
        if self.page is None:
            return
        try:
            if refresh_only:
                self.page.refresh()
            else:
                self.page.rebuild()
        except tk.TclError:  # pragma: no cover - halaman sedang dibangun
            pass

    def toggle_activity(self, activity: Activity) -> None:
        try:
            updated = self.store.toggle_done(activity.id)
        except StorageError as error:
            self.toast(str(error), kind="error")
            return
        self._refresh_current()
        self.toast(
            "Ditandai {}: {}".format(
                "selesai" if updated.done else "belum selesai", _ellipsis(updated.text)
            )
        )

    def edit_activity(self, activity: Activity) -> None:
        new_text = prompt(
            self,
            "Ubah kegiatan",
            "Perbarui teks kegiatan. Tanggal dan waktu asli tetap dipertahankan.",
            value=activity.text,
            confirm_label="Simpan perubahan",
        )
        if new_text is None:
            return
        if not new_text.strip():
            self.toast("Kegiatan tidak boleh kosong", kind="error")
            return
        try:
            self.store.update(activity.id, text=new_text)
        except (StorageError, ValueError) as error:
            self.toast(str(error), kind="error")
            return
        self._refresh_current()
        self.toast("Kegiatan diperbarui")

    def delete_activity(self, activity: Activity) -> None:
        if self.settings.confirm_delete:
            approved = confirm(
                self,
                "Hapus kegiatan?",
                '"{}"\n\nKegiatan ini akan dihapus dari file JSON.'.format(
                    _ellipsis(activity.text, 120)
                ),
                confirm_label="Hapus",
                danger=True,
            )
            if not approved:
                return
        try:
            self.store.delete(activity.id)
        except StorageError as error:
            self.toast(str(error), kind="error")
            return
        self._refresh_current()
        self.toast("Kegiatan dihapus")

    def delete_all(self) -> None:
        total = self.store.count()
        if total == 0:
            self.toast("Tidak ada data untuk dihapus", kind="info")
            return
        approved = confirm(
            self,
            "Hapus semua kegiatan?",
            "{} kegiatan akan dihapus dari file JSON.\n\nCadangan otomatis akan dibuat "
            "terlebih dahulu di folder backups/.".format(total),
            confirm_label="Ya, hapus semua",
            danger=True,
        )
        if not approved:
            return
        try:
            removed = self.store.clear(make_backup=True)
        except StorageError as error:
            self.toast(str(error), kind="error")
            return
        self.navigate("beranda")
        self.toast("{} kegiatan dihapus (cadangan tersimpan)".format(removed))

    def restore_backup(self, path: str) -> None:
        approved = confirm(
            self,
            "Pulihkan cadangan?",
            "Data saat ini akan diganti dengan isi cadangan:\n{}\n\nLanjutkan?".format(
                os.path.basename(path)
            ),
            confirm_label="Pulihkan",
        )
        if not approved:
            return
        try:
            self.store.backup("sebelum-pulihkan")
            shutil.copy2(path, self.store.path)
            self.store.load()
        except (OSError, StorageError) as error:
            self.toast("Gagal memulihkan: {}".format(error), kind="error")
            return
        self.navigate("catatan")
        self.toast("Cadangan dipulihkan")

    def reload_store(self) -> None:
        self.store.load()
        self._refresh_current(refresh_only=False)
        if self.store.load_error:
            self.toast(self.store.load_error, kind="error")
        else:
            self.toast("Data dimuat ulang dari file")

    # ------------------------------------------------------------------ #
    # Lokasi penyimpanan
    # ------------------------------------------------------------------ #
    def change_location(self) -> None:
        current = self.store.path
        folder = os.path.dirname(current)
        target = filedialog.asksaveasfilename(
            parent=self.root,
            title="Pilih file penyimpanan kegiatan",
            initialdir=folder if os.path.isdir(folder) else os.path.expanduser("~"),
            initialfile=os.path.basename(current) or "kegiatan.json",
            defaultextension=".json",
            filetypes=[("File JSON", "*.json"), ("Semua file", "*.*")],
        )
        if not target:
            return
        if os.path.abspath(target) == os.path.abspath(current):
            self.toast("Lokasi tidak berubah", kind="info")
            return
        try:
            self.store.relocate(target)
        except (StorageError, OSError) as error:
            self.toast("Gagal memindahkan: {}".format(error), kind="error")
            return
        self.settings.data_path = self.store.path
        self.settings.save()
        self._rebuild_ui()
        self.toast("Lokasi file diperbarui")

    def open_folder(self, path: str) -> None:
        folder = path or "."
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                os.system('open "{}"'.format(folder))
            else:
                os.system('xdg-open "{}" >/dev/null 2>&1 &'.format(folder))
            self.toast("Membuka folder")
        except Exception as error:  # pragma: no cover - tergantung OS
            self.toast("Tidak bisa membuka folder: {}".format(error), kind="error")

    @property
    def exports_dir(self) -> str:
        return os.path.join(os.path.dirname(self.store.path) or ".", "exports")

    def open_exports_folder(self) -> None:
        os.makedirs(self.exports_dir, exist_ok=True)
        self.open_folder(self.exports_dir)

    # ------------------------------------------------------------------ #
    # Ekspor
    # ------------------------------------------------------------------ #
    def _write_export(
        self,
        kind: str,
        items: List[Activity],
        slug: str,
        title: str,
        subtitle: str,
        summary: bool = False,
    ) -> Optional[str]:
        kind = kind.lower()
        try:
            if summary:
                content = exporter.csv_daily_summary(items)
                extension = "csv"
                filename = exporter.default_filename("csv", "csv", "ringkasan-" + slug)
            else:
                content = exporter.build_export(kind, items, title=title, subtitle=subtitle)
                extension = exporter.EXTENSIONS.get(kind, "txt")
                filename = exporter.default_filename(kind, extension, slug)
            folder = self.exports_dir
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, filename)
            exporter.write_text_file(
                path, content, excel_friendly=(extension == "csv")
            )
        except (OSError, ValueError) as error:
            self.toast("Gagal mengekspor: {}".format(error), kind="error")
            return None
        self.last_export = path
        self.toast(
            "{} · {} kegiatan → {}".format(
                extension.upper(), len(items), os.path.basename(path)
            )
        )
        return path

    def export_all(self, kind: str) -> Optional[str]:
        items = self.store.all()
        if not items:
            self.toast("Belum ada kegiatan untuk diekspor", kind="info")
            return None
        return self._write_export(
            kind, items, "semua", "Semua Kegiatan", "Seluruh catatan kegiatan"
        )

    def export_month(self, kind: str) -> Optional[str]:
        today = timeutil.today()
        start, end = timeutil.month_bounds(today.year, today.month)
        items = self.store.between(start, end)
        if not items:
            self.toast("Belum ada kegiatan bulan ini", kind="info")
            return None
        label = timeutil.month_label(today.year, today.month)
        return self._write_export(
            kind,
            items,
            timeutil.month_key(today),
            "Kegiatan {}".format(label),
            "Rekap bulan {}".format(label),
        )

    def export_range(self, kind: str, bounds, slug: str) -> Optional[str]:
        start, end = bounds
        period = stats.resolve_period("custom", start=start, end=end)
        items = stats.filter_activities(self.store.all(), period=period)
        if not items:
            self.toast("Tidak ada kegiatan pada rentang tersebut", kind="info")
            return None
        label = "{} – {}".format(
            timeutil.fmt_date_short(start), timeutil.fmt_date_short(end)
        )
        return self._write_export(
            kind, items, slug, "Kegiatan {}".format(label), "Rentang {}".format(label)
        )

    def export_summary_csv(self, bounds, slug: str) -> Optional[str]:
        start, end = bounds
        period = stats.resolve_period("custom", start=start, end=end)
        items = stats.filter_activities(self.store.all(), period=period)
        if not items:
            self.toast("Tidak ada kegiatan pada rentang tersebut", kind="info")
            return None
        return self._write_export(
            "csv", items, slug, "Ringkasan Harian", "Ringkasan", summary=True
        )

    def export_period(self, kind: str = "csv") -> Optional[str]:
        key = str(self.state.get("stats_period", "month"))
        start = (
            timeutil.parse_date(str(self.state.get("stats_start", "")))
            if self.state.get("stats_start")
            else None
        )
        end = (
            timeutil.parse_date(str(self.state.get("stats_end", "")))
            if self.state.get("stats_end")
            else None
        )
        period = stats.resolve_period(key, start=start, end=end)
        items = stats.filter_activities(self.store.all(), period=period)
        if not items:
            self.toast("Belum ada kegiatan pada periode ini", kind="info")
            return None
        return self._write_export(
            kind,
            items,
            period.slug,
            "Kegiatan {}".format(period.label),
            period.label,
        )

    def month_slug(self) -> str:
        return timeutil.month_key(timeutil.today())

    # ------------------------------------------------------------------ #
    # Preferensi
    # ------------------------------------------------------------------ #
    def set_show_seconds(self, value: bool) -> None:
        self.settings.show_seconds = bool(value)
        self.settings.save()
        self._refresh_current(refresh_only=False)

    def set_confirm_delete(self, value: bool) -> None:
        self.settings.confirm_delete = bool(value)
        self.settings.save()
        self.toast("Preferensi konfirmasi diperbarui")

    def set_mirror_markdown(self, value: bool) -> None:
        self.settings.mirror_markdown = bool(value)
        self.settings.save()
        self.store.mirror_markdown = bool(value)
        if value:
            try:
                self.store.write_markdown()
                self.toast("Cermin Markdown diaktifkan")
            except OSError as error:
                self.toast("Gagal menulis Markdown: {}".format(error), kind="error")
        else:
            self.toast("Cermin Markdown dimatikan")

    # ------------------------------------------------------------------ #
    # Server mobile
    # ------------------------------------------------------------------ #
    def _start_mobile(self, silent: bool = False) -> None:
        try:
            url = self.mobile.start(self.settings.mobile_port)
        except OSError as error:
            self.toast("Tidak bisa mengaktifkan akses HP: {}".format(error), kind="error")
            return
        self.settings.mobile_port = self.mobile.port
        self.settings.save()
        self._build_topbar()
        if self.page_key == "pengaturan":
            self._refresh_current(refresh_only=False)
        if not silent:
            self.toast("Akses HP aktif: {}".format(url))

    def _stop_mobile(self) -> None:
        self.mobile.stop()
        self._build_topbar()
        if self.page_key == "pengaturan":
            self._refresh_current(refresh_only=False)
        self.toast("Akses HP dimatikan", kind="info")

    def toggle_mobile(self) -> None:
        if self.mobile.running:
            self._stop_mobile()
        else:
            self._start_mobile()

    def _poll_mobile(self) -> None:
        try:
            if self.mobile.running and self.mobile.revision != self._mobile_revision:
                self._mobile_revision = self.mobile.revision
                self._refresh_current()
                self.toast("Diperbarui dari HP", kind="info")
        except tk.TclError:  # pragma: no cover
            return
        try:
            self.root.after(1500, self._poll_mobile)
        except tk.TclError:  # pragma: no cover
            pass

    # ------------------------------------------------------------------ #
    # Pintasan keyboard
    # ------------------------------------------------------------------ #
    def _bind_shortcuts(self) -> None:
        modifiers = ("Control", "Command") if sys.platform == "darwin" else ("Control",)
        bindings = [
            ("n", self._shortcut_new),
            ("f", self._shortcut_search),
            ("e", lambda: self.export_month("csv")),
            ("E", lambda: self.export_all("csv")),  # Ctrl+Shift+E
            ("d", self.toggle_theme),
            ("m", self.toggle_mobile),
            ("q", self.on_close),
            ("1", lambda: self.navigate("beranda")),
            ("2", lambda: self.navigate("lokasi")),
            ("3", lambda: self.navigate("catatan")),
            ("4", lambda: self.navigate("total")),
            ("5", lambda: self.navigate("export")),
            ("6", lambda: self.navigate("hapus")),
        ]
        for modifier in modifiers:
            for key, handler in bindings:
                try:
                    self.root.bind_all(
                        "<{}-{}>".format(modifier, key),
                        lambda _event, fn=handler: (fn(), "break")[1],
                    )
                except tk.TclError:  # pragma: no cover
                    pass
        self.root.bind_all("<F5>", lambda _event: (self.reload_store(), "break")[1])
        self.root.bind_all("<Escape>", lambda _event: self._on_escape())
        self.root.bind("<Configure>", self._on_configure)

    def _on_escape(self) -> None:
        if self.drawer is not None:
            self._close_drawer()

    def _shortcut_new(self) -> None:
        if self.page_key != "beranda":
            self.focus_quick_add_on_load = True
            self.navigate("beranda")
        elif self.page is not None and hasattr(self.page, "focus_input"):
            self.page.focus_input()

    def _shortcut_search(self) -> None:
        if self.page_key != "catatan":
            self.navigate("catatan")
        self.focus_page_search()

    def focus_page_search(self) -> None:
        page = self.page
        if page is None:
            return
        field = getattr(page, "search", None)
        if field is not None:
            field.focus()

    # ------------------------------------------------------------------ #
    # Tutup
    # ------------------------------------------------------------------ #
    def on_close(self) -> None:
        try:
            self._save_geometry()
            self.settings.save()
        except Exception:  # pragma: no cover
            pass
        try:
            self.mobile.stop()
        except Exception:  # pragma: no cover
            pass
        try:
            self.root.destroy()
        except tk.TclError:  # pragma: no cover
            pass

    def run(self) -> None:
        self.root.mainloop()


def _geometry_width(geometry: str, fallback: int = 1180) -> int:
    """Ambil lebar dari string geometri Tk seperti ``980x700+10+10``."""
    try:
        head = str(geometry).split("+")[0]
        return int(head.split("x")[0])
    except (TypeError, ValueError, IndexError):
        return fallback


def _ellipsis(text: str, limit: int = 60) -> str:
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def run(settings: Optional[Settings] = None) -> int:
    """Buka aplikasi dengan pengaturan tertentu lalu jalankan event loop."""
    try:
        app = ActivityApp(settings=settings)
    except tk.TclError as error:
        print("Tidak bisa membuka jendela aplikasi: {}".format(error), file=sys.stderr)
        print(
            "Pastikan kamu menjalankan aplikasi di lingkungan desktop "
            "(bukan SSH tanpa layar).",
            file=sys.stderr,
        )
        return 1
    app.run()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Alias kompatibel: delegasikan ke modul ``cli``."""
    from ..cli import main as cli_main

    return cli_main(argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
