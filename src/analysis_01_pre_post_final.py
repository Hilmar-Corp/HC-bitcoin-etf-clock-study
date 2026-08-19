from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import mannwhitneyu

# ============================================================
# CONFIG
# ============================================================

SOURCE = Path(
    "data/processed/btc_daily_nyse_panel.parquet"
)

OUT = Path("outputs/tables")
OUT.mkdir(parents=True, exist_ok=True)

SEED = 42
N_BOOT = 10000
BLOCK = 10

METRICS = [
    "us_volume_share",
    "us_trade_share",
    "us_variance_share",
    "us_abs_return_share",
]


# ============================================================
# LOAD
# ============================================================

df = pd.read_parquet(SOURCE).copy()

df = (
    df.sort_values("date")
    .reset_index(drop=True)
)

assert len(df) == 1002
assert (df["period"] == "pre_etf").sum() == 501
assert (df["period"] == "post_etf").sum() == 501


# ============================================================
# HELPERS
# ============================================================

def block_bootstrap_delta(
    pre,
    post,
    block=10,
    n_boot=10000,
    seed=42,
):
    """
    Circular moving-block bootstrap.

    Statistic:
        median(post) - median(pre)
    """

    rng = np.random.default_rng(seed)

    pre = np.asarray(pre, dtype=float)
    post = np.asarray(post, dtype=float)

    pre = pre[np.isfinite(pre)]
    post = post[np.isfinite(post)]

    def sample_blocks(x):
        n = len(x)
        out = []

        while len(out) < n:
            start = rng.integers(0, n)

            idx = (
                start
                + np.arange(block)
            ) % n

            out.extend(
                x[idx].tolist()
            )

        return np.asarray(
            out[:n]
        )

    boot = np.empty(n_boot)

    for i in range(n_boot):

        a = sample_blocks(pre)
        b = sample_blocks(post)

        boot[i] = (
            np.median(b)
            - np.median(a)
        )

    lo, hi = np.quantile(
        boot,
        [0.025, 0.975],
    )

    return (
        float(np.median(boot)),
        float(lo),
        float(hi),
    )


def rank_biserial_from_u(
    u,
    n1,
    n2,
):
    """
    Rank-biserial correlation using U
    with PRE as sample 1.
    Positive final interpretation is handled
    by comparison of medians separately.
    """
    return 1 - (
        2 * u / (n1 * n2)
    )


# ============================================================
# MAIN TESTS
# ============================================================

rows = []

print()
print("============================================================")
print("FINAL PRE / POST ANALYSIS")
print("============================================================")

for metric in METRICS:

    pre = df.loc[
        df["period"] == "pre_etf",
        metric,
    ].dropna()

    post = df.loc[
        df["period"] == "post_etf",
        metric,
    ].dropna()

    # --------------------------------------------------------
    # Descriptives
    # --------------------------------------------------------

    pre_mean = pre.mean()
    post_mean = post.mean()

    pre_median = pre.median()
    post_median = post.median()

    delta_mean = (
        post_mean - pre_mean
    )

    delta_median = (
        post_median - pre_median
    )

    # --------------------------------------------------------
    # Mann-Whitney
    # --------------------------------------------------------

    u, p_mw = mannwhitneyu(
        pre,
        post,
        alternative="two-sided",
    )

    rbc = rank_biserial_from_u(
        u,
        len(pre),
        len(post),
    )

    # --------------------------------------------------------
    # OLS Post dummy + HAC
    # --------------------------------------------------------

    tmp = df[
        [
            "period",
            metric,
        ]
    ].dropna().copy()

    tmp["post"] = (
        tmp["period"] == "post_etf"
    ).astype(int)

    X = sm.add_constant(
        tmp[["post"]]
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

    hac_beta = model.params["post"]
    hac_se = model.bse["post"]
    hac_p = model.pvalues["post"]

    hac_lo = (
        hac_beta
        - 1.96 * hac_se
    )

    hac_hi = (
        hac_beta
        + 1.96 * hac_se
    )

    # --------------------------------------------------------
    # Block bootstrap median delta
    # --------------------------------------------------------

    boot_est, boot_lo, boot_hi = (
        block_bootstrap_delta(
            pre.values,
            post.values,
            block=BLOCK,
            n_boot=N_BOOT,
            seed=SEED,
        )
    )

    rows.append({
        "metric": metric,

        "pre_n": len(pre),
        "post_n": len(post),

        "pre_mean": pre_mean,
        "post_mean": post_mean,
        "delta_mean": delta_mean,

        "pre_median": pre_median,
        "post_median": post_median,
        "delta_median": delta_median,

        "delta_median_pp": (
            delta_median * 100
        ),

        "mann_whitney_u": u,
        "mann_whitney_p": p_mw,
        "rank_biserial": rbc,

        "hac_beta": hac_beta,
        "hac_beta_pp": (
            hac_beta * 100
        ),
        "hac_se": hac_se,
        "hac_p": hac_p,
        "hac_ci_low_pp": (
            hac_lo * 100
        ),
        "hac_ci_high_pp": (
            hac_hi * 100
        ),

        "bootstrap_median_delta": (
            boot_est
        ),
        "bootstrap_ci_low_pp": (
            boot_lo * 100
        ),
        "bootstrap_ci_high_pp": (
            boot_hi * 100
        ),
    })


# ============================================================
# RESULTS
# ============================================================

results = pd.DataFrame(rows)

target = OUT / "pre_post_final.csv"

results.to_csv(
    target,
    index=False,
)

print()
print(
    results[
        [
            "metric",
            "pre_n",
            "post_n",
            "pre_median",
            "post_median",
            "delta_median_pp",
            "mann_whitney_p",
            "hac_beta_pp",
            "hac_p",
            "bootstrap_ci_low_pp",
            "bootstrap_ci_high_pp",
        ]
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.6f}",
    )
)

print()
print("============================================================")
print("READABLE SUMMARY")
print("============================================================")

for _, r in results.iterrows():

    print()
    print(r["metric"])

    print(
        f"  PRE median   : "
        f"{100*r['pre_median']:.2f}%"
    )

    print(
        f"  POST median  : "
        f"{100*r['post_median']:.2f}%"
    )

    print(
        f"  Delta median : "
        f"{r['delta_median_pp']:+.2f} pp"
    )

    print(
        f"  Mann-Whitney : "
        f"p={r['mann_whitney_p']:.6g}"
    )

    print(
        f"  HAC mean diff: "
        f"{r['hac_beta_pp']:+.2f} pp "
        f"[{r['hac_ci_low_pp']:+.2f}, "
        f"{r['hac_ci_high_pp']:+.2f}] "
        f"p={r['hac_p']:.6g}"
    )

    print(
        f"  Block bootstrap median CI: "
        f"[{r['bootstrap_ci_low_pp']:+.2f}, "
        f"{r['bootstrap_ci_high_pp']:+.2f}] pp"
    )

print()
print("Saved ->", target)
print()
print("PASS_PRE_POST_FINAL")
