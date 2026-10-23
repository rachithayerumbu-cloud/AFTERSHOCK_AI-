"""
AFTERSHOCK AI - Budget-Aware Intervention Optimizer
Owner: Rachitha

Purpose:
Choose the best combination of protective interventions that stays
within a limited budget and minimizes simulated disruption.

This is a standalone first version. Later, Rachana can connect it
to Flask and Maithri can connect it to the real simulation output.
"""

from itertools import combinations


# Demo interventions.
# Costs are SIMULATED values for the hackathon prototype.
INTERVENTIONS = [
    {
        "id": "protect_substation_A",
        "name": "Protect Substation A",
        "cost": 500000,
    },
    {
        "id": "backup_hospital_B",
        "name": "Backup Power for Hospital B",
        "cost": 400000,
    },
    {
        "id": "protect_water_pump_C",
        "name": "Protect Water Pump C",
        "cost": 300000,
    },
    {
        "id": "backup_communication_D",
        "name": "Backup Communication Tower D",
        "cost": 200000,
    },
]


# These are demo weights for the first prototype.
# Later, the optimizer should use Maithri's simulation to calculate
# the actual disruption after each intervention combination.
ASSET_WEIGHTS = {
    "HOSPITAL": 10,
    "WATER": 8,
    "SUBSTATION": 7,
    "COMMUNICATION": 5,
    "EMERGENCY": 9,
}


def calculate_disruption(failed_assets, selected_interventions):
    """
    Calculate a simple weighted disruption score.

    Lower score = better outcome.
    """

    disruption = 0

    for asset in failed_assets:
        asset_upper = asset.upper()

        matched = False

        for asset_type, weight in ASSET_WEIGHTS.items():
            if asset_type in asset_upper:
                disruption += weight
                matched = True
                break

        if not matched:
            disruption += 2

    # Demo reduction values.
    # These will eventually be replaced by actual simulation results.
    reductions = {
        "protect_substation_A": 7,
        "backup_hospital_B": 10,
        "protect_water_pump_C": 8,
        "backup_communication_D": 5,
    }

    for intervention in selected_interventions:
        disruption -= reductions.get(intervention["id"], 0)

    return max(disruption, 0)


def optimize_interventions(failed_assets, budget):
    """
    Test every affordable combination of interventions and return
    the combination with the lowest disruption score.

    Parameters
    ----------
    failed_assets : list[str]
        Assets reported as failed by the disaster simulation.

    budget : int
        Maximum simulated budget in rupees.

    Returns
    -------
    dict
        Recommended intervention combination and comparison data.
    """

    best_solution = None
    best_disruption = float("inf")

    # Test every possible combination.
    for number_selected in range(len(INTERVENTIONS) + 1):
        for combination in combinations(INTERVENTIONS, number_selected):

            total_cost = sum(item["cost"] for item in combination)

            # Never exceed the available budget.
            if total_cost > budget:
                continue

            disruption = calculate_disruption(
                failed_assets,
                combination
            )

            if disruption < best_disruption:
                best_disruption = disruption

                best_solution = {
                    "selected_interventions": [
                        item["name"] for item in combination
                    ],
                    "intervention_ids": [
                        item["id"] for item in combination
                    ],
                    "total_cost": total_cost,
                    "remaining_budget": budget - total_cost,
                    "disruption_score": disruption,
                }

    return best_solution


def get_baseline_disruption(failed_assets):
    """Calculate disruption with no intervention."""
    return calculate_disruption(failed_assets, [])


def get_optimizer_result(failed_assets, budget):
    """
    Convenient function for the Flask backend.

    Returns both baseline and optimized results.
    """

    baseline = get_baseline_disruption(failed_assets)
    optimized = optimize_interventions(failed_assets, budget)

    return {
        "budget": budget,
        "baseline_disruption": baseline,
        "optimized_disruption": optimized["disruption_score"],
        "improvement": max(
            baseline - optimized["disruption_score"], 0
        ),
        "selected_interventions": optimized["selected_interventions"],
        "intervention_ids": optimized["intervention_ids"],
        "total_cost": optimized["total_cost"],
        "remaining_budget": optimized["remaining_budget"],
    }


if __name__ == "__main__":
    # ------------------------------------------
    # DEMO TEST
    # ------------------------------------------

    failed_assets = [
        "SUBSTATION_A",
        "WATER_PUMP_C",
        "HOSPITAL_B",
    ]

    budget = 1_000_000  # ₹10 lakh simulated budget

    result = get_optimizer_result(
        failed_assets,
        budget
    )

    print("\n====================================")
    print("       AFTERSHOCK AI OPTIMIZER")
    print("====================================")

    print(f"\nBudget: ₹{result['budget']:,}")

    print(f"\nBaseline disruption: "
          f"{result['baseline_disruption']}")

    print(f"Optimized disruption: "
          f"{result['optimized_disruption']}")

    print(f"Improvement: "
          f"{result['improvement']}")

    print("\nRecommended interventions:")

    for intervention in result["selected_interventions"]:
        print(f"  ✓ {intervention}")

    print(f"\nTotal cost: ₹{result['total_cost']:,}")
    print(f"Remaining budget: ₹{result['remaining_budget']:,}")

    print("\nOptimizer test completed.")
