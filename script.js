// =====================================================
// AFTERSHOCK AI — Critical Infrastructure Resilience Dashboard
// Frontend Controller & Visualization Engine
// =====================================================

// Original 10 civic infrastructure assets
const defaultAssets = [
    {
        id: "substation",
        name: "Power Substation",
        type: "Power",
        icon: "⚡",
        dependencies: [],
        criticality: 10,
    },
    {
        id: "hospital",
        name: "Hospital",
        type: "Healthcare",
        icon: "🏥",
        dependencies: ["substation", "tower"],
        criticality: 10,
    },
    {
        id: "water",
        name: "Water Pump",
        type: "Water Supply",
        icon: "💧",
        dependencies: ["substation"],
        criticality: 8,
    },
    {
        id: "tower",
        name: "Mobile Tower",
        type: "Communication",
        icon: "📡",
        dependencies: ["substation"],
        criticality: 7,
    },
    {
        id: "emergency",
        name: "Emergency Centre",
        type: "Emergency Services",
        icon: "🚑",
        dependencies: ["substation", "tower"],
        criticality: 9,
    },
    {
        id: "shelter",
        name: "Relief Shelter",
        type: "Public Safety",
        icon: "🏠",
        dependencies: ["water"],
        criticality: 7,
    },
    {
        id: "treatment",
        name: "Water Treatment",
        type: "Water Supply",
        icon: "🚰",
        dependencies: ["substation", "water"],
        criticality: 8,
    },
    {
        id: "data",
        name: "Control Centre",
        type: "Digital Services",
        icon: "🖥️",
        dependencies: ["substation", "tower"],
        criticality: 6,
    },
    {
        id: "traffic",
        name: "Traffic Signals",
        type: "Transport",
        icon: "🚦",
        dependencies: ["substation"],
        criticality: 5,
    },
    {
        id: "fire",
        name: "Fire Station",
        type: "Emergency Services",
        icon: "🚒",
        dependencies: ["substation"],
        criticality: 8,
    },
];

// Original 6 municipal protective interventions
const defaultInterventions = [
    {
        id: "substation",
        name: "Substation Flood Barrier",
        description: "Reduces the modeled chance of a flood-triggered substation failure.",
        cost: 30000,
        benefit: 10,
        target: "substation",
    },
    {
        id: "hospital",
        name: "Hospital Backup Power",
        description: "Keeps the hospital operational during a modeled power outage.",
        cost: 25000,
        benefit: 9,
        target: "hospital",
    },
    {
        id: "water",
        name: "Water Pump Backup",
        description: "Provides backup power to the water pumping facility.",
        cost: 15000,
        benefit: 8,
        target: "water",
    },
    {
        id: "tower",
        name: "Communication Backup",
        description: "Maintains the modeled mobile tower during power failure.",
        cost: 20000,
        benefit: 7,
        target: "tower",
    },
    {
        id: "emergency",
        name: "Emergency Centre Backup",
        description: "Protects the emergency centre against power loss.",
        cost: 18000,
        benefit: 7,
        target: "emergency",
    },
    {
        id: "shelter",
        name: "Shelter Water Reserve",
        description: "Provides an alternative modeled water supply to the shelter.",
        cost: 10000,
        benefit: 5,
        target: "shelter",
    },
];

let assets = [...defaultAssets];
let interventions = [...defaultInterventions];

const scenarioNames = {
    flood: "Flood",
    power: "Power Grid Failure",
    power_outage: "Power Grid Failure",
    communication: "Communication Failure",
    communication_failure: "Communication Failure",
};

let currentSimulation = null;
let currentPlan = [];
let chart = null;
let lastOptimization = null;
let baselineSimulationCache = {};


// =====================================================
// INITIALIZATION
// =====================================================

document.addEventListener("DOMContentLoaded", async () => {
    await loadBackendMetadata();

    renderNetwork();
    renderInterventions();
    updateBudget();

    document.getElementById("budget").addEventListener("input", updateBudget);

    document.getElementById("runSimulation")
        .addEventListener("click", () => runSimulation());

    document.getElementById("quickSimulate")
        .addEventListener("click", () => runSimulation());

    document.getElementById("runOptimizer")
        .addEventListener("click", runOptimizer);

    document.getElementById("applyPlan")
        .addEventListener("click", applyPlan);

    document.getElementById("scenario").addEventListener("change", () => {
        resetResults();
        showToast("Scenario updated. Run the simulation to evaluate baseline disruption.");
    });

    setupNavigation();

    if (window.lucide) {
        lucide.createIcons();
    }
});


async function loadBackendMetadata() {
    try {
        const [infraRes, intervRes] = await Promise.all([
            fetch("/api/infrastructure").catch(() => null),
            fetch("/api/interventions").catch(() => null),
        ]);

        if (infraRes && infraRes.ok) {
            const data = await infraRes.json();
            if (Array.isArray(data.assets) && data.assets.length > 0) {
                assets = data.assets;
            }
        }

        if (intervRes && intervRes.ok) {
            const data = await intervRes.json();
            if (Array.isArray(data.interventions) && data.interventions.length > 0) {
                interventions = data.interventions;
            }
        }
    } catch (err) {
        console.warn("Using local defaults for metadata:", err);
    }
}


function setupNavigation() {
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
                optimizer: "Budget-Aware Optimizer",
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
                        block: "start",
                    });
                }
            } else {
                window.scrollTo({
                    top: 0,
                    behavior: "smooth",
                });
            }
        });
    });
}


// =====================================================
// BUDGET HELPERS
// =====================================================

function getBudget() {
    return Number(document.getElementById("budget").value);
}

function formatMoney(value) {
    return "₹" + Number(value).toLocaleString("en-IN");
}

function updateBudget() {
    const budget = getBudget();

    document.getElementById("budgetValue").textContent = formatMoney(budget);
    document.getElementById("budgetMetric").textContent = formatMoney(budget);

    updateSelectedCost();
}


// =====================================================
// INFRASTRUCTURE GRAPH VISUALIZATION (ORIGINAL DESIGN)
// =====================================================

function renderNetwork(failedIds = new Set(), protectedIds = new Set()) {
    const container = document.getElementById("networkCanvas");
    if (!container) return;

    container.innerHTML = "";

    assets.forEach(asset => {
        const node = document.createElement("div");

        let state = "Operational";
        let className = "";

        if (failedIds.has(asset.id)) {
            state = "Failed";
            className = "failed";
        } else if (protectedIds.has(asset.id)) {
            state = "Protected";
            className = "protected";
        }

        node.className = "network-node " + className;

        const icon = asset.icon || "🏢";
        const assetType = asset.type || asset.service || "Infrastructure";

        node.innerHTML = `
            <div class="node-icon">${icon}</div>
            <div class="node-name">${asset.name}</div>
            <div class="node-type">${assetType}</div>
            <div class="node-state">${state}</div>
        `;

        container.appendChild(node);
    });
}


// =====================================================
// INTERVENTION SELECTION (ORIGINAL CARDS)
// =====================================================

function renderInterventions() {
    const container = document.getElementById("interventionList");
    if (!container) return;

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

            <p>${item.description || ""}</p>

            <div class="intervention-cost">
                ${formatMoney(item.cost)}
            </div>

            <div class="intervention-impact">
                Illustrative priority weight: ${item.benefit || item.criticality || 8}
            </div>
        </div>
    `).join("");

    interventions.forEach(item => {
        const checkbox = document.getElementById("check-" + item.id);
        if (checkbox) {
            checkbox.addEventListener("change", () => {
                updateInterventionCard(item.id);
                updateSelectedCost();
            });
        }
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
    return interventions.filter(item => {
        const cb = document.getElementById("check-" + item.id);
        return cb && cb.checked;
    });
}

function updateSelectedCost() {
    const selected = getSelectedInterventions();
    const total = selected.reduce((sum, item) => sum + item.cost, 0);
    const budget = getBudget();

    const costEl = document.getElementById("selectedCost");
    if (costEl) {
        costEl.textContent = formatMoney(total);
        if (total > budget) {
            costEl.style.color = "var(--red)";
        } else {
            costEl.style.color = "var(--cyan)";
        }
    }
}


// =====================================================
// SIMULATION (BACKEND API CLIENT)
// =====================================================

async function runSimulation(appliedInterventions = null) {
    const scenario = document.getElementById("scenario").value;

    let selectedInterventions = appliedInterventions;
    if (selectedInterventions === null) {
        selectedInterventions = getSelectedInterventions().map(i => i.id);
    }

    try {
        const response = await fetch("/api/simulate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                scenario: scenario,
                interventions: selectedInterventions,
            }),
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.error || `HTTP ${response.status}`);
        }

        const data = await response.json();
        currentSimulation = data;

        renderSimulationResults(data);

        if (selectedInterventions.length === 0) {
            document.getElementById("beforeScore").textContent = data.weighted_disruption;
            document.getElementById("afterScore").textContent = "—";
            document.getElementById("improvement").textContent = "—";
            updateChart(data.weighted_disruption, null);
            baselineSimulationCache[scenario] = data.weighted_disruption;
        } else {
            const baselineScore = baselineSimulationCache[scenario] ?? data.weighted_disruption;
            document.getElementById("beforeScore").textContent = baselineScore;
            document.getElementById("afterScore").textContent = data.weighted_disruption;

            const reduction = Math.max(baselineScore - data.weighted_disruption, 0);
            const pct = baselineScore > 0 ? Math.round((reduction / baselineScore) * 100) : 0;
            document.getElementById("improvement").textContent = `${reduction} pts (${pct}%)`;
            updateChart(baselineScore, data.weighted_disruption);
        }

        showToast(
            `${data.scenario_name}: ${data.failed_count} asset(s) disrupted. ` +
            `Weighted disruption score: ${data.weighted_disruption}.`
        );
        return data;

    } catch (error) {
        console.error("Simulation error:", error);
        showToast("Simulation failed: " + error.message);
        return null;
    }
}


function renderSimulationResults(data) {
    document.getElementById("assetCount").textContent = data.total_assets || assets.length;
    document.getElementById("failedCount").textContent = data.failed_count;
    document.getElementById("serviceCount").textContent = (data.affected_services || []).length;

    const failedSet = new Set(data.failed_assets || []);
    const protectedSet = new Set([
        ...(data.protected_assets || []),
        ...(data.backed_up_assets || []),
    ]);

    renderNetwork(failedSet, protectedSet);
    renderTimeline(data.timeline || []);
    renderAssetStatus(data.assets || []);

    if (window.lucide) {
        lucide.createIcons();
    }
}


function renderTimeline(timeline) {
    const container = document.getElementById("eventTimeline");
    if (!container) return;

    if (!timeline || timeline.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i data-lucide="check-circle" style="color: var(--green);"></i>
                <p>No infrastructure failures occurred in this simulation.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = timeline.map(event => `
        <div class="timeline-item">
            <div class="timeline-time">
                ${event.step === 0 ? "INITIAL EVENT" : "CASCADE STEP " + event.step}
            </div>
            <strong>${event.title}</strong>
            <p>${event.description}</p>
        </div>
    `).join("");
}


function renderAssetStatus(assetResults) {
    const container = document.getElementById("assetStatus");
    if (!container) return;

    if (!assetResults || assetResults.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>Asset status will appear after simulation.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = assetResults.map(asset => {
        let status = "Operational";
        let badgeClass = "";

        if (asset.status === "failed") {
            status = "Failed";
            badgeClass = "failed";
        } else if (asset.status === "protected" || asset.status === "backed_up") {
            status = "Protected";
            badgeClass = "protected";
        }

        const icon = asset.icon || "🏢";
        const assetType = asset.type || asset.service || "General";

        return `
            <div class="asset-row">
                <div class="asset-info">
                    <strong>${icon} ${asset.name}</strong>
                    <p>${assetType}</p>
                </div>
                <span class="state-badge ${badgeClass}">
                    ${status}
                </span>
            </div>
        `;
    }).join("");
}


// =====================================================
// BUDGET-AWARE OPTIMIZER (BACKEND API CLIENT)
// =====================================================

async function runOptimizer() {
    const scenario = document.getElementById("scenario").value;
    const budget = getBudget();

    showToast("Evaluating feasible protection combinations...");

    try {
        const response = await fetch("/api/optimize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                scenario: scenario,
                budget: budget,
            }),
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.error || `HTTP ${response.status}`);
        }

        const result = await response.json();
        lastOptimization = result;

        // Auto-check recommended interventions in UI
        const recommendedIds = new Set(result.selected_intervention_ids || []);
        interventions.forEach(item => {
            const cb = document.getElementById("check-" + item.id);
            if (cb) {
                cb.checked = recommendedIds.has(item.id);
                updateInterventionCard(item.id);
            }
        });

        updateSelectedCost();

        // Update score indicators
        document.getElementById("beforeScore").textContent = result.baseline_disruption;
        document.getElementById("afterScore").textContent = result.optimized_disruption;

        const reductionText = `${result.disruption_reduction} pts (${result.disruption_reduction_percent}%)`;
        document.getElementById("improvement").textContent = reductionText;

        if (result.optimized) {
            renderSimulationResults(result.optimized);
        }

        updateChart(result.baseline_disruption, result.optimized_disruption);

        // Populate explanation panel matching original visual hierarchy
        const selectedList = result.selected_interventions || [];
        const actionsHtml = selectedList.length > 0
            ? selectedList.map(item => `&bull; <strong>${item.name}</strong> (${formatMoney(item.cost)}) &mdash; ${item.description}`).join("<br>")
            : "<em>No interventions selected (budget insufficient or zero improvement achievable).</em>";

        document.getElementById("optimizationResult").innerHTML = `
            <strong>Suggested protection plan</strong><br>
            Scenario: <strong>${result.scenario_name}</strong><br>
            Budget: <strong>${formatMoney(result.budget)}</strong><br>
            Selected cost: <strong>${formatMoney(result.total_cost)}</strong><br>
            Combinations evaluated: <strong>${result.combinations_evaluated}</strong><br>
            Baseline disruption score: <strong>${result.baseline_disruption}</strong><br>
            Optimized disruption score: <strong>${result.optimized_disruption}</strong><br>
            <span class="good">
                Reduction in modeled disruption: <strong>${result.disruption_reduction_percent}% (${result.disruption_reduction} points)</strong>
            </span><br><br>
            <strong>Selected actions:</strong><br>
            ${actionsHtml}<br><br>
            <strong>Why this plan?</strong><br>
            The system evaluated feasible combinations and selected the one
            with the lowest weighted disruption score under the budget.
            Ties are resolved by choosing the lower-cost option.
        `;

        showToast(
            `Optimization complete. Evaluated ${result.combinations_evaluated} combinations. Selected cost: ${formatMoney(result.total_cost)}.`
        );

    } catch (error) {
        console.error("Optimizer error:", error);
        showToast("Optimizer error: " + error.message);
    }
}


// =====================================================
// APPLY PROTECTION PLAN
// =====================================================

async function applyPlan() {
    const scenario = document.getElementById("scenario").value;
    const selected = getSelectedInterventions();
    const totalCost = selected.reduce((sum, item) => sum + item.cost, 0);
    const budget = getBudget();

    if (totalCost > budget) {
        showToast(
            `Selected interventions cost ${formatMoney(totalCost)}, ` +
            `which exceeds your budget of ${formatMoney(budget)}.`
        );
        return;
    }

    const selectedIds = selected.map(item => item.id);

    try {
        let baselineScore = baselineSimulationCache[scenario];
        if (baselineScore === undefined) {
            const baseRes = await fetch("/api/simulate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ scenario: scenario, interventions: [] }),
            });
            if (baseRes.ok) {
                const baseData = await baseRes.json();
                baselineScore = baseData.weighted_disruption;
                baselineSimulationCache[scenario] = baselineScore;
            } else {
                baselineScore = 0;
            }
        }

        const res = await fetch("/api/simulate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ scenario: scenario, interventions: selectedIds }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${res.status}`);
        }

        const data = await res.json();
        currentSimulation = data;

        renderSimulationResults(data);

        const afterScore = data.weighted_disruption;
        const reduction = Math.max(baselineScore - afterScore, 0);
        const pct = baselineScore > 0 ? Math.round((reduction / baselineScore) * 100) : 0;

        document.getElementById("beforeScore").textContent = baselineScore;
        document.getElementById("afterScore").textContent = afterScore;
        document.getElementById("improvement").textContent = `${pct}%`;

        updateChart(baselineScore, afterScore);

        document.getElementById("optimizationResult").innerHTML = `
            <strong>Protection plan applied to the simulation</strong><br>
            Selected interventions: <strong>${selected.length}</strong><br>
            Total cost: <strong>${formatMoney(totalCost)}</strong><br>
            Remaining budget: <strong>${formatMoney(budget - totalCost)}</strong><br>
            Baseline score: <strong>${baselineScore}</strong><br>
            Recalculated score: <strong>${afterScore}</strong><br>
            Weighted score reduction: <strong>${reduction}</strong><br>
            <span class="good">
                <strong>${pct}% reduction in modeled disruption.</strong>
            </span><br><br>
            <strong>Selected actions:</strong><br>
            ${
                selected.length > 0
                    ? selected.map(i => `&bull; <strong>${i.name}</strong> (${formatMoney(i.cost)})`).join("<br>")
                    : "No interventions selected."
            }
        `;

        showToast("Protection plan applied. The dashboard now shows the recalculated simulation.");

    } catch (err) {
        console.error("Apply plan error:", err);
        showToast("Failed to apply plan: " + err.message);
    }
}


// =====================================================
// CHART RENDERING (WITH OFFLINE FALLBACK)
// =====================================================

function updateChart(before, after) {
    const canvas = document.getElementById("comparisonChart");
    if (!canvas) return;

    const hasAfter = after !== null && after !== undefined;

    if (window.Chart) {
        if (chart) {
            chart.destroy();
        }

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
                    barThickness: 45,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: context => "Score: " + context.raw,
                        },
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: "#26354b" },
                        ticks: { color: "#8fa1b9", precision: 0 },
                        title: {
                            display: true,
                            text: "Weighted disruption points",
                            color: "#8fa1b9",
                        },
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: "#e9f0fa" },
                    },
                },
            },
        });
    } else {
        renderOfflineChartFallback(before, after);
    }
}


function renderOfflineChartFallback(before, after) {
    const container = document.querySelector(".chart-container");
    if (!container) return;

    const maxVal = Math.max(before, after || 0, 10);
    const beforePct = Math.round((before / maxVal) * 100);
    const afterPct = after !== null && after !== undefined ? Math.round((after / maxVal) * 100) : null;

    container.innerHTML = `
        <div style="display: flex; height: 100%; align-items: flex-end; justify-content: center; gap: 40px; padding: 20px 0;">
            <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
                <span style="font-weight: 700; color: #ff647c; font-size: 16px;">${before}</span>
                <div style="width: 50px; height: ${Math.max(beforePct * 1.5, 8)}px; background: #ff647c; border-radius: 6px;"></div>
                <span style="font-size: 11px; color: #8fa1b9;">Without Protection</span>
            </div>
            ${
                afterPct !== null
                    ? `
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 8px;">
                        <span style="font-weight: 700; color: #35d49a; font-size: 16px;">${after}</span>
                        <div style="width: 50px; height: ${Math.max(afterPct * 1.5, 8)}px; background: #35d49a; border-radius: 6px;"></div>
                        <span style="font-size: 11px; color: #8fa1b9;">With Protection</span>
                    </div>
                    `
                    : ""
            }
        </div>
    `;
}


// =====================================================
// RESET & TOAST NOTIFICATIONS
// =====================================================

function resetResults() {
    currentSimulation = null;
    currentPlan = [];
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


function showToast(message) {
    const existing = document.querySelector(".toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 4000);
}
