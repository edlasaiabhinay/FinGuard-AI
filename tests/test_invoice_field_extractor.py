
import json
import sys
from pathlib import Path

import pytest

ROOT = Path("/content/drive/MyDrive/FinGuard_AI")
sys.path.insert(0, str(ROOT))

from src.extraction.invoice_field_extractor import extract_invoice_fields


def make_ocr(lines):
    return {
        "source_file": "test_invoice.png",
        "lines": [
            {
                "line_index": i,
                "text": text,
                "confidence": 0.99,
                "bbox": [0, i * 50, 500, i * 50 + 30],
                "words": []
            }
            for i, text in enumerate(lines)
        ]
    }


def test_actual_sample_invoice():
    path = ROOT / "outputs/extracted_json/sample_finguard_invoice_ocr_runner_test.json"

    with path.open(encoding="utf-8") as f:
        ocr = json.load(f)

    result = extract_invoice_fields(ocr)

    assert result["invoice_details"]["invoice_number"]["value"] == "INV-2026-001"
    assert result["invoice_details"]["invoice_date"]["normalized_value"] == "2026-11-14"
    assert result["parties"]["supplier_gstin"]["value"] == "33ABCDE1234F1Z5"
    assert result["parties"]["customer_gstin"]["value"] == "33XYZDE5678F1Z2"
    assert result["financial_details"]["taxable_amount"]["value"] == "10000.00"
    assert result["financial_details"]["cgst"]["value"] == "900.00"
    assert result["financial_details"]["sgst"]["value"] == "900.00"
    assert result["financial_details"]["grand_total"]["value"] == "11800.00"


def test_missing_fields_return_none():
    ocr = make_ocr([
        "TAX INVOICE",
        "Thank you for your business!"
    ])

    result = extract_invoice_fields(ocr)

    assert result["invoice_details"]["invoice_number"] is None
    assert result["invoice_details"]["invoice_date"] is None
    assert result["parties"]["supplier_gstin"] is None
    assert result["parties"]["customer_gstin"] is None
    assert result["financial_details"]["grand_total"] is None


def test_alternate_date_format():
    ocr = make_ocr([
        "Invoice Number: INV-TEST-001",
        "Invoice Date: 14/11/2026"
    ])

    result = extract_invoice_fields(ocr)

    assert result["invoice_details"]["invoice_date"]["normalized_value"] == "2026-11-14"


def test_financial_amount_with_commas():
    ocr = make_ocr([
        "Taxable Amount: Rs. 1,25,000.00",
        "CGST (9%): Rs. 11,250.00",
        "SGST (9%): Rs. 11,250.00",
        "Grand Total: Rs. 1,47,500.00"
    ])

    result = extract_invoice_fields(ocr)
    financial = result["financial_details"]

    assert financial["taxable_amount"]["value"] == "125000.00"
    assert financial["cgst"]["value"] == "11250.00"
    assert financial["sgst"]["value"] == "11250.00"
    assert financial["grand_total"]["value"] == "147500.00"


def test_gstin_extraction():
    ocr = make_ocr([
        "Supplier GSTIN: 33ABCDE1234F1Z5",
        "Customer GSTIN: 33XYZDE5678F1Z2"
    ])

    result = extract_invoice_fields(ocr)

    assert result["parties"]["supplier_gstin"]["value"] == "33ABCDE1234F1Z5"
    assert result["parties"]["customer_gstin"]["value"] == "33XYZDE5678F1Z2"


def test_unparseable_date_is_not_normalized():
    ocr = make_ocr([
        "Invoice Date: 2026-99-99"
    ])

    result = extract_invoice_fields(ocr)

    date_field = result["invoice_details"]["invoice_date"]

    assert date_field["value"] == "2026-99-99"
    assert date_field["normalized_value"] is None


def test_po_number_extraction():
    ocr = make_ocr([
        "PO Number: PO-2026-001"
    ])

    result = extract_invoice_fields(ocr)

    assert result["invoice_details"]["po_number"]["value"] == "PO-2026-001"


def test_purchase_order_number_extraction():
    ocr = make_ocr([
        "Purchase Order No: PO-2026-002"
    ])

    result = extract_invoice_fields(ocr)

    assert result["invoice_details"]["po_number"]["value"] == "PO-2026-002"


def test_missing_po_number_returns_none():
    ocr = make_ocr([
        "Invoice Number: INV-TEST-001",
        "Invoice Date: 14/11/2026"
    ])

    result = extract_invoice_fields(ocr)

    assert result["invoice_details"]["po_number"] is None
