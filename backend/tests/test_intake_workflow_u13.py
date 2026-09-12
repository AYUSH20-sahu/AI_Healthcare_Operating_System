"""Automated Test Suite for Milestone U-13: AI Patient Intake & Symptom Collection.

Tests covered:
1. In-memory IntakeAgent execution directly via orchestrator.
2. Non-diagnostic and non-prescriptive safety guardrails.
3. Patient creates an intake session (POST /api/v1/intake/sessions).
4. Patient creates session with initial symptom message.
5. Patient recovers active intake session (GET /api/v1/intake/sessions/active).
6. Conversational turns & structured symptom extraction (POST /api/v1/intake/sessions/{id}/message).
7. Manual completion of intake session (POST /api/v1/intake/sessions/{id}/complete).
8. Session immutability once completed (400 Bad Request on new messages).
9. Cross-Patient Isolation (403 Forbidden on foreign session access & messaging).
10. Unauthenticated access protection (401 Unauthorized).
"""

import pytest
import pytest_asyncio
from datetime import date
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    IntakeSession,
    IntakeStatus,
    Patient,
    User,
    UserRole,
)
from app.services.auth.service import create_access_token, get_password_hash
from app.services.intake.intake_agent import IntakeAgent, IntakeAgentResult


@pytest_asyncio.fixture
async def patient_alice(db_session: AsyncSession):
    """Create Patient Alice."""
    user = User(
        email="alice.u13@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Alice Patient",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    patient = Patient(
        user_id=user.user_id,
        full_name="Alice Patient",
        email="alice.u13@test.com",
        date_of_birth=date(1993, 3, 10),
        gender="Female",
        phone="+91 98888 11111",
        abha_address="alice.u13@abdm",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(patient)
    return user, patient


@pytest_asyncio.fixture
async def patient_bob(db_session: AsyncSession):
    """Create Patient Bob."""
    user = User(
        email="bob.u13@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Bob Patient",
        role=UserRole.PATIENT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    patient = Patient(
        user_id=user.user_id,
        full_name="Bob Patient",
        email="bob.u13@test.com",
        date_of_birth=date(1989, 7, 22),
        gender="Male",
        phone="+91 98888 22222",
        abha_address="bob.u13@abdm",
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(patient)
    return user, patient


def auth_headers_for(user: User) -> dict[str, str]:
    token = create_access_token(data={"sub": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# 1. Agent In-Memory Execution & Guardrail Tests
# =============================================================================

@pytest.mark.asyncio
async def test_intake_agent_direct_execution():
    """Verify IntakeAgent executes in-memory without database access and returns structured symptoms."""
    agent = IntakeAgent()
    payload = {
        "patient_name": "Alice Patient",
        "gender": "Female",
        "messages": [],
        "new_message": "I have had a severe throbbing headache for 3 days, rated 8 out of 10, sensitive to light.",
    }

    result = await agent.execute(payload)
    assert isinstance(result, IntakeAgentResult)
    assert result.reply
    assert isinstance(result.structured_symptoms, dict)
    assert "headache" in str(result.structured_symptoms).lower() or "headache" in result.reply.lower()
    assert result.ai_confidence > 0
    assert result.basis


def test_intake_agent_guardrails_enforcement():
    """Verify guardrail sanitization rewrites diagnostic and prescriptive claims."""
    agent = IntakeAgent()

    # Test diagnostic interception
    bad_diag = "Based on what you said, you have migraine with aura."
    safe_diag = agent._enforce_guardrails(bad_diag)
    assert "you have" not in safe_diag.lower()

    # Test prescription interception
    bad_rx = "I prescribe 500mg paracetamol to take immediately."
    safe_rx = agent._enforce_guardrails(bad_rx)
    assert "i prescribe" not in safe_rx.lower()


# =============================================================================
# 2. REST API Lifecycle Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_intake_session_endpoint(async_client: AsyncClient, patient_alice):
    """Patient Alice creates an intake session."""
    user, pat = patient_alice
    headers = auth_headers_for(user)

    response = await async_client.post("/api/v1/intake/sessions", json={}, headers=headers)
    assert response.status_code == 201
    data = response.json()

    assert data["status"] == "in_progress"
    assert data["patient_id"] == str(pat.patient_id)
    assert len(data["messages"]) >= 1
    assert data["messages"][0]["role"] == "assistant"
    assert "intake assistant" in data["messages"][0]["content"].lower()


@pytest.mark.asyncio
async def test_create_intake_session_with_initial_message(async_client: AsyncClient, patient_alice):
    """Patient Alice creates an intake session providing an opening symptom statement."""
    user, pat = patient_alice
    headers = auth_headers_for(user)

    payload = {"initial_message": "Persistent dry cough for 4 days with mild throat irritation."}
    response = await async_client.post("/api/v1/intake/sessions", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()

    assert data["status"] in ("in_progress", "completed")
    # Must have initial greeting + patient message + assistant reply
    assert len(data["messages"]) >= 3
    assert data["messages"][1]["role"] == "patient"
    assert "cough" in data["messages"][1]["content"].lower()
    assert data["messages"][2]["role"] == "assistant"
    assert data["structured_symptoms"] is not None


@pytest.mark.asyncio
async def test_get_active_intake_session(async_client: AsyncClient, patient_alice):
    """Patient Alice recovers her active intake session."""
    user, pat = patient_alice
    headers = auth_headers_for(user)

    # Create active session
    create_res = await async_client.post("/api/v1/intake/sessions", json={}, headers=headers)
    created_id = create_res.json()["session_id"]

    # Retrieve active session
    active_res = await async_client.get("/api/v1/intake/sessions/active", headers=headers)
    assert active_res.status_code == 200
    active_data = active_res.json()
    assert active_data["session_id"] == created_id
    assert active_data["status"] == "in_progress"


@pytest.mark.asyncio
async def test_send_intake_message_turn(async_client: AsyncClient, patient_alice):
    """Patient Alice sends a message turn and receives structured symptom response."""
    user, pat = patient_alice
    headers = auth_headers_for(user)

    # Create session
    create_res = await async_client.post("/api/v1/intake/sessions", json={}, headers=headers)
    session_id = create_res.json()["session_id"]

    # Send message turn
    msg_res = await async_client.post(
        f"/api/v1/intake/sessions/{session_id}/message",
        json={"content": "The pain is about an 8 out of 10 and started 2 days ago."},
        headers=headers,
    )
    assert msg_res.status_code == 200
    msg_data = msg_res.json()

    assert msg_data["session_id"] == session_id
    assert msg_data["reply"]
    assert msg_data["structured_symptoms"]["severity"] == 8 or "8" in str(msg_data["structured_symptoms"])
    assert msg_data["ai_confidence"] > 0


@pytest.mark.asyncio
async def test_manual_complete_intake_session(async_client: AsyncClient, patient_alice):
    """Patient Alice manually completes and finalizes her intake session."""
    user, pat = patient_alice
    headers = auth_headers_for(user)

    create_res = await async_client.post("/api/v1/intake/sessions", json={}, headers=headers)
    session_id = create_res.json()["session_id"]

    complete_res = await async_client.post(
        f"/api/v1/intake/sessions/{session_id}/complete",
        json={"notes": "Ready for doctor consultation."},
        headers=headers,
    )
    assert complete_res.status_code == 200
    complete_data = complete_res.json()
    assert complete_data["status"] == "completed"
    assert complete_data["completed_at"] is not None


@pytest.mark.asyncio
async def test_cannot_post_message_to_completed_session(async_client: AsyncClient, patient_alice):
    """Posting messages to an already completed intake session fails with 400 Bad Request."""
    user, pat = patient_alice
    headers = auth_headers_for(user)

    create_res = await async_client.post("/api/v1/intake/sessions", json={}, headers=headers)
    session_id = create_res.json()["session_id"]

    # Complete it
    await async_client.post(f"/api/v1/intake/sessions/{session_id}/complete", headers=headers)

    # Attempt to send message
    fail_res = await async_client.post(
        f"/api/v1/intake/sessions/{session_id}/message",
        json={"content": "One more thing doctor..."},
        headers=headers,
    )
    assert fail_res.status_code == 400
    assert "completed" in fail_res.json()["detail"].lower()


# =============================================================================
# 3. Cross-Patient Isolation & Security Tests
# =============================================================================

@pytest.mark.asyncio
async def test_cross_patient_isolation(async_client: AsyncClient, patient_alice, patient_bob):
    """Bob cannot access or send messages to Alice's intake session (403 Forbidden)."""
    alice_user, _ = patient_alice
    bob_user, _ = patient_bob

    alice_headers = auth_headers_for(alice_user)
    bob_headers = auth_headers_for(bob_user)

    # Alice creates session
    create_res = await async_client.post("/api/v1/intake/sessions", json={}, headers=alice_headers)
    alice_session_id = create_res.json()["session_id"]

    # Bob tries to read Alice's session
    bob_read_res = await async_client.get(
        f"/api/v1/intake/sessions/{alice_session_id}",
        headers=bob_headers,
    )
    assert bob_read_res.status_code == 403

    # Bob tries to post a message to Alice's session
    bob_msg_res = await async_client.post(
        f"/api/v1/intake/sessions/{alice_session_id}/message",
        json={"content": "Malicious intrusion attempt"},
        headers=bob_headers,
    )
    assert bob_msg_res.status_code == 403

    # Bob tries to complete Alice's session
    bob_complete_res = await async_client.post(
        f"/api/v1/intake/sessions/{alice_session_id}/complete",
        headers=bob_headers,
    )
    assert bob_complete_res.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_blocked(async_client: AsyncClient):
    """Unauthenticated requests are rejected with 401 Unauthorized."""
    res_active = await async_client.get("/api/v1/intake/sessions/active")
    assert res_active.status_code == 401

    res_create = await async_client.post("/api/v1/intake/sessions", json={})
    assert res_create.status_code == 401
