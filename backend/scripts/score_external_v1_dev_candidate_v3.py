"""Score candidate v3 on RETIRED external-v1 development data.

This is a development/regression comparison only. External v1 has already
been inspected and used during answer-layer development, so these results
are NOT fresh generalisation evidence.

The scorer validates:
- frozen external-v1 gold;
- retired blind v1 input;
- historical candidate-v2 development predictions;
- candidate-v3 development predictions.

It performs:
- no model calls;
- no retrieval or reranking;
- no database writes.

Run from backend/:
    uv run python -m py_compile scripts/score_external_v1_dev_candidate_v3.py
    uv run python -m scripts.score_external_v1_dev_candidate_v3
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

GOLD_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_adjudication_gold_v1.json"
)

BLIND_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_questions_blind_v1.json"
)

V2_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v1_evidence_adequacy_v2.json"
)

V3_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v1_candidate_v3.json"
)

EXPECTED_GOLD_SHA256 = (
    "11D21AF433C30F99665915F0536FFE30"
    "B4AE1E76972DB6F036BED38B2D5ECCB3"
)

EXPECTED_BLIND_SHA256 = (
    "33C6A0370C382130890681064B4C32C1B"
    "519EF9CF1FC52D7C3D6570C8A60FFCB"
)

EXPECTED_V2_SHA256 = (
    "0F1E84F74DC1B50C6217A1909A48A5F"
    "F922FA537029737E1E8CE3769488FD541"
)

EXPECTED_V3_SHA256 = (
    "0AB50EE8BAF7FCE304516C989CB396F1"
    "F1344E43C28601152C98FC6F9C3FE97E"
)

EXPECTED_V2_ASK_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_V3_ASK_SHA256 = (
    "F1F17F3C714C956239E4A16BAE48EB8"
    "CFFAA2BB7D7BE809EB182F7D936B008EB"
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
            "Refusing to score changed evaluation data."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{path.name}: JSON root must be an object."
        )

    return payload


def pct(numerator: int | float, denominator: int | float) -> str:
    if not denominator:
        return "n/a"

    return f"{100.0 * numerator / denominator:.1f}%"


def build_gold_map(gold: dict) -> dict[str, dict]:
    questions = gold.get("questions")

    if not isinstance(questions, list):
        raise RuntimeError("Gold questions must be a list.")

    included = [
        item
        for item in questions
        if item.get("benchmark_status") == "include"
    ]

    if len(included) != 51:
        raise RuntimeError(
            f"Expected 51 included gold questions, got {len(included)}."
        )

    result: dict[str, dict] = {}

    for item in included:
        case_id = item.get("candidate_id")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Gold case has invalid candidate_id.")

        if case_id in result:
            raise RuntimeError(
                f"Duplicate gold candidate_id: {case_id}"
            )

        if item.get("evidence_status") not in STATUSES:
            raise RuntimeError(
                f"{case_id}: invalid gold evidence_status."
            )

        result[case_id] = item

    return result


def build_prediction_map(
    predictions: dict,
    expected_count: int = 51,
) -> dict[str, dict]:
    items = predictions.get("predictions")

    if not isinstance(items, list):
        raise RuntimeError("Predictions must be a list.")

    if len(items) != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} predictions, got {len(items)}."
        )

    result: dict[str, dict] = {}

    for item in items:
        case_id = item.get("case_id")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError(
                "Prediction has invalid case_id."
            )

        if case_id in result:
            raise RuntimeError(
                f"Duplicate prediction case_id: {case_id}"
            )

        if item.get("evidence_status") not in STATUSES:
            raise RuntimeError(
                f"{case_id}: invalid predicted evidence_status."
            )

        result[case_id] = item

    return result


def score(
    gold_by_id: dict[str, dict],
    pred_by_id: dict[str, dict],
) -> dict:
    if set(gold_by_id) != set(pred_by_id):
        missing = sorted(set(gold_by_id) - set(pred_by_id))
        extra = sorted(set(pred_by_id) - set(gold_by_id))

        raise RuntimeError(
            "Gold/prediction case sets differ.\n"
            f"Missing: {missing}\n"
            f"Extra:   {extra}"
        )

    gold_counts = Counter()
    correct_counts = Counter()
    predicted_counts = Counter()

    confusion = {
        status: Counter()
        for status in STATUSES
    }

    correct = 0

    for case_id, gold_item in gold_by_id.items():
        pred_item = pred_by_id[case_id]

        if gold_item.get("question") != pred_item.get("question"):
            raise RuntimeError(
                f"{case_id}: question text changed."
            )

        gold_status = gold_item["evidence_status"]
        pred_status = pred_item["evidence_status"]

        gold_counts[gold_status] += 1
        predicted_counts[pred_status] += 1
        confusion[gold_status][pred_status] += 1

        if gold_status == pred_status:
            correct += 1
            correct_counts[gold_status] += 1

    sufficient_ids = [
        case_id
        for case_id, item in gold_by_id.items()
        if item["evidence_status"] == "sufficient"
    ]

    any_expected = 0
    all_expected = 0
    no_citations = 0

    for case_id in sufficient_ids:
        expected = set(
            gold_by_id[case_id].get("expected_sections", [])
        )

        if not expected:
            raise RuntimeError(
                f"{case_id}: sufficient case has no expected sections."
            )

        citations = pred_by_id[case_id].get("citations", [])

        cited = {
            citation.get("section_code")
            for citation in citations
            if isinstance(citation, dict)
            and isinstance(citation.get("section_code"), str)
        }

        if not cited:
            no_citations += 1

        if expected & cited:
            any_expected += 1

        if expected <= cited:
            all_expected += 1

    return {
        "correct": correct,
        "gold_counts": gold_counts,
        "correct_counts": correct_counts,
        "predicted_counts": predicted_counts,
        "confusion": confusion,
        "sufficient_ids": sufficient_ids,
        "any_expected": any_expected,
        "all_expected": all_expected,
        "no_citations": no_citations,
    }


def main() -> None:
    require_sha(
        GOLD_PATH,
        EXPECTED_GOLD_SHA256,
        "Frozen external-v1 gold",
    )

    require_sha(
        BLIND_PATH,
        EXPECTED_BLIND_SHA256,
        "Retired external-v1 blind input",
    )

    require_sha(
        V2_PATH,
        EXPECTED_V2_SHA256,
        "Historical candidate-v2 predictions",
    )

    require_sha(
        V3_PATH,
        EXPECTED_V3_SHA256,
        "Candidate-v3 predictions",
    )

    gold = load_json(GOLD_PATH)
    blind = load_json(BLIND_PATH)
    v2 = load_json(V2_PATH)
    v3 = load_json(V3_PATH)

    if gold.get("schema") != "waypoint-external-adjudication-gold-v1":
        raise RuntimeError("Unexpected external-v1 gold schema.")

    if gold.get("status") != "FROZEN_DO_NOT_TUNE_ON_THIS_SET":
        raise RuntimeError("External-v1 gold status changed.")

    if blind.get("schema") != "waypoint-external-questions-blind-v1":
        raise RuntimeError("Unexpected external-v1 blind schema.")

    if blind.get("question_count") != 51:
        raise RuntimeError("External-v1 blind question count changed.")

    if v2.get("schema") != "waypoint-external-predictions-dev-v1-v2":
        raise RuntimeError("Unexpected candidate-v2 prediction schema.")

    if v3.get("schema") != (
        "waypoint-external-predictions-dev-v1-candidate-v3"
    ):
        raise RuntimeError("Unexpected candidate-v3 prediction schema.")

    if v2.get("status") != (
        "DEVELOPMENT_PREDICTIONS_NOT_UNTOUCHED_HOLDOUT"
    ):
        raise RuntimeError("Candidate-v2 artifact is not development.")

    if v3.get("status") != (
        "DEVELOPMENT_PREDICTIONS_NOT_UNTOUCHED_HOLDOUT"
    ):
        raise RuntimeError("Candidate-v3 artifact is not development.")

    if v2.get("runtime_ask_sha256") != EXPECTED_V2_ASK_SHA256:
        raise RuntimeError(
            "Candidate-v2 runtime ask SHA changed."
        )

    if v3.get("runtime_ask_sha256") != EXPECTED_V3_ASK_SHA256:
        raise RuntimeError(
            "Candidate-v3 runtime ask SHA changed."
        )

    if v2.get("source_blind_sha256") != EXPECTED_BLIND_SHA256:
        raise RuntimeError(
            "Candidate-v2 artifact is not linked to blind v1."
        )

    if v3.get("source_blind_sha256") != EXPECTED_BLIND_SHA256:
        raise RuntimeError(
            "Candidate-v3 artifact is not linked to blind v1."
        )

    if v3.get(
        "historical_candidate_v2_predictions_sha256"
    ) != EXPECTED_V2_SHA256:
        raise RuntimeError(
            "Candidate-v3 artifact does not preserve the historical "
            "candidate-v2 prediction linkage."
        )

    gold_by_id = build_gold_map(gold)
    v2_by_id = build_prediction_map(v2)
    v3_by_id = build_prediction_map(v3)

    blind_items = blind.get("questions")

    if not isinstance(blind_items, list):
        raise RuntimeError("Blind questions must be a list.")

    blind_by_id = {
        item["case_id"]: item
        for item in blind_items
    }

    if set(blind_by_id) != set(gold_by_id):
        raise RuntimeError(
            "Blind/gold included case sets differ."
        )

    for case_id, gold_item in gold_by_id.items():
        if blind_by_id[case_id]["question"] != gold_item["question"]:
            raise RuntimeError(
                f"{case_id}: blind question differs from gold."
            )

    old = score(gold_by_id, v2_by_id)
    new = score(gold_by_id, v3_by_id)

    gains = []
    regressions = []
    changed_wrong = []

    for case_id, gold_item in gold_by_id.items():
        gold_status = gold_item["evidence_status"]
        old_status = v2_by_id[case_id]["evidence_status"]
        new_status = v3_by_id[case_id]["evidence_status"]

        old_ok = old_status == gold_status
        new_ok = new_status == gold_status

        record = (
            case_id,
            gold_status,
            old_status,
            new_status,
            gold_item["question"],
        )

        if not old_ok and new_ok:
            gains.append(record)
        elif old_ok and not new_ok:
            regressions.append(record)
        elif (
            not old_ok
            and not new_ok
            and old_status != new_status
        ):
            changed_wrong.append(record)

    print("Waypoint candidate-v3 external-v1 DEVELOPMENT score")
    print("=" * 52)
    print(f"Gold SHA256:               {sha256(GOLD_PATH)}")
    print(f"Blind SHA256:              {sha256(BLIND_PATH)}")
    print(f"Candidate-v2 pred SHA256:  {sha256(V2_PATH)}")
    print(f"Candidate-v3 pred SHA256:  {sha256(V3_PATH)}")
    print(f"Candidate-v3 ask SHA256:   {EXPECTED_V3_ASK_SHA256}")
    print()
    print("Evaluation status:         DEVELOPMENT / DIAGNOSTIC ONLY")
    print("Runtime/model calls:       NONE")
    print("Retrieval/reranker calls:  NONE")
    print("Database writes:           NONE")
    print()

    print("Overall evidence-status accuracy")
    print("-" * 72)
    print(
        f"Candidate v2:              "
        f"{old['correct']}/51 ({pct(old['correct'], 51)})"
    )
    print(
        f"Candidate v3:              "
        f"{new['correct']}/51 ({pct(new['correct'], 51)})"
    )
    print(
        f"Delta:                      "
        f"{new['correct'] - old['correct']:+d} correct "
        f"({100 * (new['correct'] - old['correct']) / 51:+.1f} pp)"
    )
    print()

    print("Per-class comparison")
    print("-" * 72)
    print(
        f"{'class':<27}"
        f"{'candidate v2':>18}"
        f"{'candidate v3':>18}"
        f"{'delta':>9}"
    )

    for status in STATUSES:
        total = new["gold_counts"][status]
        old_correct = old["correct_counts"][status]
        new_correct = new["correct_counts"][status]

        delta_pp = (
            100 * (new_correct - old_correct) / total
            if total
            else 0.0
        )

        print(
            f"{status:<27}"
            f"{old_correct:>3}/{total:<3} {pct(old_correct, total):>8}"
            f"{new_correct:>5}/{total:<3} {pct(new_correct, total):>8}"
            f"{delta_pp:>+8.1f}"
        )

    print()

    print("Candidate-v3 predicted class distribution")
    print("-" * 72)

    for status in STATUSES:
        print(
            f"{status:<27}"
            f"{new['predicted_counts'][status]:>3}"
        )

    print()

    print("Candidate-v3 confusion matrix")
    print("-" * 72)
    print(
        f"{'gold / predicted':<29}"
        f"{'sufficient':>12}"
        f"{'corpus_gap':>12}"
        f"{'external':>12}"
    )

    for gold_status in STATUSES:
        row = new["confusion"][gold_status]

        print(
            f"{gold_status:<29}"
            f"{row['sufficient']:>12}"
            f"{row['corpus_gap']:>12}"
            f"{row['external_source_required']:>12}"
        )

    print()

    print("Sufficient-case citation comparison")
    print("-" * 72)

    n = len(new["sufficient_ids"])

    print(
        f"Candidate-v2 any expected: {old['any_expected']}/{n} "
        f"({pct(old['any_expected'], n)})"
    )

    print(
        f"Candidate-v3 any expected: {new['any_expected']}/{n} "
        f"({pct(new['any_expected'], n)})"
    )

    print(
        f"Candidate-v2 all expected: {old['all_expected']}/{n} "
        f"({pct(old['all_expected'], n)})"
    )

    print(
        f"Candidate-v3 all expected: {new['all_expected']}/{n} "
        f"({pct(new['all_expected'], n)})"
    )

    print(
        f"Candidate-v3 no citations: {new['no_citations']}/{n} "
        f"({pct(new['no_citations'], n)})"
    )

    print()

    print("Correctness transitions")
    print("-" * 72)
    print(f"Gains:                     {len(gains)}")
    print(f"Regressions:               {len(regressions)}")
    print(f"Wrong -> different wrong:  {len(changed_wrong)}")
    print()

    if gains:
        print("Gains")
        for case_id, gold_status, old_status, new_status, question in gains:
            print(
                f"  {case_id}\n"
                f"    gold: {gold_status}\n"
                f"    v2:   {old_status}\n"
                f"    v3:   {new_status}\n"
                f"    q:    {question}"
            )
        print()

    if regressions:
        print("Regressions")
        for case_id, gold_status, old_status, new_status, question in regressions:
            print(
                f"  {case_id}\n"
                f"    gold: {gold_status}\n"
                f"    v2:   {old_status}\n"
                f"    v3:   {new_status}\n"
                f"    q:    {question}"
            )
        print()

    if changed_wrong:
        print("Changed but still wrong")
        for case_id, gold_status, old_status, new_status, question in changed_wrong:
            print(
                f"  {case_id}\n"
                f"    gold: {gold_status}\n"
                f"    v2:   {old_status}\n"
                f"    v3:   {new_status}\n"
                f"    q:    {question}"
            )
        print()

    print(
        "Methodology note: external v1 is retired development data. "
        "This comparison is a regression diagnostic only and cannot "
        "establish candidate-v3 generalisation."
    )
    print()
    print("Candidate-v3 external-v1 development scoring: PASS")


if __name__ == "__main__":
    main()
