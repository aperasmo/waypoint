"""Freeze and human-review Waypoint experimental source-boundary bundle v1.

This artifact freezes the exact experimental bundle SHAs and reviews the
classifier prompt and deterministic validation contract before any model run.

NO model calls are made.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_bundle_review_v1.py
    uv run python -m scripts.freeze_source_boundary_classifier_bundle_review_v1

Output:
    tests/source_boundary_classifier_bundle_review_v1.json
"""

from __future__ import annotations

import ast
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
THRESHOLDS_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_acceptance_thresholds_v1.json"
EXPERIMENTAL_DESIGN_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_experimental_design_v1.json"

CLASSIFIER_PATH = BACKEND_DIR / "_experiments" / "source_boundary_classifier_v1.py"
RUNNER_PATH = BACKEND_DIR / "scripts" / "run_source_boundary_classifier_contract_v1.py"
SCORER_PATH = BACKEND_DIR / "scripts" / "score_source_boundary_classifier_contract_v1.py"
LEAKAGE_GUARD_PATH = BACKEND_DIR / "scripts" / "check_source_boundary_classifier_leakage.py"

OUTPUT_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_bundle_review_v1.json"

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
EXPECTED_THRESHOLDS_SHA256 = (
    "5E8AFBFFEE5880DEBF4FA6B0A6514E8C"
    "6702F5D9E74D620BA4C1575F49CAC03C"
)
EXPECTED_EXPERIMENTAL_DESIGN_SHA256 = (
    "BC8F47CE6E7C60CC4133C22ACF592CFA"
    "89E9C409C923180017D9C4163A428BDF"
)

EXPECTED_CLASSIFIER_SHA256 = (
    "BC77C28033F74E3092C8428DE623293D"
    "266FBDEE7FFC237EE79C8AB6F79DE9F3"
)
EXPECTED_RUNNER_SHA256 = (
    "CE2709C654E576B56520AAD7CA9DB90A"
    "88E80CF775C3B8AC7A3864669F610FEF"
)
EXPECTED_SCORER_SHA256 = (
    "19563B4DD326CCB1E5DA125F30625915"
    "FB2BE197786640FA6223BFB44855FE46"
)
EXPECTED_LEAKAGE_GUARD_SHA256 = (
    "BAF1296A44B5C9E72C0E3C6E78D57EFB"
    "331677B03F9EED2E57BD4E18BA9D598E"
)

EXPECTED_REASONING_EFFORT = "none"
EXPECTED_MAX_COMPLETION_TOKENS = 800


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
            "Refusing to freeze bundle review."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be a JSON object.")
    return payload


def load_ast(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def extract_assignment_literal(
    tree: ast.AST,
    name: str,
):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise RuntimeError(f"Assignment not found: {name}")


def function_node(tree: ast.AST, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise RuntimeError(f"Function not found: {name}")


def count_call_sites(tree: ast.AST, dotted_suffix: str) -> int:
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        try:
            rendered = ast.unparse(node.func)
        except Exception:
            continue
        if rendered.endswith(dotted_suffix):
            count += 1
    return count


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Bundle-review artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_sha(RUNTIME_PATH, EXPECTED_RUNTIME_SHA256, "Production v2 runtime")
    require_sha(BOUNDARY_PATH, EXPECTED_BOUNDARY_SHA256, "Boundary spec")
    require_sha(DESIGN_V2_PATH, EXPECTED_DESIGN_V2_SHA256, "Classifier design v2")
    require_sha(PACK_V3_PATH, EXPECTED_PACK_V3_SHA256, "Contract pack v3")
    require_sha(HUMAN_REVIEW_V3_PATH, EXPECTED_HUMAN_REVIEW_V3_SHA256, "Human review v3")
    require_sha(THRESHOLDS_PATH, EXPECTED_THRESHOLDS_SHA256, "Acceptance thresholds")
    require_sha(EXPERIMENTAL_DESIGN_PATH, EXPECTED_EXPERIMENTAL_DESIGN_SHA256, "Experimental design v1")

    require_sha(CLASSIFIER_PATH, EXPECTED_CLASSIFIER_SHA256, "Classifier module")
    require_sha(RUNNER_PATH, EXPECTED_RUNNER_SHA256, "Blind runner")
    require_sha(SCORER_PATH, EXPECTED_SCORER_SHA256, "Scorer")
    require_sha(LEAKAGE_GUARD_PATH, EXPECTED_LEAKAGE_GUARD_SHA256, "Leakage guard")

    experimental_design = load_json(EXPERIMENTAL_DESIGN_PATH)
    thresholds = load_json(THRESHOLDS_PATH)

    if experimental_design.get("schema") != "waypoint-source-boundary-classifier-experimental-design-v1":
        raise RuntimeError("Unexpected experimental-design schema.")
    if experimental_design.get("status") != "FROZEN_DESIGN_ONLY_NO_MODEL_RUN":
        raise RuntimeError("Experimental design is not frozen.")
    if thresholds.get("status") != "FROZEN_BEFORE_FIRST_CLASSIFIER_PREDICTION":
        raise RuntimeError("Acceptance thresholds are not frozen.")

    design_auth = experimental_design.get("authorisations", {})
    if design_auth.get("classifier_model_prediction_authorised") is not False:
        raise RuntimeError("Experimental design unexpectedly authorises prediction.")

    classifier_tree = load_ast(CLASSIFIER_PATH)
    runner_tree = load_ast(RUNNER_PATH)
    scorer_tree = load_ast(SCORER_PATH)

    system_prompt = extract_assignment_literal(classifier_tree, "SYSTEM_PROMPT")
    reasoning_effort = extract_assignment_literal(
        classifier_tree,
        "CLASSIFIER_REASONING_EFFORT",
    )
    max_tokens = extract_assignment_literal(
        classifier_tree,
        "CLASSIFIER_MAX_COMPLETION_TOKENS",
    )

    if reasoning_effort != EXPECTED_REASONING_EFFORT:
        raise RuntimeError("Classifier reasoning effort changed.")
    if max_tokens != EXPECTED_MAX_COMPLETION_TOKENS:
        raise RuntimeError("Classifier max_completion_tokens changed.")

    required_prompt_fragments = [
        "Do not answer the proposition.",
        "Do not give immigration advice.",
        "Do not decide whether retrieved evidence is sufficient.",
        "Do not infer an external source merely because Manual evidence is absent.",
        "Classify the exact proposition.",
        "manual_instruction_transition",
        "legislation_or_regulation",
        "inz_live_service_information",
        "current_fee_or_charge_information",
        "inz_non_manual_procedure_or_interpretation",
        "foreign_issuing_authority_procedure",
        "professional_or_assessor_guidance",
        "external_agency_assessment_or_service",
        "external_entitlement_or_service_regime",
        "other_official_external_authority",
        "If authoritative ownership cannot be established without guessing, return unresolved.",
        "unresolved",
        "Return JSON only with exactly these fields:",
    ]

    # Compare required prompt semantics after normalising whitespace so
    # deliberate line wrapping in the frozen prompt cannot create a false
    # negative. This does not modify the classifier prompt.
    normalised_prompt = " ".join(system_prompt.split())

    missing_prompt_fragments = [
        fragment
        for fragment in required_prompt_fragments
        if " ".join(fragment.split()) not in normalised_prompt
    ]
    if missing_prompt_fragments:
        raise RuntimeError(
            "Classifier prompt is missing required frozen-contract fragments: "
            f"{missing_prompt_fragments}"
        )

    forbidden_prompt_fragments = [
        "sbv2_",
        "expected_sections",
        "gold_status",
        "failure_inventory",
        "failure_taxonomy",
        "ext1_",
        "ext2_",
    ]
    present_forbidden_prompt = [
        fragment
        for fragment in forbidden_prompt_fragments
        if fragment.casefold() in system_prompt.casefold()
    ]
    if present_forbidden_prompt:
        raise RuntimeError(
            "Classifier prompt contains forbidden evaluation fragments: "
            f"{present_forbidden_prompt}"
        )

    classifier_text = CLASSIFIER_PATH.read_text(encoding="utf-8")
    runner_text = RUNNER_PATH.read_text(encoding="utf-8")
    scorer_text = SCORER_PATH.read_text(encoding="utf-8")

    # Structural source marker: this is code syntax, not a runtime string.
    validation_source_requirements = {
        "strict_output_schema_extra_forbid": (
            'model_config = ConfigDict(extra="forbid")'
        ),
    }

    # Runtime validation messages are checked through the parsed AST rather
    # than raw source text. Python concatenates adjacent string literals, so
    # raw-text searching can produce false negatives when a message is
    # deliberately wrapped across source lines.
    validation_literal_requirements = {
        "unresolved_all_fields_invariant": (
            "Unresolved resolution requires all categorical fields "
            "to be unresolved."
        ),
        "resolved_prohibits_unresolved": (
            "Resolved resolution prohibits unresolved categorical fields."
        ),
        "transition_context_gate": (
            "manual_instruction_transition lacks the required certified "
            "amendment transition context."
        ),
        "inz_nonmanual_context_gate": (
            "INZ non-Manual classification lacks an allowed trusted "
            "publication family."
        ),
        "other_official_context_gate": (
            "other_official_external_authority lacks the required trusted "
            "official-owner context."
        ),
        "malformed_json_is_error": (
            "Classifier model returned malformed JSON."
        ),
        "schema_violation_is_error": (
            "Classifier model output violates the frozen schema."
        ),
    }

    missing_validation_source = [
        name
        for name, fragment in validation_source_requirements.items()
        if fragment not in classifier_text
    ]

    classifier_string_literals = [
        " ".join(node.value.split())
        for node in ast.walk(classifier_tree)
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
        )
    ]

    missing_validation_literals = [
        name
        for name, fragment in validation_literal_requirements.items()
        if " ".join(fragment.split()) not in classifier_string_literals
    ]

    missing_validation = (
        missing_validation_source
        + missing_validation_literals
    )

    if missing_validation:
        raise RuntimeError(
            "Classifier deterministic validation contract is incomplete: "
            f"{missing_validation}"
        )

    classifier_call_sites = count_call_sites(
        classifier_tree,
        "chat.completions.create",
    )
    if classifier_call_sites != 1:
        raise RuntimeError(
            f"Classifier must contain exactly one model call site; "
            f"found {classifier_call_sites}."
        )

    runner_classifier_calls = count_call_sites(
        runner_tree,
        "classify_source_boundary",
    )
    if runner_classifier_calls != 1:
        raise RuntimeError(
            f"Runner must contain exactly one classifier call site; "
            f"found {runner_classifier_calls}."
        )

    scorer_model_call_sites = (
        count_call_sites(scorer_tree, "chat.completions.create")
        + count_call_sites(scorer_tree, "responses.create")
    )
    if scorer_model_call_sites != 0:
        raise RuntimeError("Scorer contains a model call site.")

    required_runner_fragments = [
        "source_boundary_classifier_run_authorisation_v1.json",
        "Classifier contract run is NOT AUTHORISED.",
        "No model calls were made.",
        "single_run_only",
        "automatic_retry",
        "expected_case_count",
        "Refusing to overwrite the first-run prediction artifact.",
    ]
    missing_runner = [
        fragment for fragment in required_runner_fragments
        if fragment not in runner_text
    ]
    if missing_runner:
        raise RuntimeError(
            f"Runner safety contract incomplete: {missing_runner}"
        )

    required_scorer_fragments = [
        "all_gates_required",
        "automatic_retry",
        "manual_override",
        "four_field_exact_match_accuracy",
        "source_class_macro_recall",
        "unresolved_recall",
        "resolved_recall",
        "contrast_group_full_consistency_rate",
        "malformed_or_error_rate",
        "per_class_floor_failures",
        "ACCEPTANCE_PASS",
        "ACCEPTANCE_FAIL",
    ]
    missing_scorer = [
        fragment for fragment in required_scorer_fragments
        if fragment not in scorer_text
    ]
    if missing_scorer:
        raise RuntimeError(
            f"Scorer frozen-metric contract incomplete: {missing_scorer}"
        )

    prompt_sha256 = hashlib.sha256(
        system_prompt.encode("utf-8")
    ).hexdigest().upper()

    review = {
        "schema": "waypoint-source-boundary-classifier-bundle-review-v1",
        "status": "APPROVED_READY_FOR_SINGLE_RUN_AUTHORISATION_FREEZE",
        "review_date": str(date.today()),
        "source_artifacts": {
            "production_runtime_sha256": EXPECTED_RUNTIME_SHA256,
            "source_boundary_sha256": EXPECTED_BOUNDARY_SHA256,
            "classifier_design_v2_sha256": EXPECTED_DESIGN_V2_SHA256,
            "contract_test_pack_v3_sha256": EXPECTED_PACK_V3_SHA256,
            "human_review_v3_sha256": EXPECTED_HUMAN_REVIEW_V3_SHA256,
            "acceptance_thresholds_v1_sha256": EXPECTED_THRESHOLDS_SHA256,
            "experimental_design_v1_sha256": EXPECTED_EXPERIMENTAL_DESIGN_SHA256,
        },
        "bundle": {
            "classifier": {
                "path": "_experiments/source_boundary_classifier_v1.py",
                "sha256": EXPECTED_CLASSIFIER_SHA256,
            },
            "blind_runner": {
                "path": "scripts/run_source_boundary_classifier_contract_v1.py",
                "sha256": EXPECTED_RUNNER_SHA256,
            },
            "scorer": {
                "path": "scripts/score_source_boundary_classifier_contract_v1.py",
                "sha256": EXPECTED_SCORER_SHA256,
            },
            "leakage_guard": {
                "path": "scripts/check_source_boundary_classifier_leakage.py",
                "sha256": EXPECTED_LEAKAGE_GUARD_SHA256,
                "last_run_result": "PASS_REPORTED_BEFORE_FREEZE",
            },
        },
        "classifier_execution_contract": {
            "reasoning_effort": reasoning_effort,
            "max_completion_tokens": max_tokens,
            "temperature": 0,
            "response_format": "json_object",
            "model_calls_per_case": 1,
            "automatic_retry": False,
            "repair_call": False,
            "fallback_model": False,
            "expected_first_run_cases": 34,
            "execution_order": "sequential",
        },
        "prompt_review": {
            "decision": "APPROVE",
            "prompt_sha256": prompt_sha256,
            "zero_shot": True,
            "examples_present": False,
            "benchmark_specific_logic_present": False,
            "manual_section_literals_present": False,
            "answers_proposition": False,
            "classifies_exact_proposition": True,
            "unresolved_fallback_present": True,
            "trusted_context_gating_present": True,
            "professional_vs_agency_precedence_present": True,
            "current_fee_vs_legal_basis_distinction_present": True,
            "legal_authority_vs_instruction_content_distinction_present": True,
        },
        "validation_review": {
            "decision": "APPROVE",
            "strict_extra_fields_forbidden": True,
            "malformed_json_is_error": True,
            "schema_violation_is_error": True,
            "unresolved_consistency_invariant": True,
            "resolved_consistency_invariant": True,
            "source_class_domain_authority_mapping_enforced": True,
            "manual_transition_context_gate": True,
            "inz_nonmanual_context_gate": True,
            "other_official_context_gate": True,
            "coercion_or_repair": False,
        },
        "runner_review": {
            "decision": "APPROVE",
            "blind_case_fields_only": [
                "test_id for correlation only",
                "unsupported_proposition",
                "trusted_source_context",
            ],
            "test_id_passed_to_classifier": False,
            "gold_or_expected_passed_to_classifier": False,
            "thresholds_passed_to_classifier": False,
            "separate_run_authorisation_required": True,
            "prediction_artifact_overwrite_refused": True,
        },
        "scorer_review": {
            "decision": "APPROVE",
            "model_calls": 0,
            "uses_frozen_thresholds": True,
            "manual_override": False,
            "automatic_retry": False,
            "case_level_reporting": True,
        },
        "remaining_blockers_before_model_run": [
            "A separate single-run authorisation artifact has not yet been frozen.",
            "That artifact must bind the exact classifier, runner, contract-pack, threshold, model, reasoning-effort, token-limit, and case-count values.",
            "The runner must refuse execution if any bound value differs.",
        ],
        "review_decision": {
            "experimental_bundle_v1": "APPROVE",
            "prompt_contract": "APPROVE",
            "validation_contract": "APPROVE",
            "single_run_authorisation_freeze_authorised": True,
            "classifier_model_prediction_authorised": False,
            "classifier_contract_run_authorised": False,
            "classifier_runtime_implementation_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": "source_boundary_classifier_run_authorisation_v1",
            "authorised": True,
            "model_prediction_authorised": False,
            "purpose": (
                "Freeze a separate one-time run-authorisation artifact that "
                "binds the exact reviewed bundle and frozen evaluation inputs. "
                "Only that later artifact may authorise the first 34-call run."
            ),
        },
        "immutability": {
            "bundle_files_must_not_change_before_first_run": True,
            "contract_pack_must_not_change_before_first_run": True,
            "thresholds_must_not_change_before_first_run": True,
            "prompt_must_not_change_before_first_run": True,
            "do_not_overwrite_prior_artifacts": True,
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(review, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)
    if saved.get("status") != "APPROVED_READY_FOR_SINGLE_RUN_AUTHORISATION_FREEZE":
        raise RuntimeError("Saved bundle-review status changed.")

    decision = saved.get("review_decision", {})
    if decision.get("single_run_authorisation_freeze_authorised") is not True:
        raise RuntimeError("Single-run authorisation freeze was not authorised.")

    for forbidden in (
        "classifier_model_prediction_authorised",
        "classifier_contract_run_authorised",
        "classifier_runtime_implementation_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if decision.get(forbidden) is not False:
            raise RuntimeError(
                f"Bundle review unexpectedly authorises: {forbidden}"
            )

    print("Waypoint source-boundary experimental bundle review freeze")
    print("=" * 62)
    print(f"Classifier SHA256:          {sha256(CLASSIFIER_PATH)}")
    print(f"Runner SHA256:              {sha256(RUNNER_PATH)}")
    print(f"Scorer SHA256:              {sha256(SCORER_PATH)}")
    print(f"Leakage guard SHA256:       {sha256(LEAKAGE_GUARD_PATH)}")
    print()
    print("Prompt review:              APPROVED")
    print(f"Prompt SHA256:              {prompt_sha256}")
    print("Zero-shot examples:         NONE")
    print("Benchmark-specific logic:   NONE")
    print("Manual section literals:    NONE")
    print()
    print("Validation review:          APPROVED")
    print("Strict schema:              YES")
    print("Context-dependent gates:    VERIFIED")
    print("Malformed output:           ERROR")
    print("Repair/retry:               NONE")
    print()
    print("Runner review:              APPROVED")
    print("Scorer review:              APPROVED")
    print()
    print("Bundle v1:                  APPROVED")
    print("Run-authorisation freeze:   AUTHORISED")
    print("Classifier model prediction:NOT AUTHORISED")
    print("Contract run:               NOT AUTHORISED")
    print("Candidate v7 build:         NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print("Fresh external-v3:          NOT AUTHORISED")
    print()
    print("Next task:                  FREEZE SINGLE-RUN AUTHORISATION")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Bundle-review SHA256:       {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                NONE")
    print("Retrieval/reranker calls:   NONE")
    print("Database writes:            NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Experimental bundle review freeze: PASS")


if __name__ == "__main__":
    main()
