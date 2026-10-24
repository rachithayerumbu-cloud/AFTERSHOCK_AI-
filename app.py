"""
AFTERSHOCK AI — Critical Infrastructure Disaster Resilience Backend
Flask API & Application Server
Module: app.py

Serves multi-page offline web client and provides RESTful endpoints for:
- Cascading disaster failure simulation
- Budget-constrained resilience intervention optimization
- Synthetic-data machine learning risk classification
"""

import os
import sys
import math
import logging
import socket
from flask import Flask, jsonify, redirect, request, send_from_directory
from werkzeug.serving import make_server

from simulator import (
    simulate_disaster,
    get_all_assets,
    get_all_dependencies,
    get_all_scenarios,
    get_all_interventions,
    get_available_cities,
    load_infrastructure_data,
    resolve_scenario,
    SCENARIOS,
)
from optimizer import optimize_interventions, validate_budget
from risk_model import assess_all_asset_risks

# =====================================================
# STRUCTURED CONSOLE LOGGING CONFIGURATION
# =====================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("aftershock_ai")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")


def create_local_server(host="127.0.0.1", preferred_port=5000, attempts=20):
    """Create a threaded local server, falling back when the requested port is busy."""
    if not 1 <= preferred_port <= 65535:
        raise ValueError("preferred_port must be between 1 and 65535.")
    if attempts < 1:
        raise ValueError("attempts must be at least 1.")

    last_error = None
    for port in range(preferred_port, min(preferred_port + attempts, 65536)):
        reservation = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                reservation.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            reservation.bind((host, port))
        except OSError as exc:
            last_error = exc
            logger.warning(f"Port {port} is unavailable; trying the next local port.")
            reservation.close()
            continue
        reservation.close()

        try:
            return make_server(host, port, app, threaded=True)
        except OSError as exc:
            last_error = exc
            logger.warning(f"Port {port} is unavailable; trying the next local port.")

    raise OSError(
        f"Could not start the server on ports {preferred_port}-"
        f"{min(preferred_port + attempts - 1, 65535)}."
    ) from last_error


@app.before_request
def log_incoming_request():
    """Log incoming API and page requests to the console."""
    if request.path.startswith("/api/"):
        logger.info(f"API Request: {request.method} {request.path}")


# =====================================================
# MULTI-PAGE FRONTEND ROUTES
# =====================================================

@app.get("/")
@app.get("/index.html")
def redirect_home_to_simulation():
    """Send the former Overview URLs to the primary Simulation page."""
    return redirect("/simulation")


@app.get("/simulation")
@app.get("/simulation.html")
def serve_simulation_page():
    """Page 2: Disaster Simulation."""
    return send_from_directory(STATIC_DIR, "simulation.html")


@app.get("/infrastructure")
@app.get("/infrastructure.html")
def serve_infrastructure_page():
    """Page 3: Infrastructure Network."""
    return send_from_directory(STATIC_DIR, "infrastructure.html")


@app.get("/optimizer")
@app.get("/optimizer.html")
def serve_optimizer_page():
    """Page 4: Budget Optimizer."""
    return send_from_directory(STATIC_DIR, "optimizer.html")


@app.get("/risks")
@app.get("/risks.html")
def serve_risks_page():
    """Page 5: AI Risk Analysis."""
    return send_from_directory(STATIC_DIR, "risks.html")


@app.get("/<path:path>")
def serve_static_asset(path):
    """Serve CSS, JS, and client assets."""
    return send_from_directory(STATIC_DIR, path)


# =====================================================
# REST API ENDPOINTS
# =====================================================

@app.get("/api/status")
def get_status():
    """
    Health check endpoint indicating server status, demonstration mode,
    target city (Mangaluru), and offline operating capability.
    """
    return jsonify({
        "status": "online",
        "project": "AFTERSHOCK AI",
        "subtitle": "AI-Based Cascading Infrastructure Failure Simulator",
        "target_city": "Mangaluru (Mangalore)",
        "state": "Karnataka",
        "country": "India",
        "demonstration_mode": True,
        "offline_ready": True,
        "version": "2.1.0",
        "server": "Flask Localhost",
        "disclaimer": "Academic demonstration prototype using sample Mangaluru infrastructure references. Not for live emergency operations.",
    }), 200


@app.get("/api/cities")
def get_cities():
    """
    Return available city configuration profiles for multi-city extensibility.
    """
    cities_data = get_available_cities()
    return jsonify({
        "status": "success",
        "active_city": cities_data.get("active_city", "mangaluru"),
        "cities": cities_data.get("cities", []),
    }), 200


@app.get("/api/infrastructure")
def get_infrastructure():
    """
    Return the complete infrastructure network:
    metadata, assets, directed dependency edges, and total asset count.
    """
    try:
        raw_data = load_infrastructure_data()
        logger.info(
            f"[INFRASTRUCTURE] Returning {len(raw_data['assets'])} assets "
            f"and {len(raw_data['dependencies'])} directed dependency edges."
        )
        return jsonify({
            "status": "success",
            "metadata": raw_data.get("metadata", {}),
            "total_assets": len(raw_data["assets"]),
            "assets": raw_data["assets"],
            "dependencies": raw_data["dependencies"],
        }), 200
    except Exception as exc:
        logger.exception(f"[INFRASTRUCTURE] Failed to load data: {exc}")
        return jsonify({"status": "error", "message": f"Failed to load infrastructure data: {exc}"}), 500


@app.get("/api/scenarios")
def get_scenarios():
    """Return all supported disaster hazard scenarios and descriptions."""
    scenarios = get_all_scenarios()
    return jsonify({
        "status": "success",
        "total_scenarios": len(scenarios),
        "scenarios": scenarios,
    }), 200


@app.get("/api/interventions")
def get_interventions():
    """Return catalog of available resilience interventions, costs in INR, and target assets."""
    interventions = get_all_interventions()
    return jsonify({
        "status": "success",
        "currency": "INR",
        "currency_symbol": "₹",
        "total_interventions": len(interventions),
        "interventions": interventions,
    }), 200


@app.get("/api/risks")
def get_risks():
    """
    Return demonstration machine-learning risk classifications for each asset.
    Includes a prominent warning explaining synthetic training data.
    """
    try:
        risk_report = assess_all_asset_risks()
        logger.info(
            f"[AI RISK] Generated Random Forest classifications for {len(risk_report['assets'])} assets "
            f"using synthetic model (seed=42)."
        )
        return jsonify(risk_report), 200
    except Exception as exc:
        logger.exception(f"[AI RISK] Error assessing asset risks: {exc}")
        return jsonify({"status": "error", "message": f"Risk assessment error: {exc}"}), 500


@app.post("/api/simulate")
def run_simulation():
    """
    Execute cascading disaster simulation for the given scenario and optional protection plan.

    Request Payload (JSON):
    -----------------------
    scenario : str (required, e.g. 'flood', 'power_outage', 'communication_failure')
    protected_assets : list of str (optional, asset IDs or intervention IDs)
    interventions : list of str (optional alias for protected_assets)
    """
    if not request.is_json:
        logger.warning("[SIMULATE] Rejected request: Request body must be JSON formatted.")
        return jsonify({
            "status": "error",
            "message": "Request body must be JSON formatted."
        }), 400

    data = request.get_json(silent=True)
    if data is None:
        logger.warning("[SIMULATE] Rejected request: Malformed or empty JSON payload.")
        return jsonify({
            "status": "error",
            "message": "Malformed or empty JSON payload."
        }), 400

    scenario = data.get("scenario")
    if not scenario or not isinstance(scenario, str):
        logger.warning(f"[SIMULATE] Rejected request: Field 'scenario' is required and must be a string, got {scenario!r}")
        return jsonify({
            "status": "error",
            "message": "Field 'scenario' is required and must be a string."
        }), 400

    # Accept both protected_assets and interventions keys for interoperability
    protections = data.get("protected_assets")
    if protections is None:
        protections = data.get("interventions", [])

    if not isinstance(protections, list):
        logger.warning(f"[SIMULATE] Rejected request: 'protected_assets' must be a list, got {type(protections).__name__}")
        return jsonify({
            "status": "error",
            "message": "'protected_assets' or 'interventions' must be a list of strings."
        }), 400

    logger.info(f"[SIMULATE] Starting simulation | Scenario: '{scenario}' | Active Protections: {protections}")

    try:
        result = simulate_disaster(scenario=scenario, protected_assets=protections)

        logger.info(
            f"[SIMULATE] Completed: '{result['scenario_name']}' | "
            f"Failed: {result['failed_count']}/{result['total_assets']} assets | "
            f"Operational: {result['operational_count']} | "
            f"Protected: {result['protected_count']} | "
            f"Disruption Score: {result['disruption_score']}"
        )

        response_payload = {
            "status": "success",
            "simulation": result,
        }
        # Merge top-level result fields for complete compatibility
        response_payload.update(result)
        return jsonify(response_payload), 200

    except ValueError as exc:
        logger.warning(f"[SIMULATE] Validation rejected: {exc}")
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception as exc:
        logger.exception(f"[SIMULATE] Internal simulation failure: {exc}")
        return jsonify({"status": "error", "message": "Internal simulation error occurred."}), 500


@app.post("/api/optimize")
def run_optimizer():
    """
    Evaluate candidate intervention combinations and recommend the optimal plan
    within the specified INR budget.

    Request Payload (JSON):
    -----------------------
    scenario : str (required)
    budget : numeric (required, non-negative, finite number in INR)
    """
    if not request.is_json:
        logger.warning("[OPTIMIZE] Rejected request: Request body must be JSON formatted.")
        return jsonify({
            "status": "error",
            "message": "Request body must be JSON formatted."
        }), 400

    data = request.get_json(silent=True)
    if data is None:
        logger.warning("[OPTIMIZE] Rejected request: Malformed or empty JSON payload.")
        return jsonify({
            "status": "error",
            "message": "Malformed or empty JSON payload."
        }), 400

    scenario = data.get("scenario")
    if not scenario or not isinstance(scenario, str):
        logger.warning(f"[OPTIMIZE] Rejected request: 'scenario' must be string, got {scenario!r}")
        return jsonify({
            "status": "error",
            "message": "Field 'scenario' is required and must be a string."
        }), 400

    if "budget" not in data:
        logger.warning("[OPTIMIZE] Rejected request: Missing required field 'budget'.")
        return jsonify({
            "status": "error",
            "message": "Field 'budget' is required."
        }), 400

    raw_budget = data["budget"]

    # Reject booleans explicitly (bool is a subclass of int in Python)
    if isinstance(raw_budget, bool):
        logger.warning("[OPTIMIZE] Rejected request: Budget cannot be boolean.")
        return jsonify({
            "status": "error",
            "message": "Budget cannot be a boolean value. Provide a numeric amount in INR."
        }), 400

    try:
        budget = validate_budget(raw_budget)
    except ValueError as exc:
        logger.warning(f"[OPTIMIZE] Invalid budget '{raw_budget}': {exc}")
        return jsonify({"status": "error", "message": str(exc)}), 400

    logger.info(f"[OPTIMIZE] Starting knapsack optimization | Scenario: '{scenario}' | Budget: Rs. {budget:,.2f}")

    try:
        opt_result = optimize_interventions(scenario=scenario, budget=budget)

        logger.info(
            f"[OPTIMIZE] Completed: Selected {len(opt_result['selected_interventions'])} interventions "
            f"{opt_result['selected_intervention_ids']} | "
            f"Total Cost: Rs. {opt_result['total_cost']:,.2f} | "
            f"Remaining: Rs. {opt_result['remaining_budget']:,.2f} | "
            f"Disruption: {opt_result['baseline_disruption']} -> {opt_result['optimized_disruption']} "
            f"(Saved {opt_result['disruption_reduction']} pts, {opt_result['disruption_reduction_percent']}%)"
        )

        response_payload = {
            "status": "success",
            "plan": opt_result,
        }
        response_payload.update(opt_result)
        return jsonify(response_payload), 200

    except ValueError as exc:
        logger.warning(f"[OPTIMIZE] Validation error: {exc}")
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception as exc:
        logger.exception(f"[OPTIMIZE] Internal optimizer failure: {exc}")
        return jsonify({"status": "error", "message": "Internal optimization error occurred."}), 500


# =====================================================
# ERROR HANDLERS
# =====================================================

@app.errorhandler(404)
def not_found_handler(err):
    """Return JSON error response for unknown API routes, or overview page for browser navigation."""
    if request.path.startswith("/api/"):
        logger.warning(f"[HTTP 404] Route not found: {request.path}")
        return jsonify({
            "status": "error",
            "message": f"Endpoint '{request.path}' not found."
        }), 404
    return redirect("/simulation")


@app.errorhandler(405)
def method_not_allowed_handler(err):
    logger.warning(f"[HTTP 405] Method '{request.method}' not allowed for {request.path}")
    return jsonify({
        "status": "error",
        "message": f"Method '{request.method}' not allowed for this endpoint."
    }), 405


@app.errorhandler(500)
def server_error_handler(err):
    logger.exception(f"[HTTP 500] Unhandled server error: {err}")
    return jsonify({
        "status": "error",
        "message": "An internal server error occurred."
    }), 500


if __name__ == "__main__":
    try:
        preferred_port = int(os.environ.get("AFTERSHOCK_PORT", "5000"))
        server = create_local_server(preferred_port=preferred_port)
        port = server.server_port
        base_url = f"http://127.0.0.1:{port}"
        logger.info(f"Website: {base_url}/")
        server.serve_forever()
    except Exception as startup_err:
        logger.critical(f"FATAL: Application server failed to start: {startup_err}", exc_info=True)
        sys.exit(1)
    finally:
        if "server" in locals():
            server.server_close()
