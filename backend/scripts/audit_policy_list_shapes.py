"""
Audit list structures used by the current archived INZ policy pages.

Read-only. No corpus, manifest, staging, database, or source files are changed.
"""

from __future__ import annotations

import sys
import traceback
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup, Tag

try:
    from .mhtml_ingest import extract_policy_html_from_mhtml
except ImportError:
    from mhtml_ingest import extract_policy_html_from_mhtml


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ARCHIVE_DIR = (
    PROJECT_ROOT
    / "data"
    / "source_archive"
    / "operational_manual"
)


def class_label(tag: Tag) -> str:
    """Return a stable tag/class label for diagnostics."""
    classes = tag.get("class") or []

    if not classes:
        return f"{tag.name}.<none>"

    return f"{tag.name}." + ".".join(classes)


def main() -> int:
    """Report list and continuation structures across the archive."""
    try:
        print("[START] Auditing policy list structures")
        print("[INFO] READ ONLY")

        files = sorted(ARCHIVE_DIR.glob("*.mhtml"))

        list_classes: Counter[str] = Counter()
        direct_paragraph_classes: Counter[str] = Counter()
        nesting_shapes: Counter[str] = Counter()

        total_lists = 0
        files_with_lists = 0

        for path in files:
            html, _, _ = extract_policy_html_from_mhtml(path)

            soup = BeautifulSoup(
                html,
                "html.parser",
            )

            main = soup.find(
                "td",
                id="main",
            )

            if main is None:
                raise ValueError(
                    f"{path.name}: td#main missing after extraction"
                )

            lists = main.find_all(
                ["ol", "ul"]
            )

            if lists:
                files_with_lists += 1

            total_lists += len(lists)

            for lst in lists:
                list_classes[class_label(lst)] += 1

                parent_list = lst.find_parent(
                    ["ol", "ul"]
                )

                if parent_list is not None:
                    nesting_shapes[
                        f"{class_label(parent_list)} -> "
                        f"{class_label(lst)}"
                    ] += 1

            for li in main.find_all("li"):
                for child in li.find_all(
                    "p",
                    recursive=False,
                ):
                    direct_paragraph_classes[
                        class_label(child)
                    ] += 1

        print()
        print("Policy list structure audit")
        print("---------------------------")
        print(f"Files found:       {len(files)}")
        print(f"Files with lists:  {files_with_lists}")
        print(f"Total ol/ul lists: {total_lists}")

        print()
        print("[LIST CLASSES]")

        for label, count in sorted(
            list_classes.items()
        ):
            print(f"  {label}: {count}")

        print()
        print("[DIRECT PARAGRAPHS INSIDE LI]")

        if direct_paragraph_classes:
            for label, count in sorted(
                direct_paragraph_classes.items()
            ):
                print(f"  {label}: {count}")
        else:
            print("  none")

        print()
        print("[NESTED LIST SHAPES]")

        if nesting_shapes:
            for shape, count in sorted(
                nesting_shapes.items()
            ):
                print(f"  {shape}: {count}")
        else:
            print("  none")

        print()
        print("[OK] List structure audit complete.")
        print("[OK] No files were modified.")

        return 0

    except Exception as exc:
        print(f"[ERROR] List structure audit failed: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())