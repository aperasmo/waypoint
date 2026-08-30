"""
audit_mhtml_parser.py

Read-only integration audit for every manually archived INZ Operational
Manual MHTML file.

Pipeline:
    MHTML -> validated policy HTML -> manual_extract.py

No Markdown, corpus, manifest, embedding, or database files are modified.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

try:
    from .manual_extract import extract_content
    from .mhtml_ingest import extract_policy_html_from_mhtml
except ImportError:
    from manual_extract import extract_content
    from mhtml_ingest import extract_policy_html_from_mhtml


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ARCHIVE_DIR = (
    PROJECT_ROOT
    / "data"
    / "source_archive"
    / "operational_manual"
)


def audit_file(file_path: Path) -> dict[str, object]:
    """Run one archived section through the complete local parsing pipeline."""
    try:
        policy_html, content_location, heading = (
            extract_policy_html_from_mhtml(file_path)
        )

        result = extract_content(policy_html)

        text = str(result["text"])
        issues: list[str] = []

        if not text:
            issues.append("Extracted text is empty.")

        if len(text) < 100:
            issues.append(
                f"Extracted text is unexpectedly short: {len(text)} chars."
            )

        if not text.casefold().startswith(heading.casefold()):
            issues.append(
                "Extracted text does not begin with the validated "
                "instruction heading."
            )

        if result["policy_tables"] != result["converted_tables"]:
            issues.append(
                "Policy table conversion mismatch: "
                f"{result['policy_tables']} observed, "
                f"{result['converted_tables']} converted."
            )

        if result["policy_lists"] != result["converted_lists"]:
            issues.append(
                "Policy list conversion mismatch: "
                f"{result['policy_lists']} observed, "
                f"{result['converted_lists']} converted."
            )

        status = "PASS" if not issues else "FAIL"

        return {
            "status": status,
            "file": file_path.name,
            "heading": heading,
            "content_location": content_location or "",
            "text_chars": len(text),
            "effective_date": result["effective_date"] or "",
            "html_tables": result["html_tables"],
            "policy_tables": result["policy_tables"],
            "converted_tables": result["converted_tables"],
            "policy_lists": result["policy_lists"],
            "converted_lists": result["converted_lists"],
            "issues": "; ".join(issues),
        }

    except Exception as exc:
        print(f"[ERROR] Audit failed for {file_path.name}: {exc}")
        traceback.print_exc()

        return {
            "status": "FAIL",
            "file": file_path.name,
            "heading": "",
            "content_location": "",
            "text_chars": 0,
            "effective_date": "",
            "html_tables": 0,
            "policy_tables": 0,
            "converted_tables": 0,
            "policy_lists": 0,
            "converted_lists": 0,
            "issues": str(exc),
        }


def main() -> int:
    """Audit every MHTML file using the production-equivalent local parser."""
    try:
        print("[START] Full Waypoint MHTML parser audit")
        print("[INFO] READ ONLY - no Waypoint data will be modified.")
        print(f"[INFO] Archive: {ARCHIVE_DIR}")

        if not ARCHIVE_DIR.exists():
            print(f"[ERROR] Archive does not exist: {ARCHIVE_DIR}")
            return 1

        files = sorted(
            ARCHIVE_DIR.glob("*.mhtml"),
            key=lambda path: path.name.lower(),
        )

        if not files:
            print("[ERROR] No MHTML files found.")
            return 1

        print(f"[INFO] Files found: {len(files)}")
        print()

        results: list[dict[str, object]] = []

        for index, file_path in enumerate(files, start=1):
            result = audit_file(file_path)
            results.append(result)

            print(
                f"[{index:03}/{len(files):03}] "
                f"[{result['status']}] "
                f"{result['file']} "
                f"| chars={result['text_chars']} "
                f"| date={result['effective_date'] or 'N/A'} "
                f"| tables="
                f"{result['policy_tables']}/"
                f"{result['converted_tables']} "
                f"| lists="
                f"{result['policy_lists']}/"
                f"{result['converted_lists']}"
            )

            if result["issues"]:
                print(f"      {result['issues']}")

        passed = sum(
            1 for result in results
            if result["status"] == "PASS"
        )
        failed = len(results) - passed

        missing_dates = [
            result["file"]
            for result in results
            if not result["effective_date"]
        ]

        total_policy_tables = sum(
            int(result["policy_tables"])
            for result in results
        )
        total_converted_tables = sum(
            int(result["converted_tables"])
            for result in results
        )
        total_policy_lists = sum(
            int(result["policy_lists"])
            for result in results
        )
        total_converted_lists = sum(
            int(result["converted_lists"])
            for result in results
        )

        print()
        print("Full MHTML parser audit")
        print("-----------------------")
        print(f"Files found:          {len(results)}")
        print(f"Passed:               {passed}")
        print(f"Failed:               {failed}")
        print(
            f"Policy tables:        "
            f"{total_policy_tables}/"
            f"{total_converted_tables}"
        )
        print(
            f"Policy lists:         "
            f"{total_policy_lists}/"
            f"{total_converted_lists}"
        )
        print(f"Missing dates:        {len(missing_dates)}")

        if missing_dates:
            print()
            print("[INFO] Sections without an extracted effective date:")
            for filename in missing_dates:
                print(f"  {filename}")

        if failed:
            print()
            print("[WARNING] Do not generate Markdown yet.")
            return 2

        print()
        print("[OK] All archived sections passed the local parser audit.")
        print("[OK] No Markdown or corpus files were written.")
        return 0

    except Exception as exc:
        print(f"[ERROR] Full parser audit failed: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())