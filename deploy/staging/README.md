# Staging deploy

This is a small same-origin staging setup for the CRM:

- `db`: PostgreSQL
- `api`: Django + Gunicorn
- host-level Caddy terminates HTTPS
- `web`: nginx serving the built frontend and proxying `/api/`, `/admin/`, and `/public/`

Because the frontend and API share the same origin, Django session auth and CSRF are simpler to operate.

On the current staging server, Caddy listens publicly for `staging.northernsound.no` and reverse-proxies to `127.0.0.1:8080`. The `web` container therefore binds `127.0.0.1:8080:80`; it must not bind public port `80`, because Caddy owns that port.

## 1. Prepare the server

Install:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER
```

Log out and in again after adding your user to the `docker` group.

## 2. Clone the project

```bash
sudo mkdir -p /srv/kreative-norge-crm
sudo chown $USER:$USER /srv/kreative-norge-crm
git clone <your-repo-url> /srv/kreative-norge-crm
cd /srv/kreative-norge-crm
```

## 3. Create the staging env file

```bash
cp .env.staging.example .env.staging
```

Then edit `.env.staging` with your real domain, secret key, and database password.

Minimum values:

```env
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=...
DJANGO_ALLOWED_HOSTS=staging.your-domain.no
DJANGO_CSRF_TRUSTED_ORIGINS=https://staging.your-domain.no
DB_NAME=crm_db
DB_USER=crm
DB_PASSWORD=...
IMAGE_ASSET_FEATURE_ENABLED=False
IMAGE_ORIGINALS_ROOT=/srv/kreative-norge/media/private
IMAGE_RENDITIONS_ROOT=/srv/kreative-norge/media/public
PUBLIC_IMAGE_DELIVERY_ROOT=/srv/kreative-norge/media/public-delivery
PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=False
PUBLIC_IMAGE_SERVING_ENABLED=False
PUBLIC_IMAGE_PROJECTION_ENABLED=False
PUBLIC_IMAGE_API_SCHEMA_ENABLED=False
PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=False
PUBLIC_SITE_ORIGIN=https://staging.your-domain.no
PUBLIC_MEDIA_ORIGIN=https://staging.your-domain.no
PUBLIC_IMAGE_SAFETY_BRIDGE_SOCKET=/run/kreative-norge-image-safety/bridge.sock
PUBLIC_IMAGE_SAFETY_BRIDGE_TIMEOUT=50
BRAVE_IMAGE_SEARCH_API_KEY=
VITE_API_BASE=
```

Keep `IMAGE_ASSET_FEATURE_ENABLED=False` until the persistence and Borg gates below are green. The two image roots are still required explicitly so the same Compose configuration can be verified before activation.

`BRAVE_IMAGE_SEARCH_API_KEY` is optional and server-side only. On staging, install an existing valid credential directly in the ignored `/srv/kreative-norge-crm/.env.staging`; never put it in Git, chat, a PR, `.env.staging.example`, a `VITE_` variable, frontend build argument, browser/API response, command output, or logs. Recreate only `api`, and verify only `configured`/`missing`, never the value. If it is empty, Brave search returns the controlled `503` code `brave_not_configured`. The live staging gate on 2026-08-11 verified 30 real candidates, private original preview, secure fetch and processing with `search_lang=nb`; the credential value was never emitted. After preserving that evidence, the credential was intentionally cleared and only `api` was recreated. Staging now reports `brave_configured=False` and controlled `brave_not_configured`: live verification remains **PASS**, but current operational activation is **NOT ACTIVE**. Do not reactivate Brave for ordinary Editor end users until the contract owner has documented compliance with the written End User agreement requirement in the current [Brave Search API Terms](https://api-dashboard.search.brave.com/documentation/resources/terms-of-service) section 4(c), including obligations substantially similar to section 3(b), and any required privacy notices/consents under the current [Privacy Policy](https://api-dashboard.search.brave.com/privacy-policy). This is a manual operational gate; this runbook does not introduce a consent or terms engine.

Phase 3D.2 does not change the existing `image_originals_private` or `image_renditions_public` storage aliases, host-persistent roots, Borg coverage, or dry-run-first orphan cleanup. It activates no PUBLIC image release or production behavior.

## 4. Prepare image storage

Run the repository-owned setup as root before the first image-capable API container is created:

```bash
sudo /srv/kreative-norge-crm/ops/staging/prepare-image-storage.sh
```

It creates only these host-persistent directories and enforces `root:root` mode `0750` without recursively changing or deleting existing image bytes:

- `/srv/kreative-norge/media/private`
- `/srv/kreative-norge/media/public`
- `/srv/kreative-norge/media/public-delivery`

The current API image runs as root and can write both directories. The root-run Borg service can read them. If the API later becomes non-root, ownership must be changed through a separate controlled delivery; do not broaden these modes ad hoc.

`public` is the historical storage-alias name for internal processing renditions. `public-delivery` er den separate, fortsatt ueksponerte release-roten. Ingen av dem er montert i `web` eller servert av nginx/Caddy.

## 5. Start staging

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d --build
```

The repository compose file binds the web container to `127.0.0.1:8080:80`.

The repository nginx configuration sets `client_max_body_size 16m`. This is intentional headroom for the application limit of a 15 MiB source image plus multipart framing. Keep the proxy limit above the application limit; do not raise either limit ad hoc during deploy.

## 6. Create an admin user

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec api python manage.py createsuperuser
```

## 7. Verify the deployment

Check:

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging ps
docker-compose -f docker-compose.staging.yml --env-file .env.staging logs --tail=100 api
docker-compose -f docker-compose.staging.yml --env-file .env.staging logs --tail=100 web
```

Then open:

- `https://staging.northernsound.no/`
- `https://staging.northernsound.no/api/auth/session/`
- `https://staging.northernsound.no/public/actors/`
- `https://staging.northernsound.no/admin/`

## 8. HTTPS

The compose setup serves HTTP only on localhost port `8080`.

Caddy terminates HTTPS and must forward:

- `Host`
- `X-Forwarded-Proto https`

Nginx inside the `web` container must pass the incoming `X-Forwarded-Proto` header onward to Django for `/api/`, `/admin/`, and `/public/`. That matches Django's `SECURE_PROXY_SSL_HEADER` setting and prevents HTTPS redirect loops.

## 9. Updating staging

Take and verify a fresh Borg backup before pulling or rebuilding a phase 3D.2 staging deploy:

```bash
sudo systemctl start kreative-norge-backup.service
sudo systemctl status kreative-norge-backup.service --no-pager
```

Stop before deploy if the backup is not green. A successful backup does not by itself verify Brave configuration or the 3D.2 user journey.

```bash
git pull
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d --build
docker-compose -f docker-compose.staging.yml --env-file .env.staging ps
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec -T api python manage.py check
```

## 10. Image persistence and activation gate

For the first image-runtime activation, keep the feature off and take a fresh backup before the deploy/recreate:

```bash
sudo systemctl start kreative-norge-backup.service
sudo systemctl status kreative-norge-backup.service --no-pager
```

After deploying the image-runtime code with the feature still off, generate a 32-character lowercase hexadecimal token and write the controlled PNG probe through the existing Django storage primitive in a one-off container:

```bash
PROBE_TOKEN=$(python3 -c 'import secrets; print(secrets.token_hex(16))')
docker-compose -f docker-compose.staging.yml --env-file .env.staging run --rm \
  -e IMAGE_ASSET_FEATURE_ENABLED=True api \
  python manage.py verify_image_storage_persistence --write --token "$PROBE_TOKEN"
```

Verify both host files against the checksum printed by the command. The exact relative keys are also printed, so no broad filesystem search is needed:

```bash
sha256sum \
  "/srv/kreative-norge/media/private/runtime-probes/$PROBE_TOKEN/original.png" \
  "/srv/kreative-norge/media/public/runtime-probes/$PROBE_TOKEN/rendition.png"
```

Recreate only the API container while the staging feature remains off, then read the same bytes through both storage aliases:

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d --no-deps --force-recreate api
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec -T api \
  python manage.py verify_image_storage_persistence --verify --token "$PROBE_TOKEN"
```

Stop if the server's known Compose 1.29.2 `ContainerConfig` failure appears. Do not remove or recreate unrelated containers as an implicit workaround.

With the probe still present, run a fresh Borg backup and the isolated restore gate. The backup manifest records a path token and checksum for one representative host-media file; restore must locate the same archive member and verify byte identity:

```bash
sudo systemctl start kreative-norge-backup.service
sudo /usr/local/lib/kreative-norge-backup/verify.sh
sudo BACKUP_ENV_FILE=/etc/kreative-norge-backup/backup.env \
  /usr/local/lib/kreative-norge-backup/restore-smoke.sh
```

Only after all three gates are green, remove the exact probe and change only the actual server's ignored `.env.staging` to `IMAGE_ASSET_FEATURE_ENABLED=True`:

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec -T api \
  python manage.py verify_image_storage_persistence --cleanup --token "$PROBE_TOKEN"
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d --no-deps --force-recreate api
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec -T api python manage.py check
```

The code/default and `.env.staging.example` stay `False`; production must not be activated by this procedure.

## 11. Minimal orphan cleanup

Database failure after immutable storage writes can leave unserved orphan bytes. The command is never scheduled and is dry-run by default:

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec -T api \
  python manage.py cleanup_image_storage_orphans
```

It requires both roots explicitly in the environment, accepts only local `FileSystemStorage`, refuses missing database-referenced files, symlink components, symlinks inside either root, special filesystem entries, invalid keys and root/backend mismatches. Files younger than 24 hours are excluded by default. Apply takes the exclusive form of the same transaction-level PostgreSQL advisory lock held in shared mode by ingest from before storage write/reuse through database commit. It then holds PostgreSQL `SHARE` locks on both reference tables while rebuilding the plan. Deletion opens the configured root and each key component descriptor-relatively with no-follow and unlinks only a verified regular filename relative to its opened parent directory. Deletion requires an explicit operator action:

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec -T api \
  python manage.py cleanup_image_storage_orphans --apply --minimum-age-hours 24
```

This is only reference-aware orphan cleanup. It is not retention, takedown, release purge or automatic scheduling.

## 12. Roll back image runtime activation

Rollback disables the Editor flow; it does not roll back or delete image assets. First record current `ImageAsset`, `ImageRendition` and `OrganizationImageRelease` counts and run the orphan command in dry-run mode. Set only `IMAGE_ASSET_FEATURE_ENABLED=False` in the ignored `.env.staging`. Keep `IMAGE_ORIGINALS_ROOT` and `IMAGE_RENDITIONS_ROOT` unchanged, and do not remove either host directory or any media bytes.

Because the current server has Docker Compose 1.29.2 and has previously hit the `ContainerConfig` recreate error, recreate only API in a controlled sequence. Do not remove database, web, volumes or media:

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging stop api
docker-compose -f docker-compose.staging.yml --env-file .env.staging rm -f api
docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d --no-deps api
docker-compose -f docker-compose.staging.yml --env-file .env.staging exec -T api python manage.py check
```

Then verify:

1. Django reports `IMAGE_ASSET_FEATURE_ENABLED=False` inside API.
2. `/`, `/api/auth/session/` and `/public/actors/` return the expected successful responses over HTTPS.
3. An authenticated Organization Editor no longer shows the `Aktørbilde` flow.
4. Database counts match the recorded pre-rollback counts.
5. `cleanup_image_storage_orphans` dry-run is green, which proves every DB-referenced original and rendition is still present. Do not use `--apply` during rollback.
6. Previously recorded representative media checksums still match on the host. No public release is created or deleted by rollback.

The Compose 1.29.2 `ContainerConfig` behavior remains a separate operational risk. Stop if the exact API-only sequence fails; do not broaden removal as an implicit workaround. Upgrading Compose is outside this delivery.

## Notes

- `api` runs `migrate` and `collectstatic` on startup.
- Frontend is built into the nginx image at deploy time.
- Static files are shared from Django to nginx through the `django_static` volume.
- Image originals and internal renditions use separate host bind mounts outside `/app` and outside staticfiles.
- For contact-data repairs, run `python manage.py repair_person_contacts` as dry-run first. Use `--apply` only after backup and explicit approval.

## 13. Fase 3E.1A safety-ledger – ACTIVE i staging

Public image safety-ledgeren installeres på hosten, ikke i Compose:

```bash
sudo /srv/kreative-norge-crm/ops/image_safety/install.sh prepare
```

Ledgeren ligger i `/var/lib/kreative-norge-image-safety/ledger.sqlite3`. Konfigurasjon og restricted writercredential ligger under `/etc/kreative-norge-image-safety/`. Ingen av pathene er montert i `api` eller `web`; Borg installeres ikke i images. `prepare` aktiverer fortsatt ingen unit eller timer alene.

Ikke kjør `init` mot den eksisterende generelle backup-repositoryen. Staging bruker et dedikert safety-subaccount/repository, separat recovery-custody og aktiv health-timer etter fullført capability-/transaction-recovery-/restartgate 2026-08-20. Se [safety-runbooken](../../docs/operations/PUBLIC_IMAGE_SAFETY_LEDGER.md) og [aktiveringsevidensen](../../docs/status/STAGING_PHASE_3E1A_ACTIVATION_2026-08-20.md). `ACTIVE` gjelder bare 3E.1A; public runtime forblir av.

## 14. Fase 3E.1B – materialisering aktiv; serving senere aktivert i 3E.1C

Systemd socket/service, API-only runtime-/delivery-mounts og aktiv backupallowlist for 3E.1B er deployet og liveverifisert i staging fra 2026-08-23. Den ignorerte stagingkonfigurasjonen har etter separat aktiveringsgate `PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=True`; kode- og eksempelstandard forblir `False`.

Staginggaten har verifisert tom release-tabell før migrasjon `0029`; root-eid socket `0600`; faktisk `SO_PEERCRED` fra API-containeren; ingen socket/delivery/ledger/Borg i `web`; ingen ledger eller Borg-credential i API; 5/45/50/60-sekunders timeoutkjede; delivery-persistens gjennom API-recreate; og identiske delivery-bytes i ny backup og isolert restore. Se [datert evidens](../../docs/status/STAGING_PHASE_3E1B_FOUNDATION_2026-08-23.md).

Den separate aktiveringsgaten har i tillegg bevist faktisk reserve → DB-binding → create-only/read-back → activate, ephemeral hard no-clobber-konflikt, recovery etter kontrollert krasj med én fil og API-restart samt full idempotent retry. Én permanent syntetisk release for en upublisert stagingaktør beholdes som evidens. Se [aktiveringsrapporten](../../docs/status/STAGING_PHASE_3E1B_MATERIALIZATION_ACTIVATION_2026-08-23.md).

Ved avslutningen av 3E.1B var ingen Nginx-route, media-alias, projection eller offentlig HTTP-serving aktivert. 3E.1C aktiverte senere den kontrollerte release-ruten separat. Fase 3E.2 har nå shadow-aktivert projection i staging mens API-schema og PUBLIC-forbruk fortsatt er av. Ikke kopier eksempelverdier over aktiv stagingkonfigurasjon ved ordinær deploy; flaggendring eller rollback er en eksplisitt operatørhandling, og permanente reservations-/activationevents eller releasefiler slettes aldri som rollback.

## 15. Fase 3E.1C – separat kontrollert servinggate

3E.1C deployes først fra eksakt grønn mergecommit med `PUBLIC_IMAGE_SERVING_ENABLED=False`. Sett samtidig faktiske, eksplisitte HTTPS-verdier for `PUBLIC_SITE_ORIGIN` og `PUBLIC_MEDIA_ORIGIN`; hosten må finnes som eksakt ikke-wildcardverdi i `DJANGO_ALLOWED_HOSTS`. Kjør `ops/staging/prepare-image-storage.sh` for å etablere den kollisjonssjekkede delivery-gruppen med GID `2000`, setgid-directories og `0640`-filer. Installer deretter oppdatert hostkode med `ops/image_safety/install.sh prepare`, restart bridge-service/socket kontrollert, og rebuild/recreate `api` og `web` slik at supplementary group, read-only deliverymount og Nginx-konfigurasjon faktisk er ny. Verifiser før aktivering:

- safety health er `READY`, systemd-socketen er `root:root` `0600`, og API-peer passerer `SO_PEERCRED`
- API har bare socket-runtime read-only og delivery read/write; web har bare delivery read-only med supplementary GID `2000` og ingen socket, artifacts, private filer, ledger, `/etc`-secret eller Borg; kontroller faktisk Nginx-worker under `/proc/<pid>/status` og krev at `Groups` inneholder `2000` etter privilegiedroppet
- ekstern canonical media-URL gir `404` med serving av, og direkte `/_protected-public-image/...` kan ikke nås eksternt
- Nginx-konfigurasjonen har Django-proxy for `/media/releases/`, `internal` delivery-location, `etag off`, eksplisitt `ETag` fra `$upstream_http_etag`, `autoindex off`, `disable_symlinks on` og ingen shared `proxy_cache`; dette gjelder bare den interne filhandleren og bevarer Djangos checksum-ETag i stedet for Nginx-filmetadata

Etter grønn preflight settes bare `PUBLIC_IMAGE_SERVING_ENABLED=True`, og API rekreeres. Bruk én publisert staging-Organization med aktiv komplett selection og kjør den støttede release-workflowen ved behov. Livegaten skal bevise:

- canonical `GET` og `HEAD` for alle tre varianter med korrekt type, lengde, checksum-`ETag`, `private, max-age=60, must-revalidate`, validert `If-None-Match` → `304` og identiske bytes som delivery-filen
- ukjent/malformed release, variant-/extension-/scopefeil, upublisert Organization og negativ safety-state gir `404` uten bytes og med `no-store`
- alle ikke-canonical former under `/media/releases/` går til en tom `404/no-store`-catch-all uten DB-, bridge- eller storagekall; canonical-viewen er CSRF-unntatt bare for at dens write-frie GET/HEAD-metodegate skal gi `405/no-store` før domenekall
- stoppet/utilgjengelig bridge og manglende/korrupt fil gir `503` uten bytes og med `no-store`; bridge restart gjenoppretter serving
- vilkårlig `Host`/`X-Forwarded-Host` endrer ikke canonical URL-bygging, intern location er fortsatt utilgjengelig, og logger viser bare strukturert utfall/release-ID/variant/status/cursor/tid uten filesystempath eller secrets
- API-, web- og bridge-restart bevarer resultatet, og PUBLIC HTML/API/legacyaliaser er uendret

Ved hvilket som helst gateavvik: sett `PUBLIC_IMAGE_SERVING_ENABLED=False`, rekreer API, bekreft `404` på media-ruten og behold ledger-, DB- og delivery-state urørt. Ikke aktiver 3E.2, projection, API/PUBLIC eller takedown som del av denne gaten.

**Aktiv stagingstatus 2026-08-24:** 3E.1C-gaten er gjennomført fra eksakt merge `38663b5`, og den ignorerte stagingverdien er `PUBLIC_IMAGE_SERVING_ENABLED=True`. HTTP/cache, negative svar, bridge-/filfeil, origins, logger, mountisolasjon, restart og backup/restore er grønne. Se [aktiveringsrapporten](../../docs/status/STAGING_PHASE_3E1C_ACTIVATION_2026-08-24.md). 3E.2 projection-shadow er senere aktivert separat på merge `90ff5e9`; API-schema, PUBLIC, legacy-cutover og takedown er fortsatt av.

## 16. Fase 3E.2 – separat projection/API-shadowgate

Deploy bare eksakt reviewet og grønn mergecommit. Behold først:

```text
PUBLIC_IMAGE_PROJECTION_ENABLED=False
PUBLIC_IMAGE_API_SCHEMA_ENABLED=False
```

Rebuild/recreate bare nødvendige `api`/`web`-tjenester; web må få de versjonerte tekniske fallbackfilene gjennom `collectstatic`-volumet. Før projection aktiveres skal API list/detail, PUBLIC HTML, Editor, OpenAPI, safety `READY` og controlled media være grønne. Sammenlign `/api/public/actors/` byte-/JSON-kontrakt og representative detailresponser med pre-deploy-baselinen. PUBLIC skal være visuelt og datamessig uendret.

Aktiver deretter bare:

```text
PUBLIC_IMAGE_PROJECTION_ENABLED=True
PUBLIC_IMAGE_API_SCHEMA_ENABLED=False
```

Recreate `api`, bekreft de faktiske flaggverdiene og kjør fullkatalog-auditen:

```bash
docker-compose -f docker-compose.staging.yml --env-file .env.staging \
  exec -T api python manage.py audit_public_image_projection
```

Evidensen skal registrere aggregert JSON med publisert antall, asset/fallback, reasons, safety unavailable/scope mismatch, legacydiff, authorize count, query count og runtime. Verifiser i tillegg at den aktive publiserte evidensreleasen gir `asset`, at alle tre projected release-URL-er matcher canonical controlled media, at teknisk fallback finnes på alle tre versjonerte static-URL-er, og at et kontrollert bridgeavvik gir projection-fallback uten å endre anonymous legacyresponse. Kontroller API/PUBLIC-responsen mot baseline på nytt og verifiser at safety cursor/events, PostgreSQL-radantall, deliveryfiler og checksums er uendret av GET/audit.

`PUBLIC_IMAGE_API_SCHEMA_ENABLED` skal forbli `False`; target-schemarespons, PUBLIC-cutover og 3E.3 inngår ikke i gaten. Ved enhver response-/PUBLIC-/safetyregresjon: sett projectionflagget tilbake til `False`, recreate bare `api`, verifiser baseline og behold serving, ledger, release-DB og delivery urørt. Dersom rollback ikke gjenoppretter baseline, stopp deployen og bruk forrige eksakte mergecommit uten å slette database, media, ledger eller volume.

**Gjennomført 2026-08-24:** Eksakt merge `90ff5e9` ble deployet etter grønn backup og isolert restore. Off/off-baseline, canonical route, fullkatalog `122 = 1 asset + 121 fallback`, alle seks asset-/fallback-HEAD-kall, unpublished-adferd, sanitert logg, performance og uendret API/PUBLIC/safety/DB/delivery var grønne. Projection står `True` i ignorert stagingkonfigurasjon; schema står `False`. En kontrollert operatørverktøyfeil utløste og beviste API-only rollback før korrigert rerun. Se [datert evidens](../../docs/status/STAGING_PHASE_3E2_SHADOW_2026-08-24.md).

## 17. Fase 3E.3 – separat API/PUBLIC/head-cutovergate

Deploy bare eksakt reviewet mergecommit etter grønn main-CI og fersk, fullverifisert backup. Behold først den aktive 3E.2-tilstanden og den nye gaten av:

```text
PUBLIC_IMAGE_PROJECTION_ENABLED=True
PUBLIC_IMAGE_API_SCHEMA_ENABLED=False
PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=False
```

Rebuild/recreate nødvendige `api`/`web`-tjenester fra den eksakte commiten. Registrer før-state for Git-head, containerimages, flagg, safety health/cursor, publisert antall, release-/selection-/renditionrader, deliverymanifest/checksummer og fullkatalog-audit. Verifiser at API/OpenAPI og PUBLIC HTML fortsatt følger 3E.2-legacykontrakten, at legacydetailredirecten virker og at de tre canonical production fallback v1-filene kan hentes fra `/static/crm/public-image-fallback/v1/fallback-{square,landscape,share}.png`. Kontroller fallbackgrafikken visuelt på desktop og mobil før cutover.

Aktiver deretter bare targetschemaet:

```text
PUBLIC_IMAGE_API_SCHEMA_ENABLED=True
PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=False
```

Recreate bare `api` og bekreft faktiske settings. Verifiser public API list/detail og OpenAPI: eksakt `image`-schema, `asset|system_fallback`, tre dimensjoner, absolutte configured-origin-URL-er og invarianten `thumbnail_image_url == preview_image_url == image.square.url`. API-responsen skal ikke inneholde legacybilde eller intern tenant-/selection-/artifact-/checksum-/safetyinformasjon.

Bevis schema-rollback før PUBLIC aktiveres: sett `PUBLIC_IMAGE_API_SCHEMA_ENABLED=False`, recreate `api`, og krev at API/OpenAPI er tilbake på byte-/semantisk legacybaseline mens projection, safety, DB og delivery er uendret. Sett deretter schemaflagget tilbake til `True`, recreate `api` og gjenta targetkontrakten grønt.

Aktiver til slutt bare:

```text
PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=True
```

Recreate `api`, bekreft hele flaggkjeden og verifiser:

- samme asset/fallback-decision i API, PUBLIC list/detail og head; square i kort/hero og share 1200 × 630 i Open Graph/Twitter
- canonical fra `PUBLIC_SITE_ORIGIN` + faktisk `reverse()`-route, base-list canonical også med filter/query, og invarians ved manipulert `Host`/`X-Forwarded-Host`/`X-Forwarded-Proto`
- godkjent asset-alttekst/kreditering, blank systemfallback-alt og én-gangs asset-bytefeil til static square-fallback med blank slutt-alt uten legacyoppslag
- faktisk asset og representative fallbackkort/detail på desktop og mobil, mange fallbackkort, lange navn/tags/kommuner og fravær av overlap/overflow/broken layout
- denied/retired/unknown, stoppet bridge og relevant scopefeil gir systemfallback i API/PUBLIC/head uten metadata- eller legacy-lekkasje; reaktivert bridge gjenoppretter asset
- API/PUBLIC list/detail query-/authorizeprofil uten N+1 og akseptabel responstid sammenlignet med 3E.2-baseline
- safety cursor/events, PostgreSQL-radantall, deliveryfiler/checksummer og backupstate er uendret av read-only schema-/PUBLIC-gaten

Ved avvik: sett først `PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=False`, recreate `api` og krev full visuell/semantisk legacyrollback. Ved API-kontraktavvik settes også `PUBLIC_IMAGE_API_SCHEMA_ENABLED=False` og API recreates. Behold projection, serving, ledger, release-DB, deliveryfiler og gamle emergency-fallbackfiler; slett eller omskriv ingen state. Dersom rollback ikke gjenoppretter baselinen, stopp og deploy forrige eksakte mergecommit. Dokumenter eksakt implementation merge, målinger og før/etter/rollback i en separat evidens-PR. Stopp før 3E.4, deny/retire/purge eller legacyopprydding.
