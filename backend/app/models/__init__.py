"""
AI-HOS Database Models

Core schema with FHIR-R4 mapping notes for healthcare interoperability.
All tables use UUID primary keys for distributed system compatibility.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)

from sqlalchemy.types import CHAR, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class SafeUUID(TypeDecorator):
    """Platform-independent UUID that accepts both str and uuid.UUID objects."""
    impl = PG_UUID
    cache_ok = True

    def __init__(self, as_uuid=True, *args, **kwargs):
        super().__init__(as_uuid=as_uuid, *args, **kwargs)
        self.as_uuid = as_uuid

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=self.as_uuid))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                value = uuid.UUID(value)
            except (ValueError, AttributeError):
                return str(value)
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except (ValueError, AttributeError):
            return value


UUID = SafeUUID


class Base(DeclarativeBase):
    """Base class for all models."""


class UserRole(PyEnum):
    """User roles in the system."""
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"
    NURSE = "nurse"
    RECEPTIONIST = "receptionist"
    SUPER_ADMIN = "super_admin"
    HEAD_PHYSICIAN = "head_physician"
    HEAD_NURSE = "head_nurse"


class AppointmentStatus(PyEnum):
    """Appointment status values."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class MedicalRecordStatus(PyEnum):
    """Medical record status values."""
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"
    AMENDED = "AMENDED"


class PrescriptionStatus(PyEnum):
    """Prescription status values."""
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"
    APPROVED = "APPROVED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class IntakeStatus(PyEnum):
    """Patient intake session status."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"


class ConsentScope(str, PyEnum):
    """Consent record scope values."""
    FULL_ACCESS = "full_access"
    RECORDS_ONLY = "records_only"
    APPOINTMENTS_ONLY = "appointments_only"
    NOTES_ONLY = "notes_only"
    LIMITED = "limited"
    EMERGENCY_ONLY = "emergency_only"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            val_lower = value.lower()
            for member in cls:
                if member.value == val_lower or member.name.lower() == val_lower:
                    return member
        return None


class AuditOutcome(PyEnum):
    """Audit log outcome values."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


# FHIR: Organization
class Organization(Base):
    """Healthcare Organization / Hospital Facility.
    
    FHIR-R4 Mapping: Organization resource
    Key FHIR fields: identifier, active, type, name, telecom, address
    """
    __tablename__ = "organizations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Medical & Clinical Facility Configuration (Step 2)
    facility_type: Mapped[str] = mapped_column(String(100), default="Multi-Specialty Hospital")
    departments: Mapped[list[str]] = mapped_column(JSON, default=list)
    total_beds: Mapped[int] = mapped_column(Integer, default=0)
    icu_beds: Mapped[int] = mapped_column(Integer, default=0)
    has_emergency: Mapped[bool] = mapped_column(Boolean, default=True)
    has_ambulance: Mapped[bool] = mapped_column(Boolean, default=True)

    # Regulatory & Licensing Credentials (Step 3)
    license_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    abdm_facility_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    insurance_network_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Operational Settings & Review Gate (Step 4)
    emergency_hotline: Mapped[str | None] = mapped_column(String(50), nullable=True)
    operating_hours: Mapped[str] = mapped_column(String(100), default="24/7 Emergency & Inpatient")
    clinical_review_policy: Mapped[str] = mapped_column(String(100), default="Strict Doctor Sign-Off Required")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="organization", cascade="all, delete-orphan", foreign_keys="User.organization_id"
    )


# FHIR: User (for authentication)
class User(Base):
    """User authentication and authorization.
    
    FHIR-R4 Mapping: Practitioner (for providers) / Patient (for patients) + Provenance
    Key FHIR fields: identifier, name, telecom, authentication, authorization
    """
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), unique=True, index=True, nullable=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.organization_id", ondelete="CASCADE"), nullable=True, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda x: [e.value for e in x]), default=UserRole.PATIENT, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Institutional Staffing & Department Hierarchy (4-Step Provisioning)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    designation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    qualifications: Mapped[str | None] = mapped_column(String(255), nullable=True)
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    room_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shift: Mapped[str | None] = mapped_column(String(100), nullable=True)
    supervisor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="users", foreign_keys=[organization_id])
    patient_profile: Mapped[Optional["Patient"]] = relationship(
        "Patient",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        primaryjoin="User.user_id == Patient.user_id",
        foreign_keys="[Patient.user_id]",
    )
    doctor_profile: Mapped[Optional["Doctor"]] = relationship(
        "Doctor",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        primaryjoin="User.user_id == Doctor.user_id",
        foreign_keys="[Doctor.user_id]",
    )


# =============================================================================
# FHIR Mapping Notes:
# - patients → FHIR Patient
# - doctors → FHIR Practitioner + PractitionerRole
# - appointments → FHIR Appointment
# - medical_records → FHIR Composition / ClinicalImpression / DiagnosticReport
# - prescriptions → FHIR MedicationRequest
# - audit_logs → FHIR AuditEvent
# - consents → FHIR Consent
# =============================================================================


# FHIR: Patient
class Patient(Base):
    """Patient demographic and contact information.
    
    FHIR-R4 Mapping: Patient resource
    Key FHIR fields: identifier (ABHA), name, gender, birthDate, telecom, address, contact
    """
    __tablename__ = "patients"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), unique=True, index=True
    )
    abha_address: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    date_of_birth: Mapped[Date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), index=True)
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(Text)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(255))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="patient_profile",
        primaryjoin="Patient.user_id == User.user_id",
        foreign_keys=[user_id],
    )
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="patient")
    medical_records: Mapped[list["MedicalRecord"]] = relationship(back_populates="patient")
    prescriptions: Mapped[list["Prescription"]] = relationship(back_populates="patient")
    voice_notes: Mapped[list["VoiceNote"]] = relationship(back_populates="patient")
    consents: Mapped[list["Consent"]] = relationship(back_populates="patient")
    intake_sessions: Mapped[list["IntakeSession"]] = relationship(back_populates="patient")
    reports: Mapped[list["PatientReport"]] = relationship(back_populates="patient", cascade="all, delete-orphan")
    medicine_reminders: Mapped[list["MedicineReminder"]] = relationship(back_populates="patient", cascade="all, delete-orphan")

    @property
    def first_name(self) -> str:
        if self.full_name:
            parts = self.full_name.split()
            return parts[0] if parts else ""
        return ""

    @first_name.setter
    def first_name(self, value: str) -> None:
        first = value or ""
        last = self.last_name
        self.full_name = f"{first} {last}".strip()

    @property
    def last_name(self) -> str:
        if self.full_name:
            parts = self.full_name.split()
            return " ".join(parts[1:]) if len(parts) > 1 else ""
        return ""

    @last_name.setter
    def last_name(self, value: str) -> None:
        first = self.first_name
        last = value or ""
        self.full_name = f"{first} {last}".strip()

    def __init__(self, **kwargs):
        if "first_name" in kwargs or "last_name" in kwargs:
            first = kwargs.pop("first_name", "") or ""
            last = kwargs.pop("last_name", "") or ""
            if "full_name" not in kwargs or not kwargs["full_name"]:
                kwargs["full_name"] = f"{first} {last}".strip()
        super().__init__(**kwargs)


# FHIR: Practitioner + PractitionerRole
class Doctor(Base):
    """Doctor/Provider information and credentials.
    
    FHIR-R4 Mapping: Practitioner + PractitionerRole resources
    Key FHIR fields: identifier (license), name, qualification, organization, specialty
    """
    __tablename__ = "doctors"

    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), unique=True, index=True
    )
    specialty: Mapped[str] = mapped_column(String(100), index=True)
    license_number: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hospital_affiliation: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(50))

    # Institutional Staffing & Department Hierarchy
    department: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    designation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    qualifications: Mapped[str | None] = mapped_column(String(255), nullable=True)
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    room_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shift: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_head_physician: Mapped[bool] = mapped_column(Boolean, default=False)
    supervisor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="doctor_profile",
        primaryjoin="Doctor.user_id == User.user_id",
        foreign_keys=[user_id],
    )
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="doctor")
    medical_records: Mapped[list["MedicalRecord"]] = relationship(back_populates="doctor")
    prescriptions: Mapped[list["Prescription"]] = relationship(back_populates="doctor")
    voice_notes: Mapped[list["VoiceNote"]] = relationship(back_populates="doctor")
    consents_given: Mapped[list["Consent"]] = relationship(back_populates="provider", foreign_keys="Consent.provider_id")

    @property
    def first_name(self) -> str:
        if self.full_name:
            parts = self.full_name.split()
            return parts[0] if parts else ""
        return ""

    @first_name.setter
    def first_name(self, value: str) -> None:
        first = value or ""
        last = self.last_name
        self.full_name = f"{first} {last}".strip()

    @property
    def last_name(self) -> str:
        if self.full_name:
            parts = self.full_name.split()
            return " ".join(parts[1:]) if len(parts) > 1 else ""
        return ""

    @last_name.setter
    def last_name(self, value: str) -> None:
        first = self.first_name
        last = value or ""
        self.full_name = f"{first} {last}".strip()

    def __init__(self, **kwargs):
        if "first_name" in kwargs or "last_name" in kwargs:
            first = kwargs.pop("first_name", "") or ""
            last = kwargs.pop("last_name", "") or ""
            if "full_name" not in kwargs or not kwargs["full_name"]:
                kwargs["full_name"] = f"{first} {last}".strip()
        super().__init__(**kwargs)


# FHIR: Appointment
class Appointment(Base):
    """Appointment scheduling between patients and doctors.
    
    FHIR-R4 Mapping: Appointment resource
    Key FHIR fields: status, serviceType, specialty, appointmentType, start/end, participant (patient, practitioner)
    """
    __tablename__ = "appointments"

    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.patient_id"), index=True
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.doctor_id"), index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    duration_minutes: Mapped[int] = mapped_column(default=30)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meeting_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    telehealth_room_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    telehealth_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    telehealth_ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient: Mapped["Patient"] = relationship(back_populates="appointments")
    doctor: Mapped["Doctor"] = relationship(back_populates="appointments")
    medical_records: Mapped[list["MedicalRecord"]] = relationship(back_populates="appointment")
    voice_notes: Mapped[list["VoiceNote"]] = relationship(back_populates="appointment")

    def __init__(self, **kwargs):
        if "reason" in kwargs and not kwargs.get("notes"):
            kwargs["notes"] = kwargs.get("reason")
        super().__init__(**kwargs)


# FHIR: Composition / ClinicalImpression / DiagnosticReport
class MedicalRecord(Base):
    """Clinical documentation for patient encounters.
    
    FHIR-R4 Mapping: Composition (for clinical notes), ClinicalImpression (for assessments), 
    DiagnosticReport (for structured results)
    Key FHIR fields: status, type, subject (patient), author (practitioner), encounter (appointment),
    date, section (structured content), code (LOINC)
    """
    __tablename__ = "medical_records"

    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.patient_id"), index=True
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.doctor_id"), index=True
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.appointment_id"), index=True
    )
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[MedicalRecordStatus] = mapped_column(
        Enum(MedicalRecordStatus), default=MedicalRecordStatus.DRAFT, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship(back_populates="medical_records")
    doctor: Mapped["Doctor"] = relationship(back_populates="medical_records")
    appointment: Mapped[Optional["Appointment"]] = relationship(back_populates="medical_records")
    prescriptions: Mapped[list["Prescription"]] = relationship(back_populates="medical_record")


# FHIR: MedicationRequest
class Prescription(Base):
    """Prescription/medication orders linked to medical records.
    
    FHIR-R4 Mapping: MedicationRequest resource
    Key FHIR fields: status, intent, medication (codeableConcept), subject (patient),
    requester (practitioner), authoredOn, dosageInstruction, dispenseRequest
    """
    __tablename__ = "prescriptions"

    prescription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    medical_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_records.record_id"), index=True, nullable=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.patient_id"), index=True
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.doctor_id"), index=True
    )
    medications: Mapped[list[dict]] = mapped_column(JSON, default=list)
    status: Mapped[PrescriptionStatus] = mapped_column(
        Enum(PrescriptionStatus), default=PrescriptionStatus.DRAFT, index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    medical_record: Mapped[Optional["MedicalRecord"]] = relationship(back_populates="prescriptions")
    patient: Mapped["Patient"] = relationship(back_populates="prescriptions")
    doctor: Mapped["Doctor"] = relationship(back_populates="prescriptions")


# FHIR: Media / Binary (for voice notes)
class VoiceNote(Base):
    """Voice note recordings linked to appointments.
    
    FHIR-R4 Mapping: Media / Binary resource
    Key FHIR fields: identifier, basedOn (appointment), status, content (attachment), 
    createdDateTime, duration, operator (doctor)
    """
    __tablename__ = "voice_notes"

    voice_note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.appointment_id"), index=True
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.doctor_id"), index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.patient_id"), index=True
    )
    file_path: Mapped[str] = mapped_column(String(500), comment="Storage path for audio file")
    file_name: Mapped[str] = mapped_column(String(255), comment="Original file name")
    content_type: Mapped[str] = mapped_column(String(100), comment="MIME type (e.g., audio/webm)")
    file_size: Mapped[int] = mapped_column(comment="File size in bytes")
    duration_seconds: Mapped[int | None] = mapped_column(comment="Audio duration in seconds")
    transcription: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Transcribed text")
    transcription_status: Mapped[str] = mapped_column(
        String(50), default="pending", comment="pending, processing, completed, failed"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    appointment: Mapped["Appointment"] = relationship(back_populates="voice_notes")
    doctor: Mapped["Doctor"] = relationship(back_populates="voice_notes")
    patient: Mapped["Patient"] = relationship(back_populates="voice_notes")


# FHIR: AuditEvent
class AuditLog(Base):
    """Immutable audit trail for compliance and security monitoring.
    
    FHIR-R4 Mapping: AuditEvent resource
    Key FHIR fields: type (code), subtype, action, recorded (timestamp), outcome,
    agent (user), entity (resource), purposeOfUse
    """
    __tablename__ = "audit_logs"

    log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(100), index=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    outcome: Mapped[AuditOutcome] = mapped_column(Enum(AuditOutcome), default=AuditOutcome.SUCCESS)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)

    # Indexes for common query patterns
    __table_args__ = (
        Index("ix_audit_logs_user_timestamp", "user_id", "timestamp"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
        Index("ix_audit_logs_action_timestamp", "action", "timestamp"),
    )


# FHIR: Consent
class Consent(Base):
    """Patient consent for data access and sharing.
    
    FHIR-R4 Mapping: Consent resource
    Key FHIR fields: status, scope (code), patient, performer (provider),
    period (granted/revoked), policyRule, provision (data scope)
    """
    __tablename__ = "consents"

    consent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.patient_id"), index=True
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.doctor_id"), index=True
    )
    record_scope: Mapped[ConsentScope] = mapped_column(
        Enum(ConsentScope), default=ConsentScope.FULL_ACCESS
    )
    granted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient: Mapped["Patient"] = relationship(back_populates="consents")
    provider: Mapped["Doctor"] = relationship(back_populates="consents_given")

    # Index for active consent queries
    __table_args__ = (
        Index("ix_consents_patient_active", "patient_id", "revoked_at"),
        Index("ix_consents_provider_active", "provider_id", "revoked_at"),
    )


# FHIR: QuestionnaireResponse / ClinicalImpression (Intake Session)
class IntakeSession(Base):
    """Patient conversational intake session for structured symptom collection."""
    __tablename__ = "intake_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.patient_id"), index=True
    )
    status: Mapped[IntakeStatus] = mapped_column(
        Enum(IntakeStatus), default=IntakeStatus.IN_PROGRESS, index=True
    )
    messages: Mapped[list[dict]] = mapped_column(JSON, default=list)
    structured_symptoms: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(nullable=True)
    basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship(back_populates="intake_sessions")

    __table_args__ = (
        Index("ix_intake_sessions_patient_status", "patient_id", "status"),
    )


# FHIR: DiagnosticReport / DocumentReference (Patient Uploaded Medical Report)
class PatientReport(Base):
    """Medical document or laboratory/imaging report uploaded by or for a patient."""
    __tablename__ = "patient_reports"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.patient_id"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), index=True)
    report_type: Mapped[str] = mapped_column(String(100), default="other", index=True)  # lab, imaging, prescription, discharge, other
    file_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(1024))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[str] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient: Mapped["Patient"] = relationship(back_populates="reports")

    __table_args__ = (
        Index("ix_patient_reports_patient_created", "patient_id", "created_at"),
    )


# FHIR: MedicationStatement / CarePlan (Patient Medicine Reminder & Adherence Schedule)
class MedicineReminder(Base):
    """Patient scheduled medicine reminder and dosage schedule."""
    __tablename__ = "medicine_reminders"

    reminder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.patient_id"), index=True
    )
    medication_name: Mapped[str] = mapped_column(String(255), index=True)
    dosage: Mapped[str] = mapped_column(String(100))  # e.g., "500mg", "1 tablet"
    frequency: Mapped[str] = mapped_column(String(100))  # e.g., "Once daily", "Twice daily"
    times_of_day: Mapped[list[str]] = mapped_column(JSON, default=list)  # e.g., ["08:00", "20:00"]
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)  # e.g., "Take after meals with water"
    start_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient: Mapped["Patient"] = relationship(back_populates="medicine_reminders")

    __table_args__ = (
        Index("ix_medicine_reminders_patient_active", "patient_id", "is_active"),
    )


# FHIR: Location / Encounter (Inpatient Bed and Clinical Ward Monitoring)
class InpatientBed(Base):
    """Hospital inpatient bed occupancy and bedside clinical vitals tracking."""
    __tablename__ = "inpatient_beds"

    bed_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bed_number: Mapped[str] = mapped_column(String(50), index=True)
    ward: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(50), default="occupied")  # occupied, vacant, maintenance
    clinical_status: Mapped[str] = mapped_column(String(50), default="Stable")  # Stable, Attention, Critical

    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.patient_id"), nullable=True, index=True
    )
    patient_name: Mapped[str] = mapped_column(String(255))
    uhid: Mapped[str] = mapped_column(String(100))
    age: Mapped[int] = mapped_column(Integer, default=45)
    gender: Mapped[str] = mapped_column(String(50), default="Unknown")
    admitted_for: Mapped[str] = mapped_column(Text)
    attending_physician: Mapped[str] = mapped_column(String(255))
    admitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    admit_day: Mapped[int] = mapped_column(Integer, default=1)
    diet: Mapped[str] = mapped_column(String(100), default="Regular Diet")
    allergies: Mapped[list[str]] = mapped_column(JSON, default=list)
    code_status: Mapped[str] = mapped_column(String(50), default="Full Code")
    isolation_precautions: Mapped[str | None] = mapped_column(String(100), nullable=True)

    next_medication: Mapped[str] = mapped_column(String(255), default="Standard IV Saline")
    medication_due: Mapped[str] = mapped_column(String(100), default="16:00 Dose Round")

    # Cached latest telemetry vitals
    bp: Mapped[str] = mapped_column(String(50), default="120/80")
    systolic: Mapped[int] = mapped_column(Integer, default=120)
    diastolic: Mapped[int] = mapped_column(Integer, default=80)
    pulse: Mapped[int] = mapped_column(Integer, default=72)
    spo2: Mapped[int] = mapped_column(Integer, default=98)
    temp: Mapped[float] = mapped_column(Float, default=98.6)
    respiratory_rate: Mapped[int] = mapped_column(Integer, default=16)
    pain_score: Mapped[int] = mapped_column(Integer, default=0)
    vitals_last_checked: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.organization_id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    vitals_logs: Mapped[list["BedVitalsLog"]] = relationship(
        back_populates="bed", cascade="all, delete-orphan", order_by="desc(BedVitalsLog.recorded_at)"
    )
    nurse_tasks: Mapped[list["NurseTask"]] = relationship(
        back_populates="bed", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_inpatient_beds_ward_status", "ward", "status"),
    )


# FHIR: Observation (Bedside Telemetry and Vital Signs Log)
class BedVitalsLog(Base):
    """Historical bedside vitals telemetry log with critical range flags."""
    __tablename__ = "bed_vitals_logs"

    log_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bed_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inpatient_beds.bed_id"), index=True
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.patient_id"), nullable=True, index=True
    )
    bp: Mapped[str] = mapped_column(String(50))
    systolic: Mapped[int] = mapped_column(Integer)
    diastolic: Mapped[int] = mapped_column(Integer)
    pulse: Mapped[int] = mapped_column(Integer)
    spo2: Mapped[int] = mapped_column(Integer)
    temp: Mapped[float] = mapped_column(Float)
    respiratory_rate: Mapped[int] = mapped_column(Integer, default=16)
    pain_score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="stable")  # stable, attention, critical
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[str] = mapped_column(String(255), default="Staff Nurse")
    recorded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    bed: Mapped["InpatientBed"] = relationship(back_populates="vitals_logs")

    __table_args__ = (
        Index("ix_bed_vitals_logs_bed_recorded", "bed_id", "recorded_at"),
    )


# FHIR: Task / MedicationAdministration (Nurse Shift Medication & Ward Round Tasks)
class NurseTask(Base):
    """Shift medication administration and ward round duties."""
    __tablename__ = "nurse_tasks"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    bed_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("inpatient_beds.bed_id"), nullable=True, index=True
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.patient_id"), nullable=True, index=True
    )
    patient_name: Mapped[str] = mapped_column(String(255))
    bed_number: Mapped[str] = mapped_column(String(50))
    ward: Mapped[str] = mapped_column(String(100))
    task_type: Mapped[str] = mapped_column(String(50), default="medication", index=True)  # medication, ward_round

    # Medication-specific
    medication: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dose: Mapped[str | None] = mapped_column(String(100), nullable=True)
    route: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Oral, IV, Subcutaneous, Inhalation
    prescribed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Ward round-specific
    round_task: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)  # positioning, wound, iv, catheter, nutrition, assessment

    # Common fields
    priority: Mapped[str] = mapped_column(String(50), default="routine")  # stat, urgent, routine
    due_time: Mapped[str] = mapped_column(String(100))
    is_overdue: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)  # pending, administered, delayed, refused, done
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    administered_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    administered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.organization_id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bed: Mapped["InpatientBed | None"] = relationship(back_populates="nurse_tasks")

    __table_args__ = (
        Index("ix_nurse_tasks_status_due", "status", "due_time"),
    )
