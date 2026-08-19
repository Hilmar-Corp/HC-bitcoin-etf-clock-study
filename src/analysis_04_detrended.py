
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from scipy.stats import spearmanr


MASTER_PATH = Path(
    "data/processed/btc_etf_master_panel.parquet"
)

BTC_PATH = Path(
    "data/processed/btc_daily_nyse_panel.parquet"
)

OUT = Path("outputs/tables")
OUT.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPERS
# ============================================================

def zscore(x):
    x = x.astype(float)

    sd = x.std(ddof=0)

    if sd == 0:
        return x * 0

    return (
        x - x.mean()
    ) / sd


def hac_model(
    df,
    y,
    xcols,
    maxlags=10,
):
    tmp = df[
        [y] + xcols
    ].dropna().copy()

    X = sm.add_constant(
        tmp[xcols]
    )

    model = sm.OLS(
        tmp[y],
        X,
    ).fit(
        cov_type="HAC",
        cov_kwds={
            "maxlags": maxlags
        },
    )

    return model


# ============================================================
# LOAD MASTER
# ============================================================

df = pd.read_parquet(
    MASTER_PATH
).copy()

df["date"] = pd.to_datetime(
    df["date"]
)

df = (
    df.sort_values("date")
    .reset_index(drop=True)
)

assert len(df) == 501


# ============================================================
# CONSTRUCT US / NON-US LOG RATIOS
# ============================================================

eps = 1e-12

df["non_us_quote_volume"] = (
    df["total_quote_volume"]
    - df["us_quote_volume"]
)

df["non_us_trades"] = (
    df["total_trades"]
    - df["us_trades"]
)

df["non_us_variance"] = (
    df["total_variance"]
    - df["us_variance"]
)

df["non_us_abs_return"] = (
    df["total_abs_return"]
    - df["us_abs_return"]
)

df["lr_volume"] = np.log(
    (df["us_quote_volume"] + eps)
    /
    (df["non_us_quote_volume"] + eps)
)

df["lr_trades"] = np.log(
    (df["us_trades"] + eps)
    /
    (df["non_us_trades"] + eps)
)

df["lr_variance"] = np.log(
    (df["us_variance"] + eps)
    /
    (df["non_us_variance"] + eps)
)

df["lr_abs_return"] = np.log(
    (df["us_abs_return"] + eps)
    /
    (df["non_us_abs_return"] + eps)
)

df["log_turnover"] = np.log1p(
    df["etf_turnover_proxy_usd"]
)

df["log_abs_flow"] = np.log1p(
    df["etf_net_flow_musd"].abs()
)

RATIOS = [
    "lr_volume",
    "lr_trades",
    "lr_variance",
    "lr_abs_return",
]


# ============================================================
# TIME VARIABLES
# ============================================================

df["t"] = np.arange(
    len(df),
    dtype=float,
)

df["t_z"] = zscore(
    df["t"]
)

df["t2_z"] = zscore(
    df["t_z"] ** 2
)

df["weekday"] = (
    df["date"].dt.dayofweek
)

weekday_dummies = pd.get_dummies(
    df["weekday"],
    prefix="dow",
    drop_first=True,
    dtype=float,
)

df = pd.concat(
    [
        df,
        weekday_dummies,
    ],
    axis=1,
)

DOW = list(
    weekday_dummies.columns
)


# ============================================================
# 1. HOW STRONGLY DOES ETF TURNOVER TREND WITH TIME?
# ============================================================

print()
print("============================================================")
print("1. ETF TURNOVER TIME TREND")
print("============================================================")

tmp = df[
    [
        "log_turnover",
        "t_z",
        "t2_z",
    ]
].copy()

model = hac_model(
    tmp,
    "log_turnover",
    [
        "t_z",
        "t2_z",
    ],
)

print(
    model.summary().tables[1]
)

rho, p = spearmanr(
    df["t"],
    df["etf_turnover_proxy_usd"],
)

print()
print(
    f"Spearman(time, ETF turnover): "
    f"rho={rho:+.4f} "
    f"p={p:.6g}"
)


# ============================================================
# 2. ETF ACTIVITY + LINEAR/QUADRATIC TIME TREND
# ============================================================

print()
print("============================================================")
print("2. TURNOVER EFFECT AFTER TIME TREND")
print("============================================================")

trend_rows = []

for xvar in [
    "log_turnover",
    "log_abs_flow",
]:

    print()
    print("X =", xvar)

    work = df.copy()

    work["x_z"] = zscore(
        work[xvar]
    )

    controls = [
        "x_z",
        "t_z",
        "t2_z",
    ] + DOW

    for metric in RATIOS:

        model = hac_model(
            work,
            metric,
            controls,
            maxlags=10,
        )

        beta = model.params["x_z"]
        se = model.bse["x_z"]
        p = model.pvalues["x_z"]

        lo = beta - 1.96 * se
        hi = beta + 1.96 * se

        pct = (
            np.exp(beta) - 1
        ) * 100

        lo_pct = (
            np.exp(lo) - 1
        ) * 100

        hi_pct = (
            np.exp(hi) - 1
        ) * 100

        print(
            f"{metric:20s} "
            f"ratio_change={pct:+7.2f}% "
            f"CI=[{lo_pct:+7.2f},{hi_pct:+7.2f}] "
            f"p={p:.6g}"
        )

        trend_rows.append({
            "family": "time_trend_control",
            "x": xvar,
            "metric": metric,
            "ratio_change_pct": pct,
            "ci_low_pct": lo_pct,
            "ci_high_pct": hi_pct,
            "p_value": p,
            "n": int(model.nobs),
        })


# ============================================================
# 3. RESIDUALIZATION
#
# Remove:
# - linear time
# - quadratic time
# - weekday structure
#
# independently from ETF activity and BTC clock metric.
# Then correlate residuals.
# ============================================================

print()
print("============================================================")
print("3. DETRENDED RESIDUAL CORRELATIONS")
print("============================================================")

base_controls = [
    "t_z",
    "t2_z",
] + DOW

resid_rows = []

for xvar in [
    "log_turnover",
    "log_abs_flow",
]:

    print()
    print("X =", xvar)

    X_controls = sm.add_constant(
        df[base_controls]
    )

    x_model = sm.OLS(
        df[xvar],
        X_controls,
    ).fit()

    x_resid = x_model.resid

    for metric in RATIOS:

        y_model = sm.OLS(
            df[metric],
            X_controls,
        ).fit()

        y_resid = y_model.resid

        rho, p = spearmanr(
            x_resid,
            y_resid,
        )

        print(
            f"{metric:20s} "
            f"rho={rho:+.4f} "
            f"p={p:.6g}"
        )

        resid_rows.append({
            "x": xvar,
            "metric": metric,
            "rho": rho,
            "p_value": p,
            "n": len(df),
        })


# ============================================================
# 4. FIRST DIFFERENCES
#
# Δ ETF activity versus Δ US/non-US ratio.
#
# This removes most slow-moving common trends.
# ============================================================

print()
print("============================================================")
print("4. FIRST DIFFERENCES")
print("============================================================")

diff_rows = []

for xvar in [
    "log_turnover",
    "log_abs_flow",
]:

    print()
    print("X =", xvar)

    work = df[
        [xvar] + RATIOS
    ].copy()

    work["dx"] = (
        work[xvar].diff()
    )

    work["dx_z"] = zscore(
        work["dx"]
    )

    for metric in RATIOS:

        work["dy"] = (
            work[metric].diff()
        )

        model = hac_model(
            work,
            "dy",
            ["dx_z"],
            maxlags=5,
        )

        beta = model.params["dx_z"]
        se = model.bse["dx_z"]
        p = model.pvalues["dx_z"]

        lo = beta - 1.96 * se
        hi = beta + 1.96 * se

        pct = (
            np.exp(beta) - 1
        ) * 100

        lo_pct = (
            np.exp(lo) - 1
        ) * 100

        hi_pct = (
            np.exp(hi) - 1
        ) * 100

        print(
            f"{metric:20s} "
            f"delta_ratio={pct:+7.2f}% "
            f"CI=[{lo_pct:+7.2f},{hi_pct:+7.2f}] "
            f"p={p:.6g}"
        )

        diff_rows.append({
            "x": xvar,
            "metric": metric,
            "effect_pct": pct,
            "ci_low_pct": lo_pct,
            "ci_high_pct": hi_pct,
            "p_value": p,
            "n": int(model.nobs),
        })


# ============================================================
# 5. WEEKLY AGGREGATION
#
# Reduces daily noise.
# ============================================================

print()
print("============================================================")
print("5. WEEKLY AGGREGATION")
print("============================================================")

weekly = df[
    [
        "date",
        "log_turnover",
        "log_abs_flow",
    ] + RATIOS
].copy()

weekly["week"] = (
    weekly["date"]
    .dt.to_period("W-FRI")
    .dt.end_time
    .dt.normalize()
)

weekly = (
    weekly
    .groupby(
        "week",
        as_index=False,
    )
    .agg(
        log_turnover=(
            "log_turnover",
            "mean",
        ),
        log_abs_flow=(
            "log_abs_flow",
            "mean",
        ),
        lr_volume=(
            "lr_volume",
            "mean",
        ),
        lr_trades=(
            "lr_trades",
            "mean",
        ),
        lr_variance=(
            "lr_variance",
            "mean",
        ),
        lr_abs_return=(
            "lr_abs_return",
            "mean",
        ),
        days=(
            "date",
            "size",
        ),
    )
)

# Full trading weeks only for primary weekly test.
weekly = weekly[
    weekly["days"] >= 4
].copy()

weekly["t"] = np.arange(
    len(weekly),
    dtype=float,
)

weekly["t_z"] = zscore(
    weekly["t"]
)

weekly["t2_z"] = zscore(
    weekly["t_z"] ** 2
)

weekly_rows = []

print(
    "Weekly observations:",
    len(weekly),
)

for xvar in [
    "log_turnover",
    "log_abs_flow",
]:

    weekly["x_z"] = zscore(
        weekly[xvar]
    )

    print()
    print("X =", xvar)

    for metric in RATIOS:

        model = hac_model(
            weekly,
            metric,
            [
                "x_z",
                "t_z",
                "t2_z",
            ],
            maxlags=3,
        )

        beta = model.params["x_z"]
        se = model.bse["x_z"]
        p = model.pvalues["x_z"]

        lo = beta - 1.96 * se
        hi = beta + 1.96 * se

        pct = (
            np.exp(beta) - 1
        ) * 100

        lo_pct = (
            np.exp(lo) - 1
        ) * 100

        hi_pct = (
            np.exp(hi) - 1
        ) * 100

        print(
            f"{metric:20s} "
            f"ratio_change={pct:+7.2f}% "
            f"CI=[{lo_pct:+7.2f},{hi_pct:+7.2f}] "
            f"p={p:.6g}"
        )

        weekly_rows.append({
            "x": xvar,
            "metric": metric,
            "ratio_change_pct": pct,
            "ci_low_pct": lo_pct,
            "ci_high_pct": hi_pct,
            "p_value": p,
            "n": int(model.nobs),
        })


# ============================================================
# 6. FAIR MATCHED PLACEBO TEST
#
# Every placebo gets EXACTLY the same number of sessions
# before and after its breakpoint.
#
# This fixes the previous asymmetric placebo design.
# ============================================================

print()
print("============================================================")
print("6. MATCHED PLACEBO BREAKPOINTS")
print("============================================================")

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

BREAK = pd.Timestamp(
    "2024-01-11"
)

break_idx = btc.index[
    btc["date"] >= BREAK
].min()

share_metrics = [
    "us_volume_share",
    "us_trade_share",
    "us_variance_share",
    "us_abs_return_share",
]

placebo_records = []
placebo_summary = []

for half_window in [
    63,
    126,
    252,
]:

    print()
    print(
        f"----- ±{half_window} NYSE SESSIONS -----"
    )

    # Actual break.
    actual_left = btc.iloc[
        break_idx - half_window:
        break_idx
    ]

    actual_right = btc.iloc[
        break_idx:
        break_idx + half_window
    ]

    assert len(actual_left) == half_window
    assert len(actual_right) == half_window

    # Placebo candidates restricted to PRE period and
    # sufficiently far from sample edges.
    pre_end = break_idx

    candidates = range(
        half_window,
        pre_end - half_window,
        5,
    )

    for metric in share_metrics:

        actual_delta = (
            actual_right[metric].median()
            - actual_left[metric].median()
        ) * 100

        placebo_vals = []

        for idx in candidates:

            left = btc.iloc[
                idx - half_window:
                idx
            ]

            right = btc.iloc[
                idx:
                idx + half_window
            ]

            # Placebo must remain entirely pre-ETF.
            if (
                right["date"].max()
                >= BREAK
            ):
                continue

            delta = (
                right[metric].median()
                - left[metric].median()
            ) * 100

            placebo_vals.append(
                delta
            )

            placebo_records.append({
                "half_window": half_window,
                "metric": metric,
                "break_date": btc.iloc[idx]["date"],
                "delta_pp": delta,
            })

        placebo_vals = np.asarray(
            placebo_vals
        )

        empirical_p = (
            1
            + np.sum(
                np.abs(placebo_vals)
                >= abs(actual_delta)
            )
        ) / (
            1 + len(placebo_vals)
        )

        percentile = (
            np.mean(
                placebo_vals
                <= actual_delta
            )
            * 100
        )

        print(
            f"{metric:24s} "
            f"actual={actual_delta:+6.2f} pp "
            f"N_placebo={len(placebo_vals):3d} "
            f"p={empirical_p:.4f} "
            f"percentile={percentile:5.1f}%"
        )

        placebo_summary.append({
            "half_window": half_window,
            "metric": metric,
            "actual_delta_pp": actual_delta,
            "n_placebo": len(placebo_vals),
            "empirical_p": empirical_p,
            "percentile": percentile,
            "placebo_median_pp": np.median(
                placebo_vals
            ),
            "placebo_max_abs_pp": np.max(
                np.abs(placebo_vals)
            ),
        })


# ============================================================
# SAVE
# ============================================================

pd.DataFrame(
    trend_rows
).to_csv(
    OUT /
    "detrended_turnover_regressions.csv",
    index=False,
)

pd.DataFrame(
    resid_rows
).to_csv(
    OUT /
    "detrended_residual_correlations.csv",
    index=False,
)

pd.DataFrame(
    diff_rows
).to_csv(
    OUT /
    "first_difference_tests.csv",
    index=False,
)

pd.DataFrame(
    weekly_rows
).to_csv(
    OUT /
    "weekly_etf_clock_tests.csv",
    index=False,
)

pd.DataFrame(
    placebo_records
).to_csv(
    OUT /
    "matched_placebo_breakpoints.csv",
    index=False,
)

pd.DataFrame(
    placebo_summary
).to_csv(
    OUT /
    "matched_placebo_summary.csv",
    index=False,
)

print()
print("============================================================")
print("PASS_DETRENDED_ANALYSIS")
print("============================================================")
