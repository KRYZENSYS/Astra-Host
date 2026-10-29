#!/bin/bash
# ==============================================================================
# BotHost PostgreSQL Automated Backup Script with 14-day Retention
# ==============================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
DATE="$(date +%Y%m%d_%H%M%S)"
FILENAME="bothost_db_${DATE}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[$(date -Iseconds)] Starting PostgreSQL database backup..."
pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" | gzip -9 > "${BACKUP_DIR}/${FILENAME}"

SIZE=$(du -h "${BACKUP_DIR}/${FILENAME}" | cut -f1)
echo "[$(date -Iseconds)] Backup created successfully: ${FILENAME} (${SIZE})"

echo "[$(date -Iseconds)] Pruning backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -type f -name "bothost_db_*.sql.gz" -mtime +"${RETENTION_DAYS}" -delete

echo "[$(date -Iseconds)] Backup routine finished."
