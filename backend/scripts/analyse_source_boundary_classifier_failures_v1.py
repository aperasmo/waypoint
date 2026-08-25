"""Diagnose the failed first Waypoint source-boundary classifier contract run.

DIAGNOSTIC ONLY.
- No model calls.
- No threshold changes.
- No classifier changes.
- No new acceptance claim.

Run from backend/:
    uv run python -m py_compile scripts/analyse_source_boundary_classifier_failures_v1.py
    uv run python -m scripts.analyse_source_boundary_classifier_failures_v1

Output:
    tests/source_boundary_classifier_failure_analysis_v1.json
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

PACK_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_contract_test_pack_v3.json"
)
PREDICTIONS_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_predictions_v1.json"
)
SCORE_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_score_v1.json"
)
SCORE_RESULT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_score_result_v1.json"
)
OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_failure_analysis_v1.json"
)

EXPECTED_PACK_SHA256 = (
    "C820489715EA3F54138023D680D04DFBF"
    "F5575A515B936FA8C2241E2EA5B219D"
)
EXPECTED_PREDICTIONS_SHA256 = (
    "F9E753BE55B5A06FC09C002962BE82A92"
    "1097D1F94843B63D7E58123661D9DF4"
)
EXPECTED_SCORE_SHA256 = (
    "EFBA19915945F2A929ABD261653070C979"
    "FA301B1A48C1742812EC9FD3DE54EA"
)
EXPECTED_SCORE_RESULT_SHA256 = (
    "CFEEC8CAD5009FACA2FA6AAA10FC7E88D"
    "CA490DCC0AD11AA3CFF4E40334ECE17"
)

FOUR_FIELDS = (
    "resolution_status",
    "source_domain",
    "source_class",
    "responsible_authority_type",
)

EXPECTED_CASE_COUNT = 34
EXPECTED_FAILURE_COUNT = 8
EXPECTED_ERROR_COUNT = 2
EXPECTED_NON_ERROR_FAILURE_COUNT = 6


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
            f"Path:     {path}\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Refusing to run failure analysis."
        )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{path.name}: root must be a JSON object."
        )

    return payload


def index_pack(
    pack: dict[str, Any],
) -> tuple[
    list[str],
    dict[str, dict[str, Any]],
    dict[str, list[str]],
]:
    tests = pack.get("tests")

    if not isinstance(tests, list):
        raise RuntimeError("Contract pack tests must be a list.")

    if len(tests) != EXPECTED_CASE_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_CASE_COUNT} contract tests; got {len(tests)}."
        )

    ordered_ids: list[str] = []
    cases: dict[str, dict[str, Any]] = {}
    groups: dict[str, list[str]] = defaultdict(list)

    for item in tests:
        if not isinstance(item, dict):
            raise RuntimeError("Every contract test must be an object.")

        test_id = item.get("test_id")

        if not isinstance(test_id, str) or not test_id:
            raise RuntimeError("Invalid contract test_id.")

        if test_id in cases:
            raise RuntimeError(f"Duplicate contract test_id: {test_id}")

        expected = item.get("expected")

        if not isinstance(expected, dict):
            raise RuntimeError(f"{test_id}: missing expected output.")

        if set(expected) != set(FOUR_FIELDS):
            raise RuntimeError(
                f"{test_id}: expected output fields changed."
            )

        ordered_ids.append(test_id)
        cases[test_id] = item

        group = item.get("contrast_group")
        if isinstance(group, str) and group:
            groups[group].append(test_id)

    return ordered_ids, cases, dict(groups)


def index_predictions(
    predictions: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    records = predictions.get("predictions")

    if not isinstance(records, list):
        raise RuntimeError("Prediction records must be a list.")

    if len(records) != EXPECTED_CASE_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_CASE_COUNT} prediction records; "
            f"got {len(records)}."
        )

    indexed: dict[str, dict[str, Any]] = {}

    for record in records:
        if not isinstance(record, dict):
            raise RuntimeError(
                "Every prediction record must be an object."
            )

        test_id = record.get("test_id")

        if not isinstance(test_id, str) or not test_id:
            raise RuntimeError(
                "Prediction record contains invalid test_id."
            )

        if test_id in indexed:
            raise RuntimeError(
                f"Duplicate prediction record: {test_id}"
            )

        indexed[test_id] = record

    return indexed


def classify_failure_mechanism(
    gold: dict[str, str],
    predicted: dict[str, str],
) -> str:
    gold_resolved = gold["resolution_status"] == "resolved"
    pred_resolved = predicted["resolution_status"] == "resolved"

    if gold_resolved and not pred_resolved:
        return "over_abstention_resolved_to_unresolved"

    if not gold_resolved and pred_resolved:
        return "under_abstention_unresolved_to_resolved"

    field_matches = {
        field: predicted[field] == gold[field]
        for field in FOUR_FIELDS
    }

    if (
        field_matches["resolution_status"]
        and not field_matches["source_domain"]
    ):
        return "wrong_source_domain"

    if (
        field_matches["resolution_status"]
        and field_matches["source_domain"]
        and not field_matches["source_class"]
    ):
        return "wrong_source_class_within_correct_domain"

    if (
        field_matches["resolution_status"]
        and field_matches["source_domain"]
        and field_matches["source_class"]
        and not field_matches["responsible_authority_type"]
    ):
        return "authority_type_only_mismatch"

    return "multi_field_resolved_classification_mismatch"


def changed_fields(
    gold: dict[str, str],
    predicted: dict[str, str],
) -> list[str]:
    return [
        field
        for field in FOUR_FIELDS
        if predicted[field] != gold[field]
    ]


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Failure-analysis artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_sha(
        PACK_PATH,
        EXPECTED_PACK_SHA256,
        "Frozen contract pack v3",
    )
    require_sha(
        PREDICTIONS_PATH,
        EXPECTED_PREDICTIONS_SHA256,
        "Frozen first-run predictions",
    )
    require_sha(
        SCORE_PATH,
        EXPECTED_SCORE_SHA256,
        "Frozen first-run score",
    )
    require_sha(
        SCORE_RESULT_PATH,
        EXPECTED_SCORE_RESULT_SHA256,
        "Frozen acceptance-result",
    )

    pack = load_json(PACK_PATH)
    predictions = load_json(PREDICTIONS_PATH)
    score = load_json(SCORE_PATH)
    score_result = load_json(SCORE_RESULT_PATH)

    if score.get("status") != "ACCEPTANCE_FAIL":
        raise RuntimeError(
            "Failure analysis requires the frozen ACCEPTANCE_FAIL score."
        )

    if score_result.get("status") != (
        "FROZEN_FIRST_UNTOUCHED_ACCEPTANCE_FAIL"
    ):
        raise RuntimeError(
            "Failure analysis is not bound to the frozen acceptance failure."
        )

    if score_result.get(
        "authorisations",
        {},
    ).get("failure_analysis_authorised") is not True:
        raise RuntimeError(
            "Frozen score result does not authorise failure analysis."
        )

    ordered_ids, gold_cases, contrast_groups = index_pack(pack)
    prediction_records = index_predictions(predictions)

    score_case_results = score.get("case_results")

    if not isinstance(score_case_results, list):
        raise RuntimeError(
            "Score artifact is missing case_results."
        )

    score_case_map = {
        item["test_id"]: item
        for item in score_case_results
        if isinstance(item, dict) and isinstance(item.get("test_id"), str)
    }

    if set(score_case_map) != set(ordered_ids):
        raise RuntimeError(
            "Score case-result IDs differ from the contract pack."
        )

    failures: list[dict[str, Any]] = []
    error_cases: list[dict[str, Any]] = []
    non_error_failures: list[dict[str, Any]] = []
    mechanism_counts: Counter[str] = Counter()
    changed_field_counts: Counter[str] = Counter()

    gold_class_failure_counts: Counter[str] = Counter()
    predicted_class_failure_counts: Counter[str] = Counter()

    resolved_gold_failure_count = 0
    unresolved_gold_failure_count = 0

    for test_id in ordered_ids:
        score_case = score_case_map[test_id]

        if score_case.get("four_field_correct") is True:
            continue

        gold_case = gold_cases[test_id]
        gold = gold_case["expected"]
        record = prediction_records[test_id]

        proposition = gold_case.get("unsupported_proposition")
        trusted_context = gold_case.get("trusted_source_context")
        basis = gold_case.get("basis")
        contrast_group = gold_case.get("contrast_group")

        if gold["resolution_status"] == "resolved":
            resolved_gold_failure_count += 1
        else:
            unresolved_gold_failure_count += 1

        gold_class_failure_counts[gold["source_class"]] += 1

        if record.get("status") == "error":
            entry = {
                "test_id": test_id,
                "failure_type": "execution_or_validation_error",
                "unsupported_proposition": proposition,
                "trusted_source_context": trusted_context,
                "contrast_group": contrast_group,
                "gold": {
                    field: gold[field]
                    for field in FOUR_FIELDS
                },
                "gold_basis": basis,
                "error_type": record.get("error_type"),
                "error": record.get("error"),
            }

            failures.append(entry)
            error_cases.append(entry)
            mechanism_counts["execution_or_validation_error"] += 1
            continue

        predicted = record.get("prediction")

        if not isinstance(predicted, dict):
            raise RuntimeError(
                f"{test_id}: non-error record lacks prediction object."
            )

        mechanism = classify_failure_mechanism(
            gold,
            predicted,
        )

        differences = changed_fields(
            gold,
            predicted,
        )

        for field in differences:
            changed_field_counts[field] += 1

        predicted_class_failure_counts[
            predicted["source_class"]
        ] += 1

        mechanism_counts[mechanism] += 1

        entry = {
            "test_id": test_id,
            "failure_type": mechanism,
            "unsupported_proposition": proposition,
            "trusted_source_context": trusted_context,
            "contrast_group": contrast_group,
            "gold": {
                field: gold[field]
                for field in FOUR_FIELDS
            },
            "prediction": {
                field: predicted[field]
                for field in FOUR_FIELDS
            },
            "changed_fields": differences,
            "model_basis": predicted.get("basis"),
            "gold_basis": basis,
        }

        failures.append(entry)
        non_error_failures.append(entry)

    if len(failures) != EXPECTED_FAILURE_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_FAILURE_COUNT} total failures; "
            f"found {len(failures)}."
        )

    if len(error_cases) != EXPECTED_ERROR_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_ERROR_COUNT} error cases; "
            f"found {len(error_cases)}."
        )

    if len(non_error_failures) != EXPECTED_NON_ERROR_FAILURE_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_NON_ERROR_FAILURE_COUNT} non-error failures; "
            f"found {len(non_error_failures)}."
        )

    if (
        resolved_gold_failure_count
        + unresolved_gold_failure_count
        != EXPECTED_FAILURE_COUNT
    ):
        raise RuntimeError(
            "Gold-resolution failure counts do not sum to the frozen "
            f"{EXPECTED_FAILURE_COUNT} four-field failures."
        )

    failed_groups_from_score = score.get(
        "acceptance",
        {},
    ).get("failed_contrast_groups")

    if not isinstance(failed_groups_from_score, list):
        raise RuntimeError(
            "Score artifact is missing failed contrast groups."
        )

    failed_contrast_details: list[dict[str, Any]] = []

    for group_item in failed_groups_from_score:
        if not isinstance(group_item, dict):
            raise RuntimeError(
                "Malformed failed contrast-group record."
            )

        group = group_item.get("contrast_group")
        members = group_item.get("members")
        failed_members = group_item.get("failed_members")

        if (
            not isinstance(group, str)
            or not isinstance(members, list)
            or not isinstance(failed_members, list)
        ):
            raise RuntimeError(
                "Malformed failed contrast-group metadata."
            )

        member_details = []

        for member_id in members:
            gold = gold_cases[member_id]["expected"]
            pred_record = prediction_records[member_id]

            member = {
                "test_id": member_id,
                "four_field_correct": (
                    score_case_map[member_id].get(
                        "four_field_correct"
                    )
                    is True
                ),
                "gold_resolution_status": gold[
                    "resolution_status"
                ],
                "gold_source_domain": gold[
                    "source_domain"
                ],
                "gold_source_class": gold[
                    "source_class"
                ],
            }

            if pred_record.get("status") == "prediction":
                predicted = pred_record["prediction"]
                member.update(
                    {
                        "prediction_status": "prediction",
                        "predicted_resolution_status": predicted[
                            "resolution_status"
                        ],
                        "predicted_source_domain": predicted[
                            "source_domain"
                        ],
                        "predicted_source_class": predicted[
                            "source_class"
                        ],
                    }
                )
            else:
                member.update(
                    {
                        "prediction_status": "error",
                        "error_type": pred_record.get(
                            "error_type"
                        ),
                        "error": pred_record.get("error"),
                    }
                )

            member_details.append(member)

        failed_contrast_details.append(
            {
                "contrast_group": group,
                "members": members,
                "failed_members": failed_members,
                "member_details": member_details,
            }
        )

    if len(failed_contrast_details) != 4:
        raise RuntimeError(
            "Expected 4 failed contrast groups."
        )

    source_class_confusion = score.get(
        "confusions",
        {},
    ).get("source_class_confusion")

    source_domain_confusion = score.get(
        "confusions",
        {},
    ).get("source_domain_confusion")

    resolution_confusion = score.get(
        "confusions",
        {},
    ).get("resolution_status_confusion")

    if not all(
        isinstance(item, dict)
        for item in (
            source_class_confusion,
            source_domain_confusion,
            resolution_confusion,
        )
    ):
        raise RuntimeError(
            "Frozen score is missing confusion matrices."
        )

    focus_classes = {
        "current_fee_or_charge_information",
        "inz_live_service_information",
    }

    focus_failures = [
        item
        for item in failures
        if item["gold"]["source_class"] in focus_classes
    ]

    focus_by_gold_class: dict[str, list[dict[str, Any]]] = {}

    for source_class in sorted(focus_classes):
        focus_by_gold_class[source_class] = [
            item
            for item in focus_failures
            if item["gold"]["source_class"] == source_class
        ]

    over_abstention_count = mechanism_counts[
        "over_abstention_resolved_to_unresolved"
    ]

    under_abstention_count = mechanism_counts[
        "under_abstention_unresolved_to_resolved"
    ]

    same_domain_wrong_class_count = mechanism_counts[
        "wrong_source_class_within_correct_domain"
    ]

    wrong_domain_count = mechanism_counts[
        "wrong_source_domain"
    ]

    authority_only_count = mechanism_counts[
        "authority_type_only_mismatch"
    ]

    multi_field_count = mechanism_counts[
        "multi_field_resolved_classification_mismatch"
    ]

    diagnostic_findings = []

    if over_abstention_count:
        diagnostic_findings.append(
            {
                "finding": (
                    "The classifier shows resolved-case underreach through "
                    "over-abstention."
                ),
                "evidence": (
                    f"{over_abstention_count} non-error failure(s) map a "
                    "gold-resolved proposition to unresolved."
                ),
            }
        )

    if focus_failures:
        diagnostic_findings.append(
            {
                "finding": (
                    "Live INZ service information and current fee/charge "
                    "classification are confirmed weak classes in this run."
                ),
                "evidence": (
                    "The frozen acceptance result records 0/3 recall for "
                    "inz_live_service_information and 0/2 for "
                    "current_fee_or_charge_information."
                ),
            }
        )

    if error_cases:
        diagnostic_findings.append(
            {
                "finding": (
                    "Execution/validation robustness is independently a "
                    "hard-gate failure."
                ),
                "evidence": (
                    f"{len(error_cases)} of 34 first-run cases ended in "
                    "error and no retry/repair was permitted."
                ),
            }
        )

    if len(failed_contrast_details) == 4:
        diagnostic_findings.append(
            {
                "finding": (
                    "The classifier did not consistently preserve all frozen "
                    "paired distinctions."
                ),
                "evidence": (
                    "4 of 11 contrast groups failed full four-field "
                    "consistency."
                ),
            }
        )

    if (
        resolved_gold_failure_count > unresolved_gold_failure_count
        and score["metrics"]["unresolved_recall"]["percent"] == 100.0
    ):
        diagnostic_findings.append(
            {
                "finding": (
                    "The observed asymmetry is toward resolved-case underreach, "
                    "not unsafe resolution of frozen unresolved cases."
                ),
                "evidence": (
                    f"{resolved_gold_failure_count}/{len(failures)} total "
                    "four-field failures occur on gold-resolved cases while "
                    "unresolved recall is 6/6."
                ),
            }
        )

    analysis = {
        "schema": (
            "waypoint-source-boundary-classifier-failure-analysis-v1"
        ),
        "status": "DIAGNOSTIC_COMPLETE_NO_CHANGES_AUTHORISED",
        "analysed_on": str(date.today()),
        "source_artifacts": {
            "contract_test_pack_v3_sha256": (
                EXPECTED_PACK_SHA256
            ),
            "prediction_sha256": (
                EXPECTED_PREDICTIONS_SHA256
            ),
            "score_sha256": EXPECTED_SCORE_SHA256,
            "score_result_v1_sha256": (
                EXPECTED_SCORE_RESULT_SHA256
            ),
        },
        "frozen_acceptance_result": {
            "decision": "FAIL",
            "four_field_exact_match": "26/34",
            "unresolved_recall": "6/6",
            "resolved_recall": "21/28",
            "error_count": "2/34",
            "failed_contrast_groups": "4/11",
        },
        "failure_counts": {
            "total_four_field_failures": len(failures),
            "execution_or_validation_errors": len(error_cases),
            "non_error_classification_failures": (
                len(non_error_failures)
            ),
            "gold_resolved_failures": (
                resolved_gold_failure_count
            ),
            "gold_unresolved_failures": (
                unresolved_gold_failure_count
            ),
        },
        "failure_mechanism_counts": dict(
            sorted(mechanism_counts.items())
        ),
        "changed_field_counts_non_error_failures": dict(
            sorted(changed_field_counts.items())
        ),
        "gold_source_class_failure_counts": dict(
            sorted(gold_class_failure_counts.items())
        ),
        "predicted_source_class_failure_counts": dict(
            sorted(predicted_class_failure_counts.items())
        ),
        "mechanism_summary": {
            "over_abstention_resolved_to_unresolved": (
                over_abstention_count
            ),
            "under_abstention_unresolved_to_resolved": (
                under_abstention_count
            ),
            "wrong_source_domain": wrong_domain_count,
            "wrong_source_class_within_correct_domain": (
                same_domain_wrong_class_count
            ),
            "authority_type_only_mismatch": (
                authority_only_count
            ),
            "multi_field_resolved_classification_mismatch": (
                multi_field_count
            ),
            "execution_or_validation_error": len(error_cases),
        },
        "focus_classes": {
            "current_fee_or_charge_information": {
                "frozen_recall": "0/2",
                "failure_cases": focus_by_gold_class[
                    "current_fee_or_charge_information"
                ],
            },
            "inz_live_service_information": {
                "frozen_recall": "0/3",
                "failure_cases": focus_by_gold_class[
                    "inz_live_service_information"
                ],
            },
        },
        "error_cases": error_cases,
        "non_error_failures": non_error_failures,
        "all_failures": failures,
        "failed_contrast_groups": failed_contrast_details,
        "confusion_matrices": {
            "resolution_status": resolution_confusion,
            "source_domain": source_domain_confusion,
            "source_class": source_class_confusion,
        },
        "diagnostic_findings": diagnostic_findings,
        "methodological_status": {
            "development_evidence_only": True,
            "same_pack_may_be_used_for_diagnosis": True,
            "same_pack_may_be_used_for_regression_testing": True,
            "same_pack_must_not_be_described_as_untouched_after_tuning": True,
            "no_threshold_change": True,
            "no_classifier_change": True,
            "no_model_calls": True,
        },
        "authorisations": {
            "human_diagnostic_review_authorised": True,
            "failure_taxonomy_freeze_authorised": False,
            "classifier_prompt_change_authorised": False,
            "classifier_logic_change_authorised": False,
            "classifier_rerun_authorised": False,
            "new_acceptance_pack_build_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_step": {
            "name": "human_review_failure_analysis_v1",
            "authorised": True,
            "purpose": (
                "Review the exact failed cases and determine the minimum "
                "evidence-supported diagnosis before authorising any revised "
                "classifier design."
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
        "DIAGNOSTIC_COMPLETE_NO_CHANGES_AUTHORISED"
    ):
        raise RuntimeError(
            "Saved failure-analysis status changed."
        )

    if saved.get(
        "failure_counts",
        {},
    ).get("total_four_field_failures") != EXPECTED_FAILURE_COUNT:
        raise RuntimeError(
            "Saved failure count changed."
        )

    print("Waypoint source-boundary classifier failure analysis v1")
    print("=" * 61)
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
    print("Frozen failure inventory")
    print("-" * 61)
    print(
        f"Total four-field failures:  "
        f"{len(failures)}/34"
    )
    print(
        f"Execution/validation errors:"
        f"  {len(error_cases)}/34"
    )
    print(
        f"Non-error failures:         "
        f"{len(non_error_failures)}/34"
    )
    print(
        f"Gold-resolved failures:     "
        f"{resolved_gold_failure_count}/28"
    )
    print(
        f"Gold-unresolved failures:   "
        f"{unresolved_gold_failure_count}/6"
    )
    print()
    print("Mechanisms")
    print("-" * 61)
    print(
        "Over-abstention:             "
        f"{over_abstention_count}"
    )
    print(
        "Under-abstention:            "
        f"{under_abstention_count}"
    )
    print(
        "Wrong source domain:         "
        f"{wrong_domain_count}"
    )
    print(
        "Wrong class, correct domain: "
        f"{same_domain_wrong_class_count}"
    )
    print(
        "Authority-only mismatch:     "
        f"{authority_only_count}"
    )
    print(
        "Other multi-field mismatch:  "
        f"{multi_field_count}"
    )
    print(
        "Execution/validation error:  "
        f"{len(error_cases)}"
    )
    print()
    print("Frozen weak classes")
    print("-" * 61)
    print(
        "current_fee_or_charge_information: "
        "0/2"
    )
    print(
        "inz_live_service_information:      "
        "0/3"
    )
    print()
    print(
        f"Failed contrast groups:      "
        f"{len(failed_contrast_details)}/11"
    )
    print()
    print("Changes authorised:          NONE")
    print("Model calls:                 NONE")
    print("Threshold changes:           NONE")
    print("Classifier changes:          NONE")
    print()
    print(
        f"Output:                     "
        f"{OUTPUT_PATH}"
    )
    print(
        f"Failure-analysis SHA256:    "
        f"{sha256(OUTPUT_PATH)}"
    )
    print()
    print("Next task:                  HUMAN DIAGNOSTIC REVIEW")
    print()
    print("Failure analysis v1:        COMPLETE")


if __name__ == "__main__":
    main()
