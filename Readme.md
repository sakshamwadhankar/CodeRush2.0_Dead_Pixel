# 🧠 Dead_Pixel | Self-Evolving Autonomous Research Agent

## 📌 Project Information

- **Team Name:** Dead_Pixel
- **Project Title:** Aegis Research OS
- **Track/Theme:** AE-02 – Self-Evolving Autonomous Research Agent (Agentic Ecosystem)

---

# 📖 Project Description

Aegis Research OS is a secure, autonomous AI research platform capable of planning complex investigations, browsing the web, analyzing documents, executing code, and generating evidence-backed reports with complete traceability.

Unlike traditional AI chatbots, the system continuously improves its research strategies through a governed self-evolution framework. Every proposed improvement is evaluated on benchmark tasks, versioned, and requires approval before deployment, ensuring the trusted control layer remains secure and auditable.

The platform integrates Retrieval-Augmented Generation (RAG), browser automation, sandboxed code execution, long-term memory, and an evidence graph to produce reliable, reproducible, and citation-backed research outputs.

---

# 🚀 Key Features

- Autonomous Research Planning
- Hybrid Live RAG Pipeline
- Browser Automation
- PDF & Document Intelligence
- Evidence Graph & Source Tracking
- Python Sandbox Execution
- Long-Term Memory
- Prompt Injection Detection
- Strategy Self-Evolution
- Human Approval Workflow
- Audit Logs & Trace Viewer

---

# 🛠 Technical Stack

### Frontend

- Next.js
- React
- Tailwind CSS
- ShadCN UI
- React Flow

### Backend

- FastAPI
- LangGraph
- Python
- Celery

### Database

- PostgreSQL
- Qdrant Vector Database
- Redis

### AI Models

- OpenAI GPT
- Claude
- Gemini
- DeepSeek

### Tools / APIs

- Tavily Search API
- Exa Search
- Playwright
- PyMuPDF
- Docker
- Python Sandbox

---

# ⚙️ Setup & Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/aegis-research-os.git

cd aegis-research-os
```

### 2. Install Dependencies

Frontend

```bash
cd frontend
npm install
```

Backend

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure Environment

Create

```
.env
```

Example

```env
OPENAI_API_KEY=
GEMINI_API_KEY=
TAVILY_API_KEY=
EXA_API_KEY=
DATABASE_URL=
REDIS_URL=
```

### 4. Start Backend

```bash
uvicorn app.main:app --reload
```

### 5. Start Frontend

```bash
npm run dev
```

---

# 📂 Project Structure

```
frontend/
backend/
sandbox/
planner/
retriever/
memory/
browser/
evaluator/
evidence_graph/
self_evolution/
database/
docs/
```

---

# 🔄 Workflow

```
User Query
      │
      ▼
Research Planner
      │
      ▼
Task Graph
      │
      ▼
Live Search + Browser
      │
      ▼
Document Analysis
      │
      ▼
Evidence Graph
      │
      ▼
Python Sandbox
      │
      ▼
Verified Report
      │
      ▼
Self Evaluation
      │
      ▼
Strategy Improvement
      │
      ▼
Human Approval
```

---

# 🔒 Security Features

- Prompt Injection Protection
- Browser Isolation
- Sandboxed Code Execution
- Versioned Strategy Updates
- Human Approval Gates
- Rollback Support
- Complete Audit Logs

---

# 📊 Evaluation Metrics

- Citation Precision
- Research Accuracy
- Prompt Injection Resistance
- Browser Success Rate
- Code Execution Success
- Strategy Improvement Score
- Report Reproducibility
- Human Intervention Count

---

# 👥 Team

**Dead_Pixel**

- **Saksham Wadhankar**
- **Om Rai**
- **Sahil Mahure**
- **Animesh Yadav**
- **Pradum Meshram**

Building trustworthy autonomous AI research systems.

---

# 📄 License

MIT License
