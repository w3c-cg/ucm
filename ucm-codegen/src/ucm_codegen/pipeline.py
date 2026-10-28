"""
Pipeline: JSON-LD → canonical graph → Pydantic IR → findings

    ingest (PyLD, URDNA2015)  →  normalize (rdflib)  →  validate (Pydantic,
    SHACL-SHACL, lints)  →  build (SpecBuilder)  →  render (Jinja)

compile_ir() runs everything up to the IR; the CLI and tests both use it.
With a cache, the IR and findings are stored by the canonical digests of
their inputs, so an unchanged spec skips normalization and PySHACL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

from rdflib import Graph

from .content import Cache
from .lint import lint
from .models import LintFinding, OntologyIR, Severity, SourceDigest
from .normalize import Normalizer
from .parser import ingest
from .shacl import validate_shapes


@dataclass
class Compilation:
    ir: OntologyIR
    ontology: Graph
    shapes: Graph
    shapes_ns: str
    findings: List[LintFinding] = field(default_factory=list)
    lint_sources: List[SourceDigest] = field(default_factory=list)

    def has(self, severity: Severity) -> bool:
        return any(f.severity == severity for f in self.findings)


def compile_ir(
    ontology: Sequence[Path],
    shapes: Sequence[Path],
    shapes_lint: Sequence[Path] = (),
    meta_shacl: bool = True,
    cache: Optional[Cache] = None,
) -> Compilation:
    """Ingest JSON-LD inputs and build the validated IR plus lint findings.

    shapes_lint is the spec's own lint (ucm-shapes-lint.ttl): shapes over the
    shapes graph, run with the shapes graph as data.
    """
    ontology_graph, ontology_sources = ingest(ontology, cache)
    shapes_graph, shapes_sources = ingest(shapes, cache)
    lint_graph, lint_sources = ingest(shapes_lint, cache) if shapes_lint else (None, [])

    key = Cache.key(
        "compile",
        [(s.file, s.digest) for s in ontology_sources + shapes_sources + lint_sources],
        meta_shacl,
    )
    cached = cache.get_json("compile", key) if cache else None
    if cached is not None:
        return Compilation(
            ir=OntologyIR.model_validate(cached["ir"]),
            ontology=ontology_graph,
            shapes=shapes_graph,
            shapes_ns=cached["shapes_ns"],
            findings=[LintFinding.model_validate(f) for f in cached["findings"]],
            lint_sources=lint_sources,
        )

    normalizer = Normalizer(ontology_graph, shapes_graph, ontology_sources + shapes_sources)
    ir = normalizer.to_ir()

    findings = lint(ir)
    reports = []
    if meta_shacl:
        reports.append(("shacl-shacl", validate_shapes(shapes_graph)))
    if lint_graph is not None:
        reports.append(("shapes-lint", validate_shapes(shapes_graph, lint_graph)))
    for code, report in reversed(reports):
        findings[:0] = [
            LintFinding(
                code=code,
                severity=r.severity,
                subject=ir.curie(r.focus_node),
                message=r.message or f"Shape fails {r.source_shape}",
            )
            for r in report.results
        ]

    compilation = Compilation(
        ir=ir,
        ontology=ontology_graph,
        shapes=shapes_graph,
        shapes_ns=str(normalizer.UCMSH),
        findings=findings,
        lint_sources=lint_sources,
    )
    if cache:
        cache.put_json("compile", key, {
            "ir": ir.model_dump(mode="json"),
            "shapes_ns": compilation.shapes_ns,
            "findings": [f.model_dump(mode="json") for f in findings],
        })
    return compilation
