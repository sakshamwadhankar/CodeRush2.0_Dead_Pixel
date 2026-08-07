import json
import os
import tarfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rollback import WorkspaceSnapshotManager, SecurityError
from sandbox import SandboxManager

@pytest.fixture
def temp_dirs(tmp_path):
    workspace = tmp_path / "workspace"
    snapshots = tmp_path / "snapshots"
    audit = tmp_path / "audit_log.json"
    workspace.mkdir()
    snapshots.mkdir()
    return workspace, snapshots, audit

def test_checkpoint_creation_and_restoration(temp_dirs):
    workspace, snapshots, audit = temp_dirs
    manager = WorkspaceSnapshotManager(workspace, snapshots, audit)
    
    # Create initial files
    (workspace / "file1.txt").write_text("Hello")
    (workspace / "dir1").mkdir()
    (workspace / "dir1" / "file2.txt").write_text("World")
    
    manager.create_checkpoint("init")
    
    # Modify workspace
    (workspace / "file1.txt").write_text("Modified")
    (workspace / "dir1" / "file2.txt").unlink()
    (workspace / "file3.txt").write_text("New file")
    
    # Rollback
    manager.rollback_to_checkpoint("init")
    
    assert (workspace / "file1.txt").read_text() == "Hello"
    assert (workspace / "dir1" / "file2.txt").exists()
    assert (workspace / "dir1" / "file2.txt").read_text() == "World"
    assert not (workspace / "file3.txt").exists()

def test_sub_second_performance(temp_dirs):
    workspace, snapshots, audit = temp_dirs
    manager = WorkspaceSnapshotManager(workspace, snapshots, audit)
    
    # Create ~5MB of dummy files
    for i in range(5):
        (workspace / f"dummy_{i}.bin").write_bytes(os.urandom(1024 * 1024))
        
    start_time = time.time()
    for _ in range(3):
        manager.create_checkpoint("perf")
        (workspace / "extra.txt").write_text("extra")
        manager.rollback_to_checkpoint("perf")
        
    duration = time.time() - start_time
    assert duration < 1.0  # Should be well under 1 second

def test_path_traversal_prevention_during_extraction(temp_dirs):
    workspace, snapshots, audit = temp_dirs
    manager = WorkspaceSnapshotManager(workspace, snapshots, audit)
    
    malicious_tar = snapshots / "malicious.tar"
    
    # Create a malicious tarball manually with path traversal
    with tarfile.open(malicious_tar, "w") as tar:
        temp_file = snapshots / "temp.txt"
        temp_file.write_text("malicious content")
        tar.add(temp_file, arcname="../outside.txt")
        
    with pytest.raises(Exception) as exc_info:
        manager.rollback_to_checkpoint("malicious")
    assert "Attempted Path Traversal in Tar File" in str(exc_info.value)

def test_sandbox_integration_rollback(temp_dirs):
    workspace, snapshots, audit = temp_dirs
    sandbox_manager = SandboxManager(workspace_dir=str(workspace), audit_log_path=str(audit))
    
    sandbox_manager.client = MagicMock()
    sandbox_manager.client.ping.return_value = True
    
    # Mock container failure
    mock_container = MagicMock()
    mock_container.wait.return_value = {"StatusCode": 1} # Simulating exit code 1 (failure)
    mock_container.logs.side_effect = [b"", b"Error trace"]
    sandbox_manager.client.containers.run.return_value = mock_container
    
    # Run a script that fails
    result = sandbox_manager.execute_code("print('fail')", language="python")
    
    assert result["status"] == "error"
    assert result["rollback_status"] == "success"
    
    # Verify workspace is empty (the created script_XXXXX.py should be rolled back)
    files_in_workspace = list(workspace.iterdir())
    assert len(files_in_workspace) == 0

    # Also verify audit log has rollback event
    with open(audit, "r") as f:
        logs = json.load(f)
        
    rollback_events = [l for l in logs if l.get("event_type") == "rollback_trigger"]
    assert len(rollback_events) == 1
