"""
Unit tests for Conflict Tracker contradiction detection utility.
"""

import pytest
from retriever.conflict_tracker import ConflictTracker


def test_conflict_tracker_numerical_discrepancy():
    tracker = ConflictTracker()

    chunks = [
        {
            "id": "c1",
            "text": "The battery life of Aegis Research device is 10 hours under normal load.",
            "metadata": {"doc_id": "doc_specs_v1"}
        },
        {
            "id": "c2",
            "text": "The battery life of Aegis Research device is 4 hours under normal load.",
            "metadata": {"doc_id": "doc_specs_v2"}
        }
    ]

    conflicts = tracker.detect_conflicts(chunks)
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c["conflict_type"] == "numerical_conflict"
    assert c["claim_a"]["source_doc_id"] == "doc_specs_v1"
    assert c["claim_b"]["source_doc_id"] == "doc_specs_v2"
    assert "10" in c["opposing_details"]["claim_a_value"]
    assert "4" in c["opposing_details"]["claim_b_value"]


def test_conflict_tracker_negation_contradiction():
    tracker = ConflictTracker()

    chunks = [
        {
            "id": "c1",
            "text": "Aegis OS supports offline execution for research agents.",
            "metadata": {"doc_id": "doc_feature_a"}
        },
        {
            "id": "c2",
            "text": "Aegis OS does not support offline execution for research agents.",
            "metadata": {"doc_id": "doc_feature_b"}
        }
    ]

    conflicts = tracker.detect_conflicts(chunks)
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c["conflict_type"] == "negation_conflict"
    assert c["claim_a"]["chunk_id"] == "c1"
    assert c["claim_b"]["chunk_id"] == "c2"


def test_conflict_tracker_antonym_contradiction():
    tracker = ConflictTracker()

    chunks = [
        {
            "id": "c1",
            "text": "The autonomous agent database node is online.",
            "metadata": {"doc_id": "doc_sys_a"}
        },
        {
            "id": "c2",
            "text": "The autonomous agent database node is offline.",
            "metadata": {"doc_id": "doc_sys_b"}
        }
    ]

    conflicts = tracker.detect_conflicts(chunks)
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c["conflict_type"] == "antonym_conflict"
    assert c["opposing_details"]["opposing_pair"] == ("online", "offline")


def test_conflict_tracker_no_false_positives():
    tracker = ConflictTracker()

    chunks = [
        {
            "id": "c1",
            "text": "ChromaDB provides fast vector similarity search.",
            "metadata": {"doc_id": "doc_rag_1"}
        },
        {
            "id": "c2",
            "text": "BM25 ranker performs term frequency keyword scoring.",
            "metadata": {"doc_id": "doc_rag_2"}
        }
    ]

    conflicts = tracker.detect_conflicts(chunks)
    assert conflicts == []
