<!-- Non-normative. Generated from doc/design/consent-concepts-plan.md (section 8.1) and kept in step with the terms in unified-care-model.ttl and ucm-lifecycle-vocabularies.ttl. SKOS code links are in consent-mappings.ttl. -->

# Mapping: NIEM 6.0 to UCM

Source: NIEM Model 6.0, OASIS Project Specification 02 (`niemopen/niem-model`, tag
`6.0-ps02`). The NIEM Core namespace is
`https://docs.oasis-open.org/niemopen/ns/model/niem-core/6.0/` (`nc:`). The Human
Services domain is `https://docs.oasis-open.org/niemopen/ns/model/domains/humanServices/6.0/`
(`hs:`). Every element below was checked in the 6.0-ps02 XML schemas.

**NIEM 6.0 has no consent, authorization-to-disclose or privacy-notice type**, and
no purpose-of-use, permit or deny, revocation or identity-assurance elements. UCM
therefore maps its consent records onto NIEM's general `Document` and `Activity`
types, its human-services privacy type, and its identity types. The rest is a gap
(Q18, decided: map only).

| UCM | NIEM 6.0 | Notes |
|---|---|---|
| `ucm:Entity` | `nc:EntityType` ("a person, organization, or item") | Same scope, and the natural carrier for the identity superset. |
| `ucm:Person` | `nc:PersonType` | |
| `ucm:birthDate` | `nc:PersonBirthDate` (`nc:DateType`) | `nc:DateType` allows `nc:Date`, `nc:YearMonthDate` and `nc:YearDate`, which line up with `xsd:date`, `xsd:gYearMonth` and `xsd:gYear`. `nc:DateAccuracyAbstract` is close to `ucm:birthDateQuality`. |
| `ucm:Organization`, `ucm:Location` | `nc:OrganizationType`, `nc:LocationType` | |
| `ucm:Identity` | `nc:IdentityType` (`nc:IdentityCharacteristics`, `nc:IdentityCreationDate`, `nc:IdentityTerminationDate`) | |
| `ucm:Identifier` | `nc:IdentificationType` | `nc:IdentificationID` to `identifierValue`. `nc:IdentificationCategoryText` to `hasIdentifierType`. `nc:IdentificationJurisdiction` to `inJurisdiction`. `nc:IdentificationIssuerOrganization` to `issuedBy`. `nc:IdentificationEffectiveDate` and `nc:IdentificationExpirationDate` to `validDuring`. `nc:IdentificationStatus`. |
| `ucm:JurisdictionContext` | `nc:JurisdictionType` | |
| `ucm:ConsentDirective`, `ucm:PrivacyNotice` | `nc:DocumentType` | `nc:DocumentEffectiveDate` and `nc:DocumentExpirationDate` to `validDuring`. `nc:DocumentSensitivityText` to `hasConfidentialityLevel`. `nc:DocumentPrivacyActIndicator` and `nc:DocumentEUDataPrivacyIndicator` to `hasRegulatoryBasis` (Privacy Act, `GDPR`). |
| `ucm:ConsentInteraction` | `nc:ActivityType` | `nc:ActivityDate` to `occursDuring`. `nc:ActivityStatus`. `nc:ActivityVerifiedDate` to a `ConsentVerification` interaction. |
| `ucm:ConsentProvision` (sensitivity part) | `hs:DataPrivacyType` | `hs:DataPrivacyCategoryText` to `coversSensitivity`. `hs:DataPrivacyElementName` to `coversInformation`. `hs:DataPrivacyIndicator` (true) to a `Deny` decision. `hs:DataPrivacyPolicyReferenceText` to `governedByPolicy`. `hs:DataPrivacyRuleText` to the provision's description. |
| `ucm:hasConfidentialityLevel` | `nc:SensitivityText` | NIEM uses free text. UCM concepts carry the codes. |
| `ConsentProxyRole` authority | `hs:GuardianWardAssociation`, `hs:ChildLegalCustodyPartyAssociation`, `hs:CustodialEntity` | The legal basis for a guardian or custodian to consent for a child. |
| `UnaccompaniedYouth` (partial) | `hs:JuvenileHomelessnessIndicator` | Covers homelessness only, not "unaccompanied". |
