from pathlib import Path

import pandas as pd
import yfinance as yf

OUT_RAW = Path("data/raw/etf_market")
OUT_PROC = Path("data/processed")

OUT_RAW.mkdir(parents=True, exist_ok=True)
OUT_PROC.mkdir(parents=True, exist_ok=True)

END = "2026-01-11"

# Cohorte effectivement exploitable.
# DEFI est volontairement démarré lors de sa conversion spot.
# BTC = Grayscale Bitcoin Mini Trust, lancé plus tard.
UNIVERSE = {
    "IBIT": "2024-01-11",
    "FBTC": "2024-01-11",
    "BITB": "2024-01-11",
    "ARKB": "2024-01-11",
    "BTCO": "2024-01-11",
    "EZBC": "2024-01-11",
    "BRRR": "2024-01-11",
    "HODL": "2024-01-11",
    "BTCW": "2024-01-11",
    "GBTC": "2024-01-11",
    "DEFI": "2024-03-27",
    "BTC":  "2024-07-31",
}

frames = []

for ticker, start in UNIVERSE.items():
    print(f"[GET] {ticker} {start} -> {END}")

    df = yf.download(
        ticker,
        start=start,
        end=END,
        auto_adjust=False,
        actions=False,
        progress=False,
        threads=False,
    )

    if df.empty:
        print(f"[WARN] no data: {ticker}")
        continue

    # yfinance peut retourner un MultiIndex.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()

    rename = {
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
    }
    df = df.rename(columns=rename)

    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df["ticker"] = ticker
    df["spot_start"] = pd.Timestamp(start)

    # Simple mesure du notionnel négocié.
    # Approximation car close * shares ≠ exact dollar volume transactionnel.
    df["dollar_volume_proxy"] = df["close"] * df["volume"]

    keep = [
        "date",
        "ticker",
        "spot_start",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "dollar_volume_proxy",
    ]

    df = df[keep].copy()

    df.to_csv(
        OUT_RAW / f"{ticker}_daily.csv",
        index=False,
    )

    frames.append(df)

if not frames:
    raise RuntimeError("No ETF data downloaded.")

all_etf = (
    pd.concat(frames, ignore_index=True)
      .sort_values(["date", "ticker"])
      .reset_index(drop=True)
)

all_etf.to_parquet(
    OUT_PROC / "bitcoin_etf_daily_market.parquet",
    index=False,
)

# Agrégation de toute la couche ETF disponible à chaque date.
daily = (
    all_etf.groupby("date", as_index=False)
    .agg(
        etf_share_volume=("volume", "sum"),
        etf_dollar_volume_proxy=("dollar_volume_proxy", "sum"),
        active_etfs=("ticker", "nunique"),
    )
)

daily.to_parquet(
    OUT_PROC / "bitcoin_etf_daily_aggregate.parquet",
    index=False,
)

print()
print("===== ETF DATASET =====")
print(all_etf.groupby("ticker").agg(
    first=("date", "min"),
    last=("date", "max"),
    observations=("date", "size"),
))

print()
print("Total rows:", len(all_etf))
print("Saved -> data/processed/bitcoin_etf_daily_market.parquet")
print("Saved -> data/processed/bitcoin_etf_daily_aggregate.parquet")
