
from pathlib import Path
from typing import Any

from src.duplicate_detection.duplicate_detector import (
    build_document_record
)
from src.duplicate_detection.duplicate_registry import (
    check_and_register_document
)


def duplicate_detection_agent(
    state: dict[str, Any]
) -> dict[str, Any]:
    """Detect duplicate invoices using the persistent document registry."""

    invoice = state.get("invoice")
    file_path = state.get("file_path")

    if not isinstance(invoice, dict) or not file_path:
        return {
            "current_stage": "duplicate_detection",
            "duplicate_detection": {
                "status": "SKIPPED_REVIEW",
                "reason": "Invoice data or original document path is missing."
            },
            "agent_status": {
                **state.get("agent_status", {}),
                "duplicate_agent": "SKIPPED"
            },
            "overall_status": (
                "REVIEW"
                if state.get("overall_status") != "EXCEPTION"
                else "EXCEPTION"
            ),
            "human_review_required": True,
            "human_review_reason": [
                *state.get("human_review_reason", []),
                "Duplicate detection could not run because the source document or invoice data is missing."
            ]
        }

    try:
        financial = invoice.get("financial_details", {})
        parties = invoice.get("parties", {})
        details = invoice.get("invoice_details", {})

        required_fields = [
            financial.get("grand_total"),
            parties.get("supplier_gstin"),
            details.get("invoice_number"),
            details.get("invoice_date")
        ]

        if not all(
            isinstance(field, dict) and field.get("value") not in (None, "")
            for field in required_fields
        ):
            return {
                "current_stage": "duplicate_detection",
                "duplicate_detection": {
                    "status": "SKIPPED_REVIEW",
                    "reason": "Required invoice identity fields are incomplete."
                },
                "agent_status": {
                    **state.get("agent_status", {}),
                    "duplicate_agent": "SKIPPED"
                },
                "overall_status": (
                    "REVIEW"
                    if state.get("overall_status") != "EXCEPTION"
                    else "EXCEPTION"
                ),
                "human_review_required": True,
                "human_review_reason": [
                    *state.get("human_review_reason", []),
                    "Duplicate detection skipped because invoice identity fields are incomplete."
                ]
            }

        source_path = Path(file_path)

        if not source_path.is_file():
            raise FileNotFoundError(
                f"Source document does not exist: {source_path}"
            )

        document_record = build_document_record(
            invoice,
            source_path
        )

        registry_result = check_and_register_document(
            document_record
        )

        is_duplicate = registry_result["is_duplicate"]

        if is_duplicate:
            status = "DUPLICATE_FOUND"
            agent_status = "DUPLICATE"
            overall_status = "EXCEPTION"

            reason = (
                "Duplicate invoice detected: "
                + registry_result["match"]["duplicate_type"]
            )
        else:
            status = "UNIQUE_REGISTERED"
            agent_status = "COMPLETED"
            overall_status = state.get(
                "overall_status",
                "PENDING_VERIFICATION"
            )
            reason = "Invoice is unique and was registered successfully."

        completed = list(state.get("completed_agents", []))

        if "duplicate_agent" not in completed:
            completed.append("duplicate_agent")

        reasons = list(state.get("human_review_reason", []))

        if is_duplicate:
            reasons.append(reason)

        return {
            "duplicate_detection": {
                **registry_result,
                "status": status,
                "document_record": document_record
            },
            "current_stage": "duplicate_detection",
            "completed_agents": completed,
            "agent_status": {
                **state.get("agent_status", {}),
                "duplicate_agent": agent_status
            },
            "overall_status": overall_status,
            "human_review_required": (
                state.get("human_review_required", False)
                or is_duplicate
            ),
            "human_review_reason": reasons
        }

    except Exception as exc:
        return {
            "current_stage": "duplicate_detection",
            "duplicate_detection": {
                "status": "ERROR",
                "reason": str(exc)
            },
            "agent_status": {
                **state.get("agent_status", {}),
                "duplicate_agent": "FAILED"
            },
            "overall_status": (
                "REVIEW"
                if state.get("overall_status") != "EXCEPTION"
                else "EXCEPTION"
            ),
            "human_review_required": True,
            "human_review_reason": [
                *state.get("human_review_reason", []),
                "Duplicate detection could not be completed."
            ],
            "errors": [
                *state.get("errors", []),
                {
                    "agent": "duplicate_agent",
                    "error": str(exc)
                }
            ]
        }
