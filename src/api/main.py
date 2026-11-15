
import os

from typing import Literal

from fastapi import (
    FastAPI,
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from pydantic import BaseModel, ConfigDict, Field
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi import _rate_limit_exceeded_handler

from src.security.reviewer_auth import (
    authenticate_reviewer,
    require_reviewer_role,
    AuthenticationError,
    AuthorizationError,
)

from src.human_review.database import (
    get_default_database_path,
    get_review_case,
    get_review_audit_history,
)

from src.human_review.review_service import (
    get_review_queue,
    get_review_case_details,
    decide_review_case,
)


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="FinGuard AI — Human Review API",
    description=(
        "Authenticated API for invoice review, "
        "reviewer decisions, and audit history."
    ),
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)

router = APIRouter(
    prefix="/api/reviews",
    tags=["Human Review"],
)

bearer_scheme = HTTPBearer(auto_error=False)


class ReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal[
        "APPROVE",
        "REJECT",
        "REQUEST_CORRECTION",
    ]

    comment: str = Field(
        default="",
        max_length=4000,
    )


def get_database_path():
    """Resolve the review database path from configuration."""

    configured_path = os.environ.get(
        "FINGUARD_HITL_DATABASE_PATH"
    )

    if configured_path:
        return configured_path

    return str(get_default_database_path())


def get_authenticated_reviewer(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
):
    """Authenticate the bearer token and return reviewer identity."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return authenticate_reviewer(credentials.credentials)

    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or unavailable reviewer credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_read_access(
    identity=Depends(get_authenticated_reviewer),
):
    try:
        return require_reviewer_role(
            identity,
            {"reviewer", "admin", "auditor"},
        )
    except AuthorizationError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view review records.",
        )


def require_decision_access(
    identity=Depends(get_authenticated_reviewer),
):
    try:
        return require_reviewer_role(
            identity,
            {"reviewer", "admin"},
        )
    except AuthorizationError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role cannot submit review decisions.",
        )


@router.get("/")
@limiter.limit("60/minute")
def list_reviews(request: Request, identity=Depends(require_read_access)):
    """Retrieve all pending human-review cases."""

    cases = get_review_queue(get_database_path())

    return {
        "count": len(cases),
        "reviews": cases,
    }


@router.get("/{case_id}")
@limiter.limit("60/minute")
def review_details(
    request: Request,
    case_id: str,
    identity=Depends(require_read_access),
):
    """Retrieve one review case and its audit history."""

    try:
        return get_review_case_details(
            case_id,
            get_database_path(),
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review case not found.",
        )


@router.post("/{case_id}/decision")
@limiter.limit("60/minute")
def submit_review_decision(
    request: Request,
    case_id: str,
    payload: ReviewDecisionRequest,
    identity=Depends(require_decision_access),
):
    """Submit a decision using the authenticated reviewer identity."""

    database_path = get_database_path()

    if get_review_case(case_id, database_path) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review case not found.",
        )

    try:
        result = decide_review_case(
            case_id=case_id,
            reviewer_id=identity["reviewer_id"],
            decision=payload.decision,
            comment=payload.comment,
            database_path=database_path,
        )

        return {
            "message": "Human review decision recorded.",
            "case": result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )


@router.get("/{case_id}/audit")
@limiter.limit("60/minute")
def review_audit_history(
    request: Request,
    case_id: str,
    identity=Depends(require_read_access),
):
    """Retrieve the audit events for a review case."""

    if get_review_case(case_id, get_database_path()) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review case not found.",
        )

    history = get_review_audit_history(
        case_id,
        get_database_path(),
    )

    return {
        "case_id": case_id,
        "event_count": len(history),
        "events": history,
    }


app.include_router(router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "FinGuard AI Human Review API",
    }
