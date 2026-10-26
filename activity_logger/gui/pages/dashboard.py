"""Halaman Beranda: input cepat, statistik singkat, dan aktivitas terbaru."""

from __future__ import annotations

import tkinter as tk
from typing import Optional

from ...core import stats, timeutil
from ...core.storage import StorageError
from .. import icons
from ..widgets import (
    ActivityRow,
    Button,
    Card,
    EmptyState,
    StatTile,
    TextField,
)
from .base import BasePage


class DashboardPage(BasePage):
    key = "beranda"
    title = "Beranda"
    subtitle = "Catat kegiatan dan lihat ringkasannya"
    icon = "home"

    def __init__(self, app, parent) -> None:
        self.field: Optional[TextField] = None
        self._clock_label: Optional[tk.Label] = None
        self._clock_after: Optional[str] = None
        self._tiles = []
        self._tiles_frame: Optional[tk.Frame] = None
        self._recent_host: Optional[tk.Frame] = None
        super().__init__(app, parent)

    # ------------------------------------------------------------------ #
    # Struktur
    # ------------------------------------------------------------------ #
    def build(self) -> None:
        self.heading(
            "Selamat Datang!",
            "Catat kegiatamu dengan cepat. Semua data otomatis tersimpan "
            "ke dalam file JSON beserta tanggal dan waktu.",
        )
        self._build_quick_add()
        self._build_tiles()
        self._build_recent()

    def _build_quick_add(self) -> None:
        card = self.card(pad=int(self.metrics["card_pad"]))
        row = tk.Frame(card.body, bg=self.pal["surface"])
        row.pack(fill="x")

        self.field = TextField(
            row,
            self.pal,
            self.fonts,
            placeholder="Ketik kegiatan yang kamu lakukan...",
            icon="edit",
            height=42,
        )
        self.field.bind_return(self._submit)

        self._save_button = Button(
            row,
            text="Simpan",
            command=self._submit,
            variant="primary",
            pal=self.pal,
            fonts=self.fonts,
            icon="save",
            size="md",
            wide=False,
        )
        if self.narrow:
            self.field.pack(fill="x", pady=(0, 10))
            self._save_button.pack(fill="x")
        else:
            self.field.pack(side="left", fill="x", expand=True)
            self._save_button.pack(side="left", padx=(10, 0))

        hint = tk.Frame(card.body, bg=self.pal["surface"])
        hint.pack(fill="x", pady=(10, 0))
        clock = tk.Canvas(
            hint, width=13, height=13, bg=self.pal["surface"],
            highlightthickness=0, bd=0, takefocus=0,
        )
        clock.pack(side="left", pady=(1, 0))
        icons.paint(clock, "clock", self.pal["text_faint"], size=13)
        self._clock_label = tk.Label(
            hint,
            text=self._clock_text(),
            bg=self.pal["surface"],
            fg=self.pal["text_faint"],
            font=self.fonts.get(9),
            anchor="w",
        )
        self._clock_label.pack(side="left", padx=(6, 0), fill="x", expand=True)
        if not self.narrow:
            tk.Label(
                hint,
                text="Tekan Enter untuk menyimpan",
                bg=self.pal["surface"],
                fg=self.pal["text_faint"],
                font=self.fonts.get(9),
            ).pack(side="right")

        self._schedule_clock()
        if self.app.focus_quick_add_on_load:
            self.after(80, self.focus_input)

    def _build_tiles(self) -> None:
        self._tiles_frame = tk.Frame(self.stack, bg=self.pal["page"])
        self._tiles_frame.pack(fill="x", pady=(0, int(self.metrics["gap"])))

        total, month_count = self._counts()
        month_label = timeutil.month_label(timeutil.today().year, timeutil.today().month)

        self._tiles = [
            StatTile(
                self._tiles_frame,
                self.pal,
                self.fonts,
                icon="list",
                title="Total Kegiatan",
                value=str(total),
                caption="semua data",
                accent="primary",
                command=lambda: self.app.navigate("catatan"),
            ),
            StatTile(
                self._tiles_frame,
                self.pal,
                self.fonts,
                icon="calendar",
                title="Kegiatan Bulan Ini",
                value=str(month_count),
                caption=month_label,
                accent="info",
                command=lambda: self.app.navigate("total"),
            ),
        ]
        self._tiles.append(self._build_location_tile(self._tiles_frame))
        self._layout_tiles()

    def _build_location_tile(self, parent: tk.Widget) -> Card:
        card = Card(parent, self.pal, pad=14)
        head = tk.Frame(card.body, bg=self.pal["surface"])
        head.pack(fill="x")
        box = tk.Frame(head, bg=self.pal["info_soft"], width=38, height=38)
        box.pack(side="left")
        box.pack_propagate(False)
        canvas = tk.Canvas(
            box, width=18, height=18, bg=self.pal["info_soft"],
            highlightthickness=0, bd=0, takefocus=0,
        )
        canvas.pack(expand=True)
        icons.paint(canvas, "folder", self.pal["info"], size=18)
        tk.Label(
            head,
            text="Lokasi File JSON",
            bg=self.pal["surface"],
            fg=self.pal["text_muted"],
            font=self.fonts.get(9),
        ).pack(side="left", padx=(10, 0))

        path = self.app.store.path
        self._path_label = tk.Label(
            card.body,
            text=path,
            bg=self.pal["surface"],
            fg=self.pal["text"],
            font=self.fonts.mono(9),
            anchor="w",
            justify="left",
            wraplength=max(200, self._tile_width() - 40),
        )
        self._path_label.pack(fill="x", pady=(8, 6))
        Button(
            card.body,
            text="Ubah Lokasi",
            command=self.app.change_location,
            variant="outline",
            pal=self.pal,
            fonts=self.fonts,
            size="sm",
        ).pack(anchor="w")
        return card

    def _layout_tiles(self) -> None:
        if self._tiles_frame is None:
            return
        columns = 1 if self.narrow else 3
        for index, tile in enumerate(self._tiles):
            tile.grid(
                row=index // columns,
                column=index % columns,
                sticky="nsew",
                padx=(0 if index % columns == 0 else 10, 0),
                pady=(0, 10 if index // columns < (len(self._tiles) - 1) // columns else 0),
            )
        for column in range(columns):
            self._tiles_frame.grid_columnconfigure(column, weight=1, uniform="tiles")

    def _build_recent(self) -> None:
        card = self.card(pad=0)
        header = tk.Frame(card.body, bg=self.pal["surface"])
        header.pack(fill="x", padx=int(self.metrics["card_pad"]), pady=(int(self.metrics["card_pad"]), 10))
        tk.Label(
            header,
            text="Aktivitas Terbaru",
            bg=self.pal["surface"],
            fg=self.pal["text"],
            font=self.fonts.h1,
            anchor="w",
        ).pack(side="left")
        Button(
            header,
            text="Lihat Semua",
            command=lambda: self.app.navigate("catatan"),
            variant="link",
            pal=self.pal,
            fonts=self.fonts,
            icon="arrow_right",
            size="sm",
        ).pack(side="right")

        self.table_header(
            card.body,
            [("Tanggal & Waktu", 2, "w", 120), ("Kegiatan", 5, "w", 200)],
            leading=31,
        )
        self._recent_host = tk.Frame(card.body, bg=self.pal["surface"])
        self._recent_host.pack(fill="x")
        self._fill_recent()
        tk.Frame(card.body, height=int(self.metrics["card_pad"]) - 6, bg=self.pal["surface"]).pack(fill="x")

    # ------------------------------------------------------------------ #
    # Data
    # ------------------------------------------------------------------ #
    def _counts(self):
        items = self.app.store.all()
        reference = timeutil.today()
        month_period = stats.resolve_period("month", reference=reference)
        month_count = len([item for item in items if month_period.contains(item.ts)])
        return len(items), month_count

    def _fill_recent(self) -> None:
        if self._recent_host is None:
            return
        for child in list(self._recent_host.winfo_children()):
            child.destroy()
        items = self.app.store.all()[:6]
        if not items:
            empty = EmptyState(
                self._recent_host,
                self.pal,
                self.fonts,
                icon="list",
                title="Belum ada kegiatan",
                message="Ketik kegiatan pertamamu di kotak di atas, lalu tekan Enter.",
            )
            empty.pack(fill="x")
            Button(
                empty,
                text="Catat sekarang",
                command=self.focus_input,
                variant="subtle",
                pal=self.pal,
                fonts=self.fonts,
                size="sm",
                icon="plus",
            ).pack(pady=(12, 0))
            return

        for index, item in enumerate(items):
            row = ActivityRow(
                self._recent_host,
                item,
                self.pal,
                self.fonts,
                layout="table",
                on_toggle=lambda activity: self.app.toggle_activity(activity),
                show_actions=False,
                compact=True,
                show_seconds=bool(self.app.settings.show_seconds),
            )
            row.pack(fill="x", padx=int(self.metrics["card_pad"]))
            row.set_wraplength(max(220, self.width - 260))
            if index == len(items) - 1:
                row._separator.configure(bg=self.pal["surface"])

    def refresh(self) -> None:
        """Perbarui data tanpa membangun ulang kotak input (fokus tetap)."""
        self.refresh_dynamic()

    def refresh_dynamic(self) -> None:
        """Perbarui angka + daftar tanpa mengganggu fokus kotak input."""
        total, month_count = self._counts()
        if len(self._tiles) >= 2:
            self._tiles[0].set(str(total), "semua data")
            self._tiles[1].set(
                str(month_count),
                timeutil.month_label(timeutil.today().year, timeutil.today().month),
            )
        if hasattr(self, "_path_label") and self._path_label.winfo_exists():
            self._path_label.configure(text=self.app.store.path)
        self._fill_recent()
        if self._clock_label is not None and self._clock_label.winfo_exists():
            self._clock_label.configure(text=self._clock_text())

    # ------------------------------------------------------------------ #
    # Aksi
    # ------------------------------------------------------------------ #
    def focus_input(self) -> None:
        if self.field is not None:
            self.field.focus()

    def _submit(self) -> None:
        if self.field is None:
            return
        text = self.field.get()
        if not text:
            self.app.toast("Ketik kegiatan terlebih dahulu", kind="error")
            self.field.focus()
            return
        try:
            activity = self.app.store.add(text)
        except (ValueError, StorageError, OSError) as error:
            self.app.toast(str(error), kind="error")
            return
        self.field.clear()
        self.field.focus()
        self.app.after_save(activity)
        self.refresh_dynamic()
        self.app.toast("Tersimpan pada {}".format(timeutil.fmt_clock(activity.ts)))

    def _clock_text(self) -> str:
        moment = timeutil.now()
        return "Otomatis tersimpan dengan tanggal & waktu: {}. Format 24 jam.".format(
            timeutil.fmt_date_indonesian(moment.date(), with_day=True)
            + " · "
            + timeutil.fmt_clock(moment)
        )

    def _schedule_clock(self) -> None:
        self._clock_after = self.after(20000, self._tick)

    def _tick(self) -> None:
        if self._clock_label is None:
            return
        try:
            if not self._clock_label.winfo_exists():
                return
            self._clock_label.configure(text=self._clock_text())
        except tk.TclError:  # pragma: no cover
            return
        self._clock_after = self.after(20000, self._tick)

    def destroy(self) -> None:
        if self._clock_after is not None:
            try:
                self.after_cancel(self._clock_after)
            except (tk.TclError, ValueError):
                pass
            self._clock_after = None
        super().destroy()

    # ------------------------------------------------------------------ #
    # Responsif
    # ------------------------------------------------------------------ #
    def on_width(self, width: int) -> None:
        super().on_width(width)
        if self.field is not None and self._save_button.winfo_exists():
            narrow = bool(self.metrics.get("narrow"))
            if narrow:
                self.field.pack_configure(side="top", fill="x", expand=False, pady=(0, 10))
                self._save_button.pack_configure(side="top", fill="x", padx=0)
            else:
                self.field.pack_configure(side="left", fill="x", expand=True, pady=0)
                self._save_button.pack_configure(side="left", fill="x", expand=False, padx=(10, 0))
        if self._recent_host is not None:
            for child in self._recent_host.winfo_children():
                if isinstance(child, ActivityRow):
                    child.set_wraplength(max(220, width - 260))
        if hasattr(self, "_path_label") and self._path_label.winfo_exists():
            self._path_label.configure(wraplength=max(180, self._tile_width() - 40))

    def _tile_width(self) -> int:
        columns = 1 if self.narrow else 3
        return max(180, int((self.width - 2 * int(self.metrics["pad"]) - 20 * columns) / columns))
