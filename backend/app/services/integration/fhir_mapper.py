"""HL7 FHIR R4 Resource Transformation Service (Milestone U-20).

Provides bi-directional mappings between internal EHR relational schemas and
HL7 FHIR Release 4 standard specifications (Patient, Appointment, DiagnosticReport,
MedicationRequest, and Bundle).

INVARIANT: Zero modification to internal PostgreSQL clinical tables.
All transformations are computed on-demand within this integration service boundary.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.models import (
    Appointment,
    AppointmentStatus,
    Doctor,
    MedicalRecord,
    MedicalRecordStatus,
    Patient,
    Prescription,
    PrescriptionStatus,
)


def to_fhir_patient(patient: Patient) -> Dict[str, Any]:
    """Map internal Patient entity to an HL7 FHIR R4 Patient resource."""
    identifiers: List[Dict[str, Any]] = [
        {
            "system": "https://aihos.org/patients",
            "value": str(patient.patient_id),
            "use": "usual",
        }
    ]

    if getattr(patient, "abha_address", None):
        identifiers.append({
            "system": "https://healthid.abdm.gov.in",
            "value": patient.abha_address,
            "use": "official",
        })

    telecom: List[Dict[str, Any]] = []
    if getattr(patient, "email", None):
        telecom.append({
            "system": "email",
            "value": patient.email,
            "use": "home",
        })
    if getattr(patient, "phone", None):
        telecom.append({
            "system": "phone",
            "value": patient.phone,
            "use": "mobile",
        })

    # Standardize FHIR administrative gender
    raw_gender = (patient.gender or "").lower().strip()
    if raw_gender in ("male", "m"):
        fhir_gender = "male"
    elif raw_gender in ("female", "f"):
        fhir_gender = "female"
    elif raw_gender in ("other", "non-binary", "transgender"):
        fhir_gender = "other"
    else:
        fhir_gender = "unknown"

    resource: Dict[str, Any] = {
        "resourceType": "Patient",
        "id": str(patient.patient_id),
        "identifier": identifiers,
        "active": True,
        "name": [
            {
                "use": "official",
                "text": patient.full_name,
            }
        ],
        "gender": fhir_gender,
        "birthDate": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
        "telecom": telecom,
    }

    if getattr(patient, "address", None):
        resource["address"] = [
            {
                "use": "home",
                "text": patient.address,
                "type": "physical",
            }
        ]

    if getattr(patient, "emergency_contact_name", None) or getattr(patient, "emergency_contact_phone", None):
        contact_entry: Dict[str, Any] = {
            "relationship": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0131",
                            "code": "C",
                            "display": "Emergency Contact",
                        }
                    ]
                }
            ]
        }
        if patient.emergency_contact_name:
            contact_entry["name"] = {"text": patient.emergency_contact_name}
        if patient.emergency_contact_phone:
            contact_entry["telecom"] = [{"system": "phone", "value": patient.emergency_contact_phone}]
        resource["contact"] = [contact_entry]

    return resource


def to_fhir_appointment(
    appointment: Appointment,
    doctor: Optional[Doctor] = None,
    patient: Optional[Patient] = None,
) -> Dict[str, Any]:
    """Map internal Appointment entity to an HL7 FHIR R4 Appointment resource."""
    status_map = {
        AppointmentStatus.SCHEDULED: "booked",
        AppointmentStatus.IN_PROGRESS: "arrived",
        AppointmentStatus.COMPLETED: "fulfilled",
        AppointmentStatus.CANCELLED: "cancelled",
    }
    fhir_status = status_map.get(appointment.status, "booked")

    duration = appointment.duration_minutes or 30
    end_time = appointment.scheduled_at + timedelta(minutes=duration)

    participants: List[Dict[str, Any]] = [
        {
            "actor": {
                "reference": f"Patient/{appointment.patient_id}",
                "display": patient.full_name if patient else None,
            },
            "status": "accepted",
        },
        {
            "actor": {
                "reference": f"Practitioner/{appointment.doctor_id}",
                "display": doctor.full_name if doctor else None,
            },
            "status": "accepted",
        },
    ]

    resource: Dict[str, Any] = {
        "resourceType": "Appointment",
        "id": str(appointment.appointment_id),
        "status": fhir_status,
        "serviceType": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/service-type",
                        "code": "consultation",
                        "display": "General Clinical Consultation",
                    }
                ]
            }
        ],
        "start": appointment.scheduled_at.isoformat(),
        "end": end_time.isoformat(),
        "minutesDuration": duration,
        "description": appointment.notes or "Scheduled Doctor Consultation",
        "participant": participants,
    }

    if getattr(appointment, "meeting_link", None):
        resource["telecom"] = [
            {
                "system": "url",
                "value": appointment.meeting_link,
                "use": "work",
            }
        ]

    return resource


def to_fhir_diagnostic_report(
    record: MedicalRecord,
    doctor: Optional[Doctor] = None,
    patient: Optional[Patient] = None,
) -> Dict[str, Any]:
    """Map internal MedicalRecord entity to an HL7 FHIR R4 DiagnosticReport / Composition."""
    is_final = record.status == MedicalRecordStatus.FINALIZED or record.finalized_at is not None
    fhir_status = "final" if is_final else "preliminary"

    content_data = record.content or {}
    assessment = content_data.get("assessment") or content_data.get("diagnosis") or "Clinical assessment recorded."

    resource: Dict[str, Any] = {
        "resourceType": "DiagnosticReport",
        "id": str(record.record_id),
        "status": fhir_status,
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                        "code": "CN",
                        "display": "Consultation Progress Note",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "11488-4",
                    "display": "Consultation note",
                }
            ],
            "text": "Outpatient Consultation Encounter Note",
        },
        "subject": {
            "reference": f"Patient/{record.patient_id}",
            "display": patient.full_name if patient else None,
        },
        "performer": [
            {
                "reference": f"Practitioner/{record.doctor_id}",
                "display": doctor.full_name if doctor else None,
            }
        ],
        "effectiveDateTime": record.created_at.isoformat(),
        "issued": (record.finalized_at or record.updated_at or record.created_at).isoformat(),
        "conclusion": str(assessment),
        "presentedForm": [
            {
                "contentType": "application/json",
                "data": content_data,
            }
        ],
    }

    if getattr(record, "appointment_id", None):
        resource["encounter"] = {
            "reference": f"Appointment/{record.appointment_id}",
        }

    return resource


def to_fhir_medication_request(
    prescription: Prescription,
    doctor: Optional[Doctor] = None,
    patient: Optional[Patient] = None,
) -> Dict[str, Any]:
    """Map internal Prescription entity to an HL7 FHIR R4 MedicationRequest resource."""
    status_map = {
        PrescriptionStatus.APPROVED: "active",
        PrescriptionStatus.DRAFT: "draft",
        PrescriptionStatus.REJECTED: "cancelled",
    }
    fhir_status = status_map.get(prescription.status, "active")

    meds_list = prescription.medications or []
    med_names = [m.get("name", "Medication") for m in meds_list if isinstance(m, dict)]
    combined_med_name = ", ".join(med_names) if med_names else "Prescribed Medication"

    dosage_instructions: List[Dict[str, Any]] = []
    for m in meds_list:
        if isinstance(m, dict):
            dosage_instructions.append({
                "text": f"{m.get('name', 'Drug')} - {m.get('dosage', '')} {m.get('frequency', '')} ({m.get('duration', '')})".strip(),
                "route": {
                    "text": m.get("route", "oral"),
                },
            })

    resource: Dict[str, Any] = {
        "resourceType": "MedicationRequest",
        "id": str(prescription.prescription_id),
        "status": fhir_status,
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "display": combined_med_name,
                }
            ],
            "text": combined_med_name,
        },
        "subject": {
            "reference": f"Patient/{prescription.patient_id}",
            "display": patient.full_name if patient else None,
        },
        "requester": {
            "reference": f"Practitioner/{prescription.doctor_id}",
            "display": doctor.full_name if doctor else None,
        },
        "authoredOn": prescription.created_at.isoformat(),
        "dosageInstruction": dosage_instructions,
    }

    if getattr(prescription, "notes", None):
        resource["note"] = [{"text": prescription.notes}]

    return resource


def to_fhir_bundle(
    patient: Patient,
    appointments: Optional[List[Appointment]] = None,
    records: Optional[List[MedicalRecord]] = None,
    prescriptions: Optional[List[Prescription]] = None,
    doctor: Optional[Doctor] = None,
) -> Dict[str, Any]:
    """Bundle Patient and all associated clinical resources into an HL7 FHIR R4 Bundle ($everything)."""
    import uuid

    entries: List[Dict[str, Any]] = []

    # 1. Patient Resource
    fhir_pat = to_fhir_patient(patient)
    entries.append({
        "fullUrl": f"urn:uuid:{patient.patient_id}",
        "resource": fhir_pat,
    })

    # 2. Appointment Resources
    for appt in (appointments or []):
        fhir_appt = to_fhir_appointment(appt, doctor=doctor, patient=patient)
        entries.append({
            "fullUrl": f"urn:uuid:{appt.appointment_id}",
            "resource": fhir_appt,
        })

    # 3. Medical Records (DiagnosticReport)
    for rec in (records or []):
        fhir_rec = to_fhir_diagnostic_report(rec, doctor=doctor, patient=patient)
        entries.append({
            "fullUrl": f"urn:uuid:{rec.record_id}",
            "resource": fhir_rec,
        })

    # 4. Prescriptions (MedicationRequest)
    for rx in (prescriptions or []):
        fhir_rx = to_fhir_medication_request(rx, doctor=doctor, patient=patient)
        entries.append({
            "fullUrl": f"urn:uuid:{rx.prescription_id}",
            "resource": fhir_rx,
        })

    bundle: Dict[str, Any] = {
        "resourceType": "Bundle",
        "id": str(uuid.uuid4()),
        "type": "searchset",
        "timestamp": datetime.utcnow().isoformat(),
        "total": len(entries),
        "entry": entries,
    }

    return bundle
