"""Freeze the first untouched Waypoint classifier score result v2.

FREEZE ONLY.
- No model calls.
- No classifier rerun.
- No threshold changes.
- No prompt changes.
- Does not modify the score artifact.
- Binds the exact first-run score before diagnostic analysis.
- Authorises failure-analysis construction only.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_score_result_v2.py
    uv run python -m scripts.freeze_source_boundary_classifier_score_result_v2

Output:
    tests/source_boundary_classifier_score_result_v2.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

SCORE_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_score_v2.json"
)

PREDICTIONS_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_predictions_v2.json"
)

PREDICTION_RESULT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_prediction_result_v2.json"
)

THRESHOLDS_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_acceptance_thresholds_v2.json"
)

PACK_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_contract_test_pack_v5.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_score_result_v2.json"
)

EXPECTED_SCORE_SHA256 = (
    "A26CADECFE6B31D9010F1855A1AAC99"
    "D76AF622554DB750191DDA143195570E7"
)

EXPECTED_PREDICTION_SHA256 = (
    "7EE68C61443D73B298574A8EB2BBA4425"
    "A99D577F618B7565848F16FEA8C6EF1"
)

EXPECTED_PREDICTION_RESULT_SHA256 = (
    "875137554FBE33BAB97A95FF6E0321498"
    "62A6BF4A522EABB1FD21A6B59F5623D"
)

EXPECTED_THRESHOLDS_SHA256 = (
    "1BDD2ED8950D6E3E612C66DCD5384BD5"
    "E0CAC784E39A70C3CE09EAD5C310D277"
)

EXPECTED_PACK_SHA256 = (
    "1B3CEA56504E3932C7DCA342DF99DC225"
    "23A4676B1C22714B9A122DDD566E67B"
)

EXPECTED_STATUS = "ACCEPTANCE_FAIL"
EXPECTED_DECISION = "FAIL"

EXPECTED_FAILED_HARD_GATES = [
    "unresolved_recall",
]

EXPECTED_FAILED_CASES = [
    "iv4_026",
    "iv4_036",
]

EXPECTED_UNRESOLVED_FAILURE_CASES = [
    "iv4_036",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_sha(
    path: Path,
    expected: str,
    label: str,
) -> None:
    if not path.exists():
        raise SystemExit(
            f"Required file not found: {path}"
        )

    actual = sha256(path)

    if actual != expected:
        raise SystemExit(
            f"{label} SHA mismatch.\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Refusing to freeze score result v2."
        )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{path.name}: root must be a JSON object."
        )

    return payload


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Score-result freeze already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_sha(
        SCORE_PATH,
        EXPECTED_SCORE_SHA256,
        "First-run classifier score v2",
    )
    require_sha(
        PREDICTIONS_PATH,
        EXPECTED_PREDICTION_SHA256,
        "First untouched prediction artifact v2",
    )
    require_sha(
        PREDICTION_RESULT_PATH,
        EXPECTED_PREDICTION_RESULT_SHA256,
        "Frozen prediction result v2",
    )
    require_sha(
        THRESHOLDS_PATH,
        EXPECTED_THRESHOLDS_SHA256,
        "Frozen acceptance thresholds v2",
    )
    require_sha(
        PACK_PATH,
        EXPECTED_PACK_SHA256,
        "Frozen independent pack v5",
    )

    score = load_json(SCORE_PATH)
    prediction_result = load_json(
        PREDICTION_RESULT_PATH
    )

    if score.get("schema") != (
        "waypoint-source-boundary-classifier-score-v2"
    ):
        raise RuntimeError(
            "Unexpected score-v2 schema."
        )

    if score.get("status") != EXPECTED_STATUS:
        raise RuntimeError(
            f"Expected score status {EXPECTED_STATUS!r}; "
            f"found {score.get('status')!r}."
        )

    if score.get(
        "acceptance_decision"
    ) != EXPECTED_DECISION:
        raise RuntimeError(
            "Score acceptance decision changed."
        )

    if score.get("model_calls") != 0:
        raise RuntimeError(
            "Score artifact unexpectedly reports model calls."
        )

    source_artifacts = score.get(
        "source_artifacts",
        {},
    )

    expected_sources = {
        "independent_contract_pack_v5_sha256": (
            EXPECTED_PACK_SHA256
        ),
        "acceptance_thresholds_v2_sha256": (
            EXPECTED_THRESHOLDS_SHA256
        ),
        "prediction_sha256": (
            EXPECTED_PREDICTION_SHA256
        ),
        "prediction_result_sha256": (
            EXPECTED_PREDICTION_RESULT_SHA256
        ),
    }

    for key, expected in expected_sources.items():
        actual = source_artifacts.get(key)

        if actual != expected:
            raise RuntimeError(
                f"Score source binding changed for {key}.\n"
                f"Expected: {expected}\n"
                f"Actual:   {actual}"
            )

    if prediction_result.get(
        "prediction_sha256"
    ) != EXPECTED_PREDICTION_SHA256:
        raise RuntimeError(
            "Frozen prediction-result binding changed."
        )

    hard_gates = score.get(
        "hard_gate_results"
    )

    if not isinstance(hard_gates, dict):
        raise RuntimeError(
            "Score hard_gate_results missing."
        )

    failed_hard_gates = sorted(
        key
        for key, passed in hard_gates.items()
        if passed is not True
    )

    if failed_hard_gates != EXPECTED_FAILED_HARD_GATES:
        raise RuntimeError(
            "Observed failed hard-gate set changed.\n"
            f"Expected: {EXPECTED_FAILED_HARD_GATES}\n"
            f"Actual:   {failed_hard_gates}"
        )

    passed_hard_gates = sorted(
        key
        for key, passed in hard_gates.items()
        if passed is True
    )

    if len(passed_hard_gates) != 8:
        raise RuntimeError(
            f"Expected 8 passed hard gates; found {len(passed_hard_gates)}."
        )

    per_class = score.get(
        "per_resolved_class_gate_results"
    )

    if not isinstance(per_class, dict):
        raise RuntimeError(
            "Per-resolved-class gate results missing."
        )

    failed_resolved_class_gates = sorted(
        key
        for key, passed in per_class.items()
        if passed is not True
    )

    if failed_resolved_class_gates:
        raise RuntimeError(
            "Expected all resolved-class floors to pass; failures: "
            + ", ".join(failed_resolved_class_gates)
        )

    metrics = score.get(
        "metrics",
        {},
    )

    expected_metrics = {
        "four_field_exact_match": (38, 40, 95.0),
        "resolution_status_accuracy": (39, 40, 97.5),
        "source_domain_accuracy": (39, 40, 97.5),
        "source_class_accuracy": (38, 40, 95.0),
        "unresolved_recall": (5, 6, 83.3),
        "resolved_recall": (33, 34, 97.1),
        "contrast_consistency": (11, 12, 91.7),
    }

    for metric_name, (
        expected_correct,
        expected_total,
        expected_percent,
    ) in expected_metrics.items():
        metric = metrics.get(metric_name)

        if not isinstance(metric, dict):
            raise RuntimeError(
                f"Metric missing: {metric_name}"
            )

        if (
            metric.get("correct") != expected_correct
            or metric.get("total") != expected_total
            or metric.get("percent") != expected_percent
        ):
            raise RuntimeError(
                f"Metric changed: {metric_name}"
            )

    macro = metrics.get(
        "source_class_macro_recall",
        {},
    ).get("percent")

    if macro != 95.8:
        raise RuntimeError(
            "Source-class macro recall changed."
        )

    error_count = metrics.get(
        "malformed_or_error_count",
        {},
    ).get("count")

    if error_count != 0:
        raise RuntimeError(
            "Malformed/error count changed."
        )

    case_results = score.get(
        "case_results"
    )

    if not isinstance(case_results, list) or len(case_results) != 40:
        raise RuntimeError(
            "Expected exactly 40 case results."
        )

    failed_cases = sorted(
        item["case_id"]
        for item in case_results
        if item.get("four_field_correct") is False
    )

    if failed_cases != EXPECTED_FAILED_CASES:
        raise RuntimeError(
            "Observed failed case set changed.\n"
            f"Expected: {EXPECTED_FAILED_CASES}\n"
            f"Actual:   {failed_cases}"
        )

    unresolved_failure_cases = sorted(
        item["case_id"]
        for item in case_results
        if (
            item.get("gold_source_class") == "unresolved"
            and item.get("predicted_source_class") != "unresolved"
        )
    )

    if (
        unresolved_failure_cases
        != EXPECTED_UNRESOLVED_FAILURE_CASES
    ):
        raise RuntimeError(
            "Observed unresolved failure set changed.\n"
            f"Expected: {EXPECTED_UNRESOLVED_FAILURE_CASES}\n"
            f"Actual:   {unresolved_failure_cases}"
        )

    score_auth = score.get(
        "authorisations",
        {},
    )

    if score_auth.get(
        "score_result_freeze_authorised"
    ) is not True:
        raise RuntimeError(
            "Score artifact does not authorise score-result freeze."
        )

    for forbidden in (
        "classifier_rerun_authorised",
        "threshold_change_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
    ):
        if score_auth.get(forbidden) is not False:
            raise RuntimeError(
                f"Score artifact unexpectedly enables {forbidden}."
            )

    artifact = {
        "schema": (
            "waypoint-source-boundary-classifier-score-result-v2"
        ),
        "status": (
            "FROZEN_FIRST_UNTOUCHED_ACCEPTANCE_FAIL"
        ),
        "frozen_on": str(date.today()),
        "score_sha256": (
            EXPECTED_SCORE_SHA256
        ),
        "acceptance_decision": (
            EXPECTED_DECISION
        ),
        "source_artifacts": {
            "score_v2_sha256": (
                EXPECTED_SCORE_SHA256
            ),
            "prediction_v2_sha256": (
                EXPECTED_PREDICTION_SHA256
            ),
            "prediction_result_v2_sha256": (
                EXPECTED_PREDICTION_RESULT_SHA256
            ),
            "acceptance_thresholds_v2_sha256": (
                EXPECTED_THRESHOLDS_SHA256
            ),
            "independent_contract_pack_v5_sha256": (
                EXPECTED_PACK_SHA256
            ),
        },
        "frozen_metrics": {
            "four_field_exact_match": {
                "correct": 38,
                "total": 40,
                "percent": 95.0,
                "gate": "PASS",
            },
            "resolution_status_accuracy": {
                "correct": 39,
                "total": 40,
                "percent": 97.5,
                "gate": "PASS",
            },
            "source_domain_accuracy": {
                "correct": 39,
                "total": 40,
                "percent": 97.5,
                "gate": "PASS",
            },
            "source_class_accuracy": {
                "correct": 38,
                "total": 40,
                "percent": 95.0,
                "gate": "PASS",
            },
            "source_class_macro_recall": {
                "percent": 95.8,
                "gate": "PASS",
            },
            "unresolved_recall": {
                "correct": 5,
                "total": 6,
                "percent": 83.3,
                "required_correct": 6,
                "required_percent": 100.0,
                "gate": "FAIL",
            },
            "resolved_recall": {
                "correct": 33,
                "total": 34,
                "percent": 97.1,
                "gate": "PASS",
            },
            "contrast_consistency": {
                "correct": 11,
                "total": 12,
                "percent": 91.7,
                "gate": "PASS",
            },
            "malformed_or_error_count": {
                "count": 0,
                "total": 40,
                "gate": "PASS",
            },
        },
        "frozen_failure_surface": {
            "failed_hard_gates": (
                EXPECTED_FAILED_HARD_GATES
            ),
            "passed_hard_gate_count": 8,
            "failed_hard_gate_count": 1,
            "all_resolved_class_floor_gates_passed": True,
            "four_field_failure_cases": (
                EXPECTED_FAILED_CASES
            ),
            "unresolved_failure_cases": (
                EXPECTED_UNRESOLVED_FAILURE_CASES
            ),
            "failed_contrast_groups": [
                "foreign_issuing_vs_external_agency_service",
            ],
        },
        "methodology": {
            "first_untouched_run": True,
            "predictions_frozen_before_scoring": True,
            "thresholds_frozen_before_prediction": True,
            "score_frozen_before_failure_analysis": True,
            "manual_override": False,
            "rerun_after_failure_authorised": False,
            "threshold_change_after_failure_authorised": False,
        },
        "authorisations": {
            "failure_analysis_v2_construction_authorised": True,
            "human_diagnostic_review_v2_authorised": True,
            "classifier_rerun_authorised": False,
            "threshold_change_authorised": False,
            "classifier_prompt_change_authorised": False,
            "classifier_implementation_change_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": (
                "source_boundary_classifier_failure_analysis_v2"
            ),
            "authorised": True,
            "model_calls": 0,
            "purpose": (
                "Diagnose the two frozen four-field failures, with primary "
                "attention to the single unresolved-safety failure, before "
                "authorising any classifier design change."
            ),
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            artifact,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    saved = load_json(
        OUTPUT_PATH
    )

    if saved.get("status") != (
        "FROZEN_FIRST_UNTOUCHED_ACCEPTANCE_FAIL"
    ):
        raise RuntimeError(
            "Saved score-result status changed."
        )

    if saved.get(
        "score_sha256"
    ) != EXPECTED_SCORE_SHA256:
        raise RuntimeError(
            "Saved score SHA binding changed."
        )

    saved_auth = saved.get(
        "authorisations",
        {},
    )

    if saved_auth.get(
        "failure_analysis_v2_construction_authorised"
    ) is not True:
        raise RuntimeError(
            "Score-result freeze did not authorise failure analysis."
        )

    for forbidden in (
        "classifier_rerun_authorised",
        "threshold_change_authorised",
        "classifier_prompt_change_authorised",
        "classifier_implementation_change_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if saved_auth.get(forbidden) is not False:
            raise RuntimeError(
                f"Score-result freeze unexpectedly enables {forbidden}."
            )

    print("Waypoint source-boundary classifier score-result freeze v2")
    print("=" * 72)
    print(
        f"Score SHA256:               "
        f"{sha256(SCORE_PATH)}"
    )
    print(
        f"Prediction SHA256:          "
        f"{sha256(PREDICTIONS_PATH)}"
    )
    print(
        f"Prediction-result SHA256:   "
        f"{sha256(PREDICTION_RESULT_PATH)}"
    )
    print(
        f"Threshold-v2 SHA256:        "
        f"{sha256(THRESHOLDS_PATH)}"
    )
    print()
    print("Frozen acceptance result")
    print("-" * 72)
    print("Four-field exact:           38/40 (95.0%) PASS")
    print("Resolution accuracy:        39/40 (97.5%) PASS")
    print("Source-domain accuracy:     39/40 (97.5%) PASS")
    print("Source-class accuracy:      38/40 (95.0%) PASS")
    print("Source-class macro recall:  95.8% PASS")
    print("Unresolved recall:          5/6 (83.3%) FAIL")
    print("Resolved recall:            33/34 (97.1%) PASS")
    print("Contrast consistency:       11/12 (91.7%) PASS")
    print("Malformed/error count:      0/40 PASS")
    print()
    print("Resolved-class floors:      ALL PASS")
    print("Failed hard gates:          1/9")
    print("Failed gate:                unresolved_recall")
    print()
    print("Four-field failure cases:   iv4_026, iv4_036")
    print("Unresolved safety failure:  iv4_036")
    print(
        "Failed contrast group:      "
        "foreign_issuing_vs_external_agency_service"
    )
    print()
    print("Acceptance decision:        FAIL")
    print("Score result:               FROZEN")
    print("Classifier rerun:           NOT AUTHORISED")
    print("Threshold change:           NOT AUTHORISED")
    print("Prompt change:              NOT AUTHORISED")
    print("Implementation change:      NOT AUTHORISED")
    print("Candidate v7:               NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print()
    print("Failure analysis v2:        AUTHORISED")
    print("Human diagnostic review:    AUTHORISED")
    print()
    print("Next task:                  FAILURE ANALYSIS V2")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(
        f"Score-result SHA256:        "
        f"{sha256(OUTPUT_PATH)}"
    )
    print()
    print("Model calls:                NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Score-result freeze v2: PASS")


if __name__ == "__main__":
    main()
