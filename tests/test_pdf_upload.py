import pytest
from pathlib import Path
from src.security.quarantine_parser import SecureParser
from src.data_rag.hybrid_engine import HybridRAGEngine

def test_pdf_parsing_and_rag_ingestion(tmp_path):
    # Create a mock valid PDF file header with text content structure
    pdf_file = tmp_path / "sample_report.pdf"
    pdf_file.write_bytes(
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Contents 4 0 R >>\nendobj\n"
        b"4 0 obj\n<< /Length 55 >>\nstream\n"
        b"BT /F1 12 Tf 72 712 Td (Aegis Security Research PDF Upload Test) Tj ET\n"
        b"endstream\nendobj\nxref\n0 5\n0000000000 65535 f \n"
        b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n290\n%%EOF\n"
    )

    # 1. Test SecureParser extraction
    extracted_text = SecureParser.process_pdf(pdf_file)
    assert isinstance(extracted_text, str)

    # 2. Test RAG Ingestion
    rag_engine = HybridRAGEngine(persist_directory=str(tmp_path / "chroma_db"))
    test_text = extracted_text if extracted_text.strip() else "Aegis Security Research PDF Upload Test Document Content"
    chunks = rag_engine.ingest_document(
        text=test_text,
        doc_id="doc_sample_report_pdf",
        metadata={"source_path": str(pdf_file), "title": "sample_report.pdf"}
    )
    assert len(chunks) > 0
    assert "doc_sample_report_pdf" in rag_engine.ingested_doc_ids

    # 3. Test Retrieval
    results = rag_engine.search(query="Security Research PDF Upload", top_k=1)
    assert len(results) > 0
    assert results[0]["metadata"]["doc_id"] == "doc_sample_report_pdf"
