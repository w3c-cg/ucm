"""Normalization into the Pydantic IR"""

import pytest
from pydantic import ValidationError
from rdflib import Graph, URIRef
from rdflib.namespace import SH

from ucm_codegen.models import OntologyClass, OntologyIR, PropertyConstraint, Severity, Tier
from ucm_codegen.normalize import NormalizationError, Normalizer, _namespace_of

UCM = "https://www.w3.org/ns/ucm#"
UCMSH = "https://www.w3.org/ns/ucm#"


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
    assert len(ir.properties) == 39
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
    scheme = compilation.ir.schemes[UCM + "LifecycleState"]
    assert scheme.term == "LifecycleState"
    assert [c.term for c in scheme.concepts] == ["Accepted", "Declined", "Pending"]
    assert scheme.concepts[1].alt_labels == ["Declined"]


def test_each_concept_is_in_one_scheme(compilation):
    """A scheme is one axis: the same word on two axes is two concepts"""
    terms = [c.term for s in compilation.ir.schemes.values() for c in s.concepts]
    assert len(terms) == len(set(terms))


def test_closure_reasons_roll_up_to_not_connected(compilation):
    """The two-level ClosureReason scheme survives normalization, so rates can roll up"""
    broader = {c.term: c.broader for c in compilation.ir.schemes[UCM + "ClosureReason"].concepts}
    assert broader["ClosedConnected"] == broader["ClosedNotConnected"] == broader["ClosedNoLongerNeeded"] == []
    assert sorted(t for t, parents in broader.items() if parents == [UCM + "ClosedNotConnected"]) == [
        "ClientDeclined", "ClientUnreachable", "Ineligible", "MissingVerification",
        "OtherClosureReason", "OutOfArea", "ProgramCapacity",
    ]


def test_concepts_carry_their_mappings(compilation):
    concepts = {c.term: c for c in compilation.ir.schemes[UCM + "ReferralDisposition"].concepts}
    assert concepts["ReferralPending"].mappings == {"exactMatch": [UCM + "Pending"]}
    assert concepts["ReferralWithdrawn"].mappings == {}


def test_narrower_is_read_as_the_inverse_of_broader():
    g = Graph().parse(data="""
        @prefix skos: <http://www.w3.org/2004/02/skos/core#> .
        @prefix ex: <https://example.org/v#> .
        @prefix owl: <http://www.w3.org/2002/07/owl#> .
        <https://example.org/v#> a owl:Ontology .
        ex:S a skos:ConceptScheme .
        ex:Top a skos:Concept ; skos:inScheme ex:S ; skos:narrower ex:Leaf .
        ex:Leaf a skos:Concept ; skos:inScheme ex:S ; skos:closeMatch ex:Other .
    """, format="turtle")
    (scheme,) = Normalizer(g, Graph())._schemes().values()
    leaf = next(c for c in scheme.concepts if c.term == "Leaf")
    assert leaf.broader == ["https://example.org/v#Top"]
    assert leaf.mappings == {"closeMatch": ["https://example.org/v#Other"]}


def test_each_new_axis_has_a_property(compilation):
    """hasX → X: every scheme is reachable from a property, so the API and FHIR can carry it"""
    ir = compilation.ir
    for scheme, domain in [
        ("ReferralDisposition", "CoordinationRequest"), ("HandoffStatus", "Handshake"),
        ("HandshakeFulfillment", "Handshake"), ("ClosureReason", "CoordinationRequest"),
        ("CommitmentStatus", "CareCommitment"),
    ]:
        prop = ir.properties[UCM + "has" + scheme]
        assert (prop.domain, prop.range) == (UCM + domain, "http://www.w3.org/2004/02/skos/core#Concept")


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


@pytest.mark.parametrize("header, namespace", [
    ("urn:w3c:cg:ucm:shapes", "urn:w3c:cg:ucm:shapes#"),
    ("https://www.w3.org/ns/ucm#", "https://www.w3.org/ns/ucm#"),
    ("https://www.w3.org/ns/ucm/shapes/", "https://www.w3.org/ns/ucm/shapes/"),
    ("https://www.w3.org/ns/ucm#shapes", "https://www.w3.org/ns/ucm#"),  # a fragment names a term, not a namespace
])
def test_namespace_of_ontology_header(header, namespace):
    assert _namespace_of(header) == namespace


def test_every_constraint_has_its_tier(compilation):
    """ucmsh:tier is read from the shapes namespace; a wrong namespace silently drops every tier"""
    shapes = compilation.ir.shapes
    assert all(c.tier for s in shapes for c in s.properties)
    assert all(q.tier for s in shapes for q in s.sparql)
