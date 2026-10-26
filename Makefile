# Perintah singkat untuk pengembangan Activity Logger
PYTHON ?= python3

.PHONY: help run test lint demo demo-clean install clean

help:
	@echo "make run        - jalankan aplikasi"
	@echo "make test       - jalankan semua tes"
	@echo "make lint       - cek statis dengan pyflakes"
	@echo "make demo       - isi data contoh (60 kegiatan)"
	@echo "make install    - pasang aplikasi + dependensi (pip install -e .)"
	@echo "make clean      - hapus cache Python"

run:
	$(PYTHON) run.py

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m pyflakes activity_logger run.py scripts

demo:
	$(PYTHON) scripts/seed_demo.py --force --count 60

install:
	$(PYTHON) -m pip install -e .

clean:
	rm -rf .pytest_cache __pycache__ */__pycache__ */*/__pycache__ */*/*/__pycache__
