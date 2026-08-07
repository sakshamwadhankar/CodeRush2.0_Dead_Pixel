"""
Semantic Text Chunker for Hybrid Live RAG Engine.
Splits raw text into context-aware passages preserving document structure and section headers.
"""

import re
from typing import List, Dict, Any, Optional


class SemanticChunker:
    """
    Context-aware semantic text chunker.
    Splits text while tracking section headers, maintaining paragraph/sentence boundaries,
    and enforcing chunk size and overlap constraints.
    """

    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 50):
        """
        Args:
            chunk_size: Target maximum character length for each chunk.
            chunk_overlap: Number of characters to overlap between consecutive chunks.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _extract_header(self, line: str) -> Optional[str]:
        """Check if line is a section header (e.g., # Header, ## Subheader, SECTION: Title)."""
        line_clean = line.strip()
        if re.match(r"^#{1,6}\s+.+", line_clean):
            return re.sub(r"^#{1,6}\s+", "", line_clean)
        if re.match(r"^(SECTION|CHAPTER|HEADING|TITLE):\s*.+", line_clean, re.IGNORECASE):
            return re.sub(r"^(SECTION|CHAPTER|HEADING|TITLE):\s*", "", line_clean, flags=re.IGNORECASE)
        return None

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split paragraph into sentences using punctuation boundaries."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def chunk_document(
        self, text: str, doc_id: str = "doc_0", extra_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Splits a document into structured passage chunks.

        Args:
            text: Raw input text.
            doc_id: Unique document identifier.
            extra_metadata: Optional key-value dictionary to attach to every chunk.

        Returns:
            List of chunk dictionaries with format:
            {
                "id": str,
                "text": str,
                "metadata": dict
            }
        """
        if not text or not text.strip():
            return []

        base_meta = extra_metadata or {}
        lines = text.splitlines()
        
        current_header = "General"
        sections: List[Dict[str, Any]] = []
        current_section_lines: List[str] = []

        for line in lines:
            header = self._extract_header(line)
            if header:
                if current_section_lines:
                    sections.append({
                        "header": current_header,
                        "text": "\n".join(current_section_lines).strip()
                    })
                    current_section_lines = []
                current_header = header
            else:
                current_section_lines.append(line)

        if current_section_lines:
            sections.append({
                "header": current_header,
                "text": "\n".join(current_section_lines).strip()
            })

        chunks: List[Dict[str, Any]] = []
        chunk_idx = 0

        for section in sections:
            header_context = section["header"]
            section_text = section["text"]
            if not section_text:
                continue

            paragraphs = [p.strip() for p in section_text.split("\n\n") if p.strip()]

            for para in paragraphs:
                if len(para) <= self.chunk_size:
                    chunk_text = f"[{header_context}] {para}" if header_context != "General" else para
                    chunk_id = f"{doc_id}_chunk_{chunk_idx}"
                    chunks.append({
                        "id": chunk_id,
                        "text": chunk_text,
                        "metadata": {
                            **base_meta,
                            "doc_id": doc_id,
                            "chunk_index": chunk_idx,
                            "header_context": header_context,
                            "raw_text": para,
                            "length": len(chunk_text)
                        }
                    })
                    chunk_idx += 1
                else:
                    sentences = self._split_into_sentences(para)
                    current_chunk_sentences: List[str] = []
                    current_len = 0

                    for sentence in sentences:
                        if current_len + len(sentence) > self.chunk_size and current_chunk_sentences:
                            chunk_body = " ".join(current_chunk_sentences)
                            chunk_text = f"[{header_context}] {chunk_body}" if header_context != "General" else chunk_body
                            chunk_id = f"{doc_id}_chunk_{chunk_idx}"
                            chunks.append({
                                "id": chunk_id,
                                "text": chunk_text,
                                "metadata": {
                                    **base_meta,
                                    "doc_id": doc_id,
                                    "chunk_index": chunk_idx,
                                    "header_context": header_context,
                                    "raw_text": chunk_body,
                                    "length": len(chunk_text)
                                }
                            })
                            chunk_idx += 1

                            overlap_sentences: List[str] = []
                            overlap_len = 0
                            for s in reversed(current_chunk_sentences):
                                if overlap_len + len(s) <= self.chunk_overlap:
                                    overlap_sentences.insert(0, s)
                                    overlap_len += len(s)
                                else:
                                    break
                            current_chunk_sentences = overlap_sentences
                            current_len = sum(len(s) + 1 for s in current_chunk_sentences)

                        current_chunk_sentences.append(sentence)
                        current_len += len(sentence) + 1

                    if current_chunk_sentences:
                        chunk_body = " ".join(current_chunk_sentences)
                        chunk_text = f"[{header_context}] {chunk_body}" if header_context != "General" else chunk_body
                        chunk_id = f"{doc_id}_chunk_{chunk_idx}"
                        chunks.append({
                            "id": chunk_id,
                            "text": chunk_text,
                            "metadata": {
                                **base_meta,
                                "doc_id": doc_id,
                                "chunk_index": chunk_idx,
                                "header_context": header_context,
                                "raw_text": chunk_body,
                                "length": len(chunk_text)
                            }
                        })
                        chunk_idx += 1

        return chunks
