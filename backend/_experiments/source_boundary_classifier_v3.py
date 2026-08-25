"""Experimental Waypoint source-boundary classifier v3 (design v4).

This module is deliberately isolated from production. The model proposes only a
source class and diagnostic basis; context gates and dependent fields are then
handled deterministically without further model calls.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Literal

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
GateAction = Literal["not_applicable", "passed", "failed_to_unresolved"]


class ClassifierContractError(RuntimeError):
    """Raised when a model response violates the classifier contract."""


class ClassifierInputError(ValueError):
    """Raised when classifier input violates the input contract."""


class TrustedSourceContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    publisher_family: str | None = None
    publication_family: str | None = None
    authority_role: str | None = None
    certification_status: str | None = None
    incorporation_status: str | None = None


class ClassifierModelOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposed_source_class: SourceClass
    basis: str = Field(min_length=1, max_length=1200)


class SourceBoundaryClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposed_source_class: SourceClass
    source_class: SourceClass
    resolution_status: ResolutionStatus
    source_domain: SourceDomain
    responsible_authority_type: ResponsibleAuthorityType
    basis: str
    gate_action: GateAction


_DERIVATION: dict[SourceClass, tuple[ResolutionStatus, SourceDomain, ResponsibleAuthorityType]] = {
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
    "unresolved": ("unresolved", "unresolved", "unresolved"),
}

_GATED_CLASSES = {
    "manual_instruction_transition",
    "inz_non_manual_procedure_or_interpretation",
    "other_official_external_authority",
}

SYSTEM_PROMPT = """You classify the authoritative source home of ONE proposition.

Do not answer the proposition, provide immigration advice, retrieve information,
or assess whether supplied Manual evidence is sufficient.

Return exactly one JSON object with exactly these fields:
- "proposed_source_class": one allowed source class
- "basis": a concise explanation of why that source class owns the proposition

Allowed source classes:
- operational_manual_instruction: a substantive certified immigration instruction.
- manual_instruction_transition: a certified INZ amendment not yet represented
  correctly in the local Manual index; this class is context-gated.
- legislation_or_regulation: a legal basis, power, obligation, or authority.
- inz_live_service_information: a current or time-varying INZ service state/value.
- current_fee_or_charge_information: a current payable immigration amount.
- inz_non_manual_procedure_or_interpretation: an INZ non-Manual procedural or
  interpretive publication; this class is context-gated.
- foreign_issuing_authority_procedure: a foreign authority's procedure where its
  issuing relationship to the relevant document or official record is established.
- external_agency_assessment_or_service: an official agency's assessment,
  recognition, verification, or administrative service.
- external_entitlement_or_service_regime: a separately administered public
  benefit or service regime.
- professional_or_assessor_guidance: professional, clinical, registration,
  provider, or specialist-assessor guidance.
- other_official_external_authority: another official external operational owner;
  this last-resort class is context-gated.
- unresolved: ownership remains materially ambiguous or a required gate is absent.

Only these classes are context-gated:
- manual_instruction_transition requires publisher_family=immigration_new_zealand,
  publication_family=certified_amendment, certification_status=certified, and
  incorporation_status=not_yet_indexed or stale_local_index.
- inz_non_manual_procedure_or_interpretation requires
  publisher_family=immigration_new_zealand and publication_family=inz_iac,
  inz_advice_to_staff, or inz_form_or_guide.
- other_official_external_authority requires
  publisher_family=other_official_authority and
  authority_role=other_official_operational_owner.

Foreign issuing boundary: verification of an already-issued document does not
by itself establish issuer identity or an issuing role. Do not infer an issuing
relationship from verification, foreign status, public-record wording, or generic
document wording alone. A clear government verification, recognition, assessment,
or administrative service without an established issuing relationship is
external_agency_assessment_or_service unless a more specific class applies. If
ownership remains materially ambiguous, use unresolved.

Professional/specialist ownership takes precedence over generic agency service.
A current amount differs from the law authorising it. A current INZ service state
differs from a substantive immigration instruction. Output no additional keys.
"""


def normalise_context(
    context: TrustedSourceContext | Mapping[str, str | None] | None,
) -> TrustedSourceContext | None:
    if context is None or isinstance(context, TrustedSourceContext):
        return context
    try:
        return TrustedSourceContext.model_validate(dict(context))
    except (TypeError, ValueError, ValidationError) as exc:
        raise ClassifierInputError("trusted_source_context violates the input schema.") from exc


def context_gate_passes(source_class: SourceClass, context: TrustedSourceContext | None) -> bool:
    """Return whether the trusted metadata satisfies a design-v4 class gate."""
    if source_class not in _GATED_CLASSES:
        return True
    if context is None:
        return False
    if source_class == "manual_instruction_transition":
        return (
            context.publisher_family == "immigration_new_zealand"
            and context.publication_family == "certified_amendment"
            and context.certification_status == "certified"
            and context.incorporation_status in {"not_yet_indexed", "stale_local_index"}
        )
    if source_class == "inz_non_manual_procedure_or_interpretation":
        return (
            context.publisher_family == "immigration_new_zealand"
            and context.publication_family
            in {"inz_iac", "inz_advice_to_staff", "inz_form_or_guide"}
        )
    return (
        context.publisher_family == "other_official_authority"
        and context.authority_role == "other_official_operational_owner"
    )


def validate_proposed_class(
    proposed_source_class: SourceClass,
    context: TrustedSourceContext | Mapping[str, str | None] | None = None,
) -> tuple[SourceClass, GateAction]:
    """Apply gates only: never promote or reclassify to another resolved class."""
    trusted_context = normalise_context(context)
    if proposed_source_class not in _GATED_CLASSES:
        return proposed_source_class, "not_applicable"
    if context_gate_passes(proposed_source_class, trusted_context):
        return proposed_source_class, "passed"
    return "unresolved", "failed_to_unresolved"


def derive_classification(
    model_output: ClassifierModelOutput,
    context: TrustedSourceContext | Mapping[str, str | None] | None = None,
) -> SourceBoundaryClassification:
    final_class, gate_action = validate_proposed_class(model_output.proposed_source_class, context)
    resolution_status, source_domain, authority_type = _DERIVATION[final_class]
    return SourceBoundaryClassification(
        proposed_source_class=model_output.proposed_source_class,
        source_class=final_class,
        resolution_status=resolution_status,
        source_domain=source_domain,
        responsible_authority_type=authority_type,
        basis=model_output.basis.strip(),
        gate_action=gate_action,
    )


def build_classifier_messages(
    unsupported_proposition: str,
    context: TrustedSourceContext | Mapping[str, str | None] | None = None,
) -> list[dict[str, str]]:
    proposition = unsupported_proposition.strip()
    if not proposition:
        raise ClassifierInputError("unsupported_proposition must not be empty.")
    trusted_context = normalise_context(context)
    context_data = trusted_context.model_dump(exclude_none=True) if trusted_context else {}
    context_text = "\n".join(f"{key}={context_data[key]}" for key in sorted(context_data))
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Unsupported proposition:\n{proposition}\n\n"
                f"Trusted source context:\n{context_text or 'NONE'}"
            ),
        },
    ]


def parse_model_content(
    content: str,
    context: TrustedSourceContext | Mapping[str, str | None] | None = None,
) -> SourceBoundaryClassification:
    if not isinstance(content, str) or not content.strip():
        raise ClassifierContractError("Classifier model returned empty content.")
    try:
        payload = json.loads(content)
        if not isinstance(payload, dict):
            raise TypeError
        proposal = ClassifierModelOutput.model_validate(payload)
    except (json.JSONDecodeError, TypeError, ValidationError) as exc:
        raise ClassifierContractError("Classifier model output violates the schema.") from exc
    return derive_classification(proposal, context)


async def classify_source_boundary(
    unsupported_proposition: str,
    trusted_source_context: TrustedSourceContext | Mapping[str, str | None] | None = None,
    *,
    client: AsyncOpenAI | None = None,
) -> SourceBoundaryClassification:
    messages = build_classifier_messages(unsupported_proposition, trusted_source_context)
    response = await (client or AsyncOpenAI()).chat.completions.create(
        model=CLASSIFIER_MODEL,
        messages=messages,
        reasoning_effort=CLASSIFIER_REASONING_EFFORT,
        max_completion_tokens=CLASSIFIER_MAX_COMPLETION_TOKENS,
        temperature=CLASSIFIER_TEMPERATURE,
        response_format={"type": "json_object"},
    )
    if len(response.choices) != 1:
        raise ClassifierContractError("Classifier returned an unexpected number of choices.")
    return parse_model_content(response.choices[0].message.content, trusted_source_context)
