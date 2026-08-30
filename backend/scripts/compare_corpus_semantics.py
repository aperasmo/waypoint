"""
compare_corpus_semantics.py

Read-only comparison of active and staging corpus bodies after conservative
text normalisation.

Only Unicode and whitespace differences are ignored. Policy wording,
punctuation, list markers, numbers, and table values remain significant.

No Waypoint files are modified.
"""

from __future__ import annotations

import json
import re
import sys
import traceback
import unicodedata
from difflib import SequenceMatcher
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
    """Load one manifest and index its entries by section code."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        pages = data["pages"] if isinstance(data, dict) else data

        result: dict[str, dict] = {}

        for entry in pages:
            section_code = str(entry["section_code"])

            if section_code in result:
                raise ValueError(
                    f"Duplicate section code {section_code} in {path}"
                )

            result[section_code] = entry

        return result

    except Exception as exc:
        print(f"[ERROR] Failed loading manifest {path}: {exc}")
        traceback.print_exc()
        raise


def canonical_body(
    manifest_path: Path,
    entry: dict,
) -> str:
    """Read one corpus body using the same cleanup as the production chunker."""
    try:
        corpus_dir = manifest_path.parent

        relative_path = Path(
            str(entry["file"]).replace("\\", "/")
        )

        file_path = corpus_dir / relative_path

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
    """Ignore encoding and whitespace variation without changing policy text."""
    try:
        value = unicodedata.normalize("NFKC", text)
        value = value.replace("\u00a0", " ")
        value = re.sub(r"\s+", " ", value)

        return value.strip()

    except Exception as exc:
        print(f"[ERROR] Failed semantic normalisation: {exc}")
        traceback.print_exc()
        raise


def main() -> int:
    """Compare every section shared by the active and staging corpora."""
    try:
        print("[START] Comparing corpus wording")
        print("[INFO] READ ONLY")
        print(
            "[INFO] Ignoring Unicode/whitespace variation only."
        )

        active = load_manifest(ACTIVE_MANIFEST)
        staging = load_manifest(STAGING_MANIFEST)

        shared = sorted(set(active) & set(staging))

        identical: list[str] = []
        changed: list[tuple[str, float, int, int]] = []

        for section_code in shared:
            old_body = canonical_body(
                ACTIVE_MANIFEST,
                active[section_code],
            )

            new_body = canonical_body(
                STAGING_MANIFEST,
                staging[section_code],
            )

            old_normalised = semantic_normalise(old_body)
            new_normalised = semantic_normalise(new_body)

            if old_normalised == new_normalised:
                identical.append(section_code)
                continue

            similarity = SequenceMatcher(
                None,
                old_normalised,
                new_normalised,
                autojunk=False,
            ).ratio()

            changed.append(
                (
                    section_code,
                    similarity,
                    len(old_normalised),
                    len(new_normalised),
                )
            )

        changed.sort(key=lambda item: item[1])

        below_90 = [
            item for item in changed
            if item[1] < 0.90
        ]

        between_90_97 = [
            item for item in changed
            if 0.90 <= item[1] < 0.97
        ]

        at_least_97 = [
            item for item in changed
            if item[1] >= 0.97
        ]

        print()
        print("Semantic corpus comparison")
        print("--------------------------")
        print(f"Shared sections:       {len(shared)}")
        print(f"Equivalent wording:    {len(identical)}")
        print(f"Changed wording:       {len(changed)}")
        print(f"Similarity < 0.90:     {len(below_90)}")
        print(f"Similarity 0.90-0.97:  {len(between_90_97)}")
        print(f"Similarity >= 0.97:    {len(at_least_97)}")

        if changed:
            print()
            print("[CHANGED WORDING]")

            for (
                section_code,
                similarity,
                old_length,
                new_length,
            ) in changed:
                print(
                    f"  {section_code}: "
                    f"similarity={similarity:.4f} "
                    f"old_chars={old_length} "
                    f"new_chars={new_length}"
                )

        print()
        print("[OK] Semantic comparison complete.")
        print("[OK] No files were modified.")

        return 0

    except Exception as exc:
        print(f"[ERROR] Semantic comparison failed: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())