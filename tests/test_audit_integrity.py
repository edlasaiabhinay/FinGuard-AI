import sqlite3

import pytest

from src.human_review.database import (
    initialize_review_database,
    create_review_case,
    record_review_decision,
    get_review_audit_history,
)


@pytest.fixture
def audit_db(tmp_path):
    database = tmp_path / "audit_integrity_test.db"
    initialize_review_database(database)
    return database


def test_fresh_database_installs_audit_triggers(audit_db):
    with sqlite3.connect(audit_db) as connection:
        triggers = {
            row[0]
            for row in connection.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'trigger'
                  AND tbl_name = 'review_audit_events'
            """)
        }

    assert "prevent_audit_event_update" in triggers
    assert "prevent_audit_event_delete" in triggers


def test_audit_event_update_is_blocked(audit_db):
    case = create_review_case(
        "AUDIT-UPDATE-001",
        "REVIEW",
        ["Integrity test"],
        database_path=audit_db,
    )

    with sqlite3.connect(audit_db) as connection:
        event_id = connection.execute(
            "SELECT event_id FROM review_audit_events WHERE case_id = ?",
            (case["case_id"],),
        ).fetchone()[0]

        with pytest.raises(
            sqlite3.IntegrityError,
            match="UPDATE prohibited",
        ):
            connection.execute(
                """
                UPDATE review_audit_events
                SET actor_id = 'TAMPERED'
                WHERE event_id = ?
                """,
                (event_id,),
            )


def test_audit_event_delete_is_blocked(audit_db):
    case = create_review_case(
        "AUDIT-DELETE-001",
        "REVIEW",
        ["Integrity test"],
        database_path=audit_db,
    )

    with sqlite3.connect(audit_db) as connection:
        event_id = connection.execute(
            "SELECT event_id FROM review_audit_events WHERE case_id = ?",
            (case["case_id"],),
        ).fetchone()[0]

        with pytest.raises(
            sqlite3.IntegrityError,
            match="DELETE prohibited",
        ):
            connection.execute(
                "DELETE FROM review_audit_events WHERE event_id = ?",
                (event_id,),
            )


def test_legitimate_audit_events_can_be_inserted(audit_db):
    case = create_review_case(
        "AUDIT-INSERT-001",
        "REVIEW",
        ["Integrity test"],
        database_path=audit_db,
    )

    history = get_review_audit_history(
        case["case_id"],
        audit_db,
    )

    assert len(history) == 1
    assert history[0]["event_type"] == "CASE_CREATED"


def test_review_decision_appends_audit_event(audit_db):
    case = create_review_case(
        "AUDIT-DECISION-001",
        "REVIEW",
        ["Manual review"],
        database_path=audit_db,
    )

    result = record_review_decision(
        case["case_id"],
        "TEST_REVIEWER",
        "APPROVE",
        "Verified.",
        database_path=audit_db,
    )

    history = get_review_audit_history(
        case["case_id"],
        audit_db,
    )

    assert result["review_status"] == "APPROVED"
    assert len(history) == 2
    assert history[0]["event_type"] == "CASE_CREATED"
    assert history[1]["event_type"] == "REVIEW_DECISION"


def test_duplicate_decision_does_not_append_event(audit_db):
    case = create_review_case(
        "AUDIT-DUPLICATE-001",
        "REVIEW",
        ["Manual review"],
        database_path=audit_db,
    )

    record_review_decision(
        case["case_id"],
        "TEST_REVIEWER",
        "APPROVE",
        database_path=audit_db,
    )

    with pytest.raises(ValueError, match="already received a decision"):
        record_review_decision(
            case["case_id"],
            "TEST_REVIEWER_2",
            "REJECT",
            database_path=audit_db,
        )

    history = get_review_audit_history(
        case["case_id"],
        audit_db,
    )

    assert len(history) == 2
