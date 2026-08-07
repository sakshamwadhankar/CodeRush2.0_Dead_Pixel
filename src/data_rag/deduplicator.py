"""
Semantic Chunk Deduplication Utility for Aegis Research OS.
Identifies and filters out redundant text passages using text similarity metrics.
"""

import re
from typing import List, Dict, Any, Tuple, Optional, Set


class ChunkDeduplicator:
    """
    Identifies and merges redundant document chunks based on semantic similarity.
    """

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Args:
            similarity_threshold: Float threshold (0.0 to 1.0) above which chunks are considered duplicates.
        """
        self.similarity_threshold = similarity_threshold

    def _tokenize(self, text: str) -> List[str]:
        """Extract lowercased word tokens from text."""
        return re.findall(r"\w+", text.lower())

    def _get_ngrams(self, tokens: List[str], n: int = 2) -> Set[Tuple[str, ...]]:
        """Extract n-grams from a list of tokens."""
        if len(tokens) < n:
            return {tuple(tokens)} if tokens else set()
        return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}

    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Computes composite similarity between two text passages.
        Combines unigram & bigram Jaccard overlap with token similarity.

        Args:
            text1: First text passage.
            text2: Second text passage.

        Returns:
            Similarity score float in range [0.0, 1.0].
        """
        if not text1 or not text2:
            return 0.0
        if text1.strip() == text2.strip():
            return 1.0

        tokens1 = self._tokenize(text1)
        tokens2 = self._tokenize(text2)

        if not tokens1 or not tokens2:
            return 0.0

        # Unigram Jaccard similarity
        set1 = set(tokens1)
        set2 = set(tokens2)
        intersection_1 = set1.intersection(set2)
        union_1 = set1.union(set2)
        jaccard_1 = len(intersection_1) / len(union_1) if union_1 else 0.0

        # Bigram Jaccard similarity
        bigrams1 = self._get_ngrams(tokens1, n=2)
        bigrams2 = self._get_ngrams(tokens2, n=2)
        intersection_2 = bigrams1.intersection(bigrams2)
        union_2 = bigrams1.union(bigrams2)
        jaccard_2 = len(intersection_2) / len(union_2) if union_2 else 0.0

        # Weighted combination of unigram and bigram overlap
        composite_sim = 0.4 * jaccard_1 + 0.6 * jaccard_2
        return min(1.0, max(0.0, composite_sim))

    def deduplicate(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Filters out duplicate chunks and merges metadata into canonical chunks.

        Args:
            chunks: List of chunk dictionaries containing 'id', 'text', and 'metadata'.

        Returns:
            Dict containing:
            - 'deduplicated_chunks': List of unique canonical chunks.
            - 'duplicate_count': Total number of removed duplicate chunks.
            - 'clusters': Dict mapping canonical_id -> list of duplicate_ids.
        """
        if not chunks:
            return {
                "deduplicated_chunks": [],
                "duplicate_count": 0,
                "clusters": {}
            }

        canonical_chunks: List[Dict[str, Any]] = []
        clusters: Dict[str, List[str]] = {}
        visited_indices: Set[int] = set()

        for i, chunk in enumerate(chunks):
            if i in visited_indices:
                continue

            visited_indices.add(i)
            canonical_chunk = dict(chunk)
            canonical_id = canonical_chunk["id"]

            duplicate_ids: List[str] = []
            duplicate_sources: List[str] = []

            meta = dict(canonical_chunk.get("metadata", {}))

            for j in range(i + 1, len(chunks)):
                if j in visited_indices:
                    continue

                other_chunk = chunks[j]
                sim = self.compute_similarity(chunk["text"], other_chunk["text"])

                if sim >= self.similarity_threshold:
                    visited_indices.add(j)
                    dup_id = other_chunk["id"]
                    dup_source = other_chunk.get("metadata", {}).get("doc_id", "unknown")

                    duplicate_ids.append(dup_id)
                    duplicate_sources.append(dup_source)

                    # Update canonical text if the duplicate is longer/more descriptive
                    if len(other_chunk["text"]) > len(canonical_chunk["text"]):
                        canonical_chunk["text"] = other_chunk["text"]

            meta["duplicate_ids"] = duplicate_ids
            meta["duplicate_sources"] = duplicate_sources
            meta["is_canonical"] = True
            canonical_chunk["metadata"] = meta

            canonical_chunks.append(canonical_chunk)
            if duplicate_ids:
                clusters[canonical_id] = duplicate_ids

        total_duplicates = len(chunks) - len(canonical_chunks)

        return {
            "deduplicated_chunks": canonical_chunks,
            "duplicate_count": total_duplicates,
            "clusters": clusters
        }
