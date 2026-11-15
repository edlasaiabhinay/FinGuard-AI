import math
import warnings

import pytest

from src.anomaly_detection.anomaly_service import (
    analyze_invoice_anomaly,
    load_anomaly_models,
)
from src.anomaly_detection.isolation_forest_detector import FEATURE_NAMES


@pytest.fixture
def sample_field_extraction():
    return {
        "financial_details": {
            "taxable_amount": {"value": "10000.00"},
            "grand_total": {"value": "11800.00"},
        }
    }


@pytest.fixture
def sample_items():
    return [
        {
            "description": "Laptop Accessories",
            "quantity": 2,
            "unit_price": 5000.00,
            "line_total": "10000.00",
        }
    ]


def test_v2_models_load_with_expected_feature_order():
    models = load_anomaly_models()

    assert models["version"] == "2.0"
    assert models["features"] == FEATURE_NAMES
    assert len(models["features"]) == 7
    assert math.isfinite(models["isolation_forest_threshold"])
    assert math.isfinite(models["autoencoder_threshold"])


def test_anomaly_analysis_returns_finite_scores(
    sample_field_extraction,
    sample_items,
):
    result = analyze_invoice_anomaly(
        sample_field_extraction,
        sample_items,
    )

    assert result["status"] == "COMPLETED"
    assert result["prediction"] in {"NORMAL", "REVIEW"}

    assert math.isfinite(
        result["isolation_forest"]["decision_score"]
    )
    assert math.isfinite(
        result["autoencoder"]["reconstruction_error"]
    )

    assert result["isolation_forest"]["threshold"] == pytest.approx(
        0.01719751902956501
    )


def test_missing_taxable_amount_raises_clear_error(sample_items):
    field_extraction = {
        "financial_details": {
            "grand_total": {"value": "11800.00"}
        }
    }

    with pytest.raises(
        ValueError,
        match="Missing required financial field: taxable_amount",
    ):
        analyze_invoice_anomaly(field_extraction, sample_items)


def test_missing_grand_total_raises_clear_error(sample_items):
    field_extraction = {
        "financial_details": {
            "taxable_amount": {"value": "10000.00"}
        }
    }

    with pytest.raises(
        ValueError,
        match="Missing required financial field: grand_total",
    ):
        analyze_invoice_anomaly(field_extraction, sample_items)


def test_empty_items_raise_clear_error(sample_field_extraction):
    with pytest.raises(
        ValueError,
        match="At least one extracted line item is required",
    ):
        analyze_invoice_anomaly(sample_field_extraction, [])


def test_feature_name_warning_is_not_emitted(
    sample_field_extraction,
    sample_items,
):
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")

        analyze_invoice_anomaly(
            sample_field_extraction,
            sample_items,
        )

    sklearn_feature_warnings = [
        warning for warning in captured
        if "valid feature names" in str(warning.message)
    ]

    assert not sklearn_feature_warnings
