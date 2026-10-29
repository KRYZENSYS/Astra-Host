#!/bin/bash
# ==============================================================================
# BotHost /data Volumes Backup Script with 7-day Retention
# ==============================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups/bot_volumes}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DATE="$(date +%Y%m%d_%H%M%S)"

mkdir -p "${BACKUP_DIR}"

echo "[$(date -Iseconds)] Scanning active bot persistent data volumes..."
VOLUMES=$(docker volume ls -q --filter label=bothost.bot_id || true)

for VOL in ${VOLUMES}; do
    BOT_ID=$(docker volume inspect "${VOL}" --format '{{ index .Labels "bothost.bot_id" }}')
    ARCHIVE_NAME="bot_${BOT_ID}_${DATE}.tar.gz"

    echo "[$(date -Iseconds)] Backing up volume: ${VOL} for bot ${BOT_ID}..."
    docker run --rm \
        -v "${VOL}:/data:ro" \
        -v "${BACKUP_DIR}:/backup" \
        alpine tar czf "/backup/${ARCHIVE_NAME}" -C /data .
done

echo "[$(date -Iseconds)] Pruning volume archives older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -type f -name "bot_*.tar.gz" -mtime +"${RETENTION_DAYS}" -delete

echo "[$(date -Iseconds)] Volume backups complete."
