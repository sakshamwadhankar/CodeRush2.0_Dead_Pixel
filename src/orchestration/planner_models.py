from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class ActionType(str, Enum):
    RAG_RETRIEVAL = "rag_retrieval"
    CODE_EXECUTION = "code_execution"
    BROWSER_SCRAPE = "browser_scrape"
    SYNTHESIS = "synthesis"


class SubTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subtask_id: str
    subquestion: str
    action_type: ActionType
    target_evidence: str
    confidence_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    code_snippet: Optional[str] = None
    status: str = Field(default="pending")


class TaskGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    subtasks: List[SubTask] = Field(default_factory=list)
    stop_condition: str = Field(default="Sufficient evidence acquired or confidence target reached")
    overall_confidence_target: float = Field(default=0.85, ge=0.0, le=1.0)


class DraftReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    executive_summary: str
    key_findings: List[str] = Field(default_factory=list)
    evidence_citations: List[Dict[str, Any]] = Field(default_factory=list)
    compiled_markdown: str
