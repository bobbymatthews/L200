"""Automated Regression Testing against the Golden Benchmark Dataset."""

from __future__ import annotations

from evals.evaluator import GoldenEvaluator


def test_golden_dataset_regression_suite(tmp_path):
    """Run golden dataset evaluation suite and verify no regressions occurred."""
    evaluator = GoldenEvaluator()
    report = evaluator.run_suite(output_dir=str(tmp_path))

    assert report.total_test_cases >= 4
    assert report.regression_detected is False
    assert report.overall_pass_rate_percent >= 80.0
    assert report.average_composite_score >= 75.0

    # Ensure all test case categories are evaluated
    categories = {r.category for r in report.test_results}
    assert "core_cloud_architecture" in categories
    assert "adversarial_hallucination_check" in categories

    # Ensure adversarial test case correctly caught hallucinations
    adversarial_case = next(r for r in report.test_results if r.category == "adversarial_hallucination_check")
    assert adversarial_case.hallucination_catch_score == 100.0
