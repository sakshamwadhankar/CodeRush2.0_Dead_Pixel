# Aegis Research OS: Comprehensive System Architecture

Aegis Research OS (AE-02) is an autonomous, self-evolving research agent designed with a focus on security, determinism, and evidence-based synthesis. The system operates on a zero-trust model, strictly separating the "brain" (the orchestration and planning layer) from the "hands" (the execution and sandbox layer). 

This document outlines the entire architecture of the project from start to finish, mapping every single directory, file, and sub-module.

---

## 1. Complete Project Structure

```text
CodeRush2.0_Dead_Pixel/
├── config/                     # Configuration and deterministic state files
│   ├── state.json              # The uncorruptible single-source-of-truth state ledger
│   ├── strategy_v1.yaml        # LLM planning strategy definitions
│   └── strategy_v2.yaml        
├── src/
│   ├── ui/                     # Frontend Presentation Layer
│   │   └── app.py              # Streamlit dashboard, HITL approval UI, log streaming
│   ├── orchestration/          # Cognitive Planner & Control Layer
│   │   ├── gateway.py          # Unified LLM Gateway (Gemini, Ollama)
│   │   ├── planner.py          # ReAct/Graph-based autonomous task planner
│   │   ├── planner_models.py   # Pydantic schema constraints for tasks
│   │   └── state_controller.py # CRUD interface for config/state.json
│   ├── security/               # Sandboxing, Web Scraping & APIs (C1 Focus)
│   │   ├── api.py              # FastAPI microservice for isolated execution
│   │   ├── sandbox.py          # Ephemeral Docker Python code execution manager
│   │   ├── rollback.py         # State rollback mechanisms on execution failure
│   │   ├── browser_controller.py # Headless Playwright automation
│   │   └── quarantine_parser.py # LLM output sanitizer / Prompt injection block
│   └── data_rag/               # RAG, Provenance, and Synthesis (C2 Focus)
│       ├── hybrid_engine.py    # BM25 + Vector retrieval (Tavily/Exa integration)
│       ├── evidence_graph.py   # NetworkX directed graph for data provenance tracking
│       ├── citation_compiler.py # Markdown parser for strict [1] citation injection
│       ├── conflict_tracker.py # Identifies contradicting claims in the Evidence Graph
│       └── benchmark_runner.py # Confidence evaluation matrices
├── tests/                      # Pytest unit and integration test suites
├── Dockerfile                  # Base image for the air-gapped Python execution sandbox
├── Dockerfile.browser          # Image containing headless browser dependencies
├── launcher.py                 # Multi-process orchestrator to boot FastAPI and Streamlit
├── requirements.txt            # Python dependencies
├── .env                        # Environment configurations (API Keys, tokens, thresholds)
└── workspace/                  # Ephemeral outputs (citations.json, generated scripts)
```

---

## 2. High-End Workflow Pipeline (Start to Finish)

When a user submits a research objective via the Streamlit UI, the following pipeline strictly executes:

### Step 1: User Input & State Reset
The query (e.g., "Investigate zero-day exploit trends") is captured in `src/ui/app.py`. The `StateController` clears old execution results from `config/state.json` to guarantee a clean slate.

### Step 2: Orchestration & Graph Decomposition (Planning)
The query is handed to `PlannerEngine` (`src/orchestration/planner.py`), which interfaces with the `ModelGateway` (`src/orchestration/gateway.py`). 
* The LLM prompt wraps the user request in a strict Pydantic JSON schema.
* The LLM responds with a `TaskGraph` containing multiple `SubTask` items, assigning each an `ActionType` (`RAG_RETRIEVAL`, `CODE_EXECUTION`, `BROWSER_SCRAPE`, or `SYNTHESIS`) and a dynamically calculated `confidence_threshold`.

### Step 3: Execution Loop & Human-in-the-Loop (HITL) Gate
The `PlannerEngine` steps through the `TaskGraph`. If the task involves code execution or report synthesis:
* The engine checks `.env` policies (e.g., `STRICT_APPROVAL_CODE_EXECUTION=True`).
* The engine pauses, sets the subtask status to `PENDING_APPROVAL` in `state.json`, and yields control back to the UI.
* The UI renders a warning banner. Once the human explicitly clicks "Approve", the `PlannerEngine` resumes execution.

### Step 4: Action Routing & Execution (C1 - Sandboxing)
* **`RAG_RETRIEVAL`**: Handled by `src/data_rag/hybrid_engine.py` using Tavily/Exa APIs for neural search and vectorization.
* **`CODE_EXECUTION`**: Formulates a REST POST request to the isolated FastAPI Sandbox API (`http://localhost:8000/sandbox/execute`). The payload contains the Python script and a mandatory `SANDBOX_AUTH_TOKEN`.
  * The `SandboxManager` (`src/security/sandbox.py`) dynamically creates an ephemeral Docker container using the `Dockerfile` image, runs the Python code with strict timeouts, and returns the STDOUT/STDERR logs without ever mounting host volumes.
* **`BROWSER_SCRAPE`**: Hits the `sandbox/scrape` API, using Playwright (`browser_controller.py`) inside `Dockerfile.browser` to extract text from heavily javascript-rendered sites safely.

### Step 5: Provenance Registration (C2 - Evidence Graph)
The raw output (stdout, scraped text, retrieval chunks) is injected into the `EvidenceGraph` (`src/data_rag/evidence_graph.py`).
* NetworkX stores the text, calculates confidence scores (e.g., `0.92`, `0.95`, `1.0`), and maintains relational edges (`SUPPORTED_BY`) tracing exactly where the data originated.
* `conflict_tracker.py` is invoked to ensure no contradicting logic is merged into the final synthesis.

### Step 6: Compilation & Markdown Rendering
Once all subtasks pass their `confidence_threshold`, the `PlannerEngine` writes a raw Markdown draft.
* The `DynamicCitationCompiler` (`src/data_rag/citation_compiler.py`) parses the Markdown, locates citation tags (`[1]`, `[2]`), and matches them to the NetworkX graph.
* The compiler generates `workspace/citations.json`.
* The UI detects completion and seamlessly renders the Final Report alongside a strictly mapped "Evidence Graph & Source Citations" table.

---

## 3. Core Models & AI Engines

Aegis is intentionally model-agnostic but strongly typed using Pydantic schemas. 

* **Google Gemini API (Primary Cognitive Engine)**: Configured via `GEMINI_API_KEY`. Gemini 1.5 Pro is the workhorse model used by `PlannerEngine` to decompose the workflow, build the initial `TaskGraph`, and synthesize the final report due to its massive context window and native JSON-schema enforcement capabilities.
* **Ollama & Llama/Gemma (Local Execution Mode)**: The `ModelGateway` natively supports routing requests to a localized Ollama instance (`http://localhost:11434`) for offline, privacy-first planning and fallback redundancy.
* **Tavily API & Exa API**: Dedicated search models invoked directly by the `HybridRAGEngine` for real-time web scraping and document retrieval, completely bypassing standard LLM hallucinations.
* **NeMo Guardrails (Security Filter)**: Positioned in front of the `ModelGateway` to intercept Prompt Injection or Jailbreak attempts before the LLM parses the command.

---

## 4. Bootstrapping & Launcher Infrastructure

The system is booted via a singular `launcher.py` script located in the root. 
* It instantiates a `multiprocessing` pipeline.
* Process 1 spins up the Uvicorn/FastAPI microservice (`src.security.api`) on port 8000 to manage docker sandboxing.
* Process 2 spins up Streamlit (`src/ui/app.py`) on port 8501 for the human interaction layer.
* Both systems remain fully decoupled and communicate *only* through REST calls and mutations to the `config/state.json` file.
