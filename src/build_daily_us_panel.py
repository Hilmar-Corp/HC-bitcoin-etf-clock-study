
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal

SOURCE = Path("data/processed/btc_5m_etf_clock.parquet")
TARGET = Path("data/processed/btc_daily_nyse_panel.parquet")

START_DATE = "2022-01-11"
END_DATE = "2026-01-10"
ETF_START_DATE = pd.Timestamp("2024-01-11").date()

required = [
    "timestamp_utc",
    "open",
    "high",
    "low",
    "close",
    "quote_volume",
    "n_trades",
    "log_return",
    "abs_log_return",
    "sq_log_return",
]

df = pd.read_parquet(
    SOURCE,
    columns=required,
)

df["timestamp_utc"] = pd.to_datetime(
    df["timestamp_utc"],
    utc=True,
)

df = df.sort_values(
    "timestamp_utc"
).reset_index(drop=True)

df["timestamp_ny"] = (
    df["timestamp_utc"]
    .dt.tz_convert("America/New_York")
)

df["date_ny"] = (
    df["timestamp_ny"]
    .dt.date
)

nyse = mcal.get_calendar("NYSE")

schedule = nyse.schedule(
    start_date=START_DATE,
    end_date=END_DATE,
).reset_index()

schedule = schedule.rename(
    columns={
        schedule.columns[0]: "session_date"
    }
)

schedule["session_date"] = (
    pd.to_datetime(schedule["session_date"])
    .dt.date
)

schedule["market_open"] = pd.to_datetime(
    schedule["market_open"],
    utc=True,
)

schedule["market_close"] = pd.to_datetime(
    schedule["market_close"],
    utc=True,
)

schedule["session_period"] = np.where(
    schedule["session_date"] < ETF_START_DATE,
    "pre_etf",
    "post_etf",
)

schedule["expected_us_bars"] = (
    (
        schedule["market_close"]
        - schedule["market_open"]
    )
    .dt.total_seconds()
    .div(300)
    .astype(int)
)

df = df.merge(
    schedule[
        [
            "session_date",
            "market_open",
            "market_close",
            "session_period",
            "expected_us_bars",
        ]
    ],
    left_on="date_ny",
    right_on="session_date",
    how="left",
    validate="many_to_one",
)

df["is_nyse_day"] = (
    df["session_date"].notna()
)

df["in_us_session"] = (
    df["is_nyse_day"]
    & (df["timestamp_utc"] >= df["market_open"])
    & (df["timestamp_utc"] < df["market_close"])
)

df["us_quote_volume"] = np.where(
    df["in_us_session"],
    df["quote_volume"],
    0.0,
)

df["us_trades"] = np.where(
    df["in_us_session"],
    df["n_trades"],
    0.0,
)

df["us_variance"] = np.where(
    df["in_us_session"],
    df["sq_log_return"],
    0.0,
)

df["us_abs_return"] = np.where(
    df["in_us_session"],
    df["abs_log_return"],
    0.0,
)

df["us_log_return"] = np.where(
    df["in_us_session"],
    df["log_return"],
    0.0,
)

x = df[df["is_nyse_day"]].copy()

daily = (
    x.groupby(
        [
            "session_date",
            "session_period",
        ],
        as_index=False,
    )
    .agg(
        market_open=("market_open", "first"),
        market_close=("market_close", "first"),
        expected_us_bars=("expected_us_bars", "first"),

        btc_open=("open", "first"),
        btc_close=("close", "last"),

        total_quote_volume=("quote_volume", "sum"),
        us_quote_volume=("us_quote_volume", "sum"),

        total_trades=("n_trades", "sum"),
        us_trades=("us_trades", "sum"),

        total_variance=("sq_log_return", "sum"),
        us_variance=("us_variance", "sum"),

        total_abs_return=("abs_log_return", "sum"),
        us_abs_return=("us_abs_return", "sum"),

        daily_log_return=("log_return", "sum"),
        us_session_log_return=("us_log_return", "sum"),

        bars=("timestamp_utc", "size"),
        us_bars=("in_us_session", "sum"),
    )
)

daily = daily.rename(
    columns={
        "session_period": "period"
    }
)

daily["date"] = pd.to_datetime(
    daily["session_date"]
)

daily["us_volume_share"] = (
    daily["us_quote_volume"]
    / daily["total_quote_volume"]
)

daily["us_trade_share"] = (
    daily["us_trades"]
    / daily["total_trades"]
)

daily["us_variance_share"] = (
    daily["us_variance"]
    / daily["total_variance"]
)

daily["us_abs_return_share"] = (
    daily["us_abs_return"]
    / daily["total_abs_return"]
)

daily["bar_diff"] = (
    daily["us_bars"]
    - daily["expected_us_bars"]
)

print("Calendar sessions:", len(schedule))
print("Panel rows:", len(daily))
print("Unique dates:", daily["date"].nunique())
print("Duplicate dates:", daily["date"].duplicated().sum())
print("Zero US bars:", int((daily["us_bars"] <= 0).sum()))
print("Bar mismatches:", int((daily["bar_diff"] != 0).sum()))

print()
print("Periods:")
print(daily["period"].value_counts())

print()
print("Session lengths:")
print(
    daily[
        ["expected_us_bars", "us_bars"]
    ]
    .value_counts()
    .sort_index()
)

assert len(schedule) == 1003
assert len(daily) == 1003
assert daily["date"].nunique() == 1003
assert daily["date"].duplicated().sum() == 0
assert (daily["us_bars"] > 0).all()

# ============================================================
# DATA-QUALITY EXCLUSION
#
# 2023-03-24 contains the unique >5m discontinuity in the
# Binance 5m source over the research sample.
#
# Because the gap affects both:
#   - the NYSE-session numerator
#   - the full-day denominator
#
# the entire NYSE date is excluded rather than interpolated.
# ============================================================

bad_sessions = daily[
    daily["bar_diff"] != 0
].copy()

if len(bad_sessions) != 1:
    raise RuntimeError(
        f"Expected exactly one incomplete NYSE session; "
        f"found {len(bad_sessions)}"
    )

bad_date = bad_sessions["date"].iloc[0]

if bad_date != pd.Timestamp("2023-03-24"):
    raise RuntimeError(
        f"Unexpected incomplete session: {bad_date}"
    )

exclusions = bad_sessions[
    [
        "date",
        "period",
        "market_open",
        "market_close",
        "expected_us_bars",
        "us_bars",
        "bar_diff",
    ]
].copy()

exclusions["reason"] = (
    "Unique source-data gap >5m; "
    "session and 24h denominator incomplete; "
    "no interpolation."
)

Path("outputs/tables").mkdir(
    parents=True,
    exist_ok=True,
)

exclusions.to_csv(
    "outputs/tables/excluded_sessions.csv",
    index=False,
)

print()
print("EXCLUDED SESSION:")
print(
    exclusions.to_string(index=False)
)

daily = daily[
    daily["date"] != bad_date
].copy()

assert len(daily) == 1002
assert daily["date"].nunique() == 1002
assert daily["date"].duplicated().sum() == 0

jan10 = daily.loc[
    daily["date"] == pd.Timestamp("2024-01-10"),
    "period",
]

jan11 = daily.loc[
    daily["date"] == pd.Timestamp("2024-01-11"),
    "period",
]

assert jan10.iloc[0] == "pre_etf"
assert jan11.iloc[0] == "post_etf"

keep = [
    "date",
    "session_date",
    "period",
    "market_open",
    "market_close",
    "expected_us_bars",
    "us_bars",
    "bars",
    "btc_open",
    "btc_close",
    "total_quote_volume",
    "us_quote_volume",
    "us_volume_share",
    "total_trades",
    "us_trades",
    "us_trade_share",
    "total_variance",
    "us_variance",
    "us_variance_share",
    "total_abs_return",
    "us_abs_return",
    "us_abs_return_share",
    "daily_log_return",
    "us_session_log_return",
]

daily = (
    daily[keep]
    .sort_values("date")
    .reset_index(drop=True)
)

daily.to_parquet(
    TARGET,
    index=False,
)

print()
print("PASS_NYSE_PANEL")
