# Deployment

**Status:** staging dokumentert; backupgrunnmur og intern bilde-runtime ACTIVE; deployautomatisering planlagt

Staging bruker Caddy foran Docker Compose:

- PostgreSQL
- Django/Gunicorn
- nginx i `web`-containeren
- bygget React-frontend

Caddy terminerer HTTPS for `staging.northernsound.no` og proxyer videre til `127.0.0.1:8080`. `web`-containeren binder derfor bare `127.0.0.1:8080:80`, ikke offentlig port `80`.

`web`-containerens nginx serverer React-frontend og proxyer `/api/`, `/admin/` og `/public/` videre til Django/Gunicorn i `api`-containeren. Nginx videresender `X-Forwarded-Proto` fra Caddy slik at Django kan stole på `SECURE_PROXY_SSL_HEADER` og unngå HTTPS redirect-loop.

Dagens dokumentasjon beskriver manuell oppdatering med `git pull` og rebuild. Målet er automatisk deploy til staging ved push, men mekanisme og sikkerhetsregler er ikke besluttet eller implementert som dokumentert standard.

## Godkjent lokal storage-MVP – konfigurasjonsgrunnmur implementert

[ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) og [ADR-008](../decisions/ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md) beslutter følgende MVP-retning:

- lokal utvikling, staging og første produksjons-MVP bruker `FileSystemStorage` eller tilsvarende gjennom navngitte Django `STORAGES`-aliaser
- aktive mediafiler blir på dagens Hetzner Cloud-server i host-persistente områder under `/srv/kreative-norge/media/`
- private originaler og offentlige renditions får separate navngitte storage-aliaser og tilgangspolicyer
- eksisterende import-/eksportfiler på default storage skal ikke flyttes eller brytes uten en separat kompatibilitets- og migreringsplan
- intern processing artifact identity og public release identity er separate; hver nye offentlige release bruker tilfeldig UUIDv4 og canonical relativ key `releases/<release_uuid>/<variant>.<ext>`
- selection-revisjon, tenant-/Organization-identitet, artifact key/checksum, request host og filesystempath inngår ikke i public key
- public key genereres internt og må være eksakt builder-resultat for release-ID, variant og outputformat; caller kan ikke levere fri key
- release-ID og keys reserveres varig og frigjøres aldri; samme key + samme forventede bytes kan være idempotent retry, mens samme key + andre bytes er fail-closed hard konflikt og public bytes aldri overskrives stilltiende
- aktiv public rendition-store er dedikert og unversioned eller har et likeverdig namespace uten offentlig tilgjengelige historiske versjoner
- offentlige renditions leveres fra en kontrollert same-origin/media-origin uten å eksponere intern filesystempath
- lokal serving/cache må støtte takedown, origin-fjerning, idempotent purge og verifikasjon
- hybridbackup omfatter private originaler, canonical metadata/profil, nødvendige referanser og audit, aktive public rendition-bytes og deny-journal i separat failure-domain
- restore går gjennom karantene, deny-replay og fail-closed reconciliation før public serving kan åpnes

S3, AWS, Backblaze, CDN og flerleverandørløsning er utsatt til dokumentert vekst- eller driftsbehov. Fase 3B.3-A har implementert den organization-typed release-aggregaten og canonical key-domenegrunnmuren med intern UUIDv4-/key-generering, eksakt builder-binding, immutable historisk mapping, databaseconstraints og atomisk feature-gated opprettelse. Permanent restore-sikker reservation-/deny-journal i separat failure-domain, varig reservasjon utenfor den aktive databasen, canonical public release-materialisering, public create-only/no-clobber og deny-reconciliation er fortsatt ikke implementert.

Første fase 3C-leveranse konfigurerte `IMAGE_ASSET_FEATURE_ENABLED=False` som standard, bevarte `default` og `staticfiles` og la til separate lokale `image_originals_private`-/`image_renditions_public`-aliaser. Roots valideres uten å opprette mapper. Når feature aktiveres utenfor debug, må begge roots være eksplisitt konfigurert; lokale temp-standarder er bare fallback i debug eller mens feature er avslått. Fase 3C.7 bruker aliasene gjennom en eksplisitt intern upload-only tjeneste: private originaler og processing-artifacts skrives med tenant-scopede deterministiske keys, eksakt-key/no-clobber og etterfølgende byte-/checksumverifikasjon. Fase 3D.1 legger til feature-gated interne API-/Editor-kall til denne tjenesten og private/no-store previews. Artifact-aliaset er fortsatt ikke en aktiv public origin, canonical `releases/...`-keys skrives ikke, og ingen filer serveres offentlig.

Staging har fra 2026-08-10 host-persistent intern bilde-runtime. API-containeren bind-mounter `/srv/kreative-norge/media/private` og `/srv/kreative-norge/media/public` til de samme absolutte pathene i containeren. `web` har ingen mediamount, og artifact-aliaset er fortsatt ikke en offentlig origin. Kode og eksempelkonfigurasjon beholder feature avslått; bare den ignorerte stagingkonfigurasjonen har `IMAGE_ASSET_FEATURE_ENABLED=True` etter grønn persistence-, backup- og restore-gate. Detaljert evidens finnes i [stagingaktiveringen 2026-08-10](../status/STAGING_IMAGE_RUNTIME_ACTIVATION_2026-08-10.md).

`cleanup_image_storage_orphans` gir en begrenset dry-run-first cleanup for de to bildealiasene. Apply krever PostgreSQL, validerte lokale roots og eksplisitt operatørvalg, revaliderer databasereferanser under lås og sletter bare gamle, urefererte regulære filer. Den er ikke en generell retention- eller public purge-mekanisme.

## Backupgrunnmur

Repoet har en generisk modul under `ops/backup/` for nattlig, kryptert Borg-backup til en separat Hetzner Storage Box:

- PostgreSQL custom-format dump med `pg_restore --list`
- eksisterende import-, rapport- og eksportfiler når de finnes
- fremtidige host-mediaområder automatisk når de finnes
- eksplisitt allowlistet serverkonfigurasjon og ikke-sensitivt manifest
- 14 daglige, 8 ukentlige og 12 månedlige arkiver
- nattlig systemd-timer og ukentlig repository-check
- isolert PostgreSQL 16 restore-smoke før aktivering
- eksplisitt eksport av kryptert Borg-repositorynøkkel og skrivebeskyttet repository-inspeksjon gjennom samme root-only Borg-/SSH-/repository-ID-kontrakt
- felles lokal Borg-port for stabil versjon `>=1.2.8` og `<1.3.0`, med remote path fortsatt `borg-1.2`
- semantisk pathgate som binder skrivbare Borg-/stateområder til dedikert backup-state og avgrenser media til godkjente host-/container-røtter før mutasjon

Status er **ACTIVE**. Den skrivebeskyttede [stagingbaselinen 2026-08-01](../status/STAGING_BACKUP_BASELINE_2026-08-01.md) ble fulgt av kontrollert [aktivering 2026-08-02](../status/STAGING_BACKUP_ACTIVATION_2026-08-02.md). Storage Box, kryptert Borg-repository, separat recovery-custody, første backup, full repository-check, isolert restore av samme arkiv, Storage Box-snapshot, nyere synlig Cloud Backup og begge systemd-timerne er verifisert grønne. Første backup brukte 8 sekunder og restore-smoke 8,7 sekunder. Se [Backup og restore](../operations/BACKUP_AND_RESTORE.md).

Backup, verify og restore deler én `flock`; bare låseieren kan skrive operativ status. Recovery-key-export krever en privat, operator-eid parent, avviser directory-/symlinktarget og oppretter sluttfilen atomisk uten overskriving eller beskyttede backup-/repo-destinasjoner. Repository-inspeksjon viser bare ufarlig sammendrag uten muterende Borg-operasjoner. Første passphrase-/key-custody er manuelt bekreftet for minst to ansvarlige; løpende custody kan fortsatt ikke bevises av kode og forblir **MANUAL REQUIRED**.

Det eksisterende `postgres_data`-volumet og de to eksplisitte bildeområdene er persistente. Django default storage har fortsatt location `/app` og ingen egen import-/eksportmount. Baselinen fant ikke `/app/imports`, `/app/exports` eller eksisterende filer i disse områdene; ingen nåværende filer er identifisert som utsatt. Nye `ImportJob.file`-, rapport- eller `ExportJob.file`-filer kan likevel havne i containerlaget og gå tapt ved recreate. Backupmodulen kan ta områdene med mens containeren finnes; en separat leveranse må etablere host-persistent default storage før disse filfunksjonene tas i aktiv bruk.

Den faktiske staging-environmentfilen er `/srv/kreative-norge-crm/.env.staging`, mens aktiv Compose-fil er `/srv/kreative-norge-crm/docker-compose.staging.yml`. Ved bildeaktiveringen ble API- og web-images rebuildet og gjenskapt kontrollert. Docker Compose 1.29.2s `ContainerConfig`-feil krevde eksakt stop/remove/create av berørte containere; oppgradering av Compose er derfor en åpen driftsrisiko, ikke en ny funksjonsgate.

Aktiv Storage Box er BX11 med 1 TB i FSN1. Applikasjonsserveren står i HEL1, og FSN1 gir fysisk lokasjonsseparasjon innen Hetzner. Kapasiteten vurderes på nytt ved 60–70 prosent faktisk bruk, med minst 20–30 prosent ledig for Borg-vekst og Storage Box-snapshots.

Hetzner Cloud Backups og Storage Box-snapshots er ekstra lag. De erstatter ikke den applikasjonsbevisste Borg-backupen eller logisk database-restore.
