"""
Postgres target: IR → SQLAlchemy models and an Alembic migration

Layout rules (the same placement and cardinality decisions as the OpenAPI
target, so a row and an API payload always have the same shape):

  root class                  table <root>; subclasses share it through
                              single-table inheritance on column "type"
  single-valued property      column on its home class's root table
  multi-valued property       association table <owner>__<property>
  reference (object property) IRI text, indexed, no foreign key: the shapes
                              keep sh:class at the Recommended tier, so a
                              reference may name a node typed elsewhere
  Definitional sh:minCount 1  NOT NULL on the root class, CHECK on a subclass
  predicates outside UCM      "extra" JSONB column (open by default)
  concept schemes             "concept" reference table, seeded by the migration
"""

from __future__ import annotations

import hashlib
import re
from typing import Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

from .builder import SpecBuilder
from .models import OntologyIR, OntologyProperty, Severity, SourceDigest

XSD = "http://www.w3.org/2001/XMLSchema#"
RESERVED_COLUMNS = {"iri", "type", "extra", "metadata", "registry"}
MAX_IDENTIFIER = 63  # Postgres NAMEDATALEN - 1

# xsd datatype → (ORM type, migration type, Python annotation, loader kind)
SQL_TYPES: Dict[str, Tuple[str, str, str, str]] = {
    XSD + "dateTime": ("UtcDateTime()", "sa.DateTime(timezone=True)", "datetime.datetime", "datetime"),
    XSD + "dateTimeStamp": ("UtcDateTime()", "sa.DateTime(timezone=True)", "datetime.datetime", "datetime"),
    XSD + "date": ("sa.Date()", "sa.Date()", "datetime.date", "date"),
    XSD + "time": ("sa.Time()", "sa.Time()", "datetime.time", "time"),
    XSD + "boolean": ("sa.Boolean()", "sa.Boolean()", "bool", "bool"),
    XSD + "integer": ("sa.BigInteger()", "sa.BigInteger()", "int", "int"),
    XSD + "int": ("sa.Integer()", "sa.Integer()", "int", "int"),
    XSD + "long": ("sa.BigInteger()", "sa.BigInteger()", "int", "int"),
    XSD + "nonNegativeInteger": ("sa.BigInteger()", "sa.BigInteger()", "int", "int"),
    XSD + "positiveInteger": ("sa.BigInteger()", "sa.BigInteger()", "int", "int"),
    XSD + "decimal": ("sa.Numeric()", "sa.Numeric()", "decimal.Decimal", "decimal"),
    XSD + "double": ("sa.Float()", "sa.Float()", "float", "float"),
    XSD + "float": ("sa.Float()", "sa.Float()", "float", "float"),
}
TEXT = ("sa.Text()", "sa.Text()", "str", "str")
REFERENCE = ("sa.Text()", "sa.Text()", "str", "reference")


def snake(term: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", term).lower()


def identifier(name: str) -> str:
    """Keep generated identifiers within Postgres' 63-byte limit, deterministically"""
    if len(name) <= MAX_IDENTIFIER:
        return name
    digest = hashlib.sha256(name.encode()).hexdigest()[:8]
    return f"{name[:MAX_IDENTIFIER - 9]}_{digest}"


class SqlColumn(BaseModel):
    name: str
    term: str
    iri: str
    kind: str = Field(description="Loader conversion: reference, datetime, str, ...")
    orm_type: str
    migration_type: str
    py_type: str
    nullable: bool = True
    index: bool = False
    comment: Optional[str] = None


class SqlCheck(BaseModel):
    name: str = Field(description="Constraint name before the ck_<table>_ naming convention")
    sql: str


class SqlClass(BaseModel):
    name: str
    parent: str
    term: str
    iri: str
    comment: Optional[str] = None


class SqlTable(BaseModel):
    name: str
    class_name: str
    iri: str
    comment: Optional[str] = None
    type_terms: List[str]
    columns: List[SqlColumn]
    checks: List[SqlCheck]
    subclasses: List[SqlClass]


class SqlAssociation(BaseModel):
    name: str
    term: str
    iri: str
    owner_table: Optional[str] = Field(description="None: the property has no domain, any node owns it")
    value: Literal["reference", "literal"]
    kind: str
    orm_type: str
    migration_type: str
    unique_subject: bool = False
    comment: Optional[str] = None


class SqlConcept(BaseModel):
    iri: str
    scheme_iri: str
    term: str
    label: str


class SqlSchema(BaseModel):
    ontology_iri: str
    ontology_version: Optional[str]
    revision: str
    sources: List[SourceDigest]
    tables: List[SqlTable]
    associations: List[SqlAssociation]
    concepts: List[SqlConcept]


class SqlBuilder:
    """Map the IR onto tables, reusing the OpenAPI placement rules"""

    def __init__(self, ir: OntologyIR, api: Optional[SpecBuilder] = None):
        self.ir = ir
        self.api = api or SpecBuilder(ir)

    def _types(self, prop: OntologyProperty) -> Tuple[str, str, str, str]:
        if prop.kind == "object":
            return REFERENCE
        constraints = self.api.all_constraints(prop.iri)
        datatypes = [prop.range] if prop.range else []
        datatypes += [d for c in constraints for d in c.datatypes]
        return next((SQL_TYPES[d] for d in datatypes if d in SQL_TYPES), TEXT)

    def _required_by(self, path: str, class_iri: str) -> bool:
        """Definitional minCount >= 1 from shapes that target this class"""
        return any(
            (c.min_count or 0) >= 1 and c.severity == Severity.VIOLATION
            for shape in self.ir.shapes_targeting(class_iri)
            for c in shape.properties
            if path in c.paths and not c.inverse
        )

    def _subtree(self, root_iri: str) -> List[str]:
        """Root then descendants, parents before children"""
        members = [root_iri] + self.ir.descendants(root_iri)
        return sorted(members, key=lambda c: (len(self.ir.ancestors(c)), self.ir.classes[c].term))

    def table(self, root_iri: str) -> SqlTable:
        ir = self.ir
        root = ir.classes[root_iri]
        name = snake(root.term)
        subtree = self._subtree(root_iri)

        columns: List[SqlColumn] = []
        checks = [SqlCheck(
            name="type",
            sql="type IN (" + ", ".join(f"'{ir.classes[c].term}'" for c in subtree) + ")",
        )]
        for prop in sorted(ir.properties.values(), key=lambda p: p.term):
            home = self.api.home(prop.iri)
            if home is None or ir.root_of(home) != root_iri or not self.api.is_single(prop.iri):
                continue
            column = snake(prop.term) + ("_" if snake(prop.term) in RESERVED_COLUMNS else "")
            orm_type, migration_type, py_type, kind = self._types(prop)
            required_classes = [c for c in subtree if self._required_by(prop.iri, c)]
            columns.append(SqlColumn(
                name=column,
                term=prop.term,
                iri=prop.iri,
                kind=kind,
                orm_type=orm_type,
                migration_type=migration_type,
                py_type=py_type,
                nullable=root_iri not in required_classes,
                index=kind == "reference",
                comment=f"{ir.curie(prop.iri)}: {prop.comment or prop.label}",
            ))
            for cls in required_classes:
                if cls == root_iri:
                    continue
                scope = [cls] + ir.descendants(cls)
                checks.append(SqlCheck(
                    name=identifier(f"{column}_{snake(ir.classes[cls].term)}"),
                    sql=(
                        "type NOT IN (" + ", ".join(f"'{ir.classes[c].term}'" for c in scope)
                        + f") OR {column} IS NOT NULL"
                    ),
                ))

        return SqlTable(
            name=name,
            class_name=root.term,
            iri=root_iri,
            comment=f"{ir.curie(root_iri)}: {root.comment or root.label}",
            type_terms=[ir.classes[c].term for c in subtree],
            columns=columns,
            checks=checks,
            subclasses=[
                SqlClass(
                    name=ir.classes[c].term,
                    parent=next(ir.classes[s].term for s in ir.classes[c].superclasses if s in ir.classes),
                    term=ir.classes[c].term,
                    iri=c,
                    comment=ir.classes[c].comment or ir.classes[c].label,
                )
                for c in subtree[1:]
            ],
        )

    def associations(self) -> List[SqlAssociation]:
        ir = self.ir
        result = []
        for prop in sorted(ir.properties.values(), key=lambda p: p.term):
            home = self.api.home(prop.iri)
            single = self.api.is_single(prop.iri)
            if single and home is not None:
                continue  # a column
            owner = snake(ir.classes[ir.root_of(home)].term) if home else None
            orm_type, migration_type, _, kind = self._types(prop)
            result.append(SqlAssociation(
                name=identifier(f"{owner or 'node'}__{snake(prop.term)}"),
                term=prop.term,
                iri=prop.iri,
                owner_table=owner,
                value="reference" if kind == "reference" else "literal",
                kind=kind,
                orm_type=orm_type,
                migration_type=migration_type,
                unique_subject=single,
                comment=f"{ir.curie(prop.iri)}: {prop.comment or prop.label}",
            ))
        return result

    def build(self) -> SqlSchema:
        ir = self.ir
        tables = [self.table(r.iri) for r in ir.roots()]
        associations = self.associations()
        names = [t.name for t in tables] + [a.name for a in associations] + ["concept"]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(f"Generated table names collide: {duplicates}")

        fingerprint = "".join(sorted(s.digest for s in ir.sources)) or ir.iri
        return SqlSchema(
            ontology_iri=ir.iri,
            ontology_version=ir.version,
            revision="ucm_" + hashlib.sha256(fingerprint.encode()).hexdigest()[:12],
            sources=ir.sources,
            tables=tables,
            associations=associations,
            concepts=[
                SqlConcept(iri=c.iri, scheme_iri=s.iri, term=c.term, label=c.label)
                for s in sorted(ir.schemes.values(), key=lambda s: s.term)
                for c in s.concepts
            ],
        )
