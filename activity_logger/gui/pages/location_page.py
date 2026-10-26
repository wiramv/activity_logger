"""Halaman Lokasi File JSON: lihat/pindah file, format data, dan cadangan."""

from __future__ import annotations

import json
import os
import tkinter as tk
from typing import List

from ...core import timeutil
from .. import icons
from ..widgets import Badge, Button, CheckboxRow, EmptyState
from .base import BasePage


class LocationPage(BasePage):
    key = "lokasi"
    title = "Lokasi File JSON"
    subtitle = "Tentukan lokasi file JSON untuk menyimpan data kegiatan."
    icon = "folder"

    def build(self) -> None:
        self.heading()
        self._build_current()
        self._build_format()
        self._build_backups()

    # ------------------------------------------------------------------ #
    # Kartu lokasi
    # ------------------------------------------------------------------ #
    def _build_current(self) -> None:
        card = self.card()
        body = card.body
        head = tk.Frame(body, bg=self.pal["surface"])
        head.pack(fill="x")
        tk.Label(
            head,
            text="Lokasi Saat Ini",
            bg=self.pal["surface"],
            fg=self.pal["text"],
            font=self.fonts.h2,
            anchor="w",
        ).pack(side="left")
        Badge(head, "Aktif", self.pal, self.fonts, tone="primary").pack(side="left", padx=(8, 0))

        path_row = tk.Frame(body, bg=self.pal["surface"])
        path_row.pack(fill="x", pady=(8, 0))
        self._path_label = tk.Label(
            path_row,
            text=self.app.store.path,
            bg=self.pal["surface"],
            fg=self.pal["text"],
            font=self.fonts.mono(10),
            anchor="w",
            justify="left",
            wraplength=self._text_width(),
        )
        self._path_label.pack(side="left", fill="x", expand=True)

        info = tk.Frame(body, bg=self.pal["surface"])
        info.pack(fill="x", pady=(6, 0))
        size_text = self._file_size()
        tk.Label(
            info,
            text="{} · {} kegiatan · {} baris JSON".format(
                "Ada" if os.path.exists(self.app.store.path) else "Belum dibuat",
                self.app.store.count(),
                self.app.store.count(),
            )
            + (" · {}".format(size_text) if size_text else ""),
            bg=self.pal["surface"],
            fg=self.pal["text_faint"],
            font=self.fonts.get(9),
            anchor="w",
            justify="left",
            wraplength=self._text_width(),
        ).pack(fill="x")

        buttons = tk.Frame(body, bg=self.pal["surface"])
        buttons.pack(fill="x", pady=(14, 0))
        specs = [
            ("Ubah Lokasi", self.app.change_location, "primary", "folder"),
            ("Buka Folder", lambda: self.app.open_folder(os.path.dirname(self.app.store.path)), "outline", "external"),
            ("Muat Ulang", self._reload, "ghost", "refresh"),
        ]
        for index, (label, command, variant, icon) in enumerate(specs):
            button = Button(
                buttons,
                text=label,
                command=command,
                variant=variant,
                pal=self.pal,
                fonts=self.fonts,
                icon=icon,
                size="md",
            )
            if self.narrow:
                button.pack(fill="x", pady=(0 if index == 0 else 6, 0))
            else:
                button.pack(side="left", padx=(0 if index == 0 else 8, 0))

    # ------------------------------------------------------------------ #
    # Kartu format
    # ------------------------------------------------------------------ #
    def _build_format(self) -> None:
        card = self.card()
        body = card.body
        tk.Label(
            body,
            text="Format File",
            bg=self.pal["surface"],
            fg=self.pal["text"],
            font=self.fonts.h2,
            anchor="w",
        ).pack(fill="x")

        note = tk.Frame(body, bg=self.pal["info_soft"])
        note.pack(fill="x", pady=(10, 12))
        inner = tk.Frame(note, bg=self.pal["info_soft"])
        inner.pack(fill="x", padx=12, pady=10)
        canvas = tk.Canvas(
            inner, width=16, height=16, bg=self.pal["info_soft"],
            highlightthickness=0, bd=0, takefocus=0,
        )
        canvas.pack(side="left", anchor="n", pady=(1, 0))
        icons.paint(canvas, "info", self.pal["info"], size=16)
        tk.Label(
            inner,
            text="File disimpan dalam format JSON Lines: satu baris = satu kegiatan, "
            "jadi mudah dibaca manusia dan tetap ringan untuk ribuan catatan. "
            "File berbentuk array JSON juga tetap bisa dibuka.",
            bg=self.pal["info_soft"],
            fg=self.pal["text"],
            font=self.fonts.get(9),
            anchor="w",
            justify="left",
            wraplength=max(200, self._text_width() - 60),
        ).pack(side="left", padx=(8, 0), fill="x", expand=True)

        tk.Label(
            body,
            text="Contoh Struktur JSON",
            bg=self.pal["surface"],
            fg=self.pal["text_muted"],
            font=self.fonts.get(9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        example = self._example_json()
        code = tk.Text(
            body,
            height=min(12, example.count("\n") + 1),
            bg=self.pal["surface_soft"],
            fg=self.pal["text"],
            font=self.fonts.mono(9),
            bd=0,
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.pal["border"],
            highlightcolor=self.pal["border"],
            padx=12,
            pady=10,
            wrap="none",
            cursor="arrow",
        )
        code.insert("1.0", example)
        code.bind("<Key>", lambda _event: "break")  # hanya-baca, warna tetap normal
        code.pack(fill="x")

        hint = tk.Frame(body, bg=self.pal["surface"])
        hint.pack(fill="x", pady=(10, 0))
        tk.Label(
            hint,
            text="Tip: file ini bisa dibuka di editor apa pun, di-backup, atau disinkronkan "
            "lewat Git/Dropbox.",
            bg=self.pal["surface"],
            fg=self.pal["text_faint"],
            font=self.fonts.get(8),
            anchor="w",
            justify="left",
            wraplength=self._text_width(),
        ).pack(fill="x")

        self.mirror_row = CheckboxRow(
            body,
            self.pal,
            self.fonts,
            label="Simpan juga versi Markdown per bulan",
            description="Setiap penyimpanan juga menulis kegiatan-YYYY-MM.md agar mudah dibaca.",
            value=self.app.settings.mirror_markdown,
            command=self.app.set_mirror_markdown,
        )
        self.mirror_row.pack(fill="x", pady=(14, 0))

    # ------------------------------------------------------------------ #
    # Kartu cadangan
    # ------------------------------------------------------------------ #
    def _build_backups(self) -> None:
        card = self.card(pad=0)
        header = tk.Frame(card.body, bg=self.pal["surface"])
        header.pack(
            fill="x",
            padx=int(self.metrics["card_pad"]),
            pady=(int(self.metrics["card_pad"]), 8),
        )
        tk.Label(
            header,
            text="Cadangan",
            bg=self.pal["surface"],
            fg=self.pal["text"],
            font=self.fonts.h2,
            anchor="w",
        ).pack(side="left")
        Button(
            header,
            text="Buat Cadangan",
            command=self._make_backup,
            variant="outline",
            pal=self.pal,
            fonts=self.fonts,
            icon="save",
            size="sm",
        ).pack(side="right")

        backups = self._backups()
        if not backups:
            EmptyState(
                card.body,
                self.pal,
                self.fonts,
                icon="save",
                title="Belum ada cadangan",
                message="Cadangan otomatis dibuat sebelum data dihapus. Kamu juga bisa membuatnya manual.",
            ).pack(fill="x", pady=4)
        else:
            for path in backups[:5]:
                self._backup_row(card.body, path)
        tk.Frame(card.body, height=int(self.metrics["card_pad"]) - 6, bg=self.pal["surface"]).pack(fill="x")

    def _backup_row(self, parent: tk.Frame, path: str) -> None:
        row = tk.Frame(parent, bg=self.pal["surface"])
        row.pack(fill="x", padx=int(self.metrics["card_pad"]))
        inner = tk.Frame(row, bg=self.pal["surface"])
        inner.pack(fill="x", pady=8)
        canvas = tk.Canvas(
            inner, width=16, height=16, bg=self.pal["surface"],
            highlightthickness=0, bd=0, takefocus=0,
        )
        canvas.pack(side="left", padx=(0, 8))
        icons.paint(canvas, "file", self.pal["text_faint"], size=16)
        tk.Label(
            inner,
            text=os.path.basename(path),
            bg=self.pal["surface"],
            fg=self.pal["text"],
            font=self.fonts.mono(9),
            anchor="w",
            justify="left",
            wraplength=max(150, self._text_width() - 170),
        ).pack(side="left")
        try:
            size = os.path.getsize(path)
            label = "{} · {}".format(_format_size(size), _format_time(os.path.getmtime(path)))
        except OSError:
            label = ""
        tk.Label(
            inner,
            text=label,
            bg=self.pal["surface"],
            fg=self.pal["text_faint"],
            font=self.fonts.get(8),
        ).pack(side="right")
        tk.Frame(row, height=1, bg=self.pal["border"]).pack(fill="x")

    # ------------------------------------------------------------------ #
    # Aksi
    # ------------------------------------------------------------------ #
    def _reload(self) -> None:
        self.app.reload_store()

    def _make_backup(self) -> None:
        try:
            path = self.app.store.backup("manual")
        except Exception as error:  # pragma: no cover - tergantung OS
            self.app.toast("Gagal membuat cadangan: {}".format(error), kind="error")
            return
        self.app.toast("Cadangan dibuat: {}".format(os.path.basename(path)))
        self.rebuild()

    def _backups(self) -> List[str]:
        try:
            return self.app.store.list_backups()
        except OSError:  # pragma: no cover
            return []

    def _example_json(self) -> str:
        items = self.app.store.all()
        if items:
            payload = items[0].to_dict()
        else:
            payload = {
                "id": "a1b2c3d4e5f6",
                "tanggal": timeutil.fmt_date_numeric(timeutil.today()),
                "waktu": timeutil.fmt_clock(timeutil.now(), seconds=True),
                "kegiatan": "Mengerjakan desain dashboard",
                "selesai": False,
            }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _file_size(self) -> str:
        try:
            return _format_size(os.path.getsize(self.app.store.path))
        except OSError:
            return ""

    def _text_width(self) -> int:
        return max(240, self.width - 2 * int(self.metrics["pad"]) - 2 * int(self.metrics["card_pad"]))


def _format_size(size: int) -> str:
    if size < 1024:
        return "{} B".format(size)
    if size < 1024 * 1024:
        return "{:.1f} KB".format(size / 1024)
    return "{:.1f} MB".format(size / (1024 * 1024))


def _format_time(timestamp: float) -> str:
    from datetime import datetime

    return datetime.fromtimestamp(timestamp).strftime("%d %b %Y %H:%M")
