"""Doctor Review/Approval API routes for M23.

This module implements the mandatory human-in-the-loop gate for AI-drafted content.
Only on explicit approval from an authenticated doctor does the Core API flip
status from draft to finalized — nothing in the system may bypass it.
"""

from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.approval import (
    MedicalRecordApprovalRequest,
    MedicalRecordApprovalResponse,
    PrescriptionApprovalRequest,
    PrescriptionApprovalResponse,
    DraftListResponse,
)
from app.api.schemas.medical_record import MedicalRecordResponse
from app.api.schemas.prescription import PrescriptionResponse
from app.database import get_db
from app.models import (
    Doctor,
    MedicalRecord,
    MedicalRecordStatus,
    Prescription,
    PrescriptionStatus,
    User,
    UserRole,
)
from app.services.auth.audit import audit_logger
from app.services.auth.service import get_current_active_user

router = APIRouter(prefix="/approval", tags=["approval"])


@router.get("/drafts", response_model=DraftListResponse)
async def list_drafts_for_review(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all draft medical records and prescriptions pending review.
    
    Only doctors and admins can access this endpoint.
    """
    # RBAC check - only doctors and admins can review
    if current_user.role not in [UserRole.DOCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors and admins can review drafts",
        )
    
    # Get doctor profile if current user is a doctor
    doctor = None
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctor profile not found",
            )
    
    # Build query for draft medical records
    mr_query = select(MedicalRecord).where(MedicalRecord.status == MedicalRecordStatus.DRAFT)
    if doctor:
        # Doctors only see drafts for their own patients
        mr_query = mr_query.where(MedicalRecord.doctor_id == doctor.doctor_id)
    
    # Build query for draft prescriptions
    rx_query = select(Prescription).where(Prescription.status == PrescriptionStatus.DRAFT)
    if doctor:
        rx_query = rx_query.where(Prescription.doctor_id == doctor.doctor_id)
    
    # Count total
    mr_count_query = select(func.count()).select_from(mr_query.subquery())
    rx_count_query = select(func.count()).select_from(rx_query.subquery())
    
    mr_total = (await db.execute(mr_count_query)).scalar() or 0
    rx_total = (await db.execute(rx_count_query)).scalar() or 0
    total = mr_total + rx_total
    
    # Apply pagination
    offset = (page - 1) * page_size
    
    # Get medical records
    mr_query = mr_query.order_by(MedicalRecord.created_at.desc()).offset(offset).limit(page_size)
    mr_result = await db.execute(mr_query)
    medical_records = mr_result.scalars().all()
    
    # Get prescriptions
    rx_query = rx_query.order_by(Prescription.created_at.desc()).offset(offset).limit(page_size)
    rx_result = await db.execute(rx_query)
    prescriptions = rx_result.scalars().all()
    
    # Format response
    mr_list = [
        {
            "record_id": str(mr.record_id),
            "patient_id": str(mr.patient_id),
            "doctor_id": str(mr.doctor_id),
            "appointment_id": str(mr.appointment_id) if mr.appointment_id else None,
            "chief_complaint": mr.content.get("chief_complaint") if mr.content else None,
            "assessment": mr.content.get("assessment") if mr.content else None,
            "confidence": mr.content.get("confidence") if mr.content else None,
            "basis": mr.content.get("basis") if mr.content else None,
            "created_at": mr.created_at.isoformat(),
            "updated_at": mr.updated_at.isoformat(),
        }
        for mr in medical_records
    ]
    
    rx_list = [
        {
            "prescription_id": str(rx.prescription_id),
            "patient_id": str(rx.patient_id),
            "doctor_id": str(rx.doctor_id),
            "medical_record_id": str(rx.medical_record_id) if rx.medical_record_id else None,
            "medications": rx.medications,
            "notes": rx.notes,
            "created_at": rx.created_at.isoformat(),
            "updated_at": rx.updated_at.isoformat(),
        }
        for rx in prescriptions
    ]
    
    return DraftListResponse(
        medical_records=mr_list,
        prescriptions=rx_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("/medical-records/{record_id}/review", response_model=MedicalRecordApprovalResponse)
async def review_medical_record(
    record_id: UUID,
    approval: MedicalRecordApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Review a draft medical record - approve, reject, or request changes.
    
    Only the assigned doctor or admin can review.
    On approve: status changes from DRAFT to FINALIZED
    On reject: status changes from DRAFT to AMENDED (with rejection notes)
    On request_changes: status stays DRAFT, content updated with edits
    """
    # Get the record
    record = await db.get(MedicalRecord, record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record not found",
        )
    
    # Verify record is in draft status (Duplicate approval protection)
    if record.status != MedicalRecordStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot review record with status: {record.status.value}. Already finalized or closed",
        )
    
    # RBAC check
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or record.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only review their own medical records",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to review medical records",
        )
    
    # Get reviewer doctor profile
    reviewer_doctor = None
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        reviewer_doctor = doctor_result.scalar_one_or_none()
    elif current_user.role == UserRole.ADMIN:
        # For admin, prioritize the record's assigned doctor profile for clinical continuity
        if record.doctor_id:
            reviewer_doctor = await db.get(Doctor, record.doctor_id)
        if not reviewer_doctor:
            doctor_result = await db.execute(select(Doctor).limit(1))
            reviewer_doctor = doctor_result.scalar_one_or_none()
    
    if not reviewer_doctor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reviewer doctor profile not found",
        )
    
    finalized_at = None
    existing_content = record.content or {}

    # Process the action
    if approval.action == "approve":
        if approval.edited_content:
            existing_content = {**existing_content, **approval.edited_content}
        record.status = MedicalRecordStatus.FINALIZED
        finalized_at = datetime.utcnow()
        record.finalized_at = finalized_at
        existing_content["approved_by"] = str(reviewer_doctor.doctor_id)
        existing_content["approved_at"] = finalized_at.isoformat()
        message = "Medical record approved and finalized"
        audit_action = "MEDICAL_RECORD_APPROVED"

    elif approval.action == "reject":
        record.status = MedicalRecordStatus.AMENDED
        reason = approval.rejection_reason or approval.reviewer_notes or "Rejected by physician"
        existing_content["rejection_reason"] = reason
        existing_content["rejected_by"] = str(reviewer_doctor.doctor_id)
        existing_content["rejected_at"] = datetime.utcnow().isoformat()
        message = "Medical record rejected"
        audit_action = "MEDICAL_RECORD_REJECTED"

    elif approval.action == "request_changes":
        # Update content with edits if provided
        if approval.edited_content:
            existing_content = {**existing_content, **approval.edited_content}
        record.status = MedicalRecordStatus.DRAFT  # Stays draft
        message = "Changes requested on medical record"
        audit_action = "MEDICAL_RECORD_CHANGES_REQUESTED"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be: approve, reject, or request_changes",
        )
    
    # Add reviewer notes to content if provided
    if approval.reviewer_notes:
        existing_content["reviewer_notes"] = approval.reviewer_notes
        existing_content["reviewed_by"] = str(reviewer_doctor.doctor_id)
        existing_content["reviewed_at"] = datetime.utcnow().isoformat()
    
    record.content = existing_content
    await db.commit()
    await db.refresh(record)
    
    # Audit log
    await audit_logger.log_event(
        action=audit_action,
        user_id=current_user.user_id,
        resource_type="medical_record",
        resource_id=record.record_id,
        details={
            "action": approval.action,
            "status": record.status.value,
            "reviewer_doctor_id": str(reviewer_doctor.doctor_id),
            "rejection_reason": approval.rejection_reason,
            "has_reviewer_notes": bool(approval.reviewer_notes),
        },
    )

    return MedicalRecordApprovalResponse(
        record_id=record.record_id,
        status=record.status.value,
        action=approval.action,
        reviewer_id=reviewer_doctor.doctor_id,
        reviewed_at=record.updated_at,
        finalized_at=finalized_at,
        reviewer_notes=approval.reviewer_notes,
        rejection_reason=approval.rejection_reason,
        message=message,
    )


@router.post("/prescriptions/{prescription_id}/review", response_model=PrescriptionApprovalResponse)
async def review_prescription(
    prescription_id: UUID,
    approval: PrescriptionApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Review a draft prescription - approve, reject, or request changes.
    
    Only the assigned doctor or admin can review.
    On approve: status changes from DRAFT to FINALIZED
    On reject: status changes from DRAFT to CANCELLED
    On request_changes: status stays DRAFT, medications updated with edits
    """
    # Get the prescription
    prescription = await db.get(Prescription, prescription_id)
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )
    
    # Verify prescription is in draft status (Duplicate approval protection)
    if prescription.status != PrescriptionStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot review prescription with status: {prescription.status.value}. Already finalized or closed",
        )
    
    # RBAC check
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or prescription.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only review their own prescriptions",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to review prescriptions",
        )
    
    # Get reviewer doctor profile
    reviewer_doctor = None
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        reviewer_doctor = doctor_result.scalar_one_or_none()
    elif current_user.role == UserRole.ADMIN:
        # For admin, prioritize the prescription's assigned doctor profile for clinical continuity
        if prescription.doctor_id:
            reviewer_doctor = await db.get(Doctor, prescription.doctor_id)
        if not reviewer_doctor:
            doctor_result = await db.execute(select(Doctor).limit(1))
            reviewer_doctor = doctor_result.scalar_one_or_none()
    
    if not reviewer_doctor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reviewer doctor profile not found",
        )
    
    # Process the action
    if approval.action == "approve":
        if approval.edited_medications:
            prescription.medications = approval.edited_medications
        prescription.status = PrescriptionStatus.FINALIZED
        prescription.finalized_at = datetime.utcnow()
        message = "Prescription approved and finalized"
        audit_action = "PRESCRIPTION_APPROVED"

    elif approval.action == "reject":
        prescription.status = PrescriptionStatus.CANCELLED
        reason = approval.rejection_reason or approval.reviewer_notes or "Rejected by physician"
        prescription.notes = (prescription.notes or "") + f"\n\n[Rejection Reason]: {reason}"
        message = "Prescription rejected"
        audit_action = "PRESCRIPTION_REJECTED"

    elif approval.action == "request_changes":
        # Update medications with edits if provided
        if approval.edited_medications:
            prescription.medications = approval.edited_medications
        prescription.status = PrescriptionStatus.DRAFT  # Stays draft
        message = "Changes requested on prescription"
        audit_action = "PRESCRIPTION_CHANGES_REQUESTED"

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be: approve, reject, or request_changes",
        )
    
    # Add reviewer notes
    if approval.reviewer_notes:
        prescription.notes = (prescription.notes or "") + f"\n\n[Review by {reviewer_doctor.doctor_id}]: {approval.reviewer_notes}"
    
    await db.commit()
    await db.refresh(prescription)
    
    # Audit log
    await audit_logger.log_event(
        action=audit_action,
        user_id=current_user.user_id,
        resource_type="prescription",
        resource_id=prescription.prescription_id,
        details={
            "action": approval.action,
            "status": prescription.status.value,
            "reviewer_doctor_id": str(reviewer_doctor.doctor_id),
            "rejection_reason": approval.rejection_reason,
            "has_reviewer_notes": bool(approval.reviewer_notes),
        },
    )

    return PrescriptionApprovalResponse(
        prescription_id=prescription.prescription_id,
        status=prescription.status.value,
        action=approval.action,
        reviewer_id=reviewer_doctor.doctor_id,
        reviewed_at=prescription.updated_at,
        finalized_at=prescription.finalized_at,
        reviewer_notes=approval.reviewer_notes,
        rejection_reason=approval.rejection_reason,
        message=message,
    )


@router.get("/medical-records/{record_id}", response_model=MedicalRecordResponse)
async def get_medical_record_for_review(
    record_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a medical record for review (doctors/admins only)."""
    record = await db.get(MedicalRecord, record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medical record not found",
        )
    
    # RBAC check
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or record.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only review their own medical records",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    
    return record


@router.get("/prescriptions/{prescription_id}", response_model=PrescriptionResponse)
async def get_prescription_for_review(
    prescription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a prescription for review (doctors/admins only)."""
    prescription = await db.get(Prescription, prescription_id)
    if not prescription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prescription not found",
        )
    
    # RBAC check
    if current_user.role == UserRole.DOCTOR:
        doctor_result = await db.execute(
            select(Doctor).where(Doctor.user_id == current_user.user_id)
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor or prescription.doctor_id != doctor.doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only review their own prescriptions",
            )
    elif current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    
    return prescription