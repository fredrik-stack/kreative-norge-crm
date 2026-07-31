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
- intern processing artifact identity og public release identity er separate; ny offentlig publiseringsrevisjon bruker alltid ny immutable release key
- aktiv public rendition-store er dedikert og unversioned eller har et likeverdig namespace uten offentlig tilgjengelige historiske versjoner
- «public storage» betyr ikke anonym bucket: produksjonsstorage bør være privat eller origin-begrenset bak et kontrollert CDN-/media-originlag, og klientene bruker `PUBLIC_MEDIA_ORIGIN`
- storage/CDN må støtte takedown, origin-fjerning, idempotent purge og verifikasjon uten å eksponere intern provider-endpoint eller credentials
- hybridbackup omfatter private originaler, canonical metadata/profil, nødvendige referanser og audit, aktive public rendition-bytes og deny-journal i separat failure-domain
- restore går gjennom karantene, deny-replay og fail-closed reconciliation før public serving kan åpnes

Konkret provider, region, IAM/private access, CDN, journalteknologi, backupverktøy, retention og RPO/RTO skal vurderes i en senere skrivebeskyttet provider-/driftsgate. Dagens stagingoppsett har ikke denne media-/objektstoragearkitekturen, og fase 3B.2 innførte ingen runtime- eller stagingkonfigurasjon.
