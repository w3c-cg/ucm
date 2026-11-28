<!-- Non-normative. Generated from doc/design/consent-concepts-plan.md (section 8.2) and kept in step with the terms in unified-care-model.ttl and ucm-lifecycle-vocabularies.ttl. SKOS code links are in consent-mappings.ttl. -->

# Mapping: Kantara Consent Receipt and ISO/IEC TS 27560:2023 to UCM

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
