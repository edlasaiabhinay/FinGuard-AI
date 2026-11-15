
import re
from decimal import Decimal, ROUND_HALF_UP
from rapidfuzz import fuzz, process


def money(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def normalize_text(value):
    return re.sub(r"\s+", " ", str(value).strip().lower())


def add_check(checks, name, status, expected, actual, message):
    checks.append({
        "check": name,
        "status": status,
        "expected": str(expected),
        "actual": str(actual),
        "message": message
    })


def verify_invoice_against_po(invoice, purchase_order):
    checks = []

    invoice_parties = invoice["parties"]
    po_supplier = purchase_order["supplier"]
    po_buyer = purchase_order["buyer"]

    # 1. Supplier identity
    invoice_supplier = invoice_parties["supplier_name"]["value"]
    po_supplier_name = po_supplier["name"]

    supplier_match = (
        normalize_text(invoice_supplier)
        == normalize_text(po_supplier_name)
    )

    add_check(
        checks,
        "Supplier name match",
        "PASS" if supplier_match else "FAIL",
        po_supplier_name,
        invoice_supplier,
        "Supplier names match."
        if supplier_match else "Supplier names differ."
    )

    supplier_gstin = invoice_parties["supplier_gstin"]["value"]
    supplier_gstin_match = supplier_gstin == po_supplier["gstin"]

    add_check(
        checks,
        "Supplier GSTIN match",
        "PASS" if supplier_gstin_match else "FAIL",
        po_supplier["gstin"],
        supplier_gstin,
        "Supplier GSTIN matches."
        if supplier_gstin_match else "Supplier GSTIN differs."
    )

    # 2. Buyer identity
    invoice_buyer = invoice_parties["customer_name"]["value"]
    po_buyer_name = po_buyer["name"]

    buyer_match = (
        normalize_text(invoice_buyer)
        == normalize_text(po_buyer_name)
    )

    add_check(
        checks,
        "Buyer name match",
        "PASS" if buyer_match else "FAIL",
        po_buyer_name,
        invoice_buyer,
        "Buyer names match."
        if buyer_match else "Buyer names differ."
    )

    buyer_gstin = invoice_parties["customer_gstin"]["value"]
    buyer_gstin_match = buyer_gstin == po_buyer["gstin"]

    add_check(
        checks,
        "Buyer GSTIN match",
        "PASS" if buyer_gstin_match else "FAIL",
        po_buyer["gstin"],
        buyer_gstin,
        "Buyer GSTIN matches."
        if buyer_gstin_match else "Buyer GSTIN differs."
    )

    # 3. PO approval status
    po_status = purchase_order.get("status", "").upper()
    approved = po_status == "APPROVED"

    add_check(
        checks,
        "Purchase order approval",
        "PASS" if approved else "FAIL",
        "APPROVED",
        po_status or "MISSING",
        "Purchase order is approved."
        if approved else "Purchase order is not approved."
    )

    # 4. PO reference number
    invoice_po_number = invoice.get("po_number")

    if invoice_po_number:
        reference_match = (
            invoice_po_number == purchase_order.get("po_number")
        )

        add_check(
            checks,
            "PO reference number",
            "PASS" if reference_match else "FAIL",
            purchase_order.get("po_number"),
            invoice_po_number,
            "PO reference matches."
            if reference_match else "Invoice references a different PO."
        )
    else:
        add_check(
            checks,
            "PO reference number",
            "NOT_VERIFIABLE",
            purchase_order.get("po_number"),
            "Not available in invoice",
            "Invoice does not contain a PO number."
        )

    # 5. Match invoice items to PO items using fuzzy descriptions.
    invoice_items = invoice.get("items", [])
    po_items = purchase_order.get("items", [])

    unmatched_po_indices = set(range(len(po_items)))
    matched_invoice_items = []

    for invoice_index, invoice_item in enumerate(invoice_items, start=1):
        if not unmatched_po_indices:
            add_check(
                checks,
                f"Item {invoice_index}: PO item match",
                "FAIL",
                "Available PO item",
                invoice_item["description"],
                "No unmatched PO item remains."
            )
            continue

        candidates = {
            index: po_items[index]["description"]
            for index in unmatched_po_indices
        }

        best = process.extractOne(
            invoice_item["description"],
            list(candidates.values()),
            scorer=fuzz.token_sort_ratio
        )

        if best is None:
            add_check(
                checks,
                f"Item {invoice_index}: PO item match",
                "FAIL",
                "Matching PO item",
                invoice_item["description"],
                "No candidate PO item found."
            )
            continue

        matched_description, score, candidate_position = best
        matched_index = list(candidates.keys())[candidate_position]
        po_item = po_items[matched_index]

        if score < 90:
            add_check(
                checks,
                f"Item {invoice_index}: PO item match",
                "FAIL",
                "Description similarity >= 90",
                f"{score:.2f}",
                "Invoice description does not sufficiently match a PO item."
            )
            continue

        unmatched_po_indices.remove(matched_index)

        matched_invoice_items.append(invoice_item)

        add_check(
            checks,
            f"Item {invoice_index}: PO item match",
            "PASS",
            po_item["description"],
            invoice_item["description"],
            f"Description matched with similarity {score:.2f}."
        )

        # Quantity
        invoice_quantity = Decimal(str(invoice_item["quantity"]))
        po_quantity = Decimal(str(po_item["quantity"]))

        add_check(
            checks,
            f"Item {invoice_index}: quantity match",
            "PASS" if invoice_quantity == po_quantity else "FAIL",
            po_quantity,
            invoice_quantity,
            "Quantity matches PO."
            if invoice_quantity == po_quantity
            else "Invoice quantity differs from PO."
        )

        # Unit price
        invoice_price = money(invoice_item["unit_price"])
        po_price = money(po_item["unit_price"])

        add_check(
            checks,
            f"Item {invoice_index}: unit price match",
            "PASS" if invoice_price == po_price else "FAIL",
            po_price,
            invoice_price,
            "Unit price matches PO."
            if invoice_price == po_price
            else "Invoice unit price differs from PO."
        )

        # Line total
        invoice_total = money(invoice_item["line_total"])
        po_total = money(po_item["line_total"])

        add_check(
            checks,
            f"Item {invoice_index}: line total match",
            "PASS" if invoice_total == po_total else "FAIL",
            po_total,
            invoice_total,
            "Line total matches PO."
            if invoice_total == po_total
            else "Invoice line total differs from PO."
        )

    # Detect PO items missing from the invoice.
    for index in sorted(unmatched_po_indices):
        add_check(
            checks,
            f"PO item {index + 1}: invoice presence",
            "FAIL",
            po_items[index]["description"],
            "Missing from invoice",
            "An approved PO item is absent from the invoice."
        )

    # 6. Financial amount comparisons
    invoice_financial = invoice["financial_details"]
    po_financial = purchase_order["financial_details"]

    financial_fields = [
        ("taxable_amount", "Taxable amount"),
        ("cgst", "CGST"),
        ("sgst", "SGST"),
        ("igst", "IGST"),
        ("grand_total", "Grand total")
    ]

    for field, label in financial_fields:
        invoice_value = invoice_financial.get(field)
        po_value = po_financial.get(field)

        if invoice_value is None and po_value is None:
            continue

        if invoice_value is None or po_value is None:
            add_check(
                checks,
                f"{label} match",
                "FAIL",
                po_value if po_value is not None else "Not applicable",
                invoice_value if invoice_value is not None else "Missing",
                f"{label} is missing from one of the documents."
            )
            continue

        invoice_amount = money(invoice_value["value"])
        po_amount = money(po_value)

        add_check(
            checks,
            f"{label} match",
            "PASS" if invoice_amount == po_amount else "FAIL",
            po_amount,
            invoice_amount,
            f"{label} matches PO."
            if invoice_amount == po_amount
            else f"{label} differs from PO."
        )

    passed = sum(c["status"] == "PASS" for c in checks)
    failed = sum(c["status"] == "FAIL" for c in checks)
    not_verifiable = sum(
        c["status"] == "NOT_VERIFIABLE" for c in checks
    )

    if failed:
        overall_status = "EXCEPTION"
    elif not_verifiable:
        overall_status = "REVIEW"
    else:
        overall_status = "MATCH"

    return {
        "document_id": invoice.get("document_id"),
        "po_number": purchase_order.get("po_number"),
        "summary": {
            "total_checks": len(checks),
            "passed": passed,
            "failed": failed,
            "not_verifiable": not_verifiable,
            "overall_status": overall_status
        },
        "checks": checks
    }
