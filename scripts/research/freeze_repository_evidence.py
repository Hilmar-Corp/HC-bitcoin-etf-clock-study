from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from scripts.research.repository_control import (
    controlled_files,
)

ROOT = Path(__file__).resolve().parents[2]

OUT = (
    ROOT
    / "evidence"
    / "repository_evidence.json"
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


files = controlled_files(ROOT)

payload = {
    "schema_version": 1,
    "study_id": (
        "HILMARCORP-BITCOIN-ETF-CLOCK"
    ),
    "frozen_at_utc": datetime.now(
        UTC
    ).isoformat(),
    "controlled_file_count": len(files),
    "files": {
        str(
            path.relative_to(ROOT)
        ): sha256(path)
        for path in files
    },
}

OUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

OUT.write_text(
    json.dumps(
        payload,
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)

print(
    "CONTROLLED FILES:",
    len(files),
)

print(
    "EVIDENCE ->",
    OUT.relative_to(ROOT),
)

print(
    "PASS_REPOSITORY_EVIDENCE_FREEZE"
)
