"""
One-shot builds: manifest → export → IR → lint → validate → targets → report

The manifest (ucm-build.yaml) names the spec sources once, relative to the
manifest itself, so CI and local runs are both `ucm-codegen build`, and
moving the toolchain into another repository means editing one file.

Builds are content-addressed (content.py):
  - export, ingest, compile and example validation are cached by the digests
    of their inputs plus the toolchain's own digest
  - ucm-build.lock records source, IR, per-node and output digests; the next
    build diffs against it, and outputs a previous build wrote but this one
    no longer produces are removed (only if nobody edited them since)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field
from rdflib import Graph

from . import __version__
from .builder import SpecBuilder
from .content import (
    BuildDiff, Cache, diff_nodes, diff_outputs, digest_file, digest_text,
    merkle_root, node_contents, node_digests, toolchain_digest,
)
from .examples import build_examples
from .fhir_target import FhirCompiler, FhirMapping
from .generator import Generator
from .models import ApiProfile, OpenAPISpec, Severity, ValidationReport
from .parser import export_jsonld, load_rdf
from .pipeline import Compilation
from .report import ReportBuilder
from .shacl import validate_data
from .sql_target import SqlBuilder, SqlSchema
from .utils import load_yaml_safe

TARGETS = ("openapi", "context", "postgres", "fhir", "report")
REPORT = "report.html"
LOCK_VERSION = 1


class BuildManifest(BaseModel):
    """ucm-build.yaml: where the spec lives and where outputs go"""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    ontology: List[Path]
    shapes: List[Path]
    shapes_lint: List[Path] = Field(default_factory=list, alias="shapes-lint")
    examples: List[Path] = Field(default_factory=list)
    profile: Optional[Path] = None
    fhir_mapping: Optional[Path] = Field(None, alias="fhir-mapping")
    ir_dir: Path = Field(Path("build"), alias="ir-dir")
    output_dir: Path = Field(Path("generated"), alias="output-dir")
    cache_dir: Optional[Path] = Field(None, alias="cache-dir", description="Default: <ir-dir>/.cache")
    lockfile: Path = Path("ucm-build.lock")
    base: Path = Field(Path("."), exclude=True, description="Directory of the manifest file")

    @classmethod
    def load(cls, path: Path) -> "BuildManifest":
        manifest = cls.model_validate(load_yaml_safe(path))
        base = path.resolve().parent

        def resolve(p: Path) -> Path:
            return p if p.is_absolute() else (base / p).resolve()

        ir_dir = resolve(manifest.ir_dir)
        return manifest.model_copy(update={
            "ontology": [resolve(p) for p in manifest.ontology],
            "shapes": [resolve(p) for p in manifest.shapes],
            "shapes_lint": [resolve(p) for p in manifest.shapes_lint],
            "examples": [resolve(p) for p in manifest.examples],
            "profile": resolve(manifest.profile) if manifest.profile else None,
            "fhir_mapping": resolve(manifest.fhir_mapping) if manifest.fhir_mapping else None,
            "ir_dir": ir_dir,
            "output_dir": resolve(manifest.output_dir),
            "cache_dir": resolve(manifest.cache_dir) if manifest.cache_dir else ir_dir / ".cache",
            "lockfile": resolve(manifest.lockfile),
            "base": base,
        })

    def missing(self) -> List[Path]:
        paths = self.ontology + self.shapes + self.shapes_lint + self.examples
        paths += [p for p in (self.profile, self.fhir_mapping) if p]
        return [p for p in paths if not p.exists()]

    def relative(self, path: Path) -> str:
        """Path as recorded in the lockfile: relative to the manifest, POSIX separators"""
        return Path(os.path.relpath(path, self.base)).as_posix()

    def source_groups(self) -> Dict[str, List[Path]]:
        groups = {
            "ontology": self.ontology,
            "shapes": self.shapes,
            "shapes-lint": self.shapes_lint,
            "examples": self.examples,
            "profile": [self.profile] if self.profile else [],
            "fhir-mapping": [self.fhir_mapping] if self.fhir_mapping else [],
        }
        return {name: paths for name, paths in groups.items() if paths}


def write_if_changed(path: Path, text: str) -> bool:
    """Write LF text unless the file already holds exactly these bytes"""
    if path.exists() and path.read_bytes() == text.encode("utf-8"):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def export_ir(manifest: BuildManifest, cache: Optional[Cache] = None) -> Dict[str, List[Path]]:
    """Write the JSON-LD IR for every source group; returns the IR paths"""
    groups = {"ontology": manifest.ontology, "shapes": manifest.shapes, "shapes-lint": manifest.shapes_lint}
    written: Dict[str, List[Path]] = {}
    for name, sources in groups.items():
        if not sources:
            written[name] = []
            continue
        key = Cache.key("export", [(p.name, digest_file(p)) for p in sources])
        text = cache.get_text("export", key, ".jsonld") if cache else None
        if text is None:
            text = export_jsonld(sources)
            if cache:
                cache.put_text("export", key, text, ".jsonld")
        target = manifest.ir_dir / f"ucm-{name}.jsonld"
        write_if_changed(target, text)
        written[name] = [target]
    return written


@dataclass
class TargetOutputs:
    spec: OpenAPISpec
    files: Dict[str, str] = field(default_factory=dict)  # relative path → text
    sql: Optional[SqlSchema] = None
    adapter: Optional[Dict[str, Any]] = None
    validation: Optional[ValidationReport] = None
    example_warnings: List[str] = field(default_factory=list)

    def digests(self, include_report: bool = False) -> Dict[str, str]:
        return {
            path: digest_text(text)
            for path, text in sorted(self.files.items())
            if include_report or path != REPORT
        }

    def write(self, output_dir: Path) -> List[Path]:
        """Write every file; returns the ones whose content actually changed"""
        return [
            output_dir / relative
            for relative, text in self.files.items()
            if write_if_changed(output_dir / relative, text)
        ]


def build_targets(
    compilation: Compilation,
    profile: Optional[ApiProfile] = None,
    fhir_mapping: Optional[FhirMapping] = None,
    examples: Sequence[Path] = (),
    targets: Sequence[str] = TARGETS,
    cache: Optional[Cache] = None,
    defer_report: bool = False,
) -> TargetOutputs:
    """Render the requested targets in memory (FhirMappingError and GenerationError propagate).

    defer_report leaves report.html to add_report(), for callers that first
    need the other outputs' digests (the build diff).
    """
    ir = compilation.ir
    builder = SpecBuilder(ir, profile)
    spec = builder.build()
    generator = Generator()
    out = TargetOutputs(spec=spec)

    data: Optional[Graph] = load_rdf(list(examples)) if examples else None
    if data is not None:
        nodes, out.example_warnings = build_examples(data, ir, spec.context)
        SpecBuilder.attach_examples(spec, nodes)
        if "report" in targets:
            out.validation = _validate_examples(compilation, data, examples, cache)

    if {"openapi", "context"} & set(targets):
        out.files["context.jsonld"] = generator.generate_jsonld_context(spec)
    if "openapi" in targets:
        out.files["openapi.yaml"] = generator.generate_openapi_yaml(spec)
    if "postgres" in targets or "report" in targets:
        out.sql = SqlBuilder(ir, builder).build()
        if "postgres" in targets:
            for relative, text in generator.generate_postgres(out.sql).items():
                out.files[f"postgres/{relative}"] = text
    if fhir_mapping is not None and ("fhir" in targets or "report" in targets):
        out.adapter = FhirCompiler(ir, fhir_mapping, builder).compile()
        if "fhir" in targets:
            out.files["fhir/ucm_fhir_adapter.py"] = generator.generate_fhir_adapter(out.adapter)
    if "report" in targets and not defer_report:
        add_report(out, compilation)
    return out


def _validate_examples(
    compilation: Compilation, data: Graph, examples: Sequence[Path], cache: Optional[Cache]
) -> ValidationReport:
    key = Cache.key(
        "validate",
        [digest_file(p) for p in examples],
        [s.digest for s in compilation.ir.sources],
        compilation.shapes_ns,
    )
    cached = cache.get_json("validate", key) if cache else None
    if cached is not None:
        return ValidationReport.model_validate(cached)
    report = validate_data(data, compilation.shapes, compilation.ontology, shapes_ns=compilation.shapes_ns)
    if cache:
        cache.put_json("validate", key, report.model_dump(mode="json"))
    return report


def add_report(
    outputs: TargetOutputs,
    compilation: Compilation,
    diff: Optional[BuildDiff] = None,
    lock: Optional["BuildLock"] = None,
) -> None:
    files = sorted(set(outputs.files) | {REPORT})
    report = ReportBuilder(
        compilation, outputs.spec, outputs.sql, outputs.adapter, outputs.validation,
        outputs.example_warnings, files=files, diff=diff, lock=lock,
        output_digests=outputs.digests(),
    ).build()
    outputs.files[REPORT] = Generator().generate_report(report)


# ============= Lockfile =============

class BuildLock(BaseModel):
    """ucm-build.lock: what went in, what came out, all by content digest"""
    model_config = ConfigDict(populate_by_name=True)

    lock_version: int = Field(LOCK_VERSION, alias="lock-version")
    toolchain: Dict[str, str]
    sources: Dict[str, List[Dict[str, str]]]
    ir: List[Dict[str, Any]]
    ir_root: str = Field(alias="ir-root")
    nodes: Dict[str, str]
    outputs: Dict[str, str]

    def dumps(self) -> str:
        return json.dumps(self.model_dump(by_alias=True), indent=2, ensure_ascii=False) + "\n"

    @classmethod
    def read(cls, path: Path) -> Optional["BuildLock"]:
        if not path.exists():
            return None
        try:
            lock = cls.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except (ValueError, json.JSONDecodeError):
            return None  # unreadable or older format: treat as a first build
        return lock if lock.lock_version == LOCK_VERSION else None


def make_lock(manifest: BuildManifest, compilation: Compilation, outputs: TargetOutputs) -> BuildLock:
    nodes = node_digests(compilation.ir.model_dump(mode="json"))
    ir_sources = compilation.ir.sources + compilation.lint_sources
    return BuildLock(
        toolchain={"version": __version__, "digest": toolchain_digest()},
        sources={
            name: [{"path": manifest.relative(p), "content": digest_file(p)} for p in paths]
            for name, paths in manifest.source_groups().items()
        },
        ir=[
            {"file": s.file, "canonical": s.digest, "content": s.content, "triples": s.triples}
            for s in ir_sources
        ],
        ir_root=merkle_root(nodes),
        nodes=nodes,
        outputs=outputs.digests(),
    )


def build_diff(
    previous: Optional[BuildLock],
    previous_ir: Optional[Dict[str, Any]],
    lock: BuildLock,
    ir: Dict[str, Any],
) -> BuildDiff:
    if previous is None:
        return BuildDiff()
    return BuildDiff(
        previous=previous.ir_root,
        nodes=diff_nodes(
            previous.nodes, lock.nodes,
            node_contents(previous_ir) if previous_ir else None, node_contents(ir),
        ),
        outputs=diff_outputs(previous.outputs, lock.outputs),
    )


def prune_outputs(
    output_dir: Path, previous: Optional[BuildLock], lock: BuildLock
) -> Tuple[List[Path], List[Path]]:
    """Delete outputs the previous build wrote that this build no longer produces.

    A file is removed only if it still holds exactly what the previous build
    wrote; edited files are kept and reported.
    """
    removed: List[Path] = []
    kept: List[Path] = []
    if previous is None:
        return removed, kept
    for relative, digest in previous.outputs.items():
        if relative in lock.outputs:
            continue
        path = output_dir / relative
        if not path.exists():
            continue
        if digest_file(path) == digest:
            path.unlink()
            removed.append(path)
        else:
            kept.append(path)
    return removed, kept


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def build_failed(compilation: Compilation, outputs: Optional[TargetOutputs], strict: bool) -> List[str]:
    """Reasons the build should exit non-zero"""
    reasons = []
    findings = compilation.findings
    violations = sum(f.severity == Severity.VIOLATION for f in findings)
    warnings = sum(f.severity == Severity.WARNING for f in findings)
    if violations:
        reasons.append(f"{violations} lint violations")
    if strict and warnings:
        reasons.append(f"{warnings} lint warnings (--strict)")
    if outputs and outputs.validation:
        v = len(outputs.validation.by_severity(Severity.VIOLATION))
        w = len(outputs.validation.by_severity(Severity.WARNING))
        if v:
            reasons.append(f"{v} SHACL violations in the examples")
        if strict and w:
            reasons.append(f"{w} SHACL warnings in the examples (--strict)")
    return reasons
