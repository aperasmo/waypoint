"""Diagnose the frozen Waypoint source-boundary classifier v2 failures.

DIAGNOSTIC ONLY.
- No model calls.
- No classifier rerun.
- No threshold changes.
- No prompt or implementation changes.
- Reads only already-frozen experimental evidence.
- Diagnoses mechanisms before any redesign is authorised.

Run from backend/:
    uv run python -m py_compile scripts/analyse_source_boundary_classifier_failures_v2.py
    uv run python -m scripts.analyse_source_boundary_classifier_failures_v2

Output:
    tests/source_boundary_classifier_failure_analysis_v2.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

CLASSIFIER_PATH = (
    BACKEND_DIR
    / "_experiments"
    / "source_boundary_classifier_v2.py"
)

DESIGN_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v3.json"
)

PACK_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_contract_test_pack_v5.json"
)

PREDICTIONS_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_predictions_v2.json"
)

SCORE_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_score_v2.json"
)

SCORE_RESULT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_score_result_v2.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_failure_analysis_v2.json"
)

EXPECTED_CLASSIFIER_SHA256 = (
    "8193FCDDB48585EC8A8BA8BCC477D123"
    "011B50F2F38531BEB2D88836975FF949"
)

EXPECTED_DESIGN_SHA256 = (
    "0EFBA11ECA5EE07A41BBB841817B93CB4"
    "69BFA5B48BF42DF268B6A8F3257356B"
)

EXPECTED_PACK_SHA256 = (
    "1B3CEA56504E3932C7DCA342DF99DC225"
    "23A4676B1C22714B9A122DDD566E67B"
)

EXPECTED_PREDICTION_SHA256 = (
    "7EE68C61443D73B298574A8EB2BBA4425"
    "A99D577F618B7565848F16FEA8C6EF1"
)

EXPECTED_SCORE_SHA256 = (
    "A26CADECFE6B31D9010F1855A1AAC99D"
    "76AF622554DB750191DDA143195570E7"
)

EXPECTED_SCORE_RESULT_SHA256 = (
    "5ABF0596DBCC0AAB6EDCA3F81403FBC25"
    "C98142608D0DEF036D07D026A786F9C"
)

EXPECTED_FAILED_CASES = {
    "iv4_026",
    "iv4_036",
}


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
            "Refusing failure analysis v2."
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


def by_case_id(
    items: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}

    for item in items:
        case_id = item.get("case_id")

        if not isinstance(case_id, str):
            raise RuntimeError(
                "Case item missing case_id."
            )

        if case_id in result:
            raise RuntimeError(
                f"Duplicate case_id: {case_id}"
            )

        result[case_id] = item

    return result


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Failure-analysis artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    for path, expected, label in (
        (
            CLASSIFIER_PATH,
            EXPECTED_CLASSIFIER_SHA256,
            "Frozen classifier implementation v2",
        ),
        (
            DESIGN_PATH,
            EXPECTED_DESIGN_SHA256,
            "Frozen classifier design v3",
        ),
        (
            PACK_PATH,
            EXPECTED_PACK_SHA256,
            "Frozen independent pack v5",
        ),
        (
            PREDICTIONS_PATH,
            EXPECTED_PREDICTION_SHA256,
            "Frozen first-run predictions v2",
        ),
        (
            SCORE_PATH,
            EXPECTED_SCORE_SHA256,
            "Frozen first-run score v2",
        ),
        (
            SCORE_RESULT_PATH,
            EXPECTED_SCORE_RESULT_SHA256,
            "Frozen score-result v2",
        ),
    ):
        require_sha(path, expected, label)

    design = load_json(DESIGN_PATH)
    pack = load_json(PACK_PATH)
    predictions = load_json(PREDICTIONS_PATH)
    score = load_json(SCORE_PATH)
    score_result = load_json(SCORE_RESULT_PATH)

    if score_result.get("schema") != (
        "waypoint-source-boundary-classifier-score-result-v2"
    ):
        raise RuntimeError(
            "Unexpected score-result schema."
        )

    if score_result.get("status") != (
        "FROZEN_FIRST_UNTOUCHED_ACCEPTANCE_FAIL"
    ):
        raise RuntimeError(
            "Score result is not frozen as the first untouched failure."
        )

    if score_result.get(
        "authorisations",
        {},
    ).get(
        "failure_analysis_v2_construction_authorised"
    ) is not True:
        raise RuntimeError(
            "Failure-analysis v2 construction is not authorised."
        )

    pack_cases = pack.get("tests")
    prediction_cases = predictions.get("cases")
    score_cases = score.get("case_results")

    if (
        not isinstance(pack_cases, list)
        or not isinstance(prediction_cases, list)
        or not isinstance(score_cases, list)
    ):
        raise RuntimeError(
            "Frozen case collections are missing."
        )

    gold_by_id = by_case_id(pack_cases)
    pred_by_id = by_case_id(prediction_cases)
    score_by_id = by_case_id(score_cases)

    failed_cases = {
        case_id
        for case_id, item in score_by_id.items()
        if item.get("four_field_correct") is False
    }

    if failed_cases != EXPECTED_FAILED_CASES:
        raise RuntimeError(
            "Frozen failure set changed.\n"
            f"Expected: {sorted(EXPECTED_FAILED_CASES)}\n"
            f"Actual:   {sorted(failed_cases)}"
        )

    case_026_gold = gold_by_id["iv4_026"]
    case_026_pred = pred_by_id["iv4_026"]

    case_036_gold = gold_by_id["iv4_036"]
    case_036_pred = pred_by_id["iv4_036"]

    if case_026_gold["expected"]["source_class"] != (
        "external_agency_assessment_or_service"
    ):
        raise RuntimeError(
            "iv4_026 gold class changed."
        )

    if case_026_pred["source_class"] != (
        "foreign_issuing_authority_procedure"
    ):
        raise RuntimeError(
            "iv4_026 prediction changed."
        )

    if case_036_gold["expected"]["source_class"] != (
        "unresolved"
    ):
        raise RuntimeError(
            "iv4_036 gold class changed."
        )

    if case_036_pred["source_class"] != (
        "other_official_external_authority"
    ):
        raise RuntimeError(
            "iv4_036 prediction changed."
        )

    if case_036_gold.get(
        "trusted_source_context"
    ) is not None:
        raise RuntimeError(
            "iv4_036 unexpectedly contains trusted context."
        )

    classifier_text = CLASSIFIER_PATH.read_text(
        encoding="utf-8"
    )

    required_prompt_fragments = [
        (
            "foreign_issuing_authority_procedure "
            "requires an actual issuing role."
        ),
        (
            "other_official_external_authority "
            "is last-resort and requires its trusted"
        ),
        (
            "Use unresolved when two or more classes "
            "remain materially plausible"
        ),
    ]

    for fragment in required_prompt_fragments:
        if fragment not in classifier_text:
            raise RuntimeError(
                "Expected design-v3 rule missing from classifier prompt: "
                + fragment
            )

    # The v2 implementation derives dependent fields from source_class
    # but has no deterministic post-prediction context-gate validator.
    deterministic_gate_function_markers = [
        "validate_context_gate",
        "enforce_context_gate",
        "apply_context_gate",
    ]

    deterministic_context_gate_present = any(
        marker in classifier_text
        for marker in deterministic_gate_function_markers
    )

    if deterministic_context_gate_present:
        raise RuntimeError(
            "Classifier unexpectedly contains a deterministic context-gate "
            "enforcement function; diagnostic assumption no longer holds."
        )

    analysis = {
        "schema": (
            "waypoint-source-boundary-classifier-failure-analysis-v2"
        ),
        "status": (
            "FROZEN_DIAGNOSTIC_READY_FOR_HUMAN_REVIEW"
        ),
        "analysed_on": str(date.today()),
        "source_artifacts": {
            "classifier_implementation_v2_sha256": (
                EXPECTED_CLASSIFIER_SHA256
            ),
            "classifier_design_v3_sha256": (
                EXPECTED_DESIGN_SHA256
            ),
            "independent_contract_pack_v5_sha256": (
                EXPECTED_PACK_SHA256
            ),
            "prediction_v2_sha256": (
                EXPECTED_PREDICTION_SHA256
            ),
            "score_v2_sha256": (
                EXPECTED_SCORE_SHA256
            ),
            "score_result_v2_sha256": (
                EXPECTED_SCORE_RESULT_SHA256
            ),
        },
        "acceptance_summary": {
            "decision": "FAIL",
            "hard_gates_passed": 8,
            "hard_gates_failed": 1,
            "failed_hard_gate": (
                "unresolved_recall"
            ),
            "four_field_exact": {
                "correct": 38,
                "total": 40,
                "percent": 95.0,
            },
            "unresolved_recall": {
                "correct": 5,
                "total": 6,
                "percent": 83.3,
                "required_correct": 6,
                "required_percent": 100.0,
            },
            "resolved_recall": {
                "correct": 33,
                "total": 34,
                "percent": 97.1,
            },
            "execution_errors": 0,
        },
        "failure_count": 2,
        "failures": [
            {
                "case_id": "iv4_026",
                "severity": (
                    "CLASS_BOUNDARY_ERROR_NON_SAFETY_GATE"
                ),
                "proposition": (
                    case_026_gold["unsupported_proposition"]
                ),
                "trusted_source_context": (
                    case_026_gold.get(
                        "trusted_source_context"
                    )
                ),
                "gold": (
                    case_026_gold["expected"]
                ),
                "gold_basis": (
                    case_026_gold["basis"]
                ),
                "prediction": {
                    "resolution_status": (
                        case_026_pred[
                            "resolution_status"
                        ]
                    ),
                    "source_domain": (
                        case_026_pred[
                            "source_domain"
                        ]
                    ),
                    "source_class": (
                        case_026_pred[
                            "source_class"
                        ]
                    ),
                    "responsible_authority_type": (
                        case_026_pred[
                            "responsible_authority_type"
                        ]
                    ),
                    "basis": (
                        case_026_pred["basis"]
                    ),
                },
                "mechanism": (
                    "FOREIGN_ISSUING_ROLE_SEMANTIC_OVERREACH"
                ),
                "diagnosis": (
                    "The classifier treated a generic authenticity-"
                    "verification service for an already-issued document as "
                    "an issuing-authority procedure. The frozen gold boundary "
                    "requires an actual issuing role for the relevant "
                    "document/record; a generic agency verification service "
                    "remains external_agency_assessment_or_service when the "
                    "issuer role is not established."
                ),
                "design_signal": {
                    "foreign_issuing_boundary_requires_revision": True,
                    "specific_issue": (
                        "The prompt permits verification within the foreign-"
                        "issuing class, but does not state strongly enough "
                        "that the proposition itself must establish that the "
                        "authority is acting as issuer of the relevant record."
                    ),
                    "generic_rule_candidate": (
                        "Verification alone is not sufficient for the foreign-"
                        "issuing class. The proposition or trusted context must "
                        "establish that the authority is the issuer of the "
                        "relevant document or record and is acting in that "
                        "issuing role."
                    ),
                },
            },
            {
                "case_id": "iv4_036",
                "severity": (
                    "UNRESOLVED_SAFETY_GATE_FAILURE"
                ),
                "proposition": (
                    case_036_gold["unsupported_proposition"]
                ),
                "trusted_source_context": (
                    case_036_gold.get(
                        "trusted_source_context"
                    )
                ),
                "gold": (
                    case_036_gold["expected"]
                ),
                "gold_basis": (
                    case_036_gold["basis"]
                ),
                "prediction": {
                    "resolution_status": (
                        case_036_pred[
                            "resolution_status"
                        ]
                    ),
                    "source_domain": (
                        case_036_pred[
                            "source_domain"
                        ]
                    ),
                    "source_class": (
                        case_036_pred[
                            "source_class"
                        ]
                    ),
                    "responsible_authority_type": (
                        case_036_pred[
                            "responsible_authority_type"
                        ]
                    ),
                    "basis": (
                        case_036_pred["basis"]
                    ),
                },
                "mechanism": (
                    "CONTEXT_GATE_NOT_DETERMINISTICALLY_ENFORCED"
                ),
                "diagnosis": (
                    "The model selected the context-gated "
                    "other_official_external_authority class even though no "
                    "trusted source context was supplied. Design v3 explicitly "
                    "requires publisher_family=other_official_authority and "
                    "authority_role=other_official_operational_owner for that "
                    "class. Implementation v2 relies on prompt compliance and "
                    "does not independently enforce the gate after prediction."
                ),
                "design_signal": {
                    "context_gate_rule_itself_invalid": False,
                    "context_gate_rule_should_be_preserved": True,
                    "prompt_only_enforcement_insufficient": True,
                    "deterministic_enforcement_candidate": (
                        "For context-gated classes, validate required trusted "
                        "context after model prediction. If required context is "
                        "absent or does not match, resolve to unresolved under "
                        "the frozen semantic contract rather than allowing the "
                        "resolved class through."
                    ),
                    "classes_potentially_affected": [
                        "manual_instruction_transition",
                        "inz_non_manual_procedure_or_interpretation",
                        "other_official_external_authority",
                    ],
                },
            },
        ],
        "cross_failure_diagnosis": {
            "primary_observed_failure": (
                "CONTEXT_GATE_EXECUTION_ENFORCEMENT"
            ),
            "secondary_observed_failure": (
                "FOREIGN_ISSUING_ROLE_BOUNDARY"
            ),
            "retrieval_related": False,
            "execution_or_schema_error_related": False,
            "threshold_problem_observed": False,
            "gold_pack_defect_observed": False,
            "resolved_class_collapse_observed": False,
            "unresolved_over_abstention_observed": False,
            "unresolved_under_abstention_observed": True,
            "under_abstention_count": 1,
        },
        "methodological_implications": {
            "pack_v5_status_after_inspection": (
                "DEVELOPMENT_DIAGNOSTIC_EVIDENCE"
            ),
            "same_pack_may_be_used_for_debugging": True,
            "same_pack_may_be_claimed_as_fresh_untouched_acceptance_again": False,
            "same_prediction_set_may_be_rerun_for_acceptance": False,
            "threshold_change_permitted": False,
            "automatic_retry_permitted": False,
            "manual_override_permitted": False,
            "fresh_independent_acceptance_set_required_after_any_revision": True,
        },
        "change_authorisation": {
            "classifier_design_v4_construction_authorised": False,
            "classifier_prompt_change_authorised": False,
            "classifier_implementation_change_authorised": False,
            "classifier_rerun_authorised": False,
            "threshold_change_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "external_retrieval_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "authorisations": {
            "human_diagnostic_review_v2_authorised": True,
            "diagnostic_review_may_consider_design_revision": True,
            "diagnostic_review_may_consider_deterministic_context_gate": True,
            "diagnostic_review_may_consider_foreign_issuing_boundary_revision": True,
            "classifier_design_change_authorised": False,
            "model_run_authorised": False,
        },
        "next_engineering_task": {
            "name": (
                "source_boundary_classifier_human_diagnostic_review_v2"
            ),
            "authorised": True,
            "model_calls": 0,
            "purpose": (
                "Review the two frozen mechanisms and decide whether a "
                "generic design-v4 revision is justified before any code or "
                "prompt is changed."
            ),
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            analysis,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)

    if saved.get("status") != (
        "FROZEN_DIAGNOSTIC_READY_FOR_HUMAN_REVIEW"
    ):
        raise RuntimeError(
            "Saved failure-analysis status changed."
        )

    if saved.get(
        "failure_count"
    ) != 2:
        raise RuntimeError(
            "Saved failure count changed."
        )

    if saved.get(
        "change_authorisation",
        {},
    ).get(
        "classifier_design_v4_construction_authorised"
    ) is not False:
        raise RuntimeError(
            "Failure analysis unexpectedly authorises design v4."
        )

    if saved.get(
        "authorisations",
        {},
    ).get(
        "human_diagnostic_review_v2_authorised"
    ) is not True:
        raise RuntimeError(
            "Failure analysis did not authorise human review."
        )

    print("Waypoint source-boundary classifier failure analysis v2")
    print("=" * 72)
    print(
        f"Classifier SHA256:          "
        f"{sha256(CLASSIFIER_PATH)}"
    )
    print(
        f"Design-v3 SHA256:           "
        f"{sha256(DESIGN_PATH)}"
    )
    print(
        f"Pack-v5 SHA256:             "
        f"{sha256(PACK_PATH)}"
    )
    print(
        f"Prediction SHA256:          "
        f"{sha256(PREDICTIONS_PATH)}"
    )
    print(
        f"Score SHA256:               "
        f"{sha256(SCORE_PATH)}"
    )
    print(
        f"Score-result SHA256:        "
        f"{sha256(SCORE_RESULT_PATH)}"
    )
    print()
    print("Frozen failure surface")
    print("-" * 72)
    print("Acceptance decision:        FAIL")
    print("Hard gates passed:          8/9")
    print("Failed hard gate:           unresolved_recall")
    print("Four-field failures:        2/40")
    print("Execution/schema errors:    0/40")
    print()
    print("iv4_026")
    print("  Gold:                     external_agency_assessment_or_service")
    print("  Predicted:                foreign_issuing_authority_procedure")
    print("  Mechanism:                FOREIGN_ISSUING_ROLE_SEMANTIC_OVERREACH")
    print("  Safety-gate failure:      NO")
    print()
    print("iv4_036")
    print("  Gold:                     unresolved")
    print("  Predicted:                other_official_external_authority")
    print("  Trusted context:          NONE")
    print("  Mechanism:                CONTEXT_GATE_NOT_DETERMINISTICALLY_ENFORCED")
    print("  Safety-gate failure:      YES")
    print()
    print("Primary observed failure:   CONTEXT_GATE_EXECUTION_ENFORCEMENT")
    print("Secondary observed failure: FOREIGN_ISSUING_ROLE_BOUNDARY")
    print()
    print("Threshold problem observed: NO")
    print("Gold-pack defect observed:  NO")
    print("Retrieval related:          NO")
    print()
    print("Pack-v5 future status:      DEVELOPMENT/DIAGNOSTIC")
    print("Same-pack untouched rerun:  NOT VALID")
    print("Fresh acceptance set after revision: REQUIRED")
    print()
    print("Design-v4 construction:     NOT AUTHORISED")
    print("Prompt change:              NOT AUTHORISED")
    print("Implementation change:      NOT AUTHORISED")
    print("Classifier rerun:           NOT AUTHORISED")
    print("Threshold change:           NOT AUTHORISED")
    print("Candidate v7:               NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print()
    print("Human diagnostic review v2: AUTHORISED")
    print()
    print("Next task:                  HUMAN DIAGNOSTIC REVIEW V2")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(
        f"Failure-analysis SHA256:    "
        f"{sha256(OUTPUT_PATH)}"
    )
    print()
    print("Model calls:                NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Failure analysis v2: PASS")


if __name__ == "__main__":
    main()
