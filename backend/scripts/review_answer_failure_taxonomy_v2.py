"""Create a reviewed draft of the candidate-v2 failure taxonomy.

This script refines taxonomy metadata only. It preserves the three primary
mechanism families from the draft, normalises secondary labels, and adds
cross-cutting diagnostic flags.

This remains DEVELOPMENT / DIAGNOSTIC ONLY and MUST NOT be used as runtime
input or as a source of case-specific rules.

It does NOT:
- modify app/api/routes/ask.py;
- call the answer model;
- call retrieval, embeddings, or reranking;
- write to the database.

Run from backend/:
    uv run python -m py_compile scripts/review_answer_failure_taxonomy_v2.py
    uv run python -m scripts.review_answer_failure_taxonomy_v2

Input:
    tests/answer_failure_taxonomy_candidate_v2_draft.json

Output:
    tests/answer_failure_taxonomy_candidate_v2_reviewed_draft.json
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
    / "answer_failure_taxonomy_candidate_v2_draft.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "answer_failure_taxonomy_candidate_v2_reviewed_draft.json"
)

RUNTIME_PATH = (
    BACKEND_DIR
    / "app"
    / "api"
    / "routes"
    / "ask.py"
)

EXPECTED_DRAFT_SHA256 = (
    "80BFA248D3DA26A46C91F4F14B7B48E4"
    "4DC7320D7E7974905B170A61F9F01082"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

NORMALISED_SECONDARY = {
    "ext_ab8d1185fdfd0481":
        "external_entitlement_or_organisation_definition",
    "ext_66c81763e3cbd5cf":
        "partial_process_treated_as_complete_rule",
    "ext_85192ee7adceec0c":
        "compositional_sufficiency_underused",
    "ext_71375d721d37bdde":
        "external_live_or_service_information",
    "ext_0b69af212aa242f4":
        "external_fee_or_charge_schedule",
    "ext_588ee3ee0b20790d":
        "criterion_or_general_evidence_rule_used_for_specific_requirement",

    "ext2_023fa6cd6621a24a":
        "external_issuing_authority_procedure",
    "ext2_b01b08c9e689cb55":
        "external_issuing_authority_procedure",
    "ext2_370bd814453c5733":
        "external_issuing_authority_procedure",
    "ext2_682333d9b9c172f4":
        "cross_scope_transfer",
    "ext2_d2f88ceae65b9b46":
        "external_agency_assessment_or_service_type",
    "ext2_67e067ccdae249ea":
        "cross_scope_transfer",
    "ext2_559a57944943aab5":
        "cross_scope_transfer",
    "ext2_b4eaf7443c1ead5d":
        "cross_scope_transfer",
    "ext2_888971954ec7678a":
        "cross_scope_transfer",
    "ext2_4ff8da290ce9fb3e":
        "criterion_or_general_evidence_rule_used_for_specific_requirement",
    "ext2_298d0e015f4e8ec2":
        "external_live_or_service_information",
    "ext2_1a4d4735dba2c2c1":
        "external_service_or_clinic_procedure",
    "ext2_25bac28c54e142ab":
        "criterion_or_general_evidence_rule_used_for_specific_requirement",
    "ext2_7d2e80a946efbc21":
        "negative_conclusion_from_non_exhaustive_silence",
    "ext2_90d50f9d92d085da":
        "external_professional_or_assessor_guidance",
    "ext2_cce51047e3ea8b52":
        "external_professional_or_assessor_guidance",
    "ext2_d8797e336a9cc692":
        "applicable_general_rule_underused",
    "ext2_8c067aa632151edd":
        "closed_or_exhaustive_rule_underused",
    "ext2_6f3fabde7896acbe":
        "negative_conclusion_from_non_exhaustive_silence",
    "ext2_ac14beba20a48211":
        "external_entitlement_or_organisation_definition",
    "ext2_139daec2a4cbe690":
        "closed_or_exhaustive_rule_underused",
    "ext2_b9c0792e1eafc5b7":
        "missing_manual_rule_wrongly_externalised",
}

# Orthogonal flags describe observable answer-quality symptoms. They are not
# primary root-cause labels and are intentionally allowed to overlap.
FLAGS = {
    "ext_66c81763e3cbd5cf": [
        "answer_status_self_inconsistency",
    ],
    "ext2_682333d9b9c172f4": [
        "answer_status_self_inconsistency",
    ],
    "ext2_559a57944943aab5": [
        "categorical_conclusion_from_silence",
    ],
    "ext2_b4eaf7443c1ead5d": [
        "answer_status_self_inconsistency",
    ],
    "ext2_888971954ec7678a": [
        "answer_status_self_inconsistency",
    ],
    "ext2_4ff8da290ce9fb3e": [
        "answer_status_self_inconsistency",
    ],
    "ext2_1a4d4735dba2c2c1": [
        "answer_status_self_inconsistency",
        "categorical_conclusion_from_silence",
    ],
    "ext2_7d2e80a946efbc21": [
        "categorical_conclusion_from_silence",
    ],
    "ext2_cce51047e3ea8b52": [
        "categorical_conclusion_from_silence",
    ],
    "ext2_6f3fabde7896acbe": [
        "answer_status_self_inconsistency",
        "categorical_conclusion_from_silence",
    ],
    "ext2_b9c0792e1eafc5b7": [
        "missing_information_contract_violation",
    ],
}

PRIMARY_COUNTS = {
    "authoritative_home_resolution_failure": 13,
    "scope_entailment_overreach": 11,
    "scope_entailment_underreach": 4,
}

EXPECTED_NORMALISED_SECONDARY_COUNTS = {
    "applicable_general_rule_underused": 1,
    "closed_or_exhaustive_rule_underused": 2,
    "compositional_sufficiency_underused": 1,
    "criterion_or_general_evidence_rule_used_for_specific_requirement": 3,
    "cross_scope_transfer": 5,
    "external_agency_assessment_or_service_type": 1,
    "external_entitlement_or_organisation_definition": 2,
    "external_fee_or_charge_schedule": 1,
    "external_issuing_authority_procedure": 3,
    "external_live_or_service_information": 2,
    "external_professional_or_assessor_guidance": 2,
    "external_service_or_clinic_procedure": 1,
    "missing_manual_rule_wrongly_externalised": 1,
    "negative_conclusion_from_non_exhaustive_silence": 2,
    "partial_process_treated_as_complete_rule": 1,
}

EXPECTED_FLAG_COUNTS = {
    "answer_status_self_inconsistency": 7,
    "categorical_conclusion_from_silence": 5,
    "missing_information_contract_violation": 1,
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
            f"Reviewed draft already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    if not INPUT_PATH.exists():
        raise SystemExit(
            f"Draft taxonomy not found: {INPUT_PATH}"
        )

    if not RUNTIME_PATH.exists():
        raise SystemExit(
            f"Runtime ask.py not found: {RUNTIME_PATH}"
        )

    draft_sha = sha256(INPUT_PATH)

    if draft_sha != EXPECTED_DRAFT_SHA256:
        raise SystemExit(
            "Draft taxonomy SHA mismatch.\n"
            f"Expected: {EXPECTED_DRAFT_SHA256}\n"
            f"Actual:   {draft_sha}\n"
            "Refusing review transformation."
        )

    runtime_sha = sha256(RUNTIME_PATH)

    if runtime_sha != EXPECTED_RUNTIME_SHA256:
        raise SystemExit(
            "Runtime ask.py is not the restored candidate v2.\n"
            f"Expected: {EXPECTED_RUNTIME_SHA256}\n"
            f"Actual:   {runtime_sha}\n"
            "Refusing review transformation."
        )

    draft = load_json(INPUT_PATH)

    if draft.get("schema") != (
        "waypoint-answer-failure-taxonomy-candidate-v2-draft"
    ):
        raise RuntimeError(
            "Unexpected taxonomy draft schema."
        )

    if draft.get("status") != "DRAFT_FOR_HUMAN_REVIEW_DO_NOT_TUNE":
        raise RuntimeError(
            "Taxonomy draft status changed."
        )

    if draft.get("failure_count") != 28:
        raise RuntimeError(
            "Expected exactly 28 taxonomy items."
        )

    if draft.get("primary_mechanism_counts") != PRIMARY_COUNTS:
        raise RuntimeError(
            "Primary mechanism counts changed."
        )

    items = draft.get("items")

    if not isinstance(items, list) or len(items) != 28:
        raise RuntimeError(
            "Taxonomy items must contain exactly 28 entries."
        )

    item_ids = {item.get("case_id") for item in items}

    if item_ids != set(NORMALISED_SECONDARY):
        missing = sorted(item_ids - set(NORMALISED_SECONDARY))
        extra = sorted(set(NORMALISED_SECONDARY) - item_ids)

        raise RuntimeError(
            "Normalised taxonomy mapping does not match draft cases.\n"
            f"Unmapped draft cases: {missing}\n"
            f"Unknown mapped cases: {extra}"
        )

    reviewed_items = []
    secondary_counts = Counter()
    flag_counts = Counter()

    for item in items:
        case_id = item["case_id"]

        normalised = NORMALISED_SECONDARY[case_id]
        flags = list(FLAGS.get(case_id, []))

        secondary_counts[normalised] += 1
        flag_counts.update(flags)

        reviewed_items.append(
            {
                **item,
                "original_secondary_mechanism": item[
                    "secondary_mechanism"
                ],
                "secondary_mechanism": normalised,
                "diagnostic_flags": flags,
                "assistant_review_status": "REVIEWED",
                "human_review_status": "PENDING",
            }
        )

    if dict(sorted(secondary_counts.items())) != (
        EXPECTED_NORMALISED_SECONDARY_COUNTS
    ):
        raise RuntimeError(
            "Normalised secondary mechanism counts differ "
            "from expected review."
        )

    if dict(sorted(flag_counts.items())) != EXPECTED_FLAG_COUNTS:
        raise RuntimeError(
            "Diagnostic flag counts differ from expected review."
        )

    output = {
        "schema": (
            "waypoint-answer-failure-taxonomy-"
            "candidate-v2-reviewed-draft"
        ),
        "status": (
            "ASSISTANT_REVIEWED_PENDING_USER_APPROVAL_DO_NOT_TUNE"
        ),
        "candidate_name": "evidence_adequacy_v2",
        "source_draft_sha256": EXPECTED_DRAFT_SHA256,
        "source_inventory_sha256": draft[
            "source_inventory_sha256"
        ],
        "runtime_ask_sha256": EXPECTED_RUNTIME_SHA256,
        "failure_count": 28,
        "review_decision": {
            "primary_taxonomy": "ACCEPT_UNCHANGED",
            "secondary_taxonomy": "NORMALISE",
            "cross_cutting_diagnostic_flags": "ADD",
            "runtime_change_authorised": False,
            "prompt_change_authorised": False,
        },
        "primary_mechanism_definitions": draft[
            "primary_mechanism_definitions"
        ],
        "primary_mechanism_counts": PRIMARY_COUNTS,
        "normalised_secondary_mechanism_counts": dict(
            sorted(secondary_counts.items())
        ),
        "diagnostic_flag_definitions": {
            "answer_status_self_inconsistency": (
                "The predicted evidence status is sufficient, or the "
                "answer otherwise makes a categorical claim, while the "
                "answer itself acknowledges that material supporting "
                "policy or information is not established by the supplied "
                "sections."
            ),
            "categorical_conclusion_from_silence": (
                "The answer reaches a categorical negative or positive "
                "conclusion primarily because the supplied text does not "
                "mention the alternative, without an applicable exhaustive "
                "rule establishing that conclusion."
            ),
            "missing_information_contract_violation": (
                "missing_information contains missing policy or source "
                "material rather than a missing user fact."
            ),
        },
        "diagnostic_flag_counts": dict(
            sorted(flag_counts.items())
        ),
        "review_notes": [
            "The three primary mechanism families are retained because they separate authoritative-home errors from scope/entailment overreach and underreach.",
            "Secondary labels were normalised to reduce one-off labels while preserving distinct recurring mechanisms.",
            "Diagnostic flags are orthogonal symptoms and may overlap with any primary mechanism.",
            "The reviewed taxonomy remains development-only and is not approved for prompt or runtime changes.",
            "User approval is required before this taxonomy is frozen as the design basis for a future candidate.",
            "Any future candidate informed by this taxonomy requires a new untouched holdout before any generalisation claim.",
        ],
        "items": reviewed_items,
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
            "Saved reviewed taxonomy count verification failed."
        )

    if verify.get("primary_mechanism_counts") != PRIMARY_COUNTS:
        raise RuntimeError(
            "Saved primary taxonomy verification failed."
        )

    print("Waypoint candidate-v2 taxonomy review")
    print("=" * 39)
    print(f"Input draft:                {INPUT_PATH}")
    print(f"Draft SHA256:               {draft_sha}")
    print(f"Runtime ask SHA256:         {runtime_sha}")
    print(f"Failures reviewed:          {len(reviewed_items)}")
    print()
    print("Primary taxonomy:           ACCEPT UNCHANGED")
    print("Secondary taxonomy:         NORMALISED")
    print("Cross-cutting flags:        ADDED")
    print()
    print("Primary mechanisms:")
    for mechanism, count in PRIMARY_COUNTS.items():
        print(f"  {mechanism:<40}{count:>3}")
    print()
    print("Diagnostic flags:")
    for flag, count in sorted(flag_counts.items()):
        print(f"  {flag:<40}{count:>3}")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Reviewed draft SHA256:      {sha256(OUTPUT_PATH)}")
    print()
    print("Human review status:        PENDING")
    print("Prompt/runtime changes:     NONE")
    print("Runtime/model calls:        NONE")
    print("Retrieval/reranker calls:   NONE")
    print("Database writes:            NONE")
    print()
    print("Candidate-v2 taxonomy review: PASS")


if __name__ == "__main__":
    main()
