"""
SHACL validation with PySHACL

validate_data(): instance data against the UCM shapes, with the ontology
merged in so sh:class sees rdfs:subClassOf (ucm:Person is a ucm:Entity) and
SPARQL constraints see the concept schemes (skos:inScheme). The merge is
explicit: PySHACL's ont_graph mixing does not expose SKOS triples to
sh:sparql constraints.
validate_shapes(): the shapes graph against SHACL-SHACL, so a malformed
shape fails the build instead of silently matching nothing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from rdflib import BNode, Graph, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import RDF, SH
from rdflib.term import Node

from .models import Severity, Tier, ValidationReport, ValidationResult
from .normalize import DEFAULT_SHAPES_NS
from .utils import local_name

def _pyshacl():  # type: ignore[no-untyped-def]
    """Imported on first use: cached builds never validate, and pyshacl takes ~1s to import"""
    import pyshacl

    return pyshacl


def shacl_shacl_path() -> Path:
    return Path(_pyshacl().__file__).parent / "assets" / "shacl-shacl.ttl"
_SEVERITY_ORDER = {Severity.VIOLATION: 0, Severity.WARNING: 1, Severity.INFO: 2}

Inference = Literal["none", "rdfs", "owlrl", "both"]


def _term(node: Optional[Node]) -> Optional[str]:
    return None if node is None else str(node)


def _path(results: Graph, path: Optional[Node]) -> Optional[str]:
    """Readable form of a result path, including alternative and inverse paths"""
    if path is None or isinstance(path, URIRef):
        return _term(path)
    alternatives = results.value(path, SH.alternativePath)
    if alternatives is not None:
        return "|".join(str(m) for m in Collection(results, alternatives))
    inverse = results.value(path, SH.inversePath)
    if inverse is not None:
        return f"^{inverse}"
    return "(complex path)"


def _report(results: Graph, shapes: Graph, shapes_ns: str) -> ValidationReport:
    tier_predicate = Namespace(shapes_ns).tier
    parsed = []
    for result in results.subjects(RDF.type, SH.ValidationResult):
        source = results.value(result, SH.sourceShape)
        tier = shapes.value(source, tier_predicate) if source is not None else None
        parsed.append(ValidationResult(
            focus_node=str(results.value(result, SH.focusNode)),
            result_path=_path(results, results.value(result, SH.resultPath)),
            value=_term(results.value(result, SH.value)),
            severity=Severity(local_name(str(results.value(result, SH.resultSeverity)))),
            tier=Tier(local_name(str(tier))) if tier is not None else None,
            message=str(results.value(result, SH.resultMessage) or ""),
            source_shape=str(source) if isinstance(source, URIRef) else None,
        ))
    report_node = next(results.subjects(RDF.type, SH.ValidationReport), BNode())
    conforms = results.value(report_node, SH.conforms)
    return ValidationReport(
        conforms=bool(conforms.toPython()) if conforms is not None else not parsed,
        results=sorted(
            parsed,
            key=lambda r: (_SEVERITY_ORDER[r.severity], r.focus_node, r.result_path or ""),
        ),
    )


def validate_data(
    data: Graph,
    shapes: Graph,
    ontology: Optional[Graph] = None,
    inference: Inference = "none",
    shapes_ns: str = DEFAULT_SHAPES_NS,
) -> ValidationReport:
    """Validate instance data against the shapes"""
    combined = Graph()
    combined += data
    if ontology is not None:
        combined += ontology
    _, results, _ = _pyshacl().validate(
        combined,
        shacl_graph=shapes,
        inference=inference,
        meta_shacl=False,
        allow_warnings=False,
    )
    return _report(results, shapes, shapes_ns)


def validate_shapes(shapes: Graph, lint: Optional[Graph] = None) -> ValidationReport:
    """Validate the shapes graph as data: against SHACL-SHACL, or a lint shapes graph"""
    rules = lint if lint is not None else Graph().parse(str(shacl_shacl_path()))
    _, results, _ = _pyshacl().validate(shapes, shacl_graph=rules, inference="none")
    return _report(results, rules, DEFAULT_SHAPES_NS)
