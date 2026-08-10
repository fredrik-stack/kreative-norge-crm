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
BRAVE_IMAGE_SEARCH_API_KEY=
VITE_API_BASE=
```

Keep `IMAGE_ASSET_FEATURE_ENABLED=False` until the persistence and Borg gates below are green. The two image roots are still required explicitly so the same Compose configuration can be verified before activation.

`BRAVE_IMAGE_SEARCH_API_KEY` is optional and server-side only. The `api` service receives it through Compose `env_file: .env.staging`; never put it in a `VITE_` variable, frontend build argument, browser response, command output, or logs. If it is empty, Brave search returns the controlled `503` code `brave_not_configured`. That is a valid fail-closed runtime state. Do not supply the credential until the project or contract owner has documented editor coverage under the current Brave Search API Terms section 4(c), plus any required privacy notices or consents for query data. After that approval, live Brave verification may proceed without exposing the value.

Phase 3D.2 does not change the existing `image_originals_private` or `image_renditions_public` storage aliases, host-persistent roots, Borg coverage, or dry-run-first orphan cleanup. It activates no PUBLIC image release or production behavior.

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

The repository nginx configuration sets `client_max_body_size 16m`. This is intentional headroom for the application limit of a 15 MiB source image plus multipart framing. Keep the proxy limit above the application limit; do not raise either limit ad hoc during deploy.

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

Take and verify a fresh Borg backup before pulling or rebuilding a phase 3D.2 staging deploy:

```bash
sudo systemctl start kreative-norge-backup.service
sudo systemctl status kreative-norge-backup.service --no-pager
```

Stop before deploy if the backup is not green. A successful backup does not by itself verify Brave configuration or the 3D.2 user journey.

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

It requires both roots explicitly in the environment, accepts only local `FileSystemStorage`, refuses missing database-referenced files, symlink components, symlinks inside either root, special filesystem entries, invalid keys and root/backend mismatches. Files younger than 24 hours are excluded by default. Apply takes the exclusive form of the same transaction-level PostgreSQL advisory lock held in shared mode by ingest from before storage write/reuse through database commit. It then holds PostgreSQL `SHARE` locks on both reference tables while rebuilding the plan. Deletion opens the configured root and each key component descriptor-relatively with no-follow and unlinks only a verified regular filename relative to its opened parent directory. Deletion requires an explicit operator action:

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec -T api \
  python manage.py cleanup_image_storage_orphans --apply --minimum-age-hours 24
```

This is only reference-aware orphan cleanup. It is not retention, takedown, release purge or automatic scheduling.

## 12. Roll back image runtime activation

Rollback disables the Editor flow; it does not roll back or delete image assets. First record current `ImageAsset`, `ImageRendition` and `OrganizationImageRelease` counts and run the orphan command in dry-run mode. Set only `IMAGE_ASSET_FEATURE_ENABLED=False` in the ignored `.env.staging`. Keep `IMAGE_ORIGINALS_ROOT` and `IMAGE_RENDITIONS_ROOT` unchanged, and do not remove either host directory or any media bytes.

Because the current server has Docker Compose 1.29.2 and has previously hit the `ContainerConfig` recreate error, recreate only API in a controlled sequence. Do not remove database, web, volumes or media:

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging stop api
docker-compose -f docker-compose.staging.yml --env-file .env.staging rm -f api
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d --no-deps api
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec -T api python manage.py check
```

Then verify:

1. Django reports `IMAGE_ASSET_FEATURE_ENABLED=False` inside API.
2. `/`, `/api/auth/session/` and `/public/actors/` return the expected successful responses over HTTPS.
3. An authenticated Organization Editor no longer shows the `Aktørbilde` flow.
4. Database counts match the recorded pre-rollback counts.
5. `cleanup_image_storage_orphans` dry-run is green, which proves every DB-referenced original and rendition is still present. Do not use `--apply` during rollback.
6. Previously recorded representative media checksums still match on the host. No public release is created or deleted by rollback.

The Compose 1.29.2 `ContainerConfig` behavior remains a separate operational risk. Stop if the exact API-only sequence fails; do not broaden removal as an implicit workaround. Upgrading Compose is outside this delivery.

## Notes

- `api` runs `migrate` and `collectstatic` on startup.
- Frontend is built into the nginx image at deploy time.
- Static files are shared from Django to nginx through the `django_static` volume.
- Image originals and internal renditions use separate host bind mounts outside `/app` and outside staticfiles.
- For contact-data repairs, run `python manage.py repair_person_contacts` as dry-run first. Use `--apply` only after backup and explicit approval.
