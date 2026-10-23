# AFTERSHOCK AI — Rachitha's Module

## Your job

You are responsible for the **Budget-Aware Intervention Optimizer**.

Your module answers:

> "We have a limited budget. Which infrastructure protection actions should we choose to reduce the simulated cascading disruption as much as possible?"

## What to do NOW

### 1. Install Python

Make sure Python 3 is installed.

### 2. Open this folder in VS Code

Open:

`aftershock_rachitha_optimizer`

### 3. Run the optimizer

Open the VS Code terminal and run:

```bash
python optimizer.py
```

If your computer uses `python3`, run:

```bash
python3 optimizer.py
```

You should see:

- the simulated budget
- baseline disruption
- optimized disruption
- recommended interventions
- total cost
- remaining budget

### 4. What you have completed

You now have a standalone working intervention-selection algorithm.

It:
1. Receives failed infrastructure.
2. Receives a maximum budget.
3. Tests possible intervention combinations.
4. Rejects combinations that exceed the budget.
5. Calculates disruption for each affordable combination.
6. Selects the lowest-disruption combination.
7. Returns the recommendation and cost.

## Important

This is the FIRST prototype.

The current `calculate_disruption()` contains demo scoring rules.

Later:

- **Maithri** will provide the real cascading-failure simulation.
- **Rachana** will connect this optimizer to Flask.
- **Poojashree** will display the optimizer result on the dashboard.

The final architecture should become:

Maithri's simulation
        ↓
failed assets
        ↓
Rachitha's optimizer
        ↓
best intervention
        ↓
Rachana's Flask API
        ↓
Poojashree's dashboard

## Do NOT change

Do not build the frontend or Flask API in this module unless your team asks you to help with integration.

## What to show your team

After running the file, send your team:

1. A screenshot of the terminal result.
2. The `optimizer.py` file.
3. The explanation:

"Given a budget, my optimizer tests affordable intervention combinations and selects the combination that minimizes simulated disruption."

## Next step

Once Maithri has the simulation working, replace the demo disruption logic with the actual simulation results.

That will make your optimizer a genuine part of the AFTERSHOCK AI system.
