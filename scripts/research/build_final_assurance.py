from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

OUT_DIR = (
    ROOT
    / "artifacts/final_assurance"
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def load(path):
    return json.loads(
        (ROOT / path).read_text(
            encoding="utf-8"
        )
    )


def command(name, cmd):
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    output = (
        result.stdout
        + "\n"
        + result.stderr
    )

    passed = re.search(
        r"(\d+) passed",
        output,
    )

    if passed:
        detail = (
            f"{passed.group(1)} passed"
        )
    elif (
        "No broken requirements found."
        in output
    ):
        detail = (
            "No broken requirements found."
        )
    else:
        detail = (
            f"exit_code={result.returncode}"
        )

    return {
        "name": name,
        "required": True,
        "status": (
            "PASS"
            if result.returncode == 0
            else "FAIL"
        ),
        "detail": detail,
    }


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

publication = load(
    "PUBLICATION_MANIFEST.json"
)

snapshot = load(
    "evidence/"
    "research_assurance_snapshot.json"
)


checks = []


checks.append(
    {
        "name": (
            "publication_artifact_manifest"
        ),
        "required": True,
        "status": (
            "PASS"
            if publication[
                "artifact_count"
            ]
            == 17
            else "FAIL"
        ),
        "detail": (
            f"{publication['artifact_count']} "
            "frozen publication artifacts"
        ),
    }
)


checks.append(
    {
        "name": (
            "analytical_core_coverage"
        ),
        "required": True,
        "status": coverage[
            "decision"
        ],
        "detail": (
            "line="
            f"{coverage['aggregate']['line_coverage_pct']:.2f}% "
            "branch="
            f"{coverage['aggregate']['branch_coverage_pct']:.2f}%"
        ),
    }
)


checks.append(
    {
        "name": (
            "coinbase_multi_venue_sensitivity"
        ),
        "required": True,
        "status": coinbase[
            "decision"
        ],
        "detail": (
            "Binance/Coinbase "
            "cross-venue sensitivity"
        ),
    }
)


checks.append(
    {
        "name": (
            "etf_market_source_spot_check"
        ),
        "required": True,
        "status": blackrock[
            "decision"
        ],
        "detail": (
            "IBIT official issuer volume "
            "vs yfinance current-date spot-check"
        ),
    }
)


checks.append(
    {
        "name": (
            "clean_room_environment"
        ),
        "required": True,
        "status": snapshot[
            "controls"
        ][
            "clean_room_environment"
        ][
            "status"
        ],
        "detail": (
            "Python 3.13.0 controlled "
            "dependency reconstruction"
        ),
    }
)


checks.append(
    {
        "name": (
            "hashed_dependency_locks"
        ),
        "required": True,
        "status": snapshot[
            "controls"
        ][
            "hashed_dependency_locks"
        ],
        "detail": (
            "transitive dependency "
            "hash controls"
        ),
    }
)


checks.append(
    {
        "name": (
            "etf_offline_semantic_replay"
        ),
        "required": True,
        "status": snapshot[
            "controls"
        ][
            "etf_offline_semantic_replay"
        ][
            "status"
        ],
        "detail": (
            "strict numerical replay "
            "of ETF local cache"
        ),
    }
)


checks.append(
    command(
        "public_tests",
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests_public",
        ],
    )
)


local_test = command(
    "local_research_tests",
    [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "tests",
    ],
)

match = re.search(
    r"(\d+) passed",
    local_test["detail"],
)

if (
    local_test["status"] == "PASS"
    and (
        match is None
        or int(match.group(1)) != 26
    )
):
    local_test["status"] = "FAIL"

checks.append(local_test)


checks.append(
    command(
        "pip_check",
        [
            sys.executable,
            "-m",
            "pip",
            "check",
        ],
    )
)


required_failed = [
    item["name"]
    for item in checks
    if (
        item["required"]
        and item["status"] != "PASS"
    )
]


decision = (
    "PASS"
    if not required_failed
    else "FAIL"
)


payload = {
    "study_id": (
        "HILMARCORP-BITCOIN-ETF-CLOCK"
    ),
    "assurance_version": "2.0.0",
    "decision": decision,
    "required_controls": len(
        [
            x
            for x in checks
            if x["required"]
        ]
    ),
    "passed_required_controls": len(
        [
            x
            for x in checks
            if (
                x["required"]
                and x["status"] == "PASS"
            )
        ]
    ),
    "failed_required_controls": (
        required_failed
    ),
    "checks": checks,
}


decision_path = (
    OUT_DIR
    / "consolidated_decision.json"
)

decision_path.write_text(
    json.dumps(
        payload,
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)


with (
    OUT_DIR
    / "assurance_checks.csv"
).open(
    "w",
    newline="",
    encoding="utf-8",
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "name",
            "required",
            "status",
            "detail",
        ],
        lineterminator="\n",
    )

    writer.writeheader()
    writer.writerows(checks)


print()
print(
    "FINAL RESEARCH ASSURANCE:",
    decision,
)

print(
    payload[
        "passed_required_controls"
    ],
    "/",
    payload[
        "required_controls"
    ],
    "required controls passed",
)

if required_failed:
    print(
        "FAILED:",
        required_failed,
    )

if decision != "PASS":
    raise SystemExit(2)

print(
    "PASS_FINAL_RESEARCH_ASSURANCE"
)
