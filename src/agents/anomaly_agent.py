
from typing import Any

from src.anomaly_detection.anomaly_service import (
    analyze_invoice_anomaly
)


def anomaly_detection_agent(
    state: dict[str, Any]
) -> dict[str, Any]:
    """Evaluate invoice anomalies using Isolation Forest and Autoencoder."""

    field_extraction = state.get("field_extraction")
    invoice = state.get("invoice")

    if not isinstance(field_extraction, dict) or not isinstance(invoice, dict):
        return {
            "current_stage": "anomaly_detection",
            "anomaly_detection": {
                "status": "NOT_RUN",
                "prediction": "REVIEW",
                "reason": "Required extraction data is unavailable."
            },
            "agent_status": {
                **state.get("agent_status", {}),
                "anomaly_agent": "SKIPPED"
            },
            "overall_status": (
                "EXCEPTION"
                if state.get("overall_status") == "EXCEPTION"
                else "REVIEW"
            ),
            "human_review_required": True,
            "human_review_reason": [
                *state.get("human_review_reason", []),
                "Anomaly detection could not run because extraction data is missing."
            ]
        }

    items = invoice.get("items", [])

    if not items:
        return {
            "current_stage": "anomaly_detection",
            "anomaly_detection": {
                "status": "NOT_RUN",
                "prediction": "REVIEW",
                "reason": "No extracted line items are available."
            },
            "agent_status": {
                **state.get("agent_status", {}),
                "anomaly_agent": "SKIPPED"
            },
            "overall_status": (
                "EXCEPTION"
                if state.get("overall_status") == "EXCEPTION"
                else "REVIEW"
            ),
            "human_review_required": True,
            "human_review_reason": [
                *state.get("human_review_reason", []),
                "Anomaly detection skipped because line items are missing."
            ]
        }

    try:
        report = analyze_invoice_anomaly(
            field_extraction,
            items
        )

        prediction = str(
            report.get("prediction", "REVIEW")
        ).upper()

        anomaly_detected = (
            prediction in {"REVIEW", "ANOMALY", "ANOMALOUS"}
            or report.get("is_anomaly") is True
            or report.get("anomaly_detected") is True
        )

        service_status = str(
            report.get("status", "")
        ).upper()

        if service_status != "COMPLETED":
            agent_status = "REVIEW"
            anomaly_detected = True
        elif anomaly_detected:
            agent_status = "REVIEW"
        else:
            agent_status = "COMPLETED"

        completed = list(state.get("completed_agents", []))

        if "anomaly_agent" not in completed:
            completed.append("anomaly_agent")

        reasons = list(state.get("human_review_reason", []))

        if anomaly_detected:
            reasons.append(
                "Anomaly detection flagged this invoice for human review. "
                "This is not proof of fraud."
            )

        overall_status = state.get(
            "overall_status",
            "PENDING_VERIFICATION"
        )

        # Never downgrade an existing duplicate or financial exception.
        if overall_status != "EXCEPTION" and anomaly_detected:
            overall_status = "REVIEW"

        return {
            "anomaly_detection": report,
            "current_stage": "anomaly_detection",
            "completed_agents": completed,
            "agent_status": {
                **state.get("agent_status", {}),
                "anomaly_agent": agent_status
            },
            "overall_status": overall_status,
            "human_review_required": (
                state.get("human_review_required", False)
                or anomaly_detected
            ),
            "human_review_reason": reasons
        }

    except Exception as exc:
        return {
            "current_stage": "anomaly_detection",
            "anomaly_detection": {
                "status": "ERROR",
                "prediction": "NOT_RUN",
                "reason": str(exc)
            },
            "agent_status": {
                **state.get("agent_status", {}),
                "anomaly_agent": "FAILED"
            },
            "overall_status": (
                "EXCEPTION"
                if state.get("overall_status") == "EXCEPTION"
                else "REVIEW"
            ),
            "human_review_required": True,
            "human_review_reason": [
                *state.get("human_review_reason", []),
                "Anomaly detection failed and requires manual review."
            ],
            "errors": [
                *state.get("errors", []),
                {
                    "agent": "anomaly_agent",
                    "error": str(exc)
                }
            ]
        }
