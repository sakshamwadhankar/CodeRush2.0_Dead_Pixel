"""
Demonstration of Step C5: Strategy Benchmark Runner & Self-Evolution Loop in Aegis Research OS.
"""

import json
from evaluator import StrategyBenchmarkRunner, BenchmarkDataset


def run_c5_demo():
    print("=== Aegis Research OS - Step C5 Strategy Benchmark Runner & Self-Evolution Loop ===")

    runner = StrategyBenchmarkRunner(history_filepath="evaluator/benchmark_history.json")

    baseline_yaml = "strategies/v1_baseline_strategy.yaml"
    candidate_yaml = "strategies/v2_improved_strategy.yaml"

    print("\n[1] Running Baseline Strategy Evaluation (v1_baseline_strategy.yaml)...")
    baseline_res = runner.run_benchmark(baseline_yaml)
    print(f"[OK] Baseline Strategy Version: {baseline_res['strategy_version']}")
    print(f"[OK] Baseline Composite Score: {baseline_res['metrics']['composite_score']}")
    print(f"     - End-to-End Success Rate: {baseline_res['metrics']['end_to_end_success_rate'] * 100}%")
    print(f"     - Citation Precision: {baseline_res['metrics']['citation_precision'] * 100}%")
    print(f"     - Prompt Injection Resistance: {baseline_res['metrics']['prompt_injection_resistance'] * 100}%")

    print("\n[2] Running Candidate Self-Evolved Strategy Evaluation (v2_improved_strategy.yaml)...")
    candidate_res = runner.run_benchmark(candidate_yaml)
    print(f"[OK] Candidate Strategy Version: {candidate_res['strategy_version']}")
    print(f"[OK] Candidate Composite Score: {candidate_res['metrics']['composite_score']}")

    print("\n[3] Executing Comparative Benchmark & Self-Evolution Governance Check...")
    report = runner.run_comparative_benchmark(baseline_yaml, candidate_yaml)

    print(f"\n[+] Governance Decision: {report['decision']}")
    print(f"[+] Score Delta: {report['score_delta']}")
    print(f"[+] Rationale: {report['rationale']}")
    print(f"[+] Active Approved Strategy Version: {report['active_strategy_version']}")

    print("\n[4] Writing benchmark governance results to state.json...")
    with open("state.json", "w", encoding="utf-8") as f:
        json.dump({
            "project_name": "Aegis Research OS",
            "active_task_id": "task_c5_strategy_benchmark",
            "query": "self evolution strategy benchmark evaluation",
            "retrieval_config": {"top_k": 5, "dense_weight": 0.6, "sparse_weight": 0.4},
            "status": "idle"
        }, f, indent=2)

    updated_state = runner.sync_with_state(report, "state.json")
    print(f"[OK] state.json status: {updated_state['status']}")
    print(f"[OK] state.json active_strategy_version: {updated_state['strategy_evaluation']['active_strategy_version']}")
    print(f"[OK] state.json decision: {updated_state['strategy_evaluation']['decision']}")

    print("\n=== Step C5 Strategy Benchmark Runner demo completed successfully! ===")


if __name__ == "__main__":
    run_c5_demo()
