from flask import Flask, jsonify, request
from flask_cors import CORS
from itertools import combinations
import math

app = Flask(__name__)
CORS(app)

# Demonstration data only. Costs and criticality scores are illustrative,
# not validated real-world infrastructure estimates.
ASSETS = [
    {"id": "SUB-01", "name": "Substation A", "type": "power", "criticality": 8, "depends_on": []},
    {"id": "SUB-02", "name": "Substation B", "type": "power", "criticality": 7, "depends_on": []},
    {"id": "WATER-01", "name": "Water Pump A", "type": "water", "criticality": 8, "depends_on": ["SUB-01"]},
    {"id": "WATER-02", "name": "Water Pump B", "type": "water", "criticality": 7, "depends_on": ["SUB-02"]},
    {"id": "HOSP-01", "name": "City Hospital", "type": "healthcare", "criticality": 10, "depends_on": ["SUB-01"]},
    {"id": "HOSP-02", "name": "Emergency Hospital", "type": "healthcare", "criticality": 10, "depends_on": ["SUB-02"]},
    {"id": "COM-01", "name": "Communication Tower A", "type": "communications", "criticality": 6, "depends_on": ["SUB-01"]},
    {"id": "COM-02", "name": "Communication Tower B", "type": "communications", "criticality": 6, "depends_on": ["SUB-02"]},
    {"id": "EMG-01", "name": "Emergency Centre A", "type": "emergency", "criticality": 9, "depends_on": ["COM-01", "SUB-01"]},
    {"id": "EMG-02", "name": "Emergency Centre B", "type": "emergency", "criticality": 9, "depends_on": ["COM-02", "SUB-02"]},
]

INTERVENTIONS = [
    {"id": "PROTECT-SUB-01", "name": "Protect Substation A", "cost": 500000, "kind": "protect", "asset_id": "SUB-01"},
    {"id": "BACKUP-WATER-01", "name": "Backup Power: Water Pump A", "cost": 200000, "kind": "backup", "asset_id": "WATER-01"},
    {"id": "BACKUP-HOSP-01", "name": "Backup Power: City Hospital", "cost": 300000, "kind": "backup", "asset_id": "HOSP-01"},
    {"id": "PROTECT-SUB-02", "name": "Protect Substation B", "cost": 400000, "kind": "protect", "asset_id": "SUB-02"},
    {"id": "BACKUP-WATER-02", "name": "Backup Power: Water Pump B", "cost": 200000, "kind": "backup", "asset_id": "WATER-02"},
    {"id": "BACKUP-HOSP-02", "name": "Backup Power: Emergency Hospital", "cost": 300000, "kind": "backup", "asset_id": "HOSP-02"},
]

SCENARIOS = {
    "flood": {"name": "Flood", "initial_failures": ["SUB-01"]},
    "power_outage": {"name": "Power outage", "initial_failures": ["SUB-01", "SUB-02"]},
    "communication_failure": {"name": "Communication failure", "initial_failures": ["COM-01"]},
}


def simulate_disaster(scenario, intervention_ids=None):
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario '{scenario}'. Choose one of: {', '.join(SCENARIOS)}")

    intervention_ids = intervention_ids or []
    known_interventions = {item["id"]: item for item in INTERVENTIONS}
    unknown = [item for item in intervention_ids if item not in known_interventions]
    if unknown:
        raise ValueError(f"Unknown intervention ID(s): {', '.join(unknown)}")

    chosen = [known_interventions[item] for item in intervention_ids]
    protected = {item["asset_id"] for item in chosen if item["kind"] == "protect"}
    backed_up = {item["asset_id"] for item in chosen if item["kind"] == "backup"}

    failed = set(SCENARIOS[scenario]["initial_failures"]) - protected
    rounds = [{"round": 0, "failed_assets": sorted(failed)}]

    changed = True
    round_number = 1
    while changed:
        changed = False
        newly_failed = set()
        for asset in ASSETS:
            asset_id = asset["id"]
            if asset_id in failed or asset_id in backed_up:
                continue
            if any(dependency in failed for dependency in asset["depends_on"]):
                newly_failed.add(asset_id)
        if newly_failed:
            failed.update(newly_failed)
            rounds.append({"round": round_number, "failed_assets": sorted(newly_failed)})
            round_number += 1
            changed = True

    asset_results = []
    weighted_disruption = 0
    for asset in ASSETS:
        is_failed = asset["id"] in failed
        if is_failed:
            weighted_disruption += asset["criticality"]
        asset_results.append({
            **asset,
            "status": "failed" if is_failed else "operational",
        })

    return {
        "scenario": scenario,
        "scenario_name": SCENARIOS[scenario]["name"],
        "failed_count": len(failed),
        "failed_assets": sorted(failed),
        "weighted_disruption": weighted_disruption,
        "rounds": rounds,
        "assets": asset_results,
        "interventions_applied": intervention_ids,
        "note": "Illustrative rule-based simulation for a prototype; not a real-world prediction.",
    }


def optimize_interventions(scenario, budget):
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario '{scenario}'. Choose one of: {', '.join(SCENARIOS)}")
    if isinstance(budget, bool) or not isinstance(budget, (int, float)) or not math.isfinite(budget) or budget < 0:
        raise ValueError("Budget must be a finite, non-negative number.")

    baseline = simulate_disaster(scenario, [])
    best = None
    count = len(INTERVENTIONS)

    # Small demo set: check every possible combination (2^6 = 64).
    for mask in range(1 << count):
        selected = [INTERVENTIONS[i] for i in range(count) if mask & (1 << i)]
        total_cost = sum(item["cost"] for item in selected)
        if total_cost > budget:
            continue
        result = simulate_disaster(scenario, [item["id"] for item in selected])
        score = (result["weighted_disruption"], total_cost, len(selected))
        if best is None or score < best["score"]:
            best = {
                "score": score,
                "selected": selected,
                "total_cost": total_cost,
                "result": result,
            }

    # Empty selection always fits a valid non-negative budget.
    selected_ids = [item["id"] for item in best["selected"]]
    optimized = best["result"]
    baseline_disruption = baseline["weighted_disruption"]
    optimized_disruption = optimized["weighted_disruption"]
    reduction = baseline_disruption - optimized_disruption
    reduction_percent = (100 * reduction / baseline_disruption) if baseline_disruption else 0

    return {
        "scenario": scenario,
        "budget": budget,
        "selected_interventions": best["selected"],
        "selected_intervention_ids": selected_ids,
        "total_cost": best["total_cost"],
        "remaining_budget": budget - best["total_cost"],
        "baseline_disruption": baseline_disruption,
        "optimized_disruption": optimized_disruption,
        "disruption_reduction": reduction,
        "disruption_reduction_percent": round(reduction_percent, 2),
        "baseline": baseline,
        "optimized": optimized,
        "note": "Optimization uses illustrative costs and a small exhaustive search; not operational advice.",
    }


@app.get("/")
def home():
    return jsonify({
        "status": "online",
        "project": "AFTERSHOCK AI",
        "message": "Budget-aware cascading failure prevention prototype API",
        "endpoints": [
            "GET /api/infrastructure",
            "GET /api/scenarios",
            "GET /api/interventions",
            "POST /api/simulate",
            "POST /api/optimize",
        ],
    })


@app.get("/api/infrastructure")
def get_infrastructure():
    return jsonify({"assets": ASSETS})


@app.get("/api/scenarios")
def get_scenarios():
    return jsonify({"scenarios": [
        {"id": key, **value} for key, value in SCENARIOS.items()
    ]})


@app.get("/api/interventions")
def get_interventions():
    return jsonify({"interventions": INTERVENTIONS})


@app.post("/api/simulate")
def run_simulation():
    data = request.get_json(silent=True) or {}
    scenario = data.get("scenario", "flood")
    interventions = data.get("interventions", [])
    if not isinstance(interventions, list) or not all(isinstance(item, str) for item in interventions):
        return jsonify({"error": "'interventions' must be a list of intervention ID strings."}), 400
    try:
        return jsonify(simulate_disaster(scenario, interventions))
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


@app.post("/api/optimize")
def run_optimizer():
    data = request.get_json(silent=True) or {}
    scenario = data.get("scenario", "flood")
    budget = data.get("budget", 1000000)
    try:
        result = optimize_interventions(scenario, budget)
        return jsonify(result)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400


if __name__ == "__main__":
    print("Starting AFTERSHOCK AI API...")
    print("Open http://127.0.0.1:5000 in your browser.")
    app.run(debug=True, host="127.0.0.1", port=5000)
