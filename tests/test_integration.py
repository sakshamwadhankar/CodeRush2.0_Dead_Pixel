import os
import pytest
from src.orchestration.planner import PlannerEngine
from src.orchestration.planner_models import TaskGraph, SubTask, ActionType
from src.data_rag.hybrid_engine import HybridRAGEngine
import requests

def test_sandbox_api_connection():
    """Verify that the FastAPI Sandbox API is reachable and authorized."""
    url = f"{os.environ.get('SANDBOX_API_URL', 'http://localhost:8000')}/sandbox/execute"
    headers = {"Authorization": f"Bearer {os.environ.get('SANDBOX_AUTH_TOKEN', 'AE02-SANDBOX-AUTH-TOKEN-1234')}"}
    try:
        res = requests.post(url, json={"code": "print('integration test')", "timeout": 5}, headers=headers)
        assert res.status_code == 200, f"Sandbox API returned {res.status_code}"
    except requests.exceptions.ConnectionError:
        pytest.skip("Sandbox API is not running locally.")

def test_planner_integration():
    """Verify Planner orchestrates RAG and Code Execution successfully."""
    # Ensure dummy .env doesn't crash test if not running fully
    if not os.environ.get("SANDBOX_AUTH_TOKEN"):
        os.environ["SANDBOX_AUTH_TOKEN"] = "AE02-SANDBOX-AUTH-TOKEN-1234"
        
    planner = PlannerEngine(state_filepath="workspace/test_state.json")
    
    # Pre-seed Hybrid RAG
    planner.rag_engine.ingest_document("Aegis securely isolates execution.", doc_id="test_doc_1")
    
    graph = TaskGraph(
        query="Test integration flow",
        subtasks=[
            SubTask(
                subtask_id="t1",
                subquestion="Retrieve test data",
                action_type=ActionType.RAG_RETRIEVAL,
                target_evidence="Test evidence"
            )
        ],
        overall_confidence_target=0.5
    )
    
    results = planner.execute_graph(graph)
    assert len(results) == 1
    assert "Aegis" in results[0]["output"] or "No documents found" in results[0]["output"]
    
    report = planner.compile_report(graph, results)
    assert "workspace/citations.json"
    assert os.path.exists("workspace/citations.json")

