from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CORE = [
    "src/analysis_01_pre_post_final.py",
    "src/analysis_02_etf_activity.py",
    "src/analysis_03_robustness.py",
    "src/analysis_04a_persist_core.py",
    "src/analysis_04b_placebos.py",
    "src/analysis_05_final_figures.py",
]

RAW_JSON = ROOT / "artifacts/coverage/analytical_core_coverage.json"
SUMMARY = ROOT / "artifacts/coverage/analytical_core_summary.json"

LINE_MIN = 90.0
BRANCH_MIN = 80.0


def run(cmd):
    env = os.environ.copy()
    env["MPLBACKEND"] = "Agg"

    print("$", " ".join(cmd))

    result = subprocess.run(
        cmd,
        cwd=ROOT,
        env=env,
        text=True,
    )

    if result.returncode != 0:
        raise SystemExit(result.returncode)


run(
    [
        sys.executable,
        "-m",
        "coverage",
        "erase",
    ]
)

for i, script in enumerate(CORE):
    cmd = [
        sys.executable,
        "-m",
        "coverage",
        "run",
        "--branch",
    ]

    if i:
        cmd.append("--append")

    cmd.append(script)

    run(cmd)


run(
    [
        sys.executable,
        "-m",
        "coverage",
        "json",
        "--include=src/analysis_*.py",
        "-o",
        str(RAW_JSON),
    ]
)


data = json.loads(
    RAW_JSON.read_text(
        encoding="utf-8"
    )
)

file_map = {}

for key, value in data["files"].items():
    normalized = key.replace("\\", "/")

    file_map[normalized] = value


per_file = {}

total_statements = 0
total_covered = 0
total_branches = 0
total_covered_branches = 0


for expected in CORE:
    matches = [
        value
        for key, value in file_map.items()
        if key.endswith(expected)
    ]

    if len(matches) != 1:
        raise SystemExit(
            f"Coverage missing for {expected}"
        )

    summary = matches[0]["summary"]

    statements = int(
        summary["num_statements"]
    )

    missing = int(
        summary["missing_lines"]
    )

    covered = statements - missing

    branches = int(
        summary.get(
            "num_branches",
            0,
        )
    )

    covered_branches = int(
        summary.get(
            "covered_branches",
            0,
        )
    )

    line_pct = (
        100.0
        if statements == 0
        else 100.0 * covered / statements
    )

    branch_pct = (
        100.0
        if branches == 0
        else 100.0
        * covered_branches
        / branches
    )

    per_file[expected] = {
        "statements": statements,
        "covered_statements": covered,
        "line_coverage_pct": line_pct,
        "branches": branches,
        "covered_branches": covered_branches,
        "branch_coverage_pct": branch_pct,
    }

    total_statements += statements
    total_covered += covered
    total_branches += branches
    total_covered_branches += covered_branches


line_pct = (
    100.0
    * total_covered
    / total_statements
)

branch_pct = (
    100.0
    if total_branches == 0
    else 100.0
    * total_covered_branches
    / total_branches
)


decision = (
    "PASS"
    if (
        line_pct >= LINE_MIN
        and branch_pct >= BRANCH_MIN
    )
    else "FAIL"
)


payload = {
    "study_id": "HILMARCORP-BITCOIN-ETF-CLOCK",
    "control": "ANALYTICAL_CORE_COVERAGE",
    "decision": decision,
    "thresholds": {
        "line_coverage_pct_min": LINE_MIN,
        "branch_coverage_pct_min": BRANCH_MIN,
    },
    "aggregate": {
        "statements": total_statements,
        "covered_statements": total_covered,
        "line_coverage_pct": line_pct,
        "branches": total_branches,
        "covered_branches": total_covered_branches,
        "branch_coverage_pct": branch_pct,
    },
    "files": per_file,
}


SUMMARY.write_text(
    json.dumps(
        payload,
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)


print()
print(
    "ANALYTICAL CORE LINE COVERAGE =",
    f"{line_pct:.2f}%",
)

print(
    "ANALYTICAL CORE BRANCH COVERAGE =",
    f"{branch_pct:.2f}%",
)

print(
    "LINE THRESHOLD =",
    f"{LINE_MIN:.2f}%",
)

print(
    "BRANCH THRESHOLD =",
    f"{BRANCH_MIN:.2f}%",
)

print(
    "ANALYTICAL CORE COVERAGE =",
    decision,
)

if decision != "PASS":
    raise SystemExit(2)

print("PASS_ANALYTICAL_CORE_COVERAGE")
