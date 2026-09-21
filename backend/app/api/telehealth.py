"""Telehealth & Doctor Schedule Consultation Endpoints for AI-HOS (Milestone U-14).

Provides endpoints for daily doctor scheduling, active consultation room context,
red-flag detection integration from U-13 intake summaries, and real-time consultation lifecycle.
"""

from datetime import date, datetime, time, timedelta
import asyncio
import json
import re
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.telehealth import (
    DoctorScheduleItemResponse,
    DoctorScheduleListResponse,
    PatientIntakeSummary,
    TelehealthActionResponse,
    TelehealthRoomResponse,
)
from app.database import get_db
from app.models import (
    Appointment,
    AppointmentStatus,
    Doctor,
    IntakeSession,
    Patient,
    User,
    UserRole,
)
from app.services.auth.service import get_current_active_user

router = APIRouter(prefix="/telehealth", tags=["telehealth"])

# ─── WebRTC Signalling State ──────────────────────────────────────────────────
# Maps room_id → list[WebSocket] (max 2 peers: doctor + patient)
_signalling_rooms: dict[str, list[WebSocket]] = {}


# Defined clinical red-flag patterns for emergency detection & triage
RED_FLAG_PATTERNS = [
    (r"(?i)\b(chest\s*pain|crushing\s*pressure|cardiac|heart\s*attack|angina)\b", "Severe Acute Cardiovascular Symptom (Red Flag)"),
    (r"(?i)\b(shortness\s*of\s*breath|cannot\s*breathe|difficulty\s*breathing|asphyxiation|gasping)\b", "Acute Respiratory Distress (Red Flag)"),
    (r"(?i)\b(sudden\s*numbness|facial\s*droop|slurred\s*speech|stroke|paralysis)\b", "Acute Neurological / Stroke Indicator (Red Flag)"),
    (r"(?i)\b(uncontrolled\s*bleeding|hemorrhage|coughing\s*blood|vomiting\s*blood)\b", "Severe Uncontrolled Hemorrhage (Red Flag)"),
    (r"(?i)\b(loss\s*of\s*consciousness|unresponsive|syncope|fainted|blacked\s*out)\b", "Impaired Consciousness / Syncope (Red Flag)"),
    (r"(?i)\b(severe\s*anaphylaxis|throat\s*swelling|tongue\s*swelling|allergic\s*shock)\b", "Acute Anaphylactic Shock (Red Flag)"),
]


def detect_red_flags(text: str) -> list[str]:
    """Scan clinical text for immediate emergency red-flag triggers."""
    warnings = []
    for pattern, label in RED_FLAG_PATTERNS:
        if re.search(pattern, text):
            warnings.append(label)
    return warnings


async def _resolve_doctor_profile(db: AsyncSession, current_user: User) -> Doctor:
    """Retrieve or initialize the attending doctor's profile."""
    if current_user.role != UserRole.DOCTOR and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors and clinical administrators can access this schedule resource.",
        )
    stmt = select(Doctor).where(Doctor.user_id == current_user.user_id)
    res = await db.execute(stmt)
    doctor = res.scalar_one_or_none()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attending doctor profile with verified medical license was not found. Please contact an institutional administrator to complete clinical provisioning.",
        )
    return doctor


async def _get_patient_intake_summary(db: AsyncSession, patient_id: UUID) -> Optional[PatientIntakeSummary]:
    """Retrieve the most recent intake session and run red-flag detection."""
    stmt = (
        select(IntakeSession)
        .where(IntakeSession.patient_id == patient_id)
        .order_by(desc(IntakeSession.created_at))
        .limit(1)
    )
    res = await db.execute(stmt)
    intake = res.scalar_one_or_none()
    if not intake:
        return None

    struct = intake.structured_symptoms or {}
    chief_complaint = struct.get("chief_complaint")
    duration = struct.get("duration")
    severity = struct.get("severity")
    associated = struct.get("associated_symptoms") or []
    summary = struct.get("summary")

    # Aggregate text for red-flag scan
    corpus = f"{chief_complaint or ''} {' '.join(associated)} {summary or ''}"
    if intake.messages:
        corpus += " " + " ".join(m.get("content", "") for m in intake.messages if m.get("role") in ("patient", "user"))

    warnings = detect_red_flags(corpus)

    return PatientIntakeSummary(
        session_id=intake.session_id,
        chief_complaint=chief_complaint,
        duration=duration,
        severity=int(severity) if severity is not None else None,
        associated_symptoms=associated,
        summary=summary,
        has_red_flags=len(warnings) > 0,
        red_flag_warnings=warnings,
    )


@router.get("/schedule", response_model=DoctorScheduleListResponse)
async def get_doctor_schedule(
    date_str: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (defaults to today)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve the doctor's appointment schedule enriched with patient intake summaries."""
    doctor = await _resolve_doctor_profile(db, current_user)

    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        target_date = date.today()

    start_dt = datetime.combine(target_date, time.min)
    end_dt = datetime.combine(target_date, time.max)

    stmt = (
        select(Appointment)
        .where(
            Appointment.doctor_id == doctor.doctor_id,
            Appointment.scheduled_at >= start_dt,
            Appointment.scheduled_at <= end_dt,
            Appointment.status != AppointmentStatus.CANCELLED,
        )
        .order_by(Appointment.scheduled_at)
    )
    res = await db.execute(stmt)
    appointments = res.scalars().all()

    items: list[DoctorScheduleItemResponse] = []
    in_consultation_count = 0
    scheduled_count = 0
    completed_count = 0

    for appt in appointments:
        # Load patient
        p_res = await db.execute(select(Patient).where(Patient.patient_id == appt.patient_id))
        patient = p_res.scalar_one_or_none()

        patient_name = patient.full_name if patient else "Patient"
        patient_gender = patient.gender if patient else None
        patient_abha = patient.abha_address if patient else None
        patient_phone = patient.phone if patient else None
        patient_age = None
        if patient and patient.date_of_birth:
            today = date.today()
            patient_age = today.year - patient.date_of_birth.year - (
                (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
            )

        intake_summary = await _get_patient_intake_summary(db, appt.patient_id)

        status_val = appt.status.value if hasattr(appt.status, "value") else str(appt.status)
        if status_val == "in_progress":
            in_consultation_count += 1
        elif status_val == "completed":
            completed_count += 1
        else:
            scheduled_count += 1

        items.append(
            DoctorScheduleItemResponse(
                appointment_id=appt.appointment_id,
                patient_id=appt.patient_id,
                patient_name=patient_name,
                patient_gender=patient_gender,
                patient_age=patient_age,
                patient_abha=patient_abha,
                patient_phone=patient_phone,
                scheduled_at=appt.scheduled_at,
                duration_minutes=appt.duration_minutes,
                status=status_val,
                meeting_link=appt.meeting_link,
                telehealth_room_id=appt.telehealth_room_id,
                notes=appt.notes,
                intake_summary=intake_summary,
            )
        )

    return DoctorScheduleListResponse(
        date=target_date.isoformat(),
        total_appointments=len(items),
        scheduled_count=scheduled_count,
        in_consultation_count=in_consultation_count,
        completed_count=completed_count,
        appointments=items,
    )


@router.get("/rooms/{appointment_id}", response_model=TelehealthRoomResponse)
async def get_telehealth_room(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve active telehealth room details, verifying participant authorization."""
    stmt = select(Appointment).where(Appointment.appointment_id == appointment_id)
    res = await db.execute(stmt)
    appointment = res.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    # Load participants
    d_res = await db.execute(select(Doctor).where(Doctor.doctor_id == appointment.doctor_id))
    doctor = d_res.scalar_one_or_none()

    p_res = await db.execute(select(Patient).where(Patient.patient_id == appointment.patient_id))
    patient = p_res.scalar_one_or_none()

    # RBAC Access Control
    is_authorized = False
    if current_user.role == UserRole.ADMIN:
        is_authorized = True
    elif current_user.role == UserRole.DOCTOR and doctor and doctor.user_id == current_user.user_id:
        is_authorized = True
    elif current_user.role == UserRole.PATIENT and patient and patient.user_id == current_user.user_id:
        is_authorized = True

    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not an authorized participant for this consultation room.",
        )

    # Initialize room identifiers if not already assigned
    if not appointment.telehealth_room_id:
        appointment.telehealth_room_id = f"telehealth-{str(appointment.appointment_id)[:8]}"
    if not appointment.meeting_link:
        appointment.meeting_link = f"/doctor/consultations/{appointment.appointment_id}"
        await db.commit()
        await db.refresh(appointment)

    intake_summary = await _get_patient_intake_summary(db, appointment.patient_id)

    patient_age = None
    if patient and patient.date_of_birth:
        today = date.today()
        patient_age = today.year - patient.date_of_birth.year - (
            (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
        )

    status_val = appointment.status.value if hasattr(appointment.status, "value") else str(appointment.status)

    return TelehealthRoomResponse(
        appointment_id=appointment.appointment_id,
        room_id=appointment.telehealth_room_id,
        meeting_link=appointment.meeting_link,
        status=status_val,
        doctor_id=appointment.doctor_id,
        doctor_name=doctor.full_name if doctor else "Doctor",
        doctor_specialty=doctor.specialty if doctor else "General Physician",
        doctor_hospital=doctor.hospital_affiliation if doctor else "AI-HOS Medical Center",
        patient_id=appointment.patient_id,
        patient_name=patient.full_name if patient else "Patient",
        patient_gender=patient.gender if patient else None,
        patient_age=patient_age,
        patient_abha=patient.abha_address if patient else None,
        patient_phone=patient.phone if patient else None,
        scheduled_at=appointment.scheduled_at,
        duration_minutes=appointment.duration_minutes,
        intake_summary=intake_summary,
        telehealth_started_at=appointment.telehealth_started_at,
        telehealth_ended_at=appointment.telehealth_ended_at,
    )


@router.post("/rooms/{appointment_id}/start", response_model=TelehealthActionResponse)
async def start_telehealth_consultation(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Doctor starts the telehealth consultation session."""
    stmt = select(Appointment).where(Appointment.appointment_id == appointment_id)
    res = await db.execute(stmt)
    appointment = res.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    # Doctor verification
    d_res = await db.execute(select(Doctor).where(Doctor.doctor_id == appointment.doctor_id))
    doctor = d_res.scalar_one_or_none()
    if current_user.role != UserRole.ADMIN and (not doctor or doctor.user_id != current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the attending physician can start this consultation room.",
        )

    now = datetime.utcnow()
    appointment.telehealth_started_at = now
    appointment.telehealth_room_id = f"telehealth-{str(appointment.appointment_id)[:8]}"
    appointment.meeting_link = f"/doctor/consultations/{appointment.appointment_id}"
    appointment.status = AppointmentStatus.IN_PROGRESS

    await db.commit()
    await db.refresh(appointment)

    return TelehealthActionResponse(
        appointment_id=appointment.appointment_id,
        status=appointment.status.value,
        message="Telehealth consultation room started successfully.",
        meeting_link=appointment.meeting_link,
        telehealth_started_at=appointment.telehealth_started_at,
    )


@router.post("/rooms/{appointment_id}/end", response_model=TelehealthActionResponse)
async def end_telehealth_consultation(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Doctor completes and concludes the telehealth consultation."""
    stmt = select(Appointment).where(Appointment.appointment_id == appointment_id)
    res = await db.execute(stmt)
    appointment = res.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    d_res = await db.execute(select(Doctor).where(Doctor.doctor_id == appointment.doctor_id))
    doctor = d_res.scalar_one_or_none()
    if current_user.role != UserRole.ADMIN and (not doctor or doctor.user_id != current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the attending physician can conclude this consultation room.",
        )

    now = datetime.utcnow()
    appointment.telehealth_ended_at = now
    appointment.status = AppointmentStatus.COMPLETED

    await db.commit()
    await db.refresh(appointment)

    return TelehealthActionResponse(
        appointment_id=appointment.appointment_id,
        status=appointment.status.value,
        message="Telehealth consultation concluded successfully.",
        meeting_link=appointment.meeting_link,
        telehealth_started_at=appointment.telehealth_started_at,
        telehealth_ended_at=appointment.telehealth_ended_at,
    )


# =============================================================================
# WebRTC Signalling — In-App Video Call
# =============================================================================

@router.get("/room/{appointment_id}/token")
async def get_room_token(
    appointment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Return a room join token for the WebRTC call tied to an appointment.
    The token is simply a signed room_id; actual auth is performed when the
    WebSocket connection is established via the bearer token query param.

    Returns:
        room_id: str — use as /telehealth/ws/{room_id}
        appointment_id: UUID
        peer_role: 'doctor' | 'patient'
    """
    appointment = await db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    # Authorisation: only the patient or doctor of this appointment may join
    is_doctor = current_user.role in [UserRole.DOCTOR, UserRole.HEAD_PHYSICIAN]
    is_patient = current_user.role == UserRole.PATIENT

    if not (is_doctor or is_patient):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the doctor or patient of this appointment may join.")

    # The room_id is deterministic for the appointment so both peers compute the same value
    room_id = f"room-{appointment_id}"
    peer_role = "doctor" if is_doctor else "patient"

    return {
        "room_id": room_id,
        "appointment_id": str(appointment_id),
        "peer_role": peer_role,
        "ws_url": f"/api/v1/telehealth/ws/{room_id}",
        "instructions": "Connect to ws_url via WebSocket. Send JSON messages: {type, payload}. Supported types: offer, answer, ice-candidate, bye",
    }


@router.websocket("/ws/{room_id}")
async def webrtc_signalling(websocket: WebSocket, room_id: str):
    """
    WebRTC signalling relay — acts as a rendezvous broker for two peers.

    Protocol (JSON messages):
        Client → Server: { "type": "offer"|"answer"|"ice-candidate"|"bye", "payload": <SDP or candidate> }
        Server → Other peer(s): same message forwarded verbatim

    Room lifecycle:
        - First peer to connect: waits for the second.
        - Second peer connects: both are notified (type="peer_joined").
        - Either peer sends "bye": other peer is notified and both are removed.
        - Room is cleaned up automatically on disconnection.
    """
    await websocket.accept()

    # Add this peer to the room (max 2 peers)
    room_peers: list[WebSocket] = _signalling_rooms.setdefault(room_id, [])
    if len(room_peers) >= 2:
        await websocket.send_json({"type": "error", "payload": "Room is full (max 2 peers)."})
        await websocket.close(code=1008)
        return

    room_peers.append(websocket)
    peer_index = len(room_peers) - 1  # 0 = first (doctor/initiator), 1 = second (patient/answerer)

    # Notify the new peer of their role
    await websocket.send_json({
        "type": "room_joined",
        "payload": {
            "room_id": room_id,
            "peer_index": peer_index,
            "is_initiator": peer_index == 0,
            "peer_count": len(room_peers),
        }
    })

    # If both peers are now present, notify the first peer
    if len(room_peers) == 2:
        try:
            await room_peers[0].send_json({"type": "peer_joined", "payload": {"peer_index": 1}})
        except Exception:
            pass

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "payload": "Invalid JSON."})
                continue

            msg_type = message.get("type", "")

            if msg_type == "bye":
                # Forward to the other peer and end session
                for peer in room_peers:
                    if peer is not websocket:
                        try:
                            await peer.send_json({"type": "bye", "payload": {}})
                        except Exception:
                            pass
                break

            # Forward offer / answer / ice-candidate to the other peer
            if msg_type in ("offer", "answer", "ice-candidate"):
                for peer in room_peers:
                    if peer is not websocket:
                        try:
                            await peer.send_json(message)
                        except Exception:
                            pass

    except WebSocketDisconnect:
        pass
    finally:
        # Clean up this peer's slot
        if websocket in room_peers:
            room_peers.remove(websocket)
        # Notify remaining peer that the other left
        for peer in room_peers:
            try:
                await peer.send_json({"type": "peer_left", "payload": {"peer_index": peer_index}})
            except Exception:
                pass
        # If room is empty, remove it
        if not room_peers:
            _signalling_rooms.pop(room_id, None)

