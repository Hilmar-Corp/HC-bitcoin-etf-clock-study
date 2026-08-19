import pandas as pd
import pytest

pytestmark = pytest.mark.data


PRIMARY_SHARES = [
    "us_volume_share",
    "us_trade_share",
    "us_variance_share",
    "us_abs_return_share",
]


def test_daily_panel_shape_and_balance(daily_panel):
    assert len(daily_panel) == 1002
    assert daily_panel["date"].nunique() == 1002
    assert daily_panel["date"].duplicated().sum() == 0

    counts = daily_panel["period"].value_counts().to_dict()
    assert counts == {
        "pre_etf": 501,
        "post_etf": 501,
    }


def test_event_boundary_is_session_date_based(daily_panel):
    jan10 = daily_panel.loc[
        daily_panel["date"] == pd.Timestamp("2024-01-10"),
        "period",
    ]
    jan11 = daily_panel.loc[
        daily_panel["date"] == pd.Timestamp("2024-01-11"),
        "period",
    ]

    assert len(jan10) == 1
    assert len(jan11) == 1
    assert jan10.iloc[0] == "pre_etf"
    assert jan11.iloc[0] == "post_etf"


def test_known_bad_session_is_excluded(daily_panel):
    assert not (
        daily_panel["date"] == pd.Timestamp("2023-03-24")
    ).any()


def test_nyse_session_bar_counts_are_exact(daily_panel):
    assert (
        daily_panel["us_bars"]
        == daily_panel["expected_us_bars"]
    ).all()

    counts = (
        daily_panel[["expected_us_bars", "us_bars"]]
        .value_counts()
        .to_dict()
    )

    assert counts == {
        (42.0, 42): 9,
        (78.0, 78): 993,
    }


@pytest.mark.parametrize("col", PRIMARY_SHARES)
def test_primary_shares_are_bounded_and_finite(daily_panel, col):
    s = daily_panel[col]
    assert s.notna().all()
    assert ((s >= 0.0) & (s <= 1.0)).all()


def test_component_sums_are_coherent(daily_panel):
    assert (
        daily_panel["us_quote_volume"]
        <= daily_panel["total_quote_volume"]
    ).all()

    assert (
        daily_panel["us_trades"]
        <= daily_panel["total_trades"]
    ).all()

    assert (
        daily_panel["us_variance"]
        <= daily_panel["total_variance"]
    ).all()

    assert (
        daily_panel["us_abs_return"]
        <= daily_panel["total_abs_return"]
    ).all()
