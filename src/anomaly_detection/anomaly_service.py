
import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch

from src.anomaly_detection.autoencoder_detector import (
    InvoiceAutoencoder,
    predict_autoencoder,
)
from src.anomaly_detection.isolation_forest_detector import (
    FEATURE_NAMES,
    extract_invoice_features,
    predict_hybrid,
)


def _project_root():
    return Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def load_anomaly_models():
    """Load and validate the trained V2 anomaly models."""

    root = _project_root()

    if_config_path = (
        root / "models/isolation_forest/isolation_forest_v2_config.json"
    )
    ae_config_path = (
        root / "models/autoencoder/autoencoder_v2_config.json"
    )

    with if_config_path.open(encoding="utf-8") as file:
        if_config = json.load(file)

    with ae_config_path.open(encoding="utf-8") as file:
        ae_config = json.load(file)

    expected_features = list(FEATURE_NAMES)

    if if_config["features"] != expected_features:
        raise ValueError("Isolation Forest feature order mismatch.")

    if ae_config["features"] != expected_features:
        raise ValueError("Autoencoder feature order mismatch.")

    if_model = joblib.load(
        root / "models/isolation_forest/finguard_isolation_forest_v2.joblib"
    )

    if list(if_model.feature_names_in_) != expected_features:
        raise ValueError("Isolation Forest model feature order mismatch.")

    checkpoint = torch.load(
        root / "models/autoencoder/finguard_autoencoder_v2.pth",
        map_location="cpu",
        weights_only=True,
    )

    if checkpoint.get("feature_names") != expected_features:
        raise ValueError("Autoencoder checkpoint feature order mismatch.")

    if checkpoint.get("input_dim") != len(expected_features):
        raise ValueError("Autoencoder checkpoint input dimension mismatch.")

    autoencoder = InvoiceAutoencoder(input_dim=len(expected_features))
    autoencoder.load_state_dict(checkpoint["model_state_dict"])
    autoencoder.eval()

    scaler = joblib.load(
        root / "models/autoencoder/autoencoder_v2_scaler.joblib"
    )

    if scaler.n_features_in_ != len(expected_features):
        raise ValueError("Autoencoder scaler feature count mismatch.")

    return {
        "isolation_forest": if_model,
        "autoencoder": autoencoder,
        "scaler": scaler,
        "autoencoder_threshold": float(ae_config["threshold"]),
        "isolation_forest_threshold": float(if_config["selected_threshold"]),
        "features": expected_features,
        "version": "2.0",
        "device": "cpu",
    }


def _prepare_invoice(field_extraction, items):
    """Build the invoice structure expected by the feature extractor."""

    if not isinstance(items, list) or not items:
        raise ValueError("At least one extracted line item is required.")

    financial = field_extraction.get("financial_details", {})

    for name in ("taxable_amount", "grand_total"):
        field = financial.get(name)

        if not isinstance(field, dict) or field.get("value") in (None, ""):
            raise ValueError(f"Missing required financial field: {name}")

    normalized_items = []

    for index, item in enumerate(items):
        if item.get("quantity") in (None, ""):
            raise ValueError(f"Missing quantity in item {index}.")

        if item.get("line_total") in (None, ""):
            raise ValueError(f"Missing line total in item {index}.")

        normalized_items.append({
            "quantity": item["quantity"],
            "line_total": str(item["line_total"]),
        })

    return {
        "financial_details": financial,
        "items": normalized_items,
    }


def analyze_invoice_anomaly(field_extraction, items):
    """
    Run Isolation Forest V2 and Autoencoder V2.

    Anomaly predictions indicate unusual patterns requiring review.
    They do not establish fraud or GST non-compliance.
    """

    models = load_anomaly_models()

    invoice = _prepare_invoice(field_extraction, items)
    features = extract_invoice_features(invoice)

    feature_values = [
        float(features[name])
        for name in models["features"]
    ]

    if not np.isfinite(feature_values).all():
        raise ValueError("Invoice feature vector contains invalid values.")

    if_row = pd.DataFrame(
        [feature_values],
        columns=models["features"],
    )

    isolation_score = float(
        models["isolation_forest"].decision_function(if_row)[0]
    )

    isolation_threshold = models["isolation_forest_threshold"]
    isolation_is_anomaly = isolation_score < isolation_threshold

    isolation_result = {
        "prediction": (
            "ANOMALY" if isolation_is_anomaly else "NORMAL"
        ),
        "is_anomaly": bool(isolation_is_anomaly),
        "decision_score": isolation_score,
        "threshold": isolation_threshold,
        "threshold_method": "Validation F1 optimization",
    }

    autoencoder_result = predict_autoencoder(
        model=models["autoencoder"],
        scaler=models["scaler"],
        features=features,
        threshold=models["autoencoder_threshold"],
        feature_names=models["features"],
        device=torch.device("cpu"),
    )

    combined_anomaly = (
        isolation_result["is_anomaly"]
        or autoencoder_result["is_anomaly"]
    )

    return {
        "status": "COMPLETED",
        "model_version": models["version"],
        "prediction": "REVIEW" if combined_anomaly else "NORMAL",
        "is_anomaly": bool(combined_anomaly),
        "review_required": bool(combined_anomaly),
        "decision_method": "ISOLATION_FOREST_V2_OR_AUTOENCODER_V2",
        "isolation_forest": isolation_result,
        "autoencoder": autoencoder_result,
        "features": features,
        "limitations": [
            "Models were trained and evaluated on synthetic data.",
            "Anomaly detection identifies unusual patterns, not fraud.",
            "Real-world thresholds require independent business-data validation."
        ],
    }
