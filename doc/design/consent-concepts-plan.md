# Plan: generalized consent concepts for the Unified Care Model

Status: **plan only**. No ontology, shapes or vocabulary files have been changed.
Date: 2026-11-27. Base branch: `reorg` (local). Namespace: `https://www.w3.org/ns/ucm#`.

## 1. Goal

Add a small set of consent concepts to UCM that are general enough to represent,
without loss, the consent artifacts found across health care and human services:

- a HIPAA or 42 CFR Part 2 authorization or FHIR `Consent` (privacy, treatment, research);
- an HMIS **Release of Information (ROI)** with Full, Limited or No Sharing, household
  scope, a witness, a start and end date, and a record lock for sensitive clients;
- an HMIS **privacy notice** posted at intake, which can be amended retroactively,
  and the **inferred, verbal or written** consent forms that a CoC may allow;
- **opt-in and opt-out** program models, **revocation**, **amendment and renewal**,
  **proxy** consent for minors and dependents, and **granular, sensitivity-based** sharing
  (data segmentation for privacy, security labels).

The UCM terms are the shared pivot. FHIR, HMIS and local forms map to them. They
do not replace those forms.

## 2. What the sources ask for

| Source | What UCM has to be able to say |
|---|---|
| **Stewards of Change / HIMSS Consent Learning Lab (2023)** | Granular consent, meaning what is shared, what is not, with whom and when. Revocation, with version control. Consent for families and households, not only individuals. Caregivers and parents consenting for others. Levels of sensitivity, such as 42 CFR Part 2, general PHI and sensitive social care information. Levels of authorization, from "a record exists" to the whole record to specific fields. Discovering every consent for one person across systems (the Consent Service Utility). Identity matching as a precondition. Cross-sector use: health, housing, education, child welfare, justice and nutrition. A universal consent form shared across programs. |
| **FHIR R5 Consent** | `status`, `category`, `subject`, `date`, `period`, `grantor`, `grantee`, `manager`, `controller`, `sourceAttachment` and `sourceReference`, `regulatoryBasis`, `policyBasis`, `policyText`, `decision` (permit or deny), `verification[]`, and a recursive `provision[]` holding `period`, `actor{role, reference}`, `action`, `securityLabel`, `purpose`, `documentType`, `resourceType`, `code`, `dataPeriod`, `data{meaning, reference}` and `expression`. In R5, permit or deny is the top-level `decision`, and provisions are exceptions to it. |
| **SHIFT Collaborative (GitHub org SHIFT-Task-Force, "Building privacy-first, trusted health exchange")** | A Security Labeling Service (SLS) tags data by content alone into sensitive topics, using `v3-ActCode` sensitivity codes (BH, PSYTHPN, SEX, STD, HIV, GDIS, SDV, SUD, OPIOIDUD, 42CFRPart2). Any sensitive tag makes the data confidentiality `R`. "Normal" data is simply untagged. Labels go in `meta.security`. The labels say nothing about consent: access policy is defined separately, and uses the labels. The org also forks the LEAP Consent Decision Service (`leap-cds-plus`) and LEAP SLS. Its value sets are examples only. Formal value sets are being built in the HL7 Cross-Paradigm Sensitive Data and Sensitivity Flags work. |
| **HUD HMIS FAQ 3310** | The form of consent (inferred, written, verbal) is set locally by the CoC. A privacy notice is posted at intake and states purposes, uses and disclosures. Amending a consent requires consent again for the amended parts. Privacy notice amendments apply retroactively only if the notice says they may (2004 HMIS Data and Technical Standards, §4.2.4). |
| **All Chicago HMIS ROI** | Consent must be recorded before any data entry. An ROI applies to selected household members, and a guardian signs for each child under 18. The recipient is the provider agency as a whole. Sharing is Full, Limited or No Sharing. The start date is the signature date. The end date is three years later, then the choice is confirmed again as a new ROI. The record is locked for DV or trafficking, HIV/AIDS, or an unaccompanied minor. The form has a witness. |

## 3. Design principles

These follow the existing UCM conventions and `arch-spec/ucm-ontology-requirements.md`.

1. **Separate the act from the record.** The consenting act is a `ucm:Process`
   (requirement 2 and 23). The resulting directive is an information object. The
   rules inside it are its parts.
2. **Reuse Participation for every party.** Grantor, subject, recipient, custodian,
   witness, verifier and proxy are `ucm:Participation`s with roles, as they are
   everywhere else in UCM. FHIR's `actor{role, reference}` is already this pattern.
3. **Keep statuses and codes in SKOS**, in the lifecycle file, with `-single` and
   `-anchored` shapes like the existing schemes. Map to HL7 and HMIS code systems
   with `skos:exactMatch`, `skos:closeMatch` or `skos:broadMatch`, not by subclassing.
4. **Keep the shapes open and tiered.** Identity-forming edges are Definitional
   (`sh:Violation`). Good practice is Recommended (`sh:Warning`). Shapes are never
   `sh:closed`, so FHIR and HMIS predicates pass through.
5. **Keep it domain-neutral.** Nothing in the core is HIPAA-only or HMIS-only.
   Regulation, program and form type are values, not classes.
6. **Make FHIR round-trips lossless** (requirement 3). Every R5 Consent element has
   a home (section 7).

## 4. Proposed classes (`unified-care-model.ttl`)

| Class | Parent | Definition (draft) | Why |
|---|---|---|---|
| `ucm:ConsentInteraction` | `ucm:Process` | A process in which a person, or someone authorized to act for them, grants, refuses, amends, renews or revokes permission for the collection, use or disclosure of information, or for an action concerning them. | The act. It carries who was present, when it happened and how (verbal, written). Revocation and amendment are also consent interactions. |
| `ucm:ConsentDirective` | `ucm:InformationArtifact` | A record of the choices a person, or a party acting for them, has made to permit or deny identified actions by identified parties, for given purposes, over given information, for a period. | The record. It maps 1:1 to FHIR `Consent` and to an HMIS ROI. It is an InformationArtifact, not a Statement (Q1, decided). |
| `ucm:ConsentProvision` | none (part of a directive) | A rule within a consent directive that permits or denies specific actions by specific actors, for specific purposes, on specific information, within a period. Provisions can nest as exceptions. | Granularity (SOCI) and FHIR `provision`. It is also how HMIS "Limited Sharing" is expressed. |
| `ucm:PrivacyNotice` | `ucm:PolicyDefinition` | A published statement of an organization's or program's purposes for collecting information and its permitted uses and disclosures, which applies without an individual consent act. | HUD posted notice, HIPAA Notice of Privacy Practices, GDPR transparency notice. |
| `ucm:ConsentPolicy` | `ucm:PolicyDefinition` | A policy, regulation or program rule that sets the consent model, the default decision and the conditions under which consent is required, allowed or not needed. | FHIR `policyBasis` and `regulatoryBasis`. Program-level opt-in or opt-out. The SOCI point that consent is often asked for when it is not needed. |
| `ucm:SelfConsentRule` | `ucm:ConsentPolicy` | A rule, in force in a jurisdiction, that sets when a minor or youth may consent for themselves: from what age, for which purposes, categories or sensitivities, and under what conditions. | Youth consent varies by region (section 6.2). |
| `ucm:JurisdictionContext` | `ucm:SemanticContext` | A legal or administrative region whose rules govern consent, such as a country, state, county, tribal nation or HUD Continuum of Care. Jurisdictions can nest. | Where a consent was given and which rules apply to it. |

New roles, all under `ucm:Role`:

| Role | Parent | Covers |
|---|---|---|
| `ucm:ConsentSubjectRole` | `ucm:SubjectRole` | The person, or group, whose information or care the consent concerns. FHIR `subject`. |
| `ucm:ConsentGrantorRole` | `ucm:Role` | The party who makes the choice. Often the same entity as the subject. FHIR `grantor`. |
| `ucm:ConsentProxyRole` | `ucm:ConsentGrantorRole` | A grantor acting for the subject: a parent, guardian, legal representative or authorized caregiver. All Chicago minors, SOCI recommendation 4. |
| `ucm:InformationRecipientRole` | `ucm:Role` | A party that a provision permits or denies to collect, access, use or disclose. FHIR `grantee` and `provision.actor`. HMIS ROI "Provider". |
| `ucm:InformationCustodianRole` | `ucm:Role` | A party responsible for holding, managing or enforcing the consent or the data. FHIR `manager` and `controller`. |
| `ucm:ConsentWitnessRole` | `ucm:Role` | A party who witnessed the consent. HMIS ROI "Witness". |
| `ucm:ConsentVerifierRole` | `ucm:Role` | A party who verified the consent with the subject or grantor. FHIR `verification.verifiedBy`. |

These roles attach through the existing pattern:
`ConsentInteraction ucm:hasParticipant Participation`, plus
`Participation ucm:participatingEntity Entity ; ucm:assumesRole Role`.
Recipients named in a provision are Participations in the *authorized* disclosure,
which is linked from the provision (see `ucm:provisionActor` below).

## 5. Proposed properties (`unified-care-model.ttl`)

Object properties:

| Property | Domain, then range | Maps to |
|---|---|---|
| `ucm:recordsConsentFrom` | `ConsentDirective`, then `ConsentInteraction` | The process that produced, amended or revoked the directive. Plays the role `generatedByProcess` plays for a Statement (Q1, decided). |
| `ucm:consentSubject` | `ConsentDirective`, then `Participation` | FHIR `subject`. The subject's Participation in the ConsentInteraction. The entity can be a `Person` or, for a household-wide ROI, a `SocialGroupEntity` (Q4). |
| `ucm:hasConsentDecision` | `ConsentDirective` or `ConsentProvision`, then `skos:Concept` (`ucm:ConsentDecision`) | FHIR `decision` on the directive. Required on every provision too (Q3, decided). |
| `ucm:hasConsentStatus` | `ConsentDirective`, then `skos:Concept` (`ucm:ConsentStatus`) | FHIR `status`. |
| `ucm:hasConsentCategory` | `ConsentDirective`, then `skos:Concept` (`ucm:ConsentCategory`) | FHIR `category`. Distinguishes a privacy consent or ROI from a treatment or research consent. |
| `ucm:hasConsentModality` | `ConsentInteraction`, then `skos:Concept` (`ucm:ConsentModality`) | HUD inferred, verbal or written. Also electronic. |
| `ucm:hasConsentInteractionType` | `ConsentInteraction`, then `skos:Concept` (`ucm:ConsentInteractionType`) | Grant, refuse, amend, renew, revoke, verify. |
| `ucm:hasProvision` | `ConsentDirective` or `ConsentProvision`, then `ConsentProvision` | FHIR `provision` and nested `provision.provision`. |
| `ucm:provisionActor` | `ConsentProvision`, then `Participation` | FHIR `provision.actor`, with role and entity on the Participation. |
| `ucm:governsAction` | `ConsentProvision`, then `skos:Concept` (`ucm:ConsentAction`) | FHIR `provision.action`. Named `governsAction`, not `permitsAction`, because a provision can be a deny (Q3). |
| `ucm:forPurpose` | `ConsentProvision` or `PrivacyNotice`, then `skos:Concept` (`ucm:PurposeOfUse`) | FHIR `provision.purpose`, HL7 PurposeOfUse, HMIS notice purposes. |
| `ucm:coversDataCategory` | `ConsentProvision`, then `skos:Concept` (`ucm:InformationCategory`) | FHIR `provision.documentType`, `resourceType` and `code`, plus SOCI cross-sector domains. |
| `ucm:coversSensitivity` | `ConsentProvision`, then `skos:Concept` (`ucm:SensitivityCategory` or `ucm:ConfidentialityLevel`) | FHIR `provision.securityLabel`, SHIFT SLS topics. |
| `ucm:coversInformation` | `ConsentProvision`, then `ucm:InformationArtifact` or `ucm:Statement` | FHIR `provision.data.reference`, with `data.meaning` via subproperties (Q6). |
| `ucm:dataPeriod` | `ConsentProvision`, then `time:TemporalEntity` (a subproperty of `ucm:hasTemporalContext`) | FHIR `provision.dataPeriod`. The time span of the *data*, as distinct from the period the consent applies. |
| `ucm:hasSensitivityLabel` | `InformationArtifact` or `Statement`, then `skos:Concept` | Security labels on data, like SHIFT SLS `meta.security`. Lets provisions match data without listing records. |
| `ucm:governedByPolicy` | `ConsentDirective`, `ConsentProvision` or `ProgramDefinition`, then `ConsentPolicy` | FHIR `policyBasis`, the program's consent rule. |
| `ucm:hasRegulatoryBasis` | `ConsentDirective` or `ConsentPolicy`, then `skos:Concept` (`ucm:RegulatoryBasis`) | FHIR `regulatoryBasis`. HIPAA, 42 CFR Part 2, the HMIS 2004 Notice, FERPA, GDPR, state law. |
| `ucm:inJurisdiction` | `ConsentDirective`, `ConsentInteraction` or `ConsentPolicy`, then `JurisdictionContext` | Where the consent was given, or where a policy is in force. Answers the Q1 follow-on: a new property rather than widening `madeWithinContext`. |
| `ucm:withinJurisdiction` | `JurisdictionContext`, then `JurisdictionContext` (transitive) | Nesting, for example a county within a state, or a CoC within a state. A rule in force in a state then applies to a CoC within it. |
| `ucm:selfConsentScope` | `SelfConsentRule`, then `skos:Concept` (`PurposeOfUse`, `ConsentCategory` or `SensitivityCategory`) | What the self-consent covers, for example STD testing, SUD or mental health treatment, or HMIS data sharing. No value means all consents. |
| `ucm:selfConsentCondition` | `SelfConsentRule`, then `skos:Concept` (`ucm:SelfConsentCondition`) | The condition that unlocks self-consent, such as being emancipated or an unaccompanied youth. Several values mean any one suffices. |
| `ucm:hasConsentModel` | `ConsentPolicy`, `ProgramDefinition` or `PrivacyNotice`, then `skos:Concept` (`ucm:ConsentModel`) | Opt-in, opt-out, opt-out with exceptions, no consent required. |
| `ucm:acknowledgesNotice` | `ConsentInteraction`, then `PrivacyNotice` | The subject was given or shown the notice. Covers HIPAA NPP acknowledgment and the HMIS posted sign. |
| `ucm:supersedes` | `ConsentDirective`, then `ConsentDirective` | Amendment and renewal, such as the All Chicago three-year re-confirmation. Gives the version chain SOCI asks for. |
| `ucm:revokedBy` | `ConsentDirective`, then `ConsentInteraction` | The revocation act: who, when, how. |
| `ucm:sourceDocument` | `ConsentDirective` or `PrivacyNotice`, then `ucm:InformationArtifact` | FHIR `sourceAttachment`, `sourceReference` and `policyText`, such as a scanned signed form. |
| `ucm:authorizedByConsent` | `ucm:Process`, then `ConsentDirective` | Ties consent to coordination. A `CoordinationRequest`, `Handshake` or disclosure can cite the directive that permits it. This is the UCM-specific value. |

Data properties:

| Property | Domain, then range | Notes |
|---|---|---|
| `ucm:amendmentAppliesRetroactively` | `PrivacyNotice`, then `xsd:boolean` | HUD §4.2.4 rule. |
| `ucm:minimumSelfConsentAge` | `SelfConsentRule`, then `xsd:nonNegativeInteger` | The age from which self-consent is allowed. Omit it when only a condition applies. |
| `ucm:birthDate` | `ucm:Person`, then `xsd:date`, `xsd:gYearMonth` or `xsd:gYear` | Date of birth, full or partial (Q16, decided). Matches FHIR `Patient.birthDate`, which allows a year or year-month, and `schema:birthDate`. Used to work out whether a subject was a minor on the consent date. |
| `ucm:birthDateQuality` | `ucm:Person`, then `skos:Concept` (`ucm:BirthDateQuality`) | How reliable the birth date is, mirroring the HMIS Date of Birth data quality element. |
| `ucm:recordLocked` | `ConsentDirective`, then `xsd:boolean` | All Chicago lock. Prefer a sensitivity label plus a deny provision, and keep this as a convenience flag (Q7). |
| `ucm:withdrawalMethod` | `ConsentDirective`, `PrivacyNotice` or `ConsentPolicy`, then `xsd:string` or `xsd:anyURI` | How the person revokes the consent: a URL, phone number, form or written instructions. ISO/IEC TS 27560 `withdrawal_method` (Q19, decided). |
| `ucm:retentionPeriod` | `ConsentDirective` or `ConsentProvision`, then `xsd:duration` | How long data may be kept, for example `P7Y`. On a provision it applies to that provision's purposes or data. TS 27560 `retention_period` (Q19, decided). |

Object properties added for Q19 (decided):

| Property | Domain, then range | Notes |
|---|---|---|
| `ucm:hasRetentionDisposition` | `ConsentDirective` or `ConsentProvision`, then `skos:Concept` (`ucm:RetentionDisposition`) | What happens to the data when the retention period ends: deleted, de-identified or archived. |
| `ucm:processingLocation` | `ConsentDirective` or `ConsentProvision`, then `JurisdictionContext` | Where the data may be stored or processed, such as a country or region. TS 27560 `storage_locations` and `processing_locations`. Several values mean any of them is allowed. |

Reused as is: `ucm:validDuring` for the consent period (FHIR `period`, HMIS start
and end), `ucm:occursDuring` and `ucm:statementDate` for when the interaction
happened or the directive was signed, `ucm:madeWithinContext` and `ucm:SemanticContext`
for jurisdiction and governance scope (domain question, see Q1), `ucm:Household` with `ucm:Membership`
and `HeadOfHouseholdRole` or `DependentRole` for family consent, and `ucm:MatchClaim`
for identity matching (SOCI recommendation 2).

### 5.1 Identity layer (added at Eric's request, 2026-11-27)

A consent is only meaningful if it is bound to a particular, identified individual,
and if the grantor is who they say they are. UCM today has `ucm:Entity` and
`ucm:MatchClaim`, but nothing that says *how* an entity is identified or how sure we
are. This layer adds that, as a superset that applies to **every** kind of
`ucm:Entity` (persons, organizations, devices, households), not only to persons.
It uses NIST SP 800-63-4 for the assurance levels, OpenID Connect (with OpenID
Connect for Identity Assurance) and W3C Verifiable Credentials for carrying identity
claims, and the Kantara Initiative and the Sequoia Project's TEFCA rules as the
trust frameworks that say which levels are required and who may vouch for them.

**Classes** (`unified-care-model.ttl`):

| Class | Parent | Definition (draft) | Aligns with |
|---|---|---|---|
| `ucm:Identity` | `ucm:InformationArtifact` | A set of identifiers, attributes and characteristics by which one entity is recognized within a context, such as a system, program, jurisdiction or trust framework. An entity can have many identities. | NIEM `nc:IdentityType`. OIDC subject (`iss` and `sub`). VC `credentialSubject`. NIST "subscriber account". |
| `ucm:Identifier` | `ucm:InformationArtifact` | A value, unique within a stated system or issuer, that designates an identity. Examples are an MRN, HMIS Personal ID, Medicaid ID, state ID number, OIDC `sub` or a DID. | NIEM `nc:IdentificationType`. FHIR `Identifier`. |
| `ucm:IdentityProofing` | `ucm:Process` | A process that establishes, to a stated assurance level, that an identity corresponds to a specific real-life person. | NIST SP 800-63A "identity proofing". OIDC IDA `verification`. |
| `ucm:IdentityEvidence` | `ucm:InformationArtifact` | Evidence used in identity proofing: a document, an electronic record, a vouch by another party, or an electronic signature. | NIST evidence, rated FAIR, STRONG or SUPERIOR. OIDC IDA `evidence` types `document`, `electronic_record`, `vouch`, `electronic_signature`. |
| `ucm:Authentication` | `ucm:Process` | A process in which a claimant proves control of one or more authenticators bound to an identity. | NIST SP 800-63B. OIDC `auth_time`, `acr`, `amr`. |
| `ucm:IdentityAssertion` | `ucm:InformationArtifact` | A statement from an identity provider to a relying party about an authenticated identity, at a stated federation assurance level. | NIST SP 800-63C. An OIDC ID Token. A SAML assertion. |
| `ucm:Credential` | `ucm:InformationArtifact` | A set of claims about an identity, issued and signed by an issuer, and held by the subject or a holder. | W3C VC 2.0 `cred:VerifiableCredential` (`issuer`, `credentialSubject`, `validFrom`, `validUntil`, `credentialStatus`, `evidence`, `termsOfUse`). |
| `ucm:TrustFramework` | `ucm:PolicyDefinition` | A set of rules, under a governing body, for proofing, authentication, federation and certification that participants agree to rely on. | NIST SP 800-63-4. Kantara's assurance program. TEFCA's IAS SOP (Sequoia Project as RCE). OIDC IDA `trust_framework`. |
| `ucm:AssuranceCertification` | `ucm:InformationArtifact` | A record that an assessor has found a provider conformant to a trust framework at stated assurance levels, for a period. | Kantara approval of a CSP at IAL2 and AAL2. |

**Roles**, used through Participation in `IdentityProofing` or `Authentication`:
`IdentityApplicantRole` (under `SubjectRole`), `CredentialServiceProviderRole`,
`IdentityProviderRole`, `RelyingPartyRole`, `ProofingAgentRole`, `TrustedRefereeRole`
and `ApplicantReferenceRole`.

NIST SP 800-63-4 matters here. Its *applicant reference* can vouch for an applicant's identity or conditions, naming **homelessness** as an example, and its *trusted referee* makes risk-based decisions for applicants who cannot meet the normal evidence rules. Those two roles are how people without government ID, such as many unaccompanied youth and people experiencing homelessness, can still reach an assurance level. That matters directly for HMIS consent.

**Properties:**

| Property | Domain, then range | Notes |
|---|---|---|
| `ucm:hasIdentity` / `ucm:identityOf` | `Entity` and `Identity` (inverses) | The superset link. Any entity, many identities. |
| `ucm:hasIdentifier` | `Identity`, then `Identifier` | |
| `ucm:identifierValue` | `Identifier`, then `xsd:string` | |
| `ucm:identifierSystem` | `Identifier`, then `xsd:anyURI` | The namespace. For OIDC, this is the `iss`. |
| `ucm:hasIdentifierType` | `Identifier`, then `skos:Concept` (`ucm:IdentifierType`) | |
| `ucm:issuedBy` | `Identifier`, `Credential` or `AssuranceCertification`, then `Entity` | |
| `ucm:identifiedAs` | `Participation`, then `Identity` | Which identity a participant acted under. This is how a consent's grantor and subject are tied to identities. |
| `ucm:establishesIdentity` | `IdentityProofing`, then `Identity` | |
| `ucm:usedEvidence` | `IdentityProofing`, then `IdentityEvidence` | |
| `ucm:hasEvidenceType`, `ucm:hasEvidenceStrength` | `IdentityEvidence`, then `skos:Concept` | |
| `ucm:hasProofingType` | `IdentityProofing`, then `skos:Concept` (`ucm:ProofingType`) | Remote unattended, remote attended, on-site unattended, on-site attended. |
| `ucm:achievedIAL` | `IdentityProofing` or `Identity`, then `skos:Concept` (`ucm:IdentityAssuranceLevel`) | |
| `ucm:achievedAAL` | `Authentication`, then `skos:Concept` (`ucm:AuthenticatorAssuranceLevel`) | |
| `ucm:achievedFAL` | `IdentityAssertion`, then `skos:Concept` (`ucm:FederationAssuranceLevel`) | |
| `ucm:assertsIdentity` | `IdentityAssertion` or `Credential`, then `Identity` | |
| `ucm:authenticatedBy` | `ConsentInteraction`, then `Authentication` | How the grantor was authenticated when consenting electronically. |
| `ucm:underTrustFramework` | `IdentityProofing`, `IdentityAssertion`, `Credential` or `AssuranceCertification`, then `TrustFramework` | |
| `ucm:trustFrameworkIdentifier` | `TrustFramework`, then `xsd:string` | The OIDC IDA `trust_framework` string, for example `nist_800_63A`. |
| `ucm:certifies` | `AssuranceCertification`, then `Organization` | |
| `ucm:requiresIAL`, `ucm:requiresAAL` | `ConsentPolicy` or `TrustFramework`, then `skos:Concept` | For example, TEFCA IAS requires IAL2 proofing and AAL2 authentication. |
| `ucm:credentialTermsOfUse` | `Credential`, then `PolicyDefinition` | VC `termsOfUse`. Lets a consent policy ride with a credential. |
| `ucm:matchesIdentity` | `MatchClaim`, then `Identity` | The existing `ucm:MatchClaim` now names the identities it says co-refer. Covers TEFCA's demographic double-check and the SOCI identity-matching recommendation. |

**SKOS schemes** (lifecycle file):

| Scheme | Concepts | Source (status of check) |
|---|---|---|
| `ucm:IdentityAssuranceLevel` | `NoIdentityProofing`, `IAL1`, `IAL2`, `IAL3` | NIST SP 800-63-4. Rev 4 names no "IAL0"; it describes the no-proofing case in words. |
| `ucm:AuthenticatorAssuranceLevel` | `AAL1`, `AAL2`, `AAL3` | NIST SP 800-63B-4. The exact level definitions still need a direct read. |
| `ucm:FederationAssuranceLevel` | `FAL1`, `FAL2`, `FAL3` | NIST SP 800-63C-4. The exact level definitions still need a direct read. |
| `ucm:EvidenceStrength` | `Fair`, `Strong`, `Superior` | NIST SP 800-63A-4. |
| `ucm:ProofingType` | `RemoteUnattended`, `RemoteAttended`, `OnsiteUnattended`, `OnsiteAttended` | NIST SP 800-63A-4. |
| `ucm:IdentityEvidenceType` | `Document`, `ElectronicRecord`, `Vouch`, `ElectronicSignature` | OIDC IDA (final). |
| `ucm:RetentionDisposition` (consent, Q19) | `RetentionDelete`, `RetentionDeidentify`, `RetentionArchive` | UCM-defined. |
| `ucm:IdentifierType` | `MedicalRecordNumber`, `HMISPersonalID`, `MedicaidID`, `StateIDNumber`, `DriversLicenseNumber`, `SocialSecurityNumber`, `OIDCSubject`, `DecentralizedIdentifier`, `OtherIdentifier` | Seed list. FHIR `v2-0203` matches go in the mapping file. |

Each level concept carries an integer `ucm:assuranceRank` annotation (IAL1 = 1, and
so on), so shapes can compare levels with `>=`.

**Shapes** (Recommended unless noted):
- `Identifier-value` (Definitional): exactly one `identifierValue`, a string. At most one `identifierSystem`.
- `ConsentIdentityAssuranceShape`: if the directive is `governedByPolicy` a policy with `requiresIAL`, the grantor's participation is `identifiedAs` an identity whose `achievedIAL` rank meets or exceeds it. Same for `requiresAAL` and `authenticatedBy`.
- `ApplicantReferenceShape`: an `ApplicantReferenceRole` participant is not also the `IdentityApplicantRole` participant. NIST says a reference "does not act on behalf of the applicant", so the shape also flags the same entity acting as both reference and consent proxy for that subject.
- `CredentialValidityShape`: `Credential` `validDuring` is reused, with the existing temporal shapes.

## 6. Proposed SKOS schemes (`ucm-lifecycle-vocabularies.ttl`)

Each scheme follows the existing pattern: `dcterms:created`, `dcterms:description`
as a question, `dcterms:publisher "MDIX"`, `skos:definition`, top concepts, and
`skos:broader` for "record narrower when known".

| Scheme | Concepts (draft) | External mapping |
|---|---|---|
| `ucm:ConsentStatus` (Does this consent apply now?) | `ConsentDraft`, `ConsentActive`, `ConsentInactive` with narrower `ConsentRevoked`, `ConsentExpired` and `ConsentSuperseded`, plus `ConsentRefused`, `ConsentEnteredInError`, `ConsentStatusUnknown` | FHIR `consent-state-codes` (verified): draft, active, inactive, not-done, entered-in-error, unknown. FHIR has no revoked or expired, so they map `skos:broadMatch` to inactive. Note FHIR's display for `not-done` is "Abandoned", which only closeMatches `ConsentRefused`. |
| `ucm:ConsentDecision` | `Permit`, `Deny` | FHIR ConsentProvisionType permit and deny. |
| `ucm:ConsentCategory` | `PrivacyConsent` with narrower `ReleaseOfInformation`, `ConsentToCollect` and `ConsentToShare`; `TreatmentConsent`; `ResearchConsent`; `AdvanceDirective` (placeholder) | `consentcategorycodes` (verified, Appendix A): `research`, `acd`, `hcd`, `npp`, `emrgonly`. HL7 has no general privacy-consent or ROI category, so `PrivacyConsent` and `ReleaseOfInformation` stay UCM-local. `v3-ActCode#42CFRPart2CD` is a closeMatch for a Part 2 consent. |
| `ucm:ConsentModality` | `WrittenConsent`, `ElectronicConsent` (broader: written), `VerbalConsent`, `InferredConsent` | HUD FAQ 3310. |
| `ucm:ConsentModel` | `OptIn`, `OptInWithRestrictions`, `OptOut`, `OptOutWithExceptions`, `NoConsentRequired` | SOCI "opt-in / opt-out models". HIE consent model literature. |
| `ucm:ConsentInteractionType` | `Grant`, `Refuse`, `Amend`, `Renew`, `Revoke`, `Verify` | HUD re-consent on amendment. All Chicago renewal. |
| `ucm:ConsentAction` | `Collect`, `Access`, `Use`, `Disclose`, `Redisclose`, `Correct` | `consentaction` (verified): collect, access, use, disclose, correct (display "Access and Correct"). `Redisclose` has no HL7 code. It is new (SOCI "share or reshare", Part 2), broader `Disclose`. |
| `ucm:PurposeOfUse` | `Treatment`, `EmergencyTreatment`, `CareCoordination`, `CareManagement`, `Payment`, `Operations`, `EligibilityDetermination`, `Research`, `PublicHealth`, `FamilyRequested`, `PatientRequested`, plus the UCM-defined social-care purposes in section 6.1 | `v3-ActReason` (verified, Appendix A): TREAT, ETREAT, COC, CAREMGT, HPAYMT, HOPERAT, ELIGDTRM, HRESCH, PUBHLTH, FAMRQT, PATRQT. HL7 has no housing or social-services purposes, so UCM defines them (section 6.1). |
| `ucm:InformationCategory` | `ClinicalInformation`, `BehavioralHealthInformation`, `HousingInformation`, `IncomeAndBenefitsInformation`, `EducationInformation`, `ChildWelfareInformation`, `JusticeInformation`, `NutritionInformation`, `IdentifyingInformation` | Lines up with the UCM `*Domain` and `*Context` classes (Q5). `IdentifyingInformation` closeMatch `v3-ActCode#IDS` and `#DEMO`. |
| `ucm:SensitivityCategory` | `SubstanceUseDisorder` (narrower `AlcoholUseDisorder`, `OpioidUseDisorder`), `BehavioralHealth` (narrower `MentalHealth`, `PsychiatricDisorder`, `PsychotherapyNote`), `HIV`, `SexuallyTransmittedDisease`, `SexualAndReproductiveHealth`, `GenderAndSexualOrientation`, `GeneticDisease`, `SexualAssaultAbuseDomesticViolence`, `Adolescent`, `Part2Protected` | `v3-ActCode` (verified, Appendix A): SUD, ETH, ETHUD, OPIOIDUD, BH, MH, PSY, PSYTHPN, HIV, STD, SEX, GENDER, GDIS, SDV, ADOL, 42CFRPart2. Same codes SHIFT SLS emits. Covers the All Chicago lock triggers for DV and HIV. Abortion, human trafficking and unaccompanied youth have no HL7 sensitivity code, so UCM defines them (section 6.1). |
| `ucm:ConfidentialityLevel` | `Unrestricted`, `Low`, `Moderate`, `Normal`, `Restricted`, `VeryRestricted` | `v3-Confidentiality` U, L, M, N, R, V (verified). |
| `ucm:RegulatoryBasis` | `HIPAA` (narrower `HIPAAAuthorization`, `HIPAANoticeOfPrivacyPractices`, `HIPAAResearch`), `CFR42Part2`, `CommonRule`, `HMISDataStandards2004`, `FERPA`, `GDPR`, `StateLaw` | `consentpolicycodes` (verified, Appendix A): `hipaa-auth`, `hipaa-npp`, `hipaa-research`, `hipaa-restrictions`, `hipaa-self-pay`, `cric`, `mdhhs-5515`. That code system has no 42 CFR Part 2, HMIS, FERPA or GDPR code, so UCM defines them (section 6.1). Adopters can add their own. |

HMIS sharing levels are **not** core concepts. They go in the mapping file
(section 8) as compositions:

- **Full Sharing** is `decision Permit` with no deny provisions.
- **No Sharing** is `decision Deny`.
- **Limited Sharing** is `decision Permit` with one or more deny provisions, for
  example on `SensitivityCategory` or on particular recipients.

### 6.1 UCM-defined concepts where HL7 has no code

HL7 has no codes for these (Appendix A), so UCM defines them. Each one sits in the
scheme named, uses `skos:broader` for hierarchy, and links outward only with
`skos:closeMatch`, `skos:broadMatch` or `skos:related`, never `exactMatch`. Those links
go in `mapping/consent-mappings.ttl` (Q12).

**Housing and social-services purposes (`ucm:PurposeOfUse`)**

| Concept | Broader | Definition (draft) | Nearest external code |
|---|---|---|---|
| `SocialCareCoordination` | `CareCoordination` | Coordinating social care services for a person or household across agencies and programs. | broadMatch `v3-ActReason#COC` (health-oriented) |
| `CoordinatedEntry` | `SocialCareCoordination` | Assessing, prioritizing and referring people experiencing homelessness through a CoC's coordinated entry process. | none |
| `HousingPlacement` | `SocialCareCoordination` | Matching a person or household to a housing program or unit and moving them in. | none |
| `SocialServicesReferral` | `SocialCareCoordination` | Referring a person to a community-based or government service and tracking whether they were connected (a closed-loop referral). | none |
| `SocialCaseManagement` | `SocialCareCoordination` | Ongoing case management by a social care provider, such as a child welfare or housing case manager. | closeMatch `v3-ActReason#CAREMGT` |
| `BenefitsEnrollment` | `EligibilityDetermination` | Applying for, enrolling in or recertifying public benefits such as SNAP, TANF or Medicaid. | broadMatch `v3-ActReason#ELIGDTRM` |
| `ProgramReporting` | none (top concept) | Required reporting to funders or oversight bodies, such as HUD HMIS reports. | broadMatch `v3-ActReason#HOPERAT` |

`CoordinatedEntry` and `HousingPlacement` tie directly to the existing `ucm:HousingContext`,
`ucm:HousingAssessment` and `ucm:CoordinationRequest` classes.

**Regulatory bases (`ucm:RegulatoryBasis`)**

| Concept | Covers | Nearest external code | Modeling note |
|---|---|---|---|
| `HMISDataStandards` | HUD HMIS Data and Technical Standards (2004 notice, including the privacy and security standards), plus the current HMIS Data Standards. | none | HUD leaves the form of consent to each CoC. So a `ConsentPolicy` with this basis usually also needs a local CoC policy with its own `ConsentModel`. |
| `CFR42Part2` | Confidentiality of Substance Use Disorder Patient Records, 42 CFR Part 2. | closeMatch `v3-ActCode#42CFRPart2` | Works with `Part2Protected` sensitivity and the `Redisclose` action. |
| `FERPA` | Family Educational Rights and Privacy Act (20 U.S.C. §1232g; 34 CFR Part 99). | none | Education records. Consent passes from parent to student at 18 or at postsecondary enrollment, which affects `ConsentProxyRole`. |
| `GDPR` | EU General Data Protection Regulation (Regulation (EU) 2016/679). | none | Consent is only one of six lawful bases under GDPR. `ConsentPolicy` should be able to say "lawful basis is not consent", which `ConsentModel/NoConsentRequired` covers. |
| `VAWA` | Violence Against Women Act confidentiality provisions. | none | Victim service providers may not enter personally identifying information into HMIS. Model this as a `ConsentPolicy` with a deny that no individual `ConsentDirective` can override. HMIS-comparable databases are the permitted alternative. |

**Sensitivity categories (`ucm:SensitivityCategory`)**

| Concept | Broader or related | Definition (draft) | Nearest external code | Modeling note |
|---|---|---|---|---|
| `Abortion` | broader `SexualAndReproductiveHealth` | Information about seeking, obtaining, providing or facilitating abortion. | closeMatch SHIFT `ExtraSensitiveCodes#ABORTION` (a placeholder marked TODO in its source); broadMatch `v3-ActCode#SEX` | Its legal sensitivity varies by state, so it is kept separate from SEX. Provisions can then deny it while permitting other reproductive health data. |
| `HumanTrafficking` | related `SexualAssaultAbuseDomesticViolence` | Information that a person is or was a victim of sex or labor trafficking, or is fleeing it. | related `v3-ActCode#SDV` (SDV does not cover labor trafficking) | An All Chicago record-lock trigger. Often paired with a VAWA basis. |
| `UnaccompaniedYouth` | related `Adolescent` | Information that a person is a youth without a parent or guardian, such as an unaccompanied homeless youth. | related `v3-ActCode#ADOL` | It is a status, not a topic, and HUD youth definitions run past age 18. So it is related to ADOL, not narrower. It is an All Chicago lock trigger. It also changes who can consent: often no proxy exists, and the jurisdiction's rules may allow self-consent (section 6.2). |

### 6.2 Youth consent that varies by region

Who may consent for a minor or youth depends on where the consent is given, and on
what it is for. Examples:
- The age of majority differs between jurisdictions.
- Many US states let minors consent on their own to STD testing, substance use
  treatment or mental health care, each with a different minimum age.
- Emancipated and married minors, and minor parents, often have full capacity.
- Unaccompanied homeless youth may self-consent in some states and not in others.
- A CoC may set its own rule. All Chicago lets clients 18 and over sign, and a
  guardian signs for each child under 18.
- FERPA moves education-record rights from parent to student at 18.

The plan models this as data, not as fixed logic:

1. **`ucm:JurisdictionContext`** (a `SemanticContext`) names a region, nested with
   `withinJurisdiction`. A CoC sits within a state, and a county within a state.
2. **`ucm:SelfConsentRule`** (a `ConsentPolicy`) is `inJurisdiction` a region and states:
   - `minimumSelfConsentAge`, optional;
   - `selfConsentScope`: the purposes, consent categories or sensitivities it covers;
   - `selfConsentCondition`: the conditions that unlock it.
   One jurisdiction can hold several rules, for example one for STD testing at 12
   and a general one at 18.
3. **The consent links to the rule it relied on.** A youth who consents for
   themselves is the grantor, and the directive is `governedByPolicy` the rule. A
   guardian who consents is a `ConsentProxyRole` grantor, as before. So the record
   shows *why* the consent was valid, which matters when a youth moves between
   regions or the data crosses a border.
4. **New SKOS scheme `ucm:SelfConsentCondition`** in the lifecycle file:
   `AgeOfMajority`, `EmancipatedMinor`, `MarriedMinor`, `MinorParent`,
   `UnaccompaniedYouth`, `SelfSupporting`, `PostsecondaryEnrollment`, `MatureMinor` (a clinician's capacity
   judgment), `ServiceSpecificMinorConsent`. A closeMatch example is
   `consentpolicycodes#illinois-minor-procedure` (verified, Appendix A).
5. **Age comes from `ucm:birthDate`** on `ucm:Person` (Q16). Age is computed as of
   the ConsentInteraction's `occursDuring` date, never stored, because it changes.
   A partial birth date (`xsd:gYear` or `xsd:gYearMonth`, which FHIR and HMIS both
   allow) gives an age range. The shape treats the subject as a minor if *any* date
   in that range would make them one, which is the conservative reading. A new
   SKOS scheme `ucm:BirthDateQuality` (`FullDateReported`, `ApproximateOrPartial`,
   `ClientDoesNotKnow`, `ClientPreferNotToAnswer`, `DataNotCollected`) mirrors the
   HMIS Date of Birth data quality element. Its codes are to be verified against the
   current HMIS Data Standards Manual. A birth date is itself identifying data
   (`IdentifyingInformation`), so provisions can deny it like any other category.
6. **Validation** is Recommended only (`SelfConsentBasisShape`, section 9). It warns
   when a youth self-consents with no rule in force for that region. It cannot
   decide legality, because the rules are adopter data.

UCM ships the structure, the condition vocabulary, and the anonymized example
rules in section 6.3. Adopters, CoCs or state partners publish their own real rules
as `SelfConsentRule` instances.

### 6.3 Example self-consent rules (anonymized)

> **Disclaimer.** These examples are drawn from real state, CoC and federal rules
> as summarized in the sources cited below, as of the dates shown. They are
> illustrations of the model, not legal guidance. Actual state and CoC rules vary,
> change over time, and have conditions and exceptions not shown here. States and
> CoCs are deliberately not named. Anyone publishing real rules must check them
> against the current statute, regulation or CoC policy.

| Example | Rule as modeled | `SelfConsentRule` values | Drawn from |
|---|---|---|---|
| **Federal: education records** | Rights over education records pass from parents to the student at 18, or at any age once the student attends a postsecondary institution. A school *may* still give parents access if the student is their tax dependent. | Jurisdiction: United States. `minimumSelfConsentAge 18`. Conditions: `AgeOfMajority` or `PostsecondaryEnrollment`. Scope: `EducationInformation`. Regulatory basis: `FERPA`. | U.S. Department of Education, Student Privacy Policy Office, "Eligible Student" (studentprivacy.ed.gov). 34 CFR §99.3. 20 U.S.C. §1232g(d). |
| **Example State A: STI care from 12** | Minors 12 and older may consent to STI testing and treatment. Providers may, but need not, tell parents. | `minimumSelfConsentAge 12`. Condition: `ServiceSpecificMinorConsent`. Scope: `SexuallyTransmittedDisease`, purpose `Treatment`. | Guttmacher Institute, "Minors' Access to STI Services", as of 2026-08-01. Four states follow this age threshold. |
| **Example State B: STI care from 14** | Minors 14 and older may consent to STI testing and treatment. There is no parental notification provision. | `minimumSelfConsentAge 14`. Condition: `ServiceSpecificMinorConsent`. Scope: `SexuallyTransmittedDisease`. | Same Guttmacher source. Three states set 14. |
| **Example State C: HIV care from 13** | Minors 13 and older may consent to HIV testing and treatment. | `minimumSelfConsentAge 13`. Scope: `HIV`, purpose `Treatment`. | Same Guttmacher source. One state sets an HIV-specific age. |
| **Example State D: housing for homeless youth** | A youth aged 16 or 17 who is homeless, or a victim of domestic violence, and is self-supporting may consent to housing, shelter, medical and mental health care and related services. A homeless service provider or school district homeless liaison verifies the status in a letter. | `minimumSelfConsentAge 16`. Conditions: `UnaccompaniedYouth` and `SelfSupporting`. Scope: `HousingPlacement`, `SocialCareCoordination`, `Treatment`. The liaison's letter is a ConsentInteraction of type `Verify` with a `ConsentVerifierRole` participation. | SchoolHouse Connection, "State Laws on Minor Consent for Housing and Related Services" (June 2026). That page is a secondary summary, so the statute should be checked. |
| **Example CoC E: HMIS release of information** | Clients 18 and over sign their own ROI. For each child under 18, a parent or legal guardian chooses the sharing option and signs a separate consent. | Jurisdiction: a CoC `withinJurisdiction` a state. `minimumSelfConsentAge 18`. Condition: `AgeOfMajority`. Scope: `ReleaseOfInformation`. Under 18, the directive needs a `ConsentProxyRole` grantor. | All Chicago HMIS, "Documenting Client Consent in HMIS (ROI)". |

Some sources describe court-appointed guardianship for homeless 16- and 17-year-olds
instead of self-consent. That pattern needs no `SelfConsentRule`. The guardian is a
`ConsentProxyRole` grantor, and the court order is the directive's `sourceDocument`.

These examples go in `examples/shapes/` with `ex:` IRIs, such as
`ex:ExampleStateA` and `ex:ExampleCoCE`, never real place names. Each example
resource carries the disclaimer as `rdfs:comment` and its source as `dcterms:source`.

## 7. Mapping: FHIR R5 Consent to UCM

| FHIR R5 | UCM |
|---|---|
| `Consent` | `ucm:ConsentDirective` |
| `identifier` | Adopter identifier (already open-world). Codegen keeps a stable id (requirement 22). |
| `status` | `ucm:hasConsentStatus` |
| `category` | `ucm:hasConsentCategory` |
| `subject` | `ucm:consentSubject`, a Participation with `ConsentSubjectRole` |
| `date` | `ucm:statementDate` on the directive, or `occursDuring` on the ConsentInteraction |
| `period` | `ucm:validDuring` (a `time:Interval`) |
| `grantor` | A Participation with `ConsentGrantorRole` or `ConsentProxyRole` in the ConsentInteraction |
| `grantee` | A Participation with `InformationRecipientRole` |
| `manager`, `controller` | A Participation with `InformationCustodianRole`. Narrower roles if the split matters (Q8). |
| `sourceAttachment`, `sourceReference`, `policyText` | `ucm:sourceDocument` |
| `regulatoryBasis` | `ucm:hasRegulatoryBasis` |
| `policyBasis` | `ucm:governedByPolicy`, pointing to a `ucm:ConsentPolicy` |
| `decision` | `ucm:hasConsentDecision` |
| `verification[]` | A ConsentInteraction with type `Verify` and a `ConsentVerifierRole` participation. `verifiedWith` is the subject or grantor participation. |
| `provision` | `ucm:hasProvision`, a `ucm:ConsentProvision` |
| `provision.period` | `ucm:validDuring` on the provision |
| `provision.actor{role, reference}` | `ucm:provisionActor`, a Participation (`assumesRole`, `participatingEntity`) |
| `provision.action` | `ucm:governsAction` |
| `provision.securityLabel` | `ucm:coversSensitivity` |
| `provision.purpose` | `ucm:forPurpose` |
| `provision.documentType`, `resourceType`, `code` | `ucm:coversDataCategory` |
| `provision.dataPeriod` | `ucm:dataPeriod` |
| `provision.data{meaning, reference}` | `ucm:coversInformation` with subproperties for instance, related, dependents and authoredby (Q6) |
| `provision.expression` | Not modeled. Keep as an adopter predicate, or `ucm:SemanticConstraint` (Q9). |
| `provision.provision` | Nested `ucm:hasProvision` |

R4 back-mapping: `patient` to subject, `performer` to grantee, `organization` to
custodian, `scope` to category, `provision.type` to the provision decision (R4 already had it on each provision),
`policyRule` to `regulatoryBasis`.

## 8. Mapping: HMIS (HUD and All Chicago) to UCM

| HMIS | UCM |
|---|---|
| ROI record | `ConsentDirective` with category `ReleaseOfInformation` |
| Client signature and date | A `ConsentInteraction` of type `Grant`, modality `WrittenConsent`, with `occursDuring` |
| Household members selected | Either one directive per member, as All Chicago does, or one directive whose subject is the `Household` (Q4) |
| Guardian signs for a child under 18 | A `ConsentProxyRole` participation, with authority derived from `Membership` and `HeadOfHouseholdRole` or `DependentRole` |
| Provider (the agency as a whole) | `provisionActor`, a Participation whose entity is the `Organization`, with `InformationRecipientRole` |
| Documentation: Full, Limited or No Sharing | Decision plus provisions (section 6), with `skos:closeMatch` in the mapping file |
| Release Granted Yes or No | Derived from the decision. Not stored separately. |
| Start Date and End Date (+3 years) | `ucm:validDuring` interval. Expiry gives status `ConsentExpired`. Re-confirmation gives a new directive that `ucm:supersedes` the old one. |
| Lock client record (DV or trafficking, HIV/AIDS, unaccompanied minor) | `hasSensitivityLabel` on the data (`SexualAssaultAbuseDomesticViolence`, `HumanTrafficking`, `HIV` or `UnaccompaniedYouth`), plus a deny provision on that sensitivity. Optionally `ucm:recordLocked`. |
| Witness | A `ConsentWitnessRole` participation |
| HUD consent form: inferred, verbal, written | `ucm:hasConsentModality` |
| HUD posted privacy notice | `ucm:PrivacyNotice` with `forPurpose`, `amendmentAppliesRetroactively`, and `locatedAt` an intake `Location` (Q10) |
| CoC consent policy | `ucm:ConsentPolicy` with `hasConsentModel` and `hasRegulatoryBasis HMISDataStandards2004` |

### 8.1 Mapping: NIEM 6.0 to UCM

Source: NIEM Model 6.0, OASIS Project Specification 02 (`niemopen/niem-model`, tag
`6.0-ps02`). The NIEM Core namespace is
`https://docs.oasis-open.org/niemopen/ns/model/niem-core/6.0/` (`nc:`). The Human
Services domain is `https://docs.oasis-open.org/niemopen/ns/model/domains/humanServices/6.0/`
(`hs:`). Every element below was checked in the 6.0-ps02 XML schemas.

**NIEM 6.0 has no consent, authorization-to-disclose or privacy-notice type**, and
no purpose-of-use, permit or deny, revocation or identity-assurance elements. UCM
therefore maps its consent records onto NIEM's general `Document` and `Activity`
types, its human-services privacy type, and its identity types. The rest is a gap
(Q18).

| UCM | NIEM 6.0 | Notes |
|---|---|---|
| `ucm:Entity` | `nc:EntityType` ("a person, organization, or item") | Same scope, and the natural carrier for the identity superset. |
| `ucm:Person` | `nc:PersonType` | |
| `ucm:birthDate` | `nc:PersonBirthDate` (`nc:DateType`) | `nc:DateType` allows `nc:Date`, `nc:YearMonthDate` and `nc:YearDate`, which line up with `xsd:date`, `xsd:gYearMonth` and `xsd:gYear`. `nc:DateAccuracyAbstract` is close to `ucm:birthDateQuality`. |
| `ucm:Organization`, `ucm:Location` | `nc:OrganizationType`, `nc:LocationType` | |
| `ucm:Identity` | `nc:IdentityType` (`nc:IdentityCharacteristics`, `nc:IdentityCreationDate`, `nc:IdentityTerminationDate`) | |
| `ucm:Identifier` | `nc:IdentificationType` | `nc:IdentificationID` to `identifierValue`. `nc:IdentificationCategoryText` to `hasIdentifierType`. `nc:IdentificationJurisdiction` to `inJurisdiction`. `nc:IdentificationIssuerOrganization` to `issuedBy`. `nc:IdentificationEffectiveDate` and `nc:IdentificationExpirationDate` to `validDuring`. `nc:IdentificationStatus`. |
| `ucm:JurisdictionContext` | `nc:JurisdictionType` | |
| `ucm:ConsentDirective`, `ucm:PrivacyNotice` | `nc:DocumentType` | `nc:DocumentEffectiveDate` and `nc:DocumentExpirationDate` to `validDuring`. `nc:DocumentSensitivityText` to `ConfidentialityLevel`. `nc:DocumentPrivacyActIndicator` and `nc:DocumentEUDataPrivacyIndicator` to `hasRegulatoryBasis` (Privacy Act, `GDPR`). |
| `ucm:ConsentInteraction` | `nc:ActivityType` | `nc:ActivityDate` to `occursDuring`. `nc:ActivityStatus`. `nc:ActivityVerifiedDate` to a `Verify` interaction. |
| `ucm:ConsentProvision` (sensitivity part) | `hs:DataPrivacyType` | `hs:DataPrivacyCategoryText` to `coversSensitivity`. `hs:DataPrivacyElementName` to `coversInformation`. `hs:DataPrivacyIndicator` (true) to a `Deny` decision. `hs:DataPrivacyPolicyReferenceText` to `governedByPolicy`. `hs:DataPrivacyRuleText` to the provision's description. |
| `ucm:ConfidentialityLevel` | `nc:SensitivityText` | NIEM uses free text. UCM concepts carry the codes. |
| `ConsentProxyRole` authority | `hs:GuardianWardAssociation`, `hs:ChildLegalCustodyPartyAssociation`, `hs:CustodialEntity` | The legal basis for a guardian or custodian to consent for a child. |
| `UnaccompaniedYouth` (partial) | `hs:JuvenileHomelessnessIndicator` | Covers homelessness only, not "unaccompanied". |

### 8.2 Mapping: Kantara Consent Receipt and ISO/IEC TS 27560:2023 to UCM

ISO/IEC TS 27560:2023 (consent record and receipt structure) grew out of the Kantara
Initiative's Consent Receipt Specification (v1.1). Field names below are as given in
Pandit et al. (arXiv 2405.04528), keyed to TS 27560 clauses. They should be checked
against the TS itself before publication.

| TS 27560 field | UCM |
|---|---|
| `privacy_notice` | `ucm:PrivacyNotice` via `acknowledgesNotice` |
| `purposes` | `forPurpose` |
| `lawful_basis` | `hasRegulatoryBasis` and `ConsentModel` |
| `pii_information`, `pii_type`, `pii_optional` | `coversDataCategory`, `coversSensitivity` |
| `pii_controllers` | a `DataControllerRole` participation |
| `recipient_third_parties` | an `InformationRecipientRole` participation |
| `jurisdiction` | `inJurisdiction` |
| `withdrawal_method` | `ucm:withdrawalMethod` |
| `retention_period` | `ucm:retentionPeriod`, with `ucm:hasRetentionDisposition` |
| `storage_locations`, `processing_locations`, `geographic_restrictions` | `ucm:processingLocation`, a `JurisdictionContext` |
| `party_name`, `party_role`, `party_type`, `entity_id` | A participation with `assumesRole`, and `identifiedAs` an identity |
| `event_type`, `event_time` | `ConsentInteractionType` and `occursDuring` |
| `validity_duration` | `validDuring` |

## 9. Shapes (`ucm-core-shapes.ttl`)

Following the existing tier convention.

Definitional (`sh:Violation`):

- `ConsentDirective-decision`: exactly one `hasConsentDecision`, an IRI.
- `ConsentDirective-status`: at most one `hasConsentStatus`, an IRI. Same for
  decision, category and modality: the `-single` pattern.
- `ConsentDirective-subject`: at least one `consentSubject`, a BlankNodeOrIRI.
- `ConsentProvision-decision`: exactly one `hasConsentDecision`, an IRI (Q3, decided).
- `ProvisionAlternationShape` (SPARQL): a provision's decision must be the opposite
  of its parent's. The parent is the directive for a top-level provision, or the
  enclosing provision for a nested one. This keeps every UCM directive equivalent
  to an FHIR R5 consent, where nested provisions are exceptions to their parent.
- Temporal: add `ucm:dataPeriod` to the targets of `TemporalEntityShape` and
  `TemporalOrderShape`.
- `ProvisionAcyclicShape`: provisions do not nest in a cycle, like `HandshakeAcyclicShape`.
- `SupersedesAcyclicShape`: a directive does not supersede itself, directly or
  indirectly.

Recommended (`sh:Warning`):

- `-anchored` SPARQL shapes for every new scheme: the value is in the scheme or
  SKOS-mapped to it.
- `ConsentDirective-validity`: has `validDuring`. Open-ended is allowed but flagged.
- `ConsentDirective-grantor`: the recording ConsentInteraction has a grantor
  participation.
- `ProxyGrantorShape`: if the grantor's entity is not the subject's entity, the
  grantor's role is `ConsentProxyRole`.
- `SelfConsentBasisShape`: if a minor or a subject with an `UnaccompaniedYouth` label
  is their own grantor, the directive is `governedByPolicy` a `SelfConsentRule`
  that is in force in the directive's jurisdiction, directly or through
  `withinJurisdiction`, and whose `minimumSelfConsentAge` the subject had reached.
  "Minor" means under the age of majority, computed from `ucm:birthDate` as of the
  interaction date (section 6.2). With no birth date, the shape falls back to the
  `UnaccompaniedYouth` label and `DependentRole` membership.
- `Person-birthDate` (Definitional): at most one `ucm:birthDate`, typed `xsd:date`,
  `xsd:gYearMonth` or `xsd:gYear` (`sh:or`).
- `RevokedHasRevocationShape`: status `ConsentRevoked` implies `revokedBy`, and
  `revokedBy` implies status inactive or revoked.
- `ActiveNotExpiredShape`: status `ConsentActive` while the `validDuring` end is in
  the past is flagged, using the same SPARQL-cast style as `TemporalOrderShape`.
- `AuthorizedByActiveConsentShape`: a Process that is `authorizedByConsent` a
  directive whose status is not active gets a warning.
- `sh:class` type checks that mirror ranges, as Recommended, per the existing convention.

Lint (`ucm-shapes-lint.ttl`): none needed. The new shapes carry `ucm:tier`.

## 10. Files that would change

| File | Change |
|---|---|
| `unified-care-model.ttl` | 7 consent classes and 9 identity classes, 14 roles, about 50 object properties, about 30 object properties and 4 data properties, including `ucm:birthDate` on the existing `ucm:Person` (sections 4 and 5). No change to existing terms (Q1 decided: no domain widening), except possibly `madeWithinContext` (see Q1 follow-on). |
| `ucm-lifecycle-vocabularies.ttl` | 21 SKOS concept schemes (sections 5.1, 6, 6.1 and 6.2). `rdfs:comment` widened from "care coordination lifecycle" to cover consent. |
| `ucm-core-shapes.ttl` | The shapes in section 9, and `dataPeriod` added to the temporal targets. |
| `examples/shapes/ucm-core-shapes-example.ttl` | The anonymized self-consent rules in section 6.3, plus worked examples: (a) the Thomson family, with Ruth as proxy for Jameson and Madison, and Sarah's Part 2 SUD data under a deny provision; (b) an All Chicago household ROI, Limited Sharing; (c) HUD verbal consent with a posted notice; (d) a revocation and a renewal chain. |
| `test-suites/test_core_shapes.py` | Conforming and non-conforming cases for each new shape. |
| `mapping/` (currently only a placeholder) | `mapping/consent-fhir-r5.md`, `mapping/consent-hmis.md`, `mapping/consent-niem.md` and `mapping/consent-iso27560.md`, holding the tables in sections 7, 8, 8.1 and 8.2, plus a `mapping/consent-mappings.ttl` with `skos:*Match` links to HL7 and HMIS codes. |
| `codegen/` and `examples/api`, `examples/db` | Regenerate after the ontology changes. Check the FHIR adapter profile for a `Consent` target. |
| `ns/ucm.ttl`, `ns/ucm.jsonld`, `ns/index.html` | Not touched. Eric hand-edits these. |
| `catalog-v001.xml` | No change (Q2 decided: no new module). |

## 11. Open questions for Eric and the CG

1. **Statement or InformationArtifact for ConsentDirective?** **Decided (Eric,
   2026-11-27): `ucm:InformationArtifact`, not `ucm:Statement`.** A consent is a
   record of choices, not a finding, and requirement 19 maps every Statement to an
   FHIR Observation. The directive therefore uses the new `recordsConsentFrom` and
   `consentSubject` properties, not `generatedByProcess` or `statementSubject`. The
   domains of the existing Statement properties stay as they are. The remaining
   follow-on, jurisdiction, is answered by the new `ucm:inJurisdiction` property
   and `ucm:JurisdictionContext` class (section 6.2). `madeWithinContext` is not
   widened.
2. **Where do the terms live?** **Decided (Eric, 2026-11-27): in the existing
   core files.** Classes and properties go in `unified-care-model.ttl`, SKOS schemes
   in `ucm-lifecycle-vocabularies.ttl`, and shapes in `ucm-core-shapes.ttl`. There
   is no separate `#consent` module, and no `catalog-v001.xml` change.
3. **Explicit decision on every provision, or FHIR R5 exception semantics?**
   **Decided (Eric, 2026-11-27): the middle path.** Every `ucm:ConsentProvision`
   carries an explicit `hasConsentDecision` (Definitional, exactly one). A
   Definitional SPARQL shape requires each provision's decision to be the opposite
   of its parent's, whether the parent is the directive or an enclosing provision.
   Each provision means the same thing on its own, so it can be queried directly
   and reused. Conversion is still one-to-one:
   - **To R5:** drop the provision decisions and keep the directive's `decision`.
     Nesting already carries the flip.
   - **From R5:** each provision's decision is the opposite of its parent's.
   - **To and from R4:** the decision maps directly to `provision.type`.
The defaults for Q4 to Q12 were **accepted by Eric on 2026-11-27**:

4. **Household or family consent.** **Decided:** support both. The default is one
   directive per member, as All Chicago does. A `Household` subject is also
   allowed, with a shape that requires a member-level `ConsentProxyRole` for each
   minor.
5. **InformationCategory.** **Decided:** SKOS concepts, each with `rdfs:seeAlso` to
   its matching `*Domain` class.
6. **FHIR `data.meaning`.** **Decided:** four subproperties of `coversInformation`:
   `coversInstance`, `coversRelated`, `coversDependents` and `coversAuthoredBy`.
7. **Record lock.** **Decided:** sensitivity labels plus deny provisions, with
   `ucm:recordLocked` kept as an optional convenience flag.
8. **Manager versus controller.** **Decided:** keep `InformationCustodianRole`, and
   add `ConsentManagerRole` and `DataControllerRole` under it.
9. **Computable policy.** **Decided:** deferred. FHIR `expression` stays an adopter
   predicate for now.
10. **Posted notices.** **Decided:** a new property `ucm:postedAt`, from
    `PrivacyNotice` to `Location`. `locatedAt` is not widened.
11. **Lifecycle naming.** **Decided:** keep the `Consent` prefix.
12. **Code lists.** **Decided:** every `skos:*Match` link to HL7, SHIFT, HMIS or NIEM
    goes in `mapping/consent-mappings.ttl`. The core stays free of external IRIs.
13. **UCM-local gaps.** **Decided (Eric, 2026-11-27): UCM defines them** (section
    6.1). Proposing them to HL7, for example through the Cross-Paradigm Sensitive Data
    work that SHIFT points to, is a later option. It does not block anything.
14. **VAWA.** **Decided (Eric, 2026-11-27): added** to `RegulatoryBasis` (section 6.1).
15. **Self-consent by youth.** **Decided (Eric, 2026-11-27): model region-dependent
    youth consent** with `SelfConsentRule` and `JurisdictionContext` (section 6.2).
16. **Age.** **Decided (Eric, 2026-11-27): add `ucm:birthDate` to `ucm:Person`**
    (section 6.2). A subject's age is computed from it as of the ConsentInteraction's
    date. It is the first new property on an existing core class in this plan.
17. **Seed rules.** **Decided (Eric, 2026-11-27): include real rules, anonymized**,
    with a disclaimer and source references (section 6.3). States and CoCs are not
    named. Federal law (FERPA) is named, because it is not a state or CoC rule.

18. **NIEM gap.** NIEM 6.0 has no consent type. Should UCM publish a NIEM-conformant
    extension namespace, with a consent type, permit or deny, purpose and revocation,
    and propose it to the NIEM Human Services domain? Or should it only map to the
    general types, as section 8.1 does now? **Decided (Eric, 2026-11-27): only map to
    NIEM's general types.**
19. **ISO/IEC TS 27560 extras.** Should withdrawal method, retention period and
    processing location become UCM properties now, or wait? **Decided (Eric,
    2026-11-27): add all three now** (`withdrawalMethod`, `retentionPeriod` with
    `hasRetentionDisposition`, and `processingLocation`; section 5).
20. **"Identity superset" reading.** The plan reads "identity superset of entities" as
    an identity layer that applies to every kind of `ucm:Entity`. The alternative is a
    new superclass *above* `ucm:Entity`. Section 5.1 explains the choice. **Decided
    (Eric, 2026-11-27): an identity layer over every `ucm:Entity`.**

## 12. Suggested sequence once approved

1. Q1 to Q20 are all decided.
2. Add the identity layer first (section 5.1), because consent refers to it: its SKOS
   schemes, classes, properties and shapes. Then add the consent SKOS schemes, classes,
   properties and shapes.
3. Add the examples and the tests together, and run `test_core_shapes.py`.
4. Write the mapping files.
5. Regenerate the codegen outputs and review the FHIR adapter.
6. Bring it to the CG (public-ucm) with the Thomson family example as the walkthrough.

## 13. Implementation notes (2026-11-27)

The plan was implemented in the `consent-plan` worktree. Where the
implementation differs from the sections above, the implementation wins:

- **Names that would have clashed or been too generic** got a suffix or prefix:
  `ConsentGrant`, `ConsentRefusal`, `ConsentAmendment`, `ConsentRenewal`,
  `ConsentRevocation` and `ConsentVerification` (interaction types);
  `CollectAction`, `AccessAction`, `UseAction`, `DiscloseAction`,
  `RediscloseAction` and `CorrectAction`; `EligibilityPurpose` (the class
  `ucm:EligibilityDetermination` already exists), `ResearchPurpose`,
  `PublicHealthPurpose` and `HealthcareOperations`; `ConfidentialityUnrestricted`
  through `ConfidentialityVeryRestricted`; `FairEvidence`, `StrongEvidence` and
  `SuperiorEvidence`; `*Proofing` for proofing types and `*Evidence` for evidence
  types; and `UnaccompaniedYouthStatus` for the self-consent condition, so it is
  not the same IRI as the `UnaccompaniedYouth` sensitivity.
- **Confidentiality is split from sensitivity.** `coversSensitivity` and
  `hasSensitivityLabel` take `SensitivityCategory` concepts. New
  `coversConfidentiality` and `hasConfidentialityLevel` take `ConfidentialityLevel`
  concepts. One property per scheme keeps the generated API typed.
- **`withdrawalMethod` is `xsd:string`.** A link is written as text.
- **`assuranceRank` is a datatype property** (on `skos:Concept`, `xsd:integer`),
  declared in the core file, so the shapes that compare levels reference a
  declared term.
- **Properties with several domains** use an `owl:unionOf` domain.
- **`SelfConsentBasisShape`** treats a subject as a minor below 18, computed from
  `birthDate` as of the consent interaction's date, reading a partial date as its
  latest possible day. With no birth date it does not fire. The fallback on the
  `UnaccompaniedYouth` label and `DependentRole` was left out: the label sits on
  data, not on the person, and `DependentRole` is only in the participation
  module's old namespace.
- **Not implemented yet:** the shape requiring a member-level proxy for each
  minor when a `Household` is the subject (Q4), and a FHIR `Consent` resource in
  the codegen FHIR adapter.
- **Codegen fixes the new terms needed:** the JSON-LD context no longer coerces
  `xsd:string` terms, and coerces a datatype-union term to the shapes' first
  datatype; examples write coerced booleans and numbers as JSON values and sort
  multi-valued properties for reproducible output; the database dump returns a
  single value for a single-valued property stored in an association table; a
  scheme binding is skipped when no vocabulary is compiled at all. Codegen tests
  with fixed counts were updated.

## Sources

- Stewards of Change Institute, *Consent Learning Lab Report* (HIMSS 2023), August 2023 (attached PDF).
- HL7 FHIR R5 Consent: https://hl7.org/fhir/consent.html
- SHIFT Collaborative: https://github.com/SHIFT-Task-Force (org page, the sls-ri, sls-ri-ig and SLS-ValueSets READMEs, and the SLS-ValueSets sources `input/fsh/valuesets/SensitiveKindCodes.fsh` and `input/pagecontent/{index,minShift,LeapSls}.md`). Website: https://www.shiftinterop.org/
- HUD Exchange FAQ 3310: https://www.hudexchange.info/faqs/3310/what-are-acceptable-forms-of-client-consent-and-privacy-notices-can-notice/
- All Chicago HMIS, *Documenting Client Consent in HMIS (ROI)*: https://hmis.allchicago.org/hc/en-us/articles/54375813606420-Documenting-Client-Consent-in-HMIS-ROI

Sources for the identity layer and the NIEM mapping (section 5.1, 8.1, 8.2):
- NIEM Model 6.0 PS02: https://github.com/niemopen/niem-model/tree/6.0-ps02 (`xsd/niem-core.xsd`, `xsd/domains/hs.xsd`)
- NIST SP 800-63-4 Digital Identity Guidelines: https://pages.nist.gov/800-63-4/ (SP 800-63, 800-63A)
- OpenID Connect Core 1.0 (errata 2): https://openid.net/specs/openid-connect-core-1_0.html
- OpenID Connect for Identity Assurance 1.0 (final): https://openid.net/specs/openid-connect-4-identity-assurance-1_0.html and OpenID IDA Verified Claims 1.0 (final, 2024-10-01): https://openid.net/specs/openid-ida-verified-claims-1_0-final.html
- W3C Verifiable Credentials Data Model 2.0 (W3C Recommendation, 2025-05-15): https://www.w3.org/TR/vc-data-model-2.0/ (vocabulary `https://www.w3.org/2018/credentials#`)
- The Sequoia Project (TEFCA RCE), Exchange Purpose Implementation SOP: Individual Access Services v3.0: https://rce.sequoiaproject.org/wp-content/uploads/2026/07/SOP-IAS-XP-v3_June2026_Clean_508.pdf. It requires CSP proofing to at least NIST IAL2 and IAS Provider authentication at AAL2, carries the IAL2 claims in an OpenID Connect ID token, and does not mention Kantara or verifiable credentials.
- Kantara Initiative: https://en.wikipedia.org/wiki/Kantara_Initiative. Its assurance program assesses CSPs against NIST SP 800-63 (IAL2/AAL2 approvals continue in 2026). The program's current name and listing should be checked on Kantara's own site.
- ISO/IEC TS 27560:2023, via Pandit et al.: https://arxiv.org/html/2405.04528v1

Sources for the section 6.3 examples:
- U.S. Department of Education, Student Privacy Policy Office: https://studentprivacy.ed.gov/content/eligible-student and https://studentprivacy.ed.gov/faq/who-eligible-student
- Guttmacher Institute, Minors' Access to STI Services (as of 2026-08-01): https://www.guttmacher.org/state-policy/explore/minors-access-sti-services
- SchoolHouse Connection, State Laws on Minor Consent for Housing and Related Services (June 2026): https://schoolhouseconnection.org/article/state-laws-on-minor-consent-for-housing-and-related-services

## Appendix A. Verified code values (2026-11-27)

Checked against HL7's published sources: the `HL7/UTG` repository (`input/sourceOfTruth/`, the source for terminology.hl7.org) and the `HL7/fhir` repository (`source/consent/`, current build). All codes listed are present and **active**, except where noted. Codes are case-sensitive.

**`http://terminology.hl7.org/CodeSystem/v3-ActCode`: sensitivity codes**

| Code | Display | UCM concept |
|---|---|---|
| SUD | substance use disorder information sensitivity | `SubstanceUseDisorder` |
| ETH | substance abuse information sensitivity | `SubstanceUseDisorder` (closeMatch, older term) |
| ETHUD | alcohol use disorder information sensitivity | `AlcoholUseDisorder` |
| OPIOIDUD | opioid use disorder information sensitivity | `OpioidUseDisorder` |
| BH | behavioral health information sensitivity | `BehavioralHealth` |
| MH | mental health information sensitivity | `MentalHealth` |
| PSY | psychiatry disorder information sensitivity | `PsychiatricDisorder` |
| PSYTHPN | psychotherapy note information sensitivity | `PsychotherapyNote` |
| HIV | HIV/AIDS information sensitivity | `HIV` |
| STD | sexually transmitted disease information sensitivity | `SexuallyTransmittedDisease` |
| SEX | sexuality and reproductive health information sensitivity | `SexualAndReproductiveHealth` |
| GENDER | gender and sexual orientation information sensitivity | `GenderAndSexualOrientation` |
| GDIS | genetic disease information sensitivity | `GeneticDisease` |
| SDV | sexual assault, abuse, or domestic violence information sensitivity | `SexualAssaultAbuseDomesticViolence` |
| ADOL | adolescent information sensitivity | `Adolescent` |
| 42CFRPart2 | 42 CFR Part2 | `Part2Protected`, and closeMatch `RegulatoryBasis/CFR42Part2` |
| 42CFRPart2CD | 42 CFR Part 2 consent directive | closeMatch on a Part 2 `ConsentCategory` |
| IDS, DEMO | Identifier Sensitivity; all demographic information sensitivity | `IdentifyingInformation` (closeMatch) |

Not found: `REPHC` (no separate reproductive health code; use SEX). `SICKLE` exists but is **retired**.

**`http://terminology.hl7.org/CodeSystem/v3-Confidentiality`**: U unrestricted, L low, M moderate, N normal, R restricted, V very restricted.

**`http://terminology.hl7.org/CodeSystem/v3-ActReason`: the PurposeOfUse value set draws from this system.** TREAT treatment, ETREAT Emergency Treatment, COC coordination of care, CAREMGT care management, HPAYMT healthcare payment, HOPERAT healthcare operations, ELIGDTRM eligibility determination, ELIGVER eligibility verification, COVERAGE coverage under policy or program, HRESCH healthcare research, CLINTRCH clinical trial research, PUBHLTH public health, POPHLTH population health, HQUALIMP health quality improvement, HSYSADMIN health system administration, PATADMIN patient administration, PATRQT patient requested, FAMRQT family requested, PWATRNY power of attorney, SUPNWK support network, HLEGAL legal, HMARKT healthcare marketing, HDIRECT directory. No housing, homelessness or social-services purpose code exists.

**`http://terminology.hl7.org/CodeSystem/consentaction`**: collect, access, use, disclose, correct ("Access and Correct").

**`http://terminology.hl7.org/CodeSystem/consentcategorycodes`**: acd, dnr, emrgonly, hcd, npp, polst, research, rsdid, rsreid.

**`http://terminology.hl7.org/CodeSystem/consentpolicycodes`** (27 codes; US-relevant shown): hipaa-auth, hipaa-npp, hipaa-restrictions, hipaa-research, hipaa-self-pay, cric (Common Rule), illinois-minor-procedure, mdhhs-5515 (Michigan behavioral health for care coordination), dch-3927, ssa-827, va-10-0484, va-10-0485, va-10-5345, va-10-5345a, va-10-5345a-mhv, va-10-10116, va-21-4142, nih-hipaa, nih-527, nih-grdr, nci, squaxin. There is **no 42 CFR Part 2, HMIS, FERPA or GDPR code**.

**`http://hl7.org/fhir/consent-state-codes`**: draft ("Pending"), active, inactive, not-done ("Abandoned"), entered-in-error, unknown.

**`http://hl7.org/fhir/consent-data-meaning`**: instance, related, dependents, authoredby.

**SHIFT SLS minimal value sets** (SLS-ValueSets, `minShift.md`), mapping each value set to the labels it applies: Behavioral Health to BH; Psychiatric Notes to PSYTHPN and BH; Sexuality and Reproductive Health to SEX; Abortion to `ExtraSensitiveCodes#ABORTION` (a SHIFT-local placeholder, marked TODO in the source); STD to STD; HIV to HIV; Genetic Disease to GDIS; Sexual Assault / Domestic Violence to SDV; Opioid to OPIOIDUD, SUD and 42CFRPart2; Hallucinogen to SUD, 42CFRPart2 and BH. SHIFT also publishes SAMHSA-derived value sets for ETH, ETHUD, OPIOIDUD, PSY, SDV and HIV. SHIFT says these are examples only. All codes except the abortion placeholder are `v3-ActCode` codes verified above.
