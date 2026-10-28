"""
Consistency lints over the ontology and shapes

PySHACL validates instance data; these checks validate the specification
itself. They catch references to undeclared terms (including namespace
drift between files), shapes that disagree with rdfs:range, and constructs
a JSON-LD context cannot express. The tier convention itself is checked by
the spec's own ucm-shapes-lint.ttl (pipeline.compile_ir).
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Set

from .models import LintFinding, OntologyIR, Severity
from .utils import local_name

_SPARQL_PREFIX = re.compile(r"PREFIX\s+([A-Za-z][\w-]*)?:\s*<([^>]*)>", re.IGNORECASE)
_SEVERITY_ORDER = {Severity.VIOLATION: 0, Severity.WARNING: 1, Severity.INFO: 2}

# Vocabularies the spec builds on. Their terms are never drift, even when a
# local name happens to match a UCM term.
STANDARD_NAMESPACES = (
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "http://www.w3.org/2000/01/rdf-schema#",
    "http://www.w3.org/2002/07/owl#",
    "http://www.w3.org/2001/XMLSchema#",
    "http://www.w3.org/2004/02/skos/core#",
    "http://www.w3.org/ns/shacl#",
    "http://www.w3.org/2006/time#",
    "http://www.w3.org/ns/prov#",
    "http://purl.org/dc/terms/",
    "http://purl.org/vocab/vann/",
    "http://xmlns.com/foaf/0.1/",
    "http://www.w3.org/ns/dcat#",
    "http://schema.org/",
    "https://schema.org/",
)


def _shape_name(ir: OntologyIR, iri: str | None) -> str:
    return ir.curie(iri) if iri else "(blank shape)"


def _namespace(iri: str) -> str:
    return iri[: len(iri) - len(local_name(iri))]


def _sparql_references(select: str) -> Set[str]:
    """IRIs named in a SPARQL constraint, by prefixed or full form, in any namespace"""
    found: Set[str] = set()
    for prefix, namespace in _SPARQL_PREFIX.findall(select):
        pattern = rf"(?<![\w:]){re.escape(prefix)}:([A-Za-z_][\w-]*)"
        found.update(namespace + name for name in re.findall(pattern, select))
    body = _SPARQL_PREFIX.sub("", select)
    found.update(re.findall(r"<([a-z][\w+.-]*:[^>\s]+)>", body))
    return found


def _references(ir: OntologyIR) -> Dict[str, Set[str]]:
    """Every IRI the ontology and shapes point at, with where it is used"""
    refs: Dict[str, Set[str]] = defaultdict(set)
    for prop in ir.properties.values():
        if prop.domain:
            refs[prop.domain].add(f"rdfs:domain of {ir.curie(prop.iri)}")
        if prop.range:
            refs[prop.range].add(f"rdfs:range of {ir.curie(prop.iri)}")
        for sup in prop.superproperties:
            refs[sup].add(f"rdfs:subPropertyOf of {ir.curie(prop.iri)}")
    for cls in ir.classes.values():
        for sup in cls.superclasses:
            refs[sup].add(f"rdfs:subClassOf of {ir.curie(cls.iri)}")
    for shape in ir.shapes:
        name = _shape_name(ir, shape.iri)
        for iri in shape.target_classes + shape.target_subjects_of + shape.target_objects_of:
            refs[iri].add(f"target of {name}")
        for constraint in shape.properties:
            for iri in constraint.paths:
                refs[iri].add(f"sh:path in {name}")
            for iri in constraint.classes:
                refs[iri].add(f"sh:class in {name}")
        for query in shape.sparql:
            for iri in _sparql_references(query.select):
                refs[iri].add(f"SPARQL in {name}")
    return refs


def lint(ir: OntologyIR) -> List[LintFinding]:
    """Run all consistency checks; findings are sorted most severe first"""
    findings: List[LintFinding] = []
    concepts = {c.iri: c for s in ir.schemes.values() for c in s.concepts}
    declared = set(ir.classes) | set(ir.properties) | set(ir.schemes) | set(concepts) | {ir.iri}
    by_local: Dict[str, Set[str]] = defaultdict(set)
    for iri in declared:
        by_local[local_name(iri)].add(iri)

    # 1. References nothing declares. A reference whose local name is declared
    #    under another namespace is drift; drift is grouped per pair of
    #    namespaces, so a whole file left on an old namespace is one finding.
    references = _references(ir)
    drift: Dict[tuple, List[tuple]] = defaultdict(list)
    for iri, uses in sorted(references.items()):
        if iri in declared or iri.startswith(STANDARD_NAMESPACES):
            continue
        elsewhere = sorted(by_local[local_name(iri)] - {iri})
        if elsewhere:
            drift[(_namespace(iri), _namespace(elsewhere[0]))].append((iri, elsewhere[0], uses))
        elif iri.startswith(ir.namespace):
            findings.append(LintFinding(
                code="undeclared-term",
                severity=Severity.WARNING,
                subject=ir.curie(iri),
                message=f"Referenced ({'; '.join(sorted(uses))}) but never declared.",
            ))

    for (referenced_ns, declared_ns), items in sorted(drift.items()):
        if len(items) == 1:
            ((iri, target, uses),) = items
            findings.append(LintFinding(
                code="namespace-drift",
                severity=Severity.WARNING,
                subject=ir.curie(iri),
                message=(
                    f"Referenced ({'; '.join(sorted(uses))}) but only declared as "
                    f"<{target}>. The files disagree on the namespace; data written "
                    f"against <{iri}> will not resolve to the declared term."
                ),
            ))
            continue
        names = [local_name(iri) for iri, _, _ in items]
        shown = ", ".join(names[:6]) + (f" and {len(names) - 6} more" if len(names) > 6 else "")
        uses = sum(len(u) for _, _, u in items)
        findings.append(LintFinding(
            code="namespace-drift",
            severity=Severity.WARNING,
            subject=referenced_ns,
            message=(
                f"{len(items)} terms ({shown}) are referenced {uses} times under <{referenced_ns}> "
                f"but declared only under <{declared_ns}>. The files disagree on the namespace: "
                f"shapes and data written against <{referenced_ns}> will not match the ontology, "
                f"so type checks on them fail. Align the @prefix (and SPARQL PREFIX) lines."
            ),
        ))

    # 2. Concept schemes outside the ontology namespace
    for scheme in ir.schemes.values():
        if not scheme.iri.startswith(ir.namespace):
            findings.append(LintFinding(
                code="foreign-scheme",
                severity=Severity.INFO,
                subject=scheme.iri,
                message=(
                    f"Concept scheme and its {len(scheme.concepts)} concepts are outside the "
                    f"ontology namespace <{ir.namespace}>. Context terms map to their full IRIs."
                ),
            ))

    # 3. sh:class that disagrees with rdfs:range
    seen_ranges: Set[tuple] = set()
    for shape in ir.shapes:
        for constraint in shape.properties:
            if constraint.inverse or not constraint.classes:
                continue
            for path in constraint.paths:
                prop = ir.properties.get(path)
                if prop is None:
                    continue
                for cls in constraint.classes:
                    key = (path, cls)
                    if key in seen_ranges:
                        continue
                    seen_ranges.add(key)
                    if prop.range is None:
                        findings.append(LintFinding(
                            code="shape-without-range",
                            severity=Severity.INFO,
                            subject=ir.curie(path),
                            message=(
                                f"{_shape_name(ir, constraint.iri or shape.iri)} requires sh:class "
                                f"{ir.curie(cls)} but the property declares no rdfs:range."
                            ),
                        ))
                        continue
                    compatible = (
                        cls == prop.range
                        or prop.range in ir.ancestors(cls)
                        or cls in ir.ancestors(prop.range)
                    )
                    if not compatible:
                        findings.append(LintFinding(
                            code="range-mismatch",
                            severity=Severity.WARNING,
                            subject=ir.curie(path),
                            message=(
                                f"rdfs:range is {ir.curie(prop.range)} but "
                                f"{_shape_name(ir, constraint.iri or shape.iri)} requires "
                                f"sh:class {ir.curie(cls)}."
                            ),
                        ))

    # 4. Datatype unions a single JSON-LD term cannot coerce
    flagged: Set[str] = set()
    for shape in ir.shapes:
        for constraint in shape.properties:
            if len(constraint.datatypes) < 2:
                continue
            for path in constraint.paths:
                if path in flagged:
                    continue
                flagged.add(path)
                prop = ir.properties.get(path)
                target = prop.range if prop and prop.range in constraint.datatypes else constraint.datatypes[0]
                others = [ir.curie(d) for d in constraint.datatypes if d != target]
                findings.append(LintFinding(
                    code="datatype-coercion",
                    severity=Severity.INFO,
                    subject=ir.curie(path),
                    message=(
                        f"Shapes accept {', '.join(ir.curie(d) for d in constraint.datatypes)}; "
                        f"the context term coerces to {ir.curie(target)}. Values typed "
                        f"{', '.join(others)} compact to a value object under the full IRI."
                    ),
                ))

    # 5. Classes nothing connects to
    used: Set[str] = set()
    for prop in ir.properties.values():
        used.update(filter(None, (prop.domain, prop.range)))
    for shape in ir.shapes:
        used.update(shape.target_classes)
        for constraint in shape.properties:
            used.update(constraint.classes)
    for root in ir.roots():
        if root.iri not in used and not ir.descendants(root.iri):
            findings.append(LintFinding(
                code="orphan-class",
                severity=Severity.INFO,
                subject=ir.curie(root.iri),
                message="No subclasses, properties or shapes refer to this class.",
            ))

    # 6. Properties without a domain
    for prop in ir.domainless_properties():
        findings.append(LintFinding(
            code="no-domain",
            severity=Severity.INFO,
            subject=ir.curie(prop.iri),
            message="No rdfs:domain: generated on the UcmNode base schema, so every resource accepts it.",
        ))

    return sorted(findings, key=lambda f: (_SEVERITY_ORDER[f.severity], f.code, f.subject))
