"""
Pydantic models for the type-safe intermediate representation (IR)

The IR is the validated, normalized form of the UCM ontology, its SKOS
concept schemes and its SHACL shapes. Everything downstream of
normalization (OpenAPI, SQL and FHIR targets, examples) reads these models,
never the RDF graph.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ============= Shape Vocabulary =============

class Severity(str, Enum):
    """SHACL result severity (sh:Violation, sh:Warning, sh:Info)"""
    VIOLATION = "Violation"
    WARNING = "Warning"
    INFO = "Info"


class Tier(str, Enum):
    """ucmsh:tier from the UCM core shapes convention"""
    DEFINITIONAL = "Definitional"
    RECOMMENDED = "Recommended"


# Severities each tier may report (ucm-core-shapes CONVENTION, ucm-shapes-lint L3/L4)
TIER_SEVERITIES = {
    Tier.DEFINITIONAL: {Severity.VIOLATION},
    Tier.RECOMMENDED: {Severity.WARNING, Severity.INFO},
}


# ============= Ontology Models =============

class OntologyClass(BaseModel):
    """owl:Class declared in the ontology namespace"""
    iri: str
    term: str = Field(description="JSON-LD term and OpenAPI schema name")
    label: str
    comment: Optional[str] = None
    superclasses: List[str] = Field(default_factory=list, description="Direct rdfs:subClassOf")
    equivalent_classes: List[str] = Field(
        default_factory=list, description="owl:equivalentClass IRIs outside the namespace"
    )


class OntologyProperty(BaseModel):
    """owl:ObjectProperty or owl:DatatypeProperty declared in the ontology namespace"""
    iri: str
    term: str
    label: str
    comment: Optional[str] = None
    kind: Literal["object", "datatype"]
    domain: Optional[str] = None
    range: Optional[str] = None
    superproperties: List[str] = Field(default_factory=list)


class Concept(BaseModel):
    """skos:Concept in a concept scheme"""
    iri: str
    term: str
    label: str
    alt_labels: List[str] = Field(default_factory=list)
    definition: Optional[str] = None


class ConceptScheme(BaseModel):
    """skos:ConceptScheme (e.g., LifecycleState)"""
    iri: str
    term: str
    label: str
    description: Optional[str] = None
    concepts: List[Concept] = Field(default_factory=list)


# ============= Shape Models =============

class ShapeConstraint(BaseModel):
    """Tier and severity common to every constraint-carrying shape"""
    iri: Optional[str] = Field(None, description="None for blank-node shapes")
    severity: Severity = Severity.VIOLATION  # SHACL default for untagged shapes
    tier: Optional[Tier] = None
    message: Optional[str] = None

    @model_validator(mode="after")
    def _tier_matches_severity(self) -> "ShapeConstraint":
        if self.tier is not None and self.severity not in TIER_SEVERITIES[self.tier]:
            expected = " or ".join(f"sh:{s.value}" for s in sorted(TIER_SEVERITIES[self.tier]))
            raise ValueError(
                f"Shape {self.iri or '(blank node)'} is tier {self.tier.value} "
                f"but has sh:{self.severity.value}; {self.tier.value} requires {expected}"
            )
        return self


class PropertyConstraint(ShapeConstraint):
    """sh:PropertyShape reduced to what the API surface can express"""
    paths: List[str] = Field(description="Predicate IRIs; several for sh:alternativePath")
    inverse: bool = False
    min_count: Optional[int] = None
    max_count: Optional[int] = None
    node_kind: Optional[str] = None
    datatypes: List[str] = Field(
        default_factory=list, description="sh:datatype, or the branches of sh:or"
    )
    classes: List[str] = Field(default_factory=list, description="sh:class")


class SparqlConstraint(ShapeConstraint):
    """sh:sparql constraint; severity and tier come from the owning node shape"""
    select: str


class NodeShape(ShapeConstraint):
    """sh:NodeShape with its targets and nested constraints"""
    target_classes: List[str] = Field(default_factory=list)
    target_subjects_of: List[str] = Field(default_factory=list)
    target_objects_of: List[str] = Field(default_factory=list)
    node_kind: Optional[str] = None
    properties: List[PropertyConstraint] = Field(default_factory=list)
    sparql: List[SparqlConstraint] = Field(default_factory=list)


# ============= Ontology IR =============

class SourceDigest(BaseModel):
    """URDNA2015 canonical digest of one JSON-LD input"""
    file: str
    digest: str = Field(description="sha256 of the canonical N-Quads: the graph's identity")
    triples: int
    content: Optional[str] = Field(None, description="sha256 of the file bytes: this serialization")


class OntologyIR(BaseModel):
    """Normalized ontology: the contract between ingest and generation"""
    iri: str
    namespace: str
    prefix: str = "ucm"
    label: str
    comment: Optional[str] = None
    version: Optional[str] = None
    sources: List[SourceDigest] = Field(default_factory=list)

    classes: Dict[str, OntologyClass]
    properties: Dict[str, OntologyProperty]
    schemes: Dict[str, ConceptScheme] = Field(default_factory=dict)
    shapes: List[NodeShape] = Field(default_factory=list)
    shapes_namespace: Optional[str] = None
    shapes_prefix: str = "ucmsh"
    prefixes: Dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _terms_are_unique(self) -> "OntologyIR":
        """Every class, property, scheme and concept becomes one JSON-LD term"""
        seen: Dict[str, str] = {prefix: iri for prefix, iri in self.prefixes.items()}
        named = (
            list(self.classes.values())
            + list(self.properties.values())
            + list(self.schemes.values())
            + [c for s in self.schemes.values() for c in s.concepts]
        )
        for item in named:
            if item.term.startswith("@"):
                raise ValueError(f"Term {item.term!r} for {item.iri} collides with a JSON-LD keyword")
            other = seen.get(item.term)
            if other is not None and other != item.iri:
                raise ValueError(
                    f"JSON-LD term {item.term!r} is ambiguous: {other} and {item.iri}"
                )
            seen[item.term] = item.iri
        return self

    # ---------- Class hierarchy ----------

    def ancestors(self, iri: str) -> List[str]:
        """Transitive superclasses, nearest first"""
        result: List[str] = []
        frontier = list(self.classes[iri].superclasses) if iri in self.classes else []
        while frontier:
            current = frontier.pop(0)
            if current in result or current not in self.classes:
                continue
            result.append(current)
            frontier.extend(self.classes[current].superclasses)
        return result

    def descendants(self, iri: str) -> List[str]:
        """Transitive subclasses, sorted by term"""
        result = [c.iri for c in self.classes.values() if iri in self.ancestors(c.iri)]
        return sorted(result, key=lambda i: self.classes[i].term)

    def roots(self) -> List[OntologyClass]:
        """Classes with no superclass inside the ontology"""
        return sorted(
            (c for c in self.classes.values() if not any(s in self.classes for s in c.superclasses)),
            key=lambda c: c.term,
        )

    def root_of(self, iri: str) -> str:
        chain = [iri] + self.ancestors(iri)
        roots = {c.iri for c in self.roots()}
        return next((c for c in reversed(chain) if c in roots), iri)

    # ---------- Properties and constraints ----------

    def declared_properties(self, class_iri: str) -> List[OntologyProperty]:
        """Properties whose rdfs:domain is exactly this class"""
        return sorted(
            (p for p in self.properties.values() if p.domain == class_iri),
            key=lambda p: p.term,
        )

    def domainless_properties(self) -> List[OntologyProperty]:
        """Properties with no rdfs:domain apply to any node"""
        return sorted(
            (p for p in self.properties.values() if p.domain is None), key=lambda p: p.term
        )

    def constraints_for(
        self, property_iri: str, class_iri: Optional[str] = None
    ) -> List[PropertyConstraint]:
        """Property shapes that constrain this property on this class.

        A shape applies when it targets the class itself (subclasses inherit
        through allOf) or targets subjects of the property, which constrains
        the property wherever it appears.
        """
        found: List[PropertyConstraint] = []
        for shape in self.shapes:
            applies = property_iri in shape.target_subjects_of or (
                class_iri is not None and class_iri in shape.target_classes
            )
            if not applies:
                continue
            for constraint in shape.properties:
                if property_iri in constraint.paths and not constraint.inverse:
                    found.append(constraint)
        return found

    def constrained_paths(self, class_iri: str) -> List[str]:
        """Forward paths constrained by shapes that target this class"""
        paths: List[str] = []
        for shape in self.shapes:
            if class_iri in shape.target_classes:
                for constraint in shape.properties:
                    if not constraint.inverse:
                        paths.extend(p for p in constraint.paths if p not in paths)
        return paths

    def shapes_targeting(self, class_iri: str) -> List[NodeShape]:
        return [s for s in self.shapes if class_iri in s.target_classes]

    def value_shapes(self, property_iri: str) -> List[NodeShape]:
        """Node shapes that target the objects of a property"""
        return [s for s in self.shapes if property_iri in s.target_objects_of]

    def term(self, iri: str) -> Optional[str]:
        for table in (self.classes, self.properties, self.schemes):
            if iri in table:
                return table[iri].term  # type: ignore[attr-defined]
        for scheme in self.schemes.values():
            for concept in scheme.concepts:
                if concept.iri == iri:
                    return concept.term
        return None

    def curie(self, iri: str) -> str:
        """Compact an IRI with the known prefixes (shape IRIs included, for messages)"""
        prefixes = dict(self.prefixes)
        if self.shapes_namespace:
            prefixes[self.shapes_prefix] = self.shapes_namespace
        for prefix, namespace in sorted(prefixes.items(), key=lambda kv: -len(kv[1])):
            if iri.startswith(namespace) and len(iri) > len(namespace):
                return f"{prefix}:{iri[len(namespace):]}"
        return iri


# ============= Findings and Validation Reports =============

class LintFinding(BaseModel):
    """Consistency finding about the ontology and shapes (not about data)"""
    code: str
    severity: Severity
    subject: str
    message: str


class ValidationResult(BaseModel):
    """One SHACL validation result"""
    focus_node: str = Field(description="Node the result is about")
    result_path: Optional[str] = Field(None, description="Property path, if any")
    value: Optional[str] = Field(None, description="Offending value node, if any")
    severity: Severity
    tier: Optional[Tier] = None
    message: str
    source_shape: Optional[str] = None


class ValidationReport(BaseModel):
    """SHACL validation report, as returned by write operations"""
    conforms: bool
    results: List[ValidationResult] = Field(default_factory=list)

    def by_severity(self, severity: Severity) -> List[ValidationResult]:
        return [r for r in self.results if r.severity == severity]


# ============= API Profile =============

OperationKind = Literal["list", "create", "read", "replace", "delete"]


class ServerConfig(BaseModel):
    url: str
    description: str


class Reference(BaseModel):
    """Normative or informative document the API conforms to"""
    name: str
    url: str
    note: Optional[str] = None


class ApiProfile(BaseModel):
    """Optional overlay for what the ontology cannot say about an HTTP API"""
    model_config = ConfigDict(populate_by_name=True)

    title: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    context_url: str = Field("./context.jsonld", alias="context-url")
    servers: List[ServerConfig] = Field(
        default_factory=lambda: [
            ServerConfig(url="http://localhost:8000/ucm/v1", description="UCM reference server")
        ]
    )
    exclude: List[str] = Field(default_factory=list, description="Root class terms not exposed")
    scheme_bindings: Dict[str, str] = Field(
        default_factory=dict,
        alias="scheme-bindings",
        description="Property term -> concept scheme term",
    )
    references: List[Reference] = Field(default_factory=list)


# ============= API Models (rendered by templates) =============

class SchemaProperty(BaseModel):
    """One JSON-LD term on a component schema"""
    name: str
    iri: str
    description: Optional[str] = None
    value_schema: Dict[str, Any] = Field(description="JSON Schema for the value")
    required: bool = False
    is_set: bool = Field(False, description="Rendered as an array; context uses @container @set")
    extensions: Dict[str, Any] = Field(default_factory=dict)


class APISchema(BaseModel):
    """Component schema generated from one ontology class"""
    name: str
    iri: str
    curie: str
    description: Optional[str] = None
    parents: List[str] = Field(default_factory=list)
    type_terms: List[str] = Field(description="Allowed @type values: class plus subclasses")
    properties: List[SchemaProperty] = Field(default_factory=list)
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    extensions: Dict[str, Any] = Field(default_factory=dict)

    @property
    def required(self) -> List[str]:
        return [p.name for p in self.properties if p.required]


class ConceptSchemeSchema(BaseModel):
    """Open-vocabulary component schema generated from a SKOS concept scheme"""
    name: str
    iri: str
    description: Optional[str] = None
    terms: List[str]
    concepts: Dict[str, Dict[str, Any]]


class APIOperation(BaseModel):
    """OpenAPI operation generated for a resource"""
    operation_id: str
    kind: OperationKind
    method: Literal["get", "post", "put", "patch", "delete"]
    path: str
    summary: str
    description: str
    tag: str
    request_schema: Optional[str] = None
    response_schema: Optional[str] = None
    success_status: int = 200
    is_collection: bool = False
    validates: bool = Field(False, description="Write validated against the SHACL shapes")


class APIResource(BaseModel):
    """Root ontology class exposed as a collection"""
    name: str
    iri: str
    description: Optional[str] = None
    collection_path: str
    item_path: str
    type_terms: List[str]
    operations: List[APIOperation]


class OpenAPISpec(BaseModel):
    """Everything the OpenAPI and context templates render"""
    title: str
    version: str
    description: str
    context_url: str
    ontology_iri: str
    ontology_version: Optional[str] = None
    sources: List[SourceDigest] = Field(default_factory=list)
    servers: List[ServerConfig]
    references: List[Reference] = Field(default_factory=list)

    base_schema: APISchema
    schemas: List[APISchema]
    concept_schemes: List[ConceptSchemeSchema] = Field(default_factory=list)
    support_schemas: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    resources: List[APIResource]
    context: Dict[str, Any] = Field(description="JSON-LD @context body")

    @property
    def operations(self) -> List[APIOperation]:
        return [op for r in self.resources for op in r.operations]
