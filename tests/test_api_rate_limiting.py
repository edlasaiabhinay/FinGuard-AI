import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, limiter
from src.human_review.database import initialize_review_database


@pytest.fixture
def rate_limit_environment(tmp_path, monkeypatch):
    database = tmp_path / "rate_limit_test.db"
    token = "rate_limit_test_reviewer_token"

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    config = [{
        "token_sha256": token_hash,
        "reviewer_id": "RATE_TEST_REVIEWER",
        "role": "reviewer",
    }]

    monkeypatch.setenv(
        "FINGUARD_REVIEWER_TOKEN_HASHES",
        json.dumps(config),
    )
    monkeypatch.setenv(
        "FINGUARD_HITL_DATABASE_PATH",
        str(database),
    )

    initialize_review_database(database)

    limiter.reset()

    yield {
        "client": TestClient(app),
        "token": token,
    }

    limiter.reset()


def test_review_queue_returns_429_after_rate_limit(
    rate_limit_environment,
):
    env = rate_limit_environment

    # Exercise the actual endpoint directly.
    # The test client uses the same client IP for all requests.
    limiter.reset()

    headers = {
        "Authorization": f"Bearer {env['token']}"
    }

    # Existing production limit is 60/minute.
    # Send 61 requests using the same test client identity.
    responses = [
        env["client"].get(
            "/api/reviews/",
            headers=headers,
        )
        for _ in range(61)
    ]

    assert all(
        response.status_code == 200
        for response in responses[:60]
    )

    assert responses[60].status_code == 429
