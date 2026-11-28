

# Unified Care Model (UCM) Specification

## W3C Group Page

[https://www.w3.org/community/ucm/](https://www.w3.org/community/ucm/)

## Participation Guidelines

All members: Please read the guidelines linked below to understand your membership rights and responsibilities. 

W3C Community Group Guidelines and Policies (this is "officially" a W3C Community Group):
* send all messages to the group to public-ucm@w3.org [public listserv archives](https://lists.w3.org/Archives/Public/public-ucm/)
* Code of conduct: https://www.w3.org/policies/code-of-conduct/
* Patent policy: https://www.w3.org/policies/patent-policy/
* https://www.w3.org/community/about/process/final/
* https://www.w3.org/2026/Talks/w3c-chairtraining.pdf
* https://www.w3.org/community/about/

## Repository layout

**Top-level ontology files**
- `unified-care-model.ttl` — the core UCM ontology. Imports the lifecycle and shapes ontologies below.
- `ucm-core-shapes.ttl` — SHACL shapes for the core ontology (`https://www.w3.org/ns/ucm#shapes`).
- `ucm-shapes-lint.ttl` — lint-style SHACL shapes used to catch authoring mistakes in the ontology itself.
- `ucm-lifecycle-vocabularies.ttl` — the lifecycle ontology (`#lifecycle`), imported by the core.
- `ucm-participation-membership.ttl` — participation/membership vocabulary.
- `ucm-core-sulo-model.ttl` — SULO-aligned core model.

**Project/community files**
- `README.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `LICENSE.md` — standard repo docs.
- `group-charter.md` — the W3C Community Group's charter.
- `w3c.json` — W3C Community Group metadata (used by W3C tooling).
- `catalog-v001.xml` — XML catalog mapping namespace URIs to local files.

**Directories**
- `ns/` — the files served at the `https://www.w3.org/ns/ucm#` namespace: `ucm.ttl`, `ucm.jsonld`, `index.html`.
- `codegen/` — the codegen tool that builds the ontology and generates API/DB artifacts from it (source, tests, build output/IR — not example output).
- `examples/` — non-normative example/generated artifacts, split by target:
  - `examples/api/` — generated OpenAPI/FHIR/JSON-LD, produced by `codegen/`.
  - `examples/db/` — generated Postgres models and Alembic migrations.
  - `examples/shapes/` — example instance data validated against the core shapes.
- `mapping/` — non-normative mappings from UCM to external standards:
  - `mapping/consent-mappings.ttl` — SKOS and subproperty links from the consent vocabularies to HL7 code systems and the W3C Data Privacy Vocabulary (DPV). Load it alongside the core.
  - `mapping/consent-fhir-r5.md`, `consent-hmis.md`, `consent-niem.md`, `consent-iso27560.md` — consent and identity mappings to FHIR R5/R4 Consent, HUD HMIS, NIEM 6.0, and ISO/IEC TS 27560 consent records.
- `test-suites/` — the test suite validating the core ontology and shapes (`test_core_shapes.py`).
- `doc/` — supporting documents and the GitHub Pages site:
  - `doc/github-pages/` — source for the project's GitHub Pages site (implementation workbench build script, templates, tests).
  - `doc/design/`, `doc/lifecycle/` — placeholders for design and lifecycle-related files.
  - presentation decks (`.pptx`) and W3C CG response notes.
- `arch-spec/` — architecture specification and ontology requirements documents.
- `agendas/` — weekly meeting agendas.
- `user-stories/` — narrative care-coordination user stories.
- `.github/workflows/` — CI workflows (ontology codegen build, GitHub Pages workbench build).
- `.claude/` — Claude Code session metadata (not part of the ontology).

## Visualization: 

[https://alexandriaconsulting.com/webvowl/#iri=https://raw.githubusercontent.com/w3c-cg/ucm/refs/heads/main/unified-care-model.ttl](https://alexandriaconsulting.com/webvowl/#iri=https://raw.githubusercontent.com/w3c-cg/ucm/refs/heads/main/unified-care-model.ttl)

