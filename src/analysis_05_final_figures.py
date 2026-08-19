
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

BTC5 = Path(
    "data/processed/btc_5m_etf_clock.parquet"
)

PANEL = Path(
    "data/processed/btc_daily_nyse_panel.parquet"
)

MASTER = Path(
    "data/processed/btc_etf_master_panel.parquet"
)

FIG = Path("outputs/figures")
TABLE = Path("outputs/tables")

FIG.mkdir(parents=True, exist_ok=True)
TABLE.mkdir(parents=True, exist_ok=True)


# ============================================================
# LOAD FINAL DAILY PANEL
# ============================================================

panel = pd.read_parquet(PANEL).copy()

panel["date"] = pd.to_datetime(
    panel["date"]
)

valid_dates = set(
    panel["date"].dt.date
)

period_map = dict(
    zip(
        panel["date"].dt.date,
        panel["period"],
        strict=True,
    )
)


# ============================================================
# LOAD BTC 5M
# ============================================================

btc = pd.read_parquet(
    BTC5,
    columns=[
        "timestamp_utc",
        "quote_volume",
        "n_trades",
        "sq_log_return",
    ],
)

btc["timestamp_utc"] = pd.to_datetime(
    btc["timestamp_utc"],
    utc=True,
)

btc["timestamp_ny"] = (
    btc["timestamp_utc"]
    .dt.tz_convert("America/New_York")
)

btc["date"] = (
    btc["timestamp_ny"]
    .dt.date
)

btc = btc[
    btc["date"].isin(valid_dates)
].copy()

btc["period"] = (
    btc["date"].map(period_map)
)

btc["minute_ny"] = (
    btc["timestamp_ny"].dt.hour * 60
    + btc["timestamp_ny"].dt.minute
)


# ============================================================
# DAILY NORMALIZATION
#
# Every BTC day receives weight 1.
# Large-volume days therefore cannot dominate the profile.
# ============================================================

for col in [
    "quote_volume",
    "n_trades",
    "sq_log_return",
]:

    total = (
        btc.groupby("date")[col]
        .transform("sum")
    )

    btc[f"{col}_share"] = (
        btc[col] / total
    )


# ============================================================
# FIGURE 1
# PRE VS POST — NORMALIZED BTC VOLUME PROFILE
# ============================================================

profile = (
    btc.groupby(
        ["period", "minute_ny"],
        as_index=False,
    )
    .agg(
        volume_share=(
            "quote_volume_share",
            "mean",
        ),
        trade_share=(
            "n_trades_share",
            "mean",
        ),
        variance_share=(
            "sq_log_return_share",
            "mean",
        ),
    )
)

# 30-minute smoothing = six 5m bins.
for period in [
    "pre_etf",
    "post_etf",
]:

    mask = profile["period"] == period

    for col in [
        "volume_share",
        "trade_share",
        "variance_share",
    ]:

        profile.loc[
            mask,
            col + "_smooth"
        ] = (
            profile.loc[mask, col]
            .rolling(
                window=6,
                center=True,
                min_periods=1,
            )
            .mean()
            .values
        )


fig, ax = plt.subplots(
    figsize=(11, 5.5)
)

for period, label in [
    ("pre_etf", "Avant ETF spot"),
    ("post_etf", "Après ETF spot"),
]:

    x = profile[
        profile["period"] == period
    ]

    ax.plot(
        x["minute_ny"] / 60,
        x["volume_share_smooth"] * 100,
        label=label,
        linewidth=2,
    )

ax.axvline(
    9.5,
    linestyle="--",
    linewidth=1,
)

ax.axvline(
    16,
    linestyle="--",
    linewidth=1,
)

ax.set_xlabel(
    "Heure de New York"
)

ax.set_ylabel(
    "Part moyenne du volume quotidien (%)"
)

ax.set_title(
    "Répartition intrajournalière du volume Bitcoin"
)

ax.legend(
    frameon=False
)

ax.set_xlim(
    0,
    24,
)

fig.tight_layout()

fig.savefig(
    FIG / "final_01_pre_post_intraday_volume.png",
    dpi=220,
)

plt.close(fig)


# ============================================================
# POST ETF + TURNOVER
# ============================================================

master = pd.read_parquet(
    MASTER
).copy()

master["date"] = pd.to_datetime(
    master["date"]
)

master["date_key"] = (
    master["date"].dt.date
)

master["turnover_quartile"] = pd.qcut(
    master["etf_turnover_proxy_usd"],
    4,
    labels=[
        "Q1",
        "Q2",
        "Q3",
        "Q4",
    ],
)

quartile_map = dict(
    zip(
        master["date_key"],
        master["turnover_quartile"],
        strict=True,
    )
)

post = btc[
    btc["period"] == "post_etf"
].copy()

post["turnover_quartile"] = (
    post["date"].map(quartile_map)
)


# ============================================================
# FIGURE 2
# LOW VS HIGH ETF TURNOVER
# ============================================================

qprofile = (
    post[
        post["turnover_quartile"]
        .isin(["Q1", "Q4"])
    ]
    .groupby(
        [
            "turnover_quartile",
            "minute_ny",
        ],
        as_index=False,
        observed=True,
    )
    .agg(
        volume_share=(
            "quote_volume_share",
            "mean",
        )
    )
)

for q in [
    "Q1",
    "Q4",
]:

    mask = (
        qprofile[
            "turnover_quartile"
        ] == q
    )

    qprofile.loc[
        mask,
        "smooth"
    ] = (
        qprofile.loc[
            mask,
            "volume_share"
        ]
        .rolling(
            6,
            center=True,
            min_periods=1,
        )
        .mean()
        .values
    )


fig, ax = plt.subplots(
    figsize=(11, 5.5)
)

for q, label in [
    ("Q1", "Faible turnover ETF"),
    ("Q4", "Fort turnover ETF"),
]:

    x = qprofile[
        qprofile[
            "turnover_quartile"
        ] == q
    ]

    ax.plot(
        x["minute_ny"] / 60,
        x["smooth"] * 100,
        label=label,
        linewidth=2,
    )

ax.axvline(
    9.5,
    linestyle="--",
    linewidth=1,
)

ax.axvline(
    16,
    linestyle="--",
    linewidth=1,
)

ax.set_xlabel(
    "Heure de New York"
)

ax.set_ylabel(
    "Part moyenne du volume quotidien (%)"
)

ax.set_title(
    "Bitcoin selon l'intensité de négociation des ETF"
)

ax.legend(
    frameon=False
)

ax.set_xlim(
    0,
    24,
)

fig.tight_layout()

fig.savefig(
    FIG / "final_02_etf_turnover_intraday_volume.png",
    dpi=220,
)

plt.close(fig)


# ============================================================
# DETRENDED RELATION
# ============================================================

eps = 1e-12

master["non_us_volume"] = (
    master["total_quote_volume"]
    - master["us_quote_volume"]
)

master["lr_volume"] = np.log(
    (
        master["us_quote_volume"]
        + eps
    )
    /
    (
        master["non_us_volume"]
        + eps
    )
)

master["log_turnover"] = np.log1p(
    master["etf_turnover_proxy_usd"]
)

master = (
    master.sort_values("date")
    .reset_index(drop=True)
)

master["t"] = np.arange(
    len(master),
    dtype=float,
)

master["t_z"] = (
    master["t"]
    - master["t"].mean()
) / master["t"].std(ddof=0)

master["t2_z"] = (
    master["t_z"] ** 2
)

master["t2_z"] = (
    master["t2_z"]
    - master["t2_z"].mean()
) / master["t2_z"].std(ddof=0)

master["dow"] = (
    master["date"].dt.dayofweek
)

dummies = pd.get_dummies(
    master["dow"],
    prefix="dow",
    drop_first=True,
    dtype=float,
)

master = pd.concat(
    [
        master,
        dummies,
    ],
    axis=1,
)

controls = [
    "t_z",
    "t2_z",
] + list(dummies.columns)

X = sm.add_constant(
    master[controls]
)

turn_model = sm.OLS(
    master["log_turnover"],
    X,
).fit()

volume_model = sm.OLS(
    master["lr_volume"],
    X,
).fit()

master["turnover_resid"] = (
    turn_model.resid
)

master["volume_resid"] = (
    volume_model.resid
)


# ============================================================
# FIGURE 3
# DETRENDED TURNOVER DECILES
# ============================================================

master["turnover_resid_decile"] = pd.qcut(
    master["turnover_resid"],
    10,
    labels=False,
) + 1

deciles = (
    master.groupby(
        "turnover_resid_decile",
        as_index=False,
    )
    .agg(
        median_turnover_resid=(
            "turnover_resid",
            "median",
        ),
        median_volume_resid=(
            "volume_resid",
            "median",
        ),
        n=(
            "date",
            "size",
        ),
    )
)

fig, ax = plt.subplots(
    figsize=(8, 5.5)
)

ax.plot(
    deciles["turnover_resid_decile"],
    deciles["median_volume_resid"],
    marker="o",
)

ax.axhline(
    0,
    linewidth=1,
)

ax.set_xlabel(
    "Décile de turnover ETF après retrait de la tendance"
)

ax.set_ylabel(
    "Ratio volume US / hors-US résiduel"
)

ax.set_title(
    "Activité ETF et concentration du volume Bitcoin"
)

fig.tight_layout()

fig.savefig(
    FIG / "final_03_detrended_turnover_deciles.png",
    dpi=220,
)

plt.close(fig)


# ============================================================
# TABLE — INTRADAY DIFFERENCE BY HOUR
# ============================================================

hourly = (
    post[
        post["turnover_quartile"]
        .isin(["Q1", "Q4"])
    ]
    .assign(
        hour=lambda x:
        x["timestamp_ny"].dt.hour
    )
    .groupby(
        [
            "turnover_quartile",
            "hour",
        ],
        observed=True,
    )[
        "quote_volume_share"
    ]
    .mean()
    .unstack(0)
)

if (
    "Q1" in hourly.columns
    and "Q4" in hourly.columns
):

    hourly["Q4_minus_Q1_pp"] = (
        hourly["Q4"]
        - hourly["Q1"]
    ) * 100

hourly.to_csv(
    TABLE /
    "final_intraday_turnover_hourly.csv"
)

print()
print("============================================================")
print("TOP HOURS: Q4 ETF TURNOVER MINUS Q1")
print("============================================================")

print(
    hourly.sort_values(
        "Q4_minus_Q1_pp",
        ascending=False,
    )
    .head(10)
    .to_string(
        float_format=lambda x: f"{x:.4f}",
    )
)

print()
print("Figures:")
print(
    FIG /
    "final_01_pre_post_intraday_volume.png"
)
print(
    FIG /
    "final_02_etf_turnover_intraday_volume.png"
)
print(
    FIG /
    "final_03_detrended_turnover_deciles.png"
)

print()
print("PASS_FINAL_INTRADAY_FIGURES")
