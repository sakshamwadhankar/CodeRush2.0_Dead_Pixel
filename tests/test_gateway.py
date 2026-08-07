import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from pydantic import BaseModel, Field

from src.orchestration.gateway import ModelGateway, ModelGatewayError
from src.orchestration.state_controller import StateController


class SamplePlan(BaseModel):
    title: str
    steps: list[str] = Field(default_factory=list)
    estimated_hours: int = Field(ge=1)


class TestModelGateway(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_state_file = Path(self.temp_dir.name) / "test_gateway_state.json"

        # State data setup
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

        self.gateway = ModelGateway(state_filepath=str(self.temp_state_file))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_json_extraction_raw(self):
        raw = '{"title": "Test Plan", "steps": ["step1", "step2"], "estimated_hours": 3}'
        extracted = self.gateway._extract_json(raw)
        self.assertEqual(extracted["title"], "Test Plan")
        self.assertEqual(extracted["estimated_hours"], 3)

    def test_json_extraction_markdown_codeblock(self):
        raw = """
        Here is the generated JSON plan:
        ```json
        {
            "title": "Markdown Plan",
            "steps": ["stepA"],
            "estimated_hours": 5
        }
        ```
        Hope this helps!
        """
        extracted = self.gateway._extract_json(raw)
        self.assertEqual(extracted["title"], "Markdown Plan")
        self.assertEqual(extracted["estimated_hours"], 5)

    def test_json_extraction_invalid(self):
        raw = "This is plain text with no json structure at all."
        with self.assertRaises(ValueError):
            self.gateway._extract_json(raw)

    def test_system_prompt_builder(self):
        system_prompt = self.gateway._build_system_prompt(SamplePlan, user_instructions="Focus on security")
        self.assertIn("REQUIRED JSON SCHEMA:", system_prompt)
        self.assertIn("SamplePlan", system_prompt)
        self.assertIn("Focus on security", system_prompt)

    @patch.object(ModelGateway, "_call_ollama")
    def test_generate_structured_success(self, mock_ollama):
        mock_ollama.return_value = '{"title": "Autonomous Audit", "steps": ["Scan", "Verify"], "estimated_hours": 4}'
        res = self.gateway.generate_structured("Create audit plan", SamplePlan)
        self.assertIsInstance(res, SamplePlan)
        self.assertEqual(res.title, "Autonomous Audit")
        self.assertEqual(res.estimated_hours, 4)
        mock_ollama.assert_called_once()

    @patch.object(ModelGateway, "_call_ollama")
    def test_retry_mechanism_on_malformed_json(self, mock_ollama):
        # First call returns malformed string, second call returns valid JSON
        mock_ollama.side_effect = [
            "Not JSON yet...",
            '{"title": "Fixed Plan", "steps": ["Retry step"], "estimated_hours": 2}'
        ]
        res = self.gateway.generate_structured("Create plan with retry", SamplePlan, max_retries=3)
        self.assertEqual(res.title, "Fixed Plan")
        self.assertEqual(mock_ollama.call_count, 2)

    @patch.object(ModelGateway, "_call_ollama")
    def test_retry_exhausted_raises_error(self, mock_ollama):
        mock_ollama.return_value = "Broken output continuous"
        with self.assertRaises(ModelGatewayError):
            self.gateway.generate_structured("Failed prompt", SamplePlan, max_retries=2, fallback_on_failure=False)


if __name__ == "__main__":
    unittest.main()
