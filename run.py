#!/usr/bin/env python3
"""Titik masuk sederhana: ``python run.py`` (tanpa perlu instalasi paket).

Semua logika ada di :mod:`activity_logger.cli`; skrip ini hanya memastikan
folder proyek masuk ke ``sys.path`` agar bisa dijalankan langsung dari hasil
``git clone``.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from activity_logger.cli import main  # noqa: E402  (setelah sys.path diatur)

if __name__ == "__main__":
    raise SystemExit(main())
