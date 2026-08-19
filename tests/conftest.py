from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def daily_panel(root: Path) -> pd.DataFrame:
    path = root / "data/processed/btc_daily_nyse_panel.parquet"
    assert path.exists(), f"Missing required dataset: {path}"
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


@pytest.fixture(scope="session")
def master_panel(root: Path) -> pd.DataFrame:
    path = root / "data/processed/btc_etf_master_panel.parquet"
    assert path.exists(), f"Missing required dataset: {path}"
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)
