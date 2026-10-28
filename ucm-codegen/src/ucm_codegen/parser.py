"""
JSON-LD ingest: the IR boundary

The toolchain accepts the ontology and shapes only as JSON-LD. PyLD is the
JSON-LD processor, so any conformant export works (Protégé, ROBOT, rdflib,
TopBraid). Each document is canonicalized with URDNA2015; the canonical
N-Quads give a stable digest of the input and are loaded into rdflib for
normalization.

export_jsonld() is the convenience on the other side of the boundary: it
turns Turtle (or any RDF rdflib reads) into the deterministic JSON-LD export
the rest of the toolchain consumes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pyld import jsonld
from rdflib import Dataset, Graph

from .content import Cache, digest_bytes, digest_text
from .models import SourceDigest

JSONLD_SUFFIXES = {".jsonld", ".json"}

# Prefixes used to keep exported JSON-LD readable; they do not affect the IR
EXPORT_PREFIXES: Dict[str, str] = {
    "ucm": "urn:w3c:cg:ucm#",
    "ucmsh": "urn:w3c:cg:ucm:shapes#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "sh": "http://www.w3.org/ns/shacl#",
    "time": "http://www.w3.org/2006/time#",
    "dcterms": "http://purl.org/dc/terms/",
}


class IRBoundaryError(ValueError):
    """Input is not usable JSON-LD"""


def _refuse_remote(url: str, options: Any = None) -> Dict[str, Any]:
    """Document loader that keeps builds hermetic: no remote @context fetches"""
    raise IRBoundaryError(
        f"Remote JSON-LD context refused: {url}. Inline the context in the export."
    )


def _canonical_nquads(doc: Any, base: str) -> str:
    return jsonld.normalize(
        doc,
        {
            "algorithm": "URDNA2015",
            "format": "application/n-quads",
            "documentLoader": _refuse_remote,
            "base": base,
        },
    )


def ingest(paths: Sequence[Path], cache: Optional[Cache] = None) -> Tuple[Graph, List[SourceDigest]]:
    """Load JSON-LD documents into one rdflib graph via PyLD canonicalization.

    With a cache, canonical N-Quads are stored by the digest of the file bytes
    (and base IRI), so unchanged inputs skip URDNA2015 entirely.
    """
    graph = Graph()
    sources: List[SourceDigest] = []

    for path in paths:
        if path.suffix.lower() not in JSONLD_SUFFIXES:
            raise IRBoundaryError(
                f"{path.name}: the IR boundary is JSON-LD. "
                f"Convert it first: ucm-codegen export -o {path.name}"
            )
        raw = path.read_bytes()
        content = digest_bytes(raw)
        base = path.resolve().as_uri()
        key = Cache.key("ingest", content, base)
        nquads = cache.get_text("ingest", key, ".nq") if cache else None

        if nquads is None:
            try:
                doc = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                raise IRBoundaryError(f"{path.name}: not valid JSON ({e})") from e
            try:
                nquads = _canonical_nquads(doc, base)
            except jsonld.JsonLdError as e:
                raise IRBoundaryError(f"{path.name}: not valid JSON-LD ({e})") from e
            if cache:
                cache.put_text("ingest", key, nquads, ".nq")

        # Named graphs, if any, are merged: the IR has a single default graph
        dataset = Dataset()
        dataset.parse(data=nquads, format="nquads")
        before = len(graph)
        for s, p, o, _ in dataset.quads((None, None, None, None)):
            graph.add((s, p, o))

        sources.append(SourceDigest(
            file=path.name,
            digest=digest_text(nquads),
            triples=len(graph) - before,
            content=content,
        ))

    for prefix, namespace in EXPORT_PREFIXES.items():
        graph.bind(prefix, namespace, override=False)
    return graph, sources


def load_rdf(paths: Sequence[Path]) -> Graph:
    """Load data graphs (not IR): JSON-LD through PyLD, anything else through rdflib"""
    jsonld_paths = [p for p in paths if p.suffix.lower() in JSONLD_SUFFIXES]
    graph, _ = ingest(jsonld_paths) if jsonld_paths else (Graph(), [])
    for path in paths:
        if path.suffix.lower() not in JSONLD_SUFFIXES:
            graph.parse(str(path))
    return graph


def export_jsonld(sources: Sequence[Path], context: Dict[str, str] | None = None) -> str:
    """Serialize RDF sources as deterministic, compacted JSON-LD.

    Blank nodes get canonical (URDNA2015) labels and nodes are sorted, so the
    same ontology always exports byte-identical JSON-LD.
    """
    graph = Graph()
    for source in sources:
        graph.parse(str(source))

    canonical = jsonld.normalize(
        jsonld.from_rdf(graph.serialize(format="nt"), {"format": "application/n-quads"}),
        {"algorithm": "URDNA2015", "format": "application/n-quads"},
    )
    expanded = jsonld.from_rdf(canonical, {"format": "application/n-quads"})
    compacted = jsonld.compact(
        expanded,
        dict(context or EXPORT_PREFIXES),
        {"documentLoader": _refuse_remote},
    )

    if "@graph" in compacted:
        nodes = compacted["@graph"]
    else:  # a single node compacts without @graph
        nodes = [{k: v for k, v in compacted.items() if k != "@context"}] if len(compacted) > 1 else []
    nodes = sorted(nodes, key=lambda n: (n.get("@id", "").startswith("_:"), n.get("@id", "")))
    return json.dumps(
        {"@context": compacted["@context"], "@graph": nodes},
        indent=2,
        ensure_ascii=False,
    ) + "\n"
