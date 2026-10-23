"""
AFTERSHOCK AI — Verification and Validation Test Suite
Tests restored 10 civic infrastructure assets, 6 municipal interventions,
exact combinatorial optimizer, and Flask REST API.
"""

from backend.simulation import (
    ASSETS,
    SCENARIOS,
    INTERVENTIONS,
    simulate_disaster,
    resolve_scenario,
)
from optimize.optimizer import (
    optimize_interventions,
    get_optimizer_result,
    get_baseline_disruption,
)
from app import app


def assert_raises_value_error(func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except ValueError:
        return
    raise AssertionError(f"Expected ValueError from {func.__name__}, but none was raised.")


# =====================================================
# SIMULATION ENGINE TESTS (10 CIVIC ASSETS)
# =====================================================

def test_all_10_civic_assets_exist():
    """Verify all 10 original civic infrastructure facilities are present."""
    expected_ids = {
        "substation", "hospital", "water", "tower", "emergency",
        "shelter", "treatment", "data", "traffic", "fire"
    }
    asset_ids = {a["id"] for a in ASSETS}
    assert asset_ids == expected_ids
    assert len(ASSETS) == 10


def test_all_6_municipal_interventions_exist():
    """Verify all 6 original municipal protective interventions and costs."""
    expected_costs = {
        "substation": 30000,
        "hospital": 25000,
        "water": 15000,
        "tower": 20000,
        "emergency": 18000,
        "shelter": 10000,
    }
    assert len(INTERVENTIONS) == 6
    for item in INTERVENTIONS:
        assert item["id"] in expected_costs
        assert item["cost"] == expected_costs[item["id"]]


def test_baseline_disaster_scenarios():
    """Verify all three scenarios initiate and cascade properly."""
    # 1. Flood
    res_flood = simulate_disaster("flood", [])
    assert res_flood["scenario"] == "flood"
    assert "substation" in res_flood["initial_failures"]
    assert "water" in res_flood["initial_failures"]
    assert res_flood["failed_count"] == 10
    assert res_flood["weighted_disruption"] == 78

    # 2. Power Grid Failure
    res_power = simulate_disaster("power", [])
    assert res_power["scenario"] == "power"
    assert "substation" in res_power["initial_failures"]
    assert res_power["failed_count"] == 10
    assert res_power["weighted_disruption"] == 78

    # 3. Communication Failure
    res_comm = simulate_disaster("communication", [])
    assert res_comm["scenario"] == "communication"
    assert res_comm["initial_failures"] == ["tower"]
    # Tower (7) + Hospital (10) + Emergency (9) + Data (6) = 32
    assert set(res_comm["failed_assets"]) == {"tower", "hospital", "emergency", "data"}
    assert res_comm["failed_count"] == 4
    assert res_comm["weighted_disruption"] == 32


def test_scenario_aliases():
    """Ensure aliases 'power_outage' and 'communication_failure' work smoothly."""
    assert resolve_scenario("power_outage") == "power"
    assert resolve_scenario("communication_failure") == "communication"
    assert resolve_scenario("power") == "power"
    assert resolve_scenario("communication") == "communication"
    assert resolve_scenario("flood") == "flood"

    res = simulate_disaster("power_outage", [])
    assert res["scenario"] == "power"
    assert res["weighted_disruption"] == 78


def test_intervention_pathways():
    """Verify each intervention genuinely affects the intended pathway."""
    # Substation Flood Barrier prevents substation failure in power outage
    saved_power = simulate_disaster("power", ["substation"])
    assert saved_power["weighted_disruption"] == 0
    assert saved_power["failed_count"] == 0

    # Communication Backup prevents tower and dependent failures in communication scenario
    saved_comm = simulate_disaster("communication", ["tower"])
    assert saved_comm["weighted_disruption"] == 0
    assert saved_comm["failed_count"] == 0

    # Hospital Backup Power saves Hospital (10 pts) during power failure
    saved_hosp = simulate_disaster("power", ["hospital"])
    assert "hospital" not in saved_hosp["failed_assets"]
    assert saved_hosp["weighted_disruption"] == 78 - 10

    # Shelter Water Reserve saves Relief Shelter (7 pts) during flood
    saved_shelter = simulate_disaster("flood", ["shelter"])
    assert "shelter" not in saved_shelter["failed_assets"]
    assert saved_shelter["weighted_disruption"] == 78 - 7


def test_invalid_intervention_raises():
    """Unknown intervention ID must raise ValueError."""
    assert_raises_value_error(simulate_disaster, "flood", ["UNKNOWN_ACTION"])


# =====================================================
# EXACT COMBINATORIAL OPTIMIZER TESTS
# =====================================================

def test_budget_zero_and_insufficient():
    """Verify handling when budget = 0 or budget is less than cheapest action (Rs. 10,000)."""
    for scenario in ["flood", "power", "communication"]:
        # Zero budget
        res_zero = optimize_interventions(scenario, 0)
        assert res_zero["total_cost"] == 0
        assert res_zero["remaining_budget"] == 0
        assert res_zero["selected_interventions"] == []
        assert res_zero["disruption_reduction"] == 0
        assert res_zero["optimized_disruption"] == res_zero["baseline_disruption"]

        # Sub-minimum budget (Rs. 5,000; cheapest is shelter @ Rs. 10,000)
        res_small = optimize_interventions(scenario, 5000)
        assert res_small["total_cost"] == 0
        assert res_small["remaining_budget"] == 5000
        assert res_small["selected_interventions"] == []
        assert res_small["disruption_reduction"] == 0
        assert res_small["optimized_disruption"] == res_small["baseline_disruption"]
        assert "insufficient" in res_small["message"].lower()


def test_budget_is_never_exceeded():
    """Verify total cost never exceeds budget across all 64 combinatorial evaluations."""
    budgets = [5000, 10000, 15000, 25000, 30000, 50000, 75000, 100000]
    for scenario in ["flood", "power", "communication"]:
        for b in budgets:
            res = optimize_interventions(scenario, b)
            assert res["total_cost"] <= b
            assert res["remaining_budget"] == b - res["total_cost"]
            assert res["optimized_disruption"] <= res["baseline_disruption"]
            assert res["combinations_evaluated"] <= 64


def test_no_false_improvements():
    """Verify post-intervention disruption is strictly calculated by actual simulation."""
    for scenario in ["flood", "power", "communication"]:
        for b in [0, 10000, 25000, 50000]:
            opt = optimize_interventions(scenario, b)
            manual_sim = simulate_disaster(scenario, opt["selected_intervention_ids"])
            assert opt["optimized_disruption"] == manual_sim["weighted_disruption"]
            assert opt["disruption_reduction"] == opt["baseline_disruption"] - manual_sim["weighted_disruption"]


def test_optimizer_smart_tradeoff():
    """
    In Flood scenario with budget = Rs. 25,000:
    - Water Pump Backup (Rs. 15,000) keeps Water Pump online (saves 8 pts)
      and prevents cascading failure of Relief Shelter (saves 7 pts), total 15 pts saved!
    - Hospital Backup Power costs Rs. 25,000 and saves only 10 pts.
    - Adding Shelter Water Reserve (Rs. 10,000) would be redundant since shelter is already saved.
    The optimizer chooses ['water'] (cost Rs. 15,000), saving 15 points and conserving Rs. 10,000 budget!
    """
    res = optimize_interventions("flood", 25000)
    assert res["selected_intervention_ids"] == ["water"]
    assert res["disruption_reduction"] == 15
    assert res["total_cost"] == 15000
    assert res["remaining_budget"] == 10000


def test_optimizer_full_budget_solves_flood():
    """With default budget = Rs. 50,000, Substation Barrier (30k) + Water Pump Backup (15k) saves 100%."""
    res = optimize_interventions("flood", 50000)
    assert set(res["selected_intervention_ids"]) == {"substation", "water"}
    assert res["total_cost"] == 45000
    assert res["remaining_budget"] == 5000
    assert res["optimized_disruption"] == 0
    assert res["disruption_reduction"] == 78


# =====================================================
# REST API ENDPOINT TESTS
# =====================================================

def test_api_infrastructure():
    client = app.test_client()
    res = client.get("/api/infrastructure")
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_assets"] == 10
    names = {a["name"] for a in data["assets"]}
    assert "Power Substation" in names
    assert "Hospital" in names
    assert "Relief Shelter" in names
    assert "Fire Station" in names


def test_api_scenarios():
    client = app.test_client()
    res = client.get("/api/scenarios")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["scenarios"]) == 3


def test_api_interventions():
    client = app.test_client()
    res = client.get("/api/interventions")
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["interventions"]) == 6


def test_api_simulate_success():
    client = app.test_client()
    res = client.post("/api/simulate", json={"scenario": "power", "interventions": []})
    assert res.status_code == 200
    data = res.get_json()
    assert data["weighted_disruption"] == 78
    assert data["failed_count"] == 10


def test_api_simulate_with_interventions():
    client = app.test_client()
    res = client.post("/api/simulate", json={"scenario": "power", "interventions": ["substation"]})
    assert res.status_code == 200
    data = res.get_json()
    assert data["weighted_disruption"] == 0


def test_api_simulate_invalid():
    client = app.test_client()
    res = client.post("/api/simulate", json={"scenario": "earthquake"})
    assert res.status_code == 400


def test_api_optimize_success():
    client = app.test_client()
    res = client.post("/api/optimize", json={"scenario": "power", "budget": 50000})
    assert res.status_code == 200
    data = res.get_json()
    assert data["total_cost"] == 30000
    assert data["remaining_budget"] == 20000
    assert data["optimized_disruption"] == 0
    assert data["disruption_reduction"] == 78


def test_api_optimize_invalid_budget():
    client = app.test_client()
    res = client.post("/api/optimize", json={"scenario": "flood", "budget": -100})
    assert res.status_code == 400


def test_static_files_served():
    client = app.test_client()
    r_index = client.get("/")
    assert r_index.status_code == 200
    assert b"AFTERSHOCK" in r_index.data

    r_js = client.get("/script.js")
    assert r_js.status_code == 200
    assert b"runSimulation" in r_js.data

    r_css = client.get("/style.css")
    assert r_css.status_code == 200
    assert b"--bg:" in r_css.data


if __name__ == "__main__":
    print("Running system test suite...")
    test_all_10_civic_assets_exist()
    test_all_6_municipal_interventions_exist()
    test_baseline_disaster_scenarios()
    test_scenario_aliases()
    test_intervention_pathways()
    test_invalid_intervention_raises()
    test_budget_zero_and_insufficient()
    test_budget_is_never_exceeded()
    test_no_false_improvements()
    test_optimizer_smart_tradeoff()
    test_optimizer_full_budget_solves_flood()
    test_api_infrastructure()
    test_api_scenarios()
    test_api_interventions()
    test_api_simulate_success()
    test_api_simulate_with_interventions()
    test_api_simulate_invalid()
    test_api_optimize_success()
    test_api_optimize_invalid_budget()
    test_static_files_served()
    print("All 20 system tests passed successfully!")
