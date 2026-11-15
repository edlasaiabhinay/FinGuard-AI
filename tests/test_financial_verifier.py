
from src.verification.financial_verifier import verify_invoice


def make_invoice(second_line_total=6000):
    return {
        "document_id": "pytest_multi_item",
        "parties": {
            "supplier_gstin": {"value": "33ABCDE1234F1Z5"},
            "customer_gstin": {"value": "33XYZDE5678F1Z2"}
        },
        "items": [
            {
                "description": "Laptop Accessories",
                "quantity": 2,
                "unit_price": 5000,
                "line_total": 10000
            },
            {
                "description": "Wireless Mouse",
                "quantity": 3,
                "unit_price": 2000,
                "line_total": second_line_total
            }
        ],
        "financial_details": {
            "taxable_amount": {"value": "16000.00"},
            "cgst": {"value": "1440.00"},
            "sgst": {"value": "1440.00"},
            "igst": None,
            "grand_total": {"value": "18880.00"}
        }
    }


OCR_TEXT = """
CGST (9%): Rs. 1440.00
SGST (9%): Rs. 1440.00
"""


def test_valid_multi_item_invoice():
    report = verify_invoice(make_invoice(), OCR_TEXT)

    assert report["summary"]["total_checks"] == 7
    assert report["summary"]["passed"] == 7
    assert report["summary"]["failed"] == 0
    assert report["summary"]["overall_status"] == "PASS"


def test_incorrect_line_item_is_detected():
    report = verify_invoice(
        make_invoice(second_line_total=6500),
        OCR_TEXT
    )

    assert report["summary"]["failed"] >= 2
    assert report["summary"]["overall_status"] == "EXCEPTION"
