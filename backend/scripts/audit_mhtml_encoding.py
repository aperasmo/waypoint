"""
Audit character encoding of archived INZ Operational Manual MHTML files.

Read-only. No source, staging, corpus, manifest, database, or frontend files
are modified.
"""

from __future__ import annotations

import sys
import traceback
from collections import Counter
from email import policy
from email.parser import BytesParser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ARCHIVE_DIR = (
    PROJECT_ROOT
    / "data"
    / "source_archive"
    / "operational_manual"
)


def main() -> int:
    """Check declared charsets and UTF-8 validity of all HTML MIME parts."""
    try:
        print("[START] Auditing MHTML encoding")
        print("[INFO] READ ONLY")

        files = sorted(ARCHIVE_DIR.glob("*.mhtml"))

        charset_counts: Counter[str] = Counter()
        html_parts = 0
        utf8_passed = 0
        utf8_failed: list[tuple[str, str]] = []

        for path in files:
            message = BytesParser(
                policy=policy.default
            ).parsebytes(
                path.read_bytes()
            )

            for part in message.walk():
                if part.get_content_type() != "text/html":
                    continue

                payload = part.get_payload(decode=True)

                if payload is None:
                    continue

                html_parts += 1

                charset = part.get_content_charset()

                charset_counts[
                    charset.lower() if charset else "<none>"
                ] += 1

                try:
                    payload.decode("utf-8", errors="strict")
                    utf8_passed += 1

                except UnicodeDecodeError as exc:
                    utf8_failed.append(
                        (
                            path.name,
                            str(exc),
                        )
                    )

        print()
        print("MHTML encoding audit")
        print("--------------------")
        print(f"Files found:        {len(files)}")
        print(f"HTML MIME parts:    {html_parts}")
        print(f"UTF-8 valid:        {utf8_passed}")
        print(f"UTF-8 failures:     {len(utf8_failed)}")

        print()
        print("[DECLARED CHARSETS]")

        for charset, count in sorted(charset_counts.items()):
            print(f"  {charset}: {count}")

        if utf8_failed:
            print()
            print("[UTF-8 FAILURES]")

            for filename, reason in utf8_failed:
                print(f"  {filename}: {reason}")

            return 2

        print()
        print("[OK] Every archived HTML MIME part is valid UTF-8.")
        print("[OK] No files were modified.")

        return 0

    except Exception as exc:
        print(f"[ERROR] Encoding audit failed: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())