"""FHIR target: mapping overlay validation and the generated adapter"""

import importlib.util

import pytest
from fhir.resources.R4B.bundle import Bundle

from ucm_codegen.fhir_target import FhirCompiler, FhirMapping, FhirMappingError
from ucm_codegen.generator import Generator
from ucm_codegen.utils import load_yaml_safe

from .conftest import FHIR_MAPPING, example_nodes


def load_adapter(tmp_path_factory, compilation, name):
    mapping = FhirMapping.model_validate(load_yaml_safe(FHIR_MAPPING))
    source = Generator().generate_fhir_adapter(FhirCompiler(compilation.ir, mapping).compile())
    path = tmp_path_factory.mktemp(name) / f"{name}.py"
    path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def adapter(tmp_path_factory, compilation):
    return load_adapter(tmp_path_factory, compilation, "adapter_shipped")


@pytest.fixture(scope="module")
def regressed_adapter(tmp_path_factory, regressed_compilation):
    return load_adapter(tmp_path_factory, regressed_compilation, "adapter_regressed")


@pytest.fixture(scope="module")
def bundle(adapter, spec):
    bundle, warnings = adapter.to_fhir_bundle(example_nodes(spec))
    assert warnings == []
    return bundle


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
    }
    assert found["req-1"]["meta"]["tag"] == [{"system": "urn:w3c:cg:ucm", "code": "CoordinationRequest"}]


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
    assert warnings == ["http://example.org/ucm/req-1 Task.status: 'ucm:Accepted' has no FHIR code in the mapping"]


def test_output_is_deterministic(adapter, spec, bundle):
    assert adapter.to_fhir_bundle(example_nodes(spec))[0] == bundle


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
