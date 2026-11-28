<!-- Non-normative. Generated from doc/design/consent-concepts-plan.md (section 7) and kept in step with the terms in unified-care-model.ttl and ucm-lifecycle-vocabularies.ttl. SKOS code links are in consent-mappings.ttl. -->

# Mapping: FHIR R5 Consent to UCM

| FHIR R5 | UCM |
|---|---|
| `Consent` | `ucm:ConsentDirective` |
| `identifier` | Adopter identifier (already open-world). Codegen keeps a stable id (requirement 22). |
| `status` | `dpv:hasConsentStatus` |
| `category` | `ucm:hasConsentCategory` |
| `subject` | `ucm:consentSubject`, a Participation with `ConsentSubjectRole` |
| `date` | `ucm:statementDate` on the directive, or `occursDuring` on the ConsentInteraction |
| `period` | `ucm:validDuring` (a `time:Interval`) |
| `grantor` | A Participation with `ConsentGrantorRole` or `ConsentProxyRole` in the ConsentInteraction |
| `grantee` | A Participation with `InformationRecipientRole` |
| `manager`, `controller` | A Participation with `InformationCustodianRole`. Narrower roles if the split matters (Q8). |
| `sourceAttachment`, `sourceReference`, `policyText` | `ucm:sourceDocument` |
| `regulatoryBasis` | `dpv:hasApplicableLaw` |
| `policyBasis` | `ucm:governedByPolicy`, pointing to a `ucm:ConsentPolicy` |
| `decision` | `ucm:hasConsentDecision` |
| `verification[]` | A ConsentInteraction with type `ConsentVerification` and a `ConsentVerifierRole` participation. `verifiedWith` is the subject or grantor participation. |
| `provision` | `ucm:hasProvision`, a `ucm:ConsentProvision` |
| `provision.period` | `ucm:validDuring` on the provision |
| `provision.actor{role, reference}` | `ucm:provisionActor`, a Participation (`assumesRole`, `participatingEntity`) |
| `provision.action` | `ucm:governsAction` |
| `provision.securityLabel` | `ucm:coversSensitivity` (sensitivity codes) or `ucm:coversConfidentiality` (confidentiality codes) |
| `provision.purpose` | `dpv:hasPurpose` |
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

## Generated adapter (FHIR R4)

The codegen FHIR adapter targets R4 (4.0.1). `codegen/profiles/ucm-fhir-mapping.yaml`
maps `ConsentDirective` to R4 `Consent`, and the generated
`examples/api/fhir/ucm_fhir_adapter.py` converts both ways:

| R4 `Consent` | UCM | Read back |
|---|---|---|
| `status` | `dpv:hasConsentStatus` (`inactive` carries the exact concept in `_status`) | yes |
| `scope` | from `hasConsentCategory` (consentscope codes) | no, `category` carries it |
| `category` | `hasConsentCategory` | yes |
| `patient` | `consentSubject` / `participatingEntity`, a Patient only | yes |
| `dateTime` | the consent interaction's `occursDuring` instant | no |
| `performer` | grantor or proxy participations in the consent interaction | no |
| `organization` | custodian participations in the consent interaction | no |
| `sourceReference` | `sourceDocument` | yes |
| `policy.uri` | `governedByPolicy` | yes |
| `policyRule` | `dpv:hasApplicableLaw` (first value; more are warned) | yes |
| `provision` (root) | the directive: `hasConsentDecision`, `validDuring` | type yes, period no |
| `provision.provision` | `hasProvision`, two levels deep | yes |
| `.type`, `.action`, `.purpose`, `.code` | `hasConsentDecision`, `governsAction`, `dpv:hasPurpose`, `coversDataCategory` | yes |
| `.securityLabel` | `coversSensitivity` and `coversConfidentiality` | yes, each to its own property |
| `.actor{role, reference}` | `provisionActor` participation | yes |
| `.data{meaning, reference}` | `coversInstance`, `coversRelated`, `coversDependents`, `coversAuthoredBy` | yes |

Not mapped on the Consent: `verification` (R4 cannot name the verifier). A
household-wide directive has no R4 `patient` (R5 `subject` allows a Group); the
adapter warns. The consent interaction goes in its own `Provenance`, below.

### The consent interaction as an R4 Provenance

Each `ConsentInteraction` becomes one `Provenance` resource that targets the
directive it recorded or revoked.

| R4 `Provenance` | UCM | Read back |
|---|---|---|
| `target` | the directive: `recordsConsentFrom` (inverse) and `revokedBy` (inverse, marked) | yes, each to its own property |
| `recorded` | `occursDuring` instant | yes |
| `activity` | `hasConsentInteractionType` (grant, refuse, amend, renew, revoke, verify) | yes |
| `agent.who` | a grantor, proxy, witness, verifier or custodian participation's entity | yes |
| `agent.role` | the participation's role | yes |
| `agent.onBehalfOf` | `consentOnBehalfOf` (first value; R4 holds one) | yes |
| `entity` (`role: source`, `what`) | `acknowledgesNotice` | yes |

The consent subject and the recipient are not agents of the act, so they are left
out. Not mapped, because R4 `Provenance` has no element for them: the modality,
`authenticatedBy` and the jurisdiction. `target`, `recorded` and `agent` are 1..* in
R4, so the adapter warns when UCM has no value for one (for example an interaction
with no time instant, or a revocation with no participant). R4 `Provenance` also has
no `identifier`, so the adapter carries the UCM IRI in the node-iri extension on the
resource instead.

Concept codings use the concept's own namespace as the coding system: UCM concepts
are coded in `https://www.w3.org/ns/ucm#`, and concepts UCM reuses from DPV in DPV's
namespace, for example `{"system": "https://w3id.org/dpv#", "code": "Disclose"}`.
