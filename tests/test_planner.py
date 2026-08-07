import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.planner.planner import PlannerEngine
from backend.planner.planner_models import TaskGraph, SubTask, ActionType, DraftReport
from backend.controllers.state_controller import StateController


class TestPlannerEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_state_file = Path(self.temp_dir.name) / "test_planner_state.json"
        
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

    def test_decompose_query_with_mock_gateway(self):
        sample_subtasks = [
            SubTask(subtask_id="st1", subquestion="RAG search docs", action_type=ActionType.RAG_RETRIEVAL, target_evidence="docs"),
            SubTask(subtask_id="st2", subquestion="Code execution sandbox", action_type=ActionType.CODE_EXECUTION, target_evidence="logs"),
            SubTask(subtask_id="st3", subquestion="Synthesis report", action_type=ActionType.SYNTHESIS, target_evidence="report")
        ]
        mock_graph = TaskGraph(query="Analyze cloud security baselines", subtasks=sample_subtasks)
        
        with patch.object(self.planner.gateway, "generate_structured", return_value=mock_graph):
            graph = self.planner.decompose_query("Analyze cloud security baselines")
            self.assertIsInstance(graph, TaskGraph)
            self.assertEqual(graph.query, "Analyze cloud security baselines")
            self.assertEqual(len(graph.subtasks), 3)

    def test_decompose_query_fallback(self):
        # Force Exception to verify deterministic fallback TaskGraph
        with patch.object(self.planner.gateway, "generate_structured", side_effect=RuntimeError("Endpoint offline")):
            graph = self.planner.decompose_query("Analyze cloud security baselines")
            self.assertIsInstance(graph, TaskGraph)
            self.assertEqual(graph.query, "Analyze cloud security baselines")
            self.assertTrue(len(graph.subtasks) >= 3)

    def test_execute_graph_and_state_updates(self):
        with patch.object(self.planner.gateway, "generate_structured", side_effect=RuntimeError("Offline fallback")):
            graph = self.planner.decompose_query("Test execution loop")
            results = self.planner.execute_graph(graph)
            self.assertEqual(len(results), len(graph.subtasks))
            
            # Verify state.json was updated with active tasks and logs
            state = self.planner.state_controller.get_state()
            self.assertEqual(len(state.active_tasks), len(graph.subtasks))
            self.assertTrue(len(state.system_logs) > 0)

    def test_compile_report(self):
        with patch.object(self.planner.gateway, "generate_structured", side_effect=RuntimeError("Offline fallback")):
            graph = self.planner.decompose_query("Test report compilation")
            results = self.planner.execute_graph(graph)
            report = self.planner.compile_report(graph, results)
            
            self.assertIsInstance(report, DraftReport)
            self.assertIn("Test report compilation", report.title)
            self.assertIn("Executive Summary", report.compiled_markdown)

    def test_run_pipeline_end_to_end(self):
        with patch.object(self.planner.gateway, "generate_structured", side_effect=RuntimeError("Offline fallback")):
            report = self.planner.run_pipeline("End to end autonomous pipeline test")
            self.assertIsInstance(report, DraftReport)
            self.assertIn("End to end autonomous pipeline test", report.compiled_markdown)


if __name__ == "__main__":
    unittest.main()
