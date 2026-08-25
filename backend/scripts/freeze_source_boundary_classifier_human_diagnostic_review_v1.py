"""Freeze the human diagnostic conclusion from classifier failure analysis v1.

DIAGNOSTIC FREEZE ONLY.
No model calls. No classifier changes. No prompt changes. No production changes.

This artifact authorises design work for a generic classifier design v3 only.
It does not authorise implementation, rerunning the observed contract pack,
candidate v7, or production integration.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_human_diagnostic_review_v1.py
    uv run python -m scripts.freeze_source_boundary_classifier_human_diagnostic_review_v1

Output:
    tests/source_boundary_classifier_human_diagnostic_review_v1.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

ANALYSIS_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_failure_analysis_v1.json"
)
SCORE_RESULT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_score_result_v1.json"
)
OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_human_diagnostic_review_v1.json"
)

EXPECTED_ANALYSIS_SHA256 = (
    "A46BF63D831B61235679CA4858FE309E7"
    "496F7770EFFDC7D9E9468C0615CA1E0"
)
EXPECTED_SCORE_RESULT_SHA256 = (
    "CFEEC8CAD5009FACA2FA6AAA10FC7E88D"
    "CA490DCC0AD11AA3CFF4E40334ECE17"
)

EXPECTED_FAILURE_IDS = {
    "sbv2_03",
    "sbv2_10",
    "sbv2_11",
    "sbv2_12",
    "sbv2_13",
    "sbv2_14",
    "sbv2_22",
    "sbv2_26",
}

EXPECTED_OVER_ABSTENTION_IDS = {
    "sbv2_03",
    "sbv2_11",
    "sbv2_13",
    "sbv2_14",
    "sbv2_22",
}

EXPECTED_ERROR_IDS = {
    "sbv2_10",
    "sbv2_12",
}

EXPECTED_WRONG_CLASS_IDS = {
    "sbv2_26",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_sha(path: Path, expected: str, label: str) -> None:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")

    actual = sha256(path)

    if actual != expected:
        raise SystemExit(
            f"{label} SHA mismatch.\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Refusing to freeze human diagnostic review."
        )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{path.name}: root must be a JSON object."
        )

    return payload


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Human diagnostic review already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_sha(
        ANALYSIS_PATH,
        EXPECTED_ANALYSIS_SHA256,
        "Frozen failure analysis v1",
    )
    require_sha(
        SCORE_RESULT_PATH,
        EXPECTED_SCORE_RESULT_SHA256,
        "Frozen score result v1",
    )

    analysis = load_json(ANALYSIS_PATH)
    score_result = load_json(SCORE_RESULT_PATH)

    if analysis.get("schema") != (
        "waypoint-source-boundary-classifier-failure-analysis-v1"
    ):
        raise RuntimeError("Unexpected failure-analysis schema.")

    if analysis.get("status") != (
        "DIAGNOSTIC_COMPLETE_NO_CHANGES_AUTHORISED"
    ):
        raise RuntimeError("Unexpected failure-analysis status.")

    if score_result.get("status") != (
        "FROZEN_FIRST_UNTOUCHED_ACCEPTANCE_FAIL"
    ):
        raise RuntimeError("Unexpected score-result status.")

    failures = analysis.get("all_failures")

    if not isinstance(failures, list) or len(failures) != 8:
        raise RuntimeError("Expected exactly eight frozen failures.")

    failure_ids = {
        item.get("test_id")
        for item in failures
        if isinstance(item, dict)
    }

    if failure_ids != EXPECTED_FAILURE_IDS:
        raise RuntimeError(
            "Frozen eight-case failure inventory changed."
        )

    mechanism_summary = analysis.get(
        "mechanism_summary",
        {},
    )

    expected_mechanisms = {
        "over_abstention_resolved_to_unresolved": 5,
        "under_abstention_unresolved_to_resolved": 0,
        "wrong_source_domain": 0,
        "wrong_source_class_within_correct_domain": 1,
        "authority_type_only_mismatch": 0,
        "multi_field_resolved_classification_mismatch": 0,
        "execution_or_validation_error": 2,
    }

    for key, expected in expected_mechanisms.items():
        if mechanism_summary.get(key) != expected:
            raise RuntimeError(
                f"Mechanism count changed for {key!r}."
            )

    over_abstentions = {
        item["test_id"]
        for item in failures
        if item.get("failure_type")
        == "over_abstention_resolved_to_unresolved"
    }

    errors = {
        item["test_id"]
        for item in failures
        if item.get("failure_type")
        == "execution_or_validation_error"
    }

    wrong_class = {
        item["test_id"]
        for item in failures
        if item.get("failure_type")
        == "wrong_source_class_within_correct_domain"
    }

    if over_abstentions != EXPECTED_OVER_ABSTENTION_IDS:
        raise RuntimeError(
            "Over-abstention case inventory changed."
        )

    if errors != EXPECTED_ERROR_IDS:
        raise RuntimeError(
            "Validation-error case inventory changed."
        )

    if wrong_class != EXPECTED_WRONG_CLASS_IDS:
        raise RuntimeError(
            "Wrong-class case inventory changed."
        )

    failure_by_id = {
        item["test_id"]: item
        for item in failures
    }

    # Evidence supporting the primary diagnosis:
    # each of these propositions is semantically recognisable as a frozen
    # source class, but the model basis explicitly abstains because trusted
    # source context is absent.
    for test_id in EXPECTED_OVER_ABSTENTION_IDS:
        item = failure_by_id[test_id]
        prediction = item.get("prediction")

        if not isinstance(prediction, dict):
            raise RuntimeError(
                f"{test_id}: missing prediction object."
            )

        if prediction.get("resolution_status") != "unresolved":
            raise RuntimeError(
                f"{test_id}: expected frozen unresolved prediction."
            )

        if item.get("trusted_source_context") is not None:
            raise RuntimeError(
                f"{test_id}: over-abstention diagnosis expects no trusted "
                "source context."
            )

    # The foreign-customs case must remain bound to the observed class
    # confusion: correct external domain, wrong specialised source class.
    customs = failure_by_id["sbv2_26"]

    if customs.get("gold", {}).get(
        "source_class"
    ) != "other_official_external_authority":
        raise RuntimeError(
            "Frozen customs gold class changed."
        )

    if customs.get("prediction", {}).get(
        "source_class"
    ) != "foreign_issuing_authority_procedure":
        raise RuntimeError(
            "Frozen customs predicted class changed."
        )

    if customs.get("prediction", {}).get(
        "source_domain"
    ) != "responsible_external_official_authority":
        raise RuntimeError(
            "Frozen customs source-domain prediction changed."
        )

    # Error records only establish schema rejection. They do not preserve the
    # rejected raw model payload, so this review must not invent its contents.
    for test_id in EXPECTED_ERROR_IDS:
        item = failure_by_id[test_id]

        if item.get("error_type") != "ClassifierContractError":
            raise RuntimeError(
                f"{test_id}: frozen error type changed."
            )

        if item.get("error") != (
            "Classifier model output violates the frozen schema."
        ):
            raise RuntimeError(
                f"{test_id}: frozen validation-error message changed."
            )

    review = {
        "schema": (
            "waypoint-source-boundary-classifier-human-diagnostic-review-v1"
        ),
        "status": (
            "FROZEN_DIAGNOSIS_REVISED_CLASSIFIER_DESIGN_V3_AUTHORISED"
        ),
        "reviewed_on": str(date.today()),
        "source_artifacts": {
            "failure_analysis_v1_sha256": (
                EXPECTED_ANALYSIS_SHA256
            ),
            "score_result_v1_sha256": (
                EXPECTED_SCORE_RESULT_SHA256
            ),
        },
        "frozen_observations": {
            "first_acceptance_result": "FAIL",
            "four_field_failures": 8,
            "gold_resolved_failures": 8,
            "gold_unresolved_failures": 0,
            "over_abstentions": 5,
            "wrong_class_with_correct_domain": 1,
            "schema_validation_rejections": 2,
            "under_abstentions": 0,
            "unresolved_recall": "6/6",
            "current_fee_or_charge_information_recall": "0/2",
            "inz_live_service_information_recall": "0/3",
        },
        "diagnosis": {
            "primary": {
                "name": (
                    "context_gate_overreach_on_semantically_resolvable_classes"
                ),
                "confidence": "high",
                "evidence_case_ids": sorted(
                    EXPECTED_OVER_ABSTENTION_IDS
                ),
                "finding": (
                    "The classifier applies trusted-source-context caution "
                    "too broadly. It abstains on propositions whose semantic "
                    "role is sufficient to identify a frozen source class."
                ),
                "affected_observed_classes": [
                    "operational_manual_instruction",
                    "inz_live_service_information",
                    "current_fee_or_charge_information",
                    "external_entitlement_or_service_regime",
                ],
                "not_supported": (
                    "This does not justify removing context gates from classes "
                    "whose frozen design explicitly requires trusted context."
                ),
            },
            "secondary": {
                "name": (
                    "foreign_issuing_authority_class_scope_overreach"
                ),
                "confidence": "high",
                "evidence_case_ids": ["sbv2_26"],
                "finding": (
                    "The classifier treats a generic foreign official "
                    "operational procedure as a foreign issuing-authority "
                    "procedure. The specialised issuing class needs a narrower "
                    "role boundary."
                ),
                "required_exclusion": (
                    "A foreign authority's customs, border, declaration, or "
                    "other operational process is not an issuing-authority "
                    "procedure merely because the authority is foreign."
                ),
            },
            "robustness": {
                "name": "schema_validation_rejections",
                "confidence": "medium",
                "evidence_case_ids": sorted(EXPECTED_ERROR_IDS),
                "finding": (
                    "Two model calls returned outputs rejected by the frozen "
                    "schema/validation contract."
                ),
                "known": (
                    "The calls produced classifier output that failed frozen "
                    "schema validation."
                ),
                "unknown": (
                    "The rejected raw model payload was not preserved, so the "
                    "specific inconsistent field combination cannot be "
                    "reconstructed from the frozen evidence."
                ),
                "constraint": (
                    "Do not relax deterministic validation merely to make "
                    "these cases pass."
                ),
            },
        },
        "revised_design_v3_requirements": [
            {
                "id": "D3-1",
                "requirement": (
                    "Separate semantic source-home recognition from trusted "
                    "context gates. Trusted context must be required only for "
                    "the source classes whose frozen authority contract "
                    "explicitly requires it."
                ),
            },
            {
                "id": "D3-2",
                "requirement": (
                    "Permit semantic resolution of operational immigration "
                    "instruction rules when the proposition itself is clearly "
                    "an immigration criterion, exception, requirement, or "
                    "instruction rule."
                ),
            },
            {
                "id": "D3-3",
                "requirement": (
                    "Permit semantic resolution of time-varying INZ service "
                    "states, including current processing timeframes, channel "
                    "availability, and capped-service availability, without "
                    "requiring publication metadata when the proposition "
                    "itself identifies the live-service role."
                ),
            },
            {
                "id": "D3-4",
                "requirement": (
                    "Permit semantic resolution of current payable immigration "
                    "fee, levy, or charge values as current_fee_or_charge_information "
                    "without requiring explicit source metadata."
                ),
            },
            {
                "id": "D3-5",
                "requirement": (
                    "Permit semantic resolution of separately administered "
                    "public benefits or service entitlements to "
                    "external_entitlement_or_service_regime when the "
                    "proposition itself identifies an external public-service "
                    "entitlement question."
                ),
            },
            {
                "id": "D3-6",
                "requirement": (
                    "Keep context gates for genuinely context-dependent "
                    "classes, including manual instruction transitions, "
                    "INZ non-Manual procedure/interpretation publications, "
                    "and the generic other-official external-authority "
                    "last-resort class."
                ),
            },
            {
                "id": "D3-7",
                "requirement": (
                    "Narrow foreign_issuing_authority_procedure to procedures "
                    "owned by an authority acting in an issuing role. Explicitly "
                    "exclude unrelated customs, border, declaration, benefit, "
                    "professional, and general operational processes."
                ),
            },
            {
                "id": "D3-8",
                "requirement": (
                    "Reduce invalid categorical combinations by design. "
                    "Evaluate whether the model should predict the minimum "
                    "independent categorical state and deterministic code "
                    "should derive dependent domain/authority fields."
                ),
            },
            {
                "id": "D3-9",
                "requirement": (
                    "Preserve unresolved as the correct outcome when semantic "
                    "ownership is genuinely ambiguous. The observed 6/6 "
                    "unresolved recall must not be traded away casually."
                ),
            },
            {
                "id": "D3-10",
                "requirement": (
                    "Do not include synthetic test IDs, benchmark literals, "
                    "expected labels, or case-specific wording in the revised "
                    "classifier design or implementation."
                ),
            },
        ],
        "evaluation_consequence": {
            "contract_pack_v3_status": (
                "DEVELOPMENT_AND_REGRESSION_ONLY_AFTER_OBSERVATION"
            ),
            "contract_pack_v3_may_be_used_for_diagnosis": True,
            "contract_pack_v3_may_be_used_for_regression": True,
            "contract_pack_v3_must_not_support_a_new_untouched_acceptance_claim": True,
            "new_independent_acceptance_pack_required_after_design_v3_freeze": True,
            "acceptance_thresholds_must_not_be_lowered": True,
            "first_run_failure_must_remain_preserved": True,
        },
        "authorisations": {
            "classifier_design_v3_authorised": True,
            "classifier_implementation_v2_authorised": False,
            "classifier_prompt_change_authorised": False,
            "classifier_model_run_authorised": False,
            "same_pack_untouched_rerun_authorised": False,
            "new_independent_acceptance_pack_build_authorised": False,
            "acceptance_threshold_change_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": "source_boundary_classifier_design_v3",
            "authorised": True,
            "model_calls": 0,
            "purpose": (
                "Write and freeze a generic revised classifier design that "
                "addresses the diagnosed context-gate scope, specialised class "
                "boundary, and output-validity issues without using case-specific "
                "logic."
            ),
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            review,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)

    if saved.get("status") != (
        "FROZEN_DIAGNOSIS_REVISED_CLASSIFIER_DESIGN_V3_AUTHORISED"
    ):
        raise RuntimeError(
            "Saved human diagnostic review status changed."
        )

    auth = saved.get("authorisations", {})

    if auth.get("classifier_design_v3_authorised") is not True:
        raise RuntimeError(
            "Revised classifier design v3 was not authorised."
        )

    for forbidden in (
        "classifier_implementation_v2_authorised",
        "classifier_prompt_change_authorised",
        "classifier_model_run_authorised",
        "same_pack_untouched_rerun_authorised",
        "new_independent_acceptance_pack_build_authorised",
        "acceptance_threshold_change_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if auth.get(forbidden) is not False:
            raise RuntimeError(
                f"Diagnostic review unexpectedly authorises {forbidden}."
            )

    print("Waypoint classifier human diagnostic review freeze v1")
    print("=" * 63)
    print(f"Failure-analysis SHA256:    {sha256(ANALYSIS_PATH)}")
    print(f"Score-result SHA256:        {sha256(SCORE_RESULT_PATH)}")
    print()
    print("Frozen diagnosis")
    print("-" * 63)
    print("Primary:                    CONTEXT-GATE OVERREACH")
    print("Evidence:                   5 over-abstentions")
    print("Secondary:                  FOREIGN-ISSUING CLASS OVERREACH")
    print("Evidence:                   1 wrong-class case")
    print("Robustness:                 2 SCHEMA-VALIDATION REJECTIONS")
    print("Rejected raw payload known: NO")
    print()
    print("Safety observation")
    print("-" * 63)
    print("Gold-unresolved failures:   0/6")
    print("Unresolved recall:          6/6")
    print()
    print("Design v3:                  AUTHORISED")
    print("Implementation:             NOT AUTHORISED")
    print("Prompt changes:             NOT AUTHORISED")
    print("Model run:                  NOT AUTHORISED")
    print("Same-pack untouched rerun:  NOT AUTHORISED")
    print("New acceptance pack:        NOT YET AUTHORISED")
    print("Candidate v7:               NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print("Fresh external-v3:          NOT AUTHORISED")
    print()
    print("Next task:                  CLASSIFIER DESIGN V3")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Human-review SHA256:        {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Human diagnostic review freeze: PASS")


if __name__ == "__main__":
    main()
