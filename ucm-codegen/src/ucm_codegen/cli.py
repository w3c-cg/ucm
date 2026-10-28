"""
Command-line interface for ucm-codegen

Usage:
    ucm-codegen export   -o unified-care-model.ttl -o ucm-lifecycle-vocabularies.ttl -s ucm-core-shapes.ttl -l ucm-shapes-lint.ttl
    ucm-codegen lint     -o build/ucm-ontology.jsonld -s build/ucm-shapes.jsonld -l build/ucm-shapes-lint.jsonld
    ucm-codegen generate -o build/ucm-ontology.jsonld -s build/ucm-shapes.jsonld --fhir-mapping profiles/ucm-fhir-mapping.yaml
    ucm-codegen build    [-m ucm-build.yaml] [--strict]
    ucm-codegen validate -o build/ucm-ontology.jsonld -s build/ucm-shapes.jsonld -D data.ttl
    ucm-codegen extract  -o build/ucm-ontology.jsonld -s build/ucm-shapes.jsonld --output ir.json
    ucm-codegen info     -o build/ucm-ontology.jsonld -s build/ucm-shapes.jsonld
"""

import json
import sys
from pathlib import Path
from typing import Any, List, Optional, Sequence

import typer
import yaml
from rich.console import Console
from rich.table import Table

from .build import (
    REPORT, TARGETS, BuildLock, BuildManifest, TargetOutputs, add_report, build_diff, build_failed,
    build_targets, export_ir, make_lock, prune_outputs, read_json, write_if_changed,
)
from .content import Cache, changed_keys, short
from .builder import SpecBuilder, SpecBuildError
from .fhir_target import FhirMapping, FhirMappingError
from .generator import GenerationError
from .models import ApiProfile, LintFinding, Severity, ValidationReport
from .normalize import NormalizationError
from .parser import IRBoundaryError, export_jsonld, load_rdf
from .pipeline import Compilation, compile_ir
from .shacl import validate_data
from .utils import load_yaml_safe

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")

app = typer.Typer(
    name="ucm-codegen",
    help="JSON-LD to OpenAPI reference compiler for the Unified Care Model (UCM)",
    add_completion=False,
)
console = Console()

FORMATS = ["all", "openapi", "context", "postgres", "fhir", "report"]
SEVERITY_STYLE = {Severity.VIOLATION: "red", Severity.WARNING: "yellow", Severity.INFO: "dim"}

OntologyOpt = typer.Option(
    ..., "--ontology", "-o", exists=True, help="JSON-LD ontology export (repeatable)"
)
ShapesOpt = typer.Option(
    ..., "--shapes", "-s", exists=True, help="JSON-LD SHACL shapes export (repeatable)"
)
ShapesLintOpt = typer.Option(
    None, "--shapes-lint", "-l", exists=True, help="JSON-LD export of ucm-shapes-lint (shapes over the shapes)"
)


# ============= Helpers =============

def _fail(message: str) -> None:
    console.print(f"[bold red]✗ {message}[/bold red]")
    raise typer.Exit(1)


def _compile(
    ontology: List[Path],
    shapes: List[Path],
    shapes_lint: Optional[List[Path]],
    cache: Optional[Cache] = None,
) -> Compilation:
    try:
        with console.status("[bold green]Ingesting JSON-LD and normalizing..."):
            compilation = compile_ir(ontology, shapes, shapes_lint or (), cache=cache)
    except IRBoundaryError as e:
        _fail(str(e))
    except NormalizationError as e:
        console.print("[bold red]✗ The ontology or shapes failed IR validation:[/bold red]")
        for error in e.errors:
            console.print(f"  • {error}")
        raise typer.Exit(1)

    ir = compilation.ir
    constraint_count = sum(len(s.properties) + len(s.sparql) for s in ir.shapes)
    console.print(
        f"✓ Parsed {len(ir.classes)} classes, {len(ir.properties)} properties, "
        f"{len(ir.schemes)} concept schemes, {len(ir.shapes)} node shapes "
        f"({constraint_count} constraints)"
    )
    if not shapes_lint:
        console.print("[dim]  ucm-shapes-lint not supplied (-l): tier convention unchecked[/dim]")
    return compilation


def _print_findings(findings: List[LintFinding], verbose: bool = False) -> None:
    shown = [f for f in findings if verbose or f.severity != Severity.INFO]
    hidden = len(findings) - len(shown)
    if shown:
        table = Table(title="Ontology and shapes lint", show_header=True, header_style="bold cyan")
        table.add_column("Severity")
        table.add_column("Code", style="cyan")
        table.add_column("Subject", style="green")
        table.add_column("Message")
        for f in shown:
            style = SEVERITY_STYLE[f.severity]
            table.add_row(f"[{style}]{f.severity.value}[/{style}]", f.code, f.subject, f.message)
        console.print(table)
    if hidden:
        console.print(f"[dim]{hidden} informational findings hidden (use --verbose)[/dim]")


def _print_report(report: ValidationReport) -> None:
    table = Table(title="SHACL validation results", show_header=True, header_style="bold cyan")
    table.add_column("Severity")
    table.add_column("Focus node", style="green")
    table.add_column("Path", style="cyan")
    table.add_column("Message")
    for r in report.results:
        style = SEVERITY_STYLE[r.severity]
        table.add_row(
            f"[{style}]{r.severity.value}[/{style}]",
            r.focus_node,
            r.result_path or "",
            r.message + (f" (value: {r.value})" if r.value else ""),
        )
    console.print(table)


def _load_model(model: Any, path: Optional[Path], label: str) -> Any:
    try:
        return model.model_validate(load_yaml_safe(path) if path else {})
    except Exception as e:  # pydantic.ValidationError or yaml.YAMLError
        _fail(f"{label} {path.name if path else ''} is invalid:\n{e}")


# ============= Commands =============

@app.command()
def export(
    ontology: List[Path] = typer.Option(
        ..., "--ontology", "-o", exists=True, help="Ontology and vocabulary sources (Turtle, RDF/XML, ...)"
    ),
    shapes: List[Path] = typer.Option(..., "--shapes", "-s", exists=True, help="SHACL shapes sources"),
    shapes_lint: Optional[List[Path]] = typer.Option(
        None, "--shapes-lint", "-l", exists=True, help="ucm-shapes-lint source"
    ),
    output_dir: Path = typer.Option(Path("./build"), "--output-dir", "-d", help="Where to write the JSON-LD IR"),
):
    """
    Export RDF sources to the JSON-LD IR

    The rest of the toolchain only reads JSON-LD. Any JSON-LD 1.1 export
    (Protégé, ROBOT) works; this command produces a deterministic one.

    Example:
        ucm-codegen export -o unified-care-model.ttl -o ucm-lifecycle-vocabularies.ttl \\
            -s ucm-core-shapes.ttl -l ucm-shapes-lint.ttl
    """
    console.print("[bold blue]UCM JSON-LD Export[/bold blue]")
    output_dir.mkdir(parents=True, exist_ok=True)
    jobs = [("ontology", ontology, "ucm-ontology.jsonld"), ("shapes", shapes, "ucm-shapes.jsonld")]
    if shapes_lint:
        jobs.append(("shapes lint", shapes_lint, "ucm-shapes-lint.jsonld"))
    for label, sources, name in jobs:
        with console.status(f"[bold green]Exporting {label}..."):
            text = export_jsonld(sources)
        target = output_dir / name
        target.write_text(text, encoding="utf-8")
        nodes = len(json.loads(text)["@graph"])
        console.print(f"✓ {label}: {', '.join(s.name for s in sources)} → {target} ({nodes} nodes)")


@app.command()
def generate(
    ontology: List[Path] = OntologyOpt,
    shapes: List[Path] = ShapesOpt,
    shapes_lint: Optional[List[Path]] = ShapesLintOpt,
    output_dir: Path = typer.Option(Path("./generated"), "--output-dir", "-d", help="Output directory"),
    format: str = typer.Option("all", "--format", "-f", help="Target: all|openapi|context|postgres|fhir|report"),
    profile: Optional[Path] = typer.Option(
        None, "--profile", "-p", exists=True, help="Optional API profile (servers, exclusions)"
    ),
    fhir_mapping: Optional[Path] = typer.Option(
        None, "--fhir-mapping", exists=True, help="UCM → FHIR mapping overlay (required for -f fhir)"
    ),
    examples: Optional[List[Path]] = typer.Option(
        None, "--examples", "-e", exists=True, help="Instance data compacted into schema examples"
    ),
    strict: bool = typer.Option(False, "--strict", help="Fail on lint warnings, not only violations"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show informational lint findings"),
):
    """
    Generate targets from the JSON-LD IR

    Targets:
        openapi   OpenAPI 3.1 reference (with the JSON-LD context)
        context   JSON-LD context only
        postgres  SQLAlchemy models + Alembic migration
        fhir      UCM ⇄ FHIR R4 adapter (needs --fhir-mapping)
        report    static HTML report (validates --examples against the shapes)

    Example:
        ucm-codegen generate -o build/ucm-ontology.jsonld -s build/ucm-shapes.jsonld \\
            -l build/ucm-shapes-lint.jsonld -e ../ucm-core-shapes-example.ttl \\
            -p profiles/ucm-api-profile.yaml --fhir-mapping profiles/ucm-fhir-mapping.yaml
    """
    if format not in FORMATS:
        _fail(f"Unknown format {format!r}; choose one of {', '.join(FORMATS)}")
    if format == "fhir" and fhir_mapping is None:
        _fail("-f fhir needs --fhir-mapping")

    console.print("[bold blue]UCM Code Generator[/bold blue]")
    compilation = _compile(ontology, shapes, shapes_lint)
    _print_findings(compilation.findings, verbose)
    if compilation.has(Severity.VIOLATION) or (strict and compilation.has(Severity.WARNING)):
        _fail("Lint failed; fix the findings above" + (" (--strict)" if strict else ""))

    targets = TARGETS if format == "all" else ((format, "context") if format == "openapi" else (format,))
    outputs = _render(compilation, profile, fhir_mapping, examples or [], targets)
    console.print()
    for written in outputs.write(output_dir):
        console.print(f"✓ Generated {written}")
    if format == "all" and fhir_mapping is None:
        console.print("[dim]  FHIR adapter skipped (no --fhir-mapping)[/dim]")
    console.print()
    console.print(f"[bold green]✓ Generation complete: {len(outputs.files)} files[/bold green]")


def _render(
    compilation: Compilation,
    profile: Optional[Path],
    fhir_mapping: Optional[Path],
    examples: List[Path],
    targets: Sequence[str],
    cache: Optional[Cache] = None,
    defer_report: bool = False,
) -> TargetOutputs:
    """Build targets in memory, reporting failures the way every command does"""
    api_profile = _load_model(ApiProfile, profile, "Profile")
    mapping = _load_model(FhirMapping, fhir_mapping, "FHIR mapping") if fhir_mapping else None
    try:
        with console.status("[bold green]Rendering targets..."):
            outputs = build_targets(
                compilation, api_profile, mapping, examples, targets, cache=cache, defer_report=defer_report
            )
    except SpecBuildError as e:
        _fail(str(e))
    except FhirMappingError as e:
        console.print("[bold red]✗ FHIR mapping does not match the ontology:[/bold red]")
        for error in e.errors:
            console.print(f"  • {error}")
        raise typer.Exit(1)
    except GenerationError as e:
        _fail(str(e))

    spec = outputs.spec
    console.print(f"✓ Mapped {len(spec.resources)} resources, {len(spec.operations)} operations, "
                  f"{len(spec.schemas)} class schemas")
    if examples:
        console.print(f"✓ Compacted {sum(len(s.examples) for s in spec.schemas)} example nodes")
        for warning in outputs.example_warnings:
            console.print(f"  [yellow]⚠ {warning}[/yellow]")
    if outputs.sql:
        console.print(f"✓ Postgres: {len(outputs.sql.tables)} tables, "
                      f"{len(outputs.sql.associations)} association tables, revision {outputs.sql.revision}")
    if outputs.adapter:
        console.print(f"✓ FHIR: {len(outputs.adapter['resources'])} UCM classes mapped to R4")
    return outputs


@app.command()
def build(
    manifest: Path = typer.Option(
        Path("ucm-build.yaml"), "--manifest", "-m", exists=True, help="Build manifest (sources and outputs)"
    ),
    strict: bool = typer.Option(False, "--strict", help="Fail on warnings too (lint and example SHACL)"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Recompute every stage (still writes the lockfile)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show informational lint findings"),
):
    """
    Export, lint, validate and generate everything from a build manifest

    Steps: TTL → JSON-LD IR (ir-dir) → IR + lint → examples against the
    shapes → OpenAPI, context, Postgres, FHIR and report.html (output-dir).
    Outputs are written even when checks fail, so the report shows why;
    the exit code is 1 on violations (and on warnings with --strict).

    Content addressing: stages are cached by input digest (cache-dir), and
    ucm-build.lock records source, IR node and output digests. Each build is
    diffed against the previous lock, and outputs the previous build wrote
    but this one no longer produces are removed.

    Example (CI):
        ucm-codegen build --strict
    """
    console.print("[bold blue]UCM Build[/bold blue]")
    try:
        plan = BuildManifest.load(manifest)
    except Exception as e:  # pydantic.ValidationError or yaml.YAMLError
        _fail(f"Manifest {manifest} is invalid:\n{e}")
    missing = plan.missing()
    if missing:
        _fail("Manifest names missing files: " + ", ".join(str(p) for p in missing))
    cache = None if no_cache else Cache(plan.cache_dir)

    with console.status("[bold green]Exporting the JSON-LD IR..."):
        ir_files = export_ir(plan, cache)
    console.print(f"✓ Exported IR to {plan.ir_dir}")

    compilation = _compile(ir_files["ontology"], ir_files["shapes"], ir_files["shapes-lint"], cache)
    _print_findings(compilation.findings, verbose)

    outputs = _render(
        compilation, plan.profile, plan.fhir_mapping, plan.examples, TARGETS, cache, defer_report=True
    )
    if outputs.validation is not None:
        if outputs.validation.results:
            _print_report(outputs.validation)
        else:
            console.print("✓ Examples conform to the UCM shapes")

    # Content addressing: diff against the previous lock, then record this build
    ir_snapshot = plan.ir_dir / "ucm-ir.json"
    previous = BuildLock.read(plan.lockfile)
    previous_ir = read_json(ir_snapshot) if previous else None
    ir_json = compilation.ir.model_dump(mode="json")
    lock = make_lock(plan, compilation, outputs)
    diff = build_diff(previous, previous_ir, lock, ir_json)
    add_report(outputs, compilation, diff, lock)

    written = outputs.write(plan.output_dir)
    removed, kept = prune_outputs(plan.output_dir, previous, lock)
    write_if_changed(ir_snapshot, json.dumps(ir_json, indent=2, ensure_ascii=False) + "\n")
    write_if_changed(plan.lockfile, lock.dumps())

    if cache is not None:
        hits, misses = len(cache.hits), len(cache.misses)
        console.print(f"✓ Cache: {hits} hits, {misses} misses ({plan.cache_dir})")
    console.print(f"✓ Wrote {len(written)} changed files to {plan.output_dir}; "
                  f"{len(outputs.files) - len(written)} unchanged")
    for path in removed:
        console.print(f"  [dim]removed stale output {path.relative_to(plan.output_dir)}[/dim]")
    for path in kept:
        console.print(f"  [yellow]⚠ kept {path.relative_to(plan.output_dir)}: no longer generated, "
                      f"but edited since the last build[/yellow]")

    console.print(f"✓ IR root {short(lock.ir_root)} ({len(lock.nodes)} nodes); lock {plan.relative(plan.lockfile)}")
    if diff.first_build:
        console.print("  First build: nothing to compare against")
    elif diff.unchanged:
        console.print("  No changes since the previous build")
    else:
        added, deleted, changed = changed_keys(diff.nodes)
        console.print(f"  Since the previous build: {added} added, {deleted} removed, {changed} changed nodes; "
                      f"{len(diff.outputs)} generated files differ")
        for change in diff.nodes[:12]:
            fields = ", ".join(f.field for f in change.fields)
            console.print(f"    {change.kind:<8} {change.key}" + (f"  [dim]({fields})[/dim]" if fields else ""))
        if len(diff.nodes) > 12:
            console.print(f"    … {len(diff.nodes) - 12} more in the report")
    console.print(f"  Report: {plan.output_dir / REPORT}")

    reasons = build_failed(compilation, outputs, strict)
    console.print()
    if reasons:
        _fail("Build failed: " + "; ".join(reasons))
    console.print("[bold green]✓ Build passed[/bold green]")


@app.command()
def lint(
    ontology: List[Path] = OntologyOpt,
    shapes: List[Path] = ShapesOpt,
    shapes_lint: Optional[List[Path]] = ShapesLintOpt,
    strict: bool = typer.Option(False, "--strict", help="Exit non-zero on warnings"),
    verbose: bool = typer.Option(True, "--verbose/--quiet", help="Show informational findings"),
):
    """
    Check the ontology and shapes for consistency

    Checks:
    - Shapes graph conforms to SHACL-SHACL, and to ucm-shapes-lint when given (-l)
    - No shape's ucmsh:tier contradicts its sh:severity (Pydantic IR validation)
    - Referenced terms are declared, in the namespace that references them
    - sh:class agrees with rdfs:range
    - Datatype unions and domainless properties the targets have to approximate
    """
    console.print("[bold blue]UCM Lint[/bold blue]")
    compilation = _compile(ontology, shapes, shapes_lint)
    _print_findings(compilation.findings, verbose)
    if compilation.has(Severity.VIOLATION) or (strict and compilation.has(Severity.WARNING)):
        raise typer.Exit(1)
    if not compilation.findings:
        console.print("[bold green]✓ No findings[/bold green]")


@app.command()
def validate(
    ontology: List[Path] = OntologyOpt,
    shapes: List[Path] = ShapesOpt,
    data: List[Path] = typer.Option(
        ..., "--data", "-D", exists=True, help="Instance data (JSON-LD, Turtle, ...) to validate"
    ),
    inference: str = typer.Option("none", "--inference", help="none|rdfs|owlrl|both"),
    report_path: Optional[Path] = typer.Option(None, "--report", help="Write the report as JSON"),
):
    """
    Validate instance data against the UCM shapes (PySHACL)

    The ontology is merged into the data graph, so sh:class sees subclasses
    and SPARQL constraints see the concept schemes. Violations fail;
    warnings (Recommended tier) pass with a notice.
    """
    console.print("[bold blue]UCM Validator[/bold blue]")
    compilation = _compile(ontology, shapes, None)
    with console.status("[bold green]Running SHACL validation..."):
        report = validate_data(
            load_rdf(data), compilation.shapes, compilation.ontology,
            inference=inference, shapes_ns=compilation.shapes_ns,  # type: ignore[arg-type]
        )
    if report_path:
        report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    violations = report.by_severity(Severity.VIOLATION)
    if report.results:
        _print_report(report)
    if violations:
        console.print(f"[bold red]✗ Validation failed: {len(violations)} violations[/bold red]")
        raise typer.Exit(1)
    if report.results:
        console.print("[bold yellow]⚠ Validation passed with warnings[/bold yellow]")
    else:
        console.print("[bold green]✓ Data conforms to the UCM shapes[/bold green]")


@app.command()
def extract(
    ontology: List[Path] = OntologyOpt,
    shapes: List[Path] = ShapesOpt,
    output: Path = typer.Option(Path("ucm-ir.json"), "--output", help="Output file for the IR"),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json|yaml"),
):
    """
    Extract the normalized IR (Pydantic) without generating outputs

    Useful for debugging the mapping and diffing ontology versions.
    """
    console.print("[bold blue]IR Extractor[/bold blue]")
    compilation = _compile(ontology, shapes, None)
    data: Any = compilation.ir.model_dump(mode="json")
    if format == "yaml":
        output.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    else:
        output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    console.print(f"[green]IR written to: {output}[/green]")


@app.command()
def info(
    ontology: List[Path] = OntologyOpt,
    shapes: List[Path] = ShapesOpt,
    profile: Optional[Path] = typer.Option(None, "--profile", "-p", exists=True),
):
    """
    Display information about the ontology and the API it compiles to
    """
    console.print("[bold blue]Ontology Info[/bold blue]")
    compilation = _compile(ontology, shapes, None)
    ir = compilation.ir
    builder = SpecBuilder(ir, _load_model(ApiProfile, profile, "Profile"))
    console.print()
    console.print(f"[bold]Ontology:[/bold] {ir.label} <{ir.iri}>")
    console.print(f"[bold]Version:[/bold] {ir.version or 'n/a'}")
    for source in ir.sources:
        console.print(f"[bold]Source:[/bold] {source.file} ({source.triples} triples) {source.digest}")
    console.print()

    table = Table(title="Statistics", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="green")
    props = list(ir.properties.values())
    table.add_row("Classes", str(len(ir.classes)))
    table.add_row("Object properties", str(sum(p.kind == "object" for p in props)))
    table.add_row("Datatype properties", str(sum(p.kind == "datatype" for p in props)))
    table.add_row("Concept schemes", str(len(ir.schemes)))
    table.add_row("Concepts", str(sum(len(s.concepts) for s in ir.schemes.values())))
    table.add_row("Node shapes", str(len(ir.shapes)))
    table.add_row("Property constraints", str(sum(len(s.properties) for s in ir.shapes)))
    table.add_row("SPARQL constraints", str(sum(len(s.sparql) for s in ir.shapes)))
    table.add_row("Lint findings", str(len(compilation.findings)))
    console.print(table)
    console.print()

    resources = Table(title="Resources", show_header=True, header_style="bold cyan")
    resources.add_column("Resource", style="cyan")
    resources.add_column("Path", style="green")
    resources.add_column("Subclasses", justify="right")
    for root in builder.resource_roots():
        res = builder.resource(root)
        resources.add_row(res.name, res.collection_path, str(len(res.type_terms) - 1))
    console.print(resources)


if __name__ == "__main__":
    app()
