"""Consistency lints over the UCM ontology and shapes"""

import pytest
from rdflib import Graph, URIRef

from ucm_codegen.build import build_failed
from ucm_codegen.models import Severity
from ucm_codegen.parser import export_jsonld
from ucm_codegen.pipeline import compile_ir

from .conftest import SHAPES_LINT_TTL

UCMSH = "urn:w3c:cg:ucm:shapes#"


def by_code(compilation, code):
    return [f for f in compilation.findings if f.code == code]


def test_shapes_conform_to_shacl_shacl(compilation):
    assert not by_code(compilation, "shacl-shacl")
    assert not compilation.has(Severity.VIOLATION)


def test_shipped_spec_is_consistent(compilation):
    for code in ("namespace-drift", "undeclared-term", "range-mismatch", "foreign-scheme"):
        assert not by_code(compilation, code), code


def test_lifecycle_namespace_drift(regressed_compilation):
    """Shapes and data say ucm:LifecycleState; the vocabulary declares another namespace"""
    (drift,) = by_code(regressed_compilation, "namespace-drift")
    assert drift.subject == "ucm:LifecycleState"
    assert "http://mdixinc.com/ucm#LifecycleState" in drift.message
    assert "ucmsh:LifecycleState-anchored" in drift.message


def test_accepts_request_range(regressed_compilation):
    """acceptsRequest ranges over an undeclared class; its shape expects Participation"""
    (undeclared,) = by_code(regressed_compilation, "undeclared-term")
    assert undeclared.subject == "ucm:ParticipationContext"
    (mismatch,) = by_code(regressed_compilation, "range-mismatch")
    assert mismatch.subject == "ucm:acceptsRequest"
    assert "sh:class ucm:Participation" in mismatch.message


def test_spec_lint_passes(compilation):
    """ucm-shapes-lint.ttl, run over the shapes graph, has no findings"""
    assert not by_code(compilation, "shapes-lint")


def test_spec_lint_catches_untiered_shape(compilation, tmp_path):
    """Drop a tier and the spec's own lint (L2) reports it"""
    shapes = Graph()
    shapes += compilation.shapes
    shapes.remove((URIRef(UCMSH + "Participation-role"), URIRef(UCMSH + "tier"), None))
    shapes_file = tmp_path / "shapes.jsonld"
    shapes_file.write_text(shapes.serialize(format="json-ld"), encoding="utf-8")
    lint_file = tmp_path / "lint.jsonld"
    lint_file.write_text(export_jsonld(SHAPES_LINT_TTL), encoding="utf-8")
    ontology_file = tmp_path / "ontology.jsonld"
    ontology_file.write_text(compilation.ontology.serialize(format="json-ld"), encoding="utf-8")

    findings = compile_ir([ontology_file], [shapes_file], [lint_file]).findings
    (finding,) = [f for f in findings if f.code == "shapes-lint"]
    assert finding.subject == "ucmsh:Participation-role"
    assert finding.message == "Constraint-bearing shape has no ucmsh:tier."
    assert finding.severity == Severity.VIOLATION


def test_informational_findings(compilation):
    coercions = {f.subject for f in by_code(compilation, "datatype-coercion")}
    assert coercions == {"ucm:statementDate", "ucm:validFrom", "ucm:validTo"}
    orphans = {f.subject for f in by_code(compilation, "orphan-class")}
    assert {"ucm:CareCommitment", "ucm:HousingDomain"} <= orphans
    assert {f.subject for f in by_code(compilation, "shape-without-range")} == {"ucm:hasCareTrajectoryContext"}


# ---------- Namespace split across files (as on main, 2026-10-28) ----------

MOVED_NAMESPACE = "https://w3.org/ns/ucm#"


@pytest.fixture(scope="module")
def split_compilation(tmp_path_factory):
    """The ontology moved to a new namespace; shapes and example still use the old one"""
    from .conftest import ONTOLOGY_TTL, UCM_NAMESPACE, export_ir

    tmp = tmp_path_factory.mktemp("split")
    moved = tmp / ONTOLOGY_TTL[0].name
    moved.write_text(
        ONTOLOGY_TTL[0].read_text(encoding="utf-8").replace(UCM_NAMESPACE, MOVED_NAMESPACE),
        encoding="utf-8",
    )
    ontology, shapes, shapes_lint = export_ir(tmp, [moved, ONTOLOGY_TTL[1]])
    return compile_ir([ontology], [shapes], [shapes_lint])


def test_namespace_split_is_one_clear_finding(split_compilation):
    (drift,) = by_code(split_compilation, "namespace-drift")
    assert drift.subject == "urn:w3c:cg:ucm#"
    assert f"declared only under <{MOVED_NAMESPACE}>" in drift.message
    assert drift.message.startswith("47 terms (ActivityFocus, ")  # every UCM term the shapes use
    assert "Align the @prefix" in drift.message
    assert not by_code(split_compilation, "undeclared-term")  # no per-term flood


def test_standard_vocabularies_are_never_drift(split_compilation, compilation):
    for c in (split_compilation, compilation):
        assert not [f for f in by_code(c, "namespace-drift") if "w3.org/2006/time" in f.subject]


def test_strict_failure_names_the_drift(split_compilation):
    reasons = build_failed(split_compilation, None, strict=True)
    assert reasons == ["1 lint warnings (--strict), 1 of them namespace drift between spec files"]
