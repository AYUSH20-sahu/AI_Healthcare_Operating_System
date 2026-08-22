"""Tests for Orchestrator Service."""

import asyncio
import sys
import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Add the ai-services directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from orchestrator import (
    TaskType,
    TaskStatus,
    TaskRequest,
    TaskResult,
    AgentBase,
    Orchestrator,
    get_orchestrator,
)


class MockAgent(AgentBase):
    """Mock agent for testing."""
    
    def __init__(self, task_type: TaskType, should_succeed: bool = True, delay: float = 0.0, result: Any = None):
        self._task_type = task_type
        self._should_succeed = should_succeed
        self._delay = delay
        self._result = result or {"status": "success"}
        self.execute_called = 0
    
    @property
    def task_type(self) -> TaskType:
        return self._task_type
    
    async def execute(self, payload: dict[str, Any]) -> Any:
        self.execute_called += 1
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        if not self._should_succeed:
            raise Exception("Agent execution failed")
        return self._result


class TestTaskRequest:
    """Tests for TaskRequest."""

    def test_default_values(self):
        """Test default values for TaskRequest."""
        request = TaskRequest(task_type=TaskType.SCRIBE, payload={"test": "data"})
        
        assert request.task_type == TaskType.SCRIBE
        assert request.payload == {"test": "data"}
        assert request.metadata == {}
        assert request.timeout_seconds == 30.0
        assert request.max_retries == 3
        assert request.retry_backoff_base == 1.0

    def test_custom_values(self):
        """Test custom values for TaskRequest."""
        request = TaskRequest(
            task_type=TaskType.PRESCRIPTION_DRAFT,
            payload={"note": "test"},
            metadata={"user_id": 123},
            timeout_seconds=60.0,
            max_retries=5,
            retry_backoff_base=2.0,
        )
        
        assert request.timeout_seconds == 60.0
        assert request.max_retries == 5
        assert request.retry_backoff_base == 2.0


class TestTaskResult:
    """Tests for TaskResult."""

    def test_completed_result(self):
        """Test completed task result."""
        result = TaskResult(
            task_type=TaskType.SCRIBE,
            status=TaskStatus.COMPLETED,
            result={"note": "test"},
            attempts=1,
            total_time_seconds=1.5,
        )
        
        assert result.status == TaskStatus.COMPLETED
        assert result.result == {"note": "test"}
        assert result.error is None
        assert result.fallback_triggered is False

    def test_failed_result(self):
        """Test failed task result."""
        result = TaskResult(
            task_type=TaskType.SCRIBE,
            status=TaskStatus.FAILED,
            error="Something went wrong",
            attempts=3,
            total_time_seconds=5.0,
        )
        
        assert result.status == TaskStatus.FAILED
        assert result.error == "Something went wrong"
        assert result.result is None

    def test_fallback_result(self):
        """Test fallback to human result."""
        result = TaskResult(
            task_type=TaskType.SCRIBE,
            status=TaskStatus.FALLBACK_TO_HUMAN,
            error="All retries failed",
            attempts=4,
            total_time_seconds=10.0,
            fallback_triggered=True,
        )
        
        assert result.status == TaskStatus.FALLBACK_TO_HUMAN
        assert result.fallback_triggered is True


class TestOrchestrator:
    """Tests for Orchestrator."""

    @pytest_asyncio.fixture
    async def orchestrator(self):
        """Create a fresh orchestrator for each test."""
        return Orchestrator(default_timeout=1.0, default_max_retries=2, default_backoff_base=0.1)

    @pytest.mark.asyncio
    async def test_register_agent(self, orchestrator):
        """Test registering an agent."""
        agent = MockAgent(TaskType.SCRIBE)
        orchestrator.register_agent(agent)
        
        assert orchestrator.get_agent(TaskType.SCRIBE) is agent
        assert TaskType.SCRIBE in orchestrator.list_task_types()

    @pytest.mark.asyncio
    async def test_get_unregistered_agent(self, orchestrator):
        """Test getting an unregistered agent returns None."""
        assert orchestrator.get_agent(TaskType.SCRIBE) is None

    @pytest.mark.asyncio
    async def test_execute_task_success(self, orchestrator):
        """Test successful task execution."""
        agent = MockAgent(TaskType.SCRIBE, should_succeed=True, result={"note": "Clinical note draft"})
        orchestrator.register_agent(agent)
        
        request = TaskRequest(task_type=TaskType.SCRIBE, payload={"audio_id": "123"})
        result = await orchestrator.execute_task(request)
        
        assert result.status == TaskStatus.COMPLETED
        assert result.result == {"note": "Clinical note draft"}
        assert result.attempts == 1
        assert agent.execute_called == 1

    @pytest.mark.asyncio
    async def test_execute_task_no_agent(self, orchestrator):
        """Test task execution with no registered agent."""
        request = TaskRequest(task_type=TaskType.SCRIBE, payload={})
        result = await orchestrator.execute_task(request)
        
        assert result.status == TaskStatus.FAILED
        assert "No agent registered" in result.error

    @pytest.mark.asyncio
    async def test_execute_task_timeout(self, orchestrator):
        """Test task execution timeout."""
        # Agent that takes longer than timeout
        agent = MockAgent(TaskType.SCRIBE, should_succeed=True, delay=2.0)
        orchestrator.register_agent(agent)
        
        request = TaskRequest(task_type=TaskType.SCRIBE, payload={}, timeout_seconds=0.5, max_retries=1)
        result = await orchestrator.execute_task(request)
        
        assert result.status == TaskStatus.FALLBACK_TO_HUMAN
        assert result.fallback_triggered is True
        assert result.attempts == 2  # Initial + 1 retry

    @pytest.mark.asyncio
    async def test_execute_task_retry_on_failure(self, orchestrator):
        """Test task retries on failure."""
        agent = MockAgent(TaskType.SCRIBE, should_succeed=False)
        orchestrator.register_agent(agent)
        
        request = TaskRequest(task_type=TaskType.SCRIBE, payload={}, max_retries=2, retry_backoff_base=0.05)
        result = await orchestrator.execute_task(request)
        
        assert result.status == TaskStatus.FALLBACK_TO_HUMAN
        assert result.fallback_triggered is True
        assert result.attempts == 3  # Initial + 2 retries
        assert agent.execute_called == 3

    @pytest.mark.asyncio
    async def test_execute_task_succeeds_on_retry(self, orchestrator):
        """Test task succeeds on retry after initial failure."""
        call_count = 0
        
        class FlakyAgent(MockAgent):
            async def execute(self, payload):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise Exception("First attempt fails")
                return await super().execute(payload)
        
        agent = FlakyAgent(TaskType.SCRIBE, should_succeed=True)
        orchestrator.register_agent(agent)
        
        request = TaskRequest(task_type=TaskType.SCRIBE, payload={}, max_retries=2, retry_backoff_base=0.05)
        result = await orchestrator.execute_task(request)
        
        assert result.status == TaskStatus.COMPLETED
        assert result.attempts == 2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_execute_task_timeout_then_succeeds_on_retry(self, orchestrator):
        """Test task times out first, then succeeds on retry."""
        call_count = 0
        
        class SlowThenFastAgent(AgentBase):
            @property
            def task_type(self):
                return TaskType.SCRIBE
            
            async def execute(self, payload):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    await asyncio.sleep(2.0)  # Longer than timeout
                return {"result": "success"}
        
        agent = SlowThenFastAgent()
        orchestrator.register_agent(agent)
        
        request = TaskRequest(task_type=TaskType.SCRIBE, payload={}, timeout_seconds=0.5, max_retries=1, retry_backoff_base=0.05)
        result = await orchestrator.execute_task(request)
        
        assert result.status == TaskStatus.COMPLETED
        assert result.attempts == 2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_human_review_queue(self, orchestrator):
        """Test human review queue collects failed tasks."""
        agent = MockAgent(TaskType.SCRIBE, should_succeed=False)
        orchestrator.register_agent(agent)
        
        request = TaskRequest(task_type=TaskType.SCRIBE, payload={"data": "test"}, max_retries=1)
        await orchestrator.execute_task(request)
        
        queue = orchestrator.get_human_review_queue()
        assert len(queue) == 1
        assert queue[0].payload == {"data": "test"}
        assert queue[0].task_type == TaskType.SCRIBE

    @pytest.mark.asyncio
    async def test_clear_human_review_queue(self, orchestrator):
        """Test clearing human review queue."""
        agent = MockAgent(TaskType.SCRIBE, should_succeed=False)
        orchestrator.register_agent(agent)
        
        request = TaskRequest(task_type=TaskType.SCRIBE, payload={}, max_retries=1)
        await orchestrator.execute_task(request)
        
        assert len(orchestrator.get_human_review_queue()) == 1
        
        orchestrator.clear_human_review_queue()
        assert len(orchestrator.get_human_review_queue()) == 0

    @pytest.mark.asyncio
    async def test_multiple_task_types(self, orchestrator):
        """Test orchestrator with multiple task types."""
        scribe_agent = MockAgent(TaskType.SCRIBE, result={"type": "scribe"})
        prescription_agent = MockAgent(TaskType.PRESCRIPTION_DRAFT, result={"type": "prescription"})
        
        orchestrator.register_agent(scribe_agent)
        orchestrator.register_agent(prescription_agent)
        
        # Execute scribe task
        scribe_result = await orchestrator.execute_task(
            TaskRequest(task_type=TaskType.SCRIBE, payload={})
        )
        assert scribe_result.result == {"type": "scribe"}
        
        # Execute prescription task
        prescription_result = await orchestrator.execute_task(
            TaskRequest(task_type=TaskType.PRESCRIPTION_DRAFT, payload={})
        )
        assert prescription_result.result == {"type": "prescription"}

    @pytest.mark.asyncio
    async def test_custom_timeout_per_request(self, orchestrator):
        """Test custom timeout per request overrides default."""
        agent = MockAgent(TaskType.SCRIBE, should_succeed=True, delay=0.5)
        orchestrator.register_agent(agent)
        
        # Request with longer timeout should succeed
        request = TaskRequest(task_type=TaskType.SCRIBE, payload={}, timeout_seconds=2.0)
        result = await orchestrator.execute_task(request)
        assert result.status == TaskStatus.COMPLETED
        
        # Request with shorter timeout should timeout
        request = TaskRequest(task_type=TaskType.SCRIBE, payload={}, timeout_seconds=0.1, max_retries=0)
        result = await orchestrator.execute_task(request)
        assert result.status == TaskStatus.FALLBACK_TO_HUMAN


class TestGlobalOrchestrator:
    """Tests for global orchestrator instance."""

    def test_get_orchestrator(self):
        """Test getting global orchestrator."""
        orch = get_orchestrator()
        assert isinstance(orch, Orchestrator)

    def test_global_orchestrator_is_singleton(self):
        """Test global orchestrator is singleton."""
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()
        assert orch1 is orch2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])