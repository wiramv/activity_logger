"""Palet warna, font, dan integrasi tema Bootstrap (ttkbootstrap).

Seluruh warna aplikasi berasal dari ``PALETTES`` di modul ini sehingga mode
terang/gelap konsisten antara widget ``tk`` (chrome buatan sendiri) dan widget
``ttk`` yang diwarnai lewat ``ttk.Style``.

Bila ``ttkbootstrap`` terpasang, aplikasi mendaftarkan tema kustom
(``activity-light`` / ``activitynight-dark``) yang memakai palet di bawah, lalu
memilih tema tersebut. Bila tidak terpasang, aplikasi tetap berjalan memakai
``ttk.Style`` biasa dengan gaya yang sama persis.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Dict, Optional, Tuple

# --------------------------------------------------------------------------- #
# Palet
# --------------------------------------------------------------------------- #
LIGHT: Dict[str, str] = {
    "name": "light",
    "page": "#eef2f7",
    "surface": "#ffffff",
    "surface_soft": "#f7f9fc",
    "surface_hover": "#f1f5f9",
    "border": "#e3e8ef",
    "border_strong": "#cbd5e1",
    "text": "#0f172a",
    "text_muted": "#5b6b82",
    "text_faint": "#8b9bb0",
    "primary": "#0f9d6b",
    "primary_hover": "#0b8459",
    "primary_soft": "#e6f7f0",
    "primary_text": "#ffffff",
    "danger": "#e11d48",
    "danger_hover": "#be123c",
    "danger_soft": "#fef2f4",
    "warning": "#f59e0b",
    "warning_soft": "#fef6e7",
    "info": "#0c7bb3",
    "info_soft": "#eaf5fb",
    "sidebar": "#0f1c2e",
    "sidebar_soft": "#16263c",
    "sidebar_text": "#93a7c4",
    "sidebar_text_active": "#ffffff",
    "sidebar_muted": "#6b7f9c",
    "chart": "#0f9d6b",
    "chart_soft": "#cdeee0",
    "chart_grid": "#e8edf4",
    "overlay": "#0f172a",
}

DARK: Dict[str, str] = {
    "name": "dark",
    "page": "#0a1220",
    "surface": "#101c2e",
    "surface_soft": "#16233a",
    "surface_hover": "#1a2942",
    "border": "#1f3050",
    "border_strong": "#2b3f63",
    "text": "#e7eef9",
    "text_muted": "#9aabc4",
    "text_faint": "#6f83a1",
    "primary": "#10b981",
    "primary_hover": "#34d399",
    "primary_soft": "#0d2f27",
    "primary_text": "#04170f",
    "danger": "#f43f5e",
    "danger_hover": "#fb7185",
    "danger_soft": "#2a1220",
    "warning": "#fbbf24",
    "warning_soft": "#2a2110",
    "info": "#38bdf8",
    "info_soft": "#0d2436",
    "sidebar": "#070f1b",
    "sidebar_soft": "#101d2f",
    "sidebar_text": "#8fa4c0",
    "sidebar_text_active": "#ffffff",
    "sidebar_muted": "#5d7291",
    "chart": "#10b981",
    "chart_soft": "#1c4a3c",
    "chart_grid": "#1a2a44",
    "overlay": "#020712",
}

PALETTES = {"light": LIGHT, "dark": DARK}

FONT_CANDIDATES = (
    "Segoe UI Variable Text",
    "Segoe UI",
    "Inter",
    "SF Pro Text",
    "Helvetica Neue",
    "Ubuntu",
    "Noto Sans",
    "Cantarell",
    "DejaVu Sans",
    "Verdana",
    "Arial",
)

MONO_CANDIDATES = (
    "Cascadia Mono",
    "Consolas",
    "SF Mono",
    "Menlo",
    "JetBrains Mono",
    "Ubuntu Mono",
    "DejaVu Sans Mono",
    "Courier New",
)


class FontBook:
    """Kumpulan font siap pakai (tuple Tk) dengan satu keluarga konsisten."""

    def __init__(self, root: Optional[tk.Misc] = None) -> None:
        self.root = root
        self.family = _pick_family(root, FONT_CANDIDATES, "TkDefaultFont")
        self.mono_family = _pick_family(root, MONO_CANDIDATES, "TkFixedFont")
        self._cache: Dict[tuple, object] = {}

    # -- pembuat -------------------------------------------------------- #
    def get(self, size: int = 10, weight: str = "normal", slant: str = "roman") -> Tuple:
        if slant == "roman":
            return (self.family, size, weight)
        return (self.family, size, weight, slant)

    def mono(self, size: int = 9, weight: str = "normal") -> Tuple:
        return (self.mono_family, size, weight)

    def font_string(self, size: int = 10, weight: str = "normal") -> str:
        """Font sebagai string Tcl (untuk ``option_add``)."""
        return "{{{}}} {} {}".format(self.family, size, weight)

    def struck(self, size: int = 10):
        """Font dengan garis coret (untuk kegiatan yang sudah selesai).

        ``tk.Label`` tidak punya opsi ``-overstrike``, jadi kita pakai objek
        ``tkinter.font.Font`` yang di-cache agar tidak membuat font baru di
        setiap baris.
        """
        key = ("struck", size)
        if key not in self._cache:
            try:
                self._cache[key] = tkfont.Font(
                    root=self.root, family=self.family, size=size, overstrike=1
                )
            except Exception:  # pragma: no cover - lingkungan Tk minim
                self._cache[key] = self.get(size)
        return self._cache[key]

    # -- peran tipografi ----------------------------------------------- #
    @property
    def display(self) -> Tuple:
        return self.get(21, "bold")

    @property
    def h1(self) -> Tuple:
        return self.get(16, "bold")

    @property
    def h2(self) -> Tuple:
        return self.get(13, "bold")

    @property
    def h3(self) -> Tuple:
        return self.get(11, "bold")

    @property
    def body(self) -> Tuple:
        return self.get(10)

    @property
    def body_bold(self) -> Tuple:
        return self.get(10, "bold")

    @property
    def body_medium(self) -> Tuple:
        return self.get(10)

    @property
    def small(self) -> Tuple:
        return self.get(9)

    @property
    def small_bold(self) -> Tuple:
        return self.get(9, "bold")

    @property
    def tiny(self) -> Tuple:
        return self.get(8)

    @property
    def tiny_bold(self) -> Tuple:
        return self.get(8, "bold")

    @property
    def numeral(self) -> Tuple:
        return self.get(22, "bold")

    @property
    def numeral_small(self) -> Tuple:
        return self.get(15, "bold")


def _pick_family(root: Optional[tk.Misc], candidates, fallback: str) -> str:
    try:
        available = set(tkfont.families(root)) if root is not None else set(tkfont.families())
    except Exception:  # pragma: no cover - lingkungan Tk tidak standar
        available = set()
    for name in candidates:
        if name in available:
            return name
    # Cari kemiripan (mis. "Segoe UI Historic" tetap cocok dengan "Segoe UI").
    lowered = {name.lower(): name for name in available}
    for name in candidates:
        for key, real in lowered.items():
            if key.startswith(name.lower()):
                return real
    return fallback


# --------------------------------------------------------------------------- #
# Integrasi ttk / ttkbootstrap
# --------------------------------------------------------------------------- #
class ThemeManager:
    """Membuat ``ttk.Style``, memilih tema, dan mewarnai widget ttk."""

    def __init__(self, root: tk.Misc, mode: str = "light") -> None:
        self.root = root
        self.mode = mode if mode in PALETTES else "light"
        self.fonts = FontBook(root)
        self.engine = None            # modul ttkbootstrap bila tersedia
        self.custom_themes: Dict[str, str] = {}
        self.style = self._create_style()
        self.apply()

    # -- publik --------------------------------------------------------- #
    @property
    def pal(self) -> Dict[str, str]:
        return PALETTES[self.mode]

    def switch(self, mode: str) -> None:
        if mode in PALETTES and mode != self.mode:
            self.mode = mode
            self.apply()

    def apply(self) -> None:
        """Pilih tema (bila engine tersedia) lalu pasang gaya widget kustom."""
        pal = self.pal
        if self.engine is not None:
            for candidate in self._theme_candidates():
                try:
                    self.style.theme_use(candidate)
                    break
                except Exception:
                    continue
        configure_widget_styles(self.style, pal, self.fonts, self.root)
        _configure_tk_defaults(self.root, pal, self.fonts)

    def _theme_candidates(self):
        """Urutan tema yang dicoba: tema kustom palet kita, lalu bawaan."""
        custom = self.custom_themes.get(self.mode)
        if self.mode == "dark":
            legacy = ("darkly", "bootstrap-dark", "superhero")
        else:
            legacy = ("flatly", "bootstrap-light", "cosmo")
        ordered = []
        if custom:
            ordered.append(custom)
        ordered.extend(legacy)
        return ordered

    # -- internal ------------------------------------------------------- #
    def _create_style(self):
        """Buat ``ttk.Style`` (ttkbootstrap bila ada, jika tidak ttk biasa)."""
        try:
            import ttkbootstrap as ttkbootstrap_pkg
        except Exception:
            return ttk.Style(self.root)

        self.engine = ttkbootstrap_pkg
        try:
            style = ttkbootstrap_pkg.Style()
        except Exception:  # pragma: no cover - versi ttkbootstrap tak terduga
            try:
                style = ttk.Style(self.root)
            except tk.TclError:
                style = None
            self.engine = None
            return style
        self.custom_themes = _register_custom_themes(ttkbootstrap_pkg)
        return style


def _register_custom_themes(engine) -> Dict[str, str]:
    """Daftarkan tema kustom (khusus ttkbootstrap 2.x).

    Tema lama (1.x) memakai API berbeda dan tidak stabil di semua versi, jadi
    untuk versi tersebut aplikasi memakai tema bawaan ``flatly``/``darkly``
    yang skemanya tetap ditimpa oleh ``configure_widget_styles``.
    """
    try:
        major = int(str(getattr(engine, "__version__", "0")).split(".")[0])
    except (TypeError, ValueError):
        return {}
    if major < 2 or not hasattr(engine, "Theme"):
        return {}

    names: Dict[str, str] = {}
    try:
        light = PALETTES["light"]
        engine.Theme(
            name="activity",
            primary=light["primary"],
            success=light["primary"],
            info=light["info"],
            warning=light["warning"],
            danger=light["danger"],
            neutral=light["text_muted"],
            light={"background": light["page"], "foreground": light["text"]},
        ).register()
        names["light"] = "activity-light"
    except Exception:
        pass
    try:
        dark = PALETTES["dark"]
        engine.Theme(
            name="activitynight",
            primary=dark["primary"],
            success=dark["primary"],
            info=dark["info"],
            warning=dark["warning"],
            danger=dark["danger"],
            neutral=dark["text_muted"],
            dark={"background": dark["page"], "foreground": dark["text"]},
        ).register()
        names["dark"] = "activitynight-dark"
    except Exception:
        pass
    return names


def _safe_style(style, func: str, name: str, **options) -> None:
    """``style.configure``/``map`` yang tidak boleh mematikan aplikasi."""
    try:
        getattr(style, func)(name, **options)
    except tk.TclError:  # pragma: no cover - tema/platform tertentu
        pass


def configure_widget_styles(style, pal: Dict[str, str], fonts: FontBook, root=None) -> None:
    """Warnai widget ttk (Entry, Combobox, Scrollbar, dsb.) sesuai palet."""
    if style is None:  # pragma: no cover - engine gaya tidak tersedia
        return
    # -- Entry ---------------------------------------------------------- #
    _safe_style(
        style,
        "configure",
        "App.TEntry",
        fieldbackground=pal["surface_soft"],
        foreground=pal["text"],
        bordercolor=pal["border"],
        lightcolor=pal["border"],
        darkcolor=pal["border"],
        insertcolor=pal["primary"],
        background=pal["surface_soft"],
        padding=(10, 9),
        relief="flat",
    )
    _safe_style(
        style,
        "map",
        "App.TEntry",
        bordercolor=[("focus", pal["primary"]), ("disabled", pal["border"])],
        lightcolor=[("focus", pal["primary"])],
        darkcolor=[("focus", pal["primary"])],
        fieldbackground=[
            ("disabled", pal["surface"]),
            ("readonly", pal["surface_soft"]),
        ],
        foreground=[("disabled", pal["text_faint"])],
    )

    # -- Combobox ------------------------------------------------------- #
    _safe_style(
        style,
        "configure",
        "App.TCombobox",
        fieldbackground=pal["surface_soft"],
        background=pal["surface_soft"],
        foreground=pal["text"],
        bordercolor=pal["border"],
        lightcolor=pal["border"],
        darkcolor=pal["border"],
        arrowcolor=pal["text_muted"],
        selectbackground=pal["primary_soft"],
        selectforeground=pal["text"],
        padding=(10, 8),
        relief="flat",
    )
    _safe_style(
        style,
        "map",
        "App.TCombobox",
        bordercolor=[("focus", pal["primary"])],
        lightcolor=[("focus", pal["primary"])],
        darkcolor=[("focus", pal["primary"])],
        fieldbackground=[("readonly", pal["surface_soft"]), ("disabled", pal["surface"])],
        foreground=[("readonly", pal["text"])],
        arrowcolor=[("active", pal["primary"])],
    )

    # -- Scrollbar ------------------------------------------------------ #
    for name in ("App.Vertical.TScrollbar", "App.Horizontal.TScrollbar"):
        _safe_style(
            style,
            "configure",
            name,
            troughcolor=pal["page"],
            background=pal["border_strong"],
            bordercolor=pal["page"],
            darkcolor=pal["border_strong"],
            lightcolor=pal["border_strong"],
            arrowcolor=pal["text_muted"],
            arrowsize=12,
            gripcount=0,
            relief="flat",
        )
        _safe_style(
            style,
            "map",
            name,
            background=[("active", pal["primary"]), ("pressed", pal["primary_hover"])],
        )

    # -- Checkbutton (dipakai pada dialog preferensi) ------------------- #
    _safe_style(
        style,
        "configure",
        "App.TCheckbutton",
        background=pal["surface"],
        foreground=pal["text"],
        focuscolor=pal["surface"],
        font=fonts.body,
    )
    _safe_style(
        style,
        "map",
        "App.TCheckbutton",
        background=[("active", pal["surface"])],
        foreground=[("disabled", pal["text_faint"])],
        indicatorcolor=[("selected", pal["primary"]), ("!selected", pal["surface_soft"])],
    )

    # -- Popdown Combobox (listbox milik Tk klasik) --------------------- #
    if root is not None:
        try:
            root.option_add("*TCombobox*Listbox.background", pal["surface"])
            root.option_add("*TCombobox*Listbox.foreground", pal["text"])
            root.option_add("*TCombobox*Listbox.selectBackground", pal["primary"])
            root.option_add("*TCombobox*Listbox.selectForeground", pal["primary_text"])
            root.option_add("*TCombobox*Listbox.font", fonts.font_string(10))
        except tk.TclError:  # pragma: no cover
            pass


def _configure_tk_defaults(root, pal: Dict[str, str], fonts: FontBook) -> None:
    """Warna default untuk widget Tk klasik (mis. menu konteks)."""
    try:
        root.configure(background=pal["page"])
    except tk.TclError:  # pragma: no cover
        pass
    for option, value in (
        ("*Menu.background", pal["surface"]),
        ("*Menu.foreground", pal["text"]),
        ("*Menu.activeBackground", pal["primary_soft"]),
        ("*Menu.activeForeground", pal["text"]),
        ("*Menu.borderWidth", 0),
        ("*Menu.font", fonts.font_string(10)),
        ("*Toplevel.background", pal["page"]),
    ):
        try:
            root.option_add(option, value)
        except tk.TclError:  # pragma: no cover
            pass


def mix(color_a: str, color_b: str, ratio: float) -> str:
    """Campur dua warna hex (``ratio`` = porsi ``color_a``)."""
    try:
        a = [int(color_a[i : i + 2], 16) for i in (1, 3, 5)]
        b = [int(color_b[i : i + 2], 16) for i in (1, 3, 5)]
    except (ValueError, IndexError):
        return color_a
    ratio = max(0.0, min(1.0, ratio))
    mixed = [round(x * ratio + y * (1 - ratio)) for x, y in zip(a, b)]
    return "#{:02x}{:02x}{:02x}".format(*mixed)


def lighten(color: str, amount: float = 0.12) -> str:
    return mix("#ffffff", color, amount)


def darken(color: str, amount: float = 0.12) -> str:
    return mix("#000000", color, amount)
