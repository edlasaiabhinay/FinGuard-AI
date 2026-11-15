import copy
import json
from pathlib import Path

from src.extraction.line_item_extractor import (
    extract_line_items_wordlevel
)

ROOT = Path(__file__).resolve().parents[1]
OCR_PATH = (
    ROOT / "outputs/extracted_json/"
    "sample_finguard_invoice_ocr_wordlevel.json"
)


def load_sample():
    with open(OCR_PATH, encoding="utf-8") as f:
        return json.load(f)


def make_word(text, x1, y1, x2, y2):
    return {
        "word_index": 0,
        "token_index": 0,
        "text": text,
        "bbox": [x1, y1, x2, y2],
        "line_confidence": 0.99
    }


def make_line(text, y1, y2, words):
    return {
        "page": 1,
        "line_index": 100 + len(words),
        "text": text,
        "confidence": 0.99,
        "bbox": [
            min(w["bbox"][0] for w in words),
            y1,
            max(w["bbox"][2] for w in words),
            y2
        ],
        "words": words
    }


def add_second_item(data):
    data["lines"].extend([
        make_line("Wireless Mouse", 885, 910, [
            make_word("Wireless", 106, 885, 220, 910),
            make_word("Mouse", 235, 885, 315, 910)
        ]),
        make_line("Ergonomic Design", 910, 935, [
            make_word("Ergonomic", 106, 910, 240, 935),
            make_word("Design", 255, 910, 330, 935)
        ]),
        make_line("3", 885, 910, [
            make_word("3", 832, 885, 837, 910)
        ]),
        make_line("2000.00", 885, 910, [
            make_word("2000.00", 957, 885, 1050, 910)
        ]),
        make_line("6000.00", 885, 910, [
            make_word("6000.00", 1139, 885, 1251, 910)
        ])
    ])
    return data


def test_actual_invoice_wordlevel_extraction():
    result = extract_line_items_wordlevel(load_sample())

    assert result["status"] == "PASS"
    assert len(result["items"]) == 1
    assert result["incomplete_rows"] == []

    item = result["items"][0]
    assert item["description"] == "Laptop Accessories"
    assert item["quantity"] == 2
    assert item["unit_price"] == 5000
    assert item["line_total"] == 10000


def test_wordlevel_multiple_items_and_wrapped_description():
    data = add_second_item(load_sample())
    result = extract_line_items_wordlevel(data)

    assert result["status"] == "PASS"
    assert len(result["items"]) == 2

    second = result["items"][1]
    assert second["description"] == "Wireless Mouse Ergonomic Design"
    assert second["quantity"] == 3
    assert second["unit_price"] == 2000
    assert second["line_total"] == 6000


def test_wordlevel_missing_quantity_is_flagged():
    data = add_second_item(load_sample())

    data["lines"] = [
        line for line in data["lines"]
        if not (
            line["text"].strip() == "3"
            and line["bbox"][1] == 885
        )
    ]

    result = extract_line_items_wordlevel(data)

    assert result["status"] == "REVIEW"
    assert len(result["items"]) == 1
    assert len(result["incomplete_rows"]) == 1
    assert "MISSING_QUANTITY" in (
        result["incomplete_rows"][0]["reasons"]
    )
