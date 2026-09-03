# Unified Care Model (UCM) Architectural Specification

**Version 3.1**  
**Status:** Informative Baseline for Community Review

This integrated specification is organized into six major sections that preserve the structure of the original UCM architectural documents while presenting them as one continuous document.

---

# Section 1 — Introduction and Overview

## 1. Introduction

### 1.1 Purpose

The Unified Care Model (UCM) is an implementation-independent semantic reference architecture for representing human-centered care information. It establishes a reusable semantic foundation that enables consistent representation, integration, reasoning, and interoperability while remaining independent of any exchange standard, implementation technology, software platform, file format, schema, or API.

The UCM defines meaning. Implementing semantic models define how that meaning is represented. Exchange standards and implementation models define how that representation is communicated, stored, or processed.

### 1.2 Objectives

The objectives of the UCM are to:

- Define reusable semantic concepts, properties, relationships, and patterns.
- Separate shared meaning from implementation-specific representation.
- Support semantic interoperability across clinical care and social care.
- Support additional domains through disciplined extension and promotion when justified.
- Separate enduring identity from contextual role and participation.
- Distinguish domain semantics from statements and information artifacts that describe or assert information about those semantics.
- Enable independent evolution of UCM and implementation models.
- Provide the common semantic foundation used by implementing semantic models.

### 1.3 Intended Audience

This specification is intended for ontology architects, domain experts (Business Knowledge), information model designers, standards organizations, interoperability implementers, researchers, and software architects.

### 1.4 Scope

This specification defines the architecture of the UCM. It does not define implementation guides, exchange standards, messaging formats, APIs, database schemas, file layouts, program-specific policy rules, or transformation mappings.

Those implementation-specific concerns belong outside the UCM and may be represented in an implementing model.

---

## 2. Motivation

Whole-person care requires information to retain consistent meaning across different care domains, organizations, standards, and technologies. Clinical care and social care often describe the same person, organizations, groups, activities, roles, conditions, needs, eligibility, and participation using different structures and terminology.

The UCM addresses this problem by establishing a stable semantic architecture beneath those representations. It is intended to complement, not replace, existing standards and established domain models.

A central architectural principle is reuse before extension. Shared semantics should be defined once and reused. Domain Models should specialize meaning only when a distinct, reusable domain concept cannot be adequately represented through composition of existing UCM concepts and patterns.

---

## 3. Overview of the Unified Care Model

The UCM contains three complementary model types: the Core Model, the Participation Model, and Domain Models. The Core Model and Participation Model are peer foundational models; Domain Models compose and specialize their reusable semantics. Section 3 presents the complete architectural relationship.

The Core Model and Participation Model are peer foundational models. Domain Models compose and specialize their reusable semantics.

The UCM is architecturally aligned with SULO. SULO supplies upper-level distinctions; the UCM supplies the reusable care-oriented semantic architecture.

At the present stage, the UCM has identified two initial Domain Models:

- **Clinical Care Domain Model**
- **Social Care Domain Model**

This is not a statement that the UCM can have only two domains. Additional subject areas may be incorporated through existing UCM semantics or promoted to Domain Models when their independent specialized semantics justify doing so.

---

## 4. Relationship to Implementation Models

The UCM supplies reusable semantic vocabulary and patterns. Implementation Models use concepts from the Core Model, Participation Model, and applicable Domain Models to assign precise, unambiguous meaning to data represented in implementations.

```text
UCM
  Core + Participation + Domain Models
                    |
                    v
             Implementation Models
     precise, context-resolved semantics
                    |
                    v
Implementation Models and Representations
FHIR | C-CDA | HL7 v2 | X12 | files | schemas | APIs | databases
```

An Implementation Model may define fully resolved semantic assertions, structural context, program-specific policy, terminology bindings, mappings, cardinality, validation, and transformation rules. These operational details do not become UCM ontology content simply because they are needed for implementation.

### 4.1 What the UCM Is

The UCM is:

- An implementation-independent semantic reference architecture.
- A reusable ontology for human-centered care information.
- A foundation for interoperable semantic models.
- A framework for shared concepts, roles, statements, participation, and domain specialization.

### 4.2 What the UCM Is Not

The UCM is not:

- An exchange standard or messaging specification.
- A FHIR profile, HL7 v2 model, C-CDA implementation guide, or X12 implementation guide.
- A database schema, API contract, or file format.
- A terminology or value set.
- A catalog of program-specific eligibility or policy rules.
- A copy of any implementation information model.

---

# Section 2 — Architectural Vision, Foundational Principles, and Semantic Architecture

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

The UCM is intended to serve as the semantic foundation for one or more implementation models. 

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

## 8. Organization of the Architectural Models

Section 3 defines the overall semantic architecture and SULO alignment. Sections 4 and 5 define the peer foundational Core and Participation Models. Section 6 defines Domain Models, reusable architectural patterns, and governance for specialization and promotion.

---

# Section 3 — UCM Semantic Architecture and Alignment with SULO


---

## 9. UCM Semantic Architecture

### 9.1 Architectural Foundation

The Unified Care Model (UCM) is an implementation-independent semantic reference architecture organized around three complementary model types:

- Core Model
- Participation Model
- Domain Models

The Core Model and Participation Model are peer foundational models. Domain Models are constructed through specialization and composition of reusable concepts from both.

```text
                         UCM
                          |
          +---------------+---------------+
          |               |               |
      Core Model   Participation Model   Domain Models
                                          |
                              +-----------+-----------+
                              |                       |
                    Clinical Care              Social Care
                    Domain Model               Domain Model
                          |
                          v
                Implementation Model
                          |
                          v
              FHIR | CDA | v2 | X12 | files
```

### 9.2 Architectural Characteristics

The UCM is:

- Semantic rather than implementation-centric.
- Implementation independent.
- Compositional rather than inheritance-driven.
- Reuse-oriented rather than domain-duplicative.
- Extensible through disciplined specialization.
- Governed so implementation detail does not expand the ontology unnecessarily.

---

## 10. Relationship to SULO

### 10.1 Architectural Alignment

The UCM is architecturally aligned with SULO. SULO supplies upper-level distinctions that help separate enduring entities, roles, processes, qualities, participation, and information objects.

The UCM neither replaces nor duplicates SULO. It organizes reusable care-oriented semantics while preserving those foundational distinctions.

### 10.2 Meaning, Assertion, and Representation

A central SULO-aligned distinction is the separation among:

1. **Domain semantics** — what exists, occurs, or characterizes a subject.
2. **Statement and information semantics** — what is asserted, recorded, or communicated about those domain semantics.
3. **Implementation representation** — how those semantics are encoded in a resource, segment, document entry, file, schema, API, or database.

For example:

```text
Person ---- hasCondition ----> ClinicalCondition
                                  ^
                                  |
                              is asserted by
                                  |
                              Statement
                                  ^
                                  |
                          represented within
                                  |
                         FHIR Condition
```

FHIR Condition may package both Condition-related semantics and Statement-related semantics. The UCM preserves the distinction; 

---

## 11. Core, Participation, and Domain Composition

### 11.1 Core and Participation

The Core Model answers primarily **what exists or occurs**. The Participation Model answers **how an entity participates in a context**.

```text
Person
  + PatientRole
  + Participation in Encounter
  = clinical participation context
```

The Person remains the enduring entity. PatientRole supplies contextual meaning and does not replace Person as identity.

### 11.2 Domain Specialization

Domain Models introduce specialized semantics only where composition of existing shared concepts is insufficient.

Most domain semantics should therefore be expressed using:

- Core classes and properties.
- Participation roles and relationships.
- Statement patterns.
- Semantic value objects.
- Domain-specific properties applied to existing UCM classes.

A domain property may describe a Core class without requiring a new subclass. For example, a Social Care property may apply to Person while remaining owned by the Social Care Domain Model.

### 11.3 When a New Domain Concept Is Required

A new Domain Model concept is justified when composition can describe relationships around a concept but cannot establish the semantic identity of the concept itself.

Example:

```text
Person ---- hasCondition ----> ClinicalCondition
```

Person, Statement, time, participation, and provenance can be reused from the shared UCM. However, if `ClinicalCondition` represents a distinct reusable clinical semantic type, the Clinical Care Domain Model may introduce it.

Likewise, the Social Care Domain may introduce `SocialNeed` if its meaning cannot be adequately reduced to an existing shared UCM concept.

---

## 12. Initial Domain Models

The initial Domain Models are Clinical Care and Social Care. Both reuse the Core and Participation Models and introduce only genuinely specialized, reusable domain meaning. Section 6 defines their scope, illustrative concepts, composition rules, and governance in detail.

### 12.3 Subject Areas Are Not Automatically Domain Models

Housing, food, transportation, education, justice, research, payment, and similar areas may be represented using existing UCM and Domain Model semantics without immediately becoming peer Domain Models.

A subject area should be promoted only when it develops a coherent independent body of specialized semantics and established external models should be leveraged wherever possible.

---

## 13. Domain Analysis Models and UCM Domain Models

Domain analysis informs semantic understanding but does not automatically create a UCM Domain Model. The UCM first evaluates candidate concepts against existing Core, Participation, and Domain Model semantics. Section 6 defines the complete evaluation and reuse process.

---

## 14. Implementation Models 

Implementation Models operationalize UCM meaning into computable, context-resolved semantics for implementation data.

Implementation Models may combine concepts from all applicable UCM models in a single semantic definition. For example, an implementation element may resolve to:

```text
Core:          Person
Participation: PatientRole
Clinical:      ClinicalCondition
Statement:     assertion about that condition
Context:       implementation-specific structure and policy
```

Implementation Models may additionally represent:

- Program-specific policy and eligibility rules.
- Structural semantics of implementation containers and hierarchies.
- Implementation-specific profile, loop, segment, entry, or schema context.
- Terminology bindings.
- Cardinality and validation constraints.
- Transformation and conformance rules.

These concerns are intentionally outside the UCM proper.

---

## 15. Architectural Benefits

This architecture provides stable shared meaning, controlled domain specialization, cross-domain reuse, precise implementation resolution, and a clear boundary between ontology and information models.

It permits the UCM to remain small and stable while allowing implementation models to carry the detailed semantics necessary for other uses.

---

# Section 4 — The Core Model

## 16. Purpose of the Core Model

The Core Model defines stable, reusable semantic concepts common across the care domains supported by the UCM. It provides the implementation-independent concepts from which Participation and Domain Model semantics can be composed.

The Core Model intentionally avoids domain-specific duplication and implementation-specific structures.

---

## 17. Design Objectives

The Core Model is designed to:

- Represent stable semantic identity and reusable foundational concepts.
- Provide shared abstractions across Clinical Care and Social Care.
- Support statements about entities, processes, qualities, conditions, and relationships.
- Provide semantic value objects independent of implementation datatypes.
- Support reuse by future Domain Models without requiring redesign of the Core.
- Remain independent of FHIR, C-CDA, HL7 v2, X12, files, schemas, and APIs.

---

## 18. Architectural Scope

Representative Core concepts include:

- Entity
- Person
- Organization
- SocialGroupEntity
- PhysicalEntity
- Device
- Location
- MaterialEntity / Substance / Specimen where shared
- Process / Activity
- Condition or state patterns where domain-neutral
- InformationArtifact
- Statement
- DefinitionArtifact
- SemanticValueObject
- Identifier
- Quantity
- TimeInterval

Core concepts are reusable because their meaning is not owned by one care domain.

---

## 19. Principal Core Concepts

### 19.1 Person

Person represents an individual human being and is intentionally separated from contextual roles such as PatientRole, ClientRole, MemberRole, BeneficiaryRole, or ProviderRole.

A Person may have a ClinicalCondition whether or not the Person is currently acting in a PatientRole. The role may contextualize a particular assertion, but it does not replace the Person as enduring identity.

### 19.2 Organization

Organization represents an organized social entity capable of participating in activities, programs, governance, or services.

### 19.3 SocialGroupEntity

SocialGroupEntity represents a group of persons defined by shared relationships, characteristics, or purposes. Membership is represented through the Participation Model.

### 19.4 Process and Activity

Processes and activities represent occurrences that unfold over time. Domain Models may specialize these concepts when a distinct reusable care-domain process is required.

### 19.5 InformationArtifact

InformationArtifact represents information that records, communicates, governs, or organizes assertions. An information artifact is distinct from the domain concept it describes.

### 19.6 Statement

Statement is the reusable UCM pattern for making an assertion about a subject, process, condition, quality, relationship, or other semantic concept.

A Statement may carry subject/context, predicate, object/value, temporal context, verification or modal status, provenance, and information-artifact context.

The Statement is not the thing it describes.

Example:

```text
Person ---- hasCondition ----> ClinicalCondition
                    ^
                    |
                 asserted by
                    |
                 Statement
```

A collection or organized set of statements about a particular focus may be represented in Implementation Models. The UCM supplies the Statement semantics; it does not need to reproduce every report, resource, document, or file structure used to organize statements.

### 19.7 DefinitionArtifact

DefinitionArtifact represents reusable definitions, criteria, policies, or semantic constraints when the definition itself is part of shared UCM meaning.

Specific operational policies — for example the current threshold used by a particular state assistance program — normally belong in the USCM rather than becoming UCM classes.

### 19.8 Semantic Value Objects

Semantic value objects such as PersonName, OrganizationName, PostalAddress, Identifier, Quantity, Code, and TimeInterval represent structured meaning independently of implementation-specific datatypes.

---

## 20. Foundational Concepts for Semantic Alignment

Core classes, properties, participation patterns, and value objects may serve as stable foundational concepts against which implementation semantics are aligned.

A foundational concept is not required to be a Core class. A Process, Role, Participation, Statement, or reusable domain concept may also serve as the stable semantic point of alignment when appropriate.

The term describes architectural use, not a new ontological category.

---

## 21. Core Properties and Domain-Owned Properties

A property may apply to a Core class while being defined in a Domain Model.

For example, a Social Care property may have Person as its semantic subject without requiring creation of a `SocialCarePerson` subclass.

Use this rule:

- If the property expresses broad, domain-independent meaning, define it in the shared UCM.
- If it expresses domain-specific meaning but describes a Core entity, define it in the applicable Domain Model and reuse the Core entity.
- If the same domain-specific property becomes broadly reusable across independent domains, consider promotion to shared UCM semantics.

This supports composition and avoids unnecessary inheritance.

---

## 22. Relationship to the Participation Model

The Core Model answers primarily:

> **What exists or occurs?**

The Participation Model answers:

> **How does an entity participate in a context?**

Together they provide the reusable semantic foundation from which Domain Models are composed.

---

## 23. Relationship to Domain Models and Implementation Models

Domain Models do not redefine Core concepts. They may:

- Apply domain-specific properties to Core concepts.
- Compose Core and Participation semantics.
- Introduce a distinct reusable domain concept when composition is insufficient.

Implementation Models then uses the Core, Participation, and applicable Domain Model semantics to resolve implementation data precisely.

For example, a FHIR Patient reference may resolve through an Implementation Model to a Person plus PatientRole context. A FHIR Condition may resolve to ClinicalCondition semantics plus Statement semantics rather than becoming a single mirrored UCM class.

---

## 24. Core Model Design Principles

1. Stable semantic identity.
2. Domain independence.
3. Reuse before extension.
4. Composition over deep inheritance.
5. Separation of domain semantics from information semantics.
6. Separation of Person from contextual roles.
7. Technology neutrality.
8. SULO alignment.
9. Foundational concepts may be reused by all Domain Models and implementing semantic models.
10. Program-specific policy and implementation constraints remain outside the Core Model.

---

# Section 5 — The Participation Model

## 25. Purpose of the Participation Model

The Participation Model defines the contextual semantics describing how entities participate in activities, organizations, groups, programs, services, transactions, and other contexts.

It is a first-class peer of the Core Model and is not an implementation detail.

---

## 26. Architectural Objectives

The Participation Model is designed to:

- Separate enduring identity from contextual participation.
- Model roles as contextual and anti-rigid.
- Represent participation as a reusable semantic relationship.
- Represent Membership as a first-class concept.
- Provide shared Eligibility and EligibilityCriteria semantics.
- Capture temporal participation and lifecycle changes.
- Support reuse by Clinical Care, Social Care, and Domain Models.

---

## 27. Fundamental Participation Pattern

The Participation Model answers:

> **How does an entity participate in a particular context?**

```text
Entity ---- bears ----> Role
   \                    /
    \                  /
      ---- Participation ----> Context
```

The same Person may simultaneously or sequentially bear PatientRole, ClientRole, MemberRole, CaregiverRole, BeneficiaryRole, SubscriberRole, or other roles.

---

## 28. Principal Participation Concepts

### 28.1 Role

Role represents a contextual capacity borne by an entity. Roles are temporary or conditional and do not redefine the identity of the bearer.

### 28.2 Participation

Participation represents an entity's involvement in a process, group, transaction, service, program, or other context, including the role and temporal scope of that involvement when material.

### 28.3 Membership

Membership is a first-class participation concept representing association of a Person or other eligible entity with a SocialGroupEntity or governed group context.

Membership may have lifecycle, status, effective period, governing criteria, and associated responsibilities.

### 28.4 MemberRole

MemberRole is the contextual role through which an entity participates as a member.

### 28.5 MembershipCriteria

MembershipCriteria describes the reusable semantic criteria governing membership. It is distinct from a particular program's current policy values or threshold expressions.

### 28.6 Eligibility and EligibilityCriteria

Eligibility represents qualification under defined conditions. EligibilityCriteria describes the criteria used to determine qualification.

These are **shared UCM participation/governance semantics**, not inherently Clinical Care or Social Care concepts.

Clinical Care may use Eligibility to determine qualification for a clinical service. Social Care may use the same pattern for a benefit or social-service program.

Specific program rules — for example Michigan residency plus household income below a particular percentage of FPL — belong in Implementation Models as program-specific policy semantics.

### 28.7 PatientRole and Other Subject Roles

PatientRole represents the contextual role borne by a Person in clinical care. It does not replace Person as the enduring subject.

A ClinicalCondition may be borne by or associated with the Person independently of PatientRole. Implementation Models may compose PatientRole into a fully resolved semantic assertion when an implementation representation, such as FHIR Patient, makes the patient context material.

---

## 29. Participation Lifecycle

Participation may have effective period, status, activation, suspension, termination, and historical state. These lifecycle semantics permit a longitudinal view without changing the identity of the underlying entity.

---

## 30. Separation of Identity and Participation

```text
Person
  |
  +-- bears --> PatientRole
  +-- bears --> ClientRole
  +-- bears --> MemberRole
  +-- bears --> CaregiverRole
```

The Person remains the same Person while roles evolve.

This distinction is important when mapping implementation information models. A FHIR `Patient`, CDA `patientRole`, or other implementation construct may encode both identity and role context. The USCM resolves those implementation semantics into the distinct UCM concepts.

---

## 31. Shared Participation Patterns Across Domains

The Participation Model supplies patterns reused by both initial Domain Models.

Examples:

```text
Clinical Care
Person + PatientRole + Participation + ClinicalProcess

Social Care
Person + ClientRole + Participation + SocialService

Eligibility
Person + Eligibility + EligibilityCriteria + Program/Service
```

A domain should not define a duplicate Patient, Client, Membership, or Eligibility architecture merely to support local use.

---

## 32. Relationship to Domain Models

Domain Models may specialize participation semantics only when a distinct reusable domain meaning exists. In many cases the domain simply composes shared Participation concepts with domain concepts.

For example, Clinical Care can combine PatientRole with ClinicalProcedure; Social Care can combine ClientRole with SocialService. The roles and participation machinery remain shared.

---

## 33. Relationship to Implementation Models

Implementation Models use Participation semantics to resolve implementation context precisely.

For example:

```text
FHIR Condition.subject -> Patient
               |
               v
        Implementation Model
Person + PatientRole context + ClinicalCondition + Statement
```

Implementation Models determine whether role context is material to the assertion and preserve it when necessary. The UCM does not need to copy the implementation's packaging of identity and role.

---

## 34. Participation Design Principles

1. Roles are contextual and anti-rigid.
2. Participation is distinct from identity.
3. Membership is a first-class semantic concept.
4. Eligibility and EligibilityCriteria are reusable across care domains.
5. Eligibility and Membership remain distinct.
6. Program-specific policy values belong in Implementation Models, not the shared Participation Model.
7. Participation possesses temporal semantics.
8. Domain Models reuse and compose participation semantics before specializing them.
9. Participation aligns architecturally with SULO.
10. Implementation role constructs are resolved by Implementation Models rather than mirrored directly into the UCM.

---

# Section 6 — Domain Models and Architectural Patterns

## 35. Purpose of Domain Models

Domain Models provide specialized, reusable semantics for coherent areas of care while preserving the common semantic foundation of the Core and Participation Models.

At the present stage, the UCM has two initial Domain Models:

- **Clinical Care Domain Model**
- **Social Care Domain Model**

Domain Models do not reproduce implementation information models and do not redefine shared UCM semantics.

---

## 36. Composition Principle

Most Domain Model semantics should be expressible through composition of existing UCM concepts, properties, Statements, Roles, Participation, and semantic value objects.

```text
Core Model
    +
Participation Model
    +
minimal domain-specific semantics
    =
Domain Model meaning
```

A domain may define a property that applies to a Core class without creating a new subclass of that Core class.

For example, a Social Care property may describe Person directly. A `SocialCarePerson` subclass is unnecessary unless the domain requires a genuinely distinct semantic type.

---

## 37. When a Domain Model Adds a New Concept

A new Domain Model class should be introduced only when the domain requires a distinct, reusable semantic type that cannot be adequately defined merely as a composition of existing UCM concepts and relationships.

### 37.1 Clinical Example — ClinicalCondition

The UCM can reuse Person, Statement, time, provenance, role, and participation patterns. However, if the clinical domain requires a distinct reusable concept representing a clinically significant condition, `ClinicalCondition` may be introduced by the Clinical Care Domain Model.

```text
Person ---- hasCondition ----> ClinicalCondition
                                  ^
                                  |
                              described/asserted by
                                  |
                              Statement
```

The domain introduces the missing semantic identity; the surrounding semantic machinery remains shared.

### 37.2 Social Care Example — SocialNeed

If SocialNeed represents a distinct reusable social-care semantic type that cannot be reduced to a generic shared Need or Condition pattern without semantic loss, the Social Care Domain Model may introduce it.

The Person, assessment process, Statement, participation, time, eligibility, and provenance semantics should still reuse the common UCM patterns.

### 37.3 Counterexample — Household Income

If the needed meaning is adequately expressed as:

```text
Household ---- hasIncome ----> MonetaryAmount
```

then a new `HouseholdIncome` class may be unnecessary. A property or Statement composition may be sufficient.

---

## 38. Initial Domain Models

### 38.1 Clinical Care Domain Model

The Clinical Care Domain Model specializes semantics required to represent clinical care.

Illustrative specialized concepts may include:

- ClinicalCondition
- ClinicalObservation / ClinicalFinding
- ClinicalProcedure
- AllergicDisposition / AllergyIntolerance semantics
- Other distinct reusable clinical semantic types

The Clinical Care Domain reuses Person, PatientRole, ProviderRole, Participation, Statement, Process, Organization, Identifier, Quantity, TimeInterval, and other shared UCM semantics.

### 38.2 Social Care Domain Model

The Social Care Domain Model specializes semantics required to represent social care and social-service activity.

Illustrative specialized concepts may include:

- SocialNeed
- SocialService
- SocialIntervention
- SocialAssessment semantics where genuinely specialized
- SocialBenefitProgram where reusable across programs

The Social Care Domain reuses Person, ClientRole, MemberRole, Membership, Eligibility, EligibilityCriteria, Organization, Statement, Process, and other shared UCM semantics.

---

## 39. Shared Concepts Versus Domain Concepts

Eligibility and EligibilityCriteria illustrate the distinction.

The shared UCM can express:

Entity ---- evaluated for ----> Eligibility
Eligibility ---- governed by ----> EligibilityCriteria
Eligibility ---- for ----> Program / Service / Benefit

Both Clinical Care and Social Care can reuse this semantic pattern.

A Clinical Care Domain may specialize the object of eligibility as a ClinicalService. A Social Care Domain may specialize it as a SocialBenefitProgram. This does not require separate ClinicalEligibility and SocialEligibility classes unless their meaning is genuinely different.

---

## 40. Program-Specific Policy and Implementation Models

Program-specific policy belongs in Implementation Models rather than in the UCM Domain Model when the policy is specific to a program, jurisdiction, organization, implementation, or current operational rule.

Example:

```text
UCM shared semantics
  Person
  Household
  Eligibility
  EligibilityCriteria
  Membership
  Income

Social Care Domain
  FinancialAssistanceProgram
  IncomeCriterion / ResidencyCriterion (if reusable domain types are needed)

Implementation Model program-specific semantics
  Michigan Program X
  residenceState = MI
  householdIncome < 150% FPL
  qualifyingDependentChild >= 1
  effective dates and program-specific policy logic

Implementation model
  MI_PROGRAM_CODE
  HH_INCOME
  FPL_PERCENT
  ELIG_STATUS
  file/API schema and datatypes
```

The UCM provides the semantic vocabulary. The Implementation Model composes it into the precise program policy. The implementation model provides the physical representation.

---

## 41. Domain Promotion

A subject area should not become a new Domain Model merely because it appears in a use case or SDOH framework.

A subject area may be promoted when:

1. It has a coherent body of specialized semantics.
2. Those semantics cannot be represented adequately through existing Core, Participation, Clinical Care, Social Care, and reusable patterns.
3. The semantics exist independently of the care processes addressing the subject area.
4. Promotion reduces semantic duplication rather than creating a silo.
5. Established authoritative domain models are leveraged or aligned wherever possible.

For example, Housing may initially be represented within Social Care use cases through housing needs, referrals, and interventions. If future interoperability requires independent semantics for dwelling, tenancy, occupancy, landlord relationships, subsidies, and housing-system processes, Housing may warrant promotion to a separate Domain Model.

---

## 42. Domain Analysis Models and Existing Domain Models

A Domain Analysis Model is an important source for understanding a domain, but it is not automatically imported wholesale into the UCM.

The UCM should:

1. Analyze the external domain model.
2. Reuse existing Core and Participation semantics first.
3. Reuse existing Domain Model concepts where possible.
4. Introduce only the specialized semantics that remain genuinely necessary.
5. Preserve alignment with established authoritative domain models instead of reinventing their semantics.

---

## 43. Domain Semantics and Information Models

A Domain Model defines specialized meaning in the subject domain. An Information Model defines how information about that meaning is organized and represented.

The same implementation construct may combine multiple domain and information semantics. Implementation Models are responsible for resolving that composition.

Example:

FHIR Condition
      |
      +--> ClinicalCondition semantics
      |
      +--> Statement / verification / provenance semantics
      |
      +--> PatientRole context when material

The UCM should not mirror the FHIR resource simply because the implementation packages these meanings together.

---

## 44. Reusable Architectural Patterns

Domain Models should reuse the following patterns rather than reinvent them:

- Entity + Role + Participation
- Person + contextual subject role
- Membership + MembershipCriteria
- Eligibility + EligibilityCriteria
- Process + Participation
- Domain concept + Statement about that concept
- Semantic value objects
- Temporal context and provenance

> **Reusable patterns ensure that each domain does not — and should not — reinvent shared semantics.**

---

## 45. Relationship to Implementation Models

Implementation Models use content from the Core Model, Participation Model, and applicable Domain Models to assign precise, unambiguous semantic meaning to data represented in implementation artifacts such as files, file formats, message structures, schemas, APIs, and databases.

Implementation Models may also represent structural semantics, profile or container context, qualifiers, program policy, and other implementation-specific information necessary to fully resolve meaning.

An Implementation Model is therefore not a Domain Model. It is an implementing semantic model that operationalizes the UCM for computable semantic resolution.

---

## 46. Domain Model Governance Principles

1. Reuse Core and Participation concepts before adding domain content.
2. Prefer properties, Statements, relationships, and composition over new classes.
3. Add a domain class only for a distinct reusable semantic type.
4. Keep the initial Domain Models limited to Clinical Care and Social Care until promotion criteria are satisfied.
5. Do not equate SDOH categories automatically with UCM Domain Models.
6. Leverage established authoritative domain models when a domain is promoted.
7. Keep program-specific policy in Implementation Models.
8. Keep exchange syntax, profiles, cardinality, file layout, datatypes, and transformation logic outside the UCM.
9. Preserve SULO-aligned separation of domain semantics from information semantics.
10. Allow domains to evolve independently without redefining shared meaning.

---

## 47. Summary

The Domain Model architecture is intentionally conservative. Clinical Care and Social Care are the two initial Domain Models. They reuse the Core and Participation Models extensively and add only the specialized semantics required by their domains.

Implementation Models operationalize those UCM semantics into precise, context-resolved definitions for implementation data and may carry program-specific policy and implementation semantics. Future Domain Models are promoted only when a coherent independent body of specialized semantics warrants that step and existing domain models have first been considered for reuse.

---
