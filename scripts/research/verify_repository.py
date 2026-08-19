from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

from scripts.research.repository_control import (
    controlled_files,
)

ROOT = Path(__file__).resolve().parents[2]

PUBLICATION = (
    ROOT / "PUBLICATION_MANIFEST.json"
)

EVIDENCE = (
    ROOT
    / "evidence"
    / "repository_evidence.json"
)

ASSURANCE = (
    ROOT
    / "evidence"
    / "research_assurance_snapshot.json"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def rows(name: str) -> list[dict[str, str]]:
    path = (
        ROOT
        / "artifacts"
        / "tables"
        / name
    )

    with path.open(
        newline="",
        encoding="utf-8",
    ) as f:
        return list(
            csv.DictReader(f)
        )


def select(
    data: list[dict[str, str]],
    **filters: str,
) -> dict[str, str]:
    matches = [
        row
        for row in data
        if all(
            str(row[key])
            == str(value)
            for key, value
            in filters.items()
        )
    ]

    if len(matches) != 1:
        raise AssertionError(
            f"Expected one row for "
            f"{filters}; found "
            f"{len(matches)}"
        )

    return matches[0]


publication = json.loads(
    PUBLICATION.read_text(
        encoding="utf-8"
    )
)

if publication[
    "artifact_count"
] != 17:
    raise AssertionError(
        "Unexpected publication "
        "artifact count"
    )

for item in publication["artifacts"]:
    path = ROOT / item["path"]

    if not path.is_file():
        raise AssertionError(
            f"Missing artifact: {path}"
        )

    if path.stat().st_size != item["bytes"]:
        raise AssertionError(
            f"Artifact size drift: {path}"
        )

    if sha256(path) != item["sha256"]:
        raise AssertionError(
            f"Artifact hash drift: {path}"
        )


evidence = json.loads(
    EVIDENCE.read_text(
        encoding="utf-8"
    )
)

current = {
    str(
        path.relative_to(ROOT)
    ): sha256(path)
    for path in controlled_files(ROOT)
}

frozen = evidence["files"]

if set(current) != set(frozen):
    missing = sorted(
        set(frozen) - set(current)
    )
    extra = sorted(
        set(current) - set(frozen)
    )

    raise AssertionError(
        "Controlled file-set drift | "
        f"missing={missing} | "
        f"extra={extra}"
    )

for path, expected in frozen.items():
    actual = current[path]

    if actual != expected:
        raise AssertionError(
            f"Repository hash drift: "
            f"{path}"
        )


assurance = json.loads(
    ASSURANCE.read_text(
        encoding="utf-8"
    )
)

if assurance["decision"] != "PASS":
    raise AssertionError(
        "Frozen research assurance "
        "is not PASS"
    )

if assurance[
    "controls"
][
    "pytest_local"
][
    "passed"
] != 26:
    raise AssertionError(
        "Unexpected local pytest "
        "snapshot"
    )


pre_post = rows(
    "pre_post_final.csv"
)

expected_pre_post = {
    "us_volume_share": (
        2.966372,
        2.984087,
    ),
    "us_trade_share": (
        6.416955,
        6.171706,
    ),
    "us_variance_share": (
        5.687037,
        4.497129,
    ),
    "us_abs_return_share": (
        2.444224,
        2.209769,
    ),
}

for metric, (
    median_delta,
    hac_delta,
) in expected_pre_post.items():
    row = select(
        pre_post,
        metric=metric,
    )

    if int(row["pre_n"]) != 501:
        raise AssertionError(metric)

    if int(row["post_n"]) != 501:
        raise AssertionError(metric)

    if not math.isclose(
        float(
            row["delta_median_pp"]
        ),
        median_delta,
        abs_tol=1e-5,
    ):
        raise AssertionError(metric)

    if not math.isclose(
        float(
            row["hac_beta_pp"]
        ),
        hac_delta,
        abs_tol=1e-5,
    ):
        raise AssertionError(metric)


detrended = rows(
    "detrended_turnover_regressions.csv"
)

row = select(
    detrended,
    x="log_turnover",
    metric="lr_volume",
)

checks = {
    "ratio_change_pct": 7.256090899,
    "ci_low_pct": 3.014268313,
    "ci_high_pct": 11.672579181,
    "p_value": 0.000667771,
}

for key, expected in checks.items():
    if not math.isclose(
        float(row[key]),
        expected,
        abs_tol=1e-8,
    ):
        raise AssertionError(
            f"Detrended result drift: {key}"
        )


placebos = rows(
    "matched_placebo_summary_v2.csv"
)

row = select(
    placebos,
    half_window="63",
    metric="us_volume_share",
)

if not math.isclose(
    float(
        row["actual_delta_pp"]
    ),
    4.117823,
    abs_tol=1e-6,
):
    raise AssertionError(
        "Placebo result drift"
    )


weekly = rows(
    "weekly_etf_clock_tests.csv"
)

row = select(
    weekly,
    x="log_turnover",
    metric="lr_volume",
)

if not math.isclose(
    float(
        row["ratio_change_pct"]
    ),
    -0.03324088,
    abs_tol=1e-7,
):
    raise AssertionError(
        "Weekly result drift"
    )


git_dir = ROOT / ".git"

if git_dir.exists():
    result = subprocess.run(
        [
            "git",
            "ls-files",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    tracked = [
        line.strip()
        for line
        in result.stdout.splitlines()
        if line.strip()
    ]

    forbidden_prefixes = (
        "data/",
        "outputs/",
        "audit/",
    )

    forbidden = [
        path
        for path in tracked
        if path.startswith(
            forbidden_prefixes
        )
    ]

    if forbidden:
        raise AssertionError(
            "Forbidden tracked research "
            f"workspace files: {forbidden}"
        )


print(
    "Publication artifacts: "
    "17 / 17 PASS"
)

print(
    "Publication numerical "
    "invariants: PASS"
)

print(
    "Repository SHA-256 "
    "evidence: PASS"
)

print(
    "Research assurance "
    "snapshot: PASS"
)

print(
    "Tracked-data boundary: PASS"
)

print(
    "REPOSITORY ASSURANCE: PASS"
)
