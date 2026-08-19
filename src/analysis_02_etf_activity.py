
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import (
    mannwhitneyu,
    spearmanr,
)

SOURCE = Path(
    "data/processed/btc_etf_master_panel.parquet"
)

OUT = Path("outputs/tables")
OUT.mkdir(parents=True, exist_ok=True)

METRICS = [
    "us_volume_share",
    "us_trade_share",
    "us_variance_share",
    "us_abs_return_share",
]

ACTIVITY = [
    "abs_etf_flow_musd",
    "etf_turnover_proxy_usd",
]

df = pd.read_parquet(SOURCE).copy()

df["date"] = pd.to_datetime(df["date"])

df = (
    df.sort_values("date")
    .reset_index(drop=True)
)

assert len(df) == 501
assert df["etf_net_flow_musd"].notna().all()
assert df["etf_turnover_proxy_usd"].notna().all()

# ============================================================
# DERIVED VARIABLES
# ============================================================

df["abs_etf_flow_musd"] = (
    df["etf_net_flow_musd"].abs()
)

df["log_abs_flow"] = np.log1p(
    df["abs_etf_flow_musd"]
)

df["log_turnover"] = np.log1p(
    df["etf_turnover_proxy_usd"]
)

# BTC total activity controls.
df["log_btc_volume"] = np.log1p(
    df["total_quote_volume"]
)

df["log_btc_variance"] = np.log1p(
    df["total_variance"] * 1e8
)

df["abs_btc_return"] = (
    df["daily_log_return"].abs()
)

# Previous NYSE-session ETF observation.
df["flow_lag1"] = (
    df["etf_net_flow_musd"]
    .shift(1)
)

df["abs_flow_lag1"] = (
    df["abs_etf_flow_musd"]
    .shift(1)
)

df["turnover_lag1"] = (
    df["etf_turnover_proxy_usd"]
    .shift(1)
)

df["log_abs_flow_lag1"] = np.log1p(
    df["abs_flow_lag1"]
)

df["log_turnover_lag1"] = np.log1p(
    df["turnover_lag1"]
)

# Next-session dependent variables for predictive-direction check.
for metric in METRICS:
    df[f"{metric}_lead1"] = (
        df[metric].shift(-1)
    )


# ============================================================
# HELPER
# ============================================================

def zscore(s):
    s = s.astype(float)
    return (
        s - s.mean()
    ) / s.std(ddof=0)


rows = []

print()
print("============================================================")
print("1. SPEARMAN — CONTEMPORANEOUS ASSOCIATION")
print("============================================================")

for xvar in [
    "abs_etf_flow_musd",
    "etf_turnover_proxy_usd",
]:

    print()
    print("X =", xvar)

    for metric in METRICS:

        tmp = df[
            [xvar, metric]
        ].dropna()

        rho, p = spearmanr(
            tmp[xvar],
            tmp[metric],
        )

        print(
            f"{metric:24s} "
            f"rho={rho:+.4f} "
            f"p={p:.6g} "
            f"N={len(tmp)}"
        )

        rows.append({
            "family": "spearman_same_day",
            "x": xvar,
            "y": metric,
            "estimate": rho,
            "p_value": p,
            "n": len(tmp),
        })


# ============================================================
# 2. QUARTILE TEST
# ============================================================

print()
print("============================================================")
print("2. Q1 VS Q4 ETF ACTIVITY")
print("============================================================")

for xvar in [
    "abs_etf_flow_musd",
    "etf_turnover_proxy_usd",
]:

    tmp = df[
        [xvar] + METRICS
    ].dropna().copy()

    tmp["quartile"] = pd.qcut(
        tmp[xvar],
        q=4,
        labels=False,
        duplicates="drop",
    )

    print()
    print("X =", xvar)

    for metric in METRICS:

        low = tmp.loc[
            tmp["quartile"] == 0,
            metric,
        ]

        high = tmp.loc[
            tmp["quartile"] == 3,
            metric,
        ]

        u, p = mannwhitneyu(
            low,
            high,
            alternative="two-sided",
        )

        delta_pp = (
            high.median()
            - low.median()
        ) * 100

        print(
            f"{metric:24s} "
            f"Q1={100*low.median():6.2f}% "
            f"Q4={100*high.median():6.2f}% "
            f"DELTA={delta_pp:+6.2f} pp "
            f"p={p:.6g}"
        )

        rows.append({
            "family": "quartile_q4_minus_q1",
            "x": xvar,
            "y": metric,
            "estimate": delta_pp,
            "p_value": p,
            "n": len(low) + len(high),
        })


# ============================================================
# 3. HAC — UNIVARIATE
#
# Coefficient = percentage-point change in BTC US-share
# associated with +1 standard deviation in ETF activity.
# ============================================================

print()
print("============================================================")
print("3. HAC — STANDARDIZED ETF ACTIVITY")
print("============================================================")

for xvar in [
    "log_abs_flow",
    "log_turnover",
]:

    print()
    print("X =", xvar)

    for metric in METRICS:

        tmp = df[
            [xvar, metric]
        ].dropna().copy()

        tmp["x_z"] = zscore(
            tmp[xvar]
        )

        X = sm.add_constant(
            tmp[["x_z"]]
        )

        model = sm.OLS(
            tmp[metric],
            X,
        ).fit(
            cov_type="HAC",
            cov_kwds={
                "maxlags": 10
            },
        )

        beta_pp = (
            model.params["x_z"]
            * 100
        )

        se_pp = (
            model.bse["x_z"]
            * 100
        )

        p = model.pvalues["x_z"]

        lo = beta_pp - 1.96 * se_pp
        hi = beta_pp + 1.96 * se_pp

        print(
            f"{metric:24s} "
            f"beta={beta_pp:+6.2f} pp "
            f"CI=[{lo:+6.2f},{hi:+6.2f}] "
            f"p={p:.6g} "
            f"N={int(model.nobs)}"
        )

        rows.append({
            "family": "hac_univariate",
            "x": xvar,
            "y": metric,
            "estimate": beta_pp,
            "ci_low": lo,
            "ci_high": hi,
            "p_value": p,
            "n": int(model.nobs),
        })


# ============================================================
# 4. HAC WITH BTC MARKET CONTROLS
#
# Controls:
# - total BTC daily quote volume
# - total BTC realized variance
#
# This asks whether ETF activity is related to the SHARE
# occurring in US hours, rather than merely high-activity days.
# ============================================================

print()
print("============================================================")
print("4. HAC — WITH BTC ACTIVITY CONTROLS")
print("============================================================")

for xvar in [
    "log_abs_flow",
    "log_turnover",
]:

    print()
    print("X =", xvar)

    for metric in METRICS:

        tmp = df[
            [
                xvar,
                metric,
                "log_btc_volume",
                "log_btc_variance",
            ]
        ].dropna().copy()

        tmp["x_z"] = zscore(
            tmp[xvar]
        )

        tmp["btc_volume_z"] = zscore(
            tmp["log_btc_volume"]
        )

        tmp["btc_variance_z"] = zscore(
            tmp["log_btc_variance"]
        )

        X = sm.add_constant(
            tmp[
                [
                    "x_z",
                    "btc_volume_z",
                    "btc_variance_z",
                ]
            ]
        )

        model = sm.OLS(
            tmp[metric],
            X,
        ).fit(
            cov_type="HAC",
            cov_kwds={
                "maxlags": 10
            },
        )

        beta_pp = (
            model.params["x_z"]
            * 100
        )

        se_pp = (
            model.bse["x_z"]
            * 100
        )

        p = model.pvalues["x_z"]

        lo = beta_pp - 1.96 * se_pp
        hi = beta_pp + 1.96 * se_pp

        print(
            f"{metric:24s} "
            f"beta={beta_pp:+6.2f} pp "
            f"CI=[{lo:+6.2f},{hi:+6.2f}] "
            f"p={p:.6g}"
        )

        rows.append({
            "family": "hac_controlled",
            "x": xvar,
            "y": metric,
            "estimate": beta_pp,
            "ci_low": lo,
            "ci_high": hi,
            "p_value": p,
            "n": int(model.nobs),
        })


# ============================================================
# 5. LAGGED ETF ACTIVITY -> CURRENT BTC STRUCTURE
#
# If same-day association is strong but lagged association
# disappears, interpretation is contemporaneous co-movement,
# not evidence of forecasting/persistence.
# ============================================================

print()
print("============================================================")
print("5. LAGGED ETF ACTIVITY -> CURRENT BTC SESSION")
print("============================================================")

for xvar in [
    "log_abs_flow_lag1",
    "log_turnover_lag1",
]:

    print()
    print("X =", xvar)

    for metric in METRICS:

        tmp = df[
            [xvar, metric]
        ].dropna()

        rho, p = spearmanr(
            tmp[xvar],
            tmp[metric],
        )

        print(
            f"{metric:24s} "
            f"rho={rho:+.4f} "
            f"p={p:.6g}"
        )

        rows.append({
            "family": "spearman_lag1",
            "x": xvar,
            "y": metric,
            "estimate": rho,
            "p_value": p,
            "n": len(tmp),
        })


# ============================================================
# 6. CURRENT ETF ACTIVITY -> NEXT BTC SESSION
# ============================================================

print()
print("============================================================")
print("6. CURRENT ETF ACTIVITY -> NEXT BTC SESSION")
print("============================================================")

for xvar in [
    "log_abs_flow",
    "log_turnover",
]:

    print()
    print("X =", xvar)

    for metric in METRICS:

        lead = f"{metric}_lead1"

        tmp = df[
            [xvar, lead]
        ].dropna()

        rho, p = spearmanr(
            tmp[xvar],
            tmp[lead],
        )

        print(
            f"{metric:24s} "
            f"rho={rho:+.4f} "
            f"p={p:.6g}"
        )

        rows.append({
            "family": "spearman_lead1",
            "x": xvar,
            "y": metric,
            "estimate": rho,
            "p_value": p,
            "n": len(tmp),
        })


# ============================================================
# 7. SIGNED FLOWS VS BTC RETURNS
#
# Distinct question:
# net creations/redemptions vs BTC return.
# This is NOT the core "US clock" test.
# ============================================================

print()
print("============================================================")
print("7. SIGNED ETF FLOWS VS BTC RETURNS")
print("============================================================")

for ret in [
    "daily_log_return",
    "us_session_log_return",
]:

    tmp = df[
        [
            "etf_net_flow_musd",
            ret,
        ]
    ].dropna()

    rho, p = spearmanr(
        tmp["etf_net_flow_musd"],
        tmp[ret],
    )

    print(
        f"{ret:24s} "
        f"rho={rho:+.4f} "
        f"p={p:.6g}"
    )

    rows.append({
        "family": "signed_flow_return",
        "x": "etf_net_flow_musd",
        "y": ret,
        "estimate": rho,
        "p_value": p,
        "n": len(tmp),
    })


# ============================================================
# 8. CORRELATION BETWEEN FLOW MAGNITUDE AND TURNOVER
# ============================================================

rho, p = spearmanr(
    df["abs_etf_flow_musd"],
    df["etf_turnover_proxy_usd"],
)

print()
print("============================================================")
print("8. ETF FLOW MAGNITUDE VS ETF TURNOVER")
print("============================================================")

print(
    f"rho={rho:+.4f} "
    f"p={p:.6g}"
)


# ============================================================
# 9. SAVE
# ============================================================

results = pd.DataFrame(rows)

results.to_csv(
    OUT /
    "etf_activity_vs_btc_us_clock.csv",
    index=False,
)

df.to_parquet(
    "data/processed/"
    "btc_etf_master_panel_enriched.parquet",
    index=False,
)

print()
print(
    "Saved -> outputs/tables/"
    "etf_activity_vs_btc_us_clock.csv"
)

print()
print("PASS_ETF_ACTIVITY_ANALYSIS")
