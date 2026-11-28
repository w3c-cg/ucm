"""FHIR target: mapping overlay validation and the generated adapter"""

import importlib.util

import pytest
from fhir.resources.R4B.bundle import Bundle

from ucm_codegen.builder import SpecBuilder
from ucm_codegen.fhir_target import FhirCompiler, FhirMapping, FhirMappingError
from ucm_codegen.generator import Generator
from ucm_codegen.utils import load_yaml_safe

from .conftest import FHIR_MAPPING, example_nodes


def load_adapter(tmp_path_factory, compilation, profile, name):
    """Compile as the build does: the API profile's scheme bindings type governsAction and the like"""
    mapping = FhirMapping.model_validate(load_yaml_safe(FHIR_MAPPING))
    api = SpecBuilder(compilation.ir, profile)
    source = Generator().generate_fhir_adapter(FhirCompiler(compilation.ir, mapping, api).compile())
    path = tmp_path_factory.mktemp(name) / f"{name}.py"
    path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def adapter(tmp_path_factory, compilation, profile):
    return load_adapter(tmp_path_factory, compilation, profile, "adapter_shipped")


@pytest.fixture(scope="module")
def regressed_adapter(tmp_path_factory, regressed_compilation, profile):
    return load_adapter(tmp_path_factory, regressed_compilation, profile, "adapter_regressed")


@pytest.fixture(scope="module")
def bundle(adapter, spec):
    bundle, warnings = adapter.to_fhir_bundle(example_nodes(spec))
    assert warnings == EXPECTED_WARNINGS
    return bundle


# R4 limits the examples run into, each reported rather than written wrongly
EXPECTED_WARNINGS = [
    # Sarah's directive cites two regulatory bases; R4 Consent.policyRule holds one
    "http://example.org/ucm/cd-sarah Consent.policyRule: FHIR allows one value here; kept the first of 2",
    # a household-wide directive: R4 Consent.patient takes only a Patient (R5 subject allows a Group)
    "http://example.org/ucm/cd-thomson-hh Consent.patient: http://example.org/ucm/hh-thomson maps to Group; "
    "FHIR R4 allows only Patient here",
]


def resources(bundle):
    return {e["resource"]["identifier"][0]["value"].rsplit("/", 1)[-1]: e["resource"] for e in bundle["entry"]}


# ---------- Overlay validation ----------

def mapping_with(resources):
    return FhirMapping.model_validate({"resources": resources})


@pytest.mark.parametrize("resources, message", [
    ({"Client": {"resource": "Patient"}}, "unknown UCM class 'Client'"),
    ({"Person": {"resource": "Human"}}, "'Human' is not a FHIR R4 resource type"),
    ({"Person": {"resource": "Patient", "fields": {"subject": {"property": "hasPatient"}}}},
     "hasPatient has domain ucm:ClinicalEncounter, not applicable to ucm:Person"),
    ({"CoordinationRequest": {"resource": "Task", "fields": {"status": {
        "property": "hasLifecycleState", "transform": "code", "map": {"Open": "requested"}}}}},
     "['Open'] are not concepts of LifecycleState"),
    ({"Person": {"resource": "Patient", "by-role": {"Household": "Practitioner"}}},
     "Household is not a ucm:Role"),
], ids=["class", "resource", "domain", "concept", "role"])
def test_overlay_is_checked_against_the_ir(compilation, resources, message):
    with pytest.raises(FhirMappingError) as error:
        FhirCompiler(compilation.ir, mapping_with(resources)).compile()
    assert any(message in e for e in error.value.errors), error.value.errors


def test_overlay_rejects_unknown_keys():
    with pytest.raises(ValueError):
        FhirMapping.model_validate({"resources": {"Person": {"resource": "Patient", "feilds": {}}}})


# ---------- UCM → FHIR ----------

def test_bundle_is_valid_fhir(bundle):
    Bundle.model_validate(bundle)
    assert bundle["type"] == "collection"


def test_resource_types_and_identity(bundle):
    found = resources(bundle)
    assert {k: r["resourceType"] for k, r in found.items()} == {
        "cm-1": "Practitioner",    # assumes CoordinatorRole
        "person-a": "Patient",     # PatientRole / ResidentRole: default
        "org-ecm": "Organization",
        "org-fund": "Organization",
        "hh-001": "Group",
        "enc-1": "Encounter",
        "req-1": "Task",
        "stmt-1": "Observation",   # HousingEligibilityStatement via HousingStatement
        # consent and identity examples: people, households, organizations, a location
        **{p: "Patient" for p in ("ruth", "jameson", "madison", "sarah", "youth", "liaison", "proofer")},
        **{o: "Organization" for o in ("org-assessor", "org-clinic", "org-csp", "org-lead-agency", "org-state-e")},
        "hh-thomson": "Group",
        "loc-intake": "Location",
        **{d: "Consent" for d in ("cd-a-2025", "cd-a-verbal", "cd-jameson", "cd-jameson-2023",
                                  "cd-madison", "cd-sarah", "cd-thomson-hh", "cd-youth")},
    }
    assert found["req-1"]["meta"]["tag"] == [{"system": "https://www.w3.org/ns/ucm#", "code": "CoordinationRequest"}]


def test_task_from_coordination_request(bundle):
    task = resources(bundle)["req-1"]
    assert task["status"] == "accepted"
    assert task["description"] == "Tenancy preservation"
    entries = {e["resource"]["identifier"][0]["value"]: e["fullUrl"] for e in bundle["entry"]}
    assert task["requester"]["reference"] == entries["http://example.org/ucm/cm-1"]
    assert task["owner"]["reference"] == entries["http://example.org/ucm/org-fund"]
    assert "for" not in task  # no subject-role participation in the example


def test_encounter_keeps_the_patient_as_subject(bundle):
    encounter = resources(bundle)["enc-1"]
    assert "subject" in encounter
    assert "participant" not in encounter  # the only participation is PatientRole


def test_observation_follows_the_participation_chain(bundle):
    observation = resources(bundle)["stmt-1"]
    assert observation["code"]["coding"][0]["code"] == "HousingEligibilityStatement"
    assert observation["effectiveDateTime"] == "2026-09-02T10:45:00-07:00"  # read from the value object
    patient_url = next(e["fullUrl"] for e in bundle["entry"]
                       if e["resource"]["identifier"][0]["value"].endswith("person-a"))
    assert observation["subject"]["reference"] == patient_url


def test_namespace_drift_reaches_the_adapter(regressed_adapter, regressed_spec):
    bundle, warnings = regressed_adapter.to_fhir_bundle(example_nodes(regressed_spec))
    assert resources(bundle)["req-1"]["status"] == "draft"  # mapping default
    # the consent vocabularies drift too; outside Consent, only the request's status is affected
    assert [w for w in warnings if " Consent." not in w] == [
        "http://example.org/ucm/req-1 Task.status: 'ucm:Accepted' has no FHIR code in the mapping"]


def test_output_is_deterministic(adapter, spec, bundle):
    assert adapter.to_fhir_bundle(example_nodes(spec))[0] == bundle


def test_multi_typed_node_is_mapped(adapter):
    """A node also typed owl:NamedIndividual (a full IRI, not a UCM class term) used to
    crash mapping_for()/_is_a() with TypeError: unhashable type 'list'; mapping and the
    resulting coding should use the real UCM term, not the generic co-type."""
    node = {
        "@id": "http://example.org/ucm/req-multi",
        "@type": ["http://www.w3.org/2002/07/owl#NamedIndividual", "CoordinationRequest"],
    }
    bundle, warnings = adapter.to_fhir_bundle([node])
    assert warnings == []
    tag = bundle["entry"][0]["resource"]["meta"]["tag"][0]["code"]
    assert tag == "CoordinationRequest"


# ---------- FHIR → UCM ----------

def facts(nodes, keys):
    """(subject, key, value) facts, unwrapping lists and compact/value-object aliases"""
    out = set()
    for node in nodes:
        for key, value in node.items():
            if key == "@id":
                continue
            term = next((t for t, aliases in keys.items() if key in aliases), key)
            for v in value if isinstance(value, list) else [value]:
                out.add((node["@id"], term, v["@value"] if isinstance(v, dict) and "@value" in v else v))
    return out


def test_round_trip_invents_nothing(adapter, spec, bundle):
    original = facts(example_nodes(spec), adapter.KEYS)
    back = facts(adapter.from_fhir_bundle(bundle), adapter.KEYS)
    assert back <= original, back - original


def test_round_trip_recovers_mapped_facts(adapter, bundle):
    back = facts(adapter.from_fhir_bundle(bundle), adapter.KEYS)
    ex = "http://example.org/ucm/"
    assert {
        (ex + "req-1", "hasLifecycleState", "Accepted"),
        (ex + "p-cm", "occursWithin", ex + "req-1"),
        (ex + "p-cm", "participatingEntity", ex + "cm-1"),
        (ex + "p-fund", "participatingEntity", ex + "org-fund"),
        (ex + "enc-1", "hasPatient", ex + "person-a"),
        (ex + "mem-a", "membershipIn", ex + "hh-001"),
        (ex + "person-a", "hasMembership", ex + "mem-a"),
        (ex + "stmt-1", "statementDate", "2026-09-02T10:45:00-07:00"),
        (ex + "cm-1", "@type", "Person"),
    } <= back


# ---------- Coded states (concept-coding) ----------

UCM_CODES = "https://www.w3.org/ns/ucm#"


def test_task_carries_disposition_and_closure_reason(bundle):
    task = resources(bundle)["req-1"]
    assert task["businessStatus"] == {"coding": [{"system": UCM_CODES, "code": "ReferralAccepted"}]}
    assert task["statusReason"] == {"coding": [{"system": UCM_CODES, "code": "ClosedConnected"}]}


def test_coded_states_round_trip(adapter, bundle):
    back = facts(adapter.from_fhir_bundle(bundle), adapter.KEYS)
    ex = "http://example.org/ucm/"
    assert {
        (ex + "req-1", "hasReferralDisposition", "ReferralAccepted"),
        (ex + "req-1", "hasClosureReason", "ClosedConnected"),
    } <= back


def test_adopter_concepts_keep_their_iri(adapter):
    """A concept outside UCM goes out as text plus its IRI and comes back unchanged"""
    local = "http://example.org/hmis#NoBedsAvailable"
    node = {"@id": "http://example.org/ucm/req-9", "@type": "CoordinationRequest", "hasClosureReason": local}
    bundle, warnings = adapter.to_fhir_bundle([node])
    assert warnings == []
    reason = bundle["entry"][0]["resource"]["statusReason"]
    assert reason["text"] == local
    back = facts(adapter.from_fhir_bundle(bundle), adapter.KEYS)
    assert ("http://example.org/ucm/req-9", "hasClosureReason", local) in back


@pytest.mark.parametrize("field, message", [
    ({"property": "hasActivityFocus", "transform": "concept-coding"},
     "transform concept-coding needs a property bound to a concept scheme"),
    ({"property": "hasClosureReason", "transform": "concept-coding", "map": {"OutOfArea": "x"}},
     "map and default do not apply"),
], ids=["unbound", "map"])
def test_concept_coding_is_checked(compilation, field, message):
    with pytest.raises(FhirMappingError) as error:
        FhirCompiler(compilation.ir, mapping_with({"CoordinationRequest": {"resource": "Task", "fields": {
            "statusReason": field}}})).compile()
    assert any(message in e for e in error.value.errors), error.value.errors



# ---------- Consent ----------

EX = "http://example.org/ucm/"


def url_of(bundle, local):
    return next(e["fullUrl"] for e in bundle["entry"] if e["resource"]["identifier"][0]["value"] == EX + local)


def test_consent_from_directive(bundle):
    consent = resources(bundle)["cd-sarah"]
    assert consent["status"] == "active"
    assert consent["scope"]["coding"][0] == {
        "system": "http://terminology.hl7.org/CodeSystem/consentscope", "code": "patient-privacy"}
    assert consent["category"] == [{"coding": [{"system": UCM_CODES, "code": "ReleaseOfInformation"}]}]
    assert consent["patient"]["reference"] == url_of(bundle, "sarah")
    assert [p["reference"] for p in consent["performer"]] == [url_of(bundle, "sarah")]
    # R4 has no top-level decision: the directive is the root provision
    root = consent["provision"]
    assert root["type"] == "permit"
    deny = root["provision"][0]
    assert deny["type"] == "deny"
    assert deny["securityLabel"] == [{"system": UCM_CODES, "code": "Part2Protected"}]  # a bare Coding
    assert deny["data"][0]["meaning"] == "instance"
    permit = deny["provision"][0]
    assert permit["type"] == "permit"
    assert permit["purpose"] == [{"system": UCM_CODES, "code": "Treatment"}]
    assert permit["actor"][0]["reference"]["reference"] == url_of(bundle, "org-clinic")
    assert permit["actor"][0]["role"]["coding"][0]["code"] == "InformationRecipientRole"


def test_proxy_is_the_performer(bundle):
    consent = resources(bundle)["cd-jameson"]
    assert consent["patient"]["reference"] == url_of(bundle, "jameson")
    assert [p["reference"] for p in consent["performer"]] == [url_of(bundle, "ruth")]
    assert consent["organization"][0]["reference"] == url_of(bundle, "org-lead-agency")
    assert consent["policy"] == [{"uri": EX + "policy-coc-e", "extension": [
        {"url": "https://www.w3.org/ns/ucm#fhirNode", "valueUri": EX + "policy-coc-e"}]}]


def test_shared_status_code_keeps_the_exact_concept(adapter, bundle):
    consent = resources(bundle)["cd-jameson-2023"]
    assert consent["status"] == "inactive"
    assert consent["_status"]["extension"][0]["valueUri"] == UCM_CODES + "ConsentSuperseded"
    back = facts(adapter.from_fhir_bundle(bundle), adapter.KEYS)
    assert (EX + "cd-jameson-2023", "hasConsentStatus", "ConsentSuperseded") in back
    assert (EX + "cd-jameson-2023", "hasConsentStatus", "ConsentInactive") not in back


def test_consent_round_trip(adapter, bundle):
    back = facts(adapter.from_fhir_bundle(bundle), adapter.KEYS)
    assert {
        (EX + "cd-sarah", "hasConsentStatus", "ConsentActive"),
        (EX + "cd-sarah", "hasConsentCategory", "ReleaseOfInformation"),
        (EX + "cd-sarah", "hasConsentDecision", "Permit"),
        (EX + "cd-sarah", "consentSubject", EX + "p-sarah-subj"),
        (EX + "p-sarah-subj", "participatingEntity", EX + "sarah"),
        (EX + "cd-sarah", "hasProvision", EX + "prov-sarah-part2"),
        (EX + "prov-sarah-part2", "@type", "ConsentProvision"),
        (EX + "prov-sarah-part2", "hasConsentDecision", "Deny"),
        (EX + "prov-sarah-part2", "governsAction", "RediscloseAction"),
        (EX + "prov-sarah-part2", "coversSensitivity", "Part2Protected"),
        (EX + "prov-sarah-part2", "coversInstance", EX + "doc-sud-note"),
        (EX + "prov-sarah-part2", "hasProvision", EX + "prov-sarah-part2-tx"),
        (EX + "prov-sarah-part2-tx", "forPurpose", "Treatment"),
        (EX + "prov-sarah-part2-tx", "coversDataCategory", "BehavioralHealthInformation"),
        (EX + "prov-sarah-part2-tx", "provisionActor", EX + "p-clinic-recipient"),
        (EX + "p-clinic-recipient", "participatingEntity", EX + "org-clinic"),
        (EX + "p-clinic-recipient", "assumesRole", EX + "role-recipient"),
        (EX + "cd-jameson", "governedByPolicy", EX + "policy-coc-e"),
    } <= back


def test_consent_dates_and_shared_labels(adapter):
    """Time nodes, when present, give dateTime and periods; two schemes share securityLabel"""
    nodes = [
        {"@id": EX + "cd-t", "@type": "ConsentDirective", "hasConsentStatus": "ConsentActive",
         "hasConsentCategory": "ConsentToShare", "hasConsentDecision": "Permit",
         "recordsConsentFrom": [EX + "ci-t"], "validDuring": [EX + "t-valid"], "hasProvision": [EX + "pr-t"]},
        {"@id": EX + "ci-t", "@type": "ConsentInteraction", "occursDuring": [EX + "t-signed"]},
        {"@id": EX + "t-signed", "time:inXSDDateTimeStamp": {"@value": "2026-10-05T10:00:00-05:00"}},
        {"@id": EX + "t-valid", "time:hasBeginning": {"@id": EX + "t-b"}, "time:hasEnd": {"@id": EX + "t-e"}},
        {"@id": EX + "t-b", "time:inXSDDateTimeStamp": "2026-10-05T00:00:00-05:00"},
        {"@id": EX + "t-e", "time:inXSDDateTimeStamp": "2029-10-05T00:00:00-05:00"},
        {"@id": EX + "pr-t", "@type": "ConsentProvision", "hasConsentDecision": "Deny",
         "coversSensitivity": ["HIV"], "coversConfidentiality": ["ConfidentialityRestricted"]},
    ]
    bundle, warnings = adapter.to_fhir_bundle(nodes)
    assert warnings == []
    consent = bundle["entry"][0]["resource"]
    assert consent["dateTime"] == "2026-10-05T10:00:00-05:00"
    assert consent["provision"]["period"] == {"start": "2026-10-05T00:00:00-05:00", "end": "2029-10-05T00:00:00-05:00"}
    assert [c["code"] for c in consent["provision"]["provision"][0]["securityLabel"]] == [
        "HIV", "ConfidentialityRestricted"]
    Bundle.model_validate(bundle)
    back = facts(adapter.from_fhir_bundle(bundle), adapter.KEYS)
    assert (EX + "pr-t", "coversSensitivity", "HIV") in back
    assert (EX + "pr-t", "coversConfidentiality", "ConfidentialityRestricted") in back
    assert (EX + "pr-t", "coversSensitivity", "ConfidentialityRestricted") not in back


@pytest.mark.parametrize("field, message", [
    ({"via": "recordsConsentFrom", "property": "participatingEntity"}, "via needs inverse"),
    ({"property": "hasConsentStatus", "transform": "code", "coding": True}, "coding applies only to transform concept-coding"),
    ({"property": "hasConsentStatus", "transform": "concept-coding", "system": "http://x"}, "system applies only to transform code"),
    ({"property": "consentSubject", "transform": "reference", "resource-types": ["Human"]}, "'Human' is not a FHIR R4 resource type"),
], ids=["via", "coding", "system", "resource-types"])
def test_consent_options_are_checked(compilation, profile, field, message):
    with pytest.raises(FhirMappingError) as error:
        FhirCompiler(compilation.ir, mapping_with({"ConsentDirective": {"resource": "Consent", "fields": {
            "x": field}}}), SpecBuilder(compilation.ir, profile)).compile()
    assert any(message in e for e in error.value.errors), error.value.errors
