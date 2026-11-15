
from pathlib import Path

from src.duplicate_detection.duplicate_detector import (
    calculate_file_hash,
    normalize_invoice_number,
    build_document_record,
    compare_documents,
)


def make_record(
    file_hash="hash_a",
    invoice_number="INV-2026-001",
    supplier_gstin="33ABCDE1234F1Z5",
    invoice_date="2026-11-14",
    grand_total="11800.00",
):
    return {
        "document_id": "test_document",
        "file_path": "test.png",
        "file_hash": file_hash,
        "invoice_number": invoice_number,
        "normalized_invoice_number": normalize_invoice_number(invoice_number),
        "supplier_gstin": supplier_gstin,
        "invoice_date": invoice_date,
        "grand_total": grand_total,
    }


def test_calculate_file_hash(tmp_path):
    file_path = tmp_path / "invoice.png"
    file_path.write_bytes(b"sample invoice content")

    first_hash = calculate_file_hash(file_path)
    second_hash = calculate_file_hash(file_path)

    assert first_hash == second_hash
    assert len(first_hash) == 64


def test_normalize_invoice_number():
    assert normalize_invoice_number("INV-2026/001") == "INV2026001"
    assert normalize_invoice_number(" inv 2026 001 ") == "INV2026001"


def test_build_document_record(tmp_path):
    file_path = tmp_path / "invoice.png"
    file_path.write_bytes(b"invoice image")

    invoice = {
        "document_id": "INV_TEST_001",
        "financial_details": {
            "grand_total": {"value": "11800.00"}
        },
        "parties": {
            "supplier_gstin": {"value": "33ABCDE1234F1Z5"}
        },
        "invoice_details": {
            "invoice_number": {"value": "INV-2026-001"},
            "invoice_date": {
                "value": "14-11-2026",
                "normalized_value": "2026-11-14",
            },
        },
    }

    record = build_document_record(invoice, file_path)

    assert record["document_id"] == "INV_TEST_001"
    assert record["normalized_invoice_number"] == "INV2026001"
    assert record["supplier_gstin"] == "33ABCDE1234F1Z5"
    assert record["invoice_date"] == "2026-11-14"
    assert record["grand_total"] == "11800.00"
    assert record["file_hash"] == calculate_file_hash(file_path)


def test_exact_file_duplicate():
    result = compare_documents(
        make_record(file_hash="same_hash"),
        make_record(file_hash="same_hash", invoice_number="OTHER-001"),
    )

    assert result["is_duplicate"] is True
    assert result["duplicate_type"] == "EXACT_FILE_DUPLICATE"
    assert result["confidence"] == 1.0


def test_invoice_identifier_duplicate():
    result = compare_documents(
        make_record(file_hash="hash_a"),
        make_record(file_hash="hash_b"),
    )

    assert result["is_duplicate"] is True
    assert result["duplicate_type"] == "INVOICE_IDENTIFIER_DUPLICATE"


def test_probable_duplicate():
    result = compare_documents(
        make_record(
            file_hash="hash_a",
            invoice_number="INV-2026-001",
        ),
        make_record(
            file_hash="hash_b",
            invoice_number="INV-2026-00I",
        ),
    )

    assert result["is_duplicate"] is True
    assert result["duplicate_type"] == "PROBABLE_DUPLICATE"
    assert result["confidence"] >= 0.90


def test_different_supplier_is_not_duplicate():
    result = compare_documents(
        make_record(),
        make_record(
            file_hash="hash_b",
            supplier_gstin="27ABCDE1234F1Z5",
            invoice_number="INV-2026-002",
        ),
    )

    assert result["is_duplicate"] is False
    assert result["duplicate_type"] == "NO_DUPLICATE_DETECTED"
