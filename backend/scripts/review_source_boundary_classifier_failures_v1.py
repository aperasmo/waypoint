"""Print the exact frozen Waypoint classifier failures for human review.

READ-ONLY DIAGNOSTIC.
- No model calls.
- No writes.
- No threshold changes.
- No classifier changes.

Run from backend/:
    uv run python -m py_compile scripts/review_source_boundary_classifier_failures_v1.py
    uv run python -m scripts.review_source_boundary_classifier_failures_v1
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

ANALYSIS_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_failure_analysis_v1.json"
)

EXPECTED_ANALYSIS_SHA256 = (
    "A46BF63D831B61235679CA4858FE309E7"
    "496F7770EFFDC7D9E9468C0615CA1E0"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Failure-analysis root must be an object.")
    return payload


def require_analysis() -> dict[str, Any]:
    if not ANALYSIS_PATH.exists():
        raise SystemExit(
            f"Failure-analysis artifact not found: {ANALYSIS_PATH}"
        )

    actual = sha256(ANALYSIS_PATH)

    if actual != EXPECTED_ANALYSIS_SHA256:
        raise SystemExit(
            "Failure-analysis SHA mismatch.\n"
            f"Expected: {EXPECTED_ANALYSIS_SHA256}\n"
            f"Actual:   {actual}\n"
            "Refusing to review a changed diagnostic artifact."
        )

    payload = load_json(ANALYSIS_PATH)

    if payload.get("schema") != (
        "waypoint-source-boundary-classifier-failure-analysis-v1"
    ):
        raise RuntimeError("Unexpected failure-analysis schema.")

    if payload.get("status") != (
        "DIAGNOSTIC_COMPLETE_NO_CHANGES_AUTHORISED"
    ):
        raise RuntimeError("Unexpected failure-analysis status.")

    if payload.get(
        "authorisations",
        {},
    ).get("human_diagnostic_review_authorised") is not True:
        raise RuntimeError(
            "Human diagnostic review is not authorised."
        )

    return payload


def show_context(context: Any) -> str:
    if context is None:
        return "NONE"

    if isinstance(context, dict):
        parts = []
        for key in sorted(context):
            value = context[key]
            if value is not None:
                parts.append(f"{key}={value}")
        return "; ".join(parts) if parts else "NONE"

    return str(context)


def show_mapping(title: str, mapping: dict[str, Any]) -> None:
    print(title)
    for field in (
        "resolution_status",
        "source_domain",
        "source_class",
        "responsible_authority_type",
    ):
        print(f"  {field}: {mapping.get(field)}")


def main() -> None:
    analysis = require_analysis()

    failures = analysis.get("all_failures")
    errors = analysis.get("error_cases")
    non_errors = analysis.get("non_error_failures")
    failed_groups = analysis.get("failed_contrast_groups")

    if not isinstance(failures, list):
        raise RuntimeError("all_failures is missing.")
    if not isinstance(errors, list):
        raise RuntimeError("error_cases is missing.")
    if not isinstance(non_errors, list):
        raise RuntimeError("non_error_failures is missing.")
    if not isinstance(failed_groups, list):
        raise RuntimeError("failed_contrast_groups is missing.")

    if len(failures) != 8:
        raise RuntimeError(f"Expected 8 failures; found {len(failures)}.")
    if len(errors) != 2:
        raise RuntimeError(f"Expected 2 error cases; found {len(errors)}.")
    if len(non_errors) != 6:
        raise RuntimeError(
            f"Expected 6 non-error failures; found {len(non_errors)}."
        )
    if len(failed_groups) != 4:
        raise RuntimeError(
            f"Expected 4 failed contrast groups; found {len(failed_groups)}."
        )

    print("Waypoint source-boundary classifier human diagnostic review")
    print("=" * 68)
    print(f"Failure-analysis SHA256: {sha256(ANALYSIS_PATH)}")
    print()
    print("Frozen mechanism summary")
    print("-" * 68)

    summary = analysis.get("mechanism_summary", {})
    for key in (
        "over_abstention_resolved_to_unresolved",
        "under_abstention_unresolved_to_resolved",
        "wrong_source_domain",
        "wrong_source_class_within_correct_domain",
        "authority_type_only_mismatch",
        "multi_field_resolved_classification_mismatch",
        "execution_or_validation_error",
    ):
        print(f"{key}: {summary.get(key)}")

    print()
    print("Exact eight failures")
    print("=" * 68)

    for index, item in enumerate(failures, start=1):
        print()
        print(f"[{index}/8] {item.get('test_id')}")
        print("-" * 68)
        print(f"Failure type: {item.get('failure_type')}")
        print(
            "Contrast group: "
            f"{item.get('contrast_group') or 'NONE'}"
        )
        print(
            "Proposition: "
            f"{item.get('unsupported_proposition')}"
        )
        print(
            "Trusted context: "
            f"{show_context(item.get('trusted_source_context'))}"
        )
        print()

        gold = item.get("gold")
        if not isinstance(gold, dict):
            raise RuntimeError(
                f"{item.get('test_id')}: missing gold mapping."
            )

        show_mapping("Gold:", gold)

        if item.get("failure_type") == (
            "execution_or_validation_error"
        ):
            print("Prediction: ERROR")
            print(f"  error_type: {item.get('error_type')}")
            print(f"  error: {item.get('error')}")
        else:
            predicted = item.get("prediction")
            if not isinstance(predicted, dict):
                raise RuntimeError(
                    f"{item.get('test_id')}: missing prediction mapping."
                )

            show_mapping("Prediction:", predicted)
            print(
                "Changed fields: "
                + ", ".join(item.get("changed_fields", []))
            )
            print(
                "Model basis: "
                f"{item.get('model_basis')}"
            )

        print(
            "Gold basis: "
            f"{item.get('gold_basis')}"
        )

    print()
    print()
    print("Failed contrast groups")
    print("=" * 68)

    for index, group in enumerate(failed_groups, start=1):
        print()
        print(
            f"[{index}/4] {group.get('contrast_group')}"
        )
        print("-" * 68)
        print(
            "Members: "
            + ", ".join(group.get("members", []))
        )
        print(
            "Failed members: "
            + ", ".join(group.get("failed_members", []))
        )

        member_details = group.get("member_details", [])

        for member in member_details:
            print()
            print(
                f"  {member.get('test_id')} | "
                f"correct={member.get('four_field_correct')} | "
                f"status={member.get('prediction_status')}"
            )
            print(
                "    gold: "
                f"{member.get('gold_resolution_status')} | "
                f"{member.get('gold_source_domain')} | "
                f"{member.get('gold_source_class')}"
            )

            if member.get("prediction_status") == "prediction":
                print(
                    "    pred: "
                    f"{member.get('predicted_resolution_status')} | "
                    f"{member.get('predicted_source_domain')} | "
                    f"{member.get('predicted_source_class')}"
                )
            else:
                print(
                    "    error: "
                    f"{member.get('error_type')} | "
                    f"{member.get('error')}"
                )

    print()
    print()
    print("Review boundary")
    print("-" * 68)
    print("This output is diagnostic development evidence only.")
    print("Classifier changes:        NOT AUTHORISED")
    print("Threshold changes:         NOT AUTHORISED")
    print("Same-pack untouched rerun: NOT AUTHORISED")
    print("Candidate v7 build:        NOT AUTHORISED")
    print("Production change:         NOT AUTHORISED")
    print("Model calls:               NONE")
    print("Writes:                    NONE")
    print()
    print("Human diagnostic review output: COMPLETE")


if __name__ == "__main__":
    main()
