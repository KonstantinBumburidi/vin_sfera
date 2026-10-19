#!/usr/bin/env bash
# Копирует базу данных и media с боевого сервера на ноутбук.
# Локальная база ПОЛНОСТЬЮ заменяется серверной (перед этим делается резервная копия).
#
# Запуск из корня проекта:  ./scripts/pull_from_prod.sh
# Только база:              ./scripts/pull_from_prod.sh --no-media

set -euo pipefail

SERVER="kostaky@77.246.247.35"
REMOTE_DIR="vin_sfera/vin_sfera"          # путь к проекту на сервере (от домашней папки)
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="$HOME/vin_sfera/db_backups"   # вне репозитория
STAMP="$(date +%Y%m%d_%H%M%S)"

WITH_MEDIA=1
[[ "${1:-}" == "--no-media" ]] && WITH_MEDIA=0

# Читает DB_* из .env, не выполняя файл как скрипт
load_env() {
    local file="$1" key value
    while IFS='=' read -r key value; do
        [[ "$key" =~ ^DB_[A-Z_]+$ ]] || continue
        value="${value%$'\r'}"
        value="${value#[\"\']}"; value="${value%[\"\']}"
        export "$key=$value"
    done < "$file"
}

mkdir -p "$BACKUP_DIR"
load_env "$PROJECT_DIR/.env"
LOCAL_DB="${DB_NAME:-vin_sfera_db}"
export PGPASSWORD="${DB_PASSWORD:-}"
PG_LOCAL=(-h "${DB_HOST:-127.0.0.1}" -p "${DB_PORT:-5432}" -U "$DB_USER")

echo "Локальная база '$LOCAL_DB' будет заменена базой с сервера $SERVER."
read -r -p "Продолжить? [y/N] " answer
[[ "$answer" =~ ^[yYдД]$ ]] || { echo "Отменено."; exit 1; }

echo "==> 1/4 Резервная копия локальной базы"
pg_dump "${PG_LOCAL[@]}" -Fc "$LOCAL_DB" > "$BACKUP_DIR/local_${STAMP}.dump"

echo "==> 2/4 Дамп базы на сервере и загрузка на ноутбук"
# На сервере берём параметры из его собственного .env
ssh "$SERVER" "cd $REMOTE_DIR && bash -s" > "$BACKUP_DIR/prod_${STAMP}.dump" <<'REMOTE'
set -euo pipefail
while IFS='=' read -r key value; do
    [[ "$key" =~ ^DB_[A-Z_]+$ ]] || continue
    value="${value%$'\r'}"
    value="${value#[\"\']}"; value="${value%[\"\']}"
    export "$key=$value"
done < .env
PGPASSWORD="${DB_PASSWORD:-}" pg_dump -h "${DB_HOST:-127.0.0.1}" -p "${DB_PORT:-5432}" \
    -U "$DB_USER" -Fc "${DB_NAME:-vin_sfera_db}"
REMOTE
echo "    сохранено: $BACKUP_DIR/prod_${STAMP}.dump"

echo "==> 3/4 Восстановление в локальную базу"
pg_restore "${PG_LOCAL[@]}" -d "$LOCAL_DB" --clean --if-exists --no-owner --no-privileges \
    "$BACKUP_DIR/prod_${STAMP}.dump"

if (( WITH_MEDIA )); then
    echo "==> 4/4 Копирование media (локальные файлы не удаляются)"
    rsync -az --info=progress2 "$SERVER:$REMOTE_DIR/media/" "$PROJECT_DIR/media/"
else
    echo "==> 4/4 media пропущено (--no-media)"
fi

echo "Готово. Откатить базу назад:"
echo "  pg_restore -h ${DB_HOST:-127.0.0.1} -U $DB_USER -d $LOCAL_DB --clean --if-exists --no-owner $BACKUP_DIR/local_${STAMP}.dump"
