"""HL7 FHIR Release 4 Schema Validator Service (Horizon E).

Provides strict Pydantic v2 schema models and validation routines conforming to the
official HL7 FHIR Release 4 (R4) specifications for:
- Patient
- Encounter
- Condition
- MedicationRequest
- DiagnosticReport
- Observation
- Composition
- Bundle
- OperationOutcome (for structured validation reporting)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, model_validator


# ─── Common FHIR R4 Primitive & Complex Types ─────────────────────────────────

class FHIRPeriod(BaseModel):
    start: Optional[Union[datetime, str]] = None
    end: Optional[Union[datetime, str]] = None


class FHIRCoding(BaseModel):
    system: Optional[str] = None
    version: Optional[str] = None
    code: Optional[str] = None
    display: Optional[str] = None
    userSelected: Optional[bool] = None


class FHIRCodeableConcept(BaseModel):
    coding: Optional[List[FHIRCoding]] = Field(default_factory=list)
    text: Optional[str] = None


class FHIRIdentifier(BaseModel):
    use: Optional[Literal["usual", "official", "temp", "secondary", "old"]] = None
    type: Optional[FHIRCodeableConcept] = None
    system: Optional[str] = None
    value: str
    period: Optional[FHIRPeriod] = None


class FHIRReference(BaseModel):
    reference: Optional[str] = None
    type: Optional[str] = None
    identifier: Optional[FHIRIdentifier] = None
    display: Optional[str] = None


class FHIRHumanName(BaseModel):
    use: Optional[Literal["usual", "official", "temp", "nickname", "anonymous", "old", "maiden"]] = None
    text: Optional[str] = None
    family: Optional[str] = None
    given: Optional[List[str]] = Field(default_factory=list)
    prefix: Optional[List[str]] = Field(default_factory=list)
    suffix: Optional[List[str]] = Field(default_factory=list)


class FHIRContactPoint(BaseModel):
    system: Optional[Literal["phone", "fax", "email", "pager", "url", "sms", "other"]] = None
    value: Optional[str] = None
    use: Optional[Literal["home", "work", "temp", "old", "mobile"]] = None


class FHIRAddress(BaseModel):
    use: Optional[Literal["home", "work", "temp", "old", "billing"]] = None
    type: Optional[Literal["postal", "physical", "both"]] = None
    text: Optional[str] = None
    line: Optional[List[str]] = Field(default_factory=list)
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: Optional[str] = None


class FHIRQuantity(BaseModel):
    value: Optional[float] = None
    comparator: Optional[Literal["<", "<=", ">=", ">"]] = None
    unit: Optional[str] = None
    system: Optional[str] = None
    code: Optional[str] = None


# ─── Resource: Patient ────────────────────────────────────────────────────────

class FHIRPatient(BaseModel):
    resourceType: Literal["Patient"]
    id: Optional[str] = None
    identifier: Optional[List[FHIRIdentifier]] = Field(default_factory=list)
    active: Optional[bool] = True
    name: Optional[List[FHIRHumanName]] = Field(default_factory=list)
    telecom: Optional[List[FHIRContactPoint]] = Field(default_factory=list)
    gender: Optional[Literal["male", "female", "other", "unknown"]] = None
    birthDate: Optional[Union[date, str]] = None
    address: Optional[List[FHIRAddress]] = Field(default_factory=list)


# ─── Resource: Encounter ──────────────────────────────────────────────────────

class FHIREncounterParticipant(BaseModel):
    type: Optional[List[FHIRCodeableConcept]] = Field(default_factory=list)
    individual: Optional[FHIRReference] = None


class FHIREncounterLocation(BaseModel):
    location: FHIRReference
    status: Optional[Literal["planned", "active", "reserved", "completed"]] = None
    period: Optional[FHIRPeriod] = None


class FHIREncounter(BaseModel):
    resourceType: Literal["Encounter"]
    id: Optional[str] = None
    identifier: Optional[List[FHIRIdentifier]] = Field(default_factory=list)
    status: Literal[
        "planned", "arrived", "triaged", "in-progress", "onleave", "finished", "cancelled", "entered-in-error", "unknown"
    ]
    class_fhir: FHIRCoding = Field(alias="class")
    subject: Optional[FHIRReference] = None
    participant: Optional[List[FHIREncounterParticipant]] = Field(default_factory=list)
    period: Optional[FHIRPeriod] = None
    reasonCode: Optional[List[FHIRCodeableConcept]] = Field(default_factory=list)
    location: Optional[List[FHIREncounterLocation]] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


# ─── Resource: Condition ──────────────────────────────────────────────────────

class FHIRCondition(BaseModel):
    resourceType: Literal["Condition"]
    id: Optional[str] = None
    identifier: Optional[List[FHIRIdentifier]] = Field(default_factory=list)
    clinicalStatus: Optional[FHIRCodeableConcept] = None
    verificationStatus: Optional[FHIRCodeableConcept] = None
    category: Optional[List[FHIRCodeableConcept]] = Field(default_factory=list)
    severity: Optional[FHIRCodeableConcept] = None
    code: Optional[FHIRCodeableConcept] = None
    subject: FHIRReference
    encounter: Optional[FHIRReference] = None
    onsetDateTime: Optional[Union[datetime, str]] = None
    recordedDate: Optional[Union[datetime, str]] = None
    recorder: Optional[FHIRReference] = None


# ─── Resource: MedicationRequest ──────────────────────────────────────────────

class FHIRDoseAndRate(BaseModel):
    doseQuantity: Optional[FHIRQuantity] = None


class FHIRDosage(BaseModel):
    sequence: Optional[int] = None
    text: Optional[str] = None
    timing: Optional[Dict[str, Any]] = None
    route: Optional[FHIRCodeableConcept] = None
    doseAndRate: Optional[List[FHIRDoseAndRate]] = Field(default_factory=list)


class FHIRMedicationRequest(BaseModel):
    resourceType: Literal["MedicationRequest"]
    id: Optional[str] = None
    identifier: Optional[List[FHIRIdentifier]] = Field(default_factory=list)
    status: Literal[
        "active", "on-hold", "cancelled", "completed", "entered-in-error", "stopped", "draft", "unknown"
    ]
    intent: Literal[
        "proposal", "plan", "order", "original-order", "reflex-order", "filler-order", "instance-order", "option"
    ]
    medicationCodeableConcept: Optional[FHIRCodeableConcept] = None
    medicationReference: Optional[FHIRReference] = None
    subject: FHIRReference
    encounter: Optional[FHIRReference] = None
    authoredOn: Optional[Union[datetime, str]] = None
    requester: Optional[FHIRReference] = None
    dosageInstruction: Optional[List[FHIRDosage]] = Field(default_factory=list)
    note: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_medication_defined(self):
        if not self.medicationCodeableConcept and not self.medicationReference:
            raise ValueError("Either medicationCodeableConcept or medicationReference must be provided.")
        return self


# ─── Resource: DiagnosticReport ───────────────────────────────────────────────

class FHIRDiagnosticReport(BaseModel):
    resourceType: Literal["DiagnosticReport"]
    id: Optional[str] = None
    identifier: Optional[List[FHIRIdentifier]] = Field(default_factory=list)
    status: Literal[
        "registered", "partial", "preliminary", "final", "amended", "corrected", "appended", "cancelled", "entered-in-error", "unknown"
    ]
    category: Optional[List[FHIRCodeableConcept]] = Field(default_factory=list)
    code: FHIRCodeableConcept
    subject: Optional[FHIRReference] = None
    encounter: Optional[FHIRReference] = None
    effectiveDateTime: Optional[Union[datetime, str]] = None
    issued: Optional[Union[datetime, str]] = None
    performer: Optional[List[FHIRReference]] = Field(default_factory=list)
    result: Optional[List[FHIRReference]] = Field(default_factory=list)
    conclusion: Optional[str] = None
    conclusionCode: Optional[List[FHIRCodeableConcept]] = Field(default_factory=list)


# ─── Resource: Observation (Bedside Telemetry / Vitals) ───────────────────────

class FHIRObservationComponent(BaseModel):
    code: FHIRCodeableConcept
    valueQuantity: Optional[FHIRQuantity] = None
    valueString: Optional[str] = None


class FHIRObservation(BaseModel):
    resourceType: Literal["Observation"]
    id: Optional[str] = None
    identifier: Optional[List[FHIRIdentifier]] = Field(default_factory=list)
    status: Literal[
        "registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error", "unknown"
    ]
    category: Optional[List[FHIRCodeableConcept]] = Field(default_factory=list)
    code: FHIRCodeableConcept
    subject: Optional[FHIRReference] = None
    encounter: Optional[FHIRReference] = None
    effectiveDateTime: Optional[Union[datetime, str]] = None
    issued: Optional[Union[datetime, str]] = None
    performer: Optional[List[FHIRReference]] = Field(default_factory=list)
    valueQuantity: Optional[FHIRQuantity] = None
    valueString: Optional[str] = None
    component: Optional[List[FHIRObservationComponent]] = Field(default_factory=list)


# ─── Resource: Composition (Discharge Summary / Clinical Notes) ───────────────

class FHIRCompositionSection(BaseModel):
    title: Optional[str] = None
    code: Optional[FHIRCodeableConcept] = None
    text: Optional[Dict[str, Any]] = None  # narrative {status, div}
    entry: Optional[List[FHIRReference]] = Field(default_factory=list)
    section: Optional[List["FHIRCompositionSection"]] = Field(default_factory=list)


class FHIRComposition(BaseModel):
    resourceType: Literal["Composition"]
    id: Optional[str] = None
    identifier: Optional[FHIRIdentifier] = None
    status: Literal["preliminary", "final", "amended", "entered-in-error"]
    type: FHIRCodeableConcept
    category: Optional[List[FHIRCodeableConcept]] = Field(default_factory=list)
    subject: FHIRReference
    encounter: Optional[FHIRReference] = None
    date: Union[datetime, str]
    author: List[FHIRReference]
    title: str
    section: Optional[List[FHIRCompositionSection]] = Field(default_factory=list)


# ─── Resource: Bundle ─────────────────────────────────────────────────────────

class FHIRBundleEntry(BaseModel):
    fullUrl: Optional[str] = None
    resource: Dict[str, Any]
    search: Optional[Dict[str, Any]] = None


class FHIRBundle(BaseModel):
    resourceType: Literal["Bundle"]
    id: Optional[str] = None
    identifier: Optional[FHIRIdentifier] = None
    type: Literal[
        "document", "message", "transaction", "transaction-response", "batch", "batch-response", "history", "searchset", "collection"
    ]
    timestamp: Optional[Union[datetime, str]] = None
    total: Optional[int] = None
    entry: Optional[List[FHIRBundleEntry]] = Field(default_factory=list)


# ─── FHIR OperationOutcome Reporting ──────────────────────────────────────────

class FHIROperationOutcomeIssue(BaseModel):
    severity: Literal["fatal", "error", "warning", "information"]
    code: str
    details: Optional[FHIRCodeableConcept] = None
    diagnostics: Optional[str] = None
    expression: Optional[List[str]] = None


class FHIROperationOutcome(BaseModel):
    resourceType: Literal["OperationOutcome"] = "OperationOutcome"
    issue: List[FHIROperationOutcomeIssue] = Field(default_factory=list)


# ─── Main FHIRValidator Service ───────────────────────────────────────────────

RESOURCE_MODEL_MAP = {
    "Patient": FHIRPatient,
    "Encounter": FHIREncounter,
    "Condition": FHIRCondition,
    "MedicationRequest": FHIRMedicationRequest,
    "DiagnosticReport": FHIRDiagnosticReport,
    "Observation": FHIRObservation,
    "Composition": FHIRComposition,
    "Bundle": FHIRBundle,
}


class FHIRValidationResult:
    def __init__(
        self,
        is_valid: bool,
        resource_type: str,
        resource_id: Optional[str] = None,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        issues: Optional[List[Dict[str, Any]]] = None,
    ):
        self.is_valid = is_valid
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.errors = errors or []
        self.warnings = warnings or []
        self.issues = issues or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "isValid": self.is_valid,
            "resourceType": self.resource_type,
            "resourceId": self.resource_id,
            "errors": self.errors,
            "warnings": self.warnings,
            "operationOutcome": self.to_operation_outcome(),
        }

    def to_operation_outcome(self) -> Dict[str, Any]:
        issues_list = []
        if self.is_valid:
            issues_list.append({
                "severity": "information",
                "code": "informational",
                "diagnostics": f"Validation passed successfully for {self.resource_type} (ID: {self.resource_id or 'anonymous'}).",
            })
        else:
            for err in self.errors:
                issues_list.append({
                    "severity": "error",
                    "code": "invalid",
                    "diagnostics": err,
                })
        for warn in self.warnings:
            issues_list.append({
                "severity": "warning",
                "code": "business-rule",
                "diagnostics": warn,
            })
        return {
            "resourceType": "OperationOutcome",
            "issue": issues_list,
        }


class FHIRValidator:
    """Institutional HL7 FHIR Release 4 Schema Validator."""

    @classmethod
    def validate_resource(cls, payload: Dict[str, Any]) -> FHIRValidationResult:
        """Validate any single FHIR R4 resource against standard schemas."""
        if not isinstance(payload, dict):
            return FHIRValidationResult(
                is_valid=False,
                resource_type="Unknown",
                errors=["Payload must be a valid JSON/dict object."],
            )

        resource_type = payload.get("resourceType")
        if not resource_type:
            return FHIRValidationResult(
                is_valid=False,
                resource_type="Unknown",
                errors=["Missing mandatory 'resourceType' field in FHIR payload."],
            )

        resource_id = payload.get("id")
        model_cls = RESOURCE_MODEL_MAP.get(resource_type)

        if not model_cls:
            # Resource type recognized by FHIR standard but not strictly modeled in this tier
            return FHIRValidationResult(
                is_valid=True,
                resource_type=resource_type,
                resource_id=resource_id,
                warnings=[f"Resource type '{resource_type}' is accepted but not under strict Pydantic profile validation."],
            )

        try:
            model_cls.model_validate(payload)
            return FHIRValidationResult(
                is_valid=True,
                resource_type=resource_type,
                resource_id=resource_id,
            )
        except Exception as e:
            errors = []
            if hasattr(e, "errors"):
                for err in e.errors():
                    loc = " -> ".join(str(p) for p in err.get("loc", []))
                    msg = err.get("msg", "Validation error")
                    errors.append(f"[{loc}]: {msg}")
            else:
                errors.append(str(e))

            return FHIRValidationResult(
                is_valid=False,
                resource_type=resource_type,
                resource_id=resource_id,
                errors=errors,
            )

    @classmethod
    def validate_bundle(cls, bundle_payload: Dict[str, Any]) -> FHIRValidationResult:
        """Validate a FHIR Bundle including recursive validation of all contained entries."""
        outer_res = cls.validate_resource(bundle_payload)
        if not outer_res.is_valid:
            return outer_res

        if bundle_payload.get("resourceType") != "Bundle":
            return FHIRValidationResult(
                is_valid=False,
                resource_type=bundle_payload.get("resourceType", "Unknown"),
                errors=["Expected 'Bundle' resourceType."],
            )

        entries = bundle_payload.get("entry") or []
        inner_errors: List[str] = []
        inner_warnings: List[str] = list(outer_res.warnings)

        for idx, entry in enumerate(entries):
            resource = entry.get("resource")
            if not resource:
                inner_errors.append(f"Bundle.entry[{idx}]: Missing 'resource' body.")
                continue

            entry_res = cls.validate_resource(resource)
            if not entry_res.is_valid:
                for err in entry_res.errors:
                    inner_errors.append(f"Bundle.entry[{idx}] ({entry_res.resource_type}): {err}")
            inner_warnings.extend(entry_res.warnings)

        return FHIRValidationResult(
            is_valid=len(inner_errors) == 0,
            resource_type="Bundle",
            resource_id=bundle_payload.get("id"),
            errors=inner_errors,
            warnings=inner_warnings,
        )
