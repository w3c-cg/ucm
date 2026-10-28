"""
FHIR target: mapping overlay + IR → UCM ⇄ FHIR R4 adapter

The overlay (profiles/ucm-fhir-mapping.yaml) is parsed into Pydantic models
and checked against the IR: classes, properties, roles and concept terms
must exist, and each path must be applicable to the class it starts from.
The compiled mapping resolves terms to IRIs, so the generated adapter needs
nothing but the standard library.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from .builder import SpecBuilder
from .models import OntologyIR

# FHIR R4 (4.0.1) resource types
R4_RESOURCES = set("""
Account ActivityDefinition AdverseEvent AllergyIntolerance Appointment AppointmentResponse
AuditEvent Basic Binary BiologicallyDerivedProduct BodyStructure Bundle CapabilityStatement
CarePlan CareTeam CatalogEntry ChargeItem ChargeItemDefinition Claim ClaimResponse
ClinicalImpression CodeSystem Communication CommunicationRequest CompartmentDefinition
Composition ConceptMap Condition Consent Contract Coverage CoverageEligibilityRequest
CoverageEligibilityResponse DetectedIssue Device DeviceDefinition DeviceMetric DeviceRequest
DeviceUseStatement DiagnosticReport DocumentManifest DocumentReference EffectEvidenceSynthesis
Encounter Endpoint EnrollmentRequest EnrollmentResponse EpisodeOfCare EventDefinition Evidence
EvidenceVariable ExampleScenario ExplanationOfBenefit FamilyMemberHistory Flag Goal
GraphDefinition Group GuidanceResponse HealthcareService ImagingStudy Immunization
ImmunizationEvaluation ImmunizationRecommendation ImplementationGuide InsurancePlan Invoice
Library Linkage List Location Measure MeasureReport Media Medication MedicationAdministration
MedicationDispense MedicationKnowledge MedicationRequest MedicationStatement
MedicinalProduct MessageDefinition MessageHeader MolecularSequence NamingSystem
NutritionOrder Observation ObservationDefinition OperationDefinition OperationOutcome
Organization OrganizationAffiliation Parameters Patient PaymentNotice PaymentReconciliation
Person PlanDefinition Practitioner PractitionerRole Procedure Provenance Questionnaire
QuestionnaireResponse RelatedPerson RequestGroup ResearchDefinition ResearchElementDefinition
ResearchStudy ResearchSubject RiskAssessment RiskEvidenceSynthesis Schedule SearchParameter
ServiceRequest Slot Specimen SpecimenDefinition StructureDefinition StructureMap Subscription
Substance SupplyDelivery SupplyRequest Task TerminologyCapabilities TestReport TestScript
ValueSet VerificationResult VisionPrescription
""".split())

Transform = Literal["direct", "reference", "code", "class-coding", "role-coding"]


class FhirMappingError(ValueError):
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


# ============= Overlay models =============

class FhirField(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    property_: Optional[Union[str, List[str]]] = Field(None, alias="property")
    inverse: Optional[str] = None
    class_: Optional[str] = Field(None, alias="class")
    roles: List[str] = Field(default_factory=list)
    exclude_roles: List[str] = Field(default_factory=list, alias="exclude-roles")
    transform: Transform = "direct"
    map: Dict[str, str] = Field(default_factory=dict)
    default: Optional[Any] = None
    each: Dict[str, "FhirField"] = Field(default_factory=dict)
    single: bool = False
    many: bool = Field(False, alias="list")

    @property
    def path(self) -> List[str]:
        if self.property_ is None:
            return []
        return [self.property_] if isinstance(self.property_, str) else [*self.property_]


class FhirResourceMapping(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    resource: str
    profile: Optional[str] = None
    by_role: Dict[str, str] = Field(default_factory=dict, alias="by-role")
    constants: Dict[str, Any] = Field(default_factory=dict)
    fields: Dict[str, FhirField] = Field(default_factory=dict)


class FhirMapping(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    fhir_version: str = Field("4.0.1", alias="fhir-version")
    code_system: str = Field("urn:w3c:cg:ucm", alias="code-system")
    node_iri_extension: str = Field("urn:w3c:cg:ucm:fhir#node-iri", alias="node-iri-extension")
    resources: Dict[str, FhirResourceMapping]


# ============= Validation and compilation =============

class FhirCompiler:
    """Check an overlay against the IR and compile it for the adapter template"""

    def __init__(self, ir: OntologyIR, mapping: FhirMapping, api: Optional[SpecBuilder] = None):
        self.ir = ir
        self.mapping = mapping
        self.api = api or SpecBuilder(ir)
        self.classes = {c.term: c for c in ir.classes.values()}
        self.properties = {p.term: p for p in ir.properties.values()}
        self.errors: List[str] = []

    # ---------- helpers ----------

    def _class(self, term: Optional[str], where: str) -> Optional[str]:
        if term is None:
            return None
        if term not in self.classes:
            self.errors.append(f"{where}: unknown UCM class {term!r}")
            return None
        return self.classes[term].iri

    def _family(self, class_iri: Optional[str]) -> List[Optional[str]]:
        if class_iri is None:
            return [None]
        return [class_iri] + self.ir.ancestors(class_iri) + self.ir.descendants(class_iri)

    def _is_role(self, term: str, where: str) -> None:
        role = self.classes.get("Role")
        iri = self._class(term, where)
        if iri and role and iri != role.iri and role.iri not in self.ir.ancestors(iri):
            self.errors.append(f"{where}: {term} is not a ucm:Role")

    def _hop(self, term: str, current: Optional[str], where: str) -> Optional[str]:
        """Check one forward hop; returns the class reached, if known"""
        prop = self.properties.get(term)
        if prop is None:
            prefix = term.split(":", 1)[0] if ":" in term else None
            if prefix not in self.ir.prefixes:
                self.errors.append(f"{where}: unknown property {term!r}")
            return None
        if current is not None and prop.domain is not None and prop.domain not in self._family(current):
            self.errors.append(
                f"{where}: {term} has domain {self.ir.curie(prop.domain)}, "
                f"not applicable to {self.ir.curie(current)}"
            )
        return prop.range if prop.range in self.ir.classes else None

    # ---------- fields ----------

    def _field(self, field: FhirField, current: Optional[str], where: str) -> Dict[str, Any]:
        item_class = current
        if field.inverse:
            prop = self.properties.get(field.inverse)
            if prop is None or prop.kind != "object":
                self.errors.append(f"{where}: inverse {field.inverse!r} is not a UCM object property")
            else:
                if current is not None and prop.range and prop.range in self.ir.classes \
                        and prop.range not in self._family(current):
                    self.errors.append(
                        f"{where}: {field.inverse} ranges over {self.ir.curie(prop.range)}, "
                        f"which never points at {self.ir.curie(current)}"
                    )
                item_class = prop.domain if prop.domain in self.ir.classes else None
            item_class = self._class(field.class_, where) or item_class
        for role in field.roles + field.exclude_roles:
            self._is_role(role, where)
        if (field.roles or field.exclude_roles) and "assumesRole" in self.properties:
            domain = self.properties["assumesRole"].domain
            if item_class is not None and domain not in self._family(item_class):
                self.errors.append(f"{where}: role filters need participations, got {self.ir.curie(item_class)}")

        reached = item_class
        for hop in field.path:
            reached = self._hop(hop, reached, where)

        compiled: Dict[str, Any] = {
            "property": field.path,
            "inverse": field.inverse,
            "class": field.class_,
            "roles": field.roles,
            "exclude_roles": field.exclude_roles,
            "transform": field.transform,
            "single": field.single or (not field.each and not field.many),
        }
        if field.transform == "code":
            last = self.properties.get(field.path[-1]) if field.path else None
            scheme = self.api.scheme_for(last)
            if scheme is None:
                self.errors.append(f"{where}: transform code needs a property bound to a concept scheme")
            else:
                concepts = {c.term: c.iri for c in scheme.concepts}
                unknown = sorted(set(field.map) - set(concepts))
                if unknown:
                    self.errors.append(f"{where}: {unknown} are not concepts of {scheme.term}")
                compiled["map"] = {concepts[k]: v for k, v in field.map.items() if k in concepts}
                compiled["reverse"] = {v: k for k, v in field.map.items() if k in concepts}
                compiled["default"] = field.default
        if field.each:
            compiled["each"] = {
                path: self._field(sub, reached, f"{where}.{path}") for path, sub in field.each.items()
            }
        return compiled

    def compile(self) -> Dict[str, Any]:
        resources: Dict[str, Any] = {}
        for term, spec in self.mapping.resources.items():
            where = f"resources.{term}"
            class_iri = self._class(term, where)
            for resource in [spec.resource] + list(spec.by_role.values()):
                if resource not in R4_RESOURCES:
                    self.errors.append(f"{where}: {resource!r} is not a FHIR R4 resource type")
            for role in spec.by_role:
                self._is_role(role, f"{where}.by-role")
            resources[term] = {
                "resource": spec.resource,
                "profile": spec.profile,
                "by_role": list(spec.by_role.items()),
                "constants": spec.constants,
                "fields": {
                    path: self._field(field, class_iri, f"{where}.fields.{path}")
                    for path, field in spec.fields.items()
                },
            }
        if self.errors:
            raise FhirMappingError(list(dict.fromkeys(self.errors)))

        ir = self.ir
        context = self.api.context()
        concepts = {c.term: c.iri for s in ir.schemes.values() for c in s.concepts}
        keys = {
            p.term: [p.term, ir.curie(p.iri), p.iri] for p in sorted(ir.properties.values(), key=lambda p: p.term)
        }
        return {
            "fhir_version": self.mapping.fhir_version,
            "code_system": self.mapping.code_system,
            "node_iri_extension": self.mapping.node_iri_extension,
            "ontology_iri": ir.iri,
            "ontology_version": ir.version,
            "resources": resources,
            "ancestors": {
                c.term: [ir.classes[a].term for a in ir.ancestors(c.iri)]
                for c in sorted(ir.classes.values(), key=lambda c: c.term)
            },
            "keys": keys,
            "sets": {
                p.term: context[p.term].get("@container") == "@set"
                for p in sorted(ir.properties.values(), key=lambda p: p.term)
            },
            "concepts": concepts,
            "concept_terms": {iri: term for term, iri in concepts.items()},
            "prefixes": dict(ir.prefixes),
        }
