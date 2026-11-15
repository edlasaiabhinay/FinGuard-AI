
from typing import Any

from src.verification.financial_verifier import verify_invoice


def financial_verification_agent(
    state: dict[str, Any]
) -> dict[str, Any]:
    """
    Verify invoice arithmetic and GST using the existing
    deterministic financial verification engine.
    """

    invoice = state.get("invoice")

    if not isinstance(invoice, dict):
        return {
            "current_stage": "financial_verification",
            "agent_status": {
                **state.get("agent_status", {}),
                "financial_agent": "FAILED"
            },
            "overall_status": "REVIEW",
            "human_review_required": True,
            "human_review_reason": [
                *state.get("human_review_reason", []),
                "Extracted invoice data is missing."
            ],
            "errors": [
                *state.get("errors", []),
                {
                    "agent": "financial_agent",
                    "error": "Missing or invalid invoice data."
                }
            ]
        }

    items = invoice.get("items", [])
    financial_details = invoice.get("financial_details")
    parties = invoice.get("parties")

    if (
        not items
        or not isinstance(financial_details, dict)
        or not isinstance(parties, dict)
        or not isinstance(parties.get("supplier_gstin"), dict)
        or not isinstance(parties.get("customer_gstin"), dict)
    ):
        return {
            "current_stage": "financial_verification",
            "financial_verification": None,
            "agent_status": {
                **state.get("agent_status", {}),
                "financial_agent": "SKIPPED"
            },
            "overall_status": "REVIEW",
            "human_review_required": True,
            "human_review_reason": [
                *state.get("human_review_reason", []),
                "Invoice lacks required financial, party, or line-item data."
            ],
            "warnings": [
                *state.get("warnings", []),
                "Financial verification was not run because required data is incomplete."
            ]
        }

    ocr_text = state.get("ocr_text")

    if not ocr_text:
        ocr_data = state.get("ocr_data", {})
        ocr_text = "\\n".join(
            line.get("text", "")
            for line in ocr_data.get("lines", [])
        )

    try:
        report = verify_invoice(invoice, ocr_text)

        summary = report["summary"]
        verification_status = summary["overall_status"]

        agent_status = (
            "COMPLETED"
            if verification_status == "PASS"
            else "EXCEPTION"
        )

        reasons = list(state.get("human_review_reason", []))

        if verification_status != "PASS":
            reasons.append(
                f"Financial verification found {summary['failed']} failed check(s)."
            )

        completed = list(state.get("completed_agents", []))

        if "financial_agent" not in completed:
            completed.append("financial_agent")

        overall_status = state.get("overall_status", "REVIEW")

        if verification_status == "EXCEPTION":
            overall_status = "EXCEPTION"
        elif verification_status != "PASS" and overall_status == "PASS":
            overall_status = "REVIEW"

        return {
            "financial_verification": report,
            "current_stage": "financial_verification",
            "completed_agents": completed,
            "agent_status": {
                **state.get("agent_status", {}),
                "financial_agent": agent_status
            },
            "overall_status": overall_status,
            "human_review_required": (
                state.get("human_review_required", False)
                or verification_status != "PASS"
            ),
            "human_review_reason": reasons
        }

    except Exception as exc:
        return {
            "current_stage": "financial_verification",
            "financial_verification": None,
            "agent_status": {
                **state.get("agent_status", {}),
                "financial_agent": "FAILED"
            },
            "overall_status": "REVIEW",
            "human_review_required": True,
            "human_review_reason": [
                *state.get("human_review_reason", []),
                "Financial verification could not be completed."
            ],
            "errors": [
                *state.get("errors", []),
                {
                    "agent": "financial_agent",
                    "error": str(exc)
                }
            ]
        }
