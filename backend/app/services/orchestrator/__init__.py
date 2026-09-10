"""Orchestrator service for AI-HOS.

Routes tasks to appropriate agents with timeout, exponential backoff retries,
and fallback-to-human review escalation when providers or agents fail.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("ai_orchestrator")


class TaskType(str, Enum):
    """Supported task types for the orchestrator."""
    COPILOT = "copilot"
    SCRIBE = "scribe"
    PRESCRIPTION_DRAFT = "prescription_draft"
    INTAKE = "intake"
    TRIAGE = "triage"


class TaskStatus(str, Enum):
    """Execution status of an orchestration task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    FALLBACK_TO_HUMAN = "fallback_to_human"


@dataclass
class TaskRequest:
    """Request envelope submitted to the orchestrator."""
    task_type: TaskType
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_backoff_base: float = 0.5  # seconds


@dataclass
class TaskResult:
    """Standardized response produced by the orchestrator."""
    task_type: TaskType
    status: TaskStatus
    result: Any | None = None
    error: str | None = None
    attempts: int = 0
    total_time_seconds: float = 0.0
    fallback_triggered: bool = False
    ai_metadata: dict[str, Any] = field(default_factory=dict)


class AgentBase(ABC):
    """Base abstract class for all specialized clinical agents."""

    @property
    @abstractmethod
    def task_type(self) -> TaskType:
        """Return the task type this agent handles."""

    @abstractmethod
    async def execute(self, payload: dict[str, Any]) -> Any:
        """Execute the agent task."""


class Orchestrator:
    """Orchestration engine that routes tasks to agents with timeout, retry, and human fallback."""

    def __init__(
        self,
        default_timeout: float = 30.0,
        default_max_retries: int = 2,
        default_backoff_base: float = 0.5,
    ):
        self._agents: dict[TaskType, AgentBase] = {}
        self._default_timeout = default_timeout
        self._default_max_retries = default_max_retries
        self._default_backoff_base = default_backoff_base
        self._human_review_queue: list[TaskRequest] = []

    def register_agent(self, agent: AgentBase) -> None:
        """Register an agent for a task type."""
        self._agents[agent.task_type] = agent
        logger.info(f"Registered agent for task type: {agent.task_type.value}")

    def get_agent(self, task_type: TaskType) -> AgentBase | None:
        """Retrieve registered agent for task type."""
        return self._agents.get(task_type)

    def list_task_types(self) -> list[TaskType]:
        """List registered task types."""
        return list(self._agents.keys())

    async def execute_task(self, request: TaskRequest) -> TaskResult:
        """Execute task with enforced timeout, retry with backoff, and human fallback escalation."""
        start_time = time.perf_counter()
        agent = self._agents.get(request.task_type)

        if agent is None:
            total_time = time.perf_counter() - start_time
            return TaskResult(
                task_type=request.task_type,
                status=TaskStatus.FAILED,
                error=f"No agent registered for task type: {request.task_type.value}",
                total_time_seconds=round(total_time, 3),
            )

        timeout = request.timeout_seconds if request.timeout_seconds is not None else self._default_timeout
        max_retries = request.max_retries if request.max_retries is not None else self._default_max_retries
        backoff_base = request.retry_backoff_base if request.retry_backoff_base is not None else self._default_backoff_base

        last_error = None
        total_attempts = 0

        for attempt in range(max_retries + 1):
            total_attempts = attempt + 1
            logger.info(f"Executing task [{request.task_type.value}], attempt {total_attempts}/{max_retries + 1}")

            try:
                # Execute agent with strict timeout
                result = await asyncio.wait_for(
                    agent.execute(request.payload),
                    timeout=timeout,
                )

                total_time = time.perf_counter() - start_time

                # Extract metadata if returned by agent
                ai_metadata = getattr(result, "ai_metadata", {})
                fallback_used = getattr(result, "fallback_used", False) or ai_metadata.get("fallback_used", False)

                return TaskResult(
                    task_type=request.task_type,
                    status=TaskStatus.COMPLETED,
                    result=result,
                    attempts=total_attempts,
                    total_time_seconds=round(total_time, 3),
                    fallback_triggered=fallback_used,
                    ai_metadata=ai_metadata,
                )

            except asyncio.TimeoutError:
                last_error = f"Task timed out after {timeout} seconds"
                logger.warning(f"Task [{request.task_type.value}] timed out on attempt {total_attempts}")

            except Exception as exc:
                last_error = str(exc)
                logger.warning(f"Task [{request.task_type.value}] failed on attempt {total_attempts}: {exc}")

            # If retries remain, back off exponentially
            if attempt < max_retries:
                backoff_time = backoff_base * (2 ** attempt)
                logger.info(f"Retrying task [{request.task_type.value}] in {backoff_time:.2f}s...")
                await asyncio.sleep(backoff_time)

        # All retries exhausted -> Escalate to human review fallback
        total_time = time.perf_counter() - start_time
        logger.error(
            f"Task [{request.task_type.value}] failed after {total_attempts} attempts. "
            f"Escalating to human review queue. Last error: {last_error}"
        )
        self._human_review_queue.append(request)

        return TaskResult(
            task_type=request.task_type,
            status=TaskStatus.FALLBACK_TO_HUMAN,
            error=last_error,
            attempts=total_attempts,
            total_time_seconds=round(total_time, 3),
            fallback_triggered=True,
            ai_metadata={
                "provider": "manual",
                "model": "clinician-fallback",
                "fallback_used": True,
                "reason": last_error,
            },
        )

    def get_human_review_queue(self) -> list[TaskRequest]:
        """Return requests pending manual clinician review."""
        return self._human_review_queue.copy()

    def clear_human_review_queue(self) -> None:
        """Clear the human review queue."""
        self._human_review_queue.clear()


orchestrator = Orchestrator()


def get_orchestrator() -> Orchestrator:
    """Return the global orchestrator singleton."""
    return orchestrator
