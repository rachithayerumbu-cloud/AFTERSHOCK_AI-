"""
AFTERSHOCK AI — Budget-Aware Optimizer Tests
Module: tests/test_optimizer.py
"""

import math
import unittest
from optimizer import optimize_interventions, validate_budget
from simulator import simulate_disaster, get_all_interventions


class TestOptimizer(unittest.TestCase):
    """Test suite for combinatorial budget optimization and constraint enforcement."""

    def test_zero_budget_handled_correctly(self):
        """Zero budget produces an empty plan with zero cost and baseline disruption."""
        res = optimize_interventions("flood", budget=0)
        self.assertEqual(res["total_cost"], 0)
        self.assertEqual(res["remaining_budget"], 0)
        self.assertEqual(res["selected_interventions"], [])
        self.assertEqual(res["disruption_reduction"], 0)
        self.assertEqual(res["optimized_disruption"], res["baseline_disruption"])

    def test_negative_budget_rejected(self):
        """Negative budgets must raise ValueError."""
        with self.assertRaises(ValueError):
            optimize_interventions("flood", budget=-1000)

    def test_non_finite_budget_rejected(self):
        """NaN and Infinite budgets must raise ValueError."""
        with self.assertRaises(ValueError):
            optimize_interventions("flood", budget=float("nan"))
        with self.assertRaises(ValueError):
            optimize_interventions("flood", budget=float("inf"))
        with self.assertRaises(ValueError):
            optimize_interventions("flood", budget=float("-inf"))

    def test_boolean_budget_rejected(self):
        """Boolean values (True, False) must be rejected even though bool is subclass of int."""
        with self.assertRaises(ValueError):
            validate_budget(True)
        with self.assertRaises(ValueError):
            validate_budget(False)

    def test_cost_never_exceeds_budget(self):
        """Total intervention cost must never exceed the specified budget."""
        test_budgets = [5000, 15000, 20000, 35000, 50000, 75000, 100000]
        for sc in ("flood", "power_outage", "communication_failure"):
            for b in test_budgets:
                res = optimize_interventions(sc, budget=b)
                self.assertLessEqual(res["total_cost"], b, f"Cost {res['total_cost']} exceeded budget {b} in {sc}")
                self.assertAlmostEqual(res["remaining_budget"], b - res["total_cost"])

    def test_reported_score_matches_actual_simulation(self):
        """The optimized score reported must exactly match re-running the simulator with chosen plan."""
        for sc in ("flood", "power_outage", "communication_failure"):
            for b in (0, 20000, 50000):
                opt = optimize_interventions(sc, budget=b)
                selected_ids = opt["selected_intervention_ids"]
                manual_sim = simulate_disaster(sc, protected_assets=selected_ids)
                self.assertEqual(opt["optimized_disruption"], manual_sim["disruption_score"])
                self.assertEqual(opt["disruption_reduction"], opt["baseline_disruption"] - manual_sim["disruption_score"])

    def test_reduction_matches_math(self):
        """Reported absolute reduction must equal baseline minus optimized."""
        res = optimize_interventions("flood", budget=50000)
        self.assertEqual(res["disruption_reduction"], res["baseline_disruption"] - res["optimized_disruption"])
        if res["baseline_disruption"] > 0:
            expected_pct = round((res["disruption_reduction"] / res["baseline_disruption"]) * 100.0, 2)
            self.assertEqual(res["disruption_reduction_percent"], expected_pct)

    def test_insufficient_budget_handled_honestly(self):
        """Budget below cheapest intervention returns 0 improvement and honest explanation."""
        min_cost = min(item["cost"] for item in get_all_interventions())
        insufficient_b = min_cost - 100
        res = optimize_interventions("flood", budget=insufficient_b)
        self.assertEqual(res["total_cost"], 0)
        self.assertEqual(res["disruption_reduction"], 0)
        self.assertEqual(res["selected_interventions"], [])
        self.assertIn("insufficient", res["explanation"].lower())

    def test_no_nonexistent_interventions_recommended(self):
        """All recommended interventions must exist in the authoritative catalog."""
        valid_ids = {item["id"] for item in get_all_interventions()}
        for sc in ("flood", "power_outage", "communication_failure"):
            res = optimize_interventions(sc, budget=60000)
            for iid in res["selected_intervention_ids"]:
                self.assertIn(iid, valid_ids)


if __name__ == "__main__":
    unittest.main()

