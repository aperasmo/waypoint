"""Freeze human review of Waypoint source-boundary contract test pack v2.

The review approves classifier design v2 but requires a narrow metadata
revision to the synthetic contract pack before acceptance thresholds or any
classifier model prediction are authorised.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_contract_pack_human_review_v2.py
    uv run python -m scripts.freeze_source_boundary_contract_pack_human_review_v2

Output:
    tests/source_boundary_contract_pack_human_review_v2.json
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
PACK_V2_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_contract_test_pack_v2.json"
OUTPUT_PATH = BACKEND_DIR / "tests" / "source_boundary_contract_pack_human_review_v2.json"

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
EXPECTED_PACK_V2_SHA256 = (
    "500B6D9E2B3FA7F36C6163CF421D2D2C"
    "676808B696335343EBD85A32A0B70367"
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
            "Refusing to freeze human review v2."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be a JSON object.")
    return payload


def index_tests(pack: dict) -> dict[str, dict]:
    tests = pack.get("tests")
    if not isinstance(tests, list):
        raise RuntimeError("Contract test pack v2 tests must be a list.")
    indexed: dict[str, dict] = {}
    for item in tests:
        if not isinstance(item, dict):
            raise RuntimeError("Every contract test must be an object.")
        test_id = item.get("test_id")
        if not isinstance(test_id, str) or not test_id:
            raise RuntimeError("Invalid test_id in contract test pack.")
        if test_id in indexed:
            raise RuntimeError(f"Duplicate test_id: {test_id}")
        indexed[test_id] = item
    return indexed


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Human-review v2 artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_sha(RUNTIME_PATH, EXPECTED_RUNTIME_SHA256, "Frozen production candidate-v2 runtime")
    require_sha(BOUNDARY_PATH, EXPECTED_BOUNDARY_SHA256, "Frozen authoritative-source boundary")
    require_sha(DESIGN_V2_PATH, EXPECTED_DESIGN_V2_SHA256, "Frozen classifier design v2")
    require_sha(PACK_V2_PATH, EXPECTED_PACK_V2_SHA256, "Frozen contract test pack v2")

    design = load_json(DESIGN_V2_PATH)
    pack = load_json(PACK_V2_PATH)

    if design.get("schema") != "waypoint-source-boundary-classifier-design-v2":
        raise RuntimeError("Unexpected classifier design-v2 schema.")
    if design.get("status") != "FROZEN_DESIGN_ONLY_NO_RUNTIME_CHANGE":
        raise RuntimeError("Unexpected classifier design-v2 status.")
    if pack.get("schema") != "waypoint-source-boundary-classifier-contract-test-pack-v2":
        raise RuntimeError("Unexpected contract test-pack-v2 schema.")
    if pack.get("status") != "FROZEN_SYNTHETIC_CONTRACT_TEST_PACK_NO_MODEL_RUN":
        raise RuntimeError("Unexpected contract test-pack-v2 status.")

    construction = pack.get("construction", {})
    independence_checks = {
        "retired_external_benchmark_questions_read": False,
        "gold_files_read": False,
        "prediction_files_read": False,
        "failure_taxonomy_read": False,
        "contract_test_pack_v1_read": False,
        "model_generated": False,
    }
    for key, expected in independence_checks.items():
        if construction.get(key) is not expected:
            raise RuntimeError(f"Contract test-pack-v2 independence check changed: {key}")

    if construction.get("test_count") != 34:
        raise RuntimeError("Unexpected v2 synthetic test count.")
    if construction.get("resolved_count") != 28:
        raise RuntimeError("Unexpected v2 resolved test count.")
    if construction.get("unresolved_count") != 6:
        raise RuntimeError("Unexpected v2 unresolved test count.")

    tests = index_tests(pack)
    if len(tests) != 34:
        raise RuntimeError("Unexpected detailed v2 test count.")

    for test_id in ("sbv2_15", "sbv2_16"):
        item = tests.get(test_id)
        if item is None:
            raise RuntimeError(f"Missing human-review target: {test_id}")
        expected = item.get("expected", {})
        if expected.get("source_class") != "inz_non_manual_procedure_or_interpretation":
            raise RuntimeError(f"{test_id}: expected source class changed.")
        context = item.get("trusted_source_context")
        if not isinstance(context, dict):
            raise RuntimeError(f"{test_id}: expected trusted source context.")
        if context.get("publisher_family") != "immigration_new_zealand":
            raise RuntimeError(f"{test_id}: unexpected publisher family.")
        if context.get("publication_family") not in {"inz_iac", "inz_advice_to_staff"}:
            raise RuntimeError(f"{test_id}: expected explicit INZ non-Manual publication.")
        if context.get("authority_role") != "immigration_instruction_owner":
            raise RuntimeError(f"{test_id}: reviewed metadata signal has changed.")

    contracts = {
        item["source_class"]: item
        for item in design.get("source_class_contracts", [])
        if isinstance(item, dict) and isinstance(item.get("source_class"), str)
    }
    nonmanual_contract = contracts.get("inz_non_manual_procedure_or_interpretation")
    if not isinstance(nonmanual_contract, dict):
        raise RuntimeError("Design v2 missing INZ non-Manual source-class contract.")
    if nonmanual_contract.get("trusted_source_context_required") is not True:
        raise RuntimeError("Design v2 no longer requires trusted context for INZ non-Manual.")
    allowed_families = set(nonmanual_contract.get("required_publication_families_any_of", []))
    if allowed_families != {"inz_iac", "inz_advice_to_staff", "inz_form_or_guide"}:
        raise RuntimeError("Design-v2 non-Manual publication-family contract changed.")

    review = {
        "schema": "waypoint-source-boundary-contract-pack-human-review-v2",
        "status": "DESIGN_V2_APPROVED_PACK_V2_METADATA_REVISION_REQUIRED",
        "review_date": str(date.today()),
        "source_artifacts": {
            "production_runtime_sha256": EXPECTED_RUNTIME_SHA256,
            "source_boundary_sha256": EXPECTED_BOUNDARY_SHA256,
            "classifier_design_v2_sha256": EXPECTED_DESIGN_V2_SHA256,
            "contract_test_pack_v2_sha256": EXPECTED_PACK_V2_SHA256,
        },
        "review_scope": {
            "benchmark_independence": True,
            "source_class_coverage": True,
            "unresolved_coverage": True,
            "context_gating": True,
            "class_exclusivity": True,
            "contrast_groups": True,
            "trusted_context_semantics": True,
            "scoring_contract": True,
            "model_or_runtime_execution": False,
        },
        "positive_findings": [
            "The pack remains independent of retired external benchmark questions, gold files, predictions, failure taxonomies, and the v1 contract pack according to frozen construction metadata.",
            "The pack covers all 12 frozen source classes with 34 synthetic propositions, including 6 explicit unresolved cases.",
            "The design-v2 context gate for certified instruction transitions is exercised by both a resolved-with-context case and an unresolved-without-context case.",
            "The design-v2 INZ non-Manual source-location rule is structurally exercised with positive and negative cases.",
            "The agency-versus-professional distinction is now explicit and materially more discriminative than in v1.",
            "The other-official class is exercised as a context-gated last resort and is paired with an unresolved no-context counterexample.",
            "The scoring contract includes the additional diagnostics required by human-review finding HR4 before any model run.",
        ],
        "blocking_findings": [
            {
                "issue_id": "HRV2_1",
                "severity": "blocking_before_threshold_freeze",
                "area": "trusted_source_context_semantics",
                "affected_tests": ["sbv2_15", "sbv2_16"],
                "finding": (
                    "Both INZ non-Manual positive cases correctly identify their publication family as an IAC or Advice to Staff, "
                    "but also set authority_role to immigration_instruction_owner. That role semantically describes certified "
                    "instruction ownership and conflicts with the explicitly non-Manual publication family."
                ),
                "why_it_matters": (
                    "The classifier is intended to consume trusted source metadata. Supplying contradictory metadata would turn "
                    "these tests partly into conflict-resolution tests rather than clean source-boundary contract tests."
                ),
                "required_revision": (
                    "Remove authority_role from trusted_source_context for sbv2_15 and sbv2_16. Design v2 does not require that "
                    "field for INZ non-Manual classification; the explicit publication_family is sufficient. Do not change the "
                    "propositions, expected outputs, or source taxonomy."
                ),
            },
        ],
        "non_blocking_observations": [
            {
                "observation_id": "OBS_V2_1",
                "area": "contrast_group_naming",
                "finding": (
                    "The label clinical_assessor_vs_public_entitlement also contains an unresolved ambiguous-health-owner case. "
                    "This does not invalidate scoring because contrast groups are identified by membership rather than label "
                    "semantics, but a future replacement pack may use a more literal group name."
                ),
            },
        ],
        "review_decision": {
            "classifier_design_v2": "APPROVE",
            "contract_test_pack_v2": "REVISE_METADATA_ONLY",
            "expected_labels_change_authorised": False,
            "source_taxonomy_change_authorised": False,
            "acceptance_threshold_freeze_authorised": False,
            "classifier_model_prediction_authorised": False,
            "classifier_experimental_implementation_authorised": False,
            "classifier_runtime_implementation_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": "source_boundary_classifier_contract_test_pack_v3",
            "authorised": True,
            "runtime_implementation_authorised": False,
            "model_prediction_authorised": False,
            "requirements": [
                "Rebuild from frozen classifier design v2, not by overwriting contract test pack v2.",
                "Preserve all 34 proposition texts and expected outputs unless a separate human review explicitly identifies a substantive ambiguity.",
                "For the INZ non-Manual positive cases corresponding to v2 tests sbv2_15 and sbv2_16, retain publisher_family and publication_family but omit authority_role.",
                "Preserve the six unresolved expected cases and all context-gating logic.",
                "Preserve the frozen scoring metrics and no-retry rule.",
                "Human-review the replacement pack before freezing acceptance thresholds.",
            ],
        },
        "immutability": {
            "classifier_design_v2_remains_frozen": True,
            "contract_test_pack_v2_remains_frozen_history": True,
            "do_not_overwrite_prior_artifacts": True,
        },
    }

    OUTPUT_PATH.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    saved = load_json(OUTPUT_PATH)
    decision = saved.get("review_decision", {})
    if decision.get("classifier_design_v2") != "APPROVE":
        raise RuntimeError("Saved design-v2 review decision changed.")
    if decision.get("contract_test_pack_v2") != "REVISE_METADATA_ONLY":
        raise RuntimeError("Saved pack-v2 review decision changed.")

    for forbidden_authorisation in (
        "acceptance_threshold_freeze_authorised",
        "classifier_model_prediction_authorised",
        "classifier_experimental_implementation_authorised",
        "classifier_runtime_implementation_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if decision.get(forbidden_authorisation) is not False:
            raise RuntimeError(
                "Human review v2 unexpectedly authorises: "
                f"{forbidden_authorisation}"
            )

    if saved.get("next_engineering_task", {}).get("name") != "source_boundary_classifier_contract_test_pack_v3":
        raise RuntimeError("Unexpected human-review-v2 next task.")

    print("Waypoint source-boundary contract-pack human review v2 freeze")
    print("=" * 62)
    print(f"Production v2 SHA256:       {sha256(RUNTIME_PATH)}")
    print(f"Boundary spec SHA256:       {sha256(BOUNDARY_PATH)}")
    print(f"Classifier design-v2 SHA:   {sha256(DESIGN_V2_PATH)}")
    print(f"Contract test-pack-v2 SHA:  {sha256(PACK_V2_PATH)}")
    print()
    print("Benchmark independence:     PASS")
    print("Source-class coverage:      PASS")
    print("Unresolved coverage:        PASS")
    print("Context-gating structure:   PASS")
    print("Class exclusivity:          PASS")
    print("Scoring contract:           PASS")
    print()
    print("Remaining blocking issue")
    print("-" * 62)
    print("HRV2_1  sbv2_15/sbv2_16 contain contradictory")
    print("         authority_role metadata")
    print()
    print("Classifier design v2:       APPROVED")
    print("Contract test pack v2:      REVISE METADATA ONLY")
    print("Expected-label changes:     NOT AUTHORISED")
    print("Source-taxonomy changes:    NOT AUTHORISED")
    print()
    print("Acceptance thresholds:      NOT AUTHORISED YET")
    print("Classifier model prediction:NOT AUTHORISED")
    print("Classifier implementation:  NOT AUTHORISED")
    print("Candidate v7 build:         NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print("Fresh external-v3:          NOT AUTHORISED")
    print()
    print("Next task:                  CONTRACT TEST PACK V3")
    print("Revision scope:             METADATA ONLY")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Human-review-v2 SHA256:     {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                NONE")
    print("Retrieval/reranker calls:   NONE")
    print("Database writes:            NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Contract-pack human review v2 freeze: PASS")


if __name__ == "__main__":
    main()
