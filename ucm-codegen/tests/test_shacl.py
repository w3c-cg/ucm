"""PySHACL validation of the conformant example and single-defect variants"""

from typing import Callable

import pytest
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import XSD

from ucm_codegen.models import Severity, Tier
from ucm_codegen.shacl import validate_data

UCM = Namespace("https://www.w3.org/ns/ucm#")
EX = Namespace("http://example.org/ucm/")


def run(compilation, data: Graph):
    return validate_data(data, compilation.shapes, compilation.ontology, shapes_ns=compilation.shapes_ns)


def test_baseline_conforms(compilation, example_graph):
    """'Conformant baseline: must produce zero results, warnings included.'"""
    report = run(compilation, example_graph)
    assert report.conforms
    assert report.results == []


def test_namespace_drift_breaks_the_baseline(regressed_compilation, example_graph):
    """With the vocabulary in another namespace, every concept value in the baseline loses its anchor"""
    report = run(regressed_compilation, example_graph)
    assert all(r.severity == Severity.WARNING and r.tier == Tier.RECOMMENDED for r in report.results)
    assert {(r.focus_node, r.value, r.source_shape) for r in report.results} == {
        (str(EX[node]), str(UCM[concept]), f"https://www.w3.org/ns/ucm#{scheme}-anchored")
        for node, concept, scheme in [
            ("req-1", "Accepted", "LifecycleState"),
            ("req-1", "ReferralAccepted", "ReferralDisposition"),
            ("req-1", "ClosedConnected", "ClosureReason"),
            ("hs-1", "HandoffAssumed", "HandoffStatus"),
            ("hs-1", "FulfillmentConfirmed", "HandshakeFulfillment"),
            ("commit-1", "CommitmentInForce", "CommitmentStatus"),
        ]
    }


def drop_entity(g: Graph) -> None:
    g.remove((EX["p-res"], UCM.participatingEntity, None))


def reverse_validity(g: Graph) -> None:
    g.set((EX["p-cm"], UCM.validTo, Literal("2026-08-01T09:00:00-07:00", datatype=XSD.dateTime)))


def handshake_cycle(g: Graph) -> None:
    g.add((EX["hs-1"], UCM.negotiates, EX["hs-1"]))


def two_lifecycle_states(g: Graph) -> None:
    g.add((EX["req-1"], UCM.hasLifecycleState, UCM.Pending))


def literal_temporal_context(g: Graph) -> None:
    g.set((EX["p-res"], UCM.enactiveDuring, Literal("2026-09-02T09:00:00-07:00", datatype=XSD.dateTime)))


@pytest.mark.parametrize(
    "defect, message",
    [
        (drop_entity, "exactly one participating entity"),
        (reverse_validity, "validTo precedes validFrom"),
        (handshake_cycle, "no base case"),
        (two_lifecycle_states, "at most one lifecycle state"),
        (literal_temporal_context, "not a literal"),
    ],
    ids=lambda v: v.__name__ if callable(v) else "",
)
def test_single_defect_is_a_violation(compilation, example_graph, defect: Callable, message: str):
    data = Graph()
    data += example_graph
    defect(data)
    report = run(compilation, data)
    violations = report.by_severity(Severity.VIOLATION)
    assert violations, f"expected a violation for {defect.__name__}"
    assert any(message in v.message for v in violations)
    assert all(v.tier == Tier.DEFINITIONAL for v in violations)
