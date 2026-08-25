"""Score frozen blind external Waypoint predictions against frozen gold.

This is a scoring-only utility.

It:
- reads the already-saved blind prediction artifact;
- only then reads the frozen adjudication gold;
- makes no retrieval calls;
- makes no embedding calls;
- makes no reranker calls;
- makes no answer-model calls;
- performs no database writes;
- contains no benchmark question literals, candidate IDs, or section mappings.

Primary metric
--------------
Evidence-status accuracy across all benchmark_status == "include" cases.

Secondary metrics
-----------------
- per-class evidence-status accuracy;
- confusion matrix;
- expected-section citation coverage for included sufficient cases.

Run from backend/:
    uv run python -m py_compile scripts/score_blind_external_predictions.py
    uv run python -m scripts.score_blind_external_predictions

Inputs:
    tests/external_questions_blind_v1.json
    tests/external_predictions_blind_v1.json
    tests/external_adjudication_gold_v1.json
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

BLIND_PATH = BACKEND_DIR / "tests" / "external_questions_blind_v1.json"
PREDICTIONS_PATH = (
    BACKEND_DIR / "tests" / "external_predictions_blind_v1.json"
)
GOLD_PATH = BACKEND_DIR / "tests" / "external_adjudication_gold_v1.json"

EXPECTED_BLIND_SCHEMA = "waypoint-external-questions-blind-v1"
EXPECTED_PREDICTIONS_SCHEMA = "waypoint-external-predictions-blind-v1"
EXPECTED_GOLD_SCHEMA = "waypoint-external-adjudication-gold-v1"

EVIDENCE_STATUSES = (
    "sufficient",
    "corpus_gap",
    "external_source_required",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: JSON root must be an object.")

    return payload


def pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{100.0 * numerator / denominator:.1f}%"


def main() -> None:
    # Load blind input and predictions before gold.
    blind = load_json(BLIND_PATH)
    predictions = load_json(PREDICTIONS_PATH)

    if blind.get("schema") != EXPECTED_BLIND_SCHEMA:
        raise RuntimeError(
            f"Unexpected blind schema: {blind.get('schema')!r}"
        )

    if predictions.get("schema") != EXPECTED_PREDICTIONS_SCHEMA:
        raise RuntimeError(
            "Unexpected predictions schema: "
            f"{predictions.get('schema')!r}"
        )

    if predictions.get("source_blind_sha256") != sha256(BLIND_PATH):
        raise RuntimeError(
            "Prediction artifact is not linked to the current blind input."
        )

    blind_questions = blind.get("questions")
    prediction_items = predictions.get("predictions")

    if not isinstance(blind_questions, list):
        raise RuntimeError("Blind questions must be a list.")
    if not isinstance(prediction_items, list):
        raise RuntimeError("Predictions must be a list.")

    if blind.get("question_count") != len(blind_questions):
        raise RuntimeError(
            "Blind question_count does not match questions list."
        )

    if predictions.get("prediction_count") != len(prediction_items):
        raise RuntimeError(
            "Prediction count metadata does not match predictions list."
        )

    blind_by_id: dict[str, dict] = {}
    for item in blind_questions:
        case_id = item.get("case_id")
        question = item.get("question")
        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Blind case has invalid case_id.")
        if case_id in blind_by_id:
            raise RuntimeError(f"Duplicate blind case_id: {case_id}")
        blind_by_id[case_id] = item

    predictions_by_id: dict[str, dict] = {}
    for item in prediction_items:
        case_id = item.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Prediction has invalid case_id.")
        if case_id in predictions_by_id:
            raise RuntimeError(f"Duplicate prediction case_id: {case_id}")
        if case_id not in blind_by_id:
            raise RuntimeError(
                f"Prediction contains unknown case_id: {case_id}"
            )
        if item.get("question") != blind_by_id[case_id].get("question"):
            raise RuntimeError(
                f"{case_id}: prediction question differs from blind input."
            )
        predictions_by_id[case_id] = item

    if set(predictions_by_id) != set(blind_by_id):
        missing = sorted(set(blind_by_id) - set(predictions_by_id))
        extra = sorted(set(predictions_by_id) - set(blind_by_id))
        raise RuntimeError(
            "Blind/prediction case mismatch. "
            f"missing={missing}, extra={extra}"
        )

    # Gold is loaded only after predictions have been fully validated.
    gold = load_json(GOLD_PATH)

    if gold.get("schema") != EXPECTED_GOLD_SCHEMA:
        raise RuntimeError(
            f"Unexpected gold schema: {gold.get('schema')!r}"
        )

    if blind.get("source_gold_sha256") != sha256(GOLD_PATH):
        raise RuntimeError(
            "Blind input is not linked to the current frozen gold file."
        )

    gold_questions = gold.get("questions")
    if not isinstance(gold_questions, list):
        raise RuntimeError("Gold questions must be a list.")

    gold_included: dict[str, dict] = {}
    for item in gold_questions:
        if item.get("benchmark_status") != "include":
            continue

        case_id = item.get("candidate_id")
        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Included gold case has invalid candidate_id.")
        if case_id in gold_included:
            raise RuntimeError(f"Duplicate gold case_id: {case_id}")

        status = item.get("evidence_status")
        if status not in EVIDENCE_STATUSES:
            raise RuntimeError(
                f"{case_id}: included gold case has invalid "
                f"evidence_status {status!r}."
            )

        gold_included[case_id] = item

    if set(gold_included) != set(blind_by_id):
        missing = sorted(set(blind_by_id) - set(gold_included))
        extra = sorted(set(gold_included) - set(blind_by_id))
        raise RuntimeError(
            "Blind/gold included-case mismatch. "
            f"missing={missing}, extra={extra}"
        )

    total = len(blind_by_id)
    correct = 0

    gold_counts: Counter = Counter()
    correct_by_gold: Counter = Counter()

    confusion: dict[str, Counter] = {
        status: Counter() for status in EVIDENCE_STATUSES
    }

    failures: list[dict] = []

    sufficient_cases = 0
    sufficient_with_expected_citation = 0
    sufficient_all_expected_cited = 0
    sufficient_no_citations = 0

    for case_id in blind_by_id:
        gold_item = gold_included[case_id]
        pred_item = predictions_by_id[case_id]

        gold_status = gold_item["evidence_status"]
        pred_status = pred_item.get("evidence_status")

        if pred_status not in EVIDENCE_STATUSES:
            raise RuntimeError(
                f"{case_id}: prediction has invalid evidence_status "
                f"{pred_status!r}."
            )

        gold_counts[gold_status] += 1
        confusion[gold_status][pred_status] += 1

        is_correct = pred_status == gold_status
        if is_correct:
            correct += 1
            correct_by_gold[gold_status] += 1
        else:
            failures.append(
                {
                    "case_id": case_id,
                    "question": gold_item["question"],
                    "gold": gold_status,
                    "predicted": pred_status,
                    "expected_sections": gold_item.get(
                        "expected_sections", []
                    ),
                    "predicted_citations": [
                        c.get("section_code")
                        for c in pred_item.get("citations", [])
                        if isinstance(c, dict)
                    ],
                }
            )

        if gold_status == "sufficient":
            sufficient_cases += 1

            expected = set(gold_item.get("expected_sections", []))
            if not expected:
                raise RuntimeError(
                    f"{case_id}: sufficient gold case has no "
                    "expected_sections."
                )

            citations = pred_item.get("citations")
            if not isinstance(citations, list):
                raise RuntimeError(
                    f"{case_id}: prediction citations must be a list."
                )

            cited = {
                c.get("section_code")
                for c in citations
                if isinstance(c, dict)
                and isinstance(c.get("section_code"), str)
            }

            if not cited:
                sufficient_no_citations += 1

            if expected & cited:
                sufficient_with_expected_citation += 1

            if expected <= cited:
                sufficient_all_expected_cited += 1

    print("Waypoint blind external evaluation score")
    print("=" * 40)
    print(f"Blind input:                {BLIND_PATH}")
    print(f"Predictions:                {PREDICTIONS_PATH}")
    print(f"Frozen gold:               {GOLD_PATH}")
    print()
    print("Prediction artifact existed before gold scoring: PASS")
    print("Retrieval calls:            NONE")
    print("Reranker calls:             NONE")
    print("Answer-model calls:         NONE")
    print("Database writes:            NONE")
    print()

    print("Primary metric")
    print("-" * 72)
    print(
        f"Evidence-status accuracy:   "
        f"{correct}/{total} ({pct(correct, total)})"
    )
    print()

    print("Per-class evidence-status accuracy")
    print("-" * 72)
    for status in EVIDENCE_STATUSES:
        class_total = gold_counts[status]
        class_correct = correct_by_gold[status]
        print(
            f"{status:<26}"
            f"{class_correct:>3}/{class_total:<3} "
            f"({pct(class_correct, class_total)})"
        )
    print()

    print("Evidence-status confusion matrix")
    print("-" * 72)
    header = (
        f"{'gold \\ predicted':<28}"
        f"{'sufficient':>12}"
        f"{'corpus_gap':>12}"
        f"{'external':>12}"
    )
    print(header)
    for gold_status in EVIDENCE_STATUSES:
        row = confusion[gold_status]
        print(
            f"{gold_status:<28}"
            f"{row['sufficient']:>12}"
            f"{row['corpus_gap']:>12}"
            f"{row['external_source_required']:>12}"
        )
    print()

    print("Secondary sufficient-case citation metrics")
    print("-" * 72)
    print(
        f"Sufficient cases:           "
        f"{sufficient_cases}"
    )
    print(
        f"Any expected section cited: "
        f"{sufficient_with_expected_citation}/{sufficient_cases} "
        f"({pct(sufficient_with_expected_citation, sufficient_cases)})"
    )
    print(
        f"All expected sections cited:"
        f" {sufficient_all_expected_cited}/{sufficient_cases} "
        f"({pct(sufficient_all_expected_cited, sufficient_cases)})"
    )
    print(
        f"No citations returned:      "
        f"{sufficient_no_citations}/{sufficient_cases}"
    )
    print()

    print("Evidence-status failures")
    print("-" * 72)
    if not failures:
        print("none")
    else:
        for index, failure in enumerate(failures, start=1):
            print(
                f"{index:>2}. {failure['case_id']}\n"
                f"    question:  {failure['question']}\n"
                f"    gold:      {failure['gold']}\n"
                f"    predicted: {failure['predicted']}\n"
                f"    expected:  {failure['expected_sections']}\n"
                f"    citations: {failure['predicted_citations']}"
            )
    print()

    print(f"Gold SHA256:                {sha256(GOLD_PATH)}")
    print(f"Blind SHA256:               {sha256(BLIND_PATH)}")
    print(
        f"Predictions SHA256:         "
        f"{sha256(PREDICTIONS_PATH)}"
    )
    print()
    print("Blind external scoring:     PASS")


if __name__ == "__main__":
    main()
