"""Browse the corpus by category or section code.

No LLM, no vector search. This is the navigation path, and it also proves
the database path end to end before ask.py adds anything harder.
"""

from __future__ import annotations

import json
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.db.session import get_session
from app.models.schema import Chunk, Section

router = APIRouter(prefix="/browse", tags=["browse"])


class Branch(BaseModel):
    label: str
    section_count: int


class Group(BaseModel):
    id: str
    label: str
    description: str
    branches: list[Branch]


class SectionSummary(BaseModel):
    section_code: str
    title: str
    effective_date: str | None


class SectionDetail(BaseModel):
    section_code: str
    title: str
    source_url: str
    effective_date: str | None
    text: str


@lru_cache
def _taxonomy() -> dict:
    path = get_settings().categories_path
    if not path.exists():
        return {"groups": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _matches(section_code: str, prefixes: list[str]) -> bool:
    """A prefix entry is either a code group (U13) or a full code (A4.10).

    Matching on the raw string alone would make 'U1' match 'U13.15', so a
    prefix must be followed by a dot or nothing at all.
    """
    for prefix in prefixes:
        if section_code == prefix or section_code.startswith(f"{prefix}."):
            return True
    return False


@router.get("/categories", response_model=list[Group])
async def list_categories(session: AsyncSession = Depends(get_session)) -> list[Group]:
    """The browse tree, with live section counts.

    Counts come from the database rather than the taxonomy file, so a branch
    that has lost its content shows zero instead of lying.
    """
    result = await session.execute(select(Section.section_code))
    codes = list(result.scalars())

    groups: list[Group] = []
    for group in _taxonomy()["groups"]:
        branches = [
            Branch(
                label=branch["label"],
                section_count=sum(1 for c in codes if _matches(c, branch["prefixes"])),
            )
            for branch in group["branches"]
        ]
        groups.append(
            Group(
                id=group["id"],
                label=group["label"],
                description=group["description"],
                branches=branches,
            )
        )
    return groups


@router.get("/sections", response_model=list[SectionSummary])
async def list_sections(
    group: str | None = None,
    branch: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[SectionSummary]:
    """Sections in a group, or in one branch of a group.

    Omitting both returns everything, which the frontend may want for a
    search-as-you-type list.
    """
    stmt = select(Section).order_by(Section.section_code)
    result = await session.execute(stmt)
    sections = list(result.scalars())

    if group:
        matched = next((g for g in _taxonomy()["groups"] if g["id"] == group), None)
        if matched is None:
            raise HTTPException(status_code=404, detail=f"Unknown group: {group}")

        branches = matched["branches"]
        if branch:
            branches = [b for b in branches if b["label"] == branch]
            if not branches:
                raise HTTPException(status_code=404, detail=f"Unknown branch: {branch}")

        prefixes = [p for b in branches for p in b["prefixes"]]
        sections = [s for s in sections if _matches(s.section_code, prefixes)]

    return [
        SectionSummary(
            section_code=s.section_code,
            title=s.title,
            effective_date=s.effective_date.isoformat() if s.effective_date else None,
        )
        for s in sections
    ]


@router.get("/sections/{section_code}", response_model=SectionDetail)
async def get_section(
    section_code: str, session: AsyncSession = Depends(get_session)
) -> SectionDetail:
    """One section with its chunks reassembled in order.

    Chunks are a retrieval concern, not something a reader should see. The
    200-character overlap between adjacent chunks is stripped on rejoin, so
    the text reads as it did in the source.
    """
    stmt = (
        select(Section)
        .options(selectinload(Section.chunks))
        .where(Section.section_code == section_code)
    )
    result = await session.execute(stmt)
    section = result.scalar_one_or_none()

    if section is None:
        raise HTTPException(status_code=404, detail=f"Unknown section: {section_code}")

    ordered = sorted(section.chunks, key=lambda c: c.chunk_index)
    parts: list[str] = []
    for i, chunk in enumerate(ordered):
        text = chunk.text
        if i > 0 and parts:
            # Drop the overlap tail that split_text prepended to this chunk.
            previous_tail = parts[-1][-200:]
            if text.startswith(previous_tail[:50]):
                text = text[len(previous_tail) :].lstrip()
        parts.append(text)

    return SectionDetail(
        section_code=section.section_code,
        title=section.title,
        source_url=section.source_url,
        effective_date=section.effective_date.isoformat() if section.effective_date else None,
        text="\n".join(parts),
    )