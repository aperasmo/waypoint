import json

import pytest
from pydantic import ValidationError

from _experiments.source_boundary_classifier_v3 import (
    ClassifierContractError,
    ClassifierModelOutput,
    SourceBoundaryClassification,
    TrustedSourceContext,
    derive_classification,
    parse_model_content,
    validate_proposed_class,
)

EXPECTED_DERIVATIONS = {
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

VALID_CONTEXTS = {
    "manual_instruction_transition": {
        "publisher_family": "immigration_new_zealand",
        "publication_family": "certified_amendment",
        "certification_status": "certified",
        "incorporation_status": "not_yet_indexed",
    },
    "inz_non_manual_procedure_or_interpretation": {
        "publisher_family": "immigration_new_zealand",
        "publication_family": "inz_form_or_guide",
    },
    "other_official_external_authority": {
        "publisher_family": "other_official_authority",
        "authority_role": "other_official_operational_owner",
    },
}


@pytest.mark.parametrize(("source_class", "expected"), EXPECTED_DERIVATIONS.items())
def test_all_source_class_derivations(source_class, expected):
    context = VALID_CONTEXTS.get(source_class)
    result = derive_classification(
        ClassifierModelOutput(proposed_source_class=source_class, basis="Generic basis"), context
    )
    assert (
        result.resolution_status,
        result.source_domain,
        result.responsible_authority_type,
    ) == expected


@pytest.mark.parametrize("source_class", VALID_CONTEXTS)
def test_each_context_gate_passes_valid_context(source_class):
    assert validate_proposed_class(source_class, VALID_CONTEXTS[source_class]) == (
        source_class,
        "passed",
    )


@pytest.mark.parametrize("source_class", VALID_CONTEXTS)
def test_each_context_gate_demotes_missing_context(source_class):
    assert validate_proposed_class(source_class) == ("unresolved", "failed_to_unresolved")


@pytest.mark.parametrize("source_class", VALID_CONTEXTS)
def test_each_context_gate_demotes_invalid_context(source_class):
    assert validate_proposed_class(source_class, {"publisher_family": "wrong"}) == (
        "unresolved",
        "failed_to_unresolved",
    )


def test_validation_cannot_promote_unresolved():
    assert validate_proposed_class(
        "unresolved", VALID_CONTEXTS["manual_instruction_transition"]
    ) == ("unresolved", "not_applicable")


@pytest.mark.parametrize(
    "source_class",
    set(EXPECTED_DERIVATIONS) - set(VALID_CONTEXTS) - {"unresolved"},
)
def test_validation_cannot_remap_resolved_non_gated_class(source_class):
    assert validate_proposed_class(source_class, {"publisher_family": "wrong"}) == (
        source_class,
        "not_applicable",
    )


def test_gate_failure_derives_everything_from_final_unresolved_class():
    result = derive_classification(
        ClassifierModelOutput(
            proposed_source_class="other_official_external_authority", basis="Owner unclear"
        )
    )
    assert result.proposed_source_class == "other_official_external_authority"
    assert result.source_class == result.resolution_status == result.source_domain == "unresolved"
    assert result.responsible_authority_type == "unresolved"
    assert result.gate_action == "failed_to_unresolved"


@pytest.mark.parametrize(
    ("proposed", "expected"),
    [
        ("foreign_issuing_authority_procedure", "foreign_issuing_authority_procedure"),
        ("external_agency_assessment_or_service", "external_agency_assessment_or_service"),
        ("unresolved", "unresolved"),
    ],
)
def test_foreign_boundary_proposals_are_not_deterministically_reclassified(proposed, expected):
    # The semantic issuer/service distinction belongs to the one model proposal;
    # deterministic validation must preserve all three possible outcomes.
    assert validate_proposed_class(proposed)[0] == expected


def test_model_output_requires_proposed_field_and_forbids_extra_fields():
    with pytest.raises(ValidationError):
        ClassifierModelOutput.model_validate({"source_class": "unresolved", "basis": "x"})
    with pytest.raises(ValidationError):
        ClassifierModelOutput.model_validate(
            {"proposed_source_class": "unresolved", "basis": "x", "extra": True}
        )


def test_final_output_forbids_extra_fields():
    valid = derive_classification(
        ClassifierModelOutput(proposed_source_class="unresolved", basis="Ambiguous")
    ).model_dump()
    valid["extra"] = True
    with pytest.raises(ValidationError):
        SourceBoundaryClassification.model_validate(valid)


def test_parser_rejects_non_object_and_extra_fields():
    with pytest.raises(ClassifierContractError):
        parse_model_content(json.dumps([]))
    with pytest.raises(ClassifierContractError):
        parse_model_content(
            json.dumps({"proposed_source_class": "unresolved", "basis": "x", "extra": 1})
        )


def test_trusted_context_forbids_extra_fields():
    with pytest.raises(ValidationError):
        TrustedSourceContext.model_validate({"publisher_family": "x", "extra": "y"})
