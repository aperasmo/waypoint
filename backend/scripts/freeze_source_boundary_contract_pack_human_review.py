"""Freeze human review of the source-boundary classifier contract test pack.

This records the review decision only. It does not modify the frozen
classifier design or test pack and does not authorise implementation.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_contract_pack_human_review.py
    uv run python -m scripts.freeze_source_boundary_contract_pack_human_review

Output:
    tests/source_boundary_contract_pack_human_review_v1.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

RUNTIME_PATH = (
    BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
)

BOUNDARY_PATH = (
    BACKEND_DIR
    / "tests"
    / "authoritative_source_boundary_spec_v1.json"
)

DESIGN_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v1.json"
)

TEST_PACK_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_contract_test_pack_v1.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_contract_pack_human_review_v1.json"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_BOUNDARY_SHA256 = (
    "2BFC518CFD892FE54AD9E46EAEE0037A9"
    "05730DDA934E3EEAEB1EBAD42C1458F"
)

EXPECTED_DESIGN_SHA256 = (
    "9443153C67A690EC24177BE61AA28CAB5"
    "E4794A90A171E44F3FAB4216A05F69F"
)

EXPECTED_TEST_PACK_SHA256 = (
    "71B982E71D533E8B3714BA1CC466C1A7"
    "D5A0CFBD0723220B153F6E2BCE39CF3F"
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
            "Refusing to freeze the human-review decision."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be a JSON object.")

    return payload


def test_map(pack: dict) -> dict[str, dict]:
    tests = pack.get("tests")

    if not isinstance(tests, list):
        raise RuntimeError("Contract test pack tests must be a list.")

    result = {}

    for item in tests:
        test_id = item.get("test_id")

        if not isinstance(test_id, str) or not test_id:
            raise RuntimeError("Contract test has invalid test_id.")

        if test_id in result:
            raise RuntimeError(f"Duplicate contract test_id: {test_id}")

        result[test_id] = item

    return result


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Human-review artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_sha(
        RUNTIME_PATH,
        EXPECTED_RUNTIME_SHA256,
        "Frozen production candidate-v2 runtime",
    )
    require_sha(
        BOUNDARY_PATH,
        EXPECTED_BOUNDARY_SHA256,
        "Frozen authoritative-source boundary",
    )
    require_sha(
        DESIGN_PATH,
        EXPECTED_DESIGN_SHA256,
        "Frozen source-boundary classifier design v1",
    )
    require_sha(
        TEST_PACK_PATH,
        EXPECTED_TEST_PACK_SHA256,
        "Frozen synthetic contract test pack v1",
    )

    boundary = load_json(BOUNDARY_PATH)
    design = load_json(DESIGN_PATH)
    pack = load_json(TEST_PACK_PATH)

    if boundary.get("schema") != (
        "waypoint-authoritative-source-boundary-spec-v1"
    ):
        raise RuntimeError("Unexpected source-boundary schema.")

    if design.get("schema") != (
        "waypoint-source-boundary-classifier-design-v1"
    ):
        raise RuntimeError("Unexpected classifier-design schema.")

    if pack.get("schema") != (
        "waypoint-source-boundary-classifier-contract-test-pack-v1"
    ):
        raise RuntimeError("Unexpected contract test-pack schema.")

    if pack.get("status") != (
        "FROZEN_SYNTHETIC_CONTRACT_TEST_PACK_NO_RUNTIME_CHANGE"
    ):
        raise RuntimeError("Unexpected contract test-pack status.")

    construction = pack.get("construction", {})

    expected_independence = {
        "retired_external_benchmark_questions_read": False,
        "gold_files_read": False,
        "prediction_files_read": False,
        "failure_taxonomy_read": False,
        "expected_sections_read": False,
        "model_generated": False,
    }

    for key, expected in expected_independence.items():
        if construction.get(key) is not expected:
            raise RuntimeError(
                f"Test-pack independence check changed: {key}"
            )

    if construction.get("test_count") != 32:
        raise RuntimeError("Unexpected synthetic test count.")

    if construction.get("resolved_count") != 29:
        raise RuntimeError("Unexpected resolved test count.")

    if construction.get("unresolved_count") != 3:
        raise RuntimeError("Unexpected unresolved test count.")

    tests = test_map(pack)

    required_ids = {
        "sb14",
        "sb15",
        "sb18",
        "sb19",
        "sb22",
        "sb23",
        "sb24",
        "sb25",
        "sb26",
        "sb27",
        "sb28",
    }

    missing = required_ids - set(tests)

    if missing:
        raise RuntimeError(
            f"Human-review target tests missing: {sorted(missing)}"
        )

    if tests["sb14"]["expected"]["source_class"] != (
        "inz_non_manual_procedure_or_interpretation"
    ):
        raise RuntimeError("sb14 expected class changed.")

    if tests["sb15"]["expected"]["source_class"] != (
        "inz_non_manual_procedure_or_interpretation"
    ):
        raise RuntimeError("sb15 expected class changed.")

    if tests["sb23"]["expected"]["source_class"] != (
        "professional_or_assessor_guidance"
    ):
        raise RuntimeError("sb23 expected class changed.")

    if tests["sb24"]["expected"]["source_class"] != (
        "other_official_external_authority"
    ):
        raise RuntimeError("sb24 expected class changed.")

    if tests["sb25"]["expected"]["source_class"] != (
        "other_official_external_authority"
    ):
        raise RuntimeError("sb25 expected class changed.")

    review = {
        "schema": "waypoint-source-boundary-contract-pack-human-review-v1",
        "status": "REVIEWED_REVISE_BEFORE_IMPLEMENTATION",
        "review_date": str(date.today()),
        "source_artifacts": {
            "production_runtime_sha256": EXPECTED_RUNTIME_SHA256,
            "source_boundary_sha256": EXPECTED_BOUNDARY_SHA256,
            "classifier_design_v1_sha256": EXPECTED_DESIGN_SHA256,
            "contract_test_pack_v1_sha256": EXPECTED_TEST_PACK_SHA256,
        },
        "review_scope": {
            "independence": True,
            "coverage": True,
            "source_class_discriminability": True,
            "ambiguity": True,
            "runtime_or_model_execution": False,
        },
        "positive_findings": [
            (
                "The pack is independent of the retired external evaluation "
                "sets according to its frozen construction metadata."
            ),
            (
                "All frozen source classes are represented, with 32 "
                "synthetic propositions, 29 resolved cases, 3 unresolved "
                "cases, and 9 contrast groups."
            ),
            (
                "The unresolved outcome is meaningfully exercised and is "
                "not treated as a generic catch-all."
            ),
            (
                "The transition cases correctly require trusted source "
                "context rather than inferring certified amendments from "
                "recency wording alone."
            ),
            (
                "The pack contains useful contrasts between immigration "
                "rules, current service information, current charges, "
                "external procedures, entitlements, and legal authority."
            ),
        ],
        "blocking_findings": [
            {
                "issue_id": "HR1",
                "severity": "blocking",
                "area": (
                    "inz_non_manual_procedure_or_interpretation"
                ),
                "affected_tests": ["sb14", "sb15"],
                "finding": (
                    "The expected non-Manual classification is not safely "
                    "derivable from proposition semantics alone. An INZ "
                    "administrative or form-handling procedure could be "
                    "stated in certified instructions or in a non-Manual "
                    "source. The classifier contract itself says the "
                    "non-Manual class applies when the material is maintained "
                    "outside certified instructions."
                ),
                "required_revision": (
                    "Require trusted source context identifying an IAC, "
                    "Advice to Staff, official form/guide, or other explicitly "
                    "non-Manual INZ source for this class. Without that "
                    "context, the classifier must return unresolved rather "
                    "than infer source location from procedural wording."
                ),
            },
            {
                "issue_id": "HR2",
                "severity": "blocking",
                "area": "external source-class overlap",
                "affected_tests": [
                    "sb18",
                    "sb19",
                    "sb22",
                    "sb23",
                ],
                "finding": (
                    "external_agency_assessment_or_service and "
                    "professional_or_assessor_guidance overlap in the frozen "
                    "v1 wording. The former includes assessment, recognition "
                    "and registration processes, while the latter also "
                    "includes assessor, professional and registration "
                    "guidance. A professional registration authority can "
                    "therefore satisfy both contracts."
                ),
                "required_revision": (
                    "Add explicit mutually exclusive scope rules. Reserve "
                    "professional_or_assessor_guidance for professional, "
                    "clinical, registration, provider or assessor authorities. "
                    "Reserve external_agency_assessment_or_service for "
                    "non-professional government/statutory agency assessment "
                    "or recognition services. Define precedence when an "
                    "authority could otherwise fit both."
                ),
            },
            {
                "issue_id": "HR3",
                "severity": "blocking",
                "area": "other_official_external_authority",
                "affected_tests": ["sb24", "sb25"],
                "finding": (
                    "The catch-all examples are not sufficiently exclusive. "
                    "The licensing/credential proposition in sb24 can fit the "
                    "more specific professional, registration or assessment "
                    "classes. The generic regulator proposition in sb25 can "
                    "also blur into a legal/regulatory requirement."
                ),
                "required_revision": (
                    "Replace these with clearly operational propositions "
                    "owned by identifiable official authorities that do not "
                    "fit foreign issuing, agency assessment, entitlement, "
                    "professional/assessor or legislation classes. Keep the "
                    "catch-all as a last-resort resolved class, not an "
                    "ambiguity sink."
                ),
            },
            {
                "issue_id": "HR4",
                "severity": "required_before_model_evaluation",
                "area": "scoring diagnostics",
                "affected_tests": [],
                "finding": (
                    "Four-field exact match is a valid strict case metric, "
                    "but overall exact-match alone could hide systematic "
                    "failure in a small source class or unresolved cases."
                ),
                "required_revision": (
                    "Before any classifier model is evaluated, freeze "
                    "additional reporting for source-domain accuracy, "
                    "source-class macro accuracy, per-class recall, "
                    "unresolved recall, and contrast-group consistency. "
                    "Do not change the expected labels after seeing model "
                    "outputs."
                ),
            },
        ],
        "review_decision": {
            "contract_test_pack_v1": "REVISE",
            "classifier_design_v1": "REVISE_FOR_DISAMBIGUATION",
            "classifier_implementation_design_authorised": False,
            "classifier_runtime_implementation_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": "source_boundary_classifier_design_v2",
            "authorised": True,
            "runtime_implementation_authorised": False,
            "requirements": [
                (
                    "Preserve the frozen top-level source domains and current "
                    "Waypoint v1 public evidence-status mapping."
                ),
                (
                    "Add explicit source-class precedence and exclusions for "
                    "external agency versus professional/assessor sources."
                ),
                (
                    "Require trusted source context for source-location-only "
                    "claims such as INZ non-Manual procedure/interpretation."
                ),
                (
                    "Clarify the last-resort other-official class so it cannot "
                    "absorb cases belonging to a more specific source class."
                ),
                (
                    "Keep unresolved as the mandatory result when ownership "
                    "cannot be established without guessing."
                ),
                (
                    "After design-v2 is frozen, build a new independent "
                    "contract test pack v2 before any classifier model call."
                ),
            ],
        },
        "immutability": {
            "classifier_design_v1_remains_frozen_history": True,
            "contract_test_pack_v1_remains_frozen_history": True,
            "do_not_overwrite_v1_artifacts": True,
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(review, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)

    if saved.get("review_decision", {}).get(
        "contract_test_pack_v1"
    ) != "REVISE":
        raise RuntimeError("Saved human-review decision changed.")

    if saved.get("review_decision", {}).get(
        "candidate_v7_build_authorised"
    ) is not False:
        raise RuntimeError(
            "Human review unexpectedly authorises candidate v7."
        )

    if saved.get("next_engineering_task", {}).get(
        "name"
    ) != "source_boundary_classifier_design_v2":
        raise RuntimeError("Unexpected human-review next task.")

    print("Waypoint source-boundary contract-pack human review freeze")
    print("=" * 59)
    print(f"Production v2 SHA256:      {sha256(RUNTIME_PATH)}")
    print(f"Boundary spec SHA256:      {sha256(BOUNDARY_PATH)}")
    print(f"Classifier design v1:      {sha256(DESIGN_PATH)}")
    print(f"Contract test pack v1:     {sha256(TEST_PACK_PATH)}")
    print()
    print("Independence:               PASS")
    print("Coverage:                   PASS")
    print("Ambiguity review:           REVISION REQUIRED")
    print()
    print("Blocking findings")
    print("-" * 59)
    print("HR1  INZ non-Manual source location needs trusted context")
    print("HR2  Agency vs professional/assessor classes overlap")
    print("HR3  Other-official examples are not mutually exclusive")
    print("HR4  Freeze class/macro/contrast diagnostics before model test")
    print()
    print("Contract test pack v1:      REVISE")
    print("Classifier design v1:       REVISE FOR DISAMBIGUATION")
    print("Classifier implementation:  NOT AUTHORISED")
    print("Candidate v7 build:         NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print("Fresh external-v3:          NOT AUTHORISED")
    print()
    print("Next task:                  CLASSIFIER DESIGN V2")
    print("Runtime implementation:     NOT AUTHORISED")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Human-review SHA256:        {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                NONE")
    print("Retrieval/reranker calls:   NONE")
    print("Database writes:            NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Contract-pack human review freeze: PASS")


if __name__ == "__main__":
    main()
