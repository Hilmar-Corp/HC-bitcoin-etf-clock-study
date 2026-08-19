from __future__ import annotations

from pathlib import Path

ROOT_FILES = {
    ".gitignore",
    ".python-version",
    "CITATION.cff",
    "DATA_NOTICE.md",
    "DATA_PROVENANCE.md",
    "LICENSE",
    "Makefile",
    "NOTICE",
    "PUBLICATION_MANIFEST.json",
    "README.md",
    "REPRODUCIBILITY.md",
    "RESEARCH_ASSURANCE.md",
    "pyproject.toml",
    "research_contract.json",
    "source_registry.json",
}

CONTROLLED_DIRS = (
    ".github",
    "artifacts",
    "config",
    "docs",
    "evidence",
    "requirements",
    "scripts",
    "src",
    "tests",
    "tests_public",
)

EVIDENCE_PATH = (
    "evidence/repository_evidence.json"
)

LOCAL_ONLY_EXCLUSIONS = {
    "requirements/environment.freeze.txt",
}


def controlled_files(
    root: Path,
) -> list[Path]:
    files: set[Path] = set()

    for name in ROOT_FILES:
        path = root / name

        if path.is_file():
            files.add(path)

    for dirname in CONTROLLED_DIRS:
        directory = root / dirname

        if not directory.exists():
            continue

        for path in directory.rglob("*"):
            if not path.is_file():
                continue

            rel = path.relative_to(root)

            if str(rel) == EVIDENCE_PATH:
                continue

            if str(rel) in LOCAL_ONLY_EXCLUSIONS:
                continue

            if "__pycache__" in rel.parts:
                continue

            files.add(path)

    return sorted(
        files,
        key=lambda path: str(
            path.relative_to(root)
        ),
    )
