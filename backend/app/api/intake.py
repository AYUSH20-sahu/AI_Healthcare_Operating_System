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
