import os
import shutil
import tempfile
import unittest
from pathlib import Path

# Add backend to sys.path
import sys
backend_path = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(backend_path))

from app.analyzer.pipeline import analyze_project
from app.analyzer.extractor import validate_and_extract_safely, SafeExtractionError
from app.analyzer.telegram_service import validate_bot_token
from app.analyzer.autofix_service import analyze_failure_and_autofix

FIXTURES_DIR = Path(__file__).parent / "fixtures"

class TestSmartAnalyzer(unittest.TestCase):
    def setUp(self):
        self.temp_dirs = []

    def tearDown(self):
        for d in self.temp_dirs:
            shutil.rmtree(d, ignore_errors=True)

    def _make_temp_dir(self) -> Path:
        d = Path(tempfile.mkdtemp(prefix="test_bothost_"))
        self.temp_dirs.append(d)
        return d

    def test_1_minimal_aiogram3(self):
        zip_path = FIXTURES_DIR / "1_minimal_aiogram3.zip"
        zip_bytes = zip_path.read_bytes()
        dest = self._make_temp_dir()

        result = analyze_project(str(dest), zip_bytes=zip_bytes)
        self.assertTrue(result.is_supported_language)
        self.assertEqual(result.detected_language, "python")
        self.assertEqual(result.framework, "aiogram_v3")
        self.assertEqual(result.recommended_entrypoint, "main.py")
        
        # Check token requirement
        token_var = next((v for v in result.env_vars if v.name == "BOT_TOKEN"), None)
        self.assertIsNotNone(token_var)
        self.assertTrue(token_var.is_required)
        self.assertEqual(token_var.var_type, "telegram_token")

        # Check confidence
        self.assertIn(result.confidence_level, ["high", "medium"])
        self.assertGreaterEqual(result.confidence_score, 80)

    def test_2_ptb_v20_no_reqs(self):
        zip_path = FIXTURES_DIR / "2_ptb_v20_no_reqs.zip"
        zip_bytes = zip_path.read_bytes()
        dest = self._make_temp_dir()

        result = analyze_project(str(dest), zip_bytes=zip_bytes)
        self.assertTrue(result.is_supported_language)
        self.assertEqual(result.framework, "python_telegram_bot_v20")
        self.assertEqual(result.recommended_entrypoint, "bot.py")
        self.assertFalse(result.dependencies.has_requirements_file)
        # Should have detected python-telegram-bot as missing and added it
        self.assertIn("python-telegram-bot", result.dependencies.missing_packages)
        self.assertIn("python-telegram-bot", result.dependencies.recommended_requirements)

    def test_3_telebot_sync(self):
        zip_path = FIXTURES_DIR / "3_telebot_sync.zip"
        zip_bytes = zip_path.read_bytes()
        dest = self._make_temp_dir()

        result = analyze_project(str(dest), zip_bytes=zip_bytes)
        self.assertTrue(result.is_supported_language)
        self.assertEqual(result.framework, "telebot")
        self.assertEqual(result.recommended_entrypoint, "run.py")

        # Top candidate should have polling flag
        top_cand = next(c for c in result.entrypoint_candidates if c.filename == "run.py")
        self.assertTrue(top_cand.has_polling)

    def test_4_messy_real_world(self):
        zip_path = FIXTURES_DIR / "4_messy_real_world.zip"
        zip_bytes = zip_path.read_bytes()
        dest = self._make_temp_dir()

        result = analyze_project(str(dest), zip_bytes=zip_bytes)
        self.assertTrue(result.is_supported_language)
        
        # Unwrapped wrapper folder and cleaned junk
        project_files = [p.name for p in Path(result.project_root).rglob("*") if p.is_file()]
        self.assertNotIn(".DS_Store", project_files)
        self.assertNotIn("bot.log", project_files)
        self.assertNotIn("data.sqlite3", project_files)
        self.assertNotIn(".env", project_files)  # Sensitive .env stripped!

        # .env keys discovered safely
        token_var = next((v for v in result.env_vars if v.name == "BOT_TOKEN"), None)
        self.assertIsNotNone(token_var)
        secret_var = next((v for v in result.env_vars if v.name == "SECRET_KEY"), None)
        self.assertIsNotNone(secret_var)

        # Duplicate detection: sleepmode1.py should be marked as duplicate of core_bot.py
        sleep_cand = next((c for c in result.entrypoint_candidates if c.filename == "sleepmode1.py"), None)
        self.assertIsNotNone(sleep_cand)
        self.assertIsNotNone(sleep_cand.is_duplicate_of)

        # Dockerfile hint or top score selected core_bot.py
        self.assertEqual(result.recommended_entrypoint, "core_bot.py")

        # SQLite warning present
        self.assertIsNotNone(result.sqlite_warning)

        # Apt packages for pillow
        self.assertTrue(any("jpeg" in pkg or "freetype" in pkg for pkg in result.dependencies.system_apt_packages))

    def test_5_multi_project(self):
        zip_path = FIXTURES_DIR / "5_multi_project.zip"
        zip_bytes = zip_path.read_bytes()
        dest = self._make_temp_dir()

        # Step A: Initial scan detects subprojects
        result = analyze_project(str(dest), zip_bytes=zip_bytes)
        self.assertGreaterEqual(len(result.sub_projects), 2)
        sub_names = [sp.name for sp in result.sub_projects]
        self.assertIn("sub_bot_alpha", sub_names)
        self.assertIn("sub_bot_beta", sub_names)

        # Step B: Select sub_bot_alpha
        alpha_res = analyze_project(str(dest), sub_project_rel_path="sub_bot_alpha")
        self.assertEqual(alpha_res.framework, "aiogram_v3")
        self.assertEqual(alpha_res.recommended_entrypoint, "main.py")

        # Step C: Select sub_bot_beta
        beta_res = analyze_project(str(dest), sub_project_rel_path="sub_bot_beta")
        self.assertEqual(beta_res.framework, "telebot")
        self.assertEqual(beta_res.recommended_entrypoint, "bot.py")

    def test_6_nodejs_bot_rejected(self):
        zip_path = FIXTURES_DIR / "6_nodejs_bot.zip"
        zip_bytes = zip_path.read_bytes()
        dest = self._make_temp_dir()

        result = analyze_project(str(dest), zip_bytes=zip_bytes)
        self.assertFalse(result.is_supported_language)
        self.assertEqual(result.detected_language, "nodejs")
        self.assertIn("Node.js", result.language_warning)

    def test_7_malicious_zip_rejected(self):
        zip_path = FIXTURES_DIR / "7_malicious_zip.zip"
        zip_bytes = zip_path.read_bytes()
        dest = self._make_temp_dir()

        with self.assertRaises(SafeExtractionError):
            validate_and_extract_safely(zip_bytes, str(dest))

    def test_8_telegram_token_validation(self):
        # Invalid format
        inv_res = validate_bot_token("invalid_token_string")
        self.assertFalse(inv_res["is_valid"])
        self.assertIn("noto'g'ri", inv_res["error_message"])

        # Format-valid dummy token
        valid_res = validate_bot_token("123456789:AAH1234567890abcdefghijklmnopqrstuv")
        # In isolated test sandbox, should either return 401 Unauthorized or offline fallback
        self.assertIn("is_valid", valid_res)

    def test_9_autofix_service(self):
        dest = self._make_temp_dir()
        (dest / "requirements.txt").write_text("aiogram\n")
        (dest / "Dockerfile").write_text("FROM python:3.12-slim\n")

        # 1. Missing module error
        trace_log = "Traceback (most recent call last):\nModuleNotFoundError: No module named 'matplotlib'"
        can_retry, action = analyze_failure_and_autofix(dest, trace_log, current_attempt=1)
        self.assertTrue(can_retry)
        self.assertEqual(action.action_type, "pip_install")
        self.assertIn("matplotlib", (dest / "requirements.txt").read_text())

        # 2. Missing shared object library
        so_log = "ImportError: libGL.so.1: cannot open shared object file: No such file or directory"
        can_retry_so, action_so = analyze_failure_and_autofix(dest, so_log, current_attempt=2)
        self.assertTrue(can_retry_so)
        self.assertEqual(action_so.action_type, "apt_install")
        self.assertIn("libgl1", (dest / "Dockerfile").read_text())

        # 3. Missing env var
        env_log = "KeyError: 'REDIS_URL'"
        can_retry_env, action_env = analyze_failure_and_autofix(dest, env_log, current_attempt=3)
        self.assertFalse(can_retry_env)
        self.assertEqual(action_env.action_type, "missing_env")


if __name__ == "__main__":
    unittest.main()
