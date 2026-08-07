"""
Unit tests for Semantic Text Chunker.
"""

import pytest
from src.data_rag.chunker import SemanticChunker


def test_chunker_header_extraction_and_context():
    raw_text = """# Security Policy
Aegis Research OS strictly enforces security boundaries.

## Prompt Injection Protection
Prompt injection is prevented through multi-stage sanitization and validation gates.

## Browser Isolation
Browsing sessions are sandboxed to avoid unsafe cross-site actions.
"""
    chunker = SemanticChunker(chunk_size=300, chunk_overlap=30)
    chunks = chunker.chunk_document(raw_text, doc_id="doc_security")

    assert len(chunks) >= 3
    assert chunks[0]["metadata"]["header_context"] == "Security Policy"
    assert chunks[1]["metadata"]["header_context"] == "Prompt Injection Protection"
    assert "[Prompt Injection Protection]" in chunks[1]["text"]
    assert chunks[2]["metadata"]["header_context"] == "Browser Isolation"


def test_chunker_empty_input():
    chunker = SemanticChunker()
    chunks = chunker.chunk_document("", doc_id="doc_empty")
    assert chunks == []


def test_chunker_large_paragraph_overlap():
    paragraph = "Aegis OS evaluates autonomous AI research agents. " * 20
    chunker = SemanticChunker(chunk_size=150, chunk_overlap=40)
    chunks = chunker.chunk_document(paragraph, doc_id="doc_large")

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk["text"]) <= 250  # Allows small header padding
        assert chunk["metadata"]["doc_id"] == "doc_large"
