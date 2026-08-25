"""Freeze Waypoint experimental source-boundary classifier implementation design v1.

DESIGN ONLY. No model prediction or runtime implementation is authorised.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_experimental_design.py
    uv run python -m scripts.freeze_source_boundary_classifier_experimental_design

Output:
    tests/source_boundary_classifier_experimental_design_v1.json
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

RUNTIME_PATH = BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
BOUNDARY_PATH = BACKEND_DIR / "tests" / "authoritative_source_boundary_spec_v1.json"
DESIGN_V2_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_design_v2.json"
PACK_V3_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_contract_test_pack_v3.json"
HUMAN_REVIEW_V3_PATH = BACKEND_DIR / "tests" / "source_boundary_contract_pack_human_review_v3.json"
THRESHOLDS_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_acceptance_thresholds_v1.json"
OUTPUT_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_experimental_design_v1.json"

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
            "Refusing to freeze experimental classifier design."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be a JSON object.")
    return payload


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Experimental design artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_sha(RUNTIME_PATH, EXPECTED_RUNTIME_SHA256, "Frozen production candidate-v2 runtime")
    require_sha(BOUNDARY_PATH, EXPECTED_BOUNDARY_SHA256, "Frozen authoritative-source boundary")
    require_sha(DESIGN_V2_PATH, EXPECTED_DESIGN_V2_SHA256, "Frozen classifier design v2")
    require_sha(PACK_V3_PATH, EXPECTED_PACK_V3_SHA256, "Frozen contract test pack v3")
    require_sha(HUMAN_REVIEW_V3_PATH, EXPECTED_HUMAN_REVIEW_V3_SHA256, "Frozen human review v3")
    require_sha(THRESHOLDS_PATH, EXPECTED_THRESHOLDS_SHA256, "Frozen acceptance thresholds")

    classifier_design = load_json(DESIGN_V2_PATH)
    pack = load_json(PACK_V3_PATH)
    review = load_json(HUMAN_REVIEW_V3_PATH)
    thresholds = load_json(THRESHOLDS_PATH)

    if classifier_design.get("schema") != "waypoint-source-boundary-classifier-design-v2":
        raise RuntimeError("Unexpected classifier-design-v2 schema.")
    if classifier_design.get("status") != "FROZEN_DESIGN_ONLY_NO_RUNTIME_CHANGE":
        raise RuntimeError("Unexpected classifier-design-v2 status.")
    if pack.get("schema") != "waypoint-source-boundary-classifier-contract-test-pack-v3":
        raise RuntimeError("Unexpected contract-test-pack-v3 schema.")
    if review.get("status") != "APPROVED_READY_FOR_THRESHOLD_FREEZE":
        raise RuntimeError("Human review v3 is not approved.")
    if thresholds.get("schema") != "waypoint-source-boundary-classifier-acceptance-thresholds-v1":
        raise RuntimeError("Unexpected threshold schema.")
    if thresholds.get("status") != "FROZEN_BEFORE_FIRST_CLASSIFIER_PREDICTION":
        raise RuntimeError("Acceptance thresholds are not frozen.")

    threshold_auth = thresholds.get("post_threshold_authorisations", {})
    if threshold_auth.get("experimental_classifier_implementation_design_authorised") is not True:
        raise RuntimeError("Threshold freeze does not authorise experimental design.")
    if threshold_auth.get("classifier_model_prediction_authorised") is not False:
        raise RuntimeError("Threshold artifact unexpectedly authorises prediction.")

    design = {
        "schema": "waypoint-source-boundary-classifier-experimental-design-v1",
        "status": "FROZEN_DESIGN_ONLY_NO_MODEL_RUN",
        "frozen_on": str(date.today()),
        "purpose": (
            "Define an isolated, zero-shot experimental implementation of the frozen "
            "source-boundary classifier contract before any classifier model output is generated."
        ),
        "source_artifacts": {
            "production_runtime_sha256": EXPECTED_RUNTIME_SHA256,
            "source_boundary_sha256": EXPECTED_BOUNDARY_SHA256,
            "classifier_design_v2_sha256": EXPECTED_DESIGN_V2_SHA256,
            "contract_test_pack_v3_sha256": EXPECTED_PACK_V3_SHA256,
            "human_review_v3_sha256": EXPECTED_HUMAN_REVIEW_V3_SHA256,
            "acceptance_thresholds_v1_sha256": EXPECTED_THRESHOLDS_SHA256,
        },
        "isolation_boundary": {
            "production_app_modified": False,
            "production_import_required_by_classifier": False,
            "retrieval_used": False,
            "reranker_used": False,
            "embedding_used": False,
            "database_used": False,
            "web_search_used": False,
            "external_source_retrieval_used": False,
            "original_user_question_used": False,
            "retrieved_manual_chunks_used": False,
            "answer_generation_used": False,
            "classifier_reads_contract_pack": False,
            "classifier_reads_gold_or_expected_outputs": False,
            "classifier_reads_thresholds": False,
        },
        "planned_files": {
            "classifier_module": (
                "_experiments/source_boundary_classifier_v1.py"
            ),
            "blind_runner": (
                "scripts/run_source_boundary_classifier_contract_v1.py"
            ),
            "scorer": (
                "scripts/score_source_boundary_classifier_contract_v1.py"
            ),
            "leakage_guard": (
                "scripts/check_source_boundary_classifier_leakage.py"
            ),
            "prediction_output": (
                "tests/source_boundary_classifier_predictions_v1.json"
            ),
            "score_output": (
                "tests/source_boundary_classifier_score_v1.json"
            ),
        },
        "classifier_api": {
            "function": "classify_source_boundary",
            "inputs": {
                "unsupported_proposition": "string",
                "trusted_source_context": "object | null",
                "model": "string supplied by caller",
            },
            "outputs": {
                "resolution_status": ["resolved", "unresolved"],
                "source_domain": [
                    "certified_immigration_instructions",
                    "legislation_or_regulation",
                    "official_inz_non_manual",
                    "responsible_external_official_authority",
                    "unresolved",
                ],
                "source_class": [
                    "operational_manual_instruction",
                    "manual_instruction_transition",
                    "legislation_or_regulation",
                    "inz_live_service_information",
                    "current_fee_or_charge_information",
                    "inz_non_manual_procedure_or_interpretation",
                    "foreign_issuing_authority_procedure",
                    "external_agency_assessment_or_service",
                    "external_entitlement_or_service_regime",
                    "professional_or_assessor_guidance",
                    "other_official_external_authority",
                    "unresolved",
                ],
                "responsible_authority_type": [
                    "immigration_new_zealand",
                    "new_zealand_legislation",
                    "foreign_issuing_authority",
                    "new_zealand_external_agency",
                    "public_service_authority",
                    "professional_or_assessment_authority",
                    "other_official_authority",
                    "unresolved",
                ],
                "basis": "short non-answer explanation",
            },
        },
        "model_call_contract": {
            "calls_per_case": 1,
            "automatic_retry": False,
            "repair_call": False,
            "fallback_model": False,
            "temperature": 0,
            "model_selection": (
                "The blind runner supplies the project's configured answer_model value and records "
                "the resolved model identifier in the immutable prediction artifact."
            ),
            "reasoning_effort": (
                "Use the project's configured answer_reasoning_effort value; do not change it after "
                "seeing contract-pack results."
            ),
            "max_completion_tokens": (
                "Use a fixed classifier-specific limit frozen in the implementation artifact before "
                "the first prediction run."
            ),
            "response_format": "JSON object",
        },
        "prompt_contract": {
            "strategy": "zero_shot_generic_contract_only",
            "examples_in_prompt": False,
            "benchmark_examples_in_prompt": False,
            "visa_specific_examples_in_prompt": False,
            "manual_section_codes_in_prompt": False,
            "required_instructions": [
                "Do not answer the unsupported proposition.",
                "Classify the authoritative owner of the exact proposition, not the broad topic.",
                "Do not infer external authority from absence or silence.",
                "Do not infer an INZ non-Manual source from procedural wording without trusted source context.",
                "Use trusted certified-amendment context for manual_instruction_transition.",
                "Separate legal authority from certified immigration-instruction content.",
                "Separate current fee amount from the legal basis for imposing the charge.",
                "Professional, clinical, registration, and professional-assessment authorities take precedence over generic non-professional agency assessment.",
                "Use other_official_external_authority only with trusted official-owner context after excluding every more-specific class.",
                "When authoritative ownership cannot be established without guessing, return unresolved.",
                "Return only the frozen JSON schema.",
            ],
            "source_class_definitions": (
                "Derived from frozen classifier design v2 only. No contract-test proposition, "
                "expected label, benchmark question, failure note, or section-specific rule may be "
                "copied into the prompt."
            ),
        },
        "validation_contract": {
            "strict_schema_validation": True,
            "coercion": False,
            "repair": False,
            "retry": False,
            "inconsistent_combination": "error",
            "malformed_json": "error",
            "missing_required_field": "error",
            "extra_fields": "error",
            "basis_answers_proposition": (
                "record as contract violation/error if deterministic validation can establish it; "
                "otherwise retain basis only as diagnostic and do not use it for exact-match scoring."
            ),
            "invariants": [
                (
                    "resolution_status=unresolved requires source_domain, source_class, and "
                    "responsible_authority_type all equal unresolved."
                ),
                "resolution_status=resolved prohibits unresolved in the three categorical fields.",
                "manual_instruction_transition requires trusted certified-amendment context.",
                (
                    "inz_non_manual_procedure_or_interpretation requires trusted context identifying "
                    "an allowed INZ non-Manual publication family."
                ),
                (
                    "other_official_external_authority requires trusted context identifying an "
                    "other-official operational owner."
                ),
                (
                    "professional_or_assessor_guidance cannot be emitted with "
                    "responsible_authority_type=new_zealand_external_agency."
                ),
                (
                    "external_agency_assessment_or_service cannot be emitted with "
                    "responsible_authority_type=professional_or_assessment_authority."
                ),
            ],
        },
        "blind_runner_contract": {
            "reads": [
                "approved contract test pack v3",
                "project settings only for model configuration",
            ],
            "extracts_per_case": [
                "test_id for result correlation only",
                "unsupported_proposition",
                "trusted_source_context",
            ],
            "never_passed_to_classifier": [
                "test_id",
                "expected output",
                "basis",
                "contrast_group",
                "coverage metadata",
                "acceptance thresholds",
            ],
            "execution_order": "frozen test-pack order",
            "concurrency": "sequential",
            "expected_model_calls": 34,
            "error_handling": (
                "Catch each model/validation error, record the case as error, continue to the next "
                "case, and never retry."
            ),
            "prediction_artifact_immutability": (
                "Refuse to overwrite an existing prediction artifact."
            ),
        },
        "prediction_artifact_contract": {
            "must_record": [
                "schema version",
                "status indicating first untouched classifier contract run",
                "classifier implementation SHA256",
                "blind runner SHA256",
                "leakage guard SHA256",
                "classifier design-v2 SHA256",
                "contract test-pack-v3 SHA256",
                "threshold SHA256",
                "resolved model identifier",
                "model configuration",
                "prediction count",
                "model-call count",
                "per-case prediction or error",
            ],
            "must_not_record": [
                "expected outputs copied beside predictions before scoring",
                "gold labels inside classifier input payloads",
            ],
        },
        "scorer_contract": {
            "model_calls": 0,
            "reads": [
                "frozen prediction artifact",
                "approved contract test pack v3",
                "frozen threshold artifact",
            ],
            "reports": [
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
                "resolution_status_confusion",
                "source_domain_confusion",
                "source_class_confusion",
                "failed contrast groups",
                "case-level correctness",
            ],
            "acceptance_decision": (
                "PASS only if every frozen hard gate and per-resolved-class floor passes."
            ),
            "manual_override": False,
        },
        "leakage_guard_contract": {
            "scope": [
                "_experiments/source_boundary_classifier_v1.py",
                "scripts/run_source_boundary_classifier_contract_v1.py",
            ],
            "must_reject": [
                "retired external benchmark identifiers",
                "synthetic contract test identifiers embedded in classifier logic or prompt",
                "expected-output mappings",
                "gold-status mappings",
                "manual section-code literals",
                "visa-category-to-source lookup mappings",
                "nationality-specific routing",
                "occupation-specific routing",
                "question-string or phrase-specific routing",
                "imports of contract-pack or gold files from the classifier module",
            ],
            "allowed_runner_behaviour": (
                "The blind runner may read the approved contract pack solely to extract test_id, "
                "unsupported_proposition, and trusted_source_context. test_id is retained only for "
                "correlation and is never passed to the classifier."
            ),
        },
        "pre_prediction_freeze_requirements": [
            "Build the classifier module, blind runner, scorer, and leakage guard without executing the model.",
            "Syntax-check every file.",
            "Run the leakage guard with zero model calls.",
            "Human-review the exact zero-shot classifier prompt and validation invariants.",
            "Freeze SHA256 for classifier module, runner, scorer, and leakage guard.",
            "Freeze classifier-specific max_completion_tokens before the first model call.",
            "Verify production runtime SHA remains unchanged.",
            "Only then may a separate artifact authorise the single first contract prediction run.",
        ],
        "authorisations": {
            "experimental_classifier_code_build_authorised": True,
            "blind_runner_code_build_authorised": True,
            "scorer_code_build_authorised": True,
            "leakage_guard_code_build_authorised": True,
            "classifier_model_prediction_authorised": False,
            "classifier_contract_run_authorised": False,
            "classifier_runtime_implementation_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "external_source_retrieval_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": "build_source_boundary_classifier_experimental_bundle_v1",
            "authorised": True,
            "execution_authorised": False,
            "purpose": (
                "Build and review the isolated classifier module, blind runner, scorer, and leakage "
                "guard exactly to this frozen design, without making any classifier model call."
            ),
        },
    }

    serialised = json.dumps(design, indent=2, ensure_ascii=False) + "\n"

    benchmark_ids = re.findall(
        r"\bext2?_[0-9a-f]{16}\b",
        serialised,
        flags=re.IGNORECASE,
    )
    if benchmark_ids:
        raise RuntimeError(f"Benchmark identifiers found in design: {benchmark_ids}")

    manual_section_literals = re.findall(
        r'"((?:A|R|SR|U|V|WA|WD)\d+(?:\.\d+)*)"',
        serialised,
    )
    if manual_section_literals:
        raise RuntimeError(
            "Operational Manual section literals found in experimental design: "
            f"{sorted(set(manual_section_literals))}"
        )

    OUTPUT_PATH.write_text(serialised, encoding="utf-8")

    saved = load_json(OUTPUT_PATH)
    if saved.get("status") != "FROZEN_DESIGN_ONLY_NO_MODEL_RUN":
        raise RuntimeError("Saved experimental design status changed.")

    auth = saved.get("authorisations", {})
    for allowed in (
        "experimental_classifier_code_build_authorised",
        "blind_runner_code_build_authorised",
        "scorer_code_build_authorised",
        "leakage_guard_code_build_authorised",
    ):
        if auth.get(allowed) is not True:
            raise RuntimeError(f"Expected code-build authorisation missing: {allowed}")

    for forbidden in (
        "classifier_model_prediction_authorised",
        "classifier_contract_run_authorised",
        "classifier_runtime_implementation_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "external_source_retrieval_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if auth.get(forbidden) is not False:
            raise RuntimeError(f"Experimental design unexpectedly authorises: {forbidden}")

    print("Waypoint source-boundary experimental classifier design freeze")
    print("=" * 65)
    print(f"Production v2 SHA256:        {sha256(RUNTIME_PATH)}")
    print(f"Boundary spec SHA256:        {sha256(BOUNDARY_PATH)}")
    print(f"Classifier design-v2 SHA:    {sha256(DESIGN_V2_PATH)}")
    print(f"Contract test-pack-v3 SHA:   {sha256(PACK_V3_PATH)}")
    print(f"Threshold SHA256:            {sha256(THRESHOLDS_PATH)}")
    print()
    print("Architecture")
    print("-" * 65)
    print("Blind runner -> isolated classifier -> immutable predictions")
    print("Frozen predictions + gold pack + thresholds -> scorer")
    print()
    print("Classifier sees")
    print("-" * 65)
    print("unsupported_proposition")
    print("trusted_source_context")
    print("configured model identifier")
    print()
    print("Classifier never sees")
    print("-" * 65)
    print("test_id / expected output / contrast group")
    print("gold data / retired benchmark data")
    print("retrieved Manual chunks / original user question")
    print("thresholds")
    print()
    print("Prompt strategy:             ZERO-SHOT GENERIC CONTRACT")
    print("Examples in prompt:          NONE")
    print("Model calls per case:        1")
    print("Automatic retry:             NO")
    print("Repair call:                 NO")
    print("Fallback model:              NO")
    print("Expected first-run calls:    34")
    print("Execution order:             SEQUENTIAL")
    print()
    print("Code build:                  AUTHORISED")
    print("Classifier model prediction: NOT AUTHORISED")
    print("Contract run:                NOT AUTHORISED")
    print("Classifier runtime change:   NOT AUTHORISED")
    print("Candidate v7 build:          NOT AUTHORISED")
    print("Production change:           NOT AUTHORISED")
    print("Fresh external-v3:           NOT AUTHORISED")
    print()
    print("Next task:                   BUILD EXPERIMENTAL BUNDLE V1")
    print("Model execution:             NOT AUTHORISED")
    print()
    print(f"Output:                      {OUTPUT_PATH}")
    print(f"Experimental design SHA256:  {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                 NONE")
    print("Retrieval/reranker calls:    NONE")
    print("Database writes:             NONE")
    print("Runtime files modified:      NONE")
    print()
    print("Experimental classifier design freeze: PASS")


if __name__ == "__main__":
    main()
