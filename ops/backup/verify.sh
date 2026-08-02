#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

BACKUP_MODULE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=ops/backup/lib.sh
source "$BACKUP_MODULE_DIR/lib.sh"

status_available=0
cleanup() {
  # Capture the incoming trap status before any command changes it.
  # shellcheck disable=SC2155
  local rc="$?"
  if [ "$rc" -ne 0 ] && [ "$status_available" -eq 1 ]; then
    backup_status --event error --timestamp "$(backup_now)" --stage weekly_verify || true
  fi
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

backup_load_config
backup_acquire_lock
status_available=1
backup_preflight

backup_log "running weekly full repository and archive-data verification"
backup_borg check --verify-data "$BORG_REPOSITORY"
latest_archive="$(backup_latest_archive)"
backup_safe_archive_name "$latest_archive" || backup_die "no safe backup archive is available"
backup_borg info --json "$BORG_REPOSITORY::$latest_archive" >/dev/null
backup_status --event repository-verified --timestamp "$(backup_now)"
status_available=0
backup_log "repository verification completed"
