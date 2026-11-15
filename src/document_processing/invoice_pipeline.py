from copy import deepcopy

from src.extraction.line_item_extractor import (
    extract_line_items_wordlevel
)
from src.verification.financial_verifier import verify_invoice
from src.verification.po_matcher import verify_invoice_against_po


def process_invoice(
    ocr_data,
    invoice_data,
    ocr_text=None,
    purchase_order=None
):
    """
    Orchestrate word-level extraction, financial verification,
    and optional purchase-order matching.

    Original input dictionaries are never modified.
    """

    invoice = deepcopy(invoice_data)

    if ocr_text is None:
        ocr_text = "\n".join(
            line.get("text", "")
            for line in ocr_data.get("lines", [])
        )

    extraction = extract_line_items_wordlevel(ocr_data)

    result = {
        "document_id": invoice.get("document_id"),
        "extraction": extraction,
        "financial_verification": None,
        "po_verification": None,
        "summary": {
            "overall_status": "REVIEW",
            "extraction_status": extraction["status"],
            "financial_status": "NOT_RUN",
            "po_status": "NOT_RUN"
        }
    }

    # Never verify an invoice using incomplete line-item data.
    if extraction["status"] != "PASS" or not extraction["items"]:
        result["summary"]["overall_status"] = "REVIEW"
        return result

    # Word-level extraction is the authoritative item source.
    invoice["items"] = extraction["items"]

    financial_report = verify_invoice(invoice, ocr_text)
    result["financial_verification"] = financial_report

    financial_status = financial_report["summary"]["overall_status"]
    result["summary"]["financial_status"] = financial_status

    po_status = "NOT_RUN"

    if purchase_order is not None:
        po_report = verify_invoice_against_po(
            invoice,
            purchase_order
        )
        result["po_verification"] = po_report
        po_status = po_report["summary"]["overall_status"]
        result["summary"]["po_status"] = po_status

    # Combine results without hiding exceptions or review conditions.
    if financial_status == "EXCEPTION" or po_status == "EXCEPTION":
        overall_status = "EXCEPTION"
    elif financial_status != "PASS":
        overall_status = "REVIEW"
    elif po_status in ("REVIEW", "NOT_RUN"):
        overall_status = "REVIEW" if po_status == "REVIEW" else "PASS"
    elif po_status == "MATCH":
        overall_status = "PASS"
    else:
        overall_status = "REVIEW"

    result["summary"]["overall_status"] = overall_status

    return result
