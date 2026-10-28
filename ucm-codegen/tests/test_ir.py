"""Normalization into the Pydantic IR"""

import pytest
from pydantic import ValidationError
from rdflib import Graph, URIRef
from rdflib.namespace import SH

from ucm_codegen.models import OntologyClass, OntologyIR, PropertyConstraint, Severity, Tier
from ucm_codegen.normalize import NormalizationError, Normalizer

UCM = "urn:w3c:cg:ucm#"
UCMSH = "urn:w3c:cg:ucm:shapes#"


def test_ontology_header(compilation):
    ir = compilation.ir
    assert ir.iri == UCM
    assert ir.namespace == UCM
    assert ir.prefix == "ucm"
    assert ir.label == "Unified Care Model"
    assert ir.version == "v0.0.1"


def test_classes_and_properties(compilation):
    ir = compilation.ir
    assert len(ir.classes) == 63
    assert len(ir.properties) == 34
    assert sum(p.kind == "datatype" for p in ir.properties.values()) == 3
    # External equivalents are annotations on Person, not classes of their own
    assert all(iri.startswith(UCM) for iri in ir.classes)


def test_hierarchy(compilation):
    ir = compilation.ir
    assert ir.ancestors(UCM + "HousingEligibilityStatement") == [UCM + "HousingStatement", UCM + "Statement"]
    assert UCM + "Handshake" in ir.descendants(UCM + "Process")
    assert ir.root_of(UCM + "Handshake") == UCM + "Process"
    roots = {c.term for c in ir.roots()}
    assert {"Entity", "Process", "Participation", "Role", "Statement", "SemanticContext"} <= roots
    assert "Person" not in roots


def test_equivalent_classes(compilation):
    person = compilation.ir.classes[UCM + "Person"]
    assert person.equivalent_classes == [
        "http://purl.bioontology.org/ontology/SNOMEDCT#337915000",
        "http://purl.obolibrary.org/obo/NCBITaxon#9606",
        "https://www.commoncoreontologies.org/AgentOntology#ont00001262",
    ]


def test_properties(compilation):
    ir = compilation.ir
    entity = ir.properties[UCM + "participatingEntity"]
    assert (entity.domain, entity.range, entity.kind) == (UCM + "Participation", UCM + "Entity", "object")
    assert ir.properties[UCM + "validDuring"].superproperties == [UCM + "hasTemporalContext"]
    assert {p.term for p in ir.domainless_properties()} == {
        "hasCareTrajectoryContext", "hasTemporalContext", "validDuring",
    }


def test_concept_scheme(compilation):
    (scheme,) = compilation.ir.schemes.values()
    assert scheme.term == "LifecycleState"
    assert [c.term for c in scheme.concepts] == ["Accepted", "Declined", "Pending"]
    assert scheme.concepts[1].alt_labels == ["Declined"]


def test_property_shapes(compilation):
    ir = compilation.ir
    (entity,) = [c for c in ir.constraints_for(UCM + "participatingEntity", UCM + "Participation")
                 if c.iri == UCMSH + "Participation-entity"]
    assert (entity.min_count, entity.max_count, entity.node_kind) == (1, 1, "BlankNodeOrIRI")
    assert (entity.tier, entity.severity) == (Tier.DEFINITIONAL, Severity.VIOLATION)

    (date,) = ir.constraints_for(UCM + "statementDate", UCM + "Statement")
    assert date.datatypes == [
        "http://www.w3.org/2001/XMLSchema#dateTime",
        "http://www.w3.org/2001/XMLSchema#dateTimeStamp",
    ]

    context = next(c for s in ir.shapes for c in s.properties if c.iri == UCMSH + "Participation-context")
    assert context.paths == [UCM + "participationContext", UCM + "scopedBy"]

    member = next(c for s in ir.shapes for c in s.properties if c.iri == UCMSH + "Membership-member")
    assert member.inverse and member.paths == [UCM + "hasMembership"]


def test_sparql_constraints_inherit_node_shape_level(compilation):
    acyclic = next(s for s in compilation.ir.shapes if s.iri == UCMSH + "HandshakeAcyclicShape")
    (query,) = acyclic.sparql
    assert (query.tier, query.severity) == (Tier.DEFINITIONAL, Severity.VIOLATION)
    assert "negotiates+" in query.select


def test_pydantic_rejects_tier_severity_mismatch():
    with pytest.raises(ValidationError, match="requires sh:Violation"):
        PropertyConstraint(paths=[UCM + "x"], tier=Tier.DEFINITIONAL, severity=Severity.WARNING)


def test_recommended_tier_may_report_info():
    """ucm-shapes-lint L3: Recommended shapes report sh:Warning or sh:Info"""
    PropertyConstraint(paths=[UCM + "x"], tier=Tier.RECOMMENDED, severity=Severity.INFO)
    with pytest.raises(ValidationError, match="requires sh:Info or sh:Warning"):
        PropertyConstraint(paths=[UCM + "x"], tier=Tier.RECOMMENDED, severity=Severity.VIOLATION)


def test_normalizer_reports_mismatched_shapes(compilation):
    """A Definitional shape downgraded to sh:Warning stops the pipeline"""
    shapes = Graph()
    shapes += compilation.shapes
    shape = URIRef(UCMSH + "Participation-entity")
    shapes.set((shape, SH.severity, SH.Warning))
    with pytest.raises(NormalizationError, match="Participation-entity is tier Definitional"):
        Normalizer(compilation.ontology, shapes).to_ir()


def test_terms_must_be_unique():
    clash = {
        iri: OntologyClass(iri=iri, term="Person", label="Person")
        for iri in (UCM + "Person", "http://example.org/other#Person")
    }
    with pytest.raises(ValidationError, match="ambiguous"):
        OntologyIR(iri=UCM, namespace=UCM, label="x", classes=clash, properties={})
