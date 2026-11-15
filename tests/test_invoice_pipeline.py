import copy
import json
from pathlib import Path

from src.document_processing.invoice_pipeline import process_invoice

ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path):
    with open(ROOT / relative_path, encoding="utf-8") as f:
        return json.load(f)


def load_inputs():
    ocr = load_json(
        "outputs/extracted_json/"
        "sample_finguard_invoice_ocr_wordlevel.json"
    )
    invoice = load_json(
        "outputs/extracted_json/"
        "sample_finguard_invoice_fields.json"
    )
    po = load_json(
        "datasets/raw/purchase_orders/sample_finguard_po.json"
    )
    return ocr, invoice, po


def test_valid_invoice_runs_complete_pipeline():
    ocr, invoice, po = load_inputs()

    result = process_invoice(ocr, invoice, purchase_order=po)

    assert result["extraction"]["status"] == "PASS"
    assert result["financial_verification"]["summary"]["failed"] == 0
    assert result["po_verification"]["summary"]["failed"] == 0

    # Missing PO reference must remain a review condition.
    assert result["po_verification"]["summary"]["not_verifiable"] == 1
    assert result["summary"]["overall_status"] == "REVIEW"


def test_incomplete_extraction_blocks_verification():
    ocr, invoice, po = load_inputs()

    # Remove the quantity word from the actual invoice table row.
    for line in ocr["lines"]:
        if line["text"].strip() == "2":
            line["words"] = []

    result = process_invoice(ocr, invoice, purchase_order=po)

    assert result["extraction"]["status"] == "REVIEW"
    assert result["financial_verification"] is None
    assert result["po_verification"] is None
    assert result["summary"]["financial_status"] == "NOT_RUN"
    assert result["summary"]["po_status"] == "NOT_RUN"
    assert result["summary"]["overall_status"] == "REVIEW"


def test_financial_error_produces_exception():
    ocr, invoice, po = load_inputs()

    invoice["financial_details"]["grand_total"]["value"] = "9999.00"

    result = process_invoice(ocr, invoice, purchase_order=po)

    assert result["extraction"]["status"] == "PASS"
    assert result["financial_verification"]["summary"]["failed"] > 0
    assert result["summary"]["overall_status"] == "EXCEPTION"


def test_pipeline_does_not_modify_input_invoice():
    ocr, invoice, po = load_inputs()
    original_invoice = copy.deepcopy(invoice)

    process_invoice(ocr, invoice, purchase_order=po)

    assert invoice == original_invoice
