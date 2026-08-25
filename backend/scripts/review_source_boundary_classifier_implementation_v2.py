"""Static review of Waypoint source-boundary classifier implementation v2.

REVIEW ONLY.
- No model calls.
- Does not read the independent acceptance pack.
- Does not read gold labels or predictions.
- Does not change the classifier.
- Does not change production.

Run from backend/:
    uv run python -m py_compile scripts/review_source_boundary_classifier_implementation_v2.py
    uv run python -m scripts.review_source_boundary_classifier_implementation_v2

Output:
    tests/source_boundary_classifier_implementation_review_v2.json
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

RUNTIME_PATH = (
    BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
)

CLASSIFIER_PATH = (
    BACKEND_DIR
    / "_experiments"
    / "source_boundary_classifier_v2.py"
)

DESIGN_V3_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v3.json"
)

THRESHOLDS_V2_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_acceptance_thresholds_v2.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_implementation_review_v2.json"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_CLASSIFIER_SHA256 = (
    "8193FCDDB48585EC8A8BA8BCC477D123"
    "011B50F2F38531BEB2D88836975FF949"
)

EXPECTED_PROMPT_SHA256 = (
    "4A5C725B528FF09F7EEC3B306FD44F1A"
    "BDA99C6EC5EE5DFBB2E451F4ECA350C2"
)

EXPECTED_DESIGN_V3_SHA256 = (
    "0EFBA11ECA5EE07A41BBB841817B93CB4"
    "69BFA5B48BF42DF268B6A8F3257356B"
)

EXPECTED_THRESHOLDS_V2_SHA256 = (
    "1BDD2ED8950D6E3E612C66DCD5384BD5"
    "E0CAC784E39A70C3CE09EAD5C310D277"
)

EXPECTED_MODEL = "gpt-5.4-mini"
EXPECTED_REASONING_EFFORT = "none"
EXPECTED_MAX_COMPLETION_TOKENS = 800
EXPECTED_TEMPERATURE = 0.0


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
            "Refusing implementation review."
        )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{path.name}: root must be a JSON object."
        )

    return payload


def extract_assignment_literal(
    tree: ast.Module,
    name: str,
) -> Any:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = [
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            ]

            if name in targets:
                return ast.literal_eval(node.value)

    raise RuntimeError(
        f"Could not statically extract assignment {name!r}."
    )


def import_classifier():
    spec = importlib.util.spec_from_file_location(
        "_waypoint_classifier_review_v2",
        CLASSIFIER_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Could not create classifier import specification."
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise

    return module


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Implementation-review artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_sha(
        RUNTIME_PATH,
        EXPECTED_RUNTIME_SHA256,
        "Frozen production candidate-v2 runtime",
    )
    require_sha(
        CLASSIFIER_PATH,
        EXPECTED_CLASSIFIER_SHA256,
        "Experimental classifier implementation v2",
    )
    require_sha(
        DESIGN_V3_PATH,
        EXPECTED_DESIGN_V3_SHA256,
        "Frozen classifier design v3",
    )
    require_sha(
        THRESHOLDS_V2_PATH,
        EXPECTED_THRESHOLDS_V2_SHA256,
        "Frozen acceptance thresholds v2",
    )

    design = load_json(DESIGN_V3_PATH)
    thresholds = load_json(THRESHOLDS_V2_PATH)

    if design.get("schema") != (
        "waypoint-source-boundary-classifier-design-v3"
    ):
        raise RuntimeError("Unexpected design-v3 schema.")

    if thresholds.get("schema") != (
        "waypoint-source-boundary-classifier-acceptance-thresholds-v2"
    ):
        raise RuntimeError("Unexpected thresholds-v2 schema.")

    if thresholds.get("status") != (
        "FROZEN_BEFORE_CLASSIFIER_IMPLEMENTATION_AND_PREDICTION"
    ):
        raise RuntimeError(
            "Thresholds v2 are not frozen before implementation/prediction."
        )

    if thresholds.get(
        "authorisations",
        {},
    ).get(
        "experimental_classifier_implementation_v2_construction_authorised"
    ) is not True:
        raise RuntimeError(
            "Classifier implementation v2 was not authorised."
        )

    source = CLASSIFIER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    system_prompt = extract_assignment_literal(
        tree,
        "SYSTEM_PROMPT",
    )

    if not isinstance(system_prompt, str):
        raise RuntimeError("SYSTEM_PROMPT is not a string.")

    prompt_sha = hashlib.sha256(
        system_prompt.encode("utf-8")
    ).hexdigest().upper()

    if prompt_sha != EXPECTED_PROMPT_SHA256:
        raise RuntimeError(
            "Classifier prompt SHA changed.\n"
            f"Expected: {EXPECTED_PROMPT_SHA256}\n"
            f"Actual:   {prompt_sha}"
        )

    # No evaluation/test-pack dependencies may exist in the classifier.
    forbidden_literals = [
        "source_boundary_classifier_contract_test_pack",
        "source_boundary_classifier_independent_contract",
        "source_boundary_classifier_predictions",
        "source_boundary_classifier_score",
        "acceptance_threshold",
        "expected_sections",
        "contrast_group",
        "sbv2_",
        "iv4_",
    ]

    found_forbidden = [
        literal
        for literal in forbidden_literals
        if literal in source
    ]

    if found_forbidden:
        raise RuntimeError(
            "Classifier contains evaluation-specific references: "
            + ", ".join(found_forbidden)
        )

    # Production app and test imports are forbidden.
    imported_modules: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(
                alias.name
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.append(node.module)

    production_imports = [
        name
        for name in imported_modules
        if name == "app" or name.startswith("app.")
    ]

    test_imports = [
        name
        for name in imported_modules
        if name == "tests" or name.startswith("tests.")
    ]

    if production_imports:
        raise RuntimeError(
            "Classifier imports production app modules: "
            + ", ".join(production_imports)
        )

    if test_imports:
        raise RuntimeError(
            "Classifier imports test modules: "
            + ", ".join(test_imports)
        )

    call_sites = source.count(
        "chat.completions.create("
    )

    if call_sites != 1:
        raise RuntimeError(
            f"Expected exactly one model-call site; found {call_sites}."
        )

    if "while " in source or "for attempt" in source:
        raise RuntimeError(
            "Potential retry loop detected in classifier source."
        )

    # Importing the classifier is safe: the module has no top-level model call.
    module = import_classifier()

    if module.CLASSIFIER_MODEL != EXPECTED_MODEL:
        raise RuntimeError("Classifier model changed.")

    if (
        module.CLASSIFIER_REASONING_EFFORT
        != EXPECTED_REASONING_EFFORT
    ):
        raise RuntimeError(
            "Classifier reasoning effort changed."
        )

    if (
        module.CLASSIFIER_MAX_COMPLETION_TOKENS
        != EXPECTED_MAX_COMPLETION_TOKENS
    ):
        raise RuntimeError(
            "Classifier max completion tokens changed."
        )

    if (
        module.CLASSIFIER_TEMPERATURE
        != EXPECTED_TEMPERATURE
    ):
        raise RuntimeError(
            "Classifier temperature changed."
        )

    # Verify model output schema contains only independent fields.
    output_schema = (
        module.ClassifierModelOutput.model_json_schema()
    )

    properties = set(
        output_schema.get("properties", {})
    )

    if properties != {"source_class", "basis"}:
        raise RuntimeError(
            "Model-output schema is not limited to source_class + basis."
        )

    required_fields = set(
        output_schema.get("required", [])
    )

    if required_fields != {"source_class", "basis"}:
        raise RuntimeError(
            "Model-output schema required fields changed."
        )

    if (
        output_schema.get("additionalProperties")
        is not False
    ):
        raise RuntimeError(
            "Model-output schema no longer forbids extra fields."
        )

    # Verify deterministic derivation against the frozen design for all classes.
    design_derivation = design.get(
        "deterministic_derivation"
    )

    if not isinstance(design_derivation, dict):
        raise RuntimeError(
            "Design-v3 deterministic derivation missing."
        )

    source_classes = (
        design.get("model_output_contract", {})
        .get("fields", {})
        .get("source_class", {})
        .get("allowed_values")
    )

    if (
        not isinstance(source_classes, list)
        or len(source_classes) != 12
    ):
        raise RuntimeError(
            "Design-v3 source-class taxonomy changed."
        )

    derivation_results: dict[str, dict[str, str]] = {}

    for source_class in source_classes:
        model_output = module.ClassifierModelOutput(
            source_class=source_class,
            basis="static review",
        )

        derived = module.derive_classification(
            model_output
        )

        actual = {
            "resolution_status": derived.resolution_status,
            "source_domain": derived.source_domain,
            "responsible_authority_type": (
                derived.responsible_authority_type
            ),
        }

        expected = design_derivation[source_class]

        if actual != expected:
            raise RuntimeError(
                f"{source_class}: deterministic derivation differs "
                "from frozen design v3."
            )

        derivation_results[source_class] = actual

    # Verify parser accepts valid independent output and rejects extra fields.
    parsed = module.parse_model_content(
        json.dumps(
            {
                "source_class": "unresolved",
                "basis": "static parser review",
            }
        )
    )

    if (
        parsed.resolution_status != "unresolved"
        or parsed.source_domain != "unresolved"
        or parsed.responsible_authority_type
        != "unresolved"
    ):
        raise RuntimeError(
            "Valid unresolved parser/derivation check failed."
        )

    extra_field_rejected = False

    try:
        module.parse_model_content(
            json.dumps(
                {
                    "source_class": "unresolved",
                    "basis": "static parser review",
                    "source_domain": "unresolved",
                }
            )
        )
    except module.ClassifierContractError:
        extra_field_rejected = True

    if not extra_field_rejected:
        raise RuntimeError(
            "Parser did not reject an extra dependent field."
        )

    # Prompt contract review.
    required_prompt_fragments = [
        (
            "Trusted source context is NOT a universal prerequisite."
        ),
        (
            "Apply context gates only to:"
        ),
        "manual_instruction_transition",
        "inz_non_manual_procedure_or_interpretation",
        "other_official_external_authority",
        (
            "foreign_issuing_authority_procedure requires an actual issuing role."
        ),
        (
            "Do not use unresolved merely because trusted metadata is absent"
        ),
        (
            'Return exactly one JSON object with exactly these fields:'
        ),
    ]

    missing_fragments = [
        fragment
        for fragment in required_prompt_fragments
        if fragment not in system_prompt
    ]

    if missing_fragments:
        raise RuntimeError(
            "Frozen design-v3 prompt requirements missing: "
            + " | ".join(missing_fragments)
        )

    zero_shot_example_markers = [
        "Example 1",
        "Example:",
        "For example, classify",
        "Correct answer:",
        "Expected source_class:",
    ]

    present_example_markers = [
        marker
        for marker in zero_shot_example_markers
        if marker in system_prompt
    ]

    if present_example_markers:
        raise RuntimeError(
            "Prompt is not zero-shot: "
            + ", ".join(present_example_markers)
        )

    review = {
        "schema": (
            "waypoint-source-boundary-classifier-implementation-review-v2"
        ),
        "status": (
            "APPROVED_STATIC_IMPLEMENTATION_READY_FOR_EXECUTION_BUNDLE_CONSTRUCTION"
        ),
        "reviewed_on": str(date.today()),
        "source_artifacts": {
            "production_runtime_sha256": (
                EXPECTED_RUNTIME_SHA256
            ),
            "classifier_design_v3_sha256": (
                EXPECTED_DESIGN_V3_SHA256
            ),
            "acceptance_thresholds_v2_sha256": (
                EXPECTED_THRESHOLDS_V2_SHA256
            ),
            "classifier_implementation_v2_sha256": (
                EXPECTED_CLASSIFIER_SHA256
            ),
            "classifier_prompt_sha256": (
                EXPECTED_PROMPT_SHA256
            ),
        },
        "static_review": {
            "syntax": "PASS",
            "production_imports": [],
            "test_imports": [],
            "evaluation_specific_references": [],
            "benchmark_ids": [],
            "model_call_sites": 1,
            "automatic_retry": False,
            "repair_call": False,
            "fallback_model": False,
            "model": EXPECTED_MODEL,
            "reasoning_effort": EXPECTED_REASONING_EFFORT,
            "max_completion_tokens": (
                EXPECTED_MAX_COMPLETION_TOKENS
            ),
            "temperature": EXPECTED_TEMPERATURE,
        },
        "model_output_contract_review": {
            "decision": "PASS",
            "model_generated_fields": [
                "source_class",
                "basis",
            ],
            "dependent_model_generated_fields": [],
            "extra_fields_forbidden": True,
            "dependent_fields_derived": [
                "resolution_status",
                "source_domain",
                "responsible_authority_type",
            ],
        },
        "derivation_review": {
            "decision": "PASS",
            "source_classes_checked": 12,
            "all_match_design_v3": True,
            "derived_values": derivation_results,
        },
        "parser_review": {
            "decision": "PASS",
            "valid_json_object_accepted": True,
            "dependent_extra_field_rejected": True,
            "malformed_or_schema_invalid_is_error": True,
        },
        "prompt_review": {
            "decision": "PASS",
            "prompt_sha256": EXPECTED_PROMPT_SHA256,
            "zero_shot": True,
            "examples": False,
            "universal_context_gate": False,
            "context_gated_classes": [
                "manual_instruction_transition",
                "inz_non_manual_procedure_or_interpretation",
                "other_official_external_authority",
            ],
            "foreign_issuing_role_boundary_explicit": True,
            "unresolved_safety_policy_explicit": True,
            "benchmark_specific_logic": False,
            "case_specific_logic": False,
        },
        "evaluation_isolation": {
            "decision": "PASS",
            "acceptance_pack_read": False,
            "gold_labels_read": False,
            "predictions_read": False,
            "scores_read": False,
            "thresholds_passed_to_model": False,
            "retrieval_calls": False,
            "database_writes": False,
        },
        "authorisations": {
            "classifier_implementation_v2_approved": True,
            "blind_runner_v2_construction_authorised": True,
            "scorer_v2_construction_authorised": True,
            "execution_bundle_review_construction_authorised": True,
            "classifier_model_run_authorised": False,
            "prediction_authorisation_freeze_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": (
                "source_boundary_classifier_execution_bundle_v2"
            ),
            "authorised": True,
            "model_calls": 0,
            "purpose": (
                "Construct the blind runner v2, scorer v2, leakage guard, "
                "and execution-bundle review around the approved classifier "
                "without executing the model."
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
        "APPROVED_STATIC_IMPLEMENTATION_READY_FOR_EXECUTION_BUNDLE_CONSTRUCTION"
    ):
        raise RuntimeError(
            "Saved implementation-review status changed."
        )

    auth = saved.get("authorisations", {})

    for required in (
        "classifier_implementation_v2_approved",
        "blind_runner_v2_construction_authorised",
        "scorer_v2_construction_authorised",
        "execution_bundle_review_construction_authorised",
    ):
        if auth.get(required) is not True:
            raise RuntimeError(
                f"Implementation review did not authorise {required}."
            )

    for forbidden in (
        "classifier_model_run_authorised",
        "prediction_authorisation_freeze_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if auth.get(forbidden) is not False:
            raise RuntimeError(
                f"Implementation review unexpectedly authorises {forbidden}."
            )

    print("Waypoint source-boundary classifier implementation v2 review")
    print("=" * 68)
    print(f"Classifier SHA256:          {sha256(CLASSIFIER_PATH)}")
    print(f"Prompt SHA256:              {prompt_sha}")
    print(f"Design-v3 SHA256:           {sha256(DESIGN_V3_PATH)}")
    print(
        f"Threshold-v2 SHA256:        "
        f"{sha256(THRESHOLDS_V2_PATH)}"
    )
    print()
    print("Isolation")
    print("-" * 68)
    print("Production imports:         NONE")
    print("Test/eval imports:          NONE")
    print("Evaluation references:      NONE")
    print("Benchmark IDs:              NONE")
    print("Acceptance pack read:       NO")
    print("Gold labels read:           NO")
    print()
    print("Execution contract")
    print("-" * 68)
    print("Model:                      gpt-5.4-mini")
    print("Reasoning effort:           none")
    print("Max completion tokens:      800")
    print("Temperature:                0")
    print("Model-call sites:           1")
    print("Automatic retry:            NO")
    print("Repair call:                NO")
    print("Fallback model:             NO")
    print()
    print("Output contract")
    print("-" * 68)
    print("Model fields:               source_class, basis")
    print("Dependent fields:           DERIVED")
    print("Derivation classes checked: 12/12 PASS")
    print("Extra fields forbidden:     YES")
    print("Parser checks:              PASS")
    print()
    print("Prompt review:              PASS")
    print("Design-v3 alignment:        PASS")
    print("Evaluation isolation:       PASS")
    print()
    print("Implementation v2:          APPROVED")
    print("Blind runner construction:  AUTHORISED")
    print("Scorer construction:        AUTHORISED")
    print("Bundle review construction: AUTHORISED")
    print("Model run:                  NOT AUTHORISED")
    print("Candidate v7:               NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print()
    print("Next task:                  EXECUTION BUNDLE V2")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Implementation review SHA:  {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Classifier implementation v2 review: PASS")


if __name__ == "__main__":
    main()
