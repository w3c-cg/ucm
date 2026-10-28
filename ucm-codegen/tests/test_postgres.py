"""Postgres target: generated SQLAlchemy models and Alembic migration"""

import datetime
import importlib
import io
import sys
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy.orm import Session

from ucm_codegen.generator import Generator
from ucm_codegen.sql_target import SqlBuilder

from .conftest import example_nodes


@pytest.fixture(scope="module")
def schema(compilation):
    return SqlBuilder(compilation.ir).build()


@pytest.fixture(scope="module")
def project(tmp_path_factory, schema) -> Path:
    root = tmp_path_factory.mktemp("postgres")
    for relative, text in Generator().generate_postgres(schema).items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return root


@pytest.fixture(scope="module")
def models(project):
    sys.path.insert(0, str(project))
    sys.modules.pop("ucm_models", None)
    yield importlib.import_module("ucm_models")
    sys.path.remove(str(project))


def alembic_config(project: Path) -> Config:
    config = Config(str(project / "alembic.ini"))
    config.attributes["configure_logger"] = False
    return config


@pytest.fixture()
def engine(project, models, tmp_path):
    """SQLite database migrated to head with the generated Alembic project"""
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'ucm.db'}")
    config = alembic_config(project)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    return engine


def test_layout(schema):
    tables = {t.name: t for t in schema.tables}
    assert len(tables) == 19
    process = tables["process"]
    assert {"Handshake", "HousingAssessment", "ClinicalEncounter"} <= set(process.type_terms)
    participation = {c.term: c for c in tables["participation"].columns}
    assert not participation["participatingEntity"].nullable  # Definitional minCount 1
    assert not participation["occursWithin"].nullable
    assert participation["validFrom"].orm_type == "UtcDateTime()"
    assert {"assumesRole", "validFrom"} - set(participation) == {"assumesRole"}  # multi-valued
    associations = {a.name: a for a in schema.associations}
    assert associations["participation__assumes_role"].owner_table == "participation"
    assert associations["node__has_temporal_context"].owner_table is None  # no rdfs:domain
    assert [c.term for c in schema.concepts] == ["Accepted", "Declined", "Pending"]


def test_revision_is_deterministic(compilation, schema):
    assert SqlBuilder(compilation.ir).build().revision == schema.revision


def test_migration_matches_models(engine, models):
    with engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), models.Base.metadata) == []
        assert connection.execute(sa.text("select count(*) from concept")).scalar() == 3


def test_examples_round_trip(engine, models, spec):
    nodes = example_nodes(spec)
    with Session(engine) as session:
        assert models.load(session, nodes) == 28
        session.commit()

    def same(a, b):
        if isinstance(a, str) and isinstance(b, str) and "T" in a and a[:4].isdigit():
            return datetime.datetime.fromisoformat(a) == datetime.datetime.fromisoformat(b)
        return a == b

    with Session(engine) as session:
        for node in nodes:
            dumped = models.dump(session, node["@id"])
            assert set(dumped) == set(node), node["@id"]
            for key, value in node.items():
                assert same(dumped[key], value), (node["@id"], key)


def test_definitional_tier_is_enforced(engine, models):
    with Session(engine) as session:
        session.add(models.Participation(iri="urn:ex:p", occurs_within="urn:ex:proc"))
        with pytest.raises(sa.exc.IntegrityError):
            session.flush()


def test_type_check_rejects_foreign_classes(engine):
    with engine.connect() as connection:
        with pytest.raises(sa.exc.IntegrityError):
            connection.execute(sa.text(
                "insert into participation (iri, type, occurs_within, participating_entity) "
                "values ('urn:ex:p', 'Person', 'urn:ex:a', 'urn:ex:b')"
            ))


def test_postgres_ddl(project, monkeypatch):
    """Offline migration renders Postgres DDL without a server"""
    monkeypatch.setenv("UCM_DATABASE_URL", "postgresql://ucm@localhost/ucm")
    config = alembic_config(project)
    buffer = io.StringIO()
    config.output_buffer = buffer
    command.upgrade(config, "head", sql=True)
    sql = buffer.getvalue()
    assert "extra JSONB DEFAULT '{}' NOT NULL" in sql
    assert "valid_from TIMESTAMP WITH TIME ZONE" in sql
    assert "participating_entity TEXT NOT NULL" in sql
    assert "CONSTRAINT ck_process_type CHECK (type IN ('Process'," in sql
    assert "REFERENCES participation (iri) ON DELETE CASCADE" in sql
    assert "INSERT INTO concept" in sql
