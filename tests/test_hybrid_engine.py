"""
Unit tests for Hybrid RAGEngine and state.json integration.
"""

import json
import os
import pytest
from src.data_rag.hybrid_engine import HybridRAGEngine
from src.data_rag.mock_retriever import MockHybridRAGEngine


def test_hybrid_engine_ingest_and_search(tmp_path):
    state_file = str(tmp_path / "state.json")

    engine = HybridRAGEngine(collection_name="test_hybrid_coll")
    engine.reset()

    doc_1 = """# Aegis Architecture
Aegis Research OS provides an autonomous multi-agent platform.
Developer C created the Hybrid Live RAG Engine using ChromaDB and BM25.

# Fusion Logic
Reciprocal Rank Fusion (RRF) dynamically calculates combined ranks for vector and keyword search.
"""
    engine.ingest_document(doc_1, doc_id="doc_aegis_arch")

    results = engine.search("ChromaDB BM25 hybrid fusion", top_k=2)
    assert len(results) > 0
    assert "rrf_score" in results[0]
    assert "hybrid_rank" in results[0]

    # Test state synchronization
    initial_state = {
        "project_name": "Aegis Research OS",
        "query": "Reciprocal Rank Fusion",
        "retrieval_config": {"top_k": 3, "dense_weight": 0.5, "sparse_weight": 0.5},
        "search_results": [],
        "status": "idle"
    }
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(initial_state, f)

    updated_state = engine.sync_with_state(state_file)
    assert updated_state["status"] == "completed"
    assert len(updated_state["search_results"]) > 0
    assert updated_state["search_results"][0]["id"].startswith("doc_aegis_arch")


def test_mock_hybrid_engine(tmp_path):
    mock_engine = MockHybridRAGEngine()
    state_file = str(tmp_path / "state.json")

    mock_engine.ingest_document("Test doc for orchestrator", doc_id="doc_mock")

    with open(state_file, "w", encoding="utf-8") as f:
        json.dump({"query": "autonomous research agent"}, f)

    updated = mock_engine.sync_with_state(state_file)
    assert updated["status"] == "completed"
    assert len(updated["search_results"]) == 2
    assert updated["search_results"][0]["metadata"]["doc_id"] == "doc_mock_v1"
