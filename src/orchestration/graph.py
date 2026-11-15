
from typing import Any

from langgraph.graph import StateGraph, START, END

from src.orchestration.state import FinGuardState

from src.agents.extraction_agent import extraction_agent
from src.agents.financial_agent import financial_verification_agent
from src.agents.po_matching_agent import po_matching_agent
from src.agents.duplicate_agent import duplicate_detection_agent
from src.agents.anomaly_agent import anomaly_detection_agent
from src.human_review.review_service import enqueue_review_case


def supervisor_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Combine specialist-agent decisions into one final decision."""

    statuses = state.get("agent_status", {})

    financial_status = statuses.get("financial_agent", "SKIPPED")
    po_status = statuses.get("po_matching_agent", "SKIPPED")
    duplicate_status = statuses.get("duplicate_agent", "SKIPPED")
    anomaly_status = statuses.get("anomaly_agent", "SKIPPED")
    extraction_status = statuses.get("extraction_agent", "SKIPPED")

    exception_conditions = (
        financial_status == "EXCEPTION"
        or duplicate_status == "DUPLICATE"
        or state.get("overall_status") == "EXCEPTION"
    )

    review_conditions = (
        extraction_status != "COMPLETED"
        or financial_status != "COMPLETED"
        or po_status != "COMPLETED"
        or duplicate_status != "COMPLETED"
        or anomaly_status != "COMPLETED"
        or state.get("human_review_required", False)
        or state.get("errors")
    )

    if exception_conditions:
        decision = "EXCEPTION"
    elif review_conditions:
        decision = "REVIEW"
    else:
        decision = "PASS"

    reasons = list(state.get("human_review_reason", []))

    if decision == "EXCEPTION":
        reasons.append("One or more verification agents detected an exception.")
    elif decision == "REVIEW" and not reasons:
        reasons.append("One or more verification agents require further review.")


    # Submit non-PASS decisions to the persistent human-review queue.
    hitl_update = {}

    if decision in {"REVIEW", "EXCEPTION"}:
        document_id = state.get("document_id")

        if not document_id:
            hitl_update = {
                "hitl_submission_status": "SKIPPED_MISSING_DOCUMENT_ID"
            }
        else:
            review_report = {
                "document_id": document_id,
                "ai_decision": decision,
                "agent_status": statuses,
                "financial_verification": state.get("financial_verification"),
                "po_verification": state.get("po_verification"),
                "duplicate_detection": state.get("duplicate_detection"),
                "anomaly_detection": state.get("anomaly_detection"),
                "extraction": state.get("extraction"),
                "errors": state.get("errors", []),
                "warnings": state.get("warnings", [])
            }

            try:
                submission = enqueue_review_case(
                    document_id=document_id,
                    ai_decision=decision,
                    reasons=list(dict.fromkeys(reasons)),
                    report=review_report,
                    database_path=state.get("hitl_database_path")
                )

                hitl_update = {
                    "hitl_review_case_id": submission["case"]["case_id"],
                    "hitl_submission_status": (
                        "CREATED"
                        if submission["created"]
                        else "ALREADY_PENDING"
                    )
                }

            except Exception as exc:
                # Do not hide or downgrade the AI decision if queue
                # persistence fails. Surface the submission failure.
                hitl_update = {
                    "hitl_submission_status": "ERROR",
                    "hitl_submission_error": str(exc),
                    "warnings": [
                        *state.get("warnings", []),
                        "HITL review queue submission failed."
                    ]
                }
    else:
        hitl_update = {
            "hitl_submission_status": "NOT_REQUIRED"
        }

    return {
        "current_stage": "WORKFLOW_COMPLETED",
        "workflow_status": "COMPLETED",
        "overall_status": decision,
        "final_decision": decision,
        "human_review_required": decision != "PASS",
        "human_review_reason": list(dict.fromkeys(reasons)),
        "agent_status": {
            **statuses,
            "supervisor_agent": "COMPLETED"
        },
        "completed_agents": [
            *state.get("completed_agents", []),
            *(
                []
                if "supervisor_agent" in state.get("completed_agents", [])
                else ["supervisor_agent"]
            )
        ],
        **hitl_update
    }


def build_finguard_graph():
    """Build and compile the FinGuard multi-agent workflow."""

    workflow = StateGraph(FinGuardState)

    workflow.add_node("extraction", extraction_agent)
    workflow.add_node("financial", financial_verification_agent)
    workflow.add_node("po_matching", po_matching_agent)
    workflow.add_node("duplicate", duplicate_detection_agent)
    workflow.add_node("anomaly", anomaly_detection_agent)
    workflow.add_node("supervisor", supervisor_agent)

    workflow.add_edge(START, "extraction")
    workflow.add_edge("extraction", "financial")
    workflow.add_edge("financial", "po_matching")
    workflow.add_edge("po_matching", "duplicate")
    workflow.add_edge("duplicate", "anomaly")
    workflow.add_edge("anomaly", "supervisor")
    workflow.add_edge("supervisor", END)

    return workflow.compile()


finguard_graph = build_finguard_graph()
