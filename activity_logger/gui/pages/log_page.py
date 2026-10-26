"""Halaman Catatan Kegiatan: pencarian, filter, dan pengelolaan catatan."""

from __future__ import annotations

import tkinter as tk
from typing import List, Optional

from ...core import stats, timeutil
from ..widgets import ActivityRow, Button, Chip, EmptyState, TextField
from .base import BasePage

PERIOD_OPTIONS = [
    ("semua-hari", "Semua"),
    ("today", "Hari ini"),
    ("week", "Minggu ini"),
    ("month", "Bulan ini"),
    ("custom", "Custom"),
]

STATUS_OPTIONS = [
    ("all", "Semua status"),
    ("pending", "Belum selesai"),
    ("done", "Selesai"),
]


class LogPage(BasePage):
    key = "catatan"
    title = "Catatan Kegiatan"
    subtitle = "Lihat dan kelola semua catatan kegiatan yang sudah tersimpan."
    icon = "list"

    def __init__(self, app, parent) -> None:
        self.search: Optional[TextField] = None
        self.start_field: Optional[TextField] = None
        self.end_field: Optional[TextField] = None
        self.rows_host: Optional[tk.Frame] = None
        self.footer_host: Optional[tk.Frame] = None
        self.count_label: Optional[tk.Label] = None
        self._period_chips = {}
        self._status_chips = {}
        self._custom_row: Optional[tk.Frame] = None
        super().__init__(app, parent)

    # ------------------------------------------------------------------ #
    # Struktur
    # ------------------------------------------------------------------ #
    def build(self) -> None:
        self.heading()
        self._build_toolbar()
        self._build_list()

    def _build_toolbar(self) -> None:
        card = self.card()
        body = card.body

        self.search = TextField(
            body,
            self.pal,
            self.fonts,
            placeholder="Cari kegiatan...",
            icon="search",
            height=40,
        )
        self.search.pack(fill="x")
        self.search.set(self.app.state.get("log_query", ""))
        self.search.var.trace_add("write", self._on_query_changed)
        self.search.bind_return(self.app.focus_page_search)

        filter_row = tk.Frame(body, bg=self.pal["surface"])
        filter_row.pack(fill="x", pady=(12, 0))

        period_row = self.chips_row(
            filter_row,
            PERIOD_OPTIONS,
            self.app.state.get("log_period", "month"),
            self._set_period,
        )
        if self.narrow:
            period_row.pack(fill="x")
        else:
            period_row.pack(side="left")
        self._period_chips = getattr(period_row, "_chips", {})

        if not self.narrow:
            status_row = self.chips_row(
                filter_row,
                STATUS_OPTIONS,
                self.app.state.get("log_status", "all"),
                self._set_status,
            )
            status_row.pack(side="right")
            self._status_chips = getattr(status_row, "_chips", {})

        self._custom_row = tk.Frame(body, bg=self.pal["surface"])
        if self.narrow:
            self._custom_row.pack(fill="x", pady=(10, 0))
        self._build_custom_row()

        if self.narrow:
            status_row = self.chips_row(
                body,
                STATUS_OPTIONS,
                self.app.state.get("log_status", "all"),
                self._set_status,
            )
            status_row.pack(fill="x", pady=(10, 0))
            self._status_chips = getattr(status_row, "_chips", {})

        if self.app.state.get("log_period") == "custom":
            self._custom_row.pack(fill="x", pady=(10, 0))

    def _build_custom_row(self) -> None:
        row = self._custom_row
        if row is None:
            return
        for child in list(row.winfo_children()):
            child.destroy()
        holder, start, end = self.range_fields(
            row,
            self.app.state.get("log_start", ""),
            self.app.state.get("log_end", ""),
            self._apply_custom,
        )
        holder.pack(fill="x")
        self.start_field = start
        self.end_field = end

    def _build_list(self) -> None:
        card = self.card(pad=0)
        self._list_card = card

        header = tk.Frame(card.body, bg=self.pal["surface"])
        header.pack(
            fill="x",
            padx=int(self.metrics["card_pad"]),
            pady=(int(self.metrics["card_pad"]), 10),
        )
        self.count_label = tk.Label(
            header,
            text="",
            bg=self.pal["surface"],
            fg=self.pal["text_muted"],
            font=self.fonts.get(9),
            anchor="w",
        )
        self.count_label.pack(side="left")
        Button(
            header,
            text="Bersihkan filter",
            command=self._reset_filters,
            variant="link",
            pal=self.pal,
            fonts=self.fonts,
            icon="refresh",
            size="sm",
        ).pack(side="right")

        columns = [("Tanggal & Waktu", 0, "w", 150), ("Kegiatan", 1, "w", 200), ("Aksi", 0, "e", 70)]
        if self.narrow:
            columns = [("Kegiatan", 1, "w", 180), ("Aksi", 0, "e", 60)]
        self._header = self.table_header(card.body, columns, leading=0 if self.narrow else 31)

        self.rows_host = tk.Frame(card.body, bg=self.pal["surface"])
        self.rows_host.pack(fill="x")

        self.footer_host = tk.Frame(card.body, bg=self.pal["surface"])
        self.footer_host.pack(fill="x", padx=int(self.metrics["card_pad"]), pady=(0, 10))

        self._refresh_list()

    # ------------------------------------------------------------------ #
    # Data
    # ------------------------------------------------------------------ #
    def _period(self):
        key = self.app.state.get("log_period", "month")
        if key == "semua-hari":
            key = "all"
        start = timeutil.parse_date(self.app.state.get("log_start", "")) if self.app.state.get("log_start") else None
        end = timeutil.parse_date(self.app.state.get("log_end", "")) if self.app.state.get("log_end") else None
        if key == "custom" and start is None and end is None:
            start = timeutil.today().replace(day=1)
            end = timeutil.today()
        return stats.resolve_period(key, start=start, end=end)

    def _filtered(self) -> List:
        period = self._period()
        return stats.filter_activities(
            self.app.store.all(),
            period=period,
            query=self.app.state.get("log_query", ""),
            status=self.app.state.get("log_status", "all"),
        )

    def _page_size(self) -> int:
        return 6 if self.narrow else 10

    def _refresh_list(self) -> None:
        if self.rows_host is None:
            return
        items = self._filtered()
        page_size = self._page_size()
        total_pages = max(1, (len(items) + page_size - 1) // page_size)
        page = min(max(1, int(self.app.state.get("log_page", 1))), total_pages)
        self.app.state["log_page"] = page
        start = (page - 1) * page_size
        visible = items[start : start + page_size]

        for child in list(self.rows_host.winfo_children()):
            child.destroy()
        for child in list(self.footer_host.winfo_children()):
            child.destroy()

        if self.count_label is not None:
            self.count_label.configure(
                text="{} kegiatan · {}".format(len(items), self._period().label)
            )

        if not visible:
            has_filter = bool(self.app.state.get("log_query"))
            empty = EmptyState(
                self.rows_host,
                self.pal,
                self.fonts,
                icon="search" if has_filter else "list",
                title="Tidak ada kegiatan" if has_filter else "Belum ada catatan",
                message=(
                    "Coba kata kunci lain atau ubah filter periode."
                    if has_filter
                    else "Tambahkan kegiatan dari halaman Beranda — cukup ketik lalu tekan Enter."
                ),
            )
            empty.pack(fill="x", pady=10)
        else:
            layout = "table" if not self.narrow else "stack"
            for index, item in enumerate(visible):
                row = ActivityRow(
                    self.rows_host,
                    item,
                    self.pal,
                    self.fonts,
                    layout=layout,
                    on_toggle=self.app.toggle_activity,
                    on_edit=self.app.edit_activity,
                    on_delete=self.app.delete_activity,
                    show_seconds=bool(self.app.settings.show_seconds),
                )
                row.pack(fill="x", padx=int(self.metrics["card_pad"]))
                row.set_wraplength(max(200, self.width - (320 if layout == "table" else 140)))
                if index == len(visible) - 1 and len(visible) < page_size:
                    row._separator.configure(bg=self.pal["surface"])

        self._build_pagination(len(items), page, total_pages)

    def _build_pagination(self, total: int, page: int, total_pages: int) -> None:
        footer = self.footer_host
        if footer is None:
            return
        info = tk.Label(
            footer,
            text="Menampilkan {}–{} dari {}".format(
                (page - 1) * self._page_size() + 1 if total else 0,
                min(page * self._page_size(), total),
                total,
            ),
            bg=self.pal["surface"],
            fg=self.pal["text_muted"],
            font=self.fonts.get(9),
        )
        controls = tk.Frame(footer, bg=self.pal["surface"])
        if self.narrow:
            info.pack(fill="x")
            controls.pack(fill="x", pady=(8, 0))
        else:
            info.pack(side="left")
            controls.pack(side="right")
        if total_pages <= 1:
            return

        if self.narrow:
            page_label = tk.Label(
                controls,
                text="Halaman {} dari {}".format(page, total_pages),
                bg=self.pal["surface"],
                fg=self.pal["text_muted"],
                font=self.fonts.get(9),
            )
            page_label.pack(side="right")

        Button(
            controls,
            text="",
            command=lambda: self._go_page(page - 1),
            variant="outline",
            pal=self.pal,
            fonts=self.fonts,
            icon="chevron_left",
            size="sm",
            padx=7,
            pady=4,
            state="normal" if page > 1 else "disabled",
        ).pack(side="left", padx=(0, 6))

        for number in self._page_numbers(page, total_pages):
            if number is None:
                tk.Label(
                    controls,
                    text="…",
                    bg=self.pal["surface"],
                    fg=self.pal["text_faint"],
                    font=self.fonts.get(9),
                    padx=4,
                ).pack(side="left")
                continue
            chip = Chip(
                controls,
                str(number),
                self.pal,
                self.fonts,
                command=lambda n=number: self._go_page(n),
                active=(number == page),
                size="sm",
            )
            chip.pack(side="left", padx=2)

        Button(
            controls,
            text="",
            command=lambda: self._go_page(page + 1),
            variant="outline",
            pal=self.pal,
            fonts=self.fonts,
            icon="chevron_right",
            size="sm",
            padx=7,
            pady=4,
            state="normal" if page < total_pages else "disabled",
        ).pack(side="left", padx=(6, 0))

    @staticmethod
    def _page_numbers(page: int, total_pages: int) -> List[Optional[int]]:
        if total_pages <= 5:
            return list(range(1, total_pages + 1))
        pages: List[Optional[int]] = [1]
        if page > 3:
            pages.append(None)
        for number in range(max(2, page - 1), min(total_pages, page + 1) + 1):
            pages.append(number)
        if page < total_pages - 2:
            pages.append(None)
        pages.append(total_pages)
        return pages

    # ------------------------------------------------------------------ #
    # Event
    # ------------------------------------------------------------------ #
    def _on_query_changed(self, *_args) -> None:
        if self.search is None:
            return
        value = self.search.get()
        if value == self.app.state.get("log_query", ""):
            return
        self.app.state["log_query"] = value
        self.app.state["log_page"] = 1
        self._refresh_list()

    def _set_period(self, value: str) -> None:
        self.app.state["log_period"] = value
        self.app.state["log_page"] = 1
        for key, chip in self._period_chips.items():
            chip.set_active(key == value)
        if self._custom_row is not None:
            if value == "custom":
                if not self.app.state.get("log_start"):
                    self.app.state["log_start"] = timeutil.fmt_date_numeric(
                        timeutil.today().replace(day=1)
                    )
                if not self.app.state.get("log_end"):
                    self.app.state["log_end"] = timeutil.fmt_date_numeric(timeutil.today())
                self._build_custom_row()
                self._custom_row.pack(fill="x", pady=(10, 0))
            else:
                self._custom_row.pack_forget()
        self._refresh_list()

    def _set_status(self, value: str) -> None:
        self.app.state["log_status"] = value
        self.app.state["log_page"] = 1
        for key, chip in self._status_chips.items():
            chip.set_active(key == value)
        self._refresh_list()

    def _apply_custom(self) -> None:
        if self.start_field is None or self.end_field is None:
            return
        start_text = self.start_field.get()
        end_text = self.end_field.get()
        start = timeutil.parse_date(start_text) if start_text else None
        end = timeutil.parse_date(end_text) if end_text else None
        if start_text and start is None:
            self.app.toast("Format tanggal harus YYYY-MM-DD", kind="error")
            return
        if end_text and end is None:
            self.app.toast("Format tanggal harus YYYY-MM-DD", kind="error")
            return
        if start and end and end < start:
            start, end = end, start
        self.app.state["log_start"] = timeutil.fmt_date_numeric(start) if start else ""
        self.app.state["log_end"] = timeutil.fmt_date_numeric(end) if end else ""
        self.app.state["log_page"] = 1
        self._refresh_list()
        self.app.toast("Filter rentang diterapkan")

    def _reset_filters(self) -> None:
        self.app.state.update(
            {
                "log_query": "",
                "log_period": "month",
                "log_status": "all",
                "log_page": 1,
                "log_start": "",
                "log_end": "",
            }
        )
        self.rebuild()

    def _go_page(self, page: int) -> None:
        self.app.state["log_page"] = max(1, int(page))
        self._refresh_list()
        self.scroll.canvas.yview_moveto(0.0)

    # ------------------------------------------------------------------ #
    # Data berubah
    # ------------------------------------------------------------------ #
    def refresh(self) -> None:
        self._refresh_list()

    def on_width(self, width: int) -> None:
        super().on_width(width)
        for child in self.rows_host.winfo_children() if self.rows_host else []:
            if isinstance(child, ActivityRow):
                child.set_wraplength(
                    max(200, width - (320 if child.layout == "table" else 140))
                )
