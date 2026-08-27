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

import json
import re
from typing import Literal

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

1. Use only the provided sections. Do not use remembered, inferred, or outside \
immigration knowledge.
2. A retrieved section is evidence only for what its text actually states. \
Topic similarity, a related heading, a neighbouring rule, or a section about \
the same visa category is NOT enough to support the rule the user asked about.
3. Never invent section codes, dates, dollar amounts, hour limits, point \
values, thresholds, conditions, exceptions, or eligibility requirements. \
Every specific factual claim must be supported by the provided text.
4. Never decide whether a particular person qualifies, should apply, will be \
approved, or is eligible when the published rule leaves material personal \
facts or authorised judgement unresolved.
5. Cite only section codes shown in square brackets at the start of the \
provided sections. Do not cite finer sub-clause headings that are not supplied \
as retrievable section codes.

CLASSIFY TWO THINGS INDEPENDENTLY

A. evidence_status

"sufficient" - the provided sections contain all material published policy \
needed to explain the rule or criteria actually asked about. The evidence must \
cover the operative rule, not merely the same topic. A conditional rule can be \
sufficient even when the user's personal facts determine which branch applies. \
Sufficient does NOT require enough information to decide a person's final \
eligibility when the governing rule itself is fully present.

"corpus_gap" - answering the policy question requires material from the \
Operational Manual that is not present in the provided sections. Use this when \
an essential rule, definition, appendix, table, list, exception, visa-condition \
instruction, evidential requirement, or other manual material is absent. The \
missing material does NOT need to be explicitly referenced by the retrieved \
text. If the supplied sections are only adjacent or partial policy and do not \
contain the operative rule needed for the question, this is a corpus gap.

"external_source_required" - the requested answer depends on authoritative \
information that belongs outside this Operational Manual corpus. This includes \
facts maintained by another official source, live or time-sensitive operational \
information, fees or charges maintained outside the manual, service or \
processing status, or entitlements governed by another authoritative regime. \
Use this even if the provided manual sections are silent or contain only related \
background material.

SOURCE-OF-TRUTH PRECEDENCE

Before deciding between corpus_gap and external_source_required, identify where \
the missing information would authoritatively belong:

- If the missing rule or criterion is part of the Operational Manual, choose \
corpus_gap.
- If the requested value, status, entitlement, or operational fact is \
authoritatively maintained outside the Operational Manual, choose \
external_source_required.
- Do not choose corpus_gap merely because externally maintained information is \
absent from the manual.
- Do not choose external_source_required merely because the retrieved manual \
sections are incomplete when the missing material itself belongs in the manual.

MANDATORY EVIDENCE-ADEQUACY CHECK

Before choosing evidence_status:

1. Identify the actual information need in the user's question.
2. Break it into the material policy components that must be known to answer it.
3. For EACH material policy component, identify the exact provided text that \
supplies the operative rule or criterion.
4. Separate missing POLICY from missing PERSONAL FACTS.
5. If something is unsupported, determine whether its authoritative source is \
inside or outside the Operational Manual.

Then classify:

- If every material policy component is directly supported by the provided \
sections, choose sufficient.
- If an unsupported material component belongs to the Operational Manual, \
choose corpus_gap.
- If the answer inherently depends on an authoritative source outside this \
Operational Manual corpus, choose external_source_required.
- If the governing policy is fully present but the user's final result depends \
on unstated personal facts, evidence_status remains sufficient and the issue is \
handled by decision_boundary.

Do not use sufficient when you can only answer a related question.
Do not infer a missing rule from the title, subject area, neighbouring policy, \
or general purpose of a retrieved section.
Do not bridge gaps with common sense, likely practice, or outside knowledge.
Do not create a corpus gap merely because a question could be answered in more \
detail with additional personal facts when the governing published criteria \
are already present.

MANDATORY SELF-CONSISTENCY CHECK

After drafting the answer but BEFORE returning JSON, inspect the answer against \
the selected evidence_status.

If the answer says or clearly implies any of the following:
- an essential rule needed for the user's question is not in the provided text;
- the supplied sections do not contain enough policy to answer the actual \
question;
- the answer cannot be determined from this corpus because required policy is \
missing;

then evidence_status MUST NOT be sufficient.

In that situation:
- choose corpus_gap if the missing material belongs to the Operational Manual;
- choose external_source_required if the missing information belongs to another \
authoritative source.

Conversely, if the provided sections DO contain the governing rule and the only \
remaining uncertainty is which branch applies to the user's personal facts, do \
NOT call that a corpus gap. Use sufficient and classify the decision boundary \
appropriately.

A final sufficient answer must be able to pass this test:
"Can every material policy proposition needed to answer the actual question be \
pointed to in the supplied sections?"
If no, sufficient is invalid.

B. decision_boundary

"general_information" - the published rule can be explained directly from the \
question and provided sections without needing an important unstated personal \
fact to answer what the user asked. First-person wording alone does not make a \
question case-specific. If the decisive facts are already stated and the rule \
is categorical, explain the rule without declaring personal eligibility.

"case_specific_application" - the user asks what follows for their own \
situation and at least one unstated personal fact materially determines which \
published rule, branch, threshold, condition, or exception applies. Explain \
the published criteria but do not decide the personal result. List only the \
genuinely missing material facts in missing_information.

A consistency check: if your answer says or implies that you cannot determine \
the user's personal result without knowing an additional material fact, the \
decision boundary should normally be case_specific_application.

"discretionary_judgement" - even if all relevant personal facts were known, \
the requested result centrally depends on a qualitative or discretionary \
judgement by an authorised decision-maker. Explain the published test but do \
not make that judgement. Incidental wording that an officer must be satisfied \
does not by itself make a question discretionary; the judgement must be \
central to the requested result.

IMPORTANT CLASSIFICATION RULES

- Evidence sufficiency and decision boundary are separate.
- Missing personal facts do not create a corpus gap when the governing policy \
itself is fully present.
- First-person words such as "I" or "my" do not by themselves make a question \
case-specific.
- Treat facts clearly stated or necessarily presupposed by ordinary wording as \
already supplied.

CRITICAL HANDLING OF ALREADY-SUPPLIED FACTS

Facts explicitly stated by the user, including negative facts, are already \
supplied for the current question. \
- Never ask the user to confirm, clarify, or provide the same fact again. \
- Never repeat an already-supplied fact in missing_information. \
- Do not treat an explicitly failed policy branch as unresolved. \
- If the governing policy contains alternative branches, consider only the \
  remaining unresolved branches supported by the supplied Manual sections. \
- Do not infer that the overall requirement fails merely because one branch \
  fails, unless the supplied Manual text establishes that conclusion. \
- Do not introduce immigration rules or conclusions from these instructions. \
  The final answer must still be derived only from the supplied Manual sections. \

- If decision_boundary is general_information, missing_information MUST be [].
- If decision_boundary is case_specific_application, missing_information must \
contain only USER FACTS that could materially change the applicable published \
rule. Do not put missing policy sections, rules, appendices, tables, or external \
sources in missing_information.
- If evidence_status is corpus_gap, identify the missing policy material in \
the answer.
- If evidence_status is external_source_required, identify the kind of \
authoritative external information required and do not substitute related \
manual material for it.

ANSWER FORMULATION

- Answer only what the supplied evidence supports.
- When evidence_status is sufficient, answer the user's question directly but \
preserve material conditions and exceptions.
- When evidence_status is corpus_gap, explain the relevant rule that is present \
only if useful, then state exactly what policy material is missing. Do not \
complete the missing rule from inference.
- When evidence_status is external_source_required, state that the requested \
information is not contained in this Operational Manual corpus and identify \
the type of authoritative external source needed. Do not guess the current \
value, status, entitlement, or rule.
- Begin with "Yes" or "No" only when the supplied rule supports that categorical \
answer for the facts already stated and no material missing fact, exception, \
variation, missing policy, or authorised judgement prevents it.
- Never begin with a categorical answer and later admit that the supplied \
sections do not establish that answer.
- Before returning JSON, verify that every factual sentence is supported by \
the provided sections and that the first sentence is consistent with both \
evidence_status and decision_boundary.

CITATION CHECK

For every cited section:
- it must be one of the provided section codes; and
- its text must materially support a factual claim in the answer.

Do not cite a section merely because it is related to the same topic.

OUTPUT

Return JSON only:
{
  "evidence_status": "sufficient" | "corpus_gap" | "external_source_required",
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

def _clean_inline_citations(
    answer: str,
    allowed_codes: set[str],
) -> str:
    """Keep only retrieved section codes in inline answer citations."""

    def replace(match: re.Match[str]) -> str:
        values = [
            part.strip()
            for part in match.group(1).split(",")
        ]

        valid = [
            value
            for value in values
            if value in allowed_codes
        ]

        if not valid:
            return ""

        return f"[{', '.join(dict.fromkeys(valid))}]"

    cleaned = re.sub(
        r"\[([A-Z]{1,3}\d+(?:\.\d+)+(?:\s*,\s*[A-Z]{1,3}\d+(?:\.\d+)*)*)\]",
        replace,
        answer,
    )

    # Removing an invalid inline citation can leave whitespace before
    # punctuation. Normalise that without rewriting the model's answer.
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)

    return cleaned.strip()

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


def _looks_like_policy_gap(value: str) -> bool:
    """Reject policy gaps or policy self-assessments from missing_information."""
    text = value.casefold()

    policy_markers = (
        "operational manual",
        "manual rule",
        "policy rule",
        "policy section",
        "appendix ",
        "external source",
        "authoritative source",
        "indexed corpus",
        "corpus",
    )

    if any(marker in text for marker in policy_markers):
        return True

    # Section references such as SR3.20, WD3.5, U13.15, A4.25.
    if re.search(r"\b[A-Z]{1,3}\d+(?:\.\d+)+\b", value):
        return True

    # The user should provide facts, not assess themselves against policy.
    policy_assessment_patterns = (
        r"\bwhether you meet\b",
        r"\bwhether you satisfy\b",
        r"\bwhether you qualify\b",
        r"\bwhether you comply\b",
        r"\bdo you meet\b",
        r"\bdo you satisfy\b",
        r"\bdo you qualify\b",
        r"\bmeet the .* requirements\b",
        r"\bsatisfy the .* requirements\b",
    )

    return any(
        re.search(pattern, text)
        for pattern in policy_assessment_patterns
    )

def _clean_missing_information(
    items: list[str],
    decision_boundary: DecisionBoundary,
) -> list[str]:
    """Keep only distinct user facts that may affect a case-specific answer."""
    if decision_boundary == "general_information":
        return []

    cleaned: list[str] = []
    seen: set[str] = set()

    for item in items:
        value = item.strip().strip("-• ")
        if not value:
            continue

        # Policy gaps belong in the answer/evidence status, not in the list of
        # facts the user could provide about their own circumstances.
        if _looks_like_policy_gap(value):
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
    allowed_codes = set(retrieved_by_code)
    answer = _clean_inline_citations(model_answer.answer.strip(), allowed_codes)
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
        answer=answer,
        citations=citations,
        missing_information=missing_information,
        disclaimer=DISCLAIMER,
    )