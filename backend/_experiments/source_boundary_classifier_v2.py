"""Experimental Waypoint source-boundary classifier v2.

Implements frozen classifier design v3.

EXPERIMENTAL ONLY.
- Not imported by production app/.
- One model call per classify() invocation.
- No retry.
- No repair call.
- No fallback model.
- No retrieval.
- No benchmark/evaluation imports.
- The model predicts only source_class + diagnostic basis.
- resolution_status, source_domain, and responsible_authority_type are derived
  deterministically from source_class.

This module does NOT execute a model call when imported.
"""

from __future__ import annotations

import json
from typing import Literal, Mapping

from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError


CLASSIFIER_MODEL = "gpt-5.4-mini"
CLASSIFIER_REASONING_EFFORT = "none"
CLASSIFIER_MAX_COMPLETION_TOKENS = 800
CLASSIFIER_TEMPERATURE = 0.0


SourceClass = Literal[
    "operational_manual_instruction",
    "manual_instruction_transition",
    "legislation_or_regulation",
    "inz_live_service_information",
    "current_fee_or_charge_information",
    "inz_non_manual_procedure_or_interpretation",
    "foreign_issuing_authority_procedure",
    "external_agency_assessment_or_service",
    "external_entitlement_or_service_regime",
    "professional_or_assessor_guidance",
    "other_official_external_authority",
    "unresolved",
]

ResolutionStatus = Literal["resolved", "unresolved"]

SourceDomain = Literal[
    "certified_immigration_instructions",
    "legislation_or_regulation",
    "official_inz_non_manual",
    "responsible_external_official_authority",
    "unresolved",
]

ResponsibleAuthorityType = Literal[
    "immigration_new_zealand",
    "new_zealand_legislature_or_regulator",
    "foreign_issuing_authority",
    "external_government_agency",
    "public_service_authority",
    "professional_or_assessment_authority",
    "other_official_authority",
    "unresolved",
]


class ClassifierContractError(RuntimeError):
    """Raised when a model response violates the classifier contract."""


class ClassifierInputError(ValueError):
    """Raised when classifier input violates the frozen input contract."""


class TrustedSourceContext(BaseModel):
    """Optional trusted metadata about the proposition's source family."""

    model_config = ConfigDict(extra="forbid")

    publisher_family: str | None = None
    publication_family: str | None = None
    authority_role: str | None = None
    certification_status: str | None = None
    incorporation_status: str | None = None


class ClassifierModelOutput(BaseModel):
    """The only categorical state the model is allowed to generate."""

    model_config = ConfigDict(extra="forbid")

    source_class: SourceClass
    basis: str = Field(min_length=1, max_length=1200)


class SourceBoundaryClassification(BaseModel):
    """Validated classification after deterministic derivation."""

    model_config = ConfigDict(extra="forbid")

    resolution_status: ResolutionStatus
    source_domain: SourceDomain
    source_class: SourceClass
    responsible_authority_type: ResponsibleAuthorityType
    basis: str


_DERIVATION: dict[
    SourceClass,
    tuple[
        ResolutionStatus,
        SourceDomain,
        ResponsibleAuthorityType,
    ],
] = {
    "operational_manual_instruction": (
        "resolved",
        "certified_immigration_instructions",
        "immigration_new_zealand",
    ),
    "manual_instruction_transition": (
        "resolved",
        "certified_immigration_instructions",
        "immigration_new_zealand",
    ),
    "legislation_or_regulation": (
        "resolved",
        "legislation_or_regulation",
        "new_zealand_legislature_or_regulator",
    ),
    "inz_live_service_information": (
        "resolved",
        "official_inz_non_manual",
        "immigration_new_zealand",
    ),
    "current_fee_or_charge_information": (
        "resolved",
        "official_inz_non_manual",
        "immigration_new_zealand",
    ),
    "inz_non_manual_procedure_or_interpretation": (
        "resolved",
        "official_inz_non_manual",
        "immigration_new_zealand",
    ),
    "foreign_issuing_authority_procedure": (
        "resolved",
        "responsible_external_official_authority",
        "foreign_issuing_authority",
    ),
    "external_agency_assessment_or_service": (
        "resolved",
        "responsible_external_official_authority",
        "external_government_agency",
    ),
    "external_entitlement_or_service_regime": (
        "resolved",
        "responsible_external_official_authority",
        "public_service_authority",
    ),
    "professional_or_assessor_guidance": (
        "resolved",
        "responsible_external_official_authority",
        "professional_or_assessment_authority",
    ),
    "other_official_external_authority": (
        "resolved",
        "responsible_external_official_authority",
        "other_official_authority",
    ),
    "unresolved": (
        "unresolved",
        "unresolved",
        "unresolved",
    ),
}


SYSTEM_PROMPT = """You classify the authoritative source home of ONE proposition.

Your task is source-home classification only.

Do not answer the proposition.
Do not provide immigration advice.
Do not decide whether retrieved Operational Manual evidence is sufficient.
Do not retrieve information.
Do not infer from benchmark labels, examples, or expected answers.

Return exactly one JSON object with exactly these fields:
- "source_class": one allowed source class
- "basis": a concise explanation of why that source class owns the proposition

Allowed source classes:

1. operational_manual_instruction
A substantive certified immigration-instruction rule: an eligibility criterion,
condition, exception, requirement, obligation, permission, restriction, or
other immigration rule whose authoritative home is certified immigration
instructions.

2. manual_instruction_transition
A certified immigration-instruction amendment that is authoritative but is not
yet represented correctly in the local Operational Manual index. This class is
CONTEXT-GATED. Use it only when trusted context establishes:
- publisher_family = immigration_new_zealand
- publication_family = certified_amendment
- certification_status = certified
- incorporation_status = not_yet_indexed OR stale_local_index

3. legislation_or_regulation
A statutory, regulatory, or other legal-authority proposition. Use this for the
legal basis, power, legal obligation, or legal authority itself, rather than an
operational immigration instruction or a current payable value.

4. inz_live_service_information
A current or time-varying Immigration New Zealand service state or operational
value, such as current processing timeframes, current service/channel opening,
current submission availability, current quota/place availability, or current
appointment availability. Trusted publication metadata is NOT required when the
proposition itself clearly identifies this live INZ service role.

5. current_fee_or_charge_information
The current payable amount of an immigration fee, levy, charge, surcharge, or
location/channel-dependent immigration application cost. Trusted publication
metadata is NOT required when the proposition itself clearly asks for a current
payable immigration amount.

6. inz_non_manual_procedure_or_interpretation
An Immigration New Zealand non-Manual procedural or interpretive publication.
This class is CONTEXT-GATED. Use it only when trusted context establishes:
- publisher_family = immigration_new_zealand
- publication_family is one of:
  inz_iac
  inz_advice_to_staff
  inz_form_or_guide
Procedural wording alone does not establish this class.

7. foreign_issuing_authority_procedure
A procedure owned by a foreign authority acting specifically in an ISSUING
role for a document or official record, including obtaining, replacing,
issuing, certifying, or verifying an item that authority is responsible for
issuing.

Do NOT use this class merely because the responsible authority is foreign.
Customs, border, traveller-declaration, tax, benefit, policing operations that
are not record issuance, and other general foreign operational processes are
not foreign_issuing_authority_procedure solely because they are foreign.

8. external_agency_assessment_or_service
An assessment, recognition, verification, or administrative service owned by a
non-professional external official agency, when a more specific professional,
entitlement, issuing, or other class does not apply.

9. external_entitlement_or_service_regime
Eligibility for, access to, or rules of a separately administered public
benefit or public service regime outside immigration instructions, including
where immigration status is an input to that external entitlement decision.

10. professional_or_assessor_guidance
Guidance or requirements whose authoritative owner is a professional,
clinical, registration, provider, or specialist-assessor role.

11. other_official_external_authority
A generic official external operational owner when no more specific external
class applies. This is a CONTEXT-GATED last-resort resolved class. Use it only
when trusted context establishes:
- publisher_family = other_official_authority
- authority_role = other_official_operational_owner

12. unresolved
Use unresolved when authoritative source ownership remains genuinely ambiguous
after applying the rules below, or when a context-gated class is plausible but
its required trusted context is absent or insufficient.

Classification policy:

A. Proposition semantics can be sufficient.
Trusted source context is NOT a universal prerequisite. If the proposition
itself clearly identifies a source role that is explicitly semantic above,
classify that role directly.

B. Apply context gates only to:
- manual_instruction_transition
- inz_non_manual_procedure_or_interpretation
- other_official_external_authority

C. Precedence and boundaries:
- Professional, clinical, registration, provider, or specialist-assessor
  ownership takes precedence over generic external-agency service.
- A CURRENT payable fee/levy/charge amount is
  current_fee_or_charge_information. The law that creates or authorises the
  charge is legislation_or_regulation.
- A CURRENT INZ service state/value is inz_live_service_information. A
  substantive certified immigration criterion, condition, exception, or rule
  is operational_manual_instruction.
- foreign_issuing_authority_procedure requires an actual issuing role.
- other_official_external_authority is last-resort and requires its trusted
  context gate.

D. Safety:
Use unresolved when two or more classes remain materially plausible after
precedence, or required context for a context-gated class is unavailable.
Do not use unresolved merely because trusted metadata is absent when the
proposition clearly identifies a semantic source role.

Output no additional keys.
"""


def _normalise_context(
    trusted_source_context: TrustedSourceContext
    | Mapping[str, str | None]
    | None,
) -> TrustedSourceContext | None:
    if trusted_source_context is None:
        return None

    if isinstance(
        trusted_source_context,
        TrustedSourceContext,
    ):
        return trusted_source_context

    try:
        return TrustedSourceContext.model_validate(
            dict(trusted_source_context)
        )
    except ValidationError as exc:
        raise ClassifierInputError(
            "trusted_source_context violates the frozen input schema."
        ) from exc


def _context_text(
    trusted_source_context: TrustedSourceContext | None,
) -> str:
    if trusted_source_context is None:
        return "NONE"

    data = trusted_source_context.model_dump(
        exclude_none=True
    )

    if not data:
        return "NONE"

    return "\n".join(
        f"{key}={data[key]}"
        for key in sorted(data)
    )


def build_classifier_messages(
    unsupported_proposition: str,
    trusted_source_context: TrustedSourceContext
    | Mapping[str, str | None]
    | None = None,
) -> list[dict[str, str]]:
    """Build the frozen zero-shot classifier messages without calling a model."""

    proposition = unsupported_proposition.strip()

    if not proposition:
        raise ClassifierInputError(
            "unsupported_proposition must not be empty."
        )

    context = _normalise_context(
        trusted_source_context
    )

    user_content = (
        "Unsupported proposition:\n"
        f"{proposition}\n\n"
        "Trusted source context:\n"
        f"{_context_text(context)}"
    )

    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]


def derive_classification(
    model_output: ClassifierModelOutput,
) -> SourceBoundaryClassification:
    """Derive all dependent categorical fields from source_class."""

    try:
        (
            resolution_status,
            source_domain,
            responsible_authority_type,
        ) = _DERIVATION[model_output.source_class]
    except KeyError as exc:
        raise ClassifierContractError(
            "Classifier returned an unsupported source_class."
        ) from exc

    return SourceBoundaryClassification(
        resolution_status=resolution_status,
        source_domain=source_domain,
        source_class=model_output.source_class,
        responsible_authority_type=responsible_authority_type,
        basis=model_output.basis.strip(),
    )


def parse_model_content(
    content: str,
) -> SourceBoundaryClassification:
    """Parse one raw model response and derive dependent fields."""

    if not isinstance(content, str) or not content.strip():
        raise ClassifierContractError(
            "Classifier model returned empty content."
        )

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ClassifierContractError(
            "Classifier model output is not valid JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise ClassifierContractError(
            "Classifier model output must be a JSON object."
        )

    try:
        model_output = ClassifierModelOutput.model_validate(
            payload
        )
    except ValidationError as exc:
        raise ClassifierContractError(
            "Classifier model output violates the frozen schema."
        ) from exc

    return derive_classification(model_output)


async def classify_source_boundary(
    unsupported_proposition: str,
    trusted_source_context: TrustedSourceContext
    | Mapping[str, str | None]
    | None = None,
    *,
    client: AsyncOpenAI | None = None,
) -> SourceBoundaryClassification:
    """Classify one unsupported proposition with exactly one model call."""

    messages = build_classifier_messages(
        unsupported_proposition,
        trusted_source_context,
    )

    api_client = client or AsyncOpenAI()

    response = await api_client.chat.completions.create(
        model=CLASSIFIER_MODEL,
        messages=messages,
        reasoning_effort=CLASSIFIER_REASONING_EFFORT,
        max_completion_tokens=CLASSIFIER_MAX_COMPLETION_TOKENS,
        temperature=CLASSIFIER_TEMPERATURE,
        response_format={"type": "json_object"},
    )

    if len(response.choices) != 1:
        raise ClassifierContractError(
            "Classifier model returned an unexpected number of choices."
        )

    content = response.choices[0].message.content

    return parse_model_content(content)
