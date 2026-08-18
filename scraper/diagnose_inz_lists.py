"""
diagnose_inz_lists.py

READ ONLY diagnostic for INZ Operational Manual list structure.
It fetches selected pages and reports <ol>/<ul> attributes, nesting depth,
and direct list-item text. It does not modify Waypoint files, manifest data,
or the database.

Run from waypoint/backend:

    uv run --with requests --with beautifulsoup4 python ..\\scraper\\diagnose_inz_lists.py
"""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup, Tag

USER_AGENT = (
    "WaypointManualCollector/0.1 "
    "(personal research project; contact: allanperasmo@gmail.com)"
)

SECTIONS = {
    "U8.25": "https://www.immigration.govt.nz/opsmanual/42649.htm",
    "R2.40": "https://www.immigration.govt.nz/opsmanual/44893.htm",
}


def selected_target(soup: BeautifulSoup) -> Tag:
    content = (
        soup.find("div", id=re.compile("content", re.I))
        or soup.find("main")
        or soup.find("article")
        or soup.body
    )
    return content if isinstance(content, Tag) else soup


def direct_li_text(li: Tag) -> str:
    """Return the text belonging directly to this <li>, excluding nested lists."""
    clone = BeautifulSoup(str(li), "html.parser")
    node = clone.find("li")
    if node is None:
        return ""

    for nested in node.find_all(["ol", "ul"]):
        nested.decompose()

    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()


def list_depth(lst: Tag) -> int:
    depth = 0
    parent = lst.find_parent(["ol", "ul"])
    while parent is not None:
        depth += 1
        parent = parent.find_parent(["ol", "ul"])
    return depth


def direct_items(lst: Tag) -> list[Tag]:
    return [
        li
        for li in lst.find_all("li", recursive=False)
        if li.find_parent(["ol", "ul"]) is lst
    ]


def inspect_page(code: str, url: str, session: requests.Session) -> None:
    print()
    print(f"{code}  {url}")
    print("=" * (len(code) + len(url) + 2))

    response = session.get(url, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    target = selected_target(soup)
    lists = target.find_all(["ol", "ul"])

    print(f"HTML bytes: {len(response.content)}")
    print(f"Lists found in selected content target: {len(lists)}")

    for index, lst in enumerate(lists, start=1):
        parent = lst.find_parent(["ol", "ul"])
        parent_index = "-"
        if parent is not None:
            try:
                parent_index = str(lists.index(parent) + 1)
            except ValueError:
                parent_index = "?"

        attrs = {
            key: value
            for key, value in lst.attrs.items()
            if key in {"class", "id", "type", "start", "style"}
        }

        items = direct_items(lst)

        print()
        print(f"List {index}")
        print(
            f"  tag={lst.name} depth={list_depth(lst)} "
            f"parent={parent_index} direct_items={len(items)}"
        )
        print(f"  attrs={attrs or '{}'}")

        for item_number, li in enumerate(items[:12], start=1):
            li_attrs = {
                key: value
                for key, value in li.attrs.items()
                if key in {"class", "id", "type", "value", "style"}
            }
            text = direct_li_text(li)
            if len(text) > 180:
                text = text[:177] + "..."
            nested_count = len(li.find_all(["ol", "ul"], recursive=False))
            print(
                f"  item_{item_number}: "
                f"attrs={li_attrs or '{}'} "
                f"nested_lists={nested_count} "
                f"text={text!r}"
            )


def main() -> None:
    print("INZ list DOM diagnostic - READ ONLY")
    print("No Waypoint files, manifest entries, or database rows will be changed.")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    for code, url in SECTIONS.items():
        inspect_page(code, url, session)


if __name__ == "__main__":
    main()