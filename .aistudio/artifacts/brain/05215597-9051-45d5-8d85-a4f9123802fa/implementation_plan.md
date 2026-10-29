# BotHost Stage 1: Architecture, Database Schema, and API Specification

This document presents the system architecture, folder structure, database schema, and API contract for **BotHost Stage 1** (Real MVP, no mocks). Every component is designed to run against a real Docker daemon on a production Linux VPS with real Telegram bot tokens.

***

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INTERNET / CLIENT BROWSER                         │
│       React 19 + Vite + Tailwind (Mobile-first, Uzbek UI / O'zbek tili)     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS / WSS / SSE
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    CADDY REVERSE PROXY (Docker container)                    │
│   • Automatic Let's Encrypt TLS / HTTPS                                     │
│   • Reverse proxies `/api/*` to FastAPI backend                             │
│   • Reverse proxies `/` to static frontend build                            │
│   • Disables buffering on `/api/v1/bots/*/logs/stream` for real-time SSE    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                FASTAPI BACKEND (Python 3.12, unprivileged user)              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ Endpoints: Auth (HttpOnly Cookie), Bot CRUD, Env Vars, Logs, Backup   │  │
│  ├───────────────────────────────────────────────────────────────────────┤  │
│  │ Security & Services:                                                  │  │
│  │  • Auth: Argon2id password hashing + JWT in HttpOnly, Secure cookie   │  │
│  │  • Rate Limiting: 10 attempts / 10 min per IP on login/signup        │  │
│  │  • Secrets: Fernet symmetric encryption at rest for env vars          │  │
│  │  • Zip Inspector: Zip-Slip traversal check, 20MB limit, 100MB unpack, │  │
│  │    junk exclusion (__pycache__, .git, *.pyc, .env, *.db), entry detect │  │
│  │  • Docker Reconciler: Background loop syncing DB with real containers │  │
│  │  • Log Redactor: Automatically redacts known env values from logs     │  │
│  ├───────────────────────────────────────────────────────────────────────┤  │
│  │ Persistence: Async SQLAlchemy 2.x + Alembic Migrations                │  │
│  └───────────────────┬───────────────────────────────┬───────────────────┘  │
└──────────────────────┼───────────────────────────────┼──────────────────────┘
                       │ SQL                           │ Docker Socket
┌──────────────────────▼──────────┐   ┌────────────────▼──────────────────────┐
│       POSTGRESQL 16 DATABASE    │   │         DOCKER DAEMON (HOST)          │
│   • `users` table               │   │   • `bothost_bot_<id>` containers     │
│   • `bots` table                │   │   • Hardened isolation constraints:   │
│   • `bot_env_vars` table        │   │     - non-root user (botuser 10001)   │
│   • `alembic_version` table     │   │     - read_only root filesystem       │
│                                 │   │     - tmpfs at /tmp (64 MB)           │
│                                 │   │     - cap_drop: ALL, no-new-privileges│
│                                 │   │     - mem_limit: 256 MB (no swap)     │
│                                 │   │     - nano_cpus: 0.25 CPU             │
│                                 │   │     - pids_limit: 100                 │
│                                 │   │     - dedicated bridge network        │
│                                 │   │     - named volume `/data` (rw)       │
│                                 │   │     - restart policy: on-failure (5)  │
│                                 │   │     - log driver: json-file (5m x 3)  │
└─────────────────────────────────┘   └───────────────────────────────────────┘
```

***

## 2. Folder Structure

```text
bothost/
├── docker-compose.yml              # Multi-container production stack (Caddy, Postgres, Backend, Frontend)
├── Caddyfile                       # Reverse proxy with automatic HTTPS and SSE streaming configuration
├── Makefile                        # make up, make test, make logs, make down
├── .env.example                    # Template with POSTGRES_*, JWT_SECRET, FERNET_KEY, APP_URL
├── README.md                       # Complete Uzbek installation & testing documentation
├── examples/
│   ├── echo_bot/                   # Sample test bot: logs timestamp and writes to /data/counter.txt
│   │   ├── main.py
│   │   └── requirements.txt
│   ├── echo_bot.zip                # Packaged zip for automated integration test
│   ├── telegram_bot/               # Real aiogram 3.x Telegram bot reading BOT_TOKEN and SQLite in /data
│   │   ├── bot.py
│   │   └── requirements.txt
│   └── telegram_bot.zip            # Packaged zip for manual verification
├── backend/
│   ├── Dockerfile                  # Non-root Python 3.12-slim backend container
│   ├── requirements.txt            # fastapi, uvicorn, sqlalchemy, asyncpg, docker, argon2-cffi, cryptography, pyjwt
│   ├── alembic.ini                 # Alembic migration configuration
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 001_initial_stage1_schema.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application, CORS, cookie middlewares, exception handlers
│   │   ├── config.py               # Pydantic Settings (DB URL, Fernet key, JWT secret, data paths)
│   │   ├── database.py             # Async engine, sessionmaker, declarative Base
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py             # User model
│   │   │   ├── bot.py              # Bot model
│   │   │   └── env_var.py          # BotEnvVar model (Fernet encrypted)
│   │   ├── schemas/
│   │   │   ├── auth.py             # Signup, Login, UserOut schemas
│   │   │   ├── bot.py              # BotCreate, BotOut, BotDetail, CodeUpdate
│   │   │   └── env_var.py          # EnvVarCreate, EnvVarOut (masked)
│   │   ├── services/
│   │   │   ├── auth_service.py     # Argon2 hashing, JWT cookie management, rate limiter
│   │   │   ├── crypto_service.py   # Fernet encryption & UI masking (••••1234)
│   │   │   ├── zip_service.py      # Zip-slip validation, bomb defense, junk filtering, flattening
│   │   │   ├── detector_service.py # if __name__ == '__main__' detection, requirements.txt scanner
│   │   │   ├── docker_service.py   # Real Docker SDK container manager with strict constraints
│   │   │   ├── reconciler.py       # Periodic container status synchronization (every 15s)
│   │   │   └── log_service.py      # Redacting log streamer with per-user connection throttling
│   │   ├── templates/
│   │   │   └── Dockerfile.template # python:3.12-slim hardened base image
│   │   └── routers/
│   │       ├── auth.py             # /api/v1/auth/*
│   │       └── bots.py             # /api/v1/bots/*
│   └── tests/
│       ├── conftest.py             # Pytest async fixtures and test client
│       ├── test_auth.py            # Signup, login, rate limiting, generic errors
│       ├── test_zip_security.py    # Zip-slip, zip bomb, symlink, oversize rejection
│       ├── test_crypto.py          # Fernet encryption at rest, masking, key validation
│       ├── test_authorization.py   # User isolation (User A cannot access User B's bot)
│       └── test_docker_real.py     # End-to-end container build, run, inspect, restart, /data persistence
└── frontend/ (in workspace root)
    ├── package.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── locales/uz.ts           # Single comprehensive Uzbek i18n dictionary
        ├── types/index.ts          # TypeScript interfaces
        ├── lib/api.ts              # Fetch client handling HttpOnly credentials & error parsing
        ├── components/
        │   ├── Navbar.tsx          # Clean header with auth state and Uzbek copy
        │   ├── BotCard.tsx         # Bot status, controls (Start/Stop/Restart/Delete)
        │   ├── CreateBotModal.tsx  # Zip upload, entrypoint selector, env vars
        │   ├── EnvVarsEditor.tsx   # Key-value manager with regex validation [A-Z_][A-Z0-9_]*
        │   ├── LogViewer.tsx       # Real-time SSE streaming with redacted secrets
        │   ├── CodeUpdateModal.tsx # Re-upload zip without touching /data volume
        │   └── BackupButton.tsx    # Download tar.gz of /data volume
        └── App.tsx                 # Main application view with responsive layout (380px mobile ready)
```

***

## 3. Database Schema (PostgreSQL 16)

```sql
-- 1. Users Table
CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX ix_users_email ON users(email);

-- 2. Bots Table
CREATE TABLE bots (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    entrypoint VARCHAR(255) NOT NULL DEFAULT 'main.py',
    has_requirements BOOLEAN NOT NULL DEFAULT FALSE,
    container_id VARCHAR(100) NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'created', 
    -- Status enum: created, building, build_failed, stopped, starting, running, crashed
    last_error TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX ix_bots_user_id ON bots(user_id);
CREATE INDEX ix_bots_status ON bots(status);

-- 3. Bot Environment Variables Table
CREATE TABLE bot_env_vars (
    id VARCHAR(36) PRIMARY KEY,
    bot_id VARCHAR(36) NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    key VARCHAR(100) NOT NULL,
    encrypted_value VARCHAR(1000) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_bot_env_key UNIQUE (bot_id, key)
);
CREATE INDEX ix_bot_env_vars_bot_id ON bot_env_vars(bot_id);
```

***

## 4. API Specification

All endpoints are mounted under `/api/v1` and communicate via JSON (except file uploads and log SSE stream).

### Authentication (`/api/v1/auth`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/v1/auth/signup` | Registers new user (`email`, `password` $\ge 8$). Returns generic error on conflict. | No |
| `POST` | `/api/v1/auth/login` | Validates Argon2 hash; sets `bothost_access_token` HttpOnly, Secure, SameSite=Lax cookie. Rate limited (10 attempts / 10 min per IP). | No |
| `POST` | `/api/v1/auth/logout` | Clears HttpOnly cookie. | Yes |
| `GET` | `/api/v1/auth/me` | Returns current user profile (`id`, `email`, `created_at`). | Yes |

### Bot Lifecycle (`/api/v1/bots`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/bots` | Lists all bots owned by the current user. | Yes |
| `POST` | `/api/v1/bots` | Multipart upload (`name`, `entrypoint` optional, `env_vars` JSON string, `file` .zip). Validates archive, generates Dockerfile, starts build background task. Limit: 1 bot per user. | Yes |
| `GET` | `/api/v1/bots/{bot_id}` | Returns bot details, real container status, and masked env vars. | Yes |
| `POST` | `/api/v1/bots/{bot_id}/start` | Starts the Docker container with all required security flags. Idempotent. | Yes |
| `POST` | `/api/v1/bots/{bot_id}/stop` | Stops the running container safely with 10s timeout. Idempotent. | Yes |
| `POST` | `/api/v1/bots/{bot_id}/restart`| Restarts the container. Idempotent. | Yes |
| `DELETE`| `/api/v1/bots/{bot_id}` | Removes container, image, source files, and optionally `/data` volume if `?delete_volume=true`. | Yes |
| `PUT` | `/api/v1/bots/{bot_id}/code` | Uploads new zip; rebuilds image and restarts container while preserving `/data` volume. | Yes |
| `GET` | `/api/v1/bots/{bot_id}/backup` | Streams `tar.gz` archive of `/data` persistent volume. | Yes |

### Environment Variables (`/api/v1/bots/{bot_id}/env`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/bots/{bot_id}/env` | Returns masked list of environment variables (`key`, `masked_value`). | Yes |
| `PUT` | `/api/v1/bots/{bot_id}/env` | Replaces or updates env vars (`key`, `value`). Validates key regex `^[A-Z_][A-Z0-9_]*$`. Encrypts with Fernet. Signals that restart is required. | Yes |

### Logs (`/api/v1/bots/{bot_id}/logs`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/bots/{bot_id}/logs?lines=200` | Returns the last N log lines from the container, with known env values redacted. | Yes |
| `GET` | `/api/v1/bots/{bot_id}/logs/stream` | Server-Sent Events (SSE) stream of real-time container output. Redacts env vars. Limited to 3 concurrent streams per user. Closes on disconnect. | Yes |

***

## 5. Scope Boundaries (Strictly Stage 1)

### In-Scope (Implemented & Tested)
- Real Docker SDK integration (no mocks, no fakes).
- Hardened container flags: non-root `botuser`, `read_only=True`, `tmpfs=/tmp:rw,size=64m`, `cap_drop=['ALL']`, `security_opt=['no-new-privileges']`, `mem_limit=256m`, `pids_limit=100`, `nano_cpus=250000000`, named persistent volume at `/data`.
- HttpOnly Cookie JWT authentication with Argon2id.
- Zip security: traversal check, bomb check, junk exclusion, flatten top-level directory, entrypoint autodetection.
- Real-time SSE logs with secret redaction.
- Clean mobile-first Uzbek UI (380px responsive).
- Caddy reverse proxy with automatic HTTPS in `docker-compose.yml`.
- `examples/echo_bot.zip` and `examples/telegram_bot.zip`.

### Out-of-Scope (Removed from UI & Backend)
- Payments (Payme / Click)
- Administrator panel & global multi-user controls
- Multiple subscription plans (Fixed to Free Tier: 1 bot per user)
- GitHub public URL import
- Resource telemetry graphs (CPU/RAM charts)
- Multi-node clustering
