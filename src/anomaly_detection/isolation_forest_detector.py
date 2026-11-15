
import numpy as np
from decimal import Decimal

FEATURE_NAMES = [
    "log_grand_total",
    "log_taxable_amount",
    "log_total_quantity",
    "log_quantity_per_item",
    "item_count",
    "log_avg_unit_price",
    "tax_ratio"
]


def create_feature_vector(
    grand_total,
    taxable_amount,
    total_quantity,
    item_count,
    avg_unit_price,
    tax_ratio
):
    quantity_per_item = (
        float(total_quantity) / max(int(item_count), 1)
    )

    values = [
        np.log1p(max(float(grand_total), 0)),
        np.log1p(max(float(taxable_amount), 0)),
        np.log1p(max(float(total_quantity), 0)),
        np.log1p(max(quantity_per_item, 0)),
        float(item_count),
        np.log1p(max(float(avg_unit_price), 0)),
        float(tax_ratio)
    ]

    return dict(zip(FEATURE_NAMES, values))


def extract_invoice_features(invoice):
    financial = invoice["financial_details"]
    items = invoice.get("items", [])

    taxable = Decimal(financial["taxable_amount"]["value"])
    grand_total = Decimal(financial["grand_total"]["value"])

    total_quantity = sum(
        int(item["quantity"]) for item in items
    )

    total_item_value = sum(
        Decimal(item["line_total"]) for item in items
    )

    avg_unit_price = (
        total_item_value / Decimal(total_quantity)
        if total_quantity > 0 else Decimal("0")
    )

    tax_ratio = (
        float((grand_total - taxable) / taxable)
        if taxable > 0 else 0.0
    )

    return create_feature_vector(
        grand_total,
        taxable,
        total_quantity,
        len(items),
        avg_unit_price,
        tax_ratio
    )


def predict_hybrid(model, features):
    import pandas as pd

    row = pd.DataFrame(
        [{name: features[name] for name in FEATURE_NAMES}],
        columns=FEATURE_NAMES
    )

    prediction = int(model.predict(row)[0])
    anomaly_score = float(model.decision_function(row)[0])

    # Prototype rules: these thresholds must be calibrated
    # against real business and industry-specific invoice data.
    quantity_per_item = (
        float(features["log_quantity_per_item"])
    )

    # Reverse log1p transformation.
    quantity_per_item = np.expm1(quantity_per_item)

    flags = []

    if quantity_per_item > 100:
        flags.append("EXTREMELY_HIGH_QUANTITY_PER_ITEM")

    if float(features["tax_ratio"]) > 0.30:
        flags.append("UNUSUAL_TAX_TO_VALUE_RATIO")

    model_flag = prediction == -1

    return {
        "prediction": (
            "REVIEW" if model_flag or flags else "NORMAL"
        ),
        "model_prediction": (
            "ANOMALY" if model_flag else "NORMAL"
        ),
        "rule_flags": flags,
        "is_anomaly": model_flag or bool(flags),
        "anomaly_score": anomaly_score,
        "review_required": model_flag or bool(flags)
    }
