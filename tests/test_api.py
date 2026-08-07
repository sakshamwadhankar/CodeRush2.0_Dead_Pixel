import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from api import app, AUTH_TOKEN

client = TestClient(app)
HEADERS = {"Authorization": f"Bearer {AUTH_TOKEN}"}

def test_unauthorized_access():
    """Verify HTTP 401 Unauthorized is returned for bad or missing tokens."""
    # Missing Token
    response = client.post("/sandbox/execute", json={"code": "print('hello')"})
    assert response.status_code == 401
    
    # Bad Token
    bad_headers = {"Authorization": "Bearer INVALID_HACKER_TOKEN"}
    response = client.post("/sandbox/execute", headers=bad_headers, json={"code": "print('hello')"})
    assert response.status_code == 401

@patch("api.sandbox_manager.execute_code")
def test_successful_execution(mock_execute):
    """Verify code execution payload correctly hits the backend and returns JSON."""
    mock_execute.return_value = {"status": "success", "stdout": "hello\n", "exit_code": 0}
    
    response = client.post("/sandbox/execute", headers=HEADERS, json={"code": "print('hello')", "language": "python"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["stdout"] == "hello\n"
    mock_execute.assert_called_once_with("print('hello')", "python")

@patch("api.snapshot_manager.create_checkpoint")
@patch("api.snapshot_manager.rollback_to_checkpoint")
def test_snapshot_and_rollback(mock_rollback, mock_create):
    """Verify HTTP requests successfully command snapshot and rollback engines."""
    mock_create.return_value = "/path/to/snap.tar"
    
    # Checkpoint Request
    res = client.post("/sandbox/checkpoint", headers=HEADERS, json={"checkpoint_name": "test_snap"})
    assert res.status_code == 200
    assert res.json()["checkpoint_path"] == "/path/to/snap.tar"
    mock_create.assert_called_once_with("test_snap")
    
    # Rollback Request
    res = client.post("/sandbox/rollback", headers=HEADERS, json={"checkpoint_name": "test_snap"})
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    mock_rollback.assert_called_once_with("test_snap")

@patch("api.browser_controller.browse_page")
def test_browser_scrape_error_formatting(mock_browse):
    """Verify that browser failures (like timeouts) are formatted cleanly as 400 Bad Requests."""
    mock_browse.return_value = {
        "status": "error", 
        "metadata": {"error": "Page load timeout exceeded (20s)"}
    }
    
    response = client.post("/browser/scrape", headers=HEADERS, json={"url": "http://slow-site.test"})
    
    # Fail closed on browser errors
    assert response.status_code == 400
    assert response.json()["detail"] == "Page load timeout exceeded (20s)"
    mock_browse.assert_called_once_with("http://slow-site.test")
