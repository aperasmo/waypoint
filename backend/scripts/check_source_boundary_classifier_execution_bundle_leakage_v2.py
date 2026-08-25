"""Leakage/isolation guard for Waypoint classifier execution bundle v2."""

from __future__ import annotations

import ast
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

CLASSIFIER_PATH = (
    BACKEND_DIR
    / "_experiments"
    / "source_boundary_classifier_v2.py"
)

RUNNER_PATH = (
    BACKEND_DIR
    / "scripts"
    / "run_source_boundary_classifier_blind_v2.py"
)

SCORER_PATH = (
    BACKEND_DIR
    / "scripts"
    / "score_source_boundary_classifier_independent_v2.py"
)


def imports_for(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                result.append(node.module)

    return result


def main() -> None:
    for path in (
        CLASSIFIER_PATH,
        RUNNER_PATH,
        SCORER_PATH,
    ):
        if not path.exists():
            raise RuntimeError(f"Required bundle file missing: {path}")

    classifier = CLASSIFIER_PATH.read_text(encoding="utf-8")
    runner = RUNNER_PATH.read_text(encoding="utf-8")
    scorer = SCORER_PATH.read_text(encoding="utf-8")

    classifier_forbidden = [
        "source_boundary_classifier_independent_contract",
        "source_boundary_classifier_blind_input_v2.json",
        "source_boundary_classifier_acceptance_thresholds",
        "source_boundary_classifier_predictions",
        "contrast_group",
        "expected_sections",
        "sbv2_",
        "iv4_",
    ]

    classifier_hits = [
        token
        for token in classifier_forbidden
        if token in classifier
    ]

    if classifier_hits:
        raise RuntimeError(
            "Classifier isolation failure: "
            + ", ".join(classifier_hits)
        )

    runner_forbidden_paths = [
        "source_boundary_classifier_independent_contract_test_pack_v5.json",
        "source_boundary_classifier_acceptance_thresholds_v2.json",
        "source_boundary_classifier_score_v2.json",
    ]

    runner_hits = [
        token
        for token in runner_forbidden_paths
        if token in runner
    ]

    if runner_hits:
        raise RuntimeError(
            "Blind runner references forbidden gold/scoring files: "
            + ", ".join(runner_hits)
        )

    if "item[\"case_id\"]" not in runner:
        raise RuntimeError("Runner case correlation handle missing.")

    model_call_fragment = (
        "classification = await classify_source_boundary(\n"
        "                item[\"unsupported_proposition\"],\n"
        "                item[\"trusted_source_context\"],\n"
        "            )"
    )

    if model_call_fragment not in runner:
        raise RuntimeError(
            "Runner classifier-call shape changed; cannot verify that "
            "case_id is excluded from model input."
        )

    if (
        "RUN_AUTHORISATION_PATH" not in runner
        or "validate_run_authorisation()" not in runner
    ):
        raise RuntimeError("Blind runner lacks one-run authorisation gate.")

    runner_eval_ids = [
        token
        for token in ("sbv2_", "iv4_")
        if token in runner
    ]

    if runner_eval_ids:
        raise RuntimeError(
            "Blind runner contains hardcoded case IDs: "
            + ", ".join(runner_eval_ids)
        )

    scorer_imports = imports_for(SCORER_PATH)

    if any(
        name == "openai"
        or name.startswith("openai.")
        or name.startswith("_experiments")
        for name in scorer_imports
    ):
        raise RuntimeError(
            "Scorer imports model/classifier execution dependencies."
        )

    if (
        "chat.completions.create(" in scorer
        or "classify_source_boundary(" in scorer
    ):
        raise RuntimeError("Scorer contains a model/classifier call.")

    scorer_ids = [
        token
        for token in ("sbv2_", "iv4_")
        if token in scorer
    ]

    if scorer_ids:
        raise RuntimeError(
            "Scorer contains hardcoded case IDs: "
            + ", ".join(scorer_ids)
        )

    print("Waypoint classifier execution-bundle leakage guard v2")
    print("=" * 65)
    print("Classifier")
    print("Production imports: NONE")
    print("Gold/pack references: NONE")
    print("Threshold references: NONE")
    print("Benchmark IDs: NONE")
    print()
    print("Blind runner")
    print("Gold pack path: NONE")
    print("Threshold file path: NONE")
    print("case_id passed to model: NO")
    print("Hardcoded case IDs: NONE")
    print("Run-authorisation gate: PRESENT")
    print()
    print("Scorer")
    print("Model/classifier imports: NONE")
    print("Model calls: NONE")
    print("Hardcoded case IDs: NONE")
    print()
    print("Execution-bundle leakage guard v2: PASS")


if __name__ == "__main__":
    main()
