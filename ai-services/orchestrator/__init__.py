"""Orchestrator service for AI-HOS.

Routes tasks to appropriate agents with timeout, retry, and fallback-to-human logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
import asyncio
import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Supported task types for the orchestrator."""
    SCRIBE = "scribe"
    PRESCRIPTION_DRAFT = "prescription_draft"
    INTAKE = "intake"
    TRIAGE = "triage"


class TaskStatus(Enum):
    """Status of a task execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    FALLBACK_TO_HUMAN = "fallback_to_human"


@dataclass
class TaskRequest:
    """Request to execute a task."""
    task_type: TaskType
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_backoff_base: float = 1.0  # seconds


@dataclass
class TaskResult:
    """Result of a task execution."""
    task_type: TaskType
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    attempts: int = 0
    total_time_seconds: float = 0.0
    fallback_triggered: bool = False


class AgentBase(ABC):
    """Base class for all agents."""
    
    @property
    @abstractmethod
    def task_type(self) -> TaskType:
        """Return the task type this agent handles."""
        pass
    
    @abstractmethod
    async def execute(self, payload: dict[str, Any]) -> Any:
        """Execute the agent's task."""
        pass


class Orchestrator:
    """Orchestrator service that routes tasks to agents with retry/fallback logic."""
    
    def __init__(
        self,
        default_timeout: float = 30.0,
        default_max_retries: int = 3,
        default_backoff_base: float = 1.0,
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
    
    def get_agent(self, task_type: TaskType) -> Optional[AgentBase]:
        """Get the agent for a task type."""
        return self._agents.get(task_type)
    
    def list_task_types(self) -> list[TaskType]:
        """List all registered task types."""
        return list(self._agents.keys())
    
    async def execute_task(self, request: TaskRequest) -> TaskResult:
        """Execute a task with timeout, retry, and fallback logic."""
        start_time = time.time()
        agent = self._agents.get(request.task_type)
        
        if agent is None:
            return TaskResult(
                task_type=request.task_type,
                status=TaskStatus.FAILED,
                error=f"No agent registered for task type: {request.task_type.value}",
                total_time_seconds=time.time() - start_time,
            )
        
        timeout = request.timeout_seconds or self._default_timeout
        max_retries = request.max_retries if request.max_retries is not None else self._default_max_retries
        backoff_base = request.retry_backoff_base or self._default_backoff_base
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            request.attempts = attempt + 1
            logger.info(f"Executing task {request.task_type.value}, attempt {attempt + 1}/{max_retries + 1}")
            
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    agent.execute(request.payload),
                    timeout=timeout,
                )
                
                return TaskResult(
                    task_type=request.task_type,
                    status=TaskStatus.COMPLETED,
                    result=result,
                    attempts=attempt + 1,
                    total_time_seconds=time.time() - start_time,
                )
            
            except asyncio.TimeoutError:
                last_error = f"Task timed out after {timeout} seconds"
                logger.warning(f"Task {request.task_type.value} timed out on attempt {attempt + 1}")
            
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Task {request.task_type.value} failed on attempt {attempt + 1}: {e}")
            
            # If not the last attempt, wait with exponential backoff
            if attempt < max_retries:
                backoff_time = backoff_base * (2 ** attempt)
                logger.info(f"Retrying in {backoff_time} seconds...")
                await asyncio.sleep(backoff_time)
        
        # All retries exhausted - fallback to human review
        logger.error(f"Task {request.task_type.value} failed after {max_retries + 1} attempts. Falling back to human review.")
        self._human_review_queue.append(request)
        
        return TaskResult(
            task_type=request.task_type,
            status=TaskStatus.FALLBACK_TO_HUMAN,
            error=last_error,
            attempts=max_retries + 1,
            total_time_seconds=time.time() - start_time,
            fallback_triggered=True,
        )
    
    def get_human_review_queue(self) -> list[TaskRequest]:
        """Get tasks that need human review."""
        return self._human_review_queue.copy()
    
    def clear_human_review_queue(self) -> None:
        """Clear the human review queue."""
        self._human_review_queue.clear()


# Global orchestrator instance
orchestrator = Orchestrator()


def get_orchestrator() -> Orchestrator:
    """Get the global orchestrator instance."""
    return orchestrator