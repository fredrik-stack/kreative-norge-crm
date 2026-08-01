#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

BACKUP_MODULE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/backup/lib.sh
source "$BACKUP_MODULE_DIR/lib.sh"

restore_dir=""
restore_container=""
status_available=0

cleanup() {
  # Capture the incoming trap status before any command changes it.
  # shellcheck disable=SC2155
  local rc="$?"
  if [ -n "$restore_container" ]; then
    docker rm -f "$restore_container" >/dev/null 2>&1 || true
  fi
  if [ -n "$restore_dir" ] && [ -d "$restore_dir" ]; then
    rm -rf -- "$restore_dir"
  fi
  if [ "$rc" -ne 0 ] && [ "$status_available" -eq 1 ]; then
    backup_status --event error --timestamp "$(backup_now)" --stage restore || true
  fi
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

backup_load_config
status_available=1
backup_acquire_lock
backup_preflight

latest_archive="$(backup_latest_archive)"
backup_safe_archive_name "$latest_archive" || backup_die "no safe backup archive is available for restore"
restore_dir="$(mktemp -d "$WORK_ROOT/restore.XXXXXX")"
chmod 700 "$restore_dir"
member_list="$restore_dir/archive-members.txt"
backup_borg list --format '{path}{NL}' "$BORG_REPOSITORY::$latest_archive" >"$member_list"

restore_members="$("$PYTHON_BIN" "$BACKUP_MODULE_DIR/status.py" restore-members <"$member_list")"
database_member="$(printf '%s\n' "$restore_members" | sed -n '1p')"
manifest_member="$(printf '%s\n' "$restore_members" | sed -n '2p')"
checksums_member="$(printf '%s\n' "$restore_members" | sed -n '3p')"
backup_validate_archive_member "$database_member"
backup_validate_archive_member "$manifest_member"
backup_validate_archive_member "$checksums_member"
staged_member_dir="$(dirname "$database_member")"
[ "$(dirname "$manifest_member")" = "$staged_member_dir" ] || backup_die "manifest is outside the staged backup directory"
[ "$(dirname "$checksums_member")" = "$staged_member_dir" ] || backup_die "checksums are outside the staged backup directory"
backup_validate_archive_member "$staged_member_dir"

(
  cd "$restore_dir"
  backup_borg extract "$BORG_REPOSITORY::$latest_archive" "$staged_member_dir"
)
database_dump="$restore_dir/$database_member"
manifest_file="$restore_dir/$manifest_member"
checksums_file="$restore_dir/$checksums_member"
[ -s "$database_dump" ] || backup_die "restored database dump is empty"
[ -s "$manifest_file" ] || backup_die "restored manifest is empty"
"$PYTHON_BIN" "$BACKUP_MODULE_DIR/status.py" validate-checksums --path "$checksums_file"
grep -Fx 'format_version=1' "$manifest_file" >/dev/null || backup_die "restored manifest format is invalid"
grep -Fx 'pg_restore_verification=passed' "$manifest_file" >/dev/null || backup_die "restored manifest lacks dump verification"
grep -Fx "borg_archive=$latest_archive" "$manifest_file" >/dev/null || backup_die "restored manifest archive identity does not match"
manifest_dump_checksum="$(sed -n 's/^database_dump_sha256=//p' "$manifest_file" | head -n 1)"
printf '%s' "$manifest_dump_checksum" | grep -Eq '^[0-9a-f]{64}$' || backup_die "restored manifest dump checksum is invalid"
[ "$manifest_dump_checksum" = "$(backup_sha256_value "$database_dump")" ] || backup_die "restored manifest dump checksum does not match"

staged_dir="$(dirname "$database_dump")"
(
  cd "$staged_dir"
  sha256sum --check --status "$(basename "$checksums_file")"
)

for media_bundle in "$staged_dir"/container-media-*.tar; do
  [ -f "$media_bundle" ] || continue
  tar -tf "$media_bundle" >/dev/null
done

docker run --rm --pull=never --network none -i "$RESTORE_POSTGRES_IMAGE" \
  pg_restore --list <"$database_dump" >/dev/null

restore_container="kreative-norge-restore-$RANDOM-$$"
restore_password="restore-smoke-$RANDOM-$$"
restore_env_file="$restore_dir/postgres.env"
printf 'POSTGRES_PASSWORD=%s\nPOSTGRES_DB=restore_smoke\n' "$restore_password" >"$restore_env_file"
chmod 600 "$restore_env_file"
docker run --detach --pull=never --network none --name "$restore_container" \
  --env-file "$restore_env_file" \
  "$RESTORE_POSTGRES_IMAGE" >/dev/null

ready=0
for ((_attempt = 1; _attempt <= 30; _attempt++)); do
  if docker exec "$restore_container" pg_isready --username postgres --dbname restore_smoke >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
[ "$ready" -eq 1 ] || backup_die "isolated PostgreSQL restore container did not become ready"

docker exec -i "$restore_container" pg_restore \
  --exit-on-error --no-owner --no-acl --username postgres --dbname restore_smoke <"$database_dump" >/dev/null

IFS=',' read -r -a expected_tables <<<"$EXPECTED_DATABASE_TABLES"
for table in "${expected_tables[@]}"; do
  printf '%s' "$table" | grep -Eq '^[a-z][a-z0-9_]*$' || backup_die "configured expected table name is unsafe"
  exists="$(docker exec "$restore_container" psql --username postgres --dbname restore_smoke --tuples-only --no-align \
    --command "SELECT to_regclass('public.$table') IS NOT NULL;")"
  [ "$(printf '%s' "$exists" | tr -d '[:space:]')" = "t" ] || backup_die "isolated restore is missing an expected database table"
  docker exec "$restore_container" psql --username postgres --dbname restore_smoke \
    --command "SELECT count(*) FROM \"$table\";" >/dev/null
done

sample_path_token="$(sed -n 's/^sample_path_token=//p' "$manifest_file" | head -n 1)"
sample_checksum="$(sed -n 's/^sample_checksum=//p' "$manifest_file" | head -n 1)"
if [ -n "$sample_path_token" ] || [ -n "$sample_checksum" ]; then
  printf '%s' "$sample_path_token" | grep -Eq '^[0-9a-f]{64}$' || backup_die "manifest sample token is invalid"
  printf '%s' "$sample_checksum" | grep -Eq '^[0-9a-f]{64}$' || backup_die "manifest sample checksum is invalid"
  sample_found=0
  while IFS= read -r member; do
    backup_validate_archive_member "$member"
    token="$(printf '%s' "$member" | sha256sum | awk '{print $1}')"
    [ "$token" = "$sample_path_token" ] || continue
    actual_checksum="$(backup_borg extract --stdout "$BORG_REPOSITORY::$latest_archive" "$member" | sha256sum | awk '{print $1}')"
    [ "$actual_checksum" = "$sample_checksum" ] || backup_die "representative media checksum did not match"
    sample_found=1
    break
  done <"$member_list"
  [ "$sample_found" -eq 1 ] || backup_die "representative media sample is missing from archive"
fi

backup_status --event restore-success --timestamp "$(backup_now)" --archive "$latest_archive"
gate_file="${RESTORE_GATE_FILE:-/var/lib/kreative-norge-backup/restore-smoke.ok}"
backup_require_absolute_path RESTORE_GATE_FILE "$gate_file"
mkdir -p "$(dirname "$gate_file")"
printf 'archive=%s\nverified_at=%s\n' "$latest_archive" "$(backup_now)" >"$gate_file"
chmod 600 "$gate_file"
status_available=0
backup_log "isolated restore smoke test completed successfully"
