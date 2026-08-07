"""
NetworkX Evidence Graph Utility for Aegis Research OS (Step C3).
Tracks document, chunk, and claim provenance relationships.
"""

from typing import List, Dict, Any, Optional, Set
import networkx as nx
import datetime


class EvidenceGraph:
    """
    Directed Graph maintaining provenance linkages between Documents, Chunks, and Claims.
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_document(
        self,
        doc_id: str,
        source_path: str = "",
        title: str = "",
        timestamp: Optional[str] = None
    ) -> None:
        """Adds a Document node to the evidence graph."""
        ts = timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.graph.add_node(
            doc_id,
            node_type="document",
            source_path=source_path or f"/sources/{doc_id}.txt",
            title=title or doc_id,
            timestamp=ts
        )

    def add_chunk(
        self,
        chunk_id: str,
        text: str,
        doc_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Adds a Chunk node and links it to its parent Document via CONTAINS edge."""
        meta = metadata or {}
        source_path = meta.get("source_path") or f"/sources/{doc_id}.txt"
        timestamp = meta.get("timestamp") or datetime.datetime.now(datetime.timezone.utc).isoformat()

        if not self.graph.has_node(doc_id):
            self.add_document(doc_id=doc_id, source_path=source_path, timestamp=timestamp)

        self.graph.add_node(
            chunk_id,
            node_type="chunk",
            text=text,
            doc_id=doc_id,
            header_context=meta.get("header_context", "General"),
            source_path=source_path,
            timestamp=timestamp
        )

        self.graph.add_edge(doc_id, chunk_id, relation="CONTAINS")

    def add_claim(
        self,
        claim_id: str,
        text: str,
        supported_by_chunk_ids: Optional[List[str]] = None,
        confidence: float = 0.90
    ) -> None:
        """Adds a Claim node and links it to supporting Chunk nodes via SUPPORTED_BY edges."""
        self.graph.add_node(
            claim_id,
            node_type="claim",
            text=text,
            confidence=confidence
        )

        if supported_by_chunk_ids:
            for chunk_id in supported_by_chunk_ids:
                if self.graph.has_node(chunk_id):
                    self.graph.add_edge(claim_id, chunk_id, relation="SUPPORTED_BY")

    def add_contradiction(self, claim_id_a: str, claim_id_b: str, reason: str = "") -> None:
        """Adds a CONTRADICTS edge between two conflicting claims."""
        if self.graph.has_node(claim_id_a) and self.graph.has_node(claim_id_b):
            self.graph.add_edge(claim_id_a, claim_id_b, relation="CONTRADICTS", reason=reason)
            self.graph.add_edge(claim_id_b, claim_id_a, relation="CONTRADICTS", reason=reason)

    def verify_claim(self, claim_text_or_id: str) -> Dict[str, Any]:
        """
        Queries the evidence graph to verify if a claim is supported by underlying passages.

        Args:
            claim_text_or_id: Claim node ID or string text.

        Returns:
            Dict containing verification status, confidence, supporting chunks, quotes, and sources.
        """
        # Find matching claim node or search by text similarity
        target_node = None
        if self.graph.has_node(claim_text_or_id):
            target_node = claim_text_or_id
        else:
            for node, attrs in self.graph.nodes(data=True):
                if attrs.get("node_type") == "claim" and attrs.get("text") == claim_text_or_id:
                    target_node = node
                    break

        if not target_node:
            # Check if any chunk text directly supports the statement
            matching_chunks = []
            for node, attrs in self.graph.nodes(data=True):
                if attrs.get("node_type") == "chunk":
                    chunk_text = attrs.get("text", "")
                    if claim_text_or_id.lower() in chunk_text.lower() or any(
                        word in chunk_text.lower() for word in claim_text_or_id.lower().split() if len(word) > 4
                    ):
                        matching_chunks.append(node)

            if matching_chunks:
                sources = []
                quotes = []
                for cid in matching_chunks:
                    cattrs = self.graph.nodes[cid]
                    sources.append(cattrs.get("source_path", ""))
                    quotes.append(cattrs.get("text", ""))

                return {
                    "verified": True,
                    "confidence": 0.85,
                    "claim_id": f"claim_auto_{len(matching_chunks)}",
                    "supporting_chunk_ids": matching_chunks,
                    "source_paths": list(set(sources)),
                    "quotes": quotes
                }

            return {
                "verified": False,
                "confidence": 0.0,
                "claim_id": None,
                "supporting_chunk_ids": [],
                "source_paths": [],
                "quotes": []
            }

        supporting_chunks = []
        sources = []
        quotes = []

        for _, neighbor, edge_attrs in self.graph.out_edges(target_node, data=True):
            if edge_attrs.get("relation") == "SUPPORTED_BY":
                supporting_chunks.append(neighbor)
                chunk_attrs = self.graph.nodes[neighbor]
                sources.append(chunk_attrs.get("source_path", ""))
                quotes.append(chunk_attrs.get("text", ""))

        confidence = self.graph.nodes[target_node].get("confidence", 0.90)

        return {
            "verified": len(supporting_chunks) > 0,
            "confidence": confidence if supporting_chunks else 0.0,
            "claim_id": target_node,
            "supporting_chunk_ids": supporting_chunks,
            "source_paths": list(set(sources)),
            "quotes": quotes
        }

    def node_count(self) -> int:
        return self.graph.number_of_nodes()

    def edge_count(self) -> int:
        return self.graph.number_of_edges()
