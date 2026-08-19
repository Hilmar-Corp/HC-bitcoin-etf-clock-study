# Bitcoin ETF Clock Study

[![Research Assurance](https://github.com/Hilmar-Corp/HC-bitcoin-etf-clock-study/actions/workflows/research-assurance.yml/badge.svg?branch=main)](https://github.com/Hilmar-Corp/HC-bitcoin-etf-clock-study/actions/workflows/research-assurance.yml)
![Python](https://img.shields.io/badge/Python-3.13-3776AB)
![Research](https://img.shields.io/badge/research-market--microstructure-2ea44f)
![Assurance](https://img.shields.io/badge/assurance-fail--closed-2ea44f)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

**Reproducible empirical study of Bitcoin activity concentration during US market hours and its relationship with US spot Bitcoin ETF trading.**

This repository contains the research pipeline, controlled analytical artifacts, validation framework and publication figures supporting a HilmarCorp Research note on whether the arrival of US spot Bitcoin ETFs coincided with a change in Bitcoin's intraday activity clock.

The repository is a quantitative-research package rather than a trading model or investment strategy.

## Research question

Bitcoin trades continuously.

US-listed spot Bitcoin ETFs do not.

The study asks:

> Did Bitcoin activity become more concentrated during US cash-market hours after January 11, 2024, and is that concentration associated with ETF trading activity?

The empirical design keeps three concepts separate:

1. Bitcoin activity during NYSE cash hours;
2. ETF net creations/redemptions;
3. ETF secondary-market trading turnover.

ETF net flow is not treated as generic institutional flow.

## Research scope

Primary Bitcoin source:

    Binance Spot BTCUSDT

Frequency:

    5 minutes

Raw Bitcoin horizon:

    2022-01-11 through 2026-01-10

ETF event boundary:

    NYSE session dated 2024-01-11

Final NYSE sample:

    501 pre-ETF sessions
    501 post-ETF sessions

Excluded session:

    2023-03-24

The excluded date contains the unique material source-data gap affecting both the US-session numerator and the daily denominator.

No interpolation is used.

## Published pre/post snapshot

| Metric | Pre median | Post median | Median change |
|---|---:|---:|---:|
| US volume share | 37.33% | 40.29% | +2.97 pp |
| US trade share | 35.27% | 41.69% | +6.42 pp |
| US variance share | 41.93% | 47.61% | +5.69 pp |
| US absolute-return share | 34.81% | 37.25% | +2.44 pp |

The long-window shift toward US hours is statistically clear.

The study does **not** find evidence of a clean instantaneous launch-day structural break.

## ETF activity result

Contemporaneous ETF net flows show little robust relationship with the Bitcoin US-hour concentration measures.

ETF secondary-market turnover is more informative.

After controlling for linear and quadratic time trends and weekday fixed effects, a one-standard-deviation increase in log ETF turnover is associated with approximately:

    +7.26%

in the Bitcoin US/non-US volume ratio.

Frozen estimate:

    95% CI: +3.01% to +11.67%
    p ≈ 0.000668
    n = 501

This is a contemporaneous descriptive association.

It is not a causal estimate and it is not a predictive signal.

Weekly aggregation does not preserve the volume result, which materially limits interpretation of the daily association.

## Market-calendar controls

US sessions use the actual NYSE schedule through `pandas_market_calendars`.

The pipeline therefore respects:

- holidays;
- early closes;
- daylight-saving transitions;
- session-date classification.

Normal NYSE sessions contain 78 five-minute intervals.

Early-close sessions contain 42.

## ETF turnover construction

For each available ETF:

    typical_price
    = (high + low + close) / 3

    dollar_turnover_proxy
    = share_volume × typical_price

The cross-fund daily sum is used as a proxy for secondary-market trading intensity.

It is not described as exact dollar trading volume.

## Robustness framework

The research package includes:

- symmetric pre/post windows;
- Mann-Whitney comparisons;
- HAC/Newey-West inference;
- block-bootstrap confidence intervals;
- interrupted time-series diagnostics;
- matched historical placebo breakpoints;
- linear and quadratic time detrending;
- weekday fixed effects;
- residual correlations;
- first-difference diagnostics;
- weekly aggregation;
- intraday turnover-quartile analysis.

Exploratory results are not represented as preregistered causal endpoints.

## Research assurance

The frozen local research state records:

    Scientific baseline: PASS
    Repository contract: PASS
    Ruff: PASS
    pytest: 26 / 26 PASS
    pip check: PASS
    Hashed dependency locks: PASS
    Lock semantic determinism: PASS
    Clean-room environment: PASS
    ETF offline semantic replay: PASS

The public repository also contains SHA-256 evidence for controlled files and publication artifacts.

Verify the public snapshot with:

    make assurance

Run the full local-data test suite when the internal research datasets are available:

    make assurance-local

See:

- `RESEARCH_ASSURANCE.md`
- `REPRODUCIBILITY.md`
- `DATA_PROVENANCE.md`
- `DATA_NOTICE.md`
- `PUBLICATION_MANIFEST.json`

## Frozen publication artifacts

Controlled derived tables are stored in:

    artifacts/tables/

Publication figures are stored in:

    artifacts/figures/

The current package contains 17 frozen publication artifacts.

Their SHA-256 identities are recorded in:

    PUBLICATION_MANIFEST.json

Repository-wide controlled evidence is stored in:

    evidence/repository_evidence.json

## Data policy

Complete third-party raw and processed market-data caches are deliberately excluded from public Git history.

The repository contains code, methodology, validation logic, derived research tables, figures and cryptographic evidence.

See `DATA_NOTICE.md`.

## Reproducibility model

Two different claims are maintained.

### Frozen-output verification

The public repository can independently verify the exact published code/artifact snapshot without redistributing complete third-party market data.

### Empirical reconstruction

Users with lawful access to the required source data may rerun the documented acquisition and transformation pipeline.

Network reacquisition can differ from the frozen snapshot if a provider revises historical data.

## Interpretation limits

This research does not establish:

- causality from ETF launch to Bitcoin activity;
- a universal Bitcoin market structure result across all venues;
- predictive power;
- future returns;
- trading profitability;
- optimal execution;
- institutional investor intent.

The primary Bitcoin activity source is Binance Spot BTCUSDT.

ETF-flow data are a secondary-source proxy.

ETF market observations are sourced through `yfinance` and should be validated against official or licensed sources where institutional publication standards require it.

## Repository structure

    .
    ├── .github/workflows/
    ├── artifacts/
    │   ├── figures/
    │   └── tables/
    ├── config/
    ├── docs/
    ├── evidence/
    ├── requirements/
    ├── scripts/research/
    ├── src/
    ├── tests/
    ├── tests_public/
    ├── CITATION.cff
    ├── DATA_NOTICE.md
    ├── DATA_PROVENANCE.md
    ├── LICENSE
    ├── Makefile
    ├── NOTICE
    ├── PUBLICATION_MANIFEST.json
    ├── README.md
    ├── REPRODUCIBILITY.md
    ├── RESEARCH_ASSURANCE.md
    ├── research_contract.json
    └── source_registry.json

## License

Original HilmarCorp code, tests, automation and documentation are released under the Apache License 2.0.

Third-party market data are outside that grant.

## Disclaimer

This repository is provided for quantitative research and educational purposes.

Nothing in this repository constitutes investment advice, a recommendation, investment management, a forecast, order execution, a solicitation, or an offer to buy or sell a financial instrument or digital asset.

Historical observations are not indicative of future outcomes.
