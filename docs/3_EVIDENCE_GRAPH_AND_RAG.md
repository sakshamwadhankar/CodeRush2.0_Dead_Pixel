# Provenance & Retrieval-Augmented Generation (RAG)

Aegis solves the hallucination problem inherent in modern LLMs by strictly coupling every generated claim back to the raw source data it was derived from.

## Hybrid RAG Engine (`src/data_rag/hybrid_engine.py`)
- Interfaces with APIs like Tavily and Exa to pull raw HTML/Text based on semantic relevance.
- Data is chunked and vectorized, utilizing both dense vectors and sparse (BM25) approaches to guarantee high precision recall.

## NetworkX Evidence Graph (`src/data_rag/evidence_graph.py`)
- Acts as a mathematical representation of truth for the system.
- **Node Types**:
  - `Document`: High-level representation of a source URL or file.
  - `Chunk`: A specific vectorized paragraph.
  - `Claim`: A synthesized LLM statement.
- **Edge Types**:
  - `CONTAINS`: Links Document -> Chunk.
  - `SUPPORTED_BY`: Links Claim -> Chunk.
- If a Code Execution task returns raw logic logs, they are inserted directly into the graph as claims natively possessing `1.0` confidence, as they do not require semantic chunks for verification.

## Citation Compiler (`src/data_rag/citation_compiler.py`)
- The LLM drafts the final report in Markdown.
- The Compiler parses the Markdown looking for strict markers (e.g., `[1]`).
- It extracts the marker, queries the Evidence Graph to pull the exact confidence score (`0.92`, `0.95`, etc.) and the underlying source paths.
- It outputs `workspace/citations.json` ensuring the UI strictly displays verified facts.
