"""Halaman Hapus Semua: zona berbahaya + pemulihan cadangan."""

from __future__ import annotations

import os
import tkinter as tk
from datetime import datetime

from ...core import timeutil
from .. import icons
from ..widgets import Button, Card, EmptyState
from .base import BasePage


class DeletePage(BasePage):
    key = "hapus"
    title = "Hapus Semua"
    subtitle = "Kelola pembersihan data dan pulihkan dari cadangan."
    icon = "trash"

    def build(self) -> None:
        self.heading()
        self._build_danger()
        self._build_backups()

    # ------------------------------------------------------------------ #
    def _build_danger(self) -> None:
        card = Card(self.stack, self.pal, pad=16)
        card.configure(highlightbackground=self.pal["danger"])
        card.pack(fill="x", pady=(0, int(self.metrics["gap"])))
        body = card.body

        alert = tk.Frame(body, bg=self.pal["danger_soft"])
        alert.pack(fill="x")
        inner = tk.Frame(alert, bg=self.pal["danger_soft"])
        inner.pack(fill="x", padx=12, pady=10)
        canvas = tk.Canvas(
            inner, width=16, height=16, bg=self.pal["danger_soft"],
            highlightthickness=0, bd=0, takefocus=0,
        )
        canvas.pack(side="left", anchor="n", pady=(1, 0))
        icons.paint(canvas, "alert", self.pal["danger"], size=16)
        tk.Label(
            inner,
            text="Tindakan ini tidak dapat dibatalkan (kecuali dari cadangan).",
            bg=self.pal["danger_soft"],
            fg=self.pal["danger"],
            font=self.fonts.get(9, "bold"),
            anchor="w",
            justify="left",
            wraplength=self._text_width() - 40,
        ).pack(side="left", padx=(8, 0), fill="x", expand=True)

        total = self.app.store.count()
        tk.Label(
            body,
            text="{} kegiatan tersimpan saat ini.".format(total),
            bg=self.pal["surface"],
            fg=self.pal["text"],
            font=self.fonts.get(13, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(14, 4))
        tk.Label(
            body,
            text="Menghapus semua kegiatan akan mengosongkan file JSON. Sebelum data "
            "dihapus, aplikasi otomatis membuat cadangan di folder backups/ sehingga "
            "kamu masih bisa memulihkannya kapan pun.",
            bg=self.pal["surface"],
            fg=self.pal["text_muted"],
            font=self.fonts.get(10),
            anchor="w",
            justify="left",
            wraplength=self._text_width(),
        ).pack(fill="x")

        Button(
            body,
            text="Hapus Semua Kegiatan",
            command=self.app.delete_all,
            variant="danger",
            pal=self.pal,
            fonts=self.fonts,
            icon="trash",
            size="md",
        ).pack(anchor="w", pady=(14, 0))

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
            text="Pulihkan dari Cadangan",
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
                message="Cadangan otomatis dibuat sebelum penghapusan data.",
            ).pack(fill="x", pady=4)
        else:
            for path in backups[:8]:
                self._row(card.body, path)
        tk.Frame(card.body, height=int(self.metrics["card_pad"]) - 6, bg=self.pal["surface"]).pack(fill="x")

    def _row(self, parent: tk.Frame, path: str) -> None:
        row = tk.Frame(parent, bg=self.pal["surface"])
        row.pack(fill="x", padx=int(self.metrics["card_pad"]))
        inner = tk.Frame(row, bg=self.pal["surface"])
        inner.pack(fill="x", pady=7)
        canvas = tk.Canvas(
            inner, width=16, height=16, bg=self.pal["surface"],
            highlightthickness=0, bd=0, takefocus=0,
        )
        canvas.pack(side="left", padx=(0, 8))
        icons.paint(canvas, "file", self.pal["text_faint"], size=16)

        text_box = tk.Frame(inner, bg=self.pal["surface"])
        text_box.pack(side="left", fill="x", expand=True)
        tk.Label(
            text_box,
            text=os.path.basename(path),
            bg=self.pal["surface"],
            fg=self.pal["text"],
            font=self.fonts.mono(9),
            anchor="w",
            justify="left",
            wraplength=max(150, self._text_width() - 190),
        ).pack(fill="x")
        try:
            stamp = datetime.fromtimestamp(os.path.getmtime(path))
            info = "{} · {}".format(
                timeutil.fmt_date_short(stamp.date()), timeutil.fmt_clock(stamp)
            )
        except OSError:  # pragma: no cover
            info = ""
        tk.Label(
            text_box,
            text=info,
            bg=self.pal["surface"],
            fg=self.pal["text_faint"],
            font=self.fonts.get(8),
            anchor="w",
        ).pack(fill="x")

        Button(
            inner,
            text="Pulihkan",
            command=lambda: self.app.restore_backup(path),
            variant="outline",
            pal=self.pal,
            fonts=self.fonts,
            size="sm",
        ).pack(side="right")
        tk.Frame(row, height=1, bg=self.pal["border"]).pack(fill="x")

    # ------------------------------------------------------------------ #
    def _backups(self):
        try:
            return self.app.store.list_backups()
        except OSError:  # pragma: no cover
            return []

    def _make_backup(self) -> None:
        try:
            path = self.app.store.backup("manual")
        except Exception as error:  # pragma: no cover
            self.app.toast("Gagal membuat cadangan: {}".format(error), kind="error")
            return
        self.app.toast("Cadangan dibuat: {}".format(os.path.basename(path)))
        self.rebuild()

    def _text_width(self) -> int:
        return max(240, self.width - 2 * int(self.metrics["pad"]) - 2 * int(self.metrics["card_pad"]))
