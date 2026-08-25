"""Human diagnostic review v2 for Waypoint source-boundary classifier.

REVIEW/FREEZE ONLY.
- No model calls.
- No classifier rerun.
- No threshold changes.
- No prompt or implementation changes.
- Reviews the frozen failure analysis and exact failed-case evidence.
- Authorises design-v4 specification construction only if the observed
  mechanisms justify generic, non-benchmark-specific revisions.

Run from backend/:
    uv run python -m py_compile scripts/review_source_boundary_classifier_human_diagnostic_v2.py
    uv run python -m scripts.review_source_boundary_classifier_human_diagnostic_v2

Output:
    tests/source_boundary_classifier_human_diagnostic_review_v2.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

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

PREDICTIONS_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_predictions_v2.json"
)

SCORE_RESULT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_score_result_v2.json"
)

FAILURE_ANALYSIS_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_failure_analysis_v2.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_human_diagnostic_review_v2.json"
)

EXPECTED_DESIGN_V3_SHA256 = (
    "0EFBA11ECA5EE07A41BBB841817B93CB4"
    "69BFA5B48BF42DF268B6A8F3257356B"
)

EXPECTED_PACK_V5_SHA256 = (
    "1B3CEA56504E3932C7DCA342DF99DC225"
    "23A4676B1C22714B9A122DDD566E67B"
)

EXPECTED_PREDICTION_SHA256 = (
    "7EE68C61443D73B298574A8EB2BBA4425"
    "A99D577F618B7565848F16FEA8C6EF1"
)

EXPECTED_SCORE_RESULT_SHA256 = (
    "5ABF0596DBCC0AAB6EDCA3F81403FBC25"
    "C98142608D0DEF036D07D026A786F9C"
)

EXPECTED_FAILURE_ANALYSIS_SHA256 = (
    "DA353315AB3EB4CB409064BD850B42893"
    "F6D59590077BA4550152EC463294F06"
)


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
            "Refusing human diagnostic review v2."
        )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{path.name}: root must be a JSON object."
        )

    return payload


def index_cases(
    items: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}

    for item in items:
        case_id = item.get("case_id")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Case missing valid case_id.")

        if case_id in result:
            raise RuntimeError(f"Duplicate case_id: {case_id}")

        result[case_id] = item

    return result


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Human diagnostic review already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    for path, expected, label in (
        (
            DESIGN_V3_PATH,
            EXPECTED_DESIGN_V3_SHA256,
            "Frozen classifier design v3",
        ),
        (
            PACK_V5_PATH,
            EXPECTED_PACK_V5_SHA256,
            "Frozen independent pack v5",
        ),
        (
            PREDICTIONS_PATH,
            EXPECTED_PREDICTION_SHA256,
            "Frozen first-run predictions v2",
        ),
        (
            SCORE_RESULT_PATH,
            EXPECTED_SCORE_RESULT_SHA256,
            "Frozen score-result v2",
        ),
        (
            FAILURE_ANALYSIS_PATH,
            EXPECTED_FAILURE_ANALYSIS_SHA256,
            "Frozen failure analysis v2",
        ),
    ):
        require_sha(path, expected, label)

    design = load_json(DESIGN_V3_PATH)
    pack = load_json(PACK_V5_PATH)
    predictions = load_json(PREDICTIONS_PATH)
    score_result = load_json(SCORE_RESULT_PATH)
    failure_analysis = load_json(FAILURE_ANALYSIS_PATH)

    if failure_analysis.get("schema") != (
        "waypoint-source-boundary-classifier-failure-analysis-v2"
    ):
        raise RuntimeError("Unexpected failure-analysis schema.")

    if failure_analysis.get("status") != (
        "FROZEN_DIAGNOSTIC_READY_FOR_HUMAN_REVIEW"
    ):
        raise RuntimeError(
            "Failure analysis is not frozen for human review."
        )

    if failure_analysis.get(
        "authorisations",
        {},
    ).get(
        "human_diagnostic_review_v2_authorised"
    ) is not True:
        raise RuntimeError(
            "Human diagnostic review v2 is not authorised."
        )

    if score_result.get("status") != (
        "FROZEN_FIRST_UNTOUCHED_ACCEPTANCE_FAIL"
    ):
        raise RuntimeError(
            "Score result is not the frozen first untouched failure."
        )

    pack_cases = pack.get("tests")
    prediction_cases = predictions.get("cases")

    if (
        not isinstance(pack_cases, list)
        or not isinstance(prediction_cases, list)
    ):
        raise RuntimeError("Frozen case evidence missing.")

    gold = index_cases(pack_cases)
    predicted = index_cases(prediction_cases)

    for required_case in ("iv4_026", "iv4_036"):
        if required_case not in gold or required_case not in predicted:
            raise RuntimeError(
                f"Required diagnostic case missing: {required_case}"
            )

    case_026 = gold["iv4_026"]
    case_036 = gold["iv4_036"]

    expected_026_proposition = (
        "Which verification service a public records agency provides to "
        "confirm the authenticity of a document already issued."
    )

    expected_036_proposition = (
        "Which official organisation controls an unspecified overseas "
        "clearance process."
    )

    if case_026.get("unsupported_proposition") != expected_026_proposition:
        raise RuntimeError("iv4_026 proposition changed.")

    if case_036.get("unsupported_proposition") != expected_036_proposition:
        raise RuntimeError("iv4_036 proposition changed.")

    if case_026["expected"]["source_class"] != (
        "external_agency_assessment_or_service"
    ):
        raise RuntimeError("iv4_026 gold class changed.")

    if predicted["iv4_026"]["source_class"] != (
        "foreign_issuing_authority_procedure"
    ):
        raise RuntimeError("iv4_026 prediction changed.")

    if case_036["expected"]["source_class"] != "unresolved":
        raise RuntimeError("iv4_036 gold class changed.")

    if predicted["iv4_036"]["source_class"] != (
        "other_official_external_authority"
    ):
        raise RuntimeError("iv4_036 prediction changed.")

    if case_036.get("trusted_source_context") is not None:
        raise RuntimeError(
            "iv4_036 unexpectedly has trusted source context."
        )

    # Review design-v3 intent: the generic external class is context-gated.
    design_text = json.dumps(
        design,
        sort_keys=True,
        ensure_ascii=False,
    )

    for required_fragment in (
        "other_official_external_authority",
        "other_official_operational_owner",
        "foreign_issuing_authority_procedure",
        "unresolved",
    ):
        if required_fragment not in design_text:
            raise RuntimeError(
                f"Design-v3 evidence missing: {required_fragment}"
            )

    cross = failure_analysis.get(
        "cross_failure_diagnosis",
        {},
    )

    if cross.get("primary_observed_failure") != (
        "CONTEXT_GATE_EXECUTION_ENFORCEMENT"
    ):
        raise RuntimeError(
            "Primary frozen diagnostic mechanism changed."
        )

    if cross.get("secondary_observed_failure") != (
        "FOREIGN_ISSUING_ROLE_BOUNDARY"
    ):
        raise RuntimeError(
            "Secondary frozen diagnostic mechanism changed."
        )

    if cross.get("threshold_problem_observed") is not False:
        raise RuntimeError(
            "Failure analysis unexpectedly identifies a threshold problem."
        )

    if cross.get("gold_pack_defect_observed") is not False:
        raise RuntimeError(
            "Failure analysis unexpectedly identifies a gold-pack defect."
        )

    if cross.get("retrieval_related") is not False:
        raise RuntimeError(
            "Failure analysis unexpectedly identifies retrieval as causal."
        )

    review = {
        "schema": (
            "waypoint-source-boundary-classifier-human-diagnostic-review-v2"
        ),
        "status": (
            "APPROVED_DESIGN_V4_CONSTRUCTION_ONLY"
        ),
        "reviewed_on": str(date.today()),
        "source_artifacts": {
            "classifier_design_v3_sha256": (
                EXPECTED_DESIGN_V3_SHA256
            ),
            "independent_contract_pack_v5_sha256": (
                EXPECTED_PACK_V5_SHA256
            ),
            "prediction_v2_sha256": (
                EXPECTED_PREDICTION_SHA256
            ),
            "score_result_v2_sha256": (
                EXPECTED_SCORE_RESULT_SHA256
            ),
            "failure_analysis_v2_sha256": (
                EXPECTED_FAILURE_ANALYSIS_SHA256
            ),
        },
        "acceptance_result_review": {
            "decision": "FAIL",
            "hard_gates_passed": 8,
            "hard_gates_failed": 1,
            "failed_gate": "unresolved_recall",
            "threshold_change_justified": False,
            "manual_override_justified": False,
            "rerun_without_revision_justified": False,
        },
        "case_reviews": {
            "iv4_026": {
                "decision": "DIAGNOSIS_CONFIRMED",
                "gold_class": (
                    "external_agency_assessment_or_service"
                ),
                "predicted_class": (
                    "foreign_issuing_authority_procedure"
                ),
                "mechanism": (
                    "FOREIGN_ISSUING_ROLE_SEMANTIC_OVERREACH"
                ),
                "gold_defect_observed": False,
                "reasoning": (
                    "The proposition establishes an authenticity-verification "
                    "service but does not establish that the public records "
                    "agency is the issuer of the relevant document or is "
                    "acting in that issuing role. Inferring issuer ownership "
                    "from verification alone is therefore too strong."
                ),
                "generic_revision_required": True,
                "revision_principle": (
                    "Verification qualifies for the foreign-issuing class only "
                    "when the proposition or trusted context establishes that "
                    "the authority is the issuer of the relevant record and is "
                    "acting in that issuing capacity. Verification alone must "
                    "not create an inferred issuing relationship."
                ),
            },
            "iv4_036": {
                "decision": "DIAGNOSIS_CONFIRMED",
                "gold_class": "unresolved",
                "predicted_class": (
                    "other_official_external_authority"
                ),
                "mechanism": (
                    "CONTEXT_GATE_NOT_DETERMINISTICALLY_ENFORCED"
                ),
                "gold_defect_observed": False,
                "reasoning": (
                    "The proposition leaves the overseas clearance role "
                    "unspecified and supplies no trusted context. Several "
                    "external authority roles remain plausible, so the "
                    "context-gated generic external class cannot be resolved."
                ),
                "generic_revision_required": True,
                "revision_principle": (
                    "Context-gated source classes must be validated "
                    "deterministically after the model proposes a class. "
                    "When required trusted context is absent or does not "
                    "match the frozen gate, the final classifier result must "
                    "be unresolved rather than the gated resolved class."
                ),
            },
        },
        "design_v4_scope": {
            "decision": "JUSTIFIED",
            "taxonomy_change_required": False,
            "source_class_count_change_required": False,
            "authority_mapping_change_required": False,
            "threshold_change_required": False,
            "gold_pack_change_required": False,
            "required_revisions": [
                {
                    "name": (
                        "DETERMINISTIC_CONTEXT_GATE_ENFORCEMENT"
                    ),
                    "scope": [
                        "manual_instruction_transition",
                        "inz_non_manual_procedure_or_interpretation",
                        "other_official_external_authority",
                    ],
                    "requirement": (
                        "Design v4 must distinguish the model's proposed "
                        "source class from the final validated source class, "
                        "or otherwise explicitly specify an equivalent "
                        "deterministic post-prediction gate. A proposal for a "
                        "context-gated class that lacks its required trusted "
                        "context must produce final source_class=unresolved. "
                        "This must be deterministic, auditable, and must not "
                        "require a second model call."
                    ),
                },
                {
                    "name": (
                        "FOREIGN_ISSUING_VERIFICATION_BOUNDARY"
                    ),
                    "scope": [
                        "foreign_issuing_authority_procedure",
                        "external_agency_assessment_or_service",
                    ],
                    "requirement": (
                        "Design v4 must state that verification of an already-"
                        "issued record belongs to the foreign-issuing class "
                        "only when issuer identity/role for that record is "
                        "established by proposition semantics or trusted "
                        "context. Verification service semantics alone are "
                        "insufficient to infer issuer status."
                    ),
                },
            ],
            "must_preserve": [
                "12 source classes",
                "existing deterministic domain/authority derivation",
                "semantic resolution without a universal context gate",
                "professional-assessor precedence",
                "current fee versus legal-basis distinction",
                "live INZ service versus certified instruction distinction",
                "conservative unresolved safety behaviour",
                "zero-shot classifier prompt",
                "one model call",
                "no retry",
                "no repair call",
                "no fallback model",
            ],
            "must_not_include": [
                "iv4_026 literal",
                "iv4_036 literal",
                "independent pack case IDs",
                "question-specific branches",
                "benchmark-answer mappings",
                "threshold-specific prediction logic",
            ],
        },
        "methodological_review": {
            "pack_v5_is_now_development_evidence": True,
            "pack_v5_may_be_used_for_debugging": True,
            "pack_v5_may_not_be_reused_as_fresh_acceptance": True,
            "same_prediction_set_may_not_be_rerun_for_acceptance": True,
            "fresh_independent_acceptance_pack_required_after_revision": True,
            "fresh_pack_must_be_constructed_after_design_v4_freeze": True,
            "fresh_pack_construction_must_not_copy_old_case_literals": True,
            "thresholds_must_be_frozen_before_new_predictions": True,
        },
        "authorisations": {
            "classifier_design_v4_construction_authorised": True,
            "design_v4_human_review_required_after_construction": True,
            "fresh_independent_acceptance_pack_construction_authorised": False,
            "classifier_prompt_change_authorised": False,
            "classifier_implementation_change_authorised": False,
            "classifier_model_run_authorised": False,
            "classifier_rerun_on_pack_v5_authorised": False,
            "threshold_change_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "external_retrieval_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": (
                "source_boundary_classifier_design_v4"
            ),
            "authorised": True,
            "model_calls": 0,
            "purpose": (
                "Construct and freeze a generic design-v4 specification that "
                "adds deterministic context-gate enforcement and narrows the "
                "foreign-issuing verification boundary without changing the "
                "12-class taxonomy or acceptance thresholds."
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
        "APPROVED_DESIGN_V4_CONSTRUCTION_ONLY"
    ):
        raise RuntimeError(
            "Saved human-review status changed."
        )

    auth = saved.get("authorisations", {})

    if auth.get(
        "classifier_design_v4_construction_authorised"
    ) is not True:
        raise RuntimeError(
            "Design-v4 construction was not authorised."
        )

    for forbidden in (
        "fresh_independent_acceptance_pack_construction_authorised",
        "classifier_prompt_change_authorised",
        "classifier_implementation_change_authorised",
        "classifier_model_run_authorised",
        "classifier_rerun_on_pack_v5_authorised",
        "threshold_change_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "external_retrieval_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if auth.get(forbidden) is not False:
            raise RuntimeError(
                f"Human review unexpectedly authorises {forbidden}."
            )

    print("Waypoint source-boundary classifier human diagnostic review v2")
    print("=" * 74)
    print(
        f"Design-v3 SHA256:           "
        f"{sha256(DESIGN_V3_PATH)}"
    )
    print(
        f"Pack-v5 SHA256:             "
        f"{sha256(PACK_V5_PATH)}"
    )
    print(
        f"Prediction SHA256:          "
        f"{sha256(PREDICTIONS_PATH)}"
    )
    print(
        f"Score-result SHA256:        "
        f"{sha256(SCORE_RESULT_PATH)}"
    )
    print(
        f"Failure-analysis SHA256:    "
        f"{sha256(FAILURE_ANALYSIS_PATH)}"
    )
    print()
    print("Diagnostic decisions")
    print("-" * 74)
    print("iv4_026 diagnosis:          CONFIRMED")
    print("  Mechanism:                FOREIGN_ISSUING_ROLE_SEMANTIC_OVERREACH")
    print("  Gold-pack defect:         NO")
    print()
    print("iv4_036 diagnosis:          CONFIRMED")
    print("  Mechanism:                CONTEXT_GATE_NOT_DETERMINISTICALLY_ENFORCED")
    print("  Gold-pack defect:         NO")
    print()
    print("Threshold change justified: NO")
    print("Manual override justified:  NO")
    print("Same-pack rerun justified:  NO")
    print()
    print("Design-v4 revision")
    print("-" * 74)
    print("Design-v4 construction:     AUTHORISED")
    print("Taxonomy change:            NO")
    print("Class-count change:         NO")
    print("Required change 1:          DETERMINISTIC CONTEXT-GATE ENFORCEMENT")
    print("Required change 2:          FOREIGN-ISSUING VERIFICATION BOUNDARY")
    print()
    print("Fresh acceptance pack:      REQUIRED AFTER DESIGN-V4 FREEZE")
    print("Pack-v5 future role:        DEVELOPMENT/DIAGNOSTIC ONLY")
    print()
    print("Prompt change:              NOT AUTHORISED")
    print("Implementation change:      NOT AUTHORISED")
    print("Model run:                  NOT AUTHORISED")
    print("Pack-v5 rerun:              NOT AUTHORISED")
    print("Threshold change:           NOT AUTHORISED")
    print("Candidate v7:               NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print()
    print("Next task:                  CLASSIFIER DESIGN V4")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(
        f"Human-review SHA256:        "
        f"{sha256(OUTPUT_PATH)}"
    )
    print()
    print("Model calls:                NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Human diagnostic review v2: PASS")


if __name__ == "__main__":
    main()
