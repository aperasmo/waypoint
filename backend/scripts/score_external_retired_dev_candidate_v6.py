"""Score candidate v6 on both RETIRED external development sets.

This is DEVELOPMENT / DIAGNOSTIC ONLY.

Candidate-v6 contract errors are explicit scoring failures:
- they remain in the denominator;
- they never count as correct;
- they are not retried or repaired;
- they count as no citation on sufficient-gold cases.

No model, retrieval, reranker, database, or runtime calls are made.

Run from backend/:
    uv run python -m py_compile scripts/score_external_retired_dev_candidate_v6.py
    uv run python -m scripts.score_external_retired_dev_candidate_v6
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

V1_V6_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v1_candidate_v6.json"
)
V2_V6_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v2_candidate_v6.json"
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

EXPECTED_V1_V6_SHA256 = (
    "24BDDB4B0AA69BBE93552F075E3A801C"
    "8905422B4F5EBBD01375779640A295FF"
)
EXPECTED_V2_V6_SHA256 = (
    "2150DA5E6E093AA1FBF8ECA39362306B"
    "50115598561BAC15D02C8573D61C3A45"
)

EXPECTED_V2_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)
EXPECTED_V6_CANDIDATE_SHA256 = (
    "04F86C7EA3E4BA296E4052FE7B7E7660"
    "9799F6FF96021AF6D658CA1890997C95"
)

STATUSES = (
    "sufficient",
    "corpus_gap",
    "external_source_required",
)
ERROR_STATUS = "candidate_error"


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

    result: dict[str, dict] = {}

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


def baseline_prediction_map(
    payload: dict,
    *,
    expected_schema: str,
    expected_count: int,
) -> dict[str, dict]:
    if payload.get("schema") != expected_schema:
        raise RuntimeError(
            f"Unexpected baseline schema: {payload.get('schema')!r}"
        )

    predictions = payload.get("predictions")
    if not isinstance(predictions, list):
        raise RuntimeError("Baseline predictions must be a list.")

    if len(predictions) != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} baseline predictions, "
            f"got {len(predictions)}."
        )

    result: dict[str, dict] = {}

    for item in predictions:
        case_id = item.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Baseline prediction has invalid case_id.")

        if case_id in result:
            raise RuntimeError(
                f"Duplicate baseline prediction case_id: {case_id}"
            )

        status = item.get("evidence_status")
        if status not in STATUSES:
            raise RuntimeError(
                f"{case_id}: invalid baseline evidence status."
            )

        result[case_id] = item

    return result


def candidate_v6_map(
    payload: dict,
    *,
    expected_schema: str,
    expected_count: int,
) -> tuple[dict[str, dict], dict]:
    if payload.get("schema") != expected_schema:
        raise RuntimeError(
            f"Unexpected candidate-v6 schema: {payload.get('schema')!r}"
        )

    if payload.get(
        "candidate_source_sha256"
    ) != EXPECTED_V6_CANDIDATE_SHA256:
        raise RuntimeError("Candidate-v6 SHA linkage changed.")

    if payload.get(
        "production_runtime_sha256"
    ) != EXPECTED_V2_RUNTIME_SHA256:
        raise RuntimeError("Candidate-v6 production linkage changed.")

    if payload.get("production_runtime_replaced") is not False:
        raise RuntimeError(
            "Candidate-v6 artifact claims production replacement."
        )

    if payload.get("candidate_errors_are_scoring_failures") is not True:
        raise RuntimeError(
            "Candidate-v6 error scoring contract changed."
        )

    if payload.get("attempted_count") != expected_count:
        raise RuntimeError(
            "Candidate-v6 attempted_count changed."
        )

    predictions = payload.get("predictions")
    errors = payload.get("errors")

    if not isinstance(predictions, list):
        raise RuntimeError("Candidate-v6 predictions must be a list.")
    if not isinstance(errors, list):
        raise RuntimeError("Candidate-v6 errors must be a list.")

    if payload.get("prediction_count") != len(predictions):
        raise RuntimeError("Candidate-v6 prediction_count mismatch.")
    if payload.get("error_count") != len(errors):
        raise RuntimeError("Candidate-v6 error_count mismatch.")

    if len(predictions) + len(errors) != expected_count:
        raise RuntimeError(
            "Candidate-v6 prediction/error total does not match attempted_count."
        )

    contract = payload.get("model_call_contract")
    if contract != {
        "support_sufficient": 2,
        "support_insufficient": 3,
    }:
        raise RuntimeError("Candidate-v6 model-call contract changed.")

    result: dict[str, dict] = {}

    for item in predictions:
        case_id = item.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError(
                "Candidate-v6 prediction has invalid case_id."
            )

        if case_id in result:
            raise RuntimeError(
                f"Duplicate candidate-v6 case_id: {case_id}"
            )

        status = item.get("evidence_status")
        if status not in STATUSES:
            raise RuntimeError(
                f"{case_id}: invalid candidate-v6 evidence status."
            )

        result[case_id] = item

    for item in errors:
        case_id = item.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError(
                "Candidate-v6 error has invalid case_id."
            )

        if case_id in result:
            raise RuntimeError(
                f"Candidate-v6 duplicate prediction/error ID: {case_id}"
            )

        if item.get("error_type") != "candidate_contract_error":
            raise RuntimeError(
                f"{case_id}: unexpected candidate-v6 error_type."
            )

        if item.get("status_code") != 502:
            raise RuntimeError(
                f"{case_id}: unexpected candidate-v6 error status."
            )

        detail = item.get("detail")
        if not isinstance(detail, str) or not detail.strip():
            raise RuntimeError(
                f"{case_id}: empty candidate-v6 error detail."
            )

        result[case_id] = {
            "case_id": case_id,
            "question": item.get("question"),
            "__candidate_error__": True,
            "error_type": item.get("error_type"),
            "status_code": item.get("status_code"),
            "detail": detail,
            "citations": [],
        }

    if len(result) != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} candidate-v6 attempted cases, "
            f"got {len(result)}."
        )

    distribution = payload.get(
        "observed_successful_prediction_distribution",
        {},
    )

    two_calls = distribution.get("two_calls")
    three_calls = distribution.get("three_calls")

    if not isinstance(two_calls, int) or not isinstance(three_calls, int):
        raise RuntimeError(
            "Candidate-v6 call-distribution metadata invalid."
        )

    if two_calls + three_calls != len(predictions):
        raise RuntimeError(
            "Candidate-v6 successful call-distribution mismatch."
        )

    actual_sufficient = sum(
        1
        for item in predictions
        if item["evidence_status"] == "sufficient"
    )

    if two_calls != actual_sufficient:
        raise RuntimeError(
            "Candidate-v6 two-call count does not equal "
            "successful sufficient predictions."
        )

    return result, {
        "predictions": len(predictions),
        "errors": len(errors),
        "two_calls": two_calls,
        "three_calls": three_calls,
    }


def predicted_status(item: dict) -> str:
    if item.get("__candidate_error__") is True:
        return ERROR_STATUS

    status = item.get("evidence_status")
    if status not in STATUSES:
        raise RuntimeError(
            f"{item.get('case_id')}: missing predicted evidence status."
        )

    return status


def validate_alignment(
    gold: dict[str, dict],
    predictions: dict[str, dict],
    label: str,
) -> None:
    if set(gold) != set(predictions):
        missing = sorted(set(gold) - set(predictions))
        extra = sorted(set(predictions) - set(gold))
        raise RuntimeError(
            f"{label}: case ID sets differ. "
            f"Missing={missing}; extra={extra}"
        )

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
    error_counts_by_gold = Counter()

    confusion = {
        status: Counter()
        for status in STATUSES
    }

    correct = 0
    false_sufficient = 0
    nonsufficient_gold = 0
    candidate_errors = 0

    for case_id, gold_item in gold.items():
        gold_status = gold_item["evidence_status"]
        pred_status = predicted_status(predictions[case_id])

        gold_counts[gold_status] += 1
        predicted_counts[pred_status] += 1
        confusion[gold_status][pred_status] += 1

        if pred_status == ERROR_STATUS:
            candidate_errors += 1
            error_counts_by_gold[gold_status] += 1
        elif gold_status == pred_status:
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

        prediction = predictions[case_id]

        citations = (
            []
            if prediction.get("__candidate_error__") is True
            else prediction.get("citations", [])
        )

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
        "candidate_errors": candidate_errors,
        "error_counts_by_gold": error_counts_by_gold,
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
                (
                    predicted_status(predictions[cid])
                    == gold[cid]["evidence_status"]
                )
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
    candidate: dict[str, dict],
) -> dict:
    gains = []
    regressions = []
    wrong_to_different_wrong = []
    unchanged_correct = []
    unchanged_wrong = []

    for case_id, gold_item in gold.items():
        gold_status = gold_item["evidence_status"]
        base_status = predicted_status(baseline[case_id])
        candidate_status = predicted_status(candidate[case_id])

        base_ok = base_status == gold_status
        candidate_ok = candidate_status == gold_status

        item = {
            "case_id": case_id,
            "gold": gold_status,
            "baseline": base_status,
            "v6": candidate_status,
        }

        if not base_ok and candidate_ok:
            gains.append(item)
        elif base_ok and not candidate_ok:
            regressions.append(item)
        elif (
            not base_ok
            and not candidate_ok
            and base_status != candidate_status
        ):
            wrong_to_different_wrong.append(item)
        elif base_ok and candidate_ok:
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
    v6_score: dict,
    comp: dict,
    total: int,
    *,
    show_clusters: bool,
) -> None:
    print()
    print(name)
    print("-" * 76)
    print(
        f"Candidate v2: {baseline_score['correct']}/{total} "
        f"({pct(baseline_score['correct'], total)})"
    )
    print(
        f"Candidate v6: {v6_score['correct']}/{total} "
        f"({pct(v6_score['correct'], total)})"
    )

    delta = v6_score["correct"] - baseline_score["correct"]
    delta_pp = 100.0 * delta / total
    print(f"Delta:        {delta:+d} correct ({delta_pp:+.1f} pp)")

    print()
    print("Per-class recall")
    for status in STATUSES:
        gold_n = v6_score["gold_counts"][status]
        base_n = baseline_score["correct_counts"][status]
        v6_n = v6_score["correct_counts"][status]
        print(
            f"  {status:<26}"
            f"v2 {base_n:>2}/{gold_n:<2} {pct(base_n, gold_n):>7}"
            f"   v6 {v6_n:>2}/{gold_n:<2} {pct(v6_n, gold_n):>7}"
        )

    print()
    print("Candidate-v6 result distribution")
    for status in STATUSES:
        print(
            f"  {status:<26}"
            f"{v6_score['predicted_counts'][status]}"
        )
    print(
        f"  {ERROR_STATUS:<26}"
        f"{v6_score['predicted_counts'][ERROR_STATUS]}"
    )

    print()
    print("Candidate-v6 confusion matrix")
    print(
        "gold / predicted               sufficient  corpus_gap"
        "    external       error"
    )
    for gold_status in STATUSES:
        row = v6_score["confusion"][gold_status]
        print(
            f"{gold_status:<32}"
            f"{row['sufficient']:>10}"
            f"{row['corpus_gap']:>12}"
            f"{row['external_source_required']:>12}"
            f"{row[ERROR_STATUS]:>12}"
        )

    print()
    print(
        "Candidate contract errors: "
        f"{v6_score['candidate_errors']}/{total} "
        f"({pct(v6_score['candidate_errors'], total)})"
    )
    if v6_score["candidate_errors"]:
        print("  Errors by gold class")
        for status in STATUSES:
            print(
                f"    {status:<26}"
                f"{v6_score['error_counts_by_gold'][status]}"
            )

    print()
    print(
        "False-sufficiency among non-sufficient gold: "
        f"{v6_score['false_sufficient']}/"
        f"{v6_score['nonsufficient_gold']} "
        f"({pct(v6_score['false_sufficient'], v6_score['nonsufficient_gold'])})"
    )

    print()
    print("Sufficient-case citation coverage")
    print(
        f"  Any expected: "
        f"{v6_score['any_expected']}/{v6_score['sufficient_count']} "
        f"({pct(v6_score['any_expected'], v6_score['sufficient_count'])})"
    )
    print(
        f"  All expected: "
        f"{v6_score['all_expected']}/{v6_score['sufficient_count']} "
        f"({pct(v6_score['all_expected'], v6_score['sufficient_count'])})"
    )
    print(
        f"  No citations: "
        f"{v6_score['no_citations']}/{v6_score['sufficient_count']}"
    )

    if show_clusters:
        print()
        print(
            "Source-cluster macro accuracy: "
            f"{100.0 * v6_score['cluster_macro']:.1f}%"
        )
        print(
            "Fully correct source clusters: "
            f"{v6_score['full_clusters']}/20"
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
        V1_V6_PATH,
        EXPECTED_V1_V6_SHA256,
        "Candidate-v6 external-v1 predictions",
    )
    require_sha(
        V2_V6_PATH,
        EXPECTED_V2_V6_SHA256,
        "Candidate-v6 external-v2 predictions",
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

    v1_base = baseline_prediction_map(
        load_json(V1_BASELINE_PATH),
        expected_schema="waypoint-external-predictions-dev-v1-v2",
        expected_count=51,
    )
    v2_base = baseline_prediction_map(
        load_json(V2_BASELINE_PATH),
        expected_schema="waypoint-external-predictions-blind-v2",
        expected_count=60,
    )

    v1_v6, v1_meta = candidate_v6_map(
        load_json(V1_V6_PATH),
        expected_schema=(
            "waypoint-external-predictions-dev-v1-candidate-v6"
        ),
        expected_count=51,
    )
    v2_v6, v2_meta = candidate_v6_map(
        load_json(V2_V6_PATH),
        expected_schema=(
            "waypoint-external-predictions-dev-v2-candidate-v6"
        ),
        expected_count=60,
    )

    validate_alignment(v1_gold, v1_base, "v1 baseline")
    validate_alignment(v1_gold, v1_v6, "v1 candidate-v6")
    validate_alignment(v2_gold, v2_base, "v2 baseline")
    validate_alignment(v2_gold, v2_v6, "v2 candidate-v6")

    v1_base_score = score(
        v1_gold,
        v1_base,
        include_clusters=False,
    )
    v1_v6_score = score(
        v1_gold,
        v1_v6,
        include_clusters=False,
    )

    v2_base_score = score(
        v2_gold,
        v2_base,
        include_clusters=True,
    )
    v2_v6_score = score(
        v2_gold,
        v2_v6,
        include_clusters=True,
    )

    v1_comp = comparison(v1_gold, v1_base, v1_v6)
    v2_comp = comparison(v2_gold, v2_base, v2_v6)

    combined_gold = {**v1_gold, **v2_gold}
    combined_base = {**v1_base, **v2_base}
    combined_v6 = {**v1_v6, **v2_v6}

    if len(combined_gold) != 111:
        raise RuntimeError("Combined case IDs unexpectedly overlap.")

    combined_base_score = score(
        combined_gold,
        combined_base,
        include_clusters=False,
    )
    combined_v6_score = score(
        combined_gold,
        combined_v6,
        include_clusters=False,
    )
    combined_comp = comparison(
        combined_gold,
        combined_base,
        combined_v6,
    )

    print("Waypoint candidate-v6 retired development score")
    print("=" * 48)
    print(
        f"Candidate v6 SHA256:      "
        f"{EXPECTED_V6_CANDIDATE_SHA256}"
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

    print()
    print("Recorded candidate execution")
    print("-" * 76)
    print(
        "External v1: "
        f"{v1_meta['predictions']} successful predictions, "
        f"{v1_meta['errors']} errors, "
        f"{v1_meta['two_calls']} two-call successes, "
        f"{v1_meta['three_calls']} three-call successes"
    )
    print(
        "External v2: "
        f"{v2_meta['predictions']} successful predictions, "
        f"{v2_meta['errors']} errors, "
        f"{v2_meta['two_calls']} two-call successes, "
        f"{v2_meta['three_calls']} three-call successes"
    )

    print_score(
        "External v1",
        v1_base_score,
        v1_v6_score,
        v1_comp,
        51,
        show_clusters=False,
    )

    print_score(
        "External v2",
        v2_base_score,
        v2_v6_score,
        v2_comp,
        60,
        show_clusters=True,
    )

    print_score(
        "Combined retired development",
        combined_base_score,
        combined_v6_score,
        combined_comp,
        111,
        show_clusters=False,
    )

    print()
    print("Combined gain cases")
    print("-" * 76)
    for item in combined_comp["gains"]:
        print(
            f"  {item['case_id']}: "
            f"{item['baseline']} -> {item['v6']} "
            f"(gold {item['gold']})"
        )

    print()
    print("Combined regression cases")
    print("-" * 76)
    for item in combined_comp["regressions"]:
        print(
            f"  {item['case_id']}: "
            f"{item['baseline']} -> {item['v6']} "
            f"(gold {item['gold']})"
        )

    print()
    print("Wrong -> different wrong cases")
    print("-" * 76)
    for item in combined_comp["wrong_to_different_wrong"]:
        print(
            f"  {item['case_id']}: "
            f"{item['baseline']} -> {item['v6']} "
            f"(gold {item['gold']})"
        )

    print()
    print("Interpretation constraint")
    print("-" * 76)
    print(
        "These results are development diagnostics only. "
        "External v1 and v2 were already inspected and used in design. "
        "Do not describe this score as fresh generalisation evidence."
    )
    print(
        "Candidate-v6 contract errors are counted as incorrect cases "
        "and remain in all denominators."
    )
    print()
    print("Candidate-v6 retired development scoring: PASS")


if __name__ == "__main__":
    main()
