# Staging deploy

This is a small same-origin staging setup for the CRM:

- `db`: PostgreSQL
- `api`: Django + Gunicorn
- host-level Caddy terminates HTTPS
- `web`: nginx serving the built frontend and proxying `/api/`, `/admin/`, and `/public/`

Because the frontend and API share the same origin, Django session auth and CSRF are simpler to operate.

On the current staging server, Caddy listens publicly for `staging.northernsound.no` and reverse-proxies to `127.0.0.1:8080`. The `web` container therefore binds `127.0.0.1:8080:80`; it must not bind public port `80`, because Caddy owns that port.

## 1. Prepare the server

Install:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER
```

Log out and in again after adding your user to the `docker` group.

## 2. Clone the project

```bash
sudo mkdir -p /srv/kreative-norge-crm
sudo chown $USER:$USER /srv/kreative-norge-crm
git clone <your-repo-url> /srv/kreative-norge-crm
cd /srv/kreative-norge-crm
```

## 3. Create the staging env file

```bash
cp .env.staging.example .env.staging
```

Then edit `.env.staging` with your real domain, secret key, and database password.

Minimum values:

```env
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=...
DJANGO_ALLOWED_HOSTS=staging.your-domain.no
DJANGO_CSRF_TRUSTED_ORIGINS=https://staging.your-domain.no
DB_NAME=crm_db
DB_USER=crm
DB_PASSWORD=...
IMAGE_ASSET_FEATURE_ENABLED=False
IMAGE_ORIGINALS_ROOT=/srv/kreative-norge/media/private
IMAGE_RENDITIONS_ROOT=/srv/kreative-norge/media/public
VITE_API_BASE=
```

Keep `IMAGE_ASSET_FEATURE_ENABLED=False` until the persistence and Borg gates below are green. The two image roots are still required explicitly so the same Compose configuration can be verified before activation.

## 4. Prepare image storage

Run the repository-owned setup as root before the first image-capable API container is created:

```bash
sudo /srv/kreative-norge-crm/ops/staging/prepare-image-storage.sh
```

It creates only these host-persistent directories and enforces `root:root` mode `0750` without recursively changing or deleting existing image bytes:

- `/srv/kreative-norge/media/private`
- `/srv/kreative-norge/media/public`

The current API image runs as root and can write both directories. The root-run Borg service can read them. If the API later becomes non-root, ownership must be changed through a separate controlled delivery; do not broaden these modes ad hoc.

`public` is the historical storage-alias name for internal processing renditions. It is not mounted into `web`, has no `base_url`, and is not served by nginx or Caddy.

## 5. Start staging

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d --build
```

The repository compose file binds the web container to `127.0.0.1:8080:80`.

## 6. Create an admin user

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec api python manage.py createsuperuser
```

## 7. Verify the deployment

Check:

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging ps
docker-compose -f docker-compose.staging.yml --env-file .env.staging logs --tail=100 api
docker-compose -f docker-compose.staging.yml --env-file .env.staging logs --tail=100 web
```

Then open:

- `https://staging.northernsound.no/`
- `https://staging.northernsound.no/api/auth/session/`
- `https://staging.northernsound.no/public/actors/`
- `https://staging.northernsound.no/admin/`

## 8. HTTPS

The compose setup serves HTTP only on localhost port `8080`.

Caddy terminates HTTPS and must forward:

- `Host`
- `X-Forwarded-Proto https`

Nginx inside the `web` container must pass the incoming `X-Forwarded-Proto` header onward to Django for `/api/`, `/admin/`, and `/public/`. That matches Django's `SECURE_PROXY_SSL_HEADER` setting and prevents HTTPS redirect loops.

## 9. Updating staging

```bash
git pull
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d --build
docker-compose -f docker-compose.staging.yml --env-file .env.staging ps
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec -T api python manage.py check
```

## 10. Image persistence and activation gate

For the first image-runtime activation, keep the feature off and take a fresh backup before the deploy/recreate:

```bash
sudo systemctl start kreative-norge-backup.service
sudo systemctl status kreative-norge-backup.service --no-pager
```

After deploying the image-runtime code with the feature still off, generate a 32-character lowercase hexadecimal token and write the controlled PNG probe through the existing Django storage primitive in a one-off container:

```bash
PROBE_TOKEN=$(python3 -c 'import secrets; print(secrets.token_hex(16))')
docker-compose -f docker-compose.staging.yml --env-file .env.staging run --rm \
  -e IMAGE_ASSET_FEATURE_ENABLED=True api \
  python manage.py verify_image_storage_persistence --write --token "$PROBE_TOKEN"
```

Verify both host files against the checksum printed by the command. The exact relative keys are also printed, so no broad filesystem search is needed:

```bash
sha256sum \
  "/srv/kreative-norge/media/private/runtime-probes/$PROBE_TOKEN/original.png" \
  "/srv/kreative-norge/media/public/runtime-probes/$PROBE_TOKEN/rendition.png"
```

Recreate only the API container while the staging feature remains off, then read the same bytes through both storage aliases:

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d --no-deps --force-recreate api
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec -T api \
  python manage.py verify_image_storage_persistence --verify --token "$PROBE_TOKEN"
```

Stop if the server's known Compose 1.29.2 `ContainerConfig` failure appears. Do not remove or recreate unrelated containers as an implicit workaround.

With the probe still present, run a fresh Borg backup and the isolated restore gate. The backup manifest records a path token and checksum for one representative host-media file; restore must locate the same archive member and verify byte identity:

```bash
sudo systemctl start kreative-norge-backup.service
sudo /usr/local/lib/kreative-norge-backup/verify.sh
sudo BACKUP_ENV_FILE=/etc/kreative-norge-backup/backup.env \
  /usr/local/lib/kreative-norge-backup/restore-smoke.sh
```

Only after all three gates are green, remove the exact probe and change only the actual server's ignored `.env.staging` to `IMAGE_ASSET_FEATURE_ENABLED=True`:

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec -T api \
  python manage.py verify_image_storage_persistence --cleanup --token "$PROBE_TOKEN"
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d --no-deps --force-recreate api
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec -T api python manage.py check
```

The code/default and `.env.staging.example` stay `False`; production must not be activated by this procedure.

## 11. Minimal orphan cleanup

Database failure after immutable storage writes can leave unserved orphan bytes. The command is never scheduled and is dry-run by default:

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec -T api \
  python manage.py cleanup_image_storage_orphans
```

It requires both roots explicitly in the environment, accepts only local `FileSystemStorage`, refuses missing database-referenced files, symlink components, symlinks inside either root, special filesystem entries, invalid keys and root/backend mismatches. Files younger than 24 hours are excluded by default. Apply also holds PostgreSQL `SHARE` locks on both reference tables while it rebuilds the plan and deletes, so a new database reference cannot appear between the final check and unlink. Deletion requires an explicit operator action:

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec -T api \
  python manage.py cleanup_image_storage_orphans --apply --minimum-age-hours 24
```

This is only reference-aware orphan cleanup. It is not retention, takedown, release purge or automatic scheduling.

## Notes

- `api` runs `migrate` and `collectstatic` on startup.
- Frontend is built into the nginx image at deploy time.
- Static files are shared from Django to nginx through the `django_static` volume.
- Image originals and internal renditions use separate host bind mounts outside `/app` and outside staticfiles.
- For contact-data repairs, run `python manage.py repair_person_contacts` as dry-run first. Use `--apply` only after backup and explicit approval.
