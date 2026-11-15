"""
FinGuard AI — Invoice Extraction Specialist Agent.

Uses the existing deterministic header and word-level line-item
extractors. Does not implement a duplicate extraction engine.
"""

from typing import Any

from src.extraction.invoice_field_extractor import extract_invoice_fields
from src.extraction.line_item_extractor import extract_line_items_wordlevel


def extraction_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Extract invoice fields and line items into shared workflow state."""

    errors = list(state.get("errors", []))
    warnings = list(state.get("warnings", []))
    completed_agents = list(state.get("completed_agents", []))
    agent_status = dict(state.get("agent_status", {}))

    ocr_data = state.get("ocr_data")

    if not isinstance(ocr_data, dict) or not ocr_data:
        error = {
            "agent": "extraction_agent",
            "type": "INVALID_INPUT",
            "message": "Valid OCR data is required for invoice extraction.",
        }
        errors.append(error)
        agent_status["extraction_agent"] = "FAILED"

        return {
            "current_stage": "EXTRACTION_FAILED",
            "agent_status": agent_status,
            "errors": errors,
            "warnings": warnings,
            "workflow_status": "REVIEW",
            "overall_status": "REVIEW",
        }

    document_id = state.get("document_id")

    try:
        header_result = extract_invoice_fields(
            ocr_data,
            document_id=document_id,
        )

        line_result = extract_line_items_wordlevel(ocr_data)

        items = line_result.get("items", [])
        extraction_status = line_result.get("status", "REVIEW")

        invoice = {
            "document_id": header_result["document_id"],
            "invoice_details": header_result["invoice_details"],
            "parties": header_result["parties"],
            "items": items,
            "financial_details": header_result["financial_details"],
            "po_number": (
                header_result["invoice_details"]
                .get("po_number", {})
                .get("value")
                if isinstance(
                    header_result["invoice_details"].get("po_number"),
                    dict,
                )
                else None
            ),
        }

        if extraction_status != "PASS":
            warnings.append(
                "Line-item extraction requires review."
            )

        completed_agents.append("extraction_agent")
        agent_status["extraction_agent"] = (
            "COMPLETED" if extraction_status == "PASS" else "REVIEW"
        )

        ocr_text = state.get("ocr_text")
        if ocr_text is None:
            ocr_text = "\\n".join(
                line.get("text", "")
                for line in ocr_data.get("lines", [])
            )

        return {
            "document_id": header_result["document_id"],
            "ocr_text": ocr_text,
            "field_extraction": header_result,
            "extraction": line_result,
            "invoice": invoice,
            "current_stage": "EXTRACTION_COMPLETED",
            "completed_agents": completed_agents,
            "agent_status": agent_status,
            "errors": errors,
            "warnings": warnings,
            "workflow_status": (
                "READY_FOR_VERIFICATION"
                if extraction_status == "PASS"
                else "REVIEW"
            ),
            "overall_status": (
                "PENDING_VERIFICATION"
                if extraction_status == "PASS"
                else "REVIEW"
            ),
        }

    except Exception as exc:
        errors.append({
            "agent": "extraction_agent",
            "type": type(exc).__name__,
            "message": str(exc),
        })

        agent_status["extraction_agent"] = "FAILED"

        return {
            "current_stage": "EXTRACTION_FAILED",
            "agent_status": agent_status,
            "errors": errors,
            "warnings": warnings,
            "workflow_status": "REVIEW",
            "overall_status": "REVIEW",
        }
