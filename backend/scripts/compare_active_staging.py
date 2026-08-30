"""
compare_active_staging.py

Read-only comparison between the currently active Waypoint corpus manifest
and the newly generated staging manifest.

No corpus, manifest, database, embedding, or frontend files are modified.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ACTIVE_MANIFEST = PROJECT_ROOT / "data" / "manifest.json"
STAGING_MANIFEST = PROJECT_ROOT / "data" / "staging" / "manifest.json"


def load_pages(path: Path) -> dict[str, dict]:
    """Load manifest pages keyed by section code."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))

        pages = data.get("pages", []) if isinstance(data, dict) else data

        if not isinstance(pages, list):
            raise ValueError(f"Manifest pages are not a list: {path}")

        result: dict[str, dict] = {}

        for entry in pages:
            code = entry.get("section_code")

            if not code:
                raise ValueError(
                    f"Manifest entry has no section_code: {entry}"
                )

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


def main() -> int:
    """Compare active and staging manifests without modifying either."""
    try:
        print("[START] Comparing active corpus with staging corpus")
        print("[INFO] READ ONLY")

        if not ACTIVE_MANIFEST.exists():
            print(f"[ERROR] Missing active manifest: {ACTIVE_MANIFEST}")
            return 1

        if not STAGING_MANIFEST.exists():
            print(f"[ERROR] Missing staging manifest: {STAGING_MANIFEST}")
            return 1

        active = load_pages(ACTIVE_MANIFEST)
        staging = load_pages(STAGING_MANIFEST)

        active_codes = set(active)
        staging_codes = set(staging)

        added = sorted(staging_codes - active_codes)
        removed = sorted(active_codes - staging_codes)
        shared = sorted(active_codes & staging_codes)

        changed_title: list[str] = []
        changed_url: list[str] = []
        changed_date: list[str] = []
        changed_hash: list[str] = []

        for code in shared:
            old = active[code]
            new = staging[code]

            if old.get("title") != new.get("title"):
                changed_title.append(code)

            if old.get("source_url") != new.get("source_url"):
                changed_url.append(code)

            if old.get("effective_date") != new.get("effective_date"):
                changed_date.append(code)

            old_hash = old.get("content_hash")
            new_hash = new.get("content_hash")

            if old_hash != new_hash:
                changed_hash.append(code)

        print()
        print("Active vs staging")
        print("-----------------")
        print(f"Active entries:         {len(active)}")
        print(f"Staging entries:        {len(staging)}")
        print(f"Shared sections:        {len(shared)}")
        print(f"Added to staging:       {len(added)}")
        print(f"Removed from staging:   {len(removed)}")
        print(f"Title changes:          {len(changed_title)}")
        print(f"Source URL changes:     {len(changed_url)}")
        print(f"Effective date changes: {len(changed_date)}")
        print(f"Content hash changes:   {len(changed_hash)}")

        if added:
            print()
            print("[ADDED]")
            for code in added:
                print(
                    f"  {code}: "
                    f"{staging[code].get('title', '')}"
                )

        if removed:
            print()
            print("[REMOVED]")
            for code in removed:
                print(
                    f"  {code}: "
                    f"{active[code].get('title', '')}"
                )

        if changed_title:
            print()
            print("[TITLE CHANGES]")
            for code in changed_title:
                print(f"  {code}")
                print(f"    old: {active[code].get('title')}")
                print(f"    new: {staging[code].get('title')}")

        if changed_url:
            print()
            print("[SOURCE URL CHANGES]")
            for code in changed_url:
                print(f"  {code}")
                print(f"    old: {active[code].get('source_url')}")
                print(f"    new: {staging[code].get('source_url')}")

        if changed_date:
            print()
            print("[EFFECTIVE DATE CHANGES]")
            for code in changed_date:
                print(
                    f"  {code}: "
                    f"{active[code].get('effective_date')} "
                    f"-> {staging[code].get('effective_date')}"
                )

        print()
        print("[OK] Comparison complete.")
        print("[OK] No files were modified.")

        return 0

    except Exception as exc:
        print(f"[ERROR] Comparison failed: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())