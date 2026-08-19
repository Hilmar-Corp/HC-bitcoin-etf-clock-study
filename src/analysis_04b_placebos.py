
from pathlib import Path

import numpy as np
import pandas as pd

# ============================================================
# CONFIG
# ============================================================

BTC_PATH = Path(
    "data/processed/btc_daily_nyse_panel.parquet"
)

OUT = Path("outputs/tables")
OUT.mkdir(parents=True, exist_ok=True)

BREAK = pd.Timestamp("2024-01-11")

METRICS = [
    "us_volume_share",
    "us_trade_share",
    "us_variance_share",
    "us_abs_return_share",
]

# 252 cannot be used for historical pre-ETF placebos because
# the complete PRE sample contains only 501 sessions.
#
# Use approximately:
# 63  = 3 months each side
# 126 = 6 months each side
# 189 = 9 months each side
HALF_WINDOWS = [
    63,
    126,
    189,
]


# ============================================================
# LOAD
# ============================================================

btc = pd.read_parquet(
    BTC_PATH
).copy()

btc["date"] = pd.to_datetime(
    btc["date"]
)

btc = (
    btc
    .sort_values("date")
    .reset_index(drop=True)
)

break_idx = btc.index[
    btc["date"] >= BREAK
].min()

print("BTC rows:", len(btc))
print("Break index:", break_idx)

print(
    "PRE observations:",
    int((btc["date"] < BREAK).sum())
)

print(
    "POST observations:",
    int((btc["date"] >= BREAK).sum())
)


# ============================================================
# MATCHED PLACEBOS
# ============================================================

records = []
summaries = []

for half_window in HALF_WINDOWS:

    print()
    print(
        "============================================================"
    )
    print(
        f"±{half_window} NYSE SESSIONS"
    )
    print(
        "============================================================"
    )

    if break_idx < half_window:
        print("SKIP: insufficient observations before actual break.")
        continue

    if len(btc) - break_idx < half_window:
        print("SKIP: insufficient observations after actual break.")
        continue

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

    # Candidate false breaks.
    #
    # Need exactly `half_window` observations before AND after
    # the false break, with the entire right window still PRE ETF.
    candidate_indices = list(
        range(
            half_window,
            break_idx - half_window + 1,
            5,
        )
    )

    print(
        "Candidate placebo breakpoints:",
        len(candidate_indices),
    )

    if len(candidate_indices) == 0:
        print("SKIP: no feasible matched placebo.")
        continue

    for metric in METRICS:

        actual_delta = (
            actual_right[metric].median()
            - actual_left[metric].median()
        ) * 100

        placebo_vals = []

        for idx in candidate_indices:

            left = btc.iloc[
                idx - half_window:
                idx
            ]

            right = btc.iloc[
                idx:
                idx + half_window
            ]

            if len(left) != half_window:
                continue

            if len(right) != half_window:
                continue

            # Entire placebo sample must precede real ETF launch.
            if right["date"].max() >= BREAK:
                continue

            delta = (
                right[metric].median()
                - left[metric].median()
            ) * 100

            placebo_vals.append(
                delta
            )

            records.append({
                "half_window": half_window,
                "metric": metric,
                "break_date": btc.iloc[idx]["date"],
                "delta_pp": delta,
            })

        placebo_vals = np.asarray(
            placebo_vals,
            dtype=float,
        )

        n = len(placebo_vals)

        if n == 0:
            print(
                f"{metric:24s} "
                f"SKIP — no valid placebo"
            )
            continue

        empirical_two_sided_p = (
            1
            + np.sum(
                np.abs(placebo_vals)
                >= abs(actual_delta)
            )
        ) / (
            n + 1
        )

        # One-sided question:
        # how often was a historical increase >= actual increase?
        empirical_upper_p = (
            1
            + np.sum(
                placebo_vals
                >= actual_delta
            )
        ) / (
            n + 1
        )

        percentile = (
            np.mean(
                placebo_vals
                <= actual_delta
            )
            * 100
        )

        placebo_median = (
            np.median(placebo_vals)
        )

        placebo_p05 = (
            np.quantile(
                placebo_vals,
                0.05,
            )
        )

        placebo_p95 = (
            np.quantile(
                placebo_vals,
                0.95,
            )
        )

        max_abs = (
            np.max(
                np.abs(placebo_vals)
            )
        )

        print(
            f"{metric:24s} "
            f"actual={actual_delta:+6.2f} pp | "
            f"N={n:3d} | "
            f"median={placebo_median:+6.2f} | "
            f"P05/P95=[{placebo_p05:+6.2f},{placebo_p95:+6.2f}] | "
            f"p2={empirical_two_sided_p:.4f} | "
            f"p+={empirical_upper_p:.4f} | "
            f"pct={percentile:5.1f}%"
        )

        summaries.append({
            "half_window": half_window,
            "metric": metric,

            "actual_delta_pp": actual_delta,

            "n_placebo": n,

            "placebo_median_pp": placebo_median,
            "placebo_p05_pp": placebo_p05,
            "placebo_p95_pp": placebo_p95,
            "placebo_max_abs_pp": max_abs,

            "empirical_two_sided_p": (
                empirical_two_sided_p
            ),

            "empirical_upper_p": (
                empirical_upper_p
            ),

            "actual_percentile": percentile,
        })


# ============================================================
# SAVE
# ============================================================

detail = pd.DataFrame(records)
summary = pd.DataFrame(summaries)

detail.to_csv(
    OUT / "matched_placebo_breakpoints_v2.csv",
    index=False,
)

summary.to_csv(
    OUT / "matched_placebo_summary_v2.csv",
    index=False,
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("============================================================")
print("SUMMARY")
print("============================================================")

print(
    summary[
        [
            "half_window",
            "metric",
            "actual_delta_pp",
            "n_placebo",
            "placebo_median_pp",
            "placebo_p95_pp",
            "empirical_two_sided_p",
            "empirical_upper_p",
            "actual_percentile",
        ]
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.4f}",
    )
)

print()
print(
    "Saved -> "
    "outputs/tables/matched_placebo_summary_v2.csv"
)

print()
print("PASS_MATCHED_PLACEBOS")
