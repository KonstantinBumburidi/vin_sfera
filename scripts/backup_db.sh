#!/usr/bin/env bash
# Резервная копия базы данных (запускать на сервере, из корня проекта).
#
#   ./scripts/backup_db.sh            # копия в ~/db_backups/, старше 14 дней удаляются
#   ./scripts/backup_db.sh --keep 30  # хранить копии 30 дней
#
# Восстановить из копии (текущая база будет ПОЛНОСТЬЮ заменена):
#   sudo systemctl stop vin_sfera
#   ./scripts/backup_db.sh --restore ~/db_backups/prod_ДАТА.dump
#   sudo systemctl start vin_sfera
#
# media/ (картинки, аудио, документы) в копию НЕ входит — это отдельная папка.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="$HOME/db_backups"
KEEP_DAYS=14
RESTORE_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --keep)    KEEP_DAYS="$2"; shift 2 ;;
        --restore) RESTORE_FILE="$2"; shift 2 ;;
        *) echo "Неизвестный параметр: $1"; exit 1 ;;
    esac
done

# Читает DB_* из .env, не выполняя файл как скрипт
while IFS='=' read -r key value; do
    [[ "$key" =~ ^DB_[A-Z_]+$ ]] || continue
    value="${value%$'\r'}"
    value="${value#[\"\']}"; value="${value%[\"\']}"
    export "$key=$value"
done < "$PROJECT_DIR/.env"

DB="${DB_NAME:-vin_sfera_db}"
export PGPASSWORD="${DB_PASSWORD:-}"
PG=(-h "${DB_HOST:-127.0.0.1}" -p "${DB_PORT:-5432}" -U "$DB_USER")

if [[ -n "$RESTORE_FILE" ]]; then
    [[ -f "$RESTORE_FILE" ]] || { echo "Нет файла $RESTORE_FILE"; exit 1; }
    echo "База '$DB' будет ПОЛНОСТЬЮ заменена копией $RESTORE_FILE."
    read -r -p "Продолжить? [y/N] " answer
    [[ "$answer" =~ ^[yYдД]$ ]] || { echo "Отменено."; exit 1; }
    pg_restore "${PG[@]}" -d "$DB" --clean --if-exists --no-owner "$RESTORE_FILE"
    echo "Готово. Не забудьте: sudo systemctl start vin_sfera"
    exit 0
fi

mkdir -p "$BACKUP_DIR"
FILE="$BACKUP_DIR/prod_$(date +%Y%m%d_%H%M%S).dump"
pg_dump "${PG[@]}" -Fc "$DB" > "$FILE.part"
mv "$FILE.part" "$FILE"
echo "Копия сохранена: $FILE ($(du -h "$FILE" | cut -f1))"

OLD=$(find "$BACKUP_DIR" -maxdepth 1 -name 'prod_*.dump' -mtime +"$KEEP_DAYS" -print -delete | wc -l)
if (( OLD > 0 )); then echo "Удалено старых копий (старше $KEEP_DAYS дн.): $OLD"; fi
echo "Всего копий: $(find "$BACKUP_DIR" -maxdepth 1 -name 'prod_*.dump' | wc -l)"
echo "Забрать на ноутбук (выполнить на ноутбуке):"
echo "  scp 'kostaky@77.246.247.35:db_backups/prod_*.dump' ~/vin_sfera/db_backups/"
