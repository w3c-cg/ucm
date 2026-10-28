"""JSON-LD context and examples: the context, schemas and conformant data agree"""

import json

import pytest
from jsonschema import Draft202012Validator
from pyld import jsonld
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from ucm_codegen.examples import build_examples
from ucm_codegen.generator import Generator

UCM = "urn:w3c:cg:ucm#"
BASE = "https://ucm.example/openapi.json"


def test_context_document_is_valid_json(spec):
    document = json.loads(Generator().generate_jsonld_context(spec))
    assert document["@context"]["ucm"] == UCM
    assert document["@context"]["Participation"] == "ucm:Participation"


def test_every_class_and_property_has_a_term(compilation, spec):
    terms = set(spec.context)
    assert {c.term for c in compilation.ir.classes.values()} <= terms
    assert {p.term for p in compilation.ir.properties.values()} <= terms


def test_context_containers_match_schema_arrays(spec):
    """@container @set exactly when the schema renders an array"""
    for schema in [spec.base_schema] + spec.schemas:
        for prop in schema.properties:
            if prop.name.startswith("@"):
                continue
            entry = spec.context[prop.name]
            assert (entry.get("@container") == "@set") == prop.is_set, prop.name
            assert (prop.value_schema.get("type") == "array") == prop.is_set, prop.name


def test_context_expands_to_ontology_iris(spec):
    node = {"@context": spec.context, "@id": "urn:ex:p", "@type": "Participation",
            "participatingEntity": "urn:ex:person", "validFrom": "2026-01-01T00:00:00Z"}
    (expanded,) = jsonld.expand(node)
    assert expanded["@type"] == [UCM + "Participation"]
    assert expanded[UCM + "participatingEntity"] == [{"@id": "urn:ex:person"}]
    assert expanded[UCM + "validFrom"][0]["@type"] == "http://www.w3.org/2001/XMLSchema#dateTime"


@pytest.fixture(scope="module")
def validators(openapi_doc):
    registry = Registry().with_resource(BASE, Resource.from_contents(openapi_doc, default_specification=DRAFT202012))

    def for_schema(name):
        return Draft202012Validator({"$ref": f"{BASE}#/components/schemas/{name}"}, registry=registry)

    return for_schema


def test_every_example_validates_against_its_schema(spec, validators):
    checked = 0
    for schema in spec.schemas:
        for example in schema.examples:
            errors = [e.message for e in validators(schema.name).iter_errors(example)]
            assert errors == [], f"{schema.name} {example['@id']}: {errors}"
            checked += 1
    assert checked == 28


def test_schemas_reject_definitional_defects(spec, validators):
    participation = next(s for s in spec.schemas if s.name == "Participation").examples[0]
    missing = {k: v for k, v in participation.items() if k != "occursWithin"}
    assert any("occursWithin" in e.message for e in validators("Participation").iter_errors(missing))
    doubled = {**participation, "participatingEntity": ["urn:ex:a", "urn:ex:b"]}
    assert list(validators("Participation").iter_errors(doubled))
    wrong_type = {**participation, "@type": "Process"}
    assert list(validators("Participation").iter_errors(wrong_type))


def test_date_time_stamp_does_not_compact(compilation, spec, example_graph):
    _, warnings = build_examples(example_graph, compilation.ir, spec.context)
    assert warnings == [
        "http://example.org/ucm/stmt-1: ucm:statementDate did not compact to a context term "
        "(value datatype differs from the term's coercion)"
    ]


def lifecycle_state(spec):
    request = next(s for s in spec.schemas if s.name == "CoordinationRequest").examples[0]
    return request["hasLifecycleState"]


def test_lifecycle_value_compacts_to_the_term(spec, regressed_spec):
    assert lifecycle_state(spec) == "Accepted"                # namespaces agree: the term
    assert lifecycle_state(regressed_spec) == "ucm:Accepted"  # drifted: no term matches
