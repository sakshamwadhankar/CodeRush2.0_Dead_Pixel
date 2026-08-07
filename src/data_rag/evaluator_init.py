"""
Strategy Benchmark Runner and Self-Evolution Evaluation Package for Aegis Research OS (Step C5).
"""

from evaluator.dataset import BenchmarkDataset, HELD_OUT_BENCHMARK_TASKS
from evaluator.metrics import EvaluationMetricsCalculator
from evaluator.benchmark_runner import StrategyBenchmarkRunner

__all__ = [
    "BenchmarkDataset",
    "HELD_OUT_BENCHMARK_TASKS",
    "EvaluationMetricsCalculator",
    "StrategyBenchmarkRunner"
]
