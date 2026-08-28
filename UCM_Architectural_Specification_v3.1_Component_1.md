# Component 1 — Introduction and Overview (Version 3.1)

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

The UCM contains three complementary model types:


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

The Core Model and Participation Model are peer foundational models. Domain Models compose and specialize their reusable semantics.

The UCM is architecturally aligned with SULO. SULO supplies upper-level distinctions; the UCM supplies the reusable care-oriented semantic architecture.

At the present stage, the UCM has identified two initial Domain Models:

- **Clinical Care Domain Model**
- **Social Care Domain Model**

This is not a statement that the UCM can have only two domains. Additional subject areas may be incorporated through existing UCM semantics or promoted to Domain Models when their independent specialized semantics justify doing so.

---

## 4. Relationship Implementation Models

The UCM supplies reusable semantic vocabulary and patterns. The Implemention Models  uses concepts from the Core Model, Participation Model, and applicable Domain Models to assign precise, unambiguous meaning to data represented in implementations.

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

## Vision Statement

> The Unified Care Model provides an implementation-independent semantic reference architecture for whole-person care. It defines reusable meaning through Core, Participation, and Domain Models, while implementing semantic models such as the USCM compose that meaning into precise, context-resolved semantics for implementation data. This separation allows care domains, standards, technologies, and programs to evolve without fragmenting shared meaning.

---

**End of Component 1 — Version 3.1**
