"""Initial migration: core schema with FHIR mapping notes

Revision ID: 51582e1d7ad0
Revises: 
Create Date: 2026-08-19 10:52:39.076997

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '51582e1d7ad0'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create all 7 core tables with FHIR mapping notes."""
    
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

    # Create enum types
    appointment_status = postgresql.ENUM(
        'scheduled', 'completed', 'cancelled', 'no_show',
        name='appointment_status', create_type=True
    )
    appointment_status.create(op.get_bind())

    medical_record_status = postgresql.ENUM(
        'draft', 'finalized', 'amended',
        name='medical_record_status', create_type=True
    )
    medical_record_status.create(op.get_bind())

    prescription_status = postgresql.ENUM(
        'draft', 'finalized', 'cancelled',
        name='prescription_status', create_type=True
    )
    prescription_status.create(op.get_bind())

    consent_scope = postgresql.ENUM(
        'full_access', 'limited', 'emergency_only',
        name='consent_scope', create_type=True
    )
    consent_scope.create(op.get_bind())

    audit_outcome = postgresql.ENUM(
        'success', 'failure', 'partial',
        name='audit_outcome', create_type=True
    )
    audit_outcome.create(op.get_bind())

    # -----------------------------------------------------------------------------
    # patients → FHIR Patient
    # Key FHIR fields: identifier (ABHA), name, gender, birthDate, telecom, address, contact
    # -----------------------------------------------------------------------------
    op.create_table(
        'patients',
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('abha_address', sa.String(255), unique=True, nullable=True, index=True),
        sa.Column('full_name', sa.String(255), nullable=False, index=True),
        sa.Column('date_of_birth', sa.Date, nullable=False),
        sa.Column('gender', sa.String(50), nullable=False),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('address', sa.Text, nullable=True),
        sa.Column('emergency_contact_name', sa.String(255), nullable=True),
        sa.Column('emergency_contact_phone', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # -----------------------------------------------------------------------------
    # doctors → FHIR Practitioner + PractitionerRole
    # Key FHIR fields: identifier (license), name, qualification, organization, specialty
    # -----------------------------------------------------------------------------
    op.create_table(
        'doctors',
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), unique=True, nullable=False, index=True),
        sa.Column('specialty', sa.String(100), nullable=False, index=True),
        sa.Column('license_number', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('hospital_affiliation', sa.String(255), nullable=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('full_name', sa.String(255), nullable=False, index=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # -----------------------------------------------------------------------------
    # appointments → FHIR Appointment
    # Key FHIR fields: status, serviceType, specialty, appointmentType, start/end, participant
    # -----------------------------------------------------------------------------
    op.create_table(
        'appointments',
        sa.Column('appointment_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.patient_id'), nullable=False, index=True),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doctors.doctor_id'), nullable=False, index=True),
        sa.Column('scheduled_at', sa.DateTime, nullable=False, index=True),
        sa.Column('duration_minutes', sa.Integer, nullable=False, server_default='30'),
        sa.Column('status', appointment_status, nullable=False, server_default='scheduled', index=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # -----------------------------------------------------------------------------
    # medical_records → FHIR Composition / ClinicalImpression / DiagnosticReport
    # Key FHIR fields: status, type, subject, author, encounter, date, section, code
    # -----------------------------------------------------------------------------
    op.create_table(
        'medical_records',
        sa.Column('record_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.patient_id'), nullable=False, index=True),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doctors.doctor_id'), nullable=False, index=True),
        sa.Column('appointment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('appointments.appointment_id'), nullable=True, index=True),
        sa.Column('content', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('status', medical_record_status, nullable=False, server_default='draft', index=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('finalized_at', sa.DateTime, nullable=True),
    )

    # -----------------------------------------------------------------------------
    # prescriptions → FHIR MedicationRequest
    # Key FHIR fields: status, intent, medication, subject, requester, authoredOn, dosageInstruction
    # -----------------------------------------------------------------------------
    op.create_table(
        'prescriptions',
        sa.Column('prescription_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('medical_record_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('medical_records.record_id'), nullable=False, index=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.patient_id'), nullable=False, index=True),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doctors.doctor_id'), nullable=False, index=True),
        sa.Column('medications', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('status', prescription_status, nullable=False, server_default='draft', index=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('finalized_at', sa.DateTime, nullable=True),
    )

    # -----------------------------------------------------------------------------
    # audit_logs → FHIR AuditEvent
    # Key FHIR fields: type, subtype, action, recorded, outcome, agent, entity, purposeOfUse
    # -----------------------------------------------------------------------------
    op.create_table(
        'audit_logs',
        sa.Column('log_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('action', sa.String(100), nullable=False, index=True),
        sa.Column('resource_type', sa.String(100), nullable=False, index=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('timestamp', sa.DateTime, nullable=False, server_default=sa.func.now(), index=True),
        sa.Column('outcome', audit_outcome, nullable=False, server_default='success'),
        sa.Column('details', postgresql.JSONB, nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text, nullable=True),
    )
    
    # Additional indexes for audit_logs
    op.create_index('ix_audit_logs_user_timestamp', 'audit_logs', ['user_id', 'timestamp'])
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])
    op.create_index('ix_audit_logs_action_timestamp', 'audit_logs', ['action', 'timestamp'])

    # -----------------------------------------------------------------------------
    # consents → FHIR Consent
    # Key FHIR fields: status, scope, patient, performer, period, policyRule, provision
    # -----------------------------------------------------------------------------
    op.create_table(
        'consents',
        sa.Column('consent_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.patient_id'), nullable=False, index=True),
        sa.Column('provider_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('doctors.doctor_id'), nullable=False, index=True),
        sa.Column('record_scope', consent_scope, nullable=False, server_default='full_access'),
        sa.Column('granted_at', sa.DateTime, nullable=False, server_default=sa.func.now(), index=True),
        sa.Column('revoked_at', sa.DateTime, nullable=True, index=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    
    # Additional indexes for consents
    op.create_index('ix_consents_patient_active', 'consents', ['patient_id', 'revoked_at'])
    op.create_index('ix_consents_provider_active', 'consents', ['provider_id', 'revoked_at'])


def downgrade() -> None:
    """Downgrade schema - drop all tables and enum types."""
    
    # Drop indexes first
    op.drop_index('ix_consents_provider_active', table_name='consents')
    op.drop_index('ix_consents_patient_active', table_name='consents')
    op.drop_index('ix_audit_logs_action_timestamp', table_name='audit_logs')
    op.drop_index('ix_audit_logs_resource', table_name='audit_logs')
    op.drop_index('ix_audit_logs_user_timestamp', table_name='audit_logs')
    
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('consents')
    op.drop_table('audit_logs')
    op.drop_table('prescriptions')
    op.drop_table('medical_records')
    op.drop_table('appointments')
    op.drop_table('doctors')
    op.drop_table('patients')
    
    # Drop enum types
    audit_outcome = postgresql.ENUM(name='audit_outcome')
    audit_outcome.drop(op.get_bind())
    
    consent_scope = postgresql.ENUM(name='consent_scope')
    consent_scope.drop(op.get_bind())
    
    prescription_status = postgresql.ENUM(name='prescription_status')
    prescription_status.drop(op.get_bind())
    
    medical_record_status = postgresql.ENUM(name='medical_record_status')
    medical_record_status.drop(op.get_bind())
    
    appointment_status = postgresql.ENUM(name='appointment_status')
    appointment_status.drop(op.get_bind())
