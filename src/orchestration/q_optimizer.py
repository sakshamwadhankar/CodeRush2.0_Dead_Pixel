"""
Q-Learning Reinforcement Learning Optimizer for Aegis Research OS.
Implements a local, offline Q-Learning agent that dynamically selects optimal
RAG retrieval weights and tool execution pathways based on query characteristics.

Mathematical Foundation:
    Bellman Update: Q(s,a) <- Q(s,a) + α * [R + γ * max_a'(Q(s',a')) - Q(s,a)]
    Reward: R = (success * 10) + (precision * 5) - (duration * 0.1) - (incident * 50)
"""

import json
import os
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, List


# ---------------------------------------------------------------------------
# Action Configuration
# ---------------------------------------------------------------------------

@dataclass
class ActionConfig:
    """Maps a discrete action ID to operational parameters."""
    action_id: int
    label: str
    dense_weight: float
    sparse_weight: float
    tool: str   # "RAG" | "Sandbox" | "Browser"


# Canonical action space (frozen after definition)
ACTION_SPACE: List[ActionConfig] = [
    ActionConfig(action_id=0, label="DENSE_HEAVY",  dense_weight=0.8, sparse_weight=0.2, tool="RAG"),
    ActionConfig(action_id=1, label="SPARSE_HEAVY", dense_weight=0.2, sparse_weight=0.8, tool="RAG"),
    ActionConfig(action_id=2, label="CODE_EXEC",    dense_weight=0.5, sparse_weight=0.5, tool="Sandbox"),
    ActionConfig(action_id=3, label="WEB_SCRAPE",   dense_weight=0.5, sparse_weight=0.5, tool="Browser"),
]

NUM_ACTIONS = len(ACTION_SPACE)


# ---------------------------------------------------------------------------
# State Encoder
# ---------------------------------------------------------------------------

class StateEncoder:
    """
    Encodes a raw query string into a discrete state tuple used as the
    Q-table key.

    State = (query_complexity, domain_class, target_source_type)

    Dimensions:
        query_complexity:   0 = Simple,  1 = Complex / multi-step
        domain_class:       0 = Code/Math-heavy,  1 = Fact/Literature-heavy,  2 = Mixed
        target_source_type: 0 = Local documents,  1 = Dynamic Web,  2 = Structured CSV
    """

    # Keyword pools for heuristic classification
    _COMPLEX_KEYWORDS = {
        "compare", "analyze", "evaluate", "multi-step", "synthesize",
        "contrast", "investigate", "assess", "comprehensive", "detailed",
        "calculate", "derive", "prove", "implement", "algorithm",
        "fibonacci", "recursive", "optimize", "benchmark", "statistical",
    }
    _CODE_KEYWORDS = {
        "python", "code", "script", "function", "class", "algorithm",
        "implement", "debug", "compile", "execute", "fibonacci", "loop",
        "variable", "programming", "api", "sql", "regex", "binary",
        "math", "calculate", "equation", "formula", "derivative",
        "integral", "matrix", "vector", "probability", "statistics",
    }
    _FACT_KEYWORDS = {
        "history", "explain", "describe", "what is", "who", "when",
        "define", "overview", "summary", "literature", "review",
        "report", "document", "research", "study", "paper", "article",
        "theory", "concept", "principle", "law",
    }
    _WEB_KEYWORDS = {
        "latest", "recent", "news", "current", "trending", "today",
        "website", "url", "online", "blog", "forum", "social media",
        "download", "live", "real-time", "update",
    }
    _CSV_KEYWORDS = {
        "csv", "dataset", "table", "spreadsheet", "column", "row",
        "data file", "excel", "structured data", "tabular", "dataframe",
        "pandas", "records",
    }

    @classmethod
    def encode(cls, query: str) -> Tuple[int, int, int]:
        """
        Classify a query string into a (complexity, domain, source) tuple.

        Returns:
            Tuple[int, int, int]: The discrete state representation.
        """
        tokens = set(query.lower().split())
        query_lower = query.lower()

        # --- Query Complexity ---
        complex_hits = sum(1 for kw in cls._COMPLEX_KEYWORDS if kw in query_lower)
        word_count = len(query.split())
        query_complexity = 1 if (complex_hits >= 2 or word_count > 15) else 0

        # --- Domain Class ---
        code_hits = sum(1 for kw in cls._CODE_KEYWORDS if kw in query_lower)
        fact_hits = sum(1 for kw in cls._FACT_KEYWORDS if kw in query_lower)

        if code_hits > fact_hits:
            domain_class = 0      # Code/Math-heavy
        elif fact_hits > code_hits:
            domain_class = 1      # Fact/Literature-heavy
        else:
            domain_class = 2      # Mixed

        # --- Target Source Type ---
        web_hits = sum(1 for kw in cls._WEB_KEYWORDS if kw in query_lower)
        csv_hits = sum(1 for kw in cls._CSV_KEYWORDS if kw in query_lower)

        if csv_hits >= 1:
            target_source_type = 2   # Structured CSV
        elif web_hits >= 2:
            target_source_type = 1   # Dynamic Web
        else:
            target_source_type = 0   # Local documents

        return (query_complexity, domain_class, target_source_type)


# ---------------------------------------------------------------------------
# Q-Learning Agent
# ---------------------------------------------------------------------------

class QLearningAgent:
    """
    Tabular Q-Learning agent operating over the Aegis Research OS action space.

    Hyperparameters:
        learning_rate (α):     Step size for Q-value updates.          Default 0.1
        discount_factor (γ):   Weight for future rewards.              Default 0.95
        epsilon (ε):           Exploration probability.                Default 0.1

    Persistence:
        The Q-table is serialized to / deserialized from a JSON file so that
        learned policies survive across sessions.
    """

    def __init__(
        self,
        q_table_path: str = "workspace/q_table.json",
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        epsilon: float = 0.1,
    ):
        self.q_table_path = Path(q_table_path)
        self.learning_rate = learning_rate       # α
        self.discount_factor = discount_factor   # γ
        self.epsilon = epsilon                   # ε
        self.q_table: Dict[str, List[float]] = {}
        self.load_q_table()

    # ---- Serialization ----

    def _state_key(self, state: Tuple[int, int, int]) -> str:
        """Convert a state tuple to a hashable JSON-safe string key."""
        return f"{state[0]}_{state[1]}_{state[2]}"

    def _ensure_state(self, state: Tuple[int, int, int]) -> None:
        """Lazily initialise Q-values for an unseen state to zeros."""
        key = self._state_key(state)
        if key not in self.q_table:
            self.q_table[key] = [0.0] * NUM_ACTIONS

    def load_q_table(self) -> None:
        """Load a previously persisted Q-table from disk, if it exists."""
        if self.q_table_path.exists():
            try:
                with open(self.q_table_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.q_table = data.get("q_table", {})
            except (json.JSONDecodeError, Exception):
                self.q_table = {}
        else:
            self.q_table = {}

    def save_q_table(self) -> None:
        """Persist the current Q-table and hyperparameters to disk."""
        self.q_table_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "hyperparameters": {
                "learning_rate": self.learning_rate,
                "discount_factor": self.discount_factor,
                "epsilon": self.epsilon,
            },
            "q_table": self.q_table,
        }
        with open(self.q_table_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    # ---- Core RL Methods ----

    def select_action(self, state: Tuple[int, int, int]) -> int:
        """
        Epsilon-greedy action selection.

        With probability ε, choose a random action (exploration).
        Otherwise, choose the action with the highest Q-value (exploitation).

        Args:
            state: The current discrete state tuple.

        Returns:
            int: Selected action ID (0–3).
        """
        self._ensure_state(state)
        if random.random() < self.epsilon:
            return random.randint(0, NUM_ACTIONS - 1)
        key = self._state_key(state)
        q_values = self.q_table[key]
        max_q = max(q_values)
        # Break ties randomly
        best_actions = [a for a, q in enumerate(q_values) if q == max_q]
        return random.choice(best_actions)

    @staticmethod
    def compute_reward(
        task_success: float,
        citation_precision: float,
        duration_seconds: float,
        security_incident: bool = False,
    ) -> float:
        """
        Computes the scalar reward signal.

        R = (task_success * 10) + (citation_precision * 5)
            - (duration_seconds * 0.1) - (security_incident * 50)

        Args:
            task_success:       Float in [0, 1]. 1.0 = full success.
            citation_precision: Float in [0, 1]. 1.0 = all citations verified.
            duration_seconds:   Wall-clock seconds elapsed.
            security_incident:  True if a security violation was raised.

        Returns:
            float: The computed reward value.
        """
        reward = (task_success * 10.0) + (citation_precision * 5.0)
        reward -= duration_seconds * 0.1
        if security_incident:
            reward -= 50.0
        return round(reward, 6)

    def update(
        self,
        state: Tuple[int, int, int],
        action: int,
        reward: float,
        next_state: Tuple[int, int, int],
    ) -> float:
        """
        Applies the Bellman equation update to the Q-table.

        Q(s, a) ← Q(s, a) + α * [R + γ * max_a'(Q(s', a')) - Q(s, a)]

        Args:
            state:      Current state tuple.
            action:     Action taken (0–3).
            reward:     Observed reward.
            next_state: State observed after the action.

        Returns:
            float: The new Q-value after the update.
        """
        self._ensure_state(state)
        self._ensure_state(next_state)

        key = self._state_key(state)
        next_key = self._state_key(next_state)

        old_q = self.q_table[key][action]
        max_next_q = max(self.q_table[next_key])

        new_q = old_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - old_q
        )
        self.q_table[key][action] = round(new_q, 6)
        return self.q_table[key][action]

    # ---- Convenience ----

    def get_best_action(self, state: Tuple[int, int, int]) -> int:
        """Return the greedy (exploitation-only) action for a given state."""
        self._ensure_state(state)
        key = self._state_key(state)
        q_values = self.q_table[key]
        return int(q_values.index(max(q_values)))

    def get_q_values(self, state: Tuple[int, int, int]) -> List[float]:
        """Return the full Q-value vector for a given state."""
        self._ensure_state(state)
        return list(self.q_table[self._state_key(state)])

    def get_full_table_display(self) -> List[Dict[str, Any]]:
        """
        Return the entire Q-table as a list of dicts suitable for display
        in the Streamlit UI.
        """
        rows = []
        for state_key, q_values in sorted(self.q_table.items()):
            parts = state_key.split("_")
            best_action = int(q_values.index(max(q_values)))
            rows.append({
                "State": f"({', '.join(parts)})",
                "DENSE_HEAVY (Q)": f"{q_values[0]:.4f}",
                "SPARSE_HEAVY (Q)": f"{q_values[1]:.4f}",
                "CODE_EXEC (Q)": f"{q_values[2]:.4f}",
                "WEB_SCRAPE (Q)": f"{q_values[3]:.4f}",
                "Best Action": ACTION_SPACE[best_action].label,
            })
        return rows
