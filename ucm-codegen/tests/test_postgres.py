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


def test_layout(compilation, schema):
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
    concepts = {c.term for s in compilation.ir.schemes.values() for c in s.concepts}
    assert {c.term for c in schema.concepts} == concepts  # one row per concept, every scheme
    assert {"Accepted", "Declined", "Pending"} <= concepts


def test_revision_is_deterministic(compilation, schema):
    assert SqlBuilder(compilation.ir).build().revision == schema.revision


def test_migration_matches_models(compilation, engine, models):
    concepts = sum(len(s.concepts) for s in compilation.ir.schemes.values())
    with engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), models.Base.metadata) == []
        assert connection.execute(sa.text("select count(*) from concept")).scalar() == concepts


def test_examples_round_trip(engine, models, spec):
    nodes = example_nodes(spec)
    with Session(engine) as session:
        assert models.load(session, nodes) == 29
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


def test_concepts_record_their_parent(schema):
    parents = {c.term: c.broader_iri for c in schema.concepts}
    assert parents["OutOfArea"] == "https://www.w3.org/ns/ucm#ClosedNotConnected"
    assert parents["ClosedNotConnected"] is None and parents["Accepted"] is None


def test_closure_rates_roll_up_in_sql(engine, compilation):
    """Successful-connection rate from one scheme: ClosedConnected / (ClosedConnected + under ClosedNotConnected)"""
    ucm = "https://www.w3.org/ns/ucm#"
    closed = ["ClosedConnected", "ClosedConnected", "OutOfArea", "ClientUnreachable", "ClosedNotConnected",
              "ClosedNoLongerNeeded"]  # one request each; the last is excluded from the rate
    with engine.begin() as connection:
        connection.execute(sa.text("create table closure (request text, reason text)"))
        connection.execute(sa.text("insert into closure values (:r, :c)"),
                           [{"r": f"req-{i}", "c": ucm + c} for i, c in enumerate(closed)])
        rows = connection.execute(sa.text("""
            with recursive under(iri, top) as (
                select iri, iri from concept where broader_iri is null and scheme_iri = :scheme
                union all
                select c.iri, u.top from concept c join under u on c.broader_iri = u.iri
            )
            select u.top, count(*) from closure x join under u on x.reason = u.iri group by u.top
        """), {"scheme": ucm + "ClosureReason"}).all()
    counts = {top.rsplit("#", 1)[1]: n for top, n in rows}
    assert counts == {"ClosedConnected": 2, "ClosedNotConnected": 3, "ClosedNoLongerNeeded": 1}
    rate = counts["ClosedConnected"] / (counts["ClosedConnected"] + counts["ClosedNotConnected"])
    assert rate == 0.4
