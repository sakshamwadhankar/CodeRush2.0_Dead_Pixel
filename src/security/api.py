import asyncio
import json
import traceback
from pathlib import Path
from typing import Dict, Any, List

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from sandbox import SandboxManager
from rollback import WorkspaceSnapshotManager
from browser_controller import SecureBrowserController
from quarantine_parser import QuarantineService

# Setup App
app = FastAPI(title="Sandbox REST API", version="1.0.0")

# Security Token (Hardcoded for B5 prototype phase)
AUTH_TOKEN = "AE02-SANDBOX-AUTH-TOKEN-1234"
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Enforces static Bearer Token authentication on all routes."""
    if credentials.credentials != AUTH_TOKEN:
        # Fail closed on bad token
        write_api_error_log("401 Unauthorized: Invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# Setup Local Paths
WORKSPACE_DIR = Path("./workspace").resolve()
AUDIT_LOG = Path("./audit_log.json").resolve()

WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
if not AUDIT_LOG.exists():
    AUDIT_LOG.write_text("[]", encoding="utf-8")

# Initialize Developer B Services
sandbox_manager = SandboxManager(workspace_dir=str(WORKSPACE_DIR), audit_log_path=str(AUDIT_LOG))
snapshot_manager = WorkspaceSnapshotManager(workspace_dir=str(WORKSPACE_DIR), snapshot_dir=str(WORKSPACE_DIR.parent / "sandbox_snapshots"), audit_log_path=str(AUDIT_LOG))
browser_controller = SecureBrowserController(audit_log_path=str(AUDIT_LOG))
quarantine_service = QuarantineService(workspace_dir=str(WORKSPACE_DIR), audit_log_path=str(AUDIT_LOG))

def write_api_error_log(error_msg: str):
    """Centralized error logger for API-layer failures."""
    logs = []
    try:
        if AUDIT_LOG.exists():
            with open(AUDIT_LOG, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    logs = json.loads(content)
    except Exception:
        pass
    
    logs.append({
        "event_type": "api_error",
        "error": error_msg,
        "timestamp": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime())
    })
    
    try:
        with open(AUDIT_LOG, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2)
    except Exception:
        pass

# Pydantic Models for Input Validation
class ExecuteRequest(BaseModel):
    code: str
    language: str = "python"

class CheckpointRequest(BaseModel):
    checkpoint_name: str

class BrowserRequest(BaseModel):
    url: str

# Endpoints
@app.post("/sandbox/execute", dependencies=[Depends(verify_token)])
async def execute_code(request: ExecuteRequest):
    try:
        # Offload Docker CPU execution to background thread
        result = await asyncio.to_thread(sandbox_manager.execute_code, request.code, request.language)
        return result
    except Exception as e:
        error_str = f"Execution Error: {str(e)}\n{traceback.format_exc()}"
        write_api_error_log(error_str)
        raise HTTPException(status_code=500, detail="Internal Execution Error")

@app.post("/sandbox/checkpoint", dependencies=[Depends(verify_token)])
async def create_checkpoint(request: CheckpointRequest):
    try:
        tar_path = await asyncio.to_thread(snapshot_manager.create_checkpoint, request.checkpoint_name)
        return {"status": "success", "checkpoint_path": tar_path}
    except Exception as e:
        write_api_error_log(f"Checkpoint Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sandbox/rollback", dependencies=[Depends(verify_token)])
async def rollback_checkpoint(request: CheckpointRequest):
    try:
        await asyncio.to_thread(snapshot_manager.rollback_to_checkpoint, request.checkpoint_name)
        return {"status": "success", "message": f"Rolled back to {request.checkpoint_name}"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Checkpoint not found")
    except Exception as e:
        write_api_error_log(f"Rollback Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/browser/scrape", dependencies=[Depends(verify_token)])
async def scrape_url(request: BrowserRequest):
    try:
        result = await asyncio.to_thread(browser_controller.browse_page, request.url)
        # Fail closed on browser navigation errors
        if result["status"] in ("error", "system_error"):
            raise HTTPException(status_code=400, detail=result["metadata"]["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        write_api_error_log(f"Browser Scrape Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Browser Scrape Error")

@app.get("/quarantine/status", dependencies=[Depends(verify_token)])
async def quarantine_status():
    try:
        if not AUDIT_LOG.exists():
            return {"events": []}
            
        with open(AUDIT_LOG, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {"events": []}
            logs = json.loads(content)
            
        # Filter quarantine events dynamically
        q_events = [l for l in logs if l.get("event_type") == "quarantine_ingestion"]
        return {"events": q_events}
    except Exception as e:
        write_api_error_log(f"Quarantine Status Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to parse audit log")

if __name__ == "__main__":
    # Must run completely offline without hot-reload for production stability
    uvicorn.run(app, host="127.0.0.1", port=8000)
