from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def table(
    name: str,
) -> list[dict[str, str]]:
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


def test_publication_artifact_count() -> None:
    manifest = json.loads(
        (
            ROOT
            / "PUBLICATION_MANIFEST.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        manifest["artifact_count"]
        == 17
    )


def test_pre_post_geometry() -> None:
    data = table(
        "pre_post_final.csv"
    )

    assert len(data) == 4

    for row in data:
        assert int(row["pre_n"]) == 501
        assert int(row["post_n"]) == 501


def test_primary_volume_shift() -> None:
    data = table(
        "pre_post_final.csv"
    )

    row = next(
        row
        for row in data
        if row["metric"]
        == "us_volume_share"
    )

    assert math.isclose(
        float(
            row["delta_median_pp"]
        ),
        2.966372,
        abs_tol=1e-5,
    )


def test_detrended_turnover_volume() -> None:
    data = table(
        "detrended_turnover_regressions.csv"
    )

    row = next(
        row
        for row in data
        if (
            row["x"]
            == "log_turnover"
            and row["metric"]
            == "lr_volume"
        )
    )

    assert math.isclose(
        float(
            row["ratio_change_pct"]
        ),
        7.256090899,
        abs_tol=1e-8,
    )

    assert (
        float(row["p_value"])
        < 0.001
    )


def test_documented_exclusion() -> None:
    data = table(
        "excluded_sessions.csv"
    )

    assert len(data) == 1

    assert (
        data[0]["date"]
        == "2023-03-24"
    )

    assert (
        int(
            float(
                data[0][
                    "expected_us_bars"
                ]
            )
        )
        == 78
    )

    assert (
        int(
            float(
                data[0]["us_bars"]
            )
        )
        == 72
    )
