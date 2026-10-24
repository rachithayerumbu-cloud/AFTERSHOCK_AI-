"""
AFTERSHOCK AI — Budget-Aware Intervention Optimizer
Module: optimizer.py

This module formulates and solves the budget-constrained infrastructure protection problem.
It uses an exhaustive combinatorial evaluation over the candidate intervention space
(2^N feasible subsets, where N=6) to identify the optimal resilience investment.

Decision Model:
---------------
Objective:
    Lexicographical optimization:
    1. Minimize post-disaster disruption score: D(Scenario, Interventions)
    2. Minimize total intervention expenditure in INR: Sum(Cost)
    3. Minimize the number of deployed interventions: |Interventions|

Subject to:
    Sum(Cost) <= Available Budget (in INR)
    Cost >= 0, Budget >= 0

Scope & Complexity Note:
------------------------
For N=6 interventions, evaluating all 64 subsets takes less than 15ms locally.
While exhaustive search guarantees the globally optimal combination for this small network,
in larger industrial networks (e.g., N > 30), exact search becomes NP-hard and heuristic
or integer programming techniques (e.g., branch-and-bound, genetic algorithms) would be required.
"""

import math
from copy import deepcopy
from simulator import (
    simulate_disaster,
    get_all_interventions,
    get_all_scenarios,
    resolve_scenario,
    SCENARIOS,
)


def validate_budget(budget):
    """
    Validate that the budget parameter is a finite, non-negative numeric value.

    Raises:
        ValueError: If budget is boolean, non-numeric, negative, NaN, or infinite.
    """
    # In Python, bool is a subclass of int (isinstance(True, int) == True),
    # so we must explicitly reject booleans.
    if isinstance(budget, bool):
        raise ValueError("Budget cannot be a boolean value.")

    if isinstance(budget, str):
        try:
            budget = float(budget.strip())
        except ValueError:
            raise ValueError(f"Invalid budget string '{budget}'. Must be a numeric amount.")

    if not isinstance(budget, (int, float)):
        raise ValueError(f"Budget must be a numeric value, got {type(budget).__name__}.")

    if not math.isfinite(budget):
        raise ValueError("Budget must be a finite number (cannot be NaN or Infinity).")

    if budget < 0:
        raise ValueError("Budget cannot be negative. Please provide a non-negative budget in INR.")

    return float(budget)


def optimize_interventions(scenario="flood", budget=50000):
    """
    Find the optimal subset of protective interventions within the user's budget.

    Parameters:
    -----------
    scenario : str
        Hazard scenario identifier ('flood', 'power_outage', 'communication_failure').
    budget : int or float
        Maximum allowable resilience expenditure in Indian Rupees (INR).

    Returns:
    --------
    dict
        Structured optimization report detailing recommended interventions,
        financial allocation, disruption reduction metrics, and the full simulation outcome.
    """
    valid_budget = validate_budget(budget)
    canonical_scenario = resolve_scenario(scenario)
    scenario_info = SCENARIOS[canonical_scenario]

    # 1. Compute baseline simulation (no protective measures applied)
    baseline_result = simulate_disaster(scenario=canonical_scenario, protected_assets=[])
    baseline_disruption = baseline_result["disruption_score"]

    candidate_interventions = get_all_interventions()
    n_candidates = len(candidate_interventions)

    best_plan = []
    best_cost = 0.0
    best_disruption = baseline_disruption
    best_sim_result = baseline_result
    combinations_evaluated = 0

    # Exhaustive evaluation over 2^N combinations
    # Tuple key for lexicographical minimization: (disruption_score, total_cost, intervention_count)
    best_score_tuple = (baseline_disruption, 0.0, 0)

    for mask in range(1 << n_candidates):
        subset = [
            candidate_interventions[i]
            for i in range(n_candidates)
            if (mask & (1 << i))
        ]

        cost = sum(item["cost"] for item in subset)

        # Enforce budget constraint
        if cost > valid_budget:
            continue

        combinations_evaluated += 1

        # Simulate scenario with this intervention subset
        subset_ids = [item["id"] for item in subset]
        sim_res = simulate_disaster(scenario=canonical_scenario, protected_assets=subset_ids)
        disruption = sim_res["disruption_score"]

        score_tuple = (disruption, cost, len(subset))

        if score_tuple < best_score_tuple:
            best_score_tuple = score_tuple
            best_plan = subset
            best_cost = cost
            best_disruption = disruption
            best_sim_result = sim_res

    # Calculate resilience benefits
    absolute_reduction = baseline_disruption - best_disruption
    if baseline_disruption > 0:
        percent_reduction = round((absolute_reduction / baseline_disruption) * 100.0, 2)
    else:
        percent_reduction = 0.0

    remaining_budget = valid_budget - best_cost
    selected_ids = [item["id"] for item in best_plan]
    selected_names = [item["name"] for item in best_plan]

    # Synthesize plain-language explanation
    min_possible_cost = min((item["cost"] for item in candidate_interventions), default=0)

    if absolute_reduction > 0:
        explanation = (
            f"Recommended {len(best_plan)} intervention(s) costing ₹{int(best_cost):,} "
            f"within your budget of ₹{int(valid_budget):,}. "
            f"This reduces cascading disruption from {baseline_disruption} to {best_disruption} "
            f"({absolute_reduction} points saved, a {percent_reduction}% improvement). "
            f"Remaining budget is ₹{int(remaining_budget):,}."
        )
    elif valid_budget < min_possible_cost:
        explanation = (
            f"Your budget of ₹{int(valid_budget):,} is insufficient to afford any single intervention "
            f"(the lowest-cost measure requires ₹{int(min_possible_cost):,}). "
            f"Disruption remains at baseline ({baseline_disruption} points)."
        )
    elif baseline_disruption == 0:
        explanation = (
            f"Scenario '{scenario_info['name']}' produces zero baseline disruption. "
            f"No expenditure is required."
        )
    else:
        explanation = (
            f"No available intervention combination within ₹{int(valid_budget):,} "
            f"could mitigate the specific failure propagation path of this scenario. "
            f"Disruption remains at baseline ({baseline_disruption} points); unnecessary spending was avoided."
        )

    return {
        "scenario": canonical_scenario,
        "scenario_name": scenario_info["name"],
        "budget": valid_budget,
        "selected_interventions": best_plan,
        "selected_intervention_ids": selected_ids,
        "selected_intervention_names": selected_names,
        "total_cost": best_cost,
        "remaining_budget": remaining_budget,
        "baseline_disruption": baseline_disruption,
        "optimized_disruption": best_disruption,
        "disruption_reduction": absolute_reduction,
        "disruption_reduction_percent": percent_reduction,
        "combinations_evaluated": combinations_evaluated,
        "total_combinations_in_space": 1 << n_candidates,
        "explanation": explanation,
        "optimized_simulation": best_sim_result,
        "baseline_simulation": baseline_result,
        "disclaimer": "Budget optimization based on illustrative simulated costs and deterministic cascade rules.",
    }


if __name__ == "__main__":
    print("Testing Optimizer directly...")
    for test_b in (0, 15000, 35000, 60000):
        res = optimize_interventions("flood", test_b)
        print(f"\nBudget: Rs. {test_b:,} | Disruption: {res['baseline_disruption']} -> {res['optimized_disruption']} (Saved {res['disruption_reduction']})")
        print(f"Plan: {res['selected_intervention_names']} | Spent: Rs. {int(res['total_cost']):,} | Left: Rs. {int(res['remaining_budget']):,}")
        # Sanitize ₹ to Rs. for windows console print
        clean_exp = res['explanation'].replace("\u20b9", "Rs. ")
        print(f"Explanation: {clean_exp}")
