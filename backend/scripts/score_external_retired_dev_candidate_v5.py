"""Score candidate v5 on both RETIRED external development sets.

This is DEVELOPMENT / DIAGNOSTIC ONLY.

It compares:
- frozen candidate v2 historical predictions;
- candidate v5 factorised-evidence predictions;

against already-retired external v1 and v2 gold.

It performs:
- no answer-model calls;
- no retrieval calls;
- no embedding calls;
- no reranking;
- no database writes;
- no runtime modification.

Run from backend/:
    uv run python -m py_compile scripts/score_external_retired_dev_candidate_v5.py
    uv run python -m scripts.score_external_retired_dev_candidate_v5
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

V1_GOLD_PATH = (
    BACKEND_DIR / "tests" / "external_adjudication_gold_v1.json"
)
V2_GOLD_PATH = (
    BACKEND_DIR / "tests" / "external_adjudication_gold_v2.json"
)

V1_BASELINE_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v1_evidence_adequacy_v2.json"
)
V2_BASELINE_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_blind_v2.json"
)

V1_V5_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v1_candidate_v5.json"
)
V2_V5_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v2_candidate_v5.json"
)

EXPECTED_V1_GOLD_SHA256 = (
    "11D21AF433C30F99665915F0536FFE30"
    "B4AE1E76972DB6F036BED38B2D5ECCB3"
)
EXPECTED_V2_GOLD_SHA256 = (
    "D584326117A4CEF64C869225AD9186FF"
    "95C1D0753ED93706A0748C6ABCC4FA36"
)

EXPECTED_V1_BASELINE_SHA256 = (
    "0F1E84F74DC1B50C6217A1909A48A5F"
    "F922FA537029737E1E8CE3769488FD541"
)
EXPECTED_V2_BASELINE_SHA256 = (
    "BCC045922577E84AA89CBBE19587E56C"
    "634ABEB119F9476191B050FB2459493D"
)

EXPECTED_V1_V5_SHA256 = (
    "BFB75B7AB9AE9385AAC88C6956407807"
    "678229FDD04E5F0D4A1B7AAAE9569DAB"
)
EXPECTED_V2_V5_SHA256 = (
    "70906FB9E78FA45F983EEADC9375AC1F"
    "82FC092716B05B564A109E96E6D1899D"
)

EXPECTED_V2_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)
EXPECTED_V5_CANDIDATE_SHA256 = (
    "6B741B99792A5131BC466A98DDFC8C38"
    "4CD14F803C262A9A396443E631DF61B6"
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
            "Refusing to score changed development artifacts."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: JSON root must be an object.")

    return payload


def pct(n: int, d: int) -> str:
    if d == 0:
        return "n/a"
    return f"{100.0 * n / d:.1f}%"


def gold_map(
    payload: dict,
    *,
    expected_schema: str,
    expected_count: int,
) -> dict[str, dict]:
    if payload.get("schema") != expected_schema:
        raise RuntimeError(
            f"Unexpected gold schema: {payload.get('schema')!r}"
        )

    if payload.get("status") != "FROZEN_DO_NOT_TUNE_ON_THIS_SET":
        raise RuntimeError("Gold artifact status changed.")

    questions = payload.get("questions")

    if not isinstance(questions, list):
        raise RuntimeError("Gold questions must be a list.")

    result = {}

    for item in questions:
        if item.get("benchmark_status") != "include":
            continue

        case_id = item.get("candidate_id")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Gold item has invalid candidate_id.")

        if case_id in result:
            raise RuntimeError(f"Duplicate gold case_id: {case_id}")

        status = item.get("evidence_status")

        if status not in STATUSES:
            raise RuntimeError(
                f"{case_id}: invalid gold evidence status."
            )

        result[case_id] = item

    if len(result) != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} included gold cases, "
            f"got {len(result)}."
        )

    return result


def prediction_map(
    payload: dict,
    *,
    expected_schema: str,
    expected_count: int,
    candidate: str,
) -> dict[str, dict]:
    if payload.get("schema") != expected_schema:
        raise RuntimeError(
            f"Unexpected prediction schema: {payload.get('schema')!r}"
        )

    predictions = payload.get("predictions")

    if not isinstance(predictions, list):
        raise RuntimeError("Prediction items must be a list.")

    if len(predictions) != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} predictions, "
            f"got {len(predictions)}."
        )

    result = {}

    for item in predictions:
        case_id = item.get("case_id")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Prediction item has invalid case_id.")

        if case_id in result:
            raise RuntimeError(f"Duplicate prediction case_id: {case_id}")

        status = item.get("evidence_status")

        if status not in STATUSES:
            raise RuntimeError(
                f"{case_id}: invalid predicted evidence status."
            )

        result[case_id] = item

    if candidate == "v5":
        if payload.get(
            "candidate_source_sha256"
        ) != EXPECTED_V5_CANDIDATE_SHA256:
            raise RuntimeError("Candidate-v5 SHA linkage changed.")

        if payload.get(
            "production_runtime_sha256"
        ) != EXPECTED_V2_RUNTIME_SHA256:
            raise RuntimeError("Candidate-v5 production linkage changed.")

        if payload.get("production_runtime_replaced") is not False:
            raise RuntimeError(
                "Candidate-v5 artifact claims production replacement."
            )

    return result


def validate_alignment(
    gold: dict[str, dict],
    predictions: dict[str, dict],
    label: str,
) -> None:
    if set(gold) != set(predictions):
        raise RuntimeError(f"{label}: case ID sets differ.")

    for case_id in gold:
        if gold[case_id].get("question") != predictions[case_id].get(
            "question"
        ):
            raise RuntimeError(
                f"{label}: question changed for {case_id}."
            )


def score(
    gold: dict[str, dict],
    predictions: dict[str, dict],
    *,
    include_clusters: bool,
) -> dict:
    gold_counts = Counter()
    correct_counts = Counter()
    predicted_counts = Counter()
    confusion = {status: Counter() for status in STATUSES}

    correct = 0
    false_sufficient = 0
    nonsufficient_gold = 0

    for case_id, gold_item in gold.items():
        gold_status = gold_item["evidence_status"]
        pred_status = predictions[case_id]["evidence_status"]

        gold_counts[gold_status] += 1
        predicted_counts[pred_status] += 1
        confusion[gold_status][pred_status] += 1

        if gold_status == pred_status:
            correct += 1
            correct_counts[gold_status] += 1

        if gold_status != "sufficient":
            nonsufficient_gold += 1
            if pred_status == "sufficient":
                false_sufficient += 1

    sufficient_ids = [
        case_id
        for case_id, item in gold.items()
        if item["evidence_status"] == "sufficient"
    ]

    any_expected = 0
    all_expected = 0
    no_citations = 0

    for case_id in sufficient_ids:
        expected = set(
            gold[case_id].get("expected_sections", [])
        )

        if not expected:
            raise RuntimeError(
                f"{case_id}: sufficient gold has no expected sections."
            )

        citations = predictions[case_id].get("citations", [])

        cited = {
            item.get("section_code")
            for item in citations
            if isinstance(item, dict)
            and isinstance(item.get("section_code"), str)
        }

        if not cited:
            no_citations += 1

        any_expected += bool(expected & cited)
        all_expected += expected <= cited

    result = {
        "correct": correct,
        "gold_counts": gold_counts,
        "correct_counts": correct_counts,
        "predicted_counts": predicted_counts,
        "confusion": confusion,
        "false_sufficient": false_sufficient,
        "nonsufficient_gold": nonsufficient_gold,
        "sufficient_count": len(sufficient_ids),
        "any_expected": any_expected,
        "all_expected": all_expected,
        "no_citations": no_citations,
    }

    if include_clusters:
        clusters = defaultdict(list)

        for case_id, item in gold.items():
            source_url = item.get("source_url")

            if not isinstance(source_url, str) or not source_url:
                raise RuntimeError(
                    f"{case_id}: v2 gold missing source_url."
                )

            clusters[source_url].append(case_id)

        if len(clusters) != 20:
            raise RuntimeError(
                f"Expected 20 v2 source clusters, got {len(clusters)}."
            )

        cluster_scores = []
        full_clusters = 0

        for source_url, case_ids in clusters.items():
            if len(case_ids) != 3:
                raise RuntimeError(
                    f"Expected 3 cases in cluster: {source_url}"
                )

            cluster_correct = sum(
                gold[cid]["evidence_status"]
                == predictions[cid]["evidence_status"]
                for cid in case_ids
            )

            cluster_scores.append(cluster_correct / 3)

            if cluster_correct == 3:
                full_clusters += 1

        result["cluster_macro"] = (
            sum(cluster_scores) / len(cluster_scores)
        )
        result["full_clusters"] = full_clusters

    return result


def comparison(
    gold: dict[str, dict],
    baseline: dict[str, dict],
    v5: dict[str, dict],
) -> dict:
    gains = []
    regressions = []
    wrong_to_different_wrong = []
    unchanged_correct = []
    unchanged_wrong = []

    for case_id, gold_item in gold.items():
        gold_status = gold_item["evidence_status"]
        base_status = baseline[case_id]["evidence_status"]
        v5_status = v5[case_id]["evidence_status"]

        base_ok = base_status == gold_status
        v5_ok = v5_status == gold_status

        item = {
            "case_id": case_id,
            "gold": gold_status,
            "baseline": base_status,
            "v5": v5_status,
        }

        if not base_ok and v5_ok:
            gains.append(item)
        elif base_ok and not v5_ok:
            regressions.append(item)
        elif not base_ok and not v5_ok and base_status != v5_status:
            wrong_to_different_wrong.append(item)
        elif base_ok and v5_ok:
            unchanged_correct.append(item)
        else:
            unchanged_wrong.append(item)

    return {
        "gains": gains,
        "regressions": regressions,
        "wrong_to_different_wrong": wrong_to_different_wrong,
        "unchanged_correct": unchanged_correct,
        "unchanged_wrong": unchanged_wrong,
    }


def print_score(
    name: str,
    baseline_score: dict,
    v5_score: dict,
    comp: dict,
    total: int,
    *,
    show_clusters: bool,
) -> None:
    print()
    print(name)
    print("-" * 72)
    print(
        f"Candidate v2: {baseline_score['correct']}/{total} "
        f"({pct(baseline_score['correct'], total)})"
    )
    print(
        f"Candidate v5: {v5_score['correct']}/{total} "
        f"({pct(v5_score['correct'], total)})"
    )
    delta = v5_score["correct"] - baseline_score["correct"]
    delta_pp = 100.0 * delta / total
    print(f"Delta:        {delta:+d} correct ({delta_pp:+.1f} pp)")
    print()

    print("Per-class recall")
    for status in STATUSES:
        gold_n = v5_score["gold_counts"][status]
        base_n = baseline_score["correct_counts"][status]
        v5_n = v5_score["correct_counts"][status]
        print(
            f"  {status:<26}"
            f"v2 {base_n:>2}/{gold_n:<2} {pct(base_n, gold_n):>7}"
            f"   v5 {v5_n:>2}/{gold_n:<2} {pct(v5_n, gold_n):>7}"
        )

    print()
    print("Candidate-v5 predicted distribution")
    for status in STATUSES:
        print(
            f"  {status:<26}"
            f"{v5_score['predicted_counts'][status]}"
        )

    print()
    print("Candidate-v5 confusion matrix")
    print(
        "gold / predicted               sufficient  corpus_gap    external"
    )
    for gold_status in STATUSES:
        row = v5_score["confusion"][gold_status]
        print(
            f"{gold_status:<32}"
            f"{row['sufficient']:>10}"
            f"{row['corpus_gap']:>12}"
            f"{row['external_source_required']:>12}"
        )

    print()
    print(
        "False-sufficiency among non-sufficient gold: "
        f"{v5_score['false_sufficient']}/"
        f"{v5_score['nonsufficient_gold']} "
        f"({pct(v5_score['false_sufficient'], v5_score['nonsufficient_gold'])})"
    )

    print()
    print("Sufficient-case citation coverage")
    print(
        f"  Any expected: "
        f"{v5_score['any_expected']}/{v5_score['sufficient_count']} "
        f"({pct(v5_score['any_expected'], v5_score['sufficient_count'])})"
    )
    print(
        f"  All expected: "
        f"{v5_score['all_expected']}/{v5_score['sufficient_count']} "
        f"({pct(v5_score['all_expected'], v5_score['sufficient_count'])})"
    )
    print(
        f"  No citations: "
        f"{v5_score['no_citations']}/{v5_score['sufficient_count']}"
    )

    if show_clusters:
        print()
        print(
            f"Source-cluster macro accuracy: "
            f"{100.0 * v5_score['cluster_macro']:.1f}%"
        )
        print(
            f"Fully correct source clusters: "
            f"{v5_score['full_clusters']}/20"
        )

    print()
    print(
        f"Gains: {len(comp['gains'])}   "
        f"Regressions: {len(comp['regressions'])}   "
        f"Wrong -> different wrong: "
        f"{len(comp['wrong_to_different_wrong'])}"
    )


def main() -> None:
    require_sha(
        V1_GOLD_PATH,
        EXPECTED_V1_GOLD_SHA256,
        "Frozen external-v1 gold",
    )
    require_sha(
        V2_GOLD_PATH,
        EXPECTED_V2_GOLD_SHA256,
        "Frozen external-v2 gold",
    )
    require_sha(
        V1_BASELINE_PATH,
        EXPECTED_V1_BASELINE_SHA256,
        "Candidate-v2 external-v1 predictions",
    )
    require_sha(
        V2_BASELINE_PATH,
        EXPECTED_V2_BASELINE_SHA256,
        "Candidate-v2 external-v2 predictions",
    )
    require_sha(
        V1_V5_PATH,
        EXPECTED_V1_V5_SHA256,
        "Candidate-v5 external-v1 predictions",
    )
    require_sha(
        V2_V5_PATH,
        EXPECTED_V2_V5_SHA256,
        "Candidate-v5 external-v2 predictions",
    )

    v1_gold = gold_map(
        load_json(V1_GOLD_PATH),
        expected_schema="waypoint-external-adjudication-gold-v1",
        expected_count=51,
    )
    v2_gold = gold_map(
        load_json(V2_GOLD_PATH),
        expected_schema="waypoint-external-adjudication-gold-v2",
        expected_count=60,
    )

    v1_base = prediction_map(
        load_json(V1_BASELINE_PATH),
        expected_schema="waypoint-external-predictions-dev-v1-v2",
        expected_count=51,
        candidate="v2",
    )
    v2_base = prediction_map(
        load_json(V2_BASELINE_PATH),
        expected_schema="waypoint-external-predictions-blind-v2",
        expected_count=60,
        candidate="v2",
    )

    v1_v5 = prediction_map(
        load_json(V1_V5_PATH),
        expected_schema=(
            "waypoint-external-predictions-dev-v1-candidate-v5"
        ),
        expected_count=51,
        candidate="v5",
    )
    v2_v5 = prediction_map(
        load_json(V2_V5_PATH),
        expected_schema=(
            "waypoint-external-predictions-dev-v2-candidate-v5"
        ),
        expected_count=60,
        candidate="v5",
    )

    validate_alignment(v1_gold, v1_base, "v1 baseline")
    validate_alignment(v1_gold, v1_v5, "v1 candidate-v5")
    validate_alignment(v2_gold, v2_base, "v2 baseline")
    validate_alignment(v2_gold, v2_v5, "v2 candidate-v5")

    v1_base_score = score(
        v1_gold,
        v1_base,
        include_clusters=False,
    )
    v1_v5_score = score(
        v1_gold,
        v1_v5,
        include_clusters=False,
    )
    v2_base_score = score(
        v2_gold,
        v2_base,
        include_clusters=True,
    )
    v2_v5_score = score(
        v2_gold,
        v2_v5,
        include_clusters=True,
    )

    v1_comp = comparison(v1_gold, v1_base, v1_v5)
    v2_comp = comparison(v2_gold, v2_base, v2_v5)

    combined_gold = {**v1_gold, **v2_gold}
    combined_base = {**v1_base, **v2_base}
    combined_v5 = {**v1_v5, **v2_v5}

    if len(combined_gold) != 111:
        raise RuntimeError("Combined case IDs unexpectedly overlap.")

    combined_base_score = score(
        combined_gold,
        combined_base,
        include_clusters=False,
    )
    combined_v5_score = score(
        combined_gold,
        combined_v5,
        include_clusters=False,
    )
    combined_comp = comparison(
        combined_gold,
        combined_base,
        combined_v5,
    )

    print("Waypoint candidate-v5 retired development score")
    print("=" * 48)
    print(
        f"Candidate v5 SHA256:      "
        f"{EXPECTED_V5_CANDIDATE_SHA256}"
    )
    print(
        f"Production v2 SHA256:     "
        f"{EXPECTED_V2_RUNTIME_SHA256}"
    )
    print(
        "Evaluation status:        RETIRED DEVELOPMENT / DIAGNOSTIC ONLY"
    )
    print()
    print("Model calls:              NONE")
    print("Retrieval calls:          NONE")
    print("Reranker calls:           NONE")
    print("Database writes:          NONE")
    print("Runtime modifications:    NONE")

    print_score(
        "External v1",
        v1_base_score,
        v1_v5_score,
        v1_comp,
        51,
        show_clusters=False,
    )

    print_score(
        "External v2",
        v2_base_score,
        v2_v5_score,
        v2_comp,
        60,
        show_clusters=True,
    )

    print_score(
        "Combined retired development",
        combined_base_score,
        combined_v5_score,
        combined_comp,
        111,
        show_clusters=False,
    )

    print()
    print("Combined gain cases")
    print("-" * 72)
    for item in combined_comp["gains"]:
        print(
            f"  {item['case_id']}: "
            f"{item['baseline']} -> {item['v5']} "
            f"(gold {item['gold']})"
        )

    print()
    print("Combined regression cases")
    print("-" * 72)
    for item in combined_comp["regressions"]:
        print(
            f"  {item['case_id']}: "
            f"{item['baseline']} -> {item['v5']} "
            f"(gold {item['gold']})"
        )

    print()
    print("Wrong -> different wrong cases")
    print("-" * 72)
    for item in combined_comp["wrong_to_different_wrong"]:
        print(
            f"  {item['case_id']}: "
            f"{item['baseline']} -> {item['v5']} "
            f"(gold {item['gold']})"
        )

    print()
    print("Interpretation constraint")
    print("-" * 72)
    print(
        "These results are development diagnostics only. "
        "External v1 and v2 were already inspected and used in design. "
        "Do not describe this score as fresh generalisation evidence."
    )
    print()
    print("Candidate-v5 retired development scoring: PASS")


if __name__ == "__main__":
    main()
