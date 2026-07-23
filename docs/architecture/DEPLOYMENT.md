# Deployment

**Status:** staging dokumentert, automatisering planlagt

Staging bruker Docker Compose med:

- PostgreSQL
- Django/Gunicorn
- nginx
- bygget React-frontend

Dagens dokumentasjon beskriver manuell oppdatering med `git pull` og rebuild. Målet er automatisk deploy til staging ved push, men mekanisme og sikkerhetsregler er ikke besluttet eller implementert som dokumentert standard.