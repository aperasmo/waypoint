"""
check_for_updates.py

Re-checks every page already in manifest.json against the live INZ site,
and only overwrites a local file when the policy has actually changed
(detected via the "Effective DD/MM/YYYY" date on the page, not just
whether the file exists).

This is what makes staying current *automatic* rather than something you
have to remember to re-run with --force. Designed to run unattended on a
schedule (see the Task Scheduler section at the bottom of this file).

WHY THIS IS SEPARATE FROM collect_manual.py:
collect_manual.py's job is discovery -- finding pages you don't have yet.
This script's job is freshness -- checking pages you already have. They
can both run on a schedule; this one should run more often, since content
changes matter more than brand-new pages appearing.

USAGE
    pip install -r requirements.txt   (same requirements as collect_manual.py)
    python check_for_updates.py --manifest ../manifest.json

    # Dry run: report what would change without writing anything
    python check_for_updates.py --manifest ../manifest.json --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USER_AGENT = "WaypointManualCollector/0.1 (personal research project; contact: allanperasmo@gmail.com)"
DEFAULT_DELAY_SECONDS = 2.0
MAX_RETRIES = 3
EFFECTIVE_DATE_RE = re.compile(r"Effective\s+(\d{2}/\d{2}/\d{4})")


def content_hash(text: str) -> str:
    """Fallback change signal for pages where no 'Effective' date could be
    parsed. A hash of the extracted body catches real content changes that
    date-parsing alone would miss -- e.g. a page whose date line renders in
    a format the regex doesn't expect."""
    normalized = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


@dataclass
class CheckResult:
    section_code: str
    status: str  # "unchanged" | "changed" | "changed_no_date" | "fetch_failed"
    old_date: str | None
    new_date: str | None


def fetch(session: requests.Session, url: str) -> str | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=20)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            wait = 2 ** attempt
            print(f"  retry {attempt}/{MAX_RETRIES} after error ({e}); waiting {wait}s")
            time.sleep(wait)
    return None


def extract_content(html: str) -> tuple[str, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    content = (
        soup.find("div", id=re.compile("content", re.I))
        or soup.find("main")
        or soup.find("article")
        or soup.body
    )
    text = content.get_text("\n", strip=True) if content else soup.get_text("\n", strip=True)
    date_match = EFFECTIVE_DATE_RE.search(text)
    return text, (date_match.group(1) if date_match else None)


def parse_front_matter(md_text: str) -> dict:
    """Minimal front-matter reader: just enough to pull effective_date back out
    of files this pipeline itself wrote, without pulling in a YAML dependency."""
    if not md_text.startswith("---"):
        return {}
    end = md_text.find("---", 3)
    if end == -1:
        return {}
    fm_block = md_text[3:end]
    result = {}
    for line in fm_block.strip().splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        result[key.strip()] = json.loads(value.strip()) if value.strip().startswith('"') else value.strip()
    return result


def run(manifest_path: Path, delay: float, dry_run: bool):
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    pages = data.get("pages", [])
    base_dir = manifest_path.parent

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    results: list[CheckResult] = []
    changelog_entries = []

    for i, entry in enumerate(pages, 1):
        code = entry["section_code"]
        url = entry["source_url"]
        file_path = base_dir / entry["file"].replace("\\", "/")

        print(f"[{i}/{len(pages)}] Checking {code}: {url}")
        html = fetch(session, url)
        if html is None:
            results.append(CheckResult(code, "fetch_failed", entry.get("effective_date"), None))
            print("  FAILED to fetch, leaving local copy untouched")
            time.sleep(delay)
            continue

        new_text, new_date = extract_content(html)
        new_hash = content_hash(new_text)
        old_date = entry.get("effective_date")
        old_hash = entry.get("content_hash")

        if new_date is not None:
            # Normal path: compare dates, the authoritative signal when available.
            changed = new_date != old_date
        else:
            # Fallback path: this page has no parseable "Effective" date
            # (either genuinely, like an index page, or because extraction
            # missed it). Either way, don't just skip -- compare content
            # hashes instead so real edits still get caught.
            changed = old_hash is not None and new_hash != old_hash
            if old_hash is None:
                # First time we've seen this page without a date: nothing
                # to compare against yet, just record the hash.
                changed = False

        if not changed:
            results.append(CheckResult(code, "unchanged", old_date, new_date))
            entry["content_hash"] = new_hash
            time.sleep(delay)
            continue

        status = "changed" if new_date is not None else "changed_no_date"
        results.append(CheckResult(code, status, old_date, new_date))
        if status == "changed":
            print(f"  CHANGED: {old_date} -> {new_date}")
        else:
            print(f"  CHANGED (no date on page, detected via content hash)")
        changelog_entries.append(
            {
                "section_code": code,
                "title": entry.get("title"),
                "old_effective_date": old_date,
                "new_effective_date": new_date,
                "detected_via": "date" if new_date is not None else "content_hash",
                "source_url": url,
                "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

        if not dry_run:
            front_matter = {
                "section_code": code,
                "title": entry.get("title"),
                "source_url": url,
                "effective_date": new_date,
                "fetched_date": time.strftime("%Y-%m-%d"),
            }
            fm_lines = "\n".join(f"{k}: {json.dumps(v)}" for k, v in front_matter.items())
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(f"---\n{fm_lines}\n---\n\n{new_text}\n", encoding="utf-8")
            entry["effective_date"] = new_date
            entry["content_hash"] = new_hash

        time.sleep(delay)

    # Summary
    changed = [r for r in results if r.status in ("changed", "changed_no_date")]
    unchanged = [r for r in results if r.status == "unchanged"]
    failed = [r for r in results if r.status == "fetch_failed"]

    print("\n--- Summary ---")
    print(f"Checked: {len(results)}")
    print(f"Unchanged: {len(unchanged)}")
    print(f"Changed: {len(changed)}")
    print(f"Fetch failed: {len(failed)}")

    if changed:
        print("\nChanged sections:")
        for r in changed:
            if r.status == "changed":
                print(f"  {r.section_code}: {r.old_date} -> {r.new_date}")
            else:
                print(f"  {r.section_code}: (no date on page, changed per content hash)")

    if not dry_run:
        manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        changelog_path = base_dir / "changelog.json"
        existing_log = []
        if changelog_path.exists():
            try:
                existing_log = json.loads(changelog_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing_log = []
        existing_log.extend(changelog_entries)
        changelog_path.write_text(json.dumps(existing_log, indent=2), encoding="utf-8")
        print(f"\nmanifest.json updated. changelog.json now has {len(existing_log)} recorded changes total.")
    else:
        print("\nDry run: nothing was written.")


def main():
    parser = argparse.ArgumentParser(description="Check collected INZ manual sections for content changes.")
    parser.add_argument("--manifest", default="../manifest.json", help="Path to manifest.json")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS, help="Seconds between requests")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing files")
    args = parser.parse_args()
    run(Path(args.manifest), args.delay, args.dry_run)


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# MAKING THIS RUN AUTOMATICALLY (Windows Task Scheduler)
# ---------------------------------------------------------------------------
#
# One-time setup, from an elevated PowerShell prompt:
#
#   schtasks /create /tn "Waypoint Manual Update Check" ^
#     /tr "python C:\path\to\scraper\check_for_updates.py --manifest C:\path\to\manifest.json" ^
#     /sc daily /st 07:00
#
# This runs the check every morning at 7am. Given the SMC changes land
# 24 August 2026, a daily check through late August is worth it; you can
# drop to weekly afterward with /sc weekly instead.
#
# To verify it's registered:      schtasks /query /tn "Waypoint Manual Update Check"
# To remove it later:             schtasks /delete /tn "Waypoint Manual Update Check" /f
#
# Note: adjust the "python" call to a full path (e.g. C:\Python312\python.exe)
# if Task Scheduler can't find python.exe on its own PATH -- scheduled tasks
# don't always inherit the same environment as an interactive terminal.