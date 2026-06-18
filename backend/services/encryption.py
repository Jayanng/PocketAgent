"""AES-GCM encryption helpers for agent private keys."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

try:
    from ..config import get_settings
except ImportError:
    from config import get_settings


def _get_aes_key() -> bytes:
    settings = get_settings()
    configured = settings.encryption_key or settings.jwt_secret
    if not configured:
        raise RuntimeError("ENCRYPTION_KEY or JWT_SECRET must be configured.")

    for decoder in (base64.urlsafe_b64decode, base64.b64decode):
        try:
            decoded = decoder(configured)
            if len(decoded) == 32:
                return decoded
        except Exception:
            pass

    try:
        decoded = bytes.fromhex(configured)
        if len(decoded) == 32:
            return decoded
    except ValueError:
        pass

    return hashlib.sha256(configured.encode("utf-8")).digest()


def encrypt_private_key(private_key: str) -> str:
    """Encrypt a hex private key and return a portable base64 payload."""
    nonce = os.urandom(12)
    ciphertext = AESGCM(_get_aes_key()).encrypt(
        nonce,
        private_key.encode("utf-8"),
        associated_data=None,
    )
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_private_key(payload: str) -> str:
    raw = base64.urlsafe_b64decode(payload.encode("ascii"))
    nonce, ciphertext = raw[:12], raw[12:]
    plaintext = AESGCM(_get_aes_key()).decrypt(
        nonce,
        ciphertext,
        associated_data=None,
    )
    return plaintext.decode("utf-8")
