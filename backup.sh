#!/bin/bash
set -e

# Config
BACKUP_DIR="/app/backups"
DB_NAME="${DB_NAME:-restaurante_db}"
DB_USER="${DB_USER:-restaurante}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="${BACKUP_DIR}/backup_${DB_NAME}_${TIMESTAMP}.sql.gz"
KEEP_DAYS=7

echo "========================================"
echo "  Backup de Base de Datos"
echo "========================================"

mkdir -p "$BACKUP_DIR"

echo "[1/2] Generando dump de PostgreSQL..."
PGPASSWORD="${DB_PASSWORD}" pg_dump \
    -h "${DB_HOST:-db}" \
    -p "${DB_PORT:-5432}" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    --clean \
    --if-exists \
    --no-owner \
    | gzip > "$FILENAME"

echo "[2/2] Limpiando backups antiguos (+$KEEP_DAYS dias)..."
find "$BACKUP_DIR" -name "backup_${DB_NAME}_*.sql.gz" -mtime +$KEEP_DAYS -delete

echo ""
echo "Backup completado: $FILENAME"
echo "Tamano: $(du -h "$FILENAME" | cut -f1)"
