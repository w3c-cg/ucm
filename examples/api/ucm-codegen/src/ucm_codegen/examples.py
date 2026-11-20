"""
Examples from instance data

Each typed node in a data graph (e.g., ucm-core-shapes-example.ttl) is
framed with the generated JSON-LD context: its concise bounded description
is embedded, references to other nodes stay IRIs. The result is what the
API would exchange for that node, so it doubles as a check that the
context and the schemas agree with conformant data.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple

from pyld import jsonld
from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from .models import OntologyIR


def frame_node(data: Graph, subject: URIRef, context: Dict[str, Any]) -> Dict[str, Any]:
    """Compact one node and its blank-node closure with the context"""
    description = data.cbd(subject)
    expanded = jsonld.from_rdf(description.serialize(format="nt"), {"format": "application/n-quads"})
    framed = jsonld.frame(
        expanded,
        {"@context": context, "@id": str(subject)},
        {"embed": "@always", "omitGraph": True},
    )
    return {k: v for k, v in framed.items() if k != "@context"}


def build_examples(
    data: Graph, ir: OntologyIR, context: Dict[str, Any]
) -> Tuple[Dict[str, List[Dict[str, Any]]], List[str]]:
    """Examples keyed by schema name, plus warnings about values the context cannot carry"""
    examples: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    warnings: List[str] = []

    for subject in sorted({s for s in data.subjects(RDF.type, None) if isinstance(s, URIRef)}, key=str):
        types = [str(t) for t in data.objects(subject, RDF.type) if str(t) in ir.classes]
        if not types:
            continue
        most_specific = max(sorted(types), key=lambda t: len(ir.ancestors(t)))
        node = frame_node(data, subject, context)

        stray = sorted(k for k in node if k.startswith(f"{ir.prefix}:"))
        if stray:
            warnings.append(
                f"{subject}: {', '.join(stray)} did not compact to a context term "
                f"(value datatype differs from the term's coercion)"
            )
        examples[ir.classes[most_specific].term].append(node)

    return dict(examples), warnings
