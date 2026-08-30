from __future__ import annotations

import csv
import re
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

REPORT_PATH = (
    PROJECT_ROOT
    / "data"
    / "source_archive"
    / "mhtml_validation_report.csv"
)


def extract_html_from_mhtml(file_path: Path) -> tuple[str | None, str | None]:
    """Extract the HTML payload and original Content-Location from an MHTML file."""
    try:
        raw_bytes = file_path.read_bytes()
        message = BytesParser(policy=policy.default).parsebytes(raw_bytes)

        for part in message.walk():
            if part.get_content_type() != "text/html":
                continue

            html = part.get_content()
            content_location = part.get("Content-Location")

            return html, content_location

        return None, None

    except Exception as exc:
        print(f"[ERROR] Failed to read {file_path.name}: {exc}")
        traceback.print_exc()
        return None, None


def normalise_text(value: str) -> str:
    """Collapse whitespace so section-code checks are not affected by page formatting."""
    try:
        return re.sub(r"\s+", " ", value).strip()

    except Exception as exc:
        print(f"[ERROR] Failed to normalise text: {exc}")
        traceback.print_exc()
        return value

def find_main_heading(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    """Find the primary Operational Manual heading inside the main content area."""
    try:
        main_content = soup.select_one("td#main")

        if main_content is None:
            return None, "Main content container td#main was not found."

        # Current INZ Operational Manual pages use p.heading4 for the
        # primary instruction heading. Do not use breadcrumbs or navigation
        # because they can contain unrelated section codes.
        heading = main_content.select_one("p.heading4")

        # Fallback for pages that may use a semantic heading element instead.
        if heading is None:
            heading = main_content.find(["h1", "h2", "h3", "h4"])

        if heading is None:
            return None, "Primary heading was not found inside td#main."

        heading_text = normalise_text(
            heading.get_text(" ", strip=True)
        )

        if not heading_text:
            return None, "Primary heading was empty."

        return heading_text, None

    except Exception as exc:
        print(f"[ERROR] Failed to find main heading: {exc}")
        traceback.print_exc()
        return None, str(exc)

def validate_file(file_path: Path) -> dict[str, str]:
    """Validate one MHTML archive against its primary INZ content heading."""
    try:
        section_code = file_path.stem

        result = {
            "file": file_path.name,
            "section_code": section_code,
            "size_bytes": str(file_path.stat().st_size),
            "mhtml_readable": "No",
            "html_found": "No",
            "section_code_found": "No",
            "page_heading": "",
            "content_location": "",
            "status": "FAIL",
            "notes": "",
        }

        html, content_location = extract_html_from_mhtml(file_path)

        if html is None:
            result["notes"] = "No text/html MIME payload found."
            return result

        result["mhtml_readable"] = "Yes"
        result["html_found"] = "Yes"
        result["content_location"] = content_location or ""

        soup = BeautifulSoup(html, "html.parser")

        page_heading, heading_error = find_main_heading(soup)

        if page_heading is None:
            result["notes"] = heading_error or "Primary heading could not be determined."
            return result

        result["page_heading"] = page_heading

        # The filename must match the section code at the START of the
        # actual instruction heading. This prevents navigation, related
        # historical pages, or other section references from causing a pass.
        section_pattern = re.compile(
            rf"^{re.escape(section_code)}(?![A-Za-z0-9.])",
            re.IGNORECASE,
        )

        if not section_pattern.search(page_heading):
            result["notes"] = (
                f"Filename expects {section_code}, but the main "
                f"instruction heading is: {page_heading}"
            )
            return result

        result["section_code_found"] = "Yes"

        main_content = soup.select_one("td#main")

        if main_content is None:
            result["notes"] = "Main content container td#main was not found."
            return result

        main_text = normalise_text(
            main_content.get_text(" ", strip=True)
        )

        if len(main_text) < 100:
            result["notes"] = (
                "Main instruction content contains very little visible text."
            )
            return result

        result["status"] = "PASS"
        result["notes"] = (
            "Primary INZ instruction heading matches the archived filename."
        )

        return result

    except Exception as exc:
        print(f"[ERROR] Validation failed for {file_path.name}: {exc}")
        traceback.print_exc()

        return {
            "file": file_path.name,
            "section_code": file_path.stem,
            "size_bytes": "",
            "mhtml_readable": "No",
            "html_found": "No",
            "section_code_found": "No",
            "page_heading": "",
            "content_location": "",
            "status": "FAIL",
            "notes": str(exc),
        }


def write_report(results: list[dict[str, str]]) -> None:
    """Write a CSV audit report for later provenance and troubleshooting."""
    try:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "file",
            "section_code",
            "size_bytes",
            "mhtml_readable",
            "html_found",
            "section_code_found",
            "page_heading",
            "content_location",
            "status",
            "notes",
        ]

        with REPORT_PATH.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        print(f"[OK] Report written to: {REPORT_PATH}")

    except Exception as exc:
        print(f"[ERROR] Failed to write report: {exc}")
        traceback.print_exc()
        raise


def main() -> int:
    """Audit every MHTML file in the manually acquired source archive."""
    try:
        print("[START] Validating Waypoint MHTML source archive")
        print(f"[INFO] Archive: {ARCHIVE_DIR}")

        if not ARCHIVE_DIR.exists():
            print(f"[ERROR] Archive directory does not exist: {ARCHIVE_DIR}")
            return 1

        files = sorted(
            ARCHIVE_DIR.glob("*.mhtml"),
            key=lambda path: path.name.lower(),
        )

        if not files:
            print("[ERROR] No .mhtml files found.")
            return 1

        print(f"[INFO] Files found: {len(files)}")

        results = []

        for file_path in files:
            result = validate_file(file_path)
            results.append(result)

            print(
                f"[{result['status']}] "
                f"{result['file']} "
                f"| heading: {result['page_heading'] or 'N/A'}"
            )

        write_report(results)

        passed = sum(
            1 for result in results if result["status"] == "PASS"
        )
        failed = len(results) - passed

        print()
        print("MHTML archive audit")
        print("-------------------")
        print(f"Files found:        {len(results)}")
        print(f"Passed:             {passed}")
        print(f"Failed:             {failed}")
        print(f"Report:             {REPORT_PATH}")

        if failed:
            print()
            print("[WARNING] Do not continue to corpus generation yet.")
            return 2

        print()
        print("[OK] All archived MHTML files passed basic validation.")
        return 0

    except Exception as exc:
        print(f"[ERROR] MHTML archive audit failed: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())