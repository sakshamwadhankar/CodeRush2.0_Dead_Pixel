"""
Reciprocal Rank Fusion (RRF) for combining dense vector search and sparse BM25 search.
"""

from typing import List, Dict, Any, Optional


class ReciprocalRankFusion:
    """
    Reciprocal Rank Fusion (RRF) implementation for Hybrid Search.
    Dynamically combines and re-ranks sparse (keyword) and dense (semantic) retrieval results.
    """

    def __init__(self, rrf_k: int = 60):
        """
        Args:
            rrf_k: Smoothing constant added to ranks (standard baseline is 60).
        """
        self.rrf_k = rrf_k

    def fuse(
        self,
        dense_results: List[Dict[str, Any]],
        sparse_results: List[Dict[str, Any]],
        top_k: int = 5,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Combines dense and sparse search result lists using Reciprocal Rank Fusion.

        Formula:
            RRF_Score(d) = (w_dense / (k + rank_dense(d))) + (w_sparse / (k + rank_sparse(d)))

        Args:
            dense_results: Search results from ChromaDB (with 'id', 'dense_rank', 'dense_score', 'text', 'metadata').
            sparse_results: Search results from BM25 (with 'id', 'sparse_rank', 'bm25_score', 'text', 'metadata').
            top_k: Number of combined results to return.
            dense_weight: Weight factor for dense vector search component.
            sparse_weight: Weight factor for sparse keyword search component.

        Returns:
            List of combined result dicts sorted descending by rrf_score.
        """
        fused_map: Dict[str, Dict[str, Any]] = {}

        # Process dense results
        for item in dense_results:
            doc_id = item["id"]
            dense_rank = item.get("dense_rank", 1)
            dense_score = item.get("dense_score", 0.0)
            
            score_contrib = dense_weight / (self.rrf_k + dense_rank)

            if doc_id not in fused_map:
                fused_map[doc_id] = {
                    "id": doc_id,
                    "text": item.get("text", ""),
                    "metadata": item.get("metadata", {}),
                    "rrf_score": score_contrib,
                    "dense_rank": dense_rank,
                    "dense_score": dense_score,
                    "sparse_rank": None,
                    "bm25_score": None
                }
            else:
                fused_map[doc_id]["rrf_score"] += score_contrib
                fused_map[doc_id]["dense_rank"] = dense_rank
                fused_map[doc_id]["dense_score"] = dense_score

        # Process sparse results
        for item in sparse_results:
            doc_id = item["id"]
            sparse_rank = item.get("sparse_rank", 1)
            bm25_score = item.get("bm25_score", 0.0)

            score_contrib = sparse_weight / (self.rrf_k + sparse_rank)

            if doc_id not in fused_map:
                fused_map[doc_id] = {
                    "id": doc_id,
                    "text": item.get("text", ""),
                    "metadata": item.get("metadata", {}),
                    "rrf_score": score_contrib,
                    "dense_rank": None,
                    "dense_score": None,
                    "sparse_rank": sparse_rank,
                    "bm25_score": bm25_score
                }
            else:
                fused_map[doc_id]["rrf_score"] += score_contrib
                fused_map[doc_id]["sparse_rank"] = sparse_rank
                fused_map[doc_id]["bm25_score"] = bm25_score

        # Convert to list and sort by RRF score descending
        fused_list = list(fused_map.values())
        fused_list.sort(key=lambda x: x["rrf_score"], reverse=True)

        # Assign final hybrid rank
        for hybrid_rank, res in enumerate(fused_list, start=1):
            res["hybrid_rank"] = hybrid_rank
            res["rrf_score"] = round(res["rrf_score"], 6)

        return fused_list[:top_k]
