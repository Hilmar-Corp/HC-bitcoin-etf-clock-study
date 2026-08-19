
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

# ============================================================
# CONFIG
# ============================================================

BTC_PATH = Path(
    "data/processed/btc_daily_nyse_panel.parquet"
)

FLOW_PATH = Path(
    "data/processed/bitcoin_etf_flows_daily.parquet"
)

RAW_DIR = Path(
    "data/raw/etf_market"
)

OUT_DIR = Path(
    "data/processed"
)

RAW_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

START = "2024-01-11"

# yfinance end is exclusive.
END = "2026-01-10"

TICKERS = [
    "IBIT",
    "FBTC",
    "BITB",
    "ARKB",
    "BTCO",
    "EZBC",
    "BRRR",
    "HODL",
    "BTCW",
    "GBTC",
    "BTC",
    "MSBT",
]

parser = argparse.ArgumentParser(
    description=(
        "Build the canonical Bitcoin ETF market/master panel."
    )
)

parser.add_argument(
    "--offline",
    action="store_true",
    help=(
        "Use only existing data/raw/etf_market/<TICKER>.csv "
        "files. No yfinance request is permitted."
    ),
)

args = parser.parse_args()
OFFLINE = args.offline


# ============================================================
# 1. LOAD / ACQUIRE ETF MARKET DATA
# ============================================================

frames = []

print()
print("============================================================")

if OFFLINE:
    print("ETF MARKET DATA — OFFLINE RAW CACHE")
else:
    print("ETF MARKET DATA — ONLINE ACQUISITION")

print("============================================================")

# MSBT is part of the Farside flow universe but no usable
# yfinance market history was available in the validated
# historical run. It is therefore explicitly optional for
# the market-turnover panel.
OPTIONAL_MISSING_MARKET_TICKERS = {
    "MSBT",
}

# Frozen cache geometry from the validated 2024-01-11 ->
# 2026-01-09 market sample.
EXPECTED_OFFLINE = {
    "IBIT": ("2024-01-11", "2026-01-09", 501),
    "FBTC": ("2024-01-11", "2026-01-09", 501),
    "BITB": ("2024-01-11", "2026-01-09", 501),
    "ARKB": ("2024-01-11", "2026-01-09", 501),
    "BTCO": ("2024-01-11", "2026-01-09", 501),
    "EZBC": ("2024-01-11", "2026-01-09", 501),
    "BRRR": ("2024-01-11", "2026-01-09", 501),
    "HODL": ("2024-01-11", "2026-01-09", 501),
    "BTCW": ("2024-01-11", "2026-01-09", 501),
    "GBTC": ("2024-01-11", "2026-01-09", 501),
    "BTC": ("2024-07-31", "2026-01-09", 363),
}

for ticker in TICKERS:

    cache_path = (
        RAW_DIR /
        f"{ticker}.csv"
    )

    # --------------------------------------------------------
    # OFFLINE
    # --------------------------------------------------------

    if OFFLINE:

        print(
            f"[CACHE] {ticker}"
        )

        if not cache_path.exists():

            if (
                ticker
                in OPTIONAL_MISSING_MARKET_TICKERS
            ):
                print(
                    f"[EXPECTED MISSING] {ticker}: "
                    "no validated market cache"
                )
                continue

            raise FileNotFoundError(
                f"Required offline ETF cache missing: "
                f"{cache_path}"
            )

        x = pd.read_csv(
            cache_path
        )

    # --------------------------------------------------------
    # ONLINE
    # --------------------------------------------------------

    else:

        print(
            f"[GET] {ticker}"
        )

        try:
            x = yf.download(
                ticker,
                start=START,
                end=END,
                auto_adjust=False,
                actions=False,
                progress=False,
                threads=False,
            )

        except Exception as e:
            print(
                f"[ERROR] {ticker}: "
                f"{type(e).__name__}: {e}"
            )
            continue

        if x.empty:
            print(
                f"[MISS] {ticker}: "
                "no observations"
            )
            continue

        # yfinance may return MultiIndex columns.
        if isinstance(
            x.columns,
            pd.MultiIndex,
        ):
            x.columns = (
                x.columns
                .get_level_values(0)
            )

        x = x.reset_index()

        x = x.rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adj_close",
                "Volume": "share_volume",
            }
        )

    # --------------------------------------------------------
    # COMMON NORMALIZATION
    # --------------------------------------------------------

    required = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "share_volume",
    ]

    missing = [
        c
        for c in required
        if c not in x.columns
    ]

    if missing:
        raise RuntimeError(
            f"{ticker}: missing required columns "
            f"{missing}"
        )

    x["date"] = pd.to_datetime(
        x["date"]
    ).dt.tz_localize(None)

    x["ticker"] = ticker

    numeric = [
        "open",
        "high",
        "low",
        "close",
        "share_volume",
    ]

    for col in numeric:
        x[col] = pd.to_numeric(
            x[col],
            errors="coerce",
        )

    if x[numeric].isna().any().any():
        raise RuntimeError(
            f"{ticker}: non-numeric / missing "
            "market observations after parsing"
        )

    # Dollar turnover proxy.
    x["typical_price"] = (
        x["high"]
        + x["low"]
        + x["close"]
    ) / 3.0

    x["dollar_turnover_proxy"] = (
        x["share_volume"]
        * x["typical_price"]
    )

    x = x[
        [
            "date",
            "ticker",
            "open",
            "high",
            "low",
            "close",
            "share_volume",
            "typical_price",
            "dollar_turnover_proxy",
        ]
    ].copy()

    x = x[
        x["date"].notna()
    ].copy()

    x = x.drop_duplicates(
        subset=[
            "date",
            "ticker",
        ],
        keep="last",
    )

    x = (
        x
        .sort_values("date")
        .reset_index(drop=True)
    )

    # --------------------------------------------------------
    # STRICT OFFLINE CACHE CONTRACT
    # --------------------------------------------------------

    if OFFLINE:

        if ticker not in EXPECTED_OFFLINE:
            raise RuntimeError(
                f"{ticker}: cache exists but ticker "
                "has no validated offline contract"
            )

        expected_start, expected_end, expected_rows = (
            EXPECTED_OFFLINE[ticker]
        )

        actual_start = (
            x["date"]
            .min()
            .strftime("%Y-%m-%d")
        )

        actual_end = (
            x["date"]
            .max()
            .strftime("%Y-%m-%d")
        )

        if len(x) != expected_rows:
            raise RuntimeError(
                f"{ticker}: expected "
                f"{expected_rows} cached rows, "
                f"found {len(x)}"
            )

        if actual_start != expected_start:
            raise RuntimeError(
                f"{ticker}: expected cache start "
                f"{expected_start}, "
                f"found {actual_start}"
            )

        if actual_end != expected_end:
            raise RuntimeError(
                f"{ticker}: expected cache end "
                f"{expected_end}, "
                f"found {actual_end}"
            )

    else:
        # Acquisition may update the raw cache.
        x.to_csv(
            cache_path,
            index=False,
        )

    print(
        f"[OK] {ticker}: "
        f"{len(x)} rows | "
        f"{x['date'].min().date()} -> "
        f"{x['date'].max().date()}"
    )

    frames.append(x)


if not frames:
    raise RuntimeError(
        "No ETF market data available."
    )


if OFFLINE:

    loaded_tickers = {
        frame["ticker"].iloc[0]
        for frame in frames
    }

    expected_tickers = (
        set(TICKERS)
        - OPTIONAL_MISSING_MARKET_TICKERS
    )

    if loaded_tickers != expected_tickers:

        missing_tickers = (
            expected_tickers
            - loaded_tickers
        )

        extra_tickers = (
            loaded_tickers
            - expected_tickers
        )

        raise RuntimeError(
            "Offline ETF universe mismatch | "
            f"missing={sorted(missing_tickers)} | "
            f"extra={sorted(extra_tickers)}"
        )

    print()
    print(
        "PASS_OFFLINE_ETF_RAW_CACHE_CONTRACT"
    )


market = pd.concat(
    frames,
    ignore_index=True,
)

market = (
    market
    .sort_values(
        ["date", "ticker"]
    )
    .reset_index(drop=True)
)

market.to_parquet(
    OUT_DIR /
    "bitcoin_etf_market_daily.parquet",
    index=False,
)


# ============================================================
# 2. MARKET QA
# ============================================================

print()
print("============================================================")
print("ETF MARKET QA")
print("============================================================")

summary = (
    market
    .groupby("ticker")
    .agg(
        first_date=("date", "min"),
        last_date=("date", "max"),
        observations=("date", "size"),
        total_share_volume=(
            "share_volume",
            "sum",
        ),
    )
    .sort_index()
)

print(
    summary.to_string()
)

print()
print(
    "Downloaded tickers:",
    market["ticker"].nunique(),
)

print(
    "Total market rows:",
    len(market),
)

print(
    "Duplicate ticker-date:",
    market[
        ["date", "ticker"]
    ].duplicated().sum(),
)

assert (
    market[
        ["date", "ticker"]
    ].duplicated().sum()
    == 0
)


# ============================================================
# 3. AGGREGATE ETF MARKET ACTIVITY
# ============================================================

market_agg = (
    market
    .groupby(
        "date",
        as_index=False,
    )
    .agg(
        etf_share_volume=(
            "share_volume",
            "sum",
        ),

        etf_turnover_proxy_usd=(
            "dollar_turnover_proxy",
            "sum",
        ),

        active_etfs=(
            "ticker",
            "nunique",
        ),
    )
)

market_agg[
    "log_etf_turnover"
] = np.log1p(
    market_agg[
        "etf_turnover_proxy_usd"
    ]
)

market_agg.to_parquet(
    OUT_DIR /
    "bitcoin_etf_market_aggregate.parquet",
    index=False,
)


# ============================================================
# 4. LOAD BTC
# ============================================================

btc = pd.read_parquet(
    BTC_PATH
).copy()

btc["date"] = pd.to_datetime(
    btc["date"]
).dt.tz_localize(None)

# Post ETF only for master interaction panel.
btc_post = btc[
    btc["period"] == "post_etf"
].copy()

print()
print("============================================================")
print("BTC POST SAMPLE")
print("============================================================")

print(
    "Rows:",
    len(btc_post),
)

print(
    "Range:",
    btc_post["date"].min(),
    "->",
    btc_post["date"].max(),
)

assert len(btc_post) == 501


# ============================================================
# 5. LOAD FARSIDE
# ============================================================

flows = pd.read_parquet(
    FLOW_PATH
).copy()

flows["date"] = pd.to_datetime(
    flows["date"]
).dt.tz_localize(None)

flows = flows[
    flows["date"]
    <= btc_post["date"].max()
].copy()

flows = flows.rename(
    columns={
        "Total": "etf_net_flow_musd"
    }
)

flows["abs_etf_flow_musd"] = (
    flows[
        "etf_net_flow_musd"
    ].abs()
)

flows["log_abs_etf_flow"] = np.log1p(
    flows["abs_etf_flow_musd"]
)

print()
print("============================================================")
print("FARSIDE SAMPLE")
print("============================================================")

print(
    "Rows through BTC cutoff:",
    len(flows),
)

print(
    "Range:",
    flows["date"].min(),
    "->",
    flows["date"].max(),
)

print(
    "Duplicate dates:",
    flows["date"].duplicated().sum(),
)

assert (
    flows["date"]
    .duplicated()
    .sum()
    == 0
)


# ============================================================
# 6. MERGE BTC + FARSIDE + ETF MARKET
# ============================================================

flow_cols = [
    "date",
    "etf_net_flow_musd",
    "abs_etf_flow_musd",
    "log_abs_etf_flow",
    "IBIT",
    "FBTC",
    "BITB",
    "ARKB",
    "BTCO",
    "EZBC",
    "BRRR",
    "HODL",
    "BTCW",
    "GBTC",
    "BTC",
    "n_reported",
]

flow_cols = [
    c for c in flow_cols
    if c in flows.columns
]

master = (
    btc_post
    .merge(
        flows[flow_cols],
        on="date",
        how="left",
        validate="one_to_one",
    )
    .merge(
        market_agg,
        on="date",
        how="left",
        validate="one_to_one",
    )
)

master[
    "has_flow"
] = master[
    "etf_net_flow_musd"
].notna()

master[
    "has_market"
] = master[
    "etf_turnover_proxy_usd"
].notna()


# ============================================================
# 7. MASTER QA
# ============================================================

print()
print("============================================================")
print("MASTER PANEL QA")
print("============================================================")

print(
    "Master rows:",
    len(master),
)

print(
    "Flow matches:",
    int(master["has_flow"].sum()),
)

print(
    "Missing flows:",
    int((~master["has_flow"]).sum()),
)

print(
    "ETF market matches:",
    int(master["has_market"].sum()),
)

print(
    "Missing ETF market:",
    int((~master["has_market"]).sum()),
)

print()
print("Missing flow dates:")

print(
    master.loc[
        ~master["has_flow"],
        ["date"],
    ].to_string(
        index=False
    )
)

print()
print("Missing market dates:")

print(
    master.loc[
        ~master["has_market"],
        ["date"],
    ].to_string(
        index=False
    )
)


# ============================================================
# 8. CHECK FLOW TOTALS
# ============================================================

print()
print("============================================================")
print("FLOW DISTRIBUTION")
print("============================================================")

print(
    master[
        "etf_net_flow_musd"
    ].describe()
)

print()
print(
    "Positive flow days:",
    int(
        (
            master[
                "etf_net_flow_musd"
            ] > 0
        ).sum()
    ),
)

print(
    "Negative flow days:",
    int(
        (
            master[
                "etf_net_flow_musd"
            ] < 0
        ).sum()
    ),
)

print(
    "Zero flow days:",
    int(
        (
            master[
                "etf_net_flow_musd"
            ] == 0
        ).sum()
    ),
)


# ============================================================
# 9. MARKET DISTRIBUTION
# ============================================================

print()
print("============================================================")
print("ETF MARKET ACTIVITY")
print("============================================================")

print(
    master[
        "etf_turnover_proxy_usd"
    ].describe()
)

print()
print("Active ETF count:")
print(
    master[
        "active_etfs"
    ].value_counts(
        dropna=False
    ).sort_index()
)


# ============================================================
# 10. SAVE
# ============================================================

target = (
    OUT_DIR /
    "btc_etf_master_panel.parquet"
)

master.to_parquet(
    target,
    index=False,
)

master.to_csv(
    OUT_DIR /
    "btc_etf_master_panel.csv",
    index=False,
)

print()
print(
    "Saved ->",
    target,
)

print()
print("PASS_MASTER_PANEL")
