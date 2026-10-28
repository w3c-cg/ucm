"""One-shot build: manifest, targets, report, exit codes, lockfile"""

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from ucm_codegen.build import BuildLock, BuildManifest, build_failed, build_targets
from ucm_codegen.cli import app
from ucm_codegen.content import digest_file
from ucm_codegen.fhir_target import FhirMapping
from ucm_codegen.models import ApiProfile
from ucm_codegen.utils import load_yaml_safe

from .conftest import EXAMPLE_TTL, FHIR_MAPPING, ONTOLOGY_TTL, PROFILE, PROJECT, SHAPES_LINT_TTL, SHAPES_TTL


SHARED: dict = {}


@pytest.fixture(scope="session", autouse=True)
def shared_cache(tmp_path_factory):
    """One stage cache for every build in this module: content addressing makes sharing safe"""
    SHARED["cache"] = tmp_path_factory.mktemp("stage-cache")


def manifest_file(tmp_path: Path, ontology) -> Path:
    path = tmp_path / "ucm-build.yaml"
    path.write_text(yaml.safe_dump({
        "cache-dir": str(SHARED["cache"]),
        "ontology": [str(p) for p in ontology],
        "shapes": [str(p) for p in SHAPES_TTL],
        "shapes-lint": [str(p) for p in SHAPES_LINT_TTL],
        "examples": [str(EXAMPLE_TTL)],
        "profile": str(PROFILE),
        "fhir-mapping": str(FHIR_MAPPING),
        "ir-dir": "ir",
        "output-dir": "out",
    }), encoding="utf-8")
    return path


def test_repository_manifest_resolves():
    manifest = BuildManifest.load(PROJECT / "ucm-build.yaml")
    assert manifest.missing() == []
    assert manifest.ontology[0].name == "unified-care-model.ttl"
    assert manifest.output_dir == (PROJECT / "generated").resolve()


def outputs_for(compilation):
    return build_targets(
        compilation,
        ApiProfile.model_validate(load_yaml_safe(PROFILE)),
        FhirMapping.model_validate(load_yaml_safe(FHIR_MAPPING)),
        [EXAMPLE_TTL],
    )


def test_all_targets_and_report(compilation):
    outputs = outputs_for(compilation)
    assert {"openapi.yaml", "context.jsonld", "report.html", "fhir/ucm_fhir_adapter.py",
            "postgres/ucm_models.py"} <= set(outputs.files)
    assert outputs.validation is not None and outputs.validation.conforms
    assert build_failed(compilation, outputs, strict=True) == []

    html = outputs.files["report.html"]
    assert "Build passed" in html
    assert "participation.participating_entity" in html
    assert "Encounter.participant.individual" in html
    assert "Patient | Practitioner" in html


def test_report_flags_a_regressed_spec(regressed_compilation):
    outputs = outputs_for(regressed_compilation)
    html = outputs.files["report.html"]
    assert "Passed with warnings" in html
    assert "namespace-drift" in html
    assert "&lt;http://mdixinc.com/ucm#LifecycleState&gt;" in html  # escaped, not markup
    assert build_failed(regressed_compilation, outputs, strict=False) == []
    assert build_failed(regressed_compilation, outputs, strict=True) == [
        # namespace-drift, undeclared-term, range-mismatch
        "3 lint warnings (--strict), 1 of them namespace drift between spec files",
        "1 SHACL warnings in the examples (--strict) (likely caused by the namespace drift)",
    ]


def test_build_command(tmp_path):
    result = CliRunner().invoke(app, ["build", "-m", str(manifest_file(tmp_path, ONTOLOGY_TTL)), "--strict"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "ir" / "ucm-shapes-lint.jsonld").exists()
    assert (tmp_path / "out" / "report.html").exists()
    assert (tmp_path / "out" / "fhir" / "ucm_fhir_adapter.py").exists()


def test_build_command_fails_strict_but_still_reports(tmp_path, regressed_sources):
    result = CliRunner().invoke(app, ["build", "-m", str(manifest_file(tmp_path, regressed_sources)), "--strict"])
    assert result.exit_code == 1
    assert "Build failed" in result.output
    assert (tmp_path / "out" / "report.html").exists()


# ---------- Lockfile, diff and stale outputs ----------

def build(manifest: Path, *args: str):
    return CliRunner().invoke(app, ["build", "-m", str(manifest), *args])


def migrations(tmp_path: Path):
    return sorted(p.name for p in (tmp_path / "out" / "postgres" / "migrations" / "versions").glob("*.py"))


def test_lockfile_is_reproducible(tmp_path):
    manifest = manifest_file(tmp_path, ONTOLOGY_TTL)
    first = build(manifest)
    assert first.exit_code == 0, first.output
    assert "First build" in first.output
    lock_bytes = (tmp_path / "ucm-build.lock").read_bytes()

    second = build(manifest)
    assert "Cache: 8 hits, 0 misses" in second.output
    assert "No changes since the previous build" in second.output
    assert (tmp_path / "ucm-build.lock").read_bytes() == lock_bytes

    uncached = build(manifest, "--no-cache")
    assert "No changes since the previous build" in uncached.output
    assert (tmp_path / "ucm-build.lock").read_bytes() == lock_bytes


def test_lock_records_what_is_on_disk(tmp_path):
    manifest = manifest_file(tmp_path, ONTOLOGY_TTL)
    assert build(manifest).exit_code == 0
    lock = BuildLock.read(tmp_path / "ucm-build.lock")
    assert lock is not None
    assert "report.html" not in lock.outputs  # a view of the build, not an artifact
    for relative, digest in lock.outputs.items():
        path = tmp_path / "out" / relative
        assert digest_file(path) == digest, relative
        assert b"\r\n" not in path.read_bytes(), relative  # LF everywhere
    assert [s["path"].endswith(".ttl") for s in lock.sources["ontology"]] == [True, True]
    assert {e["file"] for e in lock.ir} == {"ucm-ontology.jsonld", "ucm-shapes.jsonld", "ucm-shapes-lint.jsonld"}
    snapshot = json.loads((tmp_path / "ir" / "ucm-ir.json").read_text(encoding="utf-8"))
    assert snapshot["iri"] == "urn:w3c:cg:ucm#"


def test_spec_change_is_diffed_and_stale_outputs_pruned(tmp_path, regressed_sources):
    assert build(manifest_file(tmp_path, ONTOLOGY_TTL)).exit_code == 0
    (before,) = migrations(tmp_path)

    result = build(manifest_file(tmp_path, regressed_sources))
    assert result.exit_code == 0, result.output
    assert "Since the previous build: 1 added, 1 removed, 1 changed nodes" in result.output
    assert "changed  property:ucm:acceptsRequest" in result.output
    assert "removed stale output" in result.output  # Rich wraps the path; the files are checked below

    (after,) = migrations(tmp_path)  # one head: the old revision is gone
    assert after != before
    report = (tmp_path / "out" / "report.html").read_text(encoding="utf-8")
    assert "acceptsRequest" in report and "ParticipationContext" in report
    assert "postgres/migrations/versions/" + before in report


def test_edited_stale_outputs_are_kept(tmp_path, regressed_sources):
    assert build(manifest_file(tmp_path, ONTOLOGY_TTL)).exit_code == 0
    (before,) = migrations(tmp_path)
    migration = tmp_path / "out" / "postgres" / "migrations" / "versions" / before
    migration.write_text(migration.read_text(encoding="utf-8") + "\n# local edit\n", encoding="utf-8")

    result = build(manifest_file(tmp_path, regressed_sources))
    assert "kept" in result.output and "edited since the last build" in result.output
    assert migration.exists()
    assert len(migrations(tmp_path)) == 2
