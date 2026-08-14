"""Answer questions from retrieved manual text only.

The whole safety property of this endpoint is that the model reports what
the retrieved sections say and nothing else. It knows things about New
Zealand immigration from training, some of it outdated and some wrong, and
all of it would sound exactly as confident as the correct parts. The prompt,
the low reasoning effort, and the required citations all push against that.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_session
from app.ingestion.embedder import OpenAIEmbedder
from app.retrieval.acronyms import expand_acronyms
from app.retrieval.retriever import Result, retrieve

router = APIRouter(prefix="/ask", tags=["ask"])

DISCLAIMER = (
    "This is general information from the publicly available INZ Operational "
    "Manual. It is not immigration advice. For advice on your situation, "
    "consult a licensed immigration adviser (iaa.govt.nz) or contact "
    "Immigration New Zealand."
)

SYSTEM_PROMPT = """\
You answer questions about New Zealand immigration using ONLY the manual \
sections provided in the user message. You are an information retrieval tool, \
not an immigration adviser.

ABSOLUTE RULES

1. Use only the provided sections. You may know things about New Zealand \
immigration from other sources. Do not use them. If the provided sections do \
not contain the answer, say so.
2. Never invent section codes, dates, dollar amounts, hour limits, point \
values, or score thresholds. Every specific figure must appear verbatim in \
the provided text.
3. Never say "you qualify", "you should", "you can apply", "I recommend", or \
anything assessing the person's own situation. Report what the manual states \
about the requirements. Giving advice tailored to an individual's case \
requires a licence under the Immigration Advisers Licensing Act 2007.
4. Cite the section code for every claim you make.
5. Be brief. Two or three short paragraphs at most. Do not restate the whole \
section.

CHOOSING AN OUTCOME

"answered" - the provided sections contain the answer, and the question asks \
what the rules are rather than whether a particular person meets them.

"type_a" - the provided sections do not cover this topic at all. The manual \
may well address it, but it was not retrieved. Do not attempt a partial \
answer from adjacent content.

"type_b" - the provided sections state a rule but point to data held \
somewhere else: an ANZSCO occupation code, whether a specific employer is \
currently accredited, a current wage rate. Watch for phrases like "see \
ANZSCO", "must be accredited", or references to external lists. Name the \
specific official tool and the steps to use it.

"type_c" - answering would require judging this person's specific situation, \
or facts about them that were not given. This covers two cases that look \
different but need the same response: questions calling for an immigration \
officer's discretion ("do my duties substantially align"), and questions \
whose answer depends on details the person has not stated ("can I work full \
time" depends on their qualification and visa conditions). In both, state \
what the criteria are and what would determine the outcome. Do not state \
whether their case meets it. List what is missing in missing_information.

When a question could be read as either information-seeking or \
case-specific, prefer type_c. Under-answering is recoverable. A confident \
wrong answer about someone's visa is not.

OUTPUT

Return JSON only:
{
  "outcome": "answered" | "type_a" | "type_b" | "type_c",
  "answer": "your response in plain language",
  "cited_sections": ["SR3.10"],
  "missing_information": ["what would be needed"]
}

cited_sections must only contain codes from the provided sections. Leave \
missing_information empty unless the outcome is type_c.
"""


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class Citation(BaseModel):
    section_code: str
    title: str
    source_url: str
    effective_date: str | None


class AskResponse(BaseModel):
    question: str
    interpreted_as: str | None
    outcome: str
    answer: str
    citations: list[Citation]
    missing_information: list[str]
    disclaimer: str


def _format_context(results: list[Result]) -> str:
    parts = []
    for r in results:
        header = f"[{r.section_code}] {r.title}"
        if r.effective_date:
            header += f" (effective {r.effective_date})"
        if r.chunk_total > 1:
            header += f" (part {r.chunk_index + 1} of {r.chunk_total})"
        parts.append(f"{header}\n{r.text}")
    return "\n\n---\n\n".join(parts)


@router.post("", response_model=AskResponse)
async def ask(
    request: AskRequest, session: AsyncSession = Depends(get_session)
) -> AskResponse:
    settings = get_settings()
    embedder = OpenAIEmbedder()

    results = await retrieve(session, request.question, embedder, limit=5)

    if not results:
        return AskResponse(
            question=request.question,
            interpreted_as=None,
            outcome="type_a",
            answer=(
                "I could not find anything about this in the sections I have "
                "indexed. You can search the manual directly at "
                "immigration.govt.nz/opsmanual."
            ),
            citations=[],
            missing_information=[],
            disclaimer=DISCLAIMER,
        )

    expansion = expand_acronyms(request.question)

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    completion = await client.chat.completions.create(
        model=settings.answer_model,
        max_completion_tokens=settings.answer_max_tokens,
        reasoning_effort=settings.answer_reasoning_effort,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Question: {request.question}\n\n"
                    f"Manual sections:\n\n{_format_context(results)}"
                ),
            },
        ],
    )

    raw = completion.choices[0].message.content or "{}"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502, detail="The answer service returned malformed output."
        ) from exc

    outcome = parsed.get("outcome", "type_a")
    if outcome not in {"answered", "type_a", "type_b", "type_c"}:
        outcome = "type_a"

    # Only return citations for sections actually retrieved. If the model
    # names a code that was not in its context, it invented one, and the
    # citation is dropped rather than shown to the user as if it were real.
    retrieved_by_code = {r.section_code: r for r in results}
    cited = [c for c in parsed.get("cited_sections", []) if c in retrieved_by_code]

    citations = [
        Citation(
            section_code=code,
            title=retrieved_by_code[code].title,
            source_url=retrieved_by_code[code].source_url,
            effective_date=retrieved_by_code[code].effective_date,
        )
        for code in dict.fromkeys(cited)
    ]

    return AskResponse(
        question=request.question,
        interpreted_as=expansion.expanded if expansion.changed else None,
        outcome=outcome,
        answer=parsed.get("answer", ""),
        citations=citations,
        missing_information=parsed.get("missing_information", []),
        disclaimer=DISCLAIMER,
    )