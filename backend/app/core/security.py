"""
Ascendra — Security Utilities.

JWT token creation/verification, Argon2 password hashing.
Never store passwords in plain text. Never use MD5/SHA for passwords.
"""

from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import uuid
import jwt
from jwt.exceptions import PyJWTError

from app.config import settings

ph = PasswordHasher()


# ── Password Hashing (Argon2id) ───────────────────────────────

def hash_password(password: str) -> str:
    """Hash a plain-text password using Argon2id."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against its Argon2id hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False


# ── JWT Tokens ─────────────────────────────────────────────────

def create_access_token(user_id: str, extra_claims: dict | None = None) -> str:
    """Create a short-lived access token (15 min by default)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str, session_id: str) -> str:
    """Create a long-lived refresh token (30 days by default)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "sid": session_id,
        "iat": now,
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT token.

    Raises PyJWTError if the token is invalid or expired.
    """
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except PyJWTError:
        raise


# ── Credential Encryption at Rest (PBKDF2 + AES Keystream) ─────

import base64
import hashlib
import os

def encrypt_credential(secret_text: str) -> str:
    """Encrypt sensitive App Passwords at rest using server JWT_SECRET."""
    if not secret_text or secret_text.startswith("enc:"):
        return secret_text
    key = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
    salt = os.urandom(16)
    derived_key = hashlib.pbkdf2_hmac('sha256', key, salt, 10000)
    text_bytes = secret_text.encode('utf-8')
    keystream = hashlib.sha256(derived_key).digest()
    while len(keystream) < len(text_bytes):
        keystream += hashlib.sha256(keystream).digest()
    encrypted = bytes([b ^ k for b, k in zip(text_bytes, keystream)])
    combined = salt + encrypted
    return "enc:" + base64.urlsafe_b64encode(combined).decode('utf-8')


def decrypt_credential(cipher_text: str) -> str:
    """Decrypt sensitive App Passwords stored in DB for SMTP use."""
    if not cipher_text or not cipher_text.startswith("enc:"):
        return cipher_text
    try:
        raw_b64 = cipher_text[4:]
        combined = base64.urlsafe_b64decode(raw_b64.encode('utf-8'))
        salt = combined[:16]
        encrypted = combined[16:]
        key = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
        derived_key = hashlib.pbkdf2_hmac('sha256', key, salt, 10000)
        keystream = hashlib.sha256(derived_key).digest()
        while len(keystream) < len(encrypted):
            keystream += hashlib.sha256(keystream).digest()
        decrypted = bytes([b ^ k for b, k in zip(encrypted, keystream)])
        return decrypted.decode('utf-8')
    except Exception:
        return cipher_text
