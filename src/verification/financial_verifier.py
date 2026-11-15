
import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


def money(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def get_value(field):
    if field is None:
        return None
    return money(field["value"])


def extract_tax_rate(ocr_text, tax_name):
    pattern = rf"{tax_name}\s*\(\s*(\d+(?:\.\d+)?)\s*%\s*\)"
    match = re.search(pattern, ocr_text, re.IGNORECASE)

    return Decimal(match.group(1)) if match else None


def add_check(checks, name, passed, expected, actual, message):
    checks.append({
        "check": name,
        "status": "PASS" if passed else "FAIL",
        "expected": str(expected),
        "actual": str(actual),
        "message": message
    })


def verify_invoice(invoice, ocr_text):
    checks = []

    financial = invoice["financial_details"]
    parties = invoice["parties"]
    items = invoice.get("items", [])

    taxable = get_value(financial.get("taxable_amount"))
    cgst = get_value(financial.get("cgst"))
    sgst = get_value(financial.get("sgst"))
    igst = get_value(financial.get("igst"))
    grand_total = get_value(financial.get("grand_total"))

    # 1. Verify each line item and calculate the item sum.
    calculated_item_sum = Decimal("0.00")

    for index, item in enumerate(items, start=1):
        quantity = Decimal(str(item["quantity"]))
        unit_price = money(item["unit_price"])
        extracted_total = money(item["line_total"])

        calculated_total = money(quantity * unit_price)
        calculated_item_sum += extracted_total

        add_check(
            checks,
            f"Item {index}: quantity × unit price",
            calculated_total == extracted_total,
            calculated_total,
            extracted_total,
            "Line-item arithmetic is correct."
            if calculated_total == extracted_total
            else "Line-item total does not match quantity × unit price."
        )

    # 2. Reconcile calculated item sum with taxable amount.
    calculated_item_sum = money(calculated_item_sum)

    if taxable is not None:
        add_check(
            checks,
            "Item totals vs taxable amount",
            calculated_item_sum == taxable,
            calculated_item_sum,
            taxable,
            "Calculated item totals match taxable amount."
            if calculated_item_sum == taxable
            else "Calculated item totals differ from taxable amount."
        )

    # 3. Determine GST classification using GSTIN state codes.
    supplier_gstin = parties["supplier_gstin"]["value"]
    customer_gstin = parties["customer_gstin"]["value"]

    supplier_state = supplier_gstin[:2]
    customer_state = customer_gstin[:2]

    intrastate = supplier_state == customer_state

    if intrastate:
        add_check(
            checks,
            "GST type consistency",
            igst is None and cgst is not None and sgst is not None,
            "CGST + SGST",
            "IGST" if igst is not None else "CGST/SGST",
            "GST components are consistent with the state-code heuristic."
            if igst is None and cgst is not None and sgst is not None
            else "GST components are incomplete or inconsistent."
        )
    else:
        add_check(
            checks,
            "GST type consistency",
            cgst is None and sgst is None and igst is not None,
            "IGST",
            "CGST/SGST" if cgst is not None or sgst is not None else "IGST",
            "GST components are consistent with the state-code heuristic."
            if cgst is None and sgst is None and igst is not None
            else "GST components are incomplete or inconsistent."
        )

    # 4. Verify applicable tax amounts when rates are present.
    if taxable is not None:
        if intrastate:
            for tax_name, actual in [("CGST", cgst), ("SGST", sgst)]:
                rate = extract_tax_rate(ocr_text, tax_name)

                if rate is not None and actual is not None:
                    expected = money(taxable * rate / Decimal("100"))

                    add_check(
                        checks,
                        f"{tax_name} calculation",
                        expected == actual,
                        expected,
                        actual,
                        f"{tax_name} matches extracted rate."
                        if expected == actual
                        else f"{tax_name} does not match extracted rate."
                    )
        else:
            rate = extract_tax_rate(ocr_text, "IGST")

            if rate is not None and igst is not None:
                expected = money(taxable * rate / Decimal("100"))

                add_check(
                    checks,
                    "IGST calculation",
                    expected == igst,
                    expected,
                    igst,
                    "IGST matches extracted rate."
                    if expected == igst
                    else "IGST does not match extracted rate."
                )

    # 5. Reconcile grand total.
    if taxable is not None and grand_total is not None:
        available_taxes = [
            amount for amount in (cgst, sgst, igst)
            if amount is not None
        ]

        expected_total = money(
            taxable + sum(available_taxes, Decimal("0.00"))
        )

        add_check(
            checks,
            "Grand total reconciliation",
            expected_total == grand_total,
            expected_total,
            grand_total,
            "Grand total matches taxable amount plus taxes."
            if expected_total == grand_total
            else "Grand total does not match taxable amount plus taxes."
        )

    passed = sum(c["status"] == "PASS" for c in checks)
    failed = sum(c["status"] == "FAIL" for c in checks)

    return {
        "document_id": invoice.get("document_id"),
        "summary": {
            "total_checks": len(checks),
            "passed": passed,
            "failed": failed,
            "overall_status": "PASS" if failed == 0 else "EXCEPTION"
        },
        "checks": checks
    }
