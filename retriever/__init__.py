"""
Hybrid Live RAG Engine Package for Aegis Research OS.
Includes semantic chunking, dense vector search, BM25 keyword search, RRF fusion,
chunk deduplication, conflict tracking, NetworkX Evidence Graph, and Dynamic Citation Compiler.
"""

from retriever.chunker import SemanticChunker
from retriever.dense_store import ChromaDenseStore
from retriever.bm25_ranker import BM25Ranker
from retriever.fusion import ReciprocalRankFusion
from retriever.deduplicator import ChunkDeduplicator
from retriever.conflict_tracker import ConflictTracker
from retriever.evidence_graph import EvidenceGraph
from retriever.citation_compiler import MarkdownCitationParser, DynamicCitationCompiler
from retriever.hybrid_engine import HybridRAGEngine
from retriever.mock_retriever import MockHybridRAGEngine

__all__ = [
    "SemanticChunker",
    "ChromaDenseStore",
    "BM25Ranker",
    "ReciprocalRankFusion",
    "ChunkDeduplicator",
    "ConflictTracker",
    "EvidenceGraph",
    "MarkdownCitationParser",
    "DynamicCitationCompiler",
    "HybridRAGEngine",
    "MockHybridRAGEngine"
]
