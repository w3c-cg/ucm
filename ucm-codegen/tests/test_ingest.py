"""The JSON-LD IR boundary: export, ingest, canonical digests"""

import json
from pathlib import Path

import pytest
from rdflib import Graph
from rdflib.compare import isomorphic

from ucm_codegen.parser import IRBoundaryError, export_jsonld, ingest, load_rdf, parse_rdf

from .conftest import ONTOLOGY_TTL, SHAPES_TTL


def test_export_is_deterministic():
    assert export_jsonld(ONTOLOGY_TTL) == export_jsonld(ONTOLOGY_TTL)


@pytest.mark.parametrize("sources", [ONTOLOGY_TTL, SHAPES_TTL], ids=["ontology", "shapes"])
def test_export_ignores_checkout_line_endings(tmp_path: Path, sources):
    """A Windows checkout (CRLF) and a Linux runner (LF) export the same IR, multi-line literals included"""
    exports = {}
    for ending in ("\n", "\r\n"):
        folder = tmp_path / repr(ending).strip("'").replace("\\", "")
        folder.mkdir()
        copies = []
        for source in sources:
            text = source.read_bytes().decode("utf-8").replace("\r\n", "\n")
            copy = folder / source.name
            copy.write_bytes(text.replace("\n", ending).encode("utf-8"))
            copies.append(copy)
        exports[ending] = export_jsonld(copies)
        assert "\\r" not in exports[ending]
    assert exports["\n"] == exports["\r\n"]


def test_data_graphs_ignore_line_endings(tmp_path: Path):
    lf, crlf = tmp_path / "lf.ttl", tmp_path / "crlf.ttl"
    text = '@prefix ex: <http://example.org/> .\nex:a ex:note """line one\nline two""" .\n'
    lf.write_bytes(text.encode("utf-8"))
    crlf.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    assert isomorphic(load_rdf([lf]), load_rdf([crlf]))


@pytest.mark.parametrize("sources", [ONTOLOGY_TTL, SHAPES_TTL], ids=["ontology", "shapes"])
def test_round_trip_preserves_the_graph(tmp_path: Path, sources):
    """Turtle → JSON-LD (export) → PyLD → rdflib is lossless, blank nodes and lists included"""
    exported = tmp_path / "ir.jsonld"
    exported.write_text(export_jsonld(sources), encoding="utf-8")

    original = Graph()
    for source in sources:
        parse_rdf(original, source)
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
