<!-- Non-normative. Generated from doc/design/consent-concepts-plan.md (section 8.2) and kept in step with the terms in unified-care-model.ttl and ucm-lifecycle-vocabularies.ttl. SKOS code links are in consent-mappings.ttl. -->

# Mapping: Kantara Consent Receipt and ISO/IEC TS 27560:2023 to UCM

ISO/IEC TS 27560:2023 (consent record and receipt structure) grew out of the Kantara
Initiative's Consent Receipt Specification (v1.1). Field names were checked on
2026-11-27 against the ISO sample of the TS (clause 6.3.4, Table 2, "PII processing
section contents"), which confirms `storage_locations` ("the geo-locations of where the
data will be physically stored") and `retention_period` ("the retention period and/or
disposal schedule"), both Required. The fields after Table 2 in the TS (`withdrawal_method`,
`processing_locations`, `jurisdiction`, `geographic_restrictions`) are not in the free
sample; their names come from Pandit, Lindquist and Krog (arXiv 2405.04528, Table 2,
withdrawal_method at 6.3.4.18) and the W3C DPV guide "Consent Records and Receipts as
per ISO/IEC TS 27560:2023 using DPV". TS 27560 has no separate field for what happens
when retention ends: the disposal schedule sits inside `retention_period`. UCM splits
it into `retentionPeriod` (the duration) and `hasRetentionDisposition` (delete,
de-identify or archive), which lines up with DPV `StorageDuration` and `StorageDeletion`.

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
| `retention_period` (Required; period and/or disposal schedule) | `ucm:retentionPeriod` for the period, `ucm:hasRetentionDisposition` for the disposal (DPV `StorageDuration`, `StorageDeletion`) |
| `storage_locations` (Required), `processing_locations`, `geographic_restrictions` | `ucm:processingLocation`, a `JurisdictionContext` (DPV `StorageLocation`, `hasLocation`, `hasJurisdiction`) |
| `party_name`, `party_role`, `party_type`, `entity_id` | A participation with `assumesRole`, and `identifiedAs` an identity |
| `event_type`, `event_time` | `ConsentInteractionType` and `occursDuring` |
| `validity_duration` | `validDuring` |
