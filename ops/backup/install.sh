#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/usr/local/lib/kreative-norge-backup"
CONFIG_DIR="/etc/kreative-norge-backup"
STATE_DIR="/var/lib/kreative-norge-backup"
ENV_FILE="$CONFIG_DIR/backup.env"

die() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 1
}

require_root() {
  [ "$(id -u)" = "0" ] || die "installer commands must run as root"
}

require_root_private_file() {
  [ -f "$1" ] || die "$2 is missing"
  [ "$(stat -c '%u:%a' "$1")" = "0:600" ] || die "$2 must be root-owned with mode 0600"
}

require_safe_absolute_path() {
  printf '%s' "$1" | grep -Eq '^/[A-Za-z0-9_./-]+$' || die "$2 contains unsafe path characters"
  case "$1" in */../*|*/..) die "$2 contains a parent-directory component" ;; esac
}

prepare() {
  require_root
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
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  [ -n "${BORG_SSH_KEY:-}" ] || die "BORG_SSH_KEY is not configured"
  require_safe_absolute_path "$BORG_SSH_KEY" "BORG_SSH_KEY"
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
  # shellcheck disable=SC1090
  set -a
  source "$ENV_FILE"
  set +a
  for name in BORG_REPOSITORY BORG_PASSPHRASE_FILE BORG_SSH_KEY BORG_KNOWN_HOSTS STORAGE_BOX_HOST; do
    [ -n "${!name:-}" ] || die "missing required setting: $name"
  done
  [ "${BORG_REMOTE_PATH:-}" = "borg-1.2" ] || die "BORG_REMOTE_PATH must be borg-1.2"
  case "$BORG_REPOSITORY" in ssh://*) ;; *) die "BORG_REPOSITORY must use ssh://" ;; esac
  case "$BORG_REPOSITORY" in *[[:space:]]*) die "BORG_REPOSITORY contains whitespace" ;; esac
  authority="${BORG_REPOSITORY#ssh://}"
  authority="${authority%%/*}"
  case "$authority" in *@*:23) ;; *) die "BORG_REPOSITORY must use a dedicated SSH user and port 23" ;; esac
  repository_user="${authority%@*}"
  repository_host="${authority##*@}"
  repository_host="${repository_host%%:*}"
  printf '%s' "$repository_user" | grep -Eq '^[A-Za-z0-9._-]+$' || die "BORG_REPOSITORY user is invalid"
  [ "$repository_host" = "$STORAGE_BOX_HOST" ] || die "BORG_REPOSITORY host does not match STORAGE_BOX_HOST"
  repository_path="${BORG_REPOSITORY#ssh://}"
  repository_path="/${repository_path#*/}"
  printf '%s' "$repository_path" | grep -Eq '^/\./[A-Za-z0-9_./-]+$' || die "BORG_REPOSITORY path must be safe and relative"
  case "$repository_path" in */../*|*/..) die "BORG_REPOSITORY path contains a parent-directory component" ;; esac
  require_safe_absolute_path "$BORG_PASSPHRASE_FILE" "BORG_PASSPHRASE_FILE"
  require_safe_absolute_path "$BORG_SSH_KEY" "BORG_SSH_KEY"
  require_safe_absolute_path "$BORG_KNOWN_HOSTS" "BORG_KNOWN_HOSTS"
  require_root_private_file "$BORG_PASSPHRASE_FILE" "recovery-secret file"
  require_root_private_file "$BORG_SSH_KEY" "dedicated SSH key"
  require_root_private_file "$BORG_KNOWN_HOSTS" "dedicated known_hosts file"
  ssh-keygen -F "[$STORAGE_BOX_HOST]:23" -f "$BORG_KNOWN_HOSTS" >/dev/null || die "Storage Box host and port are not pinned"
  borg_version="$(borg --version | awk '{print $2}')"
  case "$borg_version" in 1.2.*) ;; *) die "local Borg must be 1.2.x" ;; esac
  export BORG_PASSCOMMAND="cat $BORG_PASSPHRASE_FILE"
  export BORG_RSH="ssh -i $BORG_SSH_KEY -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=$BORG_KNOWN_HOSTS -o ConnectTimeout=15"
  borg init --remote-path "$BORG_REMOTE_PATH" --encryption=repokey-blake2 "$BORG_REPOSITORY"
  repository_id="$(borg info --remote-path "$BORG_REMOTE_PATH" --json "$BORG_REPOSITORY" | python3 "$INSTALL_DIR/status.py" repository-id)"
  printf 'Repository initialized. Set BORG_REPOSITORY_ID=%s in %s.\n' "$repository_id" "$ENV_FILE"
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
  preflight) run_preflight ;;
  activate) activate ;;
  *)
    printf 'Usage: %s {prepare|generate-key|init-repository|preflight|activate}\n' "$0" >&2
    exit 2
    ;;
esac
