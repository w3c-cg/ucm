"""
Build report: everything the HTML report shows, gathered from the IR and targets

The report answers the questions a spec change raises: did a finding
appear, does the example still conform, and where does each property land
in the OpenAPI schema, the Postgres schema and the FHIR mapping.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .builder import BASE_SCHEMA
from .content import BuildDiff, changed_keys, short, toolchain_digest
from .models import APISchema, LintFinding, OpenAPISpec, Severity, ValidationReport
from .pipeline import Compilation
from .sql_target import SqlSchema

SQL_LABELS = {
    "sa.Text()": "text",
    "UtcDateTime()": "timestamptz",
    "sa.Date()": "date",
    "sa.Time()": "time",
    "sa.Boolean()": "boolean",
    "sa.BigInteger()": "bigint",
    "sa.Integer()": "integer",
    "sa.Numeric()": "numeric",
    "sa.Float()": "double precision",
}


def schema_summary(schema: Dict[str, Any]) -> str:
    """Short type label for a JSON Schema fragment"""
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[-1]
    if schema.get("type") == "array":
        return schema_summary(schema.get("items", {})) + "[]"
    if "anyOf" in schema:
        return " | ".join(schema_summary(s) for s in schema["anyOf"])
    kind, fmt = schema.get("type", "any"), schema.get("format")
    return f"{kind} ({fmt})" if fmt else str(kind)


def cardinality(prop: Any) -> str:
    if not prop.is_set:
        return "1" if prop.required else "0..1"
    low = prop.value_schema.get("minItems", 0)
    return f"{low}..*"


def _fhir_landings(adapter: Optional[Dict[str, Any]]) -> Dict[Tuple[Optional[str], str], List[str]]:
    """(class term or None, property term) → FHIR element paths"""
    landings: Dict[Tuple[Optional[str], str], List[str]] = {}
    if not adapter:
        return landings

    def note(cls: Optional[str], term: str, where: str) -> None:
        landings.setdefault((cls, term), [])
        if where not in landings[(cls, term)]:
            landings[(cls, term)].append(where)

    def walk(fields: Dict[str, Any], context: Optional[str], prefix: str) -> None:
        for path, field in fields.items():
            where = f"{prefix}.{path}"
            items = field["class"] if field["inverse"] else context
            if field["inverse"]:
                note(field["class"], field["inverse"], f"{where} (inverse)")
            if field["property"]:
                hop = field["property"][0]
                suffix = " (via " + "/".join(field["property"]) + ")" if len(field["property"]) > 1 else ""
                note(items, hop, where + suffix)
            if "each" in field:
                walk(field["each"], items, where)

    for term, spec in adapter["resources"].items():
        resources = [spec["resource"]] + [r for _, r in spec["by_role"] if r != spec["resource"]]
        walk(spec["fields"], term, " | ".join(resources))
    return landings


class ReportBuilder:
    def __init__(
        self,
        compilation: Compilation,
        spec: OpenAPISpec,
        sql: Optional[SqlSchema] = None,
        adapter: Optional[Dict[str, Any]] = None,
        validation: Optional[ValidationReport] = None,
        example_warnings: Optional[List[str]] = None,
        files: Optional[List[str]] = None,
        diff: Optional[BuildDiff] = None,
        lock: Optional[Any] = None,
        output_digests: Optional[Dict[str, str]] = None,
    ):
        self.diff = diff
        self.lock = lock
        self.output_digests = output_digests or {}
        self.c = compilation
        self.ir = compilation.ir
        self.spec = spec
        self.sql = sql
        self.adapter = adapter
        self.validation = validation
        self.example_warnings = example_warnings or []
        self.files = files or []
        self.fhir = _fhir_landings(adapter)
        self.columns = {
            col.term: (table.name, col) for table in (sql.tables if sql else []) for col in table.columns
        }
        self.associations = {a.term: a for a in (sql.associations if sql else [])}

    # ---------- per property / class ----------

    def _related(self, term: Optional[str]) -> List[Optional[str]]:
        if term is None or term not in {c.term for c in self.ir.classes.values()}:
            return [term]
        iri = next(c.iri for c in self.ir.classes.values() if c.term == term)
        family = [iri] + self.ir.ancestors(iri) + self.ir.descendants(iri)
        return [self.ir.classes[i].term for i in family]

    def property_row(self, prop: Any, class_term: Optional[str]) -> Dict[str, Any]:
        postgres = None
        if prop.name in self.columns:
            table, col = self.columns[prop.name]
            postgres = f"{table}.{col.name}"
            postgres_type = SQL_LABELS.get(col.orm_type, col.orm_type) + ("" if col.nullable else " not null")
        elif prop.name in self.associations:
            assoc = self.associations[prop.name]
            postgres = assoc.name
            postgres_type = "association"
        else:
            postgres_type = ""
        fhir = []
        for cls in self._related(class_term) + [None]:
            fhir.extend(w for w in self.fhir.get((cls, prop.name), []) if w not in fhir)
        constraints = prop.extensions.get("x-ucm-constraints", [])
        return {
            "name": prop.name,
            "curie": self.ir.curie(prop.iri) if not prop.iri.startswith("@") else prop.iri,
            "description": prop.description,
            "cardinality": cardinality(prop),
            "required": prop.required,
            "recommended": bool(prop.extensions.get("x-ucm-recommended")),
            "range": prop.extensions.get("x-ucm-range") or prop.extensions.get("x-ucm-datatype"),
            "openapi": schema_summary(prop.value_schema),
            "postgres": postgres,
            "postgres_type": postgres_type,
            "fhir": fhir,
            "constraints": constraints,
        }

    def class_entry(self, schema: APISchema, depth: int) -> Dict[str, Any]:
        cls = next((c for c in self.ir.classes.values() if c.term == schema.name), None)
        root_term = self.ir.classes[self.ir.root_of(cls.iri)].term if cls else None
        resource = next((r for r in self.spec.resources if r.name == root_term), None)
        mapped = None
        if self.adapter and cls:
            for candidate in [cls.term] + [self.ir.classes[a].term for a in self.ir.ancestors(cls.iri)]:
                spec = self.adapter["resources"].get(candidate)
                if spec:
                    names = [spec["resource"]] + [r for _, r in spec["by_role"] if r != spec["resource"]]
                    mapped = {"resource": " | ".join(names), "via": candidate}
                    break
        return {
            "name": schema.name,
            "label": cls.label if cls else "Base node",
            "comment": cls.comment if cls else schema.description,
            "curie": schema.curie or "(base)",
            "depth": depth,
            "is_base": cls is None,
            "parents": schema.parents,
            "subclasses": schema.extensions.get("x-ucm-subclasses", []),
            "equivalents": schema.extensions.get("x-ucm-equivalent-classes", []),
            "constraints": schema.extensions.get("x-ucm-constraints", []),
            "resource": resource.collection_path if resource else None,
            "table": next((t.name for t in (self.sql.tables if self.sql else []) if t.class_name == root_term), None),
            "fhir": mapped,
            "examples": len(schema.examples),
            "properties": [
                self.property_row(p, schema.name if cls else None)
                for p in schema.properties
                if p.name != "@type" or cls is None
            ],
        }

    def class_tree(self) -> List[Dict[str, Any]]:
        schemas = {s.name: s for s in self.spec.schemas}
        children: Dict[str, List[str]] = {}
        for s in self.spec.schemas:
            for parent in s.parents:
                children.setdefault(parent, []).append(s.name)
        ordered: List[Dict[str, Any]] = [self.class_entry(self.spec.base_schema, 0)]
        seen = set()

        def visit(name: str, depth: int) -> None:
            if name in seen:
                return
            seen.add(name)
            ordered.append(self.class_entry(schemas[name], depth))
            for child in sorted(children.get(name, [])):
                visit(child, depth + 1)

        for root in sorted(children.get(BASE_SCHEMA, [])):
            visit(root, 1)
        return ordered

    # ---------- report ----------

    def build(self) -> Dict[str, Any]:
        findings = self.c.findings
        counts = {s: sum(f.severity == s for f in findings) for s in Severity}
        validation_violations = self.validation.by_severity(Severity.VIOLATION) if self.validation else []
        validation_warnings = self.validation.by_severity(Severity.WARNING) if self.validation else []
        failed = bool(counts[Severity.VIOLATION] or validation_violations)
        warned = bool(counts[Severity.WARNING] or validation_warnings)

        def finding(f: LintFinding) -> Dict[str, str]:
            return {"severity": f.severity.value, "code": f.code, "subject": f.subject, "message": f.message}

        ir = self.ir
        return {
            "title": self.spec.title,
            "ontology": {
                "label": ir.label,
                "iri": ir.iri,
                "version": ir.version,
                "comment": ir.comment,
                "sources": [s.model_dump() for s in ir.sources],
            },
            "status": {
                "state": "failed" if failed else ("warnings" if warned else "passed"),
                "violations": counts[Severity.VIOLATION],
                "warnings": counts[Severity.WARNING],
                "infos": counts[Severity.INFO],
                "validated": self.validation is not None,
                "conforms": self.validation is not None and not self.validation.results,
                "validation_violations": len(validation_violations),
                "validation_warnings": len(validation_warnings),
            },
            "counts": [
                ("Classes", len(ir.classes)),
                ("Properties", len(ir.properties)),
                ("Concept schemes", len(ir.schemes)),
                ("Node shapes", len(ir.shapes)),
                ("Constraints", sum(len(s.properties) + len(s.sparql) for s in ir.shapes)),
                ("API resources", len(self.spec.resources)),
                ("API operations", len(self.spec.operations)),
                ("Tables", len(self.sql.tables) if self.sql else 0),
                ("Association tables", len(self.sql.associations) if self.sql else 0),
                ("FHIR-mapped classes", len(self.adapter["resources"]) if self.adapter else 0),
            ],
            "findings": [finding(f) for f in findings],
            "validation": [r.model_dump(mode="json") for r in (self.validation.results if self.validation else [])],
            "example_warnings": self.example_warnings,
            "classes": self.class_tree(),
            "schemes": [
                {"name": s.name, "iri": s.iri, "description": s.description, "concepts": s.concepts}
                for s in self.spec.concept_schemes
            ],
            "resources": [
                {
                    "name": r.name,
                    "collection": r.collection_path,
                    "item": r.item_path,
                    "subtypes": len(r.type_terms) - 1,
                    "operations": [(op.method.upper(), op.path, op.operation_id) for op in r.operations],
                }
                for r in self.spec.resources
            ],
            "sql": self.sql.model_dump() if self.sql else None,
            "fhir": [
                {
                    "term": term,
                    "resource": spec["resource"],
                    "by_role": spec["by_role"],
                    "fields": [
                        {"path": path, "source": _describe(field)} for path, field in spec["fields"].items()
                    ],
                }
                for term, spec in (self.adapter["resources"].items() if self.adapter else [])
            ],
            "files": [(f, self.output_digests.get(f)) for f in self.files],
            "provenance": {
                "toolchain": toolchain_digest(),
                "ir_root": self.lock.ir_root if self.lock else None,
                "nodes": len(self.lock.nodes) if self.lock else None,
            },
            "changes": self._changes(),
        }

    def _changes(self) -> Dict[str, Any]:
        """Build diff for the Changes pane; state is untracked, first, unchanged or changed"""
        if self.diff is None:
            return {"state": "untracked", "count": 0}
        if self.diff.first_build:
            return {"state": "first", "count": 0}
        added, removed, changed = changed_keys(self.diff.nodes)
        def compact(value: Optional[str]) -> Optional[str]:
            return self.ir.curie(value) if value and "://" in value or (value or "").startswith("urn:") else value

        nodes = []
        for change in self.diff.nodes:
            kind, _, name = change.key.partition(":")
            fields = []
            for f in change.fields:
                fields.append({
                    "field": f.field,
                    "before": compact(f.before),
                    "after": compact(f.after),
                    "added": [compact(a) for a in f.added],
                    "removed": [compact(r) for r in f.removed],
                })
            nodes.append({"kind": change.kind, "type": kind, "name": name, "fields": fields})
        return {
            "state": "unchanged" if self.diff.unchanged else "changed",
            "previous": short(self.diff.previous),
            "count": len(self.diff.nodes) + len(self.diff.outputs),
            "added": added,
            "removed": removed,
            "changed": changed,
            "nodes": nodes,
            "outputs": [o.model_dump() for o in self.diff.outputs],
        }


def _describe(field: Dict[str, Any]) -> str:
    parts = []
    if field["inverse"]:
        what = f"{field['class']} " if field["class"] else ""
        parts.append(f"{what}nodes whose {field['inverse']} points here")
    if field["roles"]:
        parts.append("role " + " | ".join(field["roles"]))
    if field["exclude_roles"]:
        parts.append("not role " + " | ".join(field["exclude_roles"]))
    if field["property"]:
        parts.append("/".join(field["property"]))
    if field["transform"] != "direct":
        parts.append(field["transform"])
    if field.get("map"):
        parts.append(", ".join(f"{k.rsplit('#', 1)[-1]}→{v}" for k, v in field["map"].items()))
    if "each" in field:
        parts.append(f"{len(field['each'])} sub-elements")
    return " · ".join(parts) or "this node"
