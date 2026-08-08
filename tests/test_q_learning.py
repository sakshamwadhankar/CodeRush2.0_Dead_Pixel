"""
Pytest assertions for the Q-Learning Reinforcement Learning agent.

Tests:
    1. StateEncoder correctly maps raw queries to discrete state tuples.
    2. Bellman update produces mathematically correct Q-values.
    3. Q-table JSON serialization and deserialization preserves data.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.orchestration.q_optimizer import (
    StateEncoder,
    QLearningAgent,
    ACTION_SPACE,
    NUM_ACTIONS,
)


# -------------------------------------------------------------------
# Test 1: State Encoding
# -------------------------------------------------------------------

class TestStateEncoder:
    """Verify that the heuristic classifier maps queries to the correct
    discrete state tuples."""

    def test_complex_code_query(self):
        """A multi-step coding query should be classified as
        (Complex=1, Code/Math=0, LocalDocs=0)."""
        query = "Write a Python script to calculate fibonacci using a recursive algorithm"
        state = StateEncoder.encode(query)
        assert state[0] == 1, f"Expected complexity=1 (Complex), got {state[0]}"
        assert state[1] == 0, f"Expected domain=0 (Code/Math), got {state[1]}"
        assert state[2] == 0, f"Expected source=0 (Local docs), got {state[2]}"

    def test_simple_fact_query(self):
        """A short factual question should be classified as
        (Simple=0, Fact/Literature=1, LocalDocs=0)."""
        query = "What is the history of the Roman Empire?"
        state = StateEncoder.encode(query)
        assert state[0] == 0, f"Expected complexity=0 (Simple), got {state[0]}"
        assert state[1] == 1, f"Expected domain=1 (Fact), got {state[1]}"
        assert state[2] == 0, f"Expected source=0 (Local docs), got {state[2]}"

    def test_web_heavy_query(self):
        """A query with many web-related keywords should select
        target_source_type=1 (Dynamic Web)."""
        query = "Find the latest trending news about live updates on the website today"
        state = StateEncoder.encode(query)
        assert state[2] == 1, f"Expected source=1 (Web), got {state[2]}"

    def test_csv_query(self):
        """A query referencing structured data should select
        target_source_type=2 (CSV)."""
        query = "Analyze the CSV dataset and show dataframe column statistics"
        state = StateEncoder.encode(query)
        assert state[2] == 2, f"Expected source=2 (CSV), got {state[2]}"

    def test_returns_tuple_of_ints(self):
        """The encoder must always return a 3-tuple of integers."""
        state = StateEncoder.encode("any random query")
        assert isinstance(state, tuple)
        assert len(state) == 3
        assert all(isinstance(v, int) for v in state)


# -------------------------------------------------------------------
# Test 2: Bellman Update
# -------------------------------------------------------------------

class TestBellmanUpdate:
    """Verify that the Q-value update follows the Bellman equation:
    Q_new = Q_old + α * (R + γ * max(Q') - Q_old)"""

    def _make_agent(self, tmp_path: Path) -> QLearningAgent:
        """Create a fresh agent with a temp q_table path."""
        return QLearningAgent(
            q_table_path=str(tmp_path / "q_table.json"),
            learning_rate=0.1,
            discount_factor=0.95,
            epsilon=0.0,   # greedy for deterministic tests
        )

    def test_initial_update(self, tmp_path):
        """From an all-zero Q-table, verify the first update."""
        agent = self._make_agent(tmp_path)
        state = (0, 0, 0)
        action = 0
        reward = 10.0
        next_state = (0, 1, 0)

        # Q_old = 0.0, max(Q') = 0.0
        # Q_new = 0 + 0.1 * (10.0 + 0.95*0.0 - 0.0) = 1.0
        new_q = agent.update(state, action, reward, next_state)
        assert abs(new_q - 1.0) < 1e-6, f"Expected Q=1.0, got {new_q}"

    def test_successive_updates(self, tmp_path):
        """Two successive updates should compound correctly."""
        agent = self._make_agent(tmp_path)
        state = (1, 0, 0)
        action = 1
        next_state = (1, 0, 0)

        # First update: Q = 0 + 0.1*(5 + 0.95*0 - 0) = 0.5
        q1 = agent.update(state, action, 5.0, next_state)
        assert abs(q1 - 0.5) < 1e-6

        # Second update: Q = 0.5 + 0.1*(5 + 0.95*0.5 - 0.5)
        #              = 0.5 + 0.1*(5 + 0.475 - 0.5)
        #              = 0.5 + 0.1*(4.975) = 0.5 + 0.4975 = 0.9975
        q2 = agent.update(state, action, 5.0, next_state)
        expected = 0.5 + 0.1 * (5.0 + 0.95 * 0.5 - 0.5)
        assert abs(q2 - expected) < 1e-4, f"Expected {expected:.6f}, got {q2}"

    def test_negative_reward(self, tmp_path):
        """Security incidents produce negative rewards; Q should decrease."""
        agent = self._make_agent(tmp_path)
        state = (0, 2, 0)
        action = 2  # CODE_EXEC
        next_state = (0, 2, 0)

        reward = QLearningAgent.compute_reward(
            task_success=0.0,
            citation_precision=0.0,
            duration_seconds=1.0,
            security_incident=True,
        )
        assert reward < 0, "Reward should be negative after a security incident"

        new_q = agent.update(state, action, reward, next_state)
        assert new_q < 0, f"Q-value should be negative, got {new_q}"


# -------------------------------------------------------------------
# Test 3: Serialization / Deserialization
# -------------------------------------------------------------------

class TestQTablePersistence:
    """Verify that saving and reloading the Q-table preserves all data."""

    def test_round_trip(self, tmp_path):
        """Save Q-table, create new agent, verify contents match."""
        path = str(tmp_path / "q_table.json")
        agent1 = QLearningAgent(q_table_path=path, learning_rate=0.2, epsilon=0.05)

        # Perform some updates to populate the table
        agent1.update((0, 0, 0), 0, 10.0, (0, 1, 0))
        agent1.update((1, 1, 1), 3, -5.0, (0, 0, 0))
        agent1.update((0, 2, 2), 1,  3.0, (1, 1, 1))
        agent1.save_q_table()

        # Reload into a new agent instance
        agent2 = QLearningAgent(q_table_path=path)
        assert agent2.q_table == agent1.q_table, "Q-tables should match after round-trip"

    def test_hyperparameters_persisted(self, tmp_path):
        """Hyperparameters should be stored alongside the Q-table."""
        path = str(tmp_path / "q_table.json")
        agent = QLearningAgent(
            q_table_path=path,
            learning_rate=0.42,
            discount_factor=0.88,
            epsilon=0.15,
        )
        agent.save_q_table()

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        hp = data["hyperparameters"]
        assert hp["learning_rate"] == 0.42
        assert hp["discount_factor"] == 0.88
        assert hp["epsilon"] == 0.15

    def test_empty_table_loads_cleanly(self, tmp_path):
        """A fresh agent with no file on disk should start with an empty table."""
        path = str(tmp_path / "nonexistent" / "q_table.json")
        agent = QLearningAgent(q_table_path=path)
        assert agent.q_table == {}


# -------------------------------------------------------------------
# Test 4: Reward Function
# -------------------------------------------------------------------

class TestRewardFunction:
    """Verify the reward formula arithmetic."""

    def test_perfect_run(self):
        r = QLearningAgent.compute_reward(1.0, 1.0, 0.5, False)
        # (1*10) + (1*5) - (0.5*0.1) = 14.95
        assert abs(r - 14.95) < 1e-4

    def test_security_incident_penalty(self):
        r = QLearningAgent.compute_reward(1.0, 1.0, 0.5, True)
        # 14.95 - 50 = -35.05
        assert abs(r - (-35.05)) < 1e-4

    def test_zero_success(self):
        r = QLearningAgent.compute_reward(0.0, 0.0, 10.0, False)
        # 0 + 0 - 1.0 = -1.0
        assert abs(r - (-1.0)) < 1e-4
