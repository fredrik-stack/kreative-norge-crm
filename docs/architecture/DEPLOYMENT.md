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

## Planlagt bildestorage – ikke implementert

[ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) beslutter følgende målretning:

- lokal utvikling bruker `FileSystemStorage` eller tilsvarende
- staging og produksjon bruker en S3-kompatibel objektlagring gjennom Djangos `STORAGES`
- private originaler og offentlige renditions får separate navngitte storage-aliaser og tilgangspolicyer
- eksisterende import-/eksportfiler på default storage skal ikke flyttes eller brytes uten en separat kompatibilitets- og migreringsplan
- offentlige rendition-nøkler er immutable og cachevennlige, men storage/CDN må støtte takedown, origin-fjerning og cache-invalidering
- database, private originaler, aktive renditionreferanser og en varig takedown-/deny-journal inngår i en verifisert backup-/restorekontrakt

Konkret leverandør og teknisk kontrakt skal velges i fase 3B. Dagens stagingoppsett har ikke denne media-/objektstoragearkitekturen.
