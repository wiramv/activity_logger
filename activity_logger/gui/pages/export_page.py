"""Halaman Export: CSV / Markdown / JSON untuk semua data, bulanan, dan rentang custom."""

from __future__ import annotations

import tkinter as tk
from datetime import date, timedelta
from typing import Optional

from ...core import stats, timeutil
from .. import icons
from ..widgets import Button, Card, Chip, TextField
from .base import BasePage


class ExportPage(BasePage):
    key = "export"
    title = "Export Kegiatan"
    subtitle = "Ekspor data kegiatan dalam format JSON atau CSV (juga Markdown)."
    icon = "download"

    def __init__(self, app, parent) -> None:
        self._start_field: Optional[TextField] = None
        self._end_field: Optional[TextField] = None
        self._preview_label: Optional[tk.Label] = None
        super().__init__(app, parent)

    # ------------------------------------------------------------------ #
    # Struktur
    # ------------------------------------------------------------------ #
    def build(self) -> None:
        self.heading()
        self._build_all_card()
        self._build_month_card()
        self._build_custom_card()
        self._build_summary_card()
        self._build_danger_card()

    def _build_all_card(self) -> None:
        card = self.card()
        body = card.body
        title_row = tk.Frame(body, bg=self.pal["surface"])
        title_row.pack(fill="x")
        self._title_row(title_row, "Export Semua Kegiatan", "list")
        total = self.app.store.count()
        tk.Label(
            body,
            text="Ekspor seluruh kegiatan yang pernah kamu catat ({} kegiatan). "
            "File CSV bisa langsung dibuka di Excel/Google Sheets.".format(total),
            bg=self.pal["surface"],
            fg=self.pal["text_muted"],
            font=self.fonts.get(10),
            anchor="w",
            justify="left",
            wraplength=self._text_width(),
        ).pack(fill="x", pady=(8, 12))
        self._format_buttons(body, lambda kind: self.app.export_all(kind), "semua")
        self._export_hint(body)

    def _build_month_card(self) -> None:
        card = self.card()
        body = card.body
        title_row = tk.Frame(body, bg=self.pal["surface"])
        title_row.pack(fill="x")
        today = timeutil.today()
        self._title_row(
            title_row,
            "Export Bulan Ini",
            "calendar",
            badge=timeutil.month_label(today.year, today.month),
        )
        count = len(self.app.store.between(*timeutil.month_bounds(today.year, today.month)))
        tk.Label(
            body,
            text="Rekap kegiatan pada bulan berjalan ({} kegiatan). Cocok untuk laporan "
            "mingguan/bulanan ke atasan atau klien.".format(count),
            bg=self.pal["surface"],
            fg=self.pal["text_muted"],
            font=self.fonts.get(10),
            anchor="w",
            justify="left",
            wraplength=self._text_width(),
        ).pack(fill="x", pady=(8, 12))
        self._format_buttons(body, lambda kind: self.app.export_month(kind), self.app.month_slug())
        self._export_hint(body)

    def _build_custom_card(self) -> None:
        card = self.card()
        body = card.body
        title_row = tk.Frame(body, bg=self.pal["surface"])
        title_row.pack(fill="x")
        self._title_row(title_row, "Export Rentang Custom", "filter")
        tk.Label(
            body,
            text="Pilih rentang tanggal sendiri — misal untuk laporan per proyek atau "
            "evaluasi mingguan.",
            bg=self.pal["surface"],
            fg=self.pal["text_muted"],
            font=self.fonts.get(10),
            anchor="w",
            justify="left",
            wraplength=self._text_width(),
        ).pack(fill="x", pady=(8, 10))

        today = timeutil.today()
        if not self.app.state.get("export_start"):
            self.app.state["export_start"] = timeutil.fmt_date_numeric(today.replace(day=1))
        if not self.app.state.get("export_end"):
            self.app.state["export_end"] = timeutil.fmt_date_numeric(today)

        holder, start, end = self.range_fields(
            body,
            str(self.app.state["export_start"]),
            str(self.app.state["export_end"]),
        )
        holder.pack(fill="x")
        self._start_field = start
        self._end_field = end
        self._start_field.var.trace_add("write", self._on_range_changed)
        self._end_field.var.trace_add("write", self._on_range_changed)

        quick = tk.Frame(body, bg=self.pal["surface"])
        quick.pack(fill="x", pady=(12, 0))
        for label, days in (("7 hari terakhir", 7), ("30 hari terakhir", 30)):
            Chip(
                quick,
                label,
                self.pal,
                self.fonts,
                command=lambda d=days: self._quick_range(d),
                size="sm",
            ).pack(side="left", padx=(0, 6), pady=2)
        Chip(
            quick,
            "Bulan lalu",
            self.pal,
            self.fonts,
            command=self._last_month,
            size="sm",
        ).pack(side="left", pady=2)

        self._preview_label = tk.Label(
            body,
            text="",
            bg=self.pal["surface"],
            fg=self.pal["text_muted"],
            font=self.fonts.get(9),
            anchor="w",
        )
        self._preview_label.pack(fill="x", pady=(12, 8))

        self._format_buttons(
            body,
            lambda kind: self.app.export_range(kind, self._range(), self._range_slug()),
            "custom",
        )
        self._export_hint(body)
        self._update_preview()

    def _build_summary_card(self) -> None:
        card = self.card()
        body = card.body
        title_row = tk.Frame(body, bg=self.pal["surface"])
        title_row.pack(fill="x")
        self._title_row(title_row, "Export Ringkasan Harian", "chart")
        tk.Label(
            body,
            text="Satu baris per hari berisi jumlah kegiatan (Tanggal, Hari, Jumlah). "
            "Praktis untuk grafik atau rekap cepat.",
            bg=self.pal["surface"],
            fg=self.pal["text_muted"],
            font=self.fonts.get(10),
            anchor="w",
            justify="left",
            wraplength=self._text_width(),
        ).pack(fill="x", pady=(8, 12))
        Button(
            body,
            text="Unduh Ringkasan CSV",
            command=lambda: self.app.export_summary_csv(self._range(), self._range_slug()),
            variant="outline",
            pal=self.pal,
            fonts=self.fonts,
            icon="download",
            size="md",
        ).pack(anchor="w")
        self._export_hint(body)

    def _build_danger_card(self) -> None:
        card = Card(self.stack, self.pal, pad=16, bg=self.pal["surface"])
        card.configure(highlightbackground=self.pal["danger"])
        card.pack(fill="x", pady=(0, int(self.metrics["gap"])))
        body = card.body

        title = tk.Frame(body, bg=self.pal["danger_soft"])
        title.pack(fill="x")
        inner = tk.Frame(title, bg=self.pal["danger_soft"])
        inner.pack(fill="x", padx=12, pady=10)
        canvas = tk.Canvas(
            inner, width=16, height=16, bg=self.pal["danger_soft"],
            highlightthickness=0, bd=0, takefocus=0,
        )
        canvas.pack(side="left")
        icons.paint(canvas, "alert", self.pal["danger"], size=16)
        tk.Label(
            inner,
            text="Hapus Semua Kegiatan",
            bg=self.pal["danger_soft"],
            fg=self.pal["danger"],
            font=self.fonts.get(10, "bold"),
        ).pack(side="left", padx=(8, 0))

        tk.Label(
            body,
            text="Tindakan ini akan menghapus semua catatan kegiatan dari file JSON. "
            "Cadangan otomatis dibuat di folder backups/ sebelum penghapusan.",
            bg=self.pal["surface"],
            fg=self.pal["text_muted"],
            font=self.fonts.get(10),
            anchor="w",
            justify="left",
            wraplength=self._text_width(),
        ).pack(fill="x", pady=(10, 12))

        Button(
            body,
            text="Hapus Semua",
            command=self.app.delete_all,
            variant="danger",
            pal=self.pal,
            fonts=self.fonts,
            icon="trash",
            size="md",
        ).pack(anchor="w")

    # ------------------------------------------------------------------ #
    # Helper tampilan
    # ------------------------------------------------------------------ #
    def _title_row(self, parent: tk.Frame, text: str, icon: str, badge: Optional[str] = None) -> None:
        box = tk.Frame(parent, bg=self.pal["surface"])
        box.pack(side="left")
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
        if badge:
            tk.Label(
                box,
                text=badge,
                bg=self.pal["primary_soft"],
                fg=self.pal["primary"],
                font=self.fonts.get(8, "bold"),
                padx=8,
                pady=2,
            ).pack(side="left", padx=(8, 0))

    def _format_buttons(self, parent: tk.Frame, handler, slug: str) -> None:
        row = tk.Frame(parent, bg=self.pal["surface"])
        row.pack(fill="x")
        specs = [
            ("CSV", "csv", "primary", "file"),
            ("Markdown", "md", "outline", "file"),
            ("JSON", "json", "outline", "copy"),
        ]
        for label, kind, variant, icon in specs:
            button = Button(
                row,
                text=label,
                command=lambda k=kind: handler(k),
                variant=variant,
                pal=self.pal,
                fonts=self.fonts,
                icon=icon,
                size="md",
            )
            if self.narrow:
                button.pack(fill="x", pady=(0, 6))
            else:
                button.pack(side="left", padx=(0, 8))
        if self.narrow:
            return
        Button(
            row,
            text="Buka folder ekspor",
            command=self.app.open_exports_folder,
            variant="link",
            pal=self.pal,
            fonts=self.fonts,
            icon="external",
            size="sm",
        ).pack(side="right")

    def _export_hint(self, parent: tk.Frame) -> None:
        hint = tk.Frame(parent, bg=self.pal["surface"])
        hint.pack(fill="x", pady=(10, 0))
        tk.Label(
            hint,
            text="Tersimpan di: {}".format(self.app.exports_dir),
            bg=self.pal["surface"],
            fg=self.pal["text_faint"],
            font=self.fonts.get(8),
            anchor="w",
            justify="left",
            wraplength=self._text_width(),
        ).pack(side="left")
        if self.narrow:
            Button(
                hint,
                text="Buka",
                command=self.app.open_exports_folder,
                variant="link",
                pal=self.pal,
                fonts=self.fonts,
                size="sm",
            ).pack(side="right")

    def _text_width(self) -> int:
        return max(240, self.width - 2 * int(self.metrics["pad"]) - 2 * int(self.metrics["card_pad"]))

    # ------------------------------------------------------------------ #
    # Rentang
    # ------------------------------------------------------------------ #
    def _range(self):
        start_text = self._start_field.get() if self._start_field else ""
        end_text = self._end_field.get() if self._end_field else ""
        start = timeutil.parse_date(start_text) or timeutil.today().replace(day=1)
        end = timeutil.parse_date(end_text) or timeutil.today()
        if end < start:
            start, end = end, start
        return start, end

    def _range_slug(self) -> str:
        start, end = self._range()
        if start == end:
            return timeutil.fmt_date_numeric(start)
        return "{}_{}".format(
            timeutil.fmt_date_numeric(start), timeutil.fmt_date_numeric(end)
        )

    def _quick_range(self, days: int) -> None:
        start, end = timeutil.last_days_end(timeutil.today(), days)
        if self._start_field and self._end_field:
            self._start_field.set(timeutil.fmt_date_numeric(start))
            self._end_field.set(timeutil.fmt_date_numeric(end))
            self.app.state["export_start"] = timeutil.fmt_date_numeric(start)
            self.app.state["export_end"] = timeutil.fmt_date_numeric(end)
        self._update_preview()

    def _last_month(self) -> None:
        today = timeutil.today()
        year, month = timeutil.shift_month(today.year, today.month, -1)
        start = date(year, month, 1)
        end = date(*timeutil.shift_month(year, month, 1), 1) - timedelta(days=1)
        if self._start_field and self._end_field:
            self._start_field.set(timeutil.fmt_date_numeric(start))
            self._end_field.set(timeutil.fmt_date_numeric(end))
            self.app.state["export_start"] = timeutil.fmt_date_numeric(start)
            self.app.state["export_end"] = timeutil.fmt_date_numeric(end)
        self._update_preview()

    def _on_range_changed(self, *_args) -> None:
        if self._start_field is not None:
            self.app.state["export_start"] = self._start_field.get()
        if self._end_field is not None:
            self.app.state["export_end"] = self._end_field.get()
        self._update_preview()

    def _update_preview(self) -> None:
        if self._preview_label is None:
            return
        start, end = self._range()
        period = stats.resolve_period("custom", start=start, end=end)
        items = stats.filter_activities(self.app.store.all(), period=period)
        self._preview_label.configure(
            text="{} kegiatan pada {} – {} siap diekspor.".format(
                len(items),
                timeutil.fmt_date_short(start),
                timeutil.fmt_date_short(end),
            )
        )

    def on_width(self, width: int) -> None:
        super().on_width(width)
