"""Ikon vektor yang digambar sendiri di ``tk.Canvas``.

Kenapa tidak memakai emoji/font ikon? Karena ketersediaan glyph berbeda-beda
di Windows/macOS/Linux. Semua ikon di bawah digambar dari koordinat 24×24
sehingga tampil identik di mana saja dan warnanya bisa diubah kapan pun
(mis. saat hover atau ganti tema).
"""

from __future__ import annotations

import math
import tkinter as tk
from typing import Dict, List, Sequence

BASE = 24.0


def _gear() -> List[tuple]:
    """Roda gigi: cincin + 8 gigi trapesium + lubang tengah."""
    ops: List[tuple] = [("o", 5.4, 5.4, 18.6, 18.6)]
    teeth = 8
    for index in range(teeth):
        angle = math.radians(index * 360.0 / teeth)
        half_inner = math.radians(10.0)
        half_outer = math.radians(17.0)
        points: List[float] = []
        for sign, half, radius in (
            (-1, half_inner, 6.1),
            (1, half_inner, 6.1),
            (1, half_outer, 9.4),
            (-1, half_outer, 9.4),
        ):
            current = angle + sign * half
            points += [12 + radius * math.cos(current), 12 - radius * math.sin(current)]
        ops.append(("pg", points))
    ops.append(("o", 9.3, 9.3, 14.7, 14.7))
    return ops


def _sun() -> List[tuple]:
    ops: List[tuple] = [("o", 7.2, 7.2, 16.8, 16.8)]
    for index in range(8):
        angle = math.radians(index * 45)
        ops.append(
            (
                "l",
                12 + 9.6 * math.cos(angle),
                12 + 9.6 * math.sin(angle),
                12 + 11.6 * math.cos(angle),
                12 + 11.6 * math.sin(angle),
            )
        )
    return ops


def _moon() -> List[tuple]:
    points: List[float] = []
    for step in range(0, 28):
        angle = math.radians(55 + step * (250 / 27))
        points += [12 + 8.6 * math.cos(angle), 12 - 8.6 * math.sin(angle)]
    for step in range(0, 29):
        angle = math.radians(305 - step * (250 / 28))
        points += [14.6 + 6.9 * math.cos(angle), 12 - 6.9 * math.sin(angle)]
    return [("pg", points)]


def _wifi() -> List[tuple]:
    return [
        ("a", 2.8, 2.0, 21.2, 20.4, 42, 96),
        ("a", 7.0, 6.2, 17.0, 16.6, 42, 96),
        ("a", 10.4, 9.6, 13.6, 12.8, 42, 96),
        ("of", 10.5, 16.1, 13.5, 19.1),
    ]


def _refresh() -> List[tuple]:
    return [
        ("a", 3.6, 3.6, 20.4, 20.4, 55, 275),
        ("pl", [15.4, 2.2, 20.6, 4.6, 17.6, 9.4]),
    ]


#: Definisi tiap ikon dalam ruang koordinat 24×24.
ICONS: Dict[str, Sequence[tuple]] = {
    "home": [
        ("pl", [2.6, 11.2, 12, 3.4, 21.4, 11.2]),
        ("pl", [5.2, 10.6, 5.2, 20.6, 18.8, 20.6, 18.8, 10.6]),
        ("r", 9.8, 14.2, 14.2, 20.6),
    ],
    "folder": [
        ("pl", [2.8, 19.2, 2.8, 5.6, 9.0, 5.6, 11.2, 8.4, 21.2, 8.4, 21.2, 19.2, 2.8, 19.2]),
    ],
    "list": [
        ("of", 3.2, 5.4, 5.6, 7.8),
        ("of", 3.2, 10.8, 5.6, 13.2),
        ("of", 3.2, 16.2, 5.6, 18.6),
        ("l", 8.6, 6.6, 20.4, 6.6),
        ("l", 8.6, 12.0, 20.4, 12.0),
        ("l", 8.6, 17.4, 20.4, 17.4),
    ],
    "chart": [
        ("rf", 3.6, 13.4, 8.0, 20.4),
        ("rf", 9.8, 8.6, 14.2, 20.4),
        ("rf", 16.0, 3.6, 20.4, 20.4),
    ],
    "grid": [
        ("rf", 3.6, 3.6, 10.8, 10.8),
        ("rf", 13.2, 3.6, 20.4, 10.8),
        ("rf", 3.6, 13.2, 10.8, 20.4),
        ("rf", 13.2, 13.2, 20.4, 20.4),
    ],
    "download": [
        ("l", 12, 3.2, 12, 14.8),
        ("pl", [7.4, 10.4, 12, 15.0, 16.6, 10.4]),
        ("pl", [3.8, 16.8, 3.8, 20.6, 20.2, 20.6, 20.2, 16.8]),
    ],
    "upload": [
        ("l", 12, 20.4, 12, 8.6),
        ("pl", [7.4, 13.2, 12, 8.6, 16.6, 13.2]),
        ("pl", [3.8, 3.8, 20.2, 3.8]),
    ],
    "trash": [
        ("l", 3.4, 6.4, 20.6, 6.4),
        ("pl", [8.8, 6.4, 8.8, 3.4, 15.2, 3.4, 15.2, 6.4]),
        ("pl", [5.4, 6.4, 6.7, 20.6, 17.3, 20.6, 18.6, 6.4]),
        ("l", 10.0, 10.2, 10.4, 17.0),
        ("l", 14.0, 10.2, 13.6, 17.0),
    ],
    "gear": _gear(),
    "sun": _sun(),
    "moon": _moon(),
    "menu": [
        ("l", 4.0, 6.6, 20.0, 6.6),
        ("l", 4.0, 12.0, 20.0, 12.0),
        ("l", 4.0, 17.4, 20.0, 17.4),
    ],
    "plus": [
        ("l", 12, 5.0, 12, 19.0),
        ("l", 5.0, 12, 19.0, 12),
    ],
    "check": [("pl", [4.6, 12.6, 9.4, 17.4, 19.4, 6.8])],
    "check_circle": [
        ("o", 3.2, 3.2, 20.8, 20.8),
        ("pl", [7.8, 12.2, 10.8, 15.2, 16.4, 9.0]),
    ],
    "x": [
        ("l", 6.4, 6.4, 17.6, 17.6),
        ("l", 17.6, 6.4, 6.4, 17.6),
    ],
    "search": [
        ("o", 3.8, 3.8, 15.4, 15.4),
        ("l", 13.4, 13.4, 20.2, 20.2),
    ],
    "chevron_right": [("pl", [9.2, 4.8, 16.4, 12.0, 9.2, 19.2])],
    "chevron_left": [("pl", [14.8, 4.8, 7.6, 12.0, 14.8, 19.2])],
    "chevron_down": [("pl", [4.8, 9.2, 12.0, 16.4, 19.2, 9.2])],
    "arrow_right": [
        ("l", 4.0, 12, 19.4, 12),
        ("pl", [13.6, 6.4, 19.6, 12, 13.6, 17.6]),
    ],
    "arrow_up": [
        ("l", 12, 20.0, 12, 4.6),
        ("pl", [6.4, 10.2, 12, 4.2, 17.6, 10.2]),
    ],
    "calendar": [
        ("r", 3.4, 5.4, 20.6, 20.6),
        ("l", 3.4, 10.4, 20.6, 10.4),
        ("l", 8.2, 2.8, 8.2, 7.0),
        ("l", 15.8, 2.8, 15.8, 7.0),
        ("of", 6.8, 13.2, 8.8, 15.2),
        ("of", 10.9, 13.2, 12.9, 15.2),
        ("of", 15.0, 13.2, 17.0, 15.2),
        ("of", 6.8, 16.6, 8.8, 18.6),
        ("of", 10.9, 16.6, 12.9, 18.6),
    ],
    "clock": [
        ("o", 3.4, 3.4, 20.6, 20.6),
        ("pl", [12, 6.8, 12, 12.2, 15.6, 14.2]),
    ],
    "phone": [
        ("r", 6.8, 2.8, 17.2, 21.2),
        ("l", 10.4, 18.6, 13.6, 18.6),
        ("l", 10.2, 5.4, 13.8, 5.4),
    ],
    "copy": [
        ("r", 8.4, 8.4, 20.4, 20.4),
        ("pl", [15.6, 8.4, 15.6, 3.6, 3.6, 3.6, 3.6, 15.6, 8.4, 15.6]),
    ],
    "file": [
        ("pl", [6.0, 2.8, 14.4, 2.8, 19.0, 7.4, 19.0, 21.2, 6.0, 21.2, 6.0, 2.8]),
        ("pl", [14.4, 2.8, 14.4, 7.4, 19.0, 7.4]),
    ],
    "edit": [
        ("pl", [3.6, 20.4, 4.8, 15.6, 15.4, 5.0, 19.0, 8.6, 8.4, 19.2, 3.6, 20.4]),
        ("l", 13.2, 7.2, 16.8, 10.8),
    ],
    "refresh": _refresh(),
    "dot": [("of", 9.6, 9.6, 14.4, 14.4)],
    "filter": [
        ("l", 3.4, 6.4, 20.6, 6.4),
        ("l", 6.4, 12.0, 17.6, 12.0),
        ("l", 9.4, 17.6, 14.6, 17.6),
    ],
    "info": [
        ("o", 3.4, 3.4, 20.6, 20.6),
        ("l", 12, 10.8, 12, 16.8),
        ("of", 11.1, 7.2, 12.9, 9.0),
    ],
    "alert": [
        ("pg", [12, 3.0, 22.2, 20.6, 1.8, 20.6]),
        ("l", 12, 9.4, 12, 14.8),
        ("of", 11.1, 16.9, 12.9, 18.7),
    ],
    "wifi": _wifi(),
    "save": [
        ("pl", [3.8, 3.8, 15.6, 3.8, 20.2, 8.4, 20.2, 20.2, 3.8, 20.2, 3.8, 3.8]),
        ("r", 8.0, 3.8, 15.6, 9.6),
        ("r", 7.6, 13.8, 16.4, 20.2),
    ],
    "external": [
        ("pl", [14.2, 3.8, 20.2, 3.8, 20.2, 9.8]),
        ("l", 20.2, 3.8, 11.4, 12.6),
        ("pl", [17.0, 13.8, 17.0, 20.2, 3.8, 20.2, 3.8, 6.8, 10.2, 6.8]),
    ],
    "more": [
        ("of", 3.6, 10.4, 7.2, 14.0),
        ("of", 10.2, 10.4, 13.8, 14.0),
        ("of", 16.8, 10.4, 20.4, 14.0),
    ],
}

ICON_NAMES = frozenset(ICONS)


def paint(
    canvas: tk.Canvas,
    name: str,
    color: str,
    size: int = 18,
    tag: str = "icon",
    width: float = 0.0,
    ox: int = 0,
    oy: int = 0,
) -> None:
    """Gambar ikon ``name`` di tengah ``canvas`` (menghapus gambar lama)."""
    canvas.delete(tag)
    ops = ICONS.get(name)
    if not ops:
        return
    try:
        box_w = int(float(canvas.cget("width")))
        box_h = int(float(canvas.cget("height")))
    except (tk.TclError, ValueError):  # pragma: no cover
        box_w = box_h = size

    scale = float(size) / BASE
    origin_x = (box_w - size) / 2.0 + ox
    origin_y = (box_h - size) / 2.0 + oy
    stroke = width if width > 0 else max(1.4, size * 0.085)

    def sx(value: float) -> float:
        return origin_x + value * scale

    def sy(value: float) -> float:
        return origin_y + value * scale

    for op in ops:
        kind = op[0]
        if kind == "l":
            canvas.create_line(
                sx(op[1]), sy(op[2]), sx(op[3]), sy(op[4]),
                fill=color, width=stroke, capstyle=tk.ROUND, tag=tag,
            )
        elif kind == "pl":
            points = op[1]
            coords: List[float] = []
            for index in range(0, len(points), 2):
                coords += [sx(points[index]), sy(points[index + 1])]
            canvas.create_line(
                *coords, fill=color, width=stroke, capstyle=tk.ROUND,
                joinstyle=tk.ROUND, smooth=False, tag=tag,
            )
        elif kind == "pg":
            points = op[1]
            coords = []
            for index in range(0, len(points), 2):
                coords += [sx(points[index]), sy(points[index + 1])]
            canvas.create_polygon(
                *coords, fill=color, outline=color, width=stroke,
                joinstyle=tk.ROUND, tag=tag,
            )
        elif kind == "r":
            canvas.create_rectangle(
                sx(op[1]), sy(op[2]), sx(op[3]), sy(op[4]),
                outline=color, width=stroke, tag=tag,
            )
        elif kind == "rf":
            canvas.create_rectangle(
                sx(op[1]), sy(op[2]), sx(op[3]), sy(op[4]),
                fill=color, outline=color, width=0, tag=tag,
            )
        elif kind == "o":
            canvas.create_oval(
                sx(op[1]), sy(op[2]), sx(op[3]), sy(op[4]),
                outline=color, width=stroke, tag=tag,
            )
        elif kind == "of":
            canvas.create_oval(
                sx(op[1]), sy(op[2]), sx(op[3]), sy(op[4]),
                fill=color, outline=color, width=0, tag=tag,
            )
        elif kind == "a":
            canvas.create_arc(
                sx(op[1]), sy(op[2]), sx(op[3]), sy(op[4]),
                start=op[5], extent=op[6], style=tk.ARC,
                outline=color, width=stroke, tag=tag,
            )


def icon_widget(
    parent: tk.Misc,
    name: str,
    color: str,
    size: int = 18,
    background: str = "#ffffff",
    pad: int = 0,
) -> tk.Canvas:
    """Buat ``Canvas`` berisi satu ikon (tanpa interaksi)."""
    canvas = tk.Canvas(
        parent,
        width=size + pad * 2,
        height=size + pad * 2,
        bg=background,
        highlightthickness=0,
        bd=0,
        takefocus=0,
    )
    paint(canvas, name, color, size=size)
    return canvas
