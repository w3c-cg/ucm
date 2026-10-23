"""Test the UCM core shapes.

  1. Baseline example conforms with zero results (warnings included).
  2. Extension: adopters' own predicates and types add no results.
  3. Seeded defects: each produces exactly its expected results, nothing else.
  4. Inference: type constraints behave differently with and without it.
  5. Closure: what sh:closed would do to the same extension data.
  6. Lint: the shapes file obeys its own convention, and mutations are caught.
  7. Meta-validation: both shapes files are valid SHACL (SHACL-for-SHACL).

Usage: python3 test_core_shapes.py <dir>
<dir> must hold unified-care-model.ttl, ucm-lifecycle-vocabularies.ttl
(in the urn:w3c:cg:ucm# namespace), ucm-core-shapes.ttl,
ucm-core-shapes-example.ttl and ucm-shapes-lint.ttl.
"""
import sys
from rdflib import Graph, BNode, Literal, URIRef
from rdflib.namespace import RDF, SH
from pyshacl import validate

D = sys.argv[1] if len(sys.argv) > 1 else "."
PFX = """
@prefix ucm:  <urn:w3c:cg:ucm#> .
@prefix ex:   <http://example.org/ucm/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix time: <http://www.w3.org/2006/time#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix fhir: <http://hl7.org/fhir/> .
@prefix hmis: <http://example.org/hmis#> .
@prefix cco:  <https://www.commoncoreontologies.org/AgentOntology#> .
"""

def shapes_graph(mutate=None):
    s = Graph(); s.parse(f"{D}/ucm-core-shapes.ttl", format="turtle")
    if mutate:
        s.parse(data=PFX + "@prefix sh: <http://www.w3.org/ns/shacl#> . @prefix ucmsh: <urn:w3c:cg:ucm:shapes#> .\n" + mutate, format="turtle")
    return s

def data_graph(extra=""):
    g = Graph()
    for f in ["unified-care-model.ttl", "ucm-lifecycle-vocabularies.ttl", "ucm-core-shapes-example.ttl"]:
        g.parse(f"{D}/{f}", format="turtle")
    if extra:
        g.parse(data=PFX + extra, format="turtle")
    return g

def name(node, s):
    if isinstance(node, BNode):
        parent = s.value(None, SH.property, node)
        path = s.value(node, SH.path)
        p = str(parent).split("#")[-1] if parent else "?"
        return f"{p}/{str(path).split('#')[-1] if path else '?'}"
    return str(node).split("#")[-1]

def results(g, s=None, inference="none"):
    s = s or shapes_graph()
    _, rep, _ = validate(g, shacl_graph=s, inference=inference, advanced=True)
    out = set()
    for r in rep.subjects(RDF.type, SH.ValidationResult):
        f = rep.value(r, SH.focusNode)
        fname = str(f) if isinstance(f, Literal) else str(f).rstrip("/").rsplit("/", 1)[-1]
        out.add((str(rep.value(r, SH.resultSeverity)).split("#")[-1],
                 name(rep.value(r, SH.sourceShape), s), fname))
    return out

def hdr(t): print("\n" + "=" * 70 + "\n" + t + "\n" + "=" * 70)
V, W = "Violation", "Warning"
failures = 0

# ------------------------------------------------------------------ 1
hdr("1. BASELINE")
base = results(data_graph())
print(f"   results on conformant example: {len(base)}", sorted(base) if base else "")
failures += bool(base)

# ------------------------------------------------------------------ 2
EXTENSION = """
ex:p-res     hmis:projectType 13 ; prov:wasDerivedFrom ex:hmis-enrollment-88 .
ex:assess-1  a hmis:CoordinatedEntryAssessment ; hmis:assessmentLevel "Housing Needs" .
ex:enc-1     a fhir:Encounter ; fhir:Encounter.class "AMB" .
ex:person-a  hmis:personalId "P-001" .
ex:stmt-1    prov:wasAttributedTo ex:cm-1 .
ex:req-2     a ucm:CoordinationRequest ; ucm:hasActivityFocus ex:focus-1 ;
             ucm:hasLifecycleState hmis:Referred ; hmis:referralSource "CES" .
hmis:Referred a skos:Concept ; skos:inScheme hmis:ReferralStatus ; skos:exactMatch ucm:Pending .
ex:partner-cm a cco:ont00001262 .                     # typed only in CCO
ex:p-partner a ucm:Participation ; ucm:participatingEntity ex:partner-cm ;
             ucm:occursWithin ex:req-2 ; ucm:assumesRole ex:role-coord2 ;
             hmis:sourceSystem "Partner HMIS" .
ex:role-coord2 a ucm:CoordinatorRole .
"""
hdr("2. EXTENSION  adopter predicates, types, local vocabulary")
ext_none = results(data_graph(EXTENSION)) - base
print(f"   new results, no inference: {sorted(ext_none)}")
expected = {(W, "Participation-entityType", "p-partner")}
ok = ext_none == expected
print(f"   only the CCO-typed participant is flagged, as a Warning: {'PASS' if ok else 'FAIL'}")
failures += not ok
ext_owl = results(data_graph(EXTENSION), inference="owlrl")
print(f"   results with OWL RL inference (baseline + extension): {sorted(ext_owl) or 'none'}")
failures += bool(ext_owl)

# ------------------------------------------------------------------ 3
CASES = [
 ("D01 two participating entities",
  "ex:p-x a ucm:Participation ; ucm:participatingEntity ex:cm-1, ex:org-ecm ; ucm:occursWithin ex:req-1 .",
  {(V, "Participation-entity", "p-x")}),
 ("D02 participation with no process",
  "ex:p-x a ucm:Participation ; ucm:participatingEntity ex:cm-1 .",
  {(V, "Participation-process", "p-x")}),
 ("D03 literal as participating entity",
  'ex:p-x a ucm:Participation ; ucm:participatingEntity "Jane Doe" ; ucm:occursWithin ex:req-1 .',
  {(V, "Participation-entity", "p-x"), (W, "Participation-entityType", "p-x")}),
 ("D04 process claims a participation that occurs elsewhere",
  "ex:req-1 ucm:hasParticipant ex:p-res .",
  {(V, "ParticipationProcessConsistencyShape", "p-res")}),
 ("D05 entity claims a participation naming someone else",
  "ex:cm-1 ucm:participatesThrough ex:p-res .",
  {(V, "ParticipationEntityConsistencyShape", "p-res")}),
 ("D06 validTo before validFrom",
  'ex:p-x a ucm:Participation ; ucm:participatingEntity ex:cm-1 ; ucm:occursWithin ex:req-1 ; '
  'ucm:validFrom "2026-10-01T00:00:00Z"^^xsd:dateTimeStamp ; ucm:validTo "2026-09-01T00:00:00Z"^^xsd:dateTimeStamp .',
  {(V, "ParticipationValidityShape", "p-x")}),
 ("D07 both temporal encodings on one participation",
  "ex:p-cm ucm:enactiveDuring ex:t-assess .",
  {(W, "DualTemporalEncodingShape", "p-cm")}),
 ("D08 membership in two groups",
  "ex:mem-a ucm:membershipIn ex:hh-002 . ex:hh-002 a ucm:Household .",
  {(V, "Membership-group", "mem-a")}),
 ("D09 membership with no member",
  "ex:mem-x a ucm:Membership ; ucm:membershipIn ex:hh-001 .",
  {(V, "Membership-member", "mem-x")}),
 ("D10 handshake that negotiates nothing",
  "ex:hs-x a ucm:Handshake .",
  {(V, "Handshake-negotiates", "hs-x"), (W, "CoordinativeActivityShape", "hs-x")}),
 ("D11 handshake cycle",
  "ex:hs-a a ucm:Handshake ; ucm:negotiates ex:hs-b . ex:hs-b a ucm:Handshake ; ucm:negotiates ex:hs-a .",
  {(V, "HandshakeAcyclicShape", "hs-a"), (V, "HandshakeAcyclicShape", "hs-b"),
   (W, "CoordinativeActivityShape", "hs-a"), (W, "CoordinativeActivityShape", "hs-b")}),
 ("D12 two lifecycle states",
  "ex:req-1 ucm:hasLifecycleState ucm:Pending .",
  {(V, "LifecycleState-single", "req-1")}),
 ("D13 lifecycle state as a literal",
  'ex:req-x a ucm:CoordinationRequest ; ucm:hasActivityFocus ex:focus-1 ; ucm:hasLifecycleState "pending" .',
  {(V, "LifecycleState-single", "req-x"), (W, "LifecycleState-anchored", "req-x")}),
 ("D14 local state concept, unmapped",
  "ex:req-x a ucm:CoordinationRequest ; ucm:hasActivityFocus ex:focus-1 ; ucm:hasLifecycleState ex:OnHold . "
  "ex:OnHold a skos:Concept ; skos:inScheme ex:LocalStates .",
  {(W, "LifecycleState-anchored", "req-x")}),
 ("D15 projection with no backing participation",
  "ex:sci-1 a ucm:SocialCareInteraction ; ucm:hasClient ex:person-a .",
  {(W, "ProjectionBackingShape", "sci-1")}),
 ("D16 coordination request with no focus",
  "ex:req-x a ucm:CoordinationRequest .",
  {(W, "CoordinativeActivityShape", "req-x")}),
 ("D17 statement with two dates",
  'ex:stmt-1 ucm:statementDate "2026-09-04T09:00:00-07:00"^^xsd:dateTime .',
  {(V, "Statement-date", "stmt-1")}),
 ("D18 statement with no context",
  'ex:stmt-x a ucm:ObservationStatement ; ucm:statementDate "2026-09-04T09:00:00-07:00"^^xsd:dateTime .',
  {(W, "Statement-context", "stmt-x")}),
 ("D19 temporal context as a bare literal",
  'ex:enc-1 ucm:occursDuring "2026-09-05"^^xsd:date .',
  {(V, "TemporalEntityShape", "2026-09-05")}),
 ("D20 interval that ends before it begins",
  "ex:enc-1 ucm:occursDuring ex:t-bad . ex:t-bad a time:ProperInterval ; "
  'time:hasBeginning [ time:inXSDDateTimeStamp "2026-09-05T12:00:00-07:00"^^xsd:dateTimeStamp ] ; '
  'time:hasEnd [ time:inXSDDateTimeStamp "2026-09-05T11:00:00-07:00"^^xsd:dateTimeStamp ] .',
  {(V, "TemporalOrderShape", "t-bad")}),
 ("D21 statement date as free text",
  'ex:stmt-y a ucm:SocialCareStatement ; ucm:madeWithinContext ex:ctx-housing ; ucm:statementDate "last Tuesday" .',
  {(V, "Statement-date", "stmt-y")}),
 # ---- controls: must stay silent ----
 ("N01 handshake chain grounded in a focused process",
  "ex:hs-c a ucm:Handshake ; ucm:negotiates ex:hs-1 .",
  set()),
 ("N02 local state concept mapped with skos:exactMatch",
  "ex:req-x a ucm:CoordinationRequest ; ucm:hasActivityFocus ex:focus-1 ; ucm:hasLifecycleState ex:Queued . "
  "ex:Queued a skos:Concept ; skos:inScheme ex:LocalStates ; skos:exactMatch ucm:Pending .",
  set()),
 ("N03 projection backed by a subclass of the role",
  "ex:sci-1 a ucm:SocialCareInteraction ; ucm:hasClient ex:person-a ; ucm:hasParticipant ex:p-cli . "
  "ex:p-cli a ucm:Participation ; ucm:participatingEntity ex:person-a ; ucm:occursWithin ex:sci-1 ; "
  "ucm:assumesRole ex:r-intake . ex:r-intake a ex:IntakeClientRole . ex:IntakeClientRole rdfs:subClassOf ucm:ClientRole .",
  set()),
 ("N04 dateTimeStamp validity, correctly ordered",
  'ex:p-x a ucm:Participation ; ucm:participatingEntity ex:cm-1 ; ucm:occursWithin ex:req-1 ; '
  'ucm:validFrom "2026-09-01T00:00:00Z"^^xsd:dateTimeStamp ; ucm:validTo "2026-10-01T00:00:00Z"^^xsd:dateTimeStamp .',
  set()),
]
hdr(f"3. SEEDED DEFECTS AND CONTROLS  ({len(CASES)} cases)")
for label, ttl, exp in CASES:
    got = results(data_graph(ttl)) - base
    ok = got == exp
    failures += not ok
    print(f"   {'PASS' if ok else 'FAIL'}  {label}")
    if not ok:
        print(f"         expected {sorted(exp)}\n         got      {sorted(got)}")

# ------------------------------------------------------------------ 4
hdr("4. INFERENCE  an untyped participant")
UNTYPED = "ex:p-u a ucm:Participation ; ucm:participatingEntity ex:someone ; ucm:occursWithin ex:req-1 ."
for inf in ["none", "rdfs"]:
    got = results(data_graph(UNTYPED), inference=inf) - results(data_graph(), inference=inf)
    print(f"   inference={inf:5}  {sorted(got) or 'no results'}")

# ------------------------------------------------------------------ 5
hdr("5. CLOSURE  ParticipationShape with sh:closed true, same extension data")
CLOSE = "ucmsh:ParticipationShape sh:closed true ; sh:ignoredProperties ( <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ) ."
closed = results(data_graph(EXTENSION), s=shapes_graph(CLOSE)) - results(data_graph(EXTENSION))
s_closed = shapes_graph(CLOSE)
_, rep, _ = validate(data_graph(EXTENSION), shacl_graph=s_closed, advanced=True)
preds = sorted({str(rep.value(r, SH.resultPath)) for r in rep.subjects(RDF.type, SH.ValidationResult)
                if rep.value(r, SH.sourceConstraintComponent) == SH.ClosedConstraintComponent})
print(f"   new Violations: {len(closed)} focus nodes")
for p in preds:
    tag = "UCM's OWN" if p.startswith("urn:w3c:cg:ucm#") else "adopter "
    print(f"     {tag}  {p}")

# ------------------------------------------------------------------ 6
hdr("6. LINT  the shapes file against its own convention")
lint = Graph(); lint.parse(f"{D}/ucm-shapes-lint.ttl", format="turtle")
def lint_results(sg):
    _, rep, _ = validate(sg, shacl_graph=lint, advanced=True)
    return sorted({(name(rep.value(r, SH.sourceShape), lint), name(rep.value(r, SH.focusNode), sg))
                   for r in rep.subjects(RDF.type, SH.ValidationResult)})
clean = lint_results(shapes_graph())
print(f"   current shapes file: {clean or 'clean'}")
failures += bool(clean)
MUTATION = (CLOSE + "\n"
            "ucmsh:NewShape a sh:NodeShape ; sh:targetClass ucm:Person ; "
            "sh:property [ sh:path ucm:affiliatedWith ; sh:minCount 1 ] .\n")
mutated = shapes_graph(MUTATION)
mutated.remove((URIRef("urn:w3c:cg:ucm:shapes#Participation-entityType"), SH.severity, None))
print("   mutated (closed w/o rationale; untiered new shape; Recommended shape missing severity):")
for r in lint_results(mutated):
    print("     ", r)

hdr("7. META-VALIDATION  SHACL-for-SHACL")
from pyshacl.errors import ReportableRuntimeError
for label, sg in [("ucm-core-shapes.ttl", shapes_graph()), ("ucm-shapes-lint.ttl", lint)]:
    try:
        validate(data_graph(), shacl_graph=sg, advanced=True, meta_shacl=True)
        print(f"   {label}: valid")
    except ReportableRuntimeError as e:
        failures += 1
        print(f"   {label}: FAILED  {str(e).splitlines()[0]}")

hdr(f"SUMMARY  {'ALL PASS' if failures == 0 else f'{failures} FAILURE(S)'}")
