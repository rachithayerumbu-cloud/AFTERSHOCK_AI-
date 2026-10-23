// =====================================================
// AFTERSHOCK AI
// Frontend demonstration simulation
// All values are illustrative, not real-world forecasts.
// =====================================================

const assets = [
    {
        id: "substation",
        name: "Power Substation",
        type: "Power",
        icon: "⚡",
        dependencies: [],
        criticality: 10,
        vulnerableTo: ["flood", "power"],
        intervention: "substation"
    },
    {
        id: "hospital",
        name: "Hospital",
        type: "Healthcare",
        icon: "🏥",
        dependencies: ["substation", "communication"],
        criticality: 10,
        vulnerableTo: [],
        intervention: "hospital"
    },
    {
        id: "water",
        name: "Water Pump",
        type: "Water Supply",
        icon: "💧",
        dependencies: ["substation"],
        criticality: 8,
        vulnerableTo: ["flood"],
        intervention: "water"
    },
    {
        id: "tower",
        name: "Mobile Tower",
        type: "Communication",
        icon: "📡",
        dependencies: ["substation"],
        criticality: 7,
        vulnerableTo: [],
        intervention: "tower"
    },
    {
        id: "emergency",
        name: "Emergency Centre",
        type: "Emergency Services",
        icon: "🚑",
        dependencies: ["substation", "communication"],
        criticality: 9,
        vulnerableTo: [],
        intervention: "emergency"
    },
    {
        id: "shelter",
        name: "Relief Shelter",
        type: "Public Safety",
        icon: "🏠",
        dependencies: ["water"],
        criticality: 7,
        vulnerableTo: [],
        intervention: "shelter"
    },
    {
        id: "treatment",
        name: "Water Treatment",
        type: "Water Supply",
        icon: "🚰",
        dependencies: ["substation", "water"],
        criticality: 8,
        vulnerableTo: [],
        intervention: "treatment"
    },
    {
        id: "data",
        name: "Control Centre",
        type: "Digital Services",
        icon: "🖥️",
        dependencies: ["substation", "communication"],
        criticality: 6,
        vulnerableTo: [],
        intervention: "data"
    },
    {
        id: "traffic",
        name: "Traffic Signals",
        type: "Transport",
        icon: "🚦",
        dependencies: ["substation"],
        criticality: 5,
        vulnerableTo: [],
        intervention: "traffic"
    },
    {
        id: "fire",
        name: "Fire Station",
        type: "Emergency Services",
        icon: "🚒",
        dependencies: ["substation"],
        criticality: 8,
        vulnerableTo: [],
        intervention: "fire"
    }
];


// Illustrative protection options.
// Benefit values are model parameters, not measured facts.
const interventions = [
    {
        id: "substation",
        name: "Substation Flood Barrier",
        description: "Reduces the modeled chance of a flood-triggered substation failure.",
        cost: 30000,
        benefit: 10,
        target: "substation"
    },
    {
        id: "hospital",
        name: "Hospital Backup Power",
        description: "Keeps the hospital operational during a modeled power outage.",
        cost: 25000,
        benefit: 9,
        target: "hospital"
    },
    {
        id: "water",
        name: "Water Pump Backup",
        description: "Provides backup power to the water pumping facility.",
        cost: 15000,
        benefit: 8,
        target: "water"
    },
    {
        id: "tower",
        name: "Communication Backup",
        description: "Maintains the modeled mobile tower during power failure.",
        cost: 20000,
        benefit: 7,
        target: "tower"
    },
    {
        id: "emergency",
        name: "Emergency Centre Backup",
        description: "Protects the emergency centre against power loss.",
        cost: 18000,
        benefit: 7,
        target: "emergency"
    },
    {
        id: "shelter",
        name: "Shelter Water Reserve",
        description: "Provides an alternative modeled water supply to the shelter.",
        cost: 10000,
        benefit: 5,
        target: "shelter"
    }
];

const scenarioNames = {
    flood: "Flood",
    power: "Power Grid Failure",
    communication: "Communication Failure"
};

let currentSimulation = null;
let currentPlan = [];
let appliedPlan = [];
let chart = null;
let lastOptimization = null;


// =====================================================
// INITIALIZATION
// =====================================================

document.addEventListener("DOMContentLoaded", () => {
    renderNetwork(new Set(), new Set());
    renderInterventions();
    updateBudget();

    document.getElementById("budget").addEventListener("input", updateBudget);

    document.getElementById("runSimulation")
        .addEventListener("click", runSimulation);

    document.getElementById("quickSimulate")
        .addEventListener("click", runSimulation);

    document.getElementById("runOptimizer")
        .addEventListener("click", runOptimizer);

    document.getElementById("applyPlan")
        .addEventListener("click", applyPlan);

    document.getElementById("scenario").addEventListener("change", () => {
        resetResults();
        showToast("Scenario changed. Run the simulation to calculate new results.");
    });

    document.querySelectorAll(".nav-item").forEach(button => {
        button.addEventListener("click", () => {
            const target = button.dataset.target;

            document.querySelectorAll(".nav-item").forEach(item => {
                item.classList.remove("active");
            });

            button.classList.add("active");

            const titles = {
                overview: "Infrastructure Overview",
                network: "Infrastructure Dependency Network",
                simulation: "Disaster Simulation",
                optimizer: "Budget-Aware Optimizer"
            };

            document.getElementById("pageTitle").textContent =
                titles[target] || "Infrastructure Overview";

            document.getElementById("pageName").textContent =
                target.replace("-", " ").toUpperCase();

            if (target !== "overview") {
                const section = document.getElementById(target);
                if (section) {
                    section.scrollIntoView({
                        behavior: "smooth",
                        block: "start"
                    });
                }
            } else {
                window.scrollTo({
                    top: 0,
                    behavior: "smooth"
                });
            }
        });
    });

    if (window.lucide) {
        lucide.createIcons();
    }
});


// =====================================================
// BUDGET
// =====================================================

function getBudget() {
    return Number(document.getElementById("budget").value);
}

function formatMoney(value) {
    return "₹" + Number(value).toLocaleString("en-IN");
}

function updateBudget() {
    const budget = getBudget();

    document.getElementById("budgetValue").textContent =
        formatMoney(budget);

    document.getElementById("budgetMetric").textContent =
        formatMoney(budget);

    updateSelectedCost();
}


// =====================================================
// INFRASTRUCTURE GRAPH DISPLAY
// =====================================================

function renderNetwork(failed = new Set(), protectedAssets = new Set()) {
    const container = document.getElementById("networkCanvas");
    container.innerHTML = "";

    assets.forEach(asset => {
        const node = document.createElement("div");

        let state = "Operational";
        let className = "";

        if (failed.has(asset.id)) {
            state = "Failed";
            className = "failed";
        } else if (protectedAssets.has(asset.id)) {
            state = "Protected";
            className = "protected";
        }

        node.className = "network-node " + className;

        node.innerHTML = `
            <div class="node-icon">${asset.icon}</div>
            <div class="node-name">${asset.name}</div>
            <div class="node-type">${asset.type}</div>
            <div class="node-state">${state}</div>
        `;

        container.appendChild(node);
    });
}


// =====================================================
// SIMULATION ENGINE
// =====================================================

function getInitialFailures(scenario, protectedAssets) {
    const initial = new Set();

    if (scenario === "flood") {
        if (!protectedAssets.has("substation")) {
            initial.add("substation");
        }
    }

    if (scenario === "power") {
        initial.add("substation");
    }

    if (scenario === "communication") {
        initial.add("tower");
    }

    return initial;
}

function simulate(scenario, protectedAssets = new Set()) {
    const failed = new Set();
    const initial = getInitialFailures(scenario, protectedAssets);
    const timeline = [];

    // Scenario-specific direct effects.
    if (scenario === "flood" && !protectedAssets.has("water")) {
        failed.add("water");
        timeline.push({
            step: 1,
            title: "Water pump affected by flooding",
            description: "The selected scenario directly disrupts the modeled water pump."
        });
    }

    if (scenario === "communication") {
        failed.add("tower");
        timeline.push({
            step: 1,
            title: "Communication tower unavailable",
            description: "The scenario directly disables the modeled communication tower."
        });
    }

    initial.forEach(id => {
        failed.add(id);

        const asset = assets.find(item => item.id === id);

        if (asset) {
            timeline.unshift({
                step: 0,
                title: asset.name + " failure",
                description: "Initial failure triggered by the selected scenario."
            });
        }
    });

    // Propagate dependencies until no new failures occur.
    let changed = true;
    let iteration = 0;

    while (changed && iteration < assets.length) {
        changed = false;
        iteration++;

        for (const asset of assets) {
            if (failed.has(asset.id)) continue;

            // A protected asset remains operational in this simplified model.
            if (protectedAssets.has(asset.id)) continue;

            const failedDependencies = asset.dependencies.filter(dep =>
                failed.has(dep)
            );

            if (failedDependencies.length > 0) {
                failed.add(asset.id);
                changed = true;

                timeline.push({
                    step: iteration,
                    title: asset.name + " disrupted",
                    description:
                        "Dependency failure: " +
                        failedDependencies.map(id =>
                            assets.find(item => item.id === id).name
                        ).join(", ") +
                        " unavailable."
                });
            }
        }
    }

    // Calculate a simple weighted disruption score.
    // Each asset contributes its illustrative criticality weight.
    const score = assets.reduce((total, asset) => {
        return total + (failed.has(asset.id) ? asset.criticality : 0);
    }, 0);

    const failedList = assets.filter(asset => failed.has(asset.id));

    const essentialServices = failedList.filter(asset =>
        ["Healthcare", "Water Supply", "Emergency Services"].includes(asset.type)
    );

    return {
        scenario,
        initialFailures: [...initial],
        failed,
        timeline,
        score,
        failedCount: failed.size,
        serviceCount: essentialServices.length,
        failedList
    };
}


// =====================================================
// RUN SIMULATION
// =====================================================

function runSimulation() {
    const scenario = document.getElementById("scenario").value;

    currentPlan = [];
    appliedPlan = [];
    lastOptimization = null;

    clearSelectedInterventions();

    currentSimulation = simulate(scenario, new Set());

    renderResults(currentSimulation, new Set());

    document.getElementById("beforeScore").textContent =
        currentSimulation.score;

    document.getElementById("afterScore").textContent = "—";
    document.getElementById("improvement").textContent = "—";

    updateChart(currentSimulation.score, null);

    document.getElementById("optimizationResult").textContent =
        "Run the optimizer to calculate a protection plan.";

    showToast(
        scenarioNames[scenario] +
        " simulation complete. " +
        currentSimulation.failedCount +
        " infrastructure assets failed in this simplified model."
    );
}


// =====================================================
// RENDER RESULTS
// =====================================================

function renderResults(result, protectedAssets = new Set()) {
    document.getElementById("assetCount").textContent = assets.length;
    document.getElementById("failedCount").textContent = result.failedCount;
    document.getElementById("serviceCount").textContent = result.serviceCount;

    renderNetwork(result.failed, protectedAssets);
    renderTimeline(result.timeline);
    renderAssetStatus(result.failed, protectedAssets);

    if (window.lucide) {
        lucide.createIcons();
    }
}

function renderTimeline(timeline) {
    const container = document.getElementById("eventTimeline");

    if (timeline.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No failures occurred under this scenario.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = timeline.map((event, index) => `
        <div class="timeline-item">
            <div class="timeline-time">
                ${index === 0 ? "INITIAL EVENT" : "CASCADE STEP " + event.step}
            </div>
            <strong>${event.title}</strong>
            <p>${event.description}</p>
        </div>
    `).join("");
}

function renderAssetStatus(failed, protectedAssets) {
    const container = document.getElementById("assetStatus");

    container.innerHTML = assets.map(asset => {
        let status = "Operational";
        let badgeClass = "";

        if (failed.has(asset.id)) {
            status = "Failed";
            badgeClass = "failed";
        } else if (protectedAssets.has(asset.id)) {
            status = "Protected";
            badgeClass = "protected";
        }

        return `
            <div class="asset-row">
                <div class="asset-info">
                    <strong>${asset.icon} ${asset.name}</strong>
                    <p>${asset.type}</p>
                </div>
                <span class="state-badge ${badgeClass}">
                    ${status}
                </span>
            </div>
        `;
    }).join("");
}


// =====================================================
// INTERVENTION OPTIONS
// =====================================================

function renderInterventions() {
    const container = document.getElementById("interventionList");

    container.innerHTML = interventions.map(item => `
        <div class="intervention-card" id="card-${item.id}">
            <div class="intervention-top">
                <h4>${item.name}</h4>
                <input
                    type="checkbox"
                    id="check-${item.id}"
                    data-id="${item.id}"
                    aria-label="Select ${item.name}"
                >
            </div>

            <p>${item.description}</p>

            <div class="intervention-cost">
                ${formatMoney(item.cost)}
            </div>

            <div class="intervention-impact">
                Illustrative priority weight: ${item.benefit}
            </div>
        </div>
    `).join("");

    interventions.forEach(item => {
        document.getElementById("check-" + item.id)
            .addEventListener("change", () => {
                updateInterventionCard(item.id);
                updateSelectedCost();
            });
    });
}

function clearSelectedInterventions() {
    interventions.forEach(item => {
        const checkbox = document.getElementById("check-" + item.id);
        if (checkbox) checkbox.checked = false;

        updateInterventionCard(item.id);
    });

    updateSelectedCost();
}

function updateInterventionCard(id) {
    const checkbox = document.getElementById("check-" + id);
    const card = document.getElementById("card-" + id);

    if (checkbox && card) {
        card.classList.toggle("selected", checkbox.checked);
    }
}

function getSelectedInterventions() {
    return interventions.filter(item =>
        document.getElementById("check-" + item.id).checked
    );
}

function updateSelectedCost() {
    const selected = getSelectedInterventions();

    const total = selected.reduce((sum, item) => sum + item.cost, 0);

    document.getElementById("selectedCost").textContent =
        formatMoney(total);
}


// =====================================================
// BUDGET-AWARE OPTIMIZER
// =====================================================

// Exhaustively evaluates all feasible intervention combinations.
// This is suitable for a small demonstration set of six interventions.
// Each combination is tested using the SAME simulation function.

function runOptimizer() {
    const scenario = document.getElementById("scenario").value;
    const budget = getBudget();

    let best = null;
    let combinationsChecked = 0;

    const count = interventions.length;
    const totalCombinations = 1 << count;

    for (let mask = 0; mask < totalCombinations; mask++) {
        const selected = [];
        let cost = 0;

        for (let i = 0; i < count; i++) {
            if (mask & (1 << i)) {
                selected.push(interventions[i]);
                cost += interventions[i].cost;
            }
        }

        if (cost > budget) continue;

        combinationsChecked++;

        const protectedAssets = new Set(
            selected.map(item => item.target)
        );

        const result = simulate(scenario, protectedAssets);

        if (
            best === null ||
            result.score < best.result.score ||
            (
                result.score === best.result.score &&
                cost < best.cost
            )
        ) {
            best = {
                selected,
                cost,
                result,
                protectedAssets
            };
        }
    }

    if (!best) {
        showToast("No feasible intervention combination was found.");
        return;
    }

    currentPlan = best.selected.map(item => item.id);

    lastOptimization = {
        ...best,
        baseline: simulate(scenario, new Set()),
        combinationsChecked,
        budget,
        scenario
    };

    // Show the optimizer's recommended checkboxes.
    interventions.forEach(item => {
        const checkbox = document.getElementById("check-" + item.id);

        checkbox.checked = currentPlan.includes(item.id);
        updateInterventionCard(item.id);
    });

    updateSelectedCost();

    const baseline = lastOptimization.baseline.score;
    const optimized = best.result.score;
    const reduction = baseline === 0
        ? 0
        : Math.round(((baseline - optimized) / baseline) * 100);

    document.getElementById("optimizationResult").innerHTML = `
        <strong>Suggested protection plan</strong><br>
        Scenario: ${scenarioNames[scenario]}<br>
        Budget: ${formatMoney(budget)}<br>
        Selected cost: ${formatMoney(best.cost)}<br>
        Combinations evaluated: ${combinationsChecked}<br>
        Baseline disruption score: ${baseline}<br>
        Optimized disruption score: ${optimized}<br>
        <span class="good">
            Reduction in modeled disruption: ${reduction}%
        </span><br><br>
        <strong>Why this plan?</strong><br>
        The system evaluated feasible combinations and selected the one
        with the lowest weighted disruption score under the budget.
        Ties are resolved by choosing the lower-cost option.
    `;

    showToast(
        "Optimization complete. Selected cost: " +
        formatMoney(best.cost) + "."
    );
}


// =====================================================
// APPLY PROTECTION PLAN
// =====================================================

function applyPlan() {
    const scenario = document.getElementById("scenario").value;
    const selected = getSelectedInterventions();
    const totalCost = selected.reduce((sum, item) => sum + item.cost, 0);
    const budget = getBudget();

    if (totalCost > budget) {
        showToast(
            "Selected interventions cost " + formatMoney(totalCost) +
            ", which exceeds your budget of " + formatMoney(budget) + "."
        );
        return;
    }

    const protectedAssets = new Set(
        selected.map(item => item.target)
    );

    const baseline = simulate(scenario, new Set());
    const after = simulate(scenario, protectedAssets);

    appliedPlan = selected.map(item => item.id);

    renderResults(after, protectedAssets);

    document.getElementById("beforeScore").textContent = baseline.score;
    document.getElementById("afterScore").textContent = after.score;

    const reduction = baseline.score === 0
        ? 0
        : Math.round(
            ((baseline.score - after.score) / baseline.score) * 100
        );

    document.getElementById("improvement").textContent =
        reduction + "%";

    updateChart(baseline.score, after.score);

    const reductionText = baseline.score - after.score;

    document.getElementById("optimizationResult").innerHTML = `
        <strong>Protection plan applied to the simulation</strong><br>
        Selected interventions: ${selected.length}<br>
        Total cost: ${formatMoney(totalCost)}<br>
        Remaining budget: ${formatMoney(budget - totalCost)}<br>
        Baseline score: ${baseline.score}<br>
        Recalculated score: ${after.score}<br>
        Weighted score reduction: ${reductionText}<br>
        <span class="good">
            ${reduction}% reduction in modeled disruption.
        </span><br><br>
        <strong>Selected actions</strong><br>
        ${
            selected.length
                ? selected.map(item => "• " + item.name).join("<br>")
                : "No interventions selected."
        }
    `;

    showToast(
        "Protection plan applied. The dashboard now shows the recalculated simulation."
    );
}


// =====================================================
// CHART
// =====================================================

function updateChart(before, after) {
    const canvas = document.getElementById("comparisonChart");

    if (!canvas || !window.Chart) return;

    if (chart) {
        chart.destroy();
    }

    const hasAfter = after !== null && after !== undefined;

    chart = new Chart(canvas, {
        type: "bar",

        data: {
            labels: hasAfter
                ? ["Without Protection", "With Protection"]
                : ["Without Protection"],

            datasets: [{
                label: "Weighted Disruption Score",
                data: hasAfter ? [before, after] : [before],
                backgroundColor: hasAfter
                    ? ["#ff647c", "#35d49a"]
                    : ["#ff647c"],
                borderRadius: 6,
                barThickness: 45
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            plugins: {
                legend: {
                    display: false
                },

                tooltip: {
                    callbacks: {
                        label: context =>
                            "Score: " + context.raw
                    }
                }
            },

            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: "#26354b"
                    },
                    ticks: {
                        color: "#8fa1b9",
                        precision: 0
                    },
                    title: {
                        display: true,
                        text: "Weighted disruption points",
                        color: "#8fa1b9"
                    }
                },

                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: "#e9f0fa"
                    }
                }
            }
        }
    });
}


// =====================================================
// RESET
// =====================================================

function resetResults() {
    currentSimulation = null;
    currentPlan = [];
    appliedPlan = [];
    lastOptimization = null;

    clearSelectedInterventions();

    document.getElementById("failedCount").textContent = "0";
    document.getElementById("serviceCount").textContent = "0";

    document.getElementById("beforeScore").textContent = "—";
    document.getElementById("afterScore").textContent = "—";
    document.getElementById("improvement").textContent = "—";

    document.getElementById("eventTimeline").innerHTML = `
        <div class="empty-state">
            <p>Run a simulation to see the event sequence.</p>
        </div>
    `;

    document.getElementById("assetStatus").innerHTML = `
        <div class="empty-state">
            <p>Asset status will appear after simulation.</p>
        </div>
    `;

    renderNetwork(new Set(), new Set());

    if (chart) {
        chart.destroy();
        chart = null;
    }

    document.getElementById("optimizationResult").textContent =
        "Run the optimizer to receive a suggested protection plan.";
}


// =====================================================
// NOTIFICATIONS
// =====================================================

function showToast(message) {
    const existing = document.querySelector(".toast");

    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3500);
}