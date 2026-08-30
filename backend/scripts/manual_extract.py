"""
manual_extract.py

Pure HTML parsing helpers for the INZ Operational Manual.

These functions were copied unchanged from the original collector so that the
rebuilt corpus is parsed exactly as the current one was. This module performs
no network access. It only turns HTML text that already exists on disk into
policy text.

Source material: Immigration New Zealand Operational Manual, (c) Crown
copyright, licensed for reuse under the Creative Commons Attribution 3.0
New Zealand licence.
"""

from __future__ import annotations

import hashlib
import re

from bs4 import BeautifulSoup, NavigableString, Tag

PAGE_ID_RE = re.compile(r"/opsmanual/(\d+)\.htm$")
SECTION_CODE_RE = re.compile(r"^([A-Z]{1,3}\d+(?:\.\d+)*)\s+(.*)$")
# INZ dates may use one- or two-digit days/months, e.g. 8/12/2025.
EFFECTIVE_DATE_RE = re.compile(r"Effective\s+(\d{1,2}/\d{1,2}/\d{4})")


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
    """Return the structural kind of an INZ policy list."""
    classes = set(lst.get("class") or [])

    if "listletter" in classes:
        return "letter"

    if "listroman" in classes:
        return "roman"

    if classes.intersection(
        {
            "listbullet",
            "listbullet2",
            "listbullet3",
            "tablelistbullet",
        }
    ):
        return "bullet"

    return None


def _direct_list_items(lst: Tag) -> list[Tag]:
    """Return only list items belonging directly to this list."""
    return [
        li
        for li in lst.find_all(
            "li",
            recursive=False,
        )
        if li.find_parent(["ol", "ul"]) is lst
    ]


def _normalise_list_text(value: str) -> str:
    """Normalise whitespace without changing policy wording."""
    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def _policy_list_marker(
    kind: str,
    index: int,
) -> str:
    """Return the explicit marker for one policy-list item."""
    if kind == "letter":
        return f"({_alpha_marker(index)})"

    if kind == "roman":
        return f"({_roman_marker(index)})"

    if kind == "bullet":
        return "-"

    raise ValueError(
        f"Unsupported policy list kind: {kind}"
    )


def _policy_list_to_markdown(
    lst: Tag,
    depth: int = 0,
) -> tuple[str, int]:
    """
    Convert one INZ policy-list tree while preserving DOM reading order.

    Direct text, continuation paragraphs, notes, and nested lists are emitted
    in the same order in which they occur inside each <li>.
    """
    kind = _policy_list_kind(lst)

    if kind is None:
        return "", 0

    lines: list[str] = []
    converted_lists = 1

    item_indent = "    " * depth
    continuation_indent = "    " * (depth + 1)

    for index, li in enumerate(
        _direct_list_items(lst),
        start=1,
    ):
        marker = _policy_list_marker(
            kind,
            index,
        )

        text_buffer: list[str] = []
        marker_used = False

        def flush_text_buffer() -> None:
            """Write accumulated direct text at its current DOM position."""
            nonlocal marker_used

            value = _normalise_list_text(
                "".join(text_buffer)
            )

            text_buffer.clear()

            if not value:
                return

            if not marker_used:
                lines.append(
                    f"{item_indent}{marker} {value}"
                )
                marker_used = True
            else:
                lines.append(
                    f"{continuation_indent}{value}"
                )

        for child in li.children:
            if isinstance(child, NavigableString):
                text_buffer.append(str(child))
                continue

            if not isinstance(child, Tag):
                continue

            if child.name in {"ol", "ul"}:
                nested_kind = _policy_list_kind(child)

                if nested_kind is None:
                    raise ValueError(
                        "Encountered an unsupported nested list class: "
                        f"{child.get('class')}"
                    )

                flush_text_buffer()

                # A structurally valid list item should normally have text
                # before its nested list. Preserve an explicit parent marker
                # if a future page begins directly with a nested structure.
                if not marker_used:
                    lines.append(
                        f"{item_indent}{marker}"
                    )
                    marker_used = True

                nested_markdown, nested_count = (
                    _policy_list_to_markdown(
                        child,
                        depth + 1,
                    )
                )

                if nested_markdown:
                    lines.extend(
                        nested_markdown.splitlines()
                    )

                converted_lists += nested_count
                continue

            if child.name == "p":
                flush_text_buffer()

                paragraph_text = _normalise_list_text(
                    child.get_text(
                        " ",
                        strip=True,
                    )
                )

                if not paragraph_text:
                    continue

                if not marker_used:
                    lines.append(
                        f"{item_indent}{marker} "
                        f"{paragraph_text}"
                    )
                    marker_used = True
                else:
                    lines.append(
                        f"{continuation_indent}"
                        f"{paragraph_text}"
                    )

                continue

            # Inline elements such as <a>, <strong>, and <span> belong to the
            # current text segment and must remain in their original position.
            text_buffer.append(
                child.get_text(
                    " ",
                    strip=False,
                )
            )

        flush_text_buffer()

    return (
        "\n".join(lines),
        converted_lists,
    )


def _convert_policy_lists(
    target: Tag,
) -> tuple[int, int]:
    """
    Convert all recognised INZ policy lists.

    The observed count is derived from the DOM rather than from a maintained
    section list. Unsupported future list structures therefore cannot silently
    masquerade as successfully converted policy lists.
    """
    policy_lists = [
        lst
        for lst in target.find_all(
            ["ol", "ul"]
        )
        if _policy_list_kind(lst) is not None
    ]

    policy_list_count = len(policy_lists)

    top_level_lists: list[Tag] = []

    for lst in policy_lists:
        parent_list = lst.find_parent(
            ["ol", "ul"]
        )

        if (
            parent_list is None
            or _policy_list_kind(parent_list) is None
        ):
            top_level_lists.append(lst)

    converted_list_count = 0

    for lst in top_level_lists:
        markdown, converted = (
            _policy_list_to_markdown(lst)
        )

        if not markdown:
            continue

        lst.replace_with(
            NavigableString(
                f"\n\n{markdown}\n\n"
            )
        )

        converted_list_count += converted

    return (
        policy_list_count,
        converted_list_count,
    )


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
    """Return a stable hash of the extracted policy body for change detection."""
    normalized = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def extract_content(html: str) -> dict[str, object]:
    """Extract policy text while preserving INZ tables and nested clauses.

    Returns the text and effective date plus observed and converted
    table/list counts, so the caller can fail closed rather than write
    structurally incomplete text.

    This is the original Collector.extract_content, unbound from the
    collector and returning a dict instead of a nine-item tuple.
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

    related_blocks_removed, utility_rows_removed = _remove_navigation_chrome(target)

    html_table_count = len(target.find_all("table"))
    policy_tables = list(target.select("table.tableintopic"))
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

    return {
        "text": text,
        "effective_date": date_match.group(1) if date_match else None,
        "html_tables": html_table_count,
        "policy_tables": len(policy_tables),
        "converted_tables": converted_table_count,
        "policy_lists": policy_list_count,
        "converted_lists": converted_list_count,
        "related_blocks_removed": related_blocks_removed,
        "utility_rows_removed": utility_rows_removed,
    }


def section_code_and_title(html: str) -> tuple[str | None, str | None]:
    """Recover the section code and title from a saved page's own heading.

    The collector used to get these from the table of contents. Reading them
    back out of the page removes the need to crawl the TOC at all.
    """
    soup = BeautifulSoup(html, "html.parser")

    candidates = []
    for tag in soup.find_all(["h1", "h2", "title"]):
        value = re.sub(r"\s+", " ", tag.get_text(" ", strip=True)).strip()
        if value:
            candidates.append(value)

    for value in candidates:
        value = re.sub(r"\s*::.*$", "", value).strip()
        match = SECTION_CODE_RE.match(value)
        if match:
            # Keep the full "SR3.1 Objective" form: the original corpus titles
            # carried the code, and the citation cards render this string.
            return match.group(1), value

    return None, candidates[0] if candidates else None
