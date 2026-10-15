"""AI Patient Intake API Endpoints for AI-HOS (Milestone U-13).

Provides endpoints for conversational symptom collection, state recovery,
AI orchestrator dispatch with non-diagnostic guardrails, and structured
symptom persistence.
"""

import base64
from datetime import datetime
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.api.schemas.intake import (
    IntakeCompleteRequest,
    IntakeMessageRequest,
    IntakeMessageResponse,
    IntakeSessionCreateRequest,
    IntakeSessionResponse,
    StructuredSymptomsData,
)
from app.database import get_db
from app.models import IntakeSession, IntakeStatus, Patient, User, UserRole
from app.services.auth.service import get_current_active_user
from app.services.intake.intake_agent import IntakeAgentResult
from app.services.orchestrator import TaskRequest, TaskType, get_orchestrator
from app.services.providers import get_stt_provider, get_tts_provider

logger = logging.getLogger("aihos.intake")

router = APIRouter(prefix="/intake", tags=["intake"])


class IntakeVoiceMessageResponse(BaseModel):
    session_id: UUID
    transcription: str
    detected_language: str
    reply: str
    audio_base64: Optional[str] = None
    tts_provider: str
    is_complete: bool
    structured_symptoms: Optional[StructuredSymptomsData] = None
    ai_confidence: Optional[float] = None
    basis: Optional[str] = None


async def _resolve_patient_for_user(db: AsyncSession, current_user: User) -> Patient:
    """Resolve or automatically initialize a patient profile for the current user."""
    if current_user.role == UserRole.PATIENT:
        stmt = select(Patient).where(Patient.user_id == current_user.user_id)
        result = await db.execute(stmt)
        patient = result.scalar_one_or_none()
        if not patient:
            from datetime import date
            patient = Patient(
                user_id=current_user.user_id,
                full_name=current_user.full_name or "Registered Patient",
                email=current_user.email,
                date_of_birth=date(1995, 1, 1),
                gender="Not Specified",
            )
            db.add(patient)
            await db.commit()
            await db.refresh(patient)
        return patient
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only registered patient users can initiate self-intake sessions.",
    )


async def _verify_session_access(
    session: IntakeSession,
    current_user: User,
    db: AsyncSession,
) -> None:
    """Verify that current_user has authorization to view or interact with this session."""
    if current_user.role in (UserRole.ADMIN, UserRole.DOCTOR):
        return  # Clinical staff have operational visibility
    
    # Patient role: must strictly own the session
    stmt = select(Patient).where(Patient.patient_id == session.patient_id)
    res = await db.execute(stmt)
    patient = res.scalar_one_or_none()
    if not patient or patient.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You are not authorized to access this intake session.",
        )


@router.post("/sessions", response_model=IntakeSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_intake_session(
    payload: Optional[IntakeSessionCreateRequest] = None,
    patient_id: Optional[UUID] = Query(None, description="Target patient ID if doctor/admin"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new AI-guided intake session for symptom collection."""
    if current_user.role == UserRole.PATIENT:
        patient = await _resolve_patient_for_user(db, current_user)
        target_patient_id = patient.patient_id
    elif current_user.role in (UserRole.ADMIN, UserRole.DOCTOR):
        if not patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="patient_id query parameter is required when staff initiate intake.",
            )
        p_res = await db.execute(select(Patient).where(Patient.patient_id == patient_id))
        patient = p_res.scalar_one_or_none()
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found.",
            )
        target_patient_id = patient_id
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized role.")

    now_iso = datetime.utcnow().isoformat()
    initial_greeting = {
        "role": "assistant",
        "content": (
            f"Hello {patient.full_name or 'there'}! I am the AI-HOS Intake Assistant. "
            "I will help gather and structure your symptoms so your doctor has full context for your consultation. "
            "Please note: I do not provide medical diagnoses or prescribe medications. "
            "To begin, what primary symptoms or health concerns are you experiencing today?"
        ),
        "timestamp": now_iso,
    }

    messages = [initial_greeting]
    structured_symptoms = None
    ai_confidence = None
    basis = None
    session_status = IntakeStatus.IN_PROGRESS

    # If the user provided an opening symptom description, run the first intake turn immediately
    if payload and payload.initial_message and payload.initial_message.strip():
        user_msg = {
            "role": "patient",
            "content": payload.initial_message.strip(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        messages.append(user_msg)

        orchestrator = get_orchestrator()
        task_req = TaskRequest(
            task_type=TaskType.INTAKE,
            payload={
                "patient_name": patient.full_name,
                "gender": patient.gender,
                "messages": [initial_greeting],
                "new_message": payload.initial_message.strip(),
            },
        )
        task_res = await orchestrator.submit_task(task_req)
        if task_res.result:
            agent_res: IntakeAgentResult = task_res.result
            messages.append({
                "role": "assistant",
                "content": agent_res.reply,
                "timestamp": datetime.utcnow().isoformat(),
            })
            structured_symptoms = agent_res.structured_symptoms
            ai_confidence = agent_res.ai_confidence
            basis = agent_res.basis
            if agent_res.is_complete:
                session_status = IntakeStatus.COMPLETED

    intake_session = IntakeSession(
        patient_id=target_patient_id,
        status=session_status,
        messages=messages,
        structured_symptoms=structured_symptoms,
        ai_confidence=float(ai_confidence) if ai_confidence is not None else None,
        basis=basis,
    )
    db.add(intake_session)
    await db.commit()
    await db.refresh(intake_session)

    return intake_session


@router.get("/sessions/active", response_model=Optional[IntakeSessionResponse])
async def get_active_intake_session(
    patient_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve the currently active (in_progress) intake session for the patient."""
    if current_user.role == UserRole.PATIENT:
        patient = await _resolve_patient_for_user(db, current_user)
        target_patient_id = patient.patient_id
    elif current_user.role in (UserRole.ADMIN, UserRole.DOCTOR):
        if not patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="patient_id query parameter is required for staff.",
            )
        target_patient_id = patient_id
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized role.")

    stmt = (
        select(IntakeSession)
        .where(
            IntakeSession.patient_id == target_patient_id,
            IntakeSession.status == IntakeStatus.IN_PROGRESS,
        )
        .order_by(desc(IntakeSession.created_at))
        .limit(1)
    )
    result = await db.execute(stmt)
    active_session = result.scalar_one_or_none()
    if not active_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active intake session found.",
        )
    return active_session


@router.get("/sessions/{session_id}", response_model=IntakeSessionResponse)
async def get_intake_session_by_id(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve a specific intake session by ID with access control."""
    stmt = select(IntakeSession).where(IntakeSession.session_id == session_id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intake session not found.")

    await _verify_session_access(session, current_user, db)
    return session


@router.post("/sessions/{session_id}/message", response_model=IntakeMessageResponse)
@router.post("/sessions/{session_id}/messages", response_model=IntakeMessageResponse)
async def send_intake_message(
    session_id: UUID,
    payload: IntakeMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Send a patient message to the intake assistant and receive non-diagnostic guidance."""
    stmt = select(IntakeSession).where(IntakeSession.session_id == session_id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intake session not found.")

    await _verify_session_access(session, current_user, db)

    if session.status in (IntakeStatus.COMPLETED, IntakeStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot post messages to an intake session that is {session.status.value}.",
        )

    # Fetch patient details for context
    p_stmt = select(Patient).where(Patient.patient_id == session.patient_id)
    p_res = await db.execute(p_stmt)
    patient = p_res.scalar_one_or_none()

    patient_name = patient.full_name if patient else "Patient"
    gender = patient.gender if patient else None

    # Append user turn
    user_turn = {
        "role": "patient",
        "content": payload.content.strip(),
        "timestamp": datetime.utcnow().isoformat(),
    }
    current_messages = list(session.messages or [])
    current_messages.append(user_turn)

    # Dispatch to orchestrator
    orchestrator = get_orchestrator()
    task_req = TaskRequest(
        task_type=TaskType.INTAKE,
        payload={
            "patient_name": patient_name,
            "gender": gender,
            "messages": current_messages[:-1],
            "new_message": payload.content.strip(),
        },
    )
    task_res = await orchestrator.submit_task(task_req)

    if not task_res.result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Intake agent failed to process dialogue turn.",
        )

    agent_res: IntakeAgentResult = task_res.result

    # Append AI assistant turn
    assistant_turn = {
        "role": "assistant",
        "content": agent_res.reply,
        "timestamp": datetime.utcnow().isoformat(),
    }
    current_messages.append(assistant_turn)

    session.messages = current_messages
    flag_modified(session, "messages")

    session.structured_symptoms = agent_res.structured_symptoms
    flag_modified(session, "structured_symptoms")

    session.ai_confidence = float(agent_res.ai_confidence)
    session.basis = agent_res.basis

    if agent_res.is_complete:
        session.status = IntakeStatus.COMPLETED
        session.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(session)

    struct_data = StructuredSymptomsData(**(agent_res.structured_symptoms or {}))

    return IntakeMessageResponse(
        session_id=session.session_id,
        reply=agent_res.reply,
        is_complete=agent_res.is_complete,
        structured_symptoms=struct_data,
        ai_confidence=agent_res.ai_confidence,
        basis=agent_res.basis,
        status=session.status.value,
    )


@router.post("/sessions/{session_id}/voice-message", response_model=IntakeVoiceMessageResponse)
async def send_intake_voice_message(
    session_id: UUID,
    file: UploadFile = File(..., description="Recorded patient speech audio"),
    language: str = Form("en", description="Target language code (en, hi, ta, te, bn, es)"),
    synthesize_reply: bool = Form(True, description="Whether to synthesize spoken assistant response"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Send voice audio to the intake dialogue pipeline.
    
    CRITICAL: Does NOT fork intake logic; transcribes audio via STT adapter,
    submits transcribed text to the canonical IntakeAgent, updates structured
    symptoms in PostgreSQL, and synthesizes spoken reply via TTS adapter.
    """
    stmt = select(IntakeSession).where(IntakeSession.session_id == session_id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intake session not found.")

    await _verify_session_access(session, current_user, db)

    if session.status in (IntakeStatus.COMPLETED, IntakeStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot post voice messages to an intake session that is {session.status.value}.",
        )

    # 1. Read audio bytes
    content = await file.read()
    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty (0 bytes).",
        )

    filename = file.filename or "intake_audio.webm"
    audio_format = filename.split(".")[-1].lower() if "." in filename else "webm"
    if audio_format not in ("webm", "mp3", "wav", "ogg", "m4a"):
        audio_format = "webm"

    # 2. Transcribe using STT provider adapter (Groq Whisper / fallback)
    stt_provider = get_stt_provider()
    try:
        stt_res = await stt_provider.transcribe(
            audio_data=content,
            format=audio_format,
            language=language,
        )
        transcribed_text = (stt_res.text or "").strip()
    except Exception as exc:
        logger.error(f"Voice intake STT transcription failure: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Audio transcription service failed: {str(exc)}",
        )

    if not transcribed_text:
        transcribed_text = "[Inaudible speech input]"

    # 3. Resolve patient context
    p_stmt = select(Patient).where(Patient.patient_id == session.patient_id)
    p_res = await db.execute(p_stmt)
    patient = p_res.scalar_one_or_none()
    patient_name = patient.full_name if patient else "Patient"
    gender = patient.gender if patient else None

    # 4. Append user turn
    user_turn = {
        "role": "patient",
        "content": transcribed_text,
        "is_voice": True,
        "language": language,
        "timestamp": datetime.utcnow().isoformat(),
    }
    current_messages = list(session.messages or [])
    current_messages.append(user_turn)

    # 5. Dispatch to canonical IntakeAgent (no fork!)
    orchestrator = get_orchestrator()
    task_req = TaskRequest(
        task_type=TaskType.INTAKE,
        payload={
            "patient_name": patient_name,
            "gender": gender,
            "messages": current_messages[:-1],
            "new_message": transcribed_text,
        },
    )
    task_res = await orchestrator.submit_task(task_req)
    if not task_res.result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Intake agent failed to process dialogue turn.",
        )

    agent_res: IntakeAgentResult = task_res.result

    # 6. Append assistant turn
    assistant_turn = {
        "role": "assistant",
        "content": agent_res.reply,
        "timestamp": datetime.utcnow().isoformat(),
    }
    current_messages.append(assistant_turn)

    session.messages = current_messages
    flag_modified(session, "messages")

    session.structured_symptoms = agent_res.structured_symptoms
    flag_modified(session, "structured_symptoms")

    session.ai_confidence = float(agent_res.ai_confidence)
    session.basis = agent_res.basis

    if agent_res.is_complete:
        session.status = IntakeStatus.COMPLETED
        session.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(session)

    # 7. Synthesize spoken response via TTS provider adapter (ElevenLabs / fallback)
    audio_base64_str = None
    active_tts_name = "none"
    if synthesize_reply and agent_res.reply:
        tts_provider = get_tts_provider()
        active_tts_name = tts_provider.name
        try:
            tts_res = await tts_provider.synthesize(
                text=agent_res.reply,
                format="mp3",
            )
            if tts_res and tts_res.audio_data:
                audio_base64_str = base64.b64encode(tts_res.audio_data).decode("ascii")
        except Exception as tts_exc:
            logger.warning(f"Voice synthesis fallback activated: {tts_exc}")
            active_tts_name = "browser_fallback"

    struct_data = StructuredSymptomsData(**(agent_res.structured_symptoms or {}))

    return IntakeVoiceMessageResponse(
        session_id=session.session_id,
        transcription=transcribed_text,
        detected_language=language,
        reply=agent_res.reply,
        audio_base64=audio_base64_str,
        tts_provider=active_tts_name,
        is_complete=agent_res.is_complete,
        structured_symptoms=struct_data,
        ai_confidence=agent_res.ai_confidence,
        basis=agent_res.basis,
    )


@router.post("/sessions/{session_id}/complete", response_model=IntakeSessionResponse)
async def complete_intake_session(
    session_id: UUID,
    payload: Optional[IntakeCompleteRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Manually finalize and complete an intake session."""
    stmt = select(IntakeSession).where(IntakeSession.session_id == session_id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intake session not found.")

    await _verify_session_access(session, current_user, db)

    if session.status != IntakeStatus.COMPLETED:
        session.status = IntakeStatus.COMPLETED
        session.completed_at = datetime.utcnow()
        if payload and payload.notes:
            notes_turn = {
                "role": "patient",
                "content": f"[Final Patient Note]: {payload.notes}",
                "timestamp": datetime.utcnow().isoformat(),
            }
            msgs = list(session.messages or [])
            msgs.append(notes_turn)
            session.messages = msgs
            flag_modified(session, "messages")
        await db.commit()
        await db.refresh(session)

    return session


@router.get("/sessions", response_model=list[IntakeSessionResponse])
async def list_intake_sessions(
    patient_id: Optional[UUID] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List past intake sessions for the patient or clinical review."""
    if current_user.role == UserRole.PATIENT:
        patient = await _resolve_patient_for_user(db, current_user)
        target_patient_id = patient.patient_id
    elif current_user.role in (UserRole.ADMIN, UserRole.DOCTOR):
        target_patient_id = patient_id
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized role.")

    stmt = select(IntakeSession)
    if target_patient_id:
        stmt = stmt.where(IntakeSession.patient_id == target_patient_id)
    stmt = stmt.order_by(desc(IntakeSession.created_at)).limit(limit)

    res = await db.execute(stmt)
    return res.scalars().all()


class ConciergeChatRequest(BaseModel):
    query: str


class ConciergeChatResponse(BaseModel):
    reply: str
    quick_actions: Optional[list[dict]] = None
    matched_doctor: Optional[dict] = None
    is_emergency: bool = False


@router.post("/concierge-chat", response_model=ConciergeChatResponse)
async def concierge_chat(
    data: ConciergeChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Public conversational concierge for patient portal questions.

    Understands doctor availability, fees, OPD schedules, and emergency alerts.
    """
    q = (data.query or "").lower().strip()

    # 1. Emergency detection
    emergency_keywords = [
        "heart attack", "chest pain", "breath", "stroke", "unconscious",
        "bleeding", "severe pain", "accident", "emergency", "ambulance", "trauma"
    ]
    if any(k in q for k in emergency_keywords):
        return ConciergeChatResponse(
            reply=(
                "🚨 **CRITICAL MEDICAL EMERGENCY PROTOCOL:**\n\n"
                "If you or someone nearby is experiencing acute symptoms (severe chest pain, sudden breathlessness, "
                "facial drooping, or heavy bleeding), do not delay. Immediately dial **108** (Ambulance) or our direct "
                "hospital trauma desk at **+91-011-2345-6789**."
            ),
            quick_actions=[
                {"label": "🚨 Open Emergency SOS Console", "action": "emergency"},
                {"label": "📞 Call Ambulance: 108", "action": "call_108"},
            ],
            is_emergency=True,
        )

    # 2. Fees & Charges inquiry
    fee_keywords = ["fee", "cost", "charge", "price", "rate", "how much"]
    if any(k in q for k in fee_keywords):
        summary = (
            "💰 **CarePulse Hospital Consultation & OPD Fee Schedule:**\n\n"
            "• **General Medicine OPD:** ₹500\n"
            "• **Pediatrics & Child Health:** ₹600\n"
            "• **Dermatology & Skin Allergy:** ₹650\n"
            "• **Orthopedics & Joint Care:** ₹750\n"
            "• **Interventional Cardiology:** ₹800\n"
            "• **Neurology & Stroke Care:** ₹900\n"
            "• **Emergency Triage Assessment:** ₹1,000\n\n"
            "✨ **Patient Inclusions:**\n"
            "• Follow-up consultations within 7 days are **100% Free**\n"
            "• Digital health record generation (ABDM ABHA): Included\n\n"
            "*Sign in or register to book a confirmed slot.*"
        )
        return ConciergeChatResponse(
            reply=summary,
            quick_actions=[
                {"label": "📅 View Doctor Slots", "action": "doctors"},
                {"label": "⏰ OPD Clinic Hours", "action": "hours"},
            ],
        )

    # 3. Doctor search / appointment query
    doc_keywords = ["doctor", "slot", "timing", "schedule", "appointment", "specialist", "cardio", "neuro", "pediatric", "ortho", "derma", "sharma", "patel"]
    if any(k in q for k in doc_keywords):
        from app.models import Doctor
        stmt = select(Doctor).order_by(Doctor.full_name)
        res = await db.execute(stmt)
        docs = res.scalars().all()

        matched_doc = None
        if docs:
            for d in docs:
                if (d.specialty and d.specialty.lower() in q) or (d.full_name and any(part.lower() in q for part in d.full_name.split())):
                    matched_doc = {
                        "id": str(d.doctor_id),
                        "name": d.full_name,
                        "specialty": d.specialty or "General Practice",
                        "qualification": d.qualifications or "MBBS, MD",
                        "room": d.room_number or "Main OPD Pavilion",
                        "fee": 800 if "cardio" in (d.specialty or "").lower() else 600,
                        "followUpFee": "Free within 7 days",
                        "status": "Available Today",
                    }
                    break

        if matched_doc:
            return ConciergeChatResponse(
                reply=(
                    f"Consultation details for **{matched_doc['name']}** ({matched_doc['specialty']}):\n\n"
                    f"• **Qualifications:** {matched_doc['qualification']}\n"
                    f"• **Location:** {matched_doc['room']}\n"
                    f"• **Consultation Fee:** ₹{matched_doc['fee']} ({matched_doc['followUpFee']})\n"
                    f"• **Status:** {matched_doc['status']}\n\n"
                    f"*Sign in to reserve an appointment.*"
                ),
                matched_doctor=matched_doc,
                quick_actions=[
                    {"label": "📋 View All Doctors", "action": "doctors"},
                    {"label": "💰 Check Consultation Fees", "action": "fees"},
                ],
            )

        # General roster
        return ConciergeChatResponse(
            reply=(
                "👨‍⚕️ **Hospital Specialist Roster & Available Time Slots:**\n\n"
                "1. **Dr. Rajesh Sharma** (Cardiology): Mon-Fri 09:00 AM - 01:00 PM (Fee: ₹800)\n"
                "2. **Dr. Priya Patel** (Neurology): Mon, Wed, Fri 10:00 AM - 02:00 PM (Fee: ₹900)\n"
                "3. **Dr. Arjun Kumar** (Pediatrics): Mon-Sat 09:30 AM - 03:30 PM (Fee: ₹600)\n"
                "4. **Dr. Kavya Singh** (Orthopedics): Tue, Thu, Sat 11:00 AM - 04:00 PM (Fee: ₹750)\n"
                "5. **Dr. Vikram Reddy** (Dermatology): Mon, Wed, Sat 02:00 PM - 06:00 PM (Fee: ₹650)\n"
                "6. **Dr. Sunita Rao** (Internal Medicine): Mon-Sat 08:30 AM - 02:30 PM (Fee: ₹500)\n"
                "7. **Dr. Priya Nair** (Emergency Medicine): 24/7 Rotational Coverage\n\n"
                "*Please sign in on the right to reserve a consultation slot.*"
            ),
            quick_actions=[
                {"label": "📋 Open Doctor Directory Tab", "action": "doctors"},
                {"label": "💰 View Fee Schedule", "action": "fees"},
            ],
        )

    # 4. Hours & Timings
    if any(k in q for k in ["hour", "time", "open", "opd", "visit"]):
        return ConciergeChatResponse(
            reply=(
                "⏰ **Hospital Operating & Visiting Hours:**\n\n"
                "• **General Outpatient (OPD):** Monday to Saturday, 08:00 AM - 05:00 PM\n"
                "• **Emergency & Trauma Center:** Open 24 Hours, 365 Days a Year\n"
                "• **Diagnostic Pathology & Imaging (CT/MRI/X-Ray):** 24/7 Operations\n"
                "• **Inpatient Visiting Hours:** Daily 04:00 PM - 07:00 PM\n"
                "• **Central Pharmacy (Ground Floor):** Open 24/7"
            ),
            quick_actions=[
                {"label": "👨‍⚕️ Available Doctor Slots", "action": "doctors"},
                {"label": "🚨 Emergency Assistance", "action": "emergency"},
            ],
        )

    # 5. Default Fallback
    return ConciergeChatResponse(
        reply=(
            "Welcome to CarePulse! I can assist you with your outpatient hospital visit:\n\n"
            "• **Doctor Time Slots:** Inquire about specific specialties or on-duty doctors.\n"
            "• **Consultation Fees:** Transparent fee breakdown for general OPD and super-specialists.\n"
            "• **Clinic Timings:** OPD consulting and visiting schedules.\n"
            "• **Emergency Assistance:** Direct contact with our 24/7 Trauma Bay & Ambulance."
        ),
        quick_actions=[
            {"label": "📅 Doctor Time Slots", "action": "doctors"},
            {"label": "💰 Consultation Fees", "action": "fees"},
            {"label": "🚨 Emergency Help", "action": "emergency"},
        ],
    )

