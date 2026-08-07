# Orchestration & Control Layer

The orchestrator is the cognitive brain of the Aegis system. It manages LLM interactions, task decomposition, and deterministic state transitions.

## The Model Gateway (`src/orchestration/gateway.py`)
- Unified interface standardizing interactions with **Google Gemini (API)** and **Ollama (Local)**.
- **Strict Pydantic Enforcement**: The gateway forcefully injects Pydantic JSON schemas into the System Prompts. If the model fails to return a valid JSON object, the Gateway executes automated retry logic, stripping out markdown formatting (` ```json ` blocks) dynamically.

## The Planner Engine (`src/orchestration/planner.py`)
- Utilizes ReAct (Reasoning and Acting) methodologies.
- The Engine queries the LLM to output a `TaskGraph` containing `SubTask` structures.
- **Idempotency**: The Planner loops through the graph. By accumulating `previous_results`, the Engine can pause (for user approval) and resume seamlessly without re-executing identical subtasks, saving massive API latency and costs.

## Deterministic State Ledger (`src/orchestration/state_controller.py`)
- Streamlit UIs are inherently stateless and re-run top-to-bottom on every interaction.
- To prevent this from crashing autonomous operations, the `StateController` forces all components to read from and write to a physical JSON ledger (`config/state.json`).
- If the app crashes, it can instantly be rebooted, restoring the exact step of the pipeline it died on.
