
import pytest

from src.human_review.database import (
    initialize_review_database,
    create_review_case,
    get_review_case,
    list_pending_reviews,
    record_review_decision,
    get_review_audit_history,
)

from src.human_review.review_service import (
    enqueue_review_case,
    get_review_queue,
    get_review_case_details,
    decide_review_case,
)

from src.orchestration.graph import supervisor_agent


@pytest.fixture
def review_db(tmp_path):
    database = tmp_path / "test_human_review.db"
    initialize_review_database(database)
    return database


def test_create_pending_review_case(review_db):
    case = create_review_case(
        "INV-001",
        "REVIEW",
        ["PO reference missing"],
        database_path=review_db,
    )

    assert case["review_status"] == "PENDING"
    assert case["ai_decision"] == "REVIEW"


def test_ai_pass_cannot_enter_review_queue(review_db):
    with pytest.raises(ValueError):
        create_review_case(
            "INV-002",
            "PASS",
            [],
            database_path=review_db,
        )


def test_duplicate_pending_case_is_prevented(review_db):
    first = enqueue_review_case(
        "INV-003",
        "REVIEW",
        ["Manual review"],
        database_path=review_db,
    )

    second = enqueue_review_case(
        "INV-003",
        "EXCEPTION",
        ["Another reason"],
        database_path=review_db,
    )

    assert first["created"] is True
    assert second["created"] is False
    assert first["case"]["case_id"] == second["case"]["case_id"]


def test_reviewer_can_approve_case(review_db):
    case = create_review_case(
        "INV-004",
        "REVIEW",
        ["Manual review"],
        database_path=review_db,
    )

    result = record_review_decision(
        case["case_id"],
        "REVIEWER_01",
        "APPROVE",
        "Supporting documents verified.",
        database_path=review_db,
    )

    assert result["review_status"] == "APPROVED"
    assert result["ai_decision"] == "REVIEW"


def test_reviewer_can_reject_case(review_db):
    case = create_review_case(
        "INV-005",
        "EXCEPTION",
        ["Duplicate suspected"],
        database_path=review_db,
    )

    result = decide_review_case(
        case["case_id"],
        "REVIEWER_02",
        "REJECT",
        "Duplicate invoice confirmed.",
        database_path=review_db,
    )

    assert result["review_status"] == "REJECTED"


def test_reviewer_can_request_correction(review_db):
    case = enqueue_review_case(
        "INV-006",
        "REVIEW",
        ["Missing PO"],
        database_path=review_db,
    )["case"]

    result = decide_review_case(
        case["case_id"],
        "REVIEWER_03",
        "REQUEST_CORRECTION",
        "Please provide the purchase order.",
        database_path=review_db,
    )

    assert result["review_status"] == "CORRECTION_REQUESTED"


def test_completed_case_cannot_be_decided_twice(review_db):
    case = create_review_case(
        "INV-007",
        "REVIEW",
        [],
        database_path=review_db,
    )

    record_review_decision(
        case["case_id"],
        "REVIEWER_01",
        "APPROVE",
        database_path=review_db,
    )

    with pytest.raises(ValueError):
        record_review_decision(
            case["case_id"],
            "REVIEWER_02",
            "REJECT",
            database_path=review_db,
        )


def test_audit_history_records_creation_and_decision(review_db):
    case = create_review_case(
        "INV-008",
        "REVIEW",
        ["Anomaly detected"],
        database_path=review_db,
    )

    record_review_decision(
        case["case_id"],
        "REVIEWER_01",
        "APPROVE",
        "Verified manually.",
        database_path=review_db,
    )

    history = get_review_audit_history(
        case["case_id"],
        review_db,
    )

    assert len(history) == 2
    assert history[0]["event_type"] == "CASE_CREATED"
    assert history[1]["event_type"] == "REVIEW_DECISION"


def test_pending_queue_excludes_completed_cases(review_db):
    case = create_review_case(
        "INV-009",
        "REVIEW",
        [],
        database_path=review_db,
    )

    assert len(get_review_queue(review_db)) == 1

    record_review_decision(
        case["case_id"],
        "REVIEWER_01",
        "REJECT",
        database_path=review_db,
    )

    assert len(list_pending_reviews(review_db)) == 0


def test_supervisor_submits_review_to_queue(review_db):
    result = supervisor_agent({
        "document_id": "INV-010",
        "agent_status": {
            "extraction_agent": "COMPLETED",
            "financial_agent": "COMPLETED",
            "po_matching_agent": "REVIEW",
            "duplicate_agent": "COMPLETED",
            "anomaly_agent": "COMPLETED",
        },
        "human_review_required": True,
        "human_review_reason": ["PO reference unavailable"],
        "hitl_database_path": str(review_db),
    })

    assert result["final_decision"] == "REVIEW"
    assert result["hitl_submission_status"] == "CREATED"
    assert len(get_review_queue(review_db)) == 1


def test_supervisor_does_not_submit_pass(review_db):
    result = supervisor_agent({
        "document_id": "INV-011",
        "agent_status": {
            "extraction_agent": "COMPLETED",
            "financial_agent": "COMPLETED",
            "po_matching_agent": "COMPLETED",
            "duplicate_agent": "COMPLETED",
            "anomaly_agent": "COMPLETED",
        },
        "human_review_required": False,
        "human_review_reason": [],
        "hitl_database_path": str(review_db),
    })

    assert result["final_decision"] == "PASS"
    assert result["hitl_submission_status"] == "NOT_REQUIRED"
    assert len(get_review_queue(review_db)) == 0


def test_missing_reviewer_identity_is_rejected(review_db):
    case = create_review_case(
        "INV-012",
        "REVIEW",
        [],
        database_path=review_db,
    )

    with pytest.raises(ValueError):
        record_review_decision(
            case["case_id"],
            "",
            "APPROVE",
            database_path=review_db,
        )


def test_case_details_include_audit_history(review_db):
    case = enqueue_review_case(
        "INV-013",
        "REVIEW",
        ["Manual verification"],
        database_path=review_db,
    )["case"]

    details = get_review_case_details(
        case["case_id"],
        review_db,
    )

    assert details["case"]["case_id"] == case["case_id"]
    assert len(details["audit_history"]) == 1
