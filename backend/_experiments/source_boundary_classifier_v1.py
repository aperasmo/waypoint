"""Isolated experimental source-boundary classifier for Waypoint.

EXPERIMENTAL ONLY.

This module:
- does not import Waypoint production runtime;
- does not read evaluation/gold files;
- does not read the contract test pack;
- does not use retrieval, embeddings, reranking, database access, or web search;
- receives only one unsupported proposition plus optional trusted source context;
- makes one model call and performs strict deterministic validation;
- performs no retry, repair call, or fallback model.

Model execution is NOT authorised merely by the existence of this file.
"""

from __future__ import annotations

import json
from typing import Literal

from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


CLASSIFIER_REASONING_EFFORT = "none"
CLASSIFIER_MAX_COMPLETION_TOKENS = 800


ResolutionStatus = Literal["resolved", "unresolved"]

SourceDomain = Literal[
    "certified_immigration_instructions",
    "legislation_or_regulation",
    "official_inz_non_manual",
    "responsible_external_official_authority",
    "unresolved",
]

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

ResponsibleAuthorityType = Literal[
    "immigration_new_zealand",
    "new_zealand_legislation",
    "foreign_issuing_authority",
    "new_zealand_external_agency",
    "public_service_authority",
    "professional_or_assessment_authority",
    "other_official_authority",
    "unresolved",
]

PublisherFamily = Literal[
    "immigration_new_zealand",
    "new_zealand_legislation",
    "foreign_official_authority",
    "new_zealand_external_agency",
    "public_service_authority",
    "professional_or_assessment_authority",
    "other_official_authority",
]

PublicationFamily = Literal[
    "operational_manual",
    "certified_amendment",
    "primary_legislation",
    "secondary_legislation",
    "inz_iac",
    "inz_advice_to_staff",
    "inz_form_or_guide",
    "inz_live_service",
    "inz_fee_service",
    "foreign_issuing_service",
    "external_agency_service",
    "public_entitlement_regime",
    "professional_or_assessment_service",
    "other_official_service",
]

AuthorityRole = Literal[
    "immigration_instruction_owner",
    "legislative_authority",
    "document_issuing_authority",
    "non_professional_agency_assessment",
    "public_entitlement_owner",
    "professional_registration",
    "clinical_assessment",
    "professional_assessment",
    "other_official_operational_owner",
]

CertificationStatus = Literal[
    "certified",
    "not_applicable",
]

IncorporationStatus = Literal[
    "incorporated",
    "not_yet_indexed",
    "stale_local_index",
    "not_applicable",
]


class TrustedSourceContext(BaseModel):
    """Optional metadata from a separate trusted source registry."""

    model_config = ConfigDict(extra="forbid")

    publisher_family: PublisherFamily | None = None
    publication_family: PublicationFamily | None = None
    authority_role: AuthorityRole | None = None
    certification_status: CertificationStatus | None = None
    incorporation_status: IncorporationStatus | None = None


class SourceBoundaryResult(BaseModel):
    """Strict classifier output contract."""

    model_config = ConfigDict(extra="forbid")

    resolution_status: ResolutionStatus
    source_domain: SourceDomain
    source_class: SourceClass
    responsible_authority_type: ResponsibleAuthorityType
    basis: str = Field(min_length=1, max_length=600)

    @model_validator(mode="after")
    def validate_category_consistency(self) -> "SourceBoundaryResult":
        if self.resolution_status == "unresolved":
            expected = {
                self.source_domain,
                self.source_class,
                self.responsible_authority_type,
            }
            if expected != {"unresolved"}:
                raise ValueError(
                    "Unresolved resolution requires all categorical fields "
                    "to be unresolved."
                )
            return self

        if "unresolved" in {
            self.source_domain,
            self.source_class,
            self.responsible_authority_type,
        }:
            raise ValueError(
                "Resolved resolution prohibits unresolved categorical fields."
            )

        expected_by_class: dict[
            str,
            tuple[str, str],
        ] = {
            "operational_manual_instruction": (
                "certified_immigration_instructions",
                "immigration_new_zealand",
            ),
            "manual_instruction_transition": (
                "certified_immigration_instructions",
                "immigration_new_zealand",
            ),
            "legislation_or_regulation": (
                "legislation_or_regulation",
                "new_zealand_legislation",
            ),
            "inz_live_service_information": (
                "official_inz_non_manual",
                "immigration_new_zealand",
            ),
            "current_fee_or_charge_information": (
                "official_inz_non_manual",
                "immigration_new_zealand",
            ),
            "inz_non_manual_procedure_or_interpretation": (
                "official_inz_non_manual",
                "immigration_new_zealand",
            ),
            "foreign_issuing_authority_procedure": (
                "responsible_external_official_authority",
                "foreign_issuing_authority",
            ),
            "external_agency_assessment_or_service": (
                "responsible_external_official_authority",
                "new_zealand_external_agency",
            ),
            "external_entitlement_or_service_regime": (
                "responsible_external_official_authority",
                "public_service_authority",
            ),
            "professional_or_assessor_guidance": (
                "responsible_external_official_authority",
                "professional_or_assessment_authority",
            ),
            "other_official_external_authority": (
                "responsible_external_official_authority",
                "other_official_authority",
            ),
        }

        expected_domain, expected_authority = expected_by_class[
            self.source_class
        ]

        if self.source_domain != expected_domain:
            raise ValueError(
                f"{self.source_class} requires source_domain="
                f"{expected_domain}."
            )

        if self.responsible_authority_type != expected_authority:
            raise ValueError(
                f"{self.source_class} requires "
                f"responsible_authority_type={expected_authority}."
            )

        return self


class ClassifierContractError(RuntimeError):
    """Raised when the model response violates the frozen classifier contract."""


SYSTEM_PROMPT = """\
You are a source-boundary classifier for Waypoint.

Waypoint is currently bounded to the New Zealand Immigration Operational
Manual as its indexed evidence base.

You receive one material proposition that has ALREADY been determined by an
upstream process to be unsupported by the supplied Operational Manual
evidence.

Your only task is to classify the authoritative source domain of that exact
unsupported proposition.

Do not answer the proposition.
Do not give immigration advice.
Do not decide whether retrieved evidence is sufficient.
Do not infer an external source merely because Manual evidence is absent.
Do not classify from the broad visa, occupation, nationality, or application
topic. Classify the exact proposition.

SOURCE CLASSES

operational_manual_instruction
Use when the proposition itself is an immigration rule, visa criterion, visa
condition, immigration evidence requirement, immigration exception,
immigration definition, immigration consequence, verification rule,
assessment rule, or immigration decision criterion.

manual_instruction_transition
Use only when trusted source context establishes a certified immigration
instruction amendment that is not yet incorporated into the local indexed
Manual or the local index is stale. Do not infer this class from recency,
future wording, or Manual silence.

legislation_or_regulation
Use when the proposition itself concerns statutory authority, a legal rule, or
a requirement prescribed by legislation or regulation. Do not use this class
merely because immigration instructions ultimately derive authority from law.

inz_live_service_information
Use for a current or time-varying Immigration New Zealand operational service
state or value, other than a current fee or charge. This includes the kind of
information maintained as a live service rather than a static immigration
eligibility rule.

current_fee_or_charge_information
Use for the current payable application fee, levy, charge, or current
fee-waiver result. The legal authority for imposing a fee or levy belongs to
legislation_or_regulation instead.

inz_non_manual_procedure_or_interpretation
Use only when trusted source context explicitly identifies an official INZ
non-Manual publication family such as an Internal Administration Circular,
Advice to Staff, or an official form/guide. Procedural wording by itself is not
enough. Without trusted non-Manual source context, return unresolved.

foreign_issuing_authority_procedure
Use when the proposition concerns how a foreign official authority issues,
requests, verifies, or requires an application for its own official document.
An INZ requirement to provide that foreign document remains an immigration
instruction instead.

professional_or_assessor_guidance
Use when the responsible authority is professional, clinical, registration,
provider-specific, or assessor-specific and owns the proposition in that
professional or assessment remit. This class takes precedence over generic
non-professional agency assessment.

external_agency_assessment_or_service
Use for a non-professional New Zealand government or statutory agency's
assessment, recognition, or service process. Do not use it for professional
registration, clinical assessment, professional assessment, or public-service
entitlement.

external_entitlement_or_service_regime
Use when the proposition concerns eligibility for or entitlement to a
separately administered public service, public benefit, or statutory service
regime.

other_official_external_authority
Use only when trusted source context identifies another official operational
owner and all more-specific source classes above have been excluded. Never use
this as a catch-all for uncertainty.

RESOLUTION ORDER

1. If trusted context establishes a certified instruction transition, classify
   manual_instruction_transition.
2. Otherwise distinguish legislation/regulation from certified immigration
   instruction content.
3. Separate current INZ live-service information from current fee/charge
   information.
4. Resolve INZ non-Manual procedure/interpretation only with explicit trusted
   non-Manual source context.
5. For external authority propositions, distinguish foreign issuing procedure,
   professional/clinical/registration authority, non-professional agency
   assessment, and public entitlement.
6. Use other_official_external_authority only with explicit trusted official
   owner context after excluding every more-specific class.
7. If authoritative ownership cannot be established without guessing, return
   unresolved.

OUTPUT RULES

Return JSON only with exactly these fields:
resolution_status
source_domain
source_class
responsible_authority_type
basis

Allowed resolution_status values:
resolved
unresolved

Allowed source_domain values:
certified_immigration_instructions
legislation_or_regulation
official_inz_non_manual
responsible_external_official_authority
unresolved

Allowed source_class values:
operational_manual_instruction
manual_instruction_transition
legislation_or_regulation
inz_live_service_information
current_fee_or_charge_information
inz_non_manual_procedure_or_interpretation
foreign_issuing_authority_procedure
external_agency_assessment_or_service
external_entitlement_or_service_regime
professional_or_assessor_guidance
other_official_external_authority
unresolved

Allowed responsible_authority_type values:
immigration_new_zealand
new_zealand_legislation
foreign_issuing_authority
new_zealand_external_agency
public_service_authority
professional_or_assessment_authority
other_official_authority
unresolved

If resolution_status is unresolved, source_domain, source_class, and
responsible_authority_type must all be unresolved.

The basis must briefly explain the source-boundary classification only. It must
not answer the unsupported proposition.
"""


def _normalise_context(
    trusted_source_context: TrustedSourceContext | dict[str, object] | None,
) -> TrustedSourceContext | None:
    if trusted_source_context is None:
        return None

    if isinstance(trusted_source_context, TrustedSourceContext):
        return trusted_source_context

    try:
        return TrustedSourceContext.model_validate(trusted_source_context)
    except ValidationError as exc:
        raise ClassifierContractError(
            "trusted_source_context violates the frozen input schema."
        ) from exc


def _validate_context_dependent_result(
    result: SourceBoundaryResult,
    context: TrustedSourceContext | None,
) -> None:
    if result.resolution_status == "unresolved":
        return

    if result.source_class == "manual_instruction_transition":
        if context is None:
            raise ClassifierContractError(
                "manual_instruction_transition requires trusted source context."
            )

        if not (
            context.publisher_family == "immigration_new_zealand"
            and context.publication_family == "certified_amendment"
            and context.certification_status == "certified"
            and context.incorporation_status
            in {"not_yet_indexed", "stale_local_index"}
        ):
            raise ClassifierContractError(
                "manual_instruction_transition lacks the required certified "
                "amendment transition context."
            )

    if result.source_class == "inz_non_manual_procedure_or_interpretation":
        if context is None:
            raise ClassifierContractError(
                "INZ non-Manual classification requires trusted source context."
            )

        if not (
            context.publisher_family == "immigration_new_zealand"
            and context.publication_family
            in {"inz_iac", "inz_advice_to_staff", "inz_form_or_guide"}
        ):
            raise ClassifierContractError(
                "INZ non-Manual classification lacks an allowed trusted "
                "publication family."
            )

    if result.source_class == "other_official_external_authority":
        if context is None:
            raise ClassifierContractError(
                "other_official_external_authority requires trusted context."
            )

        if not (
            context.publisher_family == "other_official_authority"
            and context.authority_role == "other_official_operational_owner"
        ):
            raise ClassifierContractError(
                "other_official_external_authority lacks the required trusted "
                "official-owner context."
            )


def _build_user_message(
    unsupported_proposition: str,
    context: TrustedSourceContext | None,
) -> str:
    proposition = unsupported_proposition.strip()

    if not proposition:
        raise ClassifierContractError(
            "unsupported_proposition must not be blank."
        )

    if len(proposition) > 2000:
        raise ClassifierContractError(
            "unsupported_proposition exceeds the experimental input limit."
        )

    context_payload: object

    if context is None:
        context_payload = None
    else:
        context_payload = context.model_dump(
            exclude_none=True,
            mode="json",
        )

    payload = {
        "unsupported_proposition": proposition,
        "trusted_source_context": context_payload,
    }

    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )


async def classify_source_boundary(
    unsupported_proposition: str,
    trusted_source_context: TrustedSourceContext | dict[str, object] | None,
    model: str,
) -> SourceBoundaryResult:
    """Classify one unsupported proposition.

    One model call only. No retries, repair calls, or fallbacks.
    """

    model_name = model.strip()

    if not model_name:
        raise ClassifierContractError("model must not be blank.")

    context = _normalise_context(trusted_source_context)
    user_message = _build_user_message(
        unsupported_proposition,
        context,
    )

    client = AsyncOpenAI()

    try:
        completion = await client.chat.completions.create(
            model=model_name,
            max_completion_tokens=CLASSIFIER_MAX_COMPLETION_TOKENS,
            reasoning_effort=CLASSIFIER_REASONING_EFFORT,
            response_format={"type": "json_object"},
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
        )
    except Exception as exc:
        raise ClassifierContractError(
            "Classifier model call failed."
        ) from exc

    if not completion.choices:
        raise ClassifierContractError(
            "Classifier model returned no choices."
        )

    content = completion.choices[0].message.content

    if not isinstance(content, str) or not content.strip():
        raise ClassifierContractError(
            "Classifier model returned empty content."
        )

    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ClassifierContractError(
            "Classifier model returned malformed JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise ClassifierContractError(
            "Classifier model output must be a JSON object."
        )

    try:
        result = SourceBoundaryResult.model_validate(payload)
    except ValidationError as exc:
        raise ClassifierContractError(
            "Classifier model output violates the frozen schema."
        ) from exc

    _validate_context_dependent_result(result, context)

    return result
