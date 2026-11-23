"""Tests for authenticated backup encryption and key rotation."""
import os
import unittest
from unittest.mock import patch

from app.backup_crypto import BackupEncryptionError, decrypt_backup, encrypt_backup


KEY_A = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
KEY_B = "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQE="
SNAPSHOT = b"SQLite format 3\x00example"


class BackupCryptoTests(unittest.TestCase):
    def test_round_trip_and_random_nonce(self):
        with patch.dict(os.environ, {"BACKUP_ENCRYPTION_KEY": KEY_A}, clear=True):
            first = encrypt_backup(SNAPSHOT)
            second = encrypt_backup(SNAPSHOT)
            self.assertNotEqual(first, second)
            self.assertEqual(decrypt_backup(first), SNAPSHOT)

    def test_missing_active_key_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(BackupEncryptionError):
                encrypt_backup(SNAPSHOT)
            with self.assertRaises(BackupEncryptionError):
                decrypt_backup(b"AWB1" + b"0" * 64)

    def test_tampering_is_rejected(self):
        with patch.dict(os.environ, {"BACKUP_ENCRYPTION_KEY": KEY_A}, clear=True):
            payload = bytearray(encrypt_backup(SNAPSHOT))
            payload[-1] ^= 1
            with self.assertRaises(BackupEncryptionError):
                decrypt_backup(bytes(payload))

    def test_wrong_key_is_rejected(self):
        with patch.dict(os.environ, {"BACKUP_ENCRYPTION_KEY": KEY_A}, clear=True):
            payload = encrypt_backup(SNAPSHOT)
        with patch.dict(os.environ, {"BACKUP_ENCRYPTION_KEY": KEY_B}, clear=True):
            with self.assertRaises(BackupEncryptionError):
                decrypt_backup(payload)

    def test_previous_key_decrypts_legacy_backup(self):
        with patch.dict(os.environ, {"BACKUP_ENCRYPTION_KEY": KEY_A}, clear=True):
            legacy_payload = encrypt_backup(SNAPSHOT)
        with patch.dict(os.environ, {
            "BACKUP_ENCRYPTION_KEY": KEY_B,
            "BACKUP_ENCRYPTION_KEY_PREVIOUS": KEY_A,
        }, clear=True):
            self.assertEqual(decrypt_backup(legacy_payload), SNAPSHOT)
            self.assertEqual(decrypt_backup(encrypt_backup(SNAPSHOT)), SNAPSHOT)

    def test_previous_key_alone_can_decrypt_but_not_encrypt(self):
        with patch.dict(os.environ, {"BACKUP_ENCRYPTION_KEY": KEY_A}, clear=True):
            legacy_payload = encrypt_backup(SNAPSHOT)
        with patch.dict(os.environ, {"BACKUP_ENCRYPTION_KEY_PREVIOUS": KEY_A}, clear=True):
            self.assertEqual(decrypt_backup(legacy_payload), SNAPSHOT)
            with self.assertRaises(BackupEncryptionError):
                encrypt_backup(SNAPSHOT)

    def test_malformed_previous_key_fails_closed(self):
        with patch.dict(os.environ, {
            "BACKUP_ENCRYPTION_KEY": KEY_B,
            "BACKUP_ENCRYPTION_KEY_PREVIOUS": "invalid",
        }, clear=True):
            with self.assertRaises(BackupEncryptionError):
                decrypt_backup(b"AWB1" + b"0" * 64)


if __name__ == "__main__":
    unittest.main()
