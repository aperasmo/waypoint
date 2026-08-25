"""Freeze the first Waypoint source-boundary classifier acceptance result.

No model calls. No new scoring. Diagnostic analysis only is authorised next.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_score_result_v1.py
    uv run python -m scripts.freeze_source_boundary_classifier_score_result_v1

Output:
    tests/source_boundary_classifier_score_result_v1.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

RUNTIME_PATH = BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
PACK_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_contract_test_pack_v3.json"
THRESHOLDS_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_acceptance_thresholds_v1.json"
PREDICTIONS_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_predictions_v1.json"
PREDICTION_RESULT_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_prediction_result_v1.json"
SCORE_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_score_v1.json"
SCORER_PATH = BACKEND_DIR / "scripts" / "score_source_boundary_classifier_contract_v1.py"
OUTPUT_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_score_result_v1.json"

EXPECTED = {
    RUNTIME_PATH: "FF879300C09B195681E109E5B4F5D807C89216E986AE4AA9338B104FA99AAD0E",
    PACK_PATH: "C820489715EA3F54138023D680D04DFBFF5575A515B936FA8C2241E2EA5B219D",
    THRESHOLDS_PATH: "5E8AFBFFEE5880DEBF4FA6B0A6514E8C6702F5D9E74D620BA4C1575F49CAC03C",
    PREDICTIONS_PATH: "F9E753BE55B5A06FC09C002962BE82A921097D1F94843B63D7E58123661D9DF4",
    PREDICTION_RESULT_PATH: "8A8AFABEA1BDAC54663B4D2E20600BDEAF751FA54F672691673CA8694305FE99",
    SCORE_PATH: "EFBA19915945F2A929ABD261653070C979FA301B1A48C1742812EC9FD3DE54EA",
    SCORER_PATH: "19563B4DD326CCB1E5DA125F30625915FB2BE197786640FA6223BFB44855FE46",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be an object")
    return payload


def require_files() -> None:
    for path, expected in EXPECTED.items():
        if not path.exists():
            raise SystemExit(f"Required file not found: {path}")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(
                f"SHA mismatch: {path}\nExpected: {expected}\nActual:   {actual}"
            )


def expect_metric(
    metrics: dict[str, Any],
    name: str,
    expected: dict[str, Any],
) -> None:
    actual = metrics.get(name)
    if not isinstance(actual, dict):
        raise RuntimeError(f"Missing metric: {name}")
    for key, value in expected.items():
        if actual.get(key) != value:
            raise RuntimeError(
                f"{name}.{key} changed: expected {value!r}, got {actual.get(key)!r}"
            )


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(f"Refusing to overwrite: {OUTPUT_PATH}")

    require_files()

    prediction_result = load_json(PREDICTION_RESULT_PATH)
    score = load_json(SCORE_PATH)

    if prediction_result.get("status") != "FROZEN_FIRST_UNTOUCHED_PREDICTION_RESULT":
        raise RuntimeError("Unexpected prediction-result status")

    if score.get("schema") != "waypoint-source-boundary-classifier-score-v1":
        raise RuntimeError("Unexpected score schema")

    if score.get("status") != "ACCEPTANCE_FAIL":
        raise RuntimeError("First untouched score must be ACCEPTANCE_FAIL")

    sources = score.get("source_artifacts", {})
    required_sources = {
        "prediction_sha256": EXPECTED[PREDICTIONS_PATH],
        "contract_test_pack_sha256": EXPECTED[PACK_PATH],
        "acceptance_thresholds_sha256": EXPECTED[THRESHOLDS_PATH],
    }
    for key, value in required_sources.items():
        if sources.get(key) != value:
            raise RuntimeError(f"Score source binding changed: {key}")

    counts = score.get("counts", {})
    expected_counts = {
        "case_count": 34,
        "prediction_errors": 2,
        "contrast_group_count": 11,
        "source_class_count": 12,
    }
    for key, value in expected_counts.items():
        if counts.get(key) != value:
            raise RuntimeError(f"Score count changed: {key}")

    metrics = score.get("metrics", {})
    expect_metric(metrics, "four_field_exact_match_accuracy", {"correct": 26, "total": 34, "percent": 76.5})
    expect_metric(metrics, "resolution_status_accuracy", {"correct": 27, "total": 34, "percent": 79.4})
    expect_metric(metrics, "source_domain_accuracy", {"correct": 27, "total": 34, "percent": 79.4})
    expect_metric(metrics, "source_class_accuracy", {"correct": 26, "total": 34, "percent": 76.5})
    expect_metric(metrics, "source_class_macro_recall", {"percent": 73.3, "class_count": 12})
    expect_metric(metrics, "unresolved_recall", {"correct": 6, "total": 6, "percent": 100.0})
    expect_metric(metrics, "resolved_recall", {"correct": 21, "total": 28, "percent": 75.0})
    expect_metric(metrics, "contrast_group_full_consistency_rate", {"correct_groups": 7, "total_groups": 11, "percent": 63.6})
    expect_metric(metrics, "malformed_or_error_rate", {"error_count": 2, "total": 34, "percent": 5.9})

    per_class = metrics.get("per_source_class_recall", {})
    expected_zero = {
        "current_fee_or_charge_information": {"correct": 0, "support": 2, "recall_percent": 0.0},
        "inz_live_service_information": {"correct": 0, "support": 3, "recall_percent": 0.0},
    }
    for source_class, expected in expected_zero.items():
        actual = per_class.get(source_class)
        if actual != expected:
            raise RuntimeError(
                f"Per-class result changed for {source_class}: {actual!r}"
            )

    acceptance = score.get("acceptance", {})
    if acceptance.get("overall_pass") is not False:
        raise RuntimeError("Overall acceptance decision changed")
    if acceptance.get("all_hard_gates_pass") is not False:
        raise RuntimeError("Hard-gate aggregate changed")
    if acceptance.get("per_class_floor_passed") is not False:
        raise RuntimeError("Per-class floor aggregate changed")

    expected_gate_status = {
        "four_field_exact_match_accuracy": False,
        "resolution_status_accuracy": False,
        "source_domain_accuracy": False,
        "source_class_accuracy": False,
        "source_class_macro_recall": False,
        "unresolved_recall": True,
        "resolved_recall": False,
        "contrast_group_full_consistency_rate": False,
        "malformed_or_error_rate": False,
    }
    hard_gates = acceptance.get("hard_gates", {})
    if set(hard_gates) != set(expected_gate_status):
        raise RuntimeError("Hard-gate set changed")
    for name, expected_pass in expected_gate_status.items():
        if hard_gates[name].get("passed") is not expected_pass:
            raise RuntimeError(f"Gate result changed: {name}")

    floor_failures = {
        item.get("source_class")
        for item in acceptance.get("per_class_floor_failures", [])
        if isinstance(item, dict)
    }
    if floor_failures != {
        "current_fee_or_charge_information",
        "inz_live_service_information",
    }:
        raise RuntimeError("Per-class floor failure set changed")

    result = {
        "schema": "waypoint-source-boundary-classifier-score-result-v1",
        "status": "FROZEN_FIRST_UNTOUCHED_ACCEPTANCE_FAIL",
        "frozen_on": str(date.today()),
        "source_artifacts": {
            "production_runtime_sha256": EXPECTED[RUNTIME_PATH],
            "contract_test_pack_v3_sha256": EXPECTED[PACK_PATH],
            "acceptance_thresholds_v1_sha256": EXPECTED[THRESHOLDS_PATH],
            "prediction_sha256": EXPECTED[PREDICTIONS_PATH],
            "prediction_result_v1_sha256": EXPECTED[PREDICTION_RESULT_PATH],
            "scorer_sha256": EXPECTED[SCORER_PATH],
            "score_sha256": EXPECTED[SCORE_PATH],
        },
        "acceptance_result": {
            "decision": "FAIL",
            "four_field_exact_match": "26/34 (76.5%)",
            "resolution_status_accuracy": "27/34 (79.4%)",
            "source_domain_accuracy": "27/34 (79.4%)",
            "source_class_accuracy": "26/34 (76.5%)",
            "source_class_macro_recall": "73.3%",
            "unresolved_recall": "6/6 (100.0%) PASS",
            "resolved_recall": "21/28 (75.0%)",
            "contrast_group_consistency": "7/11 (63.6%)",
            "malformed_or_error_count": "2/34",
            "per_class_floor_failures": [
                "current_fee_or_charge_information 0/2",
                "inz_live_service_information 0/3",
            ],
        },
        "methodological_consequence": {
            "prediction_set_is_development_evidence": True,
            "score_set_is_development_evidence": True,
            "same_pack_may_be_used_for_diagnosis_and_regression": True,
            "same_pack_cannot_support_a_new_untouched_acceptance_claim_after_tuning": True,
            "threshold_lowering_after_observation_prohibited": True,
            "first_run_failure_must_be_preserved": True,
        },
        "authorisations": {
            "failure_analysis_authorised": True,
            "case_level_prediction_review_authorised_for_diagnosis": True,
            "confusion_review_authorised_for_diagnosis": True,
            "failed_contrast_review_authorised_for_diagnosis": True,
            "classifier_prompt_change_authorised": False,
            "classifier_logic_change_authorised": False,
            "same_pack_untouched_rerun_authorised": False,
            "threshold_change_authorised": False,
            "contract_pack_change_authorised": False,
            "candidate_v7_build_authorised": False,
            "classifier_runtime_implementation_authorised": False,
            "production_runtime_change_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": "source_boundary_classifier_failure_analysis_v1",
            "authorised": True,
            "model_calls": 0,
            "purpose": (
                "Diagnose the eight four-field failures, two execution errors, "
                "class confusions, and failed contrast groups without changing "
                "the frozen classifier, thresholds, or contract pack."
            ),
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)
    if saved.get("status") != "FROZEN_FIRST_UNTOUCHED_ACCEPTANCE_FAIL":
        raise RuntimeError("Saved freeze status changed")
    if saved.get("authorisations", {}).get("failure_analysis_authorised") is not True:
        raise RuntimeError("Failure analysis not authorised")

    print("Waypoint source-boundary first acceptance-result freeze")
    print("=" * 61)
    print(f"Prediction SHA256:          {sha256(PREDICTIONS_PATH)}")
    print(f"Score SHA256:               {sha256(SCORE_PATH)}")
    print(f"Threshold SHA256:           {sha256(THRESHOLDS_PATH)}")
    print()
    print("Frozen acceptance result")
    print("-" * 61)
    print("Decision:                   FAIL")
    print("4-field exact match:        26/34 (76.5%)")
    print("Resolution accuracy:        27/34 (79.4%)")
    print("Source-domain accuracy:     27/34 (79.4%)")
    print("Source-class accuracy:      26/34 (76.5%)")
    print("Source-class macro recall:  73.3%")
    print("Unresolved recall:          6/6 (100.0%)  PASS")
    print("Resolved recall:            21/28 (75.0%)")
    print("Contrast consistency:       7/11 (63.6%)")
    print("Malformed/error count:      2/34")
    print()
    print("Per-class floor failures")
    print("-" * 61)
    print("current_fee_or_charge_information: 0/2")
    print("inz_live_service_information:      0/3")
    print()
    print("Prediction set:             DEVELOPMENT EVIDENCE")
    print("Threshold lowering:         NOT AUTHORISED")
    print("Same-pack untouched rerun:  NOT AUTHORISED")
    print("Failure analysis:           AUTHORISED")
    print()
    print("Classifier changes:         NOT AUTHORISED")
    print("Candidate v7 build:         NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print("Fresh external-v3:          NOT AUTHORISED")
    print()
    print("Next task:                  FAILURE ANALYSIS V1")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Score-result SHA256:        {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                NONE")
    print("Retrieval/reranker calls:   NONE")
    print("Database writes:            NONE")
    print("Runtime files modified:     NONE")
    print()
    print("First acceptance-result freeze: PASS")


if __name__ == "__main__":
    main()
