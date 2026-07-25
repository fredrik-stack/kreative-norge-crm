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
VITE_API_BASE=
```

## 4. Start staging

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d --build
```

The repository compose file binds the web container to `127.0.0.1:8080:80`.

## 5. Create an admin user

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec api python manage.py createsuperuser
```

## 6. Verify the deployment

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

## 7. HTTPS

The compose setup serves HTTP only on localhost port `8080`.

Caddy terminates HTTPS and must forward:

- `Host`
- `X-Forwarded-Proto https`

Nginx inside the `web` container must pass the incoming `X-Forwarded-Proto` header onward to Django for `/api/`, `/admin/`, and `/public/`. That matches Django's `SECURE_PROXY_SSL_HEADER` setting and prevents HTTPS redirect loops.

## 8. Updating staging

```bash
git pull
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d --build
docker-compose -f docker-compose.staging.yml --env-file .env.staging ps
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec -T api python manage.py check
```

## Notes

- `api` runs `migrate` and `collectstatic` on startup.
- Frontend is built into the nginx image at deploy time.
- Static files are shared from Django to nginx through the `django_static` volume.
- For contact-data repairs, run `python manage.py repair_person_contacts` as dry-run first. Use `--apply` only after backup and explicit approval.
