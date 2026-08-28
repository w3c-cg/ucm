# Component 6 — Domain Models and Architectural Patterns (Version 3.1)

## 36. Purpose of Domain Models

Domain Models provide specialized, reusable semantics for coherent areas of care while preserving the common semantic foundation of the Core and Participation Models.

At the present stage, the UCM has two initial Domain Models:

- **Clinical Care Domain Model**
- **Social Care Domain Model**

Domain Models do not reproduce implementation information models and do not redefine shared UCM semantics.

---

## 37. Composition Principle

Most Domain Model semantics should be expressible through composition of existing UCM concepts, properties, Statements, Roles, Participation, and semantic value objects.


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

## 38. When a Domain Model Adds a New Concept

A new Domain Model class should be introduced only when the domain requires a distinct, reusable semantic type that cannot be adequately defined merely as a composition of existing UCM concepts and relationships.

### 38.1 Clinical Example — ClinicalCondition

The UCM can reuse Person, Statement, time, provenance, role, and participation patterns. However, if the clinical domain requires a distinct reusable concept representing a clinically significant condition, `ClinicalCondition` may be introduced by the Clinical Care Domain Model.


Person ---- hasCondition ----> ClinicalCondition
                                  ^
                                  |
                              described/asserted by
                                  |
                              Statement
```

The domain introduces the missing semantic identity; the surrounding semantic machinery remains shared.

### 38.2 Social Care Example — SocialNeed

If SocialNeed represents a distinct reusable social-care semantic type that cannot be reduced to a generic shared Need or Condition pattern without semantic loss, the Social Care Domain Model may introduce it.

The Person, assessment process, Statement, participation, time, eligibility, and provenance semantics should still reuse the common UCM patterns.

### 38.3 Counterexample — Household Income

If the needed meaning is adequately expressed as:


Household ---- hasIncome ----> MonetaryAmount
```

then a new `HouseholdIncome` class may be unnecessary. A property or Statement composition may be sufficient.

---

## 39. Initial Domain Models

### 39.1 Clinical Care Domain Model

The Clinical Care Domain Model specializes semantics required to represent clinical care.

Illustrative specialized concepts may include:

- ClinicalCondition
- ClinicalObservation / ClinicalFinding
- ClinicalProcedure
- AllergicDisposition / AllergyIntolerance semantics
- Other distinct reusable clinical semantic types

The Clinical Care Domain reuses Person, PatientRole, ProviderRole, Participation, Statement, Process, Organization, Identifier, Quantity, TimeInterval, and other shared UCM semantics.

### 39.2 Social Care Domain Model

The Social Care Domain Model specializes semantics required to represent social care and social-service activity.

Illustrative specialized concepts may include:

- SocialNeed
- SocialService
- SocialIntervention
- SocialAssessment semantics where genuinely specialized
- SocialBenefitProgram where reusable across programs

The Social Care Domain reuses Person, ClientRole, MemberRole, Membership, Eligibility, EligibilityCriteria, Organization, Statement, Process, and other shared UCM semantics.

---

## 40. Shared Concepts Versus Domain Concepts

Eligibility and EligibilityCriteria illustrate the distinction.

The shared UCM can express:

Entity ---- evaluated for ----> Eligibility
Eligibility ---- governed by ----> EligibilityCriteria
Eligibility ---- for ----> Program / Service / Benefit

Both Clinical Care and Social Care can reuse this semantic pattern.

A Clinical Care Domain may specialize the object of eligibility as a ClinicalService. A Social Care Domain may specialize it as a SocialBenefitProgram. This does not require separate ClinicalEligibility and SocialEligibility classes unless their meaning is genuinely different.

---

## 41. Program-Specific Policy and Implemention Models

Program-specific policy belongs in Implemention Models rather than in the UCM Domain Model when the policy is specific to a program, jurisdiction, organization, implementation, or current operational rule.

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

Implemention Model program-specific semantics
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

The UCM provides the semantic vocabulary. The Implemention Model composes it into the precise program policy. The implementation model provides the physical representation.

---

## 42. Domain Promotion

A subject area should not become a new Domain Model merely because it appears in a use case or SDOH framework.

A subject area may be promoted when:

1. It has a coherent body of specialized semantics.
2. Those semantics cannot be represented adequately through existing Core, Participation, Clinical Care, Social Care, and reusable patterns.
3. The semantics exist independently of the care processes addressing the subject area.
4. Promotion reduces semantic duplication rather than creating a silo.
5. Established authoritative domain models are leveraged or aligned wherever possible.

For example, Housing may initially be represented within Social Care use cases through housing needs, referrals, and interventions. If future interoperability requires independent semantics for dwelling, tenancy, occupancy, landlord relationships, subsidies, and housing-system processes, Housing may warrant promotion to a separate Domain Model.

---

## 43. Domain Analysis Models and Existing Domain Models

A Domain Analysis Model is an important source for understanding a domain, but it is not automatically imported wholesale into the UCM.

The UCM should:

1. Analyze the external domain model.
2. Reuse existing Core and Participation semantics first.
3. Reuse existing Domain Model concepts where possible.
4. Introduce only the specialized semantics that remain genuinely necessary.
5. Preserve alignment with established authoritative domain models instead of reinventing their semantics.

---

## 44. Domain Semantics and Information Models

A Domain Model defines specialized meaning in the subject domain. An Information Model defines how information about that meaning is organized and represented.

The same implementation construct may combine multiple domain and information semantics. Implemention Models are responsible for resolving that composition.

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

## 45. Reusable Architectural Patterns

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

## 46. Relationship to Implemention Models

Implemention Models use content from the Core Model, Participation Model, and applicable Domain Models to assign precise, unambiguous semantic meaning to data represented in implementation artifacts such as files, file formats, message structures, schemas, APIs, and databases.

Implemention Models may also represent structural semantics, profile or container context, qualifiers, program policy, and other implementation-specific information necessary to fully resolve meaning.

Implemention Models are therefore not a Domain Model. It is an Implementing Semantic Model that operationalizes the UCM for computable semantic resolution.

---

## 47. Domain Model Governance Principles

1. Reuse Core and Participation concepts before adding domain content.
2. Prefer properties, Statements, relationships, and composition over new classes.
3. Add a domain class only for a distinct reusable semantic type.
4. Keep the initial Domain Models limited to Clinical Care and Social Care until promotion criteria are satisfied.
5. Do not equate SDOH categories automatically with UCM Domain Models.
6. Leverage established authoritative domain models when a domain is promoted.
7. Keep program-specific policy in Implemention Models.
8. Keep exchange syntax, profiles, cardinality, file layout, datatypes, and transformation logic outside the UCM.
9. Preserve SULO-aligned separation of domain semantics from information semantics.
10. Allow domains to evolve independently without redefining shared meaning.

---

## 48. Summary

The Domain Model architecture is intentionally conservative. Clinical Care and Social Care are the two initial Domain Models. They reuse the Core and Participation Models extensively and add only the specialized semantics required by their domains.

Implemention Models operationalize those UCM semantics into precise, context-resolved definitions for implementation data and may carry program-specific policy and implementation semantics. Future Domain Models are promoted only when a coherent independent body of specialized semantics warrants that step and existing domain models have first been considered for reuse.

---

**End of Component 6 — Version 3.1**
