#!/usr/bin/env bash

set -Eeuo pipefail
umask 027

MEDIA_ROOT=/srv/kreative-norge/media
PRIVATE_ROOT=/srv/kreative-norge/media/private
RENDITION_ROOT=/srv/kreative-norge/media/public
DELIVERY_ROOT=/srv/kreative-norge/media/public-delivery
DELIVERY_GROUP_NAME=kreative-norge-public-media
DELIVERY_GROUP_ID=2000

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
require_no_symlink_components "$DELIVERY_ROOT"

group_name_for_id="$(getent group "$DELIVERY_GROUP_ID" | cut -d: -f1 || true)"
group_id_for_name="$(getent group "$DELIVERY_GROUP_NAME" | cut -d: -f3 || true)"
if [ -n "$group_name_for_id" ] && [ "$group_name_for_id" != "$DELIVERY_GROUP_NAME" ]; then
  die "delivery group ID $DELIVERY_GROUP_ID is already used by $group_name_for_id"
fi
if [ -n "$group_id_for_name" ] && [ "$group_id_for_name" != "$DELIVERY_GROUP_ID" ]; then
  die "delivery group $DELIVERY_GROUP_NAME has unexpected ID $group_id_for_name"
fi
if [ -z "$group_name_for_id" ] && [ -z "$group_id_for_name" ]; then
  groupadd --system --gid "$DELIVERY_GROUP_ID" "$DELIVERY_GROUP_NAME"
fi

install -d -o root -g root -m 0750 "$MEDIA_ROOT"
install -d -o root -g root -m 0750 "$PRIVATE_ROOT" "$RENDITION_ROOT"
install -d -o root -g "$DELIVERY_GROUP_NAME" -m 2750 "$DELIVERY_ROOT"

unsafe_delivery_object="$(
  find "$DELIVERY_ROOT" -mindepth 1 ! -type d ! -type f -print -quit
)"
[ -z "$unsafe_delivery_object" ] || \
  die "delivery root contains an unsafe object: $unsafe_delivery_object"
chown -R "root:$DELIVERY_GROUP_NAME" "$DELIVERY_ROOT"
find "$DELIVERY_ROOT" -type d -exec chmod 2750 {} +
find "$DELIVERY_ROOT" -type f -exec chmod 0640 {} +

for path in "$MEDIA_ROOT" "$PRIVATE_ROOT" "$RENDITION_ROOT"; do
  [ -d "$path" ] || die "required directory is unavailable: $path"
  require_no_symlink_components "$path"
  owner_group="$(stat -c '%U:%G' "$path")"
  mode="$(stat -c '%a' "$path")"
  [ "$owner_group" = "root:root" ] || die "unexpected owner for $path"
  [ "$mode" = "750" ] || die "unexpected mode for $path"
done

delivery_owner_group="$(stat -c '%U:%G' "$DELIVERY_ROOT")"
delivery_mode="$(stat -c '%a' "$DELIVERY_ROOT")"
[ "$delivery_owner_group" = "root:$DELIVERY_GROUP_NAME" ] || \
  die "unexpected owner for $DELIVERY_ROOT"
[ "$delivery_mode" = "2750" ] || die "unexpected mode for $DELIVERY_ROOT"

printf 'image storage directories ready\n'
