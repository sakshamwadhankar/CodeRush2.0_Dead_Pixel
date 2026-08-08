# 🤖 Q-Learning Self-Evolution Engine

This document explains the mathematical Reinforcement Learning (RL) core of the **Aegis Research OS**.

## 1. What is Q-Learning in this Project?
Initially, the Aegis Research OS relied on static YAML configurations (`strategy_v1.yaml`) to decide how to execute research tasks. To achieve true autonomy (Step C5 of the AE-02 requirements), we replaced this static logic with a **Q-Learning Reinforcement Learning Agent**.

Q-Learning allows the system to autonomously learn which **actions** (e.g., retrieving documents vs. writing python code vs. scraping the web) yield the highest success rates for specific **states** (types of user queries). Over time, the agent optimizes its execution strategy by trial and error, completely eliminating the need for human-written heuristic rules.

## 2. How the Model Works

The implementation is located in `src/orchestration/q_optimizer.py`. It consists of three primary components:

### A. State Encoder
When a user submits a research query, the `StateEncoder` uses keyword heuristics to map the natural language string into a discrete mathematical tuple: `(complexity, domain, source)`.

* **Complexity**: `1` (High, e.g., "analyze", "script") or `0` (Low).
* **Domain**: `0` (Code/Math), `1` (Factual/Literature), or `2` (Other).
* **Source**: `0` (Local Docs), `1` (Web), or `2` (CSV/Data).

*Example: "Write a python script to analyze the CSV" -> State: `(1, 0, 2)`*

### B. Action Space
The agent can choose from 4 distinct actions:
1. `0: RAG_RETRIEVAL` (Query ChromaDB)
2. `1: CODE_EXECUTION` (Run isolated python code in the Docker sandbox)
3. `2: BROWSER_SCRAPE` (Scrape live web data)
4. `3: SYNTHESIS` (Compile reports using the LLM)

### C. The Bellman Equation & Rewards
When an action is taken, the resulting **confidence score** (0.0 to 1.0) is treated as the **Reward**. 
The agent updates its `Q-table` (a matrix of expected future rewards for state-action pairs) using the standard **Bellman Update Equation**:

$$Q(s, a) = Q(s, a) + \alpha \times \left(R + \gamma \times \max Q(s', a') - Q(s, a)\right)$$

* **Learning Rate ($\alpha$)**: `0.1` (How quickly it overwrites old knowledge)
* **Discount Factor ($\gamma$)**: `0.9` (Importance of future rewards)
* **Exploration Rate ($\epsilon$)**: `0.1` (10% of the time, it picks a random action to discover new strategies).

## 3. Where is it Used? (The Architecture)

The Q-Learning engine is deeply integrated across the OS:

1. **`src/orchestration/q_optimizer.py`**: Contains the core math, `QLearningAgent`, and `StateEncoder`. It handles JSON serialization to persist knowledge between reboots in `workspace/q_table.json`.
2. **`src/orchestration/planner.py`**: The `PlannerEngine` encodes the live user query, executes the subtasks, and actively calls `q_agent.update()` to feed the confidence scores back into the model as rewards.
3. **`src/data_rag/benchmark_runner.py`**: The evaluation suite runs headless simulated tasks to rapidly train the RL agent without human intervention.
4. **`src/security/policy_engine.py`**: Acts as a governor. If the Q-value for a dangerous action (like `CODE_EXECUTION`) exceeds a hardcoded safety ceiling (`8.0`), the Policy Engine intercepts and blocks the knowledge update to prevent runaway recursive execution.
5. **`src/ui/app.py`**: The Streamlit UI actively reads `workspace/q_table.json` and renders it in the **"🤖 Q-Learning Agent State"** expander in Column 2, allowing the human operator to audit exactly what the AI has learned and which action is currently deemed "best" for the given state.
