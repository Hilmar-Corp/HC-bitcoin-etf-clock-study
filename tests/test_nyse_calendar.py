import pandas as pd
import pandas_market_calendars as mcal
import pytest

pytestmark = pytest.mark.data


def test_normal_and_early_close_session_lengths():
    nyse = mcal.get_calendar("NYSE")

    schedule = nyse.schedule(
        start_date="2024-11-27",
        end_date="2024-11-29",
    )

    normal = schedule.loc[pd.Timestamp("2024-11-27")]
    early = schedule.loc[pd.Timestamp("2024-11-29")]

    normal_bars = int(
        (normal["market_close"] - normal["market_open"]).total_seconds()
        / 300
    )
    early_bars = int(
        (early["market_close"] - early["market_open"]).total_seconds()
        / 300
    )

    assert normal_bars == 78
    assert early_bars == 42


def test_christmas_is_not_nyse_session():
    nyse = mcal.get_calendar("NYSE")
    schedule = nyse.schedule(
        start_date="2024-12-25",
        end_date="2024-12-25",
    )
    assert schedule.empty


def test_dst_shift_changes_utc_open_but_not_local_session_length():
    nyse = mcal.get_calendar("NYSE")

    schedule = nyse.schedule(
        start_date="2024-03-08",
        end_date="2024-03-11",
    )

    pre_dst = schedule.loc[pd.Timestamp("2024-03-08")]
    post_dst = schedule.loc[pd.Timestamp("2024-03-11")]

    assert pre_dst["market_open"].hour == 14
    assert post_dst["market_open"].hour == 13

    for row in (pre_dst, post_dst):
        bars = int(
            (row["market_close"] - row["market_open"]).total_seconds()
            / 300
        )
        assert bars == 78
