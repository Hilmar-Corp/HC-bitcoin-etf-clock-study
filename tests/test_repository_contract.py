import csv
import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.data


def test_research_spec_exists_and_is_consistent(root: Path):
    path = root / "config/research_spec.json"
    spec = json.loads(path.read_text(encoding="utf-8"))

    assert spec["study_id"] == "bitcoin_etf_clock"
    assert spec["sample"]["event_session_date"] == "2024-01-11"
    assert spec["sample"]["pre_sessions_final"] == 501
    assert spec["sample"]["post_sessions_final"] == 501
    assert spec["inference"]["causal_identification_claim"] is False
    assert spec["publication_constraints"]["causal_wording_allowed"] is False


def test_script_registry_has_expected_noncanonical_set(root: Path):
    path = root / "audit/repository_contract_v1/script_registry.csv"

    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    do_not_run = {
        row["path"]
        for row in rows
        if row["execution_policy"] == "DO_NOT_RUN"
    }

    assert do_not_run == {
        "src/analysis_01_us_clock.py",
        "src/analysis_04_detrended.py",
        "src/download_etf_market.py",
        "src/figure_01_intraday_volume.py",
    }


def test_primary_result_registry(root: Path):
    path = root / "audit/repository_contract_v1/artifact_registry.csv"

    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    primary = {
        row["path"]
        for row in rows
        if row["classification"] == "primary_result"
    }

    assert primary == {
        "outputs/tables/pre_post_final.csv",
        "outputs/tables/detrended_turnover_regressions.csv",
    }
