from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("data/raw/binance")
OUT = Path("data/processed")
OUT.mkdir(parents=True, exist_ok=True)

SYMBOL = "BTCUSDT"
INTERVAL = "5m"

START = pd.Timestamp("2022-01-11 00:00:00", tz="UTC")
BREAK = pd.Timestamp("2024-01-11 00:00:00", tz="UTC")
END = pd.Timestamp("2026-01-11 00:00:00", tz="UTC")

COLS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume_btc",
    "close_time",
    "quote_volume",
    "n_trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
    "ignore",
]

NUMERIC_COLS = [
    "open",
    "high",
    "low",
    "close",
    "volume_btc",
    "quote_volume",
    "n_trades",
    "taker_buy_base_volume",
    "taker_buy_quote_volume",
]


def timestamp_unit(values: pd.Series) -> str:
    """
    Binance Spot archive timestamps:
    historically ms, microseconds for newer archive data.
    Detect from magnitude rather than hard-coding a date.
    """
    x = pd.to_numeric(values, errors="coerce").dropna()

    if x.empty:
        raise ValueError("No usable timestamps.")

    med = float(x.median())

    if med > 1e14:
        return "us"
    return "ms"


frames = []

files = sorted(RAW.glob(f"{SYMBOL}-{INTERVAL}-*.zip"))

if not files:
    raise FileNotFoundError("No Binance ZIP archives found.")

for path in files:
    print(f"[READ] {path.name}")

    with zipfile.ZipFile(path) as zf:
        csv_names = [n for n in zf.namelist() if n.endswith(".csv")]

        if len(csv_names) != 1:
            raise RuntimeError(
                f"Expected exactly one CSV in {path.name}, got {csv_names}"
            )

        with zf.open(csv_names[0]) as f:
            df = pd.read_csv(
                f,
                header=None,
                names=COLS,
                dtype=str,
            )

    # Defensive handling if an archive ever contains a header row.
    df["open_time"] = pd.to_numeric(df["open_time"], errors="coerce")
    df = df[df["open_time"].notna()].copy()

    unit = timestamp_unit(df["open_time"])
    df["timestamp_utc"] = pd.to_datetime(
        df["open_time"].astype("int64"),
        unit=unit,
        utc=True,
    )

    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    frames.append(df)

df = pd.concat(frames, ignore_index=True)

df = df[
    (df["timestamp_utc"] >= START)
    & (df["timestamp_utc"] < END)
].copy()

df = df.sort_values("timestamp_utc").reset_index(drop=True)

# Integrity
if df["timestamp_utc"].duplicated().any():
    dup = df.loc[df["timestamp_utc"].duplicated(), "timestamp_utc"].head()
    raise RuntimeError(f"Duplicate timestamps detected:\n{dup}")

if (df["close"] <= 0).any():
    raise RuntimeError("Non-positive BTC prices detected.")

# NY timezone: DST handled automatically.
df["timestamp_ny"] = df["timestamp_utc"].dt.tz_convert("America/New_York")

df["date_ny"] = df["timestamp_ny"].dt.date
df["hour_ny"] = df["timestamp_ny"].dt.hour
df["minute_ny"] = df["timestamp_ny"].dt.minute

df["minute_of_day_ny"] = (
    df["hour_ny"] * 60 + df["minute_ny"]
)

# Main treatment indicator
df["period"] = np.where(
    df["timestamp_utc"] < BREAK,
    "pre_etf",
    "post_etf",
)

# 09:30 <= NY time < 16:00
minute = df["minute_of_day_ny"]

df["us_cash_session"] = (
    (minute >= 9 * 60 + 30)
    & (minute < 16 * 60)
    & (df["timestamp_ny"].dt.dayofweek < 5)
)

# Returns
df["log_return"] = np.log(df["close"]).diff()
df["abs_log_return"] = df["log_return"].abs()
df["sq_log_return"] = df["log_return"] ** 2

# Buy-side share proxy
df["taker_buy_share"] = (
    df["taker_buy_quote_volume"] / df["quote_volume"]
).replace([np.inf, -np.inf], np.nan)

keep = [
    "timestamp_utc",
    "timestamp_ny",
    "date_ny",
    "period",
    "hour_ny",
    "minute_ny",
    "minute_of_day_ny",
    "us_cash_session",
    "open",
    "high",
    "low",
    "close",
    "volume_btc",
    "quote_volume",
    "n_trades",
    "taker_buy_quote_volume",
    "taker_buy_share",
    "log_return",
    "abs_log_return",
    "sq_log_return",
]

df = df[keep]

target = OUT / "btc_5m_etf_clock.parquet"
df.to_parquet(target, index=False)

print()
print("===== DATASET =====")
print(f"Rows:       {len(df):,}")
print(f"Start UTC:  {df.timestamp_utc.min()}")
print(f"End UTC:    {df.timestamp_utc.max()}")
print()
print(df["period"].value_counts())
print()
print(f"Saved -> {target}")
