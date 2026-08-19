# Bitcoin ETF Clock Study

[![Research Assurance](https://github.com/Hilmar-Corp/HC-bitcoin-etf-clock-study/actions/workflows/research-assurance.yml/badge.svg?branch=main)](https://github.com/Hilmar-Corp/HC-bitcoin-etf-clock-study/actions/workflows/research-assurance.yml)
![Python](https://img.shields.io/badge/Python-3.13-3776AB)
![Research](https://img.shields.io/badge/research-market--microstructure-2ea44f)
![Assurance](https://img.shields.io/badge/assurance-fail--closed-2ea44f)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

**Reproducible empirical research package for Bitcoin intraday activity, US market-hour concentration and US spot Bitcoin ETF activity.**

This repository contains the empirical pipeline, controlled analytical artifacts, validation framework and publication figures for the HilmarCorp Bitcoin ETF Clock Study.

The repository is intended as a reproducible quantitative-research package rather than as a standalone editorial publication.

## Research question

Bitcoin trades continuously while US-listed spot Bitcoin ETFs trade during defined market sessions.

The study evaluates two related measurement questions:

1. whether Bitcoin activity became more concentrated during US cash-market hours after the launch of US spot Bitcoin ETFs;
2. whether post-launch Bitcoin US-hour concentration is associated with ETF market activity.

The design keeps three concepts analytically distinct:

- Bitcoin activity during NYSE cash hours;
- ETF net creations and redemptions;
- ETF secondary-market turnover.

ETF net flow is not treated as a generic measure of institutional flow.

## Research scope

Primary Bitcoin market:

    Binance Spot BTCUSDT

Bitcoin frequency:

    5 minutes

Raw Bitcoin study period:

    2022-01-11 to 2026-01-10

ETF event boundary:

    NYSE session dated 2024-01-11

Final NYSE research sample:

    501 pre-event sessions
    501 post-event sessions

Excluded NYSE session:

    2023-03-24

The excluded session contains the unique material five-minute source-data gap affecting both the US-session numerator and the 24-hour denominator.

No interpolation is used.

## Research design

For each valid NYSE session, Bitcoin activity is separated into:

    US cash-session activity
    non-US-session activity

The primary activity measures are:

    us_volume_share
    us_trade_share
    us_variance_share
    us_abs_return_share

The canonical post-event ETF variables distinguish:

    ETF net flow
    absolute ETF net flow
    ETF secondary-market turnover proxy

The study combines descriptive pre/post comparisons with robustness and persistence diagnostics.

It is not represented as a randomized experiment or a causal identification design.

## Market-calendar construction

US sessions are constructed from the actual NYSE schedule using `pandas_market_calendars`.

The canonical panel therefore respects:

- holidays;
- early closes;
- daylight-saving transitions;
- actual session opens;
- actual session closes;
- NYSE session-date classification.

Normal NYSE sessions contain 78 five-minute intervals.

Early-close sessions contain 42.

A fixed UTC approximation is not used in the canonical daily panel.

## Data handling policy

The empirical pipeline applies the following controls:

- explicit source identity;
- five-minute source continuity checks;
- no interpolation;
- no silent source substitution;
- deterministic session exclusions;
- duplicate checks;
- expected-session-bar validation;
- NYSE-calendar validation;
- pre/post sample-balance validation;
- merge uniqueness checks;
- controlled ETF-universe validation;
- explicit distinction between ETF flows and ETF turnover;
- reproducible numerical regression checks.

Material data-contract violations fail closed.

## ETF turnover construction

For each validated ETF with market observations:

    typical_price
    = (high + low + close) / 3

    dollar_turnover_proxy
    = share_volume × typical_price

The daily cross-fund sum is used as a secondary-market trading-intensity proxy.

It is not represented as exact transaction-level dollar volume.

## Research modules

### Bitcoin acquisition

Downloads monthly Binance BTCUSDT spot five-minute observations.

Canonical script:

    src/download_binance.py

### Five-minute Bitcoin dataset

Builds the controlled intraday Bitcoin dataset used by downstream transformations.

Canonical script:

    src/build_dataset.py

### ETF flow acquisition

Acquires and parses daily US spot Bitcoin ETF flow observations.

Canonical script:

    src/download_etf_flows.py

### NYSE daily panel

Constructs the session-aware daily Bitcoin activity panel.

Canonical script:

    src/build_daily_us_panel.py

### ETF master panel

Builds the validated ETF market panel and merges ETF activity with Bitcoin session metrics.

Canonical script:

    src/build_etf_master_panel.py

### Pre/post analysis

Canonical script:

    src/analysis_01_pre_post_final.py

### ETF activity analysis

Canonical script:

    src/analysis_02_etf_activity.py

### Robustness analysis

Canonical script:

    src/analysis_03_robustness.py

### Persistence analysis

Canonical script:

    src/analysis_04a_persist_core.py

### Matched placebo analysis

Canonical script:

    src/analysis_04b_placebos.py

### Publication figures

Canonical script:

    src/analysis_05_final_figures.py

The authoritative executable scope is recorded in:

    config/canonical_scripts.txt

Historical exploratory scripts outside that registry are not part of the canonical assurance path.

## Controlled publication artifacts

Derived publication tables are stored in:

    artifacts/tables/

Publication figures are stored in:

    artifacts/figures/

The frozen publication bundle contains 17 controlled artifacts.

Artifact identities are recorded in:

    PUBLICATION_MANIFEST.json

The analytical tables contain the published empirical estimates and robustness results.

The README does not act as the research note itself.

## Research assurance

The repository uses a fail-closed assurance model.

The controlled local research state includes:

    Scientific baseline freeze
    Repository contract
    Data-quality contracts
    Static linting
    Python compilation
    Deterministic tests
    Hashed dependency locks
    Clean-room environment validation
    ETF offline semantic replay
    Frozen repository evidence

Public snapshot verification:

    make assurance

Full local-data assurance:

    make assurance-local

The frozen local test suite contains:

    26 deterministic research tests

The public snapshot test suite contains:

    5 deterministic publication tests

Detailed assurance documentation:

    RESEARCH_ASSURANCE.md

## Frozen evidence

Repository-level evidence is stored in:

    evidence/repository_evidence.json

The registry records SHA-256 identities for controlled:

- source code;
- tests;
- configuration;
- documentation;
- derived analytical artifacts;
- publication figures;
- assurance metadata.

A controlled-file modification invalidates the frozen repository snapshot until the evidence registry is intentionally regenerated.

Verify the current snapshot with:

    python -m scripts.research.verify_repository

Expected result:

    REPOSITORY ASSURANCE: PASS

## Repository structure

    .
    ├── .github/
    │   └── workflows/
    │       └── research-assurance.yml
    ├── artifacts/
    │   ├── figures/
    │   └── tables/
    ├── config/
    │   ├── canonical_scripts.txt
    │   └── research_spec.json
    ├── docs/
    ├── evidence/
    │   ├── repository_evidence.json
    │   └── research_assurance_snapshot.json
    ├── requirements/
    ├── scripts/
    │   └── research/
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
    ├── REPRODUCIBILITY.md
    ├── RESEARCH_ASSURANCE.md
    ├── research_contract.json
    └── source_registry.json

## Installation

Controlled runtime:

    Python 3.13.0

Create an isolated environment:

    python3.13 -m venv .venv
    source .venv/bin/activate

Install the controlled development environment:

    python -m pip install --require-hashes -r requirements/dev.lock.txt
    python -m pip check

## Static assurance

Run:

    python -m ruff check $(cat config/canonical_scripts.txt) tests tests_public scripts

Compile the canonical research scope:

    python -m py_compile $(cat config/canonical_scripts.txt)

## Tests

Public deterministic tests:

    python -m pytest -q tests_public

Full internal-data test suite:

    python -m pytest -q tests

## Complete local assurance

Run:

    make assurance-local

A valid local publication state requires:

    REPOSITORY ASSURANCE: PASS
    26 / 26 local tests passed

## Full empirical reconstruction

A full empirical rerun requires the relevant third-party source data or source reacquisition.

The canonical sequence is:

    python src/download_binance.py
    python src/build_dataset.py
    python src/download_etf_flows.py
    python src/build_daily_us_panel.py
    python src/build_etf_master_panel.py --offline
    python src/analysis_01_pre_post_final.py
    python src/analysis_02_etf_activity.py
    python src/analysis_03_robustness.py
    python src/analysis_04a_persist_core.py
    python src/analysis_04b_placebos.py
    python src/analysis_05_final_figures.py

See:

    REPRODUCIBILITY.md

for the detailed reconstruction protocol and source limitations.

## GitHub Research Assurance

Every push to `main`, pull request and manual workflow dispatch runs the repository Research Assurance workflow.

The workflow validates:

- controlled dependency installation;
- canonical-script presence;
- Ruff linting;
- Python compilation;
- deterministic public tests;
- frozen SHA-256 repository evidence;
- publication artifact integrity.

Generated assurance evidence is uploaded as a GitHub Actions artifact.

## Data provenance and third-party rights

Complete third-party raw and processed market-data caches are intentionally excluded from public Git history.

The repository supports two distinct forms of reproducibility:

1. **Frozen-output verification** — exact validation of committed code, derived artifacts, figures and SHA-256 evidence.
2. **Methodological reconstruction** — reacquisition of source data followed by rerunning the documented empirical pipeline.

Third-party market data remain subject to the rights, terms and restrictions of the relevant providers.

See:

    DATA_PROVENANCE.md
    DATA_NOTICE.md

## Interpretation limits

This repository contains descriptive and quasi-experimental empirical research.

It does not establish:

- causal effects of ETF launch;
- universal Bitcoin market structure across all venues;
- predictive power;
- future return forecasts;
- trading profitability;
- optimal execution;
- institutional investor intent.

Results remain conditional on:

- the selected Bitcoin venue;
- the study period;
- the available ETF observations;
- the NYSE session definition;
- the selected activity measures;
- the documented statistical controls.

Statistical significance must not be interpreted as economic predictability.

## Research governance

The repository is designed to preserve:

- reproducibility;
- source traceability;
- explicit methodological conventions;
- controlled exclusions;
- deterministic testing;
- evidence integrity;
- versioned analytical outputs;
- fail-closed assurance;
- resistance to unsupported editorial claims.

The repository does not claim certification or endorsement by any external asset manager, benchmark administrator or quantitative investment firm.

## Citation

Citation metadata are provided in:

    CITATION.cff

## License

Original HilmarCorp code, tests, automation and documentation are released under the Apache License 2.0.

See:

    LICENSE
    NOTICE

Third-party market data are outside the Apache-2.0 grant.

## Disclaimer

This repository is provided for quantitative research and educational purposes.

Nothing in this repository constitutes investment advice, a recommendation, a forecast, investment management, order execution, a solicitation, or an offer to buy or sell a financial instrument or digital asset.

Historical observations are not indicative of future outcomes.
