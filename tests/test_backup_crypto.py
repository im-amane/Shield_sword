"""Tests for authenticated backup encryption."""
import os
import unittest
from unittest.mock import patch

from app.backup_crypto import BackupEncryptionError, decrypt_backup, encrypt_backup


class BackupCryptoTests(unittest.TestCase):
    def test_round_trip_and_random_nonce(self):
        snapshot = b"SQLite format 3\x00example"
        with patch.dict(os.environ, {"BACKUP_ENCRYPTION_KEY": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="}):
            first = encrypt_backup(snapshot)
            second = encrypt_backup(snapshot)
            self.assertNotEqual(first, second)
            self.assertEqual(decrypt_backup(first), snapshot)

    def test_missing_key_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(BackupEncryptionError):
                encrypt_backup(b"SQLite format 3\x00example")

    def test_tampering_is_rejected(self):
        with patch.dict(os.environ, {"BACKUP_ENCRYPTION_KEY": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="}):
            payload = bytearray(encrypt_backup(b"SQLite format 3\x00example"))
            payload[-1] ^= 1
            with self.assertRaises(BackupEncryptionError):
                decrypt_backup(bytes(payload))

    def test_wrong_key_is_rejected(self):
        with patch.dict(os.environ, {"BACKUP_ENCRYPTION_KEY": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="}):
            payload = encrypt_backup(b"SQLite format 3\x00example")
        with patch.dict(os.environ, {"BACKUP_ENCRYPTION_KEY": "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE="}):
            with self.assertRaises(BackupEncryptionError):
                decrypt_backup(payload)


if __name__ == "__main__":
    unittest.main()
