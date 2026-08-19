"""
collect_manual.py

Collects sections of the public INZ Operational Manual for the Waypoint
RAG project's ingestion pipeline.

WHY THIS RUNS LOCALLY, NOT IN CLAUDE'S SANDBOX:
Claude's bash environment has no outbound network access, so this script
cannot be executed inside that sandbox. Run it on your own machine, where
you have normal internet access.

WHAT IT DOES
1. Reads robots.txt and respects Disallow rules and crawl-delay.
2. Starts from the manual's table of contents (toc.htm) and walks every
   /opsmanual/<id>.htm link, optionally filtered to a prefix allowlist
   (e.g. only "SR" and "WD" section codes).
3. Rate-limits requests (default: 1 request every 2 seconds) and retries
   transient failures with exponential backoff.
4. Extracts the page title, effective date, and body text, and writes one
   markdown file per section with YAML front matter, matching the format
   Claude already used for the seed files in this folder.
5. Is resumable: pages already saved are skipped on the next run, unless
   --force is passed.
6. Writes/updates a crawl inventory, not the curated runtime manifest.

USAGE
    pip install -r requirements.txt
    python collect_manual.py --prefixes SR WD --out ../
    python collect_manual.py --prefixes SR WD --out ../ --force   # re-download everything
    python collect_manual.py --all --out ../                     # collect the ENTIRE manual (slow, be deliberate about this)

A NOTE ON SCOPE AND COURTESY
This script is deliberately conservative by default: a real crawl-delay,
a real User-Agent that identifies the tool honestly, and a hard concurrency
of 1 (no parallel requests). Before doing a full-manual run, it's worth
rereading immigration.govt.nz's website terms of use. This is public
government information, but "publicly available" and "unrestricted bulk
scraping" are not automatically the same thing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.robotparser
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

# Requires Python 3.10+ (uses the `X | None` union syntax below).

BASE_URL = "https://www.immigration.govt.nz"
TOC_URL = f"{BASE_URL}/opsmanual/toc.htm"
USER_AGENT = "WaypointManualCollector/0.1 (personal research project; contact: allanperasmo@gmail.com)"
DEFAULT_DELAY_SECONDS = 2.0
MAX_RETRIES = 3
PAGE_ID_RE = re.compile(r"/opsmanual/(\d+)\.htm$")
SECTION_CODE_RE = re.compile(r"^([A-Z]{1,3}\d+(?:\.\d+)*)\s+(.*)$")
EFFECTIVE_DATE_RE = re.compile(r"Effective\s+(\d{2}/\d{2}/\d{4})")


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
    """Convert one INZ policy table to Markdown while expanding rowspans."""
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
    """Convert one INZ policy-list tree to explicit indented clauses."""
    kind = _policy_list_kind(lst)
    if kind is None:
        return "", 0

    lines: list[str] = []
    converted_lists = 1
    indent = "    " * depth

    for index, li in enumerate(_direct_list_items(lst), start=1):
        marker = _alpha_marker(index) if kind == "letter" else _roman_marker(index)

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
    """Convert observed INZ policy-list classes and return observed/converted counts."""
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
    """Remove known INZ page furniture without touching policy content."""
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

        if (
            "top of page" in row_text
            and "print this page" in row_text
            and len(row_text) <= 80
        ):
            row.decompose()
            utility_rows_removed += 1

    return related_blocks_removed, utility_rows_removed


def content_hash(text: str) -> str:
    """Return the same stable policy-body hash used by check_for_updates.py."""
    normalized = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


@dataclass
class Page:
    url: str
    page_id: str
    section_code: str | None = None
    title: str | None = None


@dataclass
class Collector:
    out_dir: Path
    manifest_path: Path
    prefixes: list[str] | None
    delay: float
    session: requests.Session = field(default_factory=requests.Session)
    manifest: list[dict] = field(default_factory=list)

    def __post_init__(self):
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.rp = urllib.robotparser.RobotFileParser()
        self.rp.set_url(f"{BASE_URL}/robots.txt")
        self.rp.read()

    def allowed(self, url: str) -> bool:
        return self.rp.can_fetch(USER_AGENT, url)

    def fetch(self, url: str) -> str | None:
        if not self.allowed(url):
            print(f"  SKIP (robots.txt disallows): {url}")
            return None
        last_err = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, timeout=20)
                resp.raise_for_status()
                return resp.text
            except requests.RequestException as e:
                last_err = e
                wait = 2 ** attempt
                print(f"  retry {attempt}/{MAX_RETRIES} after error ({e}); waiting {wait}s")
                time.sleep(wait)
        print(f"  FAILED after {MAX_RETRIES} attempts: {url} ({last_err})")
        return None

    def discover_links(self) -> list[Page]:
        html = self.fetch(TOC_URL)
        if not html:
            raise SystemExit("Could not fetch the table of contents. Aborting.")
        soup = BeautifulSoup(html, "html.parser")
        all_anchors = soup.find_all("a", href=True)
        print(f"  (diagnostic) total <a href> tags on the page: {len(all_anchors)}")

        pages: dict[str, Page] = {}
        opsmanual_link_count = 0
        code_matched_count = 0

        for a in all_anchors:
            href = urljoin(TOC_URL, a["href"])
            m = PAGE_ID_RE.search(urlparse(href).path)
            if not m:
                continue
            opsmanual_link_count += 1
            page_id = m.group(1)

            # The code (e.g. "SR3.10") and the title text are sometimes in
            # separate inline elements with no literal space between them,
            # which breaks a naive get_text(). Try the anchor's title
            # attribute first (this site puts "CODE Title text" there),
            # then fall back to text with an inserted separator so words
            # from different child tags don't get glued together.
            candidates = [
                a.get("title", "").strip(),
                a.get_text(" ", strip=True),
            ]
            section_code, title_text = None, None
            for candidate in candidates:
                candidate = re.sub(r"\s+", " ", candidate).strip()
                code_match = SECTION_CODE_RE.match(candidate)
                if code_match:
                    section_code = code_match.group(1)
                    title_text = candidate
                    code_matched_count += 1
                    break
            if title_text is None:
                title_text = re.sub(r"\s+", " ", a.get_text(" ", strip=True)).strip()

            if self.prefixes:
                if not section_code or not any(section_code.startswith(p) for p in self.prefixes):
                    continue

            pages[page_id] = Page(url=href, page_id=page_id, section_code=section_code, title=title_text)

        print(f"  (diagnostic) links pointing to /opsmanual/<id>.htm: {opsmanual_link_count}")
        print(f"  (diagnostic) of those, links where a section code could be parsed: {code_matched_count}")
        if opsmanual_link_count == 0:
            print(
                "  (diagnostic) WARNING: zero /opsmanual/ links found at all. This means the page "
                "requests.get() fetched doesn't look like the manual page -- possibly a redirect, "
                "cookie/consent wall, or bot-protection response. Try: "
                "print(len(html)) and print(html[:500]) right after the fetch() call to inspect it."
            )
        return list(pages.values())

    def extract_content(
        self,
        html: str,
    ) -> tuple[str, str | None, int, int, int, int, int, int, int]:
        """Extract policy text while preserving INZ tables and nested clauses.

        Returns text/date plus observed and converted table/list counts so the
        collector can fail closed rather than save structurally incomplete text.
        """
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        # Try a few likely content containers before falling back to <body>.
        content = (
            soup.find("div", id=re.compile("content", re.I))
            or soup.find("main")
            or soup.find("article")
            or soup.body
        )
        target = content if content is not None else soup

        related_blocks_removed, utility_rows_removed = _remove_navigation_chrome(target)

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

    def save_page(self, page: Page, body: str, effective_date: str | None):
        code = page.section_code or page.page_id
        safe_name = code.replace(" ", "_")
        dest = self.out_dir / f"{safe_name}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)

        body_hash = content_hash(body)
        front_matter = {
            "section_code": code,
            "title": page.title or code,
            "source_url": page.url,
            "effective_date": effective_date,
            "fetched_date": time.strftime("%Y-%m-%d"),
        }
        fm_lines = "\n".join(f'{k}: {json.dumps(v)}' for k, v in front_matter.items())
        dest.write_text(f"---\n{fm_lines}\n---\n\n{body}\n", encoding="utf-8")

        base = self.manifest_path.parent
        try:
            rel = dest.resolve().relative_to(base.resolve())
            file_path = str(rel).replace("/", "\\")
        except ValueError:
            file_path = str(dest)

        self.manifest.append(
            {
                "section_code": code,
                "title": page.title,
                "file": file_path,
                "source_url": page.url,
                "effective_date": effective_date,
                "content_hash": body_hash,
            }
        )

    def write_manifest(self):
        existing = {}
        if self.manifest_path.exists():
            try:
                existing_data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
                entries = (
                    existing_data.get("pages", existing_data.get("sections", []))
                    if isinstance(existing_data, dict)
                    else existing_data
                )
                existing = {p["section_code"]: p for p in entries}
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                raise RuntimeError(
                    f"Refusing to overwrite unreadable crawl inventory: {self.manifest_path}"
                ) from exc
        for entry in self.manifest:
            existing[entry["section_code"]] = entry

        payload = {
            "manual_toc_url": TOC_URL,
            "collected_date": time.strftime("%Y-%m-%d"),
            "purpose": "crawl_inventory_not_runtime_manifest",
            "pages": list(existing.values()),
        }
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote crawl inventory with {len(existing)} entries -> {self.manifest_path}")

    def run(self, force: bool):
        print(f"Reading table of contents: {TOC_URL}")
        pages = self.discover_links()
        print(f"Found {len(pages)} matching section links.")

        for i, page in enumerate(pages, 1):
            code = page.section_code or page.page_id
            safe_name = code.replace(" ", "_")
            dest = self.out_dir / f"{safe_name}.md"
            if dest.exists() and not force:
                print(f"[{i}/{len(pages)}] SKIP (already have) {code}")
                continue

            print(f"[{i}/{len(pages)}] Fetching {code}: {page.url}")
            html = self.fetch(page.url)
            if html is None:
                continue
            (
                body,
                effective_date,
                html_tables,
                policy_tables,
                converted_tables,
                policy_lists,
                converted_lists,
                related_blocks_removed,
                utility_rows_removed,
            ) = self.extract_content(html)

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
                time.sleep(self.delay)
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
                time.sleep(self.delay)
                continue

            if related_blocks_removed or utility_rows_removed:
                print(
                    "  Navigation removed: "
                    f"relatedtopics={related_blocks_removed}, "
                    f"utility_rows={utility_rows_removed}"
                )

            self.save_page(page, body, effective_date)
            time.sleep(self.delay)

        self.write_manifest()


def main():
    parser = argparse.ArgumentParser(description="Collect INZ Operational Manual sections.")
    parser.add_argument(
        "--prefixes",
        nargs="*",
        default=["SR", "WD"],
        help="Only collect section codes starting with these prefixes (default: SR WD). "
        "Ignored if --all is passed.",
    )
    parser.add_argument("--all", action="store_true", help="Collect the entire manual, ignoring --prefixes.")
    parser.add_argument("--out", default="../residence", help="Output directory for markdown files.")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY_SECONDS, help="Seconds between requests.")
    parser.add_argument("--force", action="store_true", help="Re-download pages even if already saved.")
    parser.add_argument(
        "--manifest",
        default=None,
        help="Crawl inventory path. Defaults to <out parent>/crawl_manifest.json.",
    )
    args = parser.parse_args()

    prefixes = None if args.all else args.prefixes
    out_dir = Path(args.out)
    manifest_path = Path(args.manifest) if args.manifest else out_dir.parent / "crawl_manifest.json"
    if manifest_path.name == "manifest.json":
        raise SystemExit(
            "Refusing to let the bulk collector write canonical manifest.json. "
            "Use crawl_manifest.json and curate/promote entries deliberately."
        )

    collector = Collector(
        out_dir=out_dir,
        manifest_path=manifest_path,
        prefixes=prefixes,
        delay=args.delay,
    )
    collector.run(force=args.force)


if __name__ == "__main__":
    main()