
import json
import sqlite3
import uuid

from pathlib import Path
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def get_default_database_path():
    project_root = Path(__file__).resolve().parents[2]
    return (
        project_root
        / "datasets"
        / "processed"
        / "human_review.db"
    )


def get_connection(database_path=None):
    path = (
        Path(database_path)
        if database_path
        else get_default_database_path()
    )

    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_review_database(database_path=None):
    """Create review-case and immutable audit-event tables."""

    with get_connection(database_path) as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS review_cases (
                case_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                ai_decision TEXT NOT NULL
                    CHECK (ai_decision IN ('REVIEW', 'EXCEPTION')),
                review_status TEXT NOT NULL DEFAULT 'PENDING'
                    CHECK (
                        review_status IN (
                            'PENDING',
                            'APPROVED',
                            'REJECTED',
                            'CORRECTION_REQUESTED'
                        )
                    ),
                reasons_json TEXT NOT NULL,
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                reviewer_id TEXT,
                reviewer_decision TEXT,
                reviewer_comment TEXT,
                reviewed_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_review_status
            ON review_cases(review_status);

            CREATE INDEX IF NOT EXISTS idx_review_document
            ON review_cases(document_id);

            CREATE TABLE IF NOT EXISTS review_audit_events (
                event_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                event_data_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(case_id)
                    REFERENCES review_cases(case_id)
            );

            CREATE INDEX IF NOT EXISTS idx_audit_case
            ON review_audit_events(case_id);

            CREATE TRIGGER IF NOT EXISTS prevent_audit_event_update
            BEFORE UPDATE ON review_audit_events
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'Audit events are immutable: UPDATE prohibited.'
                );
            END;

            CREATE TRIGGER IF NOT EXISTS prevent_audit_event_delete
            BEFORE DELETE ON review_audit_events
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'Audit events are immutable: DELETE prohibited.'
                );
            END;
        """)

    return str(
        Path(database_path)
        if database_path
        else get_default_database_path()
    )


def create_review_case(
    document_id,
    ai_decision,
    reasons,
    report=None,
    database_path=None
):
    """Create a pending human-review case for REVIEW or EXCEPTION."""

    if not document_id or not str(document_id).strip():
        raise ValueError("A valid document_id is required.")

    ai_decision = str(ai_decision).upper()

    if ai_decision not in {"REVIEW", "EXCEPTION"}:
        raise ValueError(
            "Only REVIEW or EXCEPTION decisions can enter the review queue."
        )

    if not isinstance(reasons, list):
        raise ValueError("Reasons must be supplied as a list.")

    if report is not None and not isinstance(report, dict):
        raise ValueError("Report must be a dictionary.")

    now = utc_now()
    case_id = str(uuid.uuid4())

    with get_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO review_cases (
                case_id, document_id, ai_decision,
                review_status, reasons_json, report_json,
                created_at, updated_at
            )
            VALUES (?, ?, ?, 'PENDING', ?, ?, ?, ?)
            """,
            (
                case_id,
                str(document_id),
                ai_decision,
                json.dumps(reasons, ensure_ascii=False),
                json.dumps(report or {}, ensure_ascii=False),
                now,
                now
            )
        )

        connection.execute(
            """
            INSERT INTO review_audit_events (
                event_id, case_id, event_type,
                actor_id, event_data_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                case_id,
                "CASE_CREATED",
                "SYSTEM",
                json.dumps({
                    "ai_decision": ai_decision,
                    "document_id": str(document_id)
                }),
                now
            )
        )

    return get_review_case(case_id, database_path)


def _row_to_dict(row):
    if row is None:
        return None

    result = dict(row)
    result["reasons"] = json.loads(result.pop("reasons_json"))
    result["report"] = json.loads(result.pop("report_json"))

    return result


def get_review_case(case_id, database_path=None):
    with get_connection(database_path) as connection:
        row = connection.execute(
            "SELECT * FROM review_cases WHERE case_id = ?",
            (case_id,)
        ).fetchone()

    return _row_to_dict(row)


def list_pending_reviews(database_path=None):
    with get_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM review_cases
            WHERE review_status = 'PENDING'
            ORDER BY created_at ASC
            """
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def record_review_decision(
    case_id,
    reviewer_id,
    decision,
    comment="",
    database_path=None
):
    """Record a human decision exactly once for a pending case."""

    if not reviewer_id or not str(reviewer_id).strip():
        raise ValueError("A valid reviewer_id is required.")

    decision = str(decision).upper()

    decision_mapping = {
        "APPROVE": "APPROVED",
        "REJECT": "REJECTED",
        "REQUEST_CORRECTION": "CORRECTION_REQUESTED"
    }

    if decision not in decision_mapping:
        raise ValueError(
            "Decision must be APPROVE, REJECT, or REQUEST_CORRECTION."
        )

    if not isinstance(comment, str):
        raise ValueError("Reviewer comment must be text.")

    new_status = decision_mapping[decision]
    now = utc_now()

    with get_connection(database_path) as connection:
        cursor = connection.execute(
            """
            UPDATE review_cases
            SET review_status = ?,
                updated_at = ?,
                reviewer_id = ?,
                reviewer_decision = ?,
                reviewer_comment = ?,
                reviewed_at = ?
            WHERE case_id = ?
              AND review_status = 'PENDING'
            """,
            (
                new_status,
                now,
                str(reviewer_id),
                decision,
                comment,
                now,
                case_id
            )
        )

        if cursor.rowcount != 1:
            exists = connection.execute(
                "SELECT 1 FROM review_cases WHERE case_id = ?",
                (case_id,)
            ).fetchone()

            if exists is None:
                raise ValueError("Review case not found.")

            raise ValueError(
                "This review case has already received a decision."
            )

        connection.execute(
            """
            INSERT INTO review_audit_events (
                event_id, case_id, event_type,
                actor_id, event_data_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                case_id,
                "REVIEW_DECISION",
                str(reviewer_id),
                json.dumps({
                    "decision": decision,
                    "review_status": new_status,
                    "comment": comment
                }, ensure_ascii=False),
                now
            )
        )

    return get_review_case(case_id, database_path)


def get_review_audit_history(case_id, database_path=None):
    with get_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM review_audit_events
            WHERE case_id = ?
            ORDER BY created_at ASC, rowid ASC
            """,
            (case_id,)
        ).fetchall()

    events = []

    for row in rows:
        event = dict(row)
        event["event_data"] = json.loads(
            event.pop("event_data_json")
        )
        events.append(event)

    return events
