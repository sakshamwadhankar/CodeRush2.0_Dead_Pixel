# CodeRush 2.0 | Team Project Repository

## Project Information

- **Team Name:** Dead_Pixel
- **Project Title:** Aegis Research OS (AE-02)
- **Track/Theme:** AE-02 – Self-Evolving Autonomous Research Agent (Agentic Ecosystem)

## Project Description

Aegis Research OS is a secure, autonomous AI research platform capable of planning complex investigations, browsing the web, analyzing documents, executing code, and generating evidence-backed reports with complete traceability. The system integrates Hybrid Retrieval-Augmented Generation (RAG), headless Playwright browser automation, air-gapped sandboxed code execution, and an evidence graph to produce reliable, reproducible, and citation-backed research outputs.

## Technical Stack

List the technologies used in this project:

- **Frontend:** Streamlit, React Flow, HTML/CSS
- **Backend:** FastAPI, Python, Uvicorn
- **Database:** ChromaDB, BM25Okapi, NetworkX
- **Tools/APIs:** Docker, Playwright, NeMo Guardrails, Google Gemini API, Ollama

## Setup and Installation

Provide instructions on how to run your project locally:

1. Clone the repository.
   ```bash
   git clone https://github.com/sakshamwadhankar/CodeRush2.0_Dead_Pixel.git
   cd CodeRush2.0_Dead_Pixel
   ```
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables (create a `.env` file with API keys like `OPENAI_API_KEY`, `GEMINI_API_KEY`).
4. Start the development servers: 
   ```bash
   # Terminal 1: Start Backend API
   uvicorn src.security.api:app --port 8000
   
   # Terminal 2: Start Frontend UI
   streamlit run src/ui/app.py
   ```
