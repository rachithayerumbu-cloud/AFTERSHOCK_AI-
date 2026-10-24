/**
 * AFTERSHOCK AI — Multi-Page Client Controller
 * File: static/script.js
 *
 * 100% Offline Vanilla JavaScript.
 * Coordinates page detection, REST API communication, failure simulation,
 * interactive SVG network graph, and budget knapsack optimization.
 */

// =====================================================
// GLOBAL STATE & LAYOUT CONSTANTS
// =====================================================
const state = {
    currentScenario: "flood",
    currentBudget: null,
    infrastructure: null,
    cities: [],
    activeCity: null,
    scenarios: [],
    interventions: [],
    risks: null,

    // Active simulation & optimization results
    currentSimulation: null,
    baselineDisruption: null,
    recommendedPlan: null,

    selectedNodeId: "substation",
};

const graphViews = new Map();


// =====================================================
// DOM INITIALIZATION & PAGE ROUTING
// =====================================================
document.addEventListener("DOMContentLoaded", async () => {
    document.querySelector(".page-content")?.classList.add("city-unselected");
    document.querySelectorAll(".footer-server-url").forEach(element => {
        element.textContent = window.location.origin;
    });
    initGraphControls();

    const citySelect = document.getElementById("citySelect");
    const cityState = document.getElementById("cityEmptyState");
    if (!citySelect) return;

    try {
        const response = await fetch("/api/cities");
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        state.cities = (data.cities || []).filter(city => city.id === data.active_city && city.status === "active");
        (data.cities || []).forEach(city => {
            const active = state.cities.some(available => available.id === city.id);
            const label = active ? `${city.name}, ${city.state}` : `${city.name} (data unavailable)`;
            const option = new Option(label, city.id);
            option.disabled = !active;
            citySelect.add(option);
        });
    } catch (error) {
        console.error("City list could not be loaded:", error);
        if (cityState) cityState.textContent = "City data could not be loaded. Check the backend connection.";
        citySelect.disabled = true;
        return;
    }

    citySelect.addEventListener("change", () => {
        try {
            if (citySelect.value) sessionStorage.setItem("aftershockCity", citySelect.value);
            else sessionStorage.removeItem("aftershockCity");
        } catch (error) {
            console.warn("City selection could not be saved for page navigation:", error);
        }
        window.location.reload();
    });

    let savedCity = "";
    try {
        savedCity = sessionStorage.getItem("aftershockCity") || "";
    } catch (error) {
        console.warn("Saved city selection is unavailable:", error);
    }
    if (state.cities.some(city => city.id === savedCity)) {
        citySelect.value = savedCity;
        await activateSelectedCity(savedCity);
    } else if (cityState && !state.cities.length) {
        cityState.textContent = "No city with an active infrastructure dataset is available.";
    }
});

async function activateSelectedCity(cityId) {
    const city = state.cities.find(item => item.id === cityId);
    if (!city) return;
    state.activeCity = city;
    const main = document.querySelector(".page-content");
    const emptyState = document.getElementById("cityEmptyState");
    main?.classList.remove("city-unselected");
    if (emptyState) emptyState.hidden = true;
    await loadSharedMetadata();

    initOverviewPage();
    initSimulationPage();
    initInfrastructurePage();
    initOptimizerPage();
    initRisksPage();

    document.querySelectorAll(".selected-city-name").forEach(element => {
        element.textContent = city.name;
    });
    const cityTag = document.getElementById("overviewCityTag");
    const cityName = document.getElementById("ovCityName");
    const cityRegion = document.getElementById("ovCityRegion");
    if (cityTag) cityTag.textContent = `${city.name}, ${city.state}, ${city.country}`.toUpperCase();
    if (cityName) cityName.textContent = city.name;
    if (cityRegion) cityRegion.textContent = `${city.state}, ${city.country}`;
}


// =====================================================
// BACKEND HEALTH CHECK & SHARED METADATA
// =====================================================
async function loadSharedMetadata() {
    try {
        const [infraRes, scenRes, intervRes] = await Promise.all([
            fetch("/api/infrastructure").catch(() => null),
            fetch("/api/scenarios").catch(() => null),
            fetch("/api/interventions").catch(() => null),
        ]);

        if (infraRes && infraRes.ok) {
            state.infrastructure = await infraRes.json();
        }
        if (scenRes && scenRes.ok) {
            const scenData = await scenRes.json();
            state.scenarios = scenData.scenarios || [];
        }
        if (intervRes && intervRes.ok) {
            const intervData = await intervRes.json();
            state.interventions = intervData.interventions || [];
        }
    } catch (err) {
        console.error("Failed to load shared metadata:", err);
    }
}


// =====================================================
// PAGE 1: OVERVIEW PAGE HANDLER
// =====================================================
function initOverviewPage() {
    const previewSvg = document.getElementById("previewSvg");
    if (!previewSvg) return; // Not on overview page

    // Update summary counts from live metadata
    if (state.infrastructure) {
        const assetCountEl = document.getElementById("ovAssetCount");
        const depCountEl = document.getElementById("ovDepCount");
        if (assetCountEl) assetCountEl.textContent = state.infrastructure.total_assets ?? state.infrastructure.assets?.length ?? "--";
        if (depCountEl) depCountEl.textContent = state.infrastructure.dependencies?.length ?? "--";
    }
    if (state.scenarios) {
        const scenCountEl = document.getElementById("ovScenarioCount");
        if (scenCountEl) scenCountEl.textContent = state.scenarios.length;
    }
    if (state.interventions) {
        const intervCountEl = document.getElementById("ovIntervCount");
        if (intervCountEl) intervCountEl.textContent = state.interventions.length;
    }

    // Render preview SVG diagram
    renderNetworkSvg("previewSvg", { assets: state.infrastructure?.assets || [] });
    loadOverviewScenarioResults();
}

async function loadOverviewScenarioResults() {
    const container = document.getElementById("ovScenarioResults");
    if (!container) return;
    if (!state.scenarios.length) {
        container.innerHTML = `<p class="empty-state">Scenario data could not be loaded from the backend.</p>`;
        return;
    }

    container.innerHTML = state.scenarios.map((scenario, index) => `
        <article class="kpi-card scenario-summary" data-scenario-card="${index}">
            <span class="badge scenario-name">${escapeHtml(scenario.hazard_type || scenario.id)}</span>
            <h4 class="scenario-title">${escapeHtml(scenario.name)}</h4>
            <p class="scenario-result">Calculating backend result...</p>
            <strong class="scenario-score">--</strong>
        </article>
    `).join("");

    const results = await Promise.all(state.scenarios.map(async scenario => {
        try {
            const response = await fetch("/api/simulate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ scenario: scenario.id }),
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const payload = await response.json();
            return { scenario, simulation: payload.simulation || payload };
        } catch (error) {
            console.error(`Overview scenario ${scenario.id} failed:`, error);
            return { scenario, error };
        }
    }));

    results.forEach((result, index) => {
        const card = container.querySelector(`[data-scenario-card="${index}"]`);
        if (!card) return;
        if (result.error) {
            card.querySelector(".scenario-result").textContent = "Simulation result unavailable.";
            return;
        }
        card.querySelector(".scenario-score").textContent = `${result.simulation.disruption_score} pts`;
        card.querySelector(".scenario-result").textContent = `${result.simulation.failed_count} failed · ${result.simulation.operational_count} operational`;
    });

    const latest = results.find(result => result.simulation);
    if (latest) {
        const score = document.getElementById("ovDisruptionScore");
        const label = document.getElementById("ovDisruptionScenario");
        const failed = document.getElementById("ovFailedCount");
        if (score) score.textContent = `${latest.simulation.disruption_score} pts`;
        if (label) label.textContent = latest.scenario.name;
        if (failed) failed.textContent = latest.simulation.failed_count;
    }
}


// =====================================================
// PAGE 2: DISASTER SIMULATION HANDLER
// =====================================================
function initSimulationPage() {
    const btnRunSim = document.getElementById("btnRunSimulation");
    const selScenario = document.getElementById("simScenarioSelect");
    const btnReset = document.getElementById("btnResetSim");

    if (!btnRunSim || !selScenario) return; // Not on simulation page

    // Populate scenario dropdown
    if (state.scenarios.length > 0) {
        selScenario.innerHTML = "";
        state.scenarios.forEach(sc => {
            const opt = document.createElement("option");
            opt.value = sc.id;
            opt.textContent = sc.name;
            if (sc.id === state.currentScenario) opt.selected = true;
            selScenario.appendChild(opt);
        });
    }

    // Scenario change
    selScenario.addEventListener("change", (e) => {
        state.currentScenario = e.target.value;
        updateSimulationScenarioBrief();
    });

    // Run Simulation Button Click
    btnRunSim.addEventListener("click", () => {
        executeSimulation();
    });

    // Reset button
    if (btnReset) {
        btnReset.addEventListener("click", () => {
            resetSimulation();
        });
    }


function resetSimulation() {
    state.currentScenario = state.scenarios[0]?.id || "flood";
    state.currentSimulation = null;

    const scenarioSelect = document.getElementById("simScenarioSelect");
    if (scenarioSelect) scenarioSelect.value = state.currentScenario;
    updateSimulationScenarioBrief();

    ["kpiDisruptionScore", "kpiFailedCount", "kpiOperCount"].forEach(id => {
        const element = document.getElementById(id);
        if (element) element.textContent = "--";
    });
    const protectedCount = document.getElementById("kpiProtCount");
    if (protectedCount) protectedCount.textContent = "0";

    const assetPanel = document.getElementById("simAssetStatusPanel");
    const assetRows = document.getElementById("simAssetTableBody");
    if (assetPanel) assetPanel.hidden = true;
    if (assetRows) assetRows.replaceChildren();

    const timelineCount = document.getElementById("simTimelineCount");
    const timeline = document.getElementById("simTimelineList");
    if (timelineCount) timelineCount.textContent = "--";
    if (timeline) timeline.innerHTML = `<div class="empty-timeline"><p>No simulation run yet.</p></div>`;

    const banner = document.getElementById("simAlertBanner");
    if (banner) {
        banner.style.display = "none";
        banner.replaceChildren();
    }

    try {
        sessionStorage.removeItem("aftershockSimulationCity");
    } catch (error) {
        console.warn("Saved simulation state could not be cleared:", error);
    }

    renderNetworkSvg("simulationSvg", { assets: state.infrastructure?.assets || [] }, "simInspIcon", "simInspName", "simInspBadge", "simInspMeta");
}
    updateSimulationScenarioBrief();
    const networkScope = document.getElementById("simNetworkScope");
    if (networkScope) {
        networkScope.textContent = state.infrastructure?.assets?.length
            ? `${state.infrastructure.assets.length} assets · ${state.infrastructure.dependencies?.length ?? 0} dependencies`
            : "Infrastructure data unavailable";
    }
    renderNetworkSvg("simulationSvg", { assets: state.infrastructure?.assets || [] }, "simInspIcon", "simInspName", "simInspBadge", "simInspMeta");
}

function updateSimulationScenarioBrief() {
    const sc = state.scenarios.find(s => s.id === state.currentScenario);
    if (!sc) return;

    const tag = document.getElementById("briefHazardTag");
    const title = document.getElementById("briefScenarioTitle");
    const desc = document.getElementById("briefScenarioDesc");
    const inits = document.getElementById("briefInitialList");

    if (tag) tag.textContent = `HAZARD: ${(sc.hazard_type || sc.id).toUpperCase()}`;
    if (title) title.textContent = sc.name;
    if (desc) desc.textContent = sc.description;

    if (inits) {
        const names = (sc.initial_failures || []).map(getAssetName);
        inits.textContent = names.join(", ") || "None";
    }
}

async function executeSimulation(protectedInterventions = []) {
    const btn = document.getElementById("btnRunSimulation");
    const spinner = document.getElementById("simSpinner");
    const btnText = document.getElementById("simBtnText");
    const banner = document.getElementById("simAlertBanner");

    // 1. Loading state
    if (btn) btn.disabled = true;
    if (spinner) spinner.style.display = "inline-block";
    if (btnText) btnText.textContent = "Simulating...";

    try {
        const payload = {
            scenario: state.currentScenario,
            protected_assets: protectedInterventions,
        };

        const res = await fetch("/api/simulate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.message || `Simulation failed with HTTP status ${res.status}`);
        }

        const data = await res.json();
        const sim = data.simulation || data;
        state.currentSimulation = sim;
        if (state.activeCity) {
            try {
                sessionStorage.setItem("aftershockSimulationCity", state.activeCity.id);
            } catch (storageError) {
                console.warn("Simulation completion could not be saved for page navigation:", storageError);
            }
        }

        // 2. Update KPI Metrics
        const elScore = document.getElementById("kpiDisruptionScore");
        const elFailed = document.getElementById("kpiFailedCount");
        const elOper = document.getElementById("kpiOperCount");
        const elProt = document.getElementById("kpiProtCount");

        if (elScore) elScore.textContent = `${sim.disruption_score} pts`;
        if (elFailed) elFailed.textContent = `${sim.failed_count ?? 0} / ${sim.total_assets ?? sim.assets?.length ?? 0}`;
        if (elOper) elOper.textContent = `${sim.operational_count ?? 0} / ${sim.total_assets ?? sim.assets?.length ?? 0}`;
        if (elProt) elProt.textContent = `${sim.protected_count || 0}`;

        // 3. Render persistent SVG Network Graph
        renderNetworkSvg("simulationSvg", sim, "simInspIcon", "simInspName", "simInspBadge", "simInspMeta");

        // 4. Render Asset Status Table
        const assetStatusPanel = document.getElementById("simAssetStatusPanel");
        if (assetStatusPanel) assetStatusPanel.hidden = false;
        renderSimulationAssetTable(sim.assets || []);

        // 5. Render Cascade Timeline
        renderSimulationTimeline(sim.timeline || []);

        // 6. Show Success Banner
        if (banner) {
            banner.className = "alert-banner alert-success";
            banner.style.display = "flex";
            banner.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
                <span><strong>Simulation Complete:</strong> Scenario <em>"${escapeHtml(sim.scenario_name)}"</em> produced a disruption score of <strong>${sim.disruption_score} points</strong> (${sim.failed_count} failed, ${sim.operational_count} operational).</span>
            `;
        }

    } catch (err) {
        console.error("Simulation execution error:", err);
        if (banner) {
            banner.className = "alert-banner alert-error";
            banner.style.display = "flex";
            banner.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                <span><strong>Simulation Error:</strong> ${escapeHtml(err.message)}</span>
            `;
        }
    } finally {
        // Re-enable button
        if (btn) btn.disabled = false;
        if (spinner) spinner.style.display = "none";
        if (btnText) btnText.textContent = "Run Simulation";
    }
}

function renderSimulationAssetTable(assets) {
    const tbody = document.getElementById("simAssetTableBody");
    if (!tbody) return;

    let html = "";
    assets.forEach(a => {
        let pillClass = "pill-oper";
        let statusText = "Operational";

        if (a.status === "failed") {
            pillClass = "pill-fail";
            statusText = "Disrupted";
        } else if (a.status === "protected") {
            pillClass = "pill-prot";
            statusText = "Protected";
        }

        html += `
            <tr>
                <td><strong>${escapeHtml(a.icon || "🏢")} ${escapeHtml(a.name)}</strong></td>
                <td>${escapeHtml(a.category)}</td>
                <td><strong>${a.criticality}/10</strong></td>
                <td><span class="pill ${pillClass}">${statusText}</span></td>
                <td style="font-size: 0.72rem; color: var(--text-secondary);">${escapeHtml(a.backup_protection || "Standard")}</td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

function renderSimulationTimeline(events) {
    const container = document.getElementById("simTimelineList");
    const countBadge = document.getElementById("simTimelineCount");
    if (!container) return;

    if (!events || events.length === 0) {
        if (countBadge) countBadge.textContent = "0 Steps";
        container.innerHTML = `<div class="empty-timeline"><p>No cascade disruptions recorded in this scenario.</p></div>`;
        return;
    }

    if (countBadge) countBadge.textContent = `${events.length} Events`;
    let html = "";

    events.forEach(evt => {
        const isShock = evt.step === 0;
        const stepClass = isShock ? "event-shock" : "";
        const stepLabel = isShock ? "Initial Hazard Shock" : `Wave ${evt.step} Cascade`;

        html += `
            <div class="timeline-event ${stepClass}">
                <div class="event-title">[${stepLabel}] ${escapeHtml(evt.title)}</div>
                <div class="event-desc">${escapeHtml(evt.description)}</div>
            </div>
        `;
    });

    container.innerHTML = html;
}


// =====================================================
// PAGE 3: INFRASTRUCTURE NETWORK HANDLER
// =====================================================
function initInfrastructurePage() {
    const svg = document.getElementById("infrastructureSvg");
    if (svg) {
        renderNetworkSvg("infrastructureSvg", { assets: state.infrastructure?.assets || [] }, "infraInspIcon", "infraInspName", "infraInspBadge", "infraInspMeta");
    }

    const totalAssets = document.getElementById("infraTotalAssets");
    const totalDeps = document.getElementById("infraTotalDeps");
    const networkStatus = document.getElementById("infraNetworkStatus");
    if (totalAssets) totalAssets.textContent = state.infrastructure?.assets?.length ?? "--";
    if (totalDeps) totalDeps.textContent = state.infrastructure?.dependencies?.length ?? "--";
    if (networkStatus) networkStatus.textContent = "Not supplied";

    // Populate searchable asset specification cards
    const cardsGrid = document.getElementById("infraAssetCardsGrid");
    const catalogBadge = document.getElementById("catalogCountBadge");
    const assetSearch = document.getElementById("infraAssetSearch");
    if (cardsGrid && state.infrastructure?.assets) {
        const assets = state.infrastructure.assets;
        if (catalogBadge) catalogBadge.textContent = `${assets.length} Facilities`;

        const renderCards = query => {
            const normalized = query.trim().toLowerCase();
            const filtered = assets.filter(asset => `${asset.name} ${asset.id} ${asset.category}`.toLowerCase().includes(normalized));
            cardsGrid.innerHTML = filtered.map(asset => {
                const reqNames = (asset.depends_on || []).map(getAssetName).join(", ") || "None (Primary Source)";
                return `
                    <div class="asset-spec-card" data-asset-id="${escapeHtml(asset.id)}">
                        <div class="spec-top">
                            <span class="spec-name">${escapeHtml(asset.icon || "●")} ${escapeHtml(asset.name)}</span>
                            <span class="badge">${asset.criticality}/10 Crit.</span>
                        </div>
                        <span class="spec-category">${escapeHtml(asset.id)} · ${escapeHtml(asset.category)} · ${escapeHtml(asset.service || asset.category)}</span>
                        <p class="spec-desc">${escapeHtml(asset.description)}</p>
                        <div class="spec-deps"><strong>Prerequisites:</strong> ${escapeHtml(reqNames)}</div>
                    </div>
                `;
            }).join("") || `<p class="empty-state">No matching infrastructure assets.</p>`;
        };
        renderCards("");
        assetSearch?.addEventListener("input", event => renderCards(event.target.value));
    }

    // Populate directed dependencies list
    const depList = document.getElementById("infraDepList");
    const depBadge = document.getElementById("depCountBadge");
    if (depList && state.infrastructure?.dependencies) {
        const deps = state.infrastructure.dependencies;
        if (depBadge) depBadge.textContent = `${deps.length} Edges`;

        let html = "";
        deps.forEach((d, idx) => {
            const srcName = getAssetName(d.source);
            const tgtName = getAssetName(d.target);

            html += `
                <div class="dep-item">
                    <div class="dep-route">${idx + 1}. ${escapeHtml(srcName)} <span>&rarr;</span> ${escapeHtml(tgtName)}</div>
                    <span class="dep-desc">${escapeHtml(d.description || "Operational dependency")}</span>
                </div>
            `;
        });
        depList.innerHTML = html;
    }
}


// =====================================================
// PAGE 4: BUDGET OPTIMIZER HANDLER
// =====================================================
function initOptimizerPage() {
    const btnRunOpt = document.getElementById("btnRunOptimizer");
    const btnApply = document.getElementById("btnApplyOptimizerPlan");
    const selScenario = document.getElementById("optScenarioSelect");
    const inputBudget = document.getElementById("optBudgetInput");

    if (!btnRunOpt || !inputBudget) return; // Not on optimizer page

    // Populate scenario selector
    if (state.scenarios.length > 0 && selScenario) {
        selScenario.innerHTML = "";
        state.scenarios.forEach(sc => {
            const opt = document.createElement("option");
            opt.value = sc.id;
            opt.textContent = sc.name;
            if (sc.id === state.currentScenario) opt.selected = true;
            selScenario.appendChild(opt);
        });
    }

    // Scenario change
    selScenario.addEventListener("change", (e) => {
        state.currentScenario = e.target.value;
        state.recommendedPlan = null;
        if (btnApply) btnApply.disabled = true;
        resetOptimizerOutputs();
        if (state.currentBudget !== null) executeOptimizer();
    });

    // Budget input change
    inputBudget.addEventListener("input", (e) => {
        const val = e.target.value === "" ? null : Number(e.target.value);
        if (val === null || !Number.isFinite(val) || val < 0) {
            state.currentBudget = null;
            btnRunOpt.disabled = true;
            if (btnApply) btnApply.disabled = true;
            updateOptimizerChips(null);
            resetOptimizerOutputs();
            return;
        }
        state.currentBudget = val;
        btnRunOpt.disabled = false;
        updateOptimizerChips(val);
    });

    // Quick chips
    document.querySelectorAll(".chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const val = parseFloat(chip.dataset.val);
            inputBudget.value = val;
            state.currentBudget = val;
            btnRunOpt.disabled = false;
            updateOptimizerChips(val);
        });
    });

    // Find Budget Plan
    btnRunOpt.addEventListener("click", () => {
        if (state.currentBudget !== null) executeOptimizer();
    });

    // Apply Plan
    if (btnApply) {
        btnApply.addEventListener("click", () => {
            applyOptimizerPlan();
        });
    }

    renderNetworkSvg("optimizerNetworkSvg", { assets: state.infrastructure?.assets || [] });
    inputBudget.value = "";
    btnRunOpt.disabled = true;
    if (btnApply) btnApply.disabled = true;
    resetOptimizerOutputs();
}

function updateOptimizerChips(amount) {
    document.querySelectorAll(".chip").forEach(chip => {
        if (parseFloat(chip.dataset.val) === amount) {
            chip.classList.add("active");
        } else {
            chip.classList.remove("active");
        }
    });
}

async function executeOptimizer() {
    const btn = document.getElementById("btnRunOptimizer");
    const btnText = document.getElementById("optBtnText");
    const btnApply = document.getElementById("btnApplyOptimizerPlan");
    const banner = document.getElementById("optAlertBanner");

    if (btn) btn.disabled = true;
    if (btnText) btnText.textContent = "Evaluating 64 Subsets...";

    try {
        const payload = {
            scenario: state.currentScenario,
            budget: state.currentBudget,
        };

        const res = await fetch("/api/optimize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.message || `Optimizer error HTTP ${res.status}`);
        }

        const data = await res.json();
        const plan = data.plan || data;
        state.recommendedPlan = plan;

        // Render KPI row
        const elBase = document.getElementById("optValBaseline");
        const elOpt = document.getElementById("optValOptimized");
        const elRed = document.getElementById("optValReduction");
        const elRedPct = document.getElementById("optValReductionPct");
        const elSpent = document.getElementById("optValSpent");
        const elLeft = document.getElementById("optValLeft");

        if (elBase) elBase.textContent = `${plan.baseline_disruption} pts`;
        if (elOpt) elOpt.textContent = `${plan.optimized_disruption} pts`;
        if (elRed) elRed.textContent = `${plan.disruption_reduction} pts`;
        if (elRedPct) elRedPct.textContent = `${plan.disruption_reduction_percent}% reduction`;
        if (elSpent) elSpent.textContent = `₹${Math.round(plan.total_cost).toLocaleString()}`;
        if (elLeft) elLeft.textContent = `Remaining: ₹${Math.round(plan.remaining_budget).toLocaleString()}`;

        // Render Plan Details
        renderOptimizerPlanUI(plan);

        // Render Stable Comparison Chart
        renderOptimizerComparisonChart(plan.baseline_disruption, plan.optimized_disruption, plan.disruption_reduction_percent);

        // Render Asset Status Post-Plan
        if (plan.optimized_simulation?.assets) {
            renderOptimizerAssetTable(plan.optimized_simulation.assets);
            renderNetworkSvg("optimizerNetworkSvg", plan.optimized_simulation, "", "", "", "");
        }

        // Enable Apply Plan button if interventions were recommended
        if (btnApply) {
            btnApply.disabled = !(plan.selected_interventions && plan.selected_interventions.length > 0);
        }

        // Show notice in banner
        if (banner) {
            banner.className = "alert-banner alert-success";
            banner.style.display = "flex";
            banner.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
                <span><strong>Optimal Plan Identified:</strong> Evaluated ${plan.combinations_evaluated || 64} combinations. Saved <strong>${plan.disruption_reduction} points (${plan.disruption_reduction_percent}%)</strong> using ₹${Math.round(plan.total_cost).toLocaleString()}.</span>
            `;
        }

    } catch (err) {
        console.error("Optimizer error:", err);
        if (banner) {
            banner.className = "alert-banner alert-error";
            banner.style.display = "flex";
            banner.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                <span><strong>Optimization Error:</strong> ${escapeHtml(err.message)}</span>
            `;
        }
    } finally {
        if (btn) btn.disabled = false;
        if (btnText) btnText.textContent = "Find Budget Plan";
    }
}

async function applyOptimizerPlan() {
    if (!state.recommendedPlan) return;

    const btn = document.getElementById("btnApplyOptimizerPlan");
    const applyText = document.getElementById("applyBtnText");
    const banner = document.getElementById("optAlertBanner");

    if (btn) btn.disabled = true;
    if (applyText) applyText.textContent = "Applying...";

    try {
        const selectedIds = state.recommendedPlan.selected_intervention_ids || [];

        const payload = {
            scenario: state.currentScenario,
            protected_assets: selectedIds,
        };

        const res = await fetch("/api/simulate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.message || `HTTP ${res.status}`);
        }

        const data = await res.json();
        const sim = data.simulation || data;
        state.currentSimulation = sim;

        // Update protected asset table from the real simulation response
        if (sim.assets) {
            renderOptimizerAssetTable(sim.assets);
            renderNetworkSvg("optimizerNetworkSvg", sim, "", "", "", "");
        }

        // Keep comparison chart persistent and accurate
        renderOptimizerComparisonChart(
            state.recommendedPlan.baseline_disruption,
            sim.disruption_score,
            state.recommendedPlan.disruption_reduction_percent
        );

        const lblState = document.getElementById("optLblSimState");
        if (lblState) lblState.textContent = "Plan Active in Simulation";

        if (applyText) applyText.textContent = "Plan Active";
        if (btn) btn.disabled = false;

        if (banner) {
            banner.className = "alert-banner alert-success";
            banner.style.display = "flex";
            banner.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
                <span><strong>Plan Applied to Live Simulation:</strong> Disruption score is now confirmed at <strong>${sim.disruption_score} points</strong>.</span>
            `;
        }

    } catch (err) {
        console.error("Apply Plan error:", err);
        alert(`Apply Plan Error: ${err.message}`);
        if (applyText) applyText.textContent = "Apply Plan";
        if (btn) btn.disabled = false;
    }
}

function renderOptimizerPlanUI(plan) {
    const container = document.getElementById("optPlanBody");
    const badge = document.getElementById("optCombBadge");

    if (badge) badge.textContent = `${plan.combinations_evaluated || 64} affordable evaluated`;
    if (!container) return;

    let html = `
        <div class="plan-summary-msg">
            ${escapeHtml(plan.explanation)}
        </div>
    `;

    if (plan.selected_interventions && plan.selected_interventions.length > 0) {
        html += `<div class="plan-list">`;
        plan.selected_interventions.forEach(item => {
            html += `
                <div class="plan-row">
                    <div>
                        <div class="plan-row-name">${escapeHtml(item.name)}</div>
                        <div class="plan-row-desc">${escapeHtml(item.description)}</div>
                    </div>
                    <div class="plan-row-cost">₹${item.cost.toLocaleString()}</div>
                </div>
            `;
        });
        html += `</div>`;
    } else {
        html += `
            <div class="empty-plan-box">
                <p>No interventions allocated within this budget.</p>
                <span>Increase the budget or select another hazard scenario to evaluate measures.</span>
            </div>
        `;
    }

    container.innerHTML = html;
}

function clearOptimizerPlanUI() {
    const container = document.getElementById("optPlanBody");
    if (!container) return;
    container.innerHTML = "";
}

function resetOptimizerOutputs() {
    state.recommendedPlan = null;
    const values = ["optValBaseline", "optValOptimized", "optValReduction", "optValSpent"];
    values.forEach(id => {
        const element = document.getElementById(id);
        if (element) element.textContent = "--";
    });
    const reduction = document.getElementById("optValReductionPct");
    const remaining = document.getElementById("optValLeft");
    const stateLabel = document.getElementById("optLblSimState");
    const count = document.getElementById("optCombBadge");
    const table = document.getElementById("optAssetTableBody");
    const banner = document.getElementById("optAlertBanner");
    if (reduction) reduction.textContent = "--";
    if (remaining) remaining.textContent = "--";
    if (stateLabel) stateLabel.textContent = "--";
    if (count) count.textContent = "--";
    if (table) table.replaceChildren();
    if (banner) banner.style.display = "none";
    clearOptimizerPlanUI();
    renderOptimizerComparisonChart(null, null, null);
    renderNetworkSvg("optimizerNetworkSvg", { assets: state.infrastructure?.assets || [] });
}

function renderOptimizerComparisonChart(beforeScore, afterScore, reductionPct) {
    const valBefore = document.getElementById("optBarValBefore");
    const valAfter = document.getElementById("optBarValAfter");
    const barBefore = document.getElementById("optBarBefore");
    const barAfter = document.getElementById("optBarAfter");
    const summary = document.getElementById("optChartSummary");

    if (beforeScore === null || beforeScore === undefined) {
        if (valBefore) valBefore.textContent = "--";
        if (valAfter) valAfter.textContent = "--";
        if (barBefore) barBefore.style.height = "0%";
        if (barAfter) barAfter.style.height = "0%";
        if (summary) summary.textContent = "";
        return;
    }
    if (valBefore) valBefore.textContent = `${beforeScore} pts`;

    const criticalityTotal = state.infrastructure?.assets?.reduce((total, asset) => total + asset.criticality, 0) || 1;
    const maxVal = Math.max(criticalityTotal, beforeScore || 1);
    const beforeHeight = beforeScore !== null ? Math.min(100, Math.max(8, (beforeScore / maxVal) * 100)) : 0;
    if (barBefore) barBefore.style.height = `${beforeHeight}%`;

    if (afterScore === null || afterScore === undefined) {
        if (valAfter) valAfter.textContent = "--";
        if (barAfter) barAfter.style.height = "4%";
        if (summary) summary.textContent = `Baseline disruption score is ${beforeScore} points.`;
    } else {
        if (valAfter) valAfter.textContent = `${afterScore} pts`;

        // GUARANTEED VISIBLE PEDESTAL: even if disruption is 0 (100% saved), keep a 6% minimum pedestal
        const afterHeight = afterScore > 0 ? Math.min(100, Math.max(8, (afterScore / maxVal) * 100)) : 6;
        if (barAfter) barAfter.style.height = `${afterHeight}%`;

        const saved = (beforeScore || 0) - afterScore;
        const pctStr = reductionPct !== null && reductionPct !== undefined ? reductionPct : (beforeScore > 0 ? ((saved / beforeScore) * 100).toFixed(1) : 0);

        if (summary) {
            if (saved > 0) {
                summary.innerHTML = `<strong>Resilience Gain:</strong> Disruption reduced from <strong>${beforeScore}</strong> to <strong>${afterScore}</strong> (${saved} points saved, <strong>${pctStr}% improvement</strong>).`;
            } else if (beforeScore === 0) {
                summary.textContent = "Scenario causes zero baseline disruption. No intervention needed.";
            } else {
                summary.textContent = "No disruption score reduction achieved within the selected budget limit.";
            }
        }
    }
}

function renderOptimizerAssetTable(assets) {
    const tbody = document.getElementById("optAssetTableBody");
    if (!tbody) return;

    let html = "";
    assets.forEach(a => {
        let pillClass = "pill-oper";
        let statusText = "Operational";

        if (a.status === "failed") {
            pillClass = "pill-fail";
            statusText = "Disrupted";
        } else if (a.status === "protected") {
            pillClass = "pill-prot";
            statusText = "Protected";
        }

        html += `
            <tr>
                <td><strong>${escapeHtml(a.icon || "🏢")} ${escapeHtml(a.name)}</strong></td>
                <td>${escapeHtml(a.category)}</td>
                <td><strong>${a.criticality}/10</strong></td>
                <td><span class="pill ${pillClass}">${statusText}</span></td>
                <td style="font-size: 0.72rem; color: var(--text-secondary);">${escapeHtml(a.backup_protection || "Standard")}</td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}


// =====================================================
// PAGE 5: AI RISK ANALYSIS HANDLER
// =====================================================
async function initRisksPage() {
    const grid = document.getElementById("pageRisksGrid");
    if (!grid) return; // Not on risks page

    let completedCity = "";
    try {
        completedCity = sessionStorage.getItem("aftershockSimulationCity") || "";
    } catch (error) {
        console.warn("Saved simulation state is unavailable:", error);
    }
    if (!state.activeCity || completedCity !== state.activeCity.id) {
        const page = grid.closest(".page-content");
        const emptyState = document.getElementById("cityEmptyState");
        grid.replaceChildren();
        if (page) page.classList.add("city-unselected");
        if (emptyState) {
            emptyState.hidden = false;
            emptyState.textContent = "Run a simulation for this city to view asset classifications.";
        }
        return;
    }

    try {
        const res = await fetch("/api/risks");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        state.risks = data;

        const badge = document.getElementById("riskAssetCountBadge");
        if (badge) badge.textContent = `${data.assets?.length ?? 0} Facilities Evaluated`;

        const counts = (data.assets || []).reduce((totals, item) => {
            const label = item.risk_label || "";
            if (label.includes("High")) totals.high += 1;
            else if (label.includes("Low")) totals.low += 1;
            else if (label.includes("Medium")) totals.medium += 1;
            return totals;
        }, { high: 0, medium: 0, low: 0 });
        document.getElementById("riskHighCount").textContent = counts.high;
        document.getElementById("riskMediumCount").textContent = counts.medium;
        document.getElementById("riskLowCount").textContent = counts.low;

        let html = "";
        (data.assets || []).forEach(item => {
            let badgeClass = "ml-badge-medium";
            let cardClass = "ml-card-medium";
            if (item.risk_label.includes("Low")) {
                badgeClass = "ml-badge-low";
                cardClass = "ml-card-low";
            }
            if (item.risk_label.includes("High")) {
                badgeClass = "ml-badge-high";
                cardClass = "ml-card-high";
            }

            const feats = item.features || {};
            const confidence = Math.max(0, Math.min(100, Math.round((item.confidence_score || 0) * 100)));

            html += `
                <article class="ml-card ${cardClass}">
                    <div class="ml-card-top">
                        <div>
                            <div class="ml-facility-name">${escapeHtml(item.asset_name)}</div>
                            <div class="ml-facility-cat">${escapeHtml(item.category)}</div>
                        </div>
                        <span class="ml-risk-badge ${badgeClass}">${escapeHtml(item.risk_label)}</span>
                    </div>
                    <div class="ml-features-row">
                        <div>Criticality: <strong>${feats.criticality || "--"}/10</strong></div>
                        <div>Exposure Score: <strong>${feats.exposure_score || "--"}/10</strong></div>
                    </div>
                    <div class="ml-confidence">
                        <div class="ml-confidence-label"><span>Class confidence</span><strong>${confidence}%</strong></div>
                        <div class="ml-confidence-track"><span style="width: ${confidence}%"></span></div>
                    </div>
                </article>
            `;
        });

        grid.innerHTML = html;

    } catch (err) {
        console.error("AI Risks loading error:", err);
        grid.innerHTML = `<div class="empty-plan-box"><p>Failed to load AI risk predictions from backend.</p></div>`;
    }
}


// =====================================================
// PERSISTENT SVG NETWORK GRAPH RENDERER
// (USED ACROSS SIMULATION, INFRASTRUCTURE, & OVERVIEW)
// =====================================================
function renderNetworkSvg(svgId, result, iconId, nameId, badgeId, metaId) {
    const svg = document.getElementById(svgId);
    if (!svg) return;

    const assets = Array.isArray(result?.assets) ? result.assets : [];
    const dependencies = Array.isArray(state.infrastructure?.dependencies)
        ? state.infrastructure.dependencies
        : [];
    svg.replaceChildren();

    if (!state.infrastructure || !assets.length) {
        const message = document.createElementNS("http://www.w3.org/2000/svg", "text");
        message.setAttribute("class", "svg-empty-state");
        message.setAttribute("x", "50%");
        message.setAttribute("y", "50%");
        message.setAttribute("text-anchor", "middle");
        message.textContent = !state.infrastructure
            ? "Infrastructure data could not be loaded. Check the Flask API and reload."
            : "Infrastructure dataset contains no assets.";
        svg.appendChild(message);
        svg.setAttribute("viewBox", "0 0 1200 640");
        return;
    }

    const assetById = new Map(assets.map(asset => [asset.id, asset]));
    const validDependencies = dependencies.filter(dep => assetById.has(dep.source) && assetById.has(dep.target));
    const indegree = new Map(assets.map(asset => [asset.id, 0]));
    const dependents = new Map(assets.map(asset => [asset.id, []]));
    validDependencies.forEach(dep => {
        indegree.set(dep.target, indegree.get(dep.target) + 1);
        dependents.get(dep.source).push(dep.target);
    });

    const ranks = new Map(assets.map(asset => [asset.id, 0]));
    const queue = assets.filter(asset => indegree.get(asset.id) === 0).map(asset => asset.id);
    const remainingIndegree = new Map(indegree);
    while (queue.length) {
        const sourceId = queue.shift();
        dependents.get(sourceId).forEach(targetId => {
            ranks.set(targetId, Math.max(ranks.get(targetId), ranks.get(sourceId) + 1));
            remainingIndegree.set(targetId, remainingIndegree.get(targetId) - 1);
            if (remainingIndegree.get(targetId) === 0) queue.push(targetId);
        });
    }
    const maxRank = Math.max(0, ...ranks.values());
    assets.forEach(asset => {
        if (remainingIndegree.get(asset.id) > 0) ranks.set(asset.id, maxRank + 1);
    });
    const columns = new Map();
    assets.forEach(asset => {
        const rank = ranks.get(asset.id);
        if (!columns.has(rank)) columns.set(rank, []);
        columns.get(rank).push(asset);
    });

    const width = Math.max(1200, columns.size * 390);
    const height = Math.max(640, ...Array.from(columns.values(), items => items.length * 126 + 100));
    const nodeWidth = 260;
    const nodeHeight = 82;
    const positions = new Map();
    columns.forEach((items, rank) => {
        const x = 150 + rank * ((width - 300) / Math.max(1, columns.size - 1));
        items.forEach((asset, index) => {
            positions.set(asset.id, {
                x,
                y: (height / (items.length + 1)) * (index + 1),
            });
        });
    });
    const baseViewBox = `0 0 ${width} ${height}`;
    svg.setAttribute("viewBox", baseViewBox);
    svg.dataset.baseViewBox = baseViewBox;
    graphViews.set(svgId, { x: 0, y: 0, width, height });
    fitGraphCanvas(svg);

    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    defs.innerHTML = `
        <marker id="${svgId}-arrow-oper" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#668a51" />
        </marker>
        <marker id="${svgId}-arrow-fail" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="#c44950" />
        </marker>
    `;
    svg.appendChild(defs);

    validDependencies.forEach(dep => {
        const source = positions.get(dep.source);
        const target = positions.get(dep.target);
        const sourceAsset = assetById.get(dep.source);
        const targetAsset = assetById.get(dep.target);
        const failed = sourceAsset.status === "failed" || targetAsset.status === "failed";
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        const startX = source.x + nodeWidth / 2;
        const endX = target.x - nodeWidth / 2;
        const bend = Math.max(45, (endX - startX) * 0.45);
        path.setAttribute("d", `M ${startX} ${source.y} C ${startX + bend} ${source.y}, ${endX - bend} ${target.y}, ${endX} ${target.y}`);
        path.setAttribute("class", `svg-edge ${failed ? "edge-fail" : "edge-oper"}`);
        path.setAttribute("marker-end", `url(#${svgId}-arrow-${failed ? "fail" : "oper"})`);
        path.setAttribute("aria-label", `${targetAsset.name} depends on ${sourceAsset.name}`);
        svg.appendChild(path);
    });

    assets.forEach(asset => {
        const position = positions.get(asset.id);
        const status = asset.status || "unknown";
        const node = document.createElementNS("http://www.w3.org/2000/svg", "g");
        node.setAttribute("class", `svg-node node-${status}`);
        node.setAttribute("transform", `translate(${position.x}, ${position.y})`);
        node.setAttribute("tabindex", "0");
        node.setAttribute("role", "button");
        node.setAttribute("aria-label", `${asset.name}, ${asset.id}, ${status}`);
        const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
        title.textContent = `${asset.name} (${asset.id}) · ${asset.category} · Criticality ${asset.criticality}/10 · ${status}`;
        node.appendChild(title);

        const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        rect.setAttribute("class", "svg-node-box");
        rect.setAttribute("x", String(-nodeWidth / 2));
        rect.setAttribute("y", String(-nodeHeight / 2));
        rect.setAttribute("width", String(nodeWidth));
        rect.setAttribute("height", String(nodeHeight));
        rect.setAttribute("rx", "7");
        node.appendChild(rect);

        const icon = document.createElementNS("http://www.w3.org/2000/svg", "text");
        icon.setAttribute("class", "svg-node-icon");
        icon.setAttribute("x", String(-nodeWidth / 2 + 23));
        icon.setAttribute("y", "5");
        icon.textContent = asset.icon || "●";
        node.appendChild(icon);

        const name = document.createElementNS("http://www.w3.org/2000/svg", "text");
        name.setAttribute("class", "svg-node-name");
        name.setAttribute("x", String(-nodeWidth / 2 + 44));
        name.setAttribute("y", "-16");
        name.setAttribute("text-anchor", "start");
        name.textContent = asset.name.length > 26 ? `${asset.name.slice(0, 23)}...` : asset.name;
        node.appendChild(name);

        const detail = document.createElementNS("http://www.w3.org/2000/svg", "text");
        detail.setAttribute("class", "svg-node-stat");
        detail.setAttribute("x", String(-nodeWidth / 2 + 44));
        detail.setAttribute("y", "5");
        detail.setAttribute("text-anchor", "start");
        detail.textContent = `${asset.id} · ${status === "unknown" ? "NO STATUS" : status.toUpperCase()}`;
        node.appendChild(detail);

        const category = document.createElementNS("http://www.w3.org/2000/svg", "text");
        category.setAttribute("class", "svg-node-category");
        category.setAttribute("x", String(-nodeWidth / 2 + 44));
        category.setAttribute("y", "26");
        category.setAttribute("text-anchor", "start");
        category.textContent = `${asset.category} · Crit ${asset.criticality}/10`;
        node.appendChild(category);

        const selectNode = () => inspectFacilityNode(asset.id, asset, iconId, nameId, badgeId, metaId);
        node.addEventListener("click", selectNode);
        node.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                selectNode();
            }
        });
        svg.appendChild(node);
    });

    if (iconId && nameId) {
        const selected = assetById.get(state.selectedNodeId) || assets[0];
        inspectFacilityNode(selected.id, selected, iconId, nameId, badgeId, metaId);
    }
}

function initGraphControls() {
    document.querySelectorAll("[data-graph-action]").forEach(button => {
        button.addEventListener("click", () => {
            const svgId = button.dataset.graphTarget;
            const svg = document.getElementById(svgId);
            if (!svg) return;
            if (button.dataset.graphAction === "reset") {
                const base = svg.dataset.baseViewBox;
                if (base) {
                    svg.setAttribute("viewBox", base);
                    const values = base.split(" ").map(Number);
                    graphViews.set(svgId, { x: values[0], y: values[1], width: values[2], height: values[3] });
                }
                return;
            }
            const view = graphViews.get(svgId);
            if (!view) return;
            const factor = button.dataset.graphAction === "zoom-in" ? 0.8 : 1.25;
            const nextWidth = Math.max(view.width * 0.22, Math.min(view.width * 3, view.width * factor));
            const nextHeight = nextWidth * view.height / view.width;
            const centerX = view.x + view.width / 2;
            const centerY = view.y + view.height / 2;
            view.x = centerX - nextWidth / 2;
            view.y = centerY - nextHeight / 2;
            view.width = nextWidth;
            view.height = nextHeight;
            svg.setAttribute("viewBox", `${view.x} ${view.y} ${view.width} ${view.height}`);
        });
    });

    document.querySelectorAll("#simulationSvg, #infrastructureSvg, #optimizerNetworkSvg, #previewSvg").forEach(svg => {
        if (window.ResizeObserver) {
            const observer = new ResizeObserver(() => fitGraphCanvas(svg));
            observer.observe(svg.parentElement);
        }
        let drag = null;
        svg.addEventListener("pointerdown", event => {
            if (event.target.closest(".svg-node")) return;
            const view = graphViews.get(svg.id);
            if (!view) return;
            drag = { clientX: event.clientX, clientY: event.clientY, ...view };
            svg.setPointerCapture(event.pointerId);
        });
        svg.addEventListener("pointermove", event => {
            if (!drag) return;
            const bounds = svg.parentElement.getBoundingClientRect();
            const view = graphViews.get(svg.id);
            view.x = drag.x - (event.clientX - drag.clientX) * drag.width / bounds.width;
            view.y = drag.y - (event.clientY - drag.clientY) * drag.height / bounds.height;
            svg.setAttribute("viewBox", `${view.x} ${view.y} ${view.width} ${view.height}`);
        });
        const endDrag = () => { drag = null; };
        svg.addEventListener("pointerup", endDrag);
        svg.addEventListener("pointercancel", endDrag);
    });
}

function fitGraphCanvas(svg) {
    const container = svg.parentElement;
    const values = (svg.dataset.baseViewBox || svg.getAttribute("viewBox") || "0 0 1200 640").split(" ").map(Number);
    const aspectRatio = values[2] / values[3];
    const fittedWidth = Math.max(container.clientWidth, container.clientHeight * aspectRatio);
    svg.style.width = `${fittedWidth}px`;
}

function inspectFacilityNode(id, assetInfo, iconId, nameId, badgeId, metaId) {
    state.selectedNodeId = id;
    const rawAsset = state.infrastructure?.assets?.find(a => a.id === id) || assetInfo;
    const iconEl = document.getElementById(iconId);
    const nameEl = document.getElementById(nameId);
    const badgeEl = document.getElementById(badgeId);
    const metaEl = document.getElementById(metaId);

    if (iconEl) iconEl.textContent = rawAsset.icon || "●";
    if (nameEl) nameEl.textContent = rawAsset.name || id;

    if (badgeEl) {
        const status = assetInfo.status || "Status unavailable";
        badgeEl.textContent = status.toUpperCase();
        if (assetInfo.status === "failed") {
            badgeEl.style.background = "rgba(196, 73, 80, 0.15)";
            badgeEl.style.color = "#a83e42";
        } else if (assetInfo.status === "protected") {
            badgeEl.style.background = "rgba(128, 81, 139, 0.15)";
            badgeEl.style.color = "#70447b";
        } else if (assetInfo.status === "warning") {
            badgeEl.style.background = "rgba(169, 109, 22, 0.15)";
            badgeEl.style.color = "#8a570d";
        } else if (!assetInfo.status) {
            badgeEl.style.background = "rgba(148, 163, 184, 0.12)";
            badgeEl.style.color = "#94a3b8";
        } else {
            badgeEl.style.background = "rgba(52, 122, 82, 0.15)";
            badgeEl.style.color = "#2f744d";
        }
    }

    if (metaEl) {
        const category = rawAsset.category || "Infrastructure";
        const criticality = assetInfo.criticality ?? rawAsset.criticality ?? "--";
        const reqs = rawAsset.depends_on || [];
        const reqStr = reqs.length > 0
            ? reqs.map(r => state.infrastructure?.assets?.find(a => a.id === r)?.name || r).join(", ")
            : "Primary Source (No Prerequisites)";

        metaEl.textContent = `${category} · ID: ${id} · Criticality: ${criticality}/10 · Prerequisites: ${reqStr}`;
    }
}


// =====================================================
// UTILITY SANITIZATION
// =====================================================
function getAssetName(id) {
    return state.infrastructure?.assets?.find(asset => asset.id === id)?.name || id;
}

function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
