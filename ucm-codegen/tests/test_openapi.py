"""The generated OpenAPI reference"""

import re
from collections import Counter

from openapi_spec_validator import validate

from .conftest import PROJECT


def schema(doc, name):
    return doc["components"]["schemas"][name]


def test_document_is_valid_openapi_31(openapi_doc):
    assert openapi_doc["openapi"] == "3.1.1"
    validate(openapi_doc)


def test_info_traces_the_ontology(openapi_doc):
    info = openapi_doc["info"]
    assert info["title"] == "Unified Care Model API"
    assert info["version"] == "0.0.1"
    assert info["x-jsonld-context"] == "./context.jsonld"
    ontology = info["x-ucm-ontology"]
    assert ontology["iri"] == "urn:w3c:cg:ucm#"
    assert {s["file"] for s in ontology["sources"]} == {"ucm-ontology.jsonld", "ucm-shapes.jsonld"}
    assert all(s["digest"].startswith("sha256:") for s in ontology["sources"])


def test_root_classes_become_resources(openapi_doc):
    paths = openapi_doc["paths"]
    for segment in ["entities", "processes", "participations", "roles", "statements",
                    "semantic-contexts", "definition-artifacts", "memberships",
                    "membership-criteria", "activity-foci", "care-trajectory-contexts"]:
        assert f"/{segment}" in paths
        assert f"/{segment}/{{id}}" in paths
    assert "/people" not in paths  # Person is an Entity, not a root
    assert set(paths["/processes"]) == {"get", "post"}
    assert set(paths["/processes/{id}"]) == {"get", "put", "delete"}


def test_operation_ids_are_unique(openapi_doc):
    ids = Counter(op["operationId"] for item in openapi_doc["paths"].values() for op in item.values())
    assert ids and max(ids.values()) == 1
    assert {"listEntities", "createEntity", "getProcess", "listActivityFoci", "listMembershipCriteria"} <= set(ids)


def test_list_filters_by_subclass(openapi_doc):
    (param,) = openapi_doc["paths"]["/processes"]["get"]["parameters"]
    assert param["name"] == "type"
    assert {"Process", "Handshake", "HousingAssessment", "ClinicalEncounter"} <= set(param["schema"]["enum"])


def test_writes_validate_against_shapes(openapi_doc):
    create = openapi_doc["paths"]["/participations"]["post"]
    assert create["responses"]["422"] == {"$ref": "#/components/responses/ShapeViolation"}
    report = schema(openapi_doc, "ValidationReport")
    assert set(report["properties"]) == {"conforms", "results"}
    assert set(schema(openapi_doc, "Severity")["enum"]) == {"Violation", "Warning", "Info"}


def test_participation_cardinality(openapi_doc):
    participation = schema(openapi_doc, "Participation")
    props = participation["properties"]
    assert participation["required"] == ["@type", "occursWithin", "participatingEntity"]
    assert props["participatingEntity"]["$ref"] == "#/components/schemas/NodeRef"
    assert props["validFrom"] == {**props["validFrom"], "type": "string", "format": "date-time"}
    assert props["assumesRole"]["type"] == "array"
    assert props["@type"]["enum"] == ["Participation"]
    messages = [c["message"] for c in participation["x-ucm-constraints"]]
    assert "Participation validTo precedes validFrom." in messages


def test_subclasses_compose_with_all_of(openapi_doc):
    assessment = schema(openapi_doc, "HousingAssessment")
    assert assessment["allOf"] == [{"$ref": "#/components/schemas/Process"}]
    assert "hasResident" in assessment["properties"]
    assert schema(openapi_doc, "Process")["allOf"] == [{"$ref": "#/components/schemas/UcmNode"}]
    assert {"Handshake", "CoordinationRequest"} <= set(schema(openapi_doc, "Process")["properties"]["@type"]["enum"])


def test_recommended_min_count_is_not_required(openapi_doc):
    statement = schema(openapi_doc, "Statement")
    assert "madeWithinContext" not in statement["required"]
    assert statement["properties"]["madeWithinContext"]["x-ucm-recommended"] is True


def test_handshake_requires_negotiates(openapi_doc):
    handshake = schema(openapi_doc, "Handshake")
    assert handshake["required"] == ["@type", "negotiates"]
    assert handshake["properties"]["negotiates"]["minItems"] == 1


def test_lifecycle_state_is_an_open_vocabulary(openapi_doc):
    state = schema(openapi_doc, "Process")["properties"]["hasLifecycleState"]
    assert state["$ref"] == "#/components/schemas/LifecycleState"
    vocabulary = schema(openapi_doc, "LifecycleState")
    assert vocabulary["anyOf"][0]["enum"] == ["Accepted", "Declined", "Pending"]
    assert vocabulary["anyOf"][1] == {"$ref": "#/components/schemas/IRI"}


def test_domainless_properties_live_on_the_base(openapi_doc):
    base = schema(openapi_doc, "UcmNode")
    assert {"@context", "@id", "@type", "hasTemporalContext", "validDuring", "hasCareTrajectoryContext"} <= set(base["properties"])
    assert base["properties"]["hasCareTrajectoryContext"]["x-ucm-range"] == "ucm:CareTrajectoryContext"


def test_equivalent_classes_are_annotated(openapi_doc):
    person = schema(openapi_doc, "Person")
    assert len(person["x-ucm-equivalent-classes"]) == 3
    assert schema(openapi_doc, "Entity")["x-ucm-subclasses"][:2] == ["Device", "InformationArtifact"]


def test_no_hmis_terminology(openapi_text):
    """The refurbished toolchain and its output speak UCM only"""
    pattern = re.compile(r"hmis|\bhud\b", re.IGNORECASE)
    assert not pattern.search(openapi_text)
    sources = list((PROJECT / "src").rglob("*.py")) + list((PROJECT / "src").rglob("*.j2"))
    sources += list((PROJECT / "profiles").glob("*.yaml"))
    offenders = [p.name for p in sources if pattern.search(p.read_text(encoding="utf-8"))]
    assert offenders == []
