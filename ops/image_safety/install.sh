#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "$SOURCE_DIR/../.." && pwd)"
INSTALL_DIR="${IMAGE_SAFETY_INSTALL_DIR:-/usr/local/lib/kreative-norge-image-safety}"
CONFIG_DIR="${IMAGE_SAFETY_CONFIG_DIR:-/etc/kreative-norge-image-safety}"
STATE_DIR="${IMAGE_SAFETY_STATE_DIR:-/var/lib/kreative-norge-image-safety}"
ENV_FILE="${IMAGE_SAFETY_ENV_FILE:-$CONFIG_DIR/image-safety.env}"
TEST_MODE="${IMAGE_SAFETY_TEST_MODE:-0}"

die() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 1
}

require_root() {
  if [ "$TEST_MODE" != "1" ] && [ "$(id -u)" != "0" ]; then
    die "installer must run as root"
  fi
}

require_safe_path() {
  local label="$1"
  local value="$2"
  case "$value" in
    /|*/|*//*|*/../*|*/..|*/./*|*/.) die "$label is not a normalized non-root path" ;;
    /*) ;;
    *) die "$label must be absolute" ;;
  esac
  printf '%s' "$value" | grep -Eq '^/[A-Za-z0-9_./-]+$' || \
    die "$label contains unsafe characters"
}

prepare() {
  require_root
  require_safe_path "install directory" "$INSTALL_DIR"
  require_safe_path "configuration directory" "$CONFIG_DIR"
  require_safe_path "state directory" "$STATE_DIR"
  require_safe_path "environment file" "$ENV_FILE"
  case "$STATE_DIR" in
    */kreative-norge-image-safety) ;;
    *) die "state directory must be dedicated to kreative-norge-image-safety" ;;
  esac
  case "$ENV_FILE" in
    "$CONFIG_DIR"/*) ;;
    *) die "environment file must be inside the dedicated configuration directory" ;;
  esac

  install -d -m 0755 -o root -g root "$INSTALL_DIR"
  install -d -m 0700 -o root -g root "$CONFIG_DIR" "$STATE_DIR" "$STATE_DIR/borg"
  install -d -m 0755 -o root -g root "$INSTALL_DIR/image_safety"
  install -m 0644 -o root -g root "$REPOSITORY_ROOT/image_safety/"*.py "$INSTALL_DIR/image_safety/"
  install -m 0755 -o root -g root \
    "$SOURCE_DIR/image-safety.sh" "$SOURCE_DIR/install.sh" "$INSTALL_DIR/"
  install -m 0644 -o root -g root "$SOURCE_DIR/run.py" "$INSTALL_DIR/"
  if [ ! -e "$ENV_FILE" ]; then
    install -m 0600 -o root -g root "$SOURCE_DIR/image-safety.env.example" "$ENV_FILE"
  fi
  if [ "$TEST_MODE" != "1" ]; then
    install -m 0644 -o root -g root "$SOURCE_DIR/systemd/"*.service \
      "$SOURCE_DIR/systemd/"*.timer /etc/systemd/system/
    systemctl daemon-reload
  fi
  printf '%s\n' "PREPARED only: no repository, credential, ledger, timer, or public runtime was activated."
}

generate_key() {
  require_root
  local key_path="$CONFIG_DIR/storage-box-writer-ed25519"
  [ ! -e "$key_path" ] || die "refusing to replace the existing writer key"
  install -d -m 0700 -o root -g root "$CONFIG_DIR"
  ssh-keygen -q -t ed25519 -N '' -C kreative-norge-image-safety-writer -f "$key_path"
  chmod 600 "$key_path"
  chmod 644 "$key_path.pub"
  printf '%s\n' "Generated a host-only writer key. Install its public half only on the dedicated safety subaccount."
  ssh-keygen -lf "$key_path.pub"
}

case "${1:-}" in
  prepare) prepare ;;
  generate-key) generate_key ;;
  *)
    printf 'Usage: %s {prepare|generate-key}\n' "$0" >&2
    exit 2
    ;;
esac
