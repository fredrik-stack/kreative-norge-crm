#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

# Used by backup.sh after this library is sourced.
# shellcheck disable=SC2034
BACKUP_MODULE_VERSION="1"
BACKUP_MODULE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_ENV_FILE="${BACKUP_ENV_FILE:-/etc/kreative-norge-backup/backup.env}"
# Used by backup.sh after this library is sourced.
# shellcheck disable=SC2034
BACKUP_FAILURE_STAGE="preflight"
BACKUP_TEST_MODE="${BACKUP_TEST_MODE:-0}"

backup_now() {
  date -u +%Y-%m-%dT%H:%M:%SZ
}

backup_log() {
  printf '%s backup[%s]: %s\n' "$(backup_now)" "$$" "$*" >&2
}

backup_die() {
  backup_log "ERROR: $1"
  return 1
}

backup_require_command() {
  command -v "$1" >/dev/null 2>&1 || backup_die "required command is unavailable: $1"
}

backup_require_root() {
  if [ "$BACKUP_TEST_MODE" != "1" ]; then
    [ "$(id -u)" = "0" ] || backup_die "backup commands must run as root"
  fi
}

backup_validate_root_file() {
  local path="$1"
  local label="$2"
  [ -f "$path" ] || backup_die "$label is missing"
  if [ "$BACKUP_TEST_MODE" = "1" ]; then
    return 0
  fi
  local uid mode mode_value
  uid="$(stat -c '%u' "$path")"
  mode="$(stat -c '%a' "$path")"
  [ "$uid" = "0" ] || backup_die "$label must be owned by root"
  mode_value=$((8#$mode))
  (( (mode_value & 0077) == 0 )) || backup_die "$label must not be accessible by group or other users"
}

backup_require_absolute_path() {
  case "$2" in
    /*) ;;
    *) backup_die "$1 must be an absolute path" ;;
  esac
}

backup_require_safe_shell_path() {
  printf '%s' "$2" | grep -Eq '^/[A-Za-z0-9_./-]+$' || {
    backup_die "$1 contains unsafe shell characters"
    return 1
  }
  case "$2" in
    */../*|*/..) backup_die "$1 contains a parent-directory component" ;;
  esac
}

backup_load_config() {
  backup_validate_root_file "$BACKUP_ENV_FILE" "backup environment file"
  set -a
  # shellcheck disable=SC1090
  source "$BACKUP_ENV_FILE"
  set +a

  local required
  for required in \
    BACKUP_ENVIRONMENT APP_ROOT COMPOSE_FILE COMPOSE_ENV_FILE DATABASE_SERVICE API_SERVICE \
    WORK_ROOT STATUS_FILE LOCK_FILE BORG_REPOSITORY BORG_REPOSITORY_ID BORG_REMOTE_PATH \
    BORG_EXPECTED_MAJOR_MINOR BORG_PASSPHRASE_FILE BORG_SSH_KEY BORG_KNOWN_HOSTS \
    STORAGE_BOX_HOST RETENTION_DAILY RETENTION_WEEKLY RETENTION_MONTHLY; do
    [ -n "${!required:-}" ] || backup_die "required configuration is missing: $required"
  done

  backup_require_absolute_path APP_ROOT "$APP_ROOT"
  backup_require_absolute_path COMPOSE_FILE "$COMPOSE_FILE"
  backup_require_absolute_path COMPOSE_ENV_FILE "$COMPOSE_ENV_FILE"
  backup_require_absolute_path WORK_ROOT "$WORK_ROOT"
  backup_require_absolute_path STATUS_FILE "$STATUS_FILE"
  backup_require_absolute_path LOCK_FILE "$LOCK_FILE"
  backup_require_absolute_path BORG_PASSPHRASE_FILE "$BORG_PASSPHRASE_FILE"
  backup_require_absolute_path BORG_SSH_KEY "$BORG_SSH_KEY"
  backup_require_absolute_path BORG_KNOWN_HOSTS "$BORG_KNOWN_HOSTS"
  backup_require_safe_shell_path APP_ROOT "$APP_ROOT"
  backup_require_safe_shell_path COMPOSE_FILE "$COMPOSE_FILE"
  backup_require_safe_shell_path COMPOSE_ENV_FILE "$COMPOSE_ENV_FILE"
  backup_require_safe_shell_path WORK_ROOT "$WORK_ROOT"
  backup_require_safe_shell_path STATUS_FILE "$STATUS_FILE"
  backup_require_safe_shell_path LOCK_FILE "$LOCK_FILE"
  backup_require_safe_shell_path BORG_PASSPHRASE_FILE "$BORG_PASSPHRASE_FILE"
  backup_require_safe_shell_path BORG_SSH_KEY "$BORG_SSH_KEY"
  backup_require_safe_shell_path BORG_KNOWN_HOSTS "$BORG_KNOWN_HOSTS"
  printf '%s' "$STORAGE_BOX_HOST" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9.-]*$' || \
    backup_die "STORAGE_BOX_HOST is invalid"

  [ "$BORG_EXPECTED_MAJOR_MINOR" = "1.2" ] || backup_die "this module is pinned to Borg 1.2.x"
  [ "$BORG_REMOTE_PATH" = "borg-1.2" ] || backup_die "BORG_REMOTE_PATH must be borg-1.2"
  printf '%s' "$BORG_REPOSITORY_ID" | grep -Eq '^[0-9a-fA-F]{64}$' || \
    backup_die "BORG_REPOSITORY_ID is missing or invalid"
  case "$BORG_REPOSITORY" in
    ssh://*) ;;
    *) backup_die "BORG_REPOSITORY must use an ssh:// URL" ;;
  esac
  case "$BORG_REPOSITORY" in
    *[[:space:]]*) backup_die "BORG_REPOSITORY contains whitespace" ;;
  esac
  local authority userinfo repository_host repository_path
  authority="${BORG_REPOSITORY#ssh://}"
  authority="${authority%%/*}"
  case "$authority" in
    *@*:23) ;;
    *) backup_die "BORG_REPOSITORY must use a dedicated SSH user and Storage Box port 23" ;;
  esac
  userinfo="${authority%@*}"
  printf '%s' "$userinfo" | grep -Eq '^[A-Za-z0-9._-]+$' || \
    backup_die "BORG_REPOSITORY user is invalid"
  case "$userinfo" in
    *:*) backup_die "BORG_REPOSITORY must not contain a password" ;;
  esac
  repository_host="${authority##*@}"
  repository_host="${repository_host%%:*}"
  [ "$repository_host" = "$STORAGE_BOX_HOST" ] || \
    backup_die "BORG_REPOSITORY host does not match STORAGE_BOX_HOST"
  repository_path="${BORG_REPOSITORY#ssh://}"
  repository_path="/${repository_path#*/}"
  printf '%s' "$repository_path" | grep -Eq '^/\./[A-Za-z0-9_./-]+$' || \
    backup_die "BORG_REPOSITORY must use a safe relative Storage Box path"
  case "$repository_path" in
    */../*|*/..) backup_die "BORG_REPOSITORY contains a parent-directory component" ;;
  esac

  BORG_BIN="${BORG_BIN:-borg}"
  PYTHON_BIN="${PYTHON_BIN:-python3}"
  MIN_FREE_BYTES="${MIN_FREE_BYTES:-1073741824}"
  HOST_MEDIA_PATHS="${HOST_MEDIA_PATHS:-}"
  API_CONTAINER_MEDIA_PATHS="${API_CONTAINER_MEDIA_PATHS:-/app/imports:/app/exports}"
  SERVER_CONFIG_PATHS="${SERVER_CONFIG_PATHS:-$COMPOSE_ENV_FILE:$COMPOSE_FILE:$BACKUP_ENV_FILE:/etc/caddy/Caddyfile:/etc/systemd/system/kreative-norge-backup.service:/etc/systemd/system/kreative-norge-backup.timer:/etc/systemd/system/kreative-norge-backup-verify.service:/etc/systemd/system/kreative-norge-backup-verify.timer}"
  BORG_CHECK_MAX_DURATION="${BORG_CHECK_MAX_DURATION:-300}"
  RESTORE_POSTGRES_IMAGE="${RESTORE_POSTGRES_IMAGE:-postgres:16}"
  EXPECTED_DATABASE_TABLES="${EXPECTED_DATABASE_TABLES:-django_migrations,crm_organization,crm_person}"
  ARCHIVE_PREFIX="${ARCHIVE_PREFIX:-kreative-norge}"
  case "$ARCHIVE_PREFIX" in
    *[!A-Za-z0-9._-]*|'') backup_die "ARCHIVE_PREFIX contains unsafe characters" ;;
  esac
  case "$BACKUP_ENVIRONMENT" in
    *[!A-Za-z0-9._-]*|'') backup_die "BACKUP_ENVIRONMENT contains unsafe characters" ;;
  esac
  local compose_service
  for compose_service in "$DATABASE_SERVICE" "$API_SERVICE"; do
    case "$compose_service" in
      *[!A-Za-z0-9_.-]*|'') backup_die "compose service name contains unsafe characters" ;;
    esac
  done
  local numeric_value path_value
  for numeric_value in "$MIN_FREE_BYTES" "$BORG_CHECK_MAX_DURATION" "$RETENTION_DAILY" "$RETENTION_WEEKLY" "$RETENTION_MONTHLY"; do
    printf '%s' "$numeric_value" | grep -Eq '^[0-9]+$' || backup_die "numeric backup configuration is invalid"
  done
  if [ "$RETENTION_DAILY" -le 0 ] || [ "$RETENTION_WEEKLY" -le 0 ] || [ "$RETENTION_MONTHLY" -le 0 ]; then
    backup_die "retention values must be positive"
  fi
  while IFS= read -r path_value; do
    backup_require_absolute_path configured_path "$path_value"
    backup_require_safe_shell_path configured_path "$path_value"
  done < <({ backup_split_paths "$HOST_MEDIA_PATHS"; backup_split_paths "$API_CONTAINER_MEDIA_PATHS"; backup_split_paths "$SERVER_CONFIG_PATHS"; })
}

backup_configure_borg() {
  backup_validate_root_file "$BORG_PASSPHRASE_FILE" "Borg recovery-secret file"
  backup_validate_root_file "$BORG_SSH_KEY" "dedicated Borg SSH private key"
  backup_validate_root_file "$BORG_KNOWN_HOSTS" "dedicated Borg known_hosts file"
  export BORG_PASSCOMMAND="cat $BORG_PASSPHRASE_FILE"
  export BORG_RSH="ssh -i $BORG_SSH_KEY -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$BORG_KNOWN_HOSTS -o ConnectTimeout=15"
  export BORG_CACHE_DIR="${BORG_CACHE_DIR:-$WORK_ROOT/cache}"
  export BORG_CONFIG_DIR="${BORG_CONFIG_DIR:-$WORK_ROOT/config}"
  export BORG_SECURITY_DIR="${BORG_SECURITY_DIR:-$WORK_ROOT/security}"
  mkdir -p "$BORG_CACHE_DIR" "$BORG_CONFIG_DIR" "$BORG_SECURITY_DIR"
  chmod 700 "$BORG_CACHE_DIR" "$BORG_CONFIG_DIR" "$BORG_SECURITY_DIR"
}

backup_run_low_priority() {
  if [ "$BACKUP_TEST_MODE" = "1" ]; then
    "$@"
    return
  fi
  if command -v ionice >/dev/null 2>&1 && command -v nice >/dev/null 2>&1; then
    ionice -c2 -n7 nice -n 10 "$@"
  elif command -v nice >/dev/null 2>&1; then
    nice -n 10 "$@"
  else
    "$@"
  fi
}

backup_latest_archive() {
  backup_borg list --json --glob-archives "${ARCHIVE_PREFIX}-${BACKUP_ENVIRONMENT}-*" "$BORG_REPOSITORY" | \
    "$PYTHON_BIN" "$BACKUP_MODULE_DIR/status.py" latest-archive
}

backup_validate_archive_member() {
  case "$1" in
    ''|/*|../*|*/../*|*/..) backup_die "archive contains an unsafe member path" ;;
    *) ;;
  esac
}

backup_borg() {
  local subcommand="$1"
  shift
  backup_run_low_priority "$BORG_BIN" "$subcommand" --remote-path "$BORG_REMOTE_PATH" "$@"
}

backup_borg_key_export() {
  backup_run_low_priority "$BORG_BIN" key export --remote-path "$BORG_REMOTE_PATH" "$@"
}

backup_select_compose() {
  if docker compose version >/dev/null 2>&1; then
    BACKUP_COMPOSE=(docker compose -f "$COMPOSE_FILE" --env-file "$COMPOSE_ENV_FILE")
  elif command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1; then
    BACKUP_COMPOSE=(docker-compose -f "$COMPOSE_FILE" --env-file "$COMPOSE_ENV_FILE")
  else
    backup_die "neither docker compose nor docker-compose is usable"
  fi
}

backup_compose_exec() {
  "${BACKUP_COMPOSE[@]}" exec -T "$@"
}

backup_repository_id() {
  "$BORG_BIN" info --remote-path "$BORG_REMOTE_PATH" --json "$BORG_REPOSITORY" | \
    "$PYTHON_BIN" "$BACKUP_MODULE_DIR/status.py" repository-id
}

backup_verify_repository_identity() {
  local actual expected
  expected="$(printf '%s' "$BORG_REPOSITORY_ID" | tr 'A-F' 'a-f')"
  actual="$(backup_repository_id 2>/dev/null)" || backup_die "Borg repository is unavailable or authentication failed"
  [ "$actual" = "$expected" ] || backup_die "Borg repository identity does not match configuration"
}

backup_repository_preflight() {
  backup_require_root
  local command
  for command in awk chmod grep mkdir ssh-keygen stat tr "$BORG_BIN" "$PYTHON_BIN"; do
    backup_require_command "$command"
  done
  mkdir -p "$WORK_ROOT"
  chmod 700 "$WORK_ROOT"
  backup_configure_borg
  local borg_version
  borg_version="$($BORG_BIN --version | awk '{print $2}')"
  case "$borg_version" in
    "$BORG_EXPECTED_MAJOR_MINOR".*) ;;
    *) backup_die "local Borg version does not match pinned 1.2.x contract" ;;
  esac
  ssh-keygen -F "[$STORAGE_BOX_HOST]:23" -f "$BORG_KNOWN_HOSTS" >/dev/null 2>&1 || \
    backup_die "Storage Box host is absent from the dedicated known_hosts file"
  backup_verify_repository_identity
}

backup_preflight() {
  backup_require_root
  local command
  for command in awk chmod df docker find git grep head hostname mkdir mktemp sed sha256sum ssh-keygen stat tar tr wc flock "$BORG_BIN" "$PYTHON_BIN"; do
    backup_require_command "$command"
  done
  [ -d "$APP_ROOT/.git" ] || backup_die "APP_ROOT is not a Git working tree"
  [ -f "$COMPOSE_FILE" ] || backup_die "compose file is missing"
  backup_validate_root_file "$COMPOSE_ENV_FILE" "compose environment file"
  backup_repository_preflight
  backup_select_compose
  "${BACKUP_COMPOSE[@]}" ps -q "$DATABASE_SERVICE" | grep -q . || backup_die "database service is not running"
}

backup_status() {
  "$PYTHON_BIN" "$BACKUP_MODULE_DIR/status.py" update --path "$STATUS_FILE" "$@"
}

backup_acquire_lock() {
  mkdir -p "$(dirname "$LOCK_FILE")"
  exec 9>"$LOCK_FILE"
  flock -n 9 || backup_die "another backup or restore job is already running"
}

backup_split_paths() {
  printf '%s' "$1" | tr ':' '\n' | sed '/^$/d'
}

backup_sha256_value() {
  sha256sum "$1" | awk '{print $1}'
}

backup_safe_archive_name() {
  printf '%s' "$1" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$'
}
