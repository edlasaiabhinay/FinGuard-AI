
import os
import json
import hashlib
import hmac


ALLOWED_ROLES = {"admin", "reviewer", "auditor"}


class AuthenticationError(Exception):
    pass


class AuthorizationError(Exception):
    pass


def _load_reviewer_tokens():
    """
    Load reviewer token hashes from environment configuration.

    Environment variable:
    FINGUARD_REVIEWER_TOKEN_HASHES

    Expected JSON:
    [
      {
        "token_sha256": "<64-character SHA-256 hash>",
        "reviewer_id": "reviewer_001",
        "role": "reviewer"
      }
    ]
    """

    raw_config = os.environ.get(
        "FINGUARD_REVIEWER_TOKEN_HASHES"
    )

    if not raw_config:
        raise AuthenticationError(
            "Reviewer authentication is not configured."
        )

    try:
        entries = json.loads(raw_config)
    except json.JSONDecodeError as exc:
        raise AuthenticationError(
            "Reviewer authentication configuration is invalid."
        ) from exc

    if not isinstance(entries, list) or not entries:
        raise AuthenticationError(
            "Reviewer token configuration must be a non-empty list."
        )

    validated = []

    for entry in entries:
        if not isinstance(entry, dict):
            raise AuthenticationError(
                "Invalid reviewer configuration entry."
            )

        token_hash = entry.get("token_sha256")
        reviewer_id = entry.get("reviewer_id")
        role = entry.get("role")

        if (
            not isinstance(token_hash, str)
            or len(token_hash) != 64
        ):
            raise AuthenticationError(
                "Invalid reviewer token hash."
            )

        try:
            int(token_hash, 16)
        except ValueError as exc:
            raise AuthenticationError(
                "Reviewer token hash must be hexadecimal."
            ) from exc

        if not isinstance(reviewer_id, str) or not reviewer_id.strip():
            raise AuthenticationError(
                "Reviewer identity is missing."
            )

        if role not in ALLOWED_ROLES:
            raise AuthenticationError(
                "Reviewer role is invalid."
            )

        validated.append({
            "token_sha256": token_hash.lower(),
            "reviewer_id": reviewer_id.strip(),
            "role": role
        })

    return validated


def authenticate_reviewer(token):
    """Authenticate a bearer token and return its reviewer identity."""

    if not isinstance(token, str) or not token.strip():
        raise AuthenticationError("Bearer token is missing.")

    supplied_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    reviewers = _load_reviewer_tokens()

    matched_reviewer = None

    for entry in reviewers:
        if hmac.compare_digest(
            supplied_hash,
            entry["token_sha256"]
        ):
            matched_reviewer = entry

    if matched_reviewer is None:
        raise AuthenticationError("Invalid reviewer credentials.")

    return {
        "reviewer_id": matched_reviewer["reviewer_id"],
        "role": matched_reviewer["role"]
    }


def require_reviewer_role(identity, allowed_roles):
    """Check whether an authenticated reviewer has an allowed role."""

    if not isinstance(identity, dict):
        raise AuthorizationError("Authenticated identity is required.")

    role = identity.get("role")

    if role not in allowed_roles:
        raise AuthorizationError(
            "Your role does not permit this operation."
        )

    return identity
