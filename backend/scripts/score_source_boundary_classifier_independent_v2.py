"""Score the frozen first independent classifier prediction set v2.

SCORING ONLY.
- Zero model calls.
- No classifier import.
- Reads gold pack v5 and thresholds v2 only after prediction result is frozen.
- Refuses to overwrite a score artifact.
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
    / "source_boundary_classifier_independent_contract_test_pack_v5.json"
)

THRESHOLDS_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_acceptance_thresholds_v2.json"
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

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_score_v2.json"
)

EXPECTED_PACK_SHA256 = (
    "1B3CEA56504E3932C7DCA342DF99DC225"
    "23A4676B1C22714B9A122DDD566E67B"
)

EXPECTED_THRESHOLDS_SHA256 = (
    "1BDD2ED8950D6E3E612C66DCD5384BD5"
    "E0CAC784E39A70C3CE09EAD5C310D277"
)

EXPECTED_CLASSIFIER_SHA256 = (
    "8193FCDDB48585EC8A8BA8BCC477D123"
    "011B50F2F38531BEB2D88836975FF949"
)

EXPECTED_BLIND_INPUT_SHA256 = (
    "22D3A1C184F95D65D9571191A1FFF01A"
    "D251050C554BA6D96F15FBABBFDF9D6B"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be an object.")

    return payload


def require_exact_file(
    path: Path,
    expected_sha: str,
    label: str,
) -> None:
    if not path.exists():
        raise RuntimeError(f"{label} not found: {path}")

    actual = sha256(path)

    if actual != expected_sha:
        raise RuntimeError(
            f"{label} SHA mismatch.\n"
            f"Expected: {expected_sha}\n"
            f"Actual:   {actual}"
        )


def percent(n: int, d: int) -> float:
    if d == 0:
        return 0.0
    return round((n / d) * 100.0, 1)


def main() -> None:
    if OUTPUT_PATH.exists():
        raise RuntimeError(
            f"Score artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_exact_file(
        PACK_PATH,
        EXPECTED_PACK_SHA256,
        "Independent pack v5",
    )
    require_exact_file(
        THRESHOLDS_PATH,
        EXPECTED_THRESHOLDS_SHA256,
        "Acceptance thresholds v2",
    )

    if not PREDICTIONS_PATH.exists():
        raise RuntimeError("Prediction artifact does not exist.")

    if not PREDICTION_RESULT_PATH.exists():
        raise RuntimeError(
            "Prediction-result freeze is absent. "
            "Scoring is not authorised."
        )

    pack = load_json(PACK_PATH)
    thresholds = load_json(THRESHOLDS_PATH)
    predictions = load_json(PREDICTIONS_PATH)
    prediction_result = load_json(PREDICTION_RESULT_PATH)

    if prediction_result.get("schema") != (
        "waypoint-source-boundary-classifier-prediction-result-v2"
    ):
        raise RuntimeError("Unexpected prediction-result schema.")

    if prediction_result.get("status") != (
        "FROZEN_FIRST_UNTOUCHED_INDEPENDENT_PREDICTION_RESULT"
    ):
        raise RuntimeError("Prediction result is not frozen for scoring.")

    frozen_prediction_sha = prediction_result.get(
        "prediction_sha256"
    )

    if frozen_prediction_sha != sha256(PREDICTIONS_PATH):
        raise RuntimeError(
            "Prediction artifact changed after prediction-result freeze."
        )

    if prediction_result.get(
        "authorisations", {}
    ).get("scoring_authorised") is not True:
        raise RuntimeError("Scoring is not authorised.")

    source_artifacts = predictions.get("source_artifacts", {})

    if source_artifacts.get(
        "classifier_implementation_v2_sha256"
    ) != EXPECTED_CLASSIFIER_SHA256:
        raise RuntimeError("Prediction classifier binding changed.")

    if source_artifacts.get(
        "blind_input_v2_sha256"
    ) != EXPECTED_BLIND_INPUT_SHA256:
        raise RuntimeError("Prediction blind-input binding changed.")

    if source_artifacts.get(
        "acceptance_thresholds_v2_sha256"
    ) != EXPECTED_THRESHOLDS_SHA256:
        raise RuntimeError("Prediction threshold binding changed.")

    gold_cases = pack.get("tests")
    prediction_cases = predictions.get("cases")

    if not isinstance(gold_cases, list) or len(gold_cases) != 40:
        raise RuntimeError("Gold pack must contain exactly 40 cases.")

    if not isinstance(prediction_cases, list) or len(prediction_cases) != 40:
        raise RuntimeError("Predictions must contain exactly 40 cases.")

    gold_by_id = {
        item["case_id"]: item
        for item in gold_cases
    }
    pred_by_id = {
        item["case_id"]: item
        for item in prediction_cases
    }

    if set(gold_by_id) != set(pred_by_id):
        raise RuntimeError("Prediction case IDs differ from gold case IDs.")

    four_correct = 0
    resolution_correct = 0
    domain_correct = 0
    class_correct = 0
    error_count = 0

    class_total: Counter[str] = Counter()
    class_correct_counts: Counter[str] = Counter()

    resolved_total = 0
    resolved_correct = 0
    unresolved_total = 0
    unresolved_correct = 0

    case_results: list[dict[str, Any]] = []

    for case_id in sorted(gold_by_id):
        gold_item = gold_by_id[case_id]
        pred_item = pred_by_id[case_id]
        gold = gold_item["expected"]

        class_total[gold["source_class"]] += 1

        if gold["resolution_status"] == "resolved":
            resolved_total += 1
        else:
            unresolved_total += 1

        if pred_item.get("status") != "prediction":
            error_count += 1
            case_results.append(
                {
                    "case_id": case_id,
                    "prediction_status": "error",
                    "four_field_correct": False,
                    "gold_source_class": gold["source_class"],
                    "predicted_source_class": None,
                    "error_type": pred_item.get("error_type"),
                    "error": pred_item.get("error"),
                }
            )
            continue

        resolution_match = (
            pred_item.get("resolution_status")
            == gold["resolution_status"]
        )
        domain_match = (
            pred_item.get("source_domain")
            == gold["source_domain"]
        )
        class_match = (
            pred_item.get("source_class")
            == gold["source_class"]
        )
        authority_match = (
            pred_item.get("responsible_authority_type")
            == gold["responsible_authority_type"]
        )

        exact = (
            resolution_match
            and domain_match
            and class_match
            and authority_match
        )

        resolution_correct += int(resolution_match)
        domain_correct += int(domain_match)
        class_correct += int(class_match)
        four_correct += int(exact)

        if class_match:
            class_correct_counts[gold["source_class"]] += 1

        if gold["resolution_status"] == "resolved":
            resolved_correct += int(exact)
        else:
            unresolved_correct += int(
                pred_item.get("source_class") == "unresolved"
            )

        case_results.append(
            {
                "case_id": case_id,
                "prediction_status": "prediction",
                "four_field_correct": exact,
                "resolution_correct": resolution_match,
                "source_domain_correct": domain_match,
                "source_class_correct": class_match,
                "authority_type_correct": authority_match,
                "gold_source_class": gold["source_class"],
                "predicted_source_class": pred_item.get("source_class"),
            }
        )

    per_class_recall: dict[str, dict[str, Any]] = {}

    recall_values: list[float] = []

    for source_class in sorted(class_total):
        total = class_total[source_class]
        correct = class_correct_counts[source_class]
        value = (correct / total) * 100.0
        recall_values.append(value)

        per_class_recall[source_class] = {
            "correct": correct,
            "total": total,
            "percent": round(value, 1),
        }

    macro_recall = round(
        sum(recall_values) / len(recall_values),
        1,
    )

    groups: dict[str, list[str]] = defaultdict(list)

    for item in gold_cases:
        group = item.get("contrast_group")
        if isinstance(group, str) and group:
            groups[group].append(item["case_id"])

    case_exact = {
        item["case_id"]: item["four_field_correct"]
        for item in case_results
    }

    contrast_results: dict[str, dict[str, Any]] = {}
    contrast_correct = 0

    for group in sorted(groups):
        members = groups[group]
        passed = all(case_exact[case_id] for case_id in members)
        contrast_correct += int(passed)

        contrast_results[group] = {
            "members": members,
            "correct": passed,
        }

    metrics = {
        "four_field_exact_match": {
            "correct": four_correct,
            "total": 40,
            "percent": percent(four_correct, 40),
        },
        "resolution_status_accuracy": {
            "correct": resolution_correct,
            "total": 40,
            "percent": percent(resolution_correct, 40),
        },
        "source_domain_accuracy": {
            "correct": domain_correct,
            "total": 40,
            "percent": percent(domain_correct, 40),
        },
        "source_class_accuracy": {
            "correct": class_correct,
            "total": 40,
            "percent": percent(class_correct, 40),
        },
        "source_class_macro_recall": {
            "percent": macro_recall,
        },
        "unresolved_recall": {
            "correct": unresolved_correct,
            "total": unresolved_total,
            "percent": percent(unresolved_correct, unresolved_total),
        },
        "resolved_recall": {
            "correct": resolved_correct,
            "total": resolved_total,
            "percent": percent(resolved_correct, resolved_total),
        },
        "contrast_consistency": {
            "correct": contrast_correct,
            "total": len(groups),
            "percent": percent(contrast_correct, len(groups)),
        },
        "malformed_or_error_count": {
            "count": error_count,
            "total": 40,
        },
    }

    gates = thresholds["hard_gates"]

    gate_results = {
        "four_field_exact_match": (
            four_correct
            >= gates["four_field_exact_match"]["minimum_correct"]
        ),
        "resolution_status_accuracy": (
            resolution_correct
            >= gates["resolution_status_accuracy"]["minimum_correct"]
        ),
        "source_domain_accuracy": (
            domain_correct
            >= gates["source_domain_accuracy"]["minimum_correct"]
        ),
        "source_class_accuracy": (
            class_correct
            >= gates["source_class_accuracy"]["minimum_correct"]
        ),
        "source_class_macro_recall": (
            macro_recall
            >= gates["source_class_macro_recall"]["minimum_percent"]
        ),
        "unresolved_recall": (
            unresolved_correct
            >= gates["unresolved_recall"]["minimum_correct"]
        ),
        "resolved_recall": (
            resolved_correct
            >= gates["resolved_recall"]["minimum_correct"]
        ),
        "contrast_consistency": (
            contrast_correct
            >= gates["contrast_consistency"]["minimum_groups_correct"]
        ),
        "malformed_or_error_count": (
            error_count
            <= gates["malformed_or_error_count"]["maximum_count"]
        ),
    }

    per_class_gate_results: dict[str, bool] = {}

    per_class_gates = thresholds[
        "per_resolved_source_class_recall_gates"
    ]

    for source_class, gate in per_class_gates.items():
        per_class_gate_results[source_class] = (
            class_correct_counts[source_class]
            >= gate["minimum_correct"]
        )

    accepted = (
        all(gate_results.values())
        and all(per_class_gate_results.values())
    )

    artifact = {
        "schema": "waypoint-source-boundary-classifier-score-v2",
        "status": (
            "ACCEPTANCE_PASS"
            if accepted
            else "ACCEPTANCE_FAIL"
        ),
        "source_artifacts": {
            "independent_contract_pack_v5_sha256": (
                EXPECTED_PACK_SHA256
            ),
            "acceptance_thresholds_v2_sha256": (
                EXPECTED_THRESHOLDS_SHA256
            ),
            "prediction_sha256": sha256(PREDICTIONS_PATH),
            "prediction_result_sha256": (
                sha256(PREDICTION_RESULT_PATH)
            ),
        },
        "metrics": metrics,
        "per_source_class_recall": per_class_recall,
        "contrast_results": contrast_results,
        "hard_gate_results": gate_results,
        "per_resolved_class_gate_results": (
            per_class_gate_results
        ),
        "all_gates_required": True,
        "acceptance_decision": (
            "PASS"
            if accepted
            else "FAIL"
        ),
        "case_results": case_results,
        "model_calls": 0,
        "authorisations": {
            "score_result_freeze_authorised": True,
            "classifier_rerun_authorised": False,
            "threshold_change_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("Waypoint source-boundary classifier score v2")
    print("=" * 63)
    print(f"Prediction SHA: {sha256(PREDICTIONS_PATH)}")
    print(f"Pack SHA: {sha256(PACK_PATH)}")
    print(f"Threshold SHA: {sha256(THRESHOLDS_PATH)}")
    print()
    print(
        "Four-field exact: "
        f"{four_correct}/40 ({percent(four_correct, 40)}%)"
    )
    print(
        "Resolution accuracy: "
        f"{resolution_correct}/40 ({percent(resolution_correct, 40)}%)"
    )
    print(
        "Source-domain accuracy: "
        f"{domain_correct}/40 ({percent(domain_correct, 40)}%)"
    )
    print(
        "Source-class accuracy: "
        f"{class_correct}/40 ({percent(class_correct, 40)}%)"
    )
    print(f"Source-class macro recall: {macro_recall}%")
    print(
        "Unresolved recall: "
        f"{unresolved_correct}/{unresolved_total} "
        f"({percent(unresolved_correct, unresolved_total)}%)"
    )
    print(
        "Resolved recall: "
        f"{resolved_correct}/{resolved_total} "
        f"({percent(resolved_correct, resolved_total)}%)"
    )
    print(
        "Contrast consistency: "
        f"{contrast_correct}/{len(groups)} "
        f"({percent(contrast_correct, len(groups))}%)"
    )
    print(f"Malformed/error count: {error_count}/40")
    print()
    print("Hard gates:")
    for key, passed in gate_results.items():
        print(f"  {key}: {'PASS' if passed else 'FAIL'}")
    print()
    print("Per resolved-class gates:")
    for key, passed in per_class_gate_results.items():
        print(f"  {key}: {'PASS' if passed else 'FAIL'}")
    print()
    print(
        "ACCEPTANCE DECISION: "
        f"{'PASS' if accepted else 'FAIL'}"
    )
    print(f"Output: {OUTPUT_PATH}")
    print(f"Score SHA256: {sha256(OUTPUT_PATH)}")
    print("Model calls: NONE")


if __name__ == "__main__":
    main()
