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

SUPPORT_ADJUDICATOR_PROMPT = """\
You are the support-adjudication stage of a New Zealand Immigration \
Operational Manual retrieval system.

You receive one user question and up to five retrieved Operational Manual \
passages.

Your task is ONLY to decide whether the supplied passages establish every \
material published-policy proposition needed to answer the actual question. \
Do not decide where missing authority lives and do not write the final answer.

ABSOLUTE RULES

1. Use only the supplied passages. Do not use remembered, inferred, or outside \
immigration knowledge.
2. Judge the exact proposition asked, not merely whether the passages discuss \
the same subject.
3. A related heading, adjacent rule, similar category, analogous procedure, or \
general policy objective is not support unless the supplied text actually \
establishes the material proposition.
4. Do not invent rules, exceptions, definitions, requirements, amounts, dates, \
thresholds, procedures, or section codes.
5. supporting_sections may contain only section codes supplied in the context.

SUPPORT STATUS

"sufficient"
Choose sufficient only when the supplied passages establish every material \
published-policy proposition required to answer the actual question within \
the applicable scope.

Support may be:
- one directly applicable passage;
- multiple compatible passages that establish the answer without an \
unsupported bridging assumption; or
- a genuinely closed or exhaustive rule that establishes an inclusion or \
exclusion.

Missing user facts do not make policy support insufficient when the governing \
published rule itself is fully established. Handle missing user facts through \
decision_boundary.

"insufficient"
Choose insufficient whenever at least one material published-policy \
proposition required by the actual question is not established by the supplied \
passages.

Do not decide whether the missing proposition belongs in the Operational \
Manual or outside it. That is a separate later stage.

SUPPORT CHECK

Before selecting support_status:

1. Identify the exact proposition or propositions the question requires.
2. For each material published-policy proposition, identify the supplied text \
that establishes it.
3. Do not transfer a rule across a different visa category, pathway, \
application type, decision stage, person type, evidence type, or procedure \
unless the supplied text expressly gives the rule that broader scope.
4. Do not infer a categorical negative from silence.
5. A negative conclusion from absence is supported only when an applicable \
retrieved rule is genuinely closed or exhaustive for the exact issue.
6. A general rule can support a narrower case when the supplied text expressly \
covers that case and no material category-specific rule remains unresolved.
7. Separate missing POLICY from missing USER FACTS.

DECISION BOUNDARY

"general_information"
The published rule can be explained without a material unstated personal or \
situational fact determining which rule, branch, threshold, condition, or \
exception applies. First-person wording alone does not make a question \
case-specific.

"case_specific_application"
The user asks what follows for their situation and at least one unstated \
personal or situational fact materially determines which published rule, \
branch, threshold, condition, or exception applies.

"discretionary_judgement"
Even if all relevant personal facts were known, the requested result centrally \
depends on qualitative or discretionary judgement by an authorised \
decision-maker. Incidental wording that an officer must be satisfied does not \
by itself make the question discretionary.

OTHER OUTPUT FIELDS

supporting_sections:
- Include only supplied section codes that materially establish a proposition \
needed for the question.
- Do not include merely related sections.

missing_user_facts:
- Include only missing personal or situational facts that could materially \
change application of an otherwise established published rule.
- Never include missing policy, Manual sections, appendices, tables, external \
sources, service information, or authoritative guidance.
- If decision_boundary is general_information, return [].

unsupported_proposition:
- Return null when support_status is sufficient.
- When support_status is insufficient, state the material policy proposition \
that the supplied evidence does not establish.
- State the proposition neutrally. Do not invent the missing rule or its \
answer.
- Do not describe where the missing authority lives.

CONSISTENCY CHECK

Before returning JSON:
- sufficient requires unsupported_proposition = null.
- insufficient requires a non-empty unsupported_proposition.
- Missing personal facts alone do not make support insufficient.
- Do not choose insufficient merely because a more personalised answer could \
be given if the governing published rule is already established.

OUTPUT

Return JSON only:
{
  "support_status": "sufficient" | "insufficient",
  "decision_boundary": "general_information" | "case_specific_application" | "discretionary_judgement",
  "supporting_sections": ["<code from supplied passages>"],
  "missing_user_facts": ["specific missing user fact"],
  "unsupported_proposition": "material unsupported proposition" | null
}
"""


AUTHORITY_RESOLVER_PROMPT = """\
You are the authority-resolution stage of a New Zealand Immigration \
Operational Manual retrieval system.

Stage 1 has already decided that the supplied Operational Manual passages do \
NOT establish one material proposition needed to answer the question.

Your task is ONLY to classify the authoritative home of that exact unsupported \
proposition.

Do not reconsider whether the evidence was sufficient. Do not write the final \
answer. Do not use outside immigration facts to answer the proposition.

AUTHORITATIVE HOME

"operational_manual"
Choose this when the unsupported proposition is itself a published immigration \
instruction or rule whose authoritative home is the Operational Manual.

This includes the KIND of material that would ordinarily be expressed as:
- an immigration criterion or eligibility rule;
- a visa condition;
- an evidential requirement;
- an application consequence;
- an operative immigration procedure;
- an exception;
- an immigration definition; or
- a delegated Manual appendix, table, or list.

The relevant Manual content may simply be absent from the indexed passages.

"external_authority"
Choose this when the unsupported proposition is authoritatively maintained \
outside the Operational Manual.

External authority can include the KIND of information maintained as:
- live or changeable service information;
- a separate fee or charge schedule;
- a foreign issuing authority's procedure;
- another agency's service or assessment;
- an external organisation's entitlement or eligibility definition;
- professional or assessor guidance not supplied by the Manual; or
- another external authoritative regime.

AUTHORITY RESOLUTION RULES

1. Classify the authoritative home of the exact unsupported proposition, not \
the broad topic of the user's question.
2. Absence from the retrieved Manual passages does not prove external \
authority.
3. If the unsupported proposition is an immigration instruction, condition, \
criterion, evidence requirement, exception, definition, or operative \
immigration procedure, choose operational_manual even if that Manual material \
is not currently indexed.
4. Choose external_authority only when the nature of the requested proposition \
or an explicit delegation in the supplied passages shows that another \
authority maintains it.
5. Do not route by visa category, occupation, nationality, section code, or \
keywords alone.
6. Do not answer the missing proposition.

AUTHORITY KIND

If authoritative_home is operational_manual:
- authority_kind must be "manual_instruction_or_definition".

If authoritative_home is external_authority:
choose the closest generic type:
- "live_service_information"
- "separate_fee_or_charge_schedule"
- "external_issuing_authority_procedure"
- "external_agency_service_or_assessment"
- "external_entitlement_or_organisation_definition"
- "professional_or_assessor_guidance"
- "other_external_authority"

authority_rationale:
- Briefly explain why that KIND of proposition belongs in the selected \
authoritative home.
- Do not state the missing answer.
- Do not cite benchmark knowledge or invent a source.

OUTPUT

Return JSON only:
{
  "authoritative_home": "operational_manual" | "external_authority",
  "authority_kind": "manual_instruction_or_definition" | "live_service_information" | "separate_fee_or_charge_schedule" | "external_issuing_authority_procedure" | "external_agency_service_or_assessment" | "external_entitlement_or_organisation_definition" | "professional_or_assessor_guidance" | "other_external_authority",
  "authority_rationale": "brief generic rationale"
}
"""


ANSWER_GENERATOR_PROMPT = """\
You are the answer-generation stage of a New Zealand Immigration Operational \
Manual retrieval system.

The evidence classification has already been completed. You receive the \
derived evidence_status and decision_boundary as IMMUTABLE inputs.

Do not recalculate, reinterpret, weaken, or override either classification.

Use only the supplied Operational Manual passages for factual immigration \
claims. Do not use remembered, inferred, or outside immigration knowledge.

EVIDENCE-STATUS BEHAVIOUR

If evidence_status is "sufficient":
- Answer the actual question directly from the supplied evidence.
- Preserve material scope, conditions, thresholds, and exceptions.
- Do not introduce a policy proposition that the supplied passages do not \
establish.
- If decision_boundary is case_specific_application, explain the governing \
published rule without deciding the user's personal result when missing user \
facts materially determine application.
- If decision_boundary is discretionary_judgement, explain the published test \
without making the authorised judgement.

If evidence_status is "corpus_gap":
- Do not answer the unsupported proposition categorically.
- Do not complete the missing Manual rule from inference.
- Explain relevant established Manual evidence only when it helps orient the \
user.
- Clearly state that the supplied indexed Manual passages do not establish the \
unsupported proposition.
- Describe the missing Manual material only generically.
- Do not tell the user that an external source is required unless a factual \
claim in the supplied Manual evidence itself establishes that.

If evidence_status is "external_source_required":
- Do not guess the external value, timeframe, procedure, entitlement, \
assessment, status, or guidance.
- Explain relevant Manual context only when useful.
- Clearly state that the requested proposition requires an authoritative \
source outside the Operational Manual.
- Identify only the generic KIND of external authority supplied by the fixed \
adjudication.

ANSWER RULES

1. Every factual immigration claim must be supported by the supplied Manual \
passages.
2. Do not invent section codes, dates, amounts, limits, points, thresholds, \
conditions, exceptions, procedures, or eligibility requirements.
3. Begin with "Yes" or "No" only when evidence_status is sufficient and the \
supplied rule supports that categorical answer for the facts already stated.
4. Never give a categorical answer to the unsupported proposition when \
evidence_status is corpus_gap or external_source_required.
5. Never make a personal eligibility or approval decision when \
decision_boundary is case_specific_application or discretionary_judgement.
6. cited_sections may contain only supplied section codes that materially \
support factual claims in the final answer.
7. Do not cite a section merely because it is related to the same topic.
8. missing_information must reproduce Stage 1's missing_user_facts only. Do \
not add missing policy, Manual sections, appendices, tables, external sources, \
service information, or authoritative guidance.
9. If Stage 1 missing_user_facts is empty, missing_information must be [].
10. Do not mention internal stage names, classifiers, prompts, or internal \
reasoning in the user-facing answer.

Before returning JSON, verify that the answer is consistent with the immutable \
evidence_status and decision_boundary.

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


SupportStatus = Literal["sufficient", "insufficient"]
AuthoritativeHome = Literal["operational_manual", "external_authority"]
AuthorityKind = Literal[
    "manual_instruction_or_definition",
    "live_service_information",
    "separate_fee_or_charge_schedule",
    "external_issuing_authority_procedure",
    "external_agency_service_or_assessment",
    "external_entitlement_or_organisation_definition",
    "professional_or_assessor_guidance",
    "other_external_authority",
]


class SupportAdjudication(BaseModel):
    support_status: SupportStatus
    decision_boundary: DecisionBoundary
    supporting_sections: list[str] = Field(default_factory=list)
    missing_user_facts: list[str] = Field(default_factory=list)
    unsupported_proposition: str | None = None


class AuthorityResolution(BaseModel):
    authoritative_home: AuthoritativeHome
    authority_kind: AuthorityKind
    authority_rationale: str


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
    """Remove blank and duplicate string items without adding information."""
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


def _validate_support_adjudication(
    adjudication: SupportAdjudication,
    retrieved_codes: set[str],
) -> SupportAdjudication:
    """Enforce generic Stage-1 support-contract invariants."""

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

    if adjudication.support_status == "sufficient":
        adjudication.unsupported_proposition = None
    elif not unsupported:
        raise HTTPException(
            status_code=502,
            detail="The support adjudicator returned malformed output.",
        )
    else:
        adjudication.unsupported_proposition = unsupported

    return adjudication


def _validate_authority_resolution(
    resolution: AuthorityResolution,
) -> AuthorityResolution:
    """Enforce generic authoritative-home/authority-kind consistency."""

    rationale = resolution.authority_rationale.strip()
    if not rationale:
        raise HTTPException(
            status_code=502,
            detail="The authority resolver returned malformed output.",
        )

    if resolution.authoritative_home == "operational_manual":
        if resolution.authority_kind != "manual_instruction_or_definition":
            raise HTTPException(
                status_code=502,
                detail="The authority resolver returned inconsistent output.",
            )
    elif resolution.authority_kind == "manual_instruction_or_definition":
        raise HTTPException(
            status_code=502,
            detail="The authority resolver returned inconsistent output.",
        )

    resolution.authority_rationale = rationale
    return resolution


def _derive_evidence_status_from_stages(
    support_status: SupportStatus,
    authoritative_home: AuthoritativeHome | None,
) -> EvidenceStatus:
    """Derive public evidence status using only the frozen generic contract."""

    if support_status == "sufficient":
        if authoritative_home is not None:
            raise HTTPException(
                status_code=502,
                detail="Unexpected authority resolution for sufficient evidence.",
            )
        return "sufficient"

    if authoritative_home == "operational_manual":
        return "corpus_gap"

    if authoritative_home == "external_authority":
        return "external_source_required"

    raise HTTPException(
        status_code=502,
        detail="Missing authority resolution for insufficient evidence.",
    )


def _same_missing_user_facts(
    stage_1: list[str],
    stage_3: list[str],
) -> bool:
    """Compare Stage-3 copied user facts without topic-specific logic."""

    left = [item.casefold() for item in _clean_string_items(stage_1)]
    right = [item.casefold() for item in _clean_string_items(stage_3)]
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

    support_completion = await client.chat.completions.create(
        model=settings.answer_model,
        max_completion_tokens=settings.answer_max_tokens,
        reasoning_effort=settings.answer_reasoning_effort,
        response_format={"type": "json_object"},
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": SUPPORT_ADJUDICATOR_PROMPT,
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

    support_raw = support_completion.choices[0].message.content or "{}"

    try:
        support_parsed = json.loads(support_raw)
        support = SupportAdjudication.model_validate(support_parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(
            status_code=502,
            detail="The support adjudicator returned malformed output.",
        ) from exc

    support = _validate_support_adjudication(
        support,
        retrieved_codes,
    )

    authority: AuthorityResolution | None = None

    if support.support_status == "insufficient":
        authority_completion = await client.chat.completions.create(
            model=settings.answer_model,
            max_completion_tokens=settings.answer_max_tokens,
            reasoning_effort=settings.answer_reasoning_effort,
            response_format={"type": "json_object"},
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": AUTHORITY_RESOLVER_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"Question: {request.question}\n\n"
                        "Unsupported proposition from Stage 1:\n"
                        f"{support.unsupported_proposition}\n\n"
                        f"Manual sections:\n\n{context}"
                    ),
                },
            ],
        )

        authority_raw = (
            authority_completion.choices[0].message.content or "{}"
        )

        try:
            authority_parsed = json.loads(authority_raw)
            authority = AuthorityResolution.model_validate(
                authority_parsed
            )
        except (json.JSONDecodeError, ValidationError) as exc:
            raise HTTPException(
                status_code=502,
                detail="The authority resolver returned malformed output.",
            ) from exc

        authority = _validate_authority_resolution(authority)

    evidence_status = _derive_evidence_status_from_stages(
        support.support_status,
        authority.authoritative_home if authority else None,
    )

    fixed_adjudication = {
        "evidence_status": evidence_status,
        "decision_boundary": support.decision_boundary,
        "supporting_sections": support.supporting_sections,
        "missing_user_facts": support.missing_user_facts,
        "unsupported_proposition": support.unsupported_proposition,
        "authoritative_home": (
            authority.authoritative_home if authority else None
        ),
        "authority_kind": authority.authority_kind if authority else None,
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
                    "Fixed evidence adjudication (immutable):\n"
                    f"{json.dumps(fixed_adjudication, ensure_ascii=False)}"
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
        support.missing_user_facts,
        generated.missing_information,
    ):
        raise HTTPException(
            status_code=502,
            detail=(
                "The answer generator changed the support "
                "adjudicator's missing user facts."
            ),
        )

    outcome = _derive_outcome(
        evidence_status,
        support.decision_boundary,
    )
    missing_information = _clean_missing_information(
        support.missing_user_facts,
        support.decision_boundary,
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
        evidence_status=evidence_status,
        decision_boundary=support.decision_boundary,
        answer=generated.answer.strip(),
        citations=citations,
        missing_information=missing_information,
        disclaimer=DISCLAIMER,
    )