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
BACKUP_MINIMUM_BORG_VERSION="1.2.8"

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
  if [ ! -f "$path" ]; then
    backup_die "$label is missing"
    return 1
  fi
  if [ "$BACKUP_TEST_MODE" = "1" ]; then
    return 0
  fi
  local uid mode mode_value
  uid="$(stat -c '%u' "$path")"
  mode="$(stat -c '%a' "$path")"
  if [ "$uid" != "0" ]; then
    backup_die "$label must be owned by root"
    return 1
  fi
  mode_value=$((8#$mode))
  if (( (mode_value & 0077) != 0 )); then
    backup_die "$label must not be accessible by group or other users"
    return 1
  fi
}

backup_require_absolute_path() {
  case "$2" in
    /*) ;;
    *) backup_die "$1 must be an absolute path" ;;
  esac
}

backup_require_safe_shell_path() {
  printf '%s' "$2" | grep -Eq '^/[A-Za-z0-9_./-]*$' || {
    backup_die "$1 contains unsafe shell characters"
    return 1
  }
  case "$2" in
    */../*|*/..) backup_die "$1 contains a parent-directory component" ;;
  esac
}

backup_require_normalized_path() {
  local label="$1"
  local path="$2"
  backup_require_absolute_path "$label" "$path" || return 1
  backup_require_safe_shell_path "$label" "$path" || return 1
  case "$path" in
    /|*/|*//*|*/./*|*/.)
      backup_die "$label is not a normalized non-root path"
      return 1
      ;;
  esac
}

backup_require_no_symlink_components() {
  local label="$1"
  local path="$2"
  local current=""
  local component
  local -a components=()
  IFS='/' read -r -a components <<< "${path#/}"
  for component in "${components[@]}"; do
    current="$current/$component"
    if [ -L "$current" ]; then
      backup_die "$label must not contain symlink components"
      return 1
    fi
  done
}

backup_require_host_path() {
  backup_require_normalized_path "$1" "$2" || return 1
  backup_require_no_symlink_components "$1" "$2" || return 1
}

backup_path_is_equal_or_within() {
  local candidate="$1"
  local root="${2%/}"
  case "$candidate" in
    "$root"|"$root"/*) return 0 ;;
    *) return 1 ;;
  esac
}

backup_path_is_strictly_within() {
  [ "$1" != "$2" ] && backup_path_is_equal_or_within "$1" "$2"
}

backup_paths_overlap() {
  backup_path_is_equal_or_within "$1" "$2" || backup_path_is_equal_or_within "$2" "$1"
}

backup_require_no_path_overlap() {
  local label="$1"
  local first="$2"
  local second="$3"
  if backup_paths_overlap "$first" "$second"; then
    backup_die "$label overlaps a protected path"
    return 1
  fi
}

backup_validate_borg_directory_contract() {
  local variable expected configured
  for variable in BORG_CACHE_DIR BORG_CONFIG_DIR BORG_SECURITY_DIR; do
    case "$variable" in
      BORG_CACHE_DIR) expected="$WORK_ROOT/cache" ;;
      BORG_CONFIG_DIR) expected="$WORK_ROOT/config" ;;
      BORG_SECURITY_DIR) expected="$WORK_ROOT/security" ;;
    esac
    configured="${!variable:-}"
    if [ -n "$configured" ] && [ "$configured" != "$expected" ]; then
      backup_die "$variable must use its dedicated backup work path"
      return 1
    fi
    printf -v "$variable" '%s' "$expected"
  done
  export BORG_CACHE_DIR BORG_CONFIG_DIR BORG_SECURITY_DIR
}

backup_validate_semantic_paths() {
  local path_value protected_path

  backup_require_host_path BACKUP_ENV_FILE "$BACKUP_ENV_FILE" || return 1
  backup_require_host_path APP_ROOT "$APP_ROOT" || return 1
  backup_require_host_path COMPOSE_FILE "$COMPOSE_FILE" || return 1
  backup_require_host_path COMPOSE_ENV_FILE "$COMPOSE_ENV_FILE" || return 1
  backup_require_host_path BACKUP_STATE_ROOT "$BACKUP_STATE_ROOT" || return 1
  backup_require_host_path WORK_ROOT "$WORK_ROOT" || return 1
  backup_require_host_path STATUS_FILE "$STATUS_FILE" || return 1
  backup_require_host_path RESTORE_GATE_FILE "$RESTORE_GATE_FILE" || return 1
  backup_require_host_path LOCK_FILE "$LOCK_FILE" || return 1
  backup_require_host_path BORG_PASSPHRASE_FILE "$BORG_PASSPHRASE_FILE" || return 1
  backup_require_host_path BORG_SSH_KEY "$BORG_SSH_KEY" || return 1
  backup_require_host_path BORG_KNOWN_HOSTS "$BORG_KNOWN_HOSTS" || return 1
  backup_require_host_path HOST_MEDIA_ROOT "$HOST_MEDIA_ROOT" || return 1

  case "$BACKUP_STATE_ROOT" in
    */kreative-norge-backup) ;;
    *)
      backup_die "BACKUP_STATE_ROOT must be a dedicated kreative-norge-backup path"
      return 1
      ;;
  esac
  if [ "$WORK_ROOT" != "$BACKUP_STATE_ROOT/work" ]; then
    backup_die "WORK_ROOT must be the dedicated backup state work path"
    return 1
  fi
  if [ "$STATUS_FILE" != "$BACKUP_STATE_ROOT/status.json" ]; then
    backup_die "STATUS_FILE must be the dedicated backup state status path"
    return 1
  fi
  if [ "$RESTORE_GATE_FILE" != "$BACKUP_STATE_ROOT/restore-smoke.ok" ]; then
    backup_die "RESTORE_GATE_FILE must be the dedicated backup state restore gate path"
    return 1
  fi
  case "$LOCK_FILE" in
    */kreative-norge-backup.lock) ;;
    *)
      backup_die "LOCK_FILE must use the dedicated backup lock filename"
      return 1
      ;;
  esac
  case "$HOST_MEDIA_ROOT" in
    */kreative-norge/media) ;;
    *)
      backup_die "HOST_MEDIA_ROOT must be the dedicated Kreative Norge media path"
      return 1
      ;;
  esac

  if ! backup_path_is_strictly_within "$COMPOSE_FILE" "$APP_ROOT"; then
    backup_die "COMPOSE_FILE must be inside APP_ROOT"
    return 1
  fi
  if ! backup_path_is_strictly_within "$COMPOSE_ENV_FILE" "$APP_ROOT"; then
    backup_die "COMPOSE_ENV_FILE must be inside APP_ROOT"
    return 1
  fi
  backup_require_no_path_overlap "APP_ROOT" "$APP_ROOT" "$BACKUP_STATE_ROOT" || return 1
  backup_require_no_path_overlap "APP_ROOT" "$APP_ROOT" "$HOST_MEDIA_ROOT" || return 1
  backup_validate_borg_directory_contract || return 1

  while IFS= read -r path_value; do
    backup_require_normalized_path HOST_MEDIA_PATHS "$path_value" || return 1
    if ! backup_path_is_strictly_within "$path_value" "$HOST_MEDIA_ROOT"; then
      backup_die "HOST_MEDIA_PATHS entries must be below HOST_MEDIA_ROOT"
      return 1
    fi
    backup_require_no_symlink_components HOST_MEDIA_PATHS "$path_value" || return 1
    for protected_path in \
      "$APP_ROOT" "$BACKUP_STATE_ROOT" "$WORK_ROOT" "$BORG_PASSPHRASE_FILE" \
      "$BORG_SSH_KEY" "$BORG_KNOWN_HOSTS" "$BACKUP_ENV_FILE"; do
      backup_require_no_path_overlap "HOST_MEDIA_PATHS entry" "$path_value" "$protected_path" || return 1
    done
    while IFS= read -r protected_path; do
      backup_require_no_path_overlap "HOST_MEDIA_PATHS entry" "$path_value" "$protected_path" || return 1
    done < <(backup_split_paths "$SERVER_CONFIG_PATHS")
  done < <(backup_split_paths "$HOST_MEDIA_PATHS")

  while IFS= read -r path_value; do
    backup_require_normalized_path API_CONTAINER_MEDIA_PATHS "$path_value" || return 1
    if ! backup_path_is_strictly_within "$path_value" "/app"; then
      backup_die "API_CONTAINER_MEDIA_PATHS entries must be explicit subdirectories below /app"
      return 1
    fi
  done < <(backup_split_paths "$API_CONTAINER_MEDIA_PATHS")

  while IFS= read -r path_value; do
    backup_require_host_path SERVER_CONFIG_PATHS "$path_value" || return 1
  done < <(backup_split_paths "$SERVER_CONFIG_PATHS")
}

backup_validate_borg_version() {
  local output major minor patch
  if ! output="$("$BORG_BIN" --version 2>/dev/null)"; then
    backup_die "local Borg version could not be determined"
    return 1
  fi
  if [[ "$output" =~ ^borg[[:space:]]+([0-9]|[1-9][0-9]*)\.([0-9]|[1-9][0-9]*)\.([0-9]|[1-9][0-9]*)$ ]]; then
    major="${BASH_REMATCH[1]}"
    minor="${BASH_REMATCH[2]}"
    patch="${BASH_REMATCH[3]}"
  else
    backup_die "local Borg version output is malformed or is a prerelease"
    return 1
  fi
  if [ "$major" != "1" ] || [ "$minor" != "2" ] || {
    [ "${#patch}" -eq 1 ] && [ "$patch" -lt 8 ]
  }; then
    backup_die "local Borg must be at least $BACKUP_MINIMUM_BORG_VERSION and lower than 1.3.0"
    return 1
  fi
}

backup_load_config() {
  local load_mode="${1:-operational}"
  case "$load_mode" in
    operational|repository-init) ;;
    *)
      backup_die "unsupported backup configuration load mode"
      return 1
      ;;
  esac
  backup_validate_root_file "$BACKUP_ENV_FILE" "backup environment file" || return 1
  set -a
  # shellcheck disable=SC1090
  source "$BACKUP_ENV_FILE"
  set +a

  local required
  for required in \
    BACKUP_ENVIRONMENT APP_ROOT COMPOSE_FILE COMPOSE_ENV_FILE DATABASE_SERVICE API_SERVICE \
    BACKUP_STATE_ROOT WORK_ROOT STATUS_FILE RESTORE_GATE_FILE LOCK_FILE HOST_MEDIA_ROOT \
    BORG_REPOSITORY BORG_REMOTE_PATH \
    BORG_EXPECTED_MAJOR_MINOR BORG_PASSPHRASE_FILE BORG_SSH_KEY BORG_KNOWN_HOSTS \
    STORAGE_BOX_HOST RETENTION_DAILY RETENTION_WEEKLY RETENTION_MONTHLY; do
    if [ -z "${!required:-}" ]; then
      backup_die "required configuration is missing: $required"
      return 1
    fi
  done
  if [ "$load_mode" = "operational" ]; then
    if [ -z "${BORG_REPOSITORY_ID:-}" ]; then
      backup_die "required configuration is missing: BORG_REPOSITORY_ID"
      return 1
    fi
  fi

  if ! printf '%s' "$STORAGE_BOX_HOST" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9.-]*$'; then
    backup_die "STORAGE_BOX_HOST is invalid"
    return 1
  fi

  if [ "$BORG_EXPECTED_MAJOR_MINOR" != "1.2" ]; then
    backup_die "this module is pinned to Borg 1.2.x"
    return 1
  fi
  if [ "$BORG_REMOTE_PATH" != "borg-1.2" ]; then
    backup_die "BORG_REMOTE_PATH must be borg-1.2"
    return 1
  fi
  if [ "$load_mode" = "operational" ]; then
    if ! printf '%s' "$BORG_REPOSITORY_ID" | grep -Eq '^[0-9a-fA-F]{64}$'; then
      backup_die "BORG_REPOSITORY_ID is missing or invalid"
      return 1
    fi
  fi
  case "$BORG_REPOSITORY" in
    ssh://*) ;;
    *)
      backup_die "BORG_REPOSITORY must use an ssh:// URL"
      return 1
      ;;
  esac
  case "$BORG_REPOSITORY" in
    *[[:space:]]*)
      backup_die "BORG_REPOSITORY contains whitespace"
      return 1
      ;;
  esac
  local authority userinfo repository_host repository_path
  authority="${BORG_REPOSITORY#ssh://}"
  authority="${authority%%/*}"
  case "$authority" in
    *@*:23) ;;
    *)
      backup_die "BORG_REPOSITORY must use a dedicated SSH user and Storage Box port 23"
      return 1
      ;;
  esac
  userinfo="${authority%@*}"
  if ! printf '%s' "$userinfo" | grep -Eq '^[A-Za-z0-9._-]+$'; then
    backup_die "BORG_REPOSITORY user is invalid"
    return 1
  fi
  case "$userinfo" in
    *:*)
      backup_die "BORG_REPOSITORY must not contain a password"
      return 1
      ;;
  esac
  repository_host="${authority##*@}"
  repository_host="${repository_host%%:*}"
  if [ "$repository_host" != "$STORAGE_BOX_HOST" ]; then
    backup_die "BORG_REPOSITORY host does not match STORAGE_BOX_HOST"
    return 1
  fi
  repository_path="${BORG_REPOSITORY#ssh://}"
  repository_path="/${repository_path#*/}"
  if ! printf '%s' "$repository_path" | grep -Eq '^/\./[A-Za-z0-9_./-]+$'; then
    backup_die "BORG_REPOSITORY must use a safe relative Storage Box path"
    return 1
  fi
  case "$repository_path" in
    */../*|*/..)
      backup_die "BORG_REPOSITORY contains a parent-directory component"
      return 1
      ;;
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
    *[!A-Za-z0-9._-]*|'')
      backup_die "ARCHIVE_PREFIX contains unsafe characters"
      return 1
      ;;
  esac
  case "$BACKUP_ENVIRONMENT" in
    *[!A-Za-z0-9._-]*|'')
      backup_die "BACKUP_ENVIRONMENT contains unsafe characters"
      return 1
      ;;
  esac
  local compose_service
  for compose_service in "$DATABASE_SERVICE" "$API_SERVICE"; do
    case "$compose_service" in
      *[!A-Za-z0-9_.-]*|'')
        backup_die "compose service name contains unsafe characters"
        return 1
        ;;
    esac
  done
  local numeric_value
  for numeric_value in "$MIN_FREE_BYTES" "$BORG_CHECK_MAX_DURATION" "$RETENTION_DAILY" "$RETENTION_WEEKLY" "$RETENTION_MONTHLY"; do
    if ! printf '%s' "$numeric_value" | grep -Eq '^[0-9]+$'; then
      backup_die "numeric backup configuration is invalid"
      return 1
    fi
  done
  if [ "$RETENTION_DAILY" -le 0 ] || [ "$RETENTION_WEEKLY" -le 0 ] || [ "$RETENTION_MONTHLY" -le 0 ]; then
    backup_die "retention values must be positive"
    return 1
  fi
  backup_validate_semantic_paths || return 1
}

backup_configure_borg() {
  backup_validate_root_file "$BORG_PASSPHRASE_FILE" "Borg recovery-secret file" || return 1
  backup_validate_root_file "$BORG_SSH_KEY" "dedicated Borg SSH private key" || return 1
  backup_validate_root_file "$BORG_KNOWN_HOSTS" "dedicated Borg known_hosts file" || return 1
  export BORG_PASSCOMMAND="cat $BORG_PASSPHRASE_FILE"
  export BORG_RSH="ssh -i $BORG_SSH_KEY -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$BORG_KNOWN_HOSTS -o ConnectTimeout=15"
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
  if ! actual="$(backup_repository_id 2>/dev/null)"; then
    backup_die "Borg repository is unavailable or authentication failed"
    return 1
  fi
  if [ "$actual" != "$expected" ]; then
    backup_die "Borg repository identity does not match configuration"
    return 1
  fi
}

backup_repository_preflight() {
  backup_require_root || return 1
  backup_require_command "$BORG_BIN" || return 1
  backup_validate_borg_version || return 1
  local command
  for command in awk chmod grep mkdir ssh-keygen stat tr "$PYTHON_BIN"; do
    backup_require_command "$command" || return 1
  done
  mkdir -p "$WORK_ROOT"
  chmod 700 "$WORK_ROOT"
  backup_configure_borg || return 1
  if ! ssh-keygen -F "[$STORAGE_BOX_HOST]:23" -f "$BORG_KNOWN_HOSTS" >/dev/null 2>&1; then
    backup_die "Storage Box host is absent from the dedicated known_hosts file"
    return 1
  fi
  backup_verify_repository_identity || return 1
}

backup_preflight() {
  backup_require_root || return 1
  local command
  for command in awk chmod df docker find git grep head hostname mkdir mktemp sed sha256sum ssh-keygen stat tar tr wc flock "$BORG_BIN" "$PYTHON_BIN"; do
    backup_require_command "$command" || return 1
  done
  if [ ! -d "$APP_ROOT/.git" ]; then
    backup_die "APP_ROOT is not a Git working tree"
    return 1
  fi
  if [ ! -f "$COMPOSE_FILE" ]; then
    backup_die "compose file is missing"
    return 1
  fi
  backup_validate_root_file "$COMPOSE_ENV_FILE" "compose environment file" || return 1
  backup_repository_preflight || return 1
  backup_select_compose || return 1
  if ! "${BACKUP_COMPOSE[@]}" ps -q "$DATABASE_SERVICE" | grep -q .; then
    backup_die "database service is not running"
    return 1
  fi
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
  printf '%s\n' "$1" | tr ':' '\n' | sed '/^$/d'
}

backup_sha256_value() {
  sha256sum "$1" | awk '{print $1}'
}

backup_safe_archive_name() {
  printf '%s' "$1" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$'
}
