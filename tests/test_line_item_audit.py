
import copy
import json
from pathlib import Path

import pytest

from src.extraction.line_item_extractor import (
    extract_line_items_with_audit
)

ROOT = Path("/content/drive/MyDrive/FinGuard_AI")


def load_ocr():
    path = ROOT / "outputs/extracted_json/sample_finguard_invoice_ocr.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def add_line(data, text, bbox):
    data["lines"].append({
        "text": text,
        "bbox": bbox,
        "confidence": 0.99,
        "page": 1
    })


def test_missing_line_total_is_flagged():
    data = copy.deepcopy(load_ocr())
    add_line(data, "3", [826, 940, 852, 963])
    add_line(data, "2000.00", [960, 940, 1081, 963])
    add_line(data, "Wireless Mouse", [74, 945, 357, 968])

    result = extract_line_items_with_audit(data)

    assert result["status"] == "REVIEW"
    assert "MISSING_LINE_TOTAL" in result["incomplete_rows"][0]["reasons"]


def test_missing_quantity_is_flagged():
    data = copy.deepcopy(load_ocr())
    add_line(data, "2000.00", [960, 940, 1081, 963])
    add_line(data, "6000.00", [1151, 940, 1293, 963])
    add_line(data, "Wireless Mouse", [74, 945, 357, 968])

    result = extract_line_items_with_audit(data)

    assert result["status"] == "REVIEW"
    assert "MISSING_QUANTITY" in result["incomplete_rows"][0]["reasons"]


def test_missing_description_is_flagged():
    data = copy.deepcopy(load_ocr())
    add_line(data, "3", [826, 940, 852, 963])
    add_line(data, "2000.00", [960, 940, 1081, 963])
    add_line(data, "6000.00", [1151, 940, 1293, 963])

    result = extract_line_items_with_audit(data)

    assert result["status"] == "REVIEW"
    assert "MISSING_DESCRIPTION" in result["incomplete_rows"][0]["reasons"]


def test_valid_two_item_invoice_passes_audit():
    data = copy.deepcopy(load_ocr())
    add_line(data, "3", [826, 940, 852, 963])
    add_line(data, "2000.00", [960, 940, 1081, 963])
    add_line(data, "6000.00", [1151, 940, 1293, 963])
    add_line(data, "Wireless Mouse", [74, 945, 357, 968])

    result = extract_line_items_with_audit(data)

    assert result["status"] == "PASS"
    assert len(result["items"]) == 2
    assert result["incomplete_rows"] == []


def test_missing_required_header_raises_error():
    data = copy.deepcopy(load_ocr())
    data["lines"] = [
        line for line in data["lines"]
        if line.get("text", "").strip().upper() != "TOTAL"
    ]

    with pytest.raises(ValueError, match="Required invoice table headers"):
        extract_line_items_with_audit(data)



def test_description_only_row_is_flagged():
    data = copy.deepcopy(load_ocr())

    add_line(
        data,
        "Wireless Mouse",
        [74, 945, 357, 968]
    )

    result = extract_line_items_with_audit(data)

    assert result["status"] == "REVIEW"
    assert len(result["items"]) == 1
    assert len(result["incomplete_rows"]) == 1

    incomplete = result["incomplete_rows"][0]

    assert incomplete["detected_fields"]["description"] == "Wireless Mouse"
    assert set(incomplete["missing_fields"]) == {
        "quantity",
        "unit_price",
        "line_total"
    }



def test_multiline_description_is_merged():
    data = copy.deepcopy(load_ocr())

    add_line(data, "3", [826, 940, 852, 963])
    add_line(data, "2000.00", [960, 940, 1081, 963])
    add_line(data, "6000.00", [1151, 940, 1293, 963])
    add_line(data, "Wireless Mouse", [74, 945, 357, 968])
    add_line(
        data,
        "Ergonomic Bluetooth Edition",
        [74, 970, 430, 992]
    )

    result = extract_line_items_with_audit(data)

    assert result["status"] == "PASS"
    assert len(result["items"]) == 2
    assert result["incomplete_rows"] == []

    second_item = result["items"][1]

    assert second_item["description"] == (
        "Wireless Mouse Ergonomic Bluetooth Edition"
    )
    assert second_item["quantity"] == 3
    assert second_item["unit_price"] == 2000
    assert second_item["line_total"] == 6000
