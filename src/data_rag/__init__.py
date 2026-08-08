"""
Hybrid Live RAG Engine Package for Aegis Research OS.
Includes semantic chunking, dense vector search, BM25 keyword search, RRF fusion,
chunk deduplication, conflict tracking, NetworkX Evidence Graph, and Dynamic Citation Compiler.
"""

from src.data_rag.chunker import SemanticChunker
from src.data_rag.dense_store import ChromaDenseStore
from src.data_rag.bm25_ranker import BM25Ranker
from src.data_rag.fusion import ReciprocalRankFusion
from src.data_rag.deduplicator import ChunkDeduplicator
from src.data_rag.conflict_tracker import ConflictTracker
from src.data_rag.evidence_graph import EvidenceGraph
from src.data_rag.citation_compiler import MarkdownCitationParser, DynamicCitationCompiler
from src.data_rag.hybrid_engine import HybridRAGEngine

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
    "HybridRAGEngine"
]
