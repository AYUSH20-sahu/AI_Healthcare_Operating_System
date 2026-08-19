"""
AI-HOS Database Models

Core schema with FHIR-R4 mapping notes for healthcare interoperability.
All tables use UUID primary keys for distributed system compatibility.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from enum import Enum as PyEnum

from sqlalchemy import (
    String, Text, DateTime, Date, Enum, ForeignKey, Index, JSON, Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class UserRole(PyEnum):
    """User roles in the system."""
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"
    NURSE = "nurse"
    RECEPTIONIST = "receptionist"


class AppointmentStatus(PyEnum):
    """Appointment status values."""
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class MedicalRecordStatus(PyEnum):
    """Medical record status values."""
    DRAFT = "draft"
    FINALIZED = "finalized"
    AMENDED = "amended"


class PrescriptionStatus(PyEnum):
    """Prescription status values."""
    DRAFT = "draft"
    FINALIZED = "finalized"
    CANCELLED = "cancelled"


class ConsentScope(PyEnum):
    """Consent record scope values."""
    FULL_ACCESS = "full_access"
    LIMITED = "limited"
    EMERGENCY_ONLY = "emergency_only"


class AuditOutcome(PyEnum):
    """Audit log outcome values."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


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
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda x: [e.value for e in x]), default=UserRole.PATIENT, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient_profile: Mapped[Optional["Patient"]] = relationship(back_populates="user", uselist=False)
    doctor_profile: Mapped[Optional["Doctor"]] = relationship(back_populates="user", uselist=False)


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
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), unique=True, index=True
    )
    abha_address: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    date_of_birth: Mapped[Date] = mapped_column(Date)
    gender: Mapped[str] = mapped_column(String(50))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    address: Mapped[Optional[str]] = mapped_column(Text)
    emergency_contact_name: Mapped[Optional[str]] = mapped_column(String(255))
    emergency_contact_phone: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped[Optional["User"]] = relationship(back_populates="patient_profile")
    appointments: Mapped[List["Appointment"]] = relationship(back_populates="patient")
    medical_records: Mapped[List["MedicalRecord"]] = relationship(back_populates="patient")
    prescriptions: Mapped[List["Prescription"]] = relationship(back_populates="patient")
    consents: Mapped[List["Consent"]] = relationship(back_populates="patient")


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
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), unique=True, index=True
    )
    specialty: Mapped[str] = mapped_column(String(100), index=True)
    license_number: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hospital_affiliation: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped[Optional["User"]] = relationship(back_populates="doctor_profile")
    appointments: Mapped[List["Appointment"]] = relationship(back_populates="doctor")
    medical_records: Mapped[List["MedicalRecord"]] = relationship(back_populates="doctor")
    prescriptions: Mapped[List["Prescription"]] = relationship(back_populates="doctor")
    consents_given: Mapped[List["Consent"]] = relationship(back_populates="provider", foreign_keys="Consent.provider_id")


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
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    patient: Mapped["Patient"] = relationship(back_populates="appointments")
    doctor: Mapped["Doctor"] = relationship(back_populates="appointments")
    medical_records: Mapped[List["MedicalRecord"]] = relationship(back_populates="appointment")


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
    appointment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("appointments.appointment_id"), index=True
    )
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[MedicalRecordStatus] = mapped_column(
        Enum(MedicalRecordStatus), default=MedicalRecordStatus.DRAFT, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    patient: Mapped["Patient"] = relationship(back_populates="medical_records")
    doctor: Mapped["Doctor"] = relationship(back_populates="medical_records")
    appointment: Mapped[Optional["Appointment"]] = relationship(back_populates="medical_records")
    prescriptions: Mapped[List["Prescription"]] = relationship(back_populates="medical_record")


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
    medical_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("medical_records.record_id"), index=True
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.patient_id"), index=True
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.doctor_id"), index=True
    )
    medications: Mapped[List[dict]] = mapped_column(JSON, default=list)
    status: Mapped[PrescriptionStatus] = mapped_column(
        Enum(PrescriptionStatus), default=PrescriptionStatus.DRAFT, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    medical_record: Mapped["MedicalRecord"] = relationship(back_populates="prescriptions")
    patient: Mapped["Patient"] = relationship(back_populates="prescriptions")
    doctor: Mapped["Doctor"] = relationship(back_populates="prescriptions")


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
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(100), index=True)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    outcome: Mapped[AuditOutcome] = mapped_column(Enum(AuditOutcome), default=AuditOutcome.SUCCESS)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(Text)

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
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
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