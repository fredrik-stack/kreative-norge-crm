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

S3, AWS, Backblaze, CDN og flerleverandørløsning er utsatt til dokumentert vekst- eller driftsbehov. Fase 3B.3-A etablerte release-aggregatet. Fase 3E.1A har implementert og stagingaktivert permanent reservation-/lifecycle-ledger, rebuildbar read-model, incident restore og host/systemd Borg-anchor. Fase 3E.1B har flyttet UUID/key-valget til atomisk host-reservasjon, lagt unik DB-binding, separat delivery-root, create-only/no-clobber, read-back og activation. Materialisering er `ACTIVE` i staging etter syntetisk crash/restart/retry-gate. Fase 3E.1C implementerer kontrollert serving bak et separat default-off flagg; runtime deny, projection og PUBLIC kommer senere.

Første fase 3C-leveranse konfigurerte `IMAGE_ASSET_FEATURE_ENABLED=False` som standard og separate lokale `image_originals_private`-/`image_renditions_public`-aliaser. 3E.1B legger til `public_image_delivery` med `base_url=None` og en materialiseringsgate som har kode-/eksempelstandard `PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=False`, men aktiv stagingverdi `True`. Artifact-aliaset er fortsatt ikke en public origin. Delivery-rooten godtar bare canonical `releases/...`-keys gjennom release-workflowen. I 3E.1C monteres bare delivery-rooten read-only i `web`, og den kan kun nås gjennom en Nginx-location med `internal`, `autoindex off` og `disable_symlinks on`; den anonyme `/media/releases/...`-ruten går alltid via Django-gaten.

Staging har fra 2026-08-10 host-persistent intern bilde-runtime. API-containeren bind-mounter `/srv/kreative-norge/media/private` og `/srv/kreative-norge/media/public` til de samme absolutte pathene i containeren. `web` har ingen mediamount, og artifact-aliaset er fortsatt ikke en offentlig origin. Kode og eksempelkonfigurasjon beholder feature avslått; bare den ignorerte stagingkonfigurasjonen har `IMAGE_ASSET_FEATURE_ENABLED=True` etter grønn persistence-, backup- og restore-gate. Detaljert evidens finnes i [stagingaktiveringen 2026-08-10](../status/STAGING_IMAGE_RUNTIME_ACTIVATION_2026-08-10.md).

## Fase 3E.1A – separat safety-ledger

Safety-ledgeren er bevisst utenfor Django, PostgreSQL, mediaområdene og begge containere:

- host-state: `/var/lib/kreative-norge-image-safety/ledger.sqlite3`
- host-konfigurasjon: `/etc/kreative-norge-image-safety/`
- host-kode: `/usr/local/lib/kreative-norge-image-safety/`
- execution: root-owned systemd oneshot for synkron Borg-anchor og separat fail-closed health
- remote: dedikert Storage Box-subaccount og dedikert Borg 1.2 append-only repository

`docker-compose.staging.yml` har ingen safety-mount eller Borg-credential. Den generelle ADR-008-backupen brukes ikke som safety-anchor. Installer, units, dedikert subaccount/repository, capability-/transaction-recoverytest, restartpersistens og health-timer er `ACTIVE` i staging; raw filtilgang er dokumentert og akseptert restrisiko, ikke en absolutt WORM-garanti. Se [aktiveringsrapporten](../status/STAGING_PHASE_3E1A_ACTIVATION_2026-08-20.md) og [operativ runbook](../operations/PUBLIC_IMAGE_SAFETY_LEDGER.md).

## Fase 3E.1B – materialisering ACTIVE i staging, serving av

Staging kjører en root-eid systemd `.socket`/`.service` for `/run/kreative-norge-image-safety/bridge.sock`. Bare runtime-directory mountes read-only i `api`; `web` får verken socket eller delivery-root, og ingen container får ledger, `/etc`-konfigurasjon eller Borg-credential. API har et eget read/write bindmount av `/srv/kreative-norge/media/public-delivery`. Den aktive generelle backupallowlisten inkluderer delivery-rooten eksplisitt.

Gunicorn har 60 sekunders worker-timeout. Bridge-serveren har 45 sekunders operation deadline, Django-klienten har 50 sekunder og framingtimeouten er 5 sekunder. Foundationgaten verifiserte Linux/Docker `SO_PEERCRED`, socket `root:root` `0600`, API-/webisolasjon, delivery-persistens gjennom API-recreate og identisk delivery-checksum i backup/restore. Den separate materialiseringsgaten 2026-08-23 aktiverte `PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=True` i staging og beviste ankret reserve/activate, immutable DB-binding, hard no-clobber, recovery etter én fil og API-restart samt full retry uten overskriving. Post-activation-backup og isolert restore er grønne. Se [foundationevidensen](../status/STAGING_PHASE_3E1B_FOUNDATION_2026-08-23.md) og [aktiveringsevidensen](../status/STAGING_PHASE_3E1B_MATERIALIZATION_ACTIVATION_2026-08-23.md).

## Fase 3E.1C – kodeklar kontrollert serving, staging av

`PUBLIC_IMAGE_SERVING_ENABLED=False` er egen kode- og eksempelstandard og krever både den generelle bildegaten og materialiseringsgaten. Ved aktivering kreves eksplisitte `PUBLIC_SITE_ORIGIN` og `PUBLIC_MEDIA_ORIGIN`; begge normaliseres og må bruke en eksakt, ikke-wildcard host fra `DJANGO_ALLOWED_HOSTS`. Utenfor debug kreves HTTPS. Requestens `Host` og `X-Forwarded-Host` brukes aldri til å bygge public URL.

Nginx-workerens UID/GID er `101:101`, mens 3E.1B-filene historisk er `root:root 0640`. Host-prepareringen etablerer derfor den dedikerte, kollisjonssjekkede gruppen `kreative-norge-public-media` med GID `2000`, migrerer bare delivery-rooten til `root:<gruppen>` og setter directories til `2750` og filer til `0640`. Web-imaget oppretter samme numeriske gruppe og melder `nginx`-brukeren eksplisitt inn i den; Compose beholder i tillegg `group_add: 2000`. Dette er nødvendig fordi Nginx-masterens privilegiedropp ellers fjerner en GID som bare er lagt til av container-runtime. API-root kan fortsatt materialisere, setgid arves av nye directories/filer, web får bare group-read gjennom read-only mount, og private/artifact-/safetyområder berøres ikke.

Kun canonical `GET`/`HEAD /media/releases/<uuidv4>/<square|landscape|share>.<webp|png|jpg>` kan nå Django-gaten. Den krever publisert Organization, gjeldende aktiv asset-selection, eksakt immutable DB-mapping, positiv metadata, read-only ledger-autorisasjon og byte-/checksum-/format-/dimensjonsverifikasjon av alle tre materialiserte filer for hver request. Ikke-canonical former under samme prefix treffer en tom `404/no-store`-catch-all uten domenekall. Den canonical viewen er CSRF-unntatt bare for at dens write-frie metodegate skal gi `405/no-store` for alt annet enn GET/HEAD før domenekall. Avvist eller ukjent release gir `404`; safety-/bridge-/filfeil gir `503`. Begge feiltyper har `Cache-Control: no-store`. Godkjent svar bruker bare intern `X-Accel-Redirect`, `ETag` fra checksum og `Cache-Control: private, max-age=60, must-revalidate`; validert `If-None-Match` gir `304` først etter de samme gatene. Den interne Nginx-locationen har `etag off` og setter `ETag` eksplisitt fra `$upstream_http_etag`, slik at Djangos checksum-ETag bevares i stedet for å bli fjernet eller erstattet av en filmetadata-ETag. Shared proxycache og `immutable` brukes ikke.

Aktivering skjer som separat gate etter merge og deploy med flagget av. Rollback er bare å sette servingflagget av og rekreere API/web. Projection, API/PUBLIC, legacy-cutover, takedown og 3E.2–3E.4 inngår ikke.

## Fase 3D.2 – operativ konfigurasjon og credential

Fase 3D.2 legger til Brave-bildesøk som en valgfri intern kilde. `BRAVE_IMAGE_SEARCH_API_KEY` leses bare av Django fra servermiljøet og har tom standardverdi. Staging-Compose bruker repo-rotens ignorerte `/srv/kreative-norge-crm/.env.staging` som `env_file` for `api`. En eventuell gyldig nøkkel installeres der direkte på serveren av prosjekteier/operatør, aldri i Git, chat, PR, `.env.staging.example`, `VITE_`-variabel eller frontend-buildargument. Deretter rekreeres bare API-containeren, og kontrollen rapporterer bare `configured`/`missing`, aldri verdien. Nøkkelen skal aldri eksponeres til frontend, API-responser eller logger. Manglende nøkkel gir kontrollert `503` med kode `brave_not_configured`. Live-gaten 2026-08-11 bekreftet historisk 30 ekte kandidater, privat originalpreview, secure fetch og processing med `search_lang=nb`. Credentialen ble deretter satt tilbake til tom verdi; bare API ble rekreert, og staging rapporterer nå boolsk `brave_configured=False` og kontrollert `brave_not_configured`. Brave er dermed **operativt ikke aktiv** for ordinære Editor-sluttbrukere. Reaktivering krever dokumentert oppfyllelse av sluttbrukerkravet i Braves gjeldende Terms punkt 4(c), inkludert skriftlig avtale med forpliktelser vesentlig tilsvarende 3(b), samt nødvendige privacy notices/samtykker. Dette er en manuell drifts-/avtalegate, ikke en ny API- eller samtykkemotor.

Nginx-konfigurasjonen i repoet setter `client_max_body_size 16m`. Det gir nødvendig proxy-headroom for applikasjonens maksimale kildefil på 15 MiB og multipart-overhead. Fase 3D.2 gjenbruker de eksisterende persistente `image_originals_private`-/`image_renditions_public`-aliasene, Borg-backupen og `cleanup_image_storage_orphans`; den endrer ingen storage-root, backupkontrakt eller cleanup-semantikk.

En fersk, grønn Borg-backup er obligatorisk før stagingdeploy av migrasjon `0028`. Leveransen endrer ikke PUBLIC-flyt, oppretter ingen public release og aktiverer ingenting i produksjon.

Precision/zoom-runtimecommit `3686f08` ble deployet kontrollert 2026-08-11 etter grønt Borg-arkiv `kreative-norge-staging-20260811T081243Z`. Bare API og deretter web ble rekreert; database, volum og media ble ikke rekreert. Migrasjon `0028`, historisk zoomdefault, faktisk 150 % zoomprocessing, private previews, storagechecksums og orphan-dry-run var grønne. Ekstern curl ble møtt av en eksplisitt Cloudflare-browserchallenge, mens lokal origin var grønn. Prosjekteier har senere fullført vanlig nettlesersmoke og visuelt godkjent precision/zoom-, Foto/Logo-, blank-alt- og live/server-previewreisen. Se [datert stagingevidens](../status/STAGING_IMAGE_SOURCES_2026-08-11.md).

`cleanup_image_storage_orphans` gir en begrenset dry-run-first cleanup for de to bildealiasene. Apply krever PostgreSQL, validerte lokale roots og eksplisitt operatørvalg, revaliderer databasereferanser under lås og sletter bare gamle, urefererte regulære filer. Den er ikke en generell retention- eller public purge-mekanisme.

## Backupgrunnmur

Repoet har en generisk modul under `ops/backup/` for nattlig, kryptert Borg-backup til en separat Hetzner Storage Box:

- PostgreSQL custom-format dump med `pg_restore --list`
- eksisterende import-, rapport- og eksportfiler når de finnes
- eksplisitt allowlistede host-mediaområder når de finnes; nye områder må legges til og restore-verifiseres før aktivering
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
