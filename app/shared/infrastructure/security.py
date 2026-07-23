import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import settings
from app.shared.domain.exceptions import UnauthorizedError

PBKDF2_ITERATIONS = 600_000


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), _b64decode(salt), int(iterations))
        return hmac.compare_digest(actual, _b64decode(expected))
    except (TypeError, ValueError):
        return False


def create_access_token(subject: str) -> str:
    header = {"alg": settings.jwt_algorithm, "typ": "JWT"}
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "type": "access", "exp": int(expires_at.timestamp())}
    encoded_header = _b64encode(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(
        settings.secret_key.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    return f"{signing_input}.{_b64encode(signature)}"


def create_refresh_token() -> tuple[str, str, datetime]:
    raw_token = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    return raw_token, hash_refresh_token(raw_token), expires_at


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        signing_input = f"{encoded_header}.{encoded_payload}"
        expected = hmac.new(
            settings.secret_key.encode(), signing_input.encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(expected, _b64decode(encoded_signature)):
            raise ValueError("Invalid signature")
        header = json.loads(_b64decode(encoded_header))
        payload = json.loads(_b64decode(encoded_payload))
        if header.get("alg") != settings.jwt_algorithm:
            raise ValueError("Invalid algorithm")
        if payload.get("exp", 0) <= int(datetime.now(UTC).timestamp()):
            raise ValueError("Expired token")
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise UnauthorizedError("Invalid or expired access token") from exc
    if payload.get("type") != "access" or not payload.get("sub"):
        raise UnauthorizedError("Invalid access token")
    return payload
