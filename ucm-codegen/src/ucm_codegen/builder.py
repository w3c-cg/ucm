"""
API surface mapping: IR → OpenAPISpec

The rules that turn the ontology into an API reference:

  root class (no superclass)     resource: /{plural} (list, create),
                                 /{plural}/{id} (read, replace, delete)
  class                          component schema; rdfs:subClassOf → allOf;
                                 @type enumerates the class and its subclasses
  property                       defined once, on its rdfs:domain (UcmNode if none)
  object property                NodeRef: IRI string or embedded node object
  property bound to a scheme     open enum of concept terms (any IRI also allowed)
  datatype property              JSON Schema type/format from sh:datatype or rdfs:range
  sh:maxCount 1 (Violation)      single value; otherwise array + @container @set
  sh:minCount >= 1 (Violation)   required; Recommended minCount → x-ucm-recommended
  sh:class, sh:sparql, messages  x-ucm-range / x-ucm-constraints, enforced at runtime
                                 by validating writes against the shapes (422)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import (
    APIOperation, APIResource, APISchema, ApiProfile, ConceptScheme, ConceptSchemeSchema,
    OntologyClass, OntologyIR, OntologyProperty, OpenAPISpec, PropertyConstraint, SchemaProperty,
    Severity, ValidationReport,
)
from .utils import article, collection_segment, local_name, pascal

XSD = "http://www.w3.org/2001/XMLSchema#"
SKOS_CONCEPT = "http://www.w3.org/2004/02/skos/core#Concept"
BASE_SCHEMA = "UcmNode"

XSD_JSON_SCHEMA: Dict[str, Dict[str, Any]] = {
    XSD + "string": {"type": "string"},
    XSD + "normalizedString": {"type": "string"},
    XSD + "token": {"type": "string"},
    XSD + "language": {"type": "string"},
    XSD + "anyURI": {"type": "string", "format": "uri"},
    XSD + "boolean": {"type": "boolean"},
    XSD + "decimal": {"type": "number"},
    XSD + "double": {"type": "number"},
    XSD + "float": {"type": "number"},
    XSD + "integer": {"type": "integer"},
    XSD + "int": {"type": "integer"},
    XSD + "long": {"type": "integer"},
    XSD + "nonNegativeInteger": {"type": "integer", "minimum": 0},
    XSD + "positiveInteger": {"type": "integer", "minimum": 1},
    XSD + "dateTime": {"type": "string", "format": "date-time"},
    XSD + "dateTimeStamp": {"type": "string", "format": "date-time"},
    XSD + "date": {"type": "string", "format": "date"},
    XSD + "time": {"type": "string", "format": "time"},
    XSD + "duration": {"type": "string", "format": "duration"},
    XSD + "gYear": {"type": "string", "pattern": r"^-?\d{4,}(Z|[+-]\d{2}:\d{2})?$"},
}

SUPPORT_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "IRI": {
        "type": "string",
        "format": "iri",
        "description": "Absolute IRI, or a term or compact IRI defined by the JSON-LD context.",
    },
    "NodeObject": {
        "type": "object",
        "description": "Embedded JSON-LD node (e.g., an OWL-Time interval). Open: any predicates.",
        "properties": {
            "@id": {"$ref": "#/components/schemas/IRI"},
            "@type": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}},
                ]
            },
        },
    },
    "NodeRef": {
        "description": "Reference to another node by IRI, or the node embedded inline.",
        "oneOf": [
            {"$ref": "#/components/schemas/IRI"},
            {"$ref": "#/components/schemas/NodeObject"},
        ],
    },
    "JsonLdContext": {
        "description": "JSON-LD @context: the published UCM context URL, an inline context, or both.",
        "oneOf": [
            {"type": "string", "format": "uri-reference"},
            {"type": "object"},
            {"type": "array", "items": {"oneOf": [{"type": "string"}, {"type": "object"}]}},
        ],
    },
    "Problem": {
        "type": "object",
        "description": "RFC 9457 problem details.",
        "properties": {
            "type": {"type": "string", "format": "uri-reference"},
            "title": {"type": "string"},
            "status": {"type": "integer"},
            "detail": {"type": "string"},
            "instance": {"type": "string", "format": "uri-reference"},
        },
    },
}


class SpecBuildError(ValueError):
    pass


class SpecBuilder:
    """Map the OntologyIR onto resources, schemas and a JSON-LD context"""

    def __init__(self, ir: OntologyIR, profile: Optional[ApiProfile] = None):
        self.ir = ir
        self.profile = profile or ApiProfile()
        self.schemes_by_term = {s.term: s for s in ir.schemes.values()}

    # ---------- Property placement and cardinality ----------

    def home(self, path: str) -> Optional[str]:
        """Class whose schema defines the property; None means the UcmNode base"""
        prop = self.ir.properties.get(path)
        if prop is not None:
            return prop.domain if prop.domain in self.ir.classes else None
        # Undeclared path constrained by a shape: define it on the topmost target class
        targets = [
            cls for shape in self.ir.shapes for cls in shape.target_classes
            if any(path in c.paths and not c.inverse for c in shape.properties) and cls in self.ir.classes
        ]
        return min(targets, key=lambda c: len(self.ir.ancestors(c))) if targets else None

    def all_constraints(self, path: str) -> List[PropertyConstraint]:
        return [
            c for shape in self.ir.shapes for c in shape.properties
            if path in c.paths and not c.inverse
        ]

    def is_single(self, path: str) -> bool:
        """One JSON value: some Definitional shape says sh:maxCount 1"""
        return any(
            c.max_count == 1 and c.severity == Severity.VIOLATION for c in self.all_constraints(path)
        )

    def scheme_for(self, prop: Optional[OntologyProperty]) -> Optional[ConceptScheme]:
        """Profile binding, else the hasX → X convention for skos:Concept ranges"""
        if prop is None:
            return None
        bound = self.profile.scheme_bindings.get(prop.term)
        if bound:
            if bound not in self.schemes_by_term:
                raise SpecBuildError(f"scheme-bindings: {prop.term} → unknown scheme {bound}")
            return self.schemes_by_term[bound]
        if prop.range == SKOS_CONCEPT and prop.term.startswith("has"):
            return self.schemes_by_term.get(prop.term[3:])
        return None

    def curie_list(self, iris: List[str]) -> Any:
        curies = [self.ir.curie(i) for i in iris]
        return curies[0] if len(curies) == 1 else curies

    # ---------- Schemas ----------

    def value_schema(
        self, path: str, constraints: List[PropertyConstraint]
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        prop = self.ir.properties.get(path)
        datatypes = list(dict.fromkeys(d for c in constraints for d in c.datatypes))
        node_kinds = [c.node_kind for c in constraints if c.node_kind] + [
            s.node_kind for s in self.ir.value_shapes(path) if s.node_kind
        ]
        extensions: Dict[str, Any] = {}

        if (prop is not None and prop.kind == "datatype") or datatypes or "Literal" in node_kinds:
            candidates = datatypes or ([prop.range] if prop is not None and prop.range else [])
            schemas: List[Dict[str, Any]] = []
            for datatype in candidates:
                schema = XSD_JSON_SCHEMA.get(datatype, {"type": "string"})
                if schema not in schemas:
                    schemas.append(schema)
            value = schemas[0] if len(schemas) == 1 else ({"anyOf": schemas} if schemas else {"type": "string"})
            if candidates:
                extensions["x-ucm-datatype"] = self.curie_list(candidates)
            return dict(value), extensions

        scheme = self.scheme_for(prop)
        if scheme is not None:
            value = {"$ref": f"#/components/schemas/{scheme.term}"}
            extensions["x-ucm-concept-scheme"] = scheme.term
        elif "IRI" in node_kinds:
            value = {"$ref": "#/components/schemas/IRI"}
        else:
            value = {"$ref": "#/components/schemas/NodeRef"}

        ranges = ([prop.range] if prop is not None and prop.range else []) + [
            cls for c in constraints for cls in c.classes
        ]
        ranges = list(dict.fromkeys(ranges))
        if ranges:
            extensions["x-ucm-range"] = self.curie_list(ranges)
        return value, extensions

    def schema_property(self, path: str, class_iri: Optional[str]) -> SchemaProperty:
        prop = self.ir.properties.get(path)
        constraints = self.ir.constraints_for(path, class_iri)
        hard = [c for c in constraints if c.severity == Severity.VIOLATION]
        min_count = max((c.min_count or 0 for c in hard), default=0)
        single = self.is_single(path)

        value, extensions = self.value_schema(path, constraints)
        if single:
            schema = value
        else:
            schema = {"type": "array", "items": value, "uniqueItems": True}
            if min_count:
                schema["minItems"] = min_count

        extensions = {"x-semantic-uri": path, **extensions}
        if prop is not None and prop.superproperties:
            extensions["x-ucm-subproperty-of"] = self.curie_list(prop.superproperties)
        if any((c.min_count or 0) >= 1 for c in constraints if c.severity != Severity.VIOLATION):
            extensions["x-ucm-recommended"] = True

        messages: List[Dict[str, str]] = []
        documented = [(c.severity, c.tier, c.message) for c in constraints]
        for shape in self.ir.value_shapes(path):
            documented.append((shape.severity, shape.tier, shape.message))
            documented.extend((q.severity, q.tier, q.message) for q in shape.sparql)
        for severity, tier, message in documented:
            entry = {"severity": severity.value, **({"tier": tier.value} if tier else {}), "message": message}
            if message and entry not in messages:
                messages.append(entry)  # type: ignore[arg-type]
        if messages:
            extensions["x-ucm-constraints"] = messages

        return SchemaProperty(
            name=prop.term if prop is not None else local_name(path),
            iri=path,
            description=(prop.comment or prop.label) if prop is not None else None,
            value_schema=schema,
            required=min_count >= 1,
            is_set=not single,
            extensions=extensions,
        )

    def node_constraints(self, class_iri: str) -> List[Dict[str, str]]:
        """Class-level constraints the property list cannot show (SPARQL, inverse paths)"""
        documented: List[Dict[str, str]] = []
        for shape in self.ir.shapes_targeting(class_iri):
            items = [(shape.severity, shape.tier, shape.message)] if shape.node_kind else []
            items += [(q.severity, q.tier, q.message) for q in shape.sparql]
            items += [(c.severity, c.tier, c.message) for c in shape.properties if c.inverse]
            for severity, tier, message in items:
                entry = {"severity": severity.value, **({"tier": tier.value} if tier else {}), "message": message}
                if message and entry not in documented:
                    documented.append(entry)  # type: ignore[arg-type]
        return documented

    def class_schema(self, cls: OntologyClass) -> APISchema:
        parents = [self.ir.classes[s].term for s in cls.superclasses if s in self.ir.classes]
        type_terms = [cls.term] + [self.ir.classes[d].term for d in self.ir.descendants(cls.iri)]

        paths = [p.iri for p in self.ir.declared_properties(cls.iri)]
        paths += [
            p for p in self.ir.constrained_paths(cls.iri)
            if p not in paths and p not in self.ir.properties and self.home(p) == cls.iri
        ]
        properties = [
            SchemaProperty(
                name="@type",
                iri="@type",
                description="Class of the node: this class or one of its subclasses.",
                value_schema={"type": "string", "enum": type_terms},
                required=True,
            )
        ] + sorted((self.schema_property(p, cls.iri) for p in paths), key=lambda p: p.name)

        extensions: Dict[str, Any] = {}
        direct = sorted(c.term for c in self.ir.classes.values() if cls.iri in c.superclasses)
        if direct:
            extensions["x-ucm-subclasses"] = direct
        if cls.equivalent_classes:
            extensions["x-ucm-equivalent-classes"] = cls.equivalent_classes
        inherited_required = [
            self.ir.properties[p].term if p in self.ir.properties else local_name(p)
            for p in self.ir.constrained_paths(cls.iri)
            if p not in paths
            and any(
                (c.min_count or 0) >= 1 and c.severity == Severity.VIOLATION
                for c in self.ir.constraints_for(p, cls.iri)
            )
        ]
        if inherited_required:
            extensions["x-ucm-inherited-required"] = inherited_required
        constraints = self.node_constraints(cls.iri)
        if constraints:
            extensions["x-ucm-constraints"] = constraints

        return APISchema(
            name=cls.term,
            iri=cls.iri,
            curie=self.ir.curie(cls.iri),
            description=cls.comment or cls.label,
            parents=parents or [BASE_SCHEMA],
            type_terms=type_terms,
            properties=properties,
            extensions=extensions,
        )

    def base_schema(self) -> APISchema:
        keywords = [
            SchemaProperty(
                name="@context",
                iri="@context",
                description="JSON-LD context. Top-level nodes carry the UCM context URL.",
                value_schema={"$ref": "#/components/schemas/JsonLdContext"},
            ),
            SchemaProperty(
                name="@id",
                iri="@id",
                description="IRI of the node. Assigned by the server on create if absent.",
                value_schema={"$ref": "#/components/schemas/IRI"},
            ),
            SchemaProperty(
                name="@type",
                iri="@type",
                description="Class of the node, as a context term.",
                value_schema={"type": "string"},
            ),
        ]
        homeless = [
            p for p in self.ir.properties
            if self.home(p) is None
        ]
        properties = keywords + sorted(
            (self.schema_property(p, None) for p in homeless), key=lambda p: p.name
        )
        return APISchema(
            name=BASE_SCHEMA,
            iri=self.ir.iri,
            curie="",
            description=(
                "Any node in a UCM graph, as a JSON-LD node object. Open by default: "
                "predicates outside UCM (FHIR, local dictionaries, provenance) are allowed, "
                "matching the open-world convention of the UCM shapes."
            ),
            type_terms=[],
            properties=properties,
        )

    def scheme_schema(self, scheme: ConceptScheme) -> ConceptSchemeSchema:
        return ConceptSchemeSchema(
            name=scheme.term,
            iri=scheme.iri,
            description=(
                f"{scheme.label}. {scheme.description or ''} Open vocabulary: known concepts are "
                f"listed; other concept IRIs are accepted when SKOS-mapped into the scheme."
            ).replace("  ", " ").strip(),
            terms=[c.term for c in scheme.concepts],
            concepts={
                c.term: {
                    "iri": c.iri,
                    "label": c.label,
                    **({"definition": c.definition} if c.definition else {}),
                }
                for c in scheme.concepts
            },
        )

    def support_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Static helpers plus ValidationReport, generated from the Pydantic model"""
        support = {name: dict(body) for name, body in SUPPORT_SCHEMAS.items()}
        report = ValidationReport.model_json_schema(ref_template="#/components/schemas/{model}")
        defs = report.pop("$defs", {})
        support.update(defs)
        support["ValidationReport"] = report
        clashes = sorted(set(support) & ({c.term for c in self.ir.classes.values()} | {BASE_SCHEMA}))
        if clashes:
            raise SpecBuildError(f"Support schema names collide with ontology classes: {clashes}")
        return support

    # ---------- Resources ----------

    def resource(self, root: OntologyClass) -> APIResource:
        segment = collection_segment(root.term)
        plural = pascal(segment)
        collection, item = f"/{segment}", f"/{segment}/{{id}}"
        type_terms = [root.term] + [self.ir.classes[d].term for d in self.ir.descendants(root.iri)]
        a = article(root.label)
        subtypes = ", ".join(type_terms[1:])
        typed = f" Subclasses: {subtypes}." if subtypes else ""

        def op(kind: str, method: str, path: str, summary: str, description: str, **kw: Any) -> APIOperation:
            return APIOperation(
                operation_id=kw.pop("operation_id"),
                kind=kind,  # type: ignore[arg-type]
                method=method,  # type: ignore[arg-type]
                path=path,
                summary=summary,
                description=description,
                tag=root.term,
                **kw,
            )

        validated = (
            " The request graph is validated against the UCM core shapes: Definitional "
            "(sh:Violation) results reject it with 422."
        )
        operations = [
            op("list", "get", collection, f"List {root.label} nodes",
               f"Returns {root.label} nodes as a JSON-LD @graph.{typed}",
               operation_id=f"list{plural}", response_schema=root.term, is_collection=True),
            op("create", "post", collection, f"Create {a} {root.label}",
               f"Create {a} {root.label} or subclass node.{validated}",
               operation_id=f"create{root.term}", request_schema=root.term,
               response_schema=root.term, success_status=201, validates=True),
            op("read", "get", item, f"Get {a} {root.label}", f"Fetch one {root.label} node.",
               operation_id=f"get{root.term}", response_schema=root.term),
            op("replace", "put", item, f"Replace {a} {root.label}",
               f"Replace the node's description.{validated}",
               operation_id=f"replace{root.term}", request_schema=root.term,
               response_schema=root.term, validates=True),
            op("delete", "delete", item, f"Delete {a} {root.label}", f"Delete one {root.label} node.",
               operation_id=f"delete{root.term}", success_status=204),
        ]
        return APIResource(
            name=root.term,
            iri=root.iri,
            description=root.comment or root.label,
            collection_path=collection,
            item_path=item,
            type_terms=type_terms,
            operations=operations,
        )

    def resource_roots(self) -> List[OntologyClass]:
        return [r for r in self.ir.roots() if r.term not in self.profile.exclude]

    # ---------- JSON-LD context ----------

    def context(self) -> Dict[str, Any]:
        ir = self.ir
        context: Dict[str, Any] = {"@version": 1.1}
        context.update(ir.prefixes)
        for cls in sorted(ir.classes.values(), key=lambda c: c.term):
            context[cls.term] = ir.curie(cls.iri)
        for prop in sorted(ir.properties.values(), key=lambda p: p.term):
            entry: Dict[str, Any] = {"@id": ir.curie(prop.iri)}
            if prop.kind == "datatype":
                if prop.range and prop.range.startswith(XSD):
                    entry["@type"] = ir.curie(prop.range)
            elif self.scheme_for(prop) is not None:
                entry["@type"] = "@vocab"
            else:
                entry["@type"] = "@id"
            if not self.is_single(prop.iri):
                entry["@container"] = "@set"
            context[prop.term] = entry
        for scheme in sorted(ir.schemes.values(), key=lambda s: s.term):
            context[scheme.term] = ir.curie(scheme.iri)
            for concept in scheme.concepts:
                context[concept.term] = ir.curie(concept.iri)
        return context

    # ---------- Spec ----------

    def build(self) -> OpenAPISpec:
        ir, profile = self.ir, self.profile
        version = profile.version or (ir.version or "0.0.0").lstrip("vV")
        description = profile.description or (
            f"{ir.comment or ir.label}\n\n"
            f"Reference API generated from the {ir.label} ontology <{ir.iri}> and its SHACL "
            f"shapes. Payloads are JSON-LD: every schema maps to an ontology class, every "
            f"property to an ontology property (x-semantic-uri). Shapes constraints are reflected "
            f"as required/cardinality where JSON Schema can express them and listed in "
            f"x-ucm-constraints where it cannot."
        )
        return OpenAPISpec(
            title=profile.title or f"{ir.label} API",
            version=version,
            description=description,
            context_url=profile.context_url,
            ontology_iri=ir.iri,
            ontology_version=ir.version,
            sources=ir.sources,
            servers=profile.servers,
            references=profile.references,
            base_schema=self.base_schema(),
            schemas=[self.class_schema(c) for c in sorted(ir.classes.values(), key=lambda c: c.term)],
            concept_schemes=[self.scheme_schema(s) for s in sorted(ir.schemes.values(), key=lambda s: s.term)],
            support_schemas=self.support_schemas(),
            resources=[self.resource(r) for r in self.resource_roots()],
            context=self.context(),
        )

    @staticmethod
    def attach_examples(spec: OpenAPISpec, examples: Dict[str, List[Dict[str, Any]]]) -> OpenAPISpec:
        for schema in spec.schemas:
            schema.examples = examples.get(schema.name, [])
        return spec
