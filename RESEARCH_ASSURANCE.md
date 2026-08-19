# Research Assurance

## Objective

The assurance layer is designed to keep published analytical conclusions traceable to controlled transformations, deterministic tests and versioned evidence.

## Current frozen decision

    RESEARCH ASSURANCE: PASS

Local validated controls include:

| Control | State |
|---|---|
| Scientific baseline freeze | PASS |
| Repository contract | PASS |
| Data-quality contracts | PASS |
| Ruff | PASS |
| pytest | 26 / 26 PASS |
| `pip check` | PASS |
| Hashed dependency locks | PASS |
| Lock semantic determinism | PASS |
| Fresh clean-room environment | PASS |
| ETF local-cache semantic replay | PASS |

## Fail-closed principle

Required controls are not silently ignored.

Material violations of session geometry, merge uniqueness, dependency integrity, expected ETF universe or frozen artifact identity produce a failed assurance decision.

## Calendar and sample controls

The final Bitcoin daily panel contains:

    1,002 NYSE sessions
    501 pre-ETF
    501 post-ETF

The NYSE session dated 2023-03-24 is excluded because the underlying five-minute source contains six missing US-session bars inside a unique 1h25 source discontinuity.

No interpolation is performed.

## Dependency assurance

Reference environment:

    Python 3.13.0

Dependencies are frozen with transitive pins and SHA-256 package hashes.

A new virtual environment successfully installed the development lock using `--require-hashes`, then passed:

    pip check
    Ruff
    26 pytest tests

## ETF replay finding DR-001

The historical ETF market cache is CSV.

Re-reading decimal values from CSV cannot necessarily reproduce the identical original IEEE-754 representation held in memory at acquisition time.

Observed replay differences were at machine precision, with maximum relative differences below approximately `4.4e-16`.

The downstream ETF aggregate and 501-row master research panel reproduced.

The accepted offline replay tolerance is:

    rtol = 1e-12
    atol = 1e-12

Future internal acquisitions should preserve lossless raw Parquet snapshots.

## Evidence integrity

Publication artifact hashes:

    PUBLICATION_MANIFEST.json

Repository-level controlled-file hashes:

    evidence/repository_evidence.json

A controlled-file modification invalidates the frozen repository snapshot until evidence is intentionally regenerated.

## Scientific assurance limits

Software assurance does not provide causal identification.

The study remains exposed to common shocks, macro conditions, Bitcoin regime effects, venue composition, the 2024 halving, ETF anticipation and other contemporaneous market changes.

No external asset manager, benchmark administrator or quantitative investment firm has certified this repository.

## Quant DD consolidated assurance

The institutional research-review layer adds four controls to the existing repository assurance framework:

1. executable coverage of the canonical analytical scripts;
2. full-window Coinbase BTC-USD sensitivity against the primary Binance design;
3. independent current-date IBIT market-volume validation against BlackRock/iShares;
4. a consolidated fail-closed assurance decision.

The canonical decision artifact is:

    artifacts/final_assurance/consolidated_decision.json

The associated control table is:

    artifacts/final_assurance/assurance_checks.csv

Analytical-core coverage is measured by executing the canonical analysis scripts against the controlled local research data.

The public repository does not redistribute the Coinbase or Nasdaq raw observations used for independent validation.
