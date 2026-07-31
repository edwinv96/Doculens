from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.runtime_config import (
    DEFAULT_ALLOWED_ORIGINS,
    DEFAULT_MAX_UPLOAD_BYTES,
    RuntimeSettings,
)


class RuntimeSettingsTest(unittest.TestCase):
    def test_defaults_are_local_and_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(os.environ, {}, clear=True):
            base = Path(temp_dir)
            settings = RuntimeSettings.from_env(base)

            self.assertEqual(settings.data_dir, (base / "data").resolve())
            self.assertEqual(settings.upload_dir, (base / "temp_uploads").resolve())
            self.assertEqual(settings.allowed_origins, DEFAULT_ALLOWED_ORIGINS)
            self.assertEqual(settings.max_upload_bytes, DEFAULT_MAX_UPLOAD_BYTES)

    def test_environment_values_are_parsed(self) -> None:
        env = {
            "DATA_DIR": "runtime/data",
            "UPLOAD_DIR": "runtime/uploads",
            "ALLOWED_ORIGINS": "https://demo.example, http://localhost:8501 ",
            "MAX_UPLOAD_BYTES": "2048",
        }
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(os.environ, env, clear=True):
            base = Path(temp_dir)
            settings = RuntimeSettings.from_env(base)

            self.assertEqual(settings.data_dir, (base / "runtime/data").resolve())
            self.assertEqual(settings.upload_dir, (base / "runtime/uploads").resolve())
            self.assertEqual(
                settings.allowed_origins,
                ("https://demo.example", "http://localhost:8501"),
            )
            self.assertEqual(settings.max_upload_bytes, 2048)

    def test_upload_path_accepts_a_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = RuntimeSettings(
                data_dir=Path(temp_dir) / "data",
                upload_dir=Path(temp_dir) / "uploads",
                allowed_origins=DEFAULT_ALLOWED_ORIGINS,
                max_upload_bytes=1024,
            )
            settings.ensure_directories()

            destination = settings.upload_path("report.PDF")

            self.assertEqual(destination, (Path(temp_dir) / "uploads/report.PDF").resolve())

    def test_upload_path_rejects_traversal_and_non_pdf_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = RuntimeSettings(
                data_dir=Path(temp_dir) / "data",
                upload_dir=Path(temp_dir) / "uploads",
                allowed_origins=DEFAULT_ALLOWED_ORIGINS,
                max_upload_bytes=1024,
            )

            for filename in ("../secret.pdf", "..\\secret.pdf", "notes.txt", ""):
                with self.subTest(filename=filename):
                    with self.assertRaises(ValueError):
                        settings.upload_path(filename)


if __name__ == "__main__":
    unittest.main()
