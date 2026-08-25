"""Promote the validated evidence-adequacy v3 candidate into runtime.

This script performs a hash-guarded byte-for-byte replacement of:
    app/api/routes/ask.py

It requires:
- current runtime ask.py == frozen v2 SHA;
- candidate file == validated v3 SHA.

It does NOT:
- call retrieval, embeddings, reranking, or the answer model;
- access evaluation gold;
- write to the database;
- modify any file other than app/api/routes/ask.py.

Run from backend/:
    uv run python -m py_compile scripts/promote_answer_candidate_v3.py
    uv run python -m scripts.promote_answer_candidate_v3

Required candidate:
    _candidates/ask_evidence_adequacy_candidate_v3.py
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

CANDIDATE_PATH = (
    BACKEND_DIR
    / "_candidates"
    / "ask_evidence_adequacy_candidate_v3.py"
)

RUNTIME_PATH = (
    BACKEND_DIR
    / "app"
    / "api"
    / "routes"
    / "ask.py"
)

EXPECTED_CURRENT_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_CANDIDATE_SHA256 = (
    "F1F17F3C714C956239E4A16BAE48EB8"
    "CFFAA2BB7D7BE809EB182F7D936B008EB"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_file(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")


def require_sha(path: Path, expected: str, label: str) -> None:
    actual = sha256(path)
    if actual != expected:
        raise SystemExit(
            f"{label} SHA mismatch.\n"
            f"Path:     {path}\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Refusing promotion."
        )


def main() -> None:
    require_file(CANDIDATE_PATH)
    require_file(RUNTIME_PATH)

    require_sha(
        CANDIDATE_PATH,
        EXPECTED_CANDIDATE_SHA256,
        "Candidate v3",
    )

    current_runtime_sha = sha256(RUNTIME_PATH)

    if current_runtime_sha == EXPECTED_CANDIDATE_SHA256:
        raise SystemExit(
            "Runtime ask.py already matches candidate v3.\n"
            "No promotion performed."
        )

    if current_runtime_sha != EXPECTED_CURRENT_RUNTIME_SHA256:
        raise SystemExit(
            "Current runtime ask.py is not the frozen v2 source expected "
            "for this promotion.\n"
            f"Path:     {RUNTIME_PATH}\n"
            f"Expected: {EXPECTED_CURRENT_RUNTIME_SHA256}\n"
            f"Actual:   {current_runtime_sha}\n"
            "Refusing promotion."
        )

    candidate_bytes = CANDIDATE_PATH.read_bytes()

    temp_path = RUNTIME_PATH.with_name(
        RUNTIME_PATH.name + ".candidate_v3_tmp"
    )

    if temp_path.exists():
        temp_path.unlink()

    try:
        temp_path.write_bytes(candidate_bytes)

        require_sha(
            temp_path,
            EXPECTED_CANDIDATE_SHA256,
            "Temporary promoted file",
        )

        # Atomic replacement on the same filesystem.
        os.replace(temp_path, RUNTIME_PATH)

    finally:
        if temp_path.exists():
            temp_path.unlink()

    require_sha(
        RUNTIME_PATH,
        EXPECTED_CANDIDATE_SHA256,
        "Promoted runtime ask.py",
    )

    print("Waypoint answer candidate v3 promotion")
    print("=" * 38)
    print(f"Candidate:                 {CANDIDATE_PATH}")
    print(f"Runtime:                   {RUNTIME_PATH}")
    print()
    print(
        f"Previous runtime SHA256:   "
        f"{EXPECTED_CURRENT_RUNTIME_SHA256}"
    )
    print(
        f"Candidate v3 SHA256:       "
        f"{EXPECTED_CANDIDATE_SHA256}"
    )
    print(f"Promoted runtime SHA256:   {sha256(RUNTIME_PATH)}")
    print()
    print("Replacement type:          BYTE-FOR-BYTE")
    print("Other runtime files:       UNCHANGED")
    print("Evaluation files opened:   NONE")
    print("Runtime/model calls:       NONE")
    print("Database writes:           NONE")
    print()
    print("Answer candidate v3 promotion: PASS")


if __name__ == "__main__":
    main()
