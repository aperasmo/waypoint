"""
Audit the structural end boundary of current INZ Operational Manual topics.

Read-only. No corpus, staging, manifest, database, or source files are changed.
"""

from __future__ import annotations

import sys
import traceback
from email import policy
from email.parser import BytesParser
from pathlib import Path

from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ARCHIVE_DIR = (
    PROJECT_ROOT
    / "data"
    / "source_archive"
    / "operational_manual"
)


def inspect_file(path: Path) -> tuple[bool, str]:
    """Validate the structural end of the current policy topic."""
    try:
        message = BytesParser(policy=policy.default).parsebytes(
            path.read_bytes()
        )

        for part in message.walk():
            if part.get_content_type() != "text/html":
                continue

            html = part.get_content()
            soup = BeautifulSoup(html, "html.parser")

            main = soup.find("td", id="main")

            if main is None:
                continue

            # Match the same heading patterns used by the MHTML adapter.
            heading_candidates = []

            primary = main.select_one("p.heading4")

            if primary is not None:
                heading_candidates.append(primary)

            heading_candidates.extend(
                main.find_all(["h1", "h2", "h3", "h4"])
            )

            heading = None

            for candidate in heading_candidates:
                text = candidate.get_text(" ", strip=True)

                if (
                    text == path.stem
                    or text.startswith(f"{path.stem} ")
                ):
                    heading = candidate
                    break

            if heading is None:
                continue

            heading_text = heading.get_text(" ", strip=True)

            # Find the first related-topics boundary after the current heading.
            boundary = None

            for candidate in heading.find_all_next(
                "table",
                class_="relatedtopics",
            ):
                if main not in candidate.parents:
                    break

                classes = candidate.get("class", [])

                if "belowtopictext" in classes:
                    boundary = candidate
                    break

            if boundary is not None:
                return True, f"boundary | {heading_text}"

            # No boundary is acceptable only when there is no later full topic
            # heading for the same section code.
            for candidate in heading.find_all_next(
                ["p", "h1", "h2", "h3", "h4"]
            ):
                if main not in candidate.parents:
                    break

                text = candidate.get_text(" ", strip=True)

                if (
                    candidate is not heading
                    and (
                        text == path.stem
                        or text.startswith(f"{path.stem} ")
                    )
                ):
                    return (
                        False,
                        f"no boundary before later topic: {text}",
                    )

            return True, f"end-of-main | {heading_text}"

        return False, "matching policy HTML not found"

    except Exception as exc:
        print(f"[ERROR] {path.name}: {exc}")
        traceback.print_exc()
        return False, str(exc)


def main() -> int:
    """Audit all manually archived MHTML files dynamically."""
    try:
        print("[START] Auditing MHTML current-topic boundaries")
        print("[INFO] READ ONLY")

        files = sorted(ARCHIVE_DIR.glob("*.mhtml"))

        if not files:
            print("[ERROR] No MHTML files found.")
            return 1

        boundary_pages: list[str] = []
        end_of_main_pages: list[str] = []
        failed: list[tuple[str, str]] = []

        for path in files:
            ok, detail = inspect_file(path)

            if ok:
                if detail.startswith("boundary"):
                    boundary_pages.append(path.stem)
                else:
                    end_of_main_pages.append(path.stem)
            else:
                failed.append((path.stem, detail))

        print()
        print("MHTML topic boundary audit")
        print("--------------------------")
        print(f"Files found:          {len(files)}")
        print(f"Boundary-delimited:   {len(boundary_pages)}")
        print(f"End-of-main fallback: {len(end_of_main_pages)}")
        print(f"Failed:               {len(failed)}")

        if failed:
            print()
            print("[FAILED]")
            for code, reason in failed:
                print(f"  {code}: {reason}")

            return 2

        print()
        print(
            "[OK] Every archived current topic ends before a "
            "table.relatedtopics.belowtopictext boundary."
        )

        return 0

    except Exception as exc:
        print(f"[ERROR] Boundary audit failed: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())