"""Kelas dasar halaman + helper tata letak yang dipakai semua halaman."""

from __future__ import annotations

import tkinter as tk
from typing import Dict, List, Optional

from ..theme import FontBook
from ..widgets import Button, Card, Chip, ScrollArea, TextField


class BasePage:
    """Satu halaman di area konten.

    Halaman membuat ``self.content`` (sudah diberi padding) lalu mengisi
    ``self.stack`` secara vertikal. Semua ukuran mengikuti ``app.metrics``
    sehingga responsif terhadap lebar jendela.
    """

    key = "beranda"
    title = "Beranda"
    subtitle = ""
    icon = "home"

    def __init__(self, app, parent: tk.Misc) -> None:
        self.app = app
        self.pal: Dict[str, str] = app.pal
        self.fonts: FontBook = app.fonts
        self.width = app.content_width

        self.outer = tk.Frame(parent, bg=self.pal["page"], bd=0)
        self.outer.pack(fill="both", expand=True)

        self.scroll = ScrollArea(
            self.outer,
            bg=self.pal["page"],
            thumb_color=self.pal["border_strong"],
        )
        self.scroll.pack(fill="both", expand=True)

        pad = app.metrics["pad"]
        self.content = tk.Frame(self.scroll.inner, bg=self.pal["page"], bd=0)
        self.content.pack(fill="both", expand=True, padx=pad, pady=(pad, pad))

        self.stack = tk.Frame(self.content, bg=self.pal["page"], bd=0)
        self.stack.pack(fill="both", expand=True)

        self.build()

    # ------------------------------------------------------------------ #
    # Siklus hidup
    # ------------------------------------------------------------------ #
    def build(self) -> None:
        """Bangun isi halaman (diimplementasikan tiap halaman)."""

    def rebuild(self) -> None:
        """Hapus lalu bangun ulang seluruh isi (dipakai setelah data berubah)."""
        for child in list(self.stack.winfo_children()):
            child.destroy()
        self.build()
        self.scroll.scroll_top()

    def refresh(self) -> None:
        """Muat ulang data tanpa mengubah struktur (default: rebuild)."""
        self.rebuild()

    def on_width(self, width: int) -> None:
        """Dipanggil saat area konten berubah lebar."""
        self.width = width

    def after(self, delay: int, callback=None):
        """``tk.after`` yang terikat ke halaman (otomatis berhenti saat halaman hilang)."""
        return self.outer.after(delay, callback)

    def after_cancel(self, identifier) -> None:
        try:
            self.outer.after_cancel(identifier)
        except (tk.TclError, ValueError):  # pragma: no cover
            pass

    def destroy(self) -> None:
        try:
            self.outer.destroy()
        except tk.TclError:  # pragma: no cover
            pass

    # ------------------------------------------------------------------ #
    # Helper
    # ------------------------------------------------------------------ #
    @property
    def metrics(self) -> Dict[str, object]:
        return self.app.metrics

    @property
    def narrow(self) -> bool:
        return bool(self.metrics.get("narrow"))

    def add(self, widget: tk.Widget, pady: int = 0) -> tk.Widget:
        widget.pack(fill="x", pady=(0, pady) if pady else 0)
        return widget

    def heading(self, title: Optional[str] = None, subtitle: Optional[str] = None) -> tk.Frame:
        frame = tk.Frame(self.stack, bg=self.pal["page"])
        tk.Label(
            frame,
            text=title or self.title,
            bg=self.pal["page"],
            fg=self.pal["text"],
            font=self.fonts.display if not self.narrow else self.fonts.get(18, "bold"),
            anchor="w",
            justify="left",
        ).pack(fill="x")
        text = subtitle if subtitle is not None else self.subtitle
        if text:
            tk.Label(
                frame,
                text=text,
                bg=self.pal["page"],
                fg=self.pal["text_muted"],
                font=self.fonts.get(10),
                anchor="w",
                justify="left",
                wraplength=max(260, self.width - 2 * int(self.metrics["pad"])),
            ).pack(fill="x", pady=(3, 0))
        frame.pack(fill="x", pady=(0, int(self.metrics["gap"])))
        return frame

    def card(self, pad: Optional[int] = None, pady: int = 0) -> Card:
        card = Card(self.stack, self.pal, pad=pad if pad is not None else int(self.metrics["card_pad"]))
        card.pack(fill="x", pady=(0, pady or int(self.metrics["gap"])))
        return card

    def chips_row(
        self,
        parent: tk.Misc,
        options: List[tuple],
        current: str,
        on_change,
        bg: Optional[str] = None,
        columns: Optional[int] = None,
    ) -> tk.Frame:
        """Baris pil filter. ``options`` = [(nilai, label), ...].

        Di layar sempit pil disusun dalam kisi 3 kolom supaya tidak terpotong.
        """
        background = bg or self.pal["surface"]
        row = tk.Frame(parent, bg=background)
        row._chips = {}  # type: ignore[attr-defined]
        narrow = bool(self.metrics.get("narrow"))
        cols = columns or (3 if narrow else max(1, len(options)))
        for index, (value, label) in enumerate(options):
            chip = Chip(
                row,
                label,
                self.pal,
                self.fonts,
                command=lambda v=value: on_change(v),
                active=(value == current),
                size="sm" if narrow else "md",
            )
            if narrow:
                chip.grid(
                    row=index // cols,
                    column=index % cols,
                    sticky="ew",
                    padx=(0 if index % cols == 0 else 6, 0),
                    pady=2,
                )
            else:
                chip.pack(side="left", padx=(0, 8), pady=2)
            row._chips[value] = chip  # type: ignore[attr-defined]
        if narrow:
            for column in range(cols):
                row.grid_columnconfigure(column, weight=1, uniform="chips")
        return row

    def range_fields(
        self,
        parent: tk.Misc,
        start_value: str = "",
        end_value: str = "",
        on_apply=None,
        bg: Optional[str] = None,
    ):
        """Dua kolom tanggal "Dari / Sampai" yang menumpuk di layar sempit."""
        background = bg or self.pal["surface"]
        holder = tk.Frame(parent, bg=background)
        narrow = bool(self.metrics.get("narrow"))

        def block(caption: str, value: str) -> TextField:
            container = tk.Frame(holder, bg=background)
            tk.Label(
                container,
                text=caption,
                bg=background,
                fg=self.pal["text_faint"],
                font=self.fonts.get(8, "bold"),
                anchor="w",
            ).pack(fill="x")
            field = TextField(
                container,
                self.pal,
                self.fonts,
                placeholder="YYYY-MM-DD",
                icon="calendar",
                height=36,
                width=150,
            )
            field.pack(fill="x", pady=(4, 0))
            field.set(value)
            return field

        if narrow:
            start = block("Dari tanggal", start_value)
            start.master.pack(fill="x")
            end = block("Sampai tanggal", end_value)
            end.master.pack(fill="x", pady=(8, 0))
            if on_apply is not None:
                Button(
                    holder,
                    text="Terapkan",
                    command=on_apply,
                    variant="subtle",
                    pal=self.pal,
                    fonts=self.fonts,
                    size="sm",
                ).pack(anchor="w", pady=(10, 0))
        else:
            start = block("Dari tanggal", start_value)
            start.master.pack(side="left", fill="x", expand=True)
            end = block("Sampai tanggal", end_value)
            end.master.pack(side="left", fill="x", expand=True, padx=(10, 0))
            if on_apply is not None:
                Button(
                    holder,
                    text="Terapkan",
                    command=on_apply,
                    variant="subtle",
                    pal=self.pal,
                    fonts=self.fonts,
                    size="sm",
                ).pack(side="left", padx=(10, 0), pady=(18, 0))
        return holder, start, end

    def table_header(
        self,
        parent: tk.Misc,
        columns: List[tuple],
        leading: int = 0,
    ) -> tk.Frame:
        """Header tabel: ``columns`` = [(label, weight, anchor, width), ...].

        ``leading`` menambah kolom kosong di kiri agar sejajar dengan baris
        kegiatan yang punya ikon status di depannya.
        """
        frame = tk.Frame(parent, bg=self.pal["surface_soft"])
        frame.pack(fill="x")
        inner = tk.Frame(frame, bg=self.pal["surface_soft"])
        inner.pack(fill="x", padx=12, pady=7)
        offset = 0
        if leading:
            inner.grid_columnconfigure(0, weight=0, minsize=leading)
            tk.Label(inner, text="", bg=self.pal["surface_soft"], width=1).grid(
                row=0, column=0, sticky="w"
            )
            offset = 1
        for index, (label, weight, anchor, minwidth) in enumerate(columns):
            index += offset
            inner.grid_columnconfigure(index, weight=weight, minsize=minwidth)
            tk.Label(
                inner,
                text=label.upper(),
                bg=self.pal["surface_soft"],
                fg=self.pal["text_faint"],
                font=self.fonts.get(8, "bold"),
                anchor=anchor,
            ).grid(row=0, column=index, sticky="ew", padx=(0, 8))
        return frame

    def link_button(self, parent: tk.Misc, text: str, command, icon: str = "arrow_right") -> Button:
        return Button(
            parent,
            text=text,
            command=command,
            variant="link",
            pal=self.pal,
            fonts=self.fonts,
            icon=None,
            size="sm",
            fg=self.pal["primary"],
            bg=self.pal.get(element_bg(parent, self.pal), self.pal["surface"]),
        )


def element_bg(widget: tk.Misc, pal: Dict[str, str]) -> str:
    """Tebak warna latar sebuah wadah (agar tombol "transparan" menyatu)."""
    try:
        return str(widget.cget("bg"))
    except tk.TclError:  # pragma: no cover
        return pal["surface"]


def muted_text(parent: tk.Misc, pal: Dict[str, str], fonts: FontBook, text: str, **kwargs) -> tk.Label:
    kwargs.setdefault("anchor", "w")
    kwargs.setdefault("justify", "left")
    label = tk.Label(
        parent,
        text=text,
        bg=kwargs.pop("bg", pal["surface"]),
        fg=kwargs.pop("fg", pal["text_muted"]),
        font=kwargs.pop("font", fonts.get(9)),
        **kwargs,
    )
    return label
