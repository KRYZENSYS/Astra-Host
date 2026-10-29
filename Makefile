.PHONY: up down build test logs clean help

help:
	@echo "BotHost Boshqaruv Buyruqlari:"
	@echo "  make up      - Butun tizimni ishga tushirish (Caddy + Postgres + Backend + Frontend)"
	@echo "  make down    - Tizimni to'xtatish"
	@echo "  make build   - Konteynerlarni qayta yig'ish"
	@echo "  make test    - Backend va real Docker testlarini yurgizish"
	@echo "  make logs    - Xizmatlar jurnallarini jonli kuzatish"
	@echo "  make clean   - Barcha to'xtatilgan bot konteynerlari va vaqtinchalik fayllarni tozalash"

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

test:
	docker compose exec backend pytest tests/ -v

logs:
	docker compose logs -f

clean:
	docker compose down -v
	rm -rf /var/lib/bothost/bots/*
