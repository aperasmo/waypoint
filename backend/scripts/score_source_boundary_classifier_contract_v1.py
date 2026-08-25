"""Score the first Waypoint source-boundary classifier contract run.

EXPERIMENTAL EVALUATION ONLY.

This scorer:
- makes zero model calls;
- does not import the classifier or blind runner;
- reads only the frozen prediction artifact, approved contract pack v3,
  and frozen acceptance thresholds;
- treats prediction errors/malformed records as incorrect;
- applies the frozen thresholds exactly;
- refuses to overwrite an existing score artifact.

Intended command after the first prediction artifact exists:
    uv run python -m scripts.score_source_boundary_classifier_contract_v1
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

PACK_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_contract_test_pack_v3.json"
)

THRESHOLDS_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_acceptance_thresholds_v1.json"
)

PREDICTIONS_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_predictions_v1.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_score_v1.json"
)

EXPECTED_PACK_SHA256 = (
    "C820489715EA3F54138023D680D04DFBF"
    "F5575A515B936FA8C2241E2EA5B219D"
)

EXPECTED_THRESHOLDS_SHA256 = (
    "5E8AFBFFEE5880DEBF4FA6B0A6514E8C"
    "6702F5D9E74D620BA4C1575F49CAC03C"
)

EXPECTED_CLASSIFIER_SHA256 = (
    "BC77C28033F74E3092C8428DE623293D"
    "266FBDEE7FFC237EE79C8AB6F79DE9F3"
)

EXPECTED_RUNNER_SHA256 = (
    "CE2709C654E576B56520AAD7CA9DB90A"
    "88E80CF775C3B8AC7A3864669F610FEF"
)

EXPECTED_CASE_COUNT = 34

FOUR_FIELDS = (
    "resolution_status",
    "source_domain",
    "source_class",
    "responsible_authority_type",
)

ERROR_LABEL = "__error__"


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
            "Refusing to score classifier predictions."
        )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be a JSON object.")

    return payload


def pct(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 0.0

    return round((numerator / denominator) * 100.0, 1)


def index_contract_cases(
    pack: dict[str, Any],
) -> tuple[
    list[str],
    dict[str, dict[str, Any]],
    dict[str, list[str]],
]:
    if pack.get("schema") != (
        "waypoint-source-boundary-classifier-contract-test-pack-v3"
    ):
        raise RuntimeError("Unexpected contract-pack-v3 schema.")

    if pack.get("status") != (
        "FROZEN_SYNTHETIC_CONTRACT_TEST_PACK_READY_FOR_HUMAN_REVIEW"
    ):
        raise RuntimeError("Unexpected contract-pack-v3 status.")

    tests = pack.get("tests")

    if not isinstance(tests, list):
        raise RuntimeError("Contract-pack tests must be a list.")

    if len(tests) != EXPECTED_CASE_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_CASE_COUNT} contract tests; got {len(tests)}."
        )

    ordered_ids: list[str] = []
    cases: dict[str, dict[str, Any]] = {}
    contrast_groups: dict[str, list[str]] = defaultdict(list)

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
            raise RuntimeError(f"{test_id}: expected output missing.")

        if set(expected) != set(FOUR_FIELDS):
            raise RuntimeError(
                f"{test_id}: expected output must contain exactly "
                f"{list(FOUR_FIELDS)}."
            )

        for field in FOUR_FIELDS:
            if not isinstance(expected.get(field), str):
                raise RuntimeError(
                    f"{test_id}: expected {field} must be a string."
                )

        ordered_ids.append(test_id)
        cases[test_id] = item

        group = item.get("contrast_group")

        if group is not None:
            if not isinstance(group, str) or not group:
                raise RuntimeError(
                    f"{test_id}: invalid contrast_group."
                )

            contrast_groups[group].append(test_id)

    coverage = pack.get("coverage")

    if not isinstance(coverage, dict):
        raise RuntimeError("Contract pack is missing coverage metadata.")

    frozen_groups = coverage.get("contrast_groups")

    if not isinstance(frozen_groups, dict):
        raise RuntimeError(
            "Contract pack is missing frozen contrast groups."
        )

    normalised_frozen_groups = {
        str(group): list(members)
        for group, members in frozen_groups.items()
    }

    if dict(contrast_groups) != normalised_frozen_groups:
        raise RuntimeError(
            "Derived contrast groups differ from frozen coverage metadata."
        )

    if len(contrast_groups) != 11:
        raise RuntimeError(
            f"Expected 11 contrast groups; got {len(contrast_groups)}."
        )

    return ordered_ids, cases, dict(contrast_groups)


def index_predictions(
    predictions: dict[str, Any],
    *,
    expected_order: list[str],
) -> dict[str, dict[str, Any]]:
    if predictions.get("schema") != (
        "waypoint-source-boundary-classifier-predictions-v1"
    ):
        raise RuntimeError("Unexpected prediction-artifact schema.")

    if predictions.get("status") != (
        "FIRST_UNTOUCHED_SYNTHETIC_CONTRACT_RUN"
    ):
        raise RuntimeError("Unexpected prediction-artifact status.")

    source_artifacts = predictions.get("source_artifacts")

    if not isinstance(source_artifacts, dict):
        raise RuntimeError(
            "Prediction artifact is missing source_artifacts."
        )

    expected_hashes = {
        "classifier_sha256": EXPECTED_CLASSIFIER_SHA256,
        "runner_sha256": EXPECTED_RUNNER_SHA256,
        "contract_test_pack_sha256": EXPECTED_PACK_SHA256,
        "acceptance_thresholds_sha256": EXPECTED_THRESHOLDS_SHA256,
    }

    for key, expected in expected_hashes.items():
        if source_artifacts.get(key) != expected:
            raise RuntimeError(
                f"Prediction artifact {key} mismatch.\n"
                f"Expected: {expected}\n"
                f"Found:    {source_artifacts.get(key)!r}"
            )

    counts = predictions.get("counts")

    if not isinstance(counts, dict):
        raise RuntimeError("Prediction artifact is missing counts.")

    if counts.get("case_count") != EXPECTED_CASE_COUNT:
        raise RuntimeError("Prediction artifact case_count is not 34.")

    if counts.get("model_call_attempts") != EXPECTED_CASE_COUNT:
        raise RuntimeError(
            "Prediction artifact model_call_attempts is not 34."
        )

    if (
        int(counts.get("completed_predictions", 0))
        + int(counts.get("errors", 0))
        != EXPECTED_CASE_COUNT
    ):
        raise RuntimeError(
            "Prediction completed/error counts do not sum to 34."
        )

    records = predictions.get("predictions")

    if not isinstance(records, list):
        raise RuntimeError("Prediction records must be a list.")

    if len(records) != EXPECTED_CASE_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_CASE_COUNT} prediction records; "
            f"got {len(records)}."
        )

    indexed: dict[str, dict[str, Any]] = {}
    actual_order: list[str] = []

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
                f"Duplicate prediction test_id: {test_id}"
            )

        status = record.get("status")

        if status not in {"prediction", "error"}:
            raise RuntimeError(
                f"{test_id}: invalid prediction status {status!r}."
            )

        if status == "prediction":
            payload = record.get("prediction")

            if not isinstance(payload, dict):
                raise RuntimeError(
                    f"{test_id}: prediction payload must be an object."
                )

            required = set(FOUR_FIELDS) | {"basis"}

            if set(payload) != required:
                raise RuntimeError(
                    f"{test_id}: prediction payload fields differ from "
                    "the frozen output schema."
                )

            for field in FOUR_FIELDS:
                if not isinstance(payload.get(field), str):
                    raise RuntimeError(
                        f"{test_id}: predicted {field} must be a string."
                    )

            if not isinstance(payload.get("basis"), str):
                raise RuntimeError(
                    f"{test_id}: prediction basis must be a string."
                )

        else:
            if "prediction" in record:
                raise RuntimeError(
                    f"{test_id}: error record must not include prediction."
                )

        indexed[test_id] = record
        actual_order.append(test_id)

    if actual_order != expected_order:
        raise RuntimeError(
            "Prediction order differs from frozen contract-pack order."
        )

    return indexed


def increment_confusion(
    matrix: dict[str, Counter[str]],
    *,
    gold: str,
    predicted: str,
) -> None:
    matrix[gold][predicted] += 1


def serialise_confusion(
    matrix: dict[str, Counter[str]],
) -> dict[str, dict[str, int]]:
    labels = sorted(
        set(matrix)
        | {
            predicted
            for row in matrix.values()
            for predicted in row
        }
    )

    output: dict[str, dict[str, int]] = {}

    for gold in labels:
        row = matrix.get(gold, Counter())
        output[gold] = {
            predicted: int(row.get(predicted, 0))
            for predicted in labels
        }

    return output


def evaluate_gate(
    *,
    actual_count: int | None = None,
    actual_percent: float | None = None,
    gate: dict[str, Any],
) -> tuple[bool, str]:
    if "minimum_correct" in gate:
        if actual_count is None:
            raise RuntimeError(
                "Integer minimum gate requires actual_count."
            )

        required = int(gate["minimum_correct"])
        passed = actual_count >= required

        return (
            passed,
            f"{actual_count}/{gate['denominator']} "
            f"{'>=' if passed else '<'} {required}/{gate['denominator']}",
        )

    if "minimum_groups_correct" in gate:
        if actual_count is None:
            raise RuntimeError(
                "Group minimum gate requires actual_count."
            )

        required = int(gate["minimum_groups_correct"])
        passed = actual_count >= required

        return (
            passed,
            f"{actual_count}/{gate['denominator']} "
            f"{'>=' if passed else '<'} {required}/{gate['denominator']}",
        )

    if "minimum_percent" in gate:
        if actual_percent is None:
            raise RuntimeError(
                "Percentage minimum gate requires actual_percent."
            )

        required = float(gate["minimum_percent"])
        passed = actual_percent >= required

        return (
            passed,
            f"{actual_percent:.1f}% "
            f"{'>=' if passed else '<'} {required:.1f}%",
        )

    if "maximum_count" in gate:
        if actual_count is None:
            raise RuntimeError(
                "Integer maximum gate requires actual_count."
            )

        allowed = int(gate["maximum_count"])
        passed = actual_count <= allowed

        return (
            passed,
            f"{actual_count}/{gate['denominator']} "
            f"{'<=' if passed else '>'} {allowed}/{gate['denominator']}",
        )

    raise RuntimeError("Unknown threshold gate shape.")


def main() -> None:
    require_sha(
        PACK_PATH,
        EXPECTED_PACK_SHA256,
        "Frozen contract test pack v3",
    )
    require_sha(
        THRESHOLDS_PATH,
        EXPECTED_THRESHOLDS_SHA256,
        "Frozen acceptance thresholds",
    )

    if not PREDICTIONS_PATH.exists():
        raise SystemExit(
            f"Prediction artifact not found: {PREDICTIONS_PATH}\n"
            "Nothing to score."
        )

    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Score artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    pack = load_json(PACK_PATH)
    thresholds = load_json(THRESHOLDS_PATH)
    predictions = load_json(PREDICTIONS_PATH)

    if thresholds.get("schema") != (
        "waypoint-source-boundary-classifier-acceptance-thresholds-v1"
    ):
        raise RuntimeError("Unexpected threshold schema.")

    if thresholds.get("status") != (
        "FROZEN_BEFORE_FIRST_CLASSIFIER_PREDICTION"
    ):
        raise RuntimeError("Thresholds are not frozen.")

    ordered_ids, gold_cases, contrast_groups = (
        index_contract_cases(pack)
    )

    predicted_records = index_predictions(
        predictions,
        expected_order=ordered_ids,
    )

    four_field_correct = 0
    resolution_correct = 0
    domain_correct = 0
    class_correct = 0

    gold_resolution_counts: Counter[str] = Counter()
    correct_resolution_counts: Counter[str] = Counter()

    gold_class_counts: Counter[str] = Counter()
    correct_class_counts: Counter[str] = Counter()

    resolution_confusion: dict[str, Counter[str]] = defaultdict(Counter)
    domain_confusion: dict[str, Counter[str]] = defaultdict(Counter)
    class_confusion: dict[str, Counter[str]] = defaultdict(Counter)

    case_results: list[dict[str, Any]] = []
    error_count = 0

    for test_id in ordered_ids:
        gold_case = gold_cases[test_id]
        gold = gold_case["expected"]
        record = predicted_records[test_id]

        gold_resolution = gold["resolution_status"]
        gold_domain = gold["source_domain"]
        gold_class = gold["source_class"]

        gold_resolution_counts[gold_resolution] += 1
        gold_class_counts[gold_class] += 1

        status = record["status"]

        if status == "error":
            error_count += 1

            increment_confusion(
                resolution_confusion,
                gold=gold_resolution,
                predicted=ERROR_LABEL,
            )
            increment_confusion(
                domain_confusion,
                gold=gold_domain,
                predicted=ERROR_LABEL,
            )
            increment_confusion(
                class_confusion,
                gold=gold_class,
                predicted=ERROR_LABEL,
            )

            case_results.append(
                {
                    "test_id": test_id,
                    "prediction_status": "error",
                    "four_field_correct": False,
                    "resolution_status_correct": False,
                    "source_domain_correct": False,
                    "source_class_correct": False,
                    "responsible_authority_type_correct": False,
                    "error_type": record.get("error_type"),
                    "error": record.get("error"),
                }
            )

            continue

        predicted = record["prediction"]

        resolution_match = (
            predicted["resolution_status"]
            == gold["resolution_status"]
        )

        domain_match = (
            predicted["source_domain"]
            == gold["source_domain"]
        )

        class_match = (
            predicted["source_class"]
            == gold["source_class"]
        )

        authority_match = (
            predicted["responsible_authority_type"]
            == gold["responsible_authority_type"]
        )

        exact_match = (
            resolution_match
            and domain_match
            and class_match
            and authority_match
        )

        if exact_match:
            four_field_correct += 1

        if resolution_match:
            resolution_correct += 1
            correct_resolution_counts[gold_resolution] += 1

        if domain_match:
            domain_correct += 1

        if class_match:
            class_correct += 1
            correct_class_counts[gold_class] += 1

        increment_confusion(
            resolution_confusion,
            gold=gold_resolution,
            predicted=predicted["resolution_status"],
        )
        increment_confusion(
            domain_confusion,
            gold=gold_domain,
            predicted=predicted["source_domain"],
        )
        increment_confusion(
            class_confusion,
            gold=gold_class,
            predicted=predicted["source_class"],
        )

        case_results.append(
            {
                "test_id": test_id,
                "prediction_status": "prediction",
                "four_field_correct": exact_match,
                "resolution_status_correct": resolution_match,
                "source_domain_correct": domain_match,
                "source_class_correct": class_match,
                "responsible_authority_type_correct": authority_match,
                "gold": {
                    field: gold[field]
                    for field in FOUR_FIELDS
                },
                "prediction": {
                    field: predicted[field]
                    for field in FOUR_FIELDS
                },
            }
        )

    if sum(gold_resolution_counts.values()) != EXPECTED_CASE_COUNT:
        raise RuntimeError("Gold resolution counts do not sum to 34.")

    if sum(gold_class_counts.values()) != EXPECTED_CASE_COUNT:
        raise RuntimeError("Gold source-class counts do not sum to 34.")

    if gold_resolution_counts != Counter(
        {"resolved": 28, "unresolved": 6}
    ):
        raise RuntimeError(
            "Frozen resolved/unresolved class distribution changed."
        )

    per_class_recall: dict[str, dict[str, Any]] = {}

    for source_class in sorted(gold_class_counts):
        support = gold_class_counts[source_class]
        correct = correct_class_counts[source_class]
        recall_percent = pct(correct, support)

        per_class_recall[source_class] = {
            "correct": int(correct),
            "support": int(support),
            "recall_percent": recall_percent,
        }

    macro_recall = round(
        sum(
            item["recall_percent"]
            for item in per_class_recall.values()
        )
        / len(per_class_recall),
        1,
    )

    unresolved_correct = correct_resolution_counts["unresolved"]
    resolved_correct = correct_resolution_counts["resolved"]

    failed_contrast_groups: list[dict[str, Any]] = []
    contrast_groups_correct = 0

    case_correct_map = {
        item["test_id"]: bool(item["four_field_correct"])
        for item in case_results
    }

    for group, members in contrast_groups.items():
        failed_members = [
            test_id
            for test_id in members
            if not case_correct_map[test_id]
        ]

        if not failed_members:
            contrast_groups_correct += 1
        else:
            failed_contrast_groups.append(
                {
                    "contrast_group": group,
                    "members": members,
                    "failed_members": failed_members,
                }
            )

    metrics = {
        "four_field_exact_match_accuracy": {
            "correct": four_field_correct,
            "total": EXPECTED_CASE_COUNT,
            "percent": pct(
                four_field_correct,
                EXPECTED_CASE_COUNT,
            ),
        },
        "resolution_status_accuracy": {
            "correct": resolution_correct,
            "total": EXPECTED_CASE_COUNT,
            "percent": pct(
                resolution_correct,
                EXPECTED_CASE_COUNT,
            ),
        },
        "source_domain_accuracy": {
            "correct": domain_correct,
            "total": EXPECTED_CASE_COUNT,
            "percent": pct(
                domain_correct,
                EXPECTED_CASE_COUNT,
            ),
        },
        "source_class_accuracy": {
            "correct": class_correct,
            "total": EXPECTED_CASE_COUNT,
            "percent": pct(
                class_correct,
                EXPECTED_CASE_COUNT,
            ),
        },
        "source_class_macro_recall": {
            "percent": macro_recall,
            "class_count": len(per_class_recall),
        },
        "per_source_class_recall": per_class_recall,
        "unresolved_recall": {
            "correct": int(unresolved_correct),
            "total": 6,
            "percent": pct(
                unresolved_correct,
                6,
            ),
        },
        "resolved_recall": {
            "correct": int(resolved_correct),
            "total": 28,
            "percent": pct(
                resolved_correct,
                28,
            ),
        },
        "contrast_group_full_consistency_rate": {
            "correct_groups": contrast_groups_correct,
            "total_groups": len(contrast_groups),
            "percent": pct(
                contrast_groups_correct,
                len(contrast_groups),
            ),
        },
        "malformed_or_error_rate": {
            "error_count": error_count,
            "total": EXPECTED_CASE_COUNT,
            "percent": pct(
                error_count,
                EXPECTED_CASE_COUNT,
            ),
        },
    }

    acceptance = thresholds.get("acceptance_logic")

    if not isinstance(acceptance, dict):
        raise RuntimeError(
            "Threshold artifact is missing acceptance_logic."
        )

    if acceptance.get("all_gates_required") is not True:
        raise RuntimeError(
            "Frozen threshold artifact no longer requires all gates."
        )

    if acceptance.get("automatic_retry") is not False:
        raise RuntimeError(
            "Frozen threshold artifact unexpectedly allows retries."
        )

    if acceptance.get("manual_override") is not False:
        raise RuntimeError(
            "Frozen threshold artifact unexpectedly allows manual override."
        )

    hard_gates = acceptance.get("hard_gates")

    if not isinstance(hard_gates, dict):
        raise RuntimeError(
            "Threshold artifact is missing hard_gates."
        )

    gate_inputs: dict[
        str,
        tuple[int | None, float | None],
    ] = {
        "four_field_exact_match_accuracy": (
            four_field_correct,
            metrics["four_field_exact_match_accuracy"]["percent"],
        ),
        "resolution_status_accuracy": (
            resolution_correct,
            metrics["resolution_status_accuracy"]["percent"],
        ),
        "source_domain_accuracy": (
            domain_correct,
            metrics["source_domain_accuracy"]["percent"],
        ),
        "source_class_accuracy": (
            class_correct,
            metrics["source_class_accuracy"]["percent"],
        ),
        "source_class_macro_recall": (
            None,
            macro_recall,
        ),
        "unresolved_recall": (
            int(unresolved_correct),
            metrics["unresolved_recall"]["percent"],
        ),
        "resolved_recall": (
            int(resolved_correct),
            metrics["resolved_recall"]["percent"],
        ),
        "contrast_group_full_consistency_rate": (
            contrast_groups_correct,
            metrics[
                "contrast_group_full_consistency_rate"
            ]["percent"],
        ),
        "malformed_or_error_rate": (
            error_count,
            metrics["malformed_or_error_rate"]["percent"],
        ),
    }

    if set(hard_gates) != set(gate_inputs):
        raise RuntimeError(
            "Frozen hard-gate set differs from scorer metric set."
        )

    gate_results: dict[str, dict[str, Any]] = {}
    all_hard_gates_pass = True

    for metric_name, gate in hard_gates.items():
        if not isinstance(gate, dict):
            raise RuntimeError(
                f"{metric_name}: threshold gate must be an object."
            )

        actual_count, actual_percent = gate_inputs[metric_name]

        passed, comparison = evaluate_gate(
            actual_count=actual_count,
            actual_percent=actual_percent,
            gate=gate,
        )

        gate_results[metric_name] = {
            "passed": passed,
            "comparison": comparison,
        }

        if not passed:
            all_hard_gates_pass = False

    per_class_guard = acceptance.get("per_class_guard")

    if not isinstance(per_class_guard, dict):
        raise RuntimeError(
            "Threshold artifact is missing per_class_guard."
        )

    per_class_floor = float(
        per_class_guard[
            "minimum_recall_percent_for_each_resolved_source_class"
        ]
    )

    per_class_floor_failures: list[dict[str, Any]] = []

    for source_class, item in per_class_recall.items():
        if source_class == "unresolved":
            continue

        if item["recall_percent"] < per_class_floor:
            per_class_floor_failures.append(
                {
                    "source_class": source_class,
                    "recall_percent": item["recall_percent"],
                    "minimum_percent": per_class_floor,
                    "correct": item["correct"],
                    "support": item["support"],
                }
            )

    per_class_floor_passed = not per_class_floor_failures

    overall_pass = (
        all_hard_gates_pass
        and per_class_floor_passed
    )

    score = {
        "schema": "waypoint-source-boundary-classifier-score-v1",
        "status": (
            "ACCEPTANCE_PASS"
            if overall_pass
            else "ACCEPTANCE_FAIL"
        ),
        "source_artifacts": {
            "prediction_sha256": sha256(PREDICTIONS_PATH),
            "contract_test_pack_sha256": sha256(PACK_PATH),
            "acceptance_thresholds_sha256": sha256(
                THRESHOLDS_PATH
            ),
            "classifier_sha256": EXPECTED_CLASSIFIER_SHA256,
            "runner_sha256": EXPECTED_RUNNER_SHA256,
        },
        "counts": {
            "case_count": EXPECTED_CASE_COUNT,
            "prediction_errors": error_count,
            "contrast_group_count": len(contrast_groups),
            "source_class_count": len(per_class_recall),
        },
        "metrics": metrics,
        "confusions": {
            "resolution_status_confusion": serialise_confusion(
                resolution_confusion
            ),
            "source_domain_confusion": serialise_confusion(
                domain_confusion
            ),
            "source_class_confusion": serialise_confusion(
                class_confusion
            ),
        },
        "acceptance": {
            "overall_pass": overall_pass,
            "all_hard_gates_pass": all_hard_gates_pass,
            "per_class_floor_passed": per_class_floor_passed,
            "hard_gates": gate_results,
            "per_class_floor_percent": per_class_floor,
            "per_class_floor_failures": per_class_floor_failures,
            "failed_contrast_groups": failed_contrast_groups,
            "automatic_retry": False,
            "manual_override": False,
        },
        "case_results": case_results,
        "interpretation": {
            "scope": (
                "Synthetic architecture-contract evaluation only."
            ),
            "passing_does_not_establish": [
                "real-world answer-layer generalisation",
                "production safety",
                "runtime integration approval",
                "candidate-v7 approval",
            ],
            "next_step_if_pass": (
                "Freeze and review the experimental classifier result before "
                "any answer-layer candidate design."
            ),
            "next_step_if_fail": (
                "Treat this prediction set as development evidence. Do not "
                "lower thresholds or rescore a revised classifier against the "
                "same pack as an untouched acceptance run."
            ),
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            score,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)

    if saved.get("status") not in {
        "ACCEPTANCE_PASS",
        "ACCEPTANCE_FAIL",
    }:
        raise RuntimeError("Saved score status is invalid.")

    if saved.get("acceptance", {}).get(
        "overall_pass"
    ) is not overall_pass:
        raise RuntimeError(
            "Saved overall acceptance decision changed."
        )

    print("Waypoint source-boundary classifier contract score")
    print("=" * 56)
    print(f"Predictions SHA256:          {sha256(PREDICTIONS_PATH)}")
    print(f"Contract pack SHA256:        {sha256(PACK_PATH)}")
    print(f"Threshold SHA256:            {sha256(THRESHOLDS_PATH)}")
    print()
    print("Metrics")
    print("-" * 56)
    print(
        "4-field exact match:         "
        f"{four_field_correct}/34 "
        f"({metrics['four_field_exact_match_accuracy']['percent']:.1f}%)"
    )
    print(
        "Resolution-status accuracy:  "
        f"{resolution_correct}/34 "
        f"({metrics['resolution_status_accuracy']['percent']:.1f}%)"
    )
    print(
        "Source-domain accuracy:      "
        f"{domain_correct}/34 "
        f"({metrics['source_domain_accuracy']['percent']:.1f}%)"
    )
    print(
        "Source-class accuracy:       "
        f"{class_correct}/34 "
        f"({metrics['source_class_accuracy']['percent']:.1f}%)"
    )
    print(
        "Source-class macro recall:   "
        f"{macro_recall:.1f}%"
    )
    print(
        "Unresolved recall:           "
        f"{unresolved_correct}/6 "
        f"({metrics['unresolved_recall']['percent']:.1f}%)"
    )
    print(
        "Resolved recall:             "
        f"{resolved_correct}/28 "
        f"({metrics['resolved_recall']['percent']:.1f}%)"
    )
    print(
        "Contrast consistency:        "
        f"{contrast_groups_correct}/{len(contrast_groups)} "
        f"({metrics['contrast_group_full_consistency_rate']['percent']:.1f}%)"
    )
    print(
        "Malformed/error count:       "
        f"{error_count}/34"
    )
    print()
    print("Hard gates")
    print("-" * 56)

    for metric_name, result in gate_results.items():
        label = "PASS" if result["passed"] else "FAIL"
        print(
            f"{metric_name}: {label} "
            f"({result['comparison']})"
        )

    print()
    print(
        "Per resolved-class floor:    "
        + ("PASS" if per_class_floor_passed else "FAIL")
    )

    if per_class_floor_failures:
        for item in per_class_floor_failures:
            print(
                f"  {item['source_class']}: "
                f"{item['correct']}/{item['support']} "
                f"({item['recall_percent']:.1f}%)"
            )

    print()
    print(
        "ACCEPTANCE DECISION:         "
        + ("PASS" if overall_pass else "FAIL")
    )
    print()
    print(f"Output:                      {OUTPUT_PATH}")
    print(f"Score SHA256:                {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                 NONE")
    print("Retrieval/reranker calls:    NONE")
    print("Database writes:             NONE")
    print("Runtime files modified:      NONE")


if __name__ == "__main__":
    main()
