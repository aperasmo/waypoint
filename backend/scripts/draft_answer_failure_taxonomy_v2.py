"""Create a draft semantic failure taxonomy for candidate-v2 answer errors.

This script reads the immutable factual inventory produced by
build_answer_failure_inventory_v2.py and assigns DEVELOPMENT-ONLY semantic
mechanism labels to each of the 28 observed failures.

The taxonomy is intentionally outside runtime code. It is a human-review
artifact and MUST NOT be used as runtime input.

It does NOT:
- modify app/api/routes/ask.py;
- call the answer model;
- call retrieval, embeddings, or reranking;
- write to the database.

Run from backend/:
    uv run python -m py_compile scripts/draft_answer_failure_taxonomy_v2.py
    uv run python -m scripts.draft_answer_failure_taxonomy_v2

Input:
    tests/answer_failure_inventory_candidate_v2.json

Output:
    tests/answer_failure_taxonomy_candidate_v2_draft.json
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

INPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "answer_failure_inventory_candidate_v2.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "answer_failure_taxonomy_candidate_v2_draft.json"
)

EXPECTED_INVENTORY_SHA256 = (
    "CAFC74F7985B7F0222C79924281EC36D"
    "19B32278A57D7C72DD3DCC4214A7A53B"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

# This mapping is evaluation-analysis metadata only. It is never imported by
# runtime code. Each label describes a recurring mechanism rather than an
# immigration-specific answer rule.
ASSIGNMENTS = {
    # external v1
    "ext_ab8d1185fdfd0481": (
        "authoritative_home_resolution_failure",
        "external_regime_or_entitlement",
    ),
    "ext_66c81763e3cbd5cf": (
        "scope_entailment_overreach",
        "partial_process_treated_as_complete_rule",
    ),
    "ext_85192ee7adceec0c": (
        "scope_entailment_underreach",
        "supplied_general_structure_not_recognised_as_sufficient",
    ),
    "ext_71375d721d37bdde": (
        "authoritative_home_resolution_failure",
        "live_or_service_processing_information",
    ),
    "ext_0b69af212aa242f4": (
        "authoritative_home_resolution_failure",
        "external_fee_or_charge_schedule",
    ),
    "ext_588ee3ee0b20790d": (
        "scope_entailment_overreach",
        "qualification_rule_treated_as_complete_evidence_rule",
    ),

    # external v2
    "ext2_023fa6cd6621a24a": (
        "authoritative_home_resolution_failure",
        "external_issuing_authority_procedure",
    ),
    "ext2_b01b08c9e689cb55": (
        "authoritative_home_resolution_failure",
        "external_issuing_authority_procedure",
    ),
    "ext2_370bd814453c5733": (
        "authoritative_home_resolution_failure",
        "external_issuing_authority_procedure",
    ),
    "ext2_682333d9b9c172f4": (
        "scope_entailment_overreach",
        "adjacent_general_rule_used_for_category_specific_requirement",
    ),
    "ext2_d2f88ceae65b9b46": (
        "authoritative_home_resolution_failure",
        "external_agency_service_or_assessment_type",
    ),
    "ext2_67e067ccdae249ea": (
        "scope_entailment_overreach",
        "adjacent_general_rule_used_for_category_specific_requirement",
    ),
    "ext2_559a57944943aab5": (
        "scope_entailment_overreach",
        "related_status_rule_used_for_separate_application_consequence",
    ),
    "ext2_b4eaf7443c1ead5d": (
        "scope_entailment_overreach",
        "approval_rule_used_for_separate_temporary_status_consequence",
    ),
    "ext2_888971954ec7678a": (
        "scope_entailment_overreach",
        "different_visa_or_application_context_treated_as_same_rule",
    ),
    "ext2_4ff8da290ce9fb3e": (
        "scope_entailment_overreach",
        "relationship_criterion_present_but_evidence_rule_missing",
    ),
    "ext2_298d0e015f4e8ec2": (
        "authoritative_home_resolution_failure",
        "live_or_service_process_information",
    ),
    "ext2_1a4d4735dba2c2c1": (
        "authoritative_home_resolution_failure",
        "external_clinic_or_service_process",
    ),
    "ext2_25bac28c54e142ab": (
        "scope_entailment_overreach",
        "substantive_criterion_present_but_documentary_evidence_rule_missing",
    ),
    "ext2_7d2e80a946efbc21": (
        "scope_entailment_overreach",
        "negative_conclusion_inferred_from_non_exhaustive_silence",
    ),
    "ext2_90d50f9d92d085da": (
        "authoritative_home_resolution_failure",
        "external_professional_or_assessor_guideline",
    ),
    "ext2_cce51047e3ea8b52": (
        "authoritative_home_resolution_failure",
        "external_professional_or_assessor_guideline",
    ),
    "ext2_d8797e336a9cc692": (
        "scope_entailment_underreach",
        "general_rule_explicitly_covers_specific_case",
    ),
    "ext2_8c067aa632151edd": (
        "scope_entailment_underreach",
        "closed_or_exhaustive_exception_rule_underused",
    ),
    "ext2_6f3fabde7896acbe": (
        "scope_entailment_overreach",
        "negative_conclusion_inferred_from_non_exhaustive_silence",
    ),
    "ext2_ac14beba20a48211": (
        "authoritative_home_resolution_failure",
        "external_organisation_definition_or_entitlement",
    ),
    "ext2_139daec2a4cbe690": (
        "scope_entailment_underreach",
        "closed_character_rule_underused",
    ),
    "ext2_b9c0792e1eafc5b7": (
        "authoritative_home_resolution_failure",
        "missing_manual_rule_wrongly_externalised",
    ),
}

PRIMARY_DEFINITIONS = {
    "authoritative_home_resolution_failure": (
        "The model chose the wrong authoritative home for a material "
        "unsupported proposition, confusing missing Operational Manual policy "
        "with information maintained by an external authority, live service, "
        "professional guideline, issuing body, or other regime."
    ),
    "scope_entailment_overreach": (
        "The model treated related, adjacent, partial, differently scoped, or "
        "non-exhaustive supplied text as if it entailed the exact proposition "
        "needed to answer the question."
    ),
    "scope_entailment_underreach": (
        "The supplied rule was sufficient for the information need, but the "
        "model unnecessarily declared a corpus gap instead of applying the "
        "available general, closed, or exhaustive rule."
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{path.name}: JSON root must be an object."
        )

    return payload


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Draft taxonomy already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    if not INPUT_PATH.exists():
        raise SystemExit(
            f"Failure inventory not found: {INPUT_PATH}"
        )

    actual_inventory_sha = sha256(INPUT_PATH)

    if actual_inventory_sha != EXPECTED_INVENTORY_SHA256:
        raise SystemExit(
            "Failure inventory SHA mismatch.\n"
            f"Expected: {EXPECTED_INVENTORY_SHA256}\n"
            f"Actual:   {actual_inventory_sha}\n"
            "Refusing taxonomy generation."
        )

    inventory = load_json(INPUT_PATH)

    if inventory.get("schema") != (
        "waypoint-answer-failure-inventory-candidate-v2"
    ):
        raise RuntimeError(
            "Unexpected failure inventory schema."
        )

    if inventory.get("status") != "DEVELOPMENT_DIAGNOSTIC_ONLY":
        raise RuntimeError(
            "Failure inventory is not marked development-only."
        )

    if inventory.get("runtime_ask_sha256") != EXPECTED_RUNTIME_SHA256:
        raise RuntimeError(
            "Failure inventory runtime SHA is not candidate v2."
        )

    if inventory.get("failure_count") != 28:
        raise RuntimeError(
            f"Expected 28 failures, got {inventory.get('failure_count')}."
        )

    failures = inventory.get("failures")

    if not isinstance(failures, list):
        raise RuntimeError(
            "Failure inventory 'failures' must be a list."
        )

    inventory_ids = {
        item.get("case_id")
        for item in failures
    }

    assignment_ids = set(ASSIGNMENTS)

    if inventory_ids != assignment_ids:
        missing = sorted(inventory_ids - assignment_ids)
        extra = sorted(assignment_ids - inventory_ids)

        raise RuntimeError(
            "Taxonomy assignment case set does not match inventory.\n"
            f"Unassigned inventory cases: {missing}\n"
            f"Unknown assignment cases:   {extra}"
        )

    taxonomy_items = []
    primary_counts = Counter()
    secondary_counts = Counter()
    transition_by_primary = Counter()

    for item in failures:
        case_id = item["case_id"]
        primary, secondary = ASSIGNMENTS[case_id]

        primary_counts[primary] += 1
        secondary_counts[secondary] += 1
        transition_by_primary[
            f"{primary}|{item['transition']}"
        ] += 1

        taxonomy_items.append(
            {
                **item,
                "primary_mechanism": primary,
                "secondary_mechanism": secondary,
                "mechanism_definition": PRIMARY_DEFINITIONS[primary],
                "human_review_status": "PENDING",
            }
        )

    if sum(primary_counts.values()) != 28:
        raise RuntimeError(
            "Primary taxonomy count does not equal 28."
        )

    expected_primary_counts = {
        "authoritative_home_resolution_failure": 13,
        "scope_entailment_overreach": 11,
        "scope_entailment_underreach": 4,
    }

    if dict(primary_counts) != expected_primary_counts:
        raise RuntimeError(
            "Primary mechanism counts differ from expected draft."
        )

    output = {
        "schema": "waypoint-answer-failure-taxonomy-candidate-v2-draft",
        "status": "DRAFT_FOR_HUMAN_REVIEW_DO_NOT_TUNE",
        "candidate_name": "evidence_adequacy_v2",
        "source_inventory_sha256": EXPECTED_INVENTORY_SHA256,
        "runtime_ask_sha256": EXPECTED_RUNTIME_SHA256,
        "failure_count": 28,
        "primary_mechanism_definitions": PRIMARY_DEFINITIONS,
        "primary_mechanism_counts": dict(primary_counts),
        "secondary_mechanism_counts": dict(
            sorted(secondary_counts.items())
        ),
        "transition_by_primary_counts": dict(
            sorted(transition_by_primary.items())
        ),
        "root_family_summary": {
            "authoritative_home_resolution_failure": {
                "count": primary_counts[
                    "authoritative_home_resolution_failure"
                ],
                "share_of_failures_percent": 46.4,
            },
            "scope_entailment_overreach": {
                "count": primary_counts[
                    "scope_entailment_overreach"
                ],
                "share_of_failures_percent": 39.3,
            },
            "scope_entailment_underreach": {
                "count": primary_counts[
                    "scope_entailment_underreach"
                ],
                "share_of_failures_percent": 14.3,
            },
        },
        "methodology": [
            "This taxonomy is derived only from already-retired external v1 and v2 development failures.",
            "The taxonomy is diagnostic metadata and must never be imported by runtime code.",
            "Primary mechanisms describe recurring reasoning failures rather than immigration-specific answer rules.",
            "No prompt or runtime change should be made until the draft taxonomy is reviewed.",
            "Any future candidate informed by this taxonomy requires a new untouched external holdout before generalisation claims.",
        ],
        "items": taxonomy_items,
    }

    serialised = json.dumps(
        output,
        indent=2,
        ensure_ascii=False,
    ) + "\n"

    OUTPUT_PATH.write_text(
        serialised,
        encoding="utf-8",
    )

    verify = load_json(OUTPUT_PATH)

    if verify.get("failure_count") != 28:
        raise RuntimeError(
            "Saved taxonomy failure count verification failed."
        )

    if verify.get("primary_mechanism_counts") != expected_primary_counts:
        raise RuntimeError(
            "Saved primary mechanism counts verification failed."
        )

    print("Waypoint candidate-v2 draft failure taxonomy")
    print("=" * 45)
    print(f"Input inventory:            {INPUT_PATH}")
    print(f"Inventory SHA256:           {actual_inventory_sha}")
    print(f"Failures classified:        {len(taxonomy_items)}")
    print()
    print("Primary mechanisms:")
    for mechanism, count in primary_counts.items():
        share = 100.0 * count / len(taxonomy_items)
        print(f"  {mechanism:<40}{count:>3}  ({share:.1f}%)")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Draft taxonomy SHA256:      {sha256(OUTPUT_PATH)}")
    print()
    print("Human review status:        PENDING")
    print("Runtime files modified:     NONE")
    print("Runtime/model calls:        NONE")
    print("Retrieval/reranker calls:   NONE")
    print("Database writes:            NONE")
    print()
    print("Candidate-v2 draft failure taxonomy: PASS")


if __name__ == "__main__":
    main()
