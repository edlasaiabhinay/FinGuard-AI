import copy
import json
from pathlib import Path

import pytest

from src.document_processing.automated_invoice_pipeline import (
    process_invoice_from_ocr,
    _attach_anomaly_detection,
)

ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path):
    with open(ROOT / relative_path, encoding="utf-8") as file:
        return json.load(file)


def load_inputs():
    ocr = load_json(
        "outputs/extracted_json/"
        "sample_finguard_invoice_ocr_wordlevel.json"
    )
    po = load_json(
        "datasets/raw/purchase_orders/sample_finguard_po.json"
    )
    return ocr, po


def test_anomaly_detection_integrates_with_complete_invoice():
    ocr, po = load_inputs()

    result = process_invoice_from_ocr(
        ocr_data=ocr,
        document_id="INTEGRATION_TEST",
        purchase_order=po,
    )

    assert result["anomaly_detection"]["status"] == "COMPLETED"
    assert result["summary"]["anomaly_status"] in {"NORMAL", "REVIEW"}

    assert result["financial_verification"] is not None
    assert result["financial_verification"]["summary"]["overall_status"] == "PASS"

    assert result["po_verification"] is not None
    assert result["summary"]["po_status"] == "REVIEW"

    # An anomaly must not overwrite financial or PO verification.
    if result["anomaly_detection"]["is_anomaly"]:
        assert result["summary"]["overall_status"] == "REVIEW"


def test_missing_anomaly_inputs_produce_not_run():
    result = {
        "field_extraction": {},
        "extraction": {"items": []},
        "summary": {"overall_status": "REVIEW"},
    }

    updated = _attach_anomaly_detection(result)

    assert updated["anomaly_detection"]["status"] == "NOT_RUN"
    assert updated["summary"]["anomaly_status"] == "NOT_RUN"
    assert "extraction.items" in updated["anomaly_detection"]["missing_fields"]


def test_anomaly_model_failure_does_not_crash_pipeline(monkeypatch):
    ocr, po = load_inputs()

    def failing_anomaly_model(*args, **kwargs):
        raise RuntimeError("Simulated model-loading failure")

    import src.anomaly_detection.anomaly_service as anomaly_service

    monkeypatch.setattr(
        anomaly_service,
        "analyze_invoice_anomaly",
        failing_anomaly_model,
    )

    result = process_invoice_from_ocr(
        ocr_data=ocr,
        document_id="MODEL_FAILURE_TEST",
        purchase_order=po,
    )

    assert result["anomaly_detection"]["status"] == "ERROR"
    assert result["summary"]["anomaly_status"] == "NOT_RUN"

    # Existing verification must remain available.
    assert result["financial_verification"] is not None
    assert result["financial_verification"]["summary"]["overall_status"] == "PASS"
    assert result["po_verification"] is not None

    assert result["summary"]["overall_status"] == "REVIEW"


def test_anomaly_integration_does_not_modify_ocr_input():
    ocr, po = load_inputs()
    original_ocr = copy.deepcopy(ocr)

    process_invoice_from_ocr(
        ocr_data=ocr,
        document_id="INPUT_IMMUTABILITY_TEST",
        purchase_order=po,
    )

    assert ocr == original_ocr
