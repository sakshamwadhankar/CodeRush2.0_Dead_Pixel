import pytest
from pathlib import Path
from src.security.quarantine_parser import SecureParser
from src.data_rag.hybrid_engine import HybridRAGEngine
from src.security.policy_engine import PolicyEngine

def test_ocr_fallback(tmp_path):
    """1. Successful extraction of text from a completely non-digital, scanned test PDF."""
    from unittest.mock import patch
    
    # Create a mock empty PDF (invalid PDF structure, will fail pypdf and trigger fallback)
    pdf_path = tmp_path / "scanned_doc.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%EOF\n")
    
    # We patch the actual module functions that process_pdf imports and calls
    with patch("src.security.quarantine_parser.convert_from_path") as mock_convert, \
         patch("src.security.quarantine_parser.pytesseract.image_to_string") as mock_ocr:
         
        mock_convert.return_value = ["mock_image_1"]
        mock_ocr.return_value = "Extracted OCR Text from scanned document."
        
        parser = SecureParser()
        extracted_text = parser.process_pdf(pdf_path)
    
    assert "Extracted OCR Text" in extracted_text

def test_multilingual_rag():
    """2. Successful vector retrieval of non-English queries against English stored chunks."""
    engine = HybridRAGEngine(collection_name="test_multilingual_rag")
    
    # Ingest English text
    engine.ingest_document("The capital of France is Paris.", doc_id="doc_france")
    
    # Query in Spanish: "Cual es la capital de Francia?"
    spanish_query = "¿Cuál es la capital de Francia?"
    
    # Search should translate to English, match the English chunk, and translate back to Spanish
    results = engine.search(query=spanish_query, top_k=1)
    
    assert len(results) > 0
    # The returned text should be in Spanish since it translates the fused results back.
    # Note: deep-translator might return "La capital de Francia es París."
    # We just check if the translation occurred (i.e., it's not the exact English string)
    assert results[0]["text"] != "The capital of France is Paris."
    assert "París" in results[0]["text"] or "Paris" in results[0]["text"]

def test_policy_engine_blocking():
    """3. Immediate detection and shutdown of a simulated self-proposed strategy attempting a privilege escalation."""
    engine = PolicyEngine()
    
    malicious_yaml = """
name: "Advanced Strategy"
version: 2
steps:
  - run: "os.environ.get('OPENAI_API_KEY')"
  - override_approval: true
    """
    
    passed, reason = engine.validate_strategy(malicious_yaml)
    assert passed is False
    assert "Malicious pattern detected" in reason
    
    directory_bypass_yaml = """
name: "Read System File"
target_path: "/etc/passwd"
    """
    passed, reason = engine.validate_strategy(directory_bypass_yaml)
    assert passed is False
    assert "Directory access violation" in reason

    benign_yaml = """
name: "Standard Search"
target_path: "/workspace/sanitized/data.csv"
steps:
  - query: "Find revenue"
    """
    passed, reason = engine.validate_strategy(benign_yaml)
    assert passed is True
