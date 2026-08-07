import unittest
import tempfile
import json
from pathlib import Path

from src.orchestration.state_controller import StateController
from app import get_controller, main


class TestAppLayout(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_state_file = Path(self.temp_dir.name) / "test_app_state.json"
        self.initial_data = {
            "active_tasks": [],
            "system_logs": [],
            "user_config": {
                "max_concurrent_tasks": 5,
                "sandbox_timeout_seconds": 30,
                "rag_top_k": 5,
                "log_level": "INFO",
                "security_strict_mode": True
            },
            "security_incidents": []
        }
        with open(self.temp_state_file, "w", encoding="utf-8") as f:
            json.dump(self.initial_data, f)
            
        self.controller = StateController(state_filepath=str(self.temp_state_file))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_controller_state_binding(self):
        state = self.controller.get_state()
        self.assertEqual(state.user_config.max_concurrent_tasks, 5)
        self.assertEqual(len(state.active_tasks), 0)

    def test_app_imports_cleanly(self):
        import app
        self.assertTrue(hasattr(app, "main"))
        self.assertTrue(hasattr(app, "get_controller"))


if __name__ == "__main__":
    unittest.main()
