"""
Shared state schema for the FinGuard AI multi-agent workflow.

All agents read from and update this shared state.
Existing verification engines remain authoritative.
"""

from typing import Any, TypedDict


class FinGuardState(TypedDict, total=False):
    # Document identity and input
    document_id: str
    source_type: str
    file_path: str
    ocr_data: dict[str, Any]
    ocr_text: str
    purchase_order: dict[str, Any]

    # Extraction results
    invoice: dict[str, Any]
    field_extraction: dict[str, Any]
    extraction: dict[str, Any]

    # Specialist verification results
    financial_verification: dict[str, Any] | None
    po_verification: dict[str, Any] | None
    duplicate_detection: dict[str, Any] | None
    anomaly_detection: dict[str, Any] | None

    # Agent execution tracking
    current_stage: str
    completed_agents: list[str]
    agent_status: dict[str, str]

    # Decision and human review
    overall_status: str
    final_decision: str
    human_review_required: bool
    human_review_reason: list[str]

    # Human-in-the-Loop tracking
    hitl_review_case_id: str
    hitl_submission_status: str
    hitl_submission_error: str
    hitl_database_path: str

    # Error and warning tracking
    errors: list[dict[str, str]]
    warnings: list[str]

    # Workflow metadata
    workflow_status: str
    workflow_started_at: str
    workflow_completed_at: str
