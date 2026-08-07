"""
Unit tests for BM25 Keyword Ranker.
"""

import pytest
from src.data_rag.bm25_ranker import BM25Ranker


def test_bm25_tokenization():
    ranker = BM25Ranker()
    tokens = ranker.tokenize("Hello World! Aegis-OS RAG pipeline.")
    assert tokens == ["hello", "world", "aegis", "os", "rag", "pipeline"]


def test_bm25_indexing_and_query():
    ranker = BM25Ranker()

    chunks = [
        {"id": "b1", "text": "BM25 keyword search is effective for rare domain terminology."},
        {"id": "b2", "text": "Dense vector search captures deep semantic meaning in text."},
        {"id": "b3", "text": "Hybrid search blends BM25 keyword matching with vector embeddings."}
    ]

    ranker.index_passages(chunks)
    assert ranker.count() == 3

    results = ranker.query("terminology BM25", top_k=2)
    assert len(results) >= 1
    assert results[0]["id"] == "b1"
    assert results[0]["bm25_score"] > 0
    assert results[0]["sparse_rank"] == 1

    ranker.clear()
    assert ranker.count() == 0
