from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TaskState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    name: str
    status: TaskStatus
    created_at: str
    updated_at: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class SystemLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    log_id: str
    timestamp: str
    level: LogLevel
    component: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_concurrent_tasks: int = Field(default=5, ge=1)
    sandbox_timeout_seconds: int = Field(default=30, ge=1)
    rag_top_k: int = Field(default=5, ge=1)
    log_level: LogLevel = Field(default=LogLevel.INFO)
    security_strict_mode: bool = Field(default=True)


class SecurityIncident(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str
    timestamp: str
    alert_type: str
    severity: SeverityLevel
    source_component: str
    description: str
    raw_payload: Dict[str, Any] = Field(default_factory=dict)
    resolved: bool = False


class AppState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_tasks: List[TaskState] = Field(default_factory=list)
    system_logs: List[SystemLog] = Field(default_factory=list)
    user_config: UserConfig = Field(default_factory=UserConfig)
    security_incidents: List[SecurityIncident] = Field(default_factory=list)


# Engine API Contract Models
class ContextRetrievalRequest(BaseModel):
    query: str
    top_k: int = 5
    filters: Optional[Dict[str, Any]] = None


class ContextRetrievalResponse(BaseModel):
    status: str
    query: str
    results: List[Dict[str, Any]] = Field(default_factory=list)
    message: str


class SandboxExecutionRequest(BaseModel):
    code: str
    timeout: int = 30
    environment_vars: Optional[Dict[str, str]] = None


class SandboxExecutionResponse(BaseModel):
    status: str
    stdout: str
    stderr: str
    exit_code: int
    execution_time_seconds: float
