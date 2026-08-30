"""
inspect_corpus_diffs.py

Read-only diagnostic for materially different active/staging corpus sections.

Sections are selected dynamically using a similarity threshold. No section
codes, titles, URLs, or policy rules are hardcoded.

No Waypoint files are modified.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import traceback
import unicodedata
from difflib import SequenceMatcher, unified_diff
from pathlib import Path

import frontmatter

from app.ingestion.chunker import (
    drop_repeated_title,
    normalise,
    strip_navigation,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ACTIVE_MANIFEST = PROJECT_ROOT / "data" / "manifest.json"
STAGING_MANIFEST = PROJECT_ROOT / "data" / "staging" / "manifest.json"


def load_manifest(path: Path) -> dict[str, dict]:
    """Load manifest entries indexed by section code."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        pages = data["pages"] if isinstance(data, dict) else data

        result: dict[str, dict] = {}

        for entry in pages:
            code = str(entry["section_code"])

            if code in result:
                raise ValueError(
                    f"Duplicate section code {code} in {path}"
                )

            result[code] = entry

        return result

    except Exception as exc:
        print(f"[ERROR] Failed loading {path}: {exc}")
        traceback.print_exc()
        raise


def canonical_body(
    manifest_path: Path,
    entry: dict,
) -> str:
    """Read one body using the same cleanup as the production chunker."""
    try:
        relative = Path(
            str(entry["file"]).replace("\\", "/")
        )

        file_path = manifest_path.parent / relative

        if not file_path.exists():
            raise FileNotFoundError(file_path)

        post = frontmatter.load(file_path)

        title = str(
            post.get("title")
            or entry.get("title")
            or entry["section_code"]
        )

        body = strip_navigation(post.content)
        body = drop_repeated_title(body, title)
        body = normalise(body)

        return body

    except Exception as exc:
        print(
            f"[ERROR] Failed reading "
            f"{entry.get('section_code')}: {exc}"
        )
        traceback.print_exc()
        raise


def semantic_normalise(text: str) -> str:
    """Normalise Unicode and whitespace without changing policy wording."""
    try:
        value = unicodedata.normalize("NFKC", text)
        value = value.replace("\u00a0", " ")
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r"\n{3,}", "\n\n", value)

        return value.strip()

    except Exception as exc:
        print(f"[ERROR] Failed normalising text: {exc}")
        traceback.print_exc()
        raise


def similarity(old_text: str, new_text: str) -> float:
    """Return sequence similarity between two normalised policy bodies."""
    try:
        old_value = re.sub(r"\s+", " ", old_text).strip()
        new_value = re.sub(r"\s+", " ", new_text).strip()

        return SequenceMatcher(
            None,
            old_value,
            new_value,
            autojunk=False,
        ).ratio()

    except Exception as exc:
        print(f"[ERROR] Similarity calculation failed: {exc}")
        traceback.print_exc()
        raise


def main() -> int:
    """Print unified diffs for dynamically selected changed sections."""
    try:
        parser = argparse.ArgumentParser(
            description=(
                "Inspect active/staging sections below a similarity threshold."
            )
        )

        parser.add_argument(
            "--threshold",
            type=float,
            default=0.90,
            help="Inspect sections with similarity below this value.",
        )

        parser.add_argument(
            "--context",
            type=int,
            default=2,
            help="Number of unchanged context lines around each diff.",
        )

        args = parser.parse_args()

        if not 0 <= args.threshold <= 1:
            raise ValueError(
                "--threshold must be between 0 and 1."
            )

        print("[START] Inspecting material corpus differences")
        print("[INFO] READ ONLY")
        print(f"[INFO] Similarity threshold: {args.threshold:.2f}")

        active = load_manifest(ACTIVE_MANIFEST)
        staging = load_manifest(STAGING_MANIFEST)

        shared = sorted(set(active) & set(staging))

        selected: list[
            tuple[str, float, str, str]
        ] = []

        for code in shared:
            old_body = semantic_normalise(
                canonical_body(
                    ACTIVE_MANIFEST,
                    active[code],
                )
            )

            new_body = semantic_normalise(
                canonical_body(
                    STAGING_MANIFEST,
                    staging[code],
                )
            )

            score = similarity(old_body, new_body)

            if score < args.threshold:
                selected.append(
                    (
                        code,
                        score,
                        old_body,
                        new_body,
                    )
                )

        selected.sort(key=lambda item: item[1])

        print()
        print("Material difference audit")
        print("-------------------------")
        print(f"Shared sections:  {len(shared)}")
        print(f"Selected:         {len(selected)}")

        for code, score, old_body, new_body in selected:
            print()
            print("=" * 100)
            print(
                f"{code} | similarity={score:.4f}"
            )
            print(
                f"OLD: {active[code].get('title')}"
            )
            print(
                f"NEW: {staging[code].get('title')}"
            )
            print("=" * 100)

            old_lines = old_body.splitlines()
            new_lines = new_body.splitlines()

            diff = unified_diff(
                old_lines,
                new_lines,
                fromfile="active",
                tofile="staging",
                lineterm="",
                n=args.context,
            )

            for line in diff:
                print(line)

        print()
        print("[OK] Difference inspection complete.")
        print("[OK] No files were modified.")

        return 0

    except Exception as exc:
        print(f"[ERROR] Difference inspection failed: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())