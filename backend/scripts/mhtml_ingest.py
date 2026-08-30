"""
mhtml_ingest.py

Local adapter for manually archived Immigration New Zealand Operational
Manual MHTML files.

Responsibilities:
- Parse manually saved MHTML without making network requests.
- Decode archived HTML explicitly as UTF-8.
- Locate the current policy content inside td#main.
- Validate that the policy heading matches the MHTML filename.
- Exclude related-topic navigation and historical policy versions.
- Return only the current policy HTML for the existing parser.

This module does not write files or modify the source archive.
"""

from __future__ import annotations

from email import policy
from email.parser import BytesParser
from pathlib import Path

from bs4 import BeautifulSoup, Tag


def _find_policy_heading(
    main: Tag,
    section_code: str,
) -> Tag | None:
    """
    Find the current policy heading matching the expected section code.

    Operational Manual detail pages commonly use p.heading4, while some
    top-level pages use h1-h4 elements.
    """

    candidates: list[Tag] = []

    primary = main.select_one("p.heading4")

    if primary is not None:
        candidates.append(primary)

    candidates.extend(
        main.find_all(["h1", "h2", "h3", "h4"])
    )

    for candidate in candidates:
        heading_text = candidate.get_text(
            " ",
            strip=True,
        )

        if (
            heading_text == section_code
            or heading_text.startswith(
                f"{section_code} "
            )
        ):
            return candidate

    return None


def _find_topic_boundary(
    main: Tag,
    heading: Tag,
) -> Tag | None:
    """
    Find the first related-topics boundary after the current policy topic.

    Most Operational Manual pages place a
    table.relatedtopics.belowtopictext element immediately after the current
    policy content. Some top-level pages do not contain this boundary and
    therefore legitimately fall back to the end of td#main.
    """

    for candidate in heading.find_all_next(
        "table",
        class_="relatedtopics",
    ):
        if main not in candidate.parents:
            break

        classes = candidate.get("class", [])

        if "belowtopictext" in classes:
            return candidate

    return None


def _clip_after_boundary(
    main: Tag,
    boundary: Tag,
    section_code: str,
) -> None:
    """
    Remove the related-topics boundary and everything after it.

    The boundary may be nested inside another element, so first resolve its
    top-level ancestor that is a direct child of td#main.
    """

    cutoff: Tag | None = boundary

    while cutoff is not None and cutoff.parent is not main:
        parent = cutoff.parent

        if not isinstance(parent, Tag):
            cutoff = None
            break

        cutoff = parent

    if cutoff is None:
        raise ValueError(
            f"Could not resolve topic boundary for {section_code}"
        )

    for sibling in list(
        cutoff.find_next_siblings()
    ):
        sibling.extract()

    cutoff.extract()


def extract_policy_html_from_mhtml(
    file_path: Path,
) -> tuple[str, str | None, str]:
    """
    Extract the current Operational Manual policy HTML from one MHTML file.

    Returns:
        tuple:
            policy_html:
                HTML containing only the current td#main policy content.

            content_location:
                Original Content-Location from the matching MHTML MIME part.

            heading_text:
                Validated current policy heading.

    Raises:
        FileNotFoundError:
            If the MHTML file does not exist.

        ValueError:
            If the archive cannot be decoded or no matching current policy
            content can be found.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"MHTML file does not exist: {file_path}"
        )

    if not file_path.is_file():
        raise ValueError(
            f"MHTML path is not a file: {file_path}"
        )

    section_code = file_path.stem.strip()

    if not section_code:
        raise ValueError(
            f"Could not derive section code from filename: {file_path}"
        )

    try:
        message = BytesParser(
            policy=policy.default
        ).parsebytes(
            file_path.read_bytes()
        )

    except Exception as exc:
        raise ValueError(
            f"Failed to parse MHTML file {file_path.name}: {exc}"
        ) from exc

    html_parts_found = 0

    for part in message.walk():
        if part.get_content_type() != "text/html":
            continue

        html_parts_found += 1

        payload = part.get_payload(
            decode=True
        )

        if payload is None:
            continue

        # The complete archived source set has been independently audited:
        # every HTML MIME payload is valid UTF-8 and none declares a charset.
        # Decode strictly so unexpected future encoding changes fail closed
        # rather than silently corrupting policy text.
        try:
            html = payload.decode(
                "utf-8",
                errors="strict",
            )

        except UnicodeDecodeError as exc:
            raise ValueError(
                "HTML MIME payload is not valid UTF-8 in "
                f"{file_path.name}: {exc}"
            ) from exc

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        main = soup.find(
            "td",
            id="main",
        )

        if main is None:
            continue

        heading = _find_policy_heading(
            main,
            section_code,
        )

        if heading is None:
            continue

        heading_text = heading.get_text(
            " ",
            strip=True,
        )

        # Defence-in-depth validation. _find_policy_heading() already applies
        # this rule, but extraction should fail closed if that behaviour ever
        # changes.
        if not (
            heading_text == section_code
            or heading_text.startswith(
                f"{section_code} "
            )
        ):
            raise ValueError(
                "Policy heading does not match filename section code: "
                f"{section_code!r} != {heading_text!r}"
            )

        boundary = _find_topic_boundary(
            main,
            heading,
        )

        if boundary is not None:
            _clip_after_boundary(
                main,
                boundary,
                section_code,
            )

        content_location = part.get(
            "Content-Location"
        )

        # Return a complete HTML fragment so the existing DOM-aware parser can
        # process td#main without depending on the surrounding browser shell.
        policy_html = (
            "<html><body>"
            f"{str(main)}"
            "</body></html>"
        )

        return (
            policy_html,
            content_location,
            heading_text,
        )

    if html_parts_found == 0:
        raise ValueError(
            f"No text/html MIME parts found in {file_path.name}"
        )

    raise ValueError(
        "No matching current policy content found in "
        f"{file_path.name} for section {section_code}"
    )