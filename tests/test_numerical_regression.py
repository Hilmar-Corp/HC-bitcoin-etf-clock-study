from pathlib import Path

import numpy as np
import pandas as pd
import pytest

pytestmark = [
    pytest.mark.data,
    pytest.mark.regression,
]


def _one(df: pd.DataFrame, **filters) -> pd.Series:
    mask = pd.Series(True, index=df.index)

    for col, value in filters.items():
        mask &= df[col] == value

    out = df.loc[mask]
    assert len(out) == 1, f"Expected one row for {filters}, found {len(out)}"
    return out.iloc[0]


def test_primary_pre_post_results(root: Path):
    df = pd.read_csv(root / "outputs/tables/pre_post_final.csv")

    expected = {
        "us_volume_share": (2.966372, 2.984087),
        "us_trade_share": (6.416955, 6.171706),
        "us_variance_share": (5.687037, 4.497129),
        "us_abs_return_share": (2.444224, 2.209769),
    }

    for metric, (median_delta, hac_delta) in expected.items():
        r = _one(df, metric=metric)

        assert np.isclose(
            r["delta_median_pp"],
            median_delta,
            atol=1e-5,
        )

        assert np.isclose(
            r["hac_beta_pp"],
            hac_delta,
            atol=1e-5,
        )


def test_detrended_turnover_volume_result(root: Path):
    df = pd.read_csv(
        root / "outputs/tables/detrended_turnover_regressions.csv"
    )

    r = _one(
        df,
        x="log_turnover",
        metric="lr_volume",
    )

    assert np.isclose(
        r["ratio_change_pct"],
        7.256090899,
        atol=1e-8,
    )

    assert np.isclose(
        r["p_value"],
        0.000667771,
        atol=5e-9,
    )


def test_detrended_residual_correlation(root: Path):
    df = pd.read_csv(
        root / "outputs/tables/detrended_residual_correlations.csv"
    )

    r = _one(
        df,
        x="log_turnover",
        metric="lr_volume",
    )

    assert np.isclose(
        r["spearman_rho"],
        0.155783191,
        atol=1e-9,
    )


def test_first_difference_reference_result(root: Path):
    df = pd.read_csv(
        root / "outputs/tables/first_difference_tests.csv"
    )

    r = _one(
        df,
        x="log_turnover",
        metric="lr_volume",
    )

    assert np.isclose(
        r["effect_pct"],
        21.139743743,
        atol=1e-8,
    )


def test_weekly_reference_result_is_null(root: Path):
    df = pd.read_csv(
        root / "outputs/tables/weekly_etf_clock_tests.csv"
    )

    r = _one(
        df,
        x="log_turnover",
        metric="lr_volume",
    )

    assert np.isclose(
        r["ratio_change_pct"],
        -0.033240880,
        atol=1e-8,
    )

    assert np.isclose(
        r["p_value"],
        0.987299973,
        atol=1e-9,
    )


def test_matched_placebo_summary_shape_and_short_window_volume(root: Path):
    df = pd.read_csv(
        root / "outputs/tables/matched_placebo_summary_v2.csv"
    )

    assert len(df) == 12
    assert set(df["half_window"]) == {63, 126, 189}

    r = _one(
        df,
        half_window=63,
        metric="us_volume_share",
    )

    assert np.isclose(
        r["actual_delta_pp"],
        4.1178,
        atol=5e-4,
    )

    assert np.isclose(
        r["empirical_upper_p"],
        0.0390,
        atol=5e-4,
    )
