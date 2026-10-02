# Component 5 — The Participation Model (Version 3.1)

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

Entity ---- bears ----> Role
   \                    /
    \                  /
      ---- Participation ----> Context

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

Specific program rules — for example Michigan residency plus household income below a particular percentage of FPL — belong in Implemention Models as program-specific policy semantics.

### 28.7 PatientRole and Other Subject Roles

PatientRole represents the contextual role borne by a Person in clinical care. It does not replace Person as the enduring subject.

A ClinicalCondition may be borne by or associated with the Person independently of PatientRole. Implemention Models may compose PatientRole into a fully resolved semantic assertion when an implementation representation, such as FHIR Patient, makes the patient context material.

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

## 33. Relationship to Implemention Models

Implemention Models use Participation semantics to resolve implementation context precisely.

For example:

FHIR Condition.subject -> Patient
               |
               v
        Implemention Model
Person + PatientRole context + ClinicalCondition + Statement


Implemention Models determine whether role context is material to the assertion and preserves it when necessary. The UCM does not need to copy the implementation's packaging of identity and role.

---

## 34. Participation Design Principles

1. Roles are contextual and anti-rigid.
2. Participation is distinct from identity.
3. Membership is a first-class semantic concept.
4. Eligibility and EligibilityCriteria are reusable across care domains.
5. Eligibility and Membership remain distinct.
6. Program-specific policy values belong in Implemention Models, not the shared Participation Model.
7. Participation possesses temporal semantics.
8. Domain Models reuse and compose participation semantics before specializing them.
9. Participation aligns architecturally with SULO.
10. Implementation role constructs are resolved by Implemention Models rather than mirrored directly into the UCM.

---

## 35. Transition to Component 6

Component 6 defines the Domain Model architecture, the initial Clinical Care and Social Care Domain Models, and the governed process for introducing or promoting additional domains.

---

**End of Component 5 — Version 3.1**
