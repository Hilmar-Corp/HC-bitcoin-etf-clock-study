
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import mannwhitneyu

BTC_PATH = Path(
    "data/processed/btc_daily_nyse_panel.parquet"
)

MASTER_PATH = Path(
    "data/processed/btc_etf_master_panel.parquet"
)

OUT = Path("outputs/tables")
OUT.mkdir(parents=True, exist_ok=True)

BREAK = pd.Timestamp("2024-01-11")


# ============================================================
# HELPERS
# ============================================================

def hac_post_test(df, metric, maxlags=10):

    x = df[
        ["period", metric]
    ].dropna().copy()

    x["post"] = (
        x["period"] == "post_etf"
    ).astype(int)

    X = sm.add_constant(
        x[["post"]]
    )

    model = sm.OLS(
        x[metric],
        X,
    ).fit(
        cov_type="HAC",
        cov_kwds={
            "maxlags": maxlags
        },
    )

    beta = model.params["post"]
    se = model.bse["post"]
    p = model.pvalues["post"]

    return {
        "beta": beta,
        "se": se,
        "p": p,
        "lo": beta - 1.96 * se,
        "hi": beta + 1.96 * se,
        "n": int(model.nobs),
    }


def zscore(x):
    return (
        x - x.mean()
    ) / x.std(ddof=0)


# ============================================================
# LOAD BTC
# ============================================================

btc = pd.read_parquet(
    BTC_PATH
).copy()

btc["date"] = pd.to_datetime(
    btc["date"]
)

btc = (
    btc.sort_values("date")
    .reset_index(drop=True)
)

assert len(btc) == 1002


# ============================================================
# 1. WINDOW ROBUSTNESS
# ============================================================

print()
print("============================================================")
print("1. WINDOW ROBUSTNESS")
print("============================================================")

metrics = [
    "us_volume_share",
    "us_trade_share",
    "us_variance_share",
    "us_abs_return_share",
]

window_rows = []

for months in [
    6,
    12,
    18,
    24,
]:

    start = (
        BREAK
        - pd.DateOffset(months=months)
    )

    end = (
        BREAK
        + pd.DateOffset(months=months)
    )

    x = btc[
        (btc["date"] >= start)
        & (btc["date"] < end)
    ].copy()

    print()
    print(
        f"----- ±{months} MONTHS -----"
    )

    print(
        "PRE:",
        (x["period"] == "pre_etf").sum(),
        "POST:",
        (x["period"] == "post_etf").sum(),
    )

    for metric in metrics:

        pre = x.loc[
            x["period"] == "pre_etf",
            metric,
        ].dropna()

        post = x.loc[
            x["period"] == "post_etf",
            metric,
        ].dropna()

        delta = (
            post.median()
            - pre.median()
        ) * 100

        u, p = mannwhitneyu(
            pre,
            post,
            alternative="two-sided",
        )

        hac = hac_post_test(
            x,
            metric,
        )

        print(
            f"{metric:24s} "
            f"median_delta={delta:+6.2f} pp "
            f"HAC={100*hac['beta']:+6.2f} pp "
            f"p={hac['p']:.5g}"
        )

        window_rows.append({
            "months": months,
            "metric": metric,
            "n_pre": len(pre),
            "n_post": len(post),
            "median_delta_pp": delta,
            "mw_p": p,
            "hac_beta_pp": hac["beta"] * 100,
            "hac_low_pp": hac["lo"] * 100,
            "hac_high_pp": hac["hi"] * 100,
            "hac_p": hac["p"],
        })


pd.DataFrame(
    window_rows
).to_csv(
    OUT / "window_robustness.csv",
    index=False,
)


# ============================================================
# 2. INTERRUPTED TIME SERIES
#
# Y = time trend + post level shift + post slope change
#
# Still descriptive, but checks whether the result is simply
# continuation of an existing trend.
# ============================================================

print()
print("============================================================")
print("2. INTERRUPTED TIME SERIES")
print("============================================================")

its_rows = []

for metric in metrics:

    x = btc[
        ["date", "period", metric]
    ].dropna().copy()

    x = (
        x.sort_values("date")
        .reset_index(drop=True)
    )

    x["t"] = np.arange(len(x))

    breakpoint_idx = x.index[
        x["date"] >= BREAK
    ].min()

    x["post"] = (
        x["date"] >= BREAK
    ).astype(int)

    x["t_after"] = np.where(
        x["post"] == 1,
        x["t"] - breakpoint_idx,
        0,
    )

    # Standardize time to make coefficients manageable.
    x["t_z"] = zscore(
        x["t"].astype(float)
    )

    post_t = x.loc[
        x["post"] == 1,
        "t_after",
    ]

    scale = (
        post_t.std(ddof=0)
        if post_t.std(ddof=0) > 0
        else 1
    )

    x["t_after_z"] = (
        x["t_after"] / scale
    )

    X = sm.add_constant(
        x[
            [
                "t_z",
                "post",
                "t_after_z",
            ]
        ]
    )

    model = sm.OLS(
        x[metric],
        X,
    ).fit(
        cov_type="HAC",
        cov_kwds={
            "maxlags": 10
        },
    )

    beta_post = (
        model.params["post"]
        * 100
    )

    p_post = (
        model.pvalues["post"]
    )

    beta_trend = (
        model.params["t_z"]
        * 100
    )

    p_trend = (
        model.pvalues["t_z"]
    )

    beta_slope = (
        model.params["t_after_z"]
        * 100
    )

    p_slope = (
        model.pvalues["t_after_z"]
    )

    print()
    print(metric)

    print(
        f"  pre-trend: "
        f"{beta_trend:+.3f} pp "
        f"p={p_trend:.5g}"
    )

    print(
        f"  post level shift: "
        f"{beta_post:+.3f} pp "
        f"p={p_post:.5g}"
    )

    print(
        f"  post slope change: "
        f"{beta_slope:+.3f} pp "
        f"p={p_slope:.5g}"
    )

    its_rows.append({
        "metric": metric,
        "pretrend_beta_pp": beta_trend,
        "pretrend_p": p_trend,
        "post_level_beta_pp": beta_post,
        "post_level_p": p_post,
        "post_slope_beta_pp": beta_slope,
        "post_slope_p": p_slope,
    })


pd.DataFrame(
    its_rows
).to_csv(
    OUT / "interrupted_time_series.csv",
    index=False,
)


# ============================================================
# 3. PLACEBO BREAKPOINTS
#
# Use only PRE-ETF history.
#
# Candidate placebo dates are spaced by ~21 NYSE sessions.
# Compare actual absolute median shift to placebo shifts.
# ============================================================

print()
print("============================================================")
print("3. PLACEBO BREAKPOINTS")
print("============================================================")

pre_full = btc[
    btc["date"] < BREAK
].copy()

placebo_rows = []

# Avoid edges.
candidate_indices = list(
    range(
        126,
        len(pre_full) - 126,
        21,
    )
)

for metric in metrics:

    actual_pre = btc.loc[
        btc["period"] == "pre_etf",
        metric,
    ].dropna()

    actual_post = btc.loc[
        btc["period"] == "post_etf",
        metric,
    ].dropna()

    actual = (
        actual_post.median()
        - actual_pre.median()
    ) * 100

    vals = []

    for idx in candidate_indices:

        placebo_date = (
            pre_full.iloc[idx]["date"]
        )

        left = pre_full[
            pre_full["date"]
            < placebo_date
        ][metric].dropna()

        right = pre_full[
            pre_full["date"]
            >= placebo_date
        ][metric].dropna()

        if (
            len(left) < 100
            or len(right) < 100
        ):
            continue

        delta = (
            right.median()
            - left.median()
        ) * 100

        vals.append(delta)

        placebo_rows.append({
            "metric": metric,
            "placebo_date": placebo_date,
            "delta_pp": delta,
        })

    vals = np.asarray(vals)

    empirical_p = (
        1
        + np.sum(
            np.abs(vals)
            >= abs(actual)
        )
    ) / (
        1 + len(vals)
    )

    print()
    print(metric)
    print(
        f"  actual delta: {actual:+.2f} pp"
    )
    print(
        f"  placebo N: {len(vals)}"
    )
    print(
        f"  placebo median: "
        f"{np.median(vals):+.2f} pp"
    )
    print(
        f"  max |placebo|: "
        f"{np.max(np.abs(vals)):.2f} pp"
    )
    print(
        f"  empirical p: "
        f"{empirical_p:.4f}"
    )


pd.DataFrame(
    placebo_rows
).to_csv(
    OUT / "placebo_breakpoints.csv",
    index=False,
)


# ============================================================
# 4. LOAD ETF MASTER
# ============================================================

master = pd.read_parquet(
    MASTER_PATH
).copy()

master["date"] = pd.to_datetime(
    master["date"]
)

master = (
    master.sort_values("date")
    .reset_index(drop=True)
)

assert len(master) == 501


# ============================================================
# 5. LOG RATIOS
#
# Avoid bounded share outcome:
#
# log(US / non-US)
#
# epsilon is only numerical protection.
# ============================================================

eps = 1e-12

master["non_us_quote_volume"] = (
    master["total_quote_volume"]
    - master["us_quote_volume"]
)

master["non_us_trades"] = (
    master["total_trades"]
    - master["us_trades"]
)

master["non_us_variance"] = (
    master["total_variance"]
    - master["us_variance"]
)

master["non_us_abs_return"] = (
    master["total_abs_return"]
    - master["us_abs_return"]
)

master["lr_volume"] = np.log(
    (
        master["us_quote_volume"] + eps
    )
    /
    (
        master["non_us_quote_volume"] + eps
    )
)

master["lr_trades"] = np.log(
    (
        master["us_trades"] + eps
    )
    /
    (
        master["non_us_trades"] + eps
    )
)

master["lr_variance"] = np.log(
    (
        master["us_variance"] + eps
    )
    /
    (
        master["non_us_variance"] + eps
    )
)

master["lr_abs_return"] = np.log(
    (
        master["us_abs_return"] + eps
    )
    /
    (
        master["non_us_abs_return"] + eps
    )
)

master["log_turnover"] = np.log1p(
    master["etf_turnover_proxy_usd"]
)

master["log_abs_flow"] = np.log1p(
    master["etf_net_flow_musd"].abs()
)


ratio_metrics = [
    "lr_volume",
    "lr_trades",
    "lr_variance",
    "lr_abs_return",
]


# ============================================================
# 6. ETF ACTIVITY -> LOG RATIO
# ============================================================

print()
print("============================================================")
print("4. ETF ACTIVITY -> US / NON-US LOG RATIO")
print("============================================================")

ratio_rows = []

for xvar in [
    "log_abs_flow",
    "log_turnover",
]:

    print()
    print("X =", xvar)

    for metric in ratio_metrics:

        x = master[
            [xvar, metric]
        ].dropna().copy()

        x["x_z"] = zscore(
            x[xvar]
        )

        X = sm.add_constant(
            x[["x_z"]]
        )

        model = sm.OLS(
            x[metric],
            X,
        ).fit(
            cov_type="HAC",
            cov_kwds={
                "maxlags": 10
            },
        )

        beta = model.params["x_z"]
        se = model.bse["x_z"]
        p = model.pvalues["x_z"]

        lo = beta - 1.96 * se
        hi = beta + 1.96 * se

        # Approximate percentage change in US/non-US ratio:
        ratio_pct = (
            np.exp(beta) - 1
        ) * 100

        ratio_lo = (
            np.exp(lo) - 1
        ) * 100

        ratio_hi = (
            np.exp(hi) - 1
        ) * 100

        print(
            f"{metric:20s} "
            f"ratio_change={ratio_pct:+6.2f}% "
            f"CI=[{ratio_lo:+6.2f},{ratio_hi:+6.2f}] "
            f"p={p:.6g}"
        )

        ratio_rows.append({
            "x": xvar,
            "metric": metric,
            "beta_log_ratio": beta,
            "ratio_change_pct": ratio_pct,
            "ci_low_pct": ratio_lo,
            "ci_high_pct": ratio_hi,
            "p_value": p,
            "n": int(model.nobs),
        })


pd.DataFrame(
    ratio_rows
).to_csv(
    OUT / "etf_activity_log_ratio.csv",
    index=False,
)


# ============================================================
# 7. EARLY POST VS LATE POST
#
# Is US concentration a one-off launch effect or persistent?
# ============================================================

print()
print("============================================================")
print("5. EARLY POST VS LATE POST")
print("============================================================")

post = btc[
    btc["period"] == "post_etf"
].copy()

post["post_half"] = np.where(
    np.arange(len(post))
    < len(post) / 2,
    "early",
    "late",
)

for metric in metrics:

    early = post.loc[
        post["post_half"] == "early",
        metric,
    ]

    late = post.loc[
        post["post_half"] == "late",
        metric,
    ]

    delta = (
        late.median()
        - early.median()
    ) * 100

    _, p = mannwhitneyu(
        early,
        late,
        alternative="two-sided",
    )

    print(
        f"{metric:24s} "
        f"EARLY={100*early.median():6.2f}% "
        f"LATE={100*late.median():6.2f}% "
        f"DELTA={delta:+6.2f} pp "
        f"p={p:.6g}"
    )


print()
print("PASS_ROBUSTNESS_BATTERY")
