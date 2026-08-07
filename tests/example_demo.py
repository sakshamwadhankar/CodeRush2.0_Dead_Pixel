"""
Example script demonstrating Hybrid Live RAG Engine in action for Aegis Research OS.
"""

from retriever import HybridRAGEngine
import json


def run_demo():
    print("=== Initializing Aegis Research OS - Hybrid Live RAG Engine (Developer C) ===")
    engine = HybridRAGEngine(collection_name="aegis_demo_collection")
    engine.reset()

    # Sample research document
    sample_doc = """# Aegis Research OS: Autonomous Agent Infrastructure

SECTION: Security Layer
Aegis Research OS enforces strict isolation for browser execution and code execution.
Prompt injection defense mechanisms audit all tool calls before execution.

SECTION: Hybrid Retrieval Engine
Developer C designed the data and RAG infrastructure.
It pairs ChromaDB for dense semantic vector retrieval with BM25Okapi for sparse keyword search.
Reciprocal Rank Fusion (RRF) combines both ranking scores to ensure precise passage retrieval.

SECTION: Orchestrator Integration
Developer A's Research Orchestrator uses a Contract-First Git Workflow.
The state.json file defines shared state between planning, retrieval, and evidence graph modules.
"""

    print("\n[+] Ingesting Sample Document into ChromaDB + BM25...")
    chunks = engine.ingest_document(text=sample_doc, doc_id="doc_aegis_paper_01")
    print(f"[OK] Generated {len(chunks)} context-aware semantic passages.")

    query = "How does the hybrid search use BM25 and ChromaDB?"
    print(f"\n[?] Executing Hybrid Retrieval Query: '{query}'")

    results = engine.search(query=query, top_k=3, dense_weight=0.5, sparse_weight=0.5)

    print("\n[RRF] Hybrid Search Results (Reciprocal Rank Fusion):")
    for r in results:
        print(f"\n--- [Hybrid Rank {r['hybrid_rank']}] RRF Score: {r['rrf_score']} ---")
        print(f"ID: {r['id']}")
        print(f"Header Context: {r['metadata'].get('header_context')}")
        print(f"Dense Rank: {r['dense_rank']} | BM25 Rank: {r['sparse_rank']}")
        print(f"Text Snippet: {r['text'][:150]}...")

    print("\n[State] Synchronizing query state with state.json...")
    with open("state.json", "w", encoding="utf-8") as f:
        json.dump({
            "project_name": "Aegis Research OS",
            "active_task_id": "task_demo_01",
            "query": "security prompt injection protection",
            "retrieval_config": {"top_k": 2, "dense_weight": 0.5, "sparse_weight": 0.5},
            "search_results": [],
            "status": "idle"
        }, f, indent=2)

    updated_state = engine.sync_with_state("state.json")
    print(f"[OK] State status: {updated_state['status']}")
    print(f"[OK] State search_results count: {len(updated_state['search_results'])}")
    print("\n=== Hybrid Live RAG Engine demonstration completed successfully! ===")


if __name__ == "__main__":
    run_demo()
