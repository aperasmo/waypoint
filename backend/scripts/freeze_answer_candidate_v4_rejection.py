"""Freeze the rejection decision for candidate v4.

This records the retired-development result only. It does not modify runtime,
promote a candidate, call any model, run retrieval, or write to the database.

Run from backend/:
    uv run python -m py_compile scripts/freeze_answer_candidate_v4_rejection.py
    uv run python -m scripts.freeze_answer_candidate_v4_rejection
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

RUNTIME_PATH = (
    BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
)

V4_PATH = (
    BACKEND_DIR
    / "_candidates"
    / "ask_factorised_evidence_candidate_v4.py"
)

V1_PRED_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v1_candidate_v4.json"
)

V2_PRED_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v2_candidate_v4.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "answer_candidate_v4_rejection.json"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_V4_SHA256 = (
    "F6056EAD183FFDCF19EEE386AA470C6C"
    "EA01C649F18C3C1D87C251689D78C8E8"
)

EXPECTED_V1_PRED_SHA256 = (
    "ADCA77FCC903C86DF2301F01B0AC12E7"
    "B98888966EB45A858E12D4E458C2AF9B"
)

EXPECTED_V2_PRED_SHA256 = (
    "9A8FECB538DC52B92508A6C263D00256"
    "AD8B6AD3B773BB06D6D175CFDAFB5ADB"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_sha(path: Path, expected: str, label: str) -> None:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")

    actual = sha256(path)

    if actual != expected:
        raise SystemExit(
            f"{label} SHA mismatch.\n"
            f"Path:     {path}\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Refusing to freeze the rejection decision."
        )


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Rejection artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_sha(
        RUNTIME_PATH,
        EXPECTED_RUNTIME_SHA256,
        "Frozen production candidate-v2 ask.py",
    )
    require_sha(
        V4_PATH,
        EXPECTED_V4_SHA256,
        "Candidate-v4 source",
    )
    require_sha(
        V1_PRED_PATH,
        EXPECTED_V1_PRED_SHA256,
        "Candidate-v4 external-v1 predictions",
    )
    require_sha(
        V2_PRED_PATH,
        EXPECTED_V2_PRED_SHA256,
        "Candidate-v4 external-v2 predictions",
    )

    artifact = {
        "schema": "waypoint-answer-candidate-v4-rejection",
        "status": "REJECTED_DEVELOPMENT_CANDIDATE_DO_NOT_PROMOTE",
        "candidate_name": "factorised_evidence_adjudication_v4",
        "decision_date": str(date.today()),
        "candidate_source_sha256": EXPECTED_V4_SHA256,
        "production_runtime_sha256": EXPECTED_RUNTIME_SHA256,
        "development_prediction_artifacts": {
            "external_v1_sha256": EXPECTED_V1_PRED_SHA256,
            "external_v2_sha256": EXPECTED_V2_PRED_SHA256,
        },
        "development_results": {
            "external_v1": {
                "candidate_v2": {
                    "correct": 45,
                    "total": 51,
                    "accuracy": 0.8823529411764706,
                },
                "candidate_v4": {
                    "correct": 37,
                    "total": 51,
                    "accuracy": 0.7254901960784313,
                },
                "delta_correct": -8,
                "delta_percentage_points": -15.7,
            },
            "external_v2": {
                "candidate_v2": {
                    "correct": 38,
                    "total": 60,
                    "accuracy": 0.6333333333333333,
                },
                "candidate_v4": {
                    "correct": 39,
                    "total": 60,
                    "accuracy": 0.65,
                },
                "delta_correct": 1,
                "delta_percentage_points": 1.7,
            },
            "combined": {
                "candidate_v2": {
                    "correct": 83,
                    "total": 111,
                    "accuracy": 0.7477477477477478,
                },
                "candidate_v4": {
                    "correct": 76,
                    "total": 111,
                    "accuracy": 0.6846846846846847,
                },
                "delta_correct": -7,
                "delta_percentage_points": -6.3,
                "candidate_v4_per_class": {
                    "sufficient": {
                        "correct": 6,
                        "total": 25,
                        "recall": 0.24,
                    },
                    "corpus_gap": {
                        "correct": 68,
                        "total": 68,
                        "recall": 1.0,
                    },
                    "external_source_required": {
                        "correct": 2,
                        "total": 18,
                        "recall": 0.1111111111111111,
                    },
                },
                "candidate_v4_predicted_distribution": {
                    "sufficient": 6,
                    "corpus_gap": 103,
                    "external_source_required": 2,
                },
                "candidate_v4_false_sufficiency": {
                    "count": 0,
                    "non_sufficient_gold": 86,
                    "rate": 0.0,
                },
                "gains": 13,
                "regressions": 20,
                "wrong_to_different_wrong": 2,
            },
        },
        "decision": {
            "candidate_v4": "REJECT",
            "production_candidate": "evidence_adequacy_v2",
            "production_runtime_replacement_authorised": False,
            "fresh_holdout_run_authorised_for_v4": False,
        },
        "reason": (
            "Candidate v4 eliminated false-sufficiency on the retired "
            "development sets, but became severely over-conservative. "
            "Combined accuracy fell by 6.3 percentage points, sufficient "
            "recall fell to 24.0%, and external_source_required recall "
            "fell to 11.1%. The candidate predicted corpus_gap for 103 of "
            "111 cases. This trade-off is not acceptable for promotion."
        ),
        "engineering_conclusions": [
            (
                "The factorised evidence-support concept helped reduce "
                "scope-entailment overreach and false-sufficiency."
            ),
            (
                "A single answer-model call that must both adjudicate support "
                "and formulate the final answer became strongly biased toward "
                "corpus_gap."
            ),
            (
                "Authoritative-home discrimination remains unresolved; "
                "candidate v4 did not improve external_source_required "
                "classification."
            ),
            (
                "The next candidate should not be another expansion of the "
                "same monolithic answer prompt."
            ),
            (
                "Any future architecture must remain benchmark-agnostic, "
                "section-agnostic, and free of topic-specific evidence-status "
                "routing."
            ),
            (
                "Retired external v1 and v2 remain development/diagnostic "
                "data only and cannot support a generalisation claim."
            ),
        ],
        "next_design_direction": {
            "recommended": (
                "Separate evidence adjudication from answer generation so "
                "the evidence classifier has a narrow structured task and the "
                "answer generator cannot influence the evidence-status choice."
            ),
            "runtime_change_authorised": False,
            "candidate_build_authorised": False,
            "fresh_holdout_required_after_candidate_selection": True,
            "acceptance_criteria_must_be_frozen_before_fresh_holdout": True,
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    saved = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    if saved.get("status") != (
        "REJECTED_DEVELOPMENT_CANDIDATE_DO_NOT_PROMOTE"
    ):
        raise RuntimeError("Saved rejection status verification failed.")

    if saved.get("decision", {}).get("candidate_v4") != "REJECT":
        raise RuntimeError("Saved rejection decision verification failed.")

    if saved.get("decision", {}).get(
        "production_runtime_replacement_authorised"
    ) is not False:
        raise RuntimeError(
            "Rejection artifact unexpectedly authorises runtime replacement."
        )

    print("Waypoint candidate-v4 rejection freeze")
    print("=" * 38)
    print(f"Production v2 SHA256:      {sha256(RUNTIME_PATH)}")
    print(f"Candidate v4 SHA256:       {sha256(V4_PATH)}")
    print(f"V4 external-v1 pred SHA:   {sha256(V1_PRED_PATH)}")
    print(f"V4 external-v2 pred SHA:   {sha256(V2_PRED_PATH)}")
    print()
    print("Combined v2:               83/111 (74.8%)")
    print("Combined v4:               76/111 (68.5%)")
    print("Delta:                     -7 correct (-6.3 pp)")
    print("V4 sufficient recall:      6/25 (24.0%)")
    print("V4 corpus-gap recall:      68/68 (100.0%)")
    print("V4 external recall:        2/18 (11.1%)")
    print("V4 false sufficiency:      0/86 (0.0%)")
    print()
    print("Decision:                  REJECT CANDIDATE V4")
    print("Production remains:        CANDIDATE V2")
    print("Runtime replacement:       NOT AUTHORISED")
    print("Fresh holdout for v4:      NOT AUTHORISED")
    print()
    print(f"Output:                    {OUTPUT_PATH}")
    print(f"Rejection SHA256:          {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:               NONE")
    print("Retrieval/reranker calls:  NONE")
    print("Database writes:           NONE")
    print("Runtime files modified:    NONE")
    print()
    print("Candidate-v4 rejection freeze: PASS")


if __name__ == "__main__":
    main()
