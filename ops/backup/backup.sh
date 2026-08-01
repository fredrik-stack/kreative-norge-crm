#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

BACKUP_MODULE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/backup/lib.sh
source "$BACKUP_MODULE_DIR/lib.sh"

mode="run"
case "${1:-}" in
  --preflight) mode="preflight" ;;
  --help)
    echo "Usage: backup.sh [--preflight]"
    exit 0
    ;;
  '') ;;
  *) backup_die "unsupported argument"; exit 2 ;;
esac

job_dir=""
status_started=0

cleanup() {
  # Capture the incoming trap status before any command changes it.
  # shellcheck disable=SC2155
  local rc="$?"
  if [ -n "$job_dir" ] && [ -d "$job_dir" ]; then
    rm -rf -- "$job_dir"
  fi
  if [ "$rc" -ne 0 ] && [ "$status_started" -eq 1 ]; then
    backup_status --event error --timestamp "$(backup_now)" --stage "$BACKUP_FAILURE_STAGE" || true
  fi
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

backup_load_config
backup_preflight

if [ "$mode" = "preflight" ]; then
  backup_log "preflight passed"
  exit 0
fi

backup_acquire_lock
backup_status --event start --timestamp "$(backup_now)"
status_started=1

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
archive_name="${ARCHIVE_PREFIX}-${BACKUP_ENVIRONMENT}-${timestamp}"
backup_safe_archive_name "$archive_name" || backup_die "generated archive name is unsafe"
job_dir="$(mktemp -d "$WORK_ROOT/run.XXXXXX")"
chmod 700 "$job_dir"
dump_path="$job_dir/database.dump"
manifest_path="$job_dir/manifest.txt"
checksums_path="$job_dir/checksums.sha256"

BACKUP_FAILURE_STAGE="disk"
database_size_bytes="$(backup_compose_exec "$DATABASE_SERVICE" sh -ec 'psql --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --tuples-only --no-align --command="SELECT pg_database_size(current_database());"')"
database_size_bytes="$(printf '%s' "$database_size_bytes" | tr -d '[:space:]')"
printf '%s' "$database_size_bytes" | grep -Eq '^[0-9]+$' || backup_die "database size query returned an invalid value"
available_bytes="$(df -PB1 "$WORK_ROOT" | awk 'NR==2 {print $4}')"
required_bytes=$((10#$database_size_bytes + 10#$MIN_FREE_BYTES))
[ "$available_bytes" -ge "$required_bytes" ] || backup_die "insufficient free disk for protected backup staging"

BACKUP_FAILURE_STAGE="dump"
backup_log "creating consistent PostgreSQL custom-format dump"
backup_compose_exec "$DATABASE_SERVICE" sh -ec 'exec pg_dump --format=custom --no-owner --no-acl --username="$POSTGRES_USER" --dbname="$POSTGRES_DB"' >"$dump_path"
[ -s "$dump_path" ] || backup_die "pg_dump produced an empty dump"

BACKUP_FAILURE_STAGE="dump_verify"
backup_compose_exec "$DATABASE_SERVICE" pg_restore --list <"$dump_path" >/dev/null
postgres_version="$(backup_compose_exec "$DATABASE_SERVICE" postgres --version | tr '\n' ' ')"

BACKUP_FAILURE_STAGE="media"
included_paths=""
excluded_paths=""
borg_sources=("$job_dir")

while IFS= read -r path; do
  if [ -d "$path" ]; then
    borg_sources+=("$path")
    included_paths="${included_paths}${path}\n"
  else
    excluded_paths="${excluded_paths}${path}\n"
  fi
done < <(backup_split_paths "$HOST_MEDIA_PATHS")

api_container="$("${BACKUP_COMPOSE[@]}" ps -q "$API_SERVICE")"
container_index=0
while IFS= read -r container_path; do
  container_index=$((container_index + 1))
  bundle="$job_dir/container-media-${container_index}.tar"
  if [ -n "$api_container" ] && docker exec "$api_container" test -d "$container_path" >/dev/null 2>&1; then
    parent="${container_path%/*}"
    basename="${container_path##*/}"
    docker exec "$api_container" tar -C "$parent" -cf - "$basename" >"$bundle"
    included_paths="${included_paths}container:${container_path}\n"
  else
    excluded_paths="${excluded_paths}container:${container_path}\n"
  fi
done < <(backup_split_paths "$API_CONTAINER_MEDIA_PATHS")

BACKUP_FAILURE_STAGE="config"
config_paths=()
while IFS= read -r config_path; do
  if [ -f "$config_path" ]; then
    config_paths+=("${config_path#/}")
    included_paths="${included_paths}${config_path}\n"
  else
    excluded_paths="${excluded_paths}${config_path}\n"
  fi
done < <(backup_split_paths "$SERVER_CONFIG_PATHS")
if [ "${#config_paths[@]}" -gt 0 ]; then
  tar -C / -cf "$job_dir/server-config.tar" "${config_paths[@]}"
fi

BACKUP_FAILURE_STAGE="manifest"
dump_sha256="$(backup_sha256_value "$dump_path")"
dump_size="$(wc -c <"$dump_path" | tr -d '[:space:]')"
for staged_file in "$job_dir"/*.dump "$job_dir"/*.tar; do
  [ -f "$staged_file" ] || continue
  (cd "$job_dir" && sha256sum "$(basename "$staged_file")") >>"$checksums_path"
done

git_commit="$(git -C "$APP_ROOT" rev-parse HEAD)"
if [ -n "$(git -C "$APP_ROOT" status --porcelain)" ]; then
  git_status="dirty"
else
  git_status="clean"
fi

sample_path_token=""
sample_checksum=""
while IFS= read -r media_root; do
  [ -d "$media_root" ] || continue
  sample_path=""
  while IFS= read -r -d '' candidate_path; do
    sample_path="$candidate_path"
    break
  done < <(find "$media_root" -type f -print0 2>/dev/null)
  if [ -n "$sample_path" ]; then
    sample_path_token="$(printf '%s' "${sample_path#/}" | sha256sum | awk '{print $1}')"
    sample_checksum="$(backup_sha256_value "$sample_path")"
    break
  fi
done < <(backup_split_paths "$HOST_MEDIA_PATHS")

{
  echo "format_version=1"
  echo "utc_timestamp=$(backup_now)"
  echo "environment=$BACKUP_ENVIRONMENT"
  echo "server_hostname=$(hostname)"
  echo "git_commit=$git_commit"
  echo "git_worktree=$git_status"
  echo "postgres_version=$postgres_version"
  echo "database_dump_filename=database.dump"
  echo "database_dump_size_bytes=$dump_size"
  echo "database_dump_sha256=$dump_sha256"
  printf '%b' "$included_paths" | sed 's/^/included_path=/'
  printf '%b' "$excluded_paths" | sed 's/^/excluded_path=/'
  echo "checksums_file=checksums.sha256"
  echo "borg_archive=$archive_name"
  echo "backup_script_version=$BACKUP_MODULE_VERSION"
  echo "pg_restore_verification=passed"
  echo "sample_path_token=$sample_path_token"
  echo "sample_checksum=$sample_checksum"
} >"$manifest_path"

BACKUP_FAILURE_STAGE="create"
backup_log "creating encrypted off-server Borg archive $archive_name"
backup_borg create --stats --show-rc --compression zstd,6 \
  --exclude '*/__pycache__/*' \
  --exclude '*/node_modules/*' \
  --exclude '*/staticfiles/*' \
  --exclude '*/.cache/*' \
  "$BORG_REPOSITORY::$archive_name" "${borg_sources[@]}"
backup_borg info --json "$BORG_REPOSITORY::$archive_name" >/dev/null

BACKUP_FAILURE_STAGE="repository"
backup_borg check --repository-only --max-duration "$BORG_CHECK_MAX_DURATION" "$BORG_REPOSITORY"

BACKUP_FAILURE_STAGE="prune"
backup_borg prune --show-rc --list \
  --glob-archives "${ARCHIVE_PREFIX}-${BACKUP_ENVIRONMENT}-*" \
  --keep-daily "$RETENTION_DAILY" \
  --keep-weekly "$RETENTION_WEEKLY" \
  --keep-monthly "$RETENTION_MONTHLY" \
  "$BORG_REPOSITORY"

BACKUP_FAILURE_STAGE="compact"
backup_borg compact "$BORG_REPOSITORY"

backup_status --event success --timestamp "$(backup_now)" --archive "$archive_name"
status_started=0
backup_log "backup completed successfully: $archive_name"
