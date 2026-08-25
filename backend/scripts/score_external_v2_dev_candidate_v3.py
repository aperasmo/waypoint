"""Score candidate v3 on RETIRED external holdout v2 development data.

This is a development comparison only. External v2 has already been inspected
and used to inform candidate v3, so these results are NOT fresh generalisation
evidence.

The scorer validates:
- frozen external-v2 gold;
- historical first untouched v2 prediction artifact;
- candidate-v3 development prediction artifact.

It performs:
- no model calls;
- no retrieval or reranking;
- no database writes.

Run from backend/:
    uv run python -m py_compile scripts/score_external_v2_dev_candidate_v3.py
    uv run python -m scripts.score_external_v2_dev_candidate_v3
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

GOLD_PATH = BACKEND_DIR / "tests" / "external_adjudication_gold_v2.json"
BASELINE_PATH = BACKEND_DIR / "tests" / "external_predictions_blind_v2.json"
V3_PATH = BACKEND_DIR / "tests" / "external_predictions_dev_v2_candidate_v3.json"

EXPECTED_GOLD_SHA256 = (
    "D584326117A4CEF64C869225AD9186FF"
    "95C1D0753ED93706A0748C6ABCC4FA36"
)
EXPECTED_BASELINE_SHA256 = (
    "BCC045922577E84AA89CBBE19587E56C"
    "634ABEB119F9476191B050FB2459493D"
)
EXPECTED_V3_SHA256 = (
    "758A91DBB6FB498BCA19256B4C7889CB"
    "F82A6DCEE6BA8CFC1B48C934C24B52FD"
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
        raise RuntimeError(f"{path.name}: JSON root must be an object.")
    return payload


def pct(n: int | float, d: int | float) -> str:
    if not d:
        return "n/a"
    return f"{100.0 * n / d:.1f}%"


def build_maps(gold: dict, predictions: dict):
    gold_items = gold.get("questions")
    pred_items = predictions.get("predictions")

    if not isinstance(gold_items, list) or len(gold_items) != 60:
        raise RuntimeError("Gold must contain exactly 60 questions.")
    if not isinstance(pred_items, list) or len(pred_items) != 60:
        raise RuntimeError("Predictions must contain exactly 60 cases.")

    gold_by_id = {}
    for item in gold_items:
        case_id = item.get("candidate_id")
        if case_id in gold_by_id:
            raise RuntimeError(f"Duplicate gold case_id: {case_id}")
        gold_by_id[case_id] = item

    pred_by_id = {}
    for item in pred_items:
        case_id = item.get("case_id")
        if case_id in pred_by_id:
            raise RuntimeError(f"Duplicate prediction case_id: {case_id}")
        pred_by_id[case_id] = item

    if set(gold_by_id) != set(pred_by_id):
        raise RuntimeError("Gold and prediction case sets differ.")

    for case_id in gold_by_id:
        if gold_by_id[case_id]["question"] != pred_by_id[case_id]["question"]:
            raise RuntimeError(f"{case_id}: question text changed.")

    return gold_by_id, pred_by_id


def score(gold_by_id: dict, pred_by_id: dict) -> dict:
    gold_counts = Counter()
    correct_counts = Counter()
    pred_counts = Counter()
    confusion = {status: Counter() for status in STATUSES}

    correct = 0

    for case_id, gold_item in gold_by_id.items():
        gold_status = gold_item["evidence_status"]
        pred_status = pred_by_id[case_id]["evidence_status"]

        if gold_status not in STATUSES or pred_status not in STATUSES:
            raise RuntimeError(f"{case_id}: invalid evidence status.")

        gold_counts[gold_status] += 1
        pred_counts[pred_status] += 1
        confusion[gold_status][pred_status] += 1

        if gold_status == pred_status:
            correct += 1
            correct_counts[gold_status] += 1

    clusters = defaultdict(list)
    for case_id, gold_item in gold_by_id.items():
        clusters[gold_item["source_url"]].append(case_id)

    if len(clusters) != 20:
        raise RuntimeError(f"Expected 20 source clusters, got {len(clusters)}.")

    cluster_scores = []
    full_clusters = 0

    for source_url, case_ids in clusters.items():
        if len(case_ids) != 3:
            raise RuntimeError(
                f"Expected 3 cases in source cluster: {source_url}"
            )

        cluster_correct = sum(
            gold_by_id[cid]["evidence_status"]
            == pred_by_id[cid]["evidence_status"]
            for cid in case_ids
        )

        cluster_scores.append(cluster_correct / 3)

        if cluster_correct == 3:
            full_clusters += 1

    sufficient_ids = [
        case_id
        for case_id, item in gold_by_id.items()
        if item["evidence_status"] == "sufficient"
    ]

    any_expected = 0
    all_expected = 0

    for case_id in sufficient_ids:
        expected = set(gold_by_id[case_id]["expected_sections"])
        cited = {
            citation.get("section_code")
            for citation in pred_by_id[case_id].get("citations", [])
            if isinstance(citation, dict)
        }

        any_expected += bool(expected & cited)
        all_expected += expected <= cited

    return {
        "correct": correct,
        "gold_counts": gold_counts,
        "correct_counts": correct_counts,
        "pred_counts": pred_counts,
        "confusion": confusion,
        "cluster_macro": sum(cluster_scores) / len(cluster_scores),
        "full_clusters": full_clusters,
        "any_expected": any_expected,
        "all_expected": all_expected,
        "sufficient_count": len(sufficient_ids),
    }


def main() -> None:
    require_sha(GOLD_PATH, EXPECTED_GOLD_SHA256, "Frozen external-v2 gold")
    require_sha(
        BASELINE_PATH,
        EXPECTED_BASELINE_SHA256,
        "Historical untouched v2 predictions",
    )
    require_sha(
        V3_PATH,
        EXPECTED_V3_SHA256,
        "Candidate-v3 development predictions",
    )

    gold = load_json(GOLD_PATH)
    baseline = load_json(BASELINE_PATH)
    v3 = load_json(V3_PATH)

    if gold.get("status") != "FROZEN_DO_NOT_TUNE_ON_THIS_SET":
        raise RuntimeError("Frozen gold status changed.")

    if baseline.get("status") != "FIRST_UNTOUCHED_HOLDOUT_V2_PREDICTIONS":
        raise RuntimeError("Historical prediction status changed.")

    if v3.get("status") != "DEVELOPMENT_PREDICTIONS_NOT_UNTOUCHED_HOLDOUT":
        raise RuntimeError("Candidate-v3 prediction status is not development.")

    if v3.get("runtime_ask_sha256") != EXPECTED_V3_ASK_SHA256:
        raise RuntimeError("Candidate-v3 runtime ask SHA mismatch.")

    if v3.get("historical_first_predictions_sha256") != EXPECTED_BASELINE_SHA256:
        raise RuntimeError(
            "Candidate-v3 artifact is not linked to historical first predictions."
        )

    gold_by_id, baseline_by_id = build_maps(gold, baseline)
    gold_by_id_v3, v3_by_id = build_maps(gold, v3)

    if set(gold_by_id) != set(gold_by_id_v3):
        raise RuntimeError("Gold mappings unexpectedly differ.")

    old = score(gold_by_id, baseline_by_id)
    new = score(gold_by_id, v3_by_id)

    gains = []
    regressions = []
    changed_wrong = []

    for case_id, gold_item in gold_by_id.items():
        gold_status = gold_item["evidence_status"]
        old_status = baseline_by_id[case_id]["evidence_status"]
        new_status = v3_by_id[case_id]["evidence_status"]

        old_ok = old_status == gold_status
        new_ok = new_status == gold_status

        if not old_ok and new_ok:
            gains.append(
                (case_id, gold_status, old_status, new_status, gold_item["question"])
            )
        elif old_ok and not new_ok:
            regressions.append(
                (case_id, gold_status, old_status, new_status, gold_item["question"])
            )
        elif not old_ok and not new_ok and old_status != new_status:
            changed_wrong.append(
                (case_id, gold_status, old_status, new_status, gold_item["question"])
            )

    print("Waypoint candidate-v3 external-v2 DEVELOPMENT score")
    print("=" * 52)
    print(f"Gold SHA256:               {sha256(GOLD_PATH)}")
    print(f"Historical pred SHA256:    {sha256(BASELINE_PATH)}")
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
        f"Historical untouched v2:   {old['correct']}/60 "
        f"({pct(old['correct'], 60)})"
    )
    print(
        f"Candidate v3 development:  {new['correct']}/60 "
        f"({pct(new['correct'], 60)})"
    )
    print(
        f"Delta:                      {new['correct'] - old['correct']:+d} correct "
        f"({100 * (new['correct'] - old['correct']) / 60:+.1f} pp)"
    )
    print()

    print("Per-class comparison")
    print("-" * 72)
    print(
        f"{'class':<27}"
        f"{'historical':>18}"
        f"{'candidate v3':>18}"
        f"{'delta':>9}"
    )

    for status in STATUSES:
        total = new["gold_counts"][status]
        old_correct = old["correct_counts"][status]
        new_correct = new["correct_counts"][status]
        delta_pp = 100 * (new_correct - old_correct) / total

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
        print(f"{status:<27}{new['pred_counts'][status]:>3}")
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

    print("Source-cluster comparison")
    print("-" * 72)
    print(
        f"Historical cluster macro:  "
        f"{100 * old['cluster_macro']:.1f}%"
    )
    print(
        f"Candidate-v3 cluster macro:"
        f" {100 * new['cluster_macro']:.1f}%"
    )
    print(
        f"Historical full clusters:  {old['full_clusters']}/20 "
        f"({pct(old['full_clusters'], 20)})"
    )
    print(
        f"Candidate-v3 full clusters:{new['full_clusters']:>3}/20 "
        f"({pct(new['full_clusters'], 20)})"
    )
    print()

    print("Sufficient-case citation comparison")
    print("-" * 72)
    n = new["sufficient_count"]
    print(
        f"Historical any expected:   {old['any_expected']}/{n} "
        f"({pct(old['any_expected'], n)})"
    )
    print(
        f"Candidate-v3 any expected: {new['any_expected']}/{n} "
        f"({pct(new['any_expected'], n)})"
    )
    print(
        f"Historical all expected:   {old['all_expected']}/{n} "
        f"({pct(old['all_expected'], n)})"
    )
    print(
        f"Candidate-v3 all expected: {new['all_expected']}/{n} "
        f"({pct(new['all_expected'], n)})"
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
                f"    old:  {old_status}\n"
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
                f"    old:  {old_status}\n"
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
                f"    old:  {old_status}\n"
                f"    v3:   {new_status}\n"
                f"    q:    {question}"
            )
        print()

    print(
        "Methodology note: external v2 is retired development data. "
        "This comparison may guide diagnostics, but cannot establish "
        "candidate-v3 generalisation."
    )
    print()
    print("Candidate-v3 external-v2 development scoring: PASS")


if __name__ == "__main__":
    main()
