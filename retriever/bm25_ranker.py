"""
BM25 Keyword Ranker for Sparse/Keyword Retrieval using rank_bm25.
"""

import re
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi


class BM25Ranker:
    """
    Sparse keyword ranker using Okapi BM25 algorithm.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Args:
            k1: BM25 k1 parameter controlling term frequency saturation.
            b: BM25 b parameter controlling document length normalization.
        """
        self.k1 = k1
        self.b = b
        self.passages: List[Dict[str, Any]] = []
        self.corpus_tokens: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None

    def tokenize(self, text: str) -> List[str]:
        """Lowercases and extracts word tokens from text."""
        if not text:
            return []
        tokens = re.findall(r"\w+", text.lower())
        return tokens

    def index_passages(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Indexes text passages for BM25 search.

        Args:
            chunks: List of chunk dicts containing 'id', 'text', and optional 'metadata'.
        """
        if not chunks:
            return

        for chunk in chunks:
            self.passages.append(chunk)
            tokens = self.tokenize(chunk["text"])
            self.corpus_tokens.append(tokens)

        self.bm25 = BM25Okapi(self.corpus_tokens, k1=self.k1, b=self.b)

    def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Queries the BM25 index with a keyword search string.

        Args:
            query_text: Input query string.
            top_k: Max results to retrieve.

        Returns:
            List of result dicts containing:
            ['id', 'text', 'metadata', 'bm25_score', 'sparse_rank']
        """
        if not self.bm25 or not self.passages:
            return []

        query_tokens = self.tokenize(query_text)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)

        # Pair scores with passages
        scored_passages = []
        for idx, score in enumerate(scores):
            if score > 0:  # Only include non-zero keyword matches or top results
                passage = self.passages[idx]
                scored_passages.append({
                    "id": passage["id"],
                    "text": passage["text"],
                    "metadata": passage.get("metadata", {}),
                    "bm25_score": float(score)
                })

        # Sort descending by BM25 score
        scored_passages.sort(key=lambda x: x["bm25_score"], reverse=True)

        actual_k = min(top_k, len(scored_passages))
        results = scored_passages[:actual_k]

        for rank, res in enumerate(results, start=1):
            res["sparse_rank"] = rank

        return results

    def clear(self) -> None:
        """Clears stored passages and resets BM25 index."""
        self.passages = []
        self.corpus_tokens = []
        self.bm25 = None

    def count(self) -> int:
        """Returns total indexed passage count."""
        return len(self.passages)
