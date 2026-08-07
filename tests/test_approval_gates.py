import json
import tempfile
import unittest
from pathlib import Path

from backend.planner.planner import PlannerEngine
from backend.planner.planner_models import TaskGraph, SubTask, ActionType
from backend.schema.state_models import TaskStatus, SeverityLevel


class TestApprovalGates(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_state_file = Path(self.temp_dir.name) / "test_approval_state.json"
        
        self.initial_data = {
            "active_tasks": [],
            "system_logs": [],
            "user_config": {
                "max_concurrent_tasks": 5,
                "sandbox_timeout_seconds": 30,
                "rag_top_k": 5,
                "log_level": "INFO",
                "security_strict_mode": True,
                "model_provider": "ollama",
                "ollama_model": "gemma4:latest",
                "gemini_model": "gemini-1.5-flash",
                "ollama_base_url": "http://localhost:11434"
            },
            "security_incidents": []
        }
        with open(self.temp_state_file, "w", encoding="utf-8") as f:
            json.dump(self.initial_data, f)
            
        self.planner = PlannerEngine(state_filepath=str(self.temp_state_file))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sensitivity_detection(self):
        sub_rag = SubTask(subtask_id="st1", subquestion="Retrieve docs", action_type=ActionType.RAG_RETRIEVAL, target_evidence="docs")
        sub_code = SubTask(subtask_id="st2", subquestion="Run code", action_type=ActionType.CODE_EXECUTION, target_evidence="stdout")
        sub_sensitive = SubTask(subtask_id="st3", subquestion="Publish report to external account", action_type=ActionType.SYNTHESIS, target_evidence="pub")
        
        self.assertFalse(self.planner._is_sensitive_action(sub_rag))
        self.assertTrue(self.planner._is_sensitive_action(sub_code))
        self.assertTrue(self.planner._is_sensitive_action(sub_sensitive))

    def test_approval_gate_pause(self):
        subtasks = [
            SubTask(subtask_id="st1", subquestion="Safe subtask", action_type=ActionType.RAG_RETRIEVAL, target_evidence="docs"),
            SubTask(subtask_id="st2", subquestion="Sensitive subtask", action_type=ActionType.CODE_EXECUTION, target_evidence="logs")
        ]
        graph = TaskGraph(query="Test approval pause", subtasks=subtasks)
        
        # Execute without approval -> should execute st1 and pause at st2
        results = self.planner.execute_graph(graph, approved_subtasks=[])
        self.assertEqual(len(results), 1)  # Only st1 completed
        self.assertEqual(results[0]["subtask_id"], "st1")
        
        # Verify state.json recorded PENDING_APPROVAL task status
        state = self.planner.state_controller.get_state()
        statuses = [t.status for t in state.active_tasks]
        self.assertIn(TaskStatus.PENDING_APPROVAL, statuses)

    def test_approval_gate_granted(self):
        subtasks = [
            SubTask(subtask_id="st1", subquestion="Safe subtask", action_type=ActionType.RAG_RETRIEVAL, target_evidence="docs"),
            SubTask(subtask_id="st2", subquestion="Sensitive subtask", action_type=ActionType.CODE_EXECUTION, target_evidence="logs")
        ]
        graph = TaskGraph(query="Test approval grant", subtasks=subtasks)
        
        # Execute with st2 approved -> both subtasks should complete
        results = self.planner.execute_graph(graph, approved_subtasks=["st2"])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[1]["subtask_id"], "st2")

    def test_approval_gate_rejected(self):
        subtasks = [
            SubTask(subtask_id="st1", subquestion="Safe subtask", action_type=ActionType.RAG_RETRIEVAL, target_evidence="docs"),
            SubTask(subtask_id="st2", subquestion="Sensitive subtask", action_type=ActionType.CODE_EXECUTION, target_evidence="logs")
        ]
        graph = TaskGraph(query="Test approval rejection", subtasks=subtasks)
        
        # Execute with st2 rejected -> st1 completes, st2 rejected/cancelled
        results = self.planner.execute_graph(graph, approved_subtasks=[], rejected_subtasks=["st2"])
        self.assertEqual(len(results), 1)
        
        state = self.planner.state_controller.get_state()
        statuses = [t.status for t in state.active_tasks]
        self.assertIn(TaskStatus.CANCELLED, statuses)

    def test_security_incident_halt(self):
        # Trigger an active security incident in state.json
        self.planner.state_controller.trigger_security_alert(
            alert_type="NeMo Guardrails Prompt Injection",
            severity=SeverityLevel.HIGH,
            source_component="NeMoGuardrailsFilter",
            description="Prompt injection attempt detected"
        )
        
        subtasks = [SubTask(subtask_id="st1", subquestion="Safe subtask", action_type=ActionType.RAG_RETRIEVAL, target_evidence="docs")]
        graph = TaskGraph(query="Test security halt", subtasks=subtasks)
        
        results = self.planner.execute_graph(graph)
        self.assertEqual(len(results), 0)  # Execution halted completely
        
        state = self.planner.state_controller.get_state()
        statuses = [t.status for t in state.active_tasks]
        self.assertIn(TaskStatus.FAILED, statuses)


if __name__ == "__main__":
    unittest.main()
