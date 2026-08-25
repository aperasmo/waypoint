"""Build a combined answer-layer failure inventory for candidate v2.

This is DEVELOPMENT / DIAGNOSTIC ONLY.

It combines the already-retired external v1 and external v2 evaluation sets
and extracts only candidate-v2 evidence-status failures.

The script does NOT:
- call the answer model;
- call retrieval, embeddings, or reranking;
- modify runtime code;
- write to the database;
- assign a semantic failure taxonomy.

It only creates an immutable factual inventory of observed failures, grouped
by gold -> predicted evidence-status transition.

Run from backend/:
    uv run python -m py_compile scripts/build_answer_failure_inventory_v2.py
    uv run python -m scripts.build_answer_failure_inventory_v2

Output:
    tests/answer_failure_inventory_candidate_v2.json
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

RUNTIME_PATH = (
    BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
)

V1_GOLD_PATH = (
    BACKEND_DIR / "tests" / "external_adjudication_gold_v1.json"
)
V1_PRED_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v1_evidence_adequacy_v2.json"
)

V2_GOLD_PATH = (
    BACKEND_DIR / "tests" / "external_adjudication_gold_v2.json"
)
V2_PRED_PATH = (
    BACKEND_DIR / "tests" / "external_predictions_blind_v2.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "answer_failure_inventory_candidate_v2.json"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_V1_GOLD_SHA256 = (
    "11D21AF433C30F99665915F0536FFE30"
    "B4AE1E76972DB6F036BED38B2D5ECCB3"
)

EXPECTED_V1_PRED_SHA256 = (
    "0F1E84F74DC1B50C6217A1909A48A5F"
    "F922FA537029737E1E8CE3769488FD541"
)

EXPECTED_V2_GOLD_SHA256 = (
    "D584326117A4CEF64C869225AD9186FF"
    "95C1D0753ED93706A0748C6ABCC4FA36"
)

EXPECTED_V2_PRED_SHA256 = (
    "BCC045922577E84AA89CBBE19587E56C"
    "634ABEB119F9476191B050FB2459493D"
)

STATUSES = (
    "sufficient",
    "corpus_gap",
    "external_source_required",
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
            "Refusing to build failure inventory."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{path.name}: JSON root must be an object."
        )

    return payload


def included_gold_map(payload: dict, id_field: str) -> dict[str, dict]:
    questions = payload.get("questions")

    if not isinstance(questions, list):
        raise RuntimeError("Gold questions must be a list.")

    result: dict[str, dict] = {}

    for item in questions:
        if item.get("benchmark_status") != "include":
            continue

        case_id = item.get(id_field)

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Gold case has invalid ID.")

        if case_id in result:
            raise RuntimeError(f"Duplicate gold case ID: {case_id}")

        status = item.get("evidence_status")

        if status not in STATUSES:
            raise RuntimeError(
                f"{case_id}: invalid gold evidence_status {status!r}."
            )

        result[case_id] = item

    return result


def prediction_map(payload: dict) -> dict[str, dict]:
    predictions = payload.get("predictions")

    if not isinstance(predictions, list):
        raise RuntimeError("Predictions must be a list.")

    result: dict[str, dict] = {}

    for item in predictions:
        case_id = item.get("case_id")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Prediction has invalid case_id.")

        if case_id in result:
            raise RuntimeError(
                f"Duplicate prediction case_id: {case_id}"
            )

        status = item.get("evidence_status")

        if status not in STATUSES:
            raise RuntimeError(
                f"{case_id}: invalid predicted evidence_status {status!r}."
            )

        result[case_id] = item

    return result


def extract_failures(
    dataset: str,
    gold_by_id: dict[str, dict],
    pred_by_id: dict[str, dict],
) -> tuple[list[dict], Counter, Counter]:
    if set(gold_by_id) != set(pred_by_id):
        missing = sorted(set(gold_by_id) - set(pred_by_id))
        extra = sorted(set(pred_by_id) - set(gold_by_id))

        raise RuntimeError(
            f"{dataset}: gold/prediction case sets differ.\n"
            f"Missing predictions: {missing}\n"
            f"Unexpected predictions: {extra}"
        )

    failures: list[dict] = []
    gold_counts: Counter = Counter()
    correct_counts: Counter = Counter()

    for case_id, gold_item in gold_by_id.items():
        pred_item = pred_by_id[case_id]

        if gold_item.get("question") != pred_item.get("question"):
            raise RuntimeError(
                f"{dataset}/{case_id}: question text changed."
            )

        gold_status = gold_item["evidence_status"]
        pred_status = pred_item["evidence_status"]

        gold_counts[gold_status] += 1

        if gold_status == pred_status:
            correct_counts[gold_status] += 1
            continue

        citations = [
            citation.get("section_code")
            for citation in pred_item.get("citations", [])
            if isinstance(citation, dict)
            and isinstance(citation.get("section_code"), str)
        ]

        failures.append(
            {
                "dataset": dataset,
                "case_id": case_id,
                "question": gold_item["question"],
                "gold_evidence_status": gold_status,
                "predicted_evidence_status": pred_status,
                "transition": f"{gold_status}->{pred_status}",
                "expected_sections": list(
                    gold_item.get("expected_sections", [])
                ),
                "partial_support_sections": list(
                    gold_item.get("partial_support_sections", [])
                ),
                "predicted_citations": citations,
                "predicted_answer": pred_item.get("answer"),
                "predicted_decision_boundary": pred_item.get(
                    "decision_boundary"
                ),
                "predicted_missing_information": list(
                    pred_item.get("missing_information", [])
                ),
                "adjudication_note": gold_item.get(
                    "adjudication_note"
                ),
            }
        )

    return failures, gold_counts, correct_counts


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Failure inventory already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_sha(
        RUNTIME_PATH,
        EXPECTED_RUNTIME_SHA256,
        "Restored candidate-v2 runtime",
    )
    require_sha(
        V1_GOLD_PATH,
        EXPECTED_V1_GOLD_SHA256,
        "External-v1 gold",
    )
    require_sha(
        V1_PRED_PATH,
        EXPECTED_V1_PRED_SHA256,
        "External-v1 candidate-v2 predictions",
    )
    require_sha(
        V2_GOLD_PATH,
        EXPECTED_V2_GOLD_SHA256,
        "External-v2 gold",
    )
    require_sha(
        V2_PRED_PATH,
        EXPECTED_V2_PRED_SHA256,
        "External-v2 historical predictions",
    )

    v1_gold = load_json(V1_GOLD_PATH)
    v1_pred = load_json(V1_PRED_PATH)
    v2_gold = load_json(V2_GOLD_PATH)
    v2_pred = load_json(V2_PRED_PATH)

    if v1_gold.get("schema") != "waypoint-external-adjudication-gold-v1":
        raise RuntimeError("Unexpected external-v1 gold schema.")

    if v2_gold.get("schema") != "waypoint-external-adjudication-gold-v2":
        raise RuntimeError("Unexpected external-v2 gold schema.")

    if v1_gold.get("status") != "FROZEN_DO_NOT_TUNE_ON_THIS_SET":
        raise RuntimeError("External-v1 gold status changed.")

    if v2_gold.get("status") != "FROZEN_DO_NOT_TUNE_ON_THIS_SET":
        raise RuntimeError("External-v2 gold status changed.")

    if v1_pred.get("runtime_ask_sha256") != EXPECTED_RUNTIME_SHA256:
        raise RuntimeError(
            "External-v1 candidate-v2 predictions use unexpected runtime."
        )

    if v2_pred.get("runtime_ask_sha256") != EXPECTED_RUNTIME_SHA256:
        raise RuntimeError(
            "External-v2 historical predictions use unexpected runtime."
        )

    v1_gold_by_id = included_gold_map(v1_gold, "candidate_id")
    v1_pred_by_id = prediction_map(v1_pred)

    v2_gold_by_id = included_gold_map(v2_gold, "candidate_id")
    v2_pred_by_id = prediction_map(v2_pred)

    if len(v1_gold_by_id) != 51:
        raise RuntimeError(
            f"Expected 51 included v1 cases, got {len(v1_gold_by_id)}."
        )

    if len(v2_gold_by_id) != 60:
        raise RuntimeError(
            f"Expected 60 included v2 cases, got {len(v2_gold_by_id)}."
        )

    v1_failures, v1_gold_counts, v1_correct = extract_failures(
        "external_v1",
        v1_gold_by_id,
        v1_pred_by_id,
    )

    v2_failures, v2_gold_counts, v2_correct = extract_failures(
        "external_v2",
        v2_gold_by_id,
        v2_pred_by_id,
    )

    failures = v1_failures + v2_failures

    transition_counts = Counter(
        item["transition"]
        for item in failures
    )

    combined_gold_counts = v1_gold_counts + v2_gold_counts
    combined_correct = v1_correct + v2_correct

    total_cases = len(v1_gold_by_id) + len(v2_gold_by_id)
    total_correct = sum(combined_correct.values())

    output = {
        "schema": "waypoint-answer-failure-inventory-candidate-v2",
        "status": "DEVELOPMENT_DIAGNOSTIC_ONLY",
        "candidate_name": "evidence_adequacy_v2",
        "runtime_ask_sha256": EXPECTED_RUNTIME_SHA256,
        "source_artifacts": {
            "external_v1_gold_sha256": EXPECTED_V1_GOLD_SHA256,
            "external_v1_predictions_sha256": EXPECTED_V1_PRED_SHA256,
            "external_v2_gold_sha256": EXPECTED_V2_GOLD_SHA256,
            "external_v2_predictions_sha256": EXPECTED_V2_PRED_SHA256,
        },
        "case_counts": {
            "external_v1": len(v1_gold_by_id),
            "external_v2": len(v2_gold_by_id),
            "combined": total_cases,
        },
        "accuracy": {
            "external_v1_correct": sum(v1_correct.values()),
            "external_v1_total": len(v1_gold_by_id),
            "external_v2_correct": sum(v2_correct.values()),
            "external_v2_total": len(v2_gold_by_id),
            "combined_correct": total_correct,
            "combined_total": total_cases,
        },
        "combined_gold_class_counts": {
            status: combined_gold_counts[status]
            for status in STATUSES
        },
        "combined_correct_by_class": {
            status: combined_correct[status]
            for status in STATUSES
        },
        "failure_count": len(failures),
        "failure_transition_counts": dict(
            sorted(transition_counts.items())
        ),
        "taxonomy_status": (
            "UNASSIGNED_HUMAN_REVIEW_REQUIRED"
        ),
        "notes": [
            "This file is a factual inventory of candidate-v2 evidence-status failures across retired external v1 and v2 development data.",
            "No semantic failure mechanism has been assigned yet.",
            "Do not use this artifact as runtime input.",
            "Do not claim fresh generalisation performance from these retired datasets.",
        ],
        "failures": failures,
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
            f"Expected 28 combined failures, got "
            f"{verify.get('failure_count')}."
        )

    expected_transitions = {
        "corpus_gap->external_source_required": 1,
        "corpus_gap->sufficient": 11,
        "external_source_required->corpus_gap": 10,
        "external_source_required->sufficient": 2,
        "sufficient->corpus_gap": 4,
    }

    if verify.get("failure_transition_counts") != expected_transitions:
        raise RuntimeError(
            "Combined failure-transition counts differ from expected "
            "historical results."
        )

    print("Waypoint candidate-v2 combined failure inventory")
    print("=" * 48)
    print(f"Runtime ask SHA256:        {sha256(RUNTIME_PATH)}")
    print(f"External-v1 cases:         {len(v1_gold_by_id)}")
    print(f"External-v2 cases:         {len(v2_gold_by_id)}")
    print(f"Combined cases:            {total_cases}")
    print()
    print(
        f"External-v1 correct:       "
        f"{sum(v1_correct.values())}/{len(v1_gold_by_id)}"
    )
    print(
        f"External-v2 correct:       "
        f"{sum(v2_correct.values())}/{len(v2_gold_by_id)}"
    )
    print(
        f"Combined correct:          "
        f"{total_correct}/{total_cases}"
    )
    print(f"Combined failures:         {len(failures)}")
    print()
    print("Failure transitions:")
    for transition, count in sorted(transition_counts.items()):
        print(f"  {transition:<46}{count:>3}")
    print()
    print(f"Output:                    {OUTPUT_PATH}")
    print(f"Inventory SHA256:          {sha256(OUTPUT_PATH)}")
    print()
    print("Semantic taxonomy assigned:NONE")
    print("Runtime/model calls:       NONE")
    print("Retrieval/reranker calls:  NONE")
    print("Database writes:           NONE")
    print()
    print("Candidate-v2 failure inventory: PASS")


if __name__ == "__main__":
    main()
