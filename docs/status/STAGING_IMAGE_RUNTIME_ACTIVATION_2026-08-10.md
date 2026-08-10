# Stagingaktivering av fase 3D.1 – 2026-08-10

**Status:** Teknisk gjennomført; prosjekteiers manuelle visuelle gate gjennomført

## Omfang

Leveransen aktiverer den eksisterende interne fase 3D.1-flyten i staging med host-persistente bildeområder. Den endrer ikke PUBLIC, public release, canonical `releases/...`-materialisering eller offentlig serving.

Kodekontrakten beholder `IMAGE_ASSET_FEATURE_ENABLED=False` som sikker standard. Bare den ignorerte staging-environmentfilen har flagget eksplisitt satt til `True` etter at persistence-, backup- og restore-gatene var grønne.

Implementasjonen ligger på `feature/phase3d1-staging-runtime`:

- `9648c3e536168771938b6a51247a42ed92edaeb2` etablerer runtime, runbook, probe og orphan-cleanup
- `d32add6d74215897369891fe6e62536a75a58c78` retter case-insensitiv bytes-sniffing av HTML i official discovery

## Implementert runtime

- private originaler bind-mountes én-til-én på `/srv/kreative-norge/media/private`
- interne renditions bind-mountes én-til-én på `/srv/kreative-norge/media/public`
- mountene finnes bare i API-containeren; `web` eksponerer eller serverer ikke media
- root-katalogene opprettes kontrollert som `root:root` mode `0750`, og symlinkkomponenter avvises
- `.env.staging.example` dokumenterer eksplisitte roots og beholder flagget avslått
- stagingrunbooken beskriver forberedelse, persistence-probe, backup/restore, aktivering og rollback

Minimal orphan-cleanup er implementert som dry-run-first management command. Den krever eksplisitte lokale roots, avviser symlinks og spesialfiler, blokkerer sletting når database-refererte filer mangler og revaliderer referanser under PostgreSQL-lås før `--apply`. Standard minstealder er 24 timer. Den sletter bare kvalifiserte, urefererte regulære filer og fjerner aldri kataloger.

Review-hardening i PR #32 serialiserer storage→database-vinduet mot destruktiv cleanup. Ingest tar en delt PostgreSQL transaction-level advisory lock før første immutable write/reuse og holder den gjennom aggregatecommit eller rollback. Cleanup apply tar samme lock eksklusivt før siste planskanning, tabellås og sletting; dry-run blokkerer ikke ingest. Sletting traverserer storage-root og alle katalogkomponenter descriptor-relativt med `O_DIRECTORY` og `O_NOFOLLOW`, kontrollerer sluttobjektet som regulær fil og bruker relativ unlink fra den åpne parent-fd-en. En deterministisk to-connection-test observerer cleanup ventende på advisory-låsen mens ingest er pauset etter storage og før DB-commit. En separat swap-test viser at en katalog som byttes til symlink etter scan stopper slettingen uten å berøre filen utenfor alias-rooten.

## Lokal verifikasjon

- hele backendpakken gjennom Django discovery: 336 tester grønne
- berørte processing-/ingest-/candidate-/runtime-/cleanup-tester: 64 tester grønne
- stagingkontrakter: 3 tester grønne med strukturell YAML-kontroll av service-spesifikke mounts
- `bash -n` og ShellCheck 0.10.0 av staging-scriptet grønne
- frontend: 15 tester og produksjonsbuild grønne
- runtime-/backupkontrakttester grønne
- backend- og web-images bygget som produksjonscontainere
- en deterministisk PNG-probe ble skrevet gjennom begge storagealiasene, funnet med samme checksum på hosten, lest fra en ny API-container med feature avslått og fjernet eksakt

## Staginggate

Staging ble oppdatert fra ren baseline. Før runtimeendringen ble arkivet `kreative-norge-staging-20260810T182419Z` opprettet. API- og web-images ble bygget, migrasjonene `0021`–`0026` ble kjørt additivt, og Django system check, PostgreSQL og samme-origin smoke for `/`, `/api/auth/session/` og `/public/actors/` var grønne.

Persistence-proben brukte token `75158fd0ae41c97e4106336b4817c4a3`. Original og rendition hadde SHA-256 `aa7bb0431aaeb198a77c26a14fe6dd714a75e4d7db94e3e1238a1fdcbfe1f8d4` før og etter kontrollert API-recreate. Arkivet `kreative-norge-staging-20260810T182952Z` bestod full repository-verifikasjon og isolert restore-smoke, og eksakt uttrekk av proben fra Borg-arkivet hadde samme checksum. Proben ble deretter fjernet gjennom den eksplisitte cleanup-ruten.

Stagingflagget ble først aktivert etter denne gaten. Innstillinger, storagealiaser og orphan dry-run ble kontrollert i den nye API-containeren.

Docker Compose 1.29.2 traff den kjente `ContainerConfig`-feilen ved recreate. Gjenopprettingen ble avgrenset til den eksakte stoppede API-containeren, som ble fjernet og opprettet på nytt. Tilsvarende kontrollert stop/remove/create ble brukt for den stateless web-containeren. Runtime og data var grønne etterpå, men den gamle Compose-versjonen er en åpen driftsrisiko.

## Faktisk fase 3D.1-reise

En autentisert stagingreise mot én eksisterende organisasjon verifiserte:

- official discovery returnerte seks dedupliserte kandidater
- kandidat-preview returnerte privat `no-store`-innhold
- fotoprosessering av logoen ble korrekt avvist med `upscale_required`
- logoprosessering opprettet ett asset og ett komplett rendition-sett
- square-, landscape- og share-preview svarte `200`
- eksplisitt approval opprettet aktiv selection revisjon 1 og ett review-event
- alle tre storageobjektene kunne leses gjennom aliasene med forventede checksums
- ingen public release ble opprettet

Arkivet `kreative-norge-staging-20260810T183823Z` inneholder den faktiske private originalen. Full backupverifikasjon og isolert restore-smoke var grønne, og eksakt Borg-uttrekk matchet database-checksummen `4a5ddc59b8ddfa60fcf7ead596952db15944ec4e38e1602addec50cfc40767a1`. Etter en ny kontrollert API-recreate var aktiv selection, alle previews og storagechecksums fortsatt grønne.

Den eksisterende Playwright-reisen dekker første låsing, men ikke replacement. Replacement er derfor ikke mutert i staging i denne leveransen; backendtestene dekker kontrakten.

## Prosjekteiers manuelle visuelle gate

Prosjekteier gjennomførte den visuelle kontrollen etter den tekniske aktiveringen:

- Parkenfestivalen: official discovery fungerte, logo ble valgt, Logo/contain fungerte, og prosessering og visning så riktig ut
- Bodø Bluesklubb: official discovery fungerte, Foto ble valgt, og no-upscale-gaten ble utløst for et for lite bilde; dette ble vurdert som forventet kvalitetsbeskyttelse, ikke runtimefeil

Den manuelle visuelle gaten for Leveranse 2 er dermed gjennomført. Norske processingfeil, fokusforvalg, live Foto-crop, valgfri alt-tekst, Brave/generelt søk, limt URL og manuell upload er besluttet for fase 3D.2 og er ikke implementert her.

## Nåstatus og åpne grenser

- staging: `IMAGE_ASSET_FEATURE_ENABLED=True`
- kode/default og `.env.staging.example`: `False`
- private originaler og interne renditions er host-persistente og dekkes av aktiv Borg-backup
- PUBLIC, public release, public projection og offentlig media-serving er uendret
- default storage for import-/eksport-/rapportfiler er fortsatt ikke host-persistent
- permanent reservation-/deny-journal, retentionpolicy, public cache/purge og full katastrofe-RTO gjenstår
- ordinær PR-review/merge gjenstår
