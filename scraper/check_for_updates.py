"""
check_for_updates.py

Re-checks pages already in data/manifest.json against the live INZ site and
only overwrites a local file when policy content changed, a manifest-listed
local file is missing, or a targeted maintenance refresh was explicitly
requested.

Change detection uses both the page's "Effective DD/MM/YYYY" date and a hash
of the extracted policy body. The hash catches content changes where INZ keeps
the same effective date.

WHY THIS IS SEPARATE FROM collect_manual.py:
collect_manual.py's job is discovery - finding pages you do not have yet.
This script's job is freshness - checking pages you already have.

USAGE
    # From the Waypoint backend folder:
    uv run --with requests --with beautifulsoup4 python ..\\scraper\\check_for_updates.py

    # Check only selected sections without writing anything:
    uv run --with requests --with beautifulsoup4 python ..\\scraper\\check_for_updates.py \
        --sections V3.10 --dry-run --delay 0

    # Force a targeted maintenance refresh, still read-only:
    uv run --with requests --with beautifulsoup4 python ..\\scraper\\check_for_updates.py \
        --sections SR2.10 SR3.15 SR3.30 --force-refresh --dry-run --delay 0
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
from bs4 import BeautifulSoup, NavigableString, Tag

USER_AGENT = "WaypointManualCollector/0.1 (personal research project; contact: allanperasmo@gmail.com)"
DEFAULT_DELAY_SECONDS = 2.0
MAX_RETRIES = 3
# INZ dates may use one- or two-digit days/months, e.g. 8/12/2025.
EFFECTIVE_DATE_RE = re.compile(r"Effective\s+(\d{1,2}/\d{1,2}/\d{4})")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_MANIFEST_PATH = REPO_ROOT / "data" / "manifest.json"


@dataclass
class CheckResult:
    section_code: str
    status: str
    old_date: str | None
    new_date: str | None
    detail: str | None = None


def content_hash(text: str) -> str:
    """Return a stable hash of extracted policy text."""
    normalized = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def fetch(session: requests.Session, url: str) -> str | None:
    """Fetch one INZ page with bounded retry/backoff."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(url, timeout=20)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            wait = 2**attempt
            print(
                f"  retry {attempt}/{MAX_RETRIES} after error "
                f"({exc}); waiting {wait}s"
            )
            time.sleep(wait)
    return None


def _positive_int(value: object, default: int = 1) -> int:
    try:
        parsed = int(str(value))
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def _cell_text(cell: Tag) -> str:
    """Normalise one HTML table cell for Markdown output."""
    text = cell.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text.replace("|", r"\|")


def _table_to_markdown(table: Tag) -> str:
    """Convert one INZ policy table to Markdown.

    INZ uses rowspan heavily, especially in SR3.30. Row-spanned values are
    repeated into subsequent rows so each resulting row remains meaningful
    when chunked or retrieved independently.
    """
    rows = [
        row
        for row in table.find_all("tr")
        if row.find_parent("table") is table
    ]
    if not rows:
        return ""

    grid: list[list[str]] = []
    active_rowspans: dict[int, tuple[int, str]] = {}

    for row in rows:
        values: list[str] = []
        column = 0

        def consume_active_span() -> bool:
            nonlocal column
            span = active_rowspans.get(column)
            if span is None:
                return False

            remaining, value = span
            values.append(value)
            if remaining <= 1:
                del active_rowspans[column]
            else:
                active_rowspans[column] = (remaining - 1, value)
            column += 1
            return True

        cells = [
            cell
            for cell in row.find_all(["th", "td"], recursive=False)
            if cell.find_parent("tr") is row
        ]

        for cell in cells:
            while consume_active_span():
                pass

            value = _cell_text(cell)
            rowspan = _positive_int(cell.get("rowspan"), 1)
            colspan = _positive_int(cell.get("colspan"), 1)

            for offset in range(colspan):
                rendered_value = value if offset == 0 else ""
                values.append(rendered_value)

                if rowspan > 1:
                    active_rowspans[column] = (
                        rowspan - 1,
                        rendered_value,
                    )
                column += 1

        if active_rowspans:
            last_active_column = max(active_rowspans)
            while column <= last_active_column:
                if not consume_active_span():
                    values.append("")
                    column += 1

        grid.append(values)

    width = max((len(row) for row in grid), default=0)
    if width == 0:
        return ""

    for row in grid:
        row.extend([""] * (width - len(row)))

    lines = [
        "| " + " | ".join(grid[0]) + " |",
        "| " + " | ".join(["---"] * width) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in grid[1:])
    return "\n".join(lines)



def _alpha_marker(index: int) -> str:
    """Return 1-based lowercase alphabetic markers: a, b, ..., z, aa, ab."""
    if index < 1:
        raise ValueError("index must be >= 1")

    chars: list[str] = []
    value = index
    while value:
        value, remainder = divmod(value - 1, 26)
        chars.append(chr(ord("a") + remainder))
    return "".join(reversed(chars))


def _roman_marker(index: int) -> str:
    """Return a 1-based lowercase Roman numeral."""
    if index < 1:
        raise ValueError("index must be >= 1")

    numerals = (
        (1000, "m"),
        (900, "cm"),
        (500, "d"),
        (400, "cd"),
        (100, "c"),
        (90, "xc"),
        (50, "l"),
        (40, "xl"),
        (10, "x"),
        (9, "ix"),
        (5, "v"),
        (4, "iv"),
        (1, "i"),
    )

    parts: list[str] = []
    value = index
    for number, symbol in numerals:
        while value >= number:
            parts.append(symbol)
            value -= number
    return "".join(parts)


def _policy_list_kind(lst: Tag) -> str | None:
    """Return the INZ policy-list kind observed in the Operational Manual."""
    classes = set(lst.get("class") or [])
    if "listletter" in classes:
        return "letter"
    if "listroman" in classes:
        return "roman"
    return None


def _direct_list_items(lst: Tag) -> list[Tag]:
    """Return only list items that belong directly to this list."""
    return [
        li
        for li in lst.find_all("li", recursive=False)
        if li.find_parent(["ol", "ul"]) is lst
    ]


def _direct_item_text(li: Tag) -> str:
    """Return one list item's own text, excluding nested policy lists."""
    clone = BeautifulSoup(str(li), "html.parser")
    node = clone.find("li")
    if node is None:
        return ""

    for nested in node.select("ol.listletter, ol.listroman"):
        nested.decompose()

    value = node.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", value).strip()


def _policy_list_to_markdown(
    lst: Tag,
    depth: int = 0,
) -> tuple[str, int]:
    """Convert one INZ policy-list tree to indented Markdown-like clauses.

    The live Operational Manual uses:
      - ol.listletter for (a), (b), (c) ...
      - ol.listroman  for (i), (ii), (iii) ...

    Nested lists are converted recursively so legal/policy relationships such
    as "as defined in (a) above" remain explicit in the stored corpus.
    """
    kind = _policy_list_kind(lst)
    if kind is None:
        return "", 0

    lines: list[str] = []
    converted_lists = 1
    indent = "    " * depth

    for index, li in enumerate(_direct_list_items(lst), start=1):
        if kind == "letter":
            marker = _alpha_marker(index)
        else:
            marker = _roman_marker(index)

        own_text = _direct_item_text(li)
        if own_text:
            lines.append(f"{indent}({marker}) {own_text}")

        nested_lists = [
            child
            for child in li.find_all(["ol", "ul"], recursive=False)
            if _policy_list_kind(child) is not None
        ]

        for nested in nested_lists:
            nested_markdown, nested_count = _policy_list_to_markdown(
                nested,
                depth + 1,
            )
            if nested_markdown:
                lines.append(nested_markdown)
            converted_lists += nested_count

    return "\n".join(lines), converted_lists


def _convert_policy_lists(target: Tag) -> tuple[int, int]:
    """Convert observed INZ policy-list classes and return counts.

    Only top-level policy-list trees are replaced directly. Nested lists are
    handled recursively by _policy_list_to_markdown().
    """
    policy_lists = list(target.select("ol.listletter, ol.listroman"))
    policy_list_count = len(policy_lists)

    top_level_lists = [
        lst
        for lst in policy_lists
        if lst.find_parent("ol", class_=["listletter", "listroman"]) is None
    ]

    converted_list_count = 0

    for lst in top_level_lists:
        markdown, converted = _policy_list_to_markdown(lst)
        if not markdown:
            continue

        lst.replace_with(NavigableString(f"\n\n{markdown}\n\n"))
        converted_list_count += converted

    return policy_list_count, converted_list_count


def _remove_navigation_chrome(target: Tag) -> tuple[int, int]:
    """Remove known INZ page furniture without touching policy content.

    Observed Operational Manual pages place navigation/index material in
    elements with class ``relatedtopics``. The outer layout table also
    contains a small row whose only purpose is "Top of page | Print this page".

    Returns:
        related_blocks_removed
        utility_rows_removed
    """
    related_blocks = list(target.select(".relatedtopics"))
    related_blocks_removed = len(related_blocks)

    for block in related_blocks:
        block.decompose()

    utility_rows_removed = 0

    for row in list(target.find_all("tr")):
        row_text = re.sub(
            r"\s+",
            " ",
            row.get_text(" ", strip=True),
        ).strip().casefold()

        # Keep this deliberately narrow: only remove a short utility row that
        # contains both known page-control labels and no meaningful policy text.
        if (
            "top of page" in row_text
            and "print this page" in row_text
            and len(row_text) <= 80
        ):
            row.decompose()
            utility_rows_removed += 1

    return related_blocks_removed, utility_rows_removed

def extract_content(
    html: str,
) -> tuple[str, str | None, int, int, int, int, int, int, int]:
    """Extract INZ policy text while preserving policy tables.

    Returns:
        text: extracted Markdown-like policy body
        effective_date: Effective DD/MM/YYYY value when present
        html_table_count: every HTML table in the selected content target
        policy_table_count: tables explicitly marked class="tableintopic"
        converted_table_count: policy tables successfully converted
        policy_list_count: observed INZ policy-list elements
        converted_list_count: policy-list elements successfully converted
        related_blocks_removed: navigation/index blocks removed
        utility_rows_removed: "Top of page / Print this page" rows removed
    """
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()

    content = (
        soup.find("div", id=re.compile("content", re.I))
        or soup.find("main")
        or soup.find("article")
        or soup.body
    )
    target = content if content is not None else soup

    (
        related_blocks_removed,
        utility_rows_removed,
    ) = _remove_navigation_chrome(target)

    html_table_count = len(target.find_all("table"))
    policy_tables = list(target.select("table.tableintopic"))
    policy_table_count = len(policy_tables)
    converted_table_count = 0

    for table in policy_tables:
        markdown = _table_to_markdown(table)
        if not markdown:
            continue

        table.replace_with(NavigableString(f"\n\n{markdown}\n\n"))
        converted_table_count += 1

    policy_list_count, converted_list_count = _convert_policy_lists(target)

    text = target.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    date_match = EFFECTIVE_DATE_RE.search(text)
    effective_date = date_match.group(1) if date_match else None

    return (
        text,
        effective_date,
        html_table_count,
        policy_table_count,
        converted_table_count,
        policy_list_count,
        converted_list_count,
        related_blocks_removed,
        utility_rows_removed,
    )


def _write_section_file(
    file_path: Path,
    entry: dict,
    text: str,
    effective_date: str | None,
) -> None:
    """Write one canonical Markdown section file."""
    front_matter = {
        "section_code": entry["section_code"],
        "title": entry.get("title"),
        "source_url": entry["source_url"],
        "effective_date": effective_date,
        "fetched_date": time.strftime("%Y-%m-%d"),
    }
    fm_lines = "\n".join(
        f"{key}: {json.dumps(value)}"
        for key, value in front_matter.items()
    )

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        f"---\n{fm_lines}\n---\n\n{text}\n",
        encoding="utf-8",
    )


def _load_changelog(changelog_path: Path) -> list[dict]:
    if not changelog_path.exists():
        return []
    try:
        data = json.loads(changelog_path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def run(
    manifest_path: Path,
    delay: float,
    dry_run: bool,
    selected_sections: list[str] | None = None,
    force_refresh: bool = False,
) -> None:
    """Check manifest-listed sections and optionally update local copies."""
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    all_pages = data.get("pages", [])
    base_dir = manifest_path.parent

    requested = set(selected_sections or [])
    if requested:
        known_codes = {entry["section_code"] for entry in all_pages}
        unknown_codes = sorted(requested - known_codes)
        if unknown_codes:
            raise SystemExit(
                "Unknown section code(s): " + ", ".join(unknown_codes)
            )
        pages = [
            entry
            for entry in all_pages
            if entry["section_code"] in requested
        ]
    else:
        pages = all_pages

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    results: list[CheckResult] = []
    changelog_entries: list[dict] = []
    manifest_dirty = False

    for index, entry in enumerate(pages, 1):
        code = entry["section_code"]
        url = entry["source_url"]
        file_path = base_dir / entry["file"].replace("\\", "/")
        local_missing = not file_path.exists()

        print(f"[{index}/{len(pages)}] Checking {code}: {url}")

        html = fetch(session, url)
        if html is None:
            results.append(
                CheckResult(
                    code,
                    "fetch_failed",
                    entry.get("effective_date"),
                    None,
                    "request failed",
                )
            )
            print("  FAILED to fetch, leaving local copy untouched")
            time.sleep(delay)
            continue

        (
            new_text,
            new_date,
            html_tables,
            policy_tables,
            converted_tables,
            policy_lists,
            converted_lists,
            related_blocks_removed,
            utility_rows_removed,
        ) = extract_content(html)

        if html_tables:
            print(
                f"  Tables: html={html_tables}, "
                f"policy={policy_tables}, converted={converted_tables}"
            )

        if policy_tables != converted_tables:
            print(
                "  TABLE EXTRACTION FAILED: "
                f"policy={policy_tables}, converted={converted_tables}. "
                "Skipping this section."
            )
            results.append(
                CheckResult(
                    code,
                    "fetch_failed",
                    entry.get("effective_date"),
                    new_date,
                    "table extraction validation failed",
                )
            )
            time.sleep(delay)
            continue

        if policy_lists:
            print(
                f"  Lists: policy={policy_lists}, "
                f"converted={converted_lists}"
            )

        if policy_lists != converted_lists:
            print(
                "  LIST EXTRACTION FAILED: "
                f"policy={policy_lists}, converted={converted_lists}. "
                "Skipping this section."
            )
            results.append(
                CheckResult(
                    code,
                    "fetch_failed",
                    entry.get("effective_date"),
                    new_date,
                    "list extraction validation failed",
                )
            )
            time.sleep(delay)
            continue

        if related_blocks_removed or utility_rows_removed:
            print(
                "  Navigation removed: "
                f"relatedtopics={related_blocks_removed}, "
                f"utility_rows={utility_rows_removed}"
            )

        new_hash = content_hash(new_text)
        old_date = entry.get("effective_date")
        old_hash = entry.get("content_hash")

        date_changed = new_date is not None and new_date != old_date
        hash_changed = old_hash is not None and new_hash != old_hash
        policy_changed = date_changed or hash_changed

        if local_missing:
            print(f"  MISSING LOCAL FILE: {file_path}")
            print("  Will restore it from the manifest source URL.")
            results.append(
                CheckResult(
                    code,
                    "missing_local",
                    old_date,
                    new_date,
                    "restore from manifest source URL",
                )
            )

            if not dry_run:
                _write_section_file(file_path, entry, new_text, new_date)
                entry["effective_date"] = new_date
                entry["content_hash"] = new_hash
                manifest_dirty = True
                changelog_entries.append(
                    {
                        "section_code": code,
                        "title": entry.get("title"),
                        "old_effective_date": old_date,
                        "new_effective_date": new_date,
                        "detected_via": "missing_local_file",
                        "source_url": url,
                        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

            time.sleep(delay)
            continue

        if policy_changed:
            if date_changed:
                detail = f"effective date changed: {old_date} -> {new_date}"
                detected_via = "date"
                print(f"  CHANGED: {old_date} -> {new_date}")
            else:
                detail = "content changed with same effective date"
                detected_via = "content_hash"
                print(
                    "  CHANGED: content hash differs while effective date "
                    "is unchanged"
                )

            results.append(
                CheckResult(code, "changed", old_date, new_date, detail)
            )

            if not dry_run:
                _write_section_file(file_path, entry, new_text, new_date)
                entry["effective_date"] = new_date
                entry["content_hash"] = new_hash
                manifest_dirty = True
                changelog_entries.append(
                    {
                        "section_code": code,
                        "title": entry.get("title"),
                        "old_effective_date": old_date,
                        "new_effective_date": new_date,
                        "detected_via": detected_via,
                        "source_url": url,
                        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

            time.sleep(delay)
            continue

        if force_refresh:
            print("  MAINTENANCE REFRESH: policy signal unchanged")
            results.append(
                CheckResult(
                    code,
                    "maintenance_refreshed",
                    old_date,
                    new_date,
                    "forced maintenance refresh",
                )
            )

            if not dry_run:
                _write_section_file(file_path, entry, new_text, new_date)
                entry["effective_date"] = new_date
                entry["content_hash"] = new_hash
                manifest_dirty = True
                changelog_entries.append(
                    {
                        "section_code": code,
                        "title": entry.get("title"),
                        "old_effective_date": old_date,
                        "new_effective_date": new_date,
                        "detected_via": "maintenance_refresh",
                        "source_url": url,
                        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

            time.sleep(delay)
            continue

        results.append(CheckResult(code, "unchanged", old_date, new_date))

        # Backfill/refresh manifest metadata without rewriting the section file.
        if not dry_run and (
            entry.get("content_hash") != new_hash
            or entry.get("effective_date") != new_date
        ):
            entry["content_hash"] = new_hash
            entry["effective_date"] = new_date
            manifest_dirty = True

        time.sleep(delay)

    changed = [result for result in results if result.status == "changed"]
    maintenance = [
        result
        for result in results
        if result.status == "maintenance_refreshed"
    ]
    missing = [
        result
        for result in results
        if result.status == "missing_local"
    ]
    unchanged = [
        result
        for result in results
        if result.status == "unchanged"
    ]
    failed = [
        result
        for result in results
        if result.status == "fetch_failed"
    ]

    print("\n--- Summary ---")
    print(f"Checked: {len(results)}")
    print(f"Unchanged: {len(unchanged)}")
    print(f"Changed: {len(changed)}")
    print(f"Maintenance refreshed: {len(maintenance)}")
    print(f"Missing local: {len(missing)}")
    print(f"Fetch failed: {len(failed)}")

    if changed:
        print("\nChanged sections:")
        for result in changed:
            print(f"  {result.section_code}: {result.detail}")

    if maintenance:
        print("\nMaintenance refresh sections:")
        for result in maintenance:
            print(f"  {result.section_code}: {result.detail}")

    if missing:
        print("\nMissing local files:")
        for result in missing:
            print(f"  {result.section_code}: {result.detail}")

    if failed:
        print("\nFailed sections:")
        for result in failed:
            print(f"  {result.section_code}: {result.detail}")

    if dry_run:
        print("\nDry run: nothing was written.")
        return

    if manifest_dirty:
        manifest_path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )

    if changelog_entries:
        changelog_path = base_dir / "changelog.json"
        existing_log = _load_changelog(changelog_path)
        existing_log.extend(changelog_entries)
        changelog_path.write_text(
            json.dumps(existing_log, indent=2),
            encoding="utf-8",
        )
        print(
            f"\nmanifest.json updated. changelog.json now has "
            f"{len(existing_log)} recorded changes total."
        )
    elif manifest_dirty:
        print("\nmanifest.json metadata updated. No changelog entry was required.")
    else:
        print("\nNo files or manifest entries needed updating.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check collected INZ manual sections for content changes."
    )
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST_PATH),
        help="Path to manifest.json",
    )
    parser.add_argument(
        "--sections",
        nargs="+",
        help="Optional section codes to check, for example V3.10 SR3.15",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help=(
            "Rewrite selected local files even when policy change signals "
            "are unchanged. Use for targeted extraction maintenance."
        ),
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help="Seconds between requests",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing files",
    )
    args = parser.parse_args()

    run(
        Path(args.manifest).resolve(),
        args.delay,
        args.dry_run,
        selected_sections=args.sections,
        force_refresh=args.force_refresh,
    )


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# MAKING THIS RUN AUTOMATICALLY (Windows Task Scheduler)
# ---------------------------------------------------------------------------
#
# Keep scheduling disabled until the corpus/update pipeline has completed its
# current hardening and evaluation pass. When enabled later, use an explicit
# Python/uv path and the canonical data/manifest.json path.