#!/usr/bin/env bash

set -Eeuo pipefail
umask 027

MEDIA_ROOT=/srv/kreative-norge/media
PRIVATE_ROOT=/srv/kreative-norge/media/private
RENDITION_ROOT=/srv/kreative-norge/media/public

die() {
  printf 'prepare-image-storage: %s\n' "$*" >&2
  exit 1
}

[ "${EUID:-$(id -u)}" -eq 0 ] || die "must run as root"

require_no_symlink_components() {
  local path="$1"
  local current=""
  local component
  IFS='/' read -r -a components <<<"${path#/}"
  for component in "${components[@]}"; do
    current="${current}/${component}"
    [ ! -L "$current" ] || die "refusing symlink component: $current"
  done
}

require_no_symlink_components "$PRIVATE_ROOT"
require_no_symlink_components "$RENDITION_ROOT"

install -d -o root -g root -m 0750 "$MEDIA_ROOT"
install -d -o root -g root -m 0750 "$PRIVATE_ROOT" "$RENDITION_ROOT"

for path in "$MEDIA_ROOT" "$PRIVATE_ROOT" "$RENDITION_ROOT"; do
  [ -d "$path" ] || die "required directory is unavailable: $path"
  require_no_symlink_components "$path"
  owner_group="$(stat -c '%U:%G' "$path")"
  mode="$(stat -c '%a' "$path")"
  [ "$owner_group" = "root:root" ] || die "unexpected owner for $path"
  [ "$mode" = "750" ] || die "unexpected mode for $path"
done

printf 'image storage directories ready\n'
