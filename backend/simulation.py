"""
AFTERSHOCK AI — Critical Infrastructure Disaster Simulation Engine
Authoritative Simulation Module

Simulates disaster hazards and cascading failure propagation across
the 10 municipal critical infrastructure facilities:
- Power Substation
- Hospital
- Water Pump
- Mobile Tower
- Emergency Centre
- Relief Shelter
- Water Treatment
- Control Centre
- Traffic Signals
- Fire Station
"""

from copy import deepcopy

ASSETS = [
    {
        "id": "substation",
        "name": "Power Substation",
        "type": "Power",
        "service": "Electricity",
        "icon": "⚡",
        "criticality": 10,
        "depends_on": [],
        "requires": [],
    },
    {
        "id": "hospital",
        "name": "Hospital",
        "type": "Healthcare",
        "service": "Healthcare",
        "icon": "🏥",
        "criticality": 10,
        "depends_on": ["substation", "tower"],
        "requires": ["substation", "tower"],
    },
    {
        "id": "water",
        "name": "Water Pump",
        "type": "Water Supply",
        "service": "Water Supply",
        "icon": "💧",
        "criticality": 8,
        "depends_on": ["substation"],
        "requires": ["substation"],
    },
    {
        "id": "tower",
        "name": "Mobile Tower",
        "type": "Communication",
        "service": "Communication",
        "icon": "📡",
        "criticality": 7,
        "depends_on": ["substation"],
        "requires": ["substation"],
    },
    {
        "id": "emergency",
        "name": "Emergency Centre",
        "type": "Emergency Services",
        "service": "Emergency Services",
        "icon": "🚑",
        "criticality": 9,
        "depends_on": ["substation", "tower"],
        "requires": ["substation", "tower"],
    },
    {
        "id": "shelter",
        "name": "Relief Shelter",
        "type": "Public Safety",
        "service": "Public Safety",
        "icon": "🏠",
        "criticality": 7,
        "depends_on": ["water"],
        "requires": ["water"],
    },
    {
        "id": "treatment",
        "name": "Water Treatment",
        "type": "Water Supply",
        "service": "Water Supply",
        "icon": "🚰",
        "criticality": 8,
        "depends_on": ["substation", "water"],
        "requires": ["substation", "water"],
    },
    {
        "id": "data",
        "name": "Control Centre",
        "type": "Digital Services",
        "service": "Digital Services",
        "icon": "🖥️",
        "criticality": 6,
        "depends_on": ["substation", "tower"],
        "requires": ["substation", "tower"],
    },
    {
        "id": "traffic",
        "name": "Traffic Signals",
        "type": "Transport",
        "service": "Transport",
        "icon": "🚦",
        "criticality": 5,
        "depends_on": ["substation"],
        "requires": ["substation"],
    },
    {
        "id": "fire",
        "name": "Fire Station",
        "type": "Emergency Services",
        "service": "Emergency Services",
        "icon": "🚒",
        "criticality": 8,
        "depends_on": ["substation"],
        "requires": ["substation"],
    },
]

DEFAULT_INFRASTRUCTURE = ASSETS

SCENARIOS = {
    "flood": {
        "id": "flood",
        "name": "Flood",
        "description": "Severe flooding inundates electrical substations and water pumping assets.",
        "initial_failures": ["substation", "water"],
    },
    "power": {
        "id": "power",
        "name": "Power Grid Failure",
        "description": "Grid-wide power failure trips the central power substation.",
        "initial_failures": ["substation"],
    },
    "communication": {
        "id": "communication",
        "name": "Communication Failure",
        "description": "Severe storm knocks out the primary mobile communication tower.",
        "initial_failures": ["tower"],
    },
}

SCENARIO_ALIASES = {
    "power_outage": "power",
    "communication_failure": "communication",
}

INTERVENTIONS = [
    {
        "id": "substation",
        "name": "Substation Flood Barrier",
        "description": "Reduces the modeled chance of a flood-triggered substation failure.",
        "cost": 30000,
        "benefit": 10,
        "kind": "protect",
        "asset_id": "substation",
        "target": "substation",
    },
    {
        "id": "hospital",
        "name": "Hospital Backup Power",
        "description": "Keeps the hospital operational during a modeled power outage.",
        "cost": 25000,
        "benefit": 9,
        "kind": "backup",
        "asset_id": "hospital",
        "target": "hospital",
    },
    {
        "id": "water",
        "name": "Water Pump Backup",
        "description": "Provides backup power to the water pumping facility.",
        "cost": 15000,
        "benefit": 8,
        "kind": "backup",
        "asset_id": "water",
        "target": "water",
    },
    {
        "id": "tower",
        "name": "Communication Backup",
        "description": "Maintains the modeled mobile tower during power failure.",
        "cost": 20000,
        "benefit": 7,
        "kind": "backup",
        "asset_id": "tower",
        "target": "tower",
    },
    {
        "id": "emergency",
        "name": "Emergency Centre Backup",
        "description": "Protects the emergency centre against power loss.",
        "cost": 18000,
        "benefit": 7,
        "kind": "backup",
        "asset_id": "emergency",
        "target": "emergency",
    },
    {
        "id": "shelter",
        "name": "Shelter Water Reserve",
        "description": "Provides an alternative modeled water supply to the shelter.",
        "cost": 10000,
        "benefit": 5,
        "kind": "backup",
        "asset_id": "shelter",
        "target": "shelter",
    },
]

# Backward compatibility alias map
ASSET_ALIAS_MAP = {
    "communication": "tower",
    "SUB-01": "substation",
    "SUB-02": "substation",
    "WATER-01": "water",
    "WATER-02": "water",
    "HOSP-01": "hospital",
    "HOSP-02": "hospital",
    "COM-01": "tower",
    "COM-02": "tower",
    "EMG-01": "emergency",
    "EMG-02": "emergency",
}


def resolve_scenario(scenario_name):
    """Normalize scenario name or alias to canonical ID."""
    if not isinstance(scenario_name, str):
        raise ValueError("Scenario name must be a string.")
    cleaned = scenario_name.strip().lower()
    canonical = SCENARIO_ALIASES.get(cleaned, cleaned)
    if canonical not in SCENARIOS:
        valid = ", ".join(list(SCENARIOS.keys()) + list(SCENARIO_ALIASES.keys()))
        raise ValueError(f"Unknown scenario '{scenario_name}'. Valid options: {valid}")
    return canonical


def simulate_disaster(scenario="flood", interventions=None, infrastructure=None):
    """
    Simulates disaster initiation and cascading infrastructure failure propagation.

    Parameters
    ----------
    scenario : str
        Disaster scenario ID ("flood", "power", "communication").
    interventions : list of str, optional
        List of intervention IDs (or asset IDs) applied before the disaster.
    infrastructure : list of dict, optional
        Custom infrastructure asset definitions. Defaults to ASSETS.

    Returns
    -------
    dict
        Detailed simulation results including failure chain, disruption score,
        and individual asset operational states.
    """
    scenario_id = resolve_scenario(scenario)
    scenario_def = SCENARIOS[scenario_id]

    asset_list = (
        deepcopy(infrastructure)
        if infrastructure is not None
        else deepcopy(ASSETS)
    )
    asset_by_id = {asset["id"]: asset for asset in asset_list}

    interventions = interventions or []
    if not isinstance(interventions, (list, set, tuple)):
        raise ValueError("Interventions must be a list of intervention IDs.")

    intervention_map = {item["id"]: item for item in INTERVENTIONS}

    protected_assets = set()
    backed_up_assets = set()
    applied_intervention_ids = []

    for item in interventions:
        if not isinstance(item, str):
            raise ValueError(f"Intervention identifier must be a string, got {type(item)}.")

        # Resolve intervention by ID
        if item in intervention_map:
            applied_intervention_ids.append(item)
            rule = intervention_map[item]
            target_id = rule.get("target") or rule.get("asset_id")
            if rule["kind"] == "protect":
                protected_assets.add(target_id)
            elif rule["kind"] == "backup":
                backed_up_assets.add(target_id)
        elif item in asset_by_id:
            # Direct asset ID passed
            applied_intervention_ids.append(item)
            protected_assets.add(item)
        else:
            # Check alias map
            mapped = ASSET_ALIAS_MAP.get(item)
            if mapped and mapped in asset_by_id:
                applied_intervention_ids.append(item)
                protected_assets.add(mapped)
            else:
                valid_ids = ", ".join(list(intervention_map.keys()) + list(asset_by_id.keys()))
                raise ValueError(f"Unknown intervention or asset ID '{item}'. Valid: {valid_ids}")

    # Initial hazard failures
    initial_hazard_assets = scenario_def["initial_failures"]
    initial_failures = [
        asset_id
        for asset_id in initial_hazard_assets
        if asset_id not in protected_assets and asset_id not in backed_up_assets
    ]

    failed = set(initial_failures)
    rounds = []
    timeline = []

    # Round 0: Initiating disaster shock
    round_0_events = []
    for asset_id in initial_failures:
        asset_name = asset_by_id[asset_id]["name"]
        event = {
            "step": 0,
            "asset_id": asset_id,
            "title": f"Initial shock: {asset_name}",
            "description": f"Directly disrupted by initiating hazard: {scenario_def['name']}.",
        }
        round_0_events.append(event)
        timeline.append(event)

    rounds.append({
        "round": 0,
        "failed_assets": sorted(initial_failures),
        "events": round_0_events,
    })

    # Cascade propagation rounds
    changed = True
    round_number = 1

    while changed:
        changed = False
        newly_failed = []
        round_events = []

        for asset in asset_list:
            asset_id = asset["id"]

            if (
                asset_id in failed
                or asset_id in protected_assets
                or asset_id in backed_up_assets
            ):
                continue

            deps = asset.get("depends_on") or asset.get("requires") or []
            # Normalize dependency aliases
            normalized_deps = [ASSET_ALIAS_MAP.get(d, d) for d in deps]
            failed_deps = [dep for dep in normalized_deps if dep in failed]

            if failed_deps:
                failed.add(asset_id)
                newly_failed.append(asset_id)
                changed = True

                dep_names = [
                    asset_by_id.get(d, {}).get("name", d)
                    for d in failed_deps
                ]
                event = {
                    "step": round_number,
                    "asset_id": asset_id,
                    "title": f"Cascade failure: {asset['name']}",
                    "description": f"Lost essential dependency ({', '.join(dep_names)}).",
                }
                round_events.append(event)
                timeline.append(event)

        if newly_failed:
            rounds.append({
                "round": round_number,
                "failed_assets": sorted(newly_failed),
                "events": round_events,
            })
            round_number += 1

    # Compile asset-by-asset status and disruption metrics
    asset_results = []
    affected_services = set()
    weighted_disruption = 0

    for asset in asset_list:
        asset_id = asset["id"]
        is_failed = asset_id in failed

        if is_failed:
            status = "failed"
            weighted_disruption += asset["criticality"]
            affected_services.add(asset.get("service") or asset.get("type", "General"))
        elif asset_id in protected_assets:
            status = "protected"
        elif asset_id in backed_up_assets:
            status = "backed_up"
        else:
            status = "operational"

        asset_results.append({
            "id": asset_id,
            "name": asset["name"],
            "type": asset.get("type", "infrastructure"),
            "service": asset.get("service", "General"),
            "icon": asset.get("icon", "🏢"),
            "criticality": asset["criticality"],
            "depends_on": asset.get("depends_on", []),
            "status": status,
        })

    operational_assets = [
        asset["id"] for asset in asset_list if asset["id"] not in failed
    ]

    return {
        "scenario": scenario_id,
        "scenario_name": scenario_def["name"],
        "scenario_description": scenario_def["description"],
        "initial_failures": initial_failures,
        "failed_count": len(failed),
        "failed_assets": sorted(failed),
        "operational_count": len(operational_assets),
        "operational_assets": sorted(operational_assets),
        "weighted_disruption": weighted_disruption,
        "affected_services": sorted(affected_services),
        "total_assets": len(asset_list),
        "rounds": rounds,
        "timeline": timeline,
        "failure_chain": [
            {"asset_id": t["asset_id"], "reason": t["description"]}
            for t in timeline
        ],
        "assets": asset_results,
        "interventions_applied": applied_intervention_ids,
        "protected_assets": sorted(protected_assets),
        "backed_up_assets": sorted(backed_up_assets),
        "note": "Deterministic dependency-based cascading failure simulation.",
    }


if __name__ == "__main__":
    for s in ["flood", "power", "communication"]:
        res = simulate_disaster(s)
        print(f"Scenario: {res['scenario_name']} | Failed count: {res['failed_count']} | Disruption: {res['weighted_disruption']}")
