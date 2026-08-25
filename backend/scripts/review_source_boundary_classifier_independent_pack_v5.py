"""Human-review independent source-boundary classifier contract pack v5.

REVIEW/FREEZE ONLY.
- No model calls.
- No pack mutation.
- No classifier implementation.
- No model prediction.

This review verifies the metadata-only correction from v4, confirms all
declared contrast groups span the intended source-class boundaries, and
authorises acceptance-threshold design/freeze only.

Run from backend/:
    uv run python -m py_compile scripts/review_source_boundary_classifier_independent_pack_v5.py
    uv run python -m scripts.review_source_boundary_classifier_independent_pack_v5

Output:
    tests/source_boundary_classifier_independent_pack_human_review_v5.json
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

DESIGN_V3_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v3.json"
)

PACK_V4_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_contract_test_pack_v4.json"
)

REVIEW_V4_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_pack_human_review_v4.json"
)

PACK_V5_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_contract_test_pack_v5.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_pack_human_review_v5.json"
)

EXPECTED_DESIGN_V3_SHA256 = (
    "0EFBA11ECA5EE07A41BBB841817B93CB4"
    "69BFA5B48BF42DF268B6A8F3257356B"
)

EXPECTED_PACK_V4_SHA256 = (
    "BC9515B3394E880C4FBEBD7C13F9A4FC"
    "43F7823EB484D30B3E008C3632C0304E"
)

EXPECTED_REVIEW_V4_SHA256 = (
    "1DA2FAD8EA80985E6FD9615F256F34EF"
    "227F4E2991D2159C24EB431203C95B17"
)

EXPECTED_PACK_V5_SHA256 = (
    "1B3CEA56504E3932C7DCA342DF99DC225"
    "23A4676B1C22714B9A122DDD566E67B"
)

EXPECTED_CLASS_COUNTS = {
    "operational_manual_instruction": 4,
    "manual_instruction_transition": 3,
    "legislation_or_regulation": 3,
    "inz_live_service_information": 4,
    "current_fee_or_charge_information": 3,
    "inz_non_manual_procedure_or_interpretation": 3,
    "foreign_issuing_authority_procedure": 3,
    "external_agency_assessment_or_service": 3,
    "external_entitlement_or_service_regime": 3,
    "professional_or_assessor_guidance": 3,
    "other_official_external_authority": 2,
    "unresolved": 6,
}

EXPECTED_CONTRAST_CLASSES = {
    "instruction_rule_vs_live_status": {
        "operational_manual_instruction",
        "inz_live_service_information",
    },
    "instruction_exception_vs_nonmanual_guidance": {
        "operational_manual_instruction",
        "inz_non_manual_procedure_or_interpretation",
    },
    "instruction_rule_vs_statutory_authority": {
        "operational_manual_instruction",
        "legislation_or_regulation",
    },
    "certified_transition_vs_unverified_change": {
        "manual_instruction_transition",
        "unresolved",
    },
    "legal_charge_basis_vs_current_charge": {
        "legislation_or_regulation",
        "current_fee_or_charge_information",
    },
    "current_charge_vs_live_nonprice_status": {
        "current_fee_or_charge_information",
        "inz_live_service_information",
    },
    "live_service_vs_nonmanual_publication": {
        "inz_live_service_information",
        "inz_non_manual_procedure_or_interpretation",
    },
    "foreign_issuing_vs_general_foreign_operation": {
        "foreign_issuing_authority_procedure",
        "other_official_external_authority",
    },
    "foreign_issuing_vs_external_agency_service": {
        "foreign_issuing_authority_procedure",
        "external_agency_assessment_or_service",
    },
    "agency_assessment_vs_professional_assessment": {
        "external_agency_assessment_or_service",
        "professional_or_assessor_guidance",
    },
    "immigration_status_rule_vs_external_entitlement": {
        "operational_manual_instruction",
        "external_entitlement_or_service_regime",
    },
    "generic_official_with_vs_without_context": {
        "other_official_external_authority",
        "unresolved",
    },
}

AUTHORISED_V4_TO_V5_CHANGES = {
    "iv4_002": {
        "from": None,
        "to": "immigration_status_rule_vs_external_entitlement",
    },
    "iv4_029": {
        "from": "immigration_status_rule_vs_external_entitlement",
        "to": None,
    },
    "iv4_034": {
        "from": None,
        "to": "generic_official_with_vs_without_context",
    },
    "iv4_040": {
        "from": "generic_official_with_vs_without_context",
        "to": None,
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_sha(
    path: Path,
    expected: str,
    label: str,
) -> None:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")

    actual = sha256(path)

    if actual != expected:
        raise SystemExit(
            f"{label} SHA mismatch.\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Refusing to approve independent pack v5."
        )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{path.name}: root must be a JSON object."
        )

    return payload


def index_tests(
    tests: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}

    for item in tests:
        if not isinstance(item, dict):
            raise RuntimeError("Every test must be an object.")

        case_id = item.get("case_id")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Invalid case_id.")

        if case_id in indexed:
            raise RuntimeError(f"Duplicate case_id: {case_id}")

        indexed[case_id] = item

    return indexed


def without_contrast(
    item: dict[str, Any],
) -> dict[str, Any]:
    result = copy.deepcopy(item)
    result.pop("contrast_group", None)
    return result


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Pack-v5 human review already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_sha(
        DESIGN_V3_PATH,
        EXPECTED_DESIGN_V3_SHA256,
        "Frozen classifier design v3",
    )
    require_sha(
        PACK_V4_PATH,
        EXPECTED_PACK_V4_SHA256,
        "Frozen independent pack v4",
    )
    require_sha(
        REVIEW_V4_PATH,
        EXPECTED_REVIEW_V4_SHA256,
        "Frozen pack-v4 human review",
    )
    require_sha(
        PACK_V5_PATH,
        EXPECTED_PACK_V5_SHA256,
        "Frozen independent pack v5",
    )

    design = load_json(DESIGN_V3_PATH)
    pack_v4 = load_json(PACK_V4_PATH)
    review_v4 = load_json(REVIEW_V4_PATH)
    pack_v5 = load_json(PACK_V5_PATH)

    if design.get("status") != (
        "FROZEN_REVISED_DESIGN_READY_FOR_INDEPENDENT_PACK_CONSTRUCTION"
    ):
        raise RuntimeError("Unexpected design-v3 status.")

    if review_v4.get("status") != (
        "REVISE_CONTRAST_METADATA_ONLY"
    ):
        raise RuntimeError("Unexpected pack-v4 review status.")

    if pack_v5.get("schema") != (
        "waypoint-source-boundary-classifier-independent-contract-test-pack-v5"
    ):
        raise RuntimeError("Unexpected pack-v5 schema.")

    if pack_v5.get("status") != (
        "FROZEN_METADATA_CORRECTED_INDEPENDENT_PACK_READY_FOR_HUMAN_REVIEW"
    ):
        raise RuntimeError("Unexpected pack-v5 status.")

    tests_v4 = pack_v4.get("tests")
    tests_v5 = pack_v5.get("tests")

    if (
        not isinstance(tests_v4, list)
        or not isinstance(tests_v5, list)
        or len(tests_v4) != 40
        or len(tests_v5) != 40
    ):
        raise RuntimeError(
            "Both independent packs must contain exactly 40 tests."
        )

    indexed_v4 = index_tests(tests_v4)
    indexed_v5 = index_tests(tests_v5)

    if set(indexed_v4) != set(indexed_v5):
        raise RuntimeError(
            "Pack-v5 case-ID set differs from pack v4."
        )

    changed_cases: list[str] = []

    for case_id in sorted(indexed_v4):
        old_item = indexed_v4[case_id]
        new_item = indexed_v5[case_id]

        if without_contrast(old_item) != without_contrast(new_item):
            raise RuntimeError(
                f"{case_id}: substantive case content changed from v4."
            )

        old_group = old_item.get("contrast_group")
        new_group = new_item.get("contrast_group")

        if old_group != new_group:
            changed_cases.append(case_id)

            expected_change = AUTHORIZED = (
                AUTHORISED_V4_TO_V5_CHANGES.get(case_id)
            )

            if expected_change is None:
                raise RuntimeError(
                    f"{case_id}: unauthorised metadata change."
                )

            if (
                old_group != expected_change["from"]
                or new_group != expected_change["to"]
            ):
                raise RuntimeError(
                    f"{case_id}: metadata correction differs from v4 review."
                )

    if changed_cases != sorted(
        AUTHORISED_V4_TO_V5_CHANGES
    ):
        raise RuntimeError(
            "V4-to-v5 changed-case set is not exactly the authorised four."
        )

    class_counts = Counter(
        item["expected"]["source_class"]
        for item in tests_v5
    )

    if dict(class_counts) != EXPECTED_CLASS_COUNTS:
        raise RuntimeError(
            "Pack-v5 source-class distribution changed."
        )

    resolution_counts = Counter(
        item["expected"]["resolution_status"]
        for item in tests_v5
    )

    if resolution_counts != Counter(
        {"resolved": 34, "unresolved": 6}
    ):
        raise RuntimeError(
            "Pack-v5 resolved/unresolved distribution changed."
        )

    groups: dict[str, list[str]] = defaultdict(list)

    for item in tests_v5:
        group = item.get("contrast_group")

        if isinstance(group, str) and group:
            groups[group].append(item["case_id"])

    if set(groups) != set(EXPECTED_CONTRAST_CLASSES):
        raise RuntimeError(
            "Pack-v5 contrast-group set changed."
        )

    contrast_review: dict[str, dict[str, Any]] = {}

    for group in sorted(groups):
        members = groups[group]

        if len(members) < 2:
            raise RuntimeError(
                f"{group}: fewer than two members."
            )

        actual_classes = {
            indexed_v5[case_id]["expected"]["source_class"]
            for case_id in members
        }

        expected_classes = EXPECTED_CONTRAST_CLASSES[group]

        if actual_classes != expected_classes:
            raise RuntimeError(
                f"{group}: semantic contrast differs from reviewed design.\n"
                f"Expected: {sorted(expected_classes)}\n"
                f"Actual:   {sorted(actual_classes)}"
            )

        contrast_review[group] = {
            "members": members,
            "expected_source_classes": sorted(
                actual_classes
            ),
            "decision": "APPROVE",
        }

    scoring = pack_v5.get("scoring_contract")

    if not isinstance(scoring, dict):
        raise RuntimeError(
            "Pack-v5 scoring contract is missing."
        )

    required_scoring = {
        "primary_scored_field": "source_class",
        "four_field_exact_match_after_derivation": True,
        "basis_scored": False,
        "prediction_error_is_incorrect": True,
        "malformed_output_is_incorrect": True,
    }

    for key, expected in required_scoring.items():
        if scoring.get(key) != expected:
            raise RuntimeError(
                f"Pack-v5 scoring contract changed for {key!r}."
            )

    construction = pack_v5.get("construction")

    if not isinstance(construction, dict):
        raise RuntimeError(
            "Pack-v5 construction metadata is missing."
        )

    required_construction = {
        "test_count": 40,
        "resolved_count": 34,
        "unresolved_count": 6,
        "source_class_count": 12,
        "contrast_group_count": 12,
        "reads_observed_contract_pack": False,
        "reads_observed_predictions": False,
        "reads_observed_score": False,
        "reads_failure_analysis": False,
        "uses_observed_case_ids": False,
        "copies_observed_case_wording": False,
        "benchmark_specific_logic": False,
        "question_specific_logic": False,
        "revision_type": (
            "metadata_only_contrast_group_correction"
        ),
        "changed_case_count": 4,
        "changed_field": "contrast_group",
        "case_content_changed": False,
        "expected_outputs_changed": False,
        "basis_changed": False,
        "trusted_source_context_changed": False,
        "case_ids_changed": False,
        "source_class_distribution_changed": False,
        "resolved_unresolved_distribution_changed": False,
        "model_calls": 0,
    }

    for key, expected in required_construction.items():
        if construction.get(key) != expected:
            raise RuntimeError(
                f"Pack-v5 construction metadata changed for {key!r}."
            )

    review = {
        "schema": (
            "waypoint-source-boundary-classifier-independent-pack-human-review-v5"
        ),
        "status": (
            "APPROVED_INDEPENDENT_PACK_READY_FOR_ACCEPTANCE_THRESHOLD_FREEZE"
        ),
        "reviewed_on": str(date.today()),
        "source_artifacts": {
            "classifier_design_v3_sha256": (
                EXPECTED_DESIGN_V3_SHA256
            ),
            "independent_contract_pack_v4_sha256": (
                EXPECTED_PACK_V4_SHA256
            ),
            "independent_pack_human_review_v4_sha256": (
                EXPECTED_REVIEW_V4_SHA256
            ),
            "independent_contract_pack_v5_sha256": (
                EXPECTED_PACK_V5_SHA256
            ),
        },
        "metadata_revision_review": {
            "decision": "APPROVE",
            "changed_cases": changed_cases,
            "changed_field": "contrast_group",
            "substantive_case_content_preserved": True,
            "expected_outputs_preserved": True,
            "trusted_source_context_preserved": True,
            "basis_preserved": True,
            "class_distribution_preserved": True,
            "resolution_distribution_preserved": True,
        },
        "semantic_review": {
            "decision": "APPROVE",
            "cases_reviewed": 40,
            "source_classes_reviewed": 12,
            "contrast_groups_reviewed": 12,
            "remaining_gold_label_blockers": [],
            "remaining_proposition_blockers": [],
            "remaining_trusted_context_blockers": [],
            "contrast_group_review": contrast_review,
        },
        "independence_review": {
            "decision": "APPROVE",
            "observed_pack_read_by_construction": False,
            "observed_predictions_read_by_construction": False,
            "observed_score_read_by_construction": False,
            "failure_analysis_read_by_construction": False,
            "observed_case_id_family_used": False,
            "observed_case_wording_copied": False,
            "benchmark_specific_logic": False,
        },
        "coverage_review": {
            "decision": "APPROVE",
            "test_count": 40,
            "resolved_count": 34,
            "unresolved_count": 6,
            "source_class_count": 12,
            "source_class_counts": EXPECTED_CLASS_COUNTS,
            "contrast_group_count": 12,
            "all_contrasts_span_intended_classes": True,
        },
        "scoring_contract_review": {
            "decision": "APPROVE",
            "primary_scored_field": "source_class",
            "dependent_fields_derived": True,
            "basis_unscored": True,
            "errors_incorrect": True,
            "malformed_outputs_incorrect": True,
            "contrast_group_full_consistency_required": True,
        },
        "review_decision": {
            "independent_pack_v5": "APPROVE",
            "acceptance_threshold_freeze_authorised": True,
            "pack_revision_required": False,
            "classifier_implementation_authorised": False,
            "classifier_prompt_change_authorised": False,
            "classifier_model_prediction_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "threshold_freeze_constraints": {
            "must_be_frozen_before_any_v5_prediction": True,
            "must_not_be_weaker_than_prior_percentage_and_safety_floors": True,
            "must_include_source_class_accuracy": True,
            "must_include_source_class_macro_recall": True,
            "must_include_unresolved_recall": True,
            "must_include_resolved_recall": True,
            "must_include_contrast_group_full_consistency": True,
            "must_include_malformed_or_error_zero_tolerance": True,
            "must_include_per_resolved_class_recall_floor": True,
            "manual_override": False,
            "automatic_retry": False,
        },
        "authorisations": {
            "acceptance_threshold_freeze_authorised": True,
            "classifier_implementation_v2_authorised": False,
            "classifier_prompt_change_authorised": False,
            "classifier_model_run_authorised": False,
            "same_pack_prediction_before_threshold_freeze_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": (
                "source_boundary_classifier_acceptance_thresholds_v2"
            ),
            "authorised": True,
            "model_calls": 0,
            "purpose": (
                "Freeze acceptance thresholds for the independent 40-case "
                "pack v5 before any classifier implementation or prediction."
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
        "APPROVED_INDEPENDENT_PACK_READY_FOR_ACCEPTANCE_THRESHOLD_FREEZE"
    ):
        raise RuntimeError(
            "Saved pack-v5 review status changed."
        )

    auth = saved.get("authorisations", {})

    if auth.get(
        "acceptance_threshold_freeze_authorised"
    ) is not True:
        raise RuntimeError(
            "Acceptance threshold freeze was not authorised."
        )

    for forbidden in (
        "classifier_implementation_v2_authorised",
        "classifier_prompt_change_authorised",
        "classifier_model_run_authorised",
        "same_pack_prediction_before_threshold_freeze_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if auth.get(forbidden) is not False:
            raise RuntimeError(
                f"Pack-v5 review unexpectedly authorises {forbidden}."
            )

    print("Waypoint independent contract pack v5 human review")
    print("=" * 64)
    print(f"Design-v3 SHA256:           {sha256(DESIGN_V3_PATH)}")
    print(f"Pack-v5 SHA256:             {sha256(PACK_V5_PATH)}")
    print()
    print("Metadata correction review")
    print("-" * 64)
    print("Changed cases:              4 PASS")
    print("Changed field only:         contrast_group PASS")
    print("Substantive content:        IDENTICAL")
    print("Expected outputs:           IDENTICAL")
    print("Trusted context:            IDENTICAL")
    print("Class distribution:         IDENTICAL")
    print()
    print("Semantic review")
    print("-" * 64)
    print("Cases reviewed:             40/40")
    print("Source classes reviewed:    12/12")
    print("Contrast groups reviewed:   12/12")
    print("Contrast semantics:         PASS")
    print("Gold-label blockers:        NONE")
    print("Proposition blockers:       NONE")
    print("Context blockers:           NONE")
    print()
    print("Independence review:        PASS")
    print("Scoring contract:           PASS")
    print()
    print("Pack v5:                    APPROVED")
    print("Threshold freeze:           AUTHORISED")
    print("Implementation:             NOT AUTHORISED")
    print("Prompt change:              NOT AUTHORISED")
    print("Model prediction:           NOT AUTHORISED")
    print("Candidate v7:               NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print("Fresh external-v3:          NOT AUTHORISED")
    print()
    print("Next task:                  ACCEPTANCE THRESHOLDS V2")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Human-review SHA256:        {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Independent pack v5 human review: PASS")


if __name__ == "__main__":
    main()
