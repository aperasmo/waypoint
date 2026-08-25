"""Build and freeze Waypoint source-boundary classifier contract test pack v3.

V3 is a metadata-only replacement for frozen contract test pack v2, authorised
by human review v2. It preserves every proposition and expected output.

The only test-level changes authorised are:
- remove trusted_source_context.authority_role from sbv2_15;
- remove trusted_source_context.authority_role from sbv2_16.

Run from backend/:
    uv run python -m py_compile scripts/build_source_boundary_classifier_contract_test_pack_v3.py
    uv run python -m scripts.build_source_boundary_classifier_contract_test_pack_v3

Output:
    tests/source_boundary_classifier_contract_test_pack_v3.json
"""

from __future__ import annotations

import copy
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

DESIGN_V2_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v2.json"
)

PACK_V2_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_contract_test_pack_v2.json"
)

HUMAN_REVIEW_V2_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_contract_pack_human_review_v2.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_contract_test_pack_v3.json"
)

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

EXPECTED_HUMAN_REVIEW_V2_SHA256 = (
    "99AA88D41EB769158A275356C558C77F7"
    "2935A02BA8D49BA21E77BED54B321C6"
)

ALLOWED_TEST_LEVEL_CHANGES = {
    "sbv2_15": "authority_role",
    "sbv2_16": "authority_role",
}


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
            "Refusing to build contract test pack v3."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be a JSON object.")

    return payload


def canonical(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def index_tests(pack: dict) -> dict[str, dict]:
    tests = pack.get("tests")

    if not isinstance(tests, list):
        raise RuntimeError("Contract pack tests must be a list.")

    indexed: dict[str, dict] = {}

    for item in tests:
        if not isinstance(item, dict):
            raise RuntimeError("Every contract test must be an object.")

        test_id = item.get("test_id")

        if not isinstance(test_id, str) or not test_id:
            raise RuntimeError("Every contract test requires a test_id.")

        if test_id in indexed:
            raise RuntimeError(f"Duplicate test_id: {test_id}")

        indexed[test_id] = item

    return indexed


def strip_authorised_metadata_change(
    item: dict,
    *,
    test_id: str,
) -> dict:
    cleaned = copy.deepcopy(item)

    if test_id in ALLOWED_TEST_LEVEL_CHANGES:
        context = cleaned.get("trusted_source_context")

        if not isinstance(context, dict):
            raise RuntimeError(
                f"{test_id}: expected trusted_source_context."
            )

        context.pop("authority_role", None)

    return cleaned


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Contract test pack v3 already exists: {OUTPUT_PATH}\n"
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
        DESIGN_V2_PATH,
        EXPECTED_DESIGN_V2_SHA256,
        "Frozen classifier design v2",
    )
    require_sha(
        PACK_V2_PATH,
        EXPECTED_PACK_V2_SHA256,
        "Frozen contract test pack v2",
    )
    require_sha(
        HUMAN_REVIEW_V2_PATH,
        EXPECTED_HUMAN_REVIEW_V2_SHA256,
        "Frozen human review v2",
    )

    design = load_json(DESIGN_V2_PATH)
    pack_v2 = load_json(PACK_V2_PATH)
    review = load_json(HUMAN_REVIEW_V2_PATH)

    if design.get("schema") != (
        "waypoint-source-boundary-classifier-design-v2"
    ):
        raise RuntimeError("Unexpected classifier design-v2 schema.")

    if design.get("status") != (
        "FROZEN_DESIGN_ONLY_NO_RUNTIME_CHANGE"
    ):
        raise RuntimeError("Unexpected classifier design-v2 status.")

    if pack_v2.get("schema") != (
        "waypoint-source-boundary-classifier-contract-test-pack-v2"
    ):
        raise RuntimeError("Unexpected contract test-pack-v2 schema.")

    if review.get("schema") != (
        "waypoint-source-boundary-contract-pack-human-review-v2"
    ):
        raise RuntimeError("Unexpected human-review-v2 schema.")

    if review.get("status") != (
        "DESIGN_V2_APPROVED_PACK_V2_METADATA_REVISION_REQUIRED"
    ):
        raise RuntimeError("Unexpected human-review-v2 status.")

    decision = review.get("review_decision", {})

    if decision.get("classifier_design_v2") != "APPROVE":
        raise RuntimeError("Classifier design v2 is not approved.")

    if decision.get("contract_test_pack_v2") != (
        "REVISE_METADATA_ONLY"
    ):
        raise RuntimeError(
            "Human review v2 did not authorise metadata-only replacement."
        )

    if decision.get("expected_labels_change_authorised") is not False:
        raise RuntimeError(
            "Expected-label changes are unexpectedly authorised."
        )

    if decision.get("source_taxonomy_change_authorised") is not False:
        raise RuntimeError(
            "Source-taxonomy changes are unexpectedly authorised."
        )

    if review.get("next_engineering_task", {}).get(
        "name"
    ) != "source_boundary_classifier_contract_test_pack_v3":
        raise RuntimeError("Unexpected human-review-v2 next task.")

    original_tests = index_tests(pack_v2)

    if len(original_tests) != 34:
        raise RuntimeError(
            f"Expected 34 frozen v2 tests, got {len(original_tests)}."
        )

    original_ids = [
        item["test_id"]
        for item in pack_v2.get("tests", [])
    ]

    expected_ids = [
        f"sbv2_{number:02d}"
        for number in range(1, 35)
    ]

    if original_ids != expected_ids:
        raise RuntimeError(
            "Frozen v2 test IDs/order changed unexpectedly."
        )

    # Validate the exact reviewed contradictory metadata before changing it.
    expected_nonmanual_publications = {
        "sbv2_15": "inz_iac",
        "sbv2_16": "inz_advice_to_staff",
    }

    for test_id, publication_family in (
        expected_nonmanual_publications.items()
    ):
        item = original_tests[test_id]
        context = item.get("trusted_source_context")

        if not isinstance(context, dict):
            raise RuntimeError(
                f"{test_id}: missing trusted source context."
            )

        if context.get("publisher_family") != (
            "immigration_new_zealand"
        ):
            raise RuntimeError(
                f"{test_id}: publisher_family changed."
            )

        if context.get("publication_family") != publication_family:
            raise RuntimeError(
                f"{test_id}: publication_family changed."
            )

        if context.get("authority_role") != (
            "immigration_instruction_owner"
        ):
            raise RuntimeError(
                f"{test_id}: reviewed authority_role signal changed."
            )

    pack_v3 = copy.deepcopy(pack_v2)

    # Apply only the authorised test-level metadata corrections.
    v3_tests = index_tests(pack_v3)

    for test_id in ALLOWED_TEST_LEVEL_CHANGES:
        context = v3_tests[test_id].get("trusted_source_context")

        if not isinstance(context, dict):
            raise RuntimeError(
                f"{test_id}: missing trusted source context in copy."
            )

        removed = context.pop("authority_role", None)

        if removed != "immigration_instruction_owner":
            raise RuntimeError(
                f"{test_id}: unexpected removed authority_role: {removed}"
            )

    # Update pack-level identity and provenance only.
    pack_v3["schema"] = (
        "waypoint-source-boundary-classifier-contract-test-pack-v3"
    )
    pack_v3["status"] = (
        "FROZEN_SYNTHETIC_CONTRACT_TEST_PACK_READY_FOR_HUMAN_REVIEW"
    )
    pack_v3["frozen_on"] = str(date.today())

    construction = pack_v3.setdefault("construction", {})
    construction["basis"] = (
        "Metadata-only replacement of frozen contract test pack v2, "
        "authorised by human review v2 and validated against frozen "
        "classifier design v2."
    )
    construction["classifier_design_v2_sha256"] = (
        EXPECTED_DESIGN_V2_SHA256
    )
    construction["contract_test_pack_v2_sha256"] = (
        EXPECTED_PACK_V2_SHA256
    )
    construction["human_review_v2_sha256"] = (
        EXPECTED_HUMAN_REVIEW_V2_SHA256
    )
    construction["contract_test_pack_v2_read"] = True
    construction["human_review_v2_read"] = True
    construction["metadata_only_revision"] = True
    construction["changed_test_ids"] = [
        "sbv2_15",
        "sbv2_16",
    ]
    construction["authorised_test_level_change"] = (
        "Removed trusted_source_context.authority_role only."
    )
    construction["proposition_texts_changed"] = False
    construction["expected_outputs_changed"] = False
    construction["contrast_groups_changed"] = False
    construction["source_taxonomy_changed"] = False
    construction["model_generated"] = False

    source_artifacts = pack_v3.setdefault(
        "source_artifacts",
        {},
    )
    source_artifacts["production_runtime_sha256"] = (
        EXPECTED_RUNTIME_SHA256
    )
    source_artifacts["source_boundary_sha256"] = (
        EXPECTED_BOUNDARY_SHA256
    )
    source_artifacts["classifier_design_v2_sha256"] = (
        EXPECTED_DESIGN_V2_SHA256
    )
    source_artifacts["contract_test_pack_v2_sha256"] = (
        EXPECTED_PACK_V2_SHA256
    )
    source_artifacts["human_review_v2_sha256"] = (
        EXPECTED_HUMAN_REVIEW_V2_SHA256
    )

    authorisations = pack_v3["authorisations"]
    authorisations["contract_test_pack_v3_frozen"] = True
    authorisations["human_review_v3_authorised"] = True
    authorisations["acceptance_threshold_freeze_authorised"] = False
    authorisations["classifier_model_prediction_authorised"] = False
    authorisations[
        "classifier_experimental_implementation_authorised"
    ] = False
    authorisations["classifier_runtime_implementation_authorised"] = False
    authorisations["candidate_v7_build_authorised"] = False
    authorisations["production_runtime_change_authorised"] = False
    authorisations["external_source_retrieval_authorised"] = False
    authorisations["fresh_external_v3_holdout_authorised"] = False

    # Remove superseded pack-level v2-only marker if present.
    authorisations.pop("contract_test_pack_v2_frozen", None)
    authorisations.pop("human_review_v2_authorised", None)

    pack_v3["next_step"] = {
        "name": "human_review_contract_test_pack_v3",
        "authorised": True,
        "purpose": (
            "Verify that the v3 pack differs from v2 only by the authorised "
            "trusted-source metadata correction and is ready for acceptance "
            "threshold freezing."
        ),
    }

    # ------------------------------------------------------------------
    # Strict substantive-equivalence checks.
    # ------------------------------------------------------------------
    final_tests = index_tests(pack_v3)

    if list(final_tests) != original_ids:
        raise RuntimeError(
            "V3 test IDs/order changed unexpectedly."
        )

    for test_id in original_ids:
        before = original_tests[test_id]
        after = final_tests[test_id]

        # Proposition text must be exactly preserved.
        if after.get("unsupported_proposition") != (
            before.get("unsupported_proposition")
        ):
            raise RuntimeError(
                f"{test_id}: proposition text changed."
            )

        # Expected output must be exactly preserved.
        if canonical(after.get("expected")) != canonical(
            before.get("expected")
        ):
            raise RuntimeError(
                f"{test_id}: expected output changed."
            )

        # Human-review basis must be preserved.
        if after.get("basis") != before.get("basis"):
            raise RuntimeError(
                f"{test_id}: basis text changed."
            )

        # Contrast grouping must be preserved.
        if after.get("contrast_group") != (
            before.get("contrast_group")
        ):
            raise RuntimeError(
                f"{test_id}: contrast group changed."
            )

        if test_id in ALLOWED_TEST_LEVEL_CHANGES:
            expected_after = strip_authorised_metadata_change(
                before,
                test_id=test_id,
            )

            if canonical(after) != canonical(expected_after):
                raise RuntimeError(
                    f"{test_id}: change exceeds authorised metadata removal."
                )
        else:
            if canonical(after) != canonical(before):
                raise RuntimeError(
                    f"{test_id}: unauthorised test-level change detected."
                )

    # Validate corrected source context.
    for test_id, publication_family in (
        expected_nonmanual_publications.items()
    ):
        context = final_tests[test_id].get(
            "trusted_source_context"
        )

        if not isinstance(context, dict):
            raise RuntimeError(
                f"{test_id}: corrected context missing."
            )

        if "authority_role" in context:
            raise RuntimeError(
                f"{test_id}: contradictory authority_role still present."
            )

        if context.get("publisher_family") != (
            "immigration_new_zealand"
        ):
            raise RuntimeError(
                f"{test_id}: publisher_family changed during correction."
            )

        if context.get("publication_family") != publication_family:
            raise RuntimeError(
                f"{test_id}: publication_family changed during correction."
            )

    # Construction-level counts must remain unchanged.
    if construction.get("test_count") != 34:
        raise RuntimeError("V3 test count changed.")
    if construction.get("resolved_count") != 28:
        raise RuntimeError("V3 resolved count changed.")
    if construction.get("unresolved_count") != 6:
        raise RuntimeError("V3 unresolved count changed.")

    # Scoring contract must remain substantively unchanged.
    if canonical(pack_v3.get("scoring_contract")) != canonical(
        pack_v2.get("scoring_contract")
    ):
        raise RuntimeError(
            "Scoring contract changed during metadata-only revision."
        )

    if pack_v3["scoring_contract"].get(
        "model_prediction_authorised"
    ) is not False:
        raise RuntimeError(
            "V3 scoring contract unexpectedly authorises model prediction."
        )

    if pack_v3["scoring_contract"].get(
        "acceptance_thresholds_frozen"
    ) is not False:
        raise RuntimeError(
            "V3 unexpectedly freezes acceptance thresholds."
        )

    OUTPUT_PATH.write_text(
        json.dumps(pack_v3, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)

    if saved.get("status") != (
        "FROZEN_SYNTHETIC_CONTRACT_TEST_PACK_READY_FOR_HUMAN_REVIEW"
    ):
        raise RuntimeError("Saved v3 pack status changed.")

    saved_tests = index_tests(saved)

    for test_id in ("sbv2_15", "sbv2_16"):
        context = saved_tests[test_id].get(
            "trusted_source_context",
            {},
        )

        if "authority_role" in context:
            raise RuntimeError(
                f"{test_id}: saved v3 still contains authority_role."
            )

    saved_auth = saved.get("authorisations", {})

    if saved_auth.get("human_review_v3_authorised") is not True:
        raise RuntimeError(
            "V3 pack does not authorise human review."
        )

    for forbidden_authorisation in (
        "acceptance_threshold_freeze_authorised",
        "classifier_model_prediction_authorised",
        "classifier_experimental_implementation_authorised",
        "classifier_runtime_implementation_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "external_source_retrieval_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if saved_auth.get(forbidden_authorisation) is not False:
            raise RuntimeError(
                "V3 pack unexpectedly authorises: "
                f"{forbidden_authorisation}"
            )

    print("Waypoint source-boundary classifier contract test-pack-v3 freeze")
    print("=" * 64)
    print(f"Production v2 SHA256:        {sha256(RUNTIME_PATH)}")
    print(f"Boundary spec SHA256:        {sha256(BOUNDARY_PATH)}")
    print(f"Classifier design-v2 SHA:    {sha256(DESIGN_V2_PATH)}")
    print(f"Contract test-pack-v2 SHA:   {sha256(PACK_V2_PATH)}")
    print(f"Human-review-v2 SHA:         {sha256(HUMAN_REVIEW_V2_PATH)}")
    print()
    print("Revision scope:              METADATA ONLY")
    print("Changed tests:               sbv2_15, sbv2_16")
    print("Removed field:               trusted_source_context.authority_role")
    print()
    print("Substantive equivalence")
    print("-" * 64)
    print("Proposition texts:           IDENTICAL 34/34")
    print("Expected outputs:            IDENTICAL 34/34")
    print("Basis text:                  IDENTICAL 34/34")
    print("Contrast groups:             IDENTICAL 34/34")
    print("Other test-level fields:     IDENTICAL 32/32")
    print("Scoring contract:            IDENTICAL")
    print()
    print("Synthetic tests:             34")
    print("Resolved expected:           28")
    print("Unresolved expected:         6")
    print()
    print("Classifier design v2:        UNCHANGED")
    print("Source taxonomy:             UNCHANGED")
    print("Expected labels:             UNCHANGED")
    print()
    print("Acceptance thresholds:       NOT YET FROZEN")
    print("Classifier model prediction: NOT AUTHORISED")
    print("Classifier implementation:   NOT AUTHORISED")
    print("Candidate v7 build:          NOT AUTHORISED")
    print("Production change:           NOT AUTHORISED")
    print("Fresh external-v3:           NOT AUTHORISED")
    print()
    print("Next step:                   HUMAN REVIEW OF V3 TEST PACK")
    print()
    print(f"Output:                      {OUTPUT_PATH}")
    print(f"Test-pack-v3 SHA256:         {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                 NONE")
    print("Retrieval/reranker calls:    NONE")
    print("Database writes:             NONE")
    print("Runtime files modified:      NONE")
    print()
    print("Source-boundary contract test-pack-v3 freeze: PASS")


if __name__ == "__main__":
    main()
