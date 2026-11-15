
from pathlib import Path

from src.duplicate_detection.duplicate_detector import normalize_invoice_number
from src.duplicate_detection.duplicate_registry import (
    load_registry,
    check_and_register_document,
)


def make_record(
    document_id,
    file_hash,
    invoice_number="INV-2026-001",
    supplier_gstin="33ABCDE1234F1Z5",
    invoice_date="2026-11-14",
    grand_total="11800.00",
):
    return {
        "document_id": document_id,
        "file_path": f"{document_id}.png",
        "file_hash": file_hash,
        "invoice_number": invoice_number,
        "normalized_invoice_number": normalize_invoice_number(invoice_number),
        "supplier_gstin": supplier_gstin,
        "invoice_date": invoice_date,
        "grand_total": grand_total,
    }


def test_register_unique_document(tmp_path):
    registry_path = tmp_path / "registry.json"

    result = check_and_register_document(
        make_record("INV001", "hash_001"),
        registry_path,
    )

    assert result["registry_status"] == "UNIQUE_REGISTERED"
    assert result["registered"] is True
    assert len(load_registry(registry_path)["documents"]) == 1


def test_detect_same_invoice_with_different_file_hash(tmp_path):
    registry_path = tmp_path / "registry.json"

    check_and_register_document(
        make_record("INV001", "hash_001"),
        registry_path,
    )

    result = check_and_register_document(
        make_record("INV002", "hash_002"),
        registry_path,
    )

    assert result["is_duplicate"] is True
    assert result["match"]["duplicate_type"] == "INVOICE_IDENTIFIER_DUPLICATE"
    assert result["registered"] is False


def test_duplicate_is_not_registered_again(tmp_path):
    registry_path = tmp_path / "registry.json"

    check_and_register_document(
        make_record("INV001", "hash_001"),
        registry_path,
    )

    check_and_register_document(
        make_record("INV002", "hash_002"),
        registry_path,
    )

    assert len(load_registry(registry_path)["documents"]) == 1


def test_registry_persists_after_reload(tmp_path):
    registry_path = tmp_path / "registry.json"

    check_and_register_document(
        make_record("INV001", "hash_001"),
        registry_path,
    )

    reloaded = load_registry(registry_path)

    assert len(reloaded["documents"]) == 1
    assert reloaded["documents"][0]["document_id"] == "INV001"


def test_probable_duplicate_detection(tmp_path):
    registry_path = tmp_path / "registry.json"

    check_and_register_document(
        make_record("INV001", "hash_001", "INV-2026-001"),
        registry_path,
    )

    result = check_and_register_document(
        make_record("INV002", "hash_002", "INV-2026-00I"),
        registry_path,
    )

    assert result["is_duplicate"] is True
    assert result["match"]["duplicate_type"] == "PROBABLE_DUPLICATE"


def test_different_supplier_is_registered(tmp_path):
    registry_path = tmp_path / "registry.json"

    check_and_register_document(
        make_record("INV001", "hash_001"),
        registry_path,
    )

    result = check_and_register_document(
        make_record(
            "INV002",
            "hash_002",
            invoice_number="INV-2026-002",
            supplier_gstin="27ABCDE1234F1Z5",
        ),
        registry_path,
    )

    assert result["is_duplicate"] is False
    assert result["registered"] is True
    assert len(load_registry(registry_path)["documents"]) == 2
