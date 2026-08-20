#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

ENV_FILE="${IMAGE_SAFETY_ENV_FILE:-/etc/kreative-norge-image-safety/image-safety.env}"
INSTALL_DIR="${IMAGE_SAFETY_INSTALL_DIR:-/usr/local/lib/kreative-norge-image-safety}"

if [ "${IMAGE_SAFETY_TEST_MODE:-0}" != "1" ] && [ "$(id -u)" != "0" ]; then
  printf '%s\n' 'ERROR: image safety commands must run as root' >&2
  exit 1
fi
if [ ! -f "$ENV_FILE" ] || [ -L "$ENV_FILE" ]; then
  printf '%s\n' 'ERROR: image safety environment file is missing or unsafe' >&2
  exit 1
fi
if [ "${IMAGE_SAFETY_TEST_MODE:-0}" != "1" ] && [ "$(stat -c '%u:%a' "$ENV_FILE")" != "0:600" ]; then
  printf '%s\n' 'ERROR: image safety environment file must be root-owned with mode 0600' >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

exec python3 -I "$INSTALL_DIR/run.py" "$@"
