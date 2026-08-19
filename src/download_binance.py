from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

SYMBOL = "BTCUSDT"
INTERVAL = "5m"

START = pd.Timestamp("2022-01-01")
END = pd.Timestamp("2026-01-31")

BASE = "https://data.binance.vision/data/spot/monthly/klines"
OUT = Path("data/raw/binance")
OUT.mkdir(parents=True, exist_ok=True)

months = pd.period_range(START, END, freq="M")

session = requests.Session()

for month in months:
    ym = month.strftime("%Y-%m")
    filename = f"{SYMBOL}-{INTERVAL}-{ym}.zip"
    url = f"{BASE}/{SYMBOL}/{INTERVAL}/{filename}"
    target = OUT / filename

    if target.exists() and target.stat().st_size > 0:
        print(f"[SKIP] {filename}")
        continue

    print(f"[GET ] {url}")

    r = session.get(url, timeout=60)

    if r.status_code == 404:
        print(f"[MISS] {filename}")
        continue

    r.raise_for_status()

    # Validate archive before writing
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise RuntimeError(f"Corrupted member in {filename}: {bad}")

    target.write_bytes(r.content)
    print(f"[OK  ] {filename} ({target.stat().st_size / 1e6:.1f} MB)")
