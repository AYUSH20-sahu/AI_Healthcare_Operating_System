"""HL7 FHIR R4 Resource Transformation Service (Milestone U-20).

Provides bi-directional mappings between internal EHR relational schemas and
HL7 FHIR Release 4 standard specifications (Patient, Appointment, DiagnosticReport,
MedicationRequest, and Bundle).

INVARIANT: Zero modification to internal PostgreSQL clinical tables.
All transformations are computed on-demand within this integration service boundary.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.models import (
    Appointment,
    AppointmentStatus,
    BedVitalsLog,
    Doctor,
    InpatientBed,
    MedicalRecord,
    MedicalRecordStatus,
    NurseTask,
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


def to_fhir_observation(
    vital: BedVitalsLog,
    patient: Optional[Patient] = None,
) -> Dict[str, Any]:
    """Map internal BedVitalsLog entity to an HL7 FHIR R4 Observation resource (Vital Signs)."""
    pat_id = str(patient.patient_id) if patient else (str(vital.patient_id) if vital.patient_id else "unknown")
    rec_time = vital.recorded_at.isoformat() if vital.recorded_at else datetime.utcnow().isoformat()

    components: List[Dict[str, Any]] = [
        {
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "8480-6",
                        "display": "Systolic blood pressure",
                    }
                ],
                "text": "Systolic Blood Pressure",
            },
            "valueQuantity": {
                "value": float(vital.systolic),
                "unit": "mmHg",
                "system": "http://unitsofmeasure.org",
                "code": "mm[Hg]",
            },
        },
        {
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "8462-4",
                        "display": "Diastolic blood pressure",
                    }
                ],
                "text": "Diastolic Blood Pressure",
            },
            "valueQuantity": {
                "value": float(vital.diastolic),
                "unit": "mmHg",
                "system": "http://unitsofmeasure.org",
                "code": "mm[Hg]",
            },
        },
        {
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "8867-4",
                        "display": "Heart rate",
                    }
                ],
                "text": "Heart Rate / Pulse",
            },
            "valueQuantity": {
                "value": float(vital.pulse),
                "unit": "beats/minute",
                "system": "http://unitsofmeasure.org",
                "code": "/min",
            },
        },
        {
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "2708-6",
                        "display": "Oxygen saturation in Arterial blood",
                    }
                ],
                "text": "Oxygen Saturation (SpO2)",
            },
            "valueQuantity": {
                "value": float(vital.spo2),
                "unit": "%",
                "system": "http://unitsofmeasure.org",
                "code": "%",
            },
        },
        {
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "8310-5",
                        "display": "Body temperature",
                    }
                ],
                "text": "Body Temperature",
            },
            "valueQuantity": {
                "value": float(vital.temp),
                "unit": "degF",
                "system": "http://unitsofmeasure.org",
                "code": "[degF]",
            },
        },
        {
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "9279-1",
                        "display": "Respiratory rate",
                    }
                ],
                "text": "Respiratory Rate",
            },
            "valueQuantity": {
                "value": float(getattr(vital, "respiratory_rate", 16) or 16),
                "unit": "breaths/minute",
                "system": "http://unitsofmeasure.org",
                "code": "/min",
            },
        },
    ]

    resource: Dict[str, Any] = {
        "resourceType": "Observation",
        "id": str(vital.log_id),
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs",
                    }
                ],
                "text": "Vital Signs",
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "85354-9",
                    "display": "Blood pressure panel with all children optional",
                }
            ],
            "text": "Bedside Vital Signs Telemetry",
        },
        "subject": {
            "reference": f"Patient/{pat_id}",
            "display": getattr(patient, "full_name", "Inpatient"),
        },
        "effectiveDateTime": rec_time,
        "component": components,
    }

    if getattr(vital, "notes", None):
        resource["valueString"] = vital.notes

    return resource


def to_fhir_encounter(
    bed: InpatientBed,
    patient: Optional[Patient] = None,
    doctor: Optional[Doctor] = None,
) -> Dict[str, Any]:
    """Map internal InpatientBed occupancy entity to an HL7 FHIR R4 Encounter resource."""
    pat_id = str(patient.patient_id) if patient else (str(bed.patient_id) if bed.patient_id else "unknown")
    pat_name = getattr(patient, "full_name", bed.patient_name or "Inpatient")
    admit_time = bed.admitted_at.isoformat() if bed.admitted_at else datetime.utcnow().isoformat()

    status_val = "in-progress" if bed.status == "occupied" else "finished"

    resource: Dict[str, Any] = {
        "resourceType": "Encounter",
        "id": str(bed.bed_id),
        "identifier": [
            {
                "system": "https://aihos.org/encounters/inpatient",
                "value": str(bed.bed_id),
                "use": "official",
            }
        ],
        "status": status_val,
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "IMP",
            "display": "inpatient encounter",
        },
        "subject": {
            "reference": f"Patient/{pat_id}",
            "display": pat_name,
        },
        "period": {
            "start": admit_time,
        },
        "reasonCode": [
            {
                "text": bed.admitted_for or "Inpatient Observation & Care",
            }
        ],
        "location": [
            {
                "location": {
                    "display": f"Ward {bed.ward}, Bed {bed.bed_number}",
                },
                "status": "active" if bed.status == "occupied" else "completed",
            }
        ],
    }

    if doctor:
        resource["participant"] = [
            {
                "individual": {
                    "reference": f"Practitioner/{doctor.doctor_id}",
                    "display": f"Dr. {doctor.full_name}",
                }
            }
        ]
    elif bed.attending_physician:
        resource["participant"] = [
            {
                "individual": {
                    "reference": "Practitioner/attending",
                    "display": bed.attending_physician,
                }
            }
        ]

    return resource


def to_fhir_composition(
    patient: Patient,
    bed: InpatientBed,
    vitals_logs: Optional[List[BedVitalsLog]] = None,
    nurse_tasks: Optional[List[NurseTask]] = None,
    records: Optional[List[MedicalRecord]] = None,
    prescriptions: Optional[List[Prescription]] = None,
    doctor: Optional[Doctor] = None,
) -> Dict[str, Any]:
    """Compile inpatient care data into a standardized HL7 FHIR R4 Composition (Discharge Summary)."""
    import uuid

    comp_id = str(uuid.uuid4())
    doc_ref = f"Practitioner/{doctor.doctor_id}" if doctor else "Practitioner/attending"
    doc_name = f"Dr. {doctor.full_name}" if doctor else (bed.attending_physician or "Attending Physician")

    sections: List[Dict[str, Any]] = [
        # 1. Chief Complaint & Admission Reason
        {
            "title": "Reason for Admission & Diagnosis",
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "46239-0",
                        "display": "Chief complaint and reason for visit",
                    }
                ],
                "text": "Reason for Admission",
            },
            "text": {
                "status": "generated",
                "div": f"<div><p><b>Admitted For:</b> {bed.admitted_for}</p><p><b>Ward/Bed:</b> {bed.ward} - Bed {bed.bed_number}</p></div>",
            },
        },
        # 2. Hospital Course & Doctor Consultation Notes
        {
            "title": "Hospital Course & Clinical Documentation",
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "8648-8",
                        "display": "Hospital course Clinical note",
                    }
                ],
                "text": "Hospital Course",
            },
            "entry": [
                {"reference": f"DiagnosticReport/{rec.record_id}", "display": f"Clinical Note ({rec.created_at.strftime('%Y-%m-%d')})"}
                for rec in (records or [])
            ],
            "text": {
                "status": "generated",
                "div": f"<div><p>Hospital stay duration: {bed.admit_day} day(s). Attending physician: {doc_name}. Clinical review complete.</p></div>",
            },
        },
        # 3. Vital Signs Summary
        {
            "title": "Bedside Vital Signs Telemetry",
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "8716-3",
                        "display": "Vital signs",
                    }
                ],
                "text": "Vital Signs",
            },
            "entry": [
                {"reference": f"Observation/{v.log_id}", "display": f"Vitals @ {v.recorded_at.strftime('%H:%M')} (BP: {v.bp}, Pulse: {v.pulse})"}
                for v in (vitals_logs or [])[:5]
            ],
            "text": {
                "status": "generated",
                "div": f"<div><p>Latest Telemetry: BP {bed.bp} mmHg, Pulse {bed.pulse} bpm, SpO2 {bed.spo2}%, Temp {bed.temp}°F. Clinical Status: {bed.clinical_status}.</p></div>",
            },
        },
        # 4. Inpatient Medication Administrations
        {
            "title": "Inpatient Medications Administered",
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "18610-6",
                        "display": "Medication administered",
                    }
                ],
                "text": "Medications Administered",
            },
            "text": {
                "status": "generated",
                "div": f"<div><p>{len(nurse_tasks or [])} ward medication rounds administered during hospital stay.</p></div>",
            },
        },
        # 5. Discharge Medications
        {
            "title": "Discharge Medications & Regimen",
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "75311-1",
                        "display": "Discharge medications",
                    }
                ],
                "text": "Discharge Medications",
            },
            "entry": [
                {"reference": f"MedicationRequest/{rx.prescription_id}", "display": f"Prescription #{str(rx.prescription_id)[:8]}"}
                for rx in (prescriptions or [])
            ],
            "text": {
                "status": "generated",
                "div": f"<div><p>{len(prescriptions or [])} discharge prescription order(s) finalized.</p></div>",
            },
        },
        # 6. Care Plan & Follow-Up
        {
            "title": "Plan of Care & Follow-Up Instructions",
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "18776-5",
                        "display": "Plan of care note",
                    }
                ],
                "text": "Care Plan & Follow-Up",
            },
            "text": {
                "status": "generated",
                "div": f"<div><p>Dietary instructions: {bed.diet}. Code status: {bed.code_status}. Follow-up with OPD in 7 days or immediately if acute symptoms recur.</p></div>",
            },
        },
    ]

    resource: Dict[str, Any] = {
        "resourceType": "Composition",
        "id": comp_id,
        "identifier": {
            "system": "https://aihos.org/compositions/discharge-summary",
            "value": f"DS-{bed.bed_id}-{patient.patient_id}",
            "use": "official",
        },
        "status": "final",
        "type": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "18842-5",
                    "display": "Discharge summary note",
                }
            ],
            "text": "Hospital Discharge Summary",
        },
        "category": [
            {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "LP173421-1",
                        "display": "Report",
                    }
                ],
                "text": "Clinical Report",
            }
        ],
        "subject": {
            "reference": f"Patient/{patient.patient_id}",
            "display": patient.full_name,
        },
        "encounter": {
            "reference": f"Encounter/{bed.bed_id}",
            "display": f"Inpatient Stay ({bed.ward} - Bed {bed.bed_number})",
        },
        "date": datetime.utcnow().isoformat(),
        "author": [
            {
                "reference": doc_ref,
                "display": doc_name,
            }
        ],
        "title": f"Inpatient Discharge Summary — {patient.full_name}",
        "section": sections,
    }

    return resource


def to_fhir_discharge_bundle(
    patient: Patient,
    bed: InpatientBed,
    vitals_logs: Optional[List[BedVitalsLog]] = None,
    nurse_tasks: Optional[List[NurseTask]] = None,
    records: Optional[List[MedicalRecord]] = None,
    prescriptions: Optional[List[Prescription]] = None,
    doctor: Optional[Doctor] = None,
) -> Dict[str, Any]:
    """Bundle inpatient Discharge Summary Composition and all referenced resources into a FHIR R4 Document Bundle."""
    import uuid

    entries: List[Dict[str, Any]] = []

    # 1. Composition (MUST be first entry for FHIR document bundle)
    composition = to_fhir_composition(
        patient=patient,
        bed=bed,
        vitals_logs=vitals_logs,
        nurse_tasks=nurse_tasks,
        records=records,
        prescriptions=prescriptions,
        doctor=doctor,
    )
    entries.append({
        "fullUrl": f"urn:uuid:{composition['id']}",
        "resource": composition,
    })

    # 2. Patient
    pat_res = to_fhir_patient(patient)
    entries.append({
        "fullUrl": f"urn:uuid:{patient.patient_id}",
        "resource": pat_res,
    })

    # 3. Encounter
    enc_res = to_fhir_encounter(bed, patient=patient, doctor=doctor)
    entries.append({
        "fullUrl": f"urn:uuid:{bed.bed_id}",
        "resource": enc_res,
    })

    # 4. Observations (Vitals)
    for v in (vitals_logs or []):
        obs_res = to_fhir_observation(v, patient=patient)
        entries.append({
            "fullUrl": f"urn:uuid:{v.log_id}",
            "resource": obs_res,
        })

    # 5. DiagnosticReports (Medical Records)
    for rec in (records or []):
        rep_res = to_fhir_diagnostic_report(rec, doctor=doctor, patient=patient)
        entries.append({
            "fullUrl": f"urn:uuid:{rec.record_id}",
            "resource": rep_res,
        })

    # 6. MedicationRequests (Prescriptions)
    for rx in (prescriptions or []):
        rx_res = to_fhir_medication_request(rx, doctor=doctor, patient=patient)
        entries.append({
            "fullUrl": f"urn:uuid:{rx.prescription_id}",
            "resource": rx_res,
        })

    return {
        "resourceType": "Bundle",
        "id": str(uuid.uuid4()),
        "identifier": {
            "system": "https://aihos.org/bundles/discharge-document",
            "value": f"DOC-{bed.bed_id}",
            "use": "official",
        },
        "type": "document",
        "timestamp": datetime.utcnow().isoformat(),
        "total": len(entries),
        "entry": entries,
    }

