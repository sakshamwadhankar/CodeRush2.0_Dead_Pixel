"""
Markdown Parser and Dynamic Citation Compiler for Aegis Research OS (Step C4).
Parses markdown drafts, validates claims against the NetworkX Evidence Graph,
and outputs structured JSON citation mappings.
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from src.data_rag.evidence_graph import EvidenceGraph


class MarkdownCitationParser:
    """
    Parses markdown report drafts to extract section headers, claims, and inline citation markers.
    """

    # Matches citation markers: [^1], [1], [Citation: doc_id], [Ref: doc_id]
    CITATION_MARKER_REGEX = r"(\[\^\d+\]|\[\d+\]|\[Citation:\s*[^\]]+\]|\[Ref:\s*[^\]]+\])"

    def parse_markdown(self, markdown_text: str) -> List[Dict[str, Any]]:
        """
        Parses raw markdown string and returns a list of extracted claim statements with citation markers.

        Args:
            markdown_text: Raw markdown draft content.

        Returns:
            List of claim dictionaries:
            [
                {
                    "claim_index": int,
                    "section_header": str,
                    "sentence": str,
                    "marker": Optional[str],
                    "clean_claim": str
                }
            ]
        """
        if not markdown_text or not markdown_text.strip():
            return []

        lines = markdown_text.splitlines()
        extracted_claims: List[Dict[str, Any]] = []

        current_header = "Executive Summary"
        claim_counter = 1

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Header detection
            if line_str.startswith("#"):
                current_header = line_str.lstrip("#").strip()
                continue

            # Sentence splitting within paragraph
            sentences = re.split(r"(?<=[.!?])\s+", line_str)

            for sentence in sentences:
                sentence_clean = sentence.strip()
                if not sentence_clean:
                    continue

                # Find citation markers in sentence
                markers = re.findall(self.CITATION_MARKER_REGEX, sentence_clean)
                marker_found = markers[0] if markers else None

                # Clean claim text (strip citation marker tag for verification)
                clean_claim = re.sub(self.CITATION_MARKER_REGEX, "", sentence_clean).strip()

                if len(clean_claim) > 10:  # Ignore trivial short fragments
                    extracted_claims.append({
                        "claim_index": claim_counter,
                        "section_header": current_header,
                        "sentence": sentence_clean,
                        "marker": marker_found,
                        "clean_claim": clean_claim
                    })
                    claim_counter += 1

        return extracted_claims


class DynamicCitationCompiler:
    """
    Cross-references extracted claims from markdown drafts with the Evidence Graph
    to generate clickable, verified JSON citation mappings for UI rendering.
    """

    def __init__(self, evidence_graph: Optional[EvidenceGraph] = None):
        self.parser = MarkdownCitationParser()
        self.evidence_graph = evidence_graph or EvidenceGraph()

    def compile_citations(
        self,
        markdown_draft: str,
        draft_name: str = "research_report_draft.md"
    ) -> Dict[str, Any]:
        """
        Parses draft, validates claims against evidence graph, and produces structured JSON citation map.

        Args:
            markdown_draft: Raw text of markdown report draft.
            draft_name: Name/path of draft file.

        Returns:
            Dict containing complete JSON citation report.
        """
        parsed_claims = self.parser.parse_markdown(markdown_draft)
        citation_entries: List[Dict[str, Any]] = []

        verified_count = 0
        unverified_count = 0

        for idx, claim_item in enumerate(parsed_claims, start=1):
            claim_text = claim_item["clean_claim"]
            marker = claim_item["marker"] or f"[{idx}]"
            header = claim_item["section_header"]

            # Query Evidence Graph to verify claim provenance
            verification = self.evidence_graph.verify_claim(marker if marker else claim_text)

            is_verified = verification["verified"]
            if is_verified:
                verified_count += 1
                status = "verified"
            else:
                unverified_count += 1
                status = "unverified"

            citation_entry = {
                "citation_id": f"cite_{idx:03d}",
                "marker": marker,
                "claim_text": claim_text,
                "raw_sentence": claim_item["sentence"],
                "section_header": header,
                "verification_status": status,
                "confidence": verification["confidence"],
                "uncertainty": verification.get("uncertainty", 0.0),
                "lineage": verification.get("lineage", ""),
                "provenance": {
                    "claim_id": verification.get("claim_id"),
                    "supporting_chunk_ids": verification["supporting_chunk_ids"],
                    "source_paths": verification["source_paths"],
                    "raw_quotes": verification["quotes"]
                }
            }
            citation_entries.append(citation_entry)

        summary = {
            "draft_file": draft_name,
            "total_claims": len(parsed_claims),
            "verified_claims_count": verified_count,
            "unverified_claims_count": unverified_count,
            "verification_rate": round(verified_count / len(parsed_claims), 2) if parsed_claims else 0.0,
            "citations": citation_entries
        }

        return summary

    def sync_with_state(
        self,
        markdown_draft: str,
        state_filepath: str = "state.json"
    ) -> Dict[str, Any]:
        """
        Compiles citation mapping and writes JSON summary into shared state.json contract.

        Args:
            markdown_draft: Raw markdown report text.
            state_filepath: Path to state.json.

        Returns:
            Updated state dict.
        """
        citation_map = self.compile_citations(markdown_draft)

        if not re.search(r"^[A-Za-z]:", state_filepath) and not state_filepath.startswith("/"):
            pass  # relative path

        try:
            with open(state_filepath, "r", encoding="utf-8") as f:
                state_data = json.load(f)
        except Exception:
            state_data = {"project_name": "Aegis Research OS"}

        state_data["citations"] = citation_map["citations"]
        state_data["citation_summary"] = {
            "draft_file": citation_map["draft_file"],
            "total_claims": citation_map["total_claims"],
            "verified_claims_count": citation_map["verified_claims_count"],
            "unverified_claims_count": citation_map["unverified_claims_count"],
            "verification_rate": citation_map["verification_rate"]
        }
        state_data["status"] = "citations_compiled"

        with open(state_filepath, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)

        return state_data
