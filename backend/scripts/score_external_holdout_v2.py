"""Score the FIRST untouched external holdout-v2 prediction artifact.

This scorer performs no runtime/model/retrieval/reranker/database calls.

It validates the exact frozen gold, blind linkage, candidate freeze SHA, and
prediction artifact before scoring.

Metrics:
- question-level evidence-status accuracy
- per-class accuracy
- evidence-status confusion matrix
- source-cluster macro accuracy
- fully-correct source clusters
- sufficient-case citation coverage
- evidence-status failure list

Run from backend/:
    uv run python -m py_compile scripts/score_external_holdout_v2.py
    uv run python -m scripts.score_external_holdout_v2
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

GOLD_PATH = BACKEND_DIR / "tests" / "external_adjudication_gold_v2.json"
BLIND_PATH = BACKEND_DIR / "tests" / "external_questions_blind_v2.json"
PREDICTIONS_PATH = BACKEND_DIR / "tests" / "external_predictions_blind_v2.json"

EXPECTED_GOLD_SHA256 = (
    "D584326117A4CEF64C869225AD9186FF"
    "95C1D0753ED93706A0748C6ABCC4FA36"
)
EXPECTED_BLIND_SHA256 = (
    "9A0D08AD48D49D6F83509F57251AD191"
    "BEAE1BF5DE05D680670BFA46961B1FED"
)
EXPECTED_PREDICTIONS_SHA256 = (
    "BCC045922577E84AA89CBBE19587E56C"
    "634ABEB119F9476191B050FB2459493D"
)
EXPECTED_ASK_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)
EXPECTED_CANDIDATE_FREEZE_SHA256 = (
    "0600D79FFC375C7CC8FC358722EE51A9"
    "8B0D979188F61FF8B4CBD7412A1CB03C"
)

EXPECTED_GOLD_SCHEMA = "waypoint-external-adjudication-gold-v2"
EXPECTED_BLIND_SCHEMA = "waypoint-external-questions-blind-v2"
EXPECTED_PREDICTIONS_SCHEMA = "waypoint-external-predictions-blind-v2"

STATUSES = (
    "sufficient",
    "corpus_gap",
    "external_source_required",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_file(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")


def require_sha(path: Path, expected: str) -> None:
    actual = sha256(path)
    if actual != expected:
        raise SystemExit(
            f"SHA mismatch for {path}\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Refusing to score a changed evaluation artifact."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: JSON root must be an object.")
    return payload


def pct(numerator: int | float, denominator: int | float) -> str:
    if denominator == 0:
        return "n/a"
    return f"{100.0 * numerator / denominator:.1f}%"


def main() -> None:
    for path in (GOLD_PATH, BLIND_PATH, PREDICTIONS_PATH):
        require_file(path)

    require_sha(GOLD_PATH, EXPECTED_GOLD_SHA256)
    require_sha(BLIND_PATH, EXPECTED_BLIND_SHA256)
    require_sha(PREDICTIONS_PATH, EXPECTED_PREDICTIONS_SHA256)

    gold = load_json(GOLD_PATH)
    blind = load_json(BLIND_PATH)
    predictions = load_json(PREDICTIONS_PATH)

    if gold.get("schema") != EXPECTED_GOLD_SCHEMA:
        raise RuntimeError(f"Unexpected gold schema: {gold.get('schema')!r}")
    if blind.get("schema") != EXPECTED_BLIND_SCHEMA:
        raise RuntimeError(f"Unexpected blind schema: {blind.get('schema')!r}")
    if predictions.get("schema") != EXPECTED_PREDICTIONS_SCHEMA:
        raise RuntimeError(
            f"Unexpected prediction schema: {predictions.get('schema')!r}"
        )

    if gold.get("status") != "FROZEN_DO_NOT_TUNE_ON_THIS_SET":
        raise RuntimeError("Gold file is not in frozen status.")
    if blind.get("status") != "FROZEN_BLIND_UNSCORED_HOLDOUT_V2":
        raise RuntimeError("Blind file has unexpected status.")
    if predictions.get("status") != "FIRST_UNTOUCHED_HOLDOUT_V2_PREDICTIONS":
        raise RuntimeError("Prediction file is not the first untouched v2 run.")

    if blind.get("source_gold_sha256") != EXPECTED_GOLD_SHA256:
        raise RuntimeError("Blind file is not linked to the expected frozen gold.")
    if predictions.get("source_blind_sha256") != EXPECTED_BLIND_SHA256:
        raise RuntimeError("Predictions are not linked to the expected blind file.")
    if predictions.get("source_gold_sha256_recorded_in_blind") != EXPECTED_GOLD_SHA256:
        raise RuntimeError("Prediction metadata does not preserve the gold linkage.")

    for payload_name, payload in (
        ("gold", gold),
        ("blind", blind),
        ("predictions", predictions),
    ):
        if payload.get("candidate_freeze_sha256") != EXPECTED_CANDIDATE_FREEZE_SHA256:
            raise RuntimeError(
                f"{payload_name}: candidate freeze SHA does not match."
            )
        if payload.get("runtime_ask_sha256") != EXPECTED_ASK_SHA256:
            raise RuntimeError(
                f"{payload_name}: runtime ask.py SHA does not match."
            )

    gold_questions = gold.get("questions")
    blind_questions = blind.get("questions")
    prediction_items = predictions.get("predictions")

    if not isinstance(gold_questions, list) or len(gold_questions) != 60:
        raise RuntimeError("Gold must contain exactly 60 questions.")
    if not isinstance(blind_questions, list) or len(blind_questions) != 60:
        raise RuntimeError("Blind input must contain exactly 60 questions.")
    if not isinstance(prediction_items, list) or len(prediction_items) != 60:
        raise RuntimeError("Predictions must contain exactly 60 questions.")

    if gold.get("included_question_count") != 60:
        raise RuntimeError("Expected all 60 gold questions to be included.")
    if blind.get("question_count") != 60:
        raise RuntimeError("Blind metadata question_count changed.")
    if predictions.get("prediction_count") != 60:
        raise RuntimeError("Prediction metadata count changed.")

    gold_by_id: dict[str, dict] = {}
    for item in gold_questions:
        if item.get("benchmark_status") != "include":
            raise RuntimeError(
                f"{item.get('candidate_id')}: unexpected excluded case."
            )
        case_id = item.get("candidate_id")
        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Gold case has invalid candidate_id.")
        if case_id in gold_by_id:
            raise RuntimeError(f"Duplicate gold case_id: {case_id}")
        gold_by_id[case_id] = item

    blind_by_id: dict[str, dict] = {}
    for item in blind_questions:
        case_id = item.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Blind case has invalid case_id.")
        if case_id in blind_by_id:
            raise RuntimeError(f"Duplicate blind case_id: {case_id}")
        blind_by_id[case_id] = item

    pred_by_id: dict[str, dict] = {}
    for item in prediction_items:
        case_id = item.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Prediction has invalid case_id.")
        if case_id in pred_by_id:
            raise RuntimeError(f"Duplicate prediction case_id: {case_id}")
        pred_by_id[case_id] = item

    if set(gold_by_id) != set(blind_by_id) or set(gold_by_id) != set(pred_by_id):
        raise RuntimeError("Gold, blind, and prediction case sets differ.")

    # Question text integrity.
    for case_id, gold_item in gold_by_id.items():
        expected_question = gold_item.get("question")
        if blind_by_id[case_id].get("question") != expected_question:
            raise RuntimeError(f"{case_id}: blind question text changed.")
        if pred_by_id[case_id].get("question") != expected_question:
            raise RuntimeError(f"{case_id}: prediction question text changed.")

    correct = 0
    gold_counts: Counter = Counter()
    correct_by_gold: Counter = Counter()
    predicted_counts: Counter = Counter()

    confusion = {
        status: Counter()
        for status in STATUSES
    }

    failures: list[dict] = []

    for case_id, gold_item in gold_by_id.items():
        gold_status = gold_item.get("evidence_status")
        pred_status = pred_by_id[case_id].get("evidence_status")

        if gold_status not in STATUSES:
            raise RuntimeError(
                f"{case_id}: invalid gold evidence_status {gold_status!r}."
            )
        if pred_status not in STATUSES:
            raise RuntimeError(
                f"{case_id}: invalid predicted evidence_status {pred_status!r}."
            )

        gold_counts[gold_status] += 1
        predicted_counts[pred_status] += 1
        confusion[gold_status][pred_status] += 1

        if gold_status == pred_status:
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
                        citation.get("section_code")
                        for citation in pred_by_id[case_id].get(
                            "citations", []
                        )
                        if isinstance(citation, dict)
                    ],
                }
            )

    # Source-cluster macro accuracy.
    source_clusters: dict[str, list[str]] = defaultdict(list)

    for case_id, gold_item in gold_by_id.items():
        source_url = gold_item.get("source_url")
        if not isinstance(source_url, str) or not source_url:
            raise RuntimeError(
                f"{case_id}: missing source_url for cluster scoring."
            )
        source_clusters[source_url].append(case_id)

    if len(source_clusters) != 20:
        raise RuntimeError(
            f"Expected 20 source clusters, got {len(source_clusters)}."
        )

    cluster_accuracies: list[float] = []
    fully_correct_clusters = 0

    for source_url, case_ids in source_clusters.items():
        if len(case_ids) != 3:
            raise RuntimeError(
                f"Source cluster does not contain exactly 3 cases: {source_url}"
            )

        cluster_correct = sum(
            pred_by_id[case_id]["evidence_status"]
            == gold_by_id[case_id]["evidence_status"]
            for case_id in case_ids
        )

        cluster_accuracy = cluster_correct / len(case_ids)
        cluster_accuracies.append(cluster_accuracy)

        if cluster_correct == len(case_ids):
            fully_correct_clusters += 1

    cluster_macro = sum(cluster_accuracies) / len(cluster_accuracies)

    # Sufficient-case citation coverage.
    sufficient_ids = [
        case_id
        for case_id, item in gold_by_id.items()
        if item["evidence_status"] == "sufficient"
    ]

    any_expected_cited = 0
    all_expected_cited = 0

    for case_id in sufficient_ids:
        expected = set(gold_by_id[case_id].get("expected_sections", []))

        if not expected:
            raise RuntimeError(
                f"{case_id}: sufficient gold case has no expected sections."
            )

        cited = {
            citation.get("section_code")
            for citation in pred_by_id[case_id].get("citations", [])
            if isinstance(citation, dict)
            and isinstance(citation.get("section_code"), str)
        }

        if expected & cited:
            any_expected_cited += 1
        if expected <= cited:
            all_expected_cited += 1

    total = len(gold_by_id)

    print("Waypoint external holdout-v2 score")
    print("=" * 36)
    print(f"Frozen gold:               {GOLD_PATH}")
    print(f"Blind input:               {BLIND_PATH}")
    print(f"Predictions:               {PREDICTIONS_PATH}")
    print()
    print(f"Gold SHA256:               {sha256(GOLD_PATH)}")
    print(f"Blind SHA256:              {sha256(BLIND_PATH)}")
    print(f"Predictions SHA256:        {sha256(PREDICTIONS_PATH)}")
    print(f"Frozen ask.py SHA256:      {EXPECTED_ASK_SHA256}")
    print()
    print("Evaluation status:         FIRST UNTOUCHED HOLDOUT-V2 SCORE")
    print("Runtime/model calls:       NONE")
    print("Retrieval/reranker calls:  NONE")
    print("Database writes:           NONE")
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
    for status in STATUSES:
        class_total = gold_counts[status]
        class_correct = correct_by_gold[status]
        print(
            f"{status:<27}"
            f"{class_correct:>3}/{class_total:<3} "
            f"({pct(class_correct, class_total)})"
        )
    print()

    print("Predicted class distribution")
    print("-" * 72)
    for status in STATUSES:
        print(f"{status:<27}{predicted_counts[status]:>3}")
    print()

    print("Evidence-status confusion matrix")
    print("-" * 72)
    print(
        f"{'gold / predicted':<29}"
        f"{'sufficient':>12}"
        f"{'corpus_gap':>12}"
        f"{'external':>12}"
    )
    for gold_status in STATUSES:
        row = confusion[gold_status]
        print(
            f"{gold_status:<29}"
            f"{row['sufficient']:>12}"
            f"{row['corpus_gap']:>12}"
            f"{row['external_source_required']:>12}"
        )
    print()

    print("Source-cluster metrics")
    print("-" * 72)
    print(f"Source clusters:            {len(source_clusters)}")
    print(
        f"Source-cluster macro acc.:  "
        f"{100.0 * cluster_macro:.1f}%"
    )
    print(
        f"Fully correct clusters:     "
        f"{fully_correct_clusters}/{len(source_clusters)} "
        f"({pct(fully_correct_clusters, len(source_clusters))})"
    )
    print()

    print("Sufficient-case citation metrics")
    print("-" * 72)
    print(f"Sufficient cases:           {len(sufficient_ids)}")
    print(
        f"Any expected section cited: "
        f"{any_expected_cited}/{len(sufficient_ids)} "
        f"({pct(any_expected_cited, len(sufficient_ids))})"
    )
    print(
        f"All expected sections cited:"
        f" {all_expected_cited}/{len(sufficient_ids)} "
        f"({pct(all_expected_cited, len(sufficient_ids))})"
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
    print(
        "Methodology note: external holdout v2 has now served as the "
        "first untouched generalisation test. Any tuning informed by these "
        "results makes v2 development/diagnostic data for future candidates."
    )
    print()
    print("External holdout-v2 scoring: PASS")


if __name__ == "__main__":
    main()
