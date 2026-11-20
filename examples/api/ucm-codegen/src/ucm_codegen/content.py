"""
Content addressing with hashlib

Every artifact the toolchain reads or writes is named by a sha256 of its
content: spec sources, the JSON-LD IR, each IR node (class, property, concept
scheme, shape), each generated file, and the toolchain itself. Digests are
taken over text with line endings normalized, so a Windows checkout and a
Linux CI runner agree.

On top of the digests:
  Cache        stage results keyed by the digests of their inputs
  node digests per-node identity for semantic diffs; blank-node shapes are
               named by their content, so they keep a stable identity
  diff_nodes   what changed between two builds, down to the field
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel, Field

from . import __version__

PREFIX = "sha256:"


# ============= Digests =============

def normalize_newlines(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def digest_bytes(data: bytes) -> str:
    return PREFIX + hashlib.sha256(normalize_newlines(data)).hexdigest()


def digest_text(text: str) -> str:
    return digest_bytes(text.encode("utf-8"))


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def canonical_json(value: Any) -> str:
    """One serialization per value: sorted keys, no insignificant whitespace"""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def digest_json(value: Any) -> str:
    return digest_text(canonical_json(value))


def short(digest: Optional[str], length: int = 12) -> str:
    return (digest or "").removeprefix(PREFIX)[:length]


@lru_cache(maxsize=1)
def toolchain_digest() -> str:
    """Fingerprint of the package's code and templates: outputs depend on both"""
    package = Path(__file__).resolve().parent
    files = sorted(
        p for p in package.rglob("*")
        if p.is_file() and p.suffix in {".py", ".j2"} and "__pycache__" not in p.parts
    )
    entries = [(p.relative_to(package).as_posix(), digest_file(p)) for p in files]
    return digest_json({"version": __version__, "files": entries})


# ============= Stage cache =============

class Cache:
    """Content-addressed store: <root>/<stage>/<key>.json (or .nq); no eviction"""

    def __init__(self, root: Path):
        self.root = root
        self.hits: List[str] = []
        self.misses: List[str] = []

    @staticmethod
    def key(*parts: Any) -> str:
        return short(digest_json([toolchain_digest(), *parts]), 32)

    def _path(self, stage: str, key: str, suffix: str) -> Path:
        return self.root / stage / f"{key}{suffix}"

    def get_text(self, stage: str, key: str, suffix: str = ".txt") -> Optional[str]:
        path = self._path(stage, key, suffix)
        if path.exists():
            self.hits.append(stage)
            return path.read_text(encoding="utf-8")
        self.misses.append(stage)
        return None

    def put_text(self, stage: str, key: str, text: str, suffix: str = ".txt") -> None:
        path = self._path(stage, key, suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(text, encoding="utf-8", newline="\n")
        temporary.replace(path)  # atomic: a crash never leaves a half-written entry

    def get_json(self, stage: str, key: str) -> Optional[Any]:
        text = self.get_text(stage, key, ".json")
        return json.loads(text) if text is not None else None

    def put_json(self, stage: str, key: str, value: Any) -> None:
        self.put_text(stage, key, json.dumps(value, ensure_ascii=False), ".json")


# ============= IR node digests =============

def _curie(iri: Optional[str], prefixes: Dict[str, str]) -> str:
    if not iri:
        return ""
    for prefix, namespace in sorted(prefixes.items(), key=lambda kv: -len(kv[1])):
        if iri.startswith(namespace) and len(iri) > len(namespace):
            return f"{prefix}:{iri[len(namespace):]}"
    return iri


def node_contents(ir: Dict[str, Any]) -> Dict[str, Any]:
    """IR (as JSON) → {node key: node content}. Works on any dumped IR, old or new."""
    prefixes = dict(ir.get("prefixes", {}))
    if ir.get("shapes_namespace"):
        prefixes[ir.get("shapes_prefix", "ucmsh")] = ir["shapes_namespace"]
    nodes: Dict[str, Any] = {
        "ontology": {k: ir.get(k) for k in ("iri", "namespace", "prefix", "label", "comment", "version", "prefixes")}
    }
    for kind, table in (("class", "classes"), ("property", "properties"), ("scheme", "schemes")):
        for iri, content in sorted(ir.get(table, {}).items()):
            nodes[f"{kind}:{_curie(iri, prefixes)}"] = content
    for shape in ir.get("shapes", []):
        name = _curie(shape.get("iri"), prefixes) or f"_:{short(digest_json(shape))}"
        nodes[f"shape:{name}"] = shape
    return nodes


def node_digests(ir: Dict[str, Any]) -> Dict[str, str]:
    return {key: digest_json(content) for key, content in node_contents(ir).items()}


def merkle_root(digests: Dict[str, str]) -> str:
    return digest_json(sorted(digests.items()))


# ============= Semantic diff =============

class FieldChange(BaseModel):
    field: str
    before: Optional[str] = None
    after: Optional[str] = None
    added: List[str] = Field(default_factory=list)
    removed: List[str] = Field(default_factory=list)


class NodeChange(BaseModel):
    key: str
    kind: str = Field(description="added, removed or changed")
    fields: List[FieldChange] = Field(default_factory=list)


class OutputChange(BaseModel):
    path: str
    kind: str


class BuildDiff(BaseModel):
    previous: Optional[str] = Field(None, description="IR root digest of the previous build")
    nodes: List[NodeChange] = Field(default_factory=list)
    outputs: List[OutputChange] = Field(default_factory=list)

    @property
    def first_build(self) -> bool:
        return self.previous is None

    @property
    def unchanged(self) -> bool:
        return not self.first_build and not self.nodes and not self.outputs


def _brief(value: Any, width: int = 90) -> str:
    text = value if isinstance(value, str) else canonical_json(value)
    return text if len(text) <= width else text[: width - 1] + "…"


def _label(item: Any) -> str:
    """Readable name for a list item (shape constraints are dicts)"""
    if isinstance(item, dict):
        for key in ("iri", "term"):
            if item.get(key):
                return str(item[key]).rsplit("#", 1)[-1]
        if item.get("paths"):
            return "/".join(p.rsplit("#", 1)[-1] for p in item["paths"])
        if item.get("message"):
            return _brief(item["message"], 60)
        return short(digest_json(item))
    return _brief(item, 60)


def field_changes(before: Any, after: Any) -> List[FieldChange]:
    if not isinstance(before, dict) or not isinstance(after, dict):
        return [FieldChange(field="(value)", before=_brief(before), after=_brief(after))]
    changes = []
    for name in sorted(set(before) | set(after)):
        old, new = before.get(name), after.get(name)
        if old == new:
            continue
        if isinstance(old, list) and isinstance(new, list):
            old_items = {digest_json(i): i for i in old}
            new_items = {digest_json(i): i for i in new}
            changes.append(FieldChange(
                field=name,
                added=[_label(new_items[d]) for d in new_items if d not in old_items],
                removed=[_label(old_items[d]) for d in old_items if d not in new_items],
            ))
        else:
            changes.append(FieldChange(
                field=name,
                before=None if old is None else _brief(old),
                after=None if new is None else _brief(new),
            ))
    return changes


def diff_nodes(
    before: Optional[Dict[str, str]],
    after: Dict[str, str],
    before_contents: Optional[Dict[str, Any]] = None,
    after_contents: Optional[Dict[str, Any]] = None,
) -> List[NodeChange]:
    """Changed nodes by digest; field detail when both contents are known"""
    if before is None:
        return []
    changes = []
    for key in sorted(set(before) | set(after)):
        if key not in before:
            changes.append(NodeChange(key=key, kind="added"))
        elif key not in after:
            changes.append(NodeChange(key=key, kind="removed"))
        elif before[key] != after[key]:
            fields: List[FieldChange] = []
            if before_contents and after_contents and key in before_contents and key in after_contents:
                fields = field_changes(before_contents[key], after_contents[key])
            changes.append(NodeChange(key=key, kind="changed", fields=fields))
    return changes


def diff_outputs(before: Optional[Dict[str, str]], after: Dict[str, str]) -> List[OutputChange]:
    if before is None:
        return []
    return [
        OutputChange(path=path, kind="added" if path not in before else "removed" if path not in after else "changed")
        for path in sorted(set(before) | set(after))
        if before.get(path) != after.get(path)
    ]


def changed_keys(changes: Iterable[NodeChange]) -> Tuple[int, int, int]:
    counts = {"added": 0, "removed": 0, "changed": 0}
    for change in changes:
        counts[change.kind] += 1
    return counts["added"], counts["removed"], counts["changed"]
