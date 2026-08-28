# Component 3 — UCM Semantic Architecture and Alignment with SULO (Version 3.1)


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
                Implemention Model
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

### 12.1 Clinical Care Domain Model

The Clinical Care Domain Model contains specialized reusable semantics needed to describe clinical care while reusing Core and Participation concepts.

Illustrative domain concepts may include:

- ClinicalCondition
- ClinicalObservation or ClinicalFinding
- ClinicalProcedure
- AllergicDisposition / AllergyIntolerance semantics
- Other genuinely clinical concepts that cannot be reduced to shared UCM composition

The Domain Model should not duplicate Person, PatientRole, Practitioner participation, Statement, Quantity, Identifier, TimeInterval, or other reusable shared semantics.

### 12.2 Social Care Domain Model

The Social Care Domain Model contains specialized reusable semantics needed to describe social care and social-service activity while reusing Core and Participation concepts.

Illustrative domain concepts may include:

- SocialNeed
- SocialService
- SocialIntervention
- SocialAssessment semantics where genuinely specialized
- SocialBenefitProgram or related domain concepts where reusable across programs

Eligibility and EligibilityCriteria remain shared UCM concepts unless a distinct domain-specific semantic specialization is actually required.

### 12.3 Subject Areas Are Not Automatically Domain Models

Housing, food, transportation, education, justice, research, payment, and similar areas may be represented using existing UCM and Domain Model semantics without immediately becoming peer Domain Models.

A subject area should be promoted only when it develops a coherent independent body of specialized semantics and established external models should be leveraged wherever possible.

---

## 13. Domain Analysis Models and UCM Domain Models

Domain analysis is the process of understanding a subject domain. A Domain Analysis Model may be an important input to the UCM, but it is not automatically equivalent to a UCM Domain Model.

The UCM evaluates concepts discovered through domain analysis against existing Core, Participation, and Domain Model semantics. Shared concepts are reused rather than copied into the Domain Model.

Therefore:

> **Domain analysis produces or informs the semantic understanding; the UCM Domain Model is the governed UCM specialization that remains after shared semantics have been reused.**

---

## 14. Implemention Models 

Implemention Models operationalizes UCM meaning into computable, context-resolved semantics for implementation data.

Implemention Models may combine concepts from all applicable UCM models in a single semantic definition. For example, an implementation element may resolve to:

```text
Core:          Person
Participation: PatientRole
Clinical:      ClinicalCondition
Statement:     assertion about that condition
Context:       implementation-specific structure and policy
```

Implemention Models may additionally represent:

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

## 16. Transition to Component 4

Component 4 introduces the Core Model in detail and establishes the shared semantic foundation that Domain Models.

---

**End of Component 3 — Version 3.1**
