"""Ikon jendela aplikasi (PNG 64x64, disematkan sebagai base64).

Disematkan agar ikon tetap ada setelah aplikasi dibundel (PyInstaller) atau
dipasang lewat pip, tanpa bergantung pada path file.

Ikon aslinya ada di ``assets/app_icon.png`` dan bisa dibuat ulang dengan::

    python scripts/make_icon.py
"""

from __future__ import annotations

from typing import Optional

ICON_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAACcUlEQVR42u2bv0vEMBTH+x/4"
    "H/gfuNzs2M29g3/BiauDi6tOBSfBwUVxEAcXbzoQxMJtIiIUblIE4eAGEQSHg9jv0UCM/ZG0"
    "TS9p34PvcG3fu+TTNi9JE2/tbNdTkJ8oTBQlmiVaJGKWaZGWLUrL6qvUreyCYaLYwsqqKk7r"
    "oA1gkJJkHVGU1kkJQGDpI97EKxKUAQg6WHFZQR6AQUfvfNaTMMgCEPWg8mKb8AfAsEeV5xqK"
    "AOIeAog5AL+HlefyvbTXZOQP1i/2llqVv4JCY43fzv0543b0ONL2hw83xDLVGHpp/7nx4G9f"
    "cyaarr9oiGUIwMwzlftla9tftU/gmXq/HAHACECVlvlyOmEPH9NCyVZ2fV1/lKlKxtAGcPv6"
    "xGw1lM04ANuNALQNYGt0nCnV6+r6rxxA3nWfP9+NZQHEMpUtjAFAq8ztef6uXTD4cEMs5wAg"
    "Je1Prpd9+irpCT7wRYwif2sBtCUCYGsWaEvUDyAABGC1AHRHeU2LsgABIAB2AsBUNrqyG1cH"
    "medxHOeLpry3x6eFMawFIM7pYyQn9+XxWxwtnrzc/YuBMYAYIw+ClQDk1hk9NvG83IPD9WUx"
    "AMQZAOJQGCbfPfwWn4Cs4a74FME2bw7dAcCHspiklO8+FyqEihcNl3HXEQNtAWUBAuAYADz6"
    "RbM5OI4UmPeKOA1AJQ2Kc35VPp93Pg06DUAlDdb9pGV9GuQfUPNSGI7X+ahJWYAAWAKA5gQ7"
    "AEBrkZSYv22zCt8gF9rL5DCIsRECypQ3YixbJtenVeKZCyXDHgMIabE0LZenDRO0ZYY2TdG2"
    "Odo4SVtnafN0X7fP/wLfeaK2ut6BBgAAAABJRU5ErkJggg=="
)


def load_icon(root) -> Optional[object]:
    """Pasang ikon jendela; aman dipanggil walau Tk menolak gambar."""
    try:
        import tkinter as tk

        image = tk.PhotoImage(data=ICON_PNG_BASE64)
        root.iconphoto(True, image)
        return image
    except Exception:  # pragma: no cover - platform tanpa dukungan ikon
        return None
