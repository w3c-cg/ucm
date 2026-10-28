"""The JSON-LD IR boundary: export, ingest, canonical digests"""

import json
from pathlib import Path

import pytest
from rdflib import Graph
from rdflib.compare import isomorphic

from ucm_codegen.parser import IRBoundaryError, export_jsonld, ingest

from .conftest import ONTOLOGY_TTL, SHAPES_TTL


def test_export_is_deterministic():
    assert export_jsonld(ONTOLOGY_TTL) == export_jsonld(ONTOLOGY_TTL)


@pytest.mark.parametrize("sources", [ONTOLOGY_TTL, SHAPES_TTL], ids=["ontology", "shapes"])
def test_round_trip_preserves_the_graph(tmp_path: Path, sources):
    """Turtle → JSON-LD (export) → PyLD → rdflib is lossless, blank nodes and lists included"""
    exported = tmp_path / "ir.jsonld"
    exported.write_text(export_jsonld(sources), encoding="utf-8")

    original = Graph()
    for source in sources:
        original.parse(str(source))
    ingested, digests = ingest([exported])

    assert len(ingested) == len(original)
    assert isomorphic(ingested, original)
    assert digests[0].triples == len(original)


def test_digest_is_stable_across_exports(tmp_path: Path):
    first, second = tmp_path / "a.jsonld", tmp_path / "b.jsonld"
    first.write_text(export_jsonld(ONTOLOGY_TTL), encoding="utf-8")
    second.write_text(export_jsonld(ONTOLOGY_TTL), encoding="utf-8")
    (a,), (b,) = ingest([first])[1], ingest([second])[1]
    assert a.digest == b.digest
    assert a.digest.startswith("sha256:")


def test_digest_ignores_serialization_details(tmp_path: Path):
    """Reordered, re-contexted JSON-LD of the same graph has the same digest"""
    exported = json.loads(export_jsonld(SHAPES_TTL))
    reordered = {"@context": exported["@context"], "@graph": list(reversed(exported["@graph"]))}
    first, second = tmp_path / "a.jsonld", tmp_path / "b.jsonld"
    first.write_text(json.dumps(exported), encoding="utf-8")
    second.write_text(json.dumps(reordered, indent=4), encoding="utf-8")
    assert ingest([first])[1][0].digest == ingest([second])[1][0].digest


def test_boundary_rejects_turtle():
    with pytest.raises(IRBoundaryError, match="IR boundary is JSON-LD"):
        ingest([ONTOLOGY_TTL[0]])


def test_boundary_refuses_remote_contexts(tmp_path: Path):
    doc = tmp_path / "remote.jsonld"
    doc.write_text(
        json.dumps({"@context": "https://example.org/ctx.jsonld", "@id": "urn:x", "p": "v"}),
        encoding="utf-8",
    )
    with pytest.raises(IRBoundaryError):
        ingest([doc])
