# Bitcoin ETF Clock — Canonical Research Pipeline

Canonical execution path before refactor.

## Data path

Binance ZIP -> build_dataset.py -> btc_5m_etf_clock.parquet -> build_daily_us_panel.py -> btc_daily_nyse_panel.parquet

Farside -> download_etf_flows.py -> bitcoin_etf_flows_daily.parquet

ETF market observations -> build_etf_master_panel.py -> btc_etf_master_panel.parquet

## Analysis path

- analysis_01_pre_post_final.py
- analysis_02_etf_activity.py
- analysis_03_robustness.py (refactor required)
- analysis_04a_persist_core.py
- analysis_04b_placebos.py
- analysis_05_final_figures.py

## Do not run

- analysis_01_us_clock.py
- analysis_04_detrended.py
- download_etf_market.py
- figure_01_intraday_volume.py

## Governance

2023-03-24 is excluded for source-data incompleteness. No interpolation.
2024-01-11 is a descriptive event boundary, not causal identification.
ETF net flows and ETF turnover must not be conflated.
Raw and processed market data are not public-commit eligible before data-rights review.
