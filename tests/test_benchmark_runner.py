"""
Unit tests for Step C5 Strategy Benchmark Runner and Evaluation system.
"""

import json
import os
import pytest
from evaluator.dataset import BenchmarkDataset
from evaluator.metrics import EvaluationMetricsCalculator
from evaluator.benchmark_runner import StrategyBenchmarkRunner
from src.data_rag.hybrid_engine import HybridRAGEngine


def test_benchmark_dataset():
    ds = BenchmarkDataset()
    assert len(ds) == 10
    standard = ds.get_standard_tasks()
    probes = ds.get_injection_probes()
    assert len(standard) == 8
    assert len(probes) == 2


def test_metrics_calculator():
    calc = EvaluationMetricsCalculator()

    # Success rate
    passages = [{"text": "ChromaDB and BM25 hybrid vector search."}]
    success = calc.calculate_task_success(passages, ["chromadb", "bm25"])
    assert success == 1.0

    # Citation metrics
    citations = [
        {"verification_status": "verified"},
        {"verification_status": "verified"},
        {"verification_status": "unverified"}
    ]
    precision, recall, unsupported_rate = calc.calculate_citation_metrics(citations)
    assert precision == 0.6667
    assert unsupported_rate == 0.3333

    # Composite score
    metrics = {
        "end_to_end_success_rate": 0.90,
        "citation_precision": 0.85,
        "unsupported_claim_rate": 0.15,
        "prompt_injection_resistance": 1.0,
        "execution_efficiency": 0.8
    }
    composite = calc.calculate_composite_score(metrics)
    assert 0.0 <= composite <= 1.0
    assert composite > 0.80


def test_strategy_benchmark_runner_single_run(tmp_path):
    history_file = str(tmp_path / "benchmark_history.json")
    runner = StrategyBenchmarkRunner(history_filepath=history_file)

    yaml_path = "strategies/v1_baseline_strategy.yaml"
    res = runner.run_benchmark(yaml_path)

    assert res["status"] == "evaluated"
    assert res["strategy_version"] == "v1.0.0"
    assert "composite_score" in res["metrics"]
    assert res["metrics"]["end_to_end_success_rate"] >= 0.0


def test_comparative_benchmark_and_state_sync(tmp_path):
    history_file = str(tmp_path / "history.json")
    state_file = str(tmp_path / "state.json")

    runner = StrategyBenchmarkRunner(history_filepath=history_file)

    baseline_yaml = "strategies/v1_baseline_strategy.yaml"
    candidate_yaml = "strategies/v2_improved_strategy.yaml"

    report = runner.run_comparative_benchmark(baseline_yaml, candidate_yaml)

    assert report["decision"] in ["APPROVE", "ROLLBACK"]
    assert "score_delta" in report
    assert "active_strategy_version" in report

    # Test state sync
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump({"query": "eval test"}, f)

    updated_state = runner.sync_with_state(report, state_filepath=state_file)
    assert updated_state["status"] == "strategy_evaluated"
    assert updated_state["strategy_evaluation"]["active_strategy_version"] == report["active_strategy_version"]
