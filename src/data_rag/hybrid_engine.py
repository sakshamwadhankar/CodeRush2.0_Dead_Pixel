"""
Hybrid Live RAG Engine orchestrating Semantic Chunker, ChromaDB Dense Store, BM25 Ranker, RRF Fusion,
Chunk Deduplicator, Conflict Tracker, Evidence Graph, and Dynamic Citation Compiler.
Integrates with state.json contract for Developer A's orchestrator workflow.
"""

import json
import os
from typing import List, Dict, Any, Optional

from src.data_rag.chunker import SemanticChunker
from src.data_rag.dense_store import ChromaDenseStore
from src.data_rag.bm25_ranker import BM25Ranker
from src.data_rag.fusion import ReciprocalRankFusion
from src.data_rag.deduplicator import ChunkDeduplicator
from src.data_rag.conflict_tracker import ConflictTracker
from src.data_rag.evidence_graph import EvidenceGraph
from src.data_rag.citation_compiler import DynamicCitationCompiler


class HybridRAGEngine:
    """
    Main Hybrid RAG Engine providing complete data, retrieval, evidence graph,
    and citation compilation functionality for Aegis Research OS.
    """

    def __init__(
        self,
        collection_name: str = "aegis_hybrid_rag",
        persist_directory: Optional[str] = None,
        chunk_size: int = 400,
        chunk_overlap: int = 50,
        rrf_k: int = 60,
        dedup_threshold: float = 0.85
    ):
        self.chunker = SemanticChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.dense_store = ChromaDenseStore(
            collection_name=collection_name,
            persist_directory=persist_directory
        )
        self.bm25_ranker = BM25Ranker()
        self.fusion = ReciprocalRankFusion(rrf_k=rrf_k)
        self.deduplicator = ChunkDeduplicator(similarity_threshold=dedup_threshold)
        self.conflict_tracker = ConflictTracker()
        self.evidence_graph = EvidenceGraph()
        self.citation_compiler = DynamicCitationCompiler(evidence_graph=self.evidence_graph)
        self.ingested_doc_ids: List[str] = []

    def ingest_document(
        self, text: str, doc_id: str = "doc_0", metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Chunks and indexes document into ChromaDB, BM25, and NetworkX Evidence Graph.
        """
        meta = metadata or {}
        source_path = meta.get("source_path") or f"/sources/{doc_id}.txt"
        self.evidence_graph.add_document(doc_id=doc_id, source_path=source_path, title=doc_id)

        chunks = self.chunker.chunk_document(text=text, doc_id=doc_id, extra_metadata=meta)
        if chunks:
            self.dense_store.add_passages(chunks)
            self.bm25_ranker.index_passages(chunks)
            for chunk in chunks:
                self.evidence_graph.add_chunk(
                    chunk_id=chunk["id"],
                    text=chunk["text"],
                    doc_id=doc_id,
                    metadata=chunk.get("metadata")
                )
            if doc_id not in self.ingested_doc_ids:
                self.ingested_doc_ids.append(doc_id)
        return chunks

    def ingest_passages(self, chunks: List[Dict[str, Any]]) -> None:
        """Indexes pre-chunked passages across all stores."""
        if chunks:
            self.dense_store.add_passages(chunks)
            self.bm25_ranker.index_passages(chunks)
            for chunk in chunks:
                doc_id = chunk.get("metadata", {}).get("doc_id", "doc_unknown")
                self.evidence_graph.add_chunk(
                    chunk_id=chunk["id"],
                    text=chunk["text"],
                    doc_id=doc_id,
                    metadata=chunk.get("metadata")
                )
                if doc_id not in self.ingested_doc_ids:
                    self.ingested_doc_ids.append(doc_id)

    def search(
        self,
        query: str,
        top_k: int = 5,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Performs hybrid dense vector and sparse BM25 retrieval with RRF fusion."""
        if not query or not query.strip():
            return []

        dense_top = self.dense_store.query(query_text=query, top_k=top_k * 2)
        sparse_top = self.bm25_ranker.query(query_text=query, top_k=top_k * 2)

        fused_results = self.fusion.fuse(
            dense_results=dense_top,
            sparse_results=sparse_top,
            top_k=top_k,
            dense_weight=dense_weight,
            sparse_weight=sparse_weight
        )

        return fused_results

    def deduplicate_passages(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.deduplicator.deduplicate(chunks)

    def detect_conflicts(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self.conflict_tracker.detect_conflicts(chunks)

    def compile_citations(self, markdown_draft: str) -> Dict[str, Any]:
        """Parses markdown draft and cross-references claims with Evidence Graph."""
        return self.citation_compiler.compile_citations(markdown_draft)

    def reset(self) -> None:
        """Clears all stores and resets evidence graph."""
        self.dense_store.clear()
        self.bm25_ranker.clear()
        self.evidence_graph = EvidenceGraph()
        self.citation_compiler = DynamicCitationCompiler(evidence_graph=self.evidence_graph)
        self.ingested_doc_ids = []

    def sync_with_state(self, state_filepath: str = "state.json") -> Dict[str, Any]:
        """
        Synchronizes retrieval, deduplication, conflict tracking, and citation mappings
        with state.json contract.
        """
        if not os.path.exists(state_filepath):
            state_data = {
                "project_name": "Aegis Research OS",
                "module": "Hybrid Live RAG Engine",
                "active_task_id": "task_c4_citation_compiler",
                "query": "",
                "markdown_draft": "",
                "retrieval_config": {"top_k": 5, "dense_weight": 0.5, "sparse_weight": 0.5},
                "ingested_documents": self.ingested_doc_ids,
                "search_results": [],
                "deduplicated_results": [],
                "tracked_conflicts": [],
                "citations": [],
                "status": "idle"
            }
        else:
            with open(state_filepath, "r", encoding="utf-8") as f:
                state_data = json.load(f)

        query = state_data.get("query", "").strip()
        markdown_draft = state_data.get("markdown_draft", "").strip()
        config = state_data.get("retrieval_config", {})
        top_k = config.get("top_k", 5)

        if query:
            results = self.search(query=query, top_k=top_k)
            state_data["search_results"] = results
            dedup_output = self.deduplicate_passages(results)
            state_data["deduplicated_results"] = dedup_output["deduplicated_chunks"]
            state_data["tracked_conflicts"] = self.detect_conflicts(results)

        if markdown_draft:
            citation_map = self.compile_citations(markdown_draft)
            state_data["citations"] = citation_map["citations"]
            state_data["citation_summary"] = {
                "total_claims": citation_map["total_claims"],
                "verified_claims_count": citation_map["verified_claims_count"],
                "verification_rate": citation_map["verification_rate"]
            }

        state_data["evidence_graph_nodes"] = self.evidence_graph.node_count()
        state_data["status"] = "completed"
        state_data["ingested_documents"] = list(set(state_data.get("ingested_documents", []) + self.ingested_doc_ids))

        with open(state_filepath, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)

        return state_data
