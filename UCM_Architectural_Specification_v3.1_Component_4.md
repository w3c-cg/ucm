# Component 4 — The Core Model (Version 3.1)

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

Person ---- hasCondition ----> ClinicalCondition
                    ^
                    |
                 asserted by
                    |
                 Statement
```

A collection or organized set of statements about a particular focus may be represented in Implemention Models. The UCM supplies the Statement semantics; it does not need to reproduce every report, resource, document, or file structure used to organize statements.

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

## 23. Relationship to Domain Models and Implemention Models

Domain Models do not redefine Core concepts. They may:

- Apply domain-specific properties to Core concepts.
- Compose Core and Participation semantics.
- Introduce a distinct reusable domain concept when composition is insufficient.

Implemention Models then uses the Core, Participation, and applicable Domain Model semantics to resolve implementation data precisely.

For example, a FHIR Patient reference may resolve through a Implemention Model to a Person plus PatientRole context. A FHIR Condition may resolve to ClinicalCondition semantics plus Statement semantics rather than becoming a single mirrored UCM class.

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

**End of Component 4 — Version 3.1**
