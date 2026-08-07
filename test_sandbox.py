import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from sandbox import SandboxManager


@pytest.fixture
def temp_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    audit_file = tmp_path / "audit_log.json"
    return workspace, audit_file


def test_path_traversal_prevention(temp_workspace):
    workspace, audit_file = temp_workspace
    manager = SandboxManager(workspace_dir=str(workspace), audit_log_path=str(audit_file))
    
    # Path inside workspace
    inside_path = workspace / "script.py"
    assert manager._validate_path_safety(inside_path) is True
    
    # Path outside workspace
    outside_path = workspace / ".." / "outside.py"
    assert manager._validate_path_safety(outside_path) is False


def test_fail_closed_when_docker_unresponsive(temp_workspace):
    workspace, audit_file = temp_workspace
    manager = SandboxManager(workspace_dir=str(workspace), audit_log_path=str(audit_file))
    
    # Force docker client to be None or unresponsive
    manager.client = None
    
    result = manager.execute_code("print('Test Fail Closed')")
    
    assert result["status"] == "system_error"
    assert result["exit_code"] == -1
    assert "Docker daemon is unresponsive" in result["error"]
    assert audit_file.exists()


def test_audit_logger_format(temp_workspace):
    workspace, audit_file = temp_workspace
    manager = SandboxManager(workspace_dir=str(workspace), audit_log_path=str(audit_file))
    
    # Mocking Docker execution for deterministic audit log test
    manager.client = MagicMock()
    manager.client.ping.return_value = True
    
    mock_container = MagicMock()
    mock_container.wait.return_value = {"StatusCode": 0}
    mock_container.logs.side_effect = [
        b"Audit Test Success\n",  # stdout
        b"",                      # stderr
    ]
    manager.client.containers.run.return_value = mock_container
    
    result = manager.execute_code("print('Audit Test')", language="python")
    
    assert result["status"] == "success"
    assert result["exit_code"] == 0
    assert result["stdout"] == "Audit Test Success\n"
    
    assert audit_file.exists()
    with open(audit_file, "r", encoding="utf-8") as f:
        logs = json.load(f)
    
    # We now have 2 logs: snapshot_create and sandbox execution
    assert len(logs) == 2
    
    exec_entry = [l for l in logs if "language" in l and "exit_code" in l][0]
    assert exec_entry["status"] == "success"
    assert exec_entry["language"] == "python"
    assert "resource_limits" in exec_entry
    assert exec_entry["resource_limits"]["network_mode"] == "none"


def test_execution_timeout_mock(temp_workspace):
    workspace, audit_file = temp_workspace
    manager = SandboxManager(workspace_dir=str(workspace), audit_log_path=str(audit_file))
    
    manager.client = MagicMock()
    manager.client.ping.return_value = True
    
    mock_container = MagicMock()
    # Simulate wait raising exception due to timeout
    mock_container.wait.side_effect = Exception("Container wait timeout")
    mock_container.logs.side_effect = [b"", b""]
    manager.client.containers.run.return_value = mock_container
    
    result = manager.execute_code("import time; time.sleep(100)", timeout=1.0)
    
    assert result["status"] == "timeout"
    assert result["exit_code"] == -1
    assert "Execution timed out" in result["error"]
    mock_container.kill.assert_called_once()


def test_network_isolation_configuration(temp_workspace):
    workspace, audit_file = temp_workspace
    manager = SandboxManager(workspace_dir=str(workspace), audit_log_path=str(audit_file))
    
    manager.client = MagicMock()
    manager.client.ping.return_value = True
    
    mock_container = MagicMock()
    mock_container.wait.return_value = {"StatusCode": 1}
    mock_container.logs.side_effect = [
        b"",
        b"urllib.error.URLError: <urlopen error [Errno -3] Temporary failure in name resolution>",
    ]
    manager.client.containers.run.return_value = mock_container
    
    script = "import urllib.request; urllib.request.urlopen('http://8.8.8.8')"
    result = manager.execute_code(script)
    
    assert result["status"] == "error"
    assert result["exit_code"] == 1
    # Check that network_mode="none" was passed to Docker
    args, kwargs = manager.client.containers.run.call_args
    assert kwargs.get("network_mode") == "none"
    assert kwargs.get("mem_limit") == "512m"
    assert kwargs.get("nano_cpus") == 500000000
