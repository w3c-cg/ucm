"""
UCM Code Generation Toolchain

Compiles a JSON-LD export of the Unified Care Model ontology and its SHACL
shapes into:
- An OpenAPI 3.1 reference and JSON-LD context
- A Postgres backend: SQLAlchemy models and an Alembic migration
- A UCM ⇄ FHIR R4 adapter, from a mapping overlay
"""

__version__ = "0.1.0"

from .builder import SpecBuilder
from .fhir_target import FhirCompiler, FhirMapping
from .generator import Generator
from .models import ApiProfile, OntologyIR, OpenAPISpec, ValidationReport
from .normalize import Normalizer
from .parser import export_jsonld, ingest
from .pipeline import Compilation, compile_ir
from .sql_target import SqlBuilder, SqlSchema

__all__ = [
    "ApiProfile",
    "Compilation",
    "FhirCompiler",
    "FhirMapping",
    "Generator",
    "Normalizer",
    "OntologyIR",
    "OpenAPISpec",
    "SpecBuilder",
    "SqlBuilder",
    "SqlSchema",
    "ValidationReport",
    "compile_ir",
    "export_jsonld",
    "ingest",
]
