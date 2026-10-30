# Data: daftar device + hasil pengayaan

Folder ini menyimpan input mentah dan lookup yang dipakai untuk memperkaya daftar
kode device (`Build.DEVICE`) menjadi tabel yang punya **nama perangkat, merek, OS,
jenis perangkat, dan tingkat keyakinan**.

| Berkas | Keterangan |
|---|---|
| `device_list_raw.csv` | Input asli (2.188 baris): kolom indeks + `Device` (kode device Android). |
| `device_catalog_lookup.csv` | Potongan katalog Google Play yang hanya memuat kode-kode di input (brand, manufacturer, nama model, form factor, resolusi, dpi). |
| `../device_list_enriched.csv` | **Hasil akhir** (CSV, 2.188 baris) — inilah deliverable-nya. |
| `../scripts/enrich_device_list.py` | Script pengayaan + pembangun lookup. |

## Kolom pada `device_list_enriched.csv`

| Kolom | Isi |
|---|---|
| `no` | Nomor baris dari file input (0–2187). |
| `device` | Kode device asli apa adanya (tidak diubah). |
| `nama_device` | Nama pemasaran perangkat, mis. `Galaxy A56 5G`, `Infinix HOT 60 Pro`. |
| `brand` | Merek yang dinormalisasi (`Samsung`, `OPPO`, `vivo`, `realme`, `Redmi`, `POCO`, `TECNO`, `itel`, `Advan`, …). Operator/kartu (KDDI, docomo, Verizon) diganti nama pabrikan. |
| `os` | `android` / `unknown` (lihat catatan di bawah). |
| `jenis` | `phone`, `tablet`, `watch`, `tv`, `tv box / embedded`, `chromebook`, `automotive`, `emulator`, `unknown`. |
| `keyakinan` | Skor 0–100 untuk **baris itu**. |
| `catatan` | Dasar penilaian: sumber pencocokan, kandidat merek lain, atau alasan skor diturunkan. |

## Skala `keyakinan`

| Skor | Arti |
|---|---|
| 95–100 | Cocok persis di katalog Google Play, satu merek, satu model. |
| 85–94 | Cocok persis, tetapi nama model di katalog hanya berupa kode model (mis. `CPH2239`), atau ada varian model lain dengan kode sama. |
| 70–84 | Kode dipakai beberapa merek sekaligus → dipilih merek paling umum (kandidat lain ditulis di `catatan`), atau jenis dikoreksi karena data layar tidak konsisten, atau hasil pencocokan setelah normalisasi penulisan. |
| 40–69 | Tidak ada di katalog; kesimpulan diambil dari pola kode (mis. `OP*` = OPPO/OnePlus, `RE*` = realme, `RMX*` = realme, `V####`/`PD*` = vivo, `TB*` = tablet Lenovo, `XT*` = Motorola) atau tabel kurasi kecil. |
| < 40 | Hanya dugaan: nama build ODM/klon, board SoC generik, atau kode yang meniru nama model terkenal. Merek biasanya `tidak diketahui`. |

## Cara kerja

1. Kode device dicocokkan **case-insensitive** ke katalog Google Play
   (`Device` → `Brand`/`Manufacturer`/`Model Name`/`Form Factor`/`Screen Sizes`/`Screen Densities`).
2. Bila tidak ada, dicoba pencocokan setelah normalisasi tanda baca (`opusxx` vs
   `OPUS-XX`), lalu aturan pola prefix kode merek, lalu tabel kurasi manual
   (`SUPPLEMENT` di script).
3. `Form Factor` katalog dipetakan ke `jenis`. Bila kosong atau jelas tidak konsisten
   dengan resolusi (mis. OnePlus 5 tercatat "Tablet"), jenis ditebak/dikoreksi dan skor
   diturunkan — koreksi selalu ditulis di `catatan`.
4. Nama model yang belum memuat merek diberi prefix merek agar mudah dibaca
   (`CPH2239` → `OPPO CPH2239`).

## Regenerasi

```bash
# dari katalog Google Play penuh (mis. android-devices-catalog.csv)
python scripts/enrich_device_list.py --catalog android-devices-catalog.csv --build-lookup
python scripts/enrich_device_list.py
```

Tanpa `--catalog`, script memakai `data/device_catalog_lookup.csv` yang sudah ada,
jadi bisa jalan offline.

## Batasan yang perlu diketahui

- **`os` praktis selalu `android`.** Semua nilai di input adalah kode device Android
  (`Build.DEVICE`); perangkat iOS tidak pernah muncul dengan format ini. Kolom ini tetap
  disediakan sesuai permintaan, tetapi informasinya rendah. Satu baris (`unknown`) tidak
  bisa dipastikan sehingga diisi `unknown`.
- Baris seperti `13C`, `S23 Ultra`, `i15ProMax`, atau `Galaxy_S25_Ultra` adalah **nama
  pemasaran yang dipakai sebagai kode device** — pada perangkat Samsung/Apple asli kolom
  `Build.DEVICE` berisi kode board (mis. `dm3q`, `iPhone15,3`). Baris seperti ini
  kemungkinan besar perangkat klon/replika, jadi skornya rendah dan diberi catatan.
- Sekitar 8% kode tidak ada di katalog Google Play (kode sangat baru, kode internal OEM,
  board SoC generik, atau build ODM). Untuk baris itu skor rendah dan catatan menjelaskan
  dasar dugaan.
- Sebagian entri katalog hanya memuat **kode model** sebagai "nama model" (banyak OPPO
  `CPH####` dan vivo `V####`). Nama pemasaran untuk kasus ini tidak tersedia di sumber;
  baris ditandai di `catatan` dan skornya diturunkan 5 poin.
- Sumber data pihak ketiga: Google Play *device catalog* (lewat mirror
  `hossain-khan/android-device-catalog-parser`). Nama model bisa tertinggal dari rilisan
  terbaru; perbarui lookup secara berkala dengan perintah di atas.
