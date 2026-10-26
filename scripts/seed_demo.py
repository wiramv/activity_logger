"""Isi file contoh ke data Activity Logger (untuk demo / screenshot).

Pemakaian:

    python scripts/seed_demo.py                 # 60 kegiatan contoh di bulan ini
    python scripts/seed_demo.py --count 120     # lebih banyak
    python scripts/seed_demo.py --path data/demo.json
    python scripts/seed_demo.py --force         # timpa data yang sudah ada

Skrip ini menulis lewat ``ActivityStore`` sehingga format file tetap konsisten.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from activity_logger.core import timeutil  # noqa: E402
from activity_logger.core.settings import default_data_path  # noqa: E402
from activity_logger.core.storage import ActivityStore  # noqa: E402

ACTIVITIES = [
    "Olahraga pagi",
    "Shalat Subuh",
    "Membaca buku",
    "Mengerjakan desain dashboard",
    "Meeting dengan tim",
    "Review pull request",
    "Menulis dokumentasi API",
    "Belajar Python",
    "Menonton film",
    "Menulis laporan mingguan",
    "Makan malam bersama keluarga",
    "Menyusun rencana besok",
    "Memperbaiki bug halaman login",
    "Riset kompetitor aplikasi",
    "Olahraga sore",
    "Menghubungi klien via telepon",
    "Menyiapkan materi presentasi",
    "Backup data proyek",
    "Membersihkan meja kerja",
    "Refactor modul ekspor CSV",
]

HOURS = [6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 19, 20, 21]


def build_items(count: int, reference: date, rng: random.Random):
    items = []
    for index in range(count):
        days_back = rng.randint(0, 24)
        day = reference - timedelta(days=days_back)
        hour = rng.choice(HOURS)
        minute = rng.choice((0, 5, 10, 15, 20, 30, 40, 45, 50))
        moment = datetime(day.year, day.month, day.day, hour, minute, rng.randint(0, 59))
        text = ACTIVITIES[index % len(ACTIVITIES)]
        items.append((text, moment))
    return sorted(items, key=lambda pair: pair[1])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Isi data contoh Activity Logger")
    parser.add_argument("--path", default=default_data_path(), help="lokasi file JSON")
    parser.add_argument("--count", type=int, default=60, help="jumlah kegiatan")
    parser.add_argument("--seed", type=int, default=7, help="seed acak")
    parser.add_argument(
        "--force", action="store_true", help="tetap tambah walau file sudah berisi data"
    )
    args = parser.parse_args(argv)

    store = ActivityStore(args.path)
    store.load()
    if store.count() and not args.force:
        print(
            "File {} sudah berisi {} kegiatan. Pakai --force untuk menambah contoh lagi.".format(
                store.path, store.count()
            )
        )
        return 1

    rng = random.Random(args.seed)
    items = build_items(max(1, args.count), timeutil.today(), rng)
    for text, moment in items:
        store.add(text, when=moment, done=rng.random() < 0.25)

    print("{} kegiatan contoh ditulis ke {}".format(store.count(), store.path))
    print("Buka aplikasi dengan: python run.py --data \"{}\"".format(store.path))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
