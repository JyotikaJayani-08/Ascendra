"""
Ascendra — Custom Exceptions.

Business-meaningful error codes. Never expose internal details to users.
"""

from fastapi import HTTPException, status


class AscendraException(HTTPException):
    """Base exception for all Ascendra business errors."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
    ):
        super().__init__(
            status_code=status_code,
            detail={"code": code, "message": message},
        )


# ── Auth Errors ───────────────────────────────────────────────

class InvalidCredentials(AscendraException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_CREDENTIALS",
            message="Invalid email or password.",
        )


class TokenExpired(AscendraException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="TOKEN_EXPIRED",
            message="Token has expired. Please login again.",
        )


class TokenInvalid(AscendraException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="TOKEN_INVALID",
            message="Invalid token.",
        )


class EmailAlreadyRegistered(AscendraException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="EMAIL_ALREADY_REGISTERED",
            message="An account with this email already exists.",
        )


class EmailNotVerified(AscendraException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="EMAIL_NOT_VERIFIED",
            message="Please verify your email before proceeding.",
        )


class AccountSuspended(AscendraException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="ACCOUNT_SUSPENDED",
            message="Your account has been suspended.",
        )


# ── Resource Errors ───────────────────────────────────────────

class NotFound(AscendraException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code=f"{resource.upper()}_NOT_FOUND",
            message=f"{resource} not found.",
        )


class PermissionDenied(AscendraException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="PERMISSION_DENIED",
            message="You do not have permission to access this resource.",
        )


# ── Validation Errors ─────────────────────────────────────────

class ValidationError(AscendraException):
    def __init__(self, message: str = "Validation failed."):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message=message,
        )


class InvalidStateTransition(AscendraException):
    def __init__(self, current: str, target: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="INVALID_STATE_TRANSITION",
            message=f"Cannot transition from '{current}' to '{target}'.",
        )


# ── Rate Limiting ─────────────────────────────────────────────

class RateLimitExceeded(AscendraException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMIT_EXCEEDED",
            message="Too many requests. Please try again later.",
        )
