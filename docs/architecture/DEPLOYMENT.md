# Deployment

**Status:** staging dokumentert, automatisering planlagt

Staging bruker Caddy foran Docker Compose:

- PostgreSQL
- Django/Gunicorn
- nginx i `web`-containeren
- bygget React-frontend

Caddy terminerer HTTPS for `staging.northernsound.no` og proxyer videre til `127.0.0.1:8080`. `web`-containeren binder derfor bare `127.0.0.1:8080:80`, ikke offentlig port `80`.

`web`-containerens nginx serverer React-frontend og proxyer `/api/`, `/admin/` og `/public/` videre til Django/Gunicorn i `api`-containeren. Nginx videresender `X-Forwarded-Proto` fra Caddy slik at Django kan stole på `SECURE_PROXY_SSL_HEADER` og unngå HTTPS redirect-loop.

Dagens dokumentasjon beskriver manuell oppdatering med `git pull` og rebuild. Målet er automatisk deploy til staging ved push, men mekanisme og sikkerhetsregler er ikke besluttet eller implementert som dokumentert standard.
