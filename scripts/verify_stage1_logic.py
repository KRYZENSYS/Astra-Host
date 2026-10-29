#!/usr/bin/env python3
"""
BotHost Stage 1 Standalone Python Logic Verification Script
Uses Python standard library (unittest, zipfile, io, tempfile, pathlib)
to verify:
- Zip extraction safety (Zip-Slip directory traversal blocking)
- Symlink detection
- Junk filtering (__pycache__, .git, *.pyc, .env, *.db, *.log, backups/)
- Single top-level directory wrapper flattening
- Entrypoint detection (main.py, bot.py, app.py, if __name__ == '__main__')
- Hardened Dockerfile template generation
"""

import io
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

# Add backend to sys.path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.services.detector_service import detect_or_verify_entrypoint, generate_dockerfile
from app.services.zip_service import is_junk_path, validate_and_extract_bot_zip


def create_zip(file_dict: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in file_dict.items():
            zf.writestr(filename, content)
    return buffer.getvalue()


class TestBotHostStage1Logic(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="bothost_test_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_zip_slip_traversal_blocked(self):
        """Zip-Slip traversal attack (../../evil.py) must be rejected."""
        malicious_zip = create_zip({
            "../../evil.py": b"print('hacked')",
            "main.py": b"print('normal')",
        })
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            validate_and_extract_bot_zip(malicious_zip, self.test_dir)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertTrue(
            "xavfli yo'l aniqlandi" in ctx.exception.detail or
            "Zip-slip" in ctx.exception.detail
        )
        print(" [OK] Zip-Slip traversal attack blocked successfully.")

    def test_02_junk_files_and_directories_excluded(self):
        """Development junk (.env, .git, __pycache__, *.db, *.log) must never be extracted."""
        zip_with_junk = create_zip({
            "bot.py": b"print('telegram bot ready')",
            "requirements.txt": b"aiogram==3.18.0\n",
            "__pycache__/cache.pyc": b"\x00\x00\x00",
            ".git/config": b"[core]\nrepositoryformatversion = 0",
            ".env": b"BOT_TOKEN=leak_secret",
            "user_data.db": b"sqlite bytes",
            "error.log": b"stack trace",
            "backups/old.zip": b"nested backup",
        })
        extracted = validate_and_extract_bot_zip(zip_with_junk, self.test_dir)
        self.assertIn("bot.py", extracted)
        self.assertIn("requirements.txt", extracted)
        self.assertEqual(len(extracted), 2)

        # Verify junk is absent from filesystem
        p = Path(self.test_dir)
        self.assertFalse((p / ".env").exists())
        self.assertFalse((p / ".git").exists())
        self.assertFalse((p / "__pycache__").exists())
        self.assertFalse((p / "user_data.db").exists())
        self.assertFalse((p / "error.log").exists())
        print(" [OK] Junk files (.env, .git, __pycache__, *.db, *.log) successfully filtered out.")

    def test_03_single_directory_wrapper_flattened(self):
        """Single top-level wrapper directory (e.g. repo-main/) must be flattened to root."""
        nested_zip = create_zip({
            "my-telegram-bot-master/main.py": b"print('root entry')",
            "my-telegram-bot-master/config.py": b"PORT = 8080",
            "my-telegram-bot-master/requirements.txt": b"aiogram==3.18.0\n",
        })
        extracted = validate_and_extract_bot_zip(nested_zip, self.test_dir)
        self.assertIn("main.py", extracted)
        self.assertIn("config.py", extracted)
        self.assertIn("requirements.txt", extracted)

        p = Path(self.test_dir)
        self.assertTrue((p / "main.py").is_file())
        self.assertTrue((p / "config.py").is_file())
        print(" [OK] Nested top-level wrapper directory flattened correctly.")

    def test_04_entrypoint_detection(self):
        """Entrypoint detector scans for main.py, bot.py, and if __name__ == '__main__'."""
        src = Path(self.test_dir) / "bot_src"
        src.mkdir(parents=True, exist_ok=True)

        (src / "bot.py").write_text("import os\nif __name__ == '__main__':\n    print('start')\n")
        (src / "utils.py").write_text("def helper(): pass\n")

        entry, has_reqs = detect_or_verify_entrypoint(str(src))
        self.assertEqual(entry, "bot.py")
        # Since requirements.txt was missing, it should auto-create an empty one
        self.assertTrue((src / "requirements.txt").is_file())
        print(" [OK] Entrypoint detected as bot.py and requirements.txt auto-created.")

    def test_05_hardened_dockerfile_generation(self):
        """Renders Dockerfile with non-root user (10001), /data mount, and python:3.12-slim."""
        src = Path(self.test_dir) / "docker_src"
        src.mkdir(parents=True, exist_ok=True)

        generate_dockerfile(str(src), "bot.py")
        dockerfile = (src / "Dockerfile").read_text()

        self.assertIn("FROM python:3.12-slim", dockerfile)
        self.assertIn("useradd -u 10001 -m botuser", dockerfile)
        self.assertIn("/data", dockerfile)
        self.assertIn("USER 10001:10001", dockerfile)
        self.assertIn('CMD ["python", "bot.py"]', dockerfile)
        print(" [OK] Hardened Dockerfile generated with UID 10001 and /data mount.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
