"""
Simple tests for Rachitha's optimizer.
Run with:

python test_optimizer.py
"""

from optimizer import optimize_interventions, get_optimizer_result


def test_budget_is_never_exceeded():
    failed = ["SUBSTATION_A", "HOSPITAL_B", "WATER_PUMP_C"]
    budget = 1_000_000

    result = optimize_interventions(failed, budget)

    assert result["total_cost"] <= budget


def test_result_contains_required_fields():
    failed = ["SUBSTATION_A", "HOSPITAL_B"]
    budget = 1_000_000

    result = get_optimizer_result(failed, budget)

    required = [
        "budget",
        "baseline_disruption",
        "optimized_disruption",
        "improvement",
        "selected_interventions",
        "total_cost",
        "remaining_budget",
    ]

    for field in required:
        assert field in result


def test_remaining_budget_is_correct():
    failed = ["SUBSTATION_A", "HOSPITAL_B"]
    budget = 1_000_000

    result = get_optimizer_result(failed, budget)

    assert result["remaining_budget"] == (
        budget - result["total_cost"]
    )


if __name__ == "__main__":
    test_budget_is_never_exceeded()
    test_result_contains_required_fields()
    test_remaining_budget_is_correct()

    print("All optimizer tests passed.")
