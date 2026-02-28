# Kreative Norge CRM

## Compose Modes (Dev vs Prod-like)

Use explicit compose files so `DJANGO_DEBUG=True` is only used in local development.

Local development (`DJANGO_DEBUG=True`):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

Prod-like local run (`DJANGO_DEBUG=False`):

```bash
docker compose up -d
```

## Local Smoke Test

Prerequisites:
- Docker is running
- Services are up

Run the editor API smoke test:

```bash
docker compose exec -T api python scripts/smoke_editor_api.py
```

Optional: run with explicit credentials/tenant

```bash
docker compose exec -T api python scripts/smoke_editor_api.py --tenant-id 1 --username smoke-local --password Smoke1234!
```

Expected success output ends with:

```text
SMOKE OK: auth + organizations + persons + organization-people + person-contacts
```
