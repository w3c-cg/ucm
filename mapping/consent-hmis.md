<!-- Non-normative. Generated from doc/design/consent-concepts-plan.md (section 8) and kept in step with the terms in unified-care-model.ttl and ucm-lifecycle-vocabularies.ttl. SKOS code links are in consent-mappings.ttl. -->

# Mapping: HMIS (HUD and All Chicago) to UCM

| HMIS | UCM |
|---|---|
| ROI record | `ConsentDirective` with category `ReleaseOfInformation` |
| Client signature and date | A `ConsentInteraction` of type `ConsentGrant`, modality `WrittenConsent`, with `occursDuring` |
| Household members selected | Either one directive per member, as All Chicago does, or one directive whose subject is the `Household` (Q4) |
| Guardian signs for a child under 18 | A `ConsentProxyRole` participation, with authority derived from `Membership` and `HeadOfHouseholdRole` or `DependentRole` |
| Provider (the agency as a whole) | `provisionActor`, a Participation whose entity is the `Organization`, with `InformationRecipientRole` |
| Documentation: Full, Limited or No Sharing | Decision plus provisions; see Sharing levels below |
| Release Granted Yes or No | Derived from the decision. Not stored separately. |
| Start Date and End Date (+3 years) | `ucm:validDuring` interval. Expiry gives status `ConsentExpired`. Re-confirmation gives a new directive that `ucm:supersedes` the old one. |
| Lock client record (DV or trafficking, HIV/AIDS, unaccompanied minor) | `hasSensitivityLabel` on the data (`SexualAssaultAbuseDomesticViolence`, `HumanTrafficking`, `HIV` or `UnaccompaniedYouth`), plus a deny provision on that sensitivity. Optionally `ucm:recordLocked`. |
| Witness | A `ConsentWitnessRole` participation |
| HUD consent form: inferred, verbal, written | `ucm:hasConsentModality` |
| HUD posted privacy notice | `ucm:PrivacyNotice` with `forPurpose`, `amendmentAppliesRetroactively`, and `postedAt` an intake `Location` |
| CoC consent policy | `ucm:ConsentPolicy` with `hasConsentModel` and `hasRegulatoryBasis HMISDataStandards` |

## Sharing levels

HMIS sharing levels are compositions, not core concepts:

- **Full Sharing** is `hasConsentDecision ucm:Permit` with no deny provisions.
- **No Sharing** is `hasConsentDecision ucm:Deny`.
- **Limited Sharing** is `hasConsentDecision ucm:Permit` with one or more `ucm:Deny`
  provisions, for example on a `SensitivityCategory` or on particular recipients.
  `ex:cd-sarah` in `examples/shapes/ucm-core-shapes-example.ttl` is a worked example.
