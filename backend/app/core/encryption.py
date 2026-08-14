"""
Ascendra — Encryption Utilities.

Fernet symmetric encryption for sensitive data at rest (SMTP passwords, tokens).
"""

import base64
import hashlib
import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("ascendra.encryption")

# Derive a stable Fernet key from the app's JWT_SECRET.
# This avoids requiring a separate ENCRYPTION_KEY env var.
_FERNET: Fernet | None = None


def _get_fernet() -> Fernet:
    """Lazily initialise Fernet cipher from JWT_SECRET."""
    global _FERNET
    if _FERNET is None:
        from app.config import settings
        secret = getattr(settings, "JWT_SECRET", None) or "fallback-dev-key"
        # Fernet requires a 32-byte URL-safe base64-encoded key.
        # Derive one deterministically from the JWT secret.
        raw = hashlib.sha256(secret.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(raw)
        _FERNET = Fernet(key)
    return _FERNET


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string → base64 ciphertext string."""
    if not plaintext:
        return plaintext
    try:
        token = _get_fernet().encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        # Return plaintext as fallback so the app doesn't crash
        return plaintext


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a ciphertext string → plaintext string."""
    if not ciphertext:
        return ciphertext
    try:
        plaintext = _get_fernet().decrypt(ciphertext.encode("utf-8"))
        return plaintext.decode("utf-8")
    except InvalidToken:
        # Value might be stored as plaintext (pre-encryption migration)
        logger.debug("Decryption failed — value may be stored as plaintext (pre-migration).")
        return ciphertext
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return ciphertext
