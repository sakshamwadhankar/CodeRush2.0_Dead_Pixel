# High-End Workflow & Flowchart

This document illustrates the precise end-to-end operational flow of Aegis Research OS. The architecture operates entirely on a Zero-Trust, State-Driven Loop.

## Workflow Flowchart

```mermaid
graph TD
    A[User Input via Streamlit UI] --> B[StateController Clears Old State]
    B --> C[PlannerEngine Receives Query]
    C --> D[ModelGateway Generates Prompt]
    D --> E[LLM Returns JSON TaskGraph]
    E --> F{Iterate TaskGraph}
    
    F -->|RAG_RETRIEVAL| G[HybridRAGEngine]
    F -->|CODE_EXECUTION / SYNTHESIS| H{Check .env Strict Approval}
    
    H -->|STRICT=True| I[Set PENDING_APPROVAL in state.json]
    I --> J((UI Waits for User Click))
    J -->|User Approves| K[Execute Sensitive Task]
    
    K -->|If Code| L[FastAPI Sandbox POST Request]
    L --> M[Docker Ephemeral Execution]
    M --> N[Return STDOUT/STDERR]
    
    G --> O[Inject Claims into EvidenceGraph]
    N --> O
    
    O --> P{More Subtasks?}
    P -->|Yes| F
    P -->|No| Q[Planner Drafts Markdown Report]
    
    Q --> R[DynamicCitationCompiler Parses Draft]
    R --> S[NetworkX Graph Verifies Citations]
    S --> T[Generate citations.json]
    T --> U[Streamlit UI Renders Final Report]
```

## Step-by-Step Execution Sequence

1. **Initialization (`launcher.py`)**: A dual-process boot sequence starts both the Streamlit UI (Port 8501) and the FastAPI Sandbox Microservice (Port 8000).
2. **Cognitive Breakdown**: When a query is submitted, `src/orchestration/planner.py` uses `src/orchestration/gateway.py` to force an LLM (Gemini/Ollama) to strictly adhere to Pydantic schemas. This generates a `TaskGraph` composed of explicitly typed subtasks.
3. **Execution Routing**: The loop iterates through the tasks. Non-sensitive tasks execute immediately. Sensitive tasks trigger the HITL (Human-in-the-Loop) circuit breaker, halting the orchestrator until the UI sends an approval signal to `config/state.json`.
4. **Data Aggregation**: All task outputs (whether web scraping text, API code execution logs, or vectorized chunks) are fed blindly into the `EvidenceGraph`.
5. **Synthesis & Alignment**: The `PlannerEngine` requests the LLM to synthesize the aggregated evidence. The `DynamicCitationCompiler` then acts as the ultimate verifier, ensuring that every sentence in the final Markdown can trace its roots back to the `EvidenceGraph` via `[1]` citation tags.
