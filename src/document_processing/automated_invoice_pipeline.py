
from pathlib import Path

from src.extraction.invoice_field_extractor import extract_invoice_fields
from src.extraction.line_item_extractor import extract_line_items_wordlevel
from src.document_processing.invoice_pipeline import process_invoice


def _field_value(field):
    if field is None:
        return None
    return field.get("value")


def _missing_fields(field_extraction, paths):
    missing = []

    for section, field_name in paths:
        field = field_extraction.get(section, {}).get(field_name)

        if _field_value(field) in (None, ""):
            missing.append(f"{section}.{field_name}")

    return missing


def _attach_anomaly_detection(result):
    """Attach anomaly analysis without overwriting other verification results."""

    field_extraction = result.get("field_extraction", {})
    financial = field_extraction.get("financial_details", {})
    items = result.get("extraction", {}).get("items", [])

    missing = []

    for name in ("taxable_amount", "grand_total"):
        field = financial.get(name)
        if not isinstance(field, dict) or field.get("value") in (None, ""):
            missing.append(f"financial_details.{name}")

    if not isinstance(items, list) or not items:
        missing.append("extraction.items")

    if missing:
        anomaly_result = {
            "status": "NOT_RUN",
            "prediction": "NOT_RUN",
            "is_anomaly": None,
            "review_required": False,
            "reason": "Missing anomaly detection inputs.",
            "missing_fields": missing,
        }
        result["anomaly_detection"] = anomaly_result
        result["summary"]["anomaly_status"] = "NOT_RUN"
        return result

    try:
        from src.anomaly_detection.anomaly_service import (
            analyze_invoice_anomaly,
        )

        anomaly_result = analyze_invoice_anomaly(
            field_extraction=field_extraction,
            items=items,
        )

        result["anomaly_detection"] = anomaly_result
        result["summary"]["anomaly_status"] = anomaly_result["prediction"]

        if (
            anomaly_result.get("review_required")
            and result["summary"]["overall_status"] == "PASS"
        ):
            result["summary"]["overall_status"] = "REVIEW"

    except Exception as exc:
        anomaly_result = {
            "status": "ERROR",
            "prediction": "NOT_RUN",
            "is_anomaly": None,
            "review_required": True,
            "reason": f"{type(exc).__name__}: {exc}",
        }

        result["anomaly_detection"] = anomaly_result
        result["summary"]["anomaly_status"] = "NOT_RUN"

        if result["summary"]["overall_status"] == "PASS":
            result["summary"]["overall_status"] = "REVIEW"

    return result


def process_invoice_from_ocr(
    ocr_data,
    ocr_text=None,
    purchase_order=None,
    document_id=None
):
    """
    OCR output -> header extraction -> line-item extraction
    -> financial verification -> optional PO matching.
    """

    field_extraction = extract_invoice_fields(
        ocr_data,
        document_id=document_id
    )

    if ocr_text is None:
        ocr_text = "\n".join(
            line.get("text", "")
            for line in ocr_data.get("lines", [])
        )

    invoice = {
        "document_id": field_extraction["document_id"],
        "invoice_details": field_extraction["invoice_details"],
        "parties": field_extraction["parties"],
        "items": [],
        "financial_details": field_extraction["financial_details"],
        "po_number": _field_value(
            field_extraction["invoice_details"].get("po_number")
        )
    }

    financial_required = [
        ("parties", "supplier_gstin"),
        ("parties", "customer_gstin"),
        ("financial_details", "taxable_amount"),
        ("financial_details", "grand_total")
    ]

    missing_financial = _missing_fields(
        field_extraction,
        financial_required
    )

    if missing_financial:
        extraction = extract_line_items_wordlevel(ocr_data)

        early_result = {
            "document_id": invoice["document_id"],
            "field_extraction": field_extraction,
            "extraction": extraction,
            "financial_verification": None,
            "po_verification": None,
            "summary": {
                "overall_status": "REVIEW",
                "extraction_status": extraction["status"],
                "financial_status": "NOT_RUN",
                "po_status": "REVIEW" if purchase_order is not None else "NOT_RUN",
                "missing_financial_fields": missing_financial
            }
        }

        return _attach_anomaly_detection(early_result)

    po_required = [
        ("parties", "supplier_name"),
        ("parties", "supplier_gstin"),
        ("parties", "customer_name"),
        ("parties", "customer_gstin")
    ]

    missing_po = _missing_fields(field_extraction, po_required)

    can_run_po = (
        purchase_order is not None
        and not missing_po
    )

    result = process_invoice(
        ocr_data=ocr_data,
        invoice_data=invoice,
        ocr_text=ocr_text,
        purchase_order=purchase_order if can_run_po else None
    )

    result["field_extraction"] = field_extraction

    if purchase_order is not None and not can_run_po:
        result["po_verification"] = {
            "document_id": invoice["document_id"],
            "summary": {
                "overall_status": "REVIEW",
                "total_checks": 0,
                "passed": 0,
                "failed": 0,
                "not_verifiable": len(missing_po)
            },
            "checks": [],
            "missing_fields": missing_po
        }

        result["summary"]["po_status"] = "REVIEW"

        if result["summary"]["overall_status"] == "PASS":
            result["summary"]["overall_status"] = "REVIEW"

    return _attach_anomaly_detection(result)


def process_invoice_file(
    image_path,
    purchase_order=None,
    document_id=None,
    ocr_timeout=600
):
    """
    Complete image-to-verification workflow with persistent
    duplicate detection.

    Image -> OCR -> Extraction -> Duplicate detection
    -> Financial verification -> Optional PO matching.
    """

    from src.document_processing.ocr_runner import run_ocr
    from src.duplicate_detection.duplicate_detector import (
        build_document_record,
    )
    from src.duplicate_detection.duplicate_registry import (
        check_and_register_document,
    )

    image_path = Path(image_path)

    ocr_data = run_ocr(
        image_path,
        timeout=ocr_timeout
    )

    result = process_invoice_from_ocr(
        ocr_data=ocr_data,
        purchase_order=purchase_order,
        document_id=document_id
    )

    result["ocr_metadata"] = {
        "source_file": ocr_data.get("source_file"),
        "ocr_engine": ocr_data.get("ocr_engine"),
        "ocr_version": ocr_data.get("ocr_version"),
        "total_lines": ocr_data.get("total_lines"),
        "total_words": ocr_data.get("total_words"),
        "word_box_enabled": ocr_data.get("word_box_enabled")
    }

    # Duplicate matching requires these four extracted fields.
    duplicate_required = [
        ("invoice_details", "invoice_number"),
        ("invoice_details", "invoice_date"),
        ("parties", "supplier_gstin"),
        ("financial_details", "grand_total")
    ]

    field_extraction = result.get("field_extraction", {})
    missing_duplicate_fields = _missing_fields(
        field_extraction,
        duplicate_required
    )

    if not image_path.is_file():
        raise FileNotFoundError(
            f"Invoice image does not exist: {image_path}"
        )

    if missing_duplicate_fields:
        duplicate_result = {
            "status": "SKIPPED_REVIEW",
            "is_duplicate": None,
            "registered": False,
            "missing_fields": missing_duplicate_fields,
            "reason": (
                "Duplicate detection requires complete invoice identity fields."
            )
        }

        if result["summary"]["overall_status"] == "PASS":
            result["summary"]["overall_status"] = "REVIEW"

    else:
        document_record = build_document_record(
            field_extraction,
            image_path
        )

        duplicate_result = check_and_register_document(
            document_record
        )

        if duplicate_result["is_duplicate"]:
            result["summary"]["overall_status"] = "EXCEPTION"

    result["duplicate_detection"] = duplicate_result
    result["summary"]["duplicate_status"] = duplicate_result["registry_status"] if "registry_status" in duplicate_result else duplicate_result["status"]

    return result
