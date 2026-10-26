"""Antarmuka baris perintah.

Modul ini sengaja **tidak** mengimpor Tkinter sampai benar-benar dibutuhkan,
sehingga pesan kesalahan (mis. ``--version`` atau Tkinter belum terpasang)
tetap bisa ditampilkan dengan rapi.
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys
from typing import List, Optional

from . import __version__
from .core.settings import Settings

PROG = "activity-logger"


def tkinter_available() -> bool:
    """True bila Tkinter (dan modul C ``_tkinter``) bisa diimpor."""
    try:
        importlib.import_module("_tkinter")
        importlib.import_module("tkinter")
    except Exception:
        return False
    return True


def ttkbootstrap_available() -> bool:
    try:
        importlib.import_module("ttkbootstrap")
    except Exception:
        return False
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Catat kegiatan harian ke file JSON, lalu ekspor ke CSV/Markdown. "
            "Data disimpan lokal dan langsung tersimpan setiap kali menambah kegiatan."
        ),
        epilog="Contoh: activity-logger --data ~/Catatan/kegiatan.json --theme dark",
    )
    parser.add_argument("--data", help="Lokasi file JSON penyimpanan kegiatan")
    parser.add_argument(
        "--theme", choices=("light", "dark"), help="Mode warna awal (terang/gelap)"
    )
    parser.add_argument(
        "--port", type=int, help="Port untuk akses dari HP di jaringan lokal"
    )
    parser.add_argument(
        "--version", action="store_true", help="Tampilkan versi lalu keluar"
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print("Activity Logger {}".format(__version__))
        return 0

    if not tkinter_available():
        print(
            "Tkinter tidak tersedia, jadi jendela aplikasi tidak bisa dibuka.\n"
            "Cara memasang:\n"
            "  • Windows/macOS : install ulang Python dari python.org (centang tcl/tk)\n"
            "  • Debian/Ubuntu: sudo apt install python3-tk\n"
            "  • Fedora       : sudo dnf install python3-tkinter\n"
            "  • Arch         : sudo pacman -S tk",
            file=sys.stderr,
        )
        return 1

    if not ttkbootstrap_available():
        print(
            "Catatan: paket 'ttkbootstrap' belum terpasang. Aplikasi tetap berjalan "
            "dengan tema dasar.\nUntuk tampilan Bootstrap penuh:\n"
            "    pip install -r requirements.txt\n",
            file=sys.stderr,
        )

    settings = Settings.load()
    if args.data:
        settings.data_path = os.path.abspath(os.path.expanduser(args.data))
    if args.theme:
        settings.theme = args.theme
    if args.port:
        settings.mobile_port = args.port
    settings.normalize()

    from .gui.app import run

    return run(settings)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
