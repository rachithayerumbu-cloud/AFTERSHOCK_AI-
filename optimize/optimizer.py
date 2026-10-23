"""
AFTERSHOCK AI — Budget-Aware Intervention Optimizer
Module: optimize/optimizer.py

Formulates and solves the budget-constrained critical infrastructure protection
problem using exact combinatorial multi-objective optimization over the cascading
failure simulation of the 10 civic infrastructure facilities.
"""

import sys
import os
import math

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.simulation import (
    simulate_disaster,
    INTERVENTIONS,
    ASSETS,
    SCENARIOS,
    resolve_scenario,
)


def get_baseline_disruption(scenario="flood"):
    """Calculate the baseline disruption score without any protective interventions."""
    sim = simulate_disaster(scenario, [])
    return sim["weighted_disruption"]


def optimize_interventions(scenario="flood", budget=50000, **kwargs):
    """
    Finds the optimal set of infrastructure protection interventions that
    minimizes simulated cascading disruption within a given budget.

    Decision Model:
    ---------------
    Objective:
        Lexicographic minimization:
        1. Minimize post-disaster weighted disruption score: D(S, P)
        2. Minimize intervention cost: Cost(P)
        3. Minimize intervention count: |P|

    Subject to:
        Cost(P) <= Budget

    Parameters
    ----------
    scenario : str or list
        Scenario ID ("flood", "power", "communication").
        If a list is provided (legacy test input), defaults to "flood".
    budget : int or float
        Maximum allowable intervention budget in INR. Default is 50,000.

    Returns
    -------
    dict
        Optimal intervention plan and comparative resilience metrics.
    """
    if "scenario_or_failed" in kwargs:
        scenario = kwargs["scenario_or_failed"]

    # Backward compatibility with legacy test harness passing failed asset lists
    if isinstance(scenario, (list, set)):
        scenario_id = "flood"
    else:
        scenario_id = resolve_scenario(scenario)

    if (
        isinstance(budget, bool)
        or not isinstance(budget, (int, float))
        or not math.isfinite(budget)
        or budget < 0
    ):
        raise ValueError("Budget must be a finite, non-negative number.")

    # 1. Baseline simulation without interventions
    baseline_sim = simulate_disaster(scenario_id, [])
    baseline_disruption = baseline_sim["weighted_disruption"]

    # Candidate intervention pool: 6 original interventions
    candidate_interventions = INTERVENTIONS
    n_interventions = len(candidate_interventions)

    best_solution = None
    best_score = (float("inf"), float("inf"), float("inf"))
    combinations_evaluated = 0

    # Exhaustive search over all 2^6 = 64 combinations
    for mask in range(1 << n_interventions):
        selected = [
            candidate_interventions[i]
            for i in range(n_interventions)
            if mask & (1 << i)
        ]

        total_cost = sum(item["cost"] for item in selected)

        # Budget constraint
        if total_cost > budget:
            continue

        combinations_evaluated += 1

        selected_ids = [item["id"] for item in selected]
        sim_result = simulate_disaster(scenario_id, selected_ids)
        disruption = sim_result["weighted_disruption"]

        # Lexicographic criteria: (disruption, cost, count)
        candidate_score = (disruption, total_cost, len(selected))

        if candidate_score < best_score:
            best_score = candidate_score
            best_solution = {
                "selected": selected,
                "total_cost": total_cost,
                "sim": sim_result,
            }

    if best_solution is None:
        best_solution = {
            "selected": [],
            "total_cost": 0,
            "sim": baseline_sim,
        }

    selected_list = best_solution["selected"]
    selected_ids = [item["id"] for item in selected_list]
    selected_names = [item["name"] for item in selected_list]
    total_cost = best_solution["total_cost"]
    remaining_budget = budget - total_cost

    optimized_sim = best_solution["sim"]
    optimized_disruption = optimized_sim["weighted_disruption"]
    disruption_reduction = max(baseline_disruption - optimized_disruption, 0)

    reduction_percent = (
        (100.0 * disruption_reduction / baseline_disruption)
        if baseline_disruption > 0
        else 0.0
    )

    min_cost = min((item["cost"] for item in candidate_interventions), default=0)

    if disruption_reduction > 0:
        message = (
            f"Optimal plan identified. Evaluated {combinations_evaluated} affordable combination(s). "
            f"Reduces cascading disruption by {disruption_reduction} points ({round(reduction_percent, 1)}%) "
            f"using Rs. {total_cost:,} of the Rs. {budget:,} budget."
        )
    elif budget < min_cost:
        message = (
            f"Budget of Rs. {budget:,} is insufficient for any available intervention "
            f"(minimum required: Rs. {min_cost:,}). Baseline disruption remains at {baseline_disruption}."
        )
    elif baseline_disruption == 0:
        message = (
            f"Scenario '{scenario_id}' results in zero baseline disruption. "
            f"No intervention needed."
        )
    else:
        message = (
            f"No available intervention within Rs. {budget:,} reduces disruption for scenario '{scenario_id}'. "
            f"Disruption remains at baseline ({baseline_disruption}); unneeded spending was avoided."
        )

    return {
        "scenario": scenario_id,
        "scenario_name": SCENARIOS[scenario_id]["name"],
        "budget": budget,
        "selected_interventions": selected_list,
        "selected_intervention_ids": selected_ids,
        "selected_intervention_names": selected_names,
        "intervention_ids": selected_ids,
        "total_cost": total_cost,
        "remaining_budget": remaining_budget,
        "baseline_disruption": baseline_disruption,
        "optimized_disruption": optimized_disruption,
        "disruption_reduction": disruption_reduction,
        "improvement": disruption_reduction,
        "disruption_reduction_percent": round(reduction_percent, 2),
        "combinations_evaluated": combinations_evaluated,
        "message": message,
        "baseline": baseline_sim,
        "optimized": optimized_sim,
        "note": "Combinatorial multi-objective knapsack search with fixed-point cascade simulation.",
    }


def get_optimizer_result(scenario_or_failed="flood", budget=50000):
    """Convenience alias for API and test harness."""
    return optimize_interventions(scenario_or_failed, budget)


if __name__ == "__main__":
    test_budget = 50000  # Rs. 50,000 default budget
    for s in ["flood", "power", "communication"]:
        res = get_optimizer_result(s, test_budget)
        print(f"\n====================================")
        print(f"Scenario:             {res['scenario_name']}")
        print(f"Budget:               Rs. {res['budget']:,}")
        print(f"Baseline disruption:  {res['baseline_disruption']}")
        print(f"Optimized disruption: {res['optimized_disruption']}")
        print(f"Disruption reduction: {res['disruption_reduction']} ({res['disruption_reduction_percent']}%)")
        print(f"Total cost:           Rs. {res['total_cost']:,}")
        print(f"Remaining budget:     Rs. {res['remaining_budget']:,}")
        print(f"Combinations tested:  {res['combinations_evaluated']}")
        print(f"Selected:             {res['selected_intervention_names']}")
