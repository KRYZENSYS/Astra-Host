import os
import sys
import sqlite3
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATA_DIR = os.getenv("DATA_DIR", "/data")
DB_PATH = os.path.join(DATA_DIR, "bot.db")

if not BOT_TOKEN:
    print("[Error] BOT_TOKEN muhit o'zgaruvchisi o'rnatilmagan! Iltimos, BotHost boshqaruv panelida BOT_TOKEN ni kiriting.", file=sys.stderr)
    sys.exit(1)

# Ensure persistent data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize persistent SQLite database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_seen TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT,
            created_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print(f"[{datetime.utcnow().isoformat()}] SQLite persistent bazasi faollashtirildi: {DB_PATH}")

init_db()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user = message.from_user
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_seen) VALUES (?, ?, ?)",
        (user.id, user.username, datetime.utcnow())
    )
    conn.commit()
    conn.close()

    await message.answer(
        f"Assalomu alaykum, {user.first_name}!\n\n"
        f"Ushbu bot **BotHost** platformasida, izolyatsiyalangan Docker konteyneri ichida 24/7 ishlamoqda. 🚀\n"
        f"Siz yuborgan barcha ma'lumotlar `/data/bot.db` SQLite doimiy hajmida xavfsiz saqlanadi."
    )

@dp.message()
async def echo_message(message: types.Message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (user_id, text, created_at) VALUES (?, ?, ?)",
        (message.from_user.id, message.text, datetime.utcnow())
    )
    cursor.execute("SELECT COUNT(*) FROM messages WHERE user_id = ?", (message.from_user.id,))
    count = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    await message.answer(f"Sizning xabaringiz saqlandi: \"{message.text}\"\nJami yuborgan xabarlaringiz soni: {count}")

async def main():
    print(f"[{datetime.utcnow().isoformat()}] BotHost: Telegram bot polling rejimida ishga tushdi...", flush=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
