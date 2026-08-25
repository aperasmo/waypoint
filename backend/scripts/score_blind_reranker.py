"""Score blind Waypoint reranker predictions against gold labels.

This is the only phase that loads expected_sections.

It never calls the reranker or retrieval model. It scores the already-saved
prediction artifact exactly as produced by run_blind_reranker.py.

Run from backend/:
    uv run python -m scripts.score_blind_reranker
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
GOLD_PATH = BACKEND_DIR / "tests" / "eval_questions_adjudicated_v2.json"
BLIND_PATH = BACKEND_DIR / "tests" / "rerank_questions_blind_v2.json"
PREDICTIONS_PATH = BACKEND_DIR / "tests" / "rerank_predictions_blind_v2.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def make_case_id(question: str) -> str:
    digest = hashlib.sha256(question.encode("utf-8")).hexdigest()
    return f"q_{digest[:16]}"


def main() -> None:
    for path in (GOLD_PATH, BLIND_PATH, PREDICTIONS_PATH):
        if not path.exists():
            raise SystemExit(f"Required file not found: {path}")

    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    blind = json.loads(BLIND_PATH.read_text(encoding="utf-8"))
    predictions_payload = json.loads(
        PREDICTIONS_PATH.read_text(encoding="utf-8")
    )

    if predictions_payload.get("blind_input_sha256") != sha256(BLIND_PATH):
        raise SystemExit(
            "Prediction file was not produced from the current blind input.\n"
            f"Recorded: {predictions_payload.get('blind_input_sha256')}\n"
            f"Current:  {sha256(BLIND_PATH)}"
        )

    blind_cases = blind.get("questions")
    gold_cases = gold.get("questions")
    predictions = predictions_payload.get("predictions")

    if not isinstance(blind_cases, list):
        raise SystemExit("Blind file has no valid questions list.")
    if not isinstance(gold_cases, list):
        raise SystemExit("Gold file has no valid questions list.")
    if not isinstance(predictions, list):
        raise SystemExit("Prediction file has no valid predictions list.")

    blind_by_id = {}
    for case in blind_cases:
        if set(case) != {"case_id", "question"}:
            raise SystemExit(
                "Blind case contains fields beyond case_id and question."
            )
        case_id = case["case_id"]
        question = case["question"]
        if make_case_id(question) != case_id:
            raise SystemExit(
                f"Blind case_id does not match question: {case_id}"
            )
        if case_id in blind_by_id:
            raise SystemExit(f"Duplicate blind case_id: {case_id}")
        blind_by_id[case_id] = case

    gold_by_id = {}
    for case in gold_cases:
        question = case.get("question")
        expected = case.get("expected_sections")

        if not isinstance(question, str) or not question.strip():
            raise SystemExit("Gold case contains an invalid question.")
        if not isinstance(expected, list):
            raise SystemExit(
                f"Gold case has invalid expected_sections: {question!r}"
            )

        case_id = make_case_id(question.strip())
        if case_id in gold_by_id:
            raise SystemExit(f"Duplicate gold case_id: {case_id}")

        gold_by_id[case_id] = {
            "question": question.strip(),
            "expected_sections": expected,
        }

    prediction_by_id = {}
    required_prediction_fields = {
        "case_id",
        "question",
        "production_top1_section",
        "retrieved_sections",
        "chosen_index",
        "chosen_section",
    }

    for prediction in predictions:
        if set(prediction) != required_prediction_fields:
            raise SystemExit(
                "Prediction contains unexpected fields. "
                f"Found: {sorted(prediction)}"
            )

        case_id = prediction["case_id"]
        question = prediction["question"]

        if case_id in prediction_by_id:
            raise SystemExit(f"Duplicate prediction case_id: {case_id}")

        if make_case_id(question) != case_id:
            raise SystemExit(
                f"Prediction case_id does not match question: {case_id}"
            )

        retrieved = prediction["retrieved_sections"]
        chosen_index = prediction["chosen_index"]
        chosen_section = prediction["chosen_section"]

        if not isinstance(retrieved, list) or len(retrieved) != 5:
            raise SystemExit(
                f"Prediction {case_id} does not contain exactly 5 sections."
            )
        if not isinstance(chosen_index, int) or not 1 <= chosen_index <= 5:
            raise SystemExit(
                f"Prediction {case_id} has invalid chosen_index."
            )
        if retrieved[chosen_index - 1] != chosen_section:
            raise SystemExit(
                f"Prediction {case_id} chosen_section does not match "
                "chosen_index."
            )
        if prediction["production_top1_section"] != retrieved[0]:
            raise SystemExit(
                f"Prediction {case_id} production_top1_section does not "
                "match retrieved rank 1."
            )

        prediction_by_id[case_id] = prediction

    blind_ids = set(blind_by_id)
    gold_ids = set(gold_by_id)
    prediction_ids = set(prediction_by_id)

    if blind_ids != prediction_ids:
        raise SystemExit(
            "Prediction case IDs do not exactly match blind input IDs."
        )
    if blind_ids != gold_ids:
        missing_gold = sorted(blind_ids - gold_ids)
        extra_gold = sorted(gold_ids - blind_ids)
        raise SystemExit(
            "Gold and blind case IDs do not match exactly.\n"
            f"Missing gold IDs: {missing_gold}\n"
            f"Extra gold IDs:   {extra_gold}"
        )

    production_hits = 0
    reranked_hits = 0
    top5_hits = 0

    gains = []
    regressions = []
    unchanged_misses = []

    for case_id in blind_by_id:
        blind_case = blind_by_id[case_id]
        gold_case = gold_by_id[case_id]
        prediction = prediction_by_id[case_id]

        if blind_case["question"] != gold_case["question"]:
            raise SystemExit(
                f"Question mismatch between blind and gold for {case_id}"
            )
        if blind_case["question"] != prediction["question"]:
            raise SystemExit(
                f"Question mismatch between blind and predictions for {case_id}"
            )

        expected = set(gold_case["expected_sections"])
        retrieved = prediction["retrieved_sections"]
        production = prediction["production_top1_section"]
        chosen = prediction["chosen_section"]

        production_ok = production in expected
        reranked_ok = chosen in expected
        top5_ok = bool(expected & set(retrieved))

        production_hits += int(production_ok)
        reranked_hits += int(reranked_ok)
        top5_hits += int(top5_ok)

        record = {
            "case_id": case_id,
            "question": blind_case["question"],
            "expected": gold_case["expected_sections"],
            "retrieved": retrieved,
            "production": production,
            "chosen": chosen,
        }

        if not production_ok and reranked_ok:
            gains.append(record)
        elif production_ok and not reranked_ok:
            regressions.append(record)
        elif not production_ok and not reranked_ok:
            unchanged_misses.append(record)

    total = len(blind_by_id)

    print("Waypoint blind reranker scoring")
    print("=" * 31)
    print(f"Gold:        {GOLD_PATH}")
    print(f"Blind:       {BLIND_PATH}")
    print(f"Predictions: {PREDICTIONS_PATH}")
    print()
    print("Prediction generation and gold scoring are separate: PASS")
    print(f"Cases:                       {total}")
    print()
    print("Results")
    print("-" * 76)
    print(
        f"Production Recall@1:         {production_hits}/{total} "
        f"({production_hits / total:.0%})"
    )
    print(
        f"Blind reranked Recall@1:     {reranked_hits}/{total} "
        f"({reranked_hits / total:.0%})"
    )
    print(
        f"Recall@1 delta:              "
        f"{reranked_hits - production_hits:+d}"
    )
    print(
        f"Top-5 candidate coverage:    {top5_hits}/{total} "
        f"({top5_hits / total:.0%})"
    )
    print(f"Rank-1 gains:                {len(gains)}")
    print(f"Rank-1 regressions:          {len(regressions)}")
    print(f"Still-missed rank-1 cases:   {len(unchanged_misses)}")

    def show(title: str, rows: list[dict]) -> None:
        print()
        if not rows:
            print(f"{title}: none")
            return

        print(f"{title} ({len(rows)})")
        print("-" * 76)

        for row in rows:
            print(f"{row['case_id']}  {row['question']}")
            print(f"    wanted:     {', '.join(row['expected'])}")
            print(f"    top 5:      {', '.join(row['retrieved'])}")
            print(f"    production: {row['production']}")
            print(f"    reranker:   {row['chosen']}")

    show("Rank-1 gains", gains)
    show("Rank-1 regressions", regressions)
    show("Unchanged rank-1 misses", unchanged_misses)

    print()
    print("Decision")
    print("-" * 76)

    if reranked_hits < production_hits:
        verdict = "REJECT"
        reason = "Blind reranker reduced Recall@1."
    elif regressions:
        verdict = "REVIEW"
        reason = (
            "Net Recall@1 did not regress, but one or more production-correct "
            "rank-1 cases were displaced."
        )
    elif reranked_hits > production_hits:
        verdict = "MEASURED GAIN"
        reason = (
            "Blind Recall@1 improved with no rank-1 regressions and the same "
            "retrieved evidence set."
        )
    else:
        verdict = "NO MEASURED GAIN"
        reason = "Blind Recall@1 was unchanged."

    print(f"Verdict: {verdict}")
    print(f"Reason:  {reason}")
    print()
    print(f"Gold SHA256:        {sha256(GOLD_PATH)}")
    print(f"Blind SHA256:       {sha256(BLIND_PATH)}")
    print(f"Predictions SHA256: {sha256(PREDICTIONS_PATH)}")


if __name__ == "__main__":
    main()