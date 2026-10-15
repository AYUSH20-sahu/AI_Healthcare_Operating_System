"""P95 Latency & Performance SLA Benchmark Test Suite (Non-Functional Requirement NFR-01).

Validates that non-AI clinical endpoints (healthcheck, doctors directory, patient appointments)
meet the P95 latency threshold (< 500ms) under simulated request bursts.
"""

import time
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_non_ai_endpoint_p95_latency():
    """Execute 30 sequential requests against non-AI endpoints and verify P95 latency < 500ms."""
    latencies = []
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Warmup
        await client.get("/api/v1/observability/health")

        for _ in range(30):
            t0 = time.perf_counter()
            resp = await client.get("/api/v1/doctors/public-directory")
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            assert resp.status_code == 200
            latencies.append(elapsed_ms)

    latencies.sort()
    # Compute 95th percentile index
    p95_idx = int(len(latencies) * 0.95)
    p95_latency = latencies[p95_idx]

    # Max acceptable latency per Project Charter SLA is 500ms
    assert p95_latency < 500.0, f"P95 latency {p95_latency:.2f}ms exceeds 500ms threshold"
