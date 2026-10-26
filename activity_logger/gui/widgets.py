"""Komponen UI bergaya Bootstrap di atas ``tkinter`` murni.

Semua komponen menerima ``pal`` (palet warna) dan ``font`` (``FontBook``)
sehingga tampilan otomatis mengikuti mode terang/gelap tanpa perlu memanggil
ulang ``configure`` di setiap halaman.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from ..core import timeutil
from . import icons
from .theme import FontBook, darken, lighten, mix

# --------------------------------------------------------------------------- #
# Utilitas
# --------------------------------------------------------------------------- #
def bind_tree(widget: tk.Misc, sequence: str, handler, add: str = "+") -> None:
    """Pasang binding pada widget dan seluruh turunannya."""
    widget.bind(sequence, handler, add=add)
    for child in widget.winfo_children():
        bind_tree(child, sequence, handler, add=add)


def set_bg_tree(widget: tk.Misc, color: str) -> None:
    """Ubah warna latar widget dan semua turunannya (dipakai untuk hover)."""
    try:
        widget.configure(bg=color)
    except tk.TclError:
        pass
    for child in widget.winfo_children():
        set_bg_tree(child, color)


def truncate(text: str, limit: int) -> str:
    text = str(text)
    if limit <= 1:
        return text
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def centered(window: tk.Misc, root: tk.Misc) -> None:
    """Letakkan ``window`` di tengah ``root``."""
    window.update_idletasks()
    try:
        width = window.winfo_reqwidth()
        height = window.winfo_reqheight()
        root_x, root_y = root.winfo_rootx(), root.winfo_rooty()
        root_w, root_h = root.winfo_width(), root.winfo_height()
        x = root_x + max(0, (root_w - width) // 2)
        y = root_y + max(0, (root_h - height) // 3)
        window.geometry("+{}+{}".format(x, y))
    except tk.TclError:  # pragma: no cover
        pass


# --------------------------------------------------------------------------- #
# Tombol
# --------------------------------------------------------------------------- #
class Button(tk.Frame):
    """Tombol dengan varian Bootstrap: primary, outline, ghost, danger, link."""

    SIZES = {
        "sm": (10, 6, 9),
        "md": (14, 8, 10),
        "lg": (18, 11, 11),
    }

    def __init__(
        self,
        parent: tk.Misc,
        text: str = "",
        command: Optional[Callable[[], None]] = None,
        variant: str = "primary",
        pal: Optional[Dict[str, str]] = None,
        fonts: Optional[FontBook] = None,
        icon: Optional[str] = None,
        size: str = "md",
        bg: Optional[str] = None,
        fg: Optional[str] = None,
        hover_bg: Optional[str] = None,
        border: Optional[str] = None,
        font: Optional[Tuple] = None,
        padx: Optional[int] = None,
        pady: Optional[int] = None,
        wide: bool = False,
        state: str = "normal",
        tooltip: Optional[str] = None,
    ) -> None:
        pal = pal or {}
        self.pal = pal
        self.fonts = fonts or FontBook()
        self.variant = variant
        self.command = command
        self.state = state
        self.icon_name = icon
        self._padx, self._pady, base_size = self.SIZES.get(size, self.SIZES["md"])

        colors = self._resolve_colors(variant, pal, bg, fg, hover_bg, border)
        self.bg_normal = colors["bg"]
        self.fg_normal = colors["fg"]
        self.bg_hover = colors["hover"]
        self.fg_hover = colors["fg_hover"]
        self.border = colors["border"]
        self._hovered = False

        super().__init__(
            parent,
            bg=self.bg_normal,
            highlightthickness=1 if self.border else 0,
            highlightbackground=self.border or self.bg_normal,
            highlightcolor=self.border or self.bg_normal,
            bd=0,
            takefocus=1,
        )
        self.configure(cursor="hand2" if state != "disabled" else "arrow")

        inner = tk.Frame(self, bg=self.bg_normal, bd=0)
        inner.pack(
            fill="both",
            expand=True,
            padx=padx if padx is not None else self._padx,
            pady=pady if pady is not None else self._pady,
        )
        self._inner = inner

        self._icon_canvas: Optional[tk.Canvas] = None
        if icon:
            self._icon_canvas = tk.Canvas(
                inner,
                width=16,
                height=16,
                bg=self.bg_normal,
                highlightthickness=0,
                bd=0,
                takefocus=0,
            )
            self._icon_canvas.pack(side="left", padx=(0, 7) if text else 0)
            icons.paint(self._icon_canvas, icon, self.fg_normal, size=16)

        self._label = tk.Label(
            inner,
            text=text,
            bg=self.bg_normal,
            fg=self.fg_normal,
            font=font or self.fonts.get(base_size, "bold"),
            bd=0,
            anchor="center",
        )
        if text:
            self._label.pack(side="left", fill="both", expand=True)
        else:
            inner.pack_configure(padx=max(3, self._padx - 5))

        if tooltip:
            Tooltip(self, tooltip, pal)

        if state == "disabled":
            self._paint(self.bg_normal, mix(self.fg_normal, self.bg_normal, 0.45))
        else:
            bind_tree(self, "<Enter>", self._on_enter)
            bind_tree(self, "<Leave>", self._on_leave)
            bind_tree(self, "<Button-1>", self._on_click)
            bind_tree(self, "<ButtonRelease-1>", self._on_release)
            self.bind("<Return>", lambda _event: self.invoke())
            self.bind("<space>", lambda _event: self.invoke())

    # -- warna ---------------------------------------------------------- #
    def _resolve_colors(self, variant, pal, bg, fg, hover_bg, border) -> Dict[str, str]:
        surface = pal.get("surface", "#ffffff")
        primary = pal.get("primary", "#0f9d6b")
        text = pal.get("text", "#0f172a")
        muted = pal.get("text_muted", "#5b6b82")
        table = {
            "primary": (primary, pal.get("primary_text", "#ffffff"), pal.get("primary_hover", primary), None),
            "outline": (surface, text, pal.get("surface_hover", surface), pal.get("border_strong", muted)),
            "ghost": (surface, muted, pal.get("surface_hover", surface), None),
            "subtle": (pal.get("primary_soft", surface), primary, pal.get("primary_soft", surface), None),
            "danger": (pal.get("danger", "#e11d48"), "#ffffff", pal.get("danger_hover", "#be123c"), None),
            "danger_outline": (
                surface,
                pal.get("danger", "#e11d48"),
                pal.get("danger_soft", surface),
                pal.get("danger", "#e11d48"),
            ),
            "link": (surface, primary, surface, None),
        }
        base_bg, base_fg, base_hover, base_border = table.get(variant, table["primary"])
        resolved = {
            "bg": bg if bg is not None else base_bg,
            "fg": fg if fg is not None else base_fg,
            "hover": hover_bg if hover_bg is not None else base_hover,
            "border": border if border is not None else base_border,
        }
        resolved["fg_hover"] = resolved["fg"]
        if variant == "link":
            resolved["fg_hover"] = pal.get("primary_hover", primary)
        return resolved

    # -- gambar --------------------------------------------------------- #
    def _paint(self, bg: str, fg: str, border: Optional[str] = None) -> None:
        try:
            self.configure(
                bg=bg,
                highlightbackground=border or self.border or bg,
                highlightcolor=border or self.border or bg,
            )
        except tk.TclError:
            pass
        set_bg_tree(self, bg)
        try:
            self._label.configure(fg=fg)
        except tk.TclError:
            pass
        if self._icon_canvas is not None and self.icon_name:
            icons.paint(self._icon_canvas, self.icon_name, fg, size=16)

    # -- event ---------------------------------------------------------- #
    def _on_enter(self, _event=None) -> None:
        if self.state == "disabled":
            return
        self._hovered = True
        self._paint(self.bg_hover, self.fg_hover)

    def _on_leave(self, _event=None) -> None:
        if self.state == "disabled":
            return
        self._hovered = False
        self._paint(self.bg_normal, self.fg_normal)

    def _on_click(self, _event=None) -> None:
        if self.state == "disabled":
            return
        pressed = darken(self.bg_hover, 0.06)
        self._paint(pressed, self.fg_hover)

    def _on_release(self, _event=None) -> None:
        if self.state == "disabled":
            return
        self._paint(self.bg_hover if self._hovered else self.bg_normal, self.fg_hover)
        self.invoke()

    def invoke(self) -> None:
        if self.state == "disabled" or self.command is None:
            return
        self.command()

    # -- API ------------------------------------------------------------ #
    def set_text(self, text: str) -> None:
        self._label.configure(text=text)

    def set_state(self, state: str) -> None:
        self.state = state
        self.configure(cursor="hand2" if state != "disabled" else "arrow")
        if state == "disabled":
            self._paint(self.bg_normal, mix(self.fg_normal, self.bg_normal, 0.45))
        else:
            self._paint(self.bg_normal, self.fg_normal)


class IconButton(tk.Canvas):
    """Tombol kecil berisi ikon (dipakai untuk aksi baris & topbar)."""

    def __init__(
        self,
        parent: tk.Misc,
        icon: str,
        command: Optional[Callable[[], None]] = None,
        pal: Optional[Dict[str, str]] = None,
        size: int = 16,
        pad: int = 6,
        bg: Optional[str] = None,
        fg: Optional[str] = None,
        hover_bg: Optional[str] = None,
        hover_fg: Optional[str] = None,
        tooltip: Optional[str] = None,
        shape: str = "square",
    ) -> None:
        pal = pal or {}
        self.pal = pal
        self.icon_name = icon
        self.command = command
        self.bg_normal = bg or pal.get("surface", "#ffffff")
        self.fg_normal = fg or pal.get("text_muted", "#5b6b82")
        self.bg_hover = hover_bg or pal.get("surface_hover", self.bg_normal)
        self.fg_hover = hover_fg or self.fg_normal
        self.size = size
        self.pad = pad
        self.shape = shape
        box = size + pad * 2
        super().__init__(
            parent,
            width=box,
            height=box,
            bg=self.bg_normal,
            highlightthickness=0,
            bd=0,
            takefocus=0,
            cursor="hand2",
        )
        self._render(self.fg_normal)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        if tooltip:
            Tooltip(self, tooltip, pal)

    def _render(self, color: str) -> None:
        self.delete("all")
        icons.paint(self, self.icon_name, color, size=self.size)

    def _apply(self, bg: str, fg: str) -> None:
        self.configure(bg=bg)
        self._render(fg)

    def _on_enter(self, _event=None) -> None:
        self._apply(self.bg_hover, self.fg_hover)

    def _on_leave(self, _event=None) -> None:
        self._apply(self.bg_normal, self.fg_normal)

    def _on_click(self, _event=None) -> None:
        if self.command is not None:
            self.command()

    def set_icon(self, icon: str, fg: Optional[str] = None) -> None:
        self.icon_name = icon
        if fg is not None:
            self.fg_normal = fg
        self._render(self.fg_normal)


# --------------------------------------------------------------------------- #
# Wadah
# --------------------------------------------------------------------------- #
class Card(tk.Frame):
    """Kartu putih dengan garis tepi 1px (pengganti shadow Bootstrap)."""

    def __init__(
        self,
        parent: tk.Misc,
        pal: Dict[str, str],
        pad: int = 16,
        bg: Optional[str] = None,
        border: Optional[str] = None,
        **kwargs,
    ) -> None:
        self.pal = pal
        self.card_bg = bg or pal["surface"]
        super().__init__(
            parent,
            bg=self.card_bg,
            highlightthickness=1,
            highlightbackground=border or pal["border"],
            highlightcolor=border or pal["border"],
            bd=0,
            **kwargs,
        )
        self.pad = pad
        self.body = tk.Frame(self, bg=self.card_bg, bd=0)
        self.body.pack(fill="both", expand=True, padx=pad, pady=pad)


class Divider(tk.Frame):
    def __init__(self, parent: tk.Misc, pal: Dict[str, str], pady: int = 0) -> None:
        super().__init__(parent, height=1, bg=pal["border"], bd=0)
        self.pack(fill="x", pady=pady)


class SectionHeading(tk.Frame):
    """Judul bagian + subjudul + aksi di kanan."""

    def __init__(
        self,
        parent: tk.Misc,
        pal: Dict[str, str],
        fonts: FontBook,
        title: str,
        subtitle: str = "",
        action: Optional[tk.Widget] = None,
        bg: Optional[str] = None,
    ) -> None:
        background = bg or pal["surface"]
        super().__init__(parent, bg=background)
        text_box = tk.Frame(self, bg=background)
        text_box.pack(side="left", fill="x", expand=True)
        tk.Label(
            text_box,
            text=title,
            bg=background,
            fg=pal["text"],
            font=fonts.h1,
            anchor="w",
        ).pack(fill="x")
        if subtitle:
            tk.Label(
                text_box,
                text=subtitle,
                bg=background,
                fg=pal["text_muted"],
                font=fonts.small,
                anchor="w",
                justify="left",
            ).pack(fill="x", pady=(2, 0))
        if action is not None:
            action.pack(side="right", padx=(12, 0))


class Chip(tk.Label):
    """Pil filter (Bootstrap ``badge``/``nav-pill``)."""

    def __init__(
        self,
        parent: tk.Misc,
        text: str,
        pal: Dict[str, str],
        fonts: FontBook,
        command: Optional[Callable[[], None]] = None,
        active: bool = False,
        size: str = "md",
    ) -> None:
        self.pal = pal
        self.command = command
        self.active = active
        px, py = (12, 6) if size == "md" else (9, 4)
        super().__init__(
            parent,
            text=text,
            font=fonts.get(9 if size == "md" else 8, "bold"),
            padx=px,
            pady=py,
            bd=0,
            highlightthickness=1,
            cursor="hand2",
        )
        self._paint()
        self.bind("<Button-1>", lambda _event: self.invoke())
        self.bind("<Enter>", lambda _event: self._hover(True))
        self.bind("<Leave>", lambda _event: self._hover(False))

    def _paint(self) -> None:
        if self.active:
            bg, fg, border = self.pal["primary"], self.pal["primary_text"], self.pal["primary"]
        else:
            bg, fg, border = self.pal["surface"], self.pal["text_muted"], self.pal["border"]
        self.configure(bg=bg, fg=fg, highlightbackground=border, highlightcolor=border)

    def _hover(self, inside: bool) -> None:
        if self.active:
            return
        self.configure(
            bg=self.pal["surface_hover"] if inside else self.pal["surface"],
            fg=self.pal["text"] if inside else self.pal["text_muted"],
        )

    def set_active(self, active: bool) -> None:
        self.active = active
        self._paint()

    def invoke(self) -> None:
        if self.command is not None:
            self.command()


class NavItem(tk.Frame):
    """Satu baris navigasi di sidebar."""

    def __init__(
        self,
        parent: tk.Misc,
        pal: Dict[str, str],
        fonts: FontBook,
        icon: str,
        label: str,
        command: Callable[[], None],
        active: bool = False,
        collapsed: bool = False,
    ) -> None:
        self.pal = pal
        self.fonts = fonts
        self.icon_name = icon
        self.label_text = label
        self.command = command
        self.active = active
        self.collapsed = collapsed
        self.height = 40

        super().__init__(parent, bg=pal["sidebar"], bd=0, cursor="hand2")
        self._indicator = tk.Frame(self, width=3, bg=pal["sidebar"], bd=0)
        self._indicator.pack(side="left", fill="y")

        self._icon = tk.Canvas(
            self,
            width=18,
            height=18,
            bg=pal["sidebar"],
            highlightthickness=0,
            bd=0,
            takefocus=0,
        )
        self._icon.pack(side="left", padx=(12 if collapsed else 13, 0), pady=11)

        self._label = tk.Label(
            self,
            text=label,
            bg=pal["sidebar"],
            fg=pal["sidebar_text"],
            font=fonts.body,
            anchor="w",
            bd=0,
        )
        if not collapsed:
            self._label.pack(side="left", padx=(11, 8), fill="x", expand=True)

        if collapsed:
            Tooltip(self, label, pal)

        self._paint()
        bind_tree(self, "<Button-1>", lambda _event: self.command())
        bind_tree(self, "<Enter>", lambda _event: self._hover(True))
        bind_tree(self, "<Leave>", lambda _event: self._hover(False))

    def _paint(self) -> None:
        if self.active:
            bg = self.pal["primary"]
            fg = self.pal["sidebar_text_active"]
            indicator = lighten(self.pal["primary"], 0.45)
        else:
            bg = self.pal["sidebar"]
            fg = self.pal["sidebar_text"]
            indicator = self.pal["sidebar"]
        self.configure(bg=bg)
        set_bg_tree(self, bg)
        self._indicator.configure(bg=indicator)
        self._label.configure(fg=fg)
        icons.paint(self._icon, self.icon_name, fg, size=18)

    def _hover(self, inside: bool) -> None:
        if self.active:
            return
        bg = self.pal["sidebar_soft"] if inside else self.pal["sidebar"]
        fg = self.pal["sidebar_text_active"] if inside else self.pal["sidebar_text"]
        self.configure(bg=bg)
        set_bg_tree(self, bg)
        self._indicator.configure(bg=bg)
        self._label.configure(fg=fg)
        icons.paint(self._icon, self.icon_name, fg, size=18)


# --------------------------------------------------------------------------- #
# Scroll area
# --------------------------------------------------------------------------- #
class ScrollArea(tk.Frame):
    """Area gulir dengan kanvas + thumb tipis buatan sendiri."""

    def __init__(
        self,
        parent: tk.Misc,
        bg: str,
        scrollbar: bool = True,
        thumb_color: str = "#cbd5e1",
        trough_color: Optional[str] = None,
    ) -> None:
        super().__init__(parent, bg=bg, bd=0, highlightthickness=0)
        self.bg = bg
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0, takefocus=1)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=bg, bd=0)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self._scroll_area = self
        self.inner._scroll_area = self  # type: ignore[attr-defined]
        self.canvas._scroll_area = self  # type: ignore[attr-defined]

        self.thumb: Optional[tk.Canvas] = None
        if scrollbar:
            self.thumb = tk.Canvas(
                self,
                width=10,
                bg=trough_color or bg,
                highlightthickness=0,
                bd=0,
                takefocus=0,
            )
            self.thumb.pack(side="right", fill="y", padx=(2, 2), pady=2)
            self.thumb_color = thumb_color
            self.thumb.bind("<Button-1>", self._thumb_click)
            self.thumb.bind("<B1-Motion>", self._thumb_drag)
            self._drag_offset = 0.0

        self.inner.bind("<Configure>", self._on_inner)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.configure(yscrollcommand=self._on_scroll)

    # -- ukuran --------------------------------------------------------- #
    def _on_inner(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._draw_thumb()

    def _on_canvas(self, event) -> None:
        self.canvas.itemconfigure(self._window, width=event.width)
        self._draw_thumb()

    def _on_scroll(self, first, last) -> None:
        self._first, self._last = float(first), float(last)
        self._draw_thumb()

    # -- interaksi ------------------------------------------------------ #
    def scroll_steps(self, steps: int) -> None:
        if self.inner.winfo_height() <= self.canvas.winfo_height():
            return
        self.canvas.yview_scroll(steps, "units")
        self._draw_thumb()

    def scroll_top(self) -> None:
        self.canvas.yview_moveto(0.0)
        self._draw_thumb()

    def view_fraction(self) -> float:
        try:
            return float(self.canvas.yview()[0])
        except tk.TclError:  # pragma: no cover
            return 0.0

    def _draw_thumb(self) -> None:
        if self.thumb is None:
            return
        thumb = self.thumb
        height = thumb.winfo_height()
        width = thumb.winfo_width()
        if height <= 1:
            height = max(60, self.winfo_height())
        if width <= 1:
            width = 10
        thumb.delete("thumb")
        first = getattr(self, "_first", 0.0)
        last = getattr(self, "_last", 1.0)
        if last - first >= 0.999 or last <= 0:
            return
        top = int(first * height)
        bottom = max(top + 24, int(last * height))
        bottom = min(bottom, height)
        thumb.create_rectangle(
            2, top, width - 2, bottom,
            fill=self.thumb_color, outline=self.thumb_color, width=0, tags="thumb",
        )

    def _thumb_click(self, event) -> None:
        first = getattr(self, "_first", 0.0)
        last = getattr(self, "_last", 1.0)
        height = max(1, self.thumb.winfo_height())
        thumb_top = first * height
        thumb_bottom = last * height
        if thumb_top <= event.y <= thumb_bottom:
            self._drag_offset = (event.y - thumb_top) / height
        else:
            self._drag_offset = (last - first) / 2
            self._jump_to(event.y / height)
        self._draw_thumb()

    def _thumb_drag(self, event) -> None:
        height = max(1, self.thumb.winfo_height())
        self._jump_to(event.y / height - self._drag_offset)

    def _jump_to(self, fraction: float) -> None:
        span = getattr(self, "_last", 1.0) - getattr(self, "_first", 0.0)
        target = max(0.0, min(1.0 - span, fraction))
        self.canvas.yview_moveto(target)
        self._draw_thumb()


def install_wheel_support(root: tk.Misc) -> None:
    """Satu handler global: gulir area yang paling dekat dengan kursor."""

    def dispatch(event, steps: int):
        widget = event.widget
        while widget is not None:
            area = getattr(widget, "_scroll_area", None)
            if area is not None:
                area.scroll_steps(steps)
                return "break"
            widget = getattr(widget, "master", None)
        return None

    def on_wheel(event):
        # Windows/macOS: delta bisa 120 (mouse) atau kecil (trackpad).
        delta = getattr(event, "delta", 0) or 0
        if delta == 0:
            return None
        steps = -1 if delta > 0 else 1
        magnitude = abs(delta)
        if magnitude >= 100:
            steps *= max(1, magnitude // 120)
        elif magnitude < 4:
            steps *= 1
        return dispatch(event, steps)

    def on_button4(event):
        return dispatch(event, -1)

    def on_button5(event):
        return dispatch(event, 1)

    def on_key(event):
        widget = event.widget
        area = None
        while widget is not None:
            area = getattr(widget, "_scroll_area", None)
            if area is not None:
                break
            widget = getattr(widget, "master", None)
        if area is None:
            return None
        if event.keysym == "Prior":
            area.scroll_steps(-6)
            return "break"
        if event.keysym == "Next":
            area.scroll_steps(6)
            return "break"
        return None

    for sequence, handler in (
        ("<MouseWheel>", on_wheel),
        ("<Button-4>", on_button4),
        ("<Button-5>", on_button5),
        ("<Prior>", on_key),
        ("<Next>", on_key),
    ):
        try:
            root.bind_all(sequence, handler, add="+")
        except tk.TclError:  # pragma: no cover
            pass


# --------------------------------------------------------------------------- #
# Input
# --------------------------------------------------------------------------- #
class TextField(tk.Frame):
    """Kotak input berikon (Bootstrap ``input-group``)."""

    def __init__(
        self,
        parent: tk.Misc,
        pal: Dict[str, str],
        fonts: FontBook,
        placeholder: str = "",
        icon: Optional[str] = "edit",
        font: Optional[Tuple] = None,
        height: int = 40,
        width: int = 240,
    ) -> None:
        self.pal = pal
        self.fonts = fonts
        self.placeholder = placeholder
        super().__init__(
            parent,
            bg=pal["surface_soft"],
            highlightthickness=1,
            highlightbackground=pal["border"],
            highlightcolor=pal["primary"],
            bd=0,
        )
        self._icon: Optional[tk.Canvas] = None
        if icon:
            self._icon = tk.Canvas(
                self,
                width=18,
                height=18,
                bg=pal["surface_soft"],
                highlightthickness=0,
                bd=0,
                takefocus=0,
            )
            self._icon.pack(side="left", padx=(12, 6))
            icons.paint(self._icon, icon, pal["text_faint"], size=18)
            self._icon.bind("<Button-1>", lambda _event: self.entry.focus_set())

        self.var = tk.StringVar()
        self.entry = tk.Entry(
            self,
            textvariable=self.var,
            bd=0,
            relief="flat",
            bg=pal["surface_soft"],
            fg=pal["text"],
            insertbackground=pal["primary"],
            highlightthickness=0,
            font=font or fonts.get(11),
            disabledbackground=pal["surface"],
        )
        self.entry.pack(side="left", fill="both", expand=True, padx=(0, 12), pady=0)
        self.configure(height=height, width=width)
        self.pack_propagate(False)

        self._showing_placeholder = False
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self._show_placeholder()

    # -- placeholder ---------------------------------------------------- #
    def _show_placeholder(self) -> None:
        if self.placeholder and not self.var.get():
            self._showing_placeholder = True
            self.entry.configure(fg=self.pal["text_faint"])
            self.var.set(self.placeholder)

    def _clear_placeholder(self) -> None:
        if self._showing_placeholder:
            self._showing_placeholder = False
            self.var.set("")
            self.entry.configure(fg=self.pal["text"])

    def _on_focus_in(self, _event=None) -> None:
        self._clear_placeholder()
        self.configure(highlightbackground=self.pal["primary"])

    def _on_focus_out(self, _event=None) -> None:
        self.configure(highlightbackground=self.pal["border"])
        self._show_placeholder()

    # -- API ------------------------------------------------------------ #
    def get(self) -> str:
        return "" if self._showing_placeholder else self.var.get().strip()

    def set(self, value: str) -> None:
        self._showing_placeholder = False
        self.var.set(value or "")
        if not value:
            self._show_placeholder()

    def clear(self) -> None:
        self._showing_placeholder = False
        self.var.set("")
        self.entry.configure(fg=self.pal["text"])

    def focus(self) -> None:
        self._clear_placeholder()
        self.entry.focus_set()

    def bind_return(self, callback: Callable[[], None]) -> None:
        self.entry.bind("<Return>", lambda _event: callback())


# --------------------------------------------------------------------------- #
# Baris kegiatan
# --------------------------------------------------------------------------- #
class ActivityRow(tk.Frame):
    """Satu kegiatan: status, waktu, teks, dan aksi.

    Dua tata letak tersedia:

    * ``table`` — kolom "Tanggal & Waktu" di kiri (lebar tetap), cocok untuk
      layar lebar.
    * ``stack`` — teks di atas dan waktu kecil di bawahnya, cocok untuk layar
      sempit/HP.
    """

    def __init__(
        self,
        parent: tk.Misc,
        activity,
        pal: Dict[str, str],
        fonts: FontBook,
        layout: str = "table",
        on_toggle: Optional[Callable] = None,
        on_edit: Optional[Callable] = None,
        on_delete: Optional[Callable] = None,
        show_actions: bool = True,
        show_toggle: bool = True,
        compact: bool = False,
        tooltip_time: bool = True,
        show_seconds: bool = False,
    ) -> None:
        self.pal = pal
        self.fonts = fonts
        self.activity = activity
        self.layout = layout
        self.show_actions = show_actions
        self.compact = compact
        self.show_seconds = bool(show_seconds)
        super().__init__(parent, bg=pal["surface"], bd=0)

        self.content = tk.Frame(self, bg=pal["surface"], bd=0)
        self.content.pack(fill="x", expand=True)
        self._separator = tk.Frame(self, height=1, bg=pal["border"], bd=0)
        self._separator.pack(fill="x")

        pad_y = 8 if compact else 11

        # -- status (bisa diklik untuk menandai selesai) ---------------- #
        self.check = tk.Canvas(
            self.content,
            width=20,
            height=20,
            bg=pal["surface"],
            highlightthickness=0,
            bd=0,
            takefocus=0,
            cursor="hand2" if (on_toggle and show_toggle) else "arrow",
        )
        self.check.grid(row=0, column=0, sticky="nw", padx=(0, 11), pady=(pad_y, pad_y))
        self._draw_check()
        if on_toggle and show_toggle:
            self.check.bind("<Button-1>", lambda _event: on_toggle(activity))
            Tooltip(
                self.check,
                "Tandai selesai" if not activity.done else "Tandai belum selesai",
                pal,
            )

        # -- kapan ------------------------------------------------------ #
        when_text = self._when_text(day_name=(layout == "stack"))
        if layout == "table":
            self.when_label = tk.Label(
                self.content,
                text=when_text,
                bg=pal["surface"],
                fg=pal["text_faint"] if not activity.done else pal["text_faint"],
                font=fonts.mono(9),
                anchor="w",
                justify="left",
                width=20,
            )
            self.when_label.grid(
                row=0, column=1, sticky="nw", padx=(0, 14), pady=(pad_y + 1, 0)
            )
            text_column, action_column = 2, 3
        else:
            self.when_label = tk.Label(
                self.content,
                text=when_text,
                bg=pal["surface"],
                fg=pal["text_faint"],
                font=fonts.get(8),
                anchor="w",
                justify="left",
            )
            text_column, action_column = 1, 2

        # -- teks kegiatan ---------------------------------------------- #
        text_size = 10 if compact else 11
        self.text_label = tk.Label(
            self.content,
            text=activity.text,
            bg=pal["surface"],
            fg=pal["text_muted"] if activity.done else pal["text"],
            font=fonts.struck(text_size) if activity.done else fonts.get(text_size),
            anchor="w",
            justify="left",
            wraplength=420,
        )
        self.text_label.grid(
            row=0, column=text_column, sticky="w", pady=(pad_y, 0 if layout == "stack" else pad_y)
        )
        if layout == "stack":
            self.when_label.grid(
                row=1, column=text_column, sticky="w", pady=(1, pad_y)
            )

        # -- aksi ------------------------------------------------------- #
        self.actions = tk.Frame(self.content, bg=pal["surface"], bd=0)
        self.actions.grid(
            row=0,
            column=action_column,
            rowspan=2,
            sticky="ne",
            padx=(8, 0),
            pady=(pad_y - 4, 0),
        )
        if show_actions:
            if on_edit is not None:
                IconButton(
                    self.actions,
                    "edit",
                    command=lambda: on_edit(activity),
                    pal=pal,
                    size=14,
                    pad=5,
                    bg=pal["surface"],
                    fg=pal["text_faint"],
                    hover_bg=pal["surface_hover"],
                    hover_fg=pal["primary"],
                    tooltip="Ubah kegiatan",
                ).pack(side="left")
            if on_delete is not None:
                IconButton(
                    self.actions,
                    "trash",
                    command=lambda: on_delete(activity),
                    pal=pal,
                    size=14,
                    pad=5,
                    bg=pal["surface"],
                    fg=pal["text_faint"],
                    hover_bg=pal["danger_soft"],
                    hover_fg=pal["danger"],
                    tooltip="Hapus kegiatan",
                ).pack(side="left")
        else:
            self.actions.grid_remove()

        self.content.grid_columnconfigure(text_column, weight=1)
        bind_tree(self.content, "<Enter>", self._hover_on)
        bind_tree(self.content, "<Leave>", self._hover_off)
        if tooltip_time:
            Tooltip(
                self.text_label,
                "{} · {} — {} WIB".format(
                    activity.day_name,
                    _short_date(activity.date),
                    activity.clock(True),
                ),
                pal,
            )

    # -- teks ----------------------------------------------------------- #
    def _when_text(self, day_name: bool = False) -> str:
        activity = self.activity
        if day_name:
            return "{} · {} · {}".format(
                activity.day_name,
                _short_date(activity.date),
                activity.clock(seconds=self.show_seconds),
            )
        return "{} · {}".format(
            _short_date(activity.date), activity.clock(seconds=self.show_seconds)
        )

    def _draw_check(self) -> None:
        self.check.delete("all")
        pal = self.pal
        if self.activity.done:
            self.check.create_oval(
                1, 1, 19, 19, fill=pal["primary"], outline=pal["primary"], width=0
            )
            self.check.create_line(
                5.5, 10.2, 8.6, 13.4, 14.6, 6.8,
                fill=pal["primary_text"], width=2, capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )
        else:
            self.check.create_oval(
                1.5, 1.5, 18.5, 18.5, outline=pal["border_strong"], width=1.6
            )

    # -- hover ---------------------------------------------------------- #
    def _paint_bg(self, color: str) -> None:
        self.configure(bg=color)
        self.content.configure(bg=color)
        for widget in (self.check, self.text_label, self.when_label, self.actions):
            try:
                widget.configure(bg=color)
            except tk.TclError:  # pragma: no cover
                pass
        for child in self.actions.winfo_children():
            if isinstance(child, tk.Canvas):
                child.bg_normal = color
                child.configure(bg=color)
                child._render(child.fg_normal)

    def _hover_on(self, _event=None) -> None:
        self._paint_bg(self.pal["surface_hover"])

    def _hover_off(self, _event=None) -> None:
        self._paint_bg(self.pal["surface"])

    def set_wraplength(self, pixels: int) -> None:
        self.text_label.configure(wraplength=max(160, pixels))


def _short_date(moment) -> str:
    return timeutil.fmt_date_short(moment) if hasattr(moment, "day") else str(moment)


# --------------------------------------------------------------------------- #
# Statistik
# --------------------------------------------------------------------------- #
class StatTile(Card):
    """Kartu statistik: ikon berwarna, judul, angka besar, keterangan."""

    def __init__(
        self,
        parent: tk.Misc,
        pal: Dict[str, str],
        fonts: FontBook,
        icon: str,
        title: str,
        value: str,
        caption: str = "",
        accent: str = "primary",
        command: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent, pal=pal, pad=14)
        self.fonts = fonts
        self.accent = accent
        self.command = command

        head = tk.Frame(self.body, bg=pal["surface"])
        head.pack(fill="x")

        icon_bg = pal.get(accent + "_soft", pal["primary_soft"])
        icon_fg = pal.get(accent, pal["primary"])
        self._icon_box = tk.Frame(head, bg=icon_bg, bd=0, width=38, height=38)
        self._icon_box.pack(side="left")
        self._icon_box.pack_propagate(False)
        canvas = tk.Canvas(
            self._icon_box,
            width=18,
            height=18,
            bg=icon_bg,
            highlightthickness=0,
            bd=0,
            takefocus=0,
        )
        canvas.pack(expand=True)
        icons.paint(canvas, icon, icon_fg, size=18)

        tk.Label(
            head,
            text=title,
            bg=pal["surface"],
            fg=pal["text_muted"],
            font=fonts.get(9),
            anchor="w",
        ).pack(side="left", padx=(10, 0))

        self.value_label = tk.Label(
            self.body,
            text=value,
            bg=pal["surface"],
            fg=pal["text"],
            font=fonts.numeral,
            anchor="w",
        )
        self.value_label.pack(fill="x", pady=(8, 0))

        self.caption_label = tk.Label(
            self.body,
            text=caption,
            bg=pal["surface"],
            fg=pal["text_faint"],
            font=fonts.get(9),
            anchor="w",
            justify="left",
        )
        self.caption_label.pack(fill="x", pady=(1, 0))

        if command is not None:
            self.configure(cursor="hand2")
            bind_tree(self, "<Button-1>", lambda _event: command())
            bind_tree(self, "<Enter>", lambda _event: self.configure(highlightbackground=pal["primary"]))
            bind_tree(self, "<Leave>", lambda _event: self.configure(highlightbackground=pal["border"]))

    def set(self, value: str, caption: Optional[str] = None) -> None:
        self.value_label.configure(text=value)
        if caption is not None:
            self.caption_label.configure(text=caption)


class BarChart(tk.Canvas):
    """Grafik batang sederhana (tanpa dependensi) dengan label & hover."""

    def __init__(
        self,
        parent: tk.Misc,
        pal: Dict[str, str],
        fonts: FontBook,
        height: int = 190,
        label_every: Optional[int] = None,
    ) -> None:
        self.pal = pal
        self.fonts = fonts
        self._data: List[Tuple[object, int]] = []
        self._label_every = label_every
        self._hover_index: Optional[int] = None
        super().__init__(
            parent,
            bg=pal["surface"],
            height=height,
            highlightthickness=0,
            bd=0,
            takefocus=0,
        )
        self.bind("<Configure>", lambda _event: self.redraw())
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self._bars: List[Tuple[float, float]] = []

    def set_data(self, data: Sequence[Tuple[object, int]]) -> None:
        self._data = list(data)
        self.redraw()

    # -- gambar --------------------------------------------------------- #
    def redraw(self) -> None:
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 10:
            width = 480
        if height <= 10:
            height = 190

        pal = self.pal
        if not self._data:
            self.create_text(
                width / 2, height / 2,
                text="Belum ada data untuk ditampilkan",
                fill=pal["text_faint"], font=self.fonts.get(10),
            )
            return

        top_pad, bottom_pad, left_pad, right_pad = 16, 24, 4, 4
        plot_h = max(20, height - top_pad - bottom_pad)
        plot_w = max(20, width - left_pad - right_pad)
        peak = max(count for _, count in self._data) or 1

        # garis bantu horizontal
        for step in range(0, 4):
            y = top_pad + plot_h * step / 3.0
            self.create_line(
                left_pad, y, width - right_pad, y,
                fill=pal["chart_grid"], width=1,
            )

        count = len(self._data)
        slot = plot_w / count
        bar_w = max(3.0, min(28.0, slot * 0.62))
        self._bars = []
        for index, (day, value) in enumerate(self._data):
            center = left_pad + slot * (index + 0.5)
            bar_h = 0 if value == 0 else max(3.0, plot_h * value / peak)
            x1, x2 = center - bar_w / 2, center + bar_w / 2
            y1, y2 = top_pad + plot_h - bar_h, top_pad + plot_h
            color = pal["chart"] if index != self._hover_index else pal["primary_hover"]
            if value == 0:
                self.create_line(
                    x1, y2 - 1, x2, y2 - 1, fill=pal["chart_grid"], width=2
                )
            else:
                self.create_rectangle(
                    x1, y1, x2, y2, fill=color, outline=color, width=0,
                )
            self._bars.append((x1, x2))

            show_label = True
            if self._label_every:
                show_label = index % self._label_every == 0
            elif count > 12:
                show_label = index % max(1, count // 8) == 0
            if show_label and hasattr(day, "day"):
                self.create_text(
                    center, height - 10,
                    text=str(getattr(day, "day")),
                    fill=pal["text_faint"], font=self.fonts.get(8),
                )

        total = sum(value for _, value in self._data)
        self.create_text(
            right_pad + 2, 4,
            text="maks {}".format(peak),
            anchor="ne", fill=pal["text_faint"], font=self.fonts.get(8),
        )
        if total == 0:
            self.create_text(
                width / 2, top_pad + plot_h / 2,
                text="Belum ada kegiatan pada rentang ini",
                fill=pal["text_faint"], font=self.fonts.get(10),
            )

        if self._hover_index is not None and self._hover_index < len(self._data):
            day, value = self._data[self._hover_index]
            label = "{}: {} kegiatan".format(_hover_label(day), value)
            self.create_text(
                left_pad + 2, 6, text=label, anchor="nw",
                fill=pal["text"], font=self.fonts.get(9, "bold"),
            )

    # -- hover ---------------------------------------------------------- #
    def _index_at(self, x: float) -> Optional[int]:
        if not self._bars:
            return None
        for index, (x1, x2) in enumerate(self._bars):
            if x1 - 2 <= x <= x2 + 2:
                return index
        best = min(
            range(len(self._bars)),
            key=lambda i: abs((self._bars[i][0] + self._bars[i][1]) / 2 - x),
        )
        return best

    def _on_motion(self, event) -> None:
        index = self._index_at(event.x)
        if index != self._hover_index:
            self._hover_index = index
            self.redraw()

    def _on_leave(self, _event=None) -> None:
        if self._hover_index is not None:
            self._hover_index = None
            self.redraw()


def _hover_label(day) -> str:
    if hasattr(day, "year"):
        return timeutil.fmt_date_short(day)
    return str(day)


# --------------------------------------------------------------------------- #
# Umpan balik: toast, tooltip, modal
# --------------------------------------------------------------------------- #
class Toast(tk.Frame):
    """Notifikasi kecil yang muncul lalu hilang sendiri."""

    def __init__(self, parent: tk.Misc, pal: Dict[str, str], fonts: FontBook) -> None:
        super().__init__(
            parent,
            bg=pal["overlay"],
            highlightthickness=1,
            highlightbackground=pal["primary"],
            bd=0,
        )
        self.pal = pal
        self.fonts = fonts
        self._timer: Optional[str] = None
        self.bottom_offset = 0
        self._icon = tk.Canvas(
            self, width=16, height=16, bg=pal["overlay"], highlightthickness=0, bd=0
        )
        self._icon.pack(side="left", padx=(12, 8), pady=10)
        self._label = tk.Label(
            self,
            text="",
            bg=pal["overlay"],
            fg="#ffffff",
            font=fonts.get(10),
            anchor="w",
            justify="left",
        )
        self._label.pack(side="left", padx=(0, 14), pady=10)
        self._visible = False

    def show(self, message: str, kind: str = "success", duration: int = 2600) -> None:
        colors = {
            "success": (self.pal["primary"], "check_circle"),
            "error": (self.pal["danger"], "alert"),
            "info": (self.pal["info"], "info"),
        }
        color, icon = colors.get(kind, colors["success"])
        self.configure(highlightbackground=color)
        icons.paint(self._icon, icon, color, size=16)
        self._label.configure(text=message)
        self.place(relx=0.985, rely=0.975, y=-int(self.bottom_offset), anchor="se")
        self.lift()
        self._visible = True
        if self._timer is not None:
            try:
                self.after_cancel(self._timer)
            except (tk.TclError, ValueError):
                pass
        self._timer = self.after(duration, self.hide)

    def hide(self) -> None:
        self._visible = False
        self._timer = None
        try:
            self.place_forget()
        except tk.TclError:  # pragma: no cover - widget sudah dihancurkan
            pass


def _tooltip_font():
    """Font tooltip yang aman di semua platform."""
    try:
        from tkinter import font as tkfont

        base = tkfont.nametofont("TkDefaultFont")
        return (base.actual("family"), 9)
    except Exception:  # pragma: no cover - Tk tidak standar
        return ("TkDefaultFont", 9)


class Tooltip:
    """Tooltip ringan (delay 450 ms) tanpa dependensi eksternal."""

    def __init__(
        self,
        widget: tk.Misc,
        text: str,
        pal: Dict[str, str],
        delay: int = 450,
        wraplength: int = 240,
    ) -> None:
        self.widget = widget
        self.text = text
        self.pal = pal
        self.delay = delay
        self.wraplength = wraplength
        self._after: Optional[str] = None
        self._window: Optional[tk.Toplevel] = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None) -> None:
        self._cancel()
        try:
            self._after = self.widget.after(self.delay, self._show)
        except tk.TclError:  # pragma: no cover
            self._after = None

    def _cancel(self) -> None:
        if self._after is not None:
            try:
                self.widget.after_cancel(self._after)
            except (tk.TclError, ValueError):
                pass
            self._after = None

    def _show(self) -> None:
        if self._window is not None:
            return
        try:
            x = self.widget.winfo_rootx()
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            window = tk.Toplevel(self.widget)
            window.wm_overrideredirect(True)
            window.configure(bg=self.pal["border_strong"])
            label = tk.Label(
                window,
                text=self.text,
                bg=self.pal["surface"],
                fg=self.pal["text"],
                font=_tooltip_font(),
                padx=9,
                pady=6,
                wraplength=self.wraplength,
                justify="left",
            )
            label.pack(padx=1, pady=1)
            window.update_idletasks()
            width = window.winfo_reqwidth()
            screen = self.widget.winfo_screenwidth()
            if x + width > screen:
                x = screen - width - 8
            window.wm_geometry("+{}+{}".format(x, y))
            self._window = window
        except tk.TclError:  # pragma: no cover
            self._window = None

    def _hide(self, _event=None) -> None:
        self._cancel()
        if self._window is not None:
            try:
                self._window.destroy()
            except tk.TclError:  # pragma: no cover
                pass
            self._window = None


class Modal(tk.Toplevel):
    """Dialog modal serbaguna (konfirmasi, input, atau info)."""

    def __init__(
        self,
        app,
        title: str,
        message: str = "",
        confirm_label: str = "Ya",
        cancel_label: Optional[str] = "Batal",
        kind: str = "primary",
        entry_value: Optional[str] = None,
        entry_label: str = "",
        width: int = 420,
    ) -> None:
        self.app = app
        self.pal = app.pal
        self.fonts = app.fonts
        self.result: Optional[str] = None
        super().__init__(app.root, bg=self.pal["page"])
        self.title(title)
        self.resizable(False, False)
        self.transient(app.root)
        self.configure(bg=self.pal["page"])
        try:
            self.attributes("-topmost", False)
        except tk.TclError:  # pragma: no cover
            pass

        wrapper = tk.Frame(self, bg=self.pal["page"])
        wrapper.pack(fill="both", expand=True, padx=14, pady=14)
        card = Card(wrapper, self.pal, pad=20)
        card.pack(fill="both", expand=True)

        tk.Label(
            card.body,
            text=title,
            bg=self.pal["surface"],
            fg=self.pal["text"],
            font=self.fonts.h1,
            anchor="w",
            justify="left",
            wraplength=width - 60,
        ).pack(fill="x")
        if message:
            tk.Label(
                card.body,
                text=message,
                bg=self.pal["surface"],
                fg=self.pal["text_muted"],
                font=self.fonts.get(10),
                anchor="w",
                justify="left",
                wraplength=width - 60,
            ).pack(fill="x", pady=(6, 0))

        self.entry: Optional[tk.Entry] = None
        if entry_value is not None:
            if entry_label:
                tk.Label(
                    card.body,
                    text=entry_label,
                    bg=self.pal["surface"],
                    fg=self.pal["text_muted"],
                    font=self.fonts.get(9),
                    anchor="w",
                ).pack(fill="x", pady=(14, 4))
            box = tk.Frame(
                card.body,
                bg=self.pal["surface_soft"],
                highlightthickness=1,
                highlightbackground=self.pal["border"],
                highlightcolor=self.pal["primary"],
            )
            box.pack(fill="x", pady=(8, 0))
            self.entry = tk.Entry(
                box,
                bd=0,
                relief="flat",
                bg=self.pal["surface_soft"],
                fg=self.pal["text"],
                insertbackground=self.pal["primary"],
                highlightthickness=0,
                font=self.fonts.get(11),
            )
            self.entry.pack(fill="x", padx=10, pady=9)
            self.entry.insert(0, entry_value)
            self.entry.select_range(0, "end")

        buttons = tk.Frame(card.body, bg=self.pal["surface"])
        buttons.pack(fill="x", pady=(18, 0))
        confirm_variant = "danger" if kind == "danger" else "primary"
        Button(
            buttons,
            text=confirm_label,
            command=self._confirm,
            variant=confirm_variant,
            pal=self.pal,
            fonts=self.fonts,
            size="md",
        ).pack(side="right")
        if cancel_label:
            Button(
                buttons,
                text=cancel_label,
                command=self._cancel,
                variant="outline",
                pal=self.pal,
                fonts=self.fonts,
                size="md",
            ).pack(side="right", padx=(0, 8))

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _event: self._cancel())
        self.bind("<Return>", lambda _event: self._confirm())
        centered(self, app.root)
        self.grab_set()
        if self.entry is not None:
            self.entry.focus_set()
        else:
            self.focus_set()

    def _confirm(self) -> None:
        self.result = self.entry.get() if self.entry is not None else ""
        self._close()

    def _cancel(self) -> None:
        self.result = None
        self._close()

    def _close(self) -> None:
        try:
            self.grab_release()
        except tk.TclError:  # pragma: no cover
            pass
        self.destroy()

    def show(self) -> Optional[str]:
        """Tampilkan dan tunggu hasil (``None`` bila dibatalkan)."""
        self.wait_window()
        return self.result


def confirm(app, title: str, message: str, confirm_label: str = "Ya, lanjutkan", danger: bool = False) -> bool:
    dialog = Modal(
        app,
        title,
        message,
        confirm_label=confirm_label,
        kind="danger" if danger else "primary",
    )
    return dialog.show() is not None


def prompt(app, title: str, message: str = "", value: str = "", confirm_label: str = "Simpan") -> Optional[str]:
    dialog = Modal(
        app,
        title,
        message,
        confirm_label=confirm_label,
        entry_value=value,
    )
    return dialog.show()


def info(app, title: str, message: str, confirm_label: str = "Mengerti") -> None:
    dialog = Modal(app, title, message, confirm_label=confirm_label, cancel_label=None)
    dialog.show()


class EmptyState(tk.Frame):
    """Tampilan kosong yang ramah (ikon, judul, saran)."""

    def __init__(
        self,
        parent: tk.Misc,
        pal: Dict[str, str],
        fonts: FontBook,
        icon: str = "list",
        title: str = "Belum ada data",
        message: str = "",
        action: Optional[tk.Widget] = None,
        bg: Optional[str] = None,
    ) -> None:
        background = bg or pal["surface"]
        super().__init__(parent, bg=background)
        box = tk.Frame(self, bg=background)
        box.pack(pady=26)
        circle = tk.Frame(box, bg=pal["surface_soft"], width=54, height=54)
        circle.pack()
        circle.pack_propagate(False)
        canvas = tk.Canvas(
            circle, width=24, height=24, bg=pal["surface_soft"],
            highlightthickness=0, bd=0, takefocus=0,
        )
        canvas.pack(expand=True)
        icons.paint(canvas, icon, pal["text_faint"], size=24)
        tk.Label(
            box,
            text=title,
            bg=background,
            fg=pal["text"],
            font=fonts.get(11, "bold"),
        ).pack(pady=(12, 0))
        if message:
            tk.Label(
                box,
                text=message,
                bg=background,
                fg=pal["text_muted"],
                font=fonts.get(9),
                wraplength=340,
                justify="center",
            ).pack(pady=(4, 0))
        if action is not None:
            action.pack(pady=(14, 0))


class Badge(tk.Label):
    """Label status kecil (mis. "Aktif", "JSON")."""

    def __init__(
        self,
        parent: tk.Misc,
        text: str,
        pal: Dict[str, str],
        fonts: FontBook,
        tone: str = "primary",
    ) -> None:
        self.pal = pal
        super().__init__(
            parent,
            text=text,
            bg=pal.get(tone + "_soft") or pal["surface_soft"],
            fg=pal.get(tone, pal["primary"]),
            font=fonts.get(8, "bold"),
            padx=8,
            pady=2,
            bd=0,
        )


class CheckboxRow(tk.Frame):
    """Baris centang sederhana (dipakai di halaman Pengaturan)."""

    def __init__(
        self,
        parent: tk.Misc,
        pal: Dict[str, str],
        fonts: FontBook,
        label: str,
        description: str,
        value: bool,
        command: Optional[Callable[[bool], None]] = None,
    ) -> None:
        super().__init__(parent, bg=pal["surface"])
        self.pal = pal
        self.fonts = fonts
        self.value = bool(value)
        self.command = command

        self.box = tk.Canvas(
            self,
            width=20,
            height=20,
            bg=pal["surface"],
            highlightthickness=0,
            bd=0,
            takefocus=0,
            cursor="hand2",
        )
        self.box.pack(side="left", anchor="n", pady=(1, 0))
        self.box.bind("<Button-1>", lambda _event: self.toggle())

        text_box = tk.Frame(self, bg=pal["surface"])
        text_box.pack(side="left", fill="x", expand=True, padx=(10, 0))
        self.title = tk.Label(
            text_box,
            text=label,
            bg=pal["surface"],
            fg=pal["text"],
            font=fonts.get(10),
            anchor="w",
        )
        self.title.pack(fill="x")
        self.title.bind("<Button-1>", lambda _event: self.toggle())
        if description:
            desc = tk.Label(
                text_box,
                text=description,
                bg=pal["surface"],
                fg=pal["text_muted"],
                font=fonts.get(9),
                anchor="w",
                justify="left",
                wraplength=430,
            )
            desc.pack(fill="x", pady=(1, 0))
            desc.bind("<Button-1>", lambda _event: self.toggle())
        self._render()

    def _render(self) -> None:
        self.box.delete("all")
        pal = self.pal
        if self.value:
            self.box.create_oval(0, 0, 20, 20, fill=pal["primary"], outline=pal["primary"])
            self.box.create_line(
                5, 10.2, 8.4, 13.8, 15, 6.6,
                fill=pal["primary_text"], width=2, capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )
        else:
            self.box.create_oval(1, 1, 19, 19, outline=pal["border_strong"], width=1.6)

    def toggle(self) -> None:
        self.value = not self.value
        self._render()
        if self.command is not None:
            self.command(self.value)
