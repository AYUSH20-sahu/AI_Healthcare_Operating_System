"""Doctor Copilot API Endpoints.

Provides unified AI Orchestrator endpoints for clinical consultations,
SOAP synthesis, provider failover telemetry, and human review fallback.
"""

import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.copilot import (
    AIProviderHealthResponse,
    AIMetadataResponse,
    CopilotAnalysisRequest,
    CopilotAnalysisResponse,
    CopilotDataResponse,
)
from app.database import get_db
from app.models import User, UserRole
from app.services.auth.audit import log_audit_event
from app.services.auth.service import get_current_active_user
from app.services.copilot.copilot_agent import copilot_agent
from app.services.orchestrator import (
    TaskRequest,
    TaskResult,
    TaskStatus,
    TaskType,
    get_orchestrator,
)
from app.services.providers import registry

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/analyze", response_model=CopilotAnalysisResponse)
async def analyze_consultation(
    request_data: CopilotAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyze a consultation transcript or clinical dictation via the AI Orchestrator.
    
    Routes through the provider adapter (NVIDIA primary, Gemini fallback).
    Enforces Doctor & Admin clearance.
    """
    if current_user.role not in [UserRole.DOCTOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to clinical doctors and institutional administrators.",
        )

    orchestrator = get_orchestrator()
    task_id = f"copilot-{uuid.uuid4().hex[:12]}"

    payload = {
        "transcription": request_data.transcription,
        "patient_id": request_data.patient_id,
        "patient_name": request_data.patient_name,
        "appointment_id": request_data.appointment_id,
        "vitals": request_data.vitals or {},
        "allergies": request_data.allergies or [],
        "chief_complaint": request_data.chief_complaint,
        "language": request_data.language,
    }

    task_request = TaskRequest(
        task_type=TaskType.COPILOT,
        payload=payload,
        metadata={"user_id": str(current_user.user_id), "task_id": task_id},
        timeout_seconds=30.0,
        max_retries=2,
        retry_backoff_base=0.5,
    )

    result: TaskResult = await orchestrator.execute_task(task_request)

    # Audit logging
    await log_audit_event(
        db=db,
        user_id=current_user.user_id,
        action="COPILOT_ANALYSIS",
        resource_type="copilot_task",
        resource_id=task_id,
        details={
            "status": result.status.value,
            "fallback_triggered": result.fallback_triggered,
            "provider": result.ai_metadata.get("provider", "unknown"),
            "attempts": result.attempts,
        },
    )

    if result.status == TaskStatus.COMPLETED and result.result:
        agent_res = result.result
        data_block = CopilotDataResponse(
            soap=agent_res.soap,
            icd10_codes=agent_res.icd10_codes,
            medications=agent_res.medications,
            diagnostics_ordered=agent_res.diagnostics_ordered,
            confidence=agent_res.confidence,
        )
        ai_meta = AIMetadataResponse(
            provider=agent_res.ai_metadata.get("provider", "mock"),
            model=agent_res.ai_metadata.get("model", "unknown"),
            fallback_used=agent_res.ai_metadata.get("fallback_used", False),
            latency_ms=agent_res.ai_metadata.get("latency_ms", 0.0),
            confidence=agent_res.ai_metadata.get("confidence", 90),
            tokens=agent_res.ai_metadata.get("usage"),
        )
        return CopilotAnalysisResponse(
            success=True,
            status="completed",
            task_id=task_id,
            data=data_block,
            ai_metadata=ai_meta,
            requires_human_fallback=False,
            fallback_reason=None,
        )

    elif result.status == TaskStatus.FALLBACK_TO_HUMAN:
        # Fallback to human review mode: Return a blank template for physician manual entry
        fallback_soap = {
            "subjective": {
                "chief_complaint": request_data.chief_complaint or "Physician Manual Entry",
                "history_of_present_illness": request_data.transcription or "",
                "review_of_systems": "",
            },
            "objective": {
                "vitals_reviewed": ", ".join([f"{k}: {v}" for k, v in (request_data.vitals or {}).items()]),
                "physical_exam": "",
            },
            "assessment": {
                "primary_diagnosis": "Pending Clinician Evaluation",
                "icd10_code": "R69",
                "differentials": [],
                "ai_confidence": 0,
                "clinical_rationale": "AI service providers failed or timed out. Switched to manual doctor attestation.",
            },
            "plan": {
                "medications": [],
                "diagnostics_ordered": [],
                "counseling": "",
                "follow_up": "",
            },
        }
        return CopilotAnalysisResponse(
            success=True,
            status="fallback_to_human",
            task_id=task_id,
            data=CopilotDataResponse(
                soap=fallback_soap,
                icd10_codes=["R69"],
                medications=[],
                diagnostics_ordered=[],
                confidence=0,
            ),
            ai_metadata=AIMetadataResponse(
                provider="manual",
                model="clinician-manual-fallback",
                fallback_used=True,
                latency_ms=result.total_time_seconds * 1000.0,
                confidence=0,
                tokens=None,
            ),
            requires_human_fallback=True,
            fallback_reason=result.error or "Provider failover threshold exhausted. Fallback to clinician manual entry.",
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI Copilot task execution encountered unhandled state: {result.error}",
        )


@router.get("/providers", response_model=AIProviderHealthResponse)
async def get_providers_status(
    current_user: User = Depends(get_current_active_user),
):
    """Retrieve AI Provider adapter status, active primary, and fallback availability."""
    llm_list = registry.list_llm_providers()
    stt_list = registry.list_stt_providers()
    active_llm = registry._default_llm or "mock"
    active_stt = registry._default_stt or "mock"
    has_fallback = "fallback" in llm_list or ("nvidia" in llm_list and "gemini" in llm_list)

    return AIProviderHealthResponse(
        active_llm=active_llm,
        active_stt=active_stt,
        llm_providers=llm_list,
        stt_providers=stt_list,
        failover_ready=has_fallback,
    )


@router.get("/human-queue")
async def list_human_review_queue(
    current_user: User = Depends(get_current_active_user),
):
    """List pending tasks that failed automated AI execution and require physician attention."""
    if current_user.role not in [UserRole.DOCTOR, UserRole.ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor clearance required.")
    
    orchestrator = get_orchestrator()
    queue = orchestrator.get_human_review_queue()
    return {
        "pending_reviews": [
            {
                "task_type": item.task_type.value,
                "metadata": item.metadata,
                "payload_preview": str(item.payload)[:200],
            }
            for item in queue
        ],
        "count": len(queue),
    }
