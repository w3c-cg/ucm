"""
Jinja2 template-based code generation

Targets, all rendered from the IR (through OpenAPISpec, SqlSchema and the
compiled FHIR mapping):
  openapi   OpenAPI 3.1 reference + JSON-LD context
  postgres  SQLAlchemy models + Alembic environment and initial migration
  fhir      UCM ⇄ FHIR R4 adapter
  report    static HTML build report (self-contained: inline CSS and JS)

Templates own the layout; every rendered artifact is parsed back (YAML, JSON
or Python) so a template mistake fails generation instead of shipping.
"""

from __future__ import annotations

import json
import pprint
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from jinja2 import Environment, FileSystemLoader, PackageLoader, StrictUndefined, select_autoescape

from .models import OpenAPISpec
from .sql_target import SqlSchema


class GenerationError(RuntimeError):
    """A template rendered an artifact that does not parse"""


class Generator:
    """Template-based code generator"""

    def __init__(self, templates_dir: Optional[Path] = None):
        loader = (
            FileSystemLoader(str(templates_dir))
            if templates_dir
            else PackageLoader("ucm_codegen", "templates")
        )
        self.env = Environment(
            loader=loader,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            undefined=StrictUndefined,
            # HTML templates escape by default; code and YAML templates never do
            autoescape=select_autoescape(enabled_extensions=("html.j2",), default=False),
        )

        # Add custom filters
        self.env.filters["yaml"] = self._to_yaml
        self.env.filters["yaml_str"] = self._to_yaml_scalar
        self.env.filters["yaml_flow"] = self._to_yaml_scalar
        self.env.filters["pyrepr"] = self._to_python_literal
        self.env.filters["docstring"] = self._to_docstring

    # ---------- OpenAPI target ----------

    def generate_openapi_yaml(self, spec: OpenAPISpec) -> str:
        """Generate the OpenAPI 3.1 reference"""
        text = self.env.get_template("openapi_yaml.j2").render(spec=spec)
        try:
            # libyaml's C loader when available: the pure-Python one takes ~1.5s here
            yaml.load(text, Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))
        except yaml.YAMLError as e:
            raise GenerationError(f"openapi_yaml.j2 rendered invalid YAML: {e}") from e
        return text

    def generate_jsonld_context(self, spec: OpenAPISpec) -> str:
        """Generate the JSON-LD @context document"""
        text = self.env.get_template("jsonld_context.j2").render(spec=spec)
        try:
            json.loads(text)
        except json.JSONDecodeError as e:
            raise GenerationError(f"jsonld_context.j2 rendered invalid JSON: {e}") from e
        return text

    # ---------- Postgres target ----------

    def generate_postgres(self, schema: SqlSchema) -> Dict[str, str]:
        """SQLAlchemy models and Alembic project, keyed by relative path"""
        slug = (schema.ontology_version or "initial").lstrip("vV").replace(".", "_")
        files = {
            "ucm_models.py": self._python("sqlalchemy_models.py.j2", schema=schema),
            "alembic.ini": self.env.get_template("alembic_ini.j2").render(schema=schema),
            "migrations/env.py": self._python("alembic_env.py.j2", schema=schema),
            "migrations/script.py.mako": self.env.get_template("alembic_script.py.mako.j2").render(),
            f"migrations/versions/{schema.revision}_ucm_{slug}.py": self._python(
                "alembic_migration.py.j2", schema=schema
            ),
        }
        return files

    # ---------- FHIR target ----------

    def generate_fhir_adapter(self, adapter: Dict[str, Any]) -> str:
        """UCM ⇄ FHIR adapter module from a compiled mapping (FhirCompiler.compile)"""
        return self._python("fhir_adapter.py.j2", adapter=adapter)

    # ---------- Report ----------

    def generate_report(self, report: Dict[str, Any]) -> str:
        """Static HTML report from ReportBuilder.build()"""
        text = self.env.get_template("report.html.j2").render(r=report)
        parser = HTMLParser()
        parser.feed(text)
        parser.close()
        if not text.rstrip().endswith("</html>"):
            raise GenerationError("report.html.j2 rendered an incomplete document")
        return text

    # ---------- Helpers ----------

    def _python(self, template: str, **context: Any) -> str:
        text = self.env.get_template(template).render(**context)
        try:
            compile(text, template, "exec")
        except SyntaxError as e:
            raise GenerationError(f"{template} rendered invalid Python: {e}") from e
        return text

    @staticmethod
    def _to_yaml(value: Any) -> str:
        """Block YAML for a nested value (indent it in the template)"""
        return yaml.safe_dump(
            value, sort_keys=False, default_flow_style=False, allow_unicode=True, width=10_000
        ).rstrip("\n")

    @staticmethod
    def _to_yaml_scalar(value: Any) -> str:
        """JSON is valid flow YAML: quoting is always correct"""
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _to_python_literal(value: Any) -> str:
        """Python literal for generated modules (insertion order kept)"""
        return pprint.pformat(value, width=100, sort_dicts=False)

    @staticmethod
    def _to_docstring(value: Optional[str]) -> str:
        return (value or "").replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
