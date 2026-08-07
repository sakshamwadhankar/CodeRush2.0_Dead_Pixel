"""
Conflict Tracking & Contradiction Detection Utility for Aegis Research OS.
Identifies direct factual, numerical, and negation contradictions across retrieved passages.
"""

import re
from typing import List, Dict, Any, Tuple, Optional, Set


class ConflictTracker:
    """
    Analyzes pairs of text statements to identify and log direct contradictions.
    Categorizes conflicts into numerical, negation, and antonym contradiction types.
    """

    OPPOSING_ANTONYMS = [
        ("online", "offline"),
        ("increase", "decrease"),
        ("increased", "decreased"),
        ("increases", "decreases"),
        ("enabled", "disabled"),
        ("secure", "vulnerable"),
        ("secure", "insecure"),
        ("safe", "unsafe"),
        ("compatible", "incompatible"),
        ("success", "failure"),
        ("successful", "failed"),
        ("supported", "unsupported"),
        ("true", "false"),
        ("valid", "invalid"),
        ("allowed", "denied"),
        ("permitted", "forbidden")
    ]

    NEGATION_WORDS = {"not", "no", "never", "without", "lacks", "failed", "denied", "cannot", "n't"}

    def __init__(self, min_topic_overlap: float = 0.35, max_text_similarity: float = 0.95):
        """
        Args:
            min_topic_overlap: Minimum word overlap required to confirm statements share a topic.
            max_text_similarity: Upper similarity bound to filter out near-exact duplicate passages.
        """
        self.min_topic_overlap = min_topic_overlap
        self.max_text_similarity = max_text_similarity

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def _extract_numbers_with_context(self, text: str) -> List[Tuple[str, str]]:
        """
        Extracts numbers paired with adjacent unit/noun context.
        Example: 'battery life is 10 hours' -> [('10', 'hours')]
        """
        matches = re.findall(r"(\b\d+(?:\.\d+)?\b)\s*([a-zA-Z%]+)?", text)
        results = []
        for num, unit in matches:
            results.append((num, unit.lower() if unit else ""))
        return results

    def _calculate_topic_overlap(self, tokens1: List[str], tokens2: List[str]) -> float:
        set1 = set(tokens1) - self.NEGATION_WORDS
        set2 = set(tokens2) - self.NEGATION_WORDS
        if not set1 or not set2:
            return 0.0
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        return len(intersection) / len(union) if union else 0.0

    def _check_numerical_conflict(
        self, text1: str, text2: str
    ) -> Optional[Dict[str, Any]]:
        """Detects if statements assert contradictory numbers for the same unit/metric."""
        nums1 = self._extract_numbers_with_context(text1)
        nums2 = self._extract_numbers_with_context(text2)

        for val1, unit1 in nums1:
            for val2, unit2 in nums2:
                # If units match or unit is empty and values differ
                if val1 != val2:
                    if (unit1 and unit2 and unit1 == unit2) or (not unit1 and not unit2):
                        return {
                            "type": "numerical_conflict",
                            "claim_a_value": f"{val1} {unit1}".strip(),
                            "claim_b_value": f"{val2} {unit2}".strip(),
                            "reason": f"Discrepancy in numeric metric: '{val1}' vs '{val2}' ({unit1})"
                        }
        return None

    def _check_negation_conflict(
        self, tokens1: List[str], tokens2: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Detects if one statement affirms a topic while the other explicitly negates it."""
        has_neg1 = any(w in self.NEGATION_WORDS for w in tokens1)
        has_neg2 = any(w in self.NEGATION_WORDS for w in tokens2)

        # One has negation, the other does not
        if has_neg1 != has_neg2:
            shared_words = set(tokens1).intersection(set(tokens2)) - self.NEGATION_WORDS
            if len(shared_words) >= 2:
                neg_word = [w for w in (tokens1 if has_neg1 else tokens2) if w in self.NEGATION_WORDS][0]
                return {
                    "type": "negation_conflict",
                    "negation_trigger": neg_word,
                    "reason": f"Opposing assertion on shared subject words: {list(shared_words)[:3]}"
                }
        return None

    def _check_antonym_conflict(
        self, tokens1: List[str], tokens2: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Detects if statements contain opposing domain antonyms."""
        t1_set = set(tokens1)
        t2_set = set(tokens2)

        for w1, w2 in self.OPPOSING_ANTONYMS:
            if (w1 in t1_set and w2 in t2_set) or (w2 in t1_set and w1 in t2_set):
                return {
                    "type": "antonym_conflict",
                    "opposing_pair": (w1, w2),
                    "reason": f"Direct antonym contradiction: '{w1}' vs '{w2}'"
                }
        return None

    def detect_conflicts(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Scans a list of text chunks for direct factual contradictions.

        Args:
            chunks: List of chunk dictionaries containing 'id', 'text', and 'metadata'.

        Returns:
            List of structured conflict records:
            [
                {
                    "conflict_id": str,
                    "conflict_type": str,
                    "claim_a": {"chunk_id": str, "source_doc_id": str, "statement": str},
                    "claim_b": {"chunk_id": str, "source_doc_id": str, "statement": str},
                    "opposing_details": dict,
                    "confidence": float
                }
            ]
        """
        conflicts: List[Dict[str, Any]] = []
        conflict_idx = 1

        for i in range(len(chunks)):
            for j in range(i + 1, len(chunks)):
                chunk_a = chunks[i]
                chunk_b = chunks[j]

                text_a = chunk_a["text"]
                text_b = chunk_b["text"]

                tokens_a = self._tokenize(text_a)
                tokens_b = self._tokenize(text_b)

                topic_overlap = self._calculate_topic_overlap(tokens_a, tokens_b)

                # Chunks must discuss the same topic to be contradictory
                if topic_overlap < self.min_topic_overlap:
                    continue

                # Ignore exact or near-identical duplicates (handled by deduplication)
                if topic_overlap > self.max_text_similarity:
                    continue

                conflict_detail = None

                # 1. Numerical Conflict Check
                num_conflict = self._check_numerical_conflict(text_a, text_b)
                if num_conflict:
                    conflict_detail = num_conflict

                # 2. Negation Conflict Check
                if not conflict_detail:
                    neg_conflict = self._check_negation_conflict(tokens_a, tokens_b)
                    if neg_conflict:
                        conflict_detail = neg_conflict

                # 3. Antonym Conflict Check
                if not conflict_detail:
                    ant_conflict = self._check_antonym_conflict(tokens_a, tokens_b)
                    if ant_conflict:
                        conflict_detail = ant_conflict

                if conflict_detail:
                    doc_a = chunk_a.get("metadata", {}).get("doc_id", "unknown_doc_a")
                    doc_b = chunk_b.get("metadata", {}).get("doc_id", "unknown_doc_b")

                    conflicts.append({
                        "conflict_id": f"conflict_{conflict_idx:03d}",
                        "conflict_type": conflict_detail["type"],
                        "claim_a": {
                            "chunk_id": chunk_a["id"],
                            "source_doc_id": doc_a,
                            "statement": text_a
                        },
                        "claim_b": {
                            "chunk_id": chunk_b["id"],
                            "source_doc_id": doc_b,
                            "statement": text_b
                        },
                        "opposing_details": conflict_detail,
                        "confidence": 0.90,
                        "status": "unresolved"
                    })
                    conflict_idx += 1

        return conflicts
