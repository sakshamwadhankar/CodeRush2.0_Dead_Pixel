import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

from backend.schema.state_models import (
    AppState,
    TaskState,
    TaskStatus,
    SystemLog,
    LogLevel,
    UserConfig,
    SecurityIncident,
    SeverityLevel,
    ContextRetrievalRequest,
    ContextRetrievalResponse,
    SandboxExecutionRequest,
    SandboxExecutionResponse,
)


class StateController:
    """
    State Controller for Aegis Research OS.
    Manages loading, updating, persisting, and enforcing JSON schema validation on state.json.
    Establishes interface contracts for external engine modules (RAG and Sandbox).
    """

    def __init__(self, state_filepath: Optional[str] = None):
        if state_filepath:
            self.state_file = Path(state_filepath)
        else:
            default_path = (
                Path(__file__).resolve().parent.parent / "config" / "state.json"
            )
            self.state_file = default_path

        self._state: AppState = self.load_state()

    def _get_iso_timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def load_state(self) -> AppState:
        """
        Reads and parses state.json into a strictly schema-enforced AppState object.
        If file does not exist, initializes default AppState and saves it.
        """
        if not self.state_file.exists():
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            default_state = AppState()
            self.save_state(default_state)
            return default_state

        with open(self.state_file, "r", encoding="utf-8") as f:
            raw_data = f.read()

        # Strict validation using Pydantic AppState schema
        self._state = AppState.model_validate_json(raw_data)
        return self._state

    def save_state(self, state: Optional[AppState] = None) -> None:
        """
        Validates and persists the current state into state.json.
        """
        if state is not None:
            self._state = state

        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w", encoding="utf-8") as f:
            f.write(self._state.model_dump_json(indent=2))

    def get_state(self) -> AppState:
        """
        Returns the current in-memory AppState instance.
        """
        return self._state

    def add_task(
        self, name: str, payload: Optional[Dict[str, Any]] = None, task_id: Optional[str] = None
    ) -> TaskState:
        """
        Creates a new task entry in active_tasks.
        """
        now = self._get_iso_timestamp()
        new_id = task_id or f"task_{uuid.uuid4().hex[:8]}"
        task = TaskState(
            task_id=new_id,
            name=name,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            payload=payload or {},
        )
        self._state.active_tasks.append(task)
        self.log_system_event(
            level=LogLevel.INFO,
            component="StateController",
            message=f"Added new task '{name}' ({new_id})",
            metadata={"task_id": new_id},
        )
        self.save_state()
        return task

    def update_task_status(self, task_id: str, status: TaskStatus) -> TaskState:
        """
        Updates the status of an existing task by task_id.
        """
        for task in self._state.active_tasks:
            if task.task_id == task_id:
                task.status = status
                task.updated_at = self._get_iso_timestamp()
                self.log_system_event(
                    level=LogLevel.INFO,
                    component="StateController",
                    message=f"Updated task {task_id} status to {status.value}",
                    metadata={"task_id": task_id, "new_status": status.value},
                )
                self.save_state()
                return task
        raise KeyError(f"Task with task_id '{task_id}' not found in state.")

    def log_system_event(
        self,
        level: LogLevel,
        component: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SystemLog:
        """
        Appends a system log entry into system_logs.
        """
        log_entry = SystemLog(
            log_id=f"log_{uuid.uuid4().hex[:8]}",
            timestamp=self._get_iso_timestamp(),
            level=level,
            component=component,
            message=message,
            metadata=metadata or {},
        )
        self._state.system_logs.append(log_entry)
        return log_entry

    def trigger_security_alert(
        self,
        alert_type: str,
        severity: SeverityLevel,
        source_component: str,
        description: str,
        raw_payload: Optional[Dict[str, Any]] = None,
    ) -> SecurityIncident:
        """
        Flags a critical security incident (e.g. NeMo Guardrails prompt injection alert).
        """
        incident = SecurityIncident(
            incident_id=f"sec_{uuid.uuid4().hex[:8]}",
            timestamp=self._get_iso_timestamp(),
            alert_type=alert_type,
            severity=severity,
            source_component=source_component,
            description=description,
            raw_payload=raw_payload or {},
            resolved=False,
        )
        self._state.security_incidents.append(incident)
        self.log_system_event(
            level=LogLevel.CRITICAL if severity == SeverityLevel.CRITICAL else LogLevel.WARNING,
            component=source_component,
            message=f"SECURITY ALERT [{severity.value}]: {alert_type} - {description}",
            metadata={"incident_id": incident.incident_id, "alert_type": alert_type},
        )
        self.save_state()
        return incident

    def update_user_config(self, updates: Dict[str, Any]) -> UserConfig:
        """
        Updates user configuration settings with strict validation.
        """
        current_dict = self._state.user_config.model_dump()
        current_dict.update(updates)
        new_config = UserConfig.model_validate(current_dict)
        self._state.user_config = new_config
        self.log_system_event(
            level=LogLevel.INFO,
            component="StateController",
            message="User configuration updated",
            metadata={"updated_fields": list(updates.keys())},
        )
        self.save_state()
        return new_config


# Base API Engine Interface Endpoints (Developer B & C Mock Contracts)

def retrieve_context(request: ContextRetrievalRequest) -> ContextRetrievalResponse:
    """
    Shared API Endpoint Contract for Developer C (RAG Engine).
    Provides offline verification baseline for RAG context retrieval requests.
    """
    if not request.query.strip():
        return ContextRetrievalResponse(
            status="error",
            query=request.query,
            results=[],
            message="Invalid query string: query cannot be empty.",
        )

    # Mock contract response return for offline verification loop
    mock_results = [
        {
            "document_id": "doc_contract_001",
            "content": f"Mock context snippet for query: '{request.query}'",
            "score": 0.95,
        }
    ]
    return ContextRetrievalResponse(
        status="success",
        query=request.query,
        results=mock_results[: request.top_k],
        message="Offline contract response successfully returned.",
    )


def execute_sandbox(request: SandboxExecutionRequest) -> SandboxExecutionResponse:
    """
    Shared API Endpoint Contract for Developer B (Sandbox Engine).
    Provides offline verification baseline for Python code execution requests.
    """
    if not request.code.strip():
        return SandboxExecutionResponse(
            status="failed",
            stdout="",
            stderr="Empty code snippet provided.",
            exit_code=1,
            execution_time_seconds=0.0,
        )

    # Mock contract response return for offline verification loop
    return SandboxExecutionResponse(
        status="completed",
        stdout="[Mock Sandbox Execution Output]\nProgram finished with code 0.",
        stderr="",
        exit_code=0,
        execution_time_seconds=0.012,
    )
