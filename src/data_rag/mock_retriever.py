"""
Mock Retriever for Developer A's Contract-First Git Workflow integration testing.
Includes mock support for Step C2 deduplication and conflict tracking.
"""

import json
import os
from typing import List, Dict, Any, Optional


class MockHybridRAGEngine:
    """
    Lightweight mock implementation of the Hybrid RAG Engine with Deduplication & Conflict Tracking.
    Returns deterministic responses and updates state.json for Orchestrator development.
    """

    def __init__(self):
        self.ingested_documents: List[str] = []

    def ingest_document(
        self, text: str, doc_id: str = "doc_0", metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        if doc_id not in self.ingested_documents:
            self.ingested_documents.append(doc_id)
        return [{
            "id": f"{doc_id}_chunk_0",
            "text": text[:100] + "..." if len(text) > 100 else text,
            "metadata": {"doc_id": doc_id, "mock": True}
        }]

    def search(
        self,
        query: str,
        top_k: int = 5,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5
    ) -> List[Dict[str, Any]]:
        return [
            {
                "id": "mock_chunk_1",
                "text": f"Aegis OS supports offline execution for research query '{query}'.",
                "metadata": {"doc_id": "doc_mock_v1", "confidence": 0.95},
                "rrf_score": 0.016393,
                "dense_rank": 1,
                "sparse_rank": 1,
                "hybrid_rank": 1
            },
            {
                "id": "mock_chunk_2",
                "text": f"Aegis OS does not support offline execution for research query '{query}'.",
                "metadata": {"doc_id": "doc_mock_v2", "confidence": 0.88},
                "rrf_score": 0.016129,
                "dense_rank": 2,
                "sparse_rank": 2,
                "hybrid_rank": 2
            }
        ][:top_k]

    def deduplicate_passages(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "deduplicated_chunks": chunks,
            "duplicate_count": 0,
            "clusters": {}
        }

    def detect_conflicts(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(chunks) >= 2:
            return [{
                "conflict_id": "conflict_mock_001",
                "conflict_type": "negation_conflict",
                "claim_a": {
                    "chunk_id": chunks[0]["id"],
                    "source_doc_id": chunks[0]["metadata"].get("doc_id", "mock_a"),
                    "statement": chunks[0]["text"]
                },
                "claim_b": {
                    "chunk_id": chunks[1]["id"],
                    "source_doc_id": chunks[1]["metadata"].get("doc_id", "mock_b"),
                    "statement": chunks[1]["text"]
                },
                "opposing_details": {"type": "negation_conflict", "reason": "Opposing assertion on offline support"},
                "confidence": 0.95,
                "status": "unresolved"
            }]
        return []

    def sync_with_state(self, state_filepath: str = "state.json") -> Dict[str, Any]:
        if not os.path.exists(state_filepath):
            state_data = {
                "project_name": "Aegis Research OS",
                "query": "",
                "search_results": [],
                "deduplicated_results": [],
                "tracked_conflicts": [],
                "status": "idle"
            }
        else:
            with open(state_filepath, "r", encoding="utf-8") as f:
                state_data = json.load(f)

        query = state_data.get("query", "")
        if query:
            results = self.search(query)
            state_data["search_results"] = results
            state_data["deduplicated_results"] = results
            state_data["tracked_conflicts"] = self.detect_conflicts(results)
            state_data["status"] = "completed"

        with open(state_filepath, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)

        return state_data
