"""
Unit tests for Chunk Deduplicator utility.
"""

import pytest
from src.data_rag.deduplicator import ChunkDeduplicator


def test_deduplicator_exact_duplicates():
    dedup = ChunkDeduplicator(similarity_threshold=0.85)

    chunks = [
        {
            "id": "c1",
            "text": "Aegis Research OS provides an autonomous multi-agent platform for research planning.",
            "metadata": {"doc_id": "doc_v1"}
        },
        {
            "id": "c2",
            "text": "Aegis Research OS provides an autonomous multi-agent platform for research planning.",
            "metadata": {"doc_id": "doc_v2"}
        }
    ]

    output = dedup.deduplicate(chunks)
    assert output["duplicate_count"] == 1
    assert len(output["deduplicated_chunks"]) == 1
    canonical = output["deduplicated_chunks"][0]
    assert canonical["id"] == "c1"
    assert "c2" in canonical["metadata"]["duplicate_ids"]
    assert "doc_v2" in canonical["metadata"]["duplicate_sources"]


def test_deduplicator_near_duplicates():
    dedup = ChunkDeduplicator(similarity_threshold=0.80)

    chunks = [
        {
            "id": "c1",
            "text": "The hybrid Live RAG engine uses ChromaDB for dense vector search and BM25 for keyword scoring.",
            "metadata": {"doc_id": "doc_a"}
        },
        {
            "id": "c2",
            "text": "The hybrid Live RAG engine uses ChromaDB for dense vector search and BM25 for keyword scoring in Aegis OS.",
            "metadata": {"doc_id": "doc_b"}
        },
        {
            "id": "c3",
            "text": "Python sandbox provides isolated containerized execution environment for research scripts.",
            "metadata": {"doc_id": "doc_c"}
        }
    ]

    output = dedup.deduplicate(chunks)
    assert output["duplicate_count"] == 1
    assert len(output["deduplicated_chunks"]) == 2
    # c2 is longer so it should become the canonical chunk text
    canonical_ids = [c["id"] for c in output["deduplicated_chunks"]]
    assert "c1" in canonical_ids or "c2" in canonical_ids
    assert "c3" in canonical_ids


def test_deduplicator_no_duplicates():
    dedup = ChunkDeduplicator(similarity_threshold=0.85)

    chunks = [
        {"id": "c1", "text": "First distinct passage topic."},
        {"id": "c2", "text": "Second completely unrelated text passage."}
    ]

    output = dedup.deduplicate(chunks)
    assert output["duplicate_count"] == 0
    assert len(output["deduplicated_chunks"]) == 2
