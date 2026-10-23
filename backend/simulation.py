
"""
AFTERSHOCK AI
Simple cascading disaster simulation.

This is a demonstration model, not a real-world
disaster prediction system.
"""

DEFAULT_INFRASTRUCTURE = [
    {
        "id": "SUB-01",
        "name": "Electricity Substation",
        "requires": [],
        "service": "Electricity",
        "criticality": 5,
    },
    {
        "id": "PUMP-01",
        "name": "Water Pump",
        "requires": ["SUB-01"],
        "service": "Water",
        "criticality": 5,
    },
    {
        "id": "WATER-01",
        "name": "Water Treatment Plant",
        "requires": ["PUMP-01"],
        "service": "Water",
        "criticality": 4,
    },
    {
        "id": "HOSP-01",
        "name": "Hospital",
        "requires": ["SUB-01", "WATER-01"],
        "service": "Healthcare",
        "criticality": 5,
    },
    {
        "id": "SCHOOL-01",
        "name": "School",
        "requires": ["SUB-01"],
        "service": "Education",
        "criticality": 2,
    },
    {
        "id": "SUB-02",
        "name": "Backup Area Substation",
        "requires": [],
        "service": "Electricity",
        "criticality": 4,
    },
    {
        "id": "HOSP-02",
        "name": "Second Hospital",
        "requires": ["SUB-02"],
        "service": "Healthcare",
        "criticality": 5,
    },
    {
        "id": "COMM-01",
        "name": "Communication Tower",
        "requires": ["SUB-02"],
        "service": "Communication",
        "criticality": 3,
    },
    {
        "id": "EMER-01",
        "name": "Emergency Centre",
        "requires": ["COMM-01"],
        "service": "Emergency Response",
        "criticality": 5,
    },
    {
        "id": "SHELTER-01",
        "name": "Emergency Shelter",
        "requires": ["SUB-02"],
        "service": "Emergency Shelter",
        "criticality": 4,
    },
]

SCENARIOS = {
    "flood": ["SUB-01"],
    "power_outage": ["SUB-02"],
    "communication_failure": ["COMM-01"],
}


def simulate_disaster(
    scenario="flood",
    infrastructure=None,
    interventions=None,
):
    """Simulate initial failures and cascading failures."""

    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")

    assets = (
        DEFAULT_INFRASTRUCTURE
        if infrastructure is None
        else infrastructure
    )
    protected = set(interventions or [])
    assets = [dict(asset) for asset in assets]
    asset_ids = {asset["id"] for asset in assets}

    if not protected.issubset(asset_ids):
        raise ValueError("An intervention refers to an unknown asset ID.")

    for asset in assets:
        missing = set(asset.get("requires", [])) - asset_ids
        if missing:
            raise ValueError(
                f"{asset['id']} requires unknown assets: {missing}"
            )

    initial_failures = [
        asset_id
        for asset_id in SCENARIOS[scenario]
        if asset_id not in protected
    ]

    failed = set(initial_failures)
    failure_chain = [
        {
            "asset_id": asset_id,
            "reason": f"Initial failure: {scenario}",
        }
        for asset_id in initial_failures
    ]

    # Keep checking dependencies until no new assets fail.
    changed = True
    while changed:
        changed = False

        for asset in assets:
            asset_id = asset["id"]

            if asset_id in failed or asset_id in protected:
                continue

            failed_dependencies = [
                dependency
                for dependency in asset.get("requires", [])
                if dependency in failed
            ]

            if failed_dependencies:
                failed.add(asset_id)
                changed = True
                failure_chain.append({
                    "asset_id": asset_id,
                    "reason": (
                        "Lost dependency: "
                        + ", ".join(failed_dependencies)
                    ),
                })

    asset_results = []
    for asset in assets:
        asset_id = asset["id"]

        if asset_id in failed:
            status = "failed"
        elif asset_id in protected:
            status = "protected"
        else:
            status = "operational"

        asset_results.append({
            "id": asset_id,
            "name": asset["name"],
            "service": asset["service"],
            "criticality": asset["criticality"],
            "status": status,
        })

    failed_assets = sorted(failed)
    affected_services = sorted({
        asset["service"]
        for asset in assets
        if asset["id"] in failed
    })

    weighted_disruption = sum(
        asset["criticality"]
        for asset in assets
        if asset["id"] in failed
    )

    return {
        "scenario": scenario,
        "initial_failures": initial_failures,
        "failed_assets": failed_assets,
        "affected_services": affected_services,
        "asset_results": asset_results,
        "failure_chain": failure_chain,
        "weighted_disruption": weighted_disruption,
        "total_assets": len(assets),
        "failed_count": len(failed_assets),
        "protected_assets": sorted(protected),
    }


if __name__ == "__main__":
    result = simulate_disaster("flood")

    print("\nAFTERSHOCK AI - FLOOD SIMULATION")
    print("=" * 40)
    print("Initial failures:", result["initial_failures"])
    print("Failed assets:", result["failed_assets"])
    print("Affected services:", result["affected_services"])
    print("Weighted disruption:", result["weighted_disruption"])

    print("\nFailure chain:")
    for event in result["failure_chain"]:
        print(f"- {event['asset_id']}: {event['reason']}")
