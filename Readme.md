# CodeRush 2.0 | Team Project Repository

## Project Information

- **Team Name:** Dead_Pixel
- **Project Title:** Aegis Research OS (AE-02)
- **Track/Theme:** AE-02 – Self-Evolving Autonomous Research Agent (Agentic Ecosystem)

## Project Description

Aegis Research OS is a secure, autonomous AI research platform capable of planning complex investigations, browsing the web, analyzing documents, executing code, and generating evidence-backed reports with complete traceability. The system integrates Hybrid Retrieval-Augmented Generation (RAG), headless Playwright browser automation, air-gapped sandboxed code execution, and an evidence graph to produce reliable, reproducible, and citation-backed research outputs.

## Technical Stack

- **Frontend:** Streamlit, React Flow, HTML/CSS
- **Backend:** FastAPI, Python, Uvicorn
- **Database:** ChromaDB, BM25Okapi, NetworkX
- **Tools/APIs:** Docker, Playwright, NeMo Guardrails, Google Gemini API, Ollama

## Setup and Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/sakshamwadhankar/CodeRush2.0_Dead_Pixel.git
   cd CodeRush2.0_Dead_Pixel
   ```
2. **Install dependencies & browsers:**
   ```bash
   pip install -r requirements.txt
   python -m playwright install
   ```
3. **Configure environment variables:**
   Create a `.env` file in the root directory with your API keys (e.g., `OPENAI_API_KEY`, `GEMINI_API_KEY`).
4. **Ensure Docker is running** (required for the air-gapped Python execution sandbox).
5. **Start the development servers:** 
   ```bash
   # Terminal 1: Start Backend API (FastAPI)
   uvicorn src.security.api:app --port 8000
   
   # Terminal 2: Start Frontend UI (Streamlit)
   streamlit run src/ui/app.py
   ```

## Project Structure

```text
CodeRush2.0_Dead_Pixel/
├── config/                     # Configuration and state files
│   ├── state.json
│   ├── strategy_v1.yaml
│   └── strategy_v2.yaml
├── src/
│   ├── ui/                     # Frontend Streamlit Application
│   │   └── app.py
│   ├── orchestration/          # Cognitive Planner & LLM Gateway
│   │   ├── gateway.py
│   │   ├── planner.py
│   │   └── state_controller.py
│   ├── security/               # Sandboxing, Web Scraping, & APIs
│   │   ├── api.py
│   │   ├── sandbox.py
│   │   ├── rollback.py
│   │   ├── browser_controller.py
│   │   └── quarantine_parser.py
│   └── data_rag/               # RAG, ChromaDB, and Evidence Graph
│       ├── hybrid_engine.py
│       ├── evidence_graph.py
│       ├── citation_compiler.py
│       ├── conflict_tracker.py
│       └── benchmark_runner.py
├── tests/                      # Unit and integration tests
├── Dockerfile                  # Python execution sandbox environment
├── Dockerfile.browser          # Playwright headless browser environment
└── requirements.txt            # Unified project dependencies
```
