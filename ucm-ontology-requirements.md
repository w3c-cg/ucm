# UCM Ontology Requirements

## Core Principles

1.  Separate ontological reality from epistemic representations.
2.  Distinguish clearly between Process, InformationObject, and Focus.
3.  Support roundtrip interoperability with FHIR without semantic loss.
4.  Maintain alignment with upper ontology (SULO/BFO).

## Observation Model

5.  ObservationProcess must be modeled as a Process.
6.  ObservationResult must be an InformationObject.
7.  ObservationResult may be a Collection of Statements.
8.  A Statement must represent a subject--property--value assertion.
9.  Statements must support provenance (who, when, how).

## Focus and Subject

10. CareFocus represents what is being acted upon or observed.
11. Processes use hasFocus to link to CareFocus.
12. InformationObjects use isAbout to reference entities.

## Data Semantics

13. Distinguish Quality (categorical) vs Quantity (measurable).
14. CodeableConcept maps to Quality representations.
15. Quantity maps to measurable values with units.

## Collections and Reports

16. Collections group items without adding meaning.
17. Reports organize and interpret collections.
18. ObservationResults may be collections; Reports aggregate results.

## Interoperability

19. Each Statement must map to a FHIR Observation.
20. Collections map to DiagnosticReport.
21. Processes map to Provenance (or equivalent).
22. Maintain stable identifiers for roundtrip transformations.

## Structural Integrity

23. Avoid conflating process, result, and focus.
24. Ensure all information objects are explicitly about something.
25. Ensure all processes have clear inputs, outputs, and focus.

## Extensibility

26. Model must support clinical, social, and administrative domains.
27. Support integration with digital twin concepts.
28. Support longitudinal aggregation without altering base pattern.

## Design Philosophy

29. Prefer explicit modeling over implicit assumptions.
30. Ensure semantic clarity over implementation convenience.

