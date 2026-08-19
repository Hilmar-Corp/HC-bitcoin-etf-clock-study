
from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import statsmodels
import statsmodels.api as sm
from scipy.stats import spearmanr

# ============================================================
# CONFIG
# ============================================================

SOURCE = Path(
    "data/processed/btc_etf_master_panel.parquet"
)

OUT = Path("outputs/tables")
AUDIT = Path("audit/research_outputs_v1")

OUT.mkdir(parents=True, exist_ok=True)
AUDIT.mkdir(parents=True, exist_ok=True)

EXPECTED_N = 501

RATIOS = [
    "lr_volume",
    "lr_trades",
    "lr_variance",
    "lr_abs_return",
]


# ============================================================
# HELPERS
# ============================================================

def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def zscore(x: pd.Series) -> pd.Series:
    x = x.astype(float)

    sd = x.std(ddof=0)

    if not np.isfinite(sd) or sd == 0:
        raise ValueError(
            "Cannot z-score constant/non-finite series."
        )

    return (
        x - x.mean()
    ) / sd


def hac_model(
    data: pd.DataFrame,
    y: str,
    xcols: list[str],
    maxlags: int,
):
    tmp = data[
        [y] + xcols
    ].dropna().copy()

    X = sm.add_constant(
        tmp[xcols]
    )

    return sm.OLS(
        tmp[y],
        X,
    ).fit(
        cov_type="HAC",
        cov_kwds={
            "maxlags": maxlags
        },
    )


# ============================================================
# INPUT
# ============================================================

df = pd.read_parquet(
    SOURCE
).copy()

df["date"] = pd.to_datetime(
    df["date"]
)

df = (
    df
    .sort_values("date")
    .reset_index(drop=True)
)

assert len(df) == EXPECTED_N
assert df["date"].is_monotonic_increasing
assert df["date"].duplicated().sum() == 0
assert df["etf_turnover_proxy_usd"].notna().all()
assert df["etf_net_flow_musd"].notna().all()


# ============================================================
# LOG RATIOS
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

for col in [
    "non_us_quote_volume",
    "non_us_trades",
    "non_us_variance",
    "non_us_abs_return",
]:
    assert (df[col] > 0).all()

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


# ============================================================
# TIME CONTROLS
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
# 1. ETF TURNOVER TIME TREND
# ============================================================

time_model = hac_model(
    df,
    "log_turnover",
    [
        "t_z",
        "t2_z",
    ],
    maxlags=10,
)

time_rows = []

for term in [
    "const",
    "t_z",
    "t2_z",
]:
    time_rows.append({
        "term": term,
        "coef": float(
            time_model.params[term]
        ),
        "std_error": float(
            time_model.bse[term]
        ),
        "p_value": float(
            time_model.pvalues[term]
        ),
        "ci_low": float(
            time_model.conf_int()
            .loc[term, 0]
        ),
        "ci_high": float(
            time_model.conf_int()
            .loc[term, 1]
        ),
        "n": int(
            time_model.nobs
        ),
    })

time_rho, time_p = spearmanr(
    df["t"],
    df["etf_turnover_proxy_usd"],
)

time_rows.append({
    "term": "spearman_time_turnover",
    "coef": float(time_rho),
    "std_error": np.nan,
    "p_value": float(time_p),
    "ci_low": np.nan,
    "ci_high": np.nan,
    "n": len(df),
})

time_table = pd.DataFrame(
    time_rows
)


# ============================================================
# 2. DETRENDED HAC REGRESSIONS
# ============================================================

trend_rows = []

for xvar in [
    "log_turnover",
    "log_abs_flow",
]:

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

        beta = float(
            model.params["x_z"]
        )

        se = float(
            model.bse["x_z"]
        )

        p = float(
            model.pvalues["x_z"]
        )

        lo = beta - 1.96 * se
        hi = beta + 1.96 * se

        trend_rows.append({
            "x": xvar,
            "metric": metric,
            "beta_log_ratio": beta,
            "std_error": se,
            "ratio_change_pct": (
                np.exp(beta) - 1
            ) * 100,
            "ci_low_pct": (
                np.exp(lo) - 1
            ) * 100,
            "ci_high_pct": (
                np.exp(hi) - 1
            ) * 100,
            "p_value": p,
            "n": int(
                model.nobs
            ),
            "hac_maxlags": 10,
            "controls": (
                "linear_time;"
                "quadratic_time;"
                "weekday_fixed_effects"
            ),
        })

trend_table = pd.DataFrame(
    trend_rows
)


# ============================================================
# 3. DETRENDED RESIDUAL CORRELATIONS
# ============================================================

base_controls = [
    "t_z",
    "t2_z",
] + DOW

X_controls = sm.add_constant(
    df[base_controls]
)

resid_rows = []

for xvar in [
    "log_turnover",
    "log_abs_flow",
]:

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

        resid_rows.append({
            "x": xvar,
            "metric": metric,
            "spearman_rho": float(rho),
            "p_value": float(p),
            "n": len(df),
            "residualized_against": (
                "linear_time;"
                "quadratic_time;"
                "weekday_fixed_effects"
            ),
        })

resid_table = pd.DataFrame(
    resid_rows
)


# ============================================================
# 4. FIRST DIFFERENCES
# ============================================================

diff_rows = []

for xvar in [
    "log_turnover",
    "log_abs_flow",
]:

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

        beta = float(
            model.params["dx_z"]
        )

        se = float(
            model.bse["dx_z"]
        )

        p = float(
            model.pvalues["dx_z"]
        )

        lo = beta - 1.96 * se
        hi = beta + 1.96 * se

        diff_rows.append({
            "x": xvar,
            "metric": metric,
            "beta_log_ratio_difference": beta,
            "std_error": se,
            "effect_pct": (
                np.exp(beta) - 1
            ) * 100,
            "ci_low_pct": (
                np.exp(lo) - 1
            ) * 100,
            "ci_high_pct": (
                np.exp(hi) - 1
            ) * 100,
            "p_value": p,
            "n": int(
                model.nobs
            ),
            "hac_maxlags": 5,
        })

diff_table = pd.DataFrame(
    diff_rows
)


# ============================================================
# 5. WEEKLY AGGREGATION
# ============================================================

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

weekly = weekly[
    weekly["days"] >= 4
].copy()

assert len(weekly) == 104

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

for xvar in [
    "log_turnover",
    "log_abs_flow",
]:

    weekly["x_z"] = zscore(
        weekly[xvar]
    )

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

        beta = float(
            model.params["x_z"]
        )

        se = float(
            model.bse["x_z"]
        )

        p = float(
            model.pvalues["x_z"]
        )

        lo = beta - 1.96 * se
        hi = beta + 1.96 * se

        weekly_rows.append({
            "x": xvar,
            "metric": metric,
            "beta_log_ratio": beta,
            "std_error": se,
            "ratio_change_pct": (
                np.exp(beta) - 1
            ) * 100,
            "ci_low_pct": (
                np.exp(lo) - 1
            ) * 100,
            "ci_high_pct": (
                np.exp(hi) - 1
            ) * 100,
            "p_value": p,
            "n": int(
                model.nobs
            ),
            "hac_maxlags": 3,
            "controls": (
                "linear_week_time;"
                "quadratic_week_time"
            ),
        })

weekly_table = pd.DataFrame(
    weekly_rows
)


# ============================================================
# NUMERICAL NON-REGRESSION CHECKS
#
# These are intentionally tied to the frozen environment.
# Broader portability tolerances will be designed later.
# ============================================================

def one(
    table: pd.DataFrame,
    **filters,
):
    mask = pd.Series(
        True,
        index=table.index,
    )

    for col, value in filters.items():
        mask &= (
            table[col] == value
        )

    out = table.loc[mask]

    assert len(out) == 1, (
        f"Expected one row for {filters}; "
        f"found {len(out)}"
    )

    return out.iloc[0]


# Detrended turnover -> volume.
r = one(
    trend_table,
    x="log_turnover",
    metric="lr_volume",
)

assert np.isclose(
    r["ratio_change_pct"],
    7.26,
    atol=0.05,
)

assert np.isclose(
    r["p_value"],
    0.000667771,
    atol=5e-6,
)

# Detrended flows -> volume remains null.
r = one(
    trend_table,
    x="log_abs_flow",
    metric="lr_volume",
)

assert np.isclose(
    r["ratio_change_pct"],
    1.79,
    atol=0.05,
)

assert np.isclose(
    r["p_value"],
    0.291629,
    atol=5e-4,
)

# Residual correlation.
r = one(
    resid_table,
    x="log_turnover",
    metric="lr_volume",
)

assert np.isclose(
    r["spearman_rho"],
    0.1558,
    atol=0.0002,
)

assert np.isclose(
    r["p_value"],
    0.000465995,
    atol=5e-6,
)

# First difference.
r = one(
    diff_table,
    x="log_turnover",
    metric="lr_volume",
)

assert np.isclose(
    r["effect_pct"],
    21.14,
    atol=0.05,
)

# Weekly null for volume.
r = one(
    weekly_table,
    x="log_turnover",
    metric="lr_volume",
)

assert np.isclose(
    r["ratio_change_pct"],
    -0.03,
    atol=0.05,
)

assert np.isclose(
    r["p_value"],
    0.9873,
    atol=0.001,
)


# ============================================================
# SAVE — ATOMIC ENOUGH FOR CURRENT RESEARCH STAGE
# ============================================================

targets = {
    "etf_turnover_time_trend":
        OUT / "etf_turnover_time_trend.csv",

    "detrended_turnover_regressions":
        OUT / "detrended_turnover_regressions.csv",

    "detrended_residual_correlations":
        OUT / "detrended_residual_correlations.csv",

    "first_difference_tests":
        OUT / "first_difference_tests.csv",

    "weekly_etf_clock_tests":
        OUT / "weekly_etf_clock_tests.csv",
}

tables = {
    "etf_turnover_time_trend":
        time_table,

    "detrended_turnover_regressions":
        trend_table,

    "detrended_residual_correlations":
        resid_table,

    "first_difference_tests":
        diff_table,

    "weekly_etf_clock_tests":
        weekly_table,
}

for name, path in targets.items():
    tmp = path.with_suffix(
        ".tmp.csv"
    )

    tables[name].to_csv(
        tmp,
        index=False,
    )

    tmp.replace(path)


# ============================================================
# RUN MANIFEST
# ============================================================

manifest = {
    "schema_version": 1,
    "analysis": "analysis_04_detrended_core",
    "status": "persisted_after_baseline_freeze",

    "created_at_utc": datetime.now(
        UTC
    ).isoformat(),

    "input": {
        "path": str(SOURCE),
        "sha256": sha256(SOURCE),
        "rows": len(df),
    },

    "environment": {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "statsmodels": statsmodels.__version__,
    },

    "outputs": {
        name: {
            "path": str(path),
            "rows": len(
                tables[name]
            ),
            "sha256": sha256(path),
        }
        for name, path
        in targets.items()
    },

    "validation": {
        "expected_master_rows": 501,
        "expected_weekly_rows": 104,
        "numerical_non_regression_checks": "PASS",
    },
}

manifest_path = (
    AUDIT /
    "analysis_04_manifest.json"
)

manifest_path.write_text(
    json.dumps(
        manifest,
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)


# ============================================================
# REPORT
# ============================================================

print()
print("============================================================")
print("DE-TRENDED TURNOVER — KEY RESULT")
print("============================================================")

print(
    trend_table[
        (
            trend_table["x"]
            == "log_turnover"
        )
        &
        (
            trend_table["metric"]
            == "lr_volume"
        )
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.9f}",
    )
)

print()
print("============================================================")
print("RESIDUAL CORRELATION — KEY RESULT")
print("============================================================")

print(
    resid_table[
        (
            resid_table["x"]
            == "log_turnover"
        )
        &
        (
            resid_table["metric"]
            == "lr_volume"
        )
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.9f}",
    )
)

print()
print("============================================================")
print("FIRST DIFFERENCE — KEY RESULT")
print("============================================================")

print(
    diff_table[
        (
            diff_table["x"]
            == "log_turnover"
        )
        &
        (
            diff_table["metric"]
            == "lr_volume"
        )
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.9f}",
    )
)

print()
print("============================================================")
print("WEEKLY — KEY RESULT")
print("============================================================")

print(
    weekly_table[
        (
            weekly_table["x"]
            == "log_turnover"
        )
        &
        (
            weekly_table["metric"]
            == "lr_volume"
        )
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.9f}",
    )
)

print()
print("============================================================")
print("OUTPUT HASHES")
print("============================================================")

for _, path in targets.items():
    print(
        sha256(path),
        path,
    )

print()
print(
    "Manifest ->",
    manifest_path,
)

print()
print("PASS_ANALYSIS_04_PERSISTENCE")
