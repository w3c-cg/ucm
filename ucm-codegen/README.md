# ucm-codegen

Reference compiler for the UCM specification.  

The ontology (OWL), its concept schemes (SKOS) and its shapes (SHACL) are the source of truth,
and three targets are compiled from them.

- **OpenAPI 3.1 reference** and its JSON-LD context
- **Postgres backend**: SQLAlchemy 2.0 models and an Alembic migration
- **FHIR R4 adapter**: UCM JSON-LD <> FHIR Bundle, from a mapping overlay

Each build also writes a static HTML **report** of lint, validation and
where every property lands in the three targets.

## Architecture contract

```
 unified-care-model.ttl ─┐
 ucm-lifecycle-*.ttl ────┤
 ucm-core-shapes.ttl ────┼─ export ─▶  JSON-LD IR  ◀── any JSON-LD 1.1 export (Protégé, ROBOT)
 ucm-shapes-lint.ttl ────┘                │
                                          ▼  parser.py     PyLD: URDNA2015 canonicalization,
                                          │                sha256 digest per source, no remote contexts
                                          ▼  normalize.py  rdflib graph → Pydantic IR (models.py)
                                          │                tier/severity and JSON-LD term checks
                                          ▼  pipeline.py   PySHACL: SHACL-SHACL + ucm-shapes-lint over
                                          │                the shapes; lint.py: spec consistency
                                          ▼
                 builder.py (API placement and cardinality rules, shared by every target)
                    │                        │                          │
             openapi_yaml.j2          sql_target.py              fhir_target.py + overlay
             jsonld_context.j2        sqlalchemy_models.py.j2    fhir_adapter.py.j2
                                      alembic_*.j2
                    ▼                        ▼                          ▼
        openapi.yaml, context.jsonld   postgres/ (models, Alembic)   fhir/ucm_fhir_adapter.py
```

The **JSON-LD IR is the boundary**: `generate`, `lint`, `extract` and `info`
refuse anything else, and `build` exports the IR before compiling from it. `export` exists only to produce that IR from Turtle
deterministically (canonical blank-node labels, sorted nodes). Every
rendered file is parsed back (YAML, JSON or Python) before it is written.

## Quick start

```bash
pip install -e ".[dev]"
```

```bash
ucm-codegen build
```

`build` reads [`ucm-build.yaml`](ucm-build.yaml), which names the spec
sources, examples, profile and FHIR mapping once (paths relative to the
manifest), then runs every step: TTL → JSON-LD IR in `build/` → IR and lint
→ examples validated against the shapes → all targets and `report.html` in
`generated/`. The exit code is 1 on violations, and on warnings with
`--strict`.

**A failed build writes only the report.** The report is always written,
with a banner naming the failure, because a red build is when it is most
useful. Everything else is gated on success: the generated artifacts, the
IR in `build/`, the IR snapshot and `ucm-build.lock` stay exactly as the
last good build left them, and nothing is pruned. Nothing built from a
broken spec can be committed or published by accident, and the report's
Changes pane compares against the last healthy spec. (The IR is exported to
a staging directory in the cache and promoted to `build/` on success.)
`--write-on-failure` writes everything anyway, for inspecting broken
outputs; the exit code is still 1.

The individual steps remain available:

| Command    | Does |
|------------|------|
| `build`    | Everything above, from the manifest (`-m`); `--strict` fails on warnings; `--no-cache` recomputes every stage; `--write-on-failure` lifts the gate |
| `export`   | RDF sources → JSON-LD IR (`build/ucm-ontology.jsonld`, `ucm-shapes.jsonld`, `ucm-shapes-lint.jsonld`) |
| `lint`     | SHACL-SHACL, ucm-shapes-lint (`-l`), and spec consistency checks |
| `generate` | All targets, or one with `-f openapi\|context\|postgres\|fhir\|report`; `--strict` fails on lint warnings |
| `validate` | Instance data against the shapes (PySHACL); violations fail, warnings pass with a notice |
| `extract`  | Dump the normalized IR as JSON/YAML (debugging, diffing ontology versions) |
| `info`     | Counts, source digests, and the resources the ontology compiles to |

```bash
pytest
```

The tests run against the UCM files in the parent folder: IR round-trip
isomorphism, the shapes on the conformant example and single-defect
variants, the spec lint, OpenAPI validity, every example validated against
its schema, the Alembic migration against the ORM, a database round trip of
every example node, FHIR output validated with `fhir.resources`, the build
command passing on the spec and failing (with a report) on a regressed copy
of it, the failure gate (a failed build leaves every artifact, the IR and
the lock byte-identical), and content addressing: reproducible lockfiles,
cache hits, the diff of a spec change, and stale-output pruning.

## Content addressing

Everything the build reads or writes is named by a sha256 of its content
(`content.py`), with line endings normalized so Windows checkouts and Linux
CI agree:

| Digest | Over | Used for |
|---|---|---|
| Source | spec, example, profile and mapping files | lockfile, cache keys |
| Graph | URDNA2015 canonical N-Quads of each JSON-LD IR file | identity of the graph, independent of serialization |
| Node | each IR class, property, concept scheme and shape | semantic diff; blank-node shapes are named by content |
| IR root | Merkle root of the node digests | one fingerprint for the compiled ontology |
| Output | each generated file | lockfile, stale-output pruning |
| Toolchain | ucm-codegen's own code and templates | part of every cache key |

**Stage cache** (`build/.cache/`, git-ignored, safe to delete). Export,
canonicalization, normalization with SHACL-SHACL and spec lint, and example
validation are stored under keys derived from their input digests plus the
toolchain digest. An unchanged spec skips PySHACL entirely (about 12s cold to
about 5s warm here, the rest being interpreter start-up); a changed input
simply misses. `--no-cache` produces byte-identical outputs.

**Lockfile** (`ucm-build.lock`, next to the manifest; commit it). Records
source, IR, node and output digests, deterministically: building twice, with
or without the cache, on any OS, writes the same bytes. Only passing builds
write it, so it always describes the last good build. Each build diffs
against it: the CLI and the report's **Changes** pane list
added, removed and changed IR nodes down to the field
(`range: ucm:ParticipationContext → ucm:Participation`) and which generated
files moved. `build/ucm-ir.json` holds the IR snapshot that field-level
diffs compare against.

**Stale outputs.** A spec change renames the Alembic revision (its id
derives from the ontology digests). Outputs the previous build wrote but
this one no longer produces are deleted when they still hold exactly what
was written, so the migrations directory never ends up with two heads.
Edited files are kept and reported.

## Report

`generated/report.html` is one self-contained file (inline CSS and a little
vanilla JS, no network), so it works from disk and as a CI artifact. Panes:

- **Overview**: build status, counts, source digests, IR root and toolchain digests
- **Lint** and **Validation**: findings and SHACL results by severity and tier
- **Changes**: the diff against the previous build, by content digest
- **Classes**: the class tree; each property with its cardinality, range,
  OpenAPI type, Postgres column or association table, and FHIR element
- **Vocabularies**, **OpenAPI**, **Postgres**, **FHIR**: each target's view
- **Artifacts**: links to the generated files, with their digests

## CI

[`.github/workflows/ucm-codegen.yml`](../.github/workflows/ucm-codegen.yml)
runs on any `.ttl` change (and on toolchain changes): install, restore the
stage cache, `ucm-codegen build --strict`, `pytest`, then uploads
`generated/` and `build/` as the `ucm-reference` artifact, even when the
build fails: then it holds the failed build's report next to the last good
artifacts. Whatever is committed of `ucm-build.lock`, `generated/` and
`build/` must match the rebuild (`report.html` excepted), so a spec change
cannot land without its regenerated artifacts. After moving into the UCM
repository, update the paths in `ucm-build.yaml` and the workflow's `paths`
filters.

## Target: OpenAPI

| Ontology / shapes | API |
|---|---|
| Root class (no superclass in the ontology) | Resource: `/{plural}` (list, create), `/{plural}/{id}` (read, replace, delete) |
| `owl:Class` | Component schema; `x-semantic-uri`, `x-jsonld-type` |
| `rdfs:subClassOf` | `allOf`; `@type` enumerates the class and its subclasses; list takes `?type=` |
| `owl:equivalentClass` (external) | `x-ucm-equivalent-classes` |
| Property with `rdfs:domain` | Defined once, on the domain's schema |
| Property without domain | On the `UcmNode` base schema every class extends |
| Object property | `NodeRef`: IRI string or embedded node object |
| Range `skos:Concept`, `hasX` with scheme `X` | Open vocabulary: concept terms or any IRI (shapes avoid `sh:in` on purpose) |
| Datatype property | JSON Schema type/format from `sh:datatype` / `sh:or`, else `rdfs:range` |
| `sh:maxCount 1`, Definitional | Single value; otherwise array and `@container: @set` in the context |
| `sh:minCount ≥ 1`, Definitional | `required` / `minItems` |
| `sh:minCount ≥ 1`, Recommended | Not required; `x-ucm-recommended: true` |
| `sh:class`, `sh:message`, `sh:sparql` | `x-ucm-range`, `x-ucm-constraints` (with severity and tier) |
| All shapes | Writes return `422` + `ValidationReport` (schema generated from the Pydantic model) |

`profiles/ucm-api-profile.yaml` (optional) holds what the ontology cannot
say: title, servers, context URL, `exclude` and `scheme-bindings`.

## Target: Postgres (SQLAlchemy + Alembic)

Output: `generated/postgres/` with `ucm_models.py`, `alembic.ini` and
`migrations/` (env, script template, one deterministic initial revision
whose id derives from the ontology digests).

| Ontology / shapes | Database |
|---|---|
| Root class | Table; subclasses share it (single-table inheritance on `type`, CHECK-ed) |
| Single-valued property | Column on its home class's root table |
| Multi-valued property | Association table `<owner>__<property>`, FK to the owner, ON DELETE CASCADE |
| Object property | IRI text, indexed, **no foreign key**: `sh:class` is Recommended, so a reference may name a node typed elsewhere |
| Definitional `sh:minCount 1` | `NOT NULL` on the root class, `CHECK` on a subclass |
| `xsd:dateTime` / `dateTimeStamp` | `timestamptz`, normalized to UTC |
| Predicates outside UCM | `extra` JSONB, verbatim (open by default) |
| Concept schemes | `concept` table, seeded by the migration (no FK: vocabularies are open) |

`load(session, nodes)` and `dump(session, iri)` in `ucm_models.py` convert
between rows and JSON-LD nodes compacted with the generated context.

```bash
cd generated/postgres
```

```bash
alembic upgrade head
```

The URL comes from `UCM_DATABASE_URL` (default in `alembic.ini`);
`alembic upgrade head --sql` emits the Postgres DDL without a server.

## Target: FHIR R4 adapter

`profiles/ucm-fhir-mapping.yaml` maps UCM classes to FHIR resources and
properties to FHIR elements. It is Pydantic-validated against the IR: every
class, property, role and concept term must exist, and every path must be
applicable to the class it starts from. Output: `generated/fhir/ucm_fhir_adapter.py`
(standard library only) with `to_fhir_bundle(nodes)` and `from_fhir_bundle(bundle)`.

Starter mapping: Person → Patient (Practitioner when the person assumes a
provider or coordinator role), Organization, Location, Device, Household →
Group (through Membership), CareTeam, ClinicalEncounter → Encounter
(participations as `participant`, subject roles excluded), CoordinationRequest →
Task (lifecycle Pending/Accepted/Declined → requested/accepted/rejected;
requester/owner/for by role), DiagnosisStatement → Condition, Observation-,
Housing- and SocialCareStatement → Observation.

Identity survives the round trip: each resource carries its IRI as an
`urn:ietf:rfc:3986` identifier and its UCM class as `meta.tag`; folded
nodes (participations, memberships) carry theirs in the `node-iri`
extension. Multi-hop paths are one-way.

## Lint codes

| Code | Severity | Meaning |
|---|---|---|
| `shacl-shacl` | Violation | A shape does not conform to SHACL-SHACL |
| `shapes-lint` | from the lint shape | A shape fails `ucm-shapes-lint.ttl` (tiers, closure rationale) |
| `namespace-drift` | Warning | A namespace IRI is referenced but only declared under another namespace |
| `undeclared-term` | Warning | A namespace IRI is referenced but never declared |
| `range-mismatch` | Warning | `sh:class` disagrees with `rdfs:range` |
| `datatype-coercion` | Info | `sh:or` datatypes a single context term cannot coerce |
| `foreign-scheme` | Info | Concept scheme outside the ontology namespace |
| `shape-without-range` | Info | Shape constrains a class the property's range does not declare |
| `orphan-class` | Info | Root class nothing refers to |
| `no-domain` | Info | Property placed on the base schema |

A tier that contradicts its severity (Definitional must be `sh:Violation`,
Recommended `sh:Warning` or `sh:Info`) is rejected by the Pydantic IR and
stops the pipeline.


