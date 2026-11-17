"""Tests for persistent daily owner security report scheduling."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app.storage as storage
from app.main import DAILY_REPORT_INTERVAL_SECONDS


class DailyReportScheduleTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "test.sqlite3"
        self.path_patch = patch.object(storage, "DB_PATH", self.db_path)
        self.path_patch.start()
        self.initialized_patch = patch.object(storage, "_initialized_path", None)
        self.initialized_patch.start()

    def tearDown(self):
        self.initialized_patch.stop()
        self.path_patch.stop()
        self.tempdir.cleanup()

    def test_interval_is_exactly_one_day(self):
        self.assertEqual(DAILY_REPORT_INTERVAL_SECONDS, 24 * 60 * 60)

    def test_first_run_has_no_previous_success(self):
        self.assertIsNone(storage.get_last_daily_report_at())

    def test_last_success_is_persisted_and_updated(self):
        storage.set_last_daily_report_at(1_800_000_000.0)
        self.assertEqual(storage.get_last_daily_report_at(), 1_800_000_000.0)
        storage.set_last_daily_report_at(1_800_086_400.0)
        self.assertEqual(storage.get_last_daily_report_at(), 1_800_086_400.0)

    def test_success_timestamp_survives_storage_reinitialization(self):
        storage.set_last_daily_report_at(1_800_000_000.0)
        storage._initialized_path = None
        self.assertEqual(storage.get_last_daily_report_at(), 1_800_000_000.0)


if __name__ == "__main__":
    unittest.main()
