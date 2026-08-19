from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

PATH = "data/processed/btc_5m_etf_clock.parquet"

OUT_TABLE = Path("outputs/tables")
OUT_TABLE.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(PATH)

# Exclude incomplete boundary NY dates from main daily panel.
counts = df.groupby("date_ny").size()
complete_dates = counts[counts >= 280].index
df = df[df["date_ny"].isin(complete_dates)].copy()

df["us_quote_volume"] = np.where(
    df["us_cash_session"],
    df["quote_volume"],
    0.0,
)

df["us_n_trades"] = np.where(
    df["us_cash_session"],
    df["n_trades"],
    0.0,
)

df["us_sq_return"] = np.where(
    df["us_cash_session"],
    df["sq_log_return"],
    0.0,
)

daily = (
    df.groupby(["date_ny", "period"], as_index=False)
      .agg(
          total_quote_volume=("quote_volume", "sum"),
          us_quote_volume=("us_quote_volume", "sum"),
          total_trades=("n_trades", "sum"),
          us_trades=("us_n_trades", "sum"),
          total_variance=("sq_log_return", "sum"),
          us_variance=("us_sq_return", "sum"),
      )
)

daily["us_volume_share"] = (
    daily["us_quote_volume"] / daily["total_quote_volume"]
)

daily["us_trade_share"] = (
    daily["us_trades"] / daily["total_trades"]
)

daily["us_variance_share"] = (
    daily["us_variance"] / daily["total_variance"]
)

daily = daily.replace([np.inf, -np.inf], np.nan)

metrics = [
    "us_volume_share",
    "us_trade_share",
    "us_variance_share",
]

rows = []

for metric in metrics:
    pre = daily.loc[
        daily["period"] == "pre_etf", metric
    ].dropna()

    post = daily.loc[
        daily["period"] == "post_etf", metric
    ].dropna()

    stat, p = mannwhitneyu(
        pre,
        post,
        alternative="two-sided",
    )

    rows.append(
        {
            "metric": metric,
            "pre_n": len(pre),
            "post_n": len(post),
            "pre_mean": pre.mean(),
            "post_mean": post.mean(),
            "pre_median": pre.median(),
            "post_median": post.median(),
            "delta_median_pp": (
                post.median() - pre.median()
            ) * 100,
            "mann_whitney_u": stat,
            "p_value_raw": p,
        }
    )

summary = pd.DataFrame(rows)

daily.to_parquet(
    OUT_TABLE / "daily_us_clock.parquet",
    index=False,
)

summary.to_csv(
    OUT_TABLE / "pre_post_us_clock.csv",
    index=False,
)

print("\n===== PRE / POST ETF =====")
print(
    summary.to_string(
        index=False,
        float_format=lambda x: f"{x:.6f}",
    )
)

print("\n===== MEDIANS (%) =====")
for metric in metrics:
    x = summary[summary.metric == metric].iloc[0]
    print(
        f"{metric:20s} "
        f"PRE={100*x.pre_median:6.2f}% "
        f"POST={100*x.post_median:6.2f}% "
        f"DELTA={x.delta_median_pp:+6.2f} pp"
    )
