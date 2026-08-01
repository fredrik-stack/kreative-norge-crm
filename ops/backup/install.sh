#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${BACKUP_INSTALL_DIR:-/usr/local/lib/kreative-norge-backup}"
CONFIG_DIR="${BACKUP_CONFIG_DIR:-/etc/kreative-norge-backup}"
STATE_DIR="${BACKUP_STATE_DIR:-/var/lib/kreative-norge-backup}"
ENV_FILE="${BACKUP_ENV_FILE:-$CONFIG_DIR/backup.env}"
BACKUP_ENV_FILE="$ENV_FILE"
# shellcheck source=ops/backup/lib.sh
source "$SOURCE_DIR/lib.sh"

recovery_export_dir=""
recovery_destination=""
recovery_destination_created=0

cleanup_install() {
  # Capture the incoming trap status before any command changes it.
  # shellcheck disable=SC2155
  local rc="$?"
  trap - EXIT
  if [ "$rc" -ne 0 ] && [ "$recovery_destination_created" -eq 1 ] && [ -n "$recovery_destination" ]; then
    rm -f -- "$recovery_destination"
  fi
  if [ -n "$recovery_export_dir" ] && [ -d "$recovery_export_dir" ]; then
    rm -rf -- "$recovery_export_dir"
  fi
  exit "$rc"
}
trap cleanup_install EXIT

die() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 1
}

require_root() {
  if [ "$BACKUP_TEST_MODE" != "1" ]; then
    [ "$(id -u)" = "0" ] || die "installer commands must run as root"
  fi
}

require_root_private_file() {
  [ -f "$1" ] || die "$2 is missing"
  if [ "$BACKUP_TEST_MODE" != "1" ]; then
    [ "$(stat -c '%u:%a' "$1")" = "0:600" ] || die "$2 must be root-owned with mode 0600"
  fi
}

require_installer_layout() {
  backup_require_host_path "installer directory" "$INSTALL_DIR"
  backup_require_host_path "configuration directory" "$CONFIG_DIR"
  backup_require_host_path "state directory" "$STATE_DIR"
  backup_require_host_path "backup.env path" "$ENV_FILE"
  case "$STATE_DIR" in
    */kreative-norge-backup) ;;
    *) die "state directory must be a dedicated kreative-norge-backup path" ;;
  esac
  backup_path_is_strictly_within "$ENV_FILE" "$CONFIG_DIR" || \
    die "backup.env must be inside the configuration directory"
}

require_recovery_destination() {
  recovery_destination="$1"
  backup_require_host_path "recovery key destination" "$recovery_destination" || exit 1
  [ ! -e "$recovery_destination" ] && [ ! -L "$recovery_destination" ] || \
    die "refusing to overwrite an existing recovery key export"

  local destination_parent
  destination_parent="$(dirname "$recovery_destination")"
  [ -d "$destination_parent" ] || die "recovery key destination parent is missing"
  "$PYTHON_BIN" "$SOURCE_DIR/status.py" private-directory --path "$destination_parent" || \
    die "recovery key destination parent must be operator-owned and not group/world-writable"
}

reject_protected_recovery_destination() {
  if backup_path_is_equal_or_within "$recovery_destination" "$APP_ROOT"; then
    die "recovery key destination must be outside the application repository"
  fi
  if backup_path_is_equal_or_within "$recovery_destination" "$BACKUP_STATE_ROOT"; then
    die "recovery key destination must be outside backup work paths"
  fi

  local protected_path
  while IFS= read -r protected_path; do
    if backup_path_is_equal_or_within "$recovery_destination" "$protected_path"; then
      die "recovery key destination must be outside protected media paths"
    fi
  done < <(backup_split_paths "$HOST_MEDIA_PATHS")

  while IFS= read -r protected_path; do
    [ "$recovery_destination" != "$protected_path" ] || \
      die "recovery key destination must not replace protected server configuration"
  done < <(backup_split_paths "$SERVER_CONFIG_PATHS")
}

load_repository_context() {
  require_root
  require_root_private_file "$ENV_FILE" "backup.env"
  backup_load_config
  backup_repository_preflight
}

prepare() {
  require_root
  require_installer_layout
  install -d -m 0700 -o root -g root "$CONFIG_DIR" "$STATE_DIR" "$STATE_DIR/work"
  install -d -m 0755 -o root -g root "$INSTALL_DIR"
  install -m 0755 -o root -g root \
    "$SOURCE_DIR/backup.sh" "$SOURCE_DIR/verify.sh" "$SOURCE_DIR/restore-smoke.sh" \
    "$SOURCE_DIR/install.sh" "$INSTALL_DIR/"
  install -m 0644 -o root -g root "$SOURCE_DIR/lib.sh" "$SOURCE_DIR/status.py" "$INSTALL_DIR/"
  if [ ! -e "$ENV_FILE" ]; then
    install -m 0600 -o root -g root "$SOURCE_DIR/backup.env.example" "$ENV_FILE"
  fi
  install -m 0644 -o root -g root "$SOURCE_DIR/systemd/"*.service "$SOURCE_DIR/systemd/"*.timer /etc/systemd/system/
  systemctl daemon-reload
  printf '%s\n' "Prepared files only. Timers remain disabled until a backup and isolated restore both pass."
}

generate_key() {
  require_root
  require_root_private_file "$ENV_FILE" "backup.env"
  backup_load_config repository-init
  [ ! -e "$BORG_SSH_KEY" ] || die "refusing to replace an existing SSH key"
  install -d -m 0700 -o root -g root "$(dirname "$BORG_SSH_KEY")"
  ssh-keygen -q -t ed25519 -N '' -C kreative-norge-storage-box-backup -f "$BORG_SSH_KEY"
  chmod 600 "$BORG_SSH_KEY"
  chmod 644 "$BORG_SSH_KEY.pub"
  printf 'Public key to add to the restricted Storage Box subaccount:\n'
  sed -n '1p' "$BORG_SSH_KEY.pub"
  ssh-keygen -lf "$BORG_SSH_KEY.pub"
}

initialize_repository() {
  require_root
  require_root_private_file "$ENV_FILE" "backup.env"
  backup_load_config repository-init
  backup_require_command "$BORG_BIN"
  backup_require_command "$PYTHON_BIN"
  backup_require_command ssh-keygen
  backup_validate_borg_version
  backup_configure_borg
  ssh-keygen -F "[$STORAGE_BOX_HOST]:23" -f "$BORG_KNOWN_HOSTS" >/dev/null || \
    die "Storage Box host and port are not pinned"
  "$BORG_BIN" init --remote-path "$BORG_REMOTE_PATH" --encryption=repokey-blake2 "$BORG_REPOSITORY"
  repository_id="$("$BORG_BIN" info --remote-path "$BORG_REMOTE_PATH" --json "$BORG_REPOSITORY" | \
    "$PYTHON_BIN" "$INSTALL_DIR/status.py" repository-id)"
  printf 'Repository initialized. Set BORG_REPOSITORY_ID=%s in %s.\n' "$repository_id" "$ENV_FILE"
  printf 'Next mandatory recovery step: export the encrypted repository key with export-recovery-key after setting BORG_REPOSITORY_ID.\n'
}

export_recovery_key() {
  [ "$#" -eq 1 ] || die "export-recovery-key requires one absolute destination path"
  require_root
  require_root_private_file "$ENV_FILE" "backup.env"
  backup_load_config
  backup_require_command dirname
  backup_require_command "$PYTHON_BIN"
  require_recovery_destination "$1"
  reject_protected_recovery_destination
  backup_repository_preflight

  local command destination_parent exported_key repository_id export_sha256
  for command in chmod chown mktemp rm sha256sum; do
    backup_require_command "$command"
  done
  destination_parent="$(dirname "$recovery_destination")"
  recovery_export_dir="$(mktemp -d "$destination_parent/.kreative-norge-recovery.XXXXXX")"
  chmod 700 "$recovery_export_dir"
  exported_key="$recovery_export_dir/repository-key"

  if ! backup_borg_key_export "$BORG_REPOSITORY" "$exported_key" >/dev/null 2>&1; then
    die "Borg recovery key export failed"
  fi
  [ -s "$exported_key" ] || die "Borg recovery key export is empty"
  chmod 600 "$exported_key"
  if [ "$BACKUP_TEST_MODE" != "1" ]; then
    chown root:root "$exported_key"
    [ "$(stat -c '%u:%a' "$exported_key")" = "0:600" ] || \
      die "temporary recovery key export must be root-owned with mode 0600"
  fi

  [ ! -e "$recovery_destination" ] && [ ! -L "$recovery_destination" ] || \
    die "refusing to overwrite an existing recovery key export"
  "$PYTHON_BIN" "$SOURCE_DIR/status.py" link-no-clobber \
    --source "$exported_key" --destination "$recovery_destination" || \
    die "could not create recovery key export without overwriting"
  recovery_destination_created=1
  if [ "$BACKUP_TEST_MODE" != "1" ]; then
    [ "$(stat -c '%u:%a' "$recovery_destination")" = "0:600" ] || \
      die "recovery key export must be root-owned with mode 0600"
  fi

  repository_id="$(printf '%s' "$BORG_REPOSITORY_ID" | tr 'A-F' 'a-f')"
  export_sha256="$(backup_sha256_value "$recovery_destination")"
  printf 'Encrypted Borg recovery key exported successfully.\n'
  printf 'repository_id=%s\n' "$repository_id"
  printf 'destination=%s\n' "$recovery_destination"
  printf 'sha256=%s\n' "$export_sha256"
  recovery_destination_created=0
}

inspect_repository() {
  [ "$#" -eq 0 ] || die "inspect-repository does not accept arguments"
  load_repository_context

  local summary repository_id
  if ! summary="$(backup_borg list --json --glob-archives "${ARCHIVE_PREFIX}-${BACKUP_ENVIRONMENT}-*" \
    "$BORG_REPOSITORY" 2>/dev/null | "$PYTHON_BIN" "$SOURCE_DIR/status.py" repository-summary)"; then
    die "repository inspection failed"
  fi
  [ -n "$summary" ] || die "repository inspection returned no status"
  repository_id="$(printf '%s' "$BORG_REPOSITORY_ID" | tr 'A-F' 'a-f')"
  printf 'Repository is available and identity is verified.\n'
  printf 'repository_id=%s\n' "$repository_id"
  printf '%s\n' "$summary"
}

run_preflight() {
  require_root
  BACKUP_ENV_FILE="$ENV_FILE" "$INSTALL_DIR/backup.sh" --preflight
}

activate() {
  require_root
  BACKUP_ENV_FILE="$ENV_FILE" "$INSTALL_DIR/backup.sh" --preflight
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  archive="$(python3 "$INSTALL_DIR/status.py" activation-ready --path "$STATUS_FILE")"
  gate_file="${RESTORE_GATE_FILE:-$STATE_DIR/restore-smoke.ok}"
  [ -f "$gate_file" ] || die "restore gate file is missing"
  [ "$(stat -c '%u:%a' "$gate_file")" = "0:600" ] || die "restore gate must be root-owned with mode 0600"
  grep -Fx "archive=$archive" "$gate_file" >/dev/null || die "restore gate does not match the successful archive"
  systemctl enable --now kreative-norge-backup.timer kreative-norge-backup-verify.timer
  printf '%s\n' "Backup timers activated after backup and restore gates passed."
}

case "${1:-}" in
  prepare) prepare ;;
  generate-key) generate_key ;;
  init-repository) initialize_repository ;;
  export-recovery-key) shift; export_recovery_key "$@" ;;
  inspect-repository) shift; inspect_repository "$@" ;;
  preflight) run_preflight ;;
  activate) activate ;;
  *)
    printf 'Usage: %s {prepare|generate-key|init-repository|export-recovery-key <absolute-destination>|inspect-repository|preflight|activate}\n' "$0" >&2
    exit 2
    ;;
esac
