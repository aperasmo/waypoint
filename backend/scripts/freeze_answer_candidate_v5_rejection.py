"""Freeze the rejection decision for candidate v5.

This records the retired-development result only. It does not modify runtime,
promote a candidate, call any model, run retrieval, or write to the database.

Run from backend/:
    uv run python -m py_compile scripts/freeze_answer_candidate_v5_rejection.py
    uv run python -m scripts.freeze_answer_candidate_v5_rejection
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

RUNTIME_PATH = BACKEND_DIR / "app" / "api" / "routes" / "ask.py"

V5_PATH = (
    BACKEND_DIR
    / "_candidates"
    / "ask_two_stage_evidence_then_answer_candidate_v5.py"
)

V1_PRED_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v1_candidate_v5.json"
)

V2_PRED_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v2_candidate_v5.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "answer_candidate_v5_rejection.json"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_V5_SHA256 = (
    "6B741B99792A5131BC466A98DDFC8C38"
    "4CD14F803C262A9A396443E631DF61B6"
)

EXPECTED_V1_PRED_SHA256 = (
    "BFB75B7AB9AE9385AAC88C6956407807"
    "678229FDD04E5F0D4A1B7AAAE9569DAB"
)

EXPECTED_V2_PRED_SHA256 = (
    "70906FB9E78FA45F983EEADC9375AC1F"
    "82FC092716B05B564A109E96E6D1899D"
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
        V5_PATH,
        EXPECTED_V5_SHA256,
        "Candidate-v5 source",
    )
    require_sha(
        V1_PRED_PATH,
        EXPECTED_V1_PRED_SHA256,
        "Candidate-v5 external-v1 predictions",
    )
    require_sha(
        V2_PRED_PATH,
        EXPECTED_V2_PRED_SHA256,
        "Candidate-v5 external-v2 predictions",
    )

    artifact = {
        "schema": "waypoint-answer-candidate-v5-rejection",
        "status": "REJECTED_DEVELOPMENT_CANDIDATE_DO_NOT_PROMOTE",
        "candidate_name": "two_stage_evidence_then_answer_v5",
        "decision_date": str(date.today()),
        "candidate_source_sha256": EXPECTED_V5_SHA256,
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
                    "accuracy": 45 / 51,
                },
                "candidate_v5": {
                    "correct": 40,
                    "total": 51,
                    "accuracy": 40 / 51,
                },
                "delta_correct": -5,
                "delta_percentage_points": -9.8,
            },
            "external_v2": {
                "candidate_v2": {
                    "correct": 38,
                    "total": 60,
                    "accuracy": 38 / 60,
                },
                "candidate_v5": {
                    "correct": 41,
                    "total": 60,
                    "accuracy": 41 / 60,
                },
                "delta_correct": 3,
                "delta_percentage_points": 5.0,
            },
            "combined": {
                "candidate_v2": {
                    "correct": 83,
                    "total": 111,
                    "accuracy": 83 / 111,
                },
                "candidate_v5": {
                    "correct": 81,
                    "total": 111,
                    "accuracy": 81 / 111,
                },
                "delta_correct": -2,
                "delta_percentage_points": -1.8,
                "candidate_v5_per_class": {
                    "sufficient": {
                        "correct": 19,
                        "total": 25,
                        "recall": 19 / 25,
                    },
                    "corpus_gap": {
                        "correct": 60,
                        "total": 68,
                        "recall": 60 / 68,
                    },
                    "external_source_required": {
                        "correct": 2,
                        "total": 18,
                        "recall": 2 / 18,
                    },
                },
                "candidate_v5_predicted_distribution": {
                    "sufficient": 29,
                    "corpus_gap": 80,
                    "external_source_required": 2,
                },
                "candidate_v5_false_sufficiency": {
                    "count": 10,
                    "non_sufficient_gold": 86,
                    "rate": 10 / 86,
                },
                "candidate_v5_citation_coverage": {
                    "any_expected": {
                        "correct": 19,
                        "total": 25,
                        "rate": 19 / 25,
                    },
                    "all_expected": {
                        "correct": 15,
                        "total": 25,
                        "rate": 15 / 25,
                    },
                    "no_citations": 4,
                },
                "gains": 7,
                "regressions": 9,
                "wrong_to_different_wrong": 0,
            },
        },
        "decision": {
            "candidate_v5": "REJECT",
            "production_candidate": "evidence_adequacy_v2",
            "production_runtime_replacement_authorised": False,
            "fresh_holdout_run_authorised_for_v5": False,
        },
        "reason": (
            "Candidate v5 improved the retired external-v2 development set "
            "but regressed retired external-v1 and did not improve the main "
            "authoritative-home failure. Combined accuracy was 73.0% versus "
            "74.8% for frozen candidate v2. external_source_required recall "
            "was only 11.1%, false-sufficiency among non-sufficient cases was "
            "11.6%, and sufficient-case citation coverage also regressed. "
            "This trade-off is not acceptable for promotion."
        ),
        "engineering_conclusions": [
            (
                "Separating evidence adjudication from answer generation did "
                "not by itself solve authoritative-home classification."
            ),
            (
                "Candidate v5 improved corpus_gap recall on the combined "
                "retired development data but lost sufficient and external "
                "classification quality."
            ),
            (
                "The remaining Stage-1 task still conflates two distinct "
                "decisions: whether the retrieved Manual evidence is "
                "sufficient, and if not, where the missing authority lives."
            ),
            (
                "The next candidate should factor these two decisions rather "
                "than expanding the existing Stage-1 prompt."
            ),
            (
                "Retired external v1 and v2 remain development/diagnostic "
                "data only and cannot support a generalisation claim."
            ),
            (
                "Frozen candidate v2 remains the production baseline."
            ),
        ],
        "next_design_direction": {
            "recommended": (
                "Use a narrow support adjudicator first. Only if support is "
                "insufficient, run a separate authority resolver that "
                "classifies the missing proposition into generic authority "
                "types. Derive evidence_status deterministically from those "
                "two structured outputs before answer generation."
            ),
            "generic_authority_types_example": [
                "operational_manual_instruction",
                "live_service_information",
                "separate_fee_or_charge_schedule",
                "external_issuing_authority_procedure",
                "external_agency_service_or_assessment",
                "external_entitlement_or_organisation_definition",
                "professional_or_assessor_guidance",
            ],
            "no_topic_or_visa_specific_mapping": True,
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

    if saved.get("decision", {}).get("candidate_v5") != "REJECT":
        raise RuntimeError("Saved rejection decision verification failed.")

    if saved.get("decision", {}).get(
        "production_runtime_replacement_authorised"
    ) is not False:
        raise RuntimeError(
            "Rejection artifact unexpectedly authorises runtime replacement."
        )

    print("Waypoint candidate-v5 rejection freeze")
    print("=" * 38)
    print(f"Production v2 SHA256:      {sha256(RUNTIME_PATH)}")
    print(f"Candidate v5 SHA256:       {sha256(V5_PATH)}")
    print(f"V5 external-v1 pred SHA:   {sha256(V1_PRED_PATH)}")
    print(f"V5 external-v2 pred SHA:   {sha256(V2_PRED_PATH)}")
    print()
    print("Combined v2:               83/111 (74.8%)")
    print("Combined v5:               81/111 (73.0%)")
    print("Delta:                     -2 correct (-1.8 pp)")
    print("V5 sufficient recall:      19/25 (76.0%)")
    print("V5 corpus-gap recall:      60/68 (88.2%)")
    print("V5 external recall:        2/18 (11.1%)")
    print("V5 false sufficiency:      10/86 (11.6%)")
    print()
    print("Decision:                  REJECT CANDIDATE V5")
    print("Production remains:        CANDIDATE V2")
    print("Runtime replacement:       NOT AUTHORISED")
    print("Fresh holdout for v5:      NOT AUTHORISED")
    print()
    print(f"Output:                    {OUTPUT_PATH}")
    print(f"Rejection SHA256:          {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:               NONE")
    print("Retrieval/reranker calls:  NONE")
    print("Database writes:           NONE")
    print("Runtime files modified:    NONE")
    print()
    print("Candidate-v5 rejection freeze: PASS")


if __name__ == "__main__":
    main()
