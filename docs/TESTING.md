# Testing and validation

The test harness is intentionally layered.

- Contract tests validate the frozen research specification and canonical/non-canonical registry.
- Data-contract tests validate sample geometry, date uniqueness, breakpoint treatment, session completeness and bounded shares.
- Calendar tests validate NYSE normal sessions, early closes, holidays and DST behavior.
- Source-gap tests independently verify the unique material 5-minute gap underlying the 2023-03-24 exclusion.
- Numerical regression tests validate frozen publication-level results within explicit tolerances.

These tests do not establish causal validity, data redistribution rights, or independent model validation.
They establish internal reproducibility and non-regression of the current research state.
