"""
Examples from instance data

Each typed node in a data graph (e.g., ucm-core-shapes-example.ttl) is
framed with the generated JSON-LD context: its concise bounded description
is embedded, references to other nodes stay IRIs. The result is what the
API would exchange for that node, so it doubles as a check that the
context and the schemas agree with conformant data.
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Callable, Dict, List, Tuple

from pyld import jsonld
from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from .models import OntologyIR


# Compaction writes a value whose term is coerced to one of these datatypes as
# its lexical string ("false", "18"). The schemas, like any JSON client, expect
# native JSON, which expands back to the same typed literal under the coercion.
NATIVE: Dict[str, Callable[[str], Any]] = {
    "xsd:boolean": lambda v: v.strip() in ("true", "1"),
    "xsd:integer": int,
    "xsd:int": int,
    "xsd:long": int,
    "xsd:nonNegativeInteger": int,
    "xsd:positiveInteger": int,
    "xsd:double": float,
    "xsd:float": float,
}


def _native(value: Any, context: Dict[str, Any]) -> Any:
    """Turn lexical strings of coerced boolean and numeric terms into JSON values"""
    if isinstance(value, list):
        return [_native(v, context) for v in value]
    if not isinstance(value, dict):
        return value
    out: Dict[str, Any] = {}
    for key, item in value.items():
        entry = context.get(key)
        convert = NATIVE.get(entry.get("@type", "")) if isinstance(entry, dict) else None
        if convert is not None:
            items = item if isinstance(item, list) else [item]
            converted = [convert(v) if isinstance(v, str) else v for v in items]
            out[key] = converted if isinstance(item, list) else converted[0]
        else:
            out[key] = _native(item, context)
    return out


def _sorted_sets(value: Any) -> Any:
    """Sort multi-valued properties: RDF values are a set, and pyld lists them in
    hash order, which varies run to run (PYTHONHASHSEED)"""
    if isinstance(value, dict):
        return {k: _sorted_sets(v) for k, v in value.items()}
    if isinstance(value, list):
        items = [_sorted_sets(v) for v in value]
        return sorted(items, key=lambda v: json.dumps(v, sort_keys=True, default=str))
    return value


def frame_node(data: Graph, subject: URIRef, context: Dict[str, Any]) -> Dict[str, Any]:
    """Compact one node and its blank-node closure with the context"""
    description = data.cbd(subject)
    expanded = jsonld.from_rdf(description.serialize(format="nt"), {"format": "application/n-quads"})
    framed = jsonld.frame(
        expanded,
        {"@context": context, "@id": str(subject)},
        {"embed": "@always", "omitGraph": True},
    )
    node = _sorted_sets(_native({k: v for k, v in framed.items() if k != "@context"}, context))
    if isinstance(node.get("@type"), list):
        # rdf:type is a set in the data; pyld iterates it in hash order, which varies
        # run to run (PYTHONHASHSEED) and made the generated examples non-reproducible
        node["@type"] = sorted(node["@type"])
    return node


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
