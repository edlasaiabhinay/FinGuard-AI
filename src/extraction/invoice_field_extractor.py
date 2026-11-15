
import re
from datetime import datetime
from pathlib import Path


GSTIN_PATTERN = re.compile(
    r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b",
    re.IGNORECASE
)

NUMBER_PATTERN = re.compile(
    r"(?<![A-Z0-9])(?:Rs\.?\s*)?([0-9,]+(?:\.[0-9]{1,2})?)(?![A-Z0-9])",
    re.IGNORECASE
)


def _field(value, line, normalized_value=None, extra=None):
    if value is None:
        return None

    result = {
        "value": value,
        "source_line_id": line["line_index"] + 1,
        "confidence": float(line.get("confidence", 0.0))
    }

    if normalized_value is not None:
        result["normalized_value"] = normalized_value

    if extra:
        result.update(extra)

    return result


def _find_labeled_line(lines, patterns):
    for line in lines:
        text = line.get("text", "").strip()

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)

            if match:
                value = match.group(1).strip(" :-")

                if value:
                    return value, line

    return None, None


def _extract_gstin(text):
    match = GSTIN_PATTERN.search(text.upper())
    return match.group(0).upper() if match else None


def _extract_amount(line):
    text = line.get("text", "")

    matches = list(NUMBER_PATTERN.finditer(text))

    if not matches:
        return None

    # Select the final numeric amount on a labeled financial line.
    return matches[-1].group(1).replace(",", "")


def _extract_date(value):
    formats = (
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d-%m-%y",
        "%d/%m/%y"
    )

    for date_format in formats:
        try:
            parsed = datetime.strptime(value.strip(), date_format)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def extract_invoice_fields(ocr_data, document_id=None):
    """
    Extract structured invoice header, party and financial fields.

    Line items are intentionally excluded; they are extracted
    independently by the word-level line-item extractor.
    """

    lines = ocr_data.get("lines", [])

    if not lines:
        raise ValueError("OCR data contains no text lines.")

    invoice_number, invoice_number_line = _find_labeled_line(
        lines,
        [
            r"INVOICE\s*(?:NUMBER|NO\.?|#)\s*[:\-]?\s*(.+)",
            r"BILL\s*(?:NUMBER|NO\.?)\s*[:\-]?\s*(.+)"
        ]
    )

    invoice_date, invoice_date_line = _find_labeled_line(
        lines,
        [
            r"INVOICE\s*DATE\s*[:\-]?\s*(.+)",
            r"BILL\s*DATE\s*[:\-]?\s*(.+)"
        ]
    )

    po_number, po_number_line = _find_labeled_line(
        lines,
        [
            r"PURCHASE\s+ORDER\s*(?:NUMBER|NO\.?|#)\s*[:\-]?\s*(.+)",
            r"\bP\.?\s*O\.?\s*(?:NUMBER|NO\.?|#)\s*[:\-]?\s*(.+)"
        ]
    )

    supplier_name, supplier_line = _find_labeled_line(
        lines,
        [r"SUPPLIER(?:\s*NAME)?\s*[:\-]\s*(.+)"]
    )

    customer_name, customer_line = _find_labeled_line(
        lines,
        [
            r"CUSTOMER(?:\s*NAME)?\s*[:\-]\s*(.+)",
            r"BUYER(?:\s*NAME)?\s*[:\-]\s*(.+)"
        ]
    )

    supplier_gstin = None
    supplier_gstin_line = None
    customer_gstin = None
    customer_gstin_line = None

    # First identify explicitly labeled GSTIN fields.
    for line in lines:
        text = line.get("text", "").strip()
        gstin = _extract_gstin(text)

        if not gstin:
            continue

        upper = text.upper()

        if "CUSTOMER" in upper or "BUYER" in upper:
            customer_gstin = gstin
            customer_gstin_line = line

        elif "SUPPLIER" in upper or "VENDOR" in upper:
            supplier_gstin = gstin
            supplier_gstin_line = line

    # Fallback: first unlabeled GSTIN is treated as supplier GSTIN.
    # This is a positional heuristic and should be reviewed if ambiguous.
    if supplier_gstin is None:
        for line in lines:
            gstin = _extract_gstin(line.get("text", ""))

            if gstin and line is not customer_gstin_line:
                supplier_gstin = gstin
                supplier_gstin_line = line
                break

    # Financial fields.
    financial_patterns = {
        "taxable_amount": [
            r"TAXABLE\s*AMOUNT",
            r"SUB\s*TOTAL"
        ],
        "cgst": [r"\bCGST\b"],
        "sgst": [r"\bSGST\b"],
        "igst": [r"\bIGST\b"],
        "grand_total": [
            r"GRAND\s*TOTAL",
            r"TOTAL\s*PAYABLE",
            r"AMOUNT\s*PAYABLE",
            r"NET\s*PAYABLE"
        ]
    }

    financial_details = {}

    for field_name, patterns in financial_patterns.items():
        matched_line = None
        amount = None

        for line in lines:
            text = line.get("text", "")

            if any(
                re.search(pattern, text, re.IGNORECASE)
                for pattern in patterns
            ):
                amount = _extract_amount(line)

                if amount is not None:
                    matched_line = line
                    break

        if amount is None:
            financial_details[field_name] = None
        else:
            financial_details[field_name] = _field(
                amount,
                matched_line
            )

    # Extract GST rates from the OCR text for later verification.
    for tax_name in ("cgst", "sgst", "igst"):
        entry = financial_details[tax_name]

        if entry is None:
            continue

        line = next(
            (
                line for line in lines
                if line["line_index"] + 1 == entry["source_line_id"]
            ),
            None
        )

        if line:
            rate_match = re.search(
                r"(\d+(?:\.\d+)?)\s*%",
                line.get("text", "")
            )

            if rate_match:
                entry["rate_percent"] = rate_match.group(1)

    normalized_date = (
        _extract_date(invoice_date)
        if invoice_date else None
    )

    invoice_date_field = (
        _field(invoice_date, invoice_date_line)
        if invoice_date_line else None
    )

    if invoice_date_field is not None:
        invoice_date_field["normalized_value"] = normalized_date

    invoice_details = {
        "invoice_number": (
            _field(invoice_number, invoice_number_line)
            if invoice_number_line else None
        ),
        "invoice_date": invoice_date_field,
        "po_number": (
            _field(po_number, po_number_line)
            if po_number_line else None
        )
    }

    parties = {
        "supplier_name": (
            _field(supplier_name, supplier_line)
            if supplier_line else None
        ),
        "supplier_gstin": (
            _field(
                supplier_gstin,
                supplier_gstin_line,
                extra={"format_valid": True}
            )
            if supplier_gstin_line else None
        ),
        "customer_name": (
            _field(customer_name, customer_line)
            if customer_line else None
        ),
        "customer_gstin": (
            _field(
                customer_gstin,
                customer_gstin_line,
                extra={"format_valid": True}
            )
            if customer_gstin_line else None
        )
    }

    if document_id is None:
        document_id = (
            invoice_number
            if invoice_number
            else Path(ocr_data.get("source_file", "unknown")).stem
        )

    return {
        "document_id": document_id,
        "extraction_method": "PaddleOCR deterministic label extraction",
        "invoice_details": invoice_details,
        "parties": parties,
        "items": [],
        "financial_details": financial_details
    }
