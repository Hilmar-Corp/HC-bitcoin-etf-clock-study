from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads(
        (ROOT / path).read_text(
            encoding="utf-8"
        )
    )


coverage = load(
    "artifacts/coverage/"
    "analytical_core_summary.json"
)

coinbase = load(
    "artifacts/multi_venue/"
    "coinbase_validation.json"
)

blackrock = load(
    "artifacts/source_validation/"
    "blackrock_ibit_current_volume_validation.json"
)

final = load(
    "artifacts/final_assurance/"
    "consolidated_decision.json"
)


assert coverage["decision"] == "PASS"

assert (
    coverage["aggregate"][
        "line_coverage_pct"
    ]
    >= coverage["thresholds"][
        "line_coverage_pct_min"
    ]
)

assert (
    coverage["aggregate"][
        "branch_coverage_pct"
    ]
    >= coverage["thresholds"][
        "branch_coverage_pct_min"
    ]
)

assert coinbase["decision"] == "PASS"

assert blackrock["decision"] == "PASS"

assert final["decision"] == "PASS"

assert (
    final["passed_required_controls"]
    == final["required_controls"]
)


print(
    "Analytical-core coverage: PASS"
)

print(
    "Multi-venue sensitivity: PASS"
)

print(
    "ETF source validation: PASS"
)

print(
    "Consolidated assurance: PASS"
)

print(
    "QUANT DD ASSURANCE: PASS"
)
