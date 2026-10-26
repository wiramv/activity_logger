"""Halaman Pengaturan: tampilan, penyimpanan, akses HP, dan pintasan."""

from __future__ import annotations

import os
import platform
import tkinter as tk

from ... import __version__
from ...core import timeutil
from .. import icons
from ..widgets import Badge, Button, CheckboxRow, Chip
from .base import BasePage

SHORTCUTS = [
    ("Ctrl + N", "Fokus ke kotak input cepat"),
    ("Ctrl + F", "Cari kegiatan di halaman Catatan"),
    ("Ctrl + Shift + E", "Export CSV bulan ini"),
    ("Ctrl + Shift + A", "Export CSV semua kegiatan"),
    ("Ctrl + Shift + D", "Ganti mode terang / gelap"),
    ("Ctrl + Shift + M", "Aktifkan / matikan akses dari HP"),
    ("Ctrl + 1 … 7", "Pindah antar halaman"),
    ("F5", "Muat ulang data dari file"),
    ("Esc", "Tutup menu / dialog"),
]


class SettingsPage(BasePage):
    key = "pengaturan"
    title = "Pengaturan"
    subtitle = "Sesuaikan tampilan, penyimpanan, dan akses dari perangkat lain."
    icon = "gear"

    def build(self) -> None:
        self.heading()
        self._build_appearance()
        self._build_storage()
        self._build_mobile()
        self._build_shortcuts()
        self._build_about()

    # ------------------------------------------------------------------ #
    def _build_appearance(self) -> None:
        card = self.card()
        body = card.body
        self._card_title(body, "Tampilan", "sun")

        row = tk.Frame(body, bg=self.pal["surface"])
        row.pack(fill="x", pady=(10, 0))
        tk.Label(
            row,
            text="Mode warna",
            bg=self.pal["surface"],
            fg=self.pal["text"],
            font=self.fonts.get(10),
        ).pack(side="left")
        chips = tk.Frame(row, bg=self.pal["surface"])
        chips.pack(side="right")
        for mode, label, icon_name in (
            ("light", "Terang", "sun"),
            ("dark", "Gelap", "moon"),
        ):
            Chip(
                chips,
                label,
                self.pal,
                self.fonts,
                command=lambda m=mode: self.app.set_theme(m),
                active=(self.app.mode == mode),
                size="sm",
            ).pack(side="left", padx=(6, 0))

        self._divider(body)
        CheckboxRow(
            body,
            self.pal,
            self.fonts,
            label="Tampilkan detik pada waktu",
            description="Contoh: 06:45:12 (lebih presisi untuk pencatatan detail).",
            value=self.app.settings.show_seconds,
            command=self.app.set_show_seconds,
        ).pack(fill="x")
        self._divider(body)
        CheckboxRow(
            body,
            self.pal,
            self.fonts,
            label="Konfirmasi sebelum menghapus",
            description="Tampilkan dialog konfirmasi saat menghapus satu kegiatan.",
            value=self.app.settings.confirm_delete,
            command=self.app.set_confirm_delete,
        ).pack(fill="x")

    def _build_storage(self) -> None:
        card = self.card()
        body = card.body
        self._card_title(body, "Penyimpanan", "folder")

        tk.Label(
            body,
            text=self.app.store.path,
            bg=self.pal["surface"],
            fg=self.pal["text"],
            font=self.fonts.mono(9),
            anchor="w",
            justify="left",
            wraplength=self._text_width(),
        ).pack(fill="x", pady=(10, 4))
        tk.Label(
            body,
            text="{} kegiatan · {} · format JSON Lines".format(
                self.app.store.count(), _format_size(self._file_size())
            ),
            bg=self.pal["surface"],
            fg=self.pal["text_faint"],
            font=self.fonts.get(9),
            anchor="w",
        ).pack(fill="x")

        buttons = tk.Frame(body, bg=self.pal["surface"])
        buttons.pack(fill="x", pady=(12, 0))
        Button(
            buttons,
            text="Ubah Lokasi",
            command=self.app.change_location,
            variant="outline",
            pal=self.pal,
            fonts=self.fonts,
            icon="folder",
            size="sm",
        ).pack(side="left" if not self.narrow else "top", fill="x" if self.narrow else "none")
        Button(
            buttons,
            text="Buka Folder",
            command=lambda: self.app.open_folder(os.path.dirname(self.app.store.path)),
            variant="ghost",
            pal=self.pal,
            fonts=self.fonts,
            icon="external",
            size="sm",
        ).pack(
            side="left" if not self.narrow else "top",
            fill="x" if self.narrow else "none",
            padx=(0 if self.narrow else 8, 0),
            pady=(6, 0) if self.narrow else 0,
        )

        self._divider(body)
        CheckboxRow(
            body,
            self.pal,
            self.fonts,
            label="Simpan juga versi Markdown per bulan",
            description="Menulis file kegiatan-YYYY-MM.md setiap kali data berubah.",
            value=self.app.settings.mirror_markdown,
            command=self.app.set_mirror_markdown,
        ).pack(fill="x")

    def _build_mobile(self) -> None:
        card = self.card()
        body = card.body
        running = self.app.mobile.running
        head = tk.Frame(body, bg=self.pal["surface"])
        head.pack(fill="x")
        title_box = self._card_title(head, "Akses dari HP (Wi-Fi yang sama)", "wifi", pack=False)
        title_box.pack(side="left")
        Badge(
            head,
            "Aktif" if running else "Nonaktif",
            self.pal,
            self.fonts,
            tone="primary" if running else "muted",
        ).pack(side="left", padx=(8, 0))

        tk.Label(
            body,
            text="Buka Activity Logger dari browser HP di jaringan Wi-Fi yang sama, "
            "lalu catat kegiatan langsung dari HP. Data masuk ke file JSON yang sama.",
            bg=self.pal["surface"],
            fg=self.pal["text_muted"],
            font=self.fonts.get(10),
            anchor="w",
            justify="left",
            wraplength=self._text_width(),
        ).pack(fill="x", pady=(8, 12))

        if running:
            url_box = tk.Frame(
                body,
                bg=self.pal["surface_soft"],
                highlightthickness=1,
                highlightbackground=self.pal["border"],
            )
            url_box.pack(fill="x")
            inner = tk.Frame(url_box, bg=self.pal["surface_soft"])
            inner.pack(fill="x", padx=12, pady=10)
            canvas = tk.Canvas(
                inner, width=16, height=16, bg=self.pal["surface_soft"],
                highlightthickness=0, bd=0, takefocus=0,
            )
            canvas.pack(side="left")
            icons.paint(canvas, "wifi", self.pal["primary"], size=16)
            self._url_label = tk.Label(
                inner,
                text=self.app.mobile.url(),
                bg=self.pal["surface_soft"],
                fg=self.pal["text"],
                font=self.fonts.mono(11),
                anchor="w",
            )
            self._url_label.pack(side="left", padx=(8, 0))
            Button(
                inner,
                text="Salin",
                command=lambda: self.app.copy_to_clipboard(self.app.mobile.url(), "Tautan disalin"),
                variant="link",
                pal=self.pal,
                fonts=self.fonts,
                size="sm",
                icon="copy",
            ).pack(side="right")

        row = tk.Frame(body, bg=self.pal["surface"])
        row.pack(fill="x", pady=(12, 0))
        Button(
            row,
            text="Matikan Akses HP" if running else "Aktifkan Akses HP",
            command=self.app.toggle_mobile,
            variant="danger_outline" if running else "primary",
            pal=self.pal,
            fonts=self.fonts,
            icon="wifi",
            size="md",
        ).pack(side="left" if not self.narrow else "top", fill="x" if self.narrow else "none")
        tk.Label(
            body,
            text="Port: {} · hanya bisa diakses dari jaringan lokal (bukan internet).".format(
                self.app.mobile.actual_port if running else self.app.settings.mobile_port
            ),
            bg=self.pal["surface"],
            fg=self.pal["text_faint"],
            font=self.fonts.get(8),
            anchor="w",
            justify="left",
            wraplength=self._text_width(),
        ).pack(fill="x", pady=(8, 0))

    def _build_shortcuts(self) -> None:
        card = self.card()
        body = card.body
        self._card_title(body, "Pintasan Keyboard", "grid")
        grid = tk.Frame(body, bg=self.pal["surface"])
        grid.pack(fill="x", pady=(10, 0))
        for index, (keys, description) in enumerate(SHORTCUTS):
            tk.Label(
                grid,
                text=keys,
                bg=self.pal["surface_soft"],
                fg=self.pal["text"],
                font=self.fonts.mono(9),
                padx=8,
                pady=3,
                anchor="w",
            ).grid(row=index, column=0, sticky="w", pady=3, padx=(0, 12))
            tk.Label(
                grid,
                text=description,
                bg=self.pal["surface"],
                fg=self.pal["text_muted"],
                font=self.fonts.get(9),
                anchor="w",
                justify="left",
                wraplength=max(160, self._text_width() - 140),
            ).grid(row=index, column=1, sticky="w", pady=3)

    def _build_about(self) -> None:
        card = self.card()
        body = card.body
        self._card_title(body, "Tentang", "info")
        tk.Label(
            body,
            text="Activity Logger v{} — aplikasi pencatat kegiatan harian dengan Python "
            "Tkinter + Bootstrap style. Data disimpan lokal, tanpa server, tanpa akun.".format(
                __version__
            ),
            bg=self.pal["surface"],
            fg=self.pal["text_muted"],
            font=self.fonts.get(9),
            anchor="w",
            justify="left",
            wraplength=self._text_width(),
        ).pack(fill="x", pady=(10, 6))
        tk.Label(
            body,
            text="Python {} · {} · {}".format(
                platform.python_version(), platform.system(), timeutil.fmt_date_indonesian(timeutil.today())
            ),
            bg=self.pal["surface"],
            fg=self.pal["text_faint"],
            font=self.fonts.get(8),
            anchor="w",
        ).pack(fill="x")

    # ------------------------------------------------------------------ #
    def _card_title(self, parent: tk.Frame, text: str, icon: str, pack: bool = True) -> tk.Frame:
        box = tk.Frame(parent, bg=self.pal["surface"])
        if pack:
            box.pack(fill="x")
        canvas = tk.Canvas(
            box, width=16, height=16, bg=self.pal["surface"],
            highlightthickness=0, bd=0, takefocus=0,
        )
        canvas.pack(side="left")
        icons.paint(canvas, icon, self.pal["primary"], size=16)
        tk.Label(
            box,
            text=text,
            bg=self.pal["surface"],
            fg=self.pal["text"],
            font=self.fonts.h2,
        ).pack(side="left", padx=(8, 0))
        return box

    def _divider(self, parent: tk.Frame) -> None:
        tk.Frame(parent, height=1, bg=self.pal["border"]).pack(fill="x", pady=12)

    def _file_size(self) -> int:
        try:
            return os.path.getsize(self.app.store.path)
        except OSError:
            return 0

    def _text_width(self) -> int:
        return max(240, self.width - 2 * int(self.metrics["pad"]) - 2 * int(self.metrics["card_pad"]))


def _format_size(size: int) -> str:
    if size < 1024:
        return "{} B".format(size)
    if size < 1024 * 1024:
        return "{:.1f} KB".format(size / 1024)
    return "{:.1f} MB".format(size / (1024 * 1024))
