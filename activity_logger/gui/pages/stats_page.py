"""Halaman Total Kegiatan: ringkasan angka, grafik batang, dan detail per hari."""

from __future__ import annotations

import tkinter as tk
from typing import Dict, List, Optional

from ...core import stats, timeutil
from ..widgets import BarChart, Button, Chip, EmptyState, StatTile, TextField
from .base import BasePage

PERIOD_OPTIONS = [
    ("today", "Hari ini"),
    ("week", "Minggu ini"),
    ("month", "Bulan ini"),
    ("last30", "30 hari"),
    ("all", "Semua"),
    ("custom", "Custom"),
]


class StatsPage(BasePage):
    key = "total"
    title = "Total Kegiatan"
    subtitle = "Ringkasan jumlah kegiatan berdasarkan periode."
    icon = "chart"

    def __init__(self, app, parent) -> None:
        self._period_chips: Dict[str, Chip] = {}
        self._tiles: List[StatTile] = []
        self._chart: Optional[BarChart] = None
        self._detail_host: Optional[tk.Frame] = None
        self._insight_host: Optional[tk.Frame] = None
        self._custom_row: Optional[tk.Frame] = None
        self._start_field: Optional[TextField] = None
        self._end_field: Optional[TextField] = None
        self._tiles_frame: Optional[tk.Frame] = None
        self._streak_label: Optional[tk.Label] = None
        super().__init__(app, parent)

    # ------------------------------------------------------------------ #
    # Struktur
    # ------------------------------------------------------------------ #
    def build(self) -> None:
        self.heading()
        self._build_period_card()
        self._build_tiles()
        self._build_chart()
        self._build_detail()
        self._refresh_data()

    def _build_period_card(self) -> None:
        card = self.card()
        row = tk.Frame(card.body, bg=self.pal["surface"])
        row.pack(fill="x")
        chips = self.chips_row(
            row, PERIOD_OPTIONS, self.app.state.get("stats_period", "month"), self._set_period
        )
        if self.narrow:
            chips.pack(fill="x")
        else:
            chips.pack(side="left")
        self._period_chips = getattr(chips, "_chips", {})

        self._custom_row = tk.Frame(card.body, bg=self.pal["surface"])
        self._build_custom_row()
        if self.app.state.get("stats_period") == "custom":
            self._custom_row.pack(fill="x", pady=(12, 0))

    def _build_custom_row(self) -> None:
        row = self._custom_row
        if row is None:
            return
        for child in list(row.winfo_children()):
            child.destroy()
        holder, start, end = self.range_fields(
            row,
            self.app.state.get("stats_start", ""),
            self.app.state.get("stats_end", ""),
            self._apply_custom,
        )
        holder.pack(fill="x")
        self._start_field = start
        self._end_field = end

    def _build_tiles(self) -> None:
        self._tiles_frame = tk.Frame(self.stack, bg=self.pal["page"])
        self._tiles_frame.pack(fill="x", pady=(0, int(self.metrics["gap"])))
        self._tiles = [
            StatTile(
                self._tiles_frame, self.pal, self.fonts,
                icon="list", title="Total Kegiatan", value="0", caption="", accent="primary",
            ),
            StatTile(
                self._tiles_frame, self.pal, self.fonts,
                icon="chart", title="Rata-rata per Hari", value="0", caption="", accent="info",
            ),
            StatTile(
                self._tiles_frame, self.pal, self.fonts,
                icon="calendar", title="Hari Aktif", value="0", caption="", accent="warning",
            ),
        ]
        columns = 1 if self.narrow else 3
        for index, tile in enumerate(self._tiles):
            tile.grid(
                row=index // columns,
                column=index % columns,
                sticky="nsew",
                padx=(0 if index % columns == 0 else 10, 0),
                pady=(0, 10),
            )
        for column in range(columns):
            self._tiles_frame.grid_columnconfigure(column, weight=1, uniform="tiles")

    def _build_chart(self) -> None:
        card = self.card()
        header = tk.Frame(card.body, bg=self.pal["surface"])
        header.pack(fill="x")
        tk.Label(
            header,
            text="Grafik Kegiatan",
            bg=self.pal["surface"],
            fg=self.pal["text"],
            font=self.fonts.h2,
            anchor="w",
        ).pack(side="left")
        self._streak_label = tk.Label(
            header,
            text="",
            bg=self.pal["surface"],
            fg=self.pal["text_muted"],
            font=self.fonts.get(9),
        )
        self._streak_label.pack(side="right")

        legend = tk.Frame(card.body, bg=self.pal["surface"])
        legend.pack(fill="x", pady=(4, 8))
        dot = tk.Canvas(
            legend, width=10, height=10, bg=self.pal["surface"],
            highlightthickness=0, bd=0, takefocus=0,
        )
        dot.pack(side="left")
        dot.create_oval(1, 1, 9, 9, fill=self.pal["chart"], outline=self.pal["chart"])
        tk.Label(
            legend,
            text="Jumlah kegiatan per hari",
            bg=self.pal["surface"],
            fg=self.pal["text_muted"],
            font=self.fonts.get(9),
        ).pack(side="left", padx=(6, 0))

        self._chart = BarChart(
            card.body, self.pal, self.fonts, height=150 if self.narrow else 190
        )
        self._chart.pack(fill="x", pady=(4, 0))

        self._insight_host = tk.Frame(card.body, bg=self.pal["surface"])
        self._insight_host.pack(fill="x", pady=(10, 0))

    def _build_detail(self) -> None:
        card = self.card(pad=0)
        header = tk.Frame(card.body, bg=self.pal["surface"])
        header.pack(
            fill="x",
            padx=int(self.metrics["card_pad"]),
            pady=(int(self.metrics["card_pad"]), 10),
        )
        tk.Label(
            header,
            text="Detail Kegiatan per Hari",
            bg=self.pal["surface"],
            fg=self.pal["text"],
            font=self.fonts.h2,
            anchor="w",
        ).pack(side="left")
        Button(
            header,
            text="Export CSV",
            command=lambda: self.app.export_period("csv"),
            variant="outline",
            pal=self.pal,
            fonts=self.fonts,
            icon="download",
            size="sm",
        ).pack(side="right")

        self.table_header(
            card.body,
            [("Tanggal", 2, "w", 140), ("Hari", 1, "w", 80), ("Jumlah", 1, "e", 70)],
        )
        self._detail_host = tk.Frame(card.body, bg=self.pal["surface"])
        self._detail_host.pack(fill="x")
        tk.Frame(card.body, height=int(self.metrics["card_pad"]) - 4, bg=self.pal["surface"]).pack(fill="x")

    # ------------------------------------------------------------------ #
    # Data
    # ------------------------------------------------------------------ #
    def _period(self):
        key = self.app.state.get("stats_period", "month")
        start = (
            timeutil.parse_date(self.app.state.get("stats_start", ""))
            if self.app.state.get("stats_start")
            else None
        )
        end = (
            timeutil.parse_date(self.app.state.get("stats_end", ""))
            if self.app.state.get("stats_end")
            else None
        )
        if key == "custom" and start is None and end is None:
            start = timeutil.today().replace(day=1)
            end = timeutil.today()
        return stats.resolve_period(key, start=start, end=end)

    def _refresh_data(self) -> None:
        period = self._period()
        items = stats.filter_activities(self.app.store.all(), period=period)
        summary = stats.summarize(items, period=period)

        if len(self._tiles) == 3:
            self._tiles[0].set(str(summary.total), period.label)
            self._tiles[1].set(
                "{:.1f}".format(summary.avg_per_day), "kegiatan / hari"
            )
            self._tiles[2].set(
                str(summary.active_days),
                "dari {} hari".format(summary.range_days or 0),
            )

        if self._streak_label is not None:
            self._streak_label.configure(
                text="Streak {} hari · terpanjang {} hari".format(
                    summary.current_streak, summary.longest_streak
                )
            )

        if self._chart is not None:
            self._chart.set_data(stats.chart_series_for_period(items, period))

        self._fill_insights(summary)
        self._fill_detail(items, period)

    def _fill_insights(self, summary) -> None:
        host = self._insight_host
        if host is None:
            return
        for child in list(host.winfo_children()):
            child.destroy()

        facts = []
        if summary.best_day is not None:
            facts.append(
                (
                    "Hari terbaik",
                    "{} · {} kegiatan".format(
                        timeutil.fmt_date_indonesian(summary.best_day),
                        summary.best_day_count,
                    ),
                )
            )
        if summary.busiest_hour is not None:
            facts.append(
                (
                    "Jam paling produktif",
                    "{:02d}:00–{:02d}:59 · {} kegiatan".format(
                        summary.busiest_hour,
                        summary.busiest_hour,
                        summary.busiest_hour_count,
                    ),
                )
            )
        facts.append(("Total pada periode ini", "{} kegiatan".format(summary.total)))

        columns = 1 if self.narrow else len(facts)
        for index, (label, value) in enumerate(facts):
            box = tk.Frame(host, bg=self.pal["surface_soft"], bd=0)
            box.grid(
                row=index // columns,
                column=index % columns,
                sticky="nsew",
                padx=(0 if index % columns == 0 else 8, 0),
                pady=(0 if index < columns else 8, 0),
            )
            inner = tk.Frame(box, bg=self.pal["surface_soft"])
            inner.pack(fill="x", padx=10, pady=8)
            tk.Label(
                inner,
                text=label,
                bg=self.pal["surface_soft"],
                fg=self.pal["text_faint"],
                font=self.fonts.get(8, "bold"),
                anchor="w",
            ).pack(fill="x")
            tk.Label(
                inner,
                text=value,
                bg=self.pal["surface_soft"],
                fg=self.pal["text"],
                font=self.fonts.get(9),
                anchor="w",
                wraplength=max(
                    120,
                    self.width - 120 if self.narrow
                    else int((self.width - 120) / max(1, len(facts))),
                ),
                justify="left",
            ).pack(fill="x", pady=(2, 0))
        for column in range(columns):
            host.grid_columnconfigure(column, weight=1, uniform="facts")

    def _fill_detail(self, items, period) -> None:
        host = self._detail_host
        if host is None:
            return
        for child in list(host.winfo_children()):
            child.destroy()

        summary = stats.summarize(items, period=period)
        rows = sorted(summary.per_day.items(), reverse=True)
        if not rows:
            EmptyState(
                host,
                self.pal,
                self.fonts,
                icon="chart",
                title="Belum ada kegiatan",
                message="Belum ada catatan pada periode {}.".format(period.label),
            ).pack(fill="x", pady=6)
            return

        visible = rows[:20]
        for day, count in visible:
            row = tk.Frame(host, bg=self.pal["surface"])
            row.pack(fill="x", padx=int(self.metrics["card_pad"]))
            inner = tk.Frame(row, bg=self.pal["surface"])
            inner.pack(fill="x", pady=8)
            inner.grid_columnconfigure(0, weight=2, minsize=140)
            inner.grid_columnconfigure(1, weight=1, minsize=80)
            inner.grid_columnconfigure(2, weight=1, minsize=70)
            tk.Label(
                inner,
                text=timeutil.fmt_date_numeric(day),
                bg=self.pal["surface"],
                fg=self.pal["text"],
                font=self.fonts.mono(9),
                anchor="w",
            ).grid(row=0, column=0, sticky="w")
            tk.Label(
                inner,
                text=timeutil.day_name(day),
                bg=self.pal["surface"],
                fg=self.pal["text_muted"],
                font=self.fonts.get(9),
                anchor="w",
            ).grid(row=0, column=1, sticky="w")
            tk.Label(
                inner,
                text=str(count),
                bg=self.pal["surface"],
                fg=self.pal["primary"],
                font=self.fonts.get(9, "bold"),
                anchor="e",
            ).grid(row=0, column=2, sticky="e")
            tk.Frame(row, height=1, bg=self.pal["border"]).pack(fill="x")

        if len(rows) > len(visible):
            tk.Label(
                host,
                text="Menampilkan {} hari terbaru dari {} hari aktif. Export CSV untuk data lengkap.".format(
                    len(visible), len(rows)
                ),
                bg=self.pal["surface"],
                fg=self.pal["text_faint"],
                font=self.fonts.get(8),
                anchor="w",
                justify="left",
            ).pack(fill="x", padx=int(self.metrics["card_pad"]), pady=(8, 0))

    # ------------------------------------------------------------------ #
    # Event
    # ------------------------------------------------------------------ #
    def _set_period(self, value: str) -> None:
        self.app.state["stats_period"] = value
        for key, chip in self._period_chips.items():
            chip.set_active(key == value)
        if self._custom_row is not None:
            if value == "custom":
                if not self.app.state.get("stats_start"):
                    self.app.state["stats_start"] = timeutil.fmt_date_numeric(
                        timeutil.today().replace(day=1)
                    )
                if not self.app.state.get("stats_end"):
                    self.app.state["stats_end"] = timeutil.fmt_date_numeric(timeutil.today())
                self._build_custom_row()
                self._custom_row.pack(fill="x", pady=(12, 0))
            else:
                self._custom_row.pack_forget()
        self._refresh_data()

    def _apply_custom(self) -> None:
        if self._start_field is None or self._end_field is None:
            return
        start_text = self._start_field.get()
        end_text = self._end_field.get()
        start = timeutil.parse_date(start_text) if start_text else None
        end = timeutil.parse_date(end_text) if end_text else None
        if (start_text and start is None) or (end_text and end is None):
            self.app.toast("Format tanggal harus YYYY-MM-DD", kind="error")
            return
        if start and end and end < start:
            start, end = end, start
        self.app.state["stats_start"] = timeutil.fmt_date_numeric(start) if start else ""
        self.app.state["stats_end"] = timeutil.fmt_date_numeric(end) if end else ""
        self._refresh_data()

    def refresh(self) -> None:
        self._refresh_data()

    def on_width(self, width: int) -> None:
        super().on_width(width)
