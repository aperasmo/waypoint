"""Answer questions from retrieved manual text only.

The whole safety property of this endpoint is that the model reports what
the retrieved sections say and nothing else. It knows things about New
Zealand immigration from training, some of it outdated and some wrong, and
all of it would sound exactly as confident as the correct parts. The prompt,
the low reasoning effort, and the required citations all push against that.
"""

from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError
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

EvidenceStatus = Literal["sufficient", "corpus_gap", "external_source_required"]
DecisionBoundary = Literal[
    "general_information",
    "case_specific_application",
    "discretionary_judgement",
]
Outcome = Literal["answered", "type_a", "type_b", "type_c"]

SYSTEM_PROMPT = """\
You answer questions about New Zealand immigration using ONLY the manual \
sections provided in the user message. You are an information retrieval tool, \
not an immigration adviser.

ABSOLUTE RULES

1. Use only the provided sections. You may know things about New Zealand \
immigration from other sources. Do not use them. If the provided sections do \
not contain enough evidence to explain the relevant rule, say so.
2. Never invent section codes, dates, dollar amounts, hour limits, point \
values, or score thresholds. Every specific figure must appear verbatim in \
the provided text.
3. Never decide whether a particular person qualifies, should apply, will be \
approved, or is eligible. Report what the manual states about the requirements \
and, when needed, what facts or judgement would determine the result.
4. Cite the section code for every factual claim. Use ONLY the codes shown in \
square brackets at the start of each provided section, for example [WD3.5]. \
The section text may contain finer sub-clause headings such as WD3.5.5. Do not \
cite those finer headings: they will not resolve to a source the reader can open.

CLASSIFY TWO THINGS INDEPENDENTLY

A. evidence_status

"sufficient" - the provided sections contain enough published policy to \
explain the relevant rule or criteria needed for the user's actual question. \
This remains sufficient when the rule has several branches, amounts, thresholds, \
or conditions and the answer varies with personal facts the user has not supplied. \
A conditional rule is not a corpus gap merely because there is no single flat \
yes/no answer or single universal number.

"corpus_gap" - essential Operational Manual material needed to resolve the \
policy question itself is absent from the provided sections. Use this when the \
retrieved text explicitly depends on another missing policy source and that \
missing source is necessary to answer what the user asked. Example: if a rule \
says the permitted occupation must be determined from Appendix 13, and Appendix \
13 is not provided, a question asking whether a specific occupation is permitted \
has a corpus gap. Do not fill the gap from memory or general knowledge.

"external_source_required" - the manual explains the rule, but the question \
requires authoritative current data outside this corpus, such as live employer \
accreditation or another external official data source.

EVIDENCE CHECK

Before choosing evidence_status, ask:
- Do the provided sections contain the rule, thresholds, or decision criteria \
needed to explain the user's question? If yes, choose sufficient even when the \
answer depends on unstated personal facts.
- Is a referenced but missing manual appendix, table, list, or section essential \
to determine what the rule says for the thing the user asked about? If yes, \
choose corpus_gap.
- Do not call something a corpus gap merely because the manual gives multiple \
conditional amounts or because the user's circumstances select between them.
- Consistency rule: if your answer says that a specific requested result cannot \
be determined because an essential referenced appendix, table, list, or section \
is not included in the provided material, evidence_status MUST be corpus_gap. \
Do not label that situation sufficient merely because the parent rule is present. \
For example, if WD3.5 says a level 7-or-below qualification is restricted to the \
occupation in Appendix 13 and Appendix 13 is absent, a question asking whether \
"barista" is permitted has evidence_status=corpus_gap.

B. decision_boundary

"general_information" - the published rule can be explained directly from the \
question and provided sections without needing important unstated personal facts \
to answer what the user asked. First-person wording alone does NOT make a \
question case-specific. If the user states the decisive fact and the rule is \
categorical, use general_information and explain the rule without declaring \
personal eligibility.

Examples that are general_information when the supporting rule is retrieved:
- A compulsory internship that is practical experience required by the course: \
explain the practical-experience rule.
- Asking whether a second Post-Study Work Visa is possible after already being \
granted one: explain the categorical rule about previous grants. Wording such as \
"another Post-Study Work Visa" ordinarily presupposes a previous one; do not ask \
again whether one was previously granted.
- Asking whether 40 hours can be worked during university holidays: if the manual \
states a full-time scheduled-vacation rule but no specific 40-hour cap, explain \
that published conditional rule as general_information. Do not make it \
case_specific_application merely to decide whether the user's own programme meets \
every condition.
- An 8-month temporary stay asking about medical/chest-X-ray thresholds: explain \
the duration rule and any conditional TB-screening rule without deciding whether \
the person has a TB risk factor. Do not make this case_specific_application merely \
because the TB-risk branch exists.
- Asking for student maintenance-fund amounts when the manual provides the \
amounts for the relevant programme-duration/study categories: explain all \
applicable published amounts rather than treating the absence of one universal \
amount as missing policy.

"case_specific_application" - the user is asking for a personal yes/no result \
and that result depends on one or more important personal facts that were not \
provided. Explain the published criteria but do not decide the result. List ONLY \
the genuinely missing facts in missing_information. Do not list facts the \
question already states.

Use case_specific_application when BOTH are true:
1. the user asks what follows for their own situation; and
2. at least one unstated personal fact materially determines which rule, branch, \
threshold, condition, or exception applies.

A strong consistency check: if your answer says or implies "I cannot tell whether \
you can / need to / qualify because I need to know X", then the boundary should \
normally be case_specific_application, not general_information.

Examples:
- "Can I change my course without changing my visa?" when programme/provider/\
level or existing visa-condition facts are needed.
- "Can I work full time on my student visa?" with no study type, visa-condition, \
or vacation-status facts MUST be case_specific_application because those unstated \
facts determine the user's personal entitlement.
- "I have 6 points; can I apply for residence?" MUST be case_specific_application \
when other independent Skilled Migrant Category requirements depend on facts not \
stated; six points alone does not resolve the personal application question.
- "Is NZ$15,000 enough for my student visa?" when programme length, study type, \
or prepaid living-expense facts are needed to select the applicable amount.
- "Do I need a medical/police certificate?" when visa category, intended stay, \
age, or other trigger facts are not stated.

"discretionary_judgement" - even after the relevant personal facts are known, \
the requested result centrally depends on a qualitative or discretionary \
judgement by an authorised decision-maker. Explain the test, but do not make \
that judgement for the user. Do not use discretionary_judgement merely because \
the section contains incidental wording such as "officer must be satisfied". \
The authorised judgement must be central to the user's requested result.

Example: recently transferred maintenance funds where the actual question is \
whether those funds are acceptable, and the manual makes genuineness and genuine \
availability matters for an immigration officer to assess.
If the user's requested result is the acceptability of those particular funds, \
and the governing rule centrally requires the officer to be satisfied about \
genuine source or genuine availability, use discretionary_judgement rather than \
case_specific_application. Do not treat "whether the source is genuine" or \
"whether the funds are genuinely available" as ordinary missing personal facts \
that the user can resolve by assertion; those are the authorised judgement itself.

IMPORTANT CLASSIFICATION RULES

- Evidence sufficiency and decision boundary are separate. Do not use corpus_gap \
merely because personal facts are missing.
- Do not use case_specific_application just because the question says "I" or \
"my".
- Treat facts clearly presupposed by ordinary wording as already supplied. Words \
such as "another", "again", "already", and "still" can carry material facts. Do \
not add those facts to missing_information or use their supposed absence to turn \
a categorical published rule into case_specific_application.
- Do not use general_information when your own answer says a personal result \
cannot be determined without an unstated material fact.
- Do not put an empty string, a label, or generic hedging in missing_information.
- If decision_boundary is general_information, missing_information MUST be [].
- If decision_boundary is case_specific_application, missing_information should \
contain only facts that would materially change which published rule applies.
- If evidence_status is corpus_gap, identify the missing policy material in the \
answer; do not pretend the user's missing personal facts caused the corpus gap.

ANSWER FORMULATION

- Answer the user's question directly, but do not overstate what the retrieved \
manual supports.
- Begin with "Yes" or "No" only when the provided rule supports that categorical \
answer for the facts already stated and no material missing fact, exception, \
waiver, variation/approval requirement, or authorised judgement prevents it.
- Otherwise begin with the governing rule or a qualified formulation such as \
"Normally, ...", "The manual says ...", or "That depends on ...".
- Before returning JSON, check that the first sentence does not contradict the \
conditions, exceptions, or missing-information explanation that follows it.
- Never say "Yes" and then explain that the normal rule is "No unless an \
exception applies", or vice versa.

OUTPUT

Return JSON only:
{
  "evidence_status": "sufficient" | "corpus_gap" | "external_source_required",
  "decision_boundary": "general_information" | "case_specific_application" | "discretionary_judgement",
  "answer": "your response in plain language",
  "cited_sections": ["SR3.10"],
  "missing_information": ["specific missing fact"]
}

cited_sections must only contain codes from the provided sections.
"""


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class Citation(BaseModel):
    section_code: str
    title: str
    source_url: str
    effective_date: str | None


class ModelAnswer(BaseModel):
    evidence_status: EvidenceStatus
    decision_boundary: DecisionBoundary
    answer: str
    cited_sections: list[str]
    missing_information: list[str]


class AskResponse(BaseModel):
    question: str
    interpreted_as: str | None
    outcome: Outcome
    evidence_status: EvidenceStatus
    decision_boundary: DecisionBoundary
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


def _derive_outcome(
    evidence_status: EvidenceStatus,
    decision_boundary: DecisionBoundary,
) -> Outcome:
    """Derive the legacy public outcome from two independent classifications."""
    if evidence_status == "corpus_gap":
        return "type_a"
    if evidence_status == "external_source_required":
        return "type_b"
    if decision_boundary != "general_information":
        return "type_c"
    return "answered"


def _clean_missing_information(
    items: list[str],
    decision_boundary: DecisionBoundary,
) -> list[str]:
    """Remove blank/duplicate items and suppress them for general answers."""
    if decision_boundary == "general_information":
        return []

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = item.strip().strip("-• ")
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(value)
    return cleaned


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
            evidence_status="corpus_gap",
            decision_boundary="general_information",
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
        temperature=0,
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
        model_answer = ModelAnswer.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=502,
            detail="The answer service returned malformed output.",
        ) from exc

    outcome = _derive_outcome(
        model_answer.evidence_status,
        model_answer.decision_boundary,
    )
    missing_information = _clean_missing_information(
        model_answer.missing_information,
        model_answer.decision_boundary,
    )

    # Only return citations for sections actually retrieved. If the model
    # names a code that was not in its context, it invented one, and the
    # citation is dropped rather than shown to the user as if it were real.
    retrieved_by_code = {r.section_code: r for r in results}
    cited = [
        code
        for code in model_answer.cited_sections
        if code in retrieved_by_code
    ]

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
        evidence_status=model_answer.evidence_status,
        decision_boundary=model_answer.decision_boundary,
        answer=model_answer.answer.strip(),
        citations=citations,
        missing_information=missing_information,
        disclaimer=DISCLAIMER,
    )