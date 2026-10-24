"""
AFTERSHOCK AI — Demonstration Machine-Learning Risk Classifier
Module: risk_model.py

This module implements a synthetic-data Machine Learning workflow using Scikit-Learn's
RandomForestClassifier to categorize infrastructure assets into illustrative risk tiers.

IMPORTANT ACADEMIC DISCLAIMER:
------------------------------
This machine learning model is trained entirely on programmatically generated synthetic data
to demonstrate an AI/ML workflow for third-year computer science engineering coursework.
It is NOT validated against real-world municipal disaster records, and its outputs must NOT
be construed as real-world probabilities of infrastructure failure or used in real emergency planning.

Distinct Architectural Roles:
----------------------------
1. simulator.py: Uses explicit, deterministic dependency rules and graph BFS to track cascading failures.
2. risk_model.py: Demonstrates a separate statistical classification workflow predicting static
   vulnerability tiers based on multi-attribute facility features.
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from simulator import get_all_assets

# Fixed random seed for complete experimental reproducibility
MODEL_RANDOM_SEED = 42

# Demonstration class labels
RISK_LABELS = {
    0: "Low Demonstration Risk",
    1: "Medium Demonstration Risk",
    2: "High Demonstration Risk",
}

FEATURE_NAMES = [
    "criticality",          # Asset priority rating (1 - 10)
    "exposure_score",       # Environmental hazard vulnerability score (1 - 10)
    "dependency_count",     # Number of upstream dependencies required
    "redundancy_level",     # Backup redundancy rating (0 = none, 1 = partial, 2 = full)
]


def generate_synthetic_training_data(n_samples=250, seed=MODEL_RANDOM_SEED):
    """
    Generate synthetic feature vectors and illustrative hazard vulnerability labels.

    Features generated:
    -------------------
    - criticality: float in range [1.0, 10.0]
    - exposure_score: float in range [1.0, 10.0]
    - dependency_count: integer in range [0, 5]
    - redundancy_level: integer in range [0, 2]

    Returns:
    --------
    X : np.ndarray of shape (n_samples, 4)
    y : np.ndarray of shape (n_samples,)
    """
    rng = np.random.RandomState(seed)

    criticality = rng.uniform(1.0, 10.0, size=n_samples)
    exposure = rng.uniform(1.0, 10.0, size=n_samples)
    dependencies = rng.randint(0, 5, size=n_samples)
    redundancy = rng.randint(0, 3, size=n_samples)

    X = np.column_stack([criticality, exposure, dependencies, redundancy])

    # Illustrative scoring formula to generate synthetic ground-truth classes
    # Higher criticality + higher exposure + more dependencies - redundancy => higher risk
    composite_score = (
        0.35 * criticality
        + 0.40 * exposure
        + 0.35 * dependencies
        - 1.50 * redundancy
    )

    # Add minor synthetic noise to reflect real-world data imperfections
    noise = rng.normal(0.0, 0.4, size=n_samples)
    noisy_score = composite_score + noise

    # Discretize into 3 demonstration risk classes
    y = np.zeros(n_samples, dtype=int)
    y[noisy_score >= 5.0] = 1  # Medium Risk
    y[noisy_score >= 7.2] = 2  # High Risk

    return X, y


class InfrastructureRiskModel:
    """
    Wrapper class around scikit-learn's RandomForestClassifier for
    infrastructure risk tier categorization.
    """

    def __init__(self, random_state=MODEL_RANDOM_SEED):
        self.random_state = random_state
        self.feature_names = FEATURE_NAMES
        self.model = RandomForestClassifier(
            n_estimators=60,
            max_depth=5,
            random_state=self.random_state,
        )
        self.is_trained = False
        self._train()

    def _train(self):
        """Train the Random Forest model on programmatic synthetic data."""
        X_train, y_train = generate_synthetic_training_data(
            n_samples=300, seed=self.random_state
        )
        self.model.fit(X_train, y_train)
        self.is_trained = True

    def validate_features(self, features):
        """
        Validate input feature array or dictionary.

        Raises:
            ValueError: If features are malformed or out of allowable ranges.
        """
        if isinstance(features, dict):
            # Extract features from asset dict
            try:
                crit = float(features["criticality"])
                exp = float(features.get("exposure_score", 5.0))
                deps = len(features.get("depends_on", []))
                red = int(features.get("redundancy_level", 0))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Malformed feature dictionary: {exc}") from exc
            feature_vector = [crit, exp, deps, red]
        elif isinstance(features, (list, tuple, np.ndarray)):
            if len(features) != 4:
                raise ValueError(f"Expected exactly 4 features {self.feature_names}, got {len(features)}.")
            try:
                feature_vector = [float(val) for val in features]
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Feature values must be numeric: {exc}") from exc
        else:
            raise ValueError(f"Unsupported feature type: {type(features).__name__}")

        # Range bounds validation
        crit, exp, deps, red = feature_vector
        if not (0.0 <= crit <= 20.0):
            raise ValueError(f"Criticality out of expected range [0, 20]: {crit}")
        if not (0.0 <= exp <= 20.0):
            raise ValueError(f"Exposure score out of expected range [0, 20]: {exp}")
        if deps < 0:
            raise ValueError(f"Dependency count cannot be negative: {deps}")
        if red < 0:
            raise ValueError(f"Redundancy level cannot be negative: {red}")

        return np.array([feature_vector], dtype=float)

    def predict_risk(self, features):
        """
        Predict demonstration risk class and probability distribution for an asset.

        Returns:
            dict containing class label, illustrative confidence score,
            probabilities across classes, and input feature values.
        """
        if not self.is_trained:
            raise RuntimeError("Model is not initialized or trained.")

        X = self.validate_features(features)
        predicted_class = int(self.model.predict(X)[0])
        probabilities = self.model.predict_proba(X)[0]
        confidence = float(probabilities[predicted_class])

        return {
            "predicted_class": predicted_class,
            "risk_label": RISK_LABELS[predicted_class],
            "confidence_score": round(confidence, 3),
            "class_probabilities": {
                RISK_LABELS[i]: round(float(probabilities[i]), 3)
                for i in range(len(probabilities))
            },
            "features_used": {
                "criticality": float(X[0, 0]),
                "exposure_score": float(X[0, 1]),
                "dependency_count": int(X[0, 2]),
                "redundancy_level": int(X[0, 3]),
            },
            "disclaimer": "Demonstration output based on synthetic training data. Not a validated disaster probability.",
        }


# Singleton model instance
_RISK_MODEL_INSTANCE = InfrastructureRiskModel()


def get_risk_model():
    """Return the initialized demonstration risk model singleton."""
    return _RISK_MODEL_INSTANCE


def assess_all_asset_risks():
    """
    Run the Random Forest demonstration model over all configured assets.

    Returns:
        dict with asset assessments and overall summary.
    """
    model = get_risk_model()
    assets = get_all_assets()
    results = []

    for asset in assets:
        prediction = model.predict_risk(asset)
        results.append({
            "asset_id": asset["id"],
            "asset_name": asset["name"],
            "category": asset["category"],
            "risk_label": prediction["risk_label"],
            "confidence_score": prediction["confidence_score"],
            "class_probabilities": prediction["class_probabilities"],
            "features": prediction["features_used"],
        })

    return {
        "status": "success",
        "model_type": "RandomForestClassifier",
        "training_data": "Synthetic programmatic dataset (n=300, seed=42)",
        "feature_names": FEATURE_NAMES,
        "assets": results,
        "warning": (
            "The risk classifications use synthetic training data for demonstration. "
            "They are not validated real-world failure predictions."
        ),
    }


if __name__ == "__main__":
    print("Testing ML Risk Model directly...")
    report = assess_all_asset_risks()
    print(f"Model: {report['model_type']} | Training Data: {report['training_data']}")
    for a in report["assets"]:
        print(f"  {a['asset_name']:<26} -> {a['risk_label']:<26} (Confidence: {a['confidence_score']})")

