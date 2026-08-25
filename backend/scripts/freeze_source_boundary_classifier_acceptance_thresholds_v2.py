"""Freeze Waypoint source-boundary classifier acceptance thresholds v2.

THRESHOLD FREEZE ONLY.
- No model calls.
- No classifier implementation.
- No predictions.
- No scoring.
- No production changes.

The thresholds are frozen against the approved independent 40-case pack v5
before any design-v3 classifier implementation or prediction.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_acceptance_thresholds_v2.py
    uv run python -m scripts.freeze_source_boundary_classifier_acceptance_thresholds_v2

Output:
    tests/source_boundary_classifier_acceptance_thresholds_v2.json
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

RUNTIME_PATH = (
    BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
)

DESIGN_V3_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v3.json"
)

PACK_V5_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_contract_test_pack_v5.json"
)

HUMAN_REVIEW_V5_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_pack_human_review_v5.json"
)

PRIOR_THRESHOLDS_V1_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_acceptance_thresholds_v1.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_acceptance_thresholds_v2.json"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_DESIGN_V3_SHA256 = (
    "0EFBA11ECA5EE07A41BBB841817B93CB4"
    "69BFA5B48BF42DF268B6A8F3257356B"
)

EXPECTED_PACK_V5_SHA256 = (
    "1B3CEA56504E3932C7DCA342DF99DC225"
    "23A4676B1C22714B9A122DDD566E67B"
)

EXPECTED_HUMAN_REVIEW_V5_SHA256 = (
    "1F95EAD2A0B606F37621077B4F30E5A1"
    "1D7B78344208762BE68EA9D276261C8C"
)

EXPECTED_PRIOR_THRESHOLDS_V1_SHA256 = (
    "5E8AFBFFEE5880DEBF4FA6B0A6514E8C"
    "6702F5D9E74D620BA4C1575F49CAC03C"
)

# Frozen prior acceptance floors from thresholds v1.
# These are evaluation-policy constants, not benchmark-answer mappings.
PRIOR_PERCENTAGE_FLOORS = {
    "four_field_exact_match": 88.2,
    "resolution_status_accuracy": 94.1,
    "source_domain_accuracy": 94.1,
    "source_class_accuracy": 88.2,
    "source_class_macro_recall": 85.0,
    "unresolved_recall": 83.3,
    "resolved_recall": 89.3,
    "contrast_consistency": 81.8,
    "per_resolved_class_recall_floor": 50.0,
}

SOURCE_CLASS_COUNTS = {
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

TOTAL_CASES = 40
RESOLVED_CASES = 34
UNRESOLVED_CASES = 6
CONTRAST_GROUPS = 12


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
            "Refusing to freeze acceptance thresholds v2."
        )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{path.name}: root must be a JSON object."
        )

    return payload


def pct(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100.0, 1)


def minimum_count(
    denominator: int,
    percentage_floor: float,
) -> int:
    return math.ceil(
        denominator * (percentage_floor / 100.0)
        - 1e-12
    )


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Acceptance thresholds v2 already exist: {OUTPUT_PATH}\n"
            "Refusing to overwrite them."
        )

    require_sha(
        RUNTIME_PATH,
        EXPECTED_RUNTIME_SHA256,
        "Frozen production candidate-v2 runtime",
    )
    require_sha(
        DESIGN_V3_PATH,
        EXPECTED_DESIGN_V3_SHA256,
        "Frozen classifier design v3",
    )
    require_sha(
        PACK_V5_PATH,
        EXPECTED_PACK_V5_SHA256,
        "Approved independent contract pack v5",
    )
    require_sha(
        HUMAN_REVIEW_V5_PATH,
        EXPECTED_HUMAN_REVIEW_V5_SHA256,
        "Approved independent pack-v5 human review",
    )
    require_sha(
        PRIOR_THRESHOLDS_V1_PATH,
        EXPECTED_PRIOR_THRESHOLDS_V1_SHA256,
        "Frozen prior acceptance thresholds v1",
    )

    design = load_json(DESIGN_V3_PATH)
    pack = load_json(PACK_V5_PATH)
    review = load_json(HUMAN_REVIEW_V5_PATH)

    if design.get("schema") != (
        "waypoint-source-boundary-classifier-design-v3"
    ):
        raise RuntimeError("Unexpected design-v3 schema.")

    if pack.get("schema") != (
        "waypoint-source-boundary-classifier-independent-contract-test-pack-v5"
    ):
        raise RuntimeError("Unexpected pack-v5 schema.")

    if review.get("schema") != (
        "waypoint-source-boundary-classifier-independent-pack-human-review-v5"
    ):
        raise RuntimeError("Unexpected pack-v5 human-review schema.")

    if review.get("status") != (
        "APPROVED_INDEPENDENT_PACK_READY_FOR_ACCEPTANCE_THRESHOLD_FREEZE"
    ):
        raise RuntimeError(
            "Pack-v5 human review does not approve threshold freeze."
        )

    if review.get(
        "authorisations",
        {},
    ).get(
        "acceptance_threshold_freeze_authorised"
    ) is not True:
        raise RuntimeError(
            "Acceptance threshold freeze is not authorised."
        )

    tests = pack.get("tests")

    if not isinstance(tests, list) or len(tests) != TOTAL_CASES:
        raise RuntimeError(
            "Approved independent pack must contain exactly 40 cases."
        )

    actual_class_counts: dict[str, int] = {}

    for item in tests:
        source_class = (
            item.get("expected", {})
            .get("source_class")
        )

        if not isinstance(source_class, str):
            raise RuntimeError(
                "Pack-v5 test is missing expected source_class."
            )

        actual_class_counts[source_class] = (
            actual_class_counts.get(source_class, 0) + 1
        )

    if actual_class_counts != SOURCE_CLASS_COUNTS:
        raise RuntimeError(
            "Pack-v5 source-class distribution changed."
        )

    resolved_count = sum(
        1
        for item in tests
        if item.get("expected", {}).get(
            "resolution_status"
        ) == "resolved"
    )
    unresolved_count = sum(
        1
        for item in tests
        if item.get("expected", {}).get(
            "resolution_status"
        ) == "unresolved"
    )

    if (
        resolved_count != RESOLVED_CASES
        or unresolved_count != UNRESOLVED_CASES
    ):
        raise RuntimeError(
            "Pack-v5 resolved/unresolved distribution changed."
        )

    groups = {
        item["contrast_group"]
        for item in tests
        if isinstance(item.get("contrast_group"), str)
        and item["contrast_group"]
    }

    if len(groups) != CONTRAST_GROUPS:
        raise RuntimeError(
            "Pack-v5 contrast-group count changed."
        )

    # Integer thresholds chosen so that every percentage is equal to or
    # stronger than the corresponding frozen v1 percentage floor.
    thresholds = {
        "four_field_exact_match": {
            "minimum_correct": 36,
            "denominator": TOTAL_CASES,
            "minimum_percent": pct(36, TOTAL_CASES),
        },
        "resolution_status_accuracy": {
            "minimum_correct": 38,
            "denominator": TOTAL_CASES,
            "minimum_percent": pct(38, TOTAL_CASES),
        },
        "source_domain_accuracy": {
            "minimum_correct": 38,
            "denominator": TOTAL_CASES,
            "minimum_percent": pct(38, TOTAL_CASES),
        },
        "source_class_accuracy": {
            "minimum_correct": 36,
            "denominator": TOTAL_CASES,
            "minimum_percent": pct(36, TOTAL_CASES),
        },
        "source_class_macro_recall": {
            "minimum_percent": 85.0,
            "class_count": 12,
        },
        "unresolved_recall": {
            "minimum_correct": 6,
            "denominator": UNRESOLVED_CASES,
            "minimum_percent": pct(6, UNRESOLVED_CASES),
        },
        "resolved_recall": {
            "minimum_correct": 31,
            "denominator": RESOLVED_CASES,
            "minimum_percent": pct(31, RESOLVED_CASES),
        },
        "contrast_consistency": {
            "minimum_groups_correct": 10,
            "denominator": CONTRAST_GROUPS,
            "minimum_percent": pct(10, CONTRAST_GROUPS),
        },
        "malformed_or_error_count": {
            "maximum_count": 0,
            "denominator": TOTAL_CASES,
        },
    }

    per_resolved_class = {}

    for source_class, count in SOURCE_CLASS_COUNTS.items():
        if source_class == "unresolved":
            continue

        minimum = minimum_count(
            count,
            PRIOR_PERCENTAGE_FLOORS[
                "per_resolved_class_recall_floor"
            ],
        )

        per_resolved_class[source_class] = {
            "minimum_correct": minimum,
            "denominator": count,
            "minimum_percent": pct(minimum, count),
        }

    # Prove v2 floors are not weaker than frozen v1 percentages.
    comparisons = {
        "four_field_exact_match": (
            thresholds["four_field_exact_match"][
                "minimum_percent"
            ],
            PRIOR_PERCENTAGE_FLOORS[
                "four_field_exact_match"
            ],
        ),
        "resolution_status_accuracy": (
            thresholds["resolution_status_accuracy"][
                "minimum_percent"
            ],
            PRIOR_PERCENTAGE_FLOORS[
                "resolution_status_accuracy"
            ],
        ),
        "source_domain_accuracy": (
            thresholds["source_domain_accuracy"][
                "minimum_percent"
            ],
            PRIOR_PERCENTAGE_FLOORS[
                "source_domain_accuracy"
            ],
        ),
        "source_class_accuracy": (
            thresholds["source_class_accuracy"][
                "minimum_percent"
            ],
            PRIOR_PERCENTAGE_FLOORS[
                "source_class_accuracy"
            ],
        ),
        "source_class_macro_recall": (
            thresholds["source_class_macro_recall"][
                "minimum_percent"
            ],
            PRIOR_PERCENTAGE_FLOORS[
                "source_class_macro_recall"
            ],
        ),
        "unresolved_recall": (
            thresholds["unresolved_recall"][
                "minimum_percent"
            ],
            PRIOR_PERCENTAGE_FLOORS[
                "unresolved_recall"
            ],
        ),
        "resolved_recall": (
            thresholds["resolved_recall"][
                "minimum_percent"
            ],
            PRIOR_PERCENTAGE_FLOORS[
                "resolved_recall"
            ],
        ),
        "contrast_consistency": (
            thresholds["contrast_consistency"][
                "minimum_percent"
            ],
            PRIOR_PERCENTAGE_FLOORS[
                "contrast_consistency"
            ],
        ),
    }

    for metric, (
        new_floor,
        old_floor,
    ) in comparisons.items():
        if new_floor + 1e-9 < old_floor:
            raise RuntimeError(
                f"{metric}: v2 floor {new_floor}% is weaker than "
                f"v1 floor {old_floor}%."
            )

    for source_class, gate in per_resolved_class.items():
        if (
            gate["minimum_percent"] + 1e-9
            < PRIOR_PERCENTAGE_FLOORS[
                "per_resolved_class_recall_floor"
            ]
        ):
            raise RuntimeError(
                f"{source_class}: per-class floor became weaker."
            )

    # Explicit methodological reason for the stricter unresolved gate.
    if thresholds["unresolved_recall"][
        "minimum_correct"
    ] != UNRESOLVED_CASES:
        raise RuntimeError(
            "Design-v3 safety requirement expects 6/6 unresolved recall."
        )

    artifact = {
        "schema": (
            "waypoint-source-boundary-classifier-acceptance-thresholds-v2"
        ),
        "status": (
            "FROZEN_BEFORE_CLASSIFIER_IMPLEMENTATION_AND_PREDICTION"
        ),
        "frozen_on": str(date.today()),
        "source_artifacts": {
            "production_runtime_sha256": (
                EXPECTED_RUNTIME_SHA256
            ),
            "classifier_design_v3_sha256": (
                EXPECTED_DESIGN_V3_SHA256
            ),
            "independent_contract_pack_v5_sha256": (
                EXPECTED_PACK_V5_SHA256
            ),
            "independent_pack_human_review_v5_sha256": (
                EXPECTED_HUMAN_REVIEW_V5_SHA256
            ),
            "prior_acceptance_thresholds_v1_sha256": (
                EXPECTED_PRIOR_THRESHOLDS_V1_SHA256
            ),
        },
        "evaluation_population": {
            "total_cases": TOTAL_CASES,
            "resolved_cases": RESOLVED_CASES,
            "unresolved_cases": UNRESOLVED_CASES,
            "source_classes": 12,
            "contrast_groups": CONTRAST_GROUPS,
            "source_class_counts": SOURCE_CLASS_COUNTS,
        },
        "prior_floor_policy": {
            "source": (
                "Frozen source-boundary classifier acceptance thresholds v1"
            ),
            "percentage_floors": PRIOR_PERCENTAGE_FLOORS,
            "rule": (
                "No v2 percentage or safety floor may be weaker than its "
                "corresponding frozen v1 floor."
            ),
            "comparison_result": "PASS",
        },
        "hard_gates": thresholds,
        "per_resolved_source_class_recall_gates": (
            per_resolved_class
        ),
        "all_gates_required": True,
        "safety_tightening": {
            "metric": "unresolved_recall",
            "prior_floor": "5/6 = 83.3%",
            "v2_floor": "6/6 = 100.0%",
            "reason": (
                "Frozen design v3 explicitly requires conservative unresolved "
                "behaviour to be preserved, and the diagnostic evidence showed "
                "6/6 gold-unresolved cases correctly unresolved."
            ),
        },
        "metric_semantics": {
            "source_class_accuracy": (
                "Exact predicted source_class against gold source_class."
            ),
            "four_field_exact_match": (
                "After deterministic derivation from predicted source_class, "
                "resolution_status, source_domain, source_class, and "
                "responsible_authority_type must all match gold."
            ),
            "resolution_status_accuracy": (
                "Derived resolution_status equals gold."
            ),
            "source_domain_accuracy": (
                "Derived source_domain equals gold."
            ),
            "source_class_macro_recall": (
                "Unweighted mean of recall across all 12 source classes."
            ),
            "unresolved_recall": (
                "Gold-unresolved cases predicted as source_class unresolved."
            ),
            "resolved_recall": (
                "Gold-resolved cases with exact four-field result after "
                "deterministic derivation."
            ),
            "contrast_consistency": (
                "A contrast group is correct only when every member has exact "
                "four-field correctness after deterministic derivation."
            ),
            "malformed_or_error_count": (
                "Any malformed model output, validation failure, or execution "
                "error counts as an error. Zero are permitted."
            ),
            "per_resolved_source_class_recall": (
                "Each resolved source class must independently meet its frozen "
                "minimum correct count."
            ),
        },
        "execution_policy": {
            "one_model_call_per_case": True,
            "automatic_retry": False,
            "repair_call": False,
            "fallback_model": False,
            "manual_override": False,
            "threshold_change_after_prediction": False,
            "same_prediction_set_rescore_after_threshold_change": False,
            "prediction_artifact_must_be_frozen_before_scoring": True,
        },
        "acceptance_decision": {
            "rule": (
                "PASS only if every hard gate and every resolved-class recall "
                "gate passes."
            ),
            "partial_pass": False,
            "manual_override": False,
        },
        "authorisations": {
            "acceptance_thresholds_v2_frozen": True,
            "experimental_classifier_implementation_v2_construction_authorised": True,
            "experimental_prompt_construction_authorised": True,
            "classifier_model_run_authorised": False,
            "blind_runner_v2_construction_authorised": False,
            "scorer_v2_construction_authorised": False,
            "prediction_authorisation_freeze_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "external_source_retrieval_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": "source_boundary_classifier_implementation_v2",
            "authorised": True,
            "model_calls": 0,
            "purpose": (
                "Implement the frozen design-v3 source-boundary classifier as "
                "an isolated experimental module. The implementation may "
                "construct its zero-shot prompt and strict output schema, but "
                "must not execute the model."
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

    saved = load_json(OUTPUT_PATH)

    if saved.get("status") != (
        "FROZEN_BEFORE_CLASSIFIER_IMPLEMENTATION_AND_PREDICTION"
    ):
        raise RuntimeError(
            "Saved acceptance-threshold status changed."
        )

    if saved.get("hard_gates") != thresholds:
        raise RuntimeError(
            "Saved hard gates changed."
        )

    if saved.get(
        "per_resolved_source_class_recall_gates"
    ) != per_resolved_class:
        raise RuntimeError(
            "Saved per-class gates changed."
        )

    auth = saved.get("authorisations", {})

    if auth.get(
        "experimental_classifier_implementation_v2_construction_authorised"
    ) is not True:
        raise RuntimeError(
            "Experimental classifier implementation was not authorised."
        )

    if auth.get(
        "experimental_prompt_construction_authorised"
    ) is not True:
        raise RuntimeError(
            "Experimental prompt construction was not authorised."
        )

    for forbidden in (
        "classifier_model_run_authorised",
        "blind_runner_v2_construction_authorised",
        "scorer_v2_construction_authorised",
        "prediction_authorisation_freeze_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "external_source_retrieval_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if auth.get(forbidden) is not False:
            raise RuntimeError(
                f"Threshold freeze unexpectedly authorises {forbidden}."
            )

    print("Waypoint source-boundary classifier acceptance thresholds v2")
    print("=" * 67)
    print(f"Design-v3 SHA256:           {sha256(DESIGN_V3_PATH)}")
    print(f"Pack-v5 SHA256:             {sha256(PACK_V5_PATH)}")
    print(
        f"Pack-v5 review SHA256:      "
        f"{sha256(HUMAN_REVIEW_V5_PATH)}"
    )
    print(
        f"Prior thresholds SHA256:    "
        f"{sha256(PRIOR_THRESHOLDS_V1_PATH)}"
    )
    print()
    print("Frozen hard gates")
    print("-" * 67)
    print("Four-field exact:           >= 36/40 (90.0%)")
    print("Resolution accuracy:        >= 38/40 (95.0%)")
    print("Source-domain accuracy:     >= 38/40 (95.0%)")
    print("Source-class accuracy:      >= 36/40 (90.0%)")
    print("Source-class macro recall:  >= 85.0%")
    print("Unresolved recall:          =  6/6  (100.0%)")
    print("Resolved recall:            >= 31/34 (91.2%)")
    print("Contrast consistency:       >= 10/12 (83.3%)")
    print("Malformed/error count:      =  0/40")
    print("Per resolved-class floor:   >= 50.0% by integer count")
    print()
    print("Prior percentage floors:    NOT WEAKENED")
    print("Unresolved safety floor:    TIGHTENED")
    print("All gates required:         YES")
    print("Automatic retry:            NO")
    print("Repair call:                NO")
    print("Manual override:            NO")
    print()
    print("Thresholds v2:              FROZEN")
    print("Classifier implementation:  AUTHORISED")
    print("Prompt construction:        AUTHORISED")
    print("Model run:                  NOT AUTHORISED")
    print("Blind runner v2:            NOT AUTHORISED")
    print("Scorer v2:                  NOT AUTHORISED")
    print("Candidate v7:               NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print("Fresh external-v3:          NOT AUTHORISED")
    print()
    print("Next task:                  CLASSIFIER IMPLEMENTATION V2")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Threshold-v2 SHA256:        {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Acceptance thresholds v2 freeze: PASS")


if __name__ == "__main__":
    main()
