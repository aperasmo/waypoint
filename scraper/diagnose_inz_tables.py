"""Read-only diagnostic for nested tables in INZ Operational Manual pages.

This script fetches selected pages and reports table structure only.
It does not modify Waypoint data, manifest.json, or changelog.json.
"""
from __future__ import annotations

import argparse
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "WaypointManualCollector/0.1 "
    "(personal research project; contact: allanperasmo@gmail.com)"
)
MAX_RETRIES = 3

DEFAULT_SECTIONS = {
    "SR2.10": "https://www.immigration.govt.nz/opsmanual/77808.htm",
    "SR3.15": "https://www.immigration.govt.nz/opsmanual/77813.htm",
    "SR3.30": "https://www.immigration.govt.nz/opsmanual/80475.htm",
}


def fetch(session: requests.Session, url: str) -> str:
    last_error: Exception | None = None
    for _ in range(MAX_RETRIES):
        try:
            response = session.get(url, timeout=20)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            last_error = exc
    raise RuntimeError(f"Could not fetch {url}: {last_error}")


def content_target(html: str):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    content = (
        soup.find("div", id=re.compile("content", re.I))
        or soup.find("main")
        or soup.find("article")
        or soup.body
    )
    return content if content is not None else soup


def compact(text: str, limit: int = 140) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def table_depth(table) -> int:
    depth = 0
    parent = table.parent
    while parent is not None:
        if getattr(parent, "name", None) == "table":
            depth += 1
        parent = parent.parent
    return depth


def inspect_page(code: str, url: str, session: requests.Session) -> None:
    html = fetch(session, url)
    target = content_target(html)
    tables = target.find_all("table")

    print(f"\n{code}  {url}")
    print("=" * (len(code) + len(url) + 2))
    print(f"HTML bytes: {len(html.encode('utf-8'))}")
    print(f"Tables found in selected content target: {len(tables)}")

    index_by_id = {id(table): i for i, table in enumerate(tables, start=1)}

    for i, table in enumerate(tables, start=1):
        parent_table = table.find_parent("table")
        parent_index = index_by_id.get(id(parent_table)) if parent_table is not None else None

        direct_rows = table.find_all("tr", recursive=False)
        all_rows = table.find_all("tr")
        direct_cells = []
        for row in direct_rows:
            direct_cells.extend(row.find_all(["th", "td"], recursive=False))
        all_cells = table.find_all(["th", "td"])
        nested_tables = table.find_all("table")

        attrs = []
        if table.get("id"):
            attrs.append(f"id={table.get('id')!r}")
        if table.get("class"):
            attrs.append(f"class={table.get('class')!r}")
        if table.get("role"):
            attrs.append(f"role={table.get('role')!r}")
        attr_text = ", ".join(attrs) if attrs else "none"

        print(f"\nTable {i}")
        print(f"  depth={table_depth(table)} parent={parent_index or '-'} nested_tables={len(nested_tables)}")
        print(f"  attrs={attr_text}")
        print(
            "  rows: "
            f"direct={len(direct_rows)} recursive={len(all_rows)} | "
            f"cells: direct={len(direct_cells)} recursive={len(all_cells)}"
        )
        print(f"  text_len={len(table.get_text(' ', strip=True))}")
        print(f"  sample={compact(table.get_text(' ', strip=True))!r}")

        # First three direct rows give enough evidence to distinguish layout
        # wrappers from actual data tables without dumping the full policy.
        for row_index, row in enumerate(direct_rows[:3], start=1):
            cells = row.find_all(["th", "td"], recursive=False)
            values = [compact(cell.get_text(" ", strip=True), 90) for cell in cells]
            print(f"  direct_row_{row_index}={values!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect nested INZ table structure without writing files.")
    parser.add_argument(
        "sections",
        nargs="*",
        default=list(DEFAULT_SECTIONS),
        help="Section codes to inspect (default: SR2.10 SR3.15 SR3.30).",
    )
    args = parser.parse_args()

    unknown = [code for code in args.sections if code not in DEFAULT_SECTIONS]
    if unknown:
        raise SystemExit("Unsupported diagnostic section(s): " + ", ".join(unknown))

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    print("INZ table DOM diagnostic - READ ONLY")
    print("No Waypoint files, manifest entries, or database rows will be changed.")
    for code in args.sections:
        inspect_page(code, DEFAULT_SECTIONS[code], session)


if __name__ == "__main__":
    main()