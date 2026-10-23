"""
AFTERSHOCK AI — Critical Infrastructure Disaster Resilience Backend
Flask API & Application Server

Serves the offline dashboard and provides RESTful endpoints for
cascading failure simulation and budget-constrained intervention optimization.
"""

import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from backend.simulation import (
    ASSETS,
    SCENARIOS,
    INTERVENTIONS,
    simulate_disaster,
    resolve_scenario,
)
from optimize.optimizer import optimize_interventions

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


# =====================================================
# STATIC ASSET & DASHBOARD ROUTES
# =====================================================

@app.get("/")
def home():
    """Serve the single-page dashboard."""
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/<path:filename>")
def serve_static(filename):
    """Serve CSS, JS, and client assets."""
    return send_from_directory(BASE_DIR, filename)


# =====================================================
# REST API ENDPOINTS
# =====================================================

@app.get("/api/infrastructure")
def get_infrastructure():
    """Return the dependency graph of all critical infrastructure assets."""
    return jsonify({
        "status": "success",
        "total_assets": len(ASSETS),
        "assets": ASSETS,
    })


@app.get("/api/scenarios")
def get_scenarios():
    """Return available disaster hazard scenarios."""
    return jsonify({
        "status": "success",
        "scenarios": list(SCENARIOS.values()),
    })


@app.get("/api/interventions")
def get_interventions():
    """Return catalog of available infrastructure resilience interventions and costs."""
    return jsonify({
        "status": "success",
        "interventions": INTERVENTIONS,
    })


@app.post("/api/simulate")
def run_simulation():
    """
    Run the cascading disaster simulation.

    JSON Payload
    ------------
    scenario : str, optional (default "flood")
    interventions : list of str, optional (default [])
    """
    data = request.get_json(silent=True) or {}
    scenario = data.get("scenario", "flood")
    interventions = data.get("interventions", [])

    if (
        not isinstance(interventions, list)
        or not all(isinstance(item, str) for item in interventions)
    ):
        return jsonify({
            "error": "'interventions' must be a list of intervention ID strings."
        }), 400

    try:
        result = simulate_disaster(scenario=scenario, interventions=interventions)
        return jsonify(result), 200
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": f"Internal simulation error: {str(error)}"}), 500


@app.post("/api/optimize")
def run_optimizer():
    """
    Find the optimal set of interventions under budget.

    JSON Payload
    ------------
    scenario : str, optional (default "flood")
    budget : int or float, optional (default 1000000)
    """
    data = request.get_json(silent=True) or {}
    scenario = data.get("scenario", "flood")
    budget = data.get("budget", 50000)

    try:
        # Cast numeric budget if passed as string
        if isinstance(budget, str):
            budget = float(budget)

        result = optimize_interventions(scenario=scenario, budget=budget)
        return jsonify(result), 200
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": f"Internal optimization error: {str(error)}"}), 500


if __name__ == "__main__":
    print("==================================================")
    print("               AFTERSHOCK AI SERVER               ")
    print("==================================================")
    print("Dashboard: http://127.0.0.1:5000/")
    print("API endpoints: /api/infrastructure, /api/scenarios,")
    print("               /api/interventions, /api/simulate,")
    print("               /api/optimize")
    print("==================================================")
    app.run(debug=True, host="127.0.0.1", port=5000)
