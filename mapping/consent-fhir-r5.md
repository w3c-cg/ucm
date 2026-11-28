<!-- Non-normative. Generated from doc/design/consent-concepts-plan.md (section 7) and kept in step with the terms in unified-care-model.ttl and ucm-lifecycle-vocabularies.ttl. SKOS code links are in consent-mappings.ttl. -->

# Mapping: FHIR R5 Consent to UCM

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
| `verification[]` | A ConsentInteraction with type `ConsentVerification` and a `ConsentVerifierRole` participation. `verifiedWith` is the subject or grantor participation. |
| `provision` | `ucm:hasProvision`, a `ucm:ConsentProvision` |
| `provision.period` | `ucm:validDuring` on the provision |
| `provision.actor{role, reference}` | `ucm:provisionActor`, a Participation (`assumesRole`, `participatingEntity`) |
| `provision.action` | `ucm:governsAction` |
| `provision.securityLabel` | `ucm:coversSensitivity` (sensitivity codes) or `ucm:coversConfidentiality` (confidentiality codes) |
| `provision.purpose` | `ucm:forPurpose` |
| `provision.documentType`, `resourceType`, `code` | `ucm:coversDataCategory` |
| `provision.dataPeriod` | `ucm:dataPeriod` |
| `provision.data{meaning, reference}` | `ucm:coversInformation` with subproperties for instance, related, dependents and authoredby (Q6) |
| `provision.expression` | Not modeled. Keep as an adopter predicate, or `ucm:SemanticConstraint` (Q9). |
| `provision.provision` | Nested `ucm:hasProvision` |

R4 back-mapping: `patient` to subject, `performer` to grantee, `organization` to
custodian, `scope` to category, `provision.type` to the provision decision (R4 already had it on each provision),
`policyRule` to `regulatoryBasis`.

## Conversion of provision decisions

Every UCM provision states its own decision, and `ProvisionAlternationShape`
requires it to be the opposite of its parent's.

- **To R5:** drop the provision decisions and keep the directive's `decision`. Nesting already carries the flip.
- **From R5:** each provision's decision is the opposite of its parent's.
- **To and from R4:** the decision maps directly to `provision.type`.

The codegen FHIR adapter (`codegen/profiles/ucm-fhir-mapping.yaml`) does not map
`ConsentDirective` to `Consent` yet.
