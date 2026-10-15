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


def _is_restricted_system_query(q: str) -> bool:
    """Detect queries attempting to extract system internals, source code, tech stack, or architecture."""
    system_keywords = [
        "codebase", "source code", "github", "repository", "tech stack", "technology stack",
        "fastapi", "nextjs", "next.js", "react", "python", "backend", "frontend",
        "database schema", "postgres", "sql query", "sql table", "system architecture",
        "ai healthcare operating system", "ai-hos", "system prompt", "developer mode",
        "jailbreak", "prompt injection", "what are your instructions", "what are your rules",
        "internal rules", "reveal prompt", "vulnerability", "security flaw",
        "weakness of this project", "who is your developer", "who built this",
        "who made this", "what framework", "what model is this", "api key", "secret key",
        "jwt secret", "docker", "nhost", "alembic", "directory structure", "file tree"
    ]
    return any(k in q for k in system_keywords)


def _is_restricted_patient_data_query(q: str) -> bool:
    """Detect queries attempting to retrieve confidential patient data, medical records, or credentials."""
    patient_keywords = [
        "patient data", "patient record", "patient records", "patient history",
        "patient details", "patient info", "patient medical", "patient file",
        "patient list", "all patients", "patient database", "patient chart",
        "patient names", "patient phone", "patient mobile", "patient email",
        "medical record of", "medical records of", "prescription of", "prescriptions of",
        "health record of", "health records of", "clinical notes of", "doctor notes on",
        "who is admitted", "is patient", "show patient", "find patient", "search patient",
        "look up patient", "lookup patient", "bed number of", "admitted patient",
        "abha address of", "abha id of", "abha number of", "test results of",
        "employee password", "user password", "credentials of", "salary", "salaries"
    ]
    return any(k in q for k in patient_keywords)


@router.post("/concierge-chat", response_model=ConciergeChatResponse)
async def concierge_chat(
    data: ConciergeChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Public conversational concierge for patient portal questions.

    Answers healthcare guidance, hospital departments, doctors, OPD schedules, fees,
    amenities, lab tests, and first aid while strictly protecting system internals
    and confidential patient records.
    """
    raw_query = data.query or ""
    q = raw_query.lower().strip()

    # ─────────────────────────────────────────────────────────────────────────────
    # GUARDRAIL 1: System Information, Tech Stack & Architecture Protection
    # ─────────────────────────────────────────────────────────────────────────────
    if _is_restricted_system_query(q):
        return ConciergeChatResponse(
            reply=(
                "🔒 **Information Security Notice:**\n\n"
                "I am exclusively a hospital outpatient concierge assistant. My role is strictly limited to helping "
                "patients and visitors with clinical services, doctor appointments, consultation fees, hospital navigation, "
                "and emergency assistance.\n\n"
                "I cannot disclose or discuss software architecture, system internals, source code, frameworks, tech stacks, "
                "or developmental details under any circumstances."
            ),
            quick_actions=[
                {"label": "🏥 Hospital Departments", "action": "departments"},
                {"label": "📅 Doctor Time Slots", "action": "doctors"},
                {"label": "💰 Consultation Fees", "action": "fees"},
                {"label": "🚨 Emergency Assistance", "action": "emergency"},
            ],
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # GUARDRAIL 2: Confidential Patient Data & Medical Records Privacy Protection
    # ─────────────────────────────────────────────────────────────────────────────
    if _is_restricted_patient_data_query(q):
        return ConciergeChatResponse(
            reply=(
                "🔒 **Confidentiality & Health Data Privacy Notice:**\n\n"
                "Under ABDM (Ayushman Bharat Digital Mission) and healthcare privacy standards, individual patient records, "
                "personal medical files, diagnostic reports, and confidential admission details cannot be accessed or "
                "disclosed through this public concierge desk.\n\n"
                "**How to securely access your records:**\n"
                "• **Registered Patients:** Please sign in on the right with your verified credentials to access your personal digital health locker.\n"
                "• **In-Person Requests:** Visit our Medical Records Department (MRD, Ground Floor Room 108) with a government-issued photo ID.\n"
                "• **Authorized Inquiries:** Next-of-kin for admitted emergency patients may speak directly with the Trauma Desk at **+91-011-2345-6789**."
            ),
            quick_actions=[
                {"label": "📅 Book OPD Appointment", "action": "doctors"},
                {"label": "💰 View Consultation Fees", "action": "fees"},
                {"label": "🚨 Emergency Help", "action": "emergency"},
            ],
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # 1. Emergency Detection & Acute Trauma Triage (Highest Priority)
    # ─────────────────────────────────────────────────────────────────────────────
    emergency_keywords = [
        "heart attack", "chest pain", "breath", "stroke", "unconscious",
        "bleeding", "severe pain", "accident", "emergency", "ambulance", "trauma",
        "choking", "seizure", "poison", "burns", "cpr", "head injury"
    ]
    if any(k in q for k in emergency_keywords):
        return ConciergeChatResponse(
            reply=(
                "🚨 **CRITICAL MEDICAL EMERGENCY PROTOCOL:**\n\n"
                "If you or someone nearby is experiencing acute symptoms (severe chest pain, sudden breathlessness, "
                "facial drooping, heavy bleeding, or loss of consciousness), do not delay:\n\n"
                "• **Dial Ambulance Immediately:** **108** (Toll-Free, 24/7 Dispatch)\n"
                "• **Hospital Trauma Desk:** **+91-011-2345-6789** (Direct Line to Trauma Bay 1)\n"
                "• **Hospital Location:** Ground Floor Emergency Pavilion, Gate 1\n\n"
                "*Our Trauma Team and Advanced Life Support (ALS) ambulances are on standby 24/7/365.*"
            ),
            quick_actions=[
                {"label": "🚨 Open Emergency SOS Console", "action": "emergency"},
                {"label": "📞 Call Ambulance: 108", "action": "call_108"},
            ],
            is_emergency=True,
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # 2. Insurance, Cashless TPA Claims & Government Schemes
    # ─────────────────────────────────────────────────────────────────────────────
    insurance_keywords = ["insurance", "mediclaim", "tpa", "cashless", "claim", "ayushman", "pmjay", "cghs", "echs", "policy"]
    if any(k in q for k in insurance_keywords):
        insurance_summary = (
            "💳 **CarePulse Health Insurance & Cashless TPA Desk:**\n\n"
            "We offer streamlined cashless hospitalization and claim processing across major public and private insurers:\n\n"
            "• **Empaneled TPAs & Private Insurers:** Star Health, HDFC ERGO, ICICI Lombard, Care Health, Niva Bupa, Bajaj Allianz, New India Assurance.\n"
            "• **Government Health Schemes:**\n"
            "  - **Ayushman Bharat (PM-JAY):** Dedicated Helpdesk Counter 3 with Golden Card verification.\n"
            "  - **CGHS & ECHS:** Comprehensive cashless inpatient and daycare coverage.\n"
            "• **TPA Desk Location:** Ground Floor, Room 109 (Open Mon–Sat 09:00 AM – 06:00 PM).\n"
            "• **Required for Cashless Admission:** Health insurance e-card, Government photo ID (Aadhaar/PAN), and Doctor's admission request.\n\n"
            "*For cashless pre-authorization inquiries, contact our TPA Coordinator at +91-011-2345-6789 (Ext. 109).*"
        )
        return ConciergeChatResponse(
            reply=insurance_summary,
            quick_actions=[
                {"label": "💰 Consultation Fees", "action": "fees"},
                {"label": "🏥 Hospital Departments", "action": "departments"},
                {"label": "👨‍⚕️ Doctor Time Slots", "action": "doctors"},
            ],
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # 3. Diagnostic Pathology Lab, Radiology Imaging & Test Preparations
    # ─────────────────────────────────────────────────────────────────────────────
    lab_keywords = ["lab", "test", "pathology", "blood test", "mri", "ct scan", "x-ray", "xray", "ultrasound", "scan", "ecg", "echo", "fasting", "report"]
    if any(k in q for k in lab_keywords):
        lab_summary = (
            "🔬 **Diagnostic Pathology & Imaging Services (24/7 Operations):**\n\n"
            "CarePulse houses fully NABL-accredited diagnostic laboratories and advanced imaging suites:\n\n"
            "• **Pathology & Biochemistry (Ground Floor, Wing B):**\n"
            "  - Routine Blood Work: CBC (₹250), Lipid Profile (₹450), Liver Function LFT (₹500), Kidney KFT (₹450), HbA1c (₹400), Thyroid Panel (₹550).\n"
            "  - **Fasting Preparation:** Fasting Blood Sugar and Lipid Profile require 8–10 hours of overnight water-only fasting.\n\n"
            "• **Radiology & Medical Imaging (Basement 1):**\n"
            "  - 128-Slice Multi-Detector CT Scan (Head, Chest, Abdomen)\n"
            "  - 1.5 Tesla Silent-Scan MRI (Neuro, Musculoskeletal, Spine)\n"
            "  - High-Resolution Digital X-Ray & 3D/4D Ultrasound\n"
            "  - Cardiac Diagnostics: 2D Color Doppler Echocardiography & 12-Lead Digital ECG\n\n"
            "📱 **Report Delivery:** Digital reports are automatically delivered via SMS/WhatsApp within 4–6 hours (blood tests) or 12–24 hours (CT/MRI), and accessible in your Patient Portal."
        )
        return ConciergeChatResponse(
            reply=lab_summary,
            quick_actions=[
                {"label": "💰 View Consultation Fees", "action": "fees"},
                {"label": "⏰ OPD Clinic Hours", "action": "hours"},
                {"label": "👨‍⚕️ Consult a Specialist", "action": "doctors"},
            ],
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # 4. Hospital Admissions, Room Types & Discharge Protocol
    # ─────────────────────────────────────────────────────────────────────────────
    admission_keywords = ["admission", "admit", "bed", "room type", "discharge", "ward", "icu", "deluxe", "attendant"]
    if any(k in q for k in admission_keywords):
        admission_summary = (
            "🛏️ **Hospital Inpatient Accommodation & Admission Guidelines:**\n\n"
            "We provide comfortable, sterile inpatient rooms tailored to clinical requirements:\n\n"
            "• **Room Categories:**\n"
            "  - **General Medical Ward:** ₹1,500/day (Air-conditioned, partitioned privacy, nursing station monitored)\n"
            "  - **Semi-Private Room:** ₹3,200/day (Twin-sharing with individual TV, attached washroom, sofa bed for attendant)\n"
            "  - **Private Deluxe Suite:** ₹5,500/day (Single occupancy, motorized bed, attendant couch, refrigerator, dining)\n"
            "  - **Intensive Care Unit (ICU/CCU/NICU):** ₹8,500/day (1:1 dedicated nursing ratio, multi-para cardiac monitors, ventilators)\n\n"
            "• **Admission Procedure:** Present Doctor's Admission Slip at the Central Admission Desk (Ground Floor). Please bring valid ID proof (Aadhaar/Passport) and insurance card.\n"
            "• **Attendant Policy:** One 24/7 attendant pass is issued per inpatient room.\n"
            "• **Planned Discharge Timings:** 10:00 AM – 01:00 PM daily."
        )
        return ConciergeChatResponse(
            reply=admission_summary,
            quick_actions=[
                {"label": "💰 Consultation Fees", "action": "fees"},
                {"label": "🏥 Hospital Departments", "action": "departments"},
                {"label": "⏰ Visiting Hours", "action": "hours"},
            ],
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # 5. Hospital Amenities, Pharmacy, Canteen, Parking & Accessibility
    # ─────────────────────────────────────────────────────────────────────────────
    amenity_keywords = ["pharmacy", "medicine", "canteen", "cafeteria", "food", "parking", "wheelchair", "atm", "restroom", "facilities", "amenity", "amenities"]
    if any(k in q for k in amenity_keywords):
        amenity_summary = (
            "🏢 **Hospital Amenities & Patient Facilities:**\n\n"
            "• **24/7 Central Pharmacy (Ground Floor, Main Lobby):** Stocked with all genuine prescription medications, surgical consumables, and emergency drugs (15% discount on generic essentials).\n"
            "• **Cafeteria & Dining (2nd Floor):** Nutritious, hygienic meals for attendants and visitors. Open daily 07:00 AM – 10:00 PM.\n"
            "• **Wheelchair & Stretcher Assistance:** Free wheelchair dispatch available at Main Entrance Gate 1 (simply alert hospital security on arrival).\n"
            "• **Parking Facilities:** 2-level basement parking with valet assistance for patients. First 30 minutes free.\n"
            "• **Banking & ATMs:** State Bank of India & HDFC Bank ATMs located next to the ground floor entrance corridor.\n"
            "• **Prayer / Reflection Room:** 3rd Floor quiet zone for all faiths."
        )
        return ConciergeChatResponse(
            reply=amenity_summary,
            quick_actions=[
                {"label": "⏰ Clinic Operating Hours", "action": "hours"},
                {"label": "🏥 Hospital Departments", "action": "departments"},
                {"label": "🚨 Emergency Assistance", "action": "emergency"},
            ],
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # 6. General Health, Common Symptoms & First Aid Advice
    # ─────────────────────────────────────────────────────────────────────────────
    health_keywords = ["fever", "headache", "cold", "cough", "diet", "vomiting", "diarrhea", "pain", "first aid", "remedy", "hydration", "ors", "bp", "diabetes"]
    if any(k in q for k in health_keywords):
        health_summary = (
            "🩺 **Clinical Wellness & General Health Guidance:**\n\n"
            "Here is standard clinical first-line guidance for mild symptoms:\n\n"
            "• **Fever / Body Aches:** Stay well hydrated with lukewarm fluids, rest, and monitor temperature every 4–6 hours. Over-the-counter Paracetamol (500–650mg) may be taken with food if not contraindicated.\n"
            "• **Diarrhea / Dehydration:** Rehydrate immediately with Oral Rehydration Salts (ORS) solution in boiled/filtered water. Avoid dairy and spicy meals; consume light khichdi, bananas, and coconut water.\n"
            "• **Minor Burns:** Cool the affected area under gentle running tap water for 10–15 minutes. Never apply ice, butter, or toothpaste. Cover loosely with sterile gauze.\n"
            "• **Sprain / Muscle Injury:** Apply the **R.I.C.E.** protocol (Rest, Ice packs wrapped in cloth for 15 mins, Compression bandage, Elevation).\n\n"
            "⚠️ *Clinical Disclaimer: This guidance is for informational triage only. If high fever (>102°F) persists for >48 hours, or is accompanied by severe abdominal pain, breathlessness, or vomiting, please consult our General Medicine OPD immediately.*"
        )
        return ConciergeChatResponse(
            reply=health_summary,
            quick_actions=[
                {"label": "👨‍⚕️ Consult General Physician", "action": "doctors"},
                {"label": "💰 Check Consultation Fees", "action": "fees"},
                {"label": "🚨 Emergency Trauma Bay", "action": "emergency"},
            ],
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # 7. Fees & Consultation Charges Inquiry
    # ─────────────────────────────────────────────────────────────────────────────
    fee_keywords = ["fee", "cost", "charge", "price", "rate", "how much", "payment", "upi"]
    if any(k in q for k in fee_keywords):
        summary = (
            "💰 **CarePulse Hospital Consultation & OPD Fee Schedule:**\n\n"
            "• **General Medicine OPD (Dr. Sunita Rao / Dr. Alok Verma):** ₹500\n"
            "• **Pediatrics & Child Health (Dr. Arjun Kumar / Dr. Neha Agarwal):** ₹600\n"
            "• **Dermatology & Skin Allergy (Dr. Vikram Reddy / Dr. Pooja Chawla):** ₹650\n"
            "• **Orthopedics & Joint Surgery (Dr. Kavya Singh / Dr. Rohan Mehta):** ₹750\n"
            "• **Interventional Cardiology (Dr. Rajesh Sharma / Dr. Anita Desai):** ₹800\n"
            "• **Neurology & Stroke Care (Dr. Priya Patel / Dr. Sameer Joshi):** ₹900\n"
            "• **Emergency Triage Assessment (24/7 Trauma Bay):** ₹1,000\n\n"
            "✨ **Transparent Patient Policies:**\n"
            "• **Free Follow-Up:** Follow-up consultations within 7 days of initial OPD visit are **100% Free**.\n"
            "• **Payment Methods Accepted:** UPI (GPay/PhonePe/Paytm), All Credit/Debit Cards, Cash, and Net Banking.\n"
            "• **Digital ABHA Health Record:** Created free of charge upon patient registration."
        )
        return ConciergeChatResponse(
            reply=summary,
            quick_actions=[
                {"label": "📅 View Doctor Slots", "action": "doctors"},
                {"label": "🏥 Hospital Departments", "action": "departments"},
                {"label": "⏰ OPD Clinic Hours", "action": "hours"},
            ],
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # 8. Department & Clinical Specialties Inquiry
    # ─────────────────────────────────────────────────────────────────────────────
    dept_keywords = [
        "department", "departments", "specialty", "specialties", "speciality", "specialities",
        "service", "services", "division", "divisions"
    ]
    if any(k in q for k in dept_keywords):
        dept_summary = (
            "🏥 **CarePulse Hospital Departments & Clinical Specialties:**\n\n"
            "CarePulse Hospital provides comprehensive outpatient and inpatient care across 7 specialized clinical departments:\n\n"
            "1. **Cardiology & Heart Institute** (3rd Floor, Cardiology Wing)\n"
            "   • Senior Specialists: Dr. Rajesh Sharma, Dr. Anita Desai\n"
            "   • Scope: Interventional Cardiology, Cath Lab, Echocardiography, Cardiac Care (Fee: ₹800)\n\n"
            "2. **Neurology & Stroke Center** (2nd Floor, Neurosciences Block)\n"
            "   • Senior Specialists: Dr. Priya Patel, Dr. Sameer Joshi\n"
            "   • Scope: Comprehensive Stroke Management, Epilepsy, Neuromuscular Disorders (Fee: ₹900)\n\n"
            "3. **Pediatrics & Child Health** (1st Floor, Child Health Pavilion)\n"
            "   • Senior Specialists: Dr. Arjun Kumar, Dr. Neha Agarwal\n"
            "   • Scope: Neonatal ICU (NICU), Well-Baby Clinic, Immunizations, Pediatric OPD (Fee: ₹600)\n\n"
            "4. **Orthopedics & Joint Surgery** (2nd Floor, Surgical Block)\n"
            "   • Senior Specialists: Dr. Kavya Singh, Dr. Rohan Mehta\n"
            "   • Scope: Joint Replacements (Hip/Knee), Fracture Trauma, Arthroscopy, Spine Care (Fee: ₹750)\n\n"
            "5. **Dermatology & Skin Clinic** (1st Floor, Outpatient Complex)\n"
            "   • Senior Specialists: Dr. Vikram Reddy, Dr. Pooja Chawla\n"
            "   • Scope: Clinical Dermatology, Skin Allergies, Dermatosurgery, Cosmetology (Fee: ₹650)\n\n"
            "6. **Internal & General Medicine** (Ground Floor, Main OPD Complex)\n"
            "   • Senior Specialists: Dr. Sunita Rao, Dr. Alok Verma\n"
            "   • Scope: Chronic Disease Care, Diabetology, Hypertension, Preventive Health (Fee: ₹500)\n\n"
            "7. **Emergency & Critical Trauma** (Ground Floor, 24/7 Trauma Bay)\n"
            "   • Coverage: Dr. Priya Nair, Dr. Manish Tiwari (24/7 Rotational Emergency Coverage)\n"
            "   • Scope: Immediate Resuscitation, Ambulance Dispatch (108), Emergency Triage (Fee: ₹1,000)\n\n"
            "🔬 **24/7 Diagnostic & Support Facilities:**\n"
            "• NABL-Accredited Pathology Laboratory (24/7 Operations)\n"
            "• Advanced Radiology & Imaging (128-slice CT, 1.5T MRI, Digital X-Ray, Ultrasound)\n"
            "• Central Pharmacy (Ground Floor, 24/7 Open)"
        )
        return ConciergeChatResponse(
            reply=dept_summary,
            quick_actions=[
                {"label": "👨‍⚕️ Available Doctor Slots", "action": "doctors"},
                {"label": "💰 Consultation Fee Schedule", "action": "fees"},
                {"label": "⏰ OPD Clinic Hours", "action": "hours"},
                {"label": "🚨 Emergency Assistance", "action": "emergency"},
            ],
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # 9. Doctor Search, Appointment Roster & Clinician Profiles
    # ─────────────────────────────────────────────────────────────────────────────
    doc_keywords = ["doctor", "slot", "timing", "schedule", "appointment", "specialist", "cardio", "neuro", "pediatric", "ortho", "derma", "sharma", "patel", "kumar", "singh", "reddy", "rao"]
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
                    f"*Sign in on the right to reserve an appointment.*"
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
                "*Please sign in on the right to reserve your consultation slot.*"
            ),
            quick_actions=[
                {"label": "📋 Open Doctor Directory Tab", "action": "doctors"},
                {"label": "💰 View Fee Schedule", "action": "fees"},
            ],
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # 10. Operating Hours, OPD Schedules & Visiting Windows
    # ─────────────────────────────────────────────────────────────────────────────
    if any(k in q for k in ["hour", "time", "open", "opd", "visit", "visiting"]):
        return ConciergeChatResponse(
            reply=(
                "⏰ **Hospital Operating & Visiting Hours:**\n\n"
                "• **General Outpatient (OPD):** Monday to Saturday, 08:00 AM - 05:00 PM\n"
                "• **Emergency & Trauma Center:** Open 24 Hours, 365 Days a Year\n"
                "• **Diagnostic Pathology & Imaging (CT/MRI/X-Ray):** 24/7 Operations\n"
                "• **Inpatient Visiting Hours:** Daily 04:00 PM - 07:00 PM\n"
                "• **ICU Visiting Window:** Daily 11:00 AM - 12:00 PM & 05:00 PM - 06:00 PM (1 visitor at a time)\n"
                "• **Central Pharmacy (Ground Floor):** Open 24/7"
            ),
            quick_actions=[
                {"label": "👨‍⚕️ Available Doctor Slots", "action": "doctors"},
                {"label": "🏥 Hospital Departments", "action": "departments"},
                {"label": "🚨 Emergency Assistance", "action": "emergency"},
            ],
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # 11. Hospital Location, Address, Directions & Contact
    # ─────────────────────────────────────────────────────────────────────────────
    if any(k in q for k in ["where", "location", "address", "direction", "contact", "phone", "email", "reach"]):
        return ConciergeChatResponse(
            reply=(
                "📍 **CarePulse Hospital Location & Contact Desk:**\n\n"
                "• **Address:** CarePulse Multi-Specialty Hospital, Metro Pillar 142, Main Institutional Area.\n"
                "• **24/7 Emergency Trauma Desk:** **+91-011-2345-6789**\n"
                "• **Ambulance Dispatch:** **108** (Direct Toll-Free)\n"
                "• **General OPD Reception:** **+91-011-2345-6700**\n"
                "• **Email Assistance:** helpdesk@carepulse-hospital.org\n"
                "• **Landmark & Transit:** Located directly across Metro Station Gate 2 with convenient basement parking."
            ),
            quick_actions=[
                {"label": "👨‍⚕️ View Doctor Slots", "action": "doctors"},
                {"label": "⏰ OPD Clinic Hours", "action": "hours"},
                {"label": "🚨 Emergency Assistance", "action": "emergency"},
            ],
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # 12. Default Universal Healthcare Concierge Guidance
    # ─────────────────────────────────────────────────────────────────────────────
    return ConciergeChatResponse(
        reply=(
            "Welcome to CarePulse! I am your hospital concierge assistant. I can answer any questions regarding:\n\n"
            "• **🏥 Hospital Departments:** 7 multi-specialty clinical institutes and surgical wings.\n"
            "• **👨‍⚕️ Doctor Time Slots:** Specific clinician shifts, room numbers, and OPD availability.\n"
            "• **💰 Transparent Fees & Insurance:** Consultation prices, cashless TPA claims, and PM-JAY.\n"
            "• **🔬 Diagnostic Labs & Imaging:** 24/7 Blood tests, CT/MRI scans, and fasting guidelines.\n"
            "• **🛏️ Inpatient Rooms & Amenities:** General ward to deluxe suites, 24/7 pharmacy, and visitor hours.\n"
            "• **🩺 General Health & First Aid:** Guidance on fever, hydration, minor injuries, and triage.\n\n"
            "*How may I assist you today? Feel free to ask or choose a quick option below.*"
        ),
        quick_actions=[
            {"label": "🏥 Hospital Departments", "action": "departments"},
            {"label": "📅 Doctor Time Slots", "action": "doctors"},
            {"label": "💰 Consultation Fees", "action": "fees"},
            {"label": "🚨 Emergency Help", "action": "emergency"},
        ],
    )

