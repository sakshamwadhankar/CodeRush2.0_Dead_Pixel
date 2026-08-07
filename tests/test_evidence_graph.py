"""
Unit tests for Step C3 NetworkX Evidence Graph.
"""

import pytest
from src.data_rag.evidence_graph import EvidenceGraph


def test_evidence_graph_construction_and_verification():
    graph = EvidenceGraph()

    graph.add_document(doc_id="doc_specs_v1", source_path="/sources/doc_specs_v1.pdf", title="Aegis Specs")
    graph.add_chunk(
        chunk_id="chunk_01",
        text="Aegis Research OS provides an autonomous multi-agent platform for research planning.",
        doc_id="doc_specs_v1",
        metadata={"source_path": "/sources/doc_specs_v1.pdf"}
    )
    graph.add_claim(
        claim_id="claim_01",
        text="Aegis Research OS provides an autonomous multi-agent platform for research planning.",
        supported_by_chunk_ids=["chunk_01"],
        confidence=0.95
    )

    assert graph.node_count() == 3
    assert graph.edge_count() == 2

    # Verify claim via exact claim ID
    v1 = graph.verify_claim("claim_01")
    assert v1["verified"] is True
    assert v1["confidence"] == 0.95
    assert "/sources/doc_specs_v1.pdf" in v1["source_paths"]

    # Verify claim via text matching
    v2 = graph.verify_claim("Aegis Research OS provides an autonomous multi-agent platform")
    assert v2["verified"] is True
    assert len(v2["supporting_chunk_ids"]) > 0


def test_evidence_graph_unsupported_claim():
    graph = EvidenceGraph()
    graph.add_document("doc_01")

    res = graph.verify_claim("Completely unverified random claim about unrelated space exploration")
    assert res["verified"] is False
    assert res["confidence"] == 0.0
    assert res["supporting_chunk_ids"] == []
