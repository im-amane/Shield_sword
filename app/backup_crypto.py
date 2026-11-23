"""Authenticated encryption for database backup artifacts."""
from __future__ import annotations

import base64
import hashlib
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_MAGIC = b"AWB1"
_NONCE_SIZE = 12
_AAD = b"AniWorldGuardian/database-backup/v1"


class BackupEncryptionError(RuntimeError):
    """Raised when backup encryption cannot be performed safely."""


def _decode_key(variable: str) -> bytes:
    encoded = os.getenv(variable, "")
    if not encoded:
        raise BackupEncryptionError(f"{variable} is not configured")
    try:
        raw = encoded.encode("ascii")
        key = base64.b64decode(raw, altchars=b"-_", validate=True)
    except Exception as exc:
        raise BackupEncryptionError(f"{variable} must be URL-safe base64") from exc
    if len(key) != 32 or base64.urlsafe_b64encode(key) != raw:
        raise BackupEncryptionError(
            f"{variable} must be canonical URL-safe base64 for exactly 32 bytes"
        )
    return key


def _key() -> bytes:
    """Return the active encryption key; never silently encrypt with a legacy key."""
    return _decode_key("BACKUP_ENCRYPTION_KEY")


def _decryption_keys() -> list[bytes]:
    """Load active and optional previous keys, rejecting malformed configuration."""
    keys: list[bytes] = []
    for variable in ("BACKUP_ENCRYPTION_KEY", "BACKUP_ENCRYPTION_KEY_PREVIOUS"):
        if os.getenv(variable, ""):
            key = _decode_key(variable)
            if key not in keys:
                keys.append(key)
    if not keys:
        raise BackupEncryptionError(
            "BACKUP_ENCRYPTION_KEY is required; refusing to decrypt without a configured key"
        )
    return keys


def backup_key_status() -> dict[str, str | bool]:
    """Return safe key metadata only; never return secret material."""
    try:
        active = _key()
    except BackupEncryptionError:
        active_fingerprint = "Unavailable"
        active_configured = False
    else:
        active_fingerprint = hashlib.sha256(active).hexdigest()[:12].upper()
        active_configured = True

    try:
        previous = _decode_key("BACKUP_ENCRYPTION_KEY_PREVIOUS")
    except BackupEncryptionError:
        previous_fingerprint = "Unavailable"
        previous_configured = False
    else:
        previous_fingerprint = hashlib.sha256(previous).hexdigest()[:12].upper()
        previous_configured = True

    return {
        "configured": active_configured,
        "fingerprint": active_fingerprint,
        "previous_configured": previous_configured,
        "previous_fingerprint": previous_fingerprint,
    }


def encrypt_backup(snapshot: bytes) -> bytes:
    """Encrypt a verified SQLite snapshot with the active AES-256-GCM key."""
    if not isinstance(snapshot, bytes) or not snapshot.startswith(b"SQLite format 3"):
        raise BackupEncryptionError("Refusing to encrypt an invalid SQLite snapshot")
    nonce = secrets.token_bytes(_NONCE_SIZE)
    ciphertext = AESGCM(_key()).encrypt(nonce, snapshot, _AAD)
    return _MAGIC + nonce + ciphertext


def decrypt_backup(payload: bytes) -> bytes:
    """Authenticate with active/previous keys; tampering or wrong keys fail closed."""
    if not isinstance(payload, bytes) or len(payload) <= len(_MAGIC) + _NONCE_SIZE:
        raise BackupEncryptionError("Encrypted backup is truncated")
    if not payload.startswith(_MAGIC):
        raise BackupEncryptionError("Unknown encrypted backup format")

    nonce_start = len(_MAGIC)
    nonce = payload[nonce_start:nonce_start + _NONCE_SIZE]
    ciphertext = payload[nonce_start + _NONCE_SIZE:]
    for key in _decryption_keys():
        try:
            plaintext = AESGCM(key).decrypt(nonce, ciphertext, _AAD)
        except Exception:
            continue
        if not plaintext.startswith(b"SQLite format 3"):
            raise BackupEncryptionError("Decrypted payload is not a SQLite database")
        return plaintext
    raise BackupEncryptionError("Backup authentication failed; no configured key matched")
