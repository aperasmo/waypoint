"""Freeze the current Waypoint answer-layer candidate before fresh holdout v2.

This utility creates an evaluation checkpoint only. It does not modify runtime
code and does not call retrieval, embeddings, reranking, the answer model, or
the database.

It requires the active app/api/routes/ask.py to match the evidence-adequacy v2
candidate SHA that achieved the final external-v1 DEVELOPMENT result.

Run from backend/:
    uv run python -m py_compile scripts/freeze_answer_candidate_v2.py
    uv run python -m scripts.freeze_answer_candidate_v2

Inputs:
    app/api/routes/ask.py
    tests/external_adjudication_gold_v1.json
    tests/external_questions_blind_v1.json
    tests/external_predictions_dev_v1_evidence_adequacy_v2.json

Output:
    tests/answer_candidate_v2_freeze.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

ASK_PATH = BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
GOLD_V1_PATH = (
    BACKEND_DIR / "tests" / "external_adjudication_gold_v1.json"
)
BLIND_V1_PATH = (
    BACKEND_DIR / "tests" / "external_questions_blind_v1.json"
)
PREDICTIONS_V1_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v1_evidence_adequacy_v2.json"
)
OUTPUT_PATH = (
    BACKEND_DIR / "tests" / "answer_candidate_v2_freeze.json"
)

EXPECTED_ASK_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_GOLD_V1_SHA256 = (
    "11D21AF433C30F99665915F0536FFE30"
    "B4AE1E76972DB6F036BED38B2D5ECCB3"
)

EXPECTED_BLIND_V1_SHA256 = (
    "33C6A0370C382130890681064B4C32C1"
    "B519EF9CF1FC52D7C3D6570C8A60FFCB"
)

EXPECTED_PREDICTIONS_V1_SHA256 = (
    "0F1E84F74DC1B50C6217A1909A48A5F"
    "F922FA537029737E1E8CE3769488FD541"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_file(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")


def require_sha(path: Path, expected: str) -> None:
    actual = sha256(path)
    if actual != expected:
        raise SystemExit(
            f"SHA mismatch for {path}\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Refusing to freeze a different candidate or evaluation artifact."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: JSON root must be an object.")
    return payload


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Freeze artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite an existing candidate checkpoint."
        )

    for path in (
        ASK_PATH,
        GOLD_V1_PATH,
        BLIND_V1_PATH,
        PREDICTIONS_V1_PATH,
    ):
        require_file(path)

    require_sha(ASK_PATH, EXPECTED_ASK_SHA256)
    require_sha(GOLD_V1_PATH, EXPECTED_GOLD_V1_SHA256)
    require_sha(BLIND_V1_PATH, EXPECTED_BLIND_V1_SHA256)
    require_sha(
        PREDICTIONS_V1_PATH,
        EXPECTED_PREDICTIONS_V1_SHA256,
    )

    predictions = load_json(PREDICTIONS_V1_PATH)

    if predictions.get("runtime_ask_sha256") != EXPECTED_ASK_SHA256:
        raise RuntimeError(
            "Prediction artifact does not identify the expected ask.py SHA."
        )

    if predictions.get("prediction_count") != 51:
        raise RuntimeError(
            "Unexpected external-v1 development prediction count."
        )

    freeze = {
        "schema": "waypoint-answer-candidate-freeze-v2",
        "status": "FROZEN_CANDIDATE_BEFORE_EXTERNAL_HOLDOUT_V2",
        "candidate_name": "evidence_adequacy_v2",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_entrypoint": "app.api.routes.ask.ask",
        "runtime_file": "app/api/routes/ask.py",
        "runtime_ask_sha256": EXPECTED_ASK_SHA256,
        "development_evaluation": {
            "dataset": "external-v1",
            "status": "DEVELOPMENT_ONLY_NOT_UNTOUCHED_HOLDOUT",
            "gold_sha256": EXPECTED_GOLD_V1_SHA256,
            "blind_sha256": EXPECTED_BLIND_V1_SHA256,
            "predictions_sha256": EXPECTED_PREDICTIONS_V1_SHA256,
            "included_cases": 51,
            "evidence_status_accuracy": {
                "correct": 45,
                "total": 51,
                "percent": 88.2,
            },
            "per_class": {
                "sufficient": {
                    "correct": 8,
                    "total": 9,
                    "percent": 88.9,
                },
                "corpus_gap": {
                    "correct": 32,
                    "total": 34,
                    "percent": 94.1,
                },
                "external_source_required": {
                    "correct": 5,
                    "total": 8,
                    "percent": 62.5,
                },
            },
            "sufficient_citation_coverage": {
                "any_expected_section": {
                    "correct": 9,
                    "total": 9,
                    "percent": 100.0,
                },
                "all_expected_sections": {
                    "correct": 6,
                    "total": 9,
                    "percent": 66.7,
                },
            },
        },
        "freeze_rules": [
            (
                "Do not modify the answer prompt, evidence-status contract, "
                "retrieval, ranking, reranking, chunking, embeddings, or "
                "section-specific behaviour before external holdout v2 is "
                "collected, adjudicated, frozen, and scored."
            ),
            (
                "External-v1 is development data and must not be represented "
                "as untouched holdout evidence."
            ),
            (
                "External holdout v2 must be collected independently after "
                "this freeze and must not be used for tuning before scoring."
            ),
            (
                "If the frozen candidate is changed before holdout-v2 scoring, "
                "the candidate freeze is invalid and a new untouched holdout "
                "must be collected after the new candidate is frozen."
            ),
        ],
    }

    OUTPUT_PATH.write_text(
        json.dumps(freeze, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    verify = load_json(OUTPUT_PATH)

    if verify.get("runtime_ask_sha256") != EXPECTED_ASK_SHA256:
        raise RuntimeError("Frozen candidate SHA verification failed.")

    print("Waypoint answer candidate v2 freeze")
    print("=" * 35)
    print(f"Runtime:                   {ASK_PATH}")
    print(f"Output:                    {OUTPUT_PATH}")
    print()
    print(f"ask.py SHA256:             {sha256(ASK_PATH)}")
    print(f"External-v1 gold SHA256:   {sha256(GOLD_V1_PATH)}")
    print(f"External-v1 blind SHA256:  {sha256(BLIND_V1_PATH)}")
    print(
        f"External-v1 pred SHA256:   "
        f"{sha256(PREDICTIONS_V1_PATH)}"
    )
    print()
    print("Development result:        45/51 (88.2%)")
    print("Candidate status:          FROZEN")
    print("External-v1 status:        DEVELOPMENT ONLY")
    print("Runtime/model calls:       NONE")
    print("Database writes:           NONE")
    print(f"Freeze SHA256:             {sha256(OUTPUT_PATH)}")
    print()
    print("Answer candidate v2 freeze: PASS")


if __name__ == "__main__":
    main()
