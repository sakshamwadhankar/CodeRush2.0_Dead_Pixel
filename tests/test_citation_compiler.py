"""
Unit tests for Step C4 Dynamic Citation Compiler and Markdown Parser.
"""

import json
import pytest
from src.data_rag.evidence_graph import EvidenceGraph
from src.data_rag.citation_compiler import MarkdownCitationParser, DynamicCitationCompiler


def test_markdown_citation_parser():
    parser = MarkdownCitationParser()
    draft_markdown = """# Executive Summary
Aegis Research OS provides an autonomous multi-agent platform for research planning [1].

## Security Infrastructure
Prompt injection defense mechanisms audit all tool calls before execution [^2].
Browsing sessions are sandboxed to avoid unsafe cross-site actions [Citation: doc_browser].
"""

    claims = parser.parse_markdown(draft_markdown)
    assert len(claims) == 3
    assert claims[0]["section_header"] == "Executive Summary"
    assert claims[0]["marker"] == "[1]"
    assert claims[1]["marker"] == "[^2]"
    assert claims[2]["marker"] == "[Citation: doc_browser]"


def test_dynamic_citation_compiler(tmp_path):
    graph = EvidenceGraph()

    # Populate graph with verified source data
    graph.add_document("doc_sec_v1", source_path="/docs/security_policy.pdf", title="Security Specs")
    graph.add_chunk(
        chunk_id="chunk_sec_01",
        text="Prompt injection defense mechanisms audit all tool calls before execution.",
        doc_id="doc_sec_v1",
        metadata={"source_path": "/docs/security_policy.pdf"}
    )

    compiler = DynamicCitationCompiler(evidence_graph=graph)

    draft = """# Security Audit Report
Prompt injection defense mechanisms audit all tool calls before execution [1].

Unverified claim stating that quantum servers run at zero Kelvin [2].
"""

    citation_summary = compiler.compile_citations(draft, draft_name="security_audit.md")

    assert citation_summary["total_claims"] == 2
    assert citation_summary["verified_claims_count"] == 1
    assert citation_summary["unverified_claims_count"] == 1
    assert citation_summary["verification_rate"] == 0.50

    c1 = citation_summary["citations"][0]
    assert c1["verification_status"] == "verified"
    assert "/docs/security_policy.pdf" in c1["provenance"]["source_paths"]

    c2 = citation_summary["citations"][1]
    assert c2["verification_status"] == "unverified"

    # Test state synchronization
    state_file = str(tmp_path / "state.json")
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump({"query": "security defense"}, f)

    updated_state = compiler.sync_with_state(draft, state_filepath=state_file)
    assert updated_state["status"] == "citations_compiled"
    assert len(updated_state["citations"]) == 2
    assert updated_state["citation_summary"]["verified_claims_count"] == 1
