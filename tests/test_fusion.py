"""
Unit tests for Reciprocal Rank Fusion (RRF).
"""

import pytest
from src.data_rag.fusion import ReciprocalRankFusion


def test_rrf_fusion_score_calculation_and_ranking():
    fusion = ReciprocalRankFusion(rrf_k=60)

    dense_results = [
        {"id": "doc_A", "dense_rank": 1, "dense_score": 0.95, "text": "Text A"},
        {"id": "doc_B", "dense_rank": 2, "dense_score": 0.80, "text": "Text B"},
    ]

    sparse_results = [
        {"id": "doc_B", "sparse_rank": 1, "bm25_score": 5.2, "text": "Text B"},
        {"id": "doc_C", "sparse_rank": 2, "bm25_score": 3.1, "text": "Text C"},
    ]

    # RRF formula: w / (k + rank)
    # doc_A: dense_rank=1 -> 0.5 / (60 + 1) = 0.0081967
    # doc_B: dense_rank=2 (0.5 / (60+2) = 0.0080645) + sparse_rank=1 (0.5 / (60+1) = 0.0081967) = 0.0162612
    # doc_C: sparse_rank=2 -> 0.5 / (60 + 2) = 0.0080645

    fused = fusion.fuse(
        dense_results=dense_results,
        sparse_results=sparse_results,
        top_k=3,
        dense_weight=0.5,
        sparse_weight=0.5
    )

    assert len(fused) == 3
    # doc_B appears in both top lists, so its combined RRF score should rank highest!
    assert fused[0]["id"] == "doc_B"
    assert fused[0]["hybrid_rank"] == 1
    assert fused[0]["dense_rank"] == 2
    assert fused[0]["sparse_rank"] == 1
    assert fused[0]["rrf_score"] > fused[1]["rrf_score"]

    assert fused[1]["id"] == "doc_A"
    assert fused[2]["id"] == "doc_C"
