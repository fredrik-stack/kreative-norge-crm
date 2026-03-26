# Staging deploy

This is a small same-origin staging setup for the CRM:

- `db`: PostgreSQL
- `api`: Django + Gunicorn
- `web`: nginx serving the built frontend and proxying `/api/` and `/admin/`

Because the frontend and API share the same origin, Django session auth and CSRF are simpler to operate.

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
docker compose -f docker-compose.staging.yml --env-file .env.staging up -d --build
```

## 5. Create an admin user

```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging exec api python manage.py createsuperuser
```

## 6. Verify the deployment

Check:

```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging ps
docker compose -f docker-compose.staging.yml --env-file .env.staging logs api --tail=100
docker compose -f docker-compose.staging.yml --env-file .env.staging logs web --tail=100
```

Then open:

- `http://<server-ip>/`
- `http://<server-ip>/admin/`

After DNS is pointing to the server, switch to the real staging domain.

## 7. HTTPS

The compose setup serves HTTP on port `80`.

For real staging use, add HTTPS in front of it. The easiest paths are:

1. Put Caddy or host-level nginx in front and terminate TLS there.
2. Or extend this compose setup with a certbot-based TLS layer.

If you terminate TLS in front of the app, keep forwarding:

- `Host`
- `X-Forwarded-Proto https`

That matches Django's `SECURE_PROXY_SSL_HEADER` setting.

## 8. Updating staging

```bash
git pull
docker compose -f docker-compose.staging.yml --env-file .env.staging up -d --build
```

## Notes

- `api` runs `migrate` and `collectstatic` on startup.
- Frontend is built into the nginx image at deploy time.
- Static files are shared from Django to nginx through the `django_static` volume.
