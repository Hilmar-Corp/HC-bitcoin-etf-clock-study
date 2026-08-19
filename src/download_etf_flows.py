from __future__ import annotations

import re
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import requests

URL = "https://farside.co.uk/bitcoin-etf-flow-all-data/"

RAW = Path("data/raw/etf_flows")
PROC = Path("data/processed")

RAW.mkdir(parents=True, exist_ok=True)
PROC.mkdir(parents=True, exist_ok=True)

EXPECTED = [
    "date",
    "IBIT",
    "FBTC",
    "BITB",
    "ARKB",
    "BTCO",
    "EZBC",
    "BRRR",
    "HODL",
    "BTCW",
    "MSBT",
    "GBTC",
    "BTC",
    "Total",
]

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/150 Safari/537.36"
    )
}

print("[GET] Farside ETF flows")

r = requests.get(URL, headers=headers, timeout=60)
r.raise_for_status()

html = r.text

(RAW / "farside_raw.html").write_text(
    html,
    encoding="utf-8",
)

# Read every HTML table.
tables = pd.read_html(StringIO(html))

print(f"[INFO] tables detected: {len(tables)}")

candidate = None

for i, table in enumerate(tables):
    flat = table.copy()

    # Flatten MultiIndex headers if needed.
    if isinstance(flat.columns, pd.MultiIndex):
        flat.columns = [
            " ".join(
                str(x).strip()
                for x in col
                if str(x) != "nan"
            ).strip()
            for col in flat.columns
        ]
    else:
        flat.columns = [
            str(c).strip()
            for c in flat.columns
        ]

    blob = " ".join(flat.columns).upper()

    # The all-data table should identify several canonical tickers.
    if (
        "IBIT" in blob
        and "FBTC" in blob
        and "GBTC" in blob
        and len(flat.columns) >= 13
    ):
        candidate = flat
        print(f"[SELECT] table {i}")
        print("[COLUMNS]", flat.columns.tolist())
        break

if candidate is None:
    # Fallback: parse tables structurally based on rows/column count.
    for i, table in enumerate(tables):
        if table.shape[1] == len(EXPECTED):
            tmp = table.copy()
            first_col = tmp.iloc[:, 0].astype(str)

            date_hits = first_col.str.match(
                r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}$",
                na=False,
            ).sum()

            if date_hits >= 20:
                candidate = tmp
                candidate.columns = EXPECTED
                print(f"[SELECT FALLBACK] table {i}")
                break

if candidate is None:
    raise RuntimeError(
        "Could not identify Farside ETF flow table."
    )

# If column count is correct but names are ugly/images, impose canonical schema.
if candidate.shape[1] != len(EXPECTED):
    raise RuntimeError(
        f"Unexpected column count: {candidate.shape[1]} "
        f"(expected {len(EXPECTED)})"
    )

candidate.columns = EXPECTED


def parse_flow(x):
    """
    Farside convention:
      111.7      -> +111.7
      (95.1)     -> -95.1
      1,119.9    -> +1119.9
      -          -> NaN
      blank      -> NaN
    """
    if pd.isna(x):
        return np.nan

    s = str(x).strip()

    if s in {"", "-", "–", "—", "nan", "None"}:
        return np.nan

    s = s.replace(",", "")

    negative = (
        s.startswith("(")
        and s.endswith(")")
    )

    if negative:
        s = s[1:-1]

    # Strip anything unexpected besides numeric syntax.
    s = re.sub(r"[^0-9.\-]", "", s)

    if s == "":
        return np.nan

    value = float(s)

    return -value if negative else value


df = candidate.copy()

# Keep only actual dated observations.
df["date"] = pd.to_datetime(
    df["date"],
    format="%d %b %Y",
    errors="coerce",
)

df = df[df["date"].notna()].copy()

flow_cols = EXPECTED[1:]

for col in flow_cols:
    df[col] = df[col].map(parse_flow)

df = (
    df.sort_values("date")
      .drop_duplicates("date", keep="last")
      .reset_index(drop=True)
)

# Start of US spot ETF sample.
df = df[df["date"] >= pd.Timestamp("2024-01-11")].copy()

# A row can exist before all underlying fund values have been published.
# Main research panel only includes dates with at least one published fund flow.
fund_cols = [
    "IBIT",
    "FBTC",
    "BITB",
    "ARKB",
    "BTCO",
    "EZBC",
    "BRRR",
    "HODL",
    "BTCW",
    "MSBT",
    "GBTC",
    "BTC",
]

df["n_reported"] = df[fund_cols].notna().sum(axis=1)
df["n_missing"] = df[fund_cols].isna().sum(axis=1)

# Reconstructed total from published components only.
df["total_reconstructed"] = df[fund_cols].sum(
    axis=1,
    min_count=1,
)

df["total_diff"] = (
    df["Total"] - df["total_reconstructed"]
)

# Incomplete live rows are not included in the frozen analysis dataset.
complete = df["n_reported"] > 0

research = df[complete].copy()

raw_csv = RAW / "farside_flows_parsed_all.csv"
proc_parquet = PROC / "bitcoin_etf_flows_daily.parquet"
proc_csv = PROC / "bitcoin_etf_flows_daily.csv"

df.to_csv(raw_csv, index=False)
research.to_parquet(proc_parquet, index=False)
research.to_csv(proc_csv, index=False)

print()
print("===== FARSIDE FLOW DATA =====")
print("All dated rows:      ", len(df))
print("Research rows:       ", len(research))
print("First date:          ", research["date"].min())
print("Last usable date:    ", research["date"].max())

print()
print("===== LAST 10 ROWS =====")
print(
    research[
        [
            "date",
            "IBIT",
            "FBTC",
            "GBTC",
            "BTC",
            "Total",
            "n_reported",
            "total_diff",
        ]
    ]
    .tail(10)
    .to_string(index=False)
)

print()
print("===== TOTAL RECONCILIATION =====")

diff = research["total_diff"].dropna()

print("Rows with published Total:", len(diff))
print(
    "Exact-ish reconciliation:",
    int((diff.abs() <= 0.15).sum()),
)
print(
    "Max abs diff:",
    diff.abs().max(),
)

print()
print("Saved ->", proc_parquet)
