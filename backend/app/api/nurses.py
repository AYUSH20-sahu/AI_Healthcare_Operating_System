"""Nursing department and staff management API routes."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import (
    AuditLog,
    AuditOutcome,
    BedVitalsLog,
    InpatientBed,
    NurseTask,
    User,
    UserRole,
)
from app.services.auth.rbac import require_head_nurse, require_medical_staff
from app.services.auth.service import (
    check_credentials_available,
    get_password_hash,
    normalize_phone,
)

logger = logging.getLogger("ai_hos.nurses")

router = APIRouter(prefix="/nurses", tags=["nurses"])


class JuniorNurseProvisionRequest(BaseModel):
    """Schema for Head Nurse to provision junior nursing staff within their department."""
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    license_number: str = Field(..., description="Nursing Council Registration Number")
    qualifications: str = Field(..., description="E.g. B.Sc Nursing, GNM, Critical Care Diploma")
    designation: str = Field(default="Staff Nurse", description="E.g. Staff Nurse, ICU Nurse, Ward Incharge")
    experience_years: int = 1
    room_number: Optional[str] = Field(default=None, description="Assigned Ward or Nursing Station")
    shift: str = Field(default="Morning (07:00 - 15:00)")
    phone: Optional[str] = None


class NurseResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str
    phone: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    qualifications: Optional[str] = None
    experience_years: Optional[int] = None
    room_number: Optional[str] = None
    shift: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


@router.get("/department-team")
async def get_department_team(
    db: AsyncSession = Depends(get_db),
    current_head: User = Depends(require_head_nurse),
):
    """Fetch nursing team members belonging strictly to the Head Nurse's department/ward."""
    dept = current_head.department or "General Ward"
    query = select(User).where(
        User.role.in_([UserRole.NURSE, UserRole.HEAD_NURSE]),
        (User.department == dept) | (User.supervisor_id == current_head.user_id),
    )
    if current_head.organization_id:
        query = query.where(User.organization_id == current_head.organization_id)

    result = await db.execute(query.order_by(User.role.desc(), User.full_name.asc()))
    nurses = result.scalars().all()

    return {
        "department": dept,
        "head_nurse": {
            "name": current_head.full_name,
            "email": current_head.email,
            "designation": current_head.designation,
        },
        "total_members": len(nurses),
        "team": [NurseResponse.model_validate(n) for n in nurses],
    }


@router.post("/junior-staff", status_code=status.HTTP_201_CREATED)
async def provision_junior_staff(
    req: JuniorNurseProvisionRequest,
    db: AsyncSession = Depends(get_db),
    current_head: User = Depends(require_head_nurse),
):
    """Head Nurse provisions a junior staff nurse strictly scoped to their department."""
    dept = current_head.department or "General Ward"
    clean_phone = normalize_phone(req.phone) if req.phone else None

    # 1. Universal credential uniqueness check across all account types
    await check_credentials_available(db, email=req.email, phone=clean_phone)

    # 2. Create User account locked to Head Nurse's department and supervisor
    hashed_pwd = get_password_hash(req.password)
    new_user = User(
        email=req.email,
        phone=clean_phone,
        hashed_password=hashed_pwd,
        full_name=req.full_name,
        role=UserRole.NURSE,
        organization_id=current_head.organization_id,
        department=dept,
        designation=req.designation,
        qualifications=req.qualifications,
        experience_years=req.experience_years,
        room_number=req.room_number,
        shift=req.shift,
        supervisor_id=current_head.user_id,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    # 3. Audit Logging
    audit_entry = AuditLog(
        user_id=current_head.user_id,
        action="HEAD_NURSE_PROVISION_JUNIOR",
        resource_type="users",
        resource_id=new_user.user_id,
        outcome=AuditOutcome.SUCCESS,
        details={
            "provisioned_email": new_user.email,
            "department": dept,
            "designation": req.designation,
            "license_number": req.license_number,
            "supervisor_id": str(current_head.user_id),
        },
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(new_user)

    return {
        "message": f"Successfully onboarded {req.full_name} ({req.designation}) into Department of {dept}.",
        "nurse": NurseResponse.model_validate(new_user),
    }


@router.get("/", response_model=list[NurseResponse])
async def list_nurses(
    department: Optional[str] = Query(None, description="Filter by department"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_medical_staff),
):
    """List nurses available within the organization."""
    query = select(User).where(User.role.in_([UserRole.NURSE, UserRole.HEAD_NURSE]))
    if current_user.role != UserRole.SUPER_ADMIN and current_user.organization_id:
        query = query.where(User.organization_id == current_user.organization_id)
    if department:
        query = query.where(User.department.ilike(f"%{department.strip()}%"))

    result = await db.execute(query.order_by(User.full_name.asc()))
    return [NurseResponse.model_validate(n) for n in result.scalars().all()]


# ─────────────────────────────────────────────────────────────────────────────
# Inpatient Care & Bedside Telemetry Schemas & Helpers
# ─────────────────────────────────────────────────────────────────────────────

class LogVitalsRequest(BaseModel):
    systolic: int = Field(default=120, ge=40, le=300)
    diastolic: int = Field(default=80, ge=20, le=200)
    bp: Optional[str] = None
    pulse: int = Field(default=72, ge=20, le=250)
    spo2: int = Field(default=98, ge=40, le=100)
    temp: float = Field(default=98.6, ge=80.0, le=115.0)
    respiratory_rate: int = Field(default=16, ge=4, le=60)
    pain_score: int = Field(default=0, ge=0, le=10)
    notes: Optional[str] = None


class UpdateTaskStatusRequest(BaseModel):
    status: str = Field(..., description="Task status (pending, administered, delayed, refused, done)")
    notes: Optional[str] = None


def _format_time_ago(dt: datetime) -> str:
    now = datetime.utcnow()
    diff = (now - dt).total_seconds()
    if diff < 60:
        return "Just now"
    elif diff < 3600:
        return f"{int(diff // 60)} min ago"
    elif diff < 86400:
        return f"{int(diff // 3600)}h ago"
    return dt.strftime("%b %d, %H:%M")


def _compute_vitals_status(systolic: int, diastolic: int, pulse: int, spo2: int, temp: float) -> tuple[str, bool]:
    is_crit = spo2 < 90 or systolic > 180 or pulse > 120 or temp > 102.0
    if is_crit:
        return "Critical", True
    if spo2 < 94 or systolic > 155 or diastolic > 98 or pulse > 105 or temp > 100.2:
        return "Attention", False
    return "Stable", False


def _serialize_bed(bed: InpatientBed) -> dict:
    _, is_crit = _compute_vitals_status(bed.systolic, bed.diastolic, bed.pulse, bed.spo2, bed.temp)
    is_crit = is_crit or bed.clinical_status.lower() == "critical"

    return {
        "bedId": str(bed.bed_id),
        "bed_id": str(bed.bed_id),
        "bedNumber": bed.bed_number,
        "bed_number": bed.bed_number,
        "ward": bed.ward,
        "patientName": bed.patient_name,
        "patient_name": bed.patient_name,
        "patientId": str(bed.patient_id) if bed.patient_id else str(bed.bed_id),
        "patient_id": str(bed.patient_id) if bed.patient_id else str(bed.bed_id),
        "uhid": bed.uhid,
        "age": bed.age,
        "gender": bed.gender,
        "admittedFor": bed.admitted_for,
        "admitted_for": bed.admitted_for,
        "attendingPhysician": bed.attending_physician,
        "attending_physician": bed.attending_physician,
        "admitDate": bed.admitted_at.strftime("%Y-%m-%d"),
        "day": bed.admit_day,
        "diet": bed.diet,
        "allergies": bed.allergies or [],
        "codeStatus": bed.code_status,
        "code_status": bed.code_status,
        "isolationPrecautions": bed.isolation_precautions,
        "isolation_precautions": bed.isolation_precautions,
        "nextMedication": bed.next_medication,
        "next_medication": bed.next_medication,
        "medicationDue": bed.medication_due,
        "medication_due": bed.medication_due,
        "status": bed.clinical_status,
        "clinical_status": bed.clinical_status,
        "vitals": {
            "bp": bed.bp,
            "systolic": bed.systolic,
            "diastolic": bed.diastolic,
            "pulse": bed.pulse,
            "spo2": bed.spo2,
            "temp": bed.temp,
            "respiratoryRate": bed.respiratory_rate,
            "respiratory_rate": bed.respiratory_rate,
            "painScore": bed.pain_score,
            "pain_score": bed.pain_score,
            "lastChecked": _format_time_ago(bed.vitals_last_checked),
            "isCritical": is_crit,
        },
        "latestVitals": {
            "id": f"vit-{bed.bed_number}",
            "patientName": bed.patient_name,
            "patientId": str(bed.patient_id) if bed.patient_id else str(bed.bed_id),
            "bedNumber": bed.bed_number,
            "ward": bed.ward,
            "age": bed.age,
            "gender": bed.gender,
            "admittedFor": bed.admitted_for,
            "systolic": bed.systolic,
            "diastolic": bed.diastolic,
            "pulse": bed.pulse,
            "spo2": bed.spo2,
            "temperature": bed.temp,
            "respiratoryRate": bed.respiratory_rate,
            "painScore": bed.pain_score,
            "recordedAt": bed.vitals_last_checked.isoformat(),
            "recordedBy": "Staff Nurse",
            "status": bed.clinical_status.lower(),
        },
    }


def _serialize_task(task: NurseTask) -> dict:
    return {
        "id": str(task.task_id),
        "taskId": str(task.task_id),
        "bedId": str(task.bed_id) if task.bed_id else None,
        "patientId": str(task.patient_id) if task.patient_id else "",
        "patientName": task.patient_name,
        "bedNumber": task.bed_number,
        "ward": task.ward,
        "taskType": task.task_type,
        "medication": task.medication or "",
        "dose": task.dose or "",
        "route": task.route or "",
        "prescribedBy": task.prescribed_by or "Attending Physician",
        "roundTask": task.round_task or "",
        "task": task.round_task or (f"{task.medication} — {task.dose} {task.route}" if task.medication else "Task"),
        "category": task.category or "assessment",
        "priority": task.priority,
        "dueTime": task.due_time,
        "dueBy": task.due_time,
        "overdue": task.is_overdue,
        "status": task.status,
        "notes": task.notes,
        "administeredBy": task.administered_by,
        "administeredAt": task.administered_at.isoformat() if task.administered_at else None,
    }


async def _seed_inpatient_beds_if_empty(db: AsyncSession, organization_id: Optional[uuid.UUID] = None):
    """Seed realistic initial inpatient beds and shift tasks if the table is empty."""
    cnt_res = await db.execute(select(func.count(InpatientBed.bed_id)))
    count = cnt_res.scalar() or 0
    if count > 0:
        return

    now = datetime.utcnow()
    initial_beds = [
        InpatientBed(
            bed_number="ICU-01",
            ward="Intensive Care Unit (ICU)",
            status="occupied",
            clinical_status="Critical",
            patient_name="Eleanor Vance",
            uhid="UHID-2026-0891",
            age=68,
            gender="Female",
            admitted_for="Acute Respiratory Distress (ARDS) & Sepsis",
            attending_physician="Dr. Sarah Chen, MD (Pulmonology)",
            admitted_at=now - timedelta(days=3),
            admit_day=3,
            diet="NPO (Nothing by mouth)",
            allergies=["Penicillin", "Sulfa drugs"],
            code_status="Full Code",
            isolation_precautions="Airborne & Contact",
            next_medication="Meropenem 1g IV Infusion",
            medication_due="Immediate (15:30 Stat)",
            bp="165/98",
            systolic=165,
            diastolic=98,
            pulse=118,
            spo2=89,
            temp=101.4,
            respiratory_rate=26,
            pain_score=4,
            vitals_last_checked=now - timedelta(minutes=15),
            organization_id=organization_id,
        ),
        InpatientBed(
            bed_number="ICU-02",
            ward="Intensive Care Unit (ICU)",
            status="occupied",
            clinical_status="Attention",
            patient_name="Marcus Thorne",
            uhid="UHID-2026-0904",
            age=54,
            gender="Male",
            admitted_for="Post-op CABG (Triple Bypass Day 1)",
            attending_physician="Dr. Gregory House, MD (Cardiothoracic)",
            admitted_at=now - timedelta(days=1),
            admit_day=1,
            diet="Cardiac Low Sodium",
            allergies=["Codeine"],
            code_status="Full Code",
            isolation_precautions=None,
            next_medication="Enoxaparin 40mg SubQ",
            medication_due="16:00 Dose Round",
            bp="138/84",
            systolic=138,
            diastolic=84,
            pulse=88,
            spo2=95,
            temp=99.2,
            respiratory_rate=18,
            pain_score=6,
            vitals_last_checked=now - timedelta(minutes=25),
            organization_id=organization_id,
        ),
        InpatientBed(
            bed_number="WARD-101",
            ward="General Medical Ward",
            status="occupied",
            clinical_status="Stable",
            patient_name="Amina Begum",
            uhid="UHID-2026-0922",
            age=42,
            gender="Female",
            admitted_for="Community-Acquired Pneumonia",
            attending_physician="Dr. Maya Patel, MD (Internal Medicine)",
            admitted_at=now - timedelta(days=2),
            admit_day=2,
            diet="Diabetic Diet",
            allergies=[],
            code_status="Full Code",
            isolation_precautions=None,
            next_medication="Azithromycin 500mg IV",
            medication_due="18:00 Dose Round",
            bp="118/76",
            systolic=118,
            diastolic=76,
            pulse=74,
            spo2=98,
            temp=98.4,
            respiratory_rate=16,
            pain_score=2,
            vitals_last_checked=now - timedelta(minutes=45),
            organization_id=organization_id,
        ),
        InpatientBed(
            bed_number="WARD-102",
            ward="General Medical Ward",
            status="occupied",
            clinical_status="Attention",
            patient_name="David Kowalski",
            uhid="UHID-2026-0931",
            age=61,
            gender="Male",
            admitted_for="Cellulitis Right Lower Extremity",
            attending_physician="Dr. Maya Patel, MD (Internal Medicine)",
            admitted_at=now - timedelta(days=4),
            admit_day=4,
            diet="Regular High Protein",
            allergies=["Latex"],
            code_status="Full Code",
            isolation_precautions=None,
            next_medication="Cefazolin 1g IV",
            medication_due="16:30 Dose Round",
            bp="126/82",
            systolic=126,
            diastolic=82,
            pulse=82,
            spo2=97,
            temp=100.8,
            respiratory_rate=17,
            pain_score=5,
            vitals_last_checked=now - timedelta(minutes=50),
            organization_id=organization_id,
        ),
        InpatientBed(
            bed_number="CCU-201",
            ward="Coronary Care Unit (CCU)",
            status="occupied",
            clinical_status="Stable",
            patient_name="Rajesh Sharma",
            uhid="UHID-2026-0955",
            age=58,
            gender="Male",
            admitted_for="Non-ST Elevation Myocardial Infarction",
            attending_physician="Dr. Vikram Sethi, MD (Cardiology)",
            admitted_at=now - timedelta(days=2),
            admit_day=2,
            diet="Strict Low Sodium",
            allergies=["Aspirin"],
            code_status="Full Code",
            isolation_precautions=None,
            next_medication="Atorvastatin 80mg Oral",
            medication_due="20:00 Dose Round",
            bp="122/78",
            systolic=122,
            diastolic=78,
            pulse=70,
            spo2=99,
            temp=98.6,
            respiratory_rate=15,
            pain_score=1,
            vitals_last_checked=now - timedelta(minutes=30),
            organization_id=organization_id,
        ),
    ]

    for b in initial_beds:
        db.add(b)
    await db.flush()

    for b in initial_beds:
        db.add(
            BedVitalsLog(
                bed_id=b.bed_id,
                bp=b.bp,
                systolic=b.systolic,
                diastolic=b.diastolic,
                pulse=b.pulse,
                spo2=b.spo2,
                temp=b.temp,
                respiratory_rate=b.respiratory_rate,
                pain_score=b.pain_score,
                status=b.clinical_status.lower(),
                is_critical=(b.clinical_status == "Critical"),
                notes=f"Baseline shift vitals check for {b.patient_name}.",
                recorded_by="Staff Nurse",
                recorded_at=b.vitals_last_checked,
            )
        )

    b_icu1 = initial_beds[0]
    b_icu2 = initial_beds[1]
    b_ward1 = initial_beds[2]
    b_ward2 = initial_beds[3]

    initial_tasks = [
        NurseTask(
            bed_id=b_icu1.bed_id,
            patient_name=b_icu1.patient_name,
            bed_number=b_icu1.bed_number,
            ward=b_icu1.ward,
            task_type="medication",
            medication="Meropenem 1g IV Infusion",
            dose="1g",
            route="IV Infusion",
            prescribed_by=b_icu1.attending_physician,
            priority="stat",
            due_time="15:30",
            is_overdue=True,
            status="pending",
            notes="Infuse over 30 mins; verify renal dosage",
            organization_id=organization_id,
        ),
        NurseTask(
            bed_id=b_icu1.bed_id,
            patient_name=b_icu1.patient_name,
            bed_number=b_icu1.bed_number,
            ward=b_icu1.ward,
            task_type="ward_round",
            round_task="ARDS ventilator check & endotracheal suctioning",
            category="assessment",
            priority="stat",
            due_time="15:00",
            is_overdue=True,
            status="pending",
            notes="Monitor peak airway pressures",
            organization_id=organization_id,
        ),
        NurseTask(
            bed_id=b_icu2.bed_id,
            patient_name=b_icu2.patient_name,
            bed_number=b_icu2.bed_number,
            ward=b_icu2.ward,
            task_type="medication",
            medication="Enoxaparin 40mg SubQ",
            dose="40mg",
            route="SubQ",
            prescribed_by=b_icu2.attending_physician,
            priority="urgent",
            due_time="16:00",
            is_overdue=False,
            status="pending",
            notes="Alternate abdominal injection sites",
            organization_id=organization_id,
        ),
        NurseTask(
            bed_id=b_icu2.bed_id,
            patient_name=b_icu2.patient_name,
            bed_number=b_icu2.bed_number,
            ward=b_icu2.ward,
            task_type="ward_round",
            round_task="Surgical sternotomy wound dressing check",
            category="wound",
            priority="routine",
            due_time="16:30",
            is_overdue=False,
            status="pending",
            notes="Check for erythema or drainage",
            organization_id=organization_id,
        ),
        NurseTask(
            bed_id=b_ward2.bed_id,
            patient_name=b_ward2.patient_name,
            bed_number=b_ward2.bed_number,
            ward=b_ward2.ward,
            task_type="medication",
            medication="Cefazolin 1g IV",
            dose="1g",
            route="IV Push",
            prescribed_by=b_ward2.attending_physician,
            priority="routine",
            due_time="16:30",
            is_overdue=False,
            status="pending",
            notes="Inspect IV site for phlebitis before injection",
            organization_id=organization_id,
        ),
        NurseTask(
            bed_id=b_ward2.bed_id,
            patient_name=b_ward2.patient_name,
            bed_number=b_ward2.bed_number,
            ward=b_ward2.ward,
            task_type="ward_round",
            round_task="Right lower limb elevation and cellulitis border outline",
            category="assessment",
            priority="routine",
            due_time="17:00",
            is_overdue=False,
            status="pending",
            notes="Mark border with surgical skin marker",
            organization_id=organization_id,
        ),
        NurseTask(
            bed_id=b_ward1.bed_id,
            patient_name=b_ward1.patient_name,
            bed_number=b_ward1.bed_number,
            ward=b_ward1.ward,
            task_type="ward_round",
            round_task="IV cannula patency flush & dressing inspection",
            category="iv",
            priority="routine",
            due_time="17:30",
            is_overdue=False,
            status="pending",
            notes="Flush with 5ml normal saline",
            organization_id=organization_id,
        ),
    ]

    for t in initial_tasks:
        db.add(t)

    await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Inpatient Bedside & Workstation Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/inpatient-beds")
async def list_inpatient_beds(
    ward: Optional[str] = Query(None, description="Filter beds by ward e.g. icu or ward"),
    clinical_status: Optional[str] = Query(None, description="Filter by status e.g. Critical, Attention, Stable"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_medical_staff),
):
    """Retrieve all inpatient beds with latest vitals, patient demographics, and monitoring alerts."""
    await _seed_inpatient_beds_if_empty(db, current_user.organization_id)

    query = select(InpatientBed)
    if current_user.role != UserRole.SUPER_ADMIN and current_user.organization_id:
        query = query.where(
            or_(
                InpatientBed.organization_id == current_user.organization_id,
                InpatientBed.organization_id.is_(None),
            )
        )

    if ward and ward.lower() != "all":
        if ward.lower() == "icu":
            query = query.where(InpatientBed.ward.ilike("%Intensive Care%"))
        elif ward.lower() == "ward":
            query = query.where(InpatientBed.ward.ilike("%General Ward%"))
        else:
            query = query.where(InpatientBed.ward.ilike(f"%{ward}%"))

    if clinical_status:
        query = query.where(InpatientBed.clinical_status.ilike(f"%{clinical_status}%"))

    result = await db.execute(query.order_by(InpatientBed.bed_number.asc()))
    beds = result.scalars().all()

    return [_serialize_bed(b) for b in beds]


@router.post("/inpatient-beds/{bed_id}/vitals")
async def log_bedside_vitals(
    bed_id: uuid.UUID,
    req: LogVitalsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_medical_staff),
):
    """Log calibrated telemetry vitals, flag safety thresholds, and update inpatient record."""
    result = await db.execute(select(InpatientBed).where(InpatientBed.bed_id == bed_id))
    bed = result.scalar_one_or_none()
    if not bed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inpatient bed '{bed_id}' not found.",
        )

    bp_string = req.bp or f"{req.systolic}/{req.diastolic}"
    clin_status, is_crit = _compute_vitals_status(
        systolic=req.systolic,
        diastolic=req.diastolic,
        pulse=req.pulse,
        spo2=req.spo2,
        temp=req.temp,
    )

    now = datetime.utcnow()

    # Create historical vitals log
    vitals_log = BedVitalsLog(
        bed_id=bed.bed_id,
        patient_id=bed.patient_id,
        bp=bp_string,
        systolic=req.systolic,
        diastolic=req.diastolic,
        pulse=req.pulse,
        spo2=req.spo2,
        temp=req.temp,
        respiratory_rate=req.respiratory_rate,
        pain_score=req.pain_score,
        status=clin_status.lower(),
        is_critical=is_crit,
        notes=req.notes,
        recorded_by=current_user.full_name or "Staff Nurse",
        recorded_by_id=current_user.user_id,
        recorded_at=now,
    )
    db.add(vitals_log)

    # Update bed telemetry cache
    bed.bp = bp_string
    bed.systolic = req.systolic
    bed.diastolic = req.diastolic
    bed.pulse = req.pulse
    bed.spo2 = req.spo2
    bed.temp = req.temp
    bed.respiratory_rate = req.respiratory_rate
    bed.pain_score = req.pain_score
    bed.clinical_status = clin_status
    bed.vitals_last_checked = now
    bed.updated_at = now

    # Audit logging
    db.add(
        AuditLog(
            user_id=current_user.user_id,
            action="NURSE_LOG_VITALS",
            resource_type="inpatient_beds",
            resource_id=bed.bed_id,
            outcome=AuditOutcome.SUCCESS,
            details={
                "bed_number": bed.bed_number,
                "patient_name": bed.patient_name,
                "bp": bp_string,
                "pulse": req.pulse,
                "spo2": req.spo2,
                "temp": req.temp,
                "clinical_status": clin_status,
                "is_critical": is_crit,
            },
        )
    )

    await db.commit()
    await db.refresh(bed)
    await db.refresh(vitals_log)

    try:
        from app.core.websocket_manager import telemetry_manager
        await telemetry_manager.broadcast(
            f"telemetry:{bed.ward.lower().strip()}",
            {
                "event": "VITALS_UPDATED",
                "ward": bed.ward,
                "bed_id": str(bed.bed_id),
                "bed_number": bed.bed_number,
                "patient_name": bed.patient_name,
                "bp": bp_string,
                "systolic": req.systolic,
                "diastolic": req.diastolic,
                "pulse": req.pulse,
                "spo2": req.spo2,
                "temp": req.temp,
                "respiratory_rate": req.respiratory_rate,
                "pain_score": req.pain_score,
                "clinical_status": clin_status,
                "is_critical": is_crit,
                "recorded_by": vitals_log.recorded_by,
                "vitals_last_checked": now.isoformat(),
            },
        )
    except Exception as ws_err:
        logger.warning(f"Telemetry broadcast notice: {ws_err}")

    return {
        "message": f"Bedside vitals logged for Bed {bed.bed_number} ({bed.patient_name}).",
        "bed": _serialize_bed(bed),
        "vitalsLog": {
            "id": str(vitals_log.log_id),
            "bedNumber": bed.bed_number,
            "patientName": bed.patient_name,
            "systolic": vitals_log.systolic,
            "diastolic": vitals_log.diastolic,
            "pulse": vitals_log.pulse,
            "spo2": vitals_log.spo2,
            "temperature": vitals_log.temp,
            "respiratoryRate": vitals_log.respiratory_rate,
            "painScore": vitals_log.pain_score,
            "recordedAt": vitals_log.recorded_at.isoformat(),
            "recordedBy": vitals_log.recorded_by,
            "status": vitals_log.status,
            "isCritical": vitals_log.is_critical,
            "notes": vitals_log.notes,
        },
    }


@router.get("/inpatient-beds/{bed_id}/vitals-history")
async def get_bed_vitals_history(
    bed_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_medical_staff),
):
    """Retrieve historical vitals telemetry for an inpatient bed."""
    query = (
        select(BedVitalsLog)
        .where(BedVitalsLog.bed_id == bed_id)
        .order_by(desc(BedVitalsLog.recorded_at))
        .limit(limit)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": str(log_entry.log_id),
            "bedId": str(log_entry.bed_id),
            "bp": log_entry.bp,
            "systolic": log_entry.systolic,
            "diastolic": log_entry.diastolic,
            "pulse": log_entry.pulse,
            "spo2": log_entry.spo2,
            "temperature": log_entry.temp,
            "respiratoryRate": log_entry.respiratory_rate,
            "painScore": log_entry.pain_score,
            "status": log_entry.status,
            "isCritical": log_entry.is_critical,
            "notes": log_entry.notes,
            "recordedBy": log_entry.recorded_by,
            "recordedAt": log_entry.recorded_at.isoformat(),
        }
        for log_entry in logs
    ]


@router.post("/inpatient-beds/{bed_id}/medication-administered")
async def mark_bed_medication_administered(
    bed_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_medical_staff),
):
    """Mark current medication round complete on inpatient bed."""
    result = await db.execute(select(InpatientBed).where(InpatientBed.bed_id == bed_id))
    bed = result.scalar_one_or_none()
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")

    bed.medication_due = "Completed (Next at 20:00)"
    bed.updated_at = datetime.utcnow()

    db.add(
        AuditLog(
            user_id=current_user.user_id,
            action="NURSE_MEDICATION_ADMINISTERED",
            resource_type="inpatient_beds",
            resource_id=bed.bed_id,
            outcome=AuditOutcome.SUCCESS,
            details={"bed_number": bed.bed_number, "medication": bed.next_medication},
        )
    )
    await db.commit()
    await db.refresh(bed)

    try:
        from app.core.websocket_manager import telemetry_manager
        await telemetry_manager.broadcast(
            f"telemetry:{bed.ward.lower().strip()}",
            {
                "event": "MEDICATION_ADMINISTERED",
                "ward": bed.ward,
                "bed_id": str(bed.bed_id),
                "bed_number": bed.bed_number,
                "patient_name": bed.patient_name,
                "medication": bed.next_medication,
                "medication_due": bed.medication_due,
            },
        )
    except Exception as ws_err:
        logger.warning(f"Telemetry broadcast notice: {ws_err}")

    return {"message": "Medication marked as administered.", "bed": _serialize_bed(bed)}


@router.get("/shift-tasks")
async def get_shift_tasks(
    task_type: Optional[str] = Query(None, description="medication or ward_round"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by task status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_medical_staff),
):
    """Fetch shift medication administration and ward round tasks."""
    await _seed_inpatient_beds_if_empty(db, current_user.organization_id)

    query = select(NurseTask)
    if current_user.role != UserRole.SUPER_ADMIN and current_user.organization_id:
        query = query.where(
            or_(
                NurseTask.organization_id == current_user.organization_id,
                NurseTask.organization_id.is_(None),
            )
        )

    if task_type:
        query = query.where(NurseTask.task_type == task_type)
    if status_filter:
        query = query.where(NurseTask.status == status_filter)

    result = await db.execute(query.order_by(NurseTask.is_overdue.desc(), NurseTask.due_time.asc()))
    tasks = result.scalars().all()

    med_tasks = [_serialize_task(t) for t in tasks if t.task_type == "medication"]
    round_tasks = [_serialize_task(t) for t in tasks if t.task_type == "ward_round"]

    return {
        "all": [_serialize_task(t) for t in tasks],
        "medTasks": med_tasks,
        "roundTasks": round_tasks,
        "totalTasks": len(tasks),
        "pendingCount": len([t for t in tasks if t.status == "pending"]),
        "overdueCount": len([t for t in tasks if t.status == "pending" and t.is_overdue]),
    }


@router.patch("/shift-tasks/{task_id}/status")
async def update_task_status(
    task_id: uuid.UUID,
    req: UpdateTaskStatusRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_medical_staff),
):
    """Update task status (administered, delayed, refused, done, pending) with notes."""
    result = await db.execute(select(NurseTask).where(NurseTask.task_id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found.",
        )

    task.status = req.status
    if req.notes:
        task.notes = f"{task.notes or ''} | {req.notes}".strip(" |")
    task.administered_by = current_user.full_name or "Staff Nurse"
    task.administered_at = datetime.utcnow()
    task.updated_at = datetime.utcnow()

    db.add(
        AuditLog(
            user_id=current_user.user_id,
            action="NURSE_UPDATE_TASK_STATUS",
            resource_type="nurse_tasks",
            resource_id=task.task_id,
            outcome=AuditOutcome.SUCCESS,
            details={
                "task_id": str(task.task_id),
                "task_type": task.task_type,
                "new_status": req.status,
                "patient_name": task.patient_name,
                "bed_number": task.bed_number,
                "notes": req.notes,
            },
        )
    )

    await db.commit()
    await db.refresh(task)

    try:
        from app.core.websocket_manager import telemetry_manager
        await telemetry_manager.broadcast(
            f"telemetry:{task.ward.lower().strip()}",
            {
                "event": "TASK_UPDATED",
                "ward": task.ward,
                "task_id": str(task.task_id),
                "status": task.status,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            },
        )
    except Exception as ws_err:
        logger.warning(f"Telemetry broadcast notice: {ws_err}")

    return {"message": "Task status updated successfully.", "task": _serialize_task(task)}


@router.get("/assigned-patients")
async def get_assigned_patients(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_medical_staff),
):
    """Retrieve active inpatients roster with pending meds & round counts for shift handoff."""
    await _seed_inpatient_beds_if_empty(db, current_user.organization_id)

    query = select(InpatientBed).where(InpatientBed.status == "occupied")
    if current_user.role != UserRole.SUPER_ADMIN and current_user.organization_id:
        query = query.where(
            or_(
                InpatientBed.organization_id == current_user.organization_id,
                InpatientBed.organization_id.is_(None),
            )
        )

    result = await db.execute(query.order_by(InpatientBed.bed_number.asc()))
    beds = result.scalars().all()

    # Query pending tasks per bed
    task_counts_res = await db.execute(
        select(NurseTask.bed_id, NurseTask.task_type, func.count(NurseTask.task_id))
        .where(NurseTask.status == "pending")
        .group_by(NurseTask.bed_id, NurseTask.task_type)
    )
    counts = task_counts_res.all()
    pending_meds_map = {}
    pending_rounds_map = {}
    for bed_id, t_type, cnt in counts:
        if t_type == "medication":
            pending_meds_map[bed_id] = cnt
        elif t_type == "ward_round":
            pending_rounds_map[bed_id] = cnt

    patients = []
    for b in beds:
        patient_data = {
            "patientId": str(b.patient_id) if b.patient_id else str(b.bed_id),
            "patientName": b.patient_name,
            "age": b.age,
            "gender": b.gender,
            "bedNumber": b.bed_number,
            "ward": b.ward,
            "admittedFor": b.admitted_for,
            "attendingPhysician": b.attending_physician,
            "admitDate": b.admitted_at.strftime("%Y-%m-%d"),
            "day": b.admit_day,
            "status": b.clinical_status.lower(),
            "lastVitals": {
                "bp": b.bp,
                "pulse": b.pulse,
                "spo2": b.spo2,
                "temp": b.temp,
            },
            "pendingMeds": pending_meds_map.get(b.bed_id, 1 if "Dose" in b.medication_due else 0),
            "pendingRounds": pending_rounds_map.get(b.bed_id, 1),
            "diet": b.diet,
            "allergies": b.allergies or [],
            "codeStatus": b.code_status,
            "isolationPrecautions": b.isolation_precautions,
        }
        patients.append(patient_data)

    return patients

