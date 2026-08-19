import pandas as pd
import pytest

pytestmark = pytest.mark.data


def test_master_panel_is_complete_post_etf(master_panel):
    assert len(master_panel) == 501
    assert master_panel["date"].nunique() == 501
    assert master_panel["date"].duplicated().sum() == 0

    assert master_panel["date"].min() == pd.Timestamp("2024-01-11")
    assert master_panel["date"].max() == pd.Timestamp("2026-01-09")

    assert master_panel["etf_net_flow_musd"].notna().all()
    assert master_panel["etf_turnover_proxy_usd"].notna().all()


def test_master_panel_flow_sign_counts(master_panel):
    flow = master_panel["etf_net_flow_musd"]

    assert int((flow > 0).sum()) == 314
    assert int((flow < 0).sum()) == 187
    assert int((flow == 0).sum()) == 0


def test_master_panel_active_etf_counts(master_panel):
    counts = master_panel["active_etfs"].value_counts().to_dict()
    assert counts == {
        10: 138,
        11: 363,
    }
