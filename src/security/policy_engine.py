import os
import yaml
import re
from typing import Tuple, Dict, Any
from pathlib import Path
from src.orchestration.state_controller import StateController
from src.orchestration.state_models import LogLevel

class PolicyEngine:
    """
    Step B4: Static Policy Engine for self-evolution permission escalation detection.
    Scans YAML configurations to prevent unauthorized access or behavioral drift.
    """
    def __init__(self, state_controller: StateController = None):
        self.state_controller = state_controller or StateController()
        
        self.denied_keywords = [
            r"override_approval\s*:\s*true",
            r"os\.environ",
            r"OPENAI_API_KEY",
            r"ANTHROPIC_API_KEY",
            r"click\(",  # simulated clicks
            r"pyautogui",
            r"system\(",
            r"subprocess"
        ]

    def _static_analysis(self, yaml_content: str) -> Tuple[bool, str]:
        yaml_lower = yaml_content.lower()
        
        # 1. Deny access outside /workspace/
        # Check for paths starting with / or C: that are not /workspace
        path_pattern = r"['\"](/[^w][^o][^r].*?|/[a-vx-z].*?|[a-z]:\\.*?)['\"]"
        matches = re.findall(path_pattern, yaml_lower)
        for match in matches:
            if not match.startswith("/workspace"):
                return False, f"Directory access violation: Attempted access to {match}"

        # 2. Deny specific malicious keywords/patterns
        for pattern in self.denied_keywords:
            if re.search(pattern, yaml_lower):
                return False, f"Malicious pattern detected: {pattern}"

        return True, "Passed static analysis."

    def validate_strategy(self, yaml_content: str, filename: str = "strategy_v2.yaml") -> Tuple[bool, str]:
        """
        Validates a proposed strategy YAML against the security policy.
        """
        # 1. Syntax Verification
        try:
            parsed = yaml.safe_load(yaml_content)
            if not isinstance(parsed, dict):
                raise ValueError("YAML must parse to a dictionary.")
        except Exception as e:
            msg = f"YAML Syntax Error: {str(e)}"
            self._log_and_quarantine(msg, yaml_content, filename)
            return False, msg

        # 2. Static Semantic Checks
        passed, reason = self._static_analysis(yaml_content)
        if not passed:
            self._log_and_quarantine(reason, yaml_content, filename)
            return False, reason

        return True, "Strategy is compliant."

    def _log_and_quarantine(self, reason: str, yaml_content: str, filename: str):
        """Halts execution, logs critical event, and quarantines the file."""
        self.state_controller.log_system_event(
            level=LogLevel.CRITICAL,
            component="PolicyEngine",
            message=f"Self-evolution strategy blocked: {reason}",
            metadata={"filename": filename}
        )
        
        # Isolate the proposed YAML file in /workspace/quarantine
        try:
            quarantine_dir = Path("workspace/quarantine")
            quarantine_dir.mkdir(parents=True, exist_ok=True)
            quarantine_path = quarantine_dir / f"BLOCKED_{filename}"
            with open(quarantine_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Q-Learning Safety Guard
    # ------------------------------------------------------------------
    # Actions that require elevated privileges (sandbox code execution
    # or browser scraping) must not accumulate excessive Q-values without
    # explicit operator consent.
    _UNSAFE_ACTIONS = {2, 3}       # CODE_EXEC, WEB_SCRAPE
    _Q_VALUE_CEILING = 8.0         # Maximum unsupervised Q-value

    def validate_q_table_update(
        self,
        state: tuple,
        action: int,
        q_value: float,
    ) -> Tuple[bool, str]:
        """
        Validates a proposed Q-table update before it is persisted.

        If the Q-value for a privileged action (CODE_EXEC or WEB_SCRAPE)
        exceeds the safety ceiling, the update is blocked and a CRITICAL
        security event is logged.

        Args:
            state:   The discrete state tuple.
            action:  Action ID (0-3).
            q_value: The proposed new Q-value after Bellman update.

        Returns:
            Tuple[bool, str]: (is_allowed, reason)
        """
        if action in self._UNSAFE_ACTIONS and q_value > self._Q_VALUE_CEILING:
            reason = (
                f"Q-table safety violation: Action {action} in state {state} "
                f"received Q-value {q_value:.4f} which exceeds the safety "
                f"ceiling of {self._Q_VALUE_CEILING}. Operator consent required."
            )
            self.state_controller.log_system_event(
                level=LogLevel.CRITICAL,
                component="PolicyEngine.QLearningGuard",
                message=reason,
                metadata={
                    "state": str(state),
                    "action": action,
                    "q_value": q_value,
                    "ceiling": self._Q_VALUE_CEILING,
                },
            )
            return False, reason

        return True, "Q-table update permitted."
