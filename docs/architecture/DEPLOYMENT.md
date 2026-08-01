# Deployment

**Status:** staging dokumentert; backupgrunnmur forberedt, ikke aktiv; deployautomatisering planlagt

Staging bruker Caddy foran Docker Compose:

- PostgreSQL
- Django/Gunicorn
- nginx i `web`-containeren
- bygget React-frontend

Caddy terminerer HTTPS for `staging.northernsound.no` og proxyer videre til `127.0.0.1:8080`. `web`-containeren binder derfor bare `127.0.0.1:8080:80`, ikke offentlig port `80`.

`web`-containerens nginx serverer React-frontend og proxyer `/api/`, `/admin/` og `/public/` videre til Django/Gunicorn i `api`-containeren. Nginx videresender `X-Forwarded-Proto` fra Caddy slik at Django kan stole på `SECURE_PROXY_SSL_HEADER` og unngå HTTPS redirect-loop.

Dagens dokumentasjon beskriver manuell oppdatering med `git pull` og rebuild. Målet er automatisk deploy til staging ved push, men mekanisme og sikkerhetsregler er ikke besluttet eller implementert som dokumentert standard.

## Godkjent lokal storage-MVP – runtime ikke implementert

[ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) og [ADR-008](../decisions/ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md) beslutter følgende MVP-retning:

- lokal utvikling, staging og første produksjons-MVP bruker `FileSystemStorage` eller tilsvarende gjennom navngitte Django `STORAGES`-aliaser
- aktive mediafiler blir på dagens Hetzner Cloud-server i host-persistente områder under `/srv/kreative-norge/media/`
- private originaler og offentlige renditions får separate navngitte storage-aliaser og tilgangspolicyer
- eksisterende import-/eksportfiler på default storage skal ikke flyttes eller brytes uten en separat kompatibilitets- og migreringsplan
- intern processing artifact identity og public release identity er separate; ny offentlig publiseringsrevisjon bruker alltid ny immutable release key
- aktiv public rendition-store er dedikert og unversioned eller har et likeverdig namespace uten offentlig tilgjengelige historiske versjoner
- offentlige renditions leveres fra en kontrollert same-origin/media-origin uten å eksponere intern filesystempath
- lokal serving/cache må støtte takedown, origin-fjerning, idempotent purge og verifikasjon
- hybridbackup omfatter private originaler, canonical metadata/profil, nødvendige referanser og audit, aktive public rendition-bytes og deny-journal i separat failure-domain
- restore går gjennom karantene, deny-replay og fail-closed reconciliation før public serving kan åpnes

S3, AWS, Backblaze, CDN og flerleverandørløsning er utsatt til dokumentert vekst- eller driftsbehov. Dagens stagingoppsett har ingen host-persistent media-runtime, og denne backupleveransen endrer ikke Compose, Django settings eller aktive containere.

## Backupgrunnmur

Repoet har en generisk modul under `ops/backup/` for nattlig, kryptert Borg-backup til en separat Hetzner Storage Box:

- PostgreSQL custom-format dump med `pg_restore --list`
- eksisterende import-, rapport- og eksportfiler når de finnes
- fremtidige host-mediaområder automatisk når de finnes
- eksplisitt allowlistet serverkonfigurasjon og ikke-sensitivt manifest
- 14 daglige, 8 ukentlige og 12 månedlige arkiver
- nattlig systemd-timer og ukentlig repository-check
- isolert PostgreSQL 16 restore-smoke før aktivering

Status er **PREPARED, NOT ACTIVE** fordi server-SSH, Storage Box, første backup, restore, recovery-secret, Storage Box-snapshots og Hetzner Cloud Backups ikke kunne verifiseres. Timerne installeres ikke automatisk og kan ikke aktiveres av installasjonsscriptet før de tekniske backup-/restoreportene er grønne. Se [Backup og restore](../operations/BACKUP_AND_RESTORE.md).

Det eksisterende `postgres_data`-volumet er persistent. API-containeren har derimot ingen dokumentert media-mount i dagens Compose-fil. `ImportJob.file`, preview-/feilrapporter og `ExportJob.file` kan dermed ligge i `/app/imports` og `/app/exports` i containerlaget. Backupmodulen kan ta dem med mens containeren finnes; en separat migreringsleveranse må senere flytte dem til host-persistent default storage uten datatap.

Hetzner Cloud Backups og Storage Box-snapshots er ekstra lag. De erstatter ikke den applikasjonsbevisste Borg-backupen eller logisk database-restore.
