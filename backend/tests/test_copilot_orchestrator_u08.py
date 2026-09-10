"""Milestone U-08 Tests: Doctor Copilot Provider + Orchestration Integration.

Explicitly tests:
1. NVIDIA success -> response (primary LLM path).
2. NVIDIA failure / rate limit -> Gemini fallback -> response (failover mesh path).
3. Provider failure across all providers -> human/manual fallback (safety escalation).
4. Full-stack FastAPI route integration and RBAC security.
"""

import json
from unittest.mock import AsyncMock, patch
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Doctor, User, UserRole
from app.services.auth.service import create_access_token, get_password_hash
from app.services.copilot.copilot_agent import CopilotAgent
from app.services.orchestrator import (
    Orchestrator,
    TaskRequest,
    TaskStatus,
    TaskType,
)
from app.services.providers import (
    FallbackLLMProvider,
    LLMMessage,
    LLMResponse,
    MockLLMProvider,
)


@pytest_asyncio.fixture
async def test_doctor(db_session: AsyncSession):
    """Create test doctor user and profile."""
    user = User(
        email="doctor_u08@test.com",
        hashed_password=get_password_hash("doctorpassword123"),
        full_name="Dr. Rajesh Sharma",
        role=UserRole.DOCTOR,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    doctor = Doctor(
        user_id=user.user_id,
        license_number="DOC-U08-12345",
        specialty="Cardiology",
        full_name="Dr. Rajesh Sharma",
        email="doctor_u08@test.com",
    )
    db_session.add(doctor)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_patient(db_session: AsyncSession):
    """Create test patient user."""
    user = User(
        email="patient_u08@test.com",
        hashed_password=get_password_hash("patientpassword123"),
        full_name="Amit Kumar",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_nvidia_success_primary_response():
    """Test 1: NVIDIA primary provider succeeds and returns response with correct telemetry."""
    primary_mock = MockLLMProvider("nvidia")
    fallback_mock = MockLLMProvider("gemini")
    resilient_provider = FallbackLLMProvider(primary=primary_mock, fallback=fallback_mock)

    messages = [
        LLMMessage(role="system", content="You are a clinical copilot."),
        LLMMessage(role="user", content="Patient has exertional chest pain relieved by rest. Vitals: BP 138/88."),
    ]

    response = await resilient_provider.generate(messages)

    assert response.provider == "nvidia"
    assert response.fallback_used is False
    assert "chest pain" in response.content.lower() or "angina" in response.content.lower()
    assert response.latency_ms >= 0


@pytest.mark.asyncio
async def test_nvidia_failure_gemini_fallback_response():
    """Test 2: NVIDIA failure/rate limit triggers automated Gemini fallback and returns response."""
    # Simulate NVIDIA failing with 429 rate limit
    failing_primary = MockLLMProvider("nvidia", simulate_failure=True)
    working_fallback = MockLLMProvider("gemini", simulate_failure=False)
    resilient_provider = FallbackLLMProvider(primary=failing_primary, fallback=working_fallback)

    messages = [
        LLMMessage(role="system", content="You are a clinical copilot."),
        LLMMessage(role="user", content="Patient has exertional chest pain relieved by rest. Vitals: BP 138/88."),
    ]

    response = await resilient_provider.generate(messages)

    assert response.provider == "gemini"
    assert response.fallback_used is True
    assert "chest pain" in response.content.lower() or "angina" in response.content.lower()
    assert response.latency_ms >= 0


@pytest.mark.asyncio
async def test_provider_failure_human_fallback():
    """Test 3: Both primary and fallback providers fail -> Orchestrator triggers fallback to human review."""
    # Both fail
    failing_primary = MockLLMProvider("nvidia", simulate_failure=True)
    failing_fallback = MockLLMProvider("gemini", simulate_failure=True)
    resilient_provider = FallbackLLMProvider(primary=failing_primary, fallback=failing_fallback)

    test_orchestrator = Orchestrator(default_timeout=5.0, default_max_retries=1, default_backoff_base=0.01)
    agent = CopilotAgent()

    with patch("app.services.copilot.copilot_agent.get_llm_provider", return_value=resilient_provider):
        test_orchestrator.register_agent(agent)

        request = TaskRequest(
            task_type=TaskType.COPILOT,
            payload={"transcription": "Patient has severe acute chest pain."},
            max_retries=1,
            retry_backoff_base=0.01,
            timeout_seconds=2.0,
        )

        result = await test_orchestrator.execute_task(request)

        assert result.status == TaskStatus.FALLBACK_TO_HUMAN
        assert result.fallback_triggered is True
        assert result.attempts == 2  # 1 initial + 1 retry
        assert result.ai_metadata["provider"] == "manual"
        assert len(test_orchestrator.get_human_review_queue()) == 1


@pytest.mark.asyncio
async def test_copilot_api_nvidia_success_flow(client: AsyncClient, test_doctor: User):
    """Test 4: Doctor queries /api/v1/copilot/analyze -> NVIDIA primary success flow."""
    token = create_access_token(data={"sub": str(test_doctor.user_id)})

    primary_mock = MockLLMProvider("nvidia")
    fallback_mock = MockLLMProvider("gemini")
    resilient_provider = FallbackLLMProvider(primary=primary_mock, fallback=fallback_mock)

    with patch("app.services.copilot.copilot_agent.get_llm_provider", return_value=resilient_provider):
        response = await client.post(
            "/api/v1/copilot/analyze",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "transcription": "Patient reports retrosternal chest pain on exertion. BP 138/88, HR 94.",
                "patient_name": "Amit Kumar",
                "allergies": ["Penicillin"],
                "vitals": {"bp": "138/88", "hr": 94},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "completed"
        assert data["requires_human_fallback"] is False
        assert data["ai_metadata"]["provider"] == "nvidia"
        assert data["ai_metadata"]["fallback_used"] is False

        soap = data["data"]["soap"]
        assert "subjective" in soap
        assert "objective" in soap
        assert "assessment" in soap
        assert "plan" in soap
        assert soap["assessment"]["icd10_code"] in ["I20.9", "I24.9"]


@pytest.mark.asyncio
async def test_copilot_api_gemini_fallback_flow(client: AsyncClient, test_doctor: User):
    """Test 5: Doctor queries /api/v1/copilot/analyze with NVIDIA down -> Gemini fallback serves response."""
    token = create_access_token(data={"sub": str(test_doctor.user_id)})

    # Primary fails, fallback succeeds
    failing_primary = MockLLMProvider("nvidia", simulate_failure=True)
    working_fallback = MockLLMProvider("gemini", simulate_failure=False)
    resilient_provider = FallbackLLMProvider(primary=failing_primary, fallback=working_fallback)

    with patch("app.services.copilot.copilot_agent.get_llm_provider", return_value=resilient_provider):
        response = await client.post(
            "/api/v1/copilot/analyze",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "transcription": "Patient reports exertional angina symptoms.",
                "patient_name": "Amit Kumar",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "completed"
        assert data["requires_human_fallback"] is False
        assert data["ai_metadata"]["provider"] == "gemini"
        assert data["ai_metadata"]["fallback_used"] is True
        assert data["data"]["soap"]["assessment"]["primary_diagnosis"] != ""


@pytest.mark.asyncio
async def test_copilot_api_total_outage_human_fallback(client: AsyncClient, test_doctor: User):
    """Test 6: Total provider outage triggers safe human review fallback envelope."""
    token = create_access_token(data={"sub": str(test_doctor.user_id)})

    failing_primary = MockLLMProvider("nvidia", simulate_failure=True)
    failing_fallback = MockLLMProvider("gemini", simulate_failure=True)
    resilient_provider = FallbackLLMProvider(primary=failing_primary, fallback=failing_fallback)

    with patch("app.services.copilot.copilot_agent.get_llm_provider", return_value=resilient_provider):
        response = await client.post(
            "/api/v1/copilot/analyze",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "transcription": "Patient reports severe chest pain.",
                "chief_complaint": "Acute Chest Pain",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "fallback_to_human"
        assert data["requires_human_fallback"] is True
        assert data["ai_metadata"]["provider"] == "manual"
        assert data["fallback_reason"] is not None
        assert "plan" in data["data"]["soap"]


@pytest.mark.asyncio
async def test_copilot_rbac_protection(client: AsyncClient, test_patient: User):
    """Test 7: Patient role is forbidden from triggering doctor copilot."""
    token = create_access_token(data={"sub": str(test_patient.user_id)})

    response = await client.post(
        "/api/v1/copilot/analyze",
        headers={"Authorization": f"Bearer {token}"},
        json={"transcription": "Unauthorized test call"},
    )
    assert response.status_code == 403

    # Unauthenticated
    unauth_response = await client.post(
        "/api/v1/copilot/analyze",
        json={"transcription": "Unauthorized test call"},
    )
    assert unauth_response.status_code == 401


@pytest.mark.asyncio
async def test_copilot_providers_status(client: AsyncClient, test_doctor: User):
    """Test 8: GET /api/v1/copilot/providers returns registry health status."""
    token = create_access_token(data={"sub": str(test_doctor.user_id)})

    response = await client.get(
        "/api/v1/copilot/providers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "active_llm" in data
    assert "llm_providers" in data
    assert "failover_ready" in data
