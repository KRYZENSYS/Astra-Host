import io
import os
import zipfile
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.resolve()

def create_minimal_aiogram3_zip() -> Path:
    zip_path = FIXTURES_DIR / "1_minimal_aiogram3.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "main.py",
            '''import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

TOKEN = os.getenv("BOT_TOKEN")
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Assalomu alaykum!")

async def main():
    bot = Bot(token=TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
'''
        )
        zf.writestr("requirements.txt", "aiogram>=3.4.1\n")
    zip_path.write_bytes(buf.getvalue())
    return zip_path


def create_ptb_v20_no_reqs_zip() -> Path:
    zip_path = FIXTURES_DIR / "2_ptb_v20_no_reqs.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "bot.py",
            '''import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom PTB!")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()
'''
        )
    zip_path.write_bytes(buf.getvalue())
    return zip_path


def create_telebot_sync_zip() -> Path:
    zip_path = FIXTURES_DIR / "3_telebot_sync.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "run.py",
            '''import os
import telebot

TOKEN = os.getenv("BOT_TOKEN", "default_token")
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Salom TeleBot!")

if __name__ == '__main__':
    bot.infinity_polling()
'''
        )
        zf.writestr("requirements.txt", "pyTelegramBotAPI==4.14.0\n")
    zip_path.write_bytes(buf.getvalue())
    return zip_path


def create_messy_real_world_zip() -> Path:
    zip_path = FIXTURES_DIR / "4_messy_real_world.zip"
    buf = io.BytesIO()
    wrapper = "messy_bot_archive/"
    
    main_code = '''import os
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Connect to sqlite
db_conn = sqlite3.connect("bot_storage.db")

TOKEN = os.getenv("BOT_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY")
dp = Dispatcher()

@dp.message(Command("help"))
async def help_cmd(msg: types.Message):
    await msg.answer("Yordam matni")

async def main():
    bot = Bot(token=TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
'''

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Main entrypoint inside wrapper
        zf.writestr(f"{wrapper}core_bot.py", main_code)
        
        # 2. Exact duplicate file sleepmode1.py
        zf.writestr(f"{wrapper}sleepmode1.py", main_code)
        
        # 3. Helper files
        zf.writestr(f"{wrapper}hub.py", "def hub_init(): return True\n")
        zf.writestr(f"{wrapper}plus.py", "def add(a, b): return a + b\n")
        zf.writestr(f"{wrapper}patch_v1.py", "# Patch 1\n")
        zf.writestr(f"{wrapper}patch_v2.py", "# Patch 2\n")
        zf.writestr(f"{wrapper}handlers.py", "def register(): pass\n")
        zf.writestr(f"{wrapper}keyboards.py", "def get_kb(): return None\n")
        zf.writestr(f"{wrapper}utils.py", "import os\ndef sanitize(): pass\n")
        zf.writestr(f"{wrapper}config.py", "ADMIN_ID = int(os.getenv('ADMIN_ID', '123456'))\n")
        
        # 4. Requirements & configs
        zf.writestr(f"{wrapper}requirements.txt", "aiogram>=3.4\nrequests\npillow\n")
        zf.writestr(f"{wrapper}Dockerfile", 'FROM python:3.10\nCMD ["python", "core_bot.py"]\n')
        zf.writestr(f"{wrapper}docker-compose.yml", "version: '3'\nservices:\n  bot:\n    build: .\n")
        zf.writestr(f"{wrapper}start.sh", "#!/bin/bash\npython core_bot.py\n")
        zf.writestr(f"{wrapper}.env", "BOT_TOKEN=secret_user_token_12345\nSECRET_KEY=raw_secret_value\n")
        zf.writestr(f"{wrapper}.env.example", "BOT_TOKEN=\nSECRET_KEY=\nADMIN_ID=\n")
        
        # 5. Junk that must be stripped
        zf.writestr(f"{wrapper}tests/test_core.py", "def test_ok(): assert True\n")
        zf.writestr(f"{wrapper}__pycache__/core_bot.cpython-312.pyc", b"FAKE_BYTECODE_DATA")
        zf.writestr(f"{wrapper}.github/workflows/main.yml", "name: CI\n")
        zf.writestr(f"{wrapper}backups/backup_2026.tar.gz", b"FAKE_BACKUP_TAR")
        zf.writestr(f"{wrapper}bot.log", "2026-10-29 10:00:00 - Started\n")
        zf.writestr(f"{wrapper}data.sqlite3", b"SQLITE_FORMAT_3_BYTES")
        zf.writestr(f"{wrapper}.DS_Store", b"\x00\x00\x00\x01Bud1")

    zip_path.write_bytes(buf.getvalue())
    return zip_path


def create_multi_project_zip() -> Path:
    zip_path = FIXTURES_DIR / "5_multi_project.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "sub_bot_alpha/main.py",
            '''import asyncio, os
from aiogram import Bot, Dispatcher
dp = Dispatcher()
async def main():
    await dp.start_polling(Bot(os.getenv("BOT_TOKEN")))
if __name__ == '__main__':
    asyncio.run(main())
'''
        )
        zf.writestr("sub_bot_alpha/requirements.txt", "aiogram>=3.0\n")
        
        zf.writestr(
            "sub_bot_beta/bot.py",
            '''import telebot, os
bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))
if __name__ == '__main__':
    bot.infinity_polling()
'''
        )
        zf.writestr("sub_bot_beta/requirements.txt", "pyTelegramBotAPI\n")
    zip_path.write_bytes(buf.getvalue())
    return zip_path


def create_nodejs_zip() -> Path:
    zip_path = FIXTURES_DIR / "6_nodejs_bot.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("package.json", '{"name": "tg-bot", "dependencies": {"telegraf": "^4.16.3"}}')
        zf.writestr("index.js", 'const { Telegraf } = require("telegraf"); const bot = new Telegraf(process.env.BOT_TOKEN); bot.launch();')
    zip_path.write_bytes(buf.getvalue())
    return zip_path


def create_malicious_zip() -> Path:
    zip_path = FIXTURES_DIR / "7_malicious_zip.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("../etc/passwd", "root:x:0:0:root:/root:/bin/bash\n")
        zf.writestr("bot.py", "print('safe')\n")
    zip_path.write_bytes(buf.getvalue())
    return zip_path


def build_all_fixtures():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    create_minimal_aiogram3_zip()
    create_ptb_v20_no_reqs_zip()
    create_telebot_sync_zip()
    create_messy_real_world_zip()
    create_multi_project_zip()
    create_nodejs_zip()
    create_malicious_zip()
    print("All 7 fixtures successfully created.")

if __name__ == "__main__":
    build_all_fixtures()
