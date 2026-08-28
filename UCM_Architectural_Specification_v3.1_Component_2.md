# Component 2 — Architectural Vision, Foundational Principles, and Semantic Architecture

**Unified Care Model (UCM) Architectural Specification**  
**Version 3.1**  
**Status:** Informative Baseline for Community Review

---

## 5. Architectural Vision

### 5.1 Vision

The Unified Care Model (UCM) provides a reusable, implementation-independent semantic reference architecture for representing and integrating meaning across whole-person care.

The UCM is founded on the principle that meaningful interoperability requires preservation of semantic meaning rather than merely syntactic compatibility. Exchange formats, APIs, message structures, schemas, files, and databases may transport or store information, but interoperability is achieved only when the intended meaning of that information is consistently understood.

The architecture initially recognizes two Domain Models — Clinical Care and Social Care — while providing a governed path for additional subject areas to be incorporated or promoted when their specialized semantics require an independent Domain Model.

### 5.2 Mission

The mission of the UCM is to establish a stable, extensible, and governable semantic architecture that:

- Preserves meaning across heterogeneous information models and exchange standards.
- Distinguishes domain semantics from statements and information artifacts that describe or assert information about them.
- Separates enduring identity from contextual participation and role.
- Provides reusable semantic patterns for entities, roles, processes, participation, statements, eligibility, membership, and semantic value objects.
- Supports specialized Clinical Care and Social Care semantics without duplicating shared meaning.
- Aligns architecturally with SULO.
- Remains independent of implementation technologies and syntactic representations.
- Provides the semantic foundation from which Implementation Models can assign precise, computable meaning to implementation data.

### 5.3 Architectural Purpose

The UCM defines universal and reusable semantic constructs needed to make meaningful assertions about entities, processes, states, conditions, roles, and relationships.

The UCM does not prescribe how a particular implementation must serialize, validate, transport, store, or exchange information. Those responsibilities belong to implementing semantic models, profiles, schemas, mappings, and application-specific specifications.

### 5.4 Architectural Philosophy

The UCM is not an exchange standard, implementation guide, physical information model, database schema, message definition, API contract, or application data model. It is a conceptual semantic architecture.

The architecture recognizes complementary semantic dimensions:

1. **Entities** that exist independently of a particular context.
2. **Roles** that entities bear temporarily or conditionally.
3. **Processes and activities** that unfold over time.
4. **Participation relationships** describing how entities engage in contexts.
5. **Qualities, conditions, states, and relationships** characterizing entities and processes.
6. **Statements and information artifacts** that assert, record, classify, or communicate information about domain semantics.
7. **Semantic value objects** that convey structured meaning independently of implementation datatypes.
8. **Domain specialization** where a care domain requires distinct reusable semantics not adequately expressible through existing shared concepts.

---

## 6. Foundational Modeling Principles

### 6.1 Domain Semantics and Information Semantics

The UCM distinguishes the things, processes, states, qualities, and relationships being described from the information that asserts, records, classifies, or communicates something about them.

> **The UCM defines meaning. Implementing semantic models define how that meaning is represented. Exchange standards define how that representation is communicated.**

Examples of domain semantic categories include Person, Organization, Process, Role, Participation, Quality, and Condition.

Examples of information semantic categories include Statement, Report, Assessment, Definition, Policy, Plan, Order, Classification, and other information artifacts.

A Condition is not a Statement. A procedure is not its procedure report. A Person is not a patient record. A Statement may assert that a Person has a Condition, and an implementation structure may package both the condition semantics and the assertion semantics together.

Therefore, an implementation construct should not be assumed to correspond one-to-one with a single UCM class. It may represent a semantic composition of multiple UCM concepts and relationships.

### 6.2 Alignment with SULO

The UCM is architecturally aligned with SULO and preserves foundational distinctions among enduring entities, processes, roles, participation, qualities, domain phenomena, and information objects.

SULO alignment does not require the UCM to duplicate every SULO class or axiom. The UCM introduces care-relevant reusable semantic constructs while remaining consistent with SULO distinctions.

### 6.3 Core Model

The Core Model represents stable, reusable semantic concepts that persist independently of a particular care domain, implementation, interaction, or workflow.

Examples include Person, Organization, SocialGroupEntity, Location, Device, Process, Activity, InformationArtifact, Statement, Quality, Condition, DefinitionArtifact, and SemanticValueObject.

Core concepts may serve as stable **foundational concepts** for semantic alignment across implementations.

### 6.4 Participation Model

The Participation Model is a peer of the Core Model. It defines how an entity participates in a context and includes reusable concepts such as Role, Participation, Membership, MemberRole, PatientRole, ClientRole, ProviderRole, BeneficiaryRole, Eligibility, EligibilityCriteria, and ParticipationContext.

Patient, Client, Member, Provider, Beneficiary, Guarantor, Subscriber, and similar concepts are modeled as contextual roles rather than permanent subclasses of Person.

### 6.5 Domain Models

Domain Models specialize and compose concepts from the Core Model and Participation Model for a coherent area of care.

The initial UCM Domain Models are:

- **Clinical Care Domain Model**
- **Social Care Domain Model**

Domain Models should remain deliberately small. Most domain meaning should be expressed by composing existing UCM concepts, properties, Statements, Roles, Participation, and semantic value objects.

A new domain concept is justified when the domain requires a distinct, reusable semantic type whose identity cannot be adequately expressed merely as a composition of existing UCM concepts and relationships.

For example, a Clinical Care Domain may need a reusable `ClinicalCondition` concept. The relationships surrounding it — subject, temporal context, status, role context, provenance, and statements about it — should reuse shared UCM patterns rather than be reinvented within the domain.

### 6.6 Domain Promotion

A new subject area does not automatically become a Domain Model merely because it appears in a whole-person care framework or SDOH classification.

A subject area should be considered for promotion to a Domain Model when:

1. It represents a coherent area of activity or subject matter.
2. It requires specialized semantics beyond the existing Core, Participation, and Domain Model patterns.
3. Those semantics exist independently of the care process that interacts with the subject area.
4. Promotion reduces duplication rather than creating a new semantic silo.
5. Established authoritative domain models are reused or aligned wherever possible rather than reinvented.

Housing, education, justice, research, payment, and similar subject areas may initially be represented through existing UCM semantics and applicable Domain Models. They may later be promoted if these criteria are met.

### 6.7 Reuse Before Extension

Before introducing a new class or property, determine whether the intended meaning can be represented using:

- An existing Core concept.
- An existing Participation concept or role.
- A reusable Statement pattern.
- An existing semantic property or value object.
- Composition of existing relationships.
- An existing Domain Model concept.

New classes should be introduced only when a distinct reusable concept remains after this analysis.

### 6.8 Shared Concepts Across Domains

Some concepts, such as Eligibility and EligibilityCriteria, are not intrinsically Clinical Care or Social Care concepts. They are shared UCM semantics that may be applied in both domains.

Domain specialization should occur only where the meaning itself becomes domain-specific. Program-specific eligibility thresholds, formulas, or regulatory rules are not UCM Domain Model concepts merely because they govern a domain use case.

### 6.9 Implementing Models 

The UCM is intended to serve as the semantic foundation for one or more implemention models. 

Implementation Models may define:

- Fully resolved semantic assertions.
- Data-element-level semantic definitions.
- Context-specific compositions of Core, Participation, and Domain Model concepts.
- Role context when an implementation representation makes the role semantically material.
- Program-specific semantic policy and rules.
- Structural semantics inherited from message, document, file, schema, loop, container, or profile context.
- Exchange-specific realizations.
- Terminology bindings and value-set constraints.
- Datatype mappings.
- Cardinality and validation rules.
- Transformation logic.
- Provenance and conformance metadata.
- Semantic decomposition of implementation constructs that combine multiple UCM concepts.

For example, a Michigan financial assistance rule such as `household income < 150% of FPL` belongs in the Implementation Model program-specific semantic layer, while the reusable concepts Eligibility, EligibilityCriteria, Household, Income, Person, and Membership belong in the UCM as appropriate.

### 6.10 Person and Role Context

The UCM defines Person independently of PatientRole, ClientRole, MemberRole, and other contextual roles.

A statement such as `Person has ClinicalCondition` may be true independently of whether the Person is presently participating as a patient. A FHIR implementation may instead reference `Patient` as the subject of a Condition. The USCM resolves that representation into the appropriate UCM semantics: Person as the enduring subject, PatientRole as contextual participation when material, and ClinicalCondition as the domain concept.

The role should be retained when it contributes meaning to the assertion; it should not replace the underlying Person as the enduring semantic subject.

---

## 7. Guiding Principles

1. Preserve semantic meaning.
2. Distinguish domain semantics from statements and information about those semantics.
3. Separate enduring identity from contextual role and participation.
4. Treat Core and Participation as peer foundational models.
5. Prefer composition over deep inheritance and domain-specific duplication.
6. Reuse shared semantics before introducing domain specialization.
7. Introduce new domain concepts only when a distinct reusable semantic type is required.
8. Promote new Domain Models only when coherent independent specialized semantics justify promotion.
9. Reuse established external domain models wherever possible.
10. Keep program-specific policy and implementation rules outside the UCM and in the Implementing Models.
11. Permit implementation constructs to compose multiple UCM concepts without collapsing those concepts in the UCM.
12. Remain implementation independent and architecturally aligned with SULO.
13. Support deterministic semantic resolution, knowledge graphs, and explainable AI.
14. Support transparent governance and long-term evolution.

---

## 8. Transition to the Architectural Models

The remaining components describe the Core Model, Participation Model, Domain Models, and their relationship to SULO and implementing semantic models.

---

**End of Component 2 — Version 3.1**
