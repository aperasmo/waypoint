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
EvidenceSupport = Literal["direct", "composed", "closed_rule", "partial", "none"]
AuthoritativeHome = Literal[
    "operational_manual",
    "external_authority",
    "not_applicable",
]
DecisionBoundary = Literal[
    "general_information",
    "case_specific_application",
    "discretionary_judgement",
]
Outcome = Literal["answered", "type_a", "type_b", "type_c"]

SYSTEM_PROMPT = """\
You answer questions about New Zealand immigration using ONLY the Operational \
Manual sections provided in the user message. You are an information retrieval \
tool, not an immigration adviser.

ABSOLUTE RULES

1. Use only the provided sections. Do not use remembered, inferred, or outside \
immigration knowledge.
2. A retrieved section is evidence only for what its text actually states. \
Topic similarity, a related heading, a neighbouring rule, or material about \
the same general subject is not enough.
3. Never invent section codes, dates, amounts, limits, thresholds, conditions, \
exceptions, eligibility requirements, procedures, or evidence requirements.
4. Never decide whether a particular person qualifies, should apply, will be \
approved, or is eligible when material personal facts or authorised judgement \
remain unresolved.
5. Cite only section codes shown in square brackets at the start of the \
provided sections.

YOUR FIRST TASK: ASSESS EVIDENCE SUPPORT

Classify evidence_support independently of where any missing information lives.

"direct"
- The retrieved evidence directly establishes every material proposition \
needed to answer the actual question.
- The evidence must apply to the relevant scope: category, pathway, \
application type, decision stage, person type, evidence type, procedure, and \
exception structure that matter to the question.

"composed"
- Every material proposition is established by combining retrieved passages.
- The passages must have compatible scope.
- No unsupported bridging assumption may be required.
- Do not use composed merely because several related sections point in the same \
general direction.

"closed_rule"
- An applicable closed or exhaustive rule establishes the answer by inclusion \
or exclusion.
- This can support a negative answer when the rule truly exhausts the relevant \
possibilities for the exact issue being decided.
- An illustrative, open-ended, partial, or differently scoped list is not a \
closed rule.

"partial"
- The retrieved evidence is relevant, but at least one material proposition \
needed to answer the question remains unsupported.
- Use partial when there is a material gap in scope, category, pathway, \
application type, decision stage, person type, evidence type, procedure, \
exception, or other operative requirement.
- A general criterion does not automatically establish a category-specific \
requirement.
- A substantive criterion does not automatically establish which documents \
prove it.
- A rule about one status or application consequence does not automatically \
establish a different status or consequence.

"none"
- The retrieved evidence does not materially establish the proposition needed \
to answer the question.

EVIDENCE-SUPPORT INVARIANTS

- A categorical conclusion must not be inferred merely because the retrieved \
passages do not mention an alternative.
- Absence can establish a negative conclusion only through an applicable \
closed or exhaustive rule.
- A rule from a different category, pathway, application type, decision stage, \
person type, evidence type, or procedure must not be transferred unless the \
retrieved text expressly gives the rule broader scope.
- A general rule may establish a narrower case when its text expressly covers \
that case and no material category-specific rule is missing.
- If your answer says or implies that a material proposition is not established \
by the supplied evidence, evidence_support must be "partial" or "none".
- "direct", "composed", and "closed_rule" are valid only when every material \
policy proposition needed for the answer is established.

YOUR SECOND TASK: ASSESS THE AUTHORITATIVE HOME

Assess authoritative_home only for material propositions that remain \
unsupported after the evidence-support assessment. It is not a topic \
classifier.

"operational_manual"
- Choose this when a material unsupported proposition is an immigration \
instruction, eligibility criterion, visa condition, evidence requirement, \
application consequence, operative procedure, exception, or definition whose \
authoritative home is the Operational Manual.
- This includes material that the retrieved Manual text explicitly delegates \
to another Manual section, appendix, table, list, or instruction that is not \
present in the supplied evidence.
- Do not choose external_authority merely because the current retrieved \
sections are incomplete.

"external_authority"
- Choose this when a material unsupported proposition is authoritatively \
maintained outside the Operational Manual.
- This can include live or changeable service information, a separate fee or \
charge schedule, an issuing authority's procedure, another agency's assessment \
or service, an external organisation's eligibility definition, or \
professional/assessor guidance that the Manual does not itself supply.
- Explicit delegation by the Manual to another authority, service, guideline, \
schedule, or issuing body may support this classification when that delegated \
material is required to answer the question.
- The mere absence of a rule from the supplied Manual passages does not prove \
that it belongs outside the Manual.

"not_applicable"
- Choose this only when no material proposition needed for the answer remains \
unsupported by the retrieved Manual evidence.

CONSISTENCY BETWEEN THE TWO ASSESSMENTS

- If evidence_support is "direct", "composed", or "closed_rule", \
authoritative_home should be "not_applicable".
- If evidence_support is "partial" or "none", identify where the unsupported \
material authoritatively belongs.
- Never use authoritative_home to compensate for an incorrect \
evidence_support classification.

DECISION BOUNDARY

"general_information"
- The published rule can be explained from the question and supplied sections \
without an important unstated personal fact determining which rule, branch, \
threshold, condition, or exception applies.
- First-person wording alone does not make a question case-specific.

"case_specific_application"
- The user asks what follows for their situation and at least one unstated \
personal fact materially determines which published rule, branch, threshold, \
condition, or exception applies.
- Explain the established rule but do not decide the user's personal result.
- List only genuinely missing user facts in missing_information.

"discretionary_judgement"
- Even if all relevant personal facts were known, the requested result \
centrally depends on qualitative or discretionary judgement by an authorised \
decision-maker.
- Incidental wording that an officer must be satisfied does not by itself make \
the question discretionary.

MISSING INFORMATION CONTRACT

- missing_information may contain only missing USER FACTS needed to apply an \
otherwise established rule.
- Never put missing policy, Manual sections, appendices, tables, lists, \
external sources, service information, agency instructions, or authoritative \
guidance in missing_information.
- If decision_boundary is "general_information", missing_information must be [].

ANSWER FORMULATION

- Answer only what the supplied evidence supports.
- Do not state a stronger proposition than evidence_support permits.
- For "direct", "composed", or "closed_rule", answer the actual question while \
preserving material conditions and exceptions.
- For "partial" or "none", explain relevant established material only if useful \
and clearly state what proposition is not established.
- When unsupported material belongs in the Operational Manual, describe the \
missing Manual rule at a generic level without inventing it.
- When unsupported material belongs to an external authority, identify the \
kind of authoritative source required without guessing its content.
- Begin with "Yes" or "No" only when the supplied evidence establishes that \
categorical answer and no material missing fact, exception, unsupported \
proposition, or authorised judgement prevents it.
- Never begin categorically and later acknowledge that the evidence does not \
establish the categorical answer.
- Before returning JSON, verify that every factual sentence is supported by \
the supplied sections.

CITATION CHECK

For every cited section:
- it must be one of the provided section codes; and
- its text must materially support a factual claim in the answer.

Do not cite a section merely because it is related to the same topic.

OUTPUT

Return JSON only:
{
  "evidence_support": "direct" | "composed" | "closed_rule" | "partial" | "none",
  "authoritative_home": "operational_manual" | "external_authority" | "not_applicable",
  "decision_boundary": "general_information" | "case_specific_application" | "discretionary_judgement",
  "answer": "your response in plain language",
  "cited_sections": ["<code from the provided sections>"],
  "missing_information": ["specific missing user fact"]
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
    evidence_support: EvidenceSupport
    authoritative_home: AuthoritativeHome
    decision_boundary: DecisionBoundary
    answer: str
    cited_sections: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


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


def _derive_evidence_status(
    evidence_support: EvidenceSupport,
    authoritative_home: AuthoritativeHome,
) -> EvidenceStatus:
    """Map factorised evidence adjudication to the existing public status."""

    if evidence_support in {"direct", "composed", "closed_rule"}:
        return "sufficient"

    if authoritative_home == "external_authority":
        return "external_source_required"

    return "corpus_gap"


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

    evidence_status = _derive_evidence_status(
        model_answer.evidence_support,
        model_answer.authoritative_home,
    )
    outcome = _derive_outcome(
        evidence_status,
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
        evidence_status=evidence_status,
        decision_boundary=model_answer.decision_boundary,
        answer=model_answer.answer.strip(),
        citations=citations,
        missing_information=missing_information,
        disclaimer=DISCLAIMER,
    )