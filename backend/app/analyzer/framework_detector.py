import ast
import re
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

def detect_language(project_dir: Path) -> Tuple[str, bool, Optional[str]]:
    """
    Detects if the project is Python or an unsupported language like Node.js.
    Returns: (language, is_supported, warning_message_uzbek)
    """
    has_package_json = (project_dir / "package.json").is_file()
    js_ts_files = list(project_dir.glob("*.js")) + list(project_dir.glob("*.ts"))
    py_files = list(project_dir.glob("*.py")) + list(project_dir.rglob("*.py"))

    if has_package_json or (len(js_ts_files) > len(py_files) and len(js_ts_files) > 0):
        return (
            "nodejs",
            False,
            "Ushbu arxivda Node.js (JavaScript/TypeScript) loyihasi aniqlandi. BotHost hozirda faqat Python Telegram botlarini qo'llab-quvvatlaydi."
        )

    if py_files:
        return ("python", True, None)

    return (
        "unknown",
        False,
        "Arxivda Python (.py) fayllari topilmadi. Iltimos, Python Telegram botingiz kodini yuklang."
    )


def detect_telegram_framework(project_dir: Path) -> Tuple[str, str, List[str]]:
    """
    Analyzes Python files and requirements.txt using AST to detect the Telegram framework and version.
    Returns: (framework_key, display_name, secondary_roles)
    """
    py_files = list(project_dir.glob("*.py"))
    if not py_files:
        py_files = list(project_dir.rglob("*.py"))

    # Also check requirements.txt
    req_text = ""
    req_file = project_dir / "requirements.txt"
    if req_file.is_file():
        req_text = req_file.read_text(encoding="utf-8", errors="ignore").lower()

    signals: Dict[str, int] = {
        "aiogram_v3": 0,
        "aiogram_v2": 0,
        "python_telegram_bot_v20": 0,
        "python_telegram_bot_v13": 0,
        "telebot": 0,
        "pyrogram": 0,
        "telethon": 0,
    }

    secondary_roles: List[str] = []

    # Check requirements text first
    if "aiogram" in req_text:
        if re.search(r"aiogram\s*(?:>=|==|~=)\s*3", req_text):
            signals["aiogram_v3"] += 50
        elif re.search(r"aiogram\s*(?:<|<=|==)\s*2", req_text):
            signals["aiogram_v2"] += 50
        else:
            signals["aiogram_v3"] += 20  # modern default

    if "python-telegram-bot" in req_text:
        if re.search(r"python-telegram-bot\s*(?:>=|==|~=)\s*20", req_text):
            signals["python_telegram_bot_v20"] += 50
        elif re.search(r"python-telegram-bot\s*(?:<|<=|==)\s*13", req_text):
            signals["python_telegram_bot_v13"] += 50
        else:
            signals["python_telegram_bot_v20"] += 20

    if "pytelegrambotapi" in req_text:
        signals["telebot"] += 40

    if "pyrogram" in req_text:
        signals["pyrogram"] += 40

    if "telethon" in req_text:
        signals["telethon"] += 40

    if any(k in req_text for k in ["fastapi", "flask", "aiohttp", "uvicorn", "tornado"]):
        secondary_roles.append("web_server")
    if "apscheduler" in req_text or "schedule" in req_text:
        secondary_roles.append("scheduler")

    # AST & textual inspection across all Python files
    for py_file in py_files:
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # Regex quick scans for syntax cues
        if "aiogram" in content:
            if "from aiogram.filters" in content or "from aiogram.fsm" in content or "include_router" in content:
                signals["aiogram_v3"] += 40
            if "from aiogram.dispatcher.filters" in content or "executor.start_polling" in content:
                signals["aiogram_v2"] += 40
            signals["aiogram_v3"] += 10

        if "telegram" in content or "telegram.ext" in content:
            if "Application.builder" in content or "from telegram.ext import Application" in content:
                signals["python_telegram_bot_v20"] += 40
            if "Updater(" in content or "from telegram.ext import Updater" in content:
                signals["python_telegram_bot_v13"] += 40
            signals["python_telegram_bot_v20"] += 10

        if "telebot" in content or "TeleBot" in content or "infinity_polling" in content:
            signals["telebot"] += 40

        if "pyrogram" in content or "from pyrogram" in content:
            signals["pyrogram"] += 40

        if "telethon" in content or "TelegramClient" in content:
            signals["telethon"] += 40

        # Secondary roles AST check
        if any(w in content for w in ["FastAPI()", "Flask(__name__)", "aiohttp.web.Application"]):
            if "web_server" not in secondary_roles:
                secondary_roles.append("web_server")
        if any(w in content for w in ["AsyncIOScheduler", "BackgroundScheduler", "schedule.every"]):
            if "scheduler" not in secondary_roles:
                secondary_roles.append("scheduler")
        if "web_app" in content or "WebAppInfo" in content:
            if "webapp" not in secondary_roles:
                secondary_roles.append("webapp")

    # Determine highest signal
    sorted_frameworks = sorted(signals.items(), key=lambda x: x[1], reverse=True)
    best_fw, best_score = sorted_frameworks[0]

    framework_names = {
        "aiogram_v3": "aiogram 3.x (Zamonaviy asinxron)",
        "aiogram_v2": "aiogram 2.x (Eski avlod)",
        "python_telegram_bot_v20": "python-telegram-bot v20+ (Asinxron)",
        "python_telegram_bot_v13": "python-telegram-bot v13.x (Sinxron)",
        "telebot": "Telebot / pyTelegramBotAPI",
        "pyrogram": "Pyrogram (Telegram MTProto)",
        "telethon": "Telethon (Telegram MTProto)",
    }

    if best_score > 0:
        return (best_fw, framework_names.get(best_fw, "Python Telegram Bot"), secondary_roles)

    return ("generic", "Standart Python bot", secondary_roles)
