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

EVIDENCE_ADJUDICATOR_PROMPT = """\
You are the evidence-adjudication stage of a New Zealand Immigration \
Operational Manual retrieval system.

You receive one user question and up to five retrieved Operational Manual \
passages.

Your task is ONLY to classify the evidence. Do not write the final answer to \
the user.

ABSOLUTE RULES

1. Use only the supplied passages. Do not use remembered, inferred, or outside \
immigration knowledge.
2. Judge the actual proposition asked, not merely whether the retrieved \
passages discuss the same topic.
3. A related heading, neighbouring rule, similar visa category, analogous \
procedure, or general policy objective is not enough unless the supplied text \
actually establishes the material rule needed.
4. Do not invent rules, exceptions, definitions, evidence requirements, \
amounts, dates, thresholds, procedures, or section codes.
5. supporting_sections may contain only section codes supplied in the context.

EVIDENCE STATUS

"sufficient"
Choose this when the retrieved passages establish every material published \
policy proposition needed to answer the actual question within the applicable \
scope.

Sufficient evidence may be:
- one directly applicable passage;
- multiple passages whose rules can be composed without an unsupported \
bridging assumption; or
- a genuinely closed or exhaustive rule that establishes an inclusion or \
exclusion.

Do not require the passages to decide a person's final eligibility when the \
published rule is fully present but material personal facts remain unstated. \
That belongs in decision_boundary, not evidence_status.

A general rule can be sufficient for a narrower case when the text expressly \
covers that case and no material category-specific rule is missing.

"corpus_gap"
Choose this when a material policy proposition needed to answer the question \
is not established by the supplied passages and that missing authority belongs \
in the Operational Manual.

Examples of the KIND of missing Manual material include an instruction, \
definition, appendix, table, list, exception, visa condition, evidence \
requirement, application consequence, or operative procedure.

The missing Manual material does not have to be explicitly cross-referenced by \
a retrieved passage. However, do not assume a Manual gap merely because the \
retrieval is incomplete. Decide where the missing authority would properly \
belong.

"external_source_required"
Choose this when a material proposition needed to answer the question is \
authoritatively maintained outside the Operational Manual.

This can include:
- live or changeable service information;
- a separate fee or charge schedule;
- an issuing authority's procedure;
- another agency's assessment or service;
- an external organisation's entitlement or eligibility definition; or
- professional or assessor guidance that the Manual itself does not supply.

The absence of information from the retrieved Manual passages does NOT by \
itself make the answer external. There must be a reason, grounded in the \
nature of the requested information or an explicit delegation in the supplied \
Manual text, that its authoritative home is outside the Manual.

EVIDENCE CHECK

Before selecting evidence_status:

1. Identify the exact proposition or propositions the question requires.
2. Determine whether each material policy proposition is established by the \
supplied passages.
3. Do not transfer a rule across a different visa category, pathway, \
application type, decision stage, person type, evidence type, or procedure \
unless the supplied text expressly gives it that broader scope.
4. Do not infer a categorical negative merely from silence.
5. A negative conclusion from absence is valid only when an applicable \
retrieved rule is genuinely closed or exhaustive for the exact issue.
6. If a material proposition is unsupported, decide whether its authoritative \
home is the Operational Manual or an external authority.
7. Separate missing POLICY from missing USER FACTS.

DECISION BOUNDARY

"general_information"
The published rule can be explained without a material unstated personal fact \
determining which rule, branch, threshold, condition, or exception applies. \
First-person wording alone does not make a question case-specific.

"case_specific_application"
The user asks what follows for their situation and at least one unstated \
personal or situational fact materially determines which published rule, \
branch, threshold, condition, or exception applies.

"discretionary_judgement"
Even if all relevant personal facts were known, the requested result centrally \
depends on qualitative or discretionary judgement by an authorised \
decision-maker. Incidental wording that an officer must be satisfied does not \
by itself make a question discretionary.

OTHER OUTPUT FIELDS

supporting_sections:
- Include only supplied section codes that materially support the proposition \
or relevant rule.
- Do not include merely related sections.

missing_user_facts:
- Include only missing personal or situational facts that could materially \
change application of an otherwise established rule.
- Never include missing policy, Manual sections, appendices, tables, external \
sources, service information, or authoritative guidance.
- If decision_boundary is general_information, return [].

unsupported_proposition:
- Return null when evidence_status is sufficient.
- Otherwise state, in neutral generic language, the material proposition that \
the supplied evidence does not establish.
- Do not invent the missing rule or its answer.

CONSISTENCY CHECK

Before returning JSON:
- If evidence_status is sufficient, unsupported_proposition must be null.
- If evidence_status is corpus_gap or external_source_required, \
unsupported_proposition must identify the material unresolved proposition.
- Missing personal facts alone do not make evidence insufficient.
- Do not classify a question as corpus_gap merely because a more detailed \
answer could be given with more user facts.

OUTPUT

Return JSON only:
{
  "evidence_status": "sufficient" | "corpus_gap" | "external_source_required",
  "decision_boundary": "general_information" | "case_specific_application" | "discretionary_judgement",
  "supporting_sections": ["<code from supplied passages>"],
  "missing_user_facts": ["specific missing user fact"],
  "unsupported_proposition": "material unsupported proposition" | null
}
"""


ANSWER_GENERATOR_PROMPT = """\
You are the answer-generation stage of a New Zealand Immigration Operational \
Manual retrieval system.

You receive:
- the user's question;
- retrieved Operational Manual passages; and
- an evidence adjudication already completed by Stage 1.

Stage 1's evidence_status and decision_boundary are IMMUTABLE. Do not \
reclassify, reinterpret, replace, weaken, or override them.

Use only the supplied Manual passages. Do not use remembered, inferred, or \
outside immigration knowledge.

EVIDENCE-STATUS BEHAVIOUR

If evidence_status is "sufficient":
- Answer the actual question directly from the supplied evidence.
- Preserve material conditions, scope limits, and exceptions.
- Do not introduce a policy proposition that the supplied passages do not \
establish.
- If decision_boundary is case_specific_application, explain the governing \
rule without deciding the user's personal result when missing user facts are \
material.
- If decision_boundary is discretionary_judgement, explain the published test \
without making the authorised judgement.

If evidence_status is "corpus_gap":
- Do not complete the missing Manual rule by inference.
- Explain relevant established Manual evidence only when it helps orient the \
user.
- Clearly state that the supplied indexed Manual evidence does not establish \
the unsupported proposition identified by Stage 1.
- Describe the missing Manual material only at a generic level.

If evidence_status is "external_source_required":
- Do not guess the external value, status, entitlement, procedure, assessment, \
or guidance.
- Explain relevant Manual context only when useful.
- State that the requested proposition requires an authoritative source \
outside the Operational Manual.
- Identify the KIND of external source required using Stage 1's unsupported \
proposition and the supplied evidence, without inventing its content.

ANSWER RULES

1. Every factual immigration claim must be supported by the supplied Manual \
passages.
2. Do not invent section codes, dates, amounts, limits, points, thresholds, \
conditions, exceptions, procedures, or eligibility requirements.
3. Begin with "Yes" or "No" only when Stage 1 classified the evidence as \
sufficient and the supplied rule supports that categorical answer for the \
facts already stated.
4. Never make a personal eligibility or approval decision when Stage 1 marks \
the decision boundary as case_specific_application or \
discretionary_judgement.
5. cited_sections may contain only supplied section codes that materially \
support factual claims in the answer.
6. Do not cite a section merely because it is related to the same topic.
7. missing_information must reproduce Stage 1's missing_user_facts only. Do \
not add missing policy, Manual sections, appendices, tables, external sources, \
service information, or authoritative guidance.
8. If Stage 1 missing_user_facts is empty, missing_information must be [].

Before returning JSON, verify that the answer is consistent with the immutable \
Stage 1 evidence_status and decision_boundary.

OUTPUT

Return JSON only:
{
  "answer": "plain-language user-facing response",
  "cited_sections": ["<code from supplied passages>"],
  "missing_information": ["same missing user facts supplied by Stage 1"]
}
"""


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class Citation(BaseModel):
    section_code: str
    title: str
    source_url: str
    effective_date: str | None


class EvidenceAdjudication(BaseModel):
    evidence_status: EvidenceStatus
    decision_boundary: DecisionBoundary
    supporting_sections: list[str] = Field(default_factory=list)
    missing_user_facts: list[str] = Field(default_factory=list)
    unsupported_proposition: str | None = None


class GeneratedAnswer(BaseModel):
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


def _clean_string_items(items: list[str]) -> list[str]:
    """Remove blank and duplicate list items without adding information."""
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


def _validate_adjudication(
    adjudication: EvidenceAdjudication,
    retrieved_codes: set[str],
) -> EvidenceAdjudication:
    """Enforce generic Stage-1 contract invariants."""

    adjudication.supporting_sections = list(
        dict.fromkeys(
            code
            for code in adjudication.supporting_sections
            if code in retrieved_codes
        )
    )

    adjudication.missing_user_facts = _clean_string_items(
        adjudication.missing_user_facts
    )

    if adjudication.decision_boundary == "general_information":
        adjudication.missing_user_facts = []

    unsupported = (
        adjudication.unsupported_proposition.strip()
        if adjudication.unsupported_proposition
        else ""
    )

    if adjudication.evidence_status == "sufficient":
        adjudication.unsupported_proposition = None
    elif not unsupported:
        raise HTTPException(
            status_code=502,
            detail="The evidence adjudicator returned malformed output.",
        )
    else:
        adjudication.unsupported_proposition = unsupported

    return adjudication


def _same_missing_user_facts(
    stage_1: list[str],
    stage_2: list[str],
) -> bool:
    """Compare Stage-2 copied user facts without topic-specific logic."""

    left = [item.casefold() for item in _clean_string_items(stage_1)]
    right = [item.casefold() for item in _clean_string_items(stage_2)]
    return left == right


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

    context = _format_context(results)
    retrieved_codes = {r.section_code for r in results}
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    adjudication_completion = await client.chat.completions.create(
        model=settings.answer_model,
        max_completion_tokens=settings.answer_max_tokens,
        reasoning_effort=settings.answer_reasoning_effort,
        response_format={"type": "json_object"},
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": EVIDENCE_ADJUDICATOR_PROMPT,
            },
            {
                "role": "user",
                "content": (
                    f"Question: {request.question}\n\n"
                    f"Manual sections:\n\n{context}"
                ),
            },
        ],
    )

    adjudication_raw = (
        adjudication_completion.choices[0].message.content or "{}"
    )

    try:
        adjudication_parsed = json.loads(adjudication_raw)
        adjudication = EvidenceAdjudication.model_validate(
            adjudication_parsed
        )
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=502,
            detail="The evidence adjudicator returned malformed output.",
        ) from exc

    adjudication = _validate_adjudication(
        adjudication,
        retrieved_codes,
    )

    adjudication_for_answer = {
        "evidence_status": adjudication.evidence_status,
        "decision_boundary": adjudication.decision_boundary,
        "supporting_sections": adjudication.supporting_sections,
        "missing_user_facts": adjudication.missing_user_facts,
        "unsupported_proposition": adjudication.unsupported_proposition,
    }

    answer_completion = await client.chat.completions.create(
        model=settings.answer_model,
        max_completion_tokens=settings.answer_max_tokens,
        reasoning_effort=settings.answer_reasoning_effort,
        response_format={"type": "json_object"},
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": ANSWER_GENERATOR_PROMPT,
            },
            {
                "role": "user",
                "content": (
                    f"Question: {request.question}\n\n"
                    "Stage 1 adjudication (immutable):\n"
                    f"{json.dumps(adjudication_for_answer, ensure_ascii=False)}"
                    "\n\nManual sections:\n\n"
                    f"{context}"
                ),
            },
        ],
    )

    answer_raw = answer_completion.choices[0].message.content or "{}"

    try:
        answer_parsed = json.loads(answer_raw)
        generated = GeneratedAnswer.model_validate(answer_parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=502,
            detail="The answer generator returned malformed output.",
        ) from exc

    if not _same_missing_user_facts(
        adjudication.missing_user_facts,
        generated.missing_information,
    ):
        raise HTTPException(
            status_code=502,
            detail=(
                "The answer generator changed the evidence "
                "adjudicator's missing user facts."
            ),
        )

    outcome = _derive_outcome(
        adjudication.evidence_status,
        adjudication.decision_boundary,
    )
    missing_information = _clean_missing_information(
        adjudication.missing_user_facts,
        adjudication.decision_boundary,
    )

    # Only return citations for sections actually retrieved. If the model
    # names a code that was not in its context, it invented one, and the
    # citation is dropped rather than shown to the user as if it were real.
    retrieved_by_code = {r.section_code: r for r in results}
    cited = [
        code
        for code in generated.cited_sections
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
        evidence_status=adjudication.evidence_status,
        decision_boundary=adjudication.decision_boundary,
        answer=generated.answer.strip(),
        citations=citations,
        missing_information=missing_information,
        disclaimer=DISCLAIMER,
    )