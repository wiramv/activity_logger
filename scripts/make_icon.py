"""Buat ulang ``assets/app_icon.png`` (64x64) tanpa dependensi eksternal.

Jalankan::

    python scripts/make_icon.py

Hasilnya bisa ditempel ke ``activity_logger/gui/appicon.py`` (lihat docstring
modul tersebut) bila ingin mengubah ikon aplikasi.
"""

from __future__ import annotations

import base64
import math
import os
import struct
import zlib

SIZE = 64
PAD = 7
SPAN = SIZE - 2 * PAD
SCALE = SPAN / 24.0
STROKE = 1.9 * SCALE / 2
BG = (15, 157, 107)
FG = (255, 255, 255)
SS = 4
RADIUS = 14.0

ICON = [
    ("r", 3.4, 5.4, 20.6, 20.6),
    ("l", 3.4, 10.4, 20.6, 10.4),
    ("l", 8.2, 2.8, 8.2, 7.0),
    ("l", 15.8, 2.8, 15.8, 7.0),
    ("of", 6.8, 13.2, 8.8, 15.2),
    ("of", 10.9, 13.2, 12.9, 15.2),
    ("of", 15.0, 13.2, 17.0, 15.2),
    ("of", 6.8, 16.6, 8.8, 18.6),
    ("of", 10.9, 16.6, 12.9, 18.6),
]


def seg_dist(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def ink(px, py):
    for op in ICON:
        kind = op[0]
        if kind == "l":
            a = (op[1] * SCALE + PAD, op[2] * SCALE + PAD)
            b = (op[3] * SCALE + PAD, op[4] * SCALE + PAD)
            if seg_dist(px, py, a[0], a[1], b[0], b[1]) <= STROKE:
                return True
        elif kind == "r":
            x1, y1, x2, y2 = (op[i] * SCALE + PAD for i in (1, 2, 3, 4))
            for a, b in (
                ((x1, y1), (x2, y1)),
                ((x2, y1), (x2, y2)),
                ((x2, y2), (x1, y2)),
                ((x1, y2), (x1, y1)),
            ):
                if seg_dist(px, py, a[0], a[1], b[0], b[1]) <= STROKE:
                    return True
        elif kind == "of":
            cx = (op[1] + op[3]) / 2 * SCALE + PAD
            cy = (op[2] + op[4]) / 2 * SCALE + PAD
            r = (op[3] - op[1]) / 2 * SCALE
            if math.hypot(px - cx, py - cy) <= r:
                return True
    return False


def build_png():
    width = height = SIZE * SS
    coverage = [[0] * width for _ in range(height)]
    for yy in range(height):
        for xx in range(width):
            if ink((xx + 0.5) / SS, (yy + 0.5) / SS):
                coverage[yy][xx] = 1

    rows = []
    for y in range(SIZE):
        row = bytearray()
        for x in range(SIZE):
            hits = 0
            for sy in range(SS):
                for sx in range(SS):
                    hits += coverage[y * SS + sy][x * SS + sx]
            shade = hits / (SS * SS)
            cx = min(max(x + 0.5, RADIUS), SIZE - RADIUS)
            cy = min(max(y + 0.5, RADIUS), SIZE - RADIUS)
            dist = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            alpha = 255 if dist <= RADIUS - 0.5 else max(0, int(255 * (RADIUS + 0.5 - dist)))
            row += bytes(
                (
                    int(BG[0] * (1 - shade) + FG[0] * shade),
                    int(BG[1] * (1 - shade) + FG[1] * shade),
                    int(BG[2] * (1 - shade) + FG[2] * shade),
                    alpha,
                )
            )
        rows.append(bytes(row))

    raw = b"".join(b"\x00" + row for row in rows)

    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target = os.path.join(root, "assets", "app_icon.png")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    data = build_png()
    with open(target, "wb") as handle:
        handle.write(data)
    print("Ikon ditulis ke {} ({} bytes)".format(target, len(data)))
    print("Base64 untuk appicon.py:")
    print(base64.b64encode(data).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
