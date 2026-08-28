"""Anonymous coverage feedback, stored separately from the RAG corpus.

No LLM call, no embeddings, no retrieval, no corpus write. This endpoint only
records what a reader saw and thought was wrong, for later human review of
which areas of the corpus need expanding.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StringConstraints, field_validator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.ask import EvidenceStatus
from app.db.session import get_session
from app.models.schema import Feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])

FeedbackType = Literal[
    "not_answered",
    "outside_coverage",
    "incorrect_answer",
    "irrelevant_sources",
    "external_information_needed",
    "other",
]

# Matches sections.section_code (String(32)), so a reported code can never
# outgrow the column an eventual review query would compare it against.
SectionCode = Annotated[str, StringConstraints(strip_whitespace=True, max_length=32)]

# Comment is free text from an anonymous, untrusted client; bounded well
# above any realistic feedback note but far below anything abusive.
COMMENT_MAX_LENGTH = 2000

# Answer is a snapshot of a rendered /ask response. answer_max_tokens=800
# comfortably fits well under this in characters; the margin is for
# whitespace and multi-byte characters, not for arbitrary client payloads.
ANSWER_MAX_LENGTH = 6000

MAX_CITED_SECTIONS = 10


class FeedbackRequest(BaseModel):
    question: str = Field(max_length=500)
    feedback_type: FeedbackType
    comment: str | None = Field(default=None, max_length=COMMENT_MAX_LENGTH)
    evidence_status: EvidenceStatus | None = None
    answer: str | None = Field(default=None, max_length=ANSWER_MAX_LENGTH)
    cited_sections: list[SectionCode] = Field(
        default_factory=list, max_length=MAX_CITED_SECTIONS
    )

    # status is deliberately not a field here: the public API can only ever
    # create feedback in the "new" state.

    @field_validator("question", mode="before")
    @classmethod
    def _strip_question(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("question")
    @classmethod
    def _question_not_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("question must not be blank")
        return value

    @field_validator("comment", "answer", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class FeedbackResponse(BaseModel):
    status: Literal["received"] = "received"
    id: int


@router.post("", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    request: FeedbackRequest, session: AsyncSession = Depends(get_session)
) -> FeedbackResponse:
    feedback = Feedback(
        question=request.question,
        feedback_type=request.feedback_type,
        comment=request.comment,
        evidence_status=request.evidence_status,
        answer=request.answer,
        cited_sections=list(request.cited_sections),
        # Explicit, not just relying on the column default: FeedbackRequest
        # has no status field, so this is the only place status is set.
        status="new",
    )

    session.add(feedback)
    try:
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save feedback. Please try again.",
        ) from exc

    await session.refresh(feedback)
    return FeedbackResponse(id=feedback.id)
