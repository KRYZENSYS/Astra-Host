# BotHost (1-Bosqich: MVP) — Python Telegram Bot Hosting Platform 🚀

**BotHost** — foydalanuvchilar o'zlarining Python Telegram botlarini ZIP arxiv shaklida yuklab, xavfsiz va izolyatsiyalangan Docker konteynerida 24/7 rejimida yurgizishlari uchun mo'ljallangan platforma.

Ushbu 1-bosqich (Stage 1) hech qanday simulyatsiya yoki soxta ma'lumotlarsiz (**NO MOCKS, NO FAKES**), haqiqiy Docker daemoni (`docker.sock`), PostgreSQL 16, Caddy avtomatik HTTPS proksisi, Argon2id va Fernet shifrlash tizimlari asosida to'liq ishlaydigan MVP hisoblanadi.

---

## 🏗 Texnologik Stek (Stage 1)

- **Backend**: Python 3.12, FastAPI, async SQLAlchemy 2.x, PostgreSQL 16
- **Konteyner Boshqaruvi**: Rasmiy Python Docker SDK (`asyncio.to_thread` orqali asinxron)
- **Xavfsizlik & Shifrlash**:
  - Parollar: `Argon2id` (argon2-cffi)
  - Sessiya: `JWT` access token `HttpOnly`, `SameSite=Lax`, `Secure` kukisida
  - Muhit o'zgaruvchilari (BOT_TOKEN va boshqalar): `Fernet` (AES-128-CBC) orqali saqlashda to'liq shifrlangan, UI-da `••••1234` shaklida niqoblangan va jurnallarda avtomatik qirqib tashlanadi (`[REDACTED_SECRET]`)
- **Frontend**: React 19 + Vite + Tailwind CSS, mobil qurilmalarga mos, 100% tabiiy o'zbek tilidagi interfeys (`src/locales/uz.ts`)
- **Reverse Proxy**: Caddy 2 (avtomatik Let's Encrypt SSL/TLS va SSE unbuffered streaming)
- **Orkestratsiya**: `docker-compose.yml` orqali bitta buyruq bilan ishga tushirish

---

## 🔒 Konteyner Xavfsizligi va Izolyatsiyasi (Hardened Sandboxing)

Har bir bot uchun yaratilgan Docker konteyneri quyidagi qat'iy cheklovlar ostida ishga tushiriladi:

1. **Non-root foydalanuvchi**: `user="10001:10001"` (`botuser`). Hech qanday bot `root` huquqi bilan ishlamaydi.
2. **Read-only ildiz fayl tizimi**: `read_only=True`. Bot o'zining asosiy kod fayllarini yoki tizim fayllarini o'zgartira olmaydi.
3. **Doimiy hajmi (`/data`)**: Har bir botga alohida Docker nomli volyumi (`bothost_data_<bot_id>`) biriktiriladi va faqat `/data` jildi yozish uchun ruxsat etiladi (`rw`). SQLite (`/data/bot.db`) va fayllar bot qayta yuklanganda ham yo'qolmaydi.
4. **Vaqtinchalik xotira**: `tmpfs={"/tmp": "rw,size=64m"}`.
5. **Huquqlarni qisqartirish**: `cap_drop=["ALL"]`, `security_opt=["no-new-privileges:true"]`. Konteyner ichidan host tizimiga yoki qo'shni botlarga chiqish imkonsiz.
6. **Resurs kvotalari (Free plan)**:
   - Xotira: `mem_limit="256m"`, `memswap_limit="256m"` (Swap butunlay o'chirilgan, OOM qo'shni botlarga ta'sir qilmaydi)
   - CPU: `nano_cpus=250000000` (0.25 vCPU)
   - Jarayonlar: `pids_limit=100` (Fork-bomb hujumlarining oldini oladi)
7. **Tarmoq izolyatsiyasi**: Har bir bot alohida izolatsiyalangan bridge tarmog'iga ega (`bothost_net_<bot_id>`). Botlar bir-birining paketlarini ko'ra olmaydi.
8. **Avtomatik qayta tiklash**: `restart_policy={"Name": "on-failure", "MaximumRetryCount": 5}`. Bot xato bilan qulasa 5 martagacha qayta yoqiladi, so'ng to'xtatilib foydalanuvchiga bildiriladi.
9. **ZIP Xavfsizligi**: 20 MB hajm chegarasi, 100 MB zip-bomb himoyasi, Zip-Slip (yo'l orqali katalogdan chiqib ketish) blokirovkasi, symlink rad etilishi, `.env`, `__pycache__`, `.git`, `*.db` kabi chiqindilarni filtrlash.

---

## 🚀 Toza Ubuntu 22.04 / 24.04 VPS da Ishga Tushirish

### 1. Docker va Docker Compose o'rnatish
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git make ca-certificates gnupg

# Docker rasmiy reposini qo'shish va o'rnatish
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Joriy foydalanuvchini docker guruhiga qo'shish
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Loyihani yuklab olish va sozlash
```bash
git clone <ombor_manzili> bothost
cd bothost

# Muhit parametrlarini o'rnatish
cp .env.example .env
```

`.env` faylida xavfsiz kalitlarni generatsiya qilish:
```bash
# Python orqali kalitlar generatsiya qilish:
python3 -c "import secrets; print('JWT_SECRET=' + secrets.token_hex(32))"
python3 -c "from cryptography.fernet import Fernet; print('FERNET_SECRET_KEY=' + Fernet.generate_key().decode())"
```
Ushbu hosil bo'lgan qiymatlarni `.env` fayliga yozing.

### 3. Stackni ishga tushirish (Single-Command)
```bash
make up
# yoki bevosita:
docker compose up -d --build
```

Barcha servislar holatini tekshirish:
```bash
docker compose ps
```

---

## 🧪 Avtomatlashtirilgan Testlarni Ishga Tushirish

Backend uchun to'liq test to'plami yozilgan (autentifikatsiya, argon2, fernet, zip-slip, simvollar, foydalanuvchilar o'rtasidagi izolyatsiya, va docker xavfsizlik shartnomalari):

```bash
# Testlarni konteyner ichida ishga tushirish:
make test
# yoki:
docker compose exec backend pytest -v
```

Hostda bevosita virtual muhitda ishlatish:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest -v tests/
```

Frontend mantiq testlarini tekshirish (Node.js orqali):
```bash
npx tsx --test src/lib/botLogic.test.ts
```

---

## 🤖 Haqiqiy Telegram Bot bilan Sinash (Manual Testing)

Loyiha ichida ikkita tayyor sinov boti mavjud:
1. `examples/echo_bot.zip`: Oddiy sinov dasturi. Har 2 soniyada `/data/counter.txt` fayliga sanagichni yozib boradi va jurnallarga chiqaradi.
2. `examples/telegram_bot.zip`: To'liq `aiogram 3.x` Telegram boti. `/data/bot.db` da SQLite bazasini boshqaradi, `/start` va istalgan matnli xabarlarga javob qaytaradi.

### Sinov bosqichlari:
1. Brauzerda oching: `http://<VPS_IP>` (yoki lokalda `http://localhost:3000`).
2. **Ro'yxatdan o'ting**: Yangi foydalanuvchi yarating (Argon2id orqali himoyalanadi, JWT cookie o'rnatiladi).
3. **Yangi bot yuklang**:
   - "Yangi bot yuklash" tugmasini bosing.
   - `examples/telegram_bot.zip` faylini yuklang.
   - Entrypoint avtomatik ravishda `bot.py` deb aniqlanadi.
   - `BOT_TOKEN` maydoniga Telegram `@BotFather` dan olgan haqiqiy bot tokeningizni kiriting.
   - "Botni yaratish va ishga tushirish" tugmasini bosing.
4. **Jurnallarni kuzating**: Bot kartasidagi **"Jurnal"** tugmasini bosing. Real vaqt rejimida Server-Sent Events (SSE) orqali Docker jurnallari oqib keladi. `BOT_TOKEN` jurnallarda ko'rinmaydi, avtomatik `[REDACTED_SECRET]` qilinadi.
5. **Telegramda sinab ko'ring**: Telegramda botingizga kiring va `/start` yuboring. Botingiz javob qaytaradi va `/data/bot.db` bazasiga yozadi.
6. **Kodni yangilash**: Bot kartasidagi **"Yangilash"** tugmasini bosib, yangi ZIP yuklang. Konteyner yangilanadi, ammo `/data/bot.db` bazasidagi avvalgi ma'lumotlar to'liq saqlanib qoladi.
7. **Zaxira nusxa (Backup)**: **"Zaxira"** tugmasini bosing. Tizim botni to'xtatmasdan `/data` jildini `.tar.gz` formatida kompyuteringizga yuklab beradi.
8. **To'xtatish va O'chirish**: "To'xtatish", "Qayta ishga tushirish" va "O'chirish" tugmalari orqali konteyner va uning resurslari to'liq boshqariladi.

---

## 📁 Loyiha Tuzilmasi

```
.
├── backend/
│   ├── Dockerfile             # Python 3.12-slim backend konteyneri
│   ├── requirements.txt       # FastAPI, SQLAlchemy, Docker SDK, Argon2, Fernet
│   ├── app/
│   │   ├── main.py            # FastAPI ilovasi va 15s Docker status reconciler
│   │   ├── config.py          # Sozlamalar va xavfsizlik limitlari
│   │   ├── database.py        # SQLAlchemy async engine
│   │   ├── models/            # User, Bot, BotEnvVar
│   │   ├── schemas/           # Pydantic validatsiya sxemalari
│   │   ├── routers/           # auth.py, bots.py
│   │   ├── services/
│   │   │   ├── auth_service.py      # Argon2id, JWT, HttpOnly kuki, rate limiting
│   │   │   ├── crypto_service.py    # Fernet shifrlash va niqoblash
│   │   │   ├── detector_service.py  # Entrypoint va requirements aniqlash
│   │   │   ├── docker_service.py    # Rasmiy Docker SDK integratsiyasi (RealDockerService)
│   │   │   ├── zip_service.py       # Zip-Slip, symlink va bomba himoyasi
│   │   │   └── reconciler.py        # 15s Docker holatini bazaga sinxronlash
│   │   └── templates/
│   │       └── Dockerfile.template  # Hardened bot konteyneri shabloni
│   └── tests/
│       ├── conftest.py              # In-memory SQLite va test mijozi
│       ├── test_auth.py             # Argon2, Fernet, signup, login, kuki testlari
│       ├── test_zip_security.py     # Zip-Slip, symlink, junk filtrlash testlari
│       ├── test_authorization.py    # Multi-tenant foydalanuvchilar izolyatsiyasi
│       └── test_docker_real.py      # Docker SDK xavfsizlik parametrlari tekshiruvi
├── examples/
│   ├── echo_bot.zip           # Sinov boti (fayl sanagichi)
│   └── telegram_bot.zip       # Real aiogram 3.x Telegram boti (SQLite /data da)
├── src/                       # React 19 + Tailwind CSS frontend
│   ├── components/            # BotCard, CreateBotModal, UpdateCodeModal, EnvVarsModal, LogViewerModal
│   ├── lib/                   # botLogic.ts, store.ts
│   └── locales/uz.ts          # O'zbek tilidagi barcha matnlar
├── Caddyfile                  # Avtomatik SSL/TLS va unbuffered SSE teskari proksi
├── docker-compose.yml         # To'liq stack (Caddy, Postgres, Backend, Frontend)
├── Makefile                   # up, down, build, test, logs, clean buyruqlari
└── README.md
```

---

## 🛠 Muammolarni Bartaraf Etish (Troubleshooting)

- **Docker soketiga ulanish xatosi (`Permission denied /var/run/docker.sock`)**:
  Backend konteyneriga `/var/run/docker.sock` ulanganligiga va hostdagi foydalanuvchi `docker` guruhiga tegishli ekanligiga ishonch hosil qiling (`sudo usermod -aG docker $USER`).
- **Bot "build_failed" holatiga tushdi**:
  ZIP ichidagi `requirements.txt` da mavjud bo'lmagan paketlar yozilgan bo'lishi mumkin. Jurnallar bo'limini oching, xatolik satri ko'rsatiladi.
- **Portlar bandligi**:
  80 yoki 443 portlar band bo'lsa, `Caddyfile` yoki `docker-compose.yml` da portlarni o'zgartiring (masalan `8080:80`).
