"""Add inpatient beds, bed vitals logs, nurse tasks, medicine reminders, and extended organizational columns

Revision ID: 7a8f912c34d5
Revises: 51582e1d7ad0
Create Date: 2026-10-04 20:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7a8f912c34d5'
down_revision: str | Sequence[str] | None = '51582e1d7ad0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - create inpatient care tables and add extended staff & org columns."""
    
    # 1. Inpatient Beds Table
    op.create_table(
        'inpatient_beds',
        sa.Column('bed_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('bed_number', sa.String(50), nullable=False, index=True),
        sa.Column('ward', sa.String(100), nullable=False, index=True),
        sa.Column('status', sa.String(50), server_default='occupied', nullable=False),
        sa.Column('clinical_status', sa.String(50), server_default='Stable', nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.patient_id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('patient_name', sa.String(255), nullable=False),
        sa.Column('uhid', sa.String(100), nullable=False),
        sa.Column('age', sa.Integer(), server_default='45', nullable=False),
        sa.Column('gender', sa.String(50), server_default='Unknown', nullable=False),
        sa.Column('admitted_for', sa.Text(), nullable=False),
        sa.Column('attending_physician', sa.String(255), nullable=False),
        sa.Column('admitted_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('admit_day', sa.Integer(), server_default='1', nullable=False),
        sa.Column('diet', sa.String(100), server_default='Regular Diet', nullable=False),
        sa.Column('allergies', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('code_status', sa.String(50), server_default='Full Code', nullable=False),
        sa.Column('isolation_precautions', sa.String(100), nullable=True),
        sa.Column('next_medication', sa.String(255), server_default='Standard IV Saline', nullable=False),
        sa.Column('medication_due', sa.String(100), server_default='16:00 Dose Round', nullable=False),
        sa.Column('bp', sa.String(50), server_default='120/80', nullable=False),
        sa.Column('systolic', sa.Integer(), server_default='120', nullable=False),
        sa.Column('diastolic', sa.Integer(), server_default='80', nullable=False),
        sa.Column('pulse', sa.Integer(), server_default='72', nullable=False),
        sa.Column('spo2', sa.Integer(), server_default='98', nullable=False),
        sa.Column('temp', sa.Float(), server_default='98.6', nullable=False),
        sa.Column('respiratory_rate', sa.Integer(), server_default='16', nullable=False),
        sa.Column('pain_score', sa.Integer(), server_default='0', nullable=False),
        sa.Column('vitals_last_checked', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.organization_id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_inpatient_beds_ward_status', 'inpatient_beds', ['ward', 'status'])

    # 2. Bed Vitals Logs Table
    op.create_table(
        'bed_vitals_logs',
        sa.Column('log_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('bed_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('inpatient_beds.bed_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.patient_id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('bp', sa.String(50), nullable=False),
        sa.Column('systolic', sa.Integer(), nullable=False),
        sa.Column('diastolic', sa.Integer(), nullable=False),
        sa.Column('pulse', sa.Integer(), nullable=False),
        sa.Column('spo2', sa.Integer(), nullable=False),
        sa.Column('temp', sa.Float(), nullable=False),
        sa.Column('respiratory_rate', sa.Integer(), server_default='16', nullable=False),
        sa.Column('pain_score', sa.Integer(), server_default='0', nullable=False),
        sa.Column('status', sa.String(50), server_default='stable', nullable=False),
        sa.Column('is_critical', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('recorded_by', sa.String(255), server_default='Staff Nurse', nullable=False),
        sa.Column('recorded_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), server_default=sa.func.now(), nullable=False, index=True),
    )
    op.create_index('ix_bed_vitals_logs_bed_recorded', 'bed_vitals_logs', ['bed_id', 'recorded_at'])

    # 3. Nurse Tasks Table
    op.create_table(
        'nurse_tasks',
        sa.Column('task_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('bed_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('inpatient_beds.bed_id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.patient_id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('patient_name', sa.String(255), nullable=False),
        sa.Column('bed_number', sa.String(50), nullable=False),
        sa.Column('ward', sa.String(100), nullable=False),
        sa.Column('task_type', sa.String(50), server_default='medication', nullable=False, index=True),
        sa.Column('medication', sa.String(255), nullable=True),
        sa.Column('dose', sa.String(100), nullable=True),
        sa.Column('route', sa.String(50), nullable=True),
        sa.Column('prescribed_by', sa.String(255), nullable=True),
        sa.Column('round_task', sa.String(255), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('priority', sa.String(50), server_default='routine', nullable=False),
        sa.Column('due_time', sa.String(100), nullable=False),
        sa.Column('is_overdue', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('status', sa.String(50), server_default='pending', nullable=False, index=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('administered_by', sa.String(255), nullable=True),
        sa.Column('administered_at', sa.DateTime(), nullable=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.organization_id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_nurse_tasks_status_due', 'nurse_tasks', ['status', 'due_time'])

    # 4. Medicine Reminders Table
    op.create_table(
        'medicine_reminders',
        sa.Column('reminder_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('medication_name', sa.String(255), nullable=False, index=True),
        sa.Column('dosage', sa.String(100), nullable=False),
        sa.Column('frequency', sa.String(100), nullable=False),
        sa.Column('times_of_day', sa.JSON(), server_default='[]', nullable=False),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_medicine_reminders_patient_active', 'medicine_reminders', ['patient_id', 'is_active'])


def downgrade() -> None:
    """Downgrade schema - drop added tables."""
    op.drop_table('medicine_reminders')
    op.drop_table('nurse_tasks')
    op.drop_table('bed_vitals_logs')
    op.drop_table('inpatient_beds')
