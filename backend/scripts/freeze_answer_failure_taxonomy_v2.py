"""Freeze the reviewed candidate-v2 answer failure taxonomy.

Running this script constitutes approval of the reviewed taxonomy as the
development design basis for future answer-layer experimentation.

IMPORTANT:
- This does NOT approve any prompt/runtime change.
- This taxonomy is development/diagnostic evidence only.
- It must never be imported by runtime code.
- Any candidate informed by it still requires a fresh untouched holdout
  before any generalisation claim.

Run from backend/:
    uv run python -m py_compile scripts/freeze_answer_failure_taxonomy_v2.py
    uv run python -m scripts.freeze_answer_failure_taxonomy_v2

Input:
    tests/answer_failure_taxonomy_candidate_v2_reviewed_draft.json

Output:
    tests/answer_failure_taxonomy_candidate_v2_frozen.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

INPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "answer_failure_taxonomy_candidate_v2_reviewed_draft.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "answer_failure_taxonomy_candidate_v2_frozen.json"
)

RUNTIME_PATH = (
    BACKEND_DIR
    / "app"
    / "api"
    / "routes"
    / "ask.py"
)

EXPECTED_REVIEWED_SHA256 = (
    "F78D376E96E4C84AFF4F2CDDD7BFF06F"
    "311C71FA2683508567361B7164D3B18C"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_SOURCE_DRAFT_SHA256 = (
    "80BFA248D3DA26A46C91F4F14B7B48E4"
    "4DC7320D7E7974905B170A61F9F01082"
)

EXPECTED_SOURCE_INVENTORY_SHA256 = (
    "CAFC74F7985B7F0222C79924281EC36D"
    "19B32278A57D7C72DD3DCC4214A7A53B"
)

EXPECTED_PRIMARY_COUNTS = {
    "authoritative_home_resolution_failure": 13,
    "scope_entailment_overreach": 11,
    "scope_entailment_underreach": 4,
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
            f"Frozen taxonomy already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    if not RUNTIME_PATH.exists():
        raise SystemExit(
            f"Runtime ask.py not found: {RUNTIME_PATH}"
        )

    reviewed_sha = sha256(INPUT_PATH)

    if reviewed_sha != EXPECTED_REVIEWED_SHA256:
        raise SystemExit(
            "Reviewed taxonomy SHA mismatch.\n"
            f"Expected: {EXPECTED_REVIEWED_SHA256}\n"
            f"Actual:   {reviewed_sha}\n"
            "Refusing freeze."
        )

    runtime_sha = sha256(RUNTIME_PATH)

    if runtime_sha != EXPECTED_RUNTIME_SHA256:
        raise SystemExit(
            "Runtime ask.py no longer matches frozen candidate v2.\n"
            f"Expected: {EXPECTED_RUNTIME_SHA256}\n"
            f"Actual:   {runtime_sha}\n"
            "Refusing freeze."
        )

    reviewed = load_json(INPUT_PATH)

    if reviewed.get("schema") != (
        "waypoint-answer-failure-taxonomy-candidate-v2-reviewed-draft"
    ):
        raise RuntimeError(
            "Unexpected reviewed taxonomy schema."
        )

    if reviewed.get("status") != (
        "ASSISTANT_REVIEWED_PENDING_USER_APPROVAL_DO_NOT_TUNE"
    ):
        raise RuntimeError(
            "Reviewed taxonomy status changed."
        )

    if reviewed.get("failure_count") != 28:
        raise RuntimeError(
            "Expected exactly 28 failures."
        )

    if reviewed.get("runtime_ask_sha256") != EXPECTED_RUNTIME_SHA256:
        raise RuntimeError(
            "Reviewed taxonomy points to an unexpected runtime SHA."
        )

    if reviewed.get("source_draft_sha256") != EXPECTED_SOURCE_DRAFT_SHA256:
        raise RuntimeError(
            "Reviewed taxonomy source-draft SHA changed."
        )

    if reviewed.get(
        "source_inventory_sha256"
    ) != EXPECTED_SOURCE_INVENTORY_SHA256:
        raise RuntimeError(
            "Reviewed taxonomy source-inventory SHA changed."
        )

    if reviewed.get(
        "primary_mechanism_counts"
    ) != EXPECTED_PRIMARY_COUNTS:
        raise RuntimeError(
            "Primary mechanism counts changed."
        )

    if reviewed.get(
        "diagnostic_flag_counts"
    ) != EXPECTED_FLAG_COUNTS:
        raise RuntimeError(
            "Diagnostic flag counts changed."
        )

    items = reviewed.get("items")

    if not isinstance(items, list) or len(items) != 28:
        raise RuntimeError(
            "Reviewed taxonomy must contain exactly 28 items."
        )

    frozen_items = []

    for item in items:
        frozen_item = dict(item)
        frozen_item["human_review_status"] = "APPROVED"
        frozen_items.append(frozen_item)

    output = {
        **reviewed,
        "schema": (
            "waypoint-answer-failure-taxonomy-candidate-v2-frozen"
        ),
        "status": (
            "FROZEN_DEVELOPMENT_DESIGN_BASIS_DO_NOT_USE_AS_RUNTIME"
        ),
        "source_reviewed_draft_sha256": EXPECTED_REVIEWED_SHA256,
        "frozen_on": str(date.today()),
        "approval": {
            "taxonomy_design_basis": "APPROVED",
            "primary_taxonomy": "APPROVED",
            "normalised_secondary_taxonomy": "APPROVED",
            "cross_cutting_diagnostic_flags": "APPROVED",
            "prompt_change_authorised": False,
            "runtime_change_authorised": False,
            "fresh_holdout_required_for_future_candidate": True,
        },
        "freeze_rules": [
            "This artifact may be used only as development evidence when designing future candidates.",
            "No case ID, benchmark question, adjudication note, expected section, secondary label, or diagnostic flag may be imported or hard-coded into runtime behaviour.",
            "Future runtime changes must express only generic reasoning rules that can apply to unseen questions.",
            "Retired external v1 and v2 remain development/diagnostic data only.",
            "Any future candidate informed by this taxonomy requires a fresh untouched holdout before generalisation claims.",
            "Acceptance criteria for that fresh holdout must be frozen before the first prediction run.",
        ],
        "items": frozen_items,
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

    if verify.get("status") != (
        "FROZEN_DEVELOPMENT_DESIGN_BASIS_DO_NOT_USE_AS_RUNTIME"
    ):
        raise RuntimeError(
            "Frozen taxonomy status verification failed."
        )

    if verify.get("failure_count") != 28:
        raise RuntimeError(
            "Frozen taxonomy failure-count verification failed."
        )

    if any(
        item.get("human_review_status") != "APPROVED"
        for item in verify.get("items", [])
    ):
        raise RuntimeError(
            "Not all frozen taxonomy items are marked approved."
        )

    print("Waypoint candidate-v2 failure taxonomy freeze")
    print("=" * 45)
    print(f"Reviewed draft:             {INPUT_PATH}")
    print(f"Reviewed draft SHA256:      {reviewed_sha}")
    print(f"Runtime ask SHA256:         {runtime_sha}")
    print(f"Failures frozen:            28")
    print()
    print("Primary taxonomy:           APPROVED")
    print("Secondary taxonomy:         APPROVED")
    print("Diagnostic flags:           APPROVED")
    print("Prompt change authorised:   NO")
    print("Runtime change authorised:  NO")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Frozen taxonomy SHA256:     {sha256(OUTPUT_PATH)}")
    print()
    print("Retired v1/v2 status:       DEVELOPMENT ONLY")
    print("Fresh holdout required:     YES")
    print("Runtime/model calls:        NONE")
    print("Retrieval/reranker calls:   NONE")
    print("Database writes:            NONE")
    print()
    print("Candidate-v2 failure taxonomy freeze: PASS")


if __name__ == "__main__":
    main()
