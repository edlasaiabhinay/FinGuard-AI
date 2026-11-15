
import json
from pathlib import Path

from src.extraction.line_item_extractor import extract_line_items

ROOT = Path("/content/drive/MyDrive/FinGuard_AI")


def load_ocr():
    path = ROOT / "outputs/extracted_json/sample_finguard_invoice_ocr.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_single_item_extraction():
    items = extract_line_items(load_ocr())

    assert len(items) == 1
    assert items[0]["description"] == "Laptop Accessories"
    assert items[0]["quantity"] == 2
    assert items[0]["unit_price"] == 5000
    assert items[0]["line_total"] == 10000


def test_multiple_item_extraction():
    data = load_ocr()

    extra_rows = [
        ("3", [826, 940, 852, 963]),
        ("2000.00", [960, 940, 1081, 963]),
        ("6000.00", [1151, 940, 1293, 963]),
        ("Wireless Mouse", [74, 945, 357, 968])
    ]

    for text, bbox in extra_rows:
        data["lines"].append({
            "text": text,
            "bbox": bbox,
            "confidence": 0.99,
            "page": 1
        })

    items = extract_line_items(data)

    assert len(items) == 2
    assert items[1]["description"] == "Wireless Mouse"
    assert items[1]["quantity"] == 3
    assert items[1]["unit_price"] == 2000
    assert items[1]["line_total"] == 6000
