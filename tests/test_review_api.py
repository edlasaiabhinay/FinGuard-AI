
import hashlib
import json

import pytest

from fastapi.testclient import TestClient

from src.api.main import app
from src.human_review.database import (
    initialize_review_database,
    create_review_case,
    get_review_case,
)


@pytest.fixture
def api_environment(tmp_path, monkeypatch):
    database = tmp_path / "review_api_test.db"

    reviewer_token = "permanent_test_reviewer_token"
    auditor_token = "permanent_test_auditor_token"

    def token_hash(token):
        return hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

    config = [
        {
            "token_sha256": token_hash(reviewer_token),
            "reviewer_id": "TEST_REVIEWER",
            "role": "reviewer",
        },
        {
            "token_sha256": token_hash(auditor_token),
            "reviewer_id": "TEST_AUDITOR",
            "role": "auditor",
        },
    ]

    monkeypatch.setenv(
        "FINGUARD_REVIEWER_TOKEN_HASHES",
        json.dumps(config),
    )
    monkeypatch.setenv(
        "FINGUARD_HITL_DATABASE_PATH",
        str(database),
    )

    initialize_review_database(database)

    case = create_review_case(
        document_id="API-TEST-001",
        ai_decision="REVIEW",
        reasons=["Manual PO verification required."],
        report={"financial_status": "PASS"},
        database_path=database,
    )

    return {
        "client": TestClient(app),
        "database": database,
        "case_id": case["case_id"],
        "reviewer_token": reviewer_token,
        "auditor_token": auditor_token,
    }


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_api_health(api_environment):
    response = api_environment["client"].get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_unauthenticated_queue_access_is_rejected(api_environment):
    response = api_environment["client"].get("/api/reviews/")

    assert response.status_code == 401


def test_reviewer_can_list_pending_cases(api_environment):
    env = api_environment

    response = env["client"].get(
        "/api/reviews/",
        headers=headers(env["reviewer_token"]),
    )

    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_reviewer_can_view_case_details(api_environment):
    env = api_environment

    response = env["client"].get(
        f"/api/reviews/{env['case_id']}",
        headers=headers(env["reviewer_token"]),
    )

    assert response.status_code == 200
    assert response.json()["case"]["ai_decision"] == "REVIEW"


def test_auditor_can_read_but_cannot_decide(api_environment):
    env = api_environment
    auditor_headers = headers(env["auditor_token"])

    read_response = env["client"].get(
        "/api/reviews/",
        headers=auditor_headers,
    )

    assert read_response.status_code == 200

    decision_response = env["client"].post(
        f"/api/reviews/{env['case_id']}/decision",
        headers=auditor_headers,
        json={"decision": "APPROVE"},
    )

    assert decision_response.status_code == 403


def test_reviewer_identity_cannot_be_forged(api_environment):
    env = api_environment

    response = env["client"].post(
        f"/api/reviews/{env['case_id']}/decision",
        headers=headers(env["reviewer_token"]),
        json={
            "decision": "APPROVE",
            "reviewer_id": "FORGED_REVIEWER",
        },
    )

    assert response.status_code == 422


def test_reviewer_can_submit_decision(api_environment):
    env = api_environment

    response = env["client"].post(
        f"/api/reviews/{env['case_id']}/decision",
        headers=headers(env["reviewer_token"]),
        json={
            "decision": "APPROVE",
            "comment": "Documents manually verified.",
        },
    )

    assert response.status_code == 200

    saved = get_review_case(
        env["case_id"],
        env["database"],
    )

    assert saved["reviewer_id"] == "TEST_REVIEWER"
    assert saved["review_status"] == "APPROVED"
    assert saved["ai_decision"] == "REVIEW"


def test_auditor_can_read_audit_history(api_environment):
    env = api_environment

    response = env["client"].get(
        f"/api/reviews/{env['case_id']}/audit",
        headers=headers(env["auditor_token"]),
    )

    assert response.status_code == 200
    assert response.json()["event_count"] == 1


def test_repeated_decision_returns_conflict(api_environment):
    env = api_environment
    auth = headers(env["reviewer_token"])
    url = f"/api/reviews/{env['case_id']}/decision"

    first = env["client"].post(
        url,
        headers=auth,
        json={"decision": "APPROVE"},
    )

    second = env["client"].post(
        url,
        headers=auth,
        json={"decision": "REJECT"},
    )

    assert first.status_code == 200
    assert second.status_code == 409


def test_unknown_case_returns_not_found(api_environment):
    env = api_environment

    response = env["client"].get(
        "/api/reviews/unknown-case",
        headers=headers(env["reviewer_token"]),
    )

    assert response.status_code == 404


def test_invalid_token_is_rejected(api_environment):
    env = api_environment

    response = env["client"].get(
        "/api/reviews/",
        headers=headers("invalid-token"),
    )

    assert response.status_code == 401
