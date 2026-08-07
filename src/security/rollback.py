import json
import os
import shutil
import sys
import tarfile
import time
from pathlib import Path
from typing import Dict, Any


class WorkspaceSnapshotManager:
    """
    Fast, lightweight, and secure directory checkpointing system for the AI Sandbox.
    """

    def __init__(self, workspace_dir: str | Path, snapshot_dir: str | Path, audit_log_path: str | Path):
        self.workspace_dir = Path(workspace_dir).resolve()
        self.snapshot_dir = Path(snapshot_dir).resolve()
        self.audit_log_path = Path(audit_log_path).resolve()

        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        self._prune_orphaned_snapshots()

    def _prune_orphaned_snapshots(self) -> None:
        """Removes temporary checkpoint files older than 5 minutes (300 seconds)."""
        current_time = time.time()
        for item in self.snapshot_dir.iterdir():
            if item.is_file() and item.suffix == ".tar":
                # Check modification time
                if current_time - item.stat().st_mtime > 300:
                    try:
                        item.unlink()
                    except Exception:
                        pass

    def _write_audit_log(self, entry: Dict[str, Any]) -> None:
        """Appends a snapshot or rollback event to the JSON audit log."""
        logs = []
        try:
            if self.audit_log_path.exists():
                with open(self.audit_log_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        logs = json.loads(content)
        except Exception:
            logs = []

        logs.append(entry)
        try:
            with open(self.audit_log_path, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2)
        except Exception:
            pass

    def _safe_extract(self, tar: tarfile.TarFile, path: Path, members=None, *, numeric_owner=False):
        """Safely extract tarfile preventing directory traversal attacks."""
        resolved_path = path.resolve()
        for member in tar.getmembers():
            member_path = (resolved_path / member.name).resolve()
            if not member_path.is_relative_to(resolved_path):
                raise SecurityError(f"Attempted Path Traversal in Tar File via: {member.name}")

        if sys.version_info >= (3, 12):
            tar.extractall(resolved_path, members, numeric_owner=numeric_owner, filter="data")
        else:
            tar.extractall(resolved_path, members, numeric_owner=numeric_owner)

    def create_checkpoint(self, checkpoint_name: str) -> str:
        """
        Compresses the current file tree of the workspace into a named archive.
        """
        start_time = time.time()
        tar_path = self.snapshot_dir / f"{checkpoint_name}.tar"
        
        file_count = 0
        status = "pending"
        try:
            with tarfile.open(tar_path, "w") as tar:
                for item in self.workspace_dir.iterdir():
                    tar.add(item, arcname=item.name)
            
            for root, dirs, files in os.walk(self.workspace_dir):
                file_count += len(files)
                
            status = "success"
        except Exception as e:
            status = f"error: {str(e)}"
            raise Exception(f"Failed to create checkpoint: {e}") from e
        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            self._write_audit_log({
                "event_type": "snapshot_create",
                "checkpoint_name": checkpoint_name,
                "duration_ms": duration_ms,
                "affected_files_count": file_count,
                "status": status,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })
            
        return str(tar_path)

    def rollback_to_checkpoint(self, checkpoint_name: str) -> bool:
        """
        Purges all files in the workspace and restores the exact state of the named checkpoint.
        """
        start_time = time.time()
        tar_path = self.snapshot_dir / f"{checkpoint_name}.tar"
        
        if not tar_path.exists():
            raise FileNotFoundError(f"System error: Checkpoint '{checkpoint_name}' not found.")
            
        file_count = 0
        status = "pending"
        try:
            # Purge workspace contents completely to ensure sub-second cleanup
            for item in self.workspace_dir.iterdir():
                if item.is_file() or item.is_symlink():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
                    
            # Safe extraction
            with tarfile.open(tar_path, "r") as tar:
                self._safe_extract(tar, path=self.workspace_dir)
                file_count = len([m for m in tar.getmembers() if m.isfile()])
            
            status = "success"
        except Exception as e:
            status = f"error: {str(e)}"
            raise Exception(f"System error during rollback: {e}") from e
        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            self._write_audit_log({
                "event_type": "rollback_trigger",
                "checkpoint_name": checkpoint_name,
                "duration_ms": duration_ms,
                "affected_files_count": file_count,
                "status": status,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })
            
        return True


class SecurityError(Exception):
    """Raised when a security boundary is breached."""
    pass
