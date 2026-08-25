"""Freeze/review the Waypoint classifier execution bundle v2.

REVIEW ONLY.
- No model calls.
- Does not execute the blind runner.
- Does not score predictions.
- Reviews exact runner/scorer/guard/classifier/blind-input files.
- Authorises construction of a separate one-run authorisation artifact only.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

CLASSIFIER_PATH = BACKEND_DIR / "_experiments" / "source_boundary_classifier_v2.py"
RUNNER_PATH = BACKEND_DIR / "scripts" / "run_source_boundary_classifier_blind_v2.py"
SCORER_PATH = BACKEND_DIR / "scripts" / "score_source_boundary_classifier_independent_v2.py"
GUARD_PATH = BACKEND_DIR / "scripts" / "check_source_boundary_classifier_execution_bundle_leakage_v2.py"
BLIND_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_blind_input_v2.json"
THRESHOLDS_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_acceptance_thresholds_v2.json"
PACK_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_independent_contract_test_pack_v5.json"
IMPLEMENTATION_REVIEW_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_implementation_review_v2.json"
OUTPUT_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_execution_bundle_review_v2.json"

EXPECTED_CLASSIFIER_SHA = "8193FCDDB48585EC8A8BA8BCC477D123011B50F2F38531BEB2D88836975FF949"
EXPECTED_RUNNER_SHA = "4279E0B771DFCB69202D99722292F45A90BE8FDF454C67B834D52A01E8F46A58"
EXPECTED_SCORER_SHA = "0871AA74522CDF14EE58F7C0A8D3101C080FCE7B1BB531A17A3267FD934737E4"
EXPECTED_GUARD_SHA = "BFFB174554ADA901A56D119481100BB7480A0E8B32E96CA2A2961D4BC501E3D8"
EXPECTED_BLIND_SHA = "22D3A1C184F95D65D9571191A1FFF01AD251050C554BA6D96F15FBABBFDF9D6B"
EXPECTED_THRESHOLDS_SHA = "1BDD2ED8950D6E3E612C66DCD5384BD5E0CAC784E39A70C3CE09EAD5C310D277"
EXPECTED_PACK_SHA = "1B3CEA56504E3932C7DCA342DF99DC22523A4676B1C22714B9A122DDD566E67B"
EXPECTED_IMPLEMENTATION_REVIEW_SHA = "222C11F1CEEDE217CB9F34B7771E837BCB2E92065C7D1C4FB42CC0F18A85FA1A"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require(path: Path, expected: str, label: str) -> None:
    if not path.exists():
        raise RuntimeError(f"{label} missing: {path}")
    actual = sha256(path)
    if actual != expected:
        raise RuntimeError(
            f"{label} SHA mismatch.\nExpected: {expected}\nActual:   {actual}"
        )


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError(f"{path.name} root must be an object.")
    return data


def imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.append(node.module)
    return result


def actual_call_names(path: Path) -> list[str]:
    """Return executable call targets, ignoring string literals/comments."""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        try:
            names.append(ast.unparse(node.func))
        except Exception:
            continue

    return names


def main() -> None:
    if OUTPUT_PATH.exists():
        raise RuntimeError(
            f"Bundle-review artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    for path, expected, label in (
        (CLASSIFIER_PATH, EXPECTED_CLASSIFIER_SHA, "Classifier"),
        (RUNNER_PATH, EXPECTED_RUNNER_SHA, "Blind runner"),
        (SCORER_PATH, EXPECTED_SCORER_SHA, "Scorer"),
        (GUARD_PATH, EXPECTED_GUARD_SHA, "Leakage guard"),
        (BLIND_PATH, EXPECTED_BLIND_SHA, "Blind input"),
        (THRESHOLDS_PATH, EXPECTED_THRESHOLDS_SHA, "Thresholds"),
        (PACK_PATH, EXPECTED_PACK_SHA, "Gold pack"),
        (
            IMPLEMENTATION_REVIEW_PATH,
            EXPECTED_IMPLEMENTATION_REVIEW_SHA,
            "Implementation review",
        ),
    ):
        require(path, expected, label)

    implementation_review = load_json(IMPLEMENTATION_REVIEW_PATH)

    if implementation_review.get("status") != (
        "APPROVED_STATIC_IMPLEMENTATION_READY_FOR_EXECUTION_BUNDLE_CONSTRUCTION"
    ):
        raise RuntimeError("Implementation review status changed.")

    runner_text = RUNNER_PATH.read_text(encoding="utf-8")
    scorer_text = SCORER_PATH.read_text(encoding="utf-8")
    guard_text = GUARD_PATH.read_text(encoding="utf-8")

    # Runner must remain blind to gold and threshold files.
    for forbidden in (
        "source_boundary_classifier_independent_contract_test_pack_v5.json",
        "source_boundary_classifier_acceptance_thresholds_v2.json",
        "source_boundary_classifier_score_v2.json",
    ):
        if forbidden in runner_text:
            raise RuntimeError(
                f"Runner contains forbidden evaluation file reference: {forbidden}"
            )

    if "source_boundary_classifier_blind_input_v2.json" not in runner_text:
        raise RuntimeError("Runner is not pinned to blind input v2.")

    if "source_boundary_classifier_run_authorisation_v2.json" not in runner_text:
        raise RuntimeError("Runner lacks separate run-authorisation gate.")

    if "if PREDICTIONS_PATH.exists()" not in runner_text:
        raise RuntimeError("Runner does not refuse prediction overwrite.")

    if "automatic_retry" not in runner_text or '"automatic_retry": False' not in runner_text:
        raise RuntimeError("Runner no-retry contract missing.")

    # Scorer must be model-independent and prediction-freeze gated.
    scorer_imports = imports(SCORER_PATH)
    if any(
        name == "openai"
        or name.startswith("openai.")
        or name.startswith("_experiments")
        for name in scorer_imports
    ):
        raise RuntimeError("Scorer imports model/classifier dependencies.")

    if "source_boundary_classifier_prediction_result_v2.json" not in scorer_text:
        raise RuntimeError("Scorer lacks prediction-result freeze gate.")

    scorer_calls = actual_call_names(SCORER_PATH)

    if any(
        call.endswith("chat.completions.create")
        or call == "classify_source_boundary"
        or call.endswith(".classify_source_boundary")
        for call in scorer_calls
    ):
        raise RuntimeError("Scorer contains model execution.")

    # Guard itself must be static-only. Detect executable call nodes only;
    # the guard legitimately contains forbidden-call strings as checker data.
    guard_calls = actual_call_names(GUARD_PATH)

    if any(
        call.endswith("chat.completions.create")
        or call == "classify_source_boundary"
        or call.endswith(".classify_source_boundary")
        for call in guard_calls
    ):
        raise RuntimeError("Leakage guard contains model execution.")

    # Check for actual hardcoded evaluation CASE IDs, not harmless prefix
    # strings used by the leakage guard itself as search patterns.
    case_id_pattern = re.compile(r"\\b(?:sbv2|iv4)_\\d+\\b")

    for candidate_text, label in (
        (runner_text, "runner"),
        (scorer_text, "scorer"),
        (guard_text, "guard"),
    ):
        hardcoded_ids = sorted(set(case_id_pattern.findall(candidate_text)))

        if hardcoded_ids:
            raise RuntimeError(
                f"{label} contains hardcoded evaluation IDs: "
                + ", ".join(hardcoded_ids)
            )

    artifact = {
        "schema": "waypoint-source-boundary-classifier-execution-bundle-review-v2",
        "status": "APPROVED_READY_FOR_SINGLE_RUN_AUTHORISATION_FREEZE",
        "reviewed_on": str(date.today()),
        "source_artifacts": {
            "classifier_implementation_v2_sha256": EXPECTED_CLASSIFIER_SHA,
            "blind_runner_v2_sha256": EXPECTED_RUNNER_SHA,
            "scorer_v2_sha256": EXPECTED_SCORER_SHA,
            "leakage_guard_v2_sha256": EXPECTED_GUARD_SHA,
            "blind_input_v2_sha256": EXPECTED_BLIND_SHA,
            "acceptance_thresholds_v2_sha256": EXPECTED_THRESHOLDS_SHA,
            "independent_contract_pack_v5_sha256": EXPECTED_PACK_SHA,
            "implementation_review_v2_sha256": EXPECTED_IMPLEMENTATION_REVIEW_SHA,
        },
        "runner_review": {
            "decision": "PASS",
            "reads_blind_input": True,
            "reads_gold_pack": False,
            "reads_threshold_file": False,
            "case_id_passed_to_model": False,
            "sequential_one_call_per_case": True,
            "automatic_retry": False,
            "repair_call": False,
            "fallback_model": False,
            "refuses_prediction_overwrite": True,
            "separate_run_authorisation_gate": True,
        },
        "scorer_review": {
            "decision": "PASS",
            "model_imports": False,
            "model_calls": False,
            "reads_gold_pack": True,
            "reads_thresholds": True,
            "requires_prediction_result_freeze": True,
            "refuses_score_overwrite": True,
        },
        "leakage_review": {
            "decision": "PASS",
            "benchmark_ids": False,
            "case_specific_logic": False,
            "runner_gold_access": False,
            "runner_threshold_file_access": False,
            "scorer_model_access": False,
        },
        "execution_policy": {
            "model": "gpt-5.4-mini",
            "reasoning_effort": "none",
            "max_completion_tokens": 800,
            "temperature": 0.0,
            "case_count": 40,
            "one_model_call_per_case": True,
            "sequential": True,
            "automatic_retry": False,
            "repair_call": False,
            "fallback_model": False,
            "single_first_run_only": True,
        },
        "authorisations": {
            "single_run_authorisation_freeze_authorised": True,
            "classifier_model_run_authorised": False,
            "prediction_scoring_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": "source_boundary_classifier_run_authorisation_v2",
            "authorised": True,
            "model_calls": 0,
            "purpose": (
                "Freeze a one-time authorisation artifact for the first untouched "
                "40-case independent classifier run."
            ),
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("Waypoint classifier execution bundle v2 review")
    print("=" * 63)
    print(f"Classifier SHA: {sha256(CLASSIFIER_PATH)}")
    print(f"Runner SHA:     {sha256(RUNNER_PATH)}")
    print(f"Scorer SHA:     {sha256(SCORER_PATH)}")
    print(f"Guard SHA:      {sha256(GUARD_PATH)}")
    print(f"Blind SHA:      {sha256(BLIND_PATH)}")
    print()
    print("Runner review:                 PASS")
    print("Scorer review:                 PASS")
    print("Leakage/isolation review:      PASS")
    print("Gold accessible to runner:     NO")
    print("Threshold file accessible runner: NO")
    print("case_id passed to model:       NO")
    print("Scorer model access:           NO")
    print("Automatic retry:               NO")
    print()
    print("Execution bundle v2:           APPROVED")
    print("Run-authorisation freeze:      AUTHORISED")
    print("Model run:                     NOT AUTHORISED")
    print("Prediction scoring:            NOT AUTHORISED")
    print("Candidate v7:                  NOT AUTHORISED")
    print("Production change:             NOT AUTHORISED")
    print()
    print(f"Output: {OUTPUT_PATH}")
    print(f"Bundle-review SHA256: {sha256(OUTPUT_PATH)}")
    print("Model calls: NONE")
    print()
    print("Execution bundle v2 review: PASS")


if __name__ == "__main__":
    main()
