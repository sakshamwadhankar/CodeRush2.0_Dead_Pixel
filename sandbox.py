import hashlib
import json
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import docker
    from docker.errors import DockerException, APIError, ImageNotFound
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    DockerException = Exception
    APIError = Exception
    ImageNotFound = Exception


class SandboxManager:
    """
    Programmatic manager for secure, resource-constrained, and air-gapped Docker sandbox execution.
    """

    def __init__(
        self,
        image_name: str = "python:3.12-slim",
        mem_limit: str = "512m",
        nano_cpus: int = 500000000,
        timeout: float = 15.0,
        workspace_dir: Optional[str] = None,
        audit_log_path: str = "audit_log.json",
        user: str = "1000:1000",
    ):
        self.image_name = image_name
        self.mem_limit = mem_limit
        self.nano_cpus = nano_cpus
        self.default_timeout = timeout
        self.audit_log_path = Path(audit_log_path).resolve()
        self.user = user

        # Set up isolated host workspace directory
        if workspace_dir:
            self.workspace_dir = Path(workspace_dir).resolve()
        else:
            self.workspace_dir = Path(tempfile.gettempdir()) / "sandbox_workspace"
        
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Docker client initialization with fail-closed check
        self.client = None
        if DOCKER_AVAILABLE:
            try:
                self.client = docker.from_env()
                self.client.ping()
            except Exception:
                self.client = None

    def is_docker_ready(self) -> bool:
        """Check if Docker client is active and daemon is responsive."""
        if not self.client:
            return False
        try:
            return self.client.ping()
        except Exception:
            return False

    def _validate_path_safety(self, file_path: Path) -> bool:
        """
        Prevent path traversal by verifying that file_path is strictly contained
        within workspace_dir.
        """
        try:
            resolved_path = file_path.resolve()
            resolved_workspace = self.workspace_dir.resolve()
            return resolved_path.is_relative_to(resolved_workspace)
        except Exception:
            return False

    def _write_audit_log(self, entry: Dict[str, Any]) -> None:
        """Appends a structured record to the chronological JSON audit log."""
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

    def execute_code(
        self,
        script_contents: str,
        language: str = "python",
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Safely executes Python or Bash script contents in an air-gapped Docker container.
        
        Returns structured dictionary:
            - status: "success" | "error" | "timeout" | "system_error"
            - exit_code: int
            - stdout: str
            - stderr: str
            - duration_seconds: float
            - error: str or None
            - audit_id: str
        """
        start_time = time.time()
        exec_timeout = timeout if timeout is not None else self.default_timeout
        audit_id = str(uuid.uuid4())
        script_hash = hashlib.sha256(script_contents.encode("utf-8")).hexdigest()
        
        ext = ".py" if language.lower() == "python" else ".sh"
        filename = f"script_{audit_id[:8]}{ext}"
        script_file_path = self.workspace_dir / filename

        # Fail closed if Docker daemon is unresponsive or unavailable
        if not self.is_docker_ready():
            duration = time.time() - start_time
            error_msg = "Docker daemon is unresponsive or unavailable. Sandbox operating in fail-closed mode."
            result = {
                "status": "system_error",
                "exit_code": -1,
                "stdout": "",
                "stderr": error_msg,
                "duration_seconds": round(duration, 4),
                "error": error_msg,
                "audit_id": audit_id,
            }
            self._write_audit_log({
                "audit_id": audit_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "language": language,
                "script_hash": script_hash,
                "status": "system_error",
                "exit_code": -1,
                "duration_seconds": round(duration, 4),
                "error": error_msg,
                "resource_limits": {
                    "mem_limit": self.mem_limit,
                    "nano_cpus": self.nano_cpus,
                    "network_mode": "none",
                }
            })
            return result

        # Verify path safety against path traversal attacks
        if not self._validate_path_safety(script_file_path):
            duration = time.time() - start_time
            error_msg = "Security violation: Path traversal detected outside workspace boundary."
            result = {
                "status": "system_error",
                "exit_code": -1,
                "stdout": "",
                "stderr": error_msg,
                "duration_seconds": round(duration, 4),
                "error": error_msg,
                "audit_id": audit_id,
            }
            self._write_audit_log({
                "audit_id": audit_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "language": language,
                "script_hash": script_hash,
                "status": "security_violation",
                "exit_code": -1,
                "duration_seconds": round(duration, 4),
                "error": error_msg,
            })
            return result

        try:
            with open(script_file_path, "w", encoding="utf-8") as f:
                f.write(script_contents)
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Failed to write script to workspace: {str(e)}"
            return {
                "status": "system_error",
                "exit_code": -1,
                "stdout": "",
                "stderr": error_msg,
                "duration_seconds": round(duration, 4),
                "error": error_msg,
                "audit_id": audit_id,
            }

        container_script_path = f"/workspace/{filename}"
        if language.lower() == "python":
            cmd = ["python3", container_script_path]
        elif language.lower() in ("bash", "sh"):
            cmd = ["bash", container_script_path]
        else:
            cmd = [language, container_script_path]

        container = None
        try:
            volumes = {
                str(self.workspace_dir): {
                    "bind": "/workspace",
                    "mode": "rw"
                }
            }

            container = self.client.containers.run(
                image=self.image_name,
                command=cmd,
                detach=True,
                network_mode="none",
                mem_limit=self.mem_limit,
                nano_cpus=self.nano_cpus,
                user=self.user,
                volumes=volumes,
                working_dir="/workspace",
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true"],
            )

            try:
                result_data = container.wait(timeout=exec_timeout)
                exit_code = result_data.get("StatusCode", -1)
                
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
                duration = time.time() - start_time
                
                status = "success" if exit_code == 0 else "error"
                error_desc = None if exit_code == 0 else f"Process exited with status code {exit_code}"

                exec_result = {
                    "status": status,
                    "exit_code": exit_code,
                    "stdout": stdout,
                    "stderr": stderr,
                    "duration_seconds": round(duration, 4),
                    "error": error_desc,
                    "audit_id": audit_id,
                }

            except Exception:
                # Execution timed out
                duration = time.time() - start_time
                stdout = ""
                stderr = ""
                try:
                    stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                    stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
                except Exception:
                    pass

                try:
                    container.kill()
                except Exception:
                    pass

                exec_result = {
                    "status": "timeout",
                    "exit_code": -1,
                    "stdout": stdout,
                    "stderr": stderr + f"\n[Execution Timed Out after {exec_timeout} seconds]",
                    "duration_seconds": round(duration, 4),
                    "error": f"Execution timed out after {exec_timeout} seconds",
                    "audit_id": audit_id,
                }

        except DockerException as de:
            duration = time.time() - start_time
            exec_result = {
                "status": "system_error",
                "exit_code": -1,
                "stdout": "",
                "stderr": str(de),
                "duration_seconds": round(duration, 4),
                "error": f"Docker execution error: {str(de)}",
                "audit_id": audit_id,
            }
        except Exception as ex:
            duration = time.time() - start_time
            exec_result = {
                "status": "system_error",
                "exit_code": -1,
                "stdout": "",
                "stderr": str(ex),
                "duration_seconds": round(duration, 4),
                "error": f"System error during sandbox execution: {str(ex)}",
                "audit_id": audit_id,
            }
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
            if script_file_path.exists():
                try:
                    script_file_path.unlink()
                except Exception:
                    pass

        self._write_audit_log({
            "audit_id": audit_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "language": language,
            "script_hash": script_hash,
            "status": exec_result["status"],
            "exit_code": exec_result["exit_code"],
            "duration_seconds": exec_result["duration_seconds"],
            "error": exec_result["error"],
            "resource_limits": {
                "mem_limit": self.mem_limit,
                "nano_cpus": self.nano_cpus,
                "network_mode": "none",
                "user": self.user,
            }
        })

        return exec_result
