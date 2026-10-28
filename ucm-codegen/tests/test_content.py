"""Content addressing: digests, node identity, stage cache, semantic diff"""

import ucm_codegen.content as content
from ucm_codegen.content import (
    Cache, diff_nodes, digest_json, digest_text, merkle_root, node_contents, node_digests,
    toolchain_digest,
)
from ucm_codegen.pipeline import compile_ir

UCM = "urn:w3c:cg:ucm#"


def test_digests_ignore_line_endings_and_key_order():
    assert digest_text("a\r\nb\r\n") == digest_text("a\nb\n")
    assert digest_text("a\nb") != digest_text("a\nc")
    assert digest_json({"b": 1, "a": [2, 3]}) == digest_json({"a": [2, 3], "b": 1})
    assert digest_text("x").startswith("sha256:") and len(digest_text("x")) == 71


def test_toolchain_digest_is_stable():
    assert toolchain_digest() == toolchain_digest()
    assert toolchain_digest().startswith("sha256:")


def test_every_ir_node_is_addressed(compilation):
    nodes = node_digests(compilation.ir.model_dump(mode="json"))
    ir = compilation.ir
    assert len(nodes) == 1 + len(ir.classes) + len(ir.properties) + len(ir.schemes) + len(ir.shapes)
    assert {"ontology", "class:ucm:Participation", "property:ucm:validFrom",
            "scheme:ucm:LifecycleState", "shape:ucmsh:ParticipationShape"} <= set(nodes)


def test_node_digests_are_reproducible(ir_files, compilation):
    again = compile_ir(*([p] for p in ir_files))
    before = node_digests(compilation.ir.model_dump(mode="json"))
    after = node_digests(again.ir.model_dump(mode="json"))
    assert before == after
    assert merkle_root(before) == merkle_root(after)


def test_blank_node_shapes_are_named_by_content(compilation):
    ir = compilation.ir.model_dump(mode="json")
    shape = dict(ir["shapes"][0], iri=None)
    keys = set(node_contents({**ir, "shapes": [shape]}))
    (key,) = [k for k in keys if k.startswith("shape:_:")]
    edited = dict(shape, message="different")
    (other,) = [k for k in node_contents({**ir, "shapes": [edited]}) if k.startswith("shape:_:")]
    assert key != other  # identity follows content
    assert key == next(k for k in node_contents({**ir, "shapes": [shape]}) if k.startswith("shape:_:"))


def test_diff_pins_down_the_regressed_spec(compilation, regressed_compilation):
    """The two spec defects show up as exactly three node changes"""
    old = regressed_compilation.ir.model_dump(mode="json")
    new = compilation.ir.model_dump(mode="json")
    changes = diff_nodes(node_digests(old), node_digests(new), node_contents(old), node_contents(new))
    assert [(c.kind, c.key) for c in changes] == [  # sorted by node key
        ("changed", "property:ucm:acceptsRequest"),
        ("removed", "scheme:http://mdixinc.com/ucm#LifecycleState"),
        ("added", "scheme:ucm:LifecycleState"),
    ]
    (accepts,) = [c for c in changes if c.kind == "changed"]
    (field,) = accepts.fields
    assert (field.field, field.before, field.after) == (
        "range", UCM + "ParticipationContext", UCM + "Participation"
    )


def test_compile_cache_hits_and_matches(ir_files, compilation, tmp_path):
    cache = Cache(tmp_path / "cache")
    cold = compile_ir(*([p] for p in ir_files), cache=cache)
    assert "compile" in cache.misses and "compile" not in cache.hits
    warm = compile_ir(*([p] for p in ir_files), cache=cache)
    assert "compile" in cache.hits and "ingest" in cache.hits
    assert warm.ir == cold.ir == compilation.ir
    assert warm.findings == cold.findings
    assert warm.shapes_ns == cold.shapes_ns
    assert len(warm.ontology) == len(cold.ontology)


def test_cache_keys_include_the_toolchain(ir_files, tmp_path, monkeypatch):
    cache = Cache(tmp_path / "cache")
    compile_ir(*([p] for p in ir_files), cache=cache)
    monkeypatch.setattr(content, "toolchain_digest", lambda: "sha256:edited-toolchain")
    cache.hits.clear()
    cache.misses.clear()
    compile_ir(*([p] for p in ir_files), cache=cache)
    assert "compile" in cache.misses and not cache.hits


def test_cache_put_is_atomic(tmp_path):
    cache = Cache(tmp_path)
    assert cache.get_json("stage", "k") is None and cache.misses == ["stage"]
    cache.put_json("stage", "k", {"a": 1})
    assert cache.get_json("stage", "k") == {"a": 1}
    assert not list(tmp_path.rglob("*.tmp"))
