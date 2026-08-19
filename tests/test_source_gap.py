import pandas as pd
import pytest

pytestmark = [
    pytest.mark.data,
    pytest.mark.slow,
]


def test_unique_material_gap_in_btc_5m_source(root):
    path = root / "data/processed/btc_5m_etf_clock.parquet"

    ts = pd.read_parquet(
        path,
        columns=["timestamp_utc"],
    )["timestamp_utc"]

    ts = pd.to_datetime(ts, utc=True).sort_values().reset_index(drop=True)
    delta = ts.diff()

    gaps = pd.DataFrame(
        {
            "timestamp_utc": ts,
            "delta": delta,
        }
    )

    gaps = gaps[
        gaps["delta"] > pd.Timedelta(minutes=5)
    ]

    assert len(gaps) == 1

    row = gaps.iloc[0]
    assert row["timestamp_utc"] == pd.Timestamp(
        "2023-03-24 14:00:00+00:00"
    )
    assert row["delta"] == pd.Timedelta(hours=1, minutes=25)


def test_six_missing_nyse_open_bars_are_absent(root):
    path = root / "data/processed/btc_5m_etf_clock.parquet"

    ts = pd.read_parquet(
        path,
        columns=["timestamp_utc"],
    )["timestamp_utc"]

    ts = pd.DatetimeIndex(pd.to_datetime(ts, utc=True))

    expected_missing = pd.date_range(
        "2023-03-24 13:30:00+00:00",
        "2023-03-24 13:55:00+00:00",
        freq="5min",
    )

    assert len(expected_missing) == 6
    assert expected_missing.intersection(ts).empty
    assert pd.Timestamp("2023-03-24 14:00:00+00:00") in ts
