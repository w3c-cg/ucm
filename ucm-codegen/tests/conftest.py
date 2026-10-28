"""
Shared fixtures: the UCM specification files in the toolchain root are the
ontology under test. Each session exports them to the JSON-LD IR once.
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

import re

import pytest
import yaml
from rdflib import Graph

from ucm_codegen.builder import SpecBuilder
from ucm_codegen.examples import build_examples
from ucm_codegen.generator import Generator
from ucm_codegen.models import ApiProfile, OpenAPISpec
from ucm_codegen.parser import export_jsonld
from ucm_codegen.pipeline import Compilation, compile_ir
from ucm_codegen.utils import load_yaml_safe

PROJECT = Path(__file__).resolve().parents[1]
SPEC_ROOT = PROJECT.parent

ONTOLOGY_TTL = [SPEC_ROOT / "unified-care-model.ttl", SPEC_ROOT / "ucm-lifecycle-vocabularies.ttl"]
SHAPES_TTL = [SPEC_ROOT / "ucm-core-shapes.ttl"]
SHAPES_LINT_TTL = [SPEC_ROOT / "ucm-shapes-lint.ttl"]
EXAMPLE_TTL = SPEC_ROOT / "ucm-core-shapes-example.ttl"
PROFILE = PROJECT / "profiles" / "ucm-api-profile.yaml"
FHIR_MAPPING = PROJECT / "profiles" / "ucm-fhir-mapping.yaml"

# Two spec defects fixed in the TTL sources; the regressed_* fixtures put them
# back so the lints that found them stay covered:
#   - the lifecycle vocabulary declared its concepts under another namespace
#   - ucm:acceptsRequest ranged over an undeclared ucm:ParticipationContext
DRIFTED_NAMESPACE = "http://mdixinc.com/ucm#"
UCM_NAMESPACE = "urn:w3c:cg:ucm#"


def export_ir(tmp: Path, ontology: List[Path]) -> Tuple[Path, Path, Path]:
    ontology_ir = tmp / "ucm-ontology.jsonld"
    shapes_ir = tmp / "ucm-shapes.jsonld"
    lint_ir = tmp / "ucm-shapes-lint.jsonld"
    ontology_ir.write_text(export_jsonld(ontology), encoding="utf-8")
    shapes_ir.write_text(export_jsonld(SHAPES_TTL), encoding="utf-8")
    lint_ir.write_text(export_jsonld(SHAPES_LINT_TTL), encoding="utf-8")
    return ontology_ir, shapes_ir, lint_ir


def build_spec(compilation: Compilation, profile: ApiProfile, example: Graph) -> OpenAPISpec:
    spec = SpecBuilder(compilation.ir, profile).build()
    examples, _ = build_examples(example, compilation.ir, spec.context)
    return SpecBuilder.attach_examples(spec, examples)


def example_nodes(spec: OpenAPISpec) -> List[Dict[str, Any]]:
    return [node for schema in spec.schemas for node in schema.examples]


@pytest.fixture(scope="session")
def ir_files(tmp_path_factory: pytest.TempPathFactory) -> Tuple[Path, Path, Path]:
    return export_ir(tmp_path_factory.mktemp("ir"), ONTOLOGY_TTL)


@pytest.fixture(scope="session")
def compilation(ir_files: Tuple[Path, Path, Path]) -> Compilation:
    ontology, shapes, shapes_lint = ir_files
    return compile_ir([ontology], [shapes], [shapes_lint])


@pytest.fixture(scope="session")
def regressed_sources(tmp_path_factory: pytest.TempPathFactory) -> List[Path]:
    """The ontology and vocabulary with both earlier defects reintroduced"""
    tmp = tmp_path_factory.mktemp("regressed")
    ontology_text, ranges = re.subn(
        r"(ucm:acceptsRequest rdf:type owl:ObjectProperty ;.*?rdfs:range )ucm:Participation ;",
        r"\1ucm:ParticipationContext ;",
        ONTOLOGY_TTL[0].read_text(encoding="utf-8"),
        flags=re.DOTALL,
    )
    vocabulary_text = ONTOLOGY_TTL[1].read_text(encoding="utf-8")
    prefix = f"@prefix ucm: <{UCM_NAMESPACE}> ."
    assert ranges == 1 and prefix in vocabulary_text, "the TTL sources changed shape"
    ontology = tmp / ONTOLOGY_TTL[0].name
    vocabulary = tmp / ONTOLOGY_TTL[1].name
    ontology.write_text(ontology_text, encoding="utf-8")
    vocabulary.write_text(
        vocabulary_text.replace(prefix, f"@prefix ucm: <{DRIFTED_NAMESPACE}> ."), encoding="utf-8"
    )
    return [ontology, vocabulary]


@pytest.fixture(scope="session")
def regressed_compilation(tmp_path_factory: pytest.TempPathFactory, regressed_sources: List[Path]) -> Compilation:
    ontology, shapes, shapes_lint = export_ir(tmp_path_factory.mktemp("ir-regressed"), regressed_sources)
    return compile_ir([ontology], [shapes], [shapes_lint])


@pytest.fixture(scope="session")
def example_graph() -> Graph:
    return Graph().parse(str(EXAMPLE_TTL))


@pytest.fixture(scope="session")
def profile() -> ApiProfile:
    return ApiProfile.model_validate(load_yaml_safe(PROFILE))


@pytest.fixture(scope="session")
def spec(compilation: Compilation, profile: ApiProfile, example_graph: Graph) -> OpenAPISpec:
    return build_spec(compilation, profile, example_graph)


@pytest.fixture(scope="session")
def regressed_spec(regressed_compilation: Compilation, profile: ApiProfile, example_graph: Graph) -> OpenAPISpec:
    return build_spec(regressed_compilation, profile, example_graph)


@pytest.fixture(scope="session")
def openapi_text(spec: OpenAPISpec) -> str:
    return Generator().generate_openapi_yaml(spec)


@pytest.fixture(scope="session")
def openapi_doc(openapi_text: str) -> Dict[str, Any]:
    return yaml.safe_load(openapi_text)
