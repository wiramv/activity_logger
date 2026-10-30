#!/usr/bin/env python3
"""Enrich a raw Android device-codename list with brand / model / OS / type / confidence.

Input : data/device_list_raw.csv  (kolom: index kosong + "Device" = kode device / Build.DEVICE)
Output: device_list_enriched.csv  (CSV, kolom: no, device, nama_device, brand, os, jenis, keyakinan, catatan)

Sumber utama pemetaan: Google Play "device catalog" CSV (kolom
Brand, Device, Manufacturer, Model Name, Form Factor, ...). Lookup ringkas untuk
kode yang dipakai disimpan di data/device_catalog_lookup.csv supaya script tetap
bisa dijalankan offline. Bangun ulang lookup dari katalog penuh dengan:

    python scripts/enrich_device_list.py --catalog android-devices-catalog.csv --build-lookup

Sisa kode yang tidak ada di katalog diselesaikan dengan aturan pola (prefix kode
merek/model) + tabel kurasi kecil (SUPPLEMENT). Setiap baris diberi skor
keyakinan 0-100 beserta catatan dasar penilaiannya.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "device_list_raw.csv"
DEFAULT_LOOKUP = ROOT / "data" / "device_catalog_lookup.csv"
DEFAULT_OUTPUT = ROOT / "device_list_enriched.csv"

LOOKUP_FIELDS = ["device", "brand", "manufacturer", "model_name", "form_factor", "screen", "dpi"]

# ---------------------------------------------------------------------------
# Normalisasi nama merek
# ---------------------------------------------------------------------------

BRAND_CANON = {
    "samsung": "Samsung", "xiaomi": "Xiaomi", "redmi": "Redmi", "poco": "POCO",
    "oppo": "OPPO", "vivo": "vivo", "realme": "realme", "oneplus": "OnePlus",
    "infinix": "Infinix", "tecno": "TECNO", "tecno-mobile": "TECNO", "itel": "itel",
    "motorola": "Motorola", "honor": "HONOR", "huawei": "Huawei", "google": "Google",
    "asus": "ASUS", "sony": "Sony", "nokia": "Nokia", "zte": "ZTE", "nubia": "nubia",
    "redmagic": "RedMagic (nubia)", "iqoo": "iQOO", "lenovo": "Lenovo", "lge": "LG",
    "lg": "LG", "sharp": "Sharp", "nothing": "Nothing", "meizu": "Meizu", "tcl": "TCL",
    "advan": "Advan", "evercoss": "Evercoss", "alcatel": "Alcatel", "wiko": "Wiko",
    "blackberry": "BlackBerry", "htc": "HTC", "amazon": "Amazon", "coolpad": "Coolpad",
    "umidigi": "UMIDIGI", "doogee": "Doogee", "blackview": "Blackview",
    "blackshark": "Black Shark", "cubot": "Cubot", "oukitel": "Oukitel",
    "ulefone": "Ulefone", "teclast": "Teclast", "mobicel": "Mobicel", "inoi": "INOI",
    "lava": "Lava", "blu": "BLU", "symphony": "Symphony", "walton": "Walton",
    "villaon": "VillaOn", "stylo": "Stylo", "iku": "IKU", "hiking": "HiKing",
    "kxd": "KXD", "sg": "SG", "luna": "Luna", "leagoo": "LEAGOO", "hyundai": "Hyundai",
    "g-tab": "G-Tab", "g-tab_": "G-Tab", "hotwav": "Hotwav", "elevate": "Elevate",
    "seuic": "SEUIC", "hmd": "HMD", "vortex": "Vortex", "trident": "Trident",
    "wintouch": "Wintouch", "we": "WE", "gloria": "Gloria", "x-tigi": "X-TIGI",
    "blaupunkt": "Blaupunkt", "fpd": "FPD", "aiwa": "Aiwa",
    "daewoo": "Daewoo", "infocus": "InFocus", "besttab": "BestTab", "iyou": "iYOU",
    "aoc": "AOC", "starlight": "Starlight", "lanix": "Lanix", "rakuten": "Rakuten",
    "sego": "Sego", "alps": "Alps", "omix": "OMIX", "techpad": "TechPad",
    "xmobile": "Xmobile", "neffos": "Neffos", "vernee": "Vernee",
    "phonemax": "PhoneMax", "olike": "Olike", "meitu": "Meitu", "pritom": "Pritom",
    "vgo_tel": "VGO Tel", "vgotel": "VGO Tel", "zebra": "Zebra", "benco": "Benco",
    "allwinner": "Allwinner", "axioo": "Axioo", "aigo": "AIGO", "admiral": "Admiral",
    "turbo-x": "Turbo-X", "jeazans": "Jeazans", "odea": "Odea", "sico": "SICO",
    "essl": "eSSL", "pax": "PAX", "marvue": "Marvue", "ainmel": "Ainmel", "ktc": "KTC",
    "rangs": "Rangs", "phimark": "Phimark", "rca": "RCA", "diggio": "Diggio",
    "mag": "MAG", "kiowa": "Kiowa", "master-g": "Master-G", "global": "Global",
    "wybor": "Wybor", "daiwa": "Daiwa", "siragon": "Siragon", "qriom": "Qriom",
    "philips": "Philips", "star-track": "Star-Track", "vimeel": "Vimeel",
    "colorview": "ColorView", "kenwood": "Kenwood", "esley": "Esley",
    "damasco": "Damasco", "mitsuki": "Mitsuki", "challenger": "Challenger",
    "pel": "PEL", "jvc": "JVC", "nexus": "Nexus", "multismart": "Multismart",
    "innova": "Innova", "mastertech": "Mastertech", "tvb": "TVB", "env": "ENV",
    "contixo": "Contixo", "picassotab": "PicassoTab", "concord": "Concord",
    "caxilysh": "Caxilysh", "sgin": "SGIN", "tibuta": "Tibuta", "avidpad": "AvidPad",
    "quest": "Quest", "yandex": "Yandex", "dora": "Dora", "bpl": "BPL",
    "techlife": "Techlife", "rindo": "Rindo", "homez": "Homez", "brando": "Brando",
    "wansa": "Wansa", "classpro": "Classpro", "kogan": "Kogan", "bauhn": "Bauhn",
    "changhong": "Changhong", "asher": "Asher", "grunhelm": "Grunhelm",
    "chiq": "CHiQ", "liberton": "Liberton", "nikkei": "Nikkei", "condor": "Condor",
    "tdsystems": "TDSYSTEMS", "pilot": "Pilot", "strong": "Strong",
    "albadeel": "Albadeel", "kolin": "Kolin", "united": "United", "syinix": "Syinix",
    "biolux": "Biolux", "ergo": "Ergo", "elsonic": "Elsonic", "ok": "OK",
    "cristor": "Cristor", "premier": "Premier", "jetpoint": "JetPoint",
    "kunft": "Kunft", "shinon": "Shinon", "saba": "Saba", "teklio": "Teklio",
    "orion": "Orion", "thomson": "Thomson", "benq": "BenQ", "ud": "UD",
    "anexa": "Anexa", "polaroid": "Polaroid", "singer": "Singer", "maximus": "Maximus",
    "kozen": "Kozen", "getnord": "Getnord", "trimble": "Trimble", "kobo": "Kobo",
    "lifephone": "LifePhone", "smart": "Smart", "attila": "Attila", "q7": "Q7",
    "sunmax": "SunMax", "tench": "Tench", "acepad": "AcePad", "teracube": "Teracube",
    "africell": "Africell", "gplus": "Gplus", "duoduogo": "Duoduogo",
    "vankyo": "Vankyo", "nomu": "NOMU", "i-custom": "i-custom", "dialn": "Dialn",
    "bluebird": "Bluebird", "xgody": "XGODY", "plimpton": "Plimpton",
    "dragon_touch": "Dragon Touch", "eks": "EKS", "nio": "NIO",
    "motorolasolutions": "Motorola Solutions", "selvas": "Selvas",
    "x-premium": "X-Premium", "rizzen": "Rizzen", "abctech": "ABCTECH",
    "litetel": "LiteTEL", "iotapk": "iotapk", "surfans": "Surfans",
    "azeyou": "Azeyou", "colorroom": "ColorRoom", "okulaku": "Okulaku",
    "muisoo": "Muisoo", "aiplus": "Aiplus", "maxhub": "MAXHUB", "redbeat": "Redbeat",
    "ila": "ILA", "winnovo": "Winnovo", "homtom": "Homtom", "senraise": "Senraise",
    "kenshi": "Kenshi", "freeyond": "FreeYond", "xplore": "Xplore",
    "meberry": "Meberry", "homii": "HOMII", "olla": "Olla", "estream4k": "eStream4K",
    "airtv": "AirTV", "uauu": "UAUU", "telpo": "Telpo", "evertek": "Evertek",
    "cwell": "Cwell", "ipro": "iPro", "mito": "MITO", "benten": "Benten",
    "foxxd": "FOXXD", "poptel": "Poptel", "mafe": "Mafe", "maxtron": "Maxtron",
    "sunbio": "Sunbio", "bigme": "Bigme", "kalley": "Kalley",
    "ramtechnology": "RAMTechnology", "solanamobile": "Solana Mobile",
    "imuz": "iMUZ", "rebotai": "RebotAi", "digit": "Digit", "kyocera": "Kyocera",
    "orbic": "Orbic", "crelander": "Crelander", "droidlogic": "Droidlogic",
    "ajib": "Ajib", "vocal": "Vocal", "qps": "QPS", "idata": "iData",
    "digits": "digITS", "tevau": "Tevau", "ayya": "AYYA",
    "trumpmobile": "TrumpMobile", "mls": "MLS", "asanzo": "Asanzo",
    "sparx": "Sparx", "my": "My", "acer": "Acer", "vastking": "Vastking",
    "kanselir": "Kanselir", "strawberry": "Strawberry", "zoji": "ZOJI",
    "reekoo": "Reekoo",
    "veidoo": "Veidoo", "dcode": "DCODE", "hoozo": "HOOZO", "bmax": "BMAX",
    "panasonic": "Panasonic", "e-lead": "E-LEAD", "atozee": "Atozee", "zyrex": "Zyrex",
    "rebecco": "Rebecco", "premio": "Premio", "astech": "Astech",
    "callsky": "Callsky", "callsky-tab": "Callsky", "doro": "Doro", "haier": "Haier",
    "reeder": "Reeder", "trecfone": "TrecFone", "tabwee": "Tabwee", "aauw": "AAUW",
    "oscal": "Oscal", "altron": "Altron", "sprd": "SPRD", "sunmi": "Sunmi",
    "wigor": "Wigor", "koolmaax": "KOOLMAAX", "vsmart": "Vsmart", "newland": "Newland",
}
# pembersihan entri yang tidak sengaja memakai huruf non-latin
BRAND_CANON["maxtron"] = "Maxtron"

# Merek operator/retail: pakai nama pabrikan agar kolom brand bermakna
CARRIER_BRANDS = {
    "kddi", "docomo", "verizon", "altice", "deutschetelekom", "mtn", "smartfren",
    "rakuten", "att", "t-mobile", "softbank", "sprint", "orange", "vodafone",
    "telekom", "cellcom", "bell", "ntt", "chunghwa", "telia", "elisa", "swisscom",
}

# Merek besar/umum di pasar Indonesia -> dipakai mendahulukan saat kode dipakai
# beberapa merek sekaligus (kode bentrok antar-OEM).
BRAND_PRIORITY = [
    "samsung", "xiaomi", "redmi", "poco", "oppo", "vivo", "realme", "oneplus",
    "infinix", "tecno", "itel", "motorola", "honor", "huawei", "google", "asus",
    "sony", "nokia", "zte", "nubia", "iqoo", "lenovo", "lge", "lg", "sharp",
    "nothing", "meizu", "tcl", "advan", "evercoss", "alcatel", "wiko",
    "blackberry", "htc", "amazon", "coolpad", "umidigi", "doogee", "blackview",
]
PRIORITY_RANK = {b: i for i, b in enumerate(BRAND_PRIORITY)}

FORM_FACTOR_MAP = {
    "phone": "phone",
    "tablet": "tablet",
    "tv": "tv",
    "wearable": "watch",
    "chromebook": "chromebook",
    "android automotive": "automotive",
    "google play games on pc": "emulator",
}

# ---------------------------------------------------------------------------
# Aturan cadangan (kode tidak ada di katalog Google Play)
# Format: kode (lowercase) -> (brand, nama_device, jenis, keyakinan, catatan)
# ---------------------------------------------------------------------------

SUPPLEMENT = {
    # --- nilai bukan device nyata -------------------------------------------
    "unknown": ("", "tidak diketahui", "unknown", 0,
                "sumber data berisi 'unknown'; tidak ada informasi apa pun"),
    "android": ("", "nama perangkat generik ('Android')", "unknown", 10,
                "nama device terlalu generik untuk diidentifikasi"),
    "smartphone": ("", "nama perangkat generik ('SmartPhone')", "phone", 15,
                   "nama generik; jenis hanya dugaan dari namanya"),
    "emu64a": ("", "Android Emulator (AVD arm64)", "emulator", 85,
               "nama AVD emulator Android resmi, bukan perangkat fisik"),
    "emu64xa": ("", "Android Emulator (AVD arm64/x86)", "emulator", 80,
                "nama AVD emulator Android resmi, bukan perangkat fisik"),
    "emu64a16k": ("", "Android Emulator (AVD arm64, RAM 16K page)", "emulator", 75,
                  "varian AVD emulator Android, bukan perangkat fisik"),
    "x86_64": ("", "abstraksi arsitektur x86_64", "emulator", 45,
               "nama arsitektur/emulator, bukan model perangkat"),
    "windows_x86_64": ("", "abstraksi arsitektur Windows x86_64", "emulator", 45,
                       "nama arsitektur/emulator, bukan model perangkat"),
    # --- merek jelas dari prefix -------------------------------------------
    "tecno": ("TECNO", "TECNO (model tidak diketahui)", "phone", 80,
              "hanya nama merek yang terkirim"),
    "tecno-bd4a": ("TECNO", "TECNO BD4a", "phone", 90, "prefix TECNO-* = kode model TECNO"),
    "tecno-kl4h": ("TECNO", "TECNO KL4h", "phone", 90, "prefix TECNO-* = kode model TECNO"),
    "tecno-km4n": ("TECNO", "TECNO KM4n", "phone", 90, "prefix TECNO-* = kode model TECNO"),
    "infinix-x6831": ("Infinix", "Infinix X6831", "phone", 90, "prefix Infinix-* = kode model Infinix"),
    "infinix-x6816": ("Infinix", "Infinix X6816", "phone", 90, "prefix Infinix-* = kode model Infinix"),
    "infinix-x666b": ("Infinix", "Infinix X666B", "phone", 90, "prefix Infinix-* = kode model Infinix"),
    "infinix-x1301": ("Infinix", "Infinix X1301", "phone", 85, "prefix Infinix-* = kode model Infinix"),
    "itel-a681l": ("itel", "itel A681L", "phone", 90, "prefix itel-* = kode model itel"),
    "itel-p673l": ("itel", "itel P673L", "phone", 90, "prefix itel-* = kode model itel"),
    "itel-p08002l": ("itel", "itel P08002L", "phone", 80, "prefix itel-* = kode model itel"),
    "advan_tab_v8": ("Advan", "Advan Tab V8", "tablet", 90, "prefix ADVAN_* + 'TAB' = tablet Advan"),
    "advan_a10_pro": ("Advan", "Advan A10 Pro", "phone", 85, "prefix ADVAN_* = perangkat Advan"),
    "advan_v11": ("Advan", "Advan V11", "phone", 85, "prefix ADVAN_* = perangkat Advan"),
    "advan_x1_neo": ("Advan", "Advan X1 Neo", "phone", 85, "prefix ADVAN_* = perangkat Advan"),
    "asus_x00t_1": ("ASUS", "ASUS ZenFone Max Pro M1 (X00T)", "phone", 85,
                    "kode X00T = ZenFone Max Pro M1; sufiks _1 hanya varian SKU"),
    "asus_i005da": ("ASUS", "ASUS ROG Phone 5 (I005D)", "phone", 90,
                    "kode I005D = ROG Phone 5; sufiks _A/DA varian regional"),
    "rmx2163l1": ("realme", "realme RMX2163", "phone", 85,
                  "prefix RMX* = realme; sufiks L1 varian pasar"),
    "rmx1903": ("realme", "realme RMX1903", "phone", 85,
                "prefix RMX* = realme; sufiks L1 varian pasar"),
    "cph1869": ("OPPO", "OPPO CPH1869", "phone", 85, "prefix CPH* = OPPO"),
    "pd2324": ("vivo", "vivo PD2324", "phone", 80, "prefix PD* didominasi vivo di katalog"),
    "pd1930f_ex": ("vivo", "vivo PD1930F (EX)", "phone", 80, "prefix PD* didominasi vivo di katalog"),
    "pd1803f_ex": ("vivo", "vivo PD1803F (EX)", "phone", 80, "prefix PD* didominasi vivo di katalog"),
    "v2111": ("vivo", "vivo V2111", "phone", 75, "pola V#### = kode model vivo"),
    "vcph2477": ("vivo", "vivo VCPH2477", "phone", 65, "pola mirip kode vivo/OPPO, tidak ada di katalog"),
    "vcph2591": ("vivo", "vivo VCPH2591", "phone", 65, "pola mirip kode vivo/OPPO, tidak ada di katalog"),
    "2127u": ("vivo", "vivo 2127U", "phone", 70, "pola kode 4 digit = vivo (mis. 2127)"),
    "xt2573-1": ("Motorola", "Motorola XT2573-1", "phone", 90, "prefix XT#### = kode model Motorola"),
    "xt2571-1": ("Motorola", "Motorola XT2571-1", "phone", 90, "prefix XT#### = kode model Motorola"),
    "tb331fc": ("Lenovo", "Lenovo Tab (TB331FC)", "tablet", 90, "prefix TB* = tablet Lenovo"),
    "tb322fc": ("Lenovo", "Lenovo Tab (TB322FC)", "tablet", 90, "prefix TB* = tablet Lenovo"),
    "sm-s938b": ("Samsung", "Galaxy S25 Ultra", "phone", 95, "kode model SM-S938 = Galaxy S25 Ultra"),
    "sm-s928b": ("Samsung", "Galaxy S24 Ultra", "phone", 95, "kode model SM-S928 = Galaxy S24 Ultra"),
    "gts12p": ("Samsung", "Galaxy Tab S12+ (dugaan)", "tablet", 65,
               "pola board Samsung gts* = Galaxy Tab S; nomor 12 belum ada di katalog"),
    "a18m": ("Samsung", "Galaxy A18 (dugaan)", "phone", 60,
             "pola board Samsung a##m; model belum terverifikasi"),
    "r14s": ("Samsung", "Galaxy S26 FE (dugaan)", "phone", 55,
             "pola board Samsung r1Xs = seri Galaxy Sxx FE (r12s=S24 FE, r13s=S25 FE)"),
    "y51l": ("vivo", "vivo Y51L", "phone", 85, "nama device = kode model vivo Y51L"),
    "a59m": ("OPPO", "OPPO A59m", "phone", 85, "nama device = kode model OPPO A59m"),
    "tissot": ("Xiaomi", "Mi A1", "phone", 85, "tissot = kode Xiaomi Mi A1 (Android One)"),
    "p60_pro": ("Huawei", "Huawei P60 Pro", "phone", 75, "nama device berupa nama marketing Huawei"),
    "pura_80_air": ("Huawei", "Huawei Pura 80 Air (dugaan)", "phone", 65,
                    "nama mengikuti seri Huawei Pura; model belum terverifikasi"),
    "reno10 pro": ("OPPO", "OPPO Reno10 Pro", "phone", 85, "nama device berupa nama marketing OPPO"),
    "reno10_pro": ("OPPO", "OPPO Reno10 Pro", "phone", 85, "nama device berupa nama marketing OPPO"),
    "reno9 pro": ("OPPO", "OPPO Reno9 Pro", "phone", 85, "nama device berupa nama marketing OPPO"),
    "galaxy_a56_5g": ("Samsung", "Galaxy A56 5G (klaim)", "phone", 60,
                      "nama marketing dipakai sebagai kode device; umumnya perangkat klon/replika"),
    "galaxy_s25_ultra": ("Samsung", "Galaxy S25 Ultra (klaim)", "phone", 60,
                         "nama marketing dipakai sebagai kode device; umumnya perangkat klon/replika"),
    "oppo6779": ("OPPO", "OPPO (board MT6779)", "phone", 72,
                 "nama board MediaTek MT6779 yang dipakai seri OPPO; model pasti tidak diketahui"),
    "oppo6833": ("OPPO", "OPPO (board MT6833)", "phone", 72,
                 "nama board MediaTek MT6833 yang dipakai seri OPPO; model pasti tidak diketahui"),
    "pad7s": ("", "Tablet 'Pad7S' (merek tidak diketahui)", "tablet", 35,
              "nama menyerupai tablet; merek tidak ada di katalog"),
    "pro12": ("", "Tablet 'Pro 12' (merek tidak diketahui)", "tablet", 32,
              "nama menyerupai tablet generik; merek tidak dapat dipastikan"),
    "pro12ultra": ("", "Tablet 'Pro 12 Ultra' (merek tidak diketahui)", "tablet", 32,
                   "nama menyerupai tablet generik; merek tidak dapat dipastikan"),
    "xpad20": ("", "Tablet 'XPAD20' (merek tidak diketahui)", "tablet", 32,
               "nama menyerupai tablet generik; merek tidak dapat dipastikan"),
    "tab_g17pro": ("", "Tablet 'Tab G17 Pro' (merek tidak diketahui)", "tablet", 38,
                   "kata 'Tab' menandakan tablet; merek tidak dapat dipastikan"),
    "pro11": ("", "Tablet 'Pro 11' (merek tidak diketahui)", "tablet", 30,
              "nama menyerupai tablet generik; merek tidak dapat dipastikan"),
    "pro12ultra": ("", "Tablet 'Pro 12 Ultra' (merek tidak diketahui)", "tablet", 30,
                   "nama menyerupai tablet generik; merek tidak dapat dipastikan"),
    "mercury-demo": ("", "perangkat demo/kiosk ('mercury-demo')", "unknown", 20,
                     "label demo/prototipe, bukan model ritel"),
    "t527-demo-car": ("", "head unit / demo board Allwinner T527", "automotive", 45,
                      "nama board Allwinner T527 untuk head unit mobil"),
    "ravoz_a7": ("RAVOZ", "RAVOZ A7", "phone", 75, "nama perangkat memuat merek RAVOZ"),
    "inoi_tab_2": ("INOI", "INOI Tab 2", "tablet", 80, "nama perangkat memuat merek INOI + 'Tab'"),
    "pearl_k2_2020": ("Pearl", "Pearl K2 (2020)", "phone", 65, "nama perangkat memuat merek Pearl"),
    "pearl_k3_2021": ("Pearl", "Pearl K3 (2021)", "phone", 65, "nama perangkat memuat merek Pearl"),
    "m9pro": ("LEAGOO", "LEAGOO M9 Pro", "phone", 55,
              "mirip entri katalog 'LEAGOO M9 Pro' (beda penulisan)"),
    "s10pro": ("Ulefone", "Ulefone S10 Pro", "phone", 50,
               "mirip entri katalog 'Ulefone S10_Pro' (beda penulisan)"),
    "neo6": ("Sparx", "Sparx Neo 6", "phone", 50, "mirip entri katalog 'Sparx NEO_6'"),
    "tab_s1": ("MOVISUN", "MOVISUN TAB-S1", "tablet", 55, "mirip entri katalog 'MOVISUN TAB-S1'"),
}

# Pola prefix/sufiks kode -> (regex, brand, jenis, keyakinan, catatan)
PREFIX_RULES = [
    (r"^op[0-9a-z]+$", "OPPO", "phone", 60,
     "pola kode OP* dipakai OPPO & OnePlus (BBK); model tidak ada di katalog"),
    (r"^rmx[0-9]+[a-z0-9]*$", "realme", "phone", 80, "prefix RMX* = realme"),
    (r"^cph[0-9]+$", "OPPO", "phone", 80, "prefix CPH* = OPPO"),
    (r"^infinix-", "Infinix", "phone", 85, "prefix Infinix-*"),
    (r"^tecno-", "TECNO", "phone", 85, "prefix TECNO-*"),
    (r"^itel-", "itel", "phone", 85, "prefix itel-*"),
    (r"^advan", "Advan", "phone", 75, "prefix ADVAN_* (merek lokal Indonesia)"),
    (r"^villaon-", "VillaOn", "phone", 80, "prefix VILLAON-* (merek lokal Indonesia)"),
    (r"^asus", "ASUS", "phone", 85, "prefix ASUS*"),
    (r"^xt[0-9]{4}", "Motorola", "phone", 85, "prefix XT#### = Motorola"),
    (r"^tb[0-9]{3}", "Lenovo", "tablet", 85, "prefix TB### = tablet Lenovo"),
    (r"^sm-s[0-9]{3}", "Samsung", "phone", 85, "prefix SM-S### = Galaxy S series"),
    (r"^gt[sa]", "Samsung", "tablet", 75, "pola board Samsung gta*/gts* = Galaxy Tab"),
    (r"^v[0-9]{4}$", "vivo", "phone", 72, "pola V#### = kode model vivo"),
    (r"^hn[a-z0-9\-]+$", "HONOR", "phone", 72, "pola HN* = kode internal HONOR"),
    (r"^hw[a-z0-9\-]+$", "Huawei", "phone", 65, "pola HW* = kode internal Huawei (sebagian HONOR)"),
    (r"^p[0-9]{3}f[0-9]", "ZTE", "phone", 70, "pola P###F## didominasi ZTE di katalog"),
    (r"^i[0-9]{4}$", "iQOO", "phone", 65, "pola I#### didominasi iQOO di katalog"),
    (r"^[0-9]{4}[a-z]?$", "vivo", "phone", 65, "pola kode 4 digit = vivo"),
    (r"^nx[0-9]{3}[a-z]", "nubia", "phone", 78, "prefix NX### = nubia/RedMagic"),
]

# Kode generik: board/SoC/emulator/klon. Dievaluasi sebelum prefix rules.
GENERIC_RULES = [
    (r"^(emu64|ranchu|goldfish)", "emulator", 75, "nama emulator Android (AVD)"),
    (r"^(rk3[0-9]{3}|rk35[0-9]{2}|t527|t3-k2001|t3-p1|auto_rk|uis8581|sl8541|sp7731|"
     r"tb8163p3|sdm6[0-9]{2}|mt6[0-9]{3}|k50v1_64|k50sv1_64|k53v1_64|k62v1_64|k63v2_64|k80_bsp|"
     r"8227l)", "tv box / embedded", 45,
     "nama board/SoC generik (Rockchip/Unisoc/MediaTek) -> biasanya TV box, head unit, atau perangkat embedded"),
    (r"^[a-z0-9]+_[a-z0-9]+_[a-z0-9_]+$", "phone", 35,
     "nama build ODM/klon (memuat kata kunci model tiruan), merek tidak dapat dipastikan"),
]

# Nama yang jelas meniru model terkenal -> indikasi klon/replika
CLONE_PATTERNS = re.compile(
    r"(^ip(hone)?\s?\d|^i1[0-9]pro|pro_?max$|^galaxy_|^s\d{2}\s?ultra$|^s\d{2}_ultra$|"
    r"^note\s?\d{2}\s?pro$|^reno\d+|^hot\s?\d{2}\s?pro$|^p\d{2}\s?pro$|^a\d{2}pro$|"
    r"^1[0-9]c$|^1[0-9] pro$|^[0-9]{2}$|^[0-9]{2} ?(pro|ultra)$|^x\d{2}pro$)",
    re.IGNORECASE,
)


def screen_profile(screen: str, dpi: str) -> tuple[float, float, bool]:
    """Kembalikan (rasio sisi besar/kecil, lebar-dp sisi kecil, potret?) dari katalog."""
    m = re.match(r"(\d+)\s*x\s*(\d+)", screen or "")
    if not m:
        return 0.0, 0.0, False
    w, h = int(m.group(1)), int(m.group(2))
    low, high = sorted((w, h))
    if not low:
        return 0.0, 0.0, False
    dpis = [int(x) for x in re.findall(r"\d+", dpi or "")] or [0]
    # beberapa entri memuat daftar resolusi/dpi; ambil kerapatan tertinggi
    min_dp = min(low * 160.0 / d for d in dpis if d) if any(dpis) else 0.0
    return high / low, min_dp, h > w


def fix_form_factor(jenis: str, screen: str, dpi: str, nama: str) -> tuple[str, str]:
    """Koreksi jenis katalog yang jelas tidak konsisten dengan data layar.

    Contoh kasus nyata: OnePlus 5 tercatat 'Tablet' di katalog, dan sebagian TV
    box beresolusi potret. Koreksi hanya dilakukan bila resolution potret,
    rasio ponsel, ukuran < 600 dp, dan nama model tidak menyiratkan tablet/TV.
    """
    ratio, min_dp, portrait = screen_profile(screen, dpi)
    if not ratio:
        return jenis, ""
    low = nama.lower()
    if "tab" in low or "pad" in low or "tv" in low or "book" in low or "watch" in low:
        return jenis, ""
    if jenis in ("tv", "tablet") and portrait and ratio > 1.5 and min_dp < 600:
        return "phone", (f"katalog menandai '{jenis}' padahal layar {screen} ({dpi} dpi) "
                         f"berbentuk potret seperti ponsel; jenis dikoreksi ke phone")
    return jenis, ""


MODEL_CODE = re.compile(r"^(CPH\d+[A-Z]*|RMX\d+[A-Z]*|SM-[A-Z0-9]+|V\d{4}[A-Z]?|XT\d{4}[-\w]*|"
                        r"PB[A-Z0-9]+|M\d{4}|[A-Z]{2,4}\d{2,5}[A-Z]{0,2})$")
FOLDABLE = re.compile(r"\b(fold|flip)\b|Find N\d", re.IGNORECASE)


def canonical_brand(raw: str, manufacturer: str = "") -> str:
    """Nama merek rapi + konsisten; operator diganti nama pabrikan."""
    key = re.sub(r"[\s_]+", "", (raw or "").strip().lower())
    man_key = re.sub(r"[\s_]+", "", (manufacturer or "").strip().lower())
    if key in CARRIER_BRANDS and man_key:
        key = man_key
    if key in BRAND_CANON:
        return BRAND_CANON[key]
    for cand in (key.replace("_", ""), man_key):
        if cand in BRAND_CANON:
            return BRAND_CANON[cand]
    # fallback: rapikan kapitalisasi
    base = (raw or manufacturer or "").strip()
    if not base:
        return ""
    if base.isupper():
        return base.title() if len(base) > 4 else base
    return base[0].upper() + base[1:] if base.islower() else base


def normalize_key(code: str) -> str:
    return re.sub(r"[^a-z0-9]", "", code.lower())


def load_lookup(path: Path) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = defaultdict(list)
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            index[row["device"].strip().lower()].append(row)
    return index


def build_lookup(catalog: Path, out: Path, codes: set[str]) -> None:
    """Ambil hanya kode yang dibutuhkan dari katalog Google Play penuh."""
    wanted = {c.lower() for c in codes}
    alnum = {normalize_key(c) for c in codes}
    picked: list[dict] = []
    seen: set[tuple] = set()
    with catalog.open(encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            dev = (row.get("Device") or "").strip()
            if not dev:
                continue
            low = dev.lower()
            if low not in wanted and normalize_key(dev) not in alnum:
                continue
            key = (low, row.get("Brand", ""), row.get("Model Name", ""))
            if key in seen:
                continue
            seen.add(key)
            picked.append({
                "device": low,
                "brand": (row.get("Brand") or "").strip(),
                "manufacturer": (row.get("Manufacturer") or "").strip(),
                "model_name": (row.get("Model Name") or "").strip(),
                "form_factor": (row.get("Form Factor") or "").strip(),
                "screen": (row.get("Screen Sizes") or "").strip(),
                "dpi": (row.get("Screen Densities") or "").strip(),
            })
    picked.sort(key=lambda r: (r["device"], r["brand"], r["model_name"]))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=LOOKUP_FIELDS)
        writer.writeheader()
        writer.writerows(picked)
    print(f"lookup ditulis: {out} ({len(picked)} baris untuk {len(wanted)} kode)")


# Terjemahan nama model berbahasa Mandarin di katalog Google Play
CJK_NAME = {
    "Reno2 Z 中国版": "Reno2 Z (versi Tiongkok)",
    "荣耀 8X": "Honor 8X",
    "A9 中国版": "A9 (versi Tiongkok)",
    "A3中国版": "A3 (versi Tiongkok)",
    "Y93标准版 64G": "Y93 Standard Edition 64GB",
    "红魔11 Pro游戏手机": "RedMagic 11 Pro",
    "荣耀9i": "Honor 9i",
    "X300 Pro 卫星通信版": "X300 Pro Satellite Edition",
    "荣耀畅享7 Plus": "Honor Changxiang 7 Plus",
    "红魔10 Pro": "RedMagic 10 Pro",
    "荣耀平板5": "Honor Pad 5",
    "荣耀畅玩5A": "Honor Play 5A",
    "联想小新平板Pro GT": "Lenovo Xiaoxin Pad Pro GT",
}


CJK_SUBSTR = [
    ("\u4e2d\u56fd\u7248", "(versi Tiongkok)"),
    ("\u6807\u51c6\u7248", "Standard Edition"),
    ("\u536b\u661f\u901a\u4fe1\u7248", "Satellite Edition"),
    ("\u6e38\u620f\u624b\u673a", "gaming phone"),
    ("\u8363\u8000\u5e73\u677f", "Honor Pad"),
    ("\u8363\u8000", "Honor"),
    ("\u8054\u60f3\u5c0f\u65b0\u5e73\u677f", "Lenovo Xiaoxin Pad"),
    ("\u5e73\u677f", "Pad"),
]


NAME_BRAND_TOKENS = {
    "redmi", "poco", "mi", "galaxy", "pixel", "moto", "iqoo", "honor", "huawei",
    "oppo", "vivo", "realme", "oneplus", "oneplus5", "samsung", "infinix", "tecno",
    "itel", "nokia", "sony", "xperia", "lenovo", "asus", "lg", "zte", "nubia",
    "redmagic", "black", "motorola", "meizu", "tcl", "alcatel", "sharp", "nothing",
    "microsoft", "blackberry", "amazon", "coolpad", "fplus", "trecfone", "advan",
}


def with_brand(brand: str, nama: str) -> str:
    """Tambahkan merek di depan nama model yang belum menyebut mereknya."""
    if not brand or brand == "tidak diketahui" or not nama:
        return nama
    low = nama.lower()
    first = re.split(r"[\s\-]", low)[0]
    brand_words = [w for w in re.split(r"[\s\-]+", brand.lower()) if len(w) > 2]
    if brand.lower() in low or first in NAME_BRAND_TOKENS:
        return nama
    if any(w in low for w in brand_words):
        return nama
    return f"{brand} {nama}"


def clean_model_name(name: str) -> str:
    """Rapikan nama model: terjemahkan nama Mandarin, normalkan spasi/simbol."""
    name = name.strip()
    name = CJK_NAME.get(name, name)
    for src, dst in CJK_SUBSTR:
        name = name.replace(src, dst)
    name = name.replace("\uff08", " (").replace("\uff09", ")")
    name = re.sub(r"[\u00a0\u2000-\u200b\u202f\u3000]", " ", name)
    name = name.replace("\u2122", "").replace("\u00ae", "")
    name = re.sub(r"\s{2,}", " ", name).strip()
    return name


def rank_candidates(cands: list[dict]) -> list[dict]:
    """Urutkan kandidat: merek besar dulu, lalu merek dengan katalog terbanyak."""
    def key(row: dict):
        brand = canonical_brand(row["brand"], row["manufacturer"]).lower()
        return (PRIORITY_RANK.get(brand, 999), 0 if row["model_name"] else 1, row["brand"])
    return sorted(cands, key=key)


def classify(code: str, lookup: dict[str, list[dict]]) -> dict:
    """Tentukan brand/nama/jenis/keyakinan/catatan untuk satu kode device."""
    low = code.strip().lower()

    # 1) tabel kurasi untuk kode yang tidak ada di katalog
    if low in SUPPLEMENT and low not in lookup:
        brand, nama, jenis, conf, note = SUPPLEMENT[low]
        return _result(brand, nama, jenis, conf, note and [note] or [])

    # 2) cocok persis katalog Google Play
    cands = lookup.get(low)
    used_note: list[str] = []
    conf = 97

    if not cands:
        # 3) cocok setelah normalisasi (beda tanda hubung/garis bawah/spasi)
        nkey = normalize_key(low)
        cands = [r for k, rows in lookup.items() if normalize_key(k) == nkey for r in rows]
        if cands:
            conf = 78
            used_note.append("cocok setelah normalisasi penulisan kode")

    if not cands and low in SUPPLEMENT:
        brand, nama, jenis, confv, note = SUPPLEMENT[low]
        return _result(brand, nama, jenis, confv, note and [note] or [])

    if cands:
        cands = rank_candidates(cands)
        brands = []
        for row in cands:
            b = canonical_brand(row["brand"], row["manufacturer"])
            if b not in brands:
                brands.append(b)
        best = cands[0]
        brand = canonical_brand(best["brand"], best["manufacturer"])
        raw_name = clean_model_name(best["model_name"]) or brand
        nama = with_brand(brand, raw_name)
        ff = FORM_FACTOR_MAP.get(best["form_factor"].strip().lower())
        jenis = ff or "unknown"
        if not ff:
            jenis = guess_type_from_screen(best["screen"], code)
            conf -= 8
            used_note.append("form factor kosong di katalog; jenis ditebak dari resolusi/nama")
        else:
            jenis, ff_note = fix_form_factor(jenis, best["screen"], best["dpi"], raw_name)
            if ff_note:
                conf -= 5
                used_note.append(ff_note)
        if len(brands) > 1:
            conf -= 15
            others = ", ".join(f"{b} {clean_model_name(r['model_name'])}"
                               for b, r in _other_variants(cands, brand))
            used_note.append(f"kode dipakai beberapa merek; dipilih merek paling umum "
                             f"(kandidat lain: {others})")
        elif len({clean_model_name(r["model_name"]) for r in cands}) > 1:
            conf -= 7
            others = ", ".join(clean_model_name(r["model_name"])
                               for _, r in _other_variants(cands, brand))
            used_note.append(f"beberapa model memakai kode sama (varian: {others})")
        if raw_name.lower() == code.lower():
            conf -= 10
            used_note.append("nama model di katalog hanya mengulang kode device")
        if FOLDABLE.search(nama) and jenis == "tablet":
            jenis = "phone"
            used_note.append("perangkat lipat (foldable); katalog menandainya tablet, "
                             "di sini dikelompokkan sebagai phone")
        if MODEL_CODE.fullmatch(raw_name):
            conf -= 5
            used_note.append("katalog hanya menyediakan kode model, nama marketing tidak tersedia")
        if any(ord(ch) > 0x2E80 for ch in best["model_name"]) and best["model_name"] not in CJK_NAME:
            used_note.append("nama model asli berbahasa Mandarin")
        used_note.insert(0, "cocok persis katalog Google Play (brand + model)")
        return _result(brand, nama, jenis, max(conf, 40), used_note)

    # 4) aturan pola kode merek/model
    for pattern, brand, jenis, confv, note in PREFIX_RULES:
        if re.match(pattern, low):
            return _result(brand, f"{brand} (model tidak diketahui)", jenis, confv, [note])

    # 5) kode generik / board / klon
    for pattern, jenis, confv, note in GENERIC_RULES:
        if re.match(pattern, low):
            if CLONE_PATTERNS.search(code):
                note += "; nama meniru model terkenal (indikasi klon)"
            return _result("", f"tidak diketahui ({code})", jenis, confv, [note])

    # 6) meniru model terkenal (klon) / tidak dikenali
    if CLONE_PATTERNS.search(code):
        return _result("", f"tidak diketahui ({code})", "phone", 30,
                       ["nama menyerupai model merek besar -> indikasi perangkat klon/replika",
                        "tidak ada di katalog Google Play"])
    note = "tidak ada di katalog Google Play maupun aturan pola"
    if re.fullmatch(r"[a-z]{4,}", code.strip().lower()):
        note += ("; berbentuk satu kata khas kode internal OEM (mis. Xiaomi/Motorola/"
                 "Samsung), tetapi mereknya tidak dapat dipastikan")
    return _result("", "tidak diketahui", "unknown", 12, [note])


def _other_variants(cands: list[dict], brand: str) -> list[tuple[str, dict]]:
    out, seen = [], {(brand, clean_model_name(cands[0]["model_name"]))}
    for row in cands[1:]:
        b = canonical_brand(row["brand"], row["manufacturer"])
        key = (b, clean_model_name(row["model_name"]))
        if key in seen:
            continue
        seen.add(key)
        out.append((b, row))
    return out[:3]


def guess_type_from_screen(screen: str, code: str) -> str:
    """Tebak jenis dari resolusi layar bila katalog tidak menyebutkannya."""
    m = re.match(r"(\d+)\s*x\s*(\d+)", screen or "")
    if m:
        w, h = int(m.group(1)), int(m.group(2))
        low, high = sorted((w, h))
        if high and abs(w - h) <= high * 0.12:
            return "watch"
        if low >= 600 and high / low <= 1.45:
            return "tablet"
        return "phone"
    low = code.lower()
    if re.search(r"(pad|tab)", low):
        return "tablet"
    if re.search(r"(watch|wear)", low):
        return "watch"
    if re.search(r"(box|tv)", low):
        return "tv box / embedded"
    return "phone"


def _result(brand: str, nama: str, jenis: str, conf: int, notes: list[str]) -> dict:
    return {
        "nama_device": nama,
        "brand": brand or "tidak diketahui",
        "os": "android",
        "jenis": jenis,
        "keyakinan": max(0, min(100, int(round(conf)))),
        "catatan": "; ".join(n for n in notes if n),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--lookup", type=Path, default=DEFAULT_LOOKUP)
    ap.add_argument("--catalog", type=Path, help="katalog Google Play penuh (CSV)")
    ap.add_argument("--build-lookup", action="store_true",
                    help="bangun ulang data/device_catalog_lookup.csv dari --catalog")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    with args.input.open(encoding="utf-8-sig", newline="") as fh:
        raw_rows = list(csv.DictReader(fh))
    codes = [(r.get("Device") or "").strip() for r in raw_rows]

    if args.build_lookup:
        if not args.catalog:
            ap.error("--build-lookup memerlukan --catalog")
        build_lookup(args.catalog, args.lookup, set(codes))
        return 0

    if not args.lookup.exists():
        ap.error(f"lookup tidak ditemukan: {args.lookup} "
                 f"(buat dengan --catalog FILE --build-lookup)")
    lookup = load_lookup(args.lookup)

    out_rows = []
    for i, (raw, code) in enumerate(zip(raw_rows, codes)):
        res = classify(code, lookup)
        out_rows.append({
            "no": (raw.get("") or str(i)).strip(),
            "device": code,
            "nama_device": res["nama_device"],
            "brand": res["brand"],
            "os": "unknown" if code.strip().lower() == "unknown" else res["os"],
            "jenis": res["jenis"],
            "keyakinan": res["keyakinan"],
            "catatan": res["catatan"],
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["no", "device", "nama_device", "brand",
                                                "os", "jenis", "keyakinan", "catatan"])
        writer.writeheader()
        writer.writerows(out_rows)

    if not args.quiet:
        confs = [r["keyakinan"] for r in out_rows]
        buckets = Counter("tinggi (>=90)" if c >= 90 else
                          "sedang (70-89)" if c >= 70 else
                          "rendah (40-69)" if c >= 40 else "sangat rendah (<40)"
                          for c in confs)
        print(f"output: {args.output}  ({len(out_rows)} baris)")
        print(f"rata-rata keyakinan: {sum(confs)/len(confs):.1f}")
        for k in ("tinggi (>=90)", "sedang (70-89)", "rendah (40-69)", "sangat rendah (<40)"):
            print(f"  {k:20} {buckets.get(k, 0):5} baris")
        print("\ntop 15 merek:")
        for b, n in Counter(r["brand"] for r in out_rows).most_common(15):
            print(f"  {b:20} {n:5}")
        print("\njenis:")
        for t, n in Counter(r["jenis"] for r in out_rows).most_common():
            print(f"  {t:20} {n:5}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
