"""
AFTERSHOCK AI — Cascading Infrastructure Failure Simulation Engine
Module: simulator.py

This module implements a deterministic, graph-based cascading failure simulation
for interconnected municipal infrastructure assets.

Algorithm:
----------
1. Load and validate network nodes (assets), directed dependency edges, and hazard scenarios.
2. Initialize the failure queue with initial hazard shocks defined by the scenario,
   skipping assets that have hazard-specific physical defenses.
3. Propagate failures step-by-step using Breadth-First Search (BFS) / Queue traversal:
   - For every asset whose prerequisites fail, evaluate if an active backup intervention
     protects the asset against that failure mode.
   - If not protected, transition asset state to 'failed' and enqueue its dependents.
4. Prevent cycles and infinite loops by maintaining a visited/failed set.
5. Compute the deterministic Disruption Score:
   disruption_score = sum(criticality of all failed assets)
"""

import json
import os
from copy import deepcopy

# Base directory for relative file resolution
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_FILE_PATH = os.path.join(BASE_DIR, "data", "infrastructure.json")
CITIES_FILE_PATH = os.path.join(BASE_DIR, "data", "cities.json")


def get_available_cities():
    """
    Return available city configuration profiles for multi-city extensibility.
    """
    if os.path.exists(CITIES_FILE_PATH):
        try:
            with open(CITIES_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "active_city": "mangaluru",
        "cities": [
            {
                "id": "mangaluru",
                "name": "Mangaluru (Mangalore)",
                "state": "Karnataka",
                "country": "India",
                "status": "active",
                "description": "Coastal port city vulnerable to Southwest monsoon flooding and cyclone storm surges along Netravati and Gurupura rivers."
            }
        ]
    }


def load_infrastructure_data(filepath=None):
    """
    Load and strictly validate infrastructure data from the JSON storage file.

    Raises:
        FileNotFoundError: If the data file does not exist.
        ValueError: If JSON syntax is invalid or schema constraints are violated.
    """
    target_path = filepath or DATA_FILE_PATH
    if not os.path.exists(target_path):
        raise FileNotFoundError(f"Infrastructure data file not found at: {target_path}")

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Corrupt JSON format in {target_path}: {exc}") from exc

    # Validate essential top-level keys
    required_keys = {"assets", "dependencies", "scenarios", "interventions"}
    missing = required_keys - set(data.keys())
    if missing:
        raise ValueError(f"Missing required top-level keys in infrastructure data: {missing}")

    # Validate assets
    asset_ids = set()
    for asset in data["assets"]:
        for field in ("id", "name", "category", "criticality", "depends_on"):
            if field not in asset:
                raise ValueError(f"Asset missing required field '{field}': {asset}")
        aid = asset["id"]
        if aid in asset_ids:
            raise ValueError(f"Duplicate asset ID '{aid}' detected in infrastructure data.")
        asset_ids.add(aid)

        if not isinstance(asset["criticality"], (int, float)) or asset["criticality"] < 0:
            raise ValueError(f"Asset '{aid}' has invalid criticality: {asset['criticality']}")

    # Validate dependencies point to existing assets
    for dep in data["dependencies"]:
        for field in ("source", "target"):
            if field not in dep:
                raise ValueError(f"Dependency missing '{field}': {dep}")
        if dep["source"] not in asset_ids:
            raise ValueError(f"Dependency source '{dep['source']}' does not exist in assets.")
        if dep["target"] not in asset_ids:
            raise ValueError(f"Dependency target '{dep['target']}' does not exist in assets.")

    # Validate scenario references
    for scen in data["scenarios"]:
        for field in ("id", "name", "initial_failures"):
            if field not in scen:
                raise ValueError(f"Scenario missing required field '{field}': {scen}")
        for init_f in scen["initial_failures"]:
            if init_f not in asset_ids:
                raise ValueError(f"Scenario '{scen['id']}' initial failure '{init_f}' is unknown.")

    # Validate interventions
    for item in data["interventions"]:
        for field in ("id", "name", "cost", "asset_id"):
            if field not in item:
                raise ValueError(f"Intervention missing required field '{field}': {item}")
        if item["asset_id"] not in asset_ids:
            raise ValueError(f"Intervention '{item['id']}' references unknown asset '{item['asset_id']}'.")
        if not isinstance(item["cost"], (int, float)) or item["cost"] < 0:
            raise ValueError(f"Intervention '{item['id']}' has invalid cost: {item['cost']}")

    return data


# Load authoritative data once at module import
_DATA = load_infrastructure_data()
ASSETS = _DATA["assets"]
DEPENDENCIES = _DATA["dependencies"]
SCENARIOS = {s["id"]: s for s in _DATA["scenarios"]}
INTERVENTIONS = _DATA["interventions"]

# Canonical alias mapping for robust scenario resolution
SCENARIO_ALIASES = {
    "flood": "flood",
    "flooding": "flood",
    "power": "power_outage",
    "power_grid": "power_outage",
    "power_grid_failure": "power_outage",
    "power_outage": "power_outage",
    "communication": "communication_failure",
    "communication_failure": "communication_failure",
    "telecom": "communication_failure",
}


def get_all_assets():
    """Return all configured infrastructure assets."""
    return deepcopy(ASSETS)


def get_all_dependencies():
    """Return all directed infrastructure dependencies."""
    return deepcopy(DEPENDENCIES)


def get_all_scenarios():
    """Return list of all configured disaster hazard scenarios."""
    return list(deepcopy(SCENARIOS).values())


def get_all_interventions():
    """Return list of all available protective interventions."""
    return deepcopy(INTERVENTIONS)


def resolve_scenario(scenario_name):
    """
    Normalize and validate scenario name or alias to canonical scenario ID.

    Raises:
        ValueError: If scenario name is not recognized or not a string.
    """
    if not isinstance(scenario_name, str):
        raise ValueError("Scenario name must be a string.")
    cleaned = scenario_name.strip().lower()
    canonical = SCENARIO_ALIASES.get(cleaned, cleaned)
    if canonical not in SCENARIOS:
        valid_options = ", ".join(sorted(SCENARIOS.keys()))
        raise ValueError(f"Unknown scenario '{scenario_name}'. Valid options: {valid_options}")
    return canonical


def simulate_disaster(scenario="flood", protected_assets=None, interventions=None, custom_data=None):
    """
    Simulate initial disaster shocks and cascading failure propagation.

    Parameters:
    -----------
    scenario : str
        Hazard scenario ID ('flood', 'power_outage', 'communication_failure').
    protected_assets : list of str, optional
        List of asset IDs or intervention IDs marked for protection.
    interventions : list of str, optional
        Alternative parameter name for protected_assets for API flexibility.
    custom_data : dict, optional
        Optional custom infrastructure data dictionary (default uses loaded data).

    Returns:
    --------
    dict
        Structured simulation results containing failed assets, operational assets,
        disruption score, timeline of cascade steps, and asset-by-asset status.
    """
    canonical_scenario = resolve_scenario(scenario)
    data = custom_data or _DATA
    scenario_def = next(s for s in data["scenarios"] if s["id"] == canonical_scenario)

    asset_list = deepcopy(data["assets"])
    asset_by_id = {a["id"]: a for a in asset_list}
    intervention_by_id = {item["id"]: item for item in data["interventions"]}
    intervention_by_asset = {item["asset_id"]: item for item in data["interventions"]}

    # Normalize input protection IDs (accepting either argument)
    raw_protections = []
    if protected_assets is not None:
        if not isinstance(protected_assets, (list, tuple, set)):
            raise ValueError("'protected_assets' must be a list of identifiers.")
        raw_protections.extend(protected_assets)
    if interventions is not None:
        if not isinstance(interventions, (list, tuple, set)):
            raise ValueError("'interventions' must be a list of identifiers.")
        raw_protections.extend(interventions)

    # Validate and map protection identifiers
    applied_interventions = set()
    active_protected_assets = set()

    for item in raw_protections:
        if not isinstance(item, str):
            raise ValueError(f"Protection identifier must be a string, got {type(item).__name__}.")
        clean_id = item.strip()
        if clean_id in intervention_by_id:
            applied_interventions.add(clean_id)
            active_protected_assets.add(intervention_by_id[clean_id]["asset_id"])
        elif clean_id in asset_by_id:
            active_protected_assets.add(clean_id)
            # Link to intervention ID if matching asset has an intervention
            if clean_id in intervention_by_asset:
                applied_interventions.add(intervention_by_asset[clean_id]["id"])
        else:
            valid_ids = sorted(list(intervention_by_id.keys()) + list(asset_by_id.keys()))
            raise ValueError(f"Unknown intervention or asset ID '{item}'. Valid options: {valid_ids}")

    # Build directed dependency graph: source -> list of dependent targets
    # (e.g. substation -> [water, tower, hospital, emergency, treatment])
    dependents_of = {aid: [] for aid in asset_by_id}
    dependencies_of = {aid: [] for aid in asset_by_id}

    for dep in data["dependencies"]:
        src = dep["source"]
        tgt = dep["target"]
        if tgt not in dependents_of[src]:
            dependents_of[src].append(tgt)
        if src not in dependencies_of[tgt]:
            dependencies_of[tgt].append(src)

    # -------------------------------------------------------------
    # Step 0: Identify Initial Disaster Failures
    # -------------------------------------------------------------
    initial_hazard_assets = scenario_def["initial_failures"]
    initial_failed = []
    safeguarded_from_shock = []

    for aid in initial_hazard_assets:
        # Check if intervention protects against this initial hazard shock
        is_shielded = False
        if aid in active_protected_assets:
            # Check intervention applicability
            int_info = intervention_by_asset.get(aid)
            if int_info:
                app_hazard = int_info.get("applicable_hazard", "all")
                if app_hazard in ("all", canonical_scenario):
                    is_shielded = True
                elif canonical_scenario == "power_outage" and app_hazard == "power_loss":
                    is_shielded = True
            else:
                is_shielded = True

        if is_shielded:
            safeguarded_from_shock.append(aid)
        else:
            initial_failed.append(aid)

    failed = set(initial_failed)
    timeline = []
    rounds = []

    # Record Round 0 events
    round_0_events = []
    for aid in initial_failed:
        name = asset_by_id[aid]["name"]
        event = {
            "step": 0,
            "round": 0,
            "asset_id": aid,
            "asset_name": name,
            "title": f"Initial Hazard Shock: {name}",
            "description": f"Directly disrupted by initiating hazard '{scenario_def['name']}'.",
            "rule": "Initiating disaster condition breached primary operational threshold.",
        }
        round_0_events.append(event)
        timeline.append(event)

    rounds.append({
        "round": 0,
        "step_name": "Direct Disaster Impact",
        "failed_assets": sorted(initial_failed),
        "events": round_0_events,
    })

    # -------------------------------------------------------------
    # Breadth-First Cascade Propagation
    # -------------------------------------------------------------
    round_num = 1
    queue = list(initial_failed)
    visited_for_propagation = set(initial_failed)

    while queue:
        current_layer = list(queue)
        queue = []
        newly_failed_in_round = []
        round_events = []

        # Find all unfailed candidates that depend on currently failed assets
        candidates_to_check = set()
        for f_aid in current_layer:
            for dep_target in dependents_of.get(f_aid, []):
                if dep_target not in failed and dep_target not in visited_for_propagation:
                    candidates_to_check.add(dep_target)

        for tgt in candidates_to_check:
            # Determine which prerequisites of tgt are failed
            lost_dependencies = [src for src in dependencies_of[tgt] if src in failed]
            if not lost_dependencies:
                continue

            # Check if tgt is protected by an active backup intervention
            is_protected = False
            protection_reason = ""

            if tgt in active_protected_assets:
                int_def = intervention_by_asset.get(tgt)
                prot_type = int_def.get("protection_type", "dependency_backup") if int_def else "dependency_backup"

                # Hospital specific resilience rule:
                # Hospital backup power & water protects against electrical and water loss,
                # BUT if road is blocked, ambulances cannot reach the hospital!
                if tgt == "hospital":
                    lost_road = "road" in lost_dependencies
                    lost_utilities = any(u in lost_dependencies for u in ("substation", "water", "tower"))
                    if lost_road and "INT-ROD" not in applied_interventions and "road" not in active_protected_assets:
                        is_protected = False
                        protection_reason = "Hospital backup generator is active, but ambulance ingress is severed due to road washout."
                    else:
                        is_protected = True
                        protection_reason = "Hospital emergency microgrid & water reserves maintain life-support operations."
                elif prot_type in ("dependency_backup", "hazard_defense_and_backup"):
                    is_protected = True
                    protection_reason = f"{int_def['name']} provides redundant operational continuity."

            if not is_protected:
                failed.add(tgt)
                visited_for_propagation.add(tgt)
                newly_failed_in_round.append(tgt)
                queue.append(tgt)

                lost_names = [asset_by_id[src]["name"] for src in lost_dependencies]
                event = {
                    "step": round_num,
                    "round": round_num,
                    "asset_id": tgt,
                    "asset_name": asset_by_id[tgt]["name"],
                    "title": f"Cascading Failure: {asset_by_id[tgt]['name']}",
                    "description": f"Lost essential dependencies: {', '.join(lost_names)}.",
                    "rule": f"Predefined directed dependency ({' & '.join(lost_dependencies)} -> {tgt}) triggered cascade.",
                }
                round_events.append(event)
                timeline.append(event)

        if newly_failed_in_round:
            rounds.append({
                "round": round_num,
                "step_name": f"Cascade Wave {round_num}",
                "failed_assets": sorted(newly_failed_in_round),
                "events": round_events,
            })
            round_num += 1

    # -------------------------------------------------------------
    # Metrics Calculation
    # -------------------------------------------------------------
    # Disruption score = sum of criticality of all failed assets
    disruption_score = sum(asset_by_id[aid]["criticality"] for aid in failed)

    operational_assets = [aid for aid in asset_by_id if aid not in failed]
    effectively_protected = [aid for aid in active_protected_assets if aid not in failed]

    # Detailed asset status list
    asset_status_list = []
    affected_categories = set()

    for asset in asset_list:
        aid = asset["id"]
        is_f = aid in failed
        if is_f:
            status = "failed"
            affected_categories.add(asset["category"])
        elif aid in effectively_protected:
            status = "protected"
        else:
            status = "operational"

        asset_status_list.append({
            "id": aid,
            "name": asset["name"],
            "category": asset["category"],
            "service": asset.get("service", asset["category"]),
            "icon": asset.get("icon", "🏢"),
            "criticality": asset["criticality"],
            "exposure_score": asset.get("exposure_score", 5.0),
            "depends_on": asset.get("depends_on", []),
            "status": status,
            "backup_protection": asset.get("backup_protection", "Standard"),
        })

    return {
        "scenario": canonical_scenario,
        "scenario_name": scenario_def["name"],
        "scenario_description": scenario_def["description"],
        "hazard_type": scenario_def.get("hazard_type", canonical_scenario),
        "initial_failures": initial_failed,
        "failed_assets": sorted(failed),
        "failed_count": len(failed),
        "operational_assets": sorted(operational_assets),
        "operational_count": len(operational_assets),
        "protected_assets": sorted(effectively_protected),
        "protected_count": len(effectively_protected),
        "total_assets": len(asset_list),
        "disruption_score": disruption_score,
        "affected_services": sorted(affected_categories),
        "rounds": rounds,
        "timeline": timeline,
        "assets": asset_status_list,
        "applied_interventions": sorted(applied_interventions),
        "disclaimer": "Illustrative educational simulation. Not a validated disaster prediction system.",
    }


if __name__ == "__main__":
    print("Testing Cascading Failure Simulator directly...")
    for sc in ("flood", "power_outage", "communication_failure"):
        res = simulate_disaster(sc)
        print(f"Scenario: {res['scenario_name']}")
        print(f"  Disruption Score: {res['disruption_score']} | Failed: {res['failed_count']}/{res['total_assets']}")
        print(f"  Timeline Steps: {len(res['timeline'])}")

