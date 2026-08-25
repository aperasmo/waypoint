"""Freeze Waypoint source-boundary classifier acceptance thresholds v1.

Thresholds are frozen before any classifier model prediction. This artifact
does not run a model, implement a classifier, modify runtime, or authorise
candidate v7.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_acceptance_thresholds.py
    uv run python -m scripts.freeze_source_boundary_classifier_acceptance_thresholds

Output:
    tests/source_boundary_classifier_acceptance_thresholds_v1.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

RUNTIME_PATH = BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
BOUNDARY_PATH = BACKEND_DIR / "tests" / "authoritative_source_boundary_spec_v1.json"
DESIGN_V2_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_design_v2.json"
PACK_V3_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_contract_test_pack_v3.json"
HUMAN_REVIEW_V3_PATH = BACKEND_DIR / "tests" / "source_boundary_contract_pack_human_review_v3.json"
OUTPUT_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_acceptance_thresholds_v1.json"

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)
EXPECTED_BOUNDARY_SHA256 = (
    "2BFC518CFD892FE54AD9E46EAEE0037A9"
    "05730DDA934E3EEAEB1EBAD42C1458F"
)
EXPECTED_DESIGN_V2_SHA256 = (
    "2A7D44B8948D66091F5E4F37E5C38284"
    "4C752452E31637AD2199CF0E9232C2F2"
)
EXPECTED_PACK_V3_SHA256 = (
    "C820489715EA3F54138023D680D04DFBF"
    "F5575A515B936FA8C2241E2EA5B219D"
)
EXPECTED_HUMAN_REVIEW_V3_SHA256 = (
    "308ACC0A7747F9D9EFD78594D49208C4"
    "30F252C1FBFA5B28DD66D4A60922BF17"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_sha(path: Path, expected: str, label: str) -> None:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")
    actual = sha256(path)
    if actual != expected:
        raise SystemExit(
            f"{label} SHA mismatch.\n"
            f"Path:     {path}\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Refusing to freeze acceptance thresholds."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be a JSON object.")
    return payload


def pct(numerator: int, denominator: int) -> float:
    return round((numerator / denominator) * 100.0, 1)


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Acceptance-threshold artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_sha(RUNTIME_PATH, EXPECTED_RUNTIME_SHA256, "Frozen production candidate-v2 runtime")
    require_sha(BOUNDARY_PATH, EXPECTED_BOUNDARY_SHA256, "Frozen authoritative-source boundary")
    require_sha(DESIGN_V2_PATH, EXPECTED_DESIGN_V2_SHA256, "Frozen classifier design v2")
    require_sha(PACK_V3_PATH, EXPECTED_PACK_V3_SHA256, "Frozen contract test pack v3")
    require_sha(HUMAN_REVIEW_V3_PATH, EXPECTED_HUMAN_REVIEW_V3_SHA256, "Frozen human review v3")

    design = load_json(DESIGN_V2_PATH)
    pack = load_json(PACK_V3_PATH)
    review = load_json(HUMAN_REVIEW_V3_PATH)

    if design.get("schema") != "waypoint-source-boundary-classifier-design-v2":
        raise RuntimeError("Unexpected classifier design-v2 schema.")
    if design.get("status") != "FROZEN_DESIGN_ONLY_NO_RUNTIME_CHANGE":
        raise RuntimeError("Unexpected classifier design-v2 status.")
    if pack.get("schema") != "waypoint-source-boundary-classifier-contract-test-pack-v3":
        raise RuntimeError("Unexpected contract test-pack-v3 schema.")
    if pack.get("status") != "FROZEN_SYNTHETIC_CONTRACT_TEST_PACK_READY_FOR_HUMAN_REVIEW":
        raise RuntimeError("Unexpected contract test-pack-v3 status.")
    if review.get("schema") != "waypoint-source-boundary-contract-pack-human-review-v3":
        raise RuntimeError("Unexpected human-review-v3 schema.")
    if review.get("status") != "APPROVED_READY_FOR_THRESHOLD_FREEZE":
        raise RuntimeError("Human review v3 is not ready for thresholds.")

    decision = review.get("review_decision", {})
    if decision.get("acceptance_threshold_freeze_authorised") is not True:
        raise RuntimeError("Human review v3 does not authorise threshold freezing.")
    if decision.get("classifier_model_prediction_authorised") is not False:
        raise RuntimeError("Human review v3 unexpectedly authorises model prediction.")

    construction = pack.get("construction", {})
    if construction.get("test_count") != 34:
        raise RuntimeError("Unexpected test count.")
    if construction.get("resolved_count") != 28:
        raise RuntimeError("Unexpected resolved count.")
    if construction.get("unresolved_count") != 6:
        raise RuntimeError("Unexpected unresolved count.")

    coverage = pack.get("coverage", {})
    class_counts = coverage.get("source_class_counts", {})
    contrast_groups = coverage.get("contrast_groups", {})

    if not isinstance(class_counts, dict) or len(class_counts) != 12:
        raise RuntimeError("Expected 12 source classes.")
    if not isinstance(contrast_groups, dict) or len(contrast_groups) != 11:
        raise RuntimeError("Expected 11 contrast groups.")

    scoring_contract = pack.get("scoring_contract", {})
    required_metrics = set(scoring_contract.get("required_secondary_metrics", []))
    expected_required_metrics = {
        "resolution_status_accuracy",
        "source_domain_accuracy",
        "source_class_accuracy",
        "source_class_macro_recall",
        "per_source_class_recall",
        "unresolved_recall",
        "resolved_recall",
        "contrast_group_full_consistency_rate",
        "malformed_or_error_rate",
    }
    if required_metrics != expected_required_metrics:
        raise RuntimeError("Contract test-pack-v3 required metrics changed.")
    if scoring_contract.get("acceptance_thresholds_frozen") is not False:
        raise RuntimeError("Pack v3 already claims thresholds are frozen.")
    if scoring_contract.get("model_prediction_authorised") is not False:
        raise RuntimeError("Pack v3 unexpectedly authorises model prediction.")

    hard_gates = {
        "four_field_exact_match_accuracy": {
            "minimum_correct": 30,
            "denominator": 34,
            "minimum_percent": pct(30, 34),
            "rationale": (
                "Primary contract metric. Allows at most four complete-case "
                "classification failures while requiring high end-to-end "
                "agreement across all four output fields."
            ),
        },
        "resolution_status_accuracy": {
            "minimum_correct": 32,
            "denominator": 34,
            "minimum_percent": pct(32, 34),
            "rationale": (
                "Resolved versus unresolved is a foundational safety boundary. "
                "At most two status errors are permitted."
            ),
        },
        "source_domain_accuracy": {
            "minimum_correct": 32,
            "denominator": 34,
            "minimum_percent": pct(32, 34),
            "rationale": (
                "The classifier must reliably separate Manual instructions, "
                "legislation, INZ non-Manual sources, external authorities, "
                "and unresolved ownership."
            ),
        },
        "source_class_accuracy": {
            "minimum_correct": 30,
            "denominator": 34,
            "minimum_percent": pct(30, 34),
            "rationale": (
                "Specific source class is the main classifier output and must "
                "remain close to the primary exact-match gate."
            ),
        },
        "source_class_macro_recall": {
            "minimum_percent": 85.0,
            "rationale": (
                "Prevents high-volume classes from masking systematic failure "
                "in smaller source classes."
            ),
        },
        "unresolved_recall": {
            "minimum_correct": 5,
            "denominator": 6,
            "minimum_percent": pct(5, 6),
            "rationale": (
                "The design uses unresolved to prevent forced authority guesses. "
                "At least five of six ambiguous cases must remain unresolved."
            ),
        },
        "resolved_recall": {
            "minimum_correct": 25,
            "denominator": 28,
            "minimum_percent": pct(25, 28),
            "rationale": (
                "Prevents excessive abstention. At least 25 of 28 resolvable "
                "contract cases must be resolved."
            ),
        },
        "contrast_group_full_consistency_rate": {
            "minimum_groups_correct": 9,
            "denominator": 11,
            "minimum_percent": pct(9, 11),
            "rationale": (
                "At least nine of eleven contrast groups must be completely "
                "correct so paired distinctions are not learned one-sidedly."
            ),
        },
        "malformed_or_error_rate": {
            "maximum_count": 0,
            "denominator": 34,
            "maximum_percent": 0.0,
            "rationale": (
                "The contract is small and structured. Malformed output or a "
                "classifier exception is not acceptable in the acceptance run."
            ),
        },
    }

    per_class_guard = {
        "required_reporting": True,
        "minimum_recall_percent_for_each_resolved_source_class": 50.0,
        "unresolved_class_uses_separate_hard_gate": True,
        "rationale": (
            "No resolved source class may collapse to zero recall. Individual "
            "classes are small, so a 50% floor is combined with the stronger "
            "macro-recall and overall accuracy gates rather than demanding "
            "perfection from every two-case class."
        ),
    }

    artifact = {
        "schema": "waypoint-source-boundary-classifier-acceptance-thresholds-v1",
        "status": "FROZEN_BEFORE_FIRST_CLASSIFIER_PREDICTION",
        "frozen_on": str(date.today()),
        "source_artifacts": {
            "production_runtime_sha256": EXPECTED_RUNTIME_SHA256,
            "source_boundary_sha256": EXPECTED_BOUNDARY_SHA256,
            "classifier_design_v2_sha256": EXPECTED_DESIGN_V2_SHA256,
            "contract_test_pack_v3_sha256": EXPECTED_PACK_V3_SHA256,
            "human_review_v3_sha256": EXPECTED_HUMAN_REVIEW_V3_SHA256,
        },
        "evaluation_set": {
            "type": "synthetic_contract_test_pack",
            "test_count": 34,
            "resolved_count": 28,
            "unresolved_count": 6,
            "source_class_count": 12,
            "contrast_group_count": 11,
            "purpose": (
                "Architecture-contract evaluation only. Passing this pack "
                "does not establish real-world generalisation."
            ),
        },
        "acceptance_logic": {
            "decision": "PASS only if every hard gate and the per-class floor passes.",
            "hard_gates": hard_gates,
            "per_class_guard": per_class_guard,
            "all_gates_required": True,
            "automatic_retry": False,
            "manual_override": False,
            "rounding_rule": (
                "Integer numerator gates control whenever a denominator is fixed. "
                "Display percentages are informational only."
            ),
        },
        "required_reporting": {
            "primary": "four_field_exact_match_accuracy",
            "metrics": [
                "four_field_exact_match_accuracy",
                "resolution_status_accuracy",
                "source_domain_accuracy",
                "source_class_accuracy",
                "source_class_macro_recall",
                "per_source_class_recall",
                "unresolved_recall",
                "resolved_recall",
                "contrast_group_full_consistency_rate",
                "malformed_or_error_rate",
            ],
            "confusions": [
                "resolution_status_confusion",
                "source_domain_confusion",
                "source_class_confusion",
            ],
            "case_level_output_required": True,
            "failed_contrast_groups_required": True,
            "per_class_counts_required": True,
        },
        "methodological_rules": [
            "Thresholds are frozen before the first classifier model prediction.",
            "The approved contract test pack v3 must not be changed after predictions are observed.",
            (
                "If the classifier fails, the prediction set becomes development evidence. "
                "Any revised design or prompt requires a newly versioned independent "
                "contract pack before another acceptance claim."
            ),
            "Do not lower thresholds after observing model output.",
            (
                "Do not add retries, repair logic, class-specific examples, or "
                "benchmark-derived routing after seeing failures and then re-score "
                "the same pack as if untouched."
            ),
            (
                "Passing this synthetic contract pack authorises only the next "
                "engineering review step. It does not by itself authorise production "
                "runtime integration."
            ),
            (
                "Real-world answer-layer generalisation still requires a future "
                "fresh external evaluation after any candidate is fully frozen."
            ),
        ],
        "post_threshold_authorisations": {
            "experimental_classifier_implementation_design_authorised": True,
            "classifier_model_prediction_authorised": False,
            "classifier_runtime_implementation_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "external_source_retrieval_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": "source_boundary_classifier_experimental_implementation_design_v1",
            "authorised": True,
            "model_prediction_authorised": False,
            "runtime_implementation_authorised": False,
            "purpose": (
                "Design an isolated experimental classifier implementation that "
                "consumes only unsupported_proposition plus permitted trusted_source_context, "
                "returns the frozen classifier-v2 schema, and can be scored against "
                "the approved contract pack without modifying production runtime."
            ),
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)
    if saved.get("status") != "FROZEN_BEFORE_FIRST_CLASSIFIER_PREDICTION":
        raise RuntimeError("Saved threshold artifact status changed.")

    gates = saved.get("acceptance_logic", {}).get("hard_gates", {})
    if gates.get("four_field_exact_match_accuracy", {}).get("minimum_correct") != 30:
        raise RuntimeError("Primary acceptance gate changed.")
    if gates.get("unresolved_recall", {}).get("minimum_correct") != 5:
        raise RuntimeError("Unresolved-recall gate changed.")
    if gates.get("resolved_recall", {}).get("minimum_correct") != 25:
        raise RuntimeError("Resolved-recall gate changed.")
    if gates.get("malformed_or_error_rate", {}).get("maximum_count") != 0:
        raise RuntimeError("Malformed/error gate changed.")

    auth = saved.get("post_threshold_authorisations", {})
    if auth.get("experimental_classifier_implementation_design_authorised") is not True:
        raise RuntimeError("Threshold freeze does not authorise implementation design.")

    for forbidden in (
        "classifier_model_prediction_authorised",
        "classifier_runtime_implementation_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "external_source_retrieval_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if auth.get(forbidden) is not False:
            raise RuntimeError(f"Threshold freeze unexpectedly authorises: {forbidden}")

    print("Waypoint source-boundary classifier acceptance-threshold freeze")
    print("=" * 65)
    print(f"Production v2 SHA256:        {sha256(RUNTIME_PATH)}")
    print(f"Boundary spec SHA256:        {sha256(BOUNDARY_PATH)}")
    print(f"Classifier design-v2 SHA:    {sha256(DESIGN_V2_PATH)}")
    print(f"Contract test-pack-v3 SHA:   {sha256(PACK_V3_PATH)}")
    print(f"Human-review-v3 SHA:         {sha256(HUMAN_REVIEW_V3_PATH)}")
    print()
    print("Thresholds frozen BEFORE first classifier prediction")
    print("-" * 65)
    print("4-field exact match:         >= 30/34 (88.2%)")
    print("Resolution-status accuracy:  >= 32/34 (94.1%)")
    print("Source-domain accuracy:      >= 32/34 (94.1%)")
    print("Source-class accuracy:       >= 30/34 (88.2%)")
    print("Source-class macro recall:   >= 85.0%")
    print("Unresolved recall:           >= 5/6  (83.3%)")
    print("Resolved recall:             >= 25/28 (89.3%)")
    print("Contrast consistency:        >= 9/11 (81.8%)")
    print("Malformed/error count:       0/34")
    print("Per resolved-class floor:    >= 50.0% recall")
    print()
    print("All gates required:          YES")
    print("Automatic retry:             NO")
    print("Manual override:             NO")
    print()
    print("Classifier model prediction: NOT AUTHORISED")
    print("Classifier implementation:   NOT AUTHORISED")
    print("Candidate v7 build:          NOT AUTHORISED")
    print("Production change:           NOT AUTHORISED")
    print("Fresh external-v3:           NOT AUTHORISED")
    print()
    print("Next task:                   EXPERIMENTAL CLASSIFIER DESIGN")
    print("Design only:                 AUTHORISED")
    print()
    print(f"Output:                      {OUTPUT_PATH}")
    print(f"Threshold SHA256:            {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                 NONE")
    print("Retrieval/reranker calls:    NONE")
    print("Database writes:             NONE")
    print("Runtime files modified:      NONE")
    print()
    print("Classifier acceptance-threshold freeze: PASS")


if __name__ == "__main__":
    main()
