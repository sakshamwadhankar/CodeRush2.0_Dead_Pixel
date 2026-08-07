import json
import time
from pathlib import Path
from unittest.mock import patch
import pytest

from quarantine_parser import QuarantineService, SecureParser

@pytest.fixture
def quarantine_env(tmp_path):
    workspace = tmp_path / "workspace"
    audit = tmp_path / "audit_log.json"
    service = QuarantineService(workspace_dir=workspace, audit_log_path=audit)
    return service, workspace, audit

def test_csv_formula_injection_sanitization(quarantine_env):
    service, workspace, audit = quarantine_env
    csv_path = service.quarantine_dir / "malicious.csv"
    
    # Create malicious CSV containing command injections and macro strings
    # in both headers and cell bodies
    content = "=cmd|' /C calc'!A1,SafeCol\n+1+2,normal\n-rm -rf,normal\n@SUM(A1:A2),normal"
    csv_path.write_text(content)
    
    # Directly process to test parsing logic without threading
    service.process_file(csv_path)
    
    # Verify file was isolated and removed from quarantine
    assert not csv_path.exists()
    
    # Verify sanitized file exists in JSON form
    sanitized_files = list(service.sanitized_dir.glob("*.json"))
    assert len(sanitized_files) == 1
    
    sanitized_json = json.loads(sanitized_files[0].read_text())
    assert isinstance(sanitized_json, list)
    assert len(sanitized_json) == 3
    
    # Check escaping on cells and headers
    header_key = "'=cmd|' /C calc'!A1"
    assert header_key in sanitized_json[0]
    assert sanitized_json[0][header_key] == "'+1+2"
    assert sanitized_json[1][header_key] == "'-rm -rf"
    assert sanitized_json[2][header_key] == "'@SUM(A1:A2)"

def test_unrecognized_format(quarantine_env):
    service, workspace, audit = quarantine_env
    bad_path = service.quarantine_dir / "payload.exe"
    bad_path.write_text("MZ...")
    
    service.process_file(bad_path)
    
    # Fail closed: the file must remain trapped in quarantine
    assert bad_path.exists()
    assert len(list(service.sanitized_dir.iterdir())) == 0
    
    with open(audit, "r") as f:
        logs = json.load(f)
    assert logs[-1]["sanitization_status"] == "quarantined_malicious"
    assert "Unrecognized or hostile file format" in logs[-1]["error"]

def test_txt_extraction_and_lifecycle(quarantine_env):
    service, workspace, audit = quarantine_env
    txt_path = service.quarantine_dir / "safe.txt"
    txt_path.write_text("Safe content")
    
    service.process_file(txt_path)
    
    assert not txt_path.exists()
    sanitized = list(service.sanitized_dir.glob("*.txt"))
    assert len(sanitized) == 1
    assert sanitized[0].read_text() == "Safe content"

def test_real_time_detection(quarantine_env):
    service, workspace, audit = quarantine_env
    
    # Spin up the watchdog thread
    service.start()
    
    txt_path = service.quarantine_dir / "watched.txt"
    # Trigger watchdog `on_created` event
    txt_path.write_text("Trigger watchdog")
    
    # Allow async thread processing time
    time.sleep(1)
    service.stop()
    
    # Validates interception, processing, and promotion
    assert not txt_path.exists()
    sanitized = list(service.sanitized_dir.glob("*.txt"))
    assert len(sanitized) == 1
    assert sanitized[0].read_text() == "Trigger watchdog"

    with open(audit, "r") as f:
        logs = json.load(f)
    assert logs[-1]["sanitization_status"] == "success"

def test_magic_byte_validation(quarantine_env):
    service, workspace, audit = quarantine_env
    fake_pdf = service.quarantine_dir / "fake.pdf"
    fake_pdf.write_bytes(b"NOT A PDF HEADER")
    
    service.process_file(fake_pdf)
    
    assert fake_pdf.exists()
    with open(audit, "r") as f:
        logs = json.load(f)
    assert logs[-1]["sanitization_status"] == "quarantined_malicious"
    assert "Magic byte signature mismatch" in logs[-1]["error"]

def test_size_limit_validation(quarantine_env):
    service, workspace, audit = quarantine_env
    huge_file = service.quarantine_dir / "huge.txt"
    
    # Mock stat to pretend file is 30MB without writing to disk
    with patch("pathlib.Path.stat") as mock_stat:
        mock_stat.return_value.st_size = 30 * 1024 * 1024
        huge_file.write_text("Dummy content")
        service.process_file(huge_file)
        
    assert huge_file.exists()
    with open(audit, "r") as f:
        logs = json.load(f)
    assert logs[-1]["sanitization_status"] == "quarantined_malicious"
    assert "size_limit_exceeded" in logs[-1]["error"]
