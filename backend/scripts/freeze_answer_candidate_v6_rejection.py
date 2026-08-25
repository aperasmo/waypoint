"""Freeze the rejection decision for candidate v6.

Run from backend/:
    uv run python -m py_compile scripts/freeze_answer_candidate_v6_rejection.py
    uv run python -m scripts.freeze_answer_candidate_v6_rejection
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

RUNTIME_PATH = BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
V6_PATH = (
    BACKEND_DIR
    / "_candidates"
    / "ask_support_then_authority_then_answer_candidate_v6.py"
)
V6_DESIGN_PATH = (
    BACKEND_DIR / "tests" / "answer_candidate_v6_design_contract.json"
)
V1_PRED_PATH = (
    BACKEND_DIR / "tests" / "external_predictions_dev_v1_candidate_v6.json"
)
V2_PRED_PATH = (
    BACKEND_DIR / "tests" / "external_predictions_dev_v2_candidate_v6.json"
)
OUTPUT_PATH = (
    BACKEND_DIR / "tests" / "answer_candidate_v6_rejection.json"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)
EXPECTED_V6_SHA256 = (
    "04F86C7EA3E4BA296E4052FE7B7E7660"
    "9799F6FF96021AF6D658CA1890997C95"
)
EXPECTED_V6_DESIGN_SHA256 = (
    "8985D1845561C1914199F2C5457C9B76"
    "92D4DEF551B473D26CE1EE7B57D043DA"
)
EXPECTED_V1_PRED_SHA256 = (
    "24BDDB4B0AA69BBE93552F075E3A801C"
    "8905422B4F5EBBD01375779640A295FF"
)
EXPECTED_V2_PRED_SHA256 = (
    "2150DA5E6E093AA1FBF8ECA39362306B"
    "50115598561BAC15D02C8573D61C3A45"
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
            "Refusing to freeze the v6 rejection."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: JSON root must be an object.")
    return payload


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
    require_sha(V6_PATH, EXPECTED_V6_SHA256, "Candidate-v6 source")
    require_sha(
        V6_DESIGN_PATH,
        EXPECTED_V6_DESIGN_SHA256,
        "Frozen candidate-v6 design contract",
    )
    require_sha(
        V1_PRED_PATH,
        EXPECTED_V1_PRED_SHA256,
        "Candidate-v6 external-v1 predictions",
    )
    require_sha(
        V2_PRED_PATH,
        EXPECTED_V2_PRED_SHA256,
        "Candidate-v6 external-v2 predictions",
    )

    design = load_json(V6_DESIGN_PATH)
    if design.get("schema") != "waypoint-answer-candidate-v6-design-contract":
        raise RuntimeError("Unexpected v6 design schema.")
    if design.get("status") != "FROZEN_DESIGN_ONLY_NO_RUNTIME_CHANGE":
        raise RuntimeError("Unexpected v6 design status.")

    v1 = load_json(V1_PRED_PATH)
    v2 = load_json(V2_PRED_PATH)

    if (
        v1.get("attempted_count"),
        v1.get("prediction_count"),
        v1.get("error_count"),
    ) != (51, 49, 2):
        raise RuntimeError("Unexpected v1 candidate-v6 execution counts.")

    if (
        v2.get("attempted_count"),
        v2.get("prediction_count"),
        v2.get("error_count"),
    ) != (60, 60, 0):
        raise RuntimeError("Unexpected v2 candidate-v6 execution counts.")

    artifact = {
        "schema": "waypoint-answer-candidate-v6-rejection",
        "status": "REJECTED_DEVELOPMENT_CANDIDATE_DO_NOT_PROMOTE",
        "candidate_name": "support_then_authority_then_answer_v6",
        "decision_date": str(date.today()),
        "candidate_source_sha256": EXPECTED_V6_SHA256,
        "candidate_design_sha256": EXPECTED_V6_DESIGN_SHA256,
        "production_runtime_sha256": EXPECTED_RUNTIME_SHA256,
        "development_prediction_artifacts": {
            "external_v1_sha256": EXPECTED_V1_PRED_SHA256,
            "external_v2_sha256": EXPECTED_V2_PRED_SHA256,
        },
        "candidate_execution": {
            "external_v1": {
                "attempted": 51,
                "successful_predictions": 49,
                "contract_errors": 2,
                "two_call_successes": 3,
                "three_call_successes": 46,
            },
            "external_v2": {
                "attempted": 60,
                "successful_predictions": 60,
                "contract_errors": 0,
                "two_call_successes": 7,
                "three_call_successes": 53,
            },
            "combined_contract_errors": {
                "count": 2,
                "total": 111,
                "rate": 2 / 111,
            },
        },
        "development_results": {
            "external_v1": {
                "candidate_v2_correct": 45,
                "candidate_v6_correct": 39,
                "total": 51,
                "delta_correct": -6,
                "delta_percentage_points": -11.8,
            },
            "external_v2": {
                "candidate_v2_correct": 38,
                "candidate_v6_correct": 40,
                "total": 60,
                "delta_correct": 2,
                "delta_percentage_points": 3.3,
                "source_cluster_macro_accuracy": 40 / 60,
                "fully_correct_source_clusters": 9,
                "source_cluster_count": 20,
            },
            "combined": {
                "candidate_v2": {
                    "correct": 83,
                    "total": 111,
                    "accuracy": 83 / 111,
                },
                "candidate_v6": {
                    "correct": 79,
                    "total": 111,
                    "accuracy": 79 / 111,
                },
                "delta_correct": -4,
                "delta_percentage_points": -3.6,
                "candidate_v6_per_class": {
                    "sufficient": {
                        "correct": 8,
                        "total": 25,
                        "recall": 8 / 25,
                    },
                    "corpus_gap": {
                        "correct": 65,
                        "total": 68,
                        "recall": 65 / 68,
                    },
                    "external_source_required": {
                        "correct": 6,
                        "total": 18,
                        "recall": 6 / 18,
                    },
                },
                "candidate_v6_result_distribution": {
                    "sufficient": 10,
                    "corpus_gap": 93,
                    "external_source_required": 6,
                    "candidate_error": 2,
                },
                "candidate_v6_false_sufficiency": {
                    "count": 2,
                    "non_sufficient_gold": 86,
                    "rate": 2 / 86,
                },
                "candidate_v6_citation_coverage": {
                    "any_expected": {
                        "correct": 18,
                        "total": 25,
                        "rate": 18 / 25,
                    },
                    "all_expected": {
                        "correct": 14,
                        "total": 25,
                        "rate": 14 / 25,
                    },
                    "no_citations": 5,
                },
                "gains": 12,
                "regressions": 16,
                "wrong_to_different_wrong": 2,
            },
        },
        "decision": {
            "candidate_v6": "REJECT",
            "production_candidate": "evidence_adequacy_v2",
            "production_runtime_replacement_authorised": False,
            "fresh_holdout_run_authorised_for_v6": False,
        },
        "reason": (
            "Candidate v6 materially over-classified corpus_gap. Combined "
            "corpus_gap recall increased to 95.6% and false sufficiency fell "
            "to 2.3%, but sufficient recall collapsed from 84.0% under "
            "candidate v2 to 32.0%. external_source_required recall remained "
            "33.3% combined, so the factored authority resolver did not "
            "improve the unresolved external-authority problem. Overall "
            "accuracy fell from 74.8% to 71.2%, and the candidate produced "
            "two explicit Stage-1 contract errors."
        ),
        "engineering_conclusions": [
            (
                "Separating support adjudication from authoritative-home "
                "resolution did not improve combined external-source recall "
                "over frozen candidate v2."
            ),
            (
                "The support adjudicator became substantially too "
                "conservative and rejected many fully supported cases."
            ),
            (
                "The authority resolver recovered some live-service and "
                "fee-schedule cases, but did not produce a balanced gain."
            ),
            (
                "Prompt decomposition has now repeatedly shifted the decision "
                "boundary without outperforming the frozen production baseline."
            ),
            (
                "The next development step should not be another larger or "
                "more finely divided answer prompt."
            ),
            "Frozen candidate v2 remains the production baseline.",
            (
                "Retired external v1 and v2 remain development/diagnostic "
                "data only and cannot support a generalisation claim."
            ),
        ],
        "next_design_direction": {
            "recommended": (
                "Pause answer-layer prompt architecture experiments and "
                "perform a structured error audit of candidate v2 versus "
                "v5/v6. Determine whether the remaining failures are "
                "primarily retrieval-evidence availability, evidence "
                "representation, authoritative-source taxonomy, or model "
                "classification limitations before designing candidate v7."
            ),
            "runtime_change_authorised": False,
            "candidate_v7_build_authorised": False,
            "fresh_holdout_required_after_candidate_selection": True,
            "acceptance_criteria_must_be_frozen_before_fresh_holdout": True,
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)

    if saved.get("decision", {}).get("candidate_v6") != "REJECT":
        raise RuntimeError("Saved v6 rejection verification failed.")

    if saved.get("decision", {}).get(
        "production_runtime_replacement_authorised"
    ) is not False:
        raise RuntimeError(
            "Rejection unexpectedly authorises runtime replacement."
        )

    if saved.get("next_design_direction", {}).get(
        "candidate_v7_build_authorised"
    ) is not False:
        raise RuntimeError(
            "Rejection unexpectedly authorises candidate v7."
        )

    print("Waypoint candidate-v6 rejection freeze")
    print("=" * 38)
    print(f"Production v2 SHA256:      {sha256(RUNTIME_PATH)}")
    print(f"Candidate v6 SHA256:       {sha256(V6_PATH)}")
    print(f"V6 design SHA256:          {sha256(V6_DESIGN_PATH)}")
    print(f"V6 external-v1 pred SHA:   {sha256(V1_PRED_PATH)}")
    print(f"V6 external-v2 pred SHA:   {sha256(V2_PRED_PATH)}")
    print()
    print("Combined v2:               83/111 (74.8%)")
    print("Combined v6:               79/111 (71.2%)")
    print("Delta:                     -4 correct (-3.6 pp)")
    print("V6 sufficient recall:      8/25 (32.0%)")
    print("V6 corpus-gap recall:      65/68 (95.6%)")
    print("V6 external recall:        6/18 (33.3%)")
    print("V6 false sufficiency:      2/86 (2.3%)")
    print("V6 contract errors:        2/111 (1.8%)")
    print()
    print("Decision:                  REJECT CANDIDATE V6")
    print("Production remains:        CANDIDATE V2")
    print("Runtime replacement:       NOT AUTHORISED")
    print("Fresh holdout for v6:      NOT AUTHORISED")
    print("Candidate v7 build:        NOT AUTHORISED")
    print()
    print("Next step:                 STRUCTURED ERROR AUDIT BEFORE V7")
    print()
    print(f"Output:                    {OUTPUT_PATH}")
    print(f"Rejection SHA256:          {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:               NONE")
    print("Retrieval/reranker calls:  NONE")
    print("Database writes:           NONE")
    print("Runtime files modified:    NONE")
    print()
    print("Candidate-v6 rejection freeze: PASS")


if __name__ == "__main__":
    main()
