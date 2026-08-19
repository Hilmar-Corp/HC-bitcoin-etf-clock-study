# Reproducibility

The project distinguishes frozen-output verification from empirical data reacquisition.

## Public frozen verification

Raw and processed third-party market datasets are not required.

Install the controlled development environment:

    python3.13 -m venv .venv
    source .venv/bin/activate
    python -m pip install --require-hashes -r requirements/dev.lock.txt
    python -m pip check

Run:

    make assurance

The public gate checks:

1. Ruff;
2. Python compilation;
3. deterministic public snapshot tests;
4. publication artifact SHA-256 identities;
5. repository SHA-256 evidence;
6. publication-level numerical invariants;
7. absence of forbidden tracked raw-data directories.

## Local full-data assurance

When the internal research data are available:

    make assurance-local

This adds the complete local research test suite.

Current frozen local result:

    26 passed

## Canonical empirical sequence

The research workflow is divided into acquisition, transformation and analysis.

Bitcoin acquisition:

    python src/download_binance.py

Bitcoin five-minute construction:

    python src/build_dataset.py

ETF flow acquisition/parsing:

    python src/download_etf_flows.py

NYSE daily panel:

    python src/build_daily_us_panel.py

ETF market/master panel:

    python src/build_etf_master_panel.py --offline

The `--offline` mode uses the validated local ETF raw cache and does not request new yfinance observations.

Analyses:

    python src/analysis_01_pre_post_final.py
    python src/analysis_02_etf_activity.py
    python src/analysis_03_robustness.py
    python src/analysis_04a_persist_core.py
    python src/analysis_04b_placebos.py
    python src/analysis_05_final_figures.py

Some historical exploratory scripts remain in the repository for provenance but are not part of the canonical execution path.

See `docs/CANONICAL_PIPELINE.md`.

## Network-data caveat

A live reacquisition is methodological reproduction, not necessarily byte-identical snapshot reproduction.

Providers can revise historical observations, page structure or metadata.

The frozen public research package therefore uses derived artifacts and cryptographic evidence as the publication reference.

## ETF raw-cache precision

The historical yfinance cache was serialized to CSV.

The validated offline reconstruction therefore uses strict numerical rather than byte-level equivalence.

Future internal acquisitions should preserve a lossless raw representation.
