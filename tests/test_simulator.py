"""
AFTERSHOCK AI — Infrastructure Data & Simulation Engine Tests
Module: tests/test_simulator.py
"""

import os
import unittest
from simulator import (
    load_infrastructure_data,
    simulate_disaster,
    resolve_scenario,
    get_all_assets,
    get_all_scenarios,
    get_all_interventions,
    DATA_FILE_PATH,
)


class TestInfrastructureData(unittest.TestCase):
    """Test suite for validating JSON storage format and relational integrity."""

    def test_json_file_exists_and_loads(self):
        """The infrastructure JSON file exists and loads successfully."""
        self.assertTrue(os.path.exists(DATA_FILE_PATH))
        data = load_infrastructure_data(DATA_FILE_PATH)
        self.assertIn("assets", data)
        self.assertIn("dependencies", data)
        self.assertIn("scenarios", data)
        self.assertIn("interventions", data)

    def test_asset_ids_are_unique(self):
        """All configured assets must have unique IDs."""
        data = load_infrastructure_data()
        ids = [a["id"] for a in data["assets"]]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate asset IDs detected.")

    def test_required_five_assets_present(self):
        """The required five critical assets must be present."""
        assets = get_all_assets()
        asset_ids = {a["id"] for a in assets}
        required_core = {"substation", "water", "hospital", "tower", "road"}
        self.assertTrue(required_core.issubset(asset_ids), f"Missing core assets: {required_core - asset_ids}")

    def test_asset_properties_present(self):
        """Assets must contain id, name, category, criticality, and depends_on."""
        assets = get_all_assets()
        for a in assets:
            self.assertIn("id", a)
            self.assertIn("name", a)
            self.assertIn("category", a)
            self.assertIn("criticality", a)
            self.assertIn("depends_on", a)
            self.assertIsInstance(a["criticality"], (int, float))
            self.assertGreater(a["criticality"], 0)

    def test_dependencies_point_to_valid_assets(self):
        """Directed dependencies must reference existing source and target assets."""
        data = load_infrastructure_data()
        valid_ids = {a["id"] for a in data["assets"]}
        for dep in data["dependencies"]:
            self.assertIn(dep["source"], valid_ids, f"Unknown dependency source: {dep['source']}")
            self.assertIn(dep["target"], valid_ids, f"Unknown dependency target: {dep['target']}")

    def test_scenarios_reference_valid_assets(self):
        """Scenarios must only list valid asset IDs in initial_failures."""
        data = load_infrastructure_data()
        valid_ids = {a["id"] for a in data["assets"]}
        for scen in data["scenarios"]:
            for init_f in scen["initial_failures"]:
                self.assertIn(init_f, valid_ids, f"Scenario '{scen['id']}' references unknown asset '{init_f}'")


class TestCascadingSimulator(unittest.TestCase):
    """Test suite for cascade propagation, protection rules, and cycle safety."""

    def test_all_supported_scenarios_run(self):
        """All supported scenarios run without error and return expected schema."""
        for sc in ("flood", "power_outage", "communication_failure"):
            res = simulate_disaster(sc)
            self.assertEqual(res["scenario"], sc)
            self.assertIn("disruption_score", res)
            self.assertIn("failed_assets", res)
            self.assertIn("operational_assets", res)
            self.assertIn("timeline", res)
            self.assertGreater(res["failed_count"], 0)
            self.assertEqual(res["total_assets"], res["failed_count"] + res["operational_count"])

    def test_initial_failures_respected(self):
        """Simulation begins with the exact initial failures defined by the scenario."""
        res_flood = simulate_disaster("flood")
        self.assertIn("substation", res_flood["initial_failures"])
        self.assertIn("road", res_flood["initial_failures"])

        res_comm = simulate_disaster("communication_failure")
        self.assertEqual(res_comm["initial_failures"], ["tower"])

    def test_cascade_propagation_correctness(self):
        """Communication failure propagates strictly to dependent assets (hospital, emergency)."""
        res_comm = simulate_disaster("communication_failure")
        # In communication failure, tower fails. Hospital and emergency depend on tower.
        # Water pump and substation do NOT depend on tower, so they stay operational!
        self.assertIn("tower", res_comm["failed_assets"])
        self.assertIn("hospital", res_comm["failed_assets"])
        self.assertIn("emergency", res_comm["failed_assets"])
        self.assertNotIn("substation", res_comm["failed_assets"])
        self.assertNotIn("water", res_comm["failed_assets"])
        self.assertNotIn("road", res_comm["failed_assets"])

    def test_disruption_score_formula(self):
        """Disruption score equals the sum of criticality of all failed assets."""
        assets_map = {a["id"]: a["criticality"] for a in get_all_assets()}
        for sc in ("flood", "power_outage", "communication_failure"):
            res = simulate_disaster(sc)
            expected_score = sum(assets_map[aid] for aid in res["failed_assets"])
            self.assertEqual(res["disruption_score"], expected_score)

    def test_cycle_safety_no_infinite_loop(self):
        """Simulation handles cyclic dependencies safely without hanging or duplicating."""
        cyclic_data = load_infrastructure_data()
        # Add artificial cycle: road depends on water, water depends on road
        cyclic_data["dependencies"].append({"source": "hospital", "target": "substation"})
        # Run simulation with cycle present
        res = simulate_disaster("power_outage", custom_data=cyclic_data)
        self.assertIsNotNone(res)
        # Ensure each asset is failed at most once
        self.assertEqual(len(res["failed_assets"]), len(set(res["failed_assets"])))

    def test_protected_asset_behavior(self):
        """Applying protection prevents failure according to defined mechanism."""
        # Substation flood protection in flood scenario
        baseline = simulate_disaster("flood", protected_assets=[])
        protected = simulate_disaster("flood", protected_assets=["INT-SUB", "INT-ROD"])
        self.assertLess(protected["disruption_score"], baseline["disruption_score"])
        self.assertEqual(protected["disruption_score"], 0)
        self.assertIn("substation", protected["operational_assets"])
        self.assertIn("road", protected["operational_assets"])

    def test_protection_specificity_not_universal(self):
        """Substation flood protection does NOT protect against power grid explosion."""
        # INT-SUB is a flood defense; in power_outage it is ineffective against internal grid surge
        res_power_protected = simulate_disaster("power_outage", protected_assets=["INT-SUB"])
        self.assertIn("substation", res_power_protected["failed_assets"])

    def test_invalid_scenario_rejected(self):
        """Invalid scenario names must raise ValueError."""
        with self.assertRaises(ValueError):
            simulate_disaster("tornado_unsupported")

    def test_invalid_protected_id_rejected(self):
        """Nonexistent protection or asset IDs must raise ValueError."""
        with self.assertRaises(ValueError):
            simulate_disaster("flood", protected_assets=["FAKE_ASSET_XYZ"])


if __name__ == "__main__":
    unittest.main()

