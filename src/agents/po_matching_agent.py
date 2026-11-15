
from typing import Any

from src.verification.po_matcher import verify_invoice_against_po


def po_matching_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Compare extracted invoice information with its purchase order."""

    invoice = state.get("invoice")
    purchase_order = state.get("purchase_order")

    if not isinstance(invoice, dict):
        return {
            "current_stage": "po_matching",
            "agent_status": {
                **state.get("agent_status", {}),
                "po_matching_agent": "FAILED"
            },
            "overall_status": "REVIEW",
            "human_review_required": True,
            "human_review_reason": [
                *state.get("human_review_reason", []),
                "Invoice data is unavailable for PO matching."
            ],
            "errors": [
                *state.get("errors", []),
                {
                    "agent": "po_matching_agent",
                    "error": "Missing or invalid invoice data."
                }
            ]
        }

    if not isinstance(purchase_order, dict) or not purchase_order:
        return {
            "current_stage": "po_matching",
            "po_verification": None,
            "agent_status": {
                **state.get("agent_status", {}),
                "po_matching_agent": "SKIPPED"
            },
            "overall_status": "REVIEW",
            "human_review_required": True,
            "human_review_reason": [
                *state.get("human_review_reason", []),
                "Purchase order was not supplied; PO matching could not run."
            ],
            "warnings": [
                *state.get("warnings", []),
                "PO matching skipped because no purchase order was supplied."
            ]
        }

    try:
        report = verify_invoice_against_po(invoice, purchase_order)

        summary = report.get("summary", {})

        raw_status = (
            summary.get("overall_status")
            or summary.get("status")
            or report.get("overall_status")
            or report.get("status")
            or ""
        )

        raw_status = str(raw_status).upper()

        if raw_status in {"MATCH", "PASS", "VERIFIED"}:
            verification_status = "MATCH"
            agent_status = "COMPLETED"
        elif raw_status in {"EXCEPTION", "FAIL", "FAILED", "MISMATCH"}:
            verification_status = "EXCEPTION"
            agent_status = "EXCEPTION"
        elif raw_status in {"REVIEW", "PARTIAL", "NOT_VERIFIABLE"}:
            verification_status = "REVIEW"
            agent_status = "REVIEW"
        else:
            verification_status = "REVIEW"
            agent_status = "REVIEW"

        reasons = list(state.get("human_review_reason", []))

        if verification_status != "MATCH":
            reasons.append(
                "PO matching requires review: "
                + (raw_status or "the matcher returned an unrecognized status.")
            )

        completed = list(state.get("completed_agents", []))

        if "po_matching_agent" not in completed:
            completed.append("po_matching_agent")

        overall_status = state.get("overall_status", "PENDING_VERIFICATION")

        if verification_status == "EXCEPTION":
            overall_status = "EXCEPTION"
        elif verification_status == "REVIEW" and overall_status != "EXCEPTION":
            overall_status = "REVIEW"

        return {
            "po_verification": report,
            "current_stage": "po_matching",
            "completed_agents": completed,
            "agent_status": {
                **state.get("agent_status", {}),
                "po_matching_agent": agent_status
            },
            "overall_status": overall_status,
            "human_review_required": (
                state.get("human_review_required", False)
                or verification_status != "MATCH"
            ),
            "human_review_reason": reasons
        }

    except Exception as exc:
        return {
            "current_stage": "po_matching",
            "po_verification": None,
            "agent_status": {
                **state.get("agent_status", {}),
                "po_matching_agent": "FAILED"
            },
            "overall_status": "REVIEW",
            "human_review_required": True,
            "human_review_reason": [
                *state.get("human_review_reason", []),
                "PO matching could not be completed."
            ],
            "errors": [
                *state.get("errors", []),
                {
                    "agent": "po_matching_agent",
                    "error": str(exc)
                }
            ]
        }
