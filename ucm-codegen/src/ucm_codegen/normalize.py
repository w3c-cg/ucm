"""
Normalization: RDF graphs → Pydantic IR

Reads the canonical ontology graph (OWL classes and properties, SKOS
concept schemes) and the shapes graph (SHACL node and property shapes)
and builds the OntologyIR. Pydantic validation runs here: a shape whose
ucmsh:tier contradicts its sh:severity, or two IRIs that would map to the
same JSON-LD term, stop the pipeline before anything is generated.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from pydantic import ValidationError
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SH, SKOS
from rdflib.term import Node

from .models import (
    Concept, ConceptScheme, NodeShape, OntologyClass, OntologyIR, OntologyProperty,
    PropertyConstraint, SourceDigest, SparqlConstraint,
)
from .utils import local_name

DEFAULT_SHAPES_NS = "urn:w3c:cg:ucm:shapes#"

# Prefixes carried into the IR (and from there into the JSON-LD context)
STANDARD_PREFIXES = {
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "time": "http://www.w3.org/2006/time#",
}


class NormalizationError(ValueError):
    """The graphs cannot be turned into a valid IR"""

    def __init__(self, errors: Sequence[str]):
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


def _namespace_of(iri: str) -> str:
    return iri if iri.endswith(("#", "/")) else iri + "#"


class Normalizer:
    """Build the OntologyIR from the ontology and shapes graphs"""

    def __init__(
        self,
        ontology: Graph,
        shapes: Graph,
        sources: Iterable[SourceDigest] = (),
    ):
        self.ont = ontology
        self.shapes = shapes
        self.sources = list(sources)
        self.errors: List[str] = []

        self.ontology_iri = self._find_ontology()
        self.namespace = _namespace_of(self.ontology_iri)
        shapes_header = next(
            (s for s in shapes.subjects(RDF.type, OWL.Ontology) if isinstance(s, URIRef)), None
        )
        self.UCMSH = Namespace(_namespace_of(str(shapes_header)) if shapes_header else DEFAULT_SHAPES_NS)
        self.prefix = next(
            (p for p, ns in ontology.namespaces() if str(ns) == self.namespace and p), "ucm"
        )

    # ---------- Helpers ----------

    def _find_ontology(self) -> str:
        """The owl:Ontology whose namespace declares the most classes"""
        headers = [str(s) for s in self.ont.subjects(RDF.type, OWL.Ontology) if isinstance(s, URIRef)]
        if not headers:
            raise NormalizationError(["Ontology graph has no owl:Ontology header"])

        def declared(header: str) -> int:
            ns = _namespace_of(header)
            return sum(1 for c in self.ont.subjects(RDF.type, OWL.Class) if str(c).startswith(ns))

        return max(sorted(headers), key=declared)

    def _in_namespace(self, node: Node) -> bool:
        return isinstance(node, URIRef) and str(node).startswith(self.namespace) and str(node) != self.namespace

    @staticmethod
    def _text(graph: Graph, subject: Node, *predicates: URIRef) -> Optional[str]:
        """First literal for the first predicate that has one; English or untagged preferred"""
        for predicate in predicates:
            literals = [o for o in graph.objects(subject, predicate) if isinstance(o, Literal)]
            if not literals:
                continue
            preferred = [lit for lit in literals if lit.language in (None, "en")] or literals
            return str(sorted(preferred, key=str)[0]).strip()
        return None

    @staticmethod
    def _iris(graph: Graph, subject: Node, predicate: URIRef) -> List[str]:
        return sorted(str(o) for o in graph.objects(subject, predicate) if isinstance(o, URIRef))

    def _build(self, model: type, **fields: object) -> Optional[object]:
        """Construct a Pydantic model, collecting validation errors instead of raising"""
        try:
            return model(**fields)
        except ValidationError as e:
            for err in e.errors():
                self.errors.append(str(err["msg"]).removeprefix("Value error, "))
            return None

    # ---------- Ontology ----------

    def _classes(self) -> Dict[str, OntologyClass]:
        classes: Dict[str, OntologyClass] = {}
        candidates = set(self.ont.subjects(RDF.type, OWL.Class)) | set(self.ont.subjects(RDF.type, RDFS.Class))
        for cls in sorted(filter(self._in_namespace, candidates), key=str):
            equivalents = {
                str(o) for o in self.ont.objects(cls, OWL.equivalentClass) if isinstance(o, URIRef)
            } | {
                str(s) for s in self.ont.subjects(OWL.equivalentClass, cls) if isinstance(s, URIRef)
            }
            term = local_name(str(cls))
            classes[str(cls)] = OntologyClass(
                iri=str(cls),
                term=term,
                label=self._text(self.ont, cls, RDFS.label, SKOS.prefLabel) or term,
                comment=self._text(self.ont, cls, RDFS.comment, SKOS.definition),
                superclasses=self._iris(self.ont, cls, RDFS.subClassOf),
                equivalent_classes=sorted(e for e in equivalents if not e.startswith(self.namespace)),
            )
        return classes

    def _properties(self) -> Dict[str, OntologyProperty]:
        properties: Dict[str, OntologyProperty] = {}
        for kind, owl_type in (("object", OWL.ObjectProperty), ("datatype", OWL.DatatypeProperty)):
            for prop in sorted(filter(self._in_namespace, self.ont.subjects(RDF.type, owl_type)), key=str):
                domains = self._iris(self.ont, prop, RDFS.domain)
                ranges = self._iris(self.ont, prop, RDFS.range)
                term = local_name(str(prop))
                properties[str(prop)] = OntologyProperty(
                    iri=str(prop),
                    term=term,
                    label=self._text(self.ont, prop, RDFS.label, SKOS.prefLabel) or term,
                    comment=self._text(self.ont, prop, RDFS.comment, SKOS.definition),
                    kind=kind,  # type: ignore[arg-type]
                    domain=domains[0] if domains else None,
                    range=ranges[0] if ranges else None,
                    superproperties=self._iris(self.ont, prop, RDFS.subPropertyOf),
                )
        return properties

    def _schemes(self) -> Dict[str, ConceptScheme]:
        schemes: Dict[str, ConceptScheme] = {}
        for scheme in sorted(self.ont.subjects(RDF.type, SKOS.ConceptScheme), key=str):
            if not isinstance(scheme, URIRef):
                continue
            members = (
                set(self.ont.subjects(SKOS.inScheme, scheme))
                | set(self.ont.subjects(SKOS.topConceptOf, scheme))
                | set(self.ont.objects(scheme, SKOS.hasTopConcept))
            )
            concepts = [
                Concept(
                    iri=str(c),
                    term=local_name(str(c)),
                    label=self._text(self.ont, c, SKOS.prefLabel, RDFS.label) or local_name(str(c)),
                    alt_labels=sorted(str(a) for a in self.ont.objects(c, SKOS.altLabel)),
                    definition=self._text(self.ont, c, SKOS.definition, RDFS.comment),
                )
                for c in members if isinstance(c, URIRef)
            ]
            term = local_name(str(scheme))
            schemes[str(scheme)] = ConceptScheme(
                iri=str(scheme),
                term=term,
                label=self._text(self.ont, scheme, SKOS.prefLabel, DCTERMS.title, RDFS.label) or term,
                description=self._text(
                    self.ont, scheme, DCTERMS.description, SKOS.definition, RDFS.comment
                ),
                concepts=sorted(concepts, key=lambda c: c.term),
            )
        return schemes

    # ---------- Shapes ----------

    def _severity_and_tier(self, shape: Node) -> Dict[str, Optional[str]]:
        severity = self.shapes.value(shape, SH.severity)
        tier = self.shapes.value(shape, self.UCMSH.tier)
        return {
            "severity": local_name(str(severity)) if severity is not None else "Violation",
            "tier": local_name(str(tier)) if tier is not None else None,
        }

    def _paths(self, path: Optional[Node]) -> Tuple[List[str], bool]:
        """Predicate IRIs for a sh:path; alternative and inverse paths are expanded"""
        if isinstance(path, URIRef):
            return [str(path)], False
        if isinstance(path, BNode):
            alternatives = self.shapes.value(path, SH.alternativePath)
            if alternatives is not None:
                members = Collection(self.shapes, alternatives)
                return [str(m) for m in members if isinstance(m, URIRef)], False
            inverse = self.shapes.value(path, SH.inversePath)
            if isinstance(inverse, URIRef):
                return [str(inverse)], True
        return [], False

    def _property_shape(self, shape: Node) -> Optional[PropertyConstraint]:
        paths, inverse = self._paths(self.shapes.value(shape, SH.path))
        datatypes = self._iris(self.shapes, shape, SH.datatype)
        for branches in self.shapes.objects(shape, SH["or"]):
            for branch in Collection(self.shapes, branches):
                datatypes.extend(d for d in self._iris(self.shapes, branch, SH.datatype) if d not in datatypes)

        min_count = self.shapes.value(shape, SH.minCount)
        max_count = self.shapes.value(shape, SH.maxCount)
        node_kind = self.shapes.value(shape, SH.nodeKind)
        return self._build(  # type: ignore[return-value]
            PropertyConstraint,
            iri=str(shape) if isinstance(shape, URIRef) else None,
            message=self._text(self.shapes, shape, SH.message),
            paths=paths,
            inverse=inverse,
            min_count=int(min_count) if min_count is not None else None,
            max_count=int(max_count) if max_count is not None else None,
            node_kind=local_name(str(node_kind)) if node_kind is not None else None,
            datatypes=datatypes,
            classes=self._iris(self.shapes, shape, SH["class"]),
            **self._severity_and_tier(shape),
        )

    def _node_shape(self, shape: Node) -> Optional[NodeShape]:
        level = self._severity_and_tier(shape)
        properties = [
            c for c in (self._property_shape(p) for p in self.shapes.objects(shape, SH.property)) if c
        ]
        sparql = [
            self._build(
                SparqlConstraint,
                iri=str(shape) if isinstance(shape, URIRef) else None,
                message=self._text(self.shapes, q, SH.message),
                select=str(select),
                **level,
            )
            for q in self.shapes.objects(shape, SH.sparql)
            for select in self.shapes.objects(q, SH.select)
        ]
        node_kind = self.shapes.value(shape, SH.nodeKind)
        return self._build(  # type: ignore[return-value]
            NodeShape,
            iri=str(shape) if isinstance(shape, URIRef) else None,
            message=self._text(self.shapes, shape, SH.message),
            target_classes=self._iris(self.shapes, shape, SH.targetClass),
            target_subjects_of=self._iris(self.shapes, shape, SH.targetSubjectsOf),
            target_objects_of=self._iris(self.shapes, shape, SH.targetObjectsOf),
            node_kind=local_name(str(node_kind)) if node_kind is not None else None,
            properties=sorted(properties, key=lambda c: (c.paths, c.iri or "", c.message or "")),
            sparql=sorted((q for q in sparql if q), key=lambda q: q.message or ""),
            **level,
        )

    def _node_shapes(self) -> List[NodeShape]:
        """sh:NodeShape instances, plus untyped subjects of a SHACL target"""
        candidates = set(self.shapes.subjects(RDF.type, SH.NodeShape))
        for target in (SH.targetClass, SH.targetSubjectsOf, SH.targetObjectsOf, SH.targetNode):
            candidates |= set(self.shapes.subjects(target, None))
        candidates = {c for c in candidates if self.shapes.value(c, SH.path) is None}
        shapes = [self._node_shape(c) for c in sorted(candidates, key=str)]
        return [s for s in shapes if s]

    # ---------- IR ----------

    def to_ir(self) -> OntologyIR:
        header = URIRef(self.ontology_iri)
        classes = self._classes()
        properties = self._properties()
        schemes = self._schemes()
        shapes = self._node_shapes()
        if self.errors:
            raise NormalizationError(list(dict.fromkeys(self.errors)))

        try:
            return OntologyIR(
                iri=self.ontology_iri,
                namespace=self.namespace,
                prefix=self.prefix,
                label=self._text(self.ont, header, RDFS.label, DCTERMS.title) or local_name(self.ontology_iri),
                comment=self._text(self.ont, header, RDFS.comment, DCTERMS.description),
                version=self._text(self.ont, header, OWL.versionInfo),
                sources=self.sources,
                classes=classes,
                properties=properties,
                schemes=schemes,
                shapes=shapes,
                shapes_namespace=str(self.UCMSH),
                shapes_prefix=next(
                    (p for p, ns in self.shapes.namespaces() if str(ns) == str(self.UCMSH) and p),
                    "ucmsh",
                ),
                prefixes={self.prefix: self.namespace, **STANDARD_PREFIXES},
            )
        except ValidationError as e:
            raise NormalizationError(
                [str(err["msg"]).removeprefix("Value error, ") for err in e.errors()]
            ) from e
