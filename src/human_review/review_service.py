
import json
import sqlite3
import uuid

from datetime import datetime, timezone

from src.human_review.database import (
    get_connection,
    get_review_case,
    list_pending_reviews,
    record_review_decision,
    get_review_audit_history,
)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def enqueue_review_case(
    document_id,
    ai_decision,
    reasons,
    report=None,
    database_path=None,
):
    """
    Add a REVIEW or EXCEPTION document to the human-review queue.

    If the same document already has a pending case, return that case
    instead of creating another one.
    """

    if not document_id or not str(document_id).strip():
        raise ValueError("A valid document_id is required.")

    ai_decision = str(ai_decision).upper()

    if ai_decision not in {"REVIEW", "EXCEPTION"}:
        raise ValueError(
            "Only REVIEW or EXCEPTION decisions can enter the review queue."
        )

    if not isinstance(reasons, list):
        raise ValueError("Reasons must be a list.")

    if report is not None and not isinstance(report, dict):
        raise ValueError("Report must be a dictionary.")

    document_id = str(document_id).strip()
    now = _utc_now()
    case_id = str(uuid.uuid4())

    # BEGIN IMMEDIATE serializes concurrent queue submissions.
    with get_connection(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")

        existing = connection.execute(
            """
            SELECT case_id
            FROM review_cases
            WHERE document_id = ?
              AND review_status = 'PENDING'
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (document_id,)
        ).fetchone()

        if existing:
            existing_case_id = existing["case_id"]
            connection.commit()

            return {
                "created": False,
                "message": "A pending review case already exists.",
                "case": get_review_case(
                    existing_case_id,
                    database_path
                ),
            }

        connection.execute(
            """
            INSERT INTO review_cases (
                case_id,
                document_id,
                ai_decision,
                review_status,
                reasons_json,
                report_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, 'PENDING', ?, ?, ?, ?)
            """,
            (
                case_id,
                document_id,
                ai_decision,
                json.dumps(reasons, ensure_ascii=False),
                json.dumps(report or {}, ensure_ascii=False, default=str),
                now,
                now,
            )
        )

        connection.execute(
            """
            INSERT INTO review_audit_events (
                event_id,
                case_id,
                event_type,
                actor_id,
                event_data_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                case_id,
                "CASE_CREATED",
                "SYSTEM",
                json.dumps({
                    "document_id": document_id,
                    "ai_decision": ai_decision,
                }),
                now,
            )
        )

        connection.commit()

    return {
        "created": True,
        "message": "Review case successfully created.",
        "case": get_review_case(case_id, database_path),
    }


def get_review_queue(database_path=None):
    """Return all pending cases, oldest first."""

    return list_pending_reviews(database_path)


def get_review_case_details(case_id, database_path=None):
    """Return a review case together with its audit history."""

    case = get_review_case(case_id, database_path)

    if case is None:
        raise ValueError("Review case not found.")

    return {
        "case": case,
        "audit_history": get_review_audit_history(
            case_id,
            database_path
        ),
    }


def decide_review_case(
    case_id,
    reviewer_id,
    decision,
    comment="",
    database_path=None,
):
    """Submit a human decision for a pending review case."""

    return record_review_decision(
        case_id=case_id,
        reviewer_id=reviewer_id,
        decision=decision,
        comment=comment,
        database_path=database_path,
    )
