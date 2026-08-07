"""
Unit tests for ChromaDB Dense Store.
"""

import pytest
from retriever.dense_store import ChromaDenseStore


def test_dense_store_insertion_and_query():
    store = ChromaDenseStore(collection_name="test_dense_coll")
    store.clear()

    sample_chunks = [
        {
            "id": "c1",
            "text": "Aegis OS uses ChromaDB for dense vector semantic search.",
            "metadata": {"doc_id": "d1", "topic": "vector_db"}
        },
        {
            "id": "c2",
            "text": "Python sandbox provides secure isolated code execution.",
            "metadata": {"doc_id": "d2", "topic": "sandbox"}
        },
        {
            "id": "c3",
            "text": "Reciprocal Rank Fusion combines vector search with BM25 keyword search.",
            "metadata": {"doc_id": "d3", "topic": "fusion"}
        }
    ]

    store.add_passages(sample_chunks)
    assert store.count() == 3

    results = store.query("semantic vector search in Chroma", top_k=2)
    assert len(results) == 2
    assert results[0]["id"] == "c1"
    assert "dense_score" in results[0]
    assert results[0]["dense_rank"] == 1

    store.clear()
    assert store.count() == 0
