# Staging and Deployment

**Status:** staging eksisterer, automatisk deploy planlagt

Dagens dokumenterte stagingoppsett bruker Caddy foran Docker Compose, PostgreSQL, Django/Gunicorn og nginx.

Caddy terminerer HTTPS for `staging.northernsound.no` og sender trafikk videre til `127.0.0.1:8080`. `web`-containeren binder derfor `127.0.0.1:8080:80`. Nginx i `web`-containeren serverer frontend og proxyer `/api/`, `/admin/` og `/public/` til Django. Nginx må videresende `X-Forwarded-Proto` fra Caddy, ellers vil Django tolke proxied HTTPS-kall som HTTP og svare med redirect til samme HTTPS-URL.

Public HTML-visning brukes foreløpig bare i staging.

## Ønsket neste steg

Push til avtalt branch skal kunne utløse en sikker automatisk deploy til staging etter at obligatoriske tester er bestått.

Før dette etableres må vi beslutte:

- hvilken branch som deployer
- GitHub Actions eller annen mekanisme
- secrets og servertilgang
- migrasjonsflyt
- helse-/smoke-test
- rollback ved feil
