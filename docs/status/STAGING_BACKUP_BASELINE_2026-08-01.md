# Staging backup baseline 2026-08-01

## 1. Status og avgrensning

Denne baselinen ble gjennomført skrivebeskyttet 2026-08-01 før eventuell installasjon av backupgrunnmuren i [ADR-008](../decisions/ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md). Resultatet er anonymisert og inneholder ikke hostname, IP-adresse, credentials, brukernavn, nøkkelpaths, environmentverdier, personopplysninger eller sensitive filnavn.

Repoets backupmodul er fortsatt **PREPARED, NOT ACTIVE**. Ingen serverfiler, Git-refs, database, data, containere, volumes, tjenester, timere, secrets, backup, Storage Box, DNS, Cloudflare eller deploy ble opprettet, endret, stoppet eller startet.

## 2. SSH-verifisering

- SSH authentication: `PASS`
- hostname returnert: `YES`
- `SSH_OK` returnert: `YES`

## 3. Repository- og Git-status

- repository-path: `/srv/kreative-norge-crm`
- serverbranch: `main`
- serverrepoet var rent på applikasjonscommiten `6768af8a3b48314aec028ec5972939c6ef0e38e8`
- autoritativ GitHub `main` var `5219806020fb2c9b0a62340eb9f94999fe10565b`
- serverrepoet var 0 commits foran og 11 commits bak autoritativ `main`
- PR #16s backupfiler var ikke installert eller sjekket ut på serveren
- det fantes ingen lokale, ucommittede serverendringer

Serverrepoet skal ikke synkroniseres før separat merge- og deploygodkjenning.

## 4. Systemdisk og mounts

- systemdisk: 75 GiB
- brukt: omtrent 41 GiB
- ledig: omtrent 32 GiB
- diskbruk: omtrent 57 prosent
- inodebruk: omtrent 60 prosent
- root og EFI var montert fra samme systemdisk
- ingen ekstra persistent block device eller mount ble funnet
- Hetzner Console viste 0 Cloud Volumes, i samsvar med lokal mountstatus
- Docker data root og navngitte Docker-volumes lå på systemdisken

## 5. Docker og Compose

- Docker Engine: `28.2.2`
- aktivt Compose-verktøy: `docker-compose 1.29.2`
- Docker Compose v2 var ikke tilgjengelig
- aktiv Compose-fil: `/srv/kreative-norge-crm/docker-compose.staging.yml`
- aktiv environmentfil: `/srv/kreative-norge-crm/.env.staging`
- service-navnene `db`, `api` og `web` var aktive
- alle tre CRM-containerne kjørte med null restarter
- `postgres_data` var omtrent 71,3 MiB og lå på systemdisken
- `django_static` var omtrent 3,3 MiB og lå på systemdisken
- ingen uventede bind mounts eller Docker-volumes ble funnet
- API-containeren hadde bare static-mount; web-containeren hadde bare read-only static-mount

## 6. PostgreSQL-versjon og størrelser

- database-service: `db`
- PostgreSQL: `16.13`
- database: `crm_db`
- readiness: `READY`
- aktiv databasestørrelse: omtrent 16,6 MiB
- rått PostgreSQL-volume: omtrent 71,3 MiB; dette volumet skal ikke kopieres rått av backupmodulen
- fire databaser var registrert i PostgreSQL-instansen
- restore-smoke-tabellene `django_migrations`, `crm_organization` og `crm_person` fantes

## 7. Eksisterende manuelle dumps

- ingen automatisert CRM- eller PostgreSQL-backupjobb ble funnet
- fire tidligere manuelle PostgreSQL-dumper ble funnet i to serverkataloger
- samlet størrelse var omtrent 21,5 MiB
- den dokumenterte reparasjonsdumpen fra juli 2026 fantes fortsatt med forventet størrelse og tidspunkt
- ingen dumpnavn eller checksums er gjengitt her

## 8. FileField- og mediafunn

### Dagens faktum

- `/app/imports` fantes ikke
- `/app/exports` fantes ikke
- filantallet var null
- ingen eksisterende import- eller eksportfiler ble identifisert som utsatt
- Django default storage brukte `FileSystemStorage` med location `/app`
- API-containeren hadde ingen persistent import-, eksport- eller media-mount
- `/srv/kreative-norge/media/default`, `/srv/kreative-norge/media/private` og `/srv/kreative-norge/media/public` fantes ikke

### Fremtidig risiko

Nye `ImportJob`-, rapport- eller `ExportJob`-filer kan med dagens runtime bli skrevet til API-containerlaget og gå tapt ved recreate.

### Senere oppgave

Host-persistent default/media-storage og runtimekobling skal implementeres i en separat, kontrollert leveranse før import-/eksportfiler eller bildearkitekturen tas i aktiv bruk. Ingen kataloger eller mounts ble opprettet av baselinen.

## 9. Faktiske konfigurasjonspaths

- repository-root: `/srv/kreative-norge-crm`
- Compose-fil: `/srv/kreative-norge-crm/docker-compose.staging.yml`
- Compose-environmentfil: `/srv/kreative-norge-crm/.env.staging`
- Caddy-konfigurasjon: `/etc/caddy/Caddyfile`
- Docker data root: `/var/lib/docker`
- ingen CRM-relaterte backup-units eller installert backupkonfigurasjon fantes

`ops/backup/backup.env.example` måtte derfor bruke `.env.staging` både i `COMPOSE_ENV_FILE` og i `SERVER_CONFIG_PATHS`. Environmentfilens innhold ble ikke lest eller gjengitt.

## 10. Eksisterende backup- og timerstatus

- automatisert CRM-/PostgreSQL-backup: ikke funnet
- CRM-relaterte backup-timere: ikke funnet
- eksisterende OS-timer for pakkedatabasebackup var ikke en konflikt
- Restic og Rclone: ikke installert
- Rsync: installert, men ingen tilknyttet backupjobb ble funnet
- backup-statusfil, restore-gate og restorebevis: ikke funnet
- ekstern backupvarsling: ikke funnet

## 11. Borg-forutsetninger

- Borg: `NOT INSTALLED`
- lokal Borg-versjon: `UNVERIFIED`
- `borg-1.2` remote-path-konsept: forberedt i PR #16
- dedikert backupidentitet: `NOT CREATED`
- Storage Box: `NOT CREATED / MANUAL REQUIRED`
- Borg-repository: `NOT CONFIGURED`
- recovery-secret: `NOT CREATED`
- første Borg-backup: `NOT RUN`
- restore-smoke: `NOT RUN`
- systemd-timere: `NOT INSTALLED OR ENABLED`

## 12. Cloud Backup

Prosjekteier verifiserte manuelt i Hetzner Console 2026-08-01:

- status: **ENABLED AND FIRST BACKUP VERIFIED**
- første synlige backupstørrelse: 11,6 GB
- Cloud Volumes: 0
- serverlokasjon: HEL1

Cloud Backup er et ekstra helserverlag. Det erstatter ikke logisk PostgreSQL-dump, kryptert Borg-backup til separat Storage Box eller isolert restore-smoke.

## 13. Storage Box-kapasitetsanbefaling

- anbefalt plan: BX11
- kapasitet: 1 TB
- anbefalt lokasjon: FSN1
- begrunnelse: applikasjonsserveren står i HEL1, og FSN1 gir fysisk lokasjonsseparasjon innen Hetzner
- dagens database- og filgrunnlag er svært lite; BX11 er minste tilgjengelige plan og gir god vekstmargin
- gjennomfør kapasitetsreview ved 60–70 prosent faktisk bruk
- behold minst 20–30 prosent ledig for Borg-vekst og Storage Box-snapshots
- Borg-deduplisering kan redusere behovet, men ingen bestemt kompresjons- eller dedupliseringsgrad legges til grunn
- fremtidig bildevekst er ikke regnet som eksisterende data

Storage Box ble ikke bestilt eller kontaktet under baselinen.

## 14. Kjente risikoer

- FileField-data blir ikke host-persistent før en separat runtimeleveranse etablerer mount og storagekobling
- Storage Box, Borg, recovery-secret, første Borg-backup, restore-smoke og timere mangler fortsatt
- Storage Box-snapshots er ikke konfigurert
- ingen ekstern backupvarsling er etablert
- faktisk Borg-RPO/RTO og restorevarighet er ikke målt
- serverrepoet er eldre enn autoritativ GitHub `main` og skal bare synkroniseres gjennom separat godkjent deploy

## 15. Endringsbekreftelse

Baselinen var skrivebeskyttet. Ingen filer, konfigurasjon, Git-refs, database, data, publiseringsflagg, containere, volumes, tjenester, timere, secrets, backup, Storage Box, Cloud Backup, DNS, Cloudflare eller deploy ble opprettet, endret, stoppet eller startet.
