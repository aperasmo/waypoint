"""
audit_browse_taxonomy.py

Read-only compatibility check between the current manually archived
Operational Manual corpus and Waypoint's browse taxonomy.

No corpus, manifest, database, or frontend files are modified.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ARCHIVE_DIR = (
    PROJECT_ROOT
    / "data"
    / "source_archive"
    / "operational_manual"
)

CATEGORIES_PATH = PROJECT_ROOT / "data" / "categories.json"


def matches(section_code: str, prefixes: list[str]) -> bool:
    """Apply the same prefix semantics used by /browse/sections."""
    try:
        return any(
            section_code == prefix
            or section_code.startswith(f"{prefix}.")
            for prefix in prefixes
        )

    except Exception as exc:
        print(f"[ERROR] Failed matching {section_code}: {exc}")
        traceback.print_exc()
        raise


def main() -> int:
    """Check whether every current archived section is browseable."""
    try:
        print("[START] Auditing browse taxonomy compatibility")
        print("[INFO] READ ONLY")

        if not CATEGORIES_PATH.exists():
            print(f"[ERROR] Missing taxonomy: {CATEGORIES_PATH}")
            return 1

        if not ARCHIVE_DIR.exists():
            print(f"[ERROR] Missing archive: {ARCHIVE_DIR}")
            return 1

        taxonomy = json.loads(
            CATEGORIES_PATH.read_text(encoding="utf-8")
        )

        groups = taxonomy.get("groups", [])

        section_codes = sorted(
            path.stem
            for path in ARCHIVE_DIR.glob("*.mhtml")
        )

        if not section_codes:
            print("[ERROR] No MHTML sections found.")
            return 1

        uncovered: list[str] = []
        multiple: dict[str, list[str]] = {}

        for section_code in section_codes:
            branch_matches: list[str] = []

            for group in groups:
                for branch in group.get("branches", []):
                    prefixes = branch.get("prefixes", [])

                    if matches(section_code, prefixes):
                        branch_matches.append(
                            f"{group['id']} -> {branch['label']}"
                        )

            if not branch_matches:
                uncovered.append(section_code)

            if len(branch_matches) > 1:
                multiple[section_code] = branch_matches

        print()
        print("Browse taxonomy audit")
        print("---------------------")
        print(f"Archived sections:     {len(section_codes)}")
        print(f"Uncovered sections:    {len(uncovered)}")
        print(f"Multi-branch sections: {len(multiple)}")

        if uncovered:
            print()
            print("[FAIL] Sections not reachable through any browse branch:")
            for section_code in uncovered:
                print(f"  {section_code}")

        if multiple:
            print()
            print("[INFO] Sections appearing in multiple branches:")
            for section_code, branches in multiple.items():
                print(f"  {section_code}")
                for branch in branches:
                    print(f"    - {branch}")

        if uncovered:
            print()
            print(
                "[WARNING] Update categories.json before promoting "
                "the refreshed corpus."
            )
            return 2

        print()
        print(
            "[OK] Every archived section is reachable through "
            "the current browse taxonomy."
        )
        print(
            "[OK] Frontend browse routing remains compatible."
        )

        return 0

    except Exception as exc:
        print(f"[ERROR] Browse taxonomy audit failed: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())