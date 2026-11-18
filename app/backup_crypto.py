"""Authenticated encryption for database backup artifacts."""
from __future__ import annotations

import base64
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_MAGIC = b"AWB1"
_NONCE_SIZE = 12
_AAD = b"AniWorldGuardian/database-backup/v1"


class BackupEncryptionError(RuntimeError):
    """Raised when backup encryption cannot be performed safely."""


def _key() -> bytes:
    encoded = os.getenv("BACKUP_ENCRYPTION_KEY", "")
    if not encoded:
        raise BackupEncryptionError(
            "BACKUP_ENCRYPTION_KEY is required; refusing to send a plaintext backup"
        )
    try:
        key = base64.urlsafe_b64decode(encoded.encode("ascii"))
    except Exception as exc:
        raise BackupEncryptionError("BACKUP_ENCRYPTION_KEY must be URL-safe base64") from exc
    if len(key) != 32:
        raise BackupEncryptionError("BACKUP_ENCRYPTION_KEY must decode to exactly 32 bytes")
    return key


def encrypt_backup(snapshot: bytes) -> bytes:
    """Encrypt a verified SQLite snapshot with AES-256-GCM."""
    if not isinstance(snapshot, bytes) or not snapshot.startswith(b"SQLite format 3"):
        raise BackupEncryptionError("Refusing to encrypt an invalid SQLite snapshot")
    nonce = secrets.token_bytes(_NONCE_SIZE)
    ciphertext = AESGCM(_key()).encrypt(nonce, snapshot, _AAD)
    return _MAGIC + nonce + ciphertext


def decrypt_backup(payload: bytes) -> bytes:
    """Authenticate and decrypt a backup; tampering or a wrong key fails closed."""
    if not isinstance(payload, bytes) or len(payload) <= len(_MAGIC) + _NONCE_SIZE:
        raise BackupEncryptionError("Encrypted backup is truncated")
    if not payload.startswith(_MAGIC):
        raise BackupEncryptionError("Unknown encrypted backup format")
    nonce_start = len(_MAGIC)
    nonce = payload[nonce_start:nonce_start + _NONCE_SIZE]
    try:
        plaintext = AESGCM(_key()).decrypt(nonce, payload[nonce_start + _NONCE_SIZE:], _AAD)
    except Exception as exc:
        raise BackupEncryptionError("Backup authentication failed; wrong key or damaged file") from exc
    if not plaintext.startswith(b"SQLite format 3"):
        raise BackupEncryptionError("Decrypted payload is not a SQLite database")
    return plaintext
