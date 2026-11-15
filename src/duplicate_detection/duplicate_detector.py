
import hashlib
import re
from decimal import Decimal
from rapidfuzz.fuzz import ratio


def calculate_file_hash(file_path):
    """Calculate SHA-256 hash of a document."""
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def normalize_invoice_number(value):
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())


def build_document_record(invoice, file_path):
    financial = invoice["financial_details"]
    parties = invoice["parties"]
    invoice_details = invoice["invoice_details"]

    invoice_date = invoice_details["invoice_date"]

    normalized_date = (
        invoice_date.get("normalized_value")
        or invoice_date["value"]
    )

    return {
        "document_id": invoice.get("document_id"),
        "file_path": str(file_path),
        "file_hash": calculate_file_hash(file_path),
        "invoice_number": invoice_details["invoice_number"]["value"],
        "normalized_invoice_number": normalize_invoice_number(
            invoice_details["invoice_number"]["value"]
        ),
        "supplier_gstin": parties["supplier_gstin"]["value"].upper(),
        "invoice_date": normalized_date,
        "grand_total": str(
            Decimal(financial["grand_total"]["value"])
        )
    }


def compare_documents(document_a, document_b):
    """Compare two invoice records and classify duplicate risk."""

    # Level 1: Exact document duplicate.
    if document_a["file_hash"] == document_b["file_hash"]:
        return {
            "is_duplicate": True,
            "duplicate_type": "EXACT_FILE_DUPLICATE",
            "confidence": 1.0,
            "reason": "Both documents have identical SHA-256 hashes."
        }

    same_supplier = (
        document_a["supplier_gstin"]
        == document_b["supplier_gstin"]
    )

    same_invoice_number = (
        document_a["normalized_invoice_number"]
        == document_b["normalized_invoice_number"]
    )

    same_date = (
        document_a["invoice_date"]
        == document_b["invoice_date"]
    )

    same_amount = (
        Decimal(document_a["grand_total"])
        == Decimal(document_b["grand_total"])
    )

    # Level 2: Same invoice identity, different document file.
    if same_supplier and same_invoice_number:
        return {
            "is_duplicate": True,
            "duplicate_type": "INVOICE_IDENTIFIER_DUPLICATE",
            "confidence": 0.99,
            "reason": (
                "Supplier GSTIN and invoice number match, "
                "although the document files differ."
            )
        }

    # Level 3: Probable duplicate using fuzzy invoice-number matching.
    similarity = ratio(
        document_a["normalized_invoice_number"],
        document_b["normalized_invoice_number"]
    )

    probable = (
        same_supplier
        and same_date
        and same_amount
        and similarity >= 90
    )

    if probable:
        return {
            "is_duplicate": True,
            "duplicate_type": "PROBABLE_DUPLICATE",
            "confidence": round(similarity / 100, 4),
            "reason": (
                "Same supplier, date, and amount, with a highly "
                "similar invoice number."
            ),
            "invoice_number_similarity": round(similarity, 2)
        }

    return {
        "is_duplicate": False,
        "duplicate_type": "NO_DUPLICATE_DETECTED",
        "confidence": 0.0,
        "reason": "The available duplicate matching conditions were not met."
    }
