# Staging – fase 3E.3 API/PUBLIC/head-cutover 2026-08-24

**Status:** `CLOSED / ACTIVE`

## Kontrollpunkt

- Start-`main`: `5d0acc444c5746cc999179dfa242983b7676a963`
- Implementerings-PR: #49, reviewet head `dea89a75af3bafa31c21f2c1de4e44287d89eeac`
- Første implementation merge: `cbbad65b087521cebcdcd78e5270628eeb11180f`
- Aktiveringsblocker-fix: PR #50, reviewet head `080aebe5197a6b42e13365f9aa9156b286e5f8af`
- Endelig deployet merge: `e04220b783c8d572846de595e1ce955c85bd30ed`; post-merge CI-run `32735523645` var 6/6 grønn
- Migrasjon: fortsatt `0029_release_selection_revision_gate`; ingen 3E.3-migrasjon
- Verifisert predeploy-backup: `kreative-norge-staging-20260824T131620Z`, full repository-verifikasjon og isolert restore-smoke grønn

PR #49 hadde seks grønne CI-jobber og en separat full review med null funn på den endelige headen. Post-merge-CI på `cbbad65b` var grønn. Den siste ytelsesgaten fant deretter en eksisterende N+1 i public API-personserialiseringen: 299 SQL-spørringer for 122 aktører. Gatene ble automatisk slått av. PR #50 erstattet de lineære person-/kontaktspørringene med to faste prefetcher, la inn en skalerende regresjonstest, fikk seks grønne CI-jobber og en separat review med `0 BLOCKER`, `0 HIGH`, `0 MEDIUM` og `0 LOW`. Endelig stagingdeploy bruker merge `e04220b`.

## Aktiv sluttkonfigurasjon

```text
PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=True
PUBLIC_IMAGE_SERVING_ENABLED=True
PUBLIC_IMAGE_PROJECTION_ENABLED=True
PUBLIC_IMAGE_API_SCHEMA_ENABLED=True
PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=True
PUBLIC_SITE_ORIGIN=https://staging.northernsound.no
PUBLIC_MEDIA_ORIGIN=https://staging.northernsound.no
```

Kode- og eksempelstandardene er fortsatt `False`. Stagingverdiene er eksplisitte, ignorerte driftsverdier. PUBLIC-gaten krever projection, targetschema, controlled serving og gyldige origins og feiler lukket ved ugyldig kombinasjon.

## Baseline, schema og rollback

Før aktivering ble eksakt deploy med begge nye gater av kontrollert mot før-deploy-baseline:

- public API list/detail og OpenAPI var byteidentiske med legacybaselinen
- PUBLIC list/detail var semantisk identisk etter normalisering av den eksisterende tilfeldige tagrekkefølgen
- legacy detaljredirect, kontrollert media og alle production fallback v1-staticfiler svarte korrekt
- production fallback v1 var byteidentisk mellom repository, collected static og de bevarte emergency-filene
- safety health/cursor, databaseantall og deliverymanifest var uendret

Schema ble deretter kjørt `OFF → ON → OFF → ON`. Med schema på hadde API-et det strukturerte `image`-objektet, og `thumbnail_image_url`/`preview_image_url` var aliaser til samme `image.square.url`. Rollback gjenopprettet eksakt legacy API/OpenAPI uten å endre ledger, database eller deliveryfiler. Reaktivering ga samme targetrespons byte-for-byte.

PUBLIC ble kjørt `OFF → ON → OFF → ON` etter grønn schema-gate. Full rollback av begge nye flagg gjenopprettet legacy API, PUBLIC og head. Reaktivering gjenopprettet samme targetprojection. Alle feil i operatørskriptene og ytelsesblockeren utløste den samme automatiske flags-off-rollbacken; ingen sikkerhets-, release- eller delivery-state ble slettet eller omskrevet.

## Aktiv API/PUBLIC/head-kontrakt

Den publiserte assetaktøren var Nordnorsk Jazzsenter, organisasjonsnummer `980445895`, PUBLIC-ID `1`. Fallbackaktøren var organisasjonsnummer `986639551`, PUBLIC-ID `93`.

- API list/detail, PUBLIC card/detail og head tok samme `asset|system_fallback`-beslutning.
- Kort og hero brukte `projection.square`; Open Graph og Twitter brukte `projection.share` med `1200 × 630`.
- Canonical kom fra `PUBLIC_SITE_ORIGIN`; rendition-URL-er kom fra `PUBLIC_MEDIA_ORIGIN`.
- Endret `Host`, `X-Forwarded-Host` eller proxy-proto kunne ikke påvirke canonical eller bilde-URL-er.
- Upubliserte aktører ga `404` i både API og PUBLIC.
- Ingen tenant-ID, selection-ID, intern key/checksum, safetykategori/cursor, source/proveniens, privat original eller filesystempath ble eksponert.
- Legacybilde-URL-er forekom ikke i aktiv API/PUBLIC/head-reise.

Fullkatalogauditen var:

```text
published=122
asset=1
system_fallback=121
safety_unavailable=0
scope_mismatch=0
query_count=5
authorize_count=3
```

## Browser og fallback

Prosjektets Playwright-gate ble kjørt mot faktisk staging på desktop og mobil. Den verifiserte assetkort/-detail, fallbackkort/-detail, lange navn, full katalog uten horisontal overflow, canonical/head, blank fallback-alt og én-gangs browserfallback ved avbrutte assetbytes. Ved bytefeil ble `src` byttet til static square-fallback, `alt` nullstilt og `onerror` fjernet; ingen legacy-URL eller state-write ble brukt. Fallbackgrafikken var visuelt ryddig på desktop og mobil. Den aktive stagingasseten hadde ingen credit; CI-browsertesten dekker separat nonblank credit og at credit ikke overlapper hero-innholdet.

Production fallback v1 kan hentes fra versionerte static-stier uavhengig av ledger, bridge og delivery-root. Square-, landscape- og sharefilene er byteidentiske med de visuelt godkjente emergency-filene og systemfallback har eksplisitt blank alttekst.

## Fail-closed, restart og persistens

En live read-only autorisasjon med endret checksum ga `scope_mismatch` uten write. Da bridge service og socket ble stoppet, falt API, PUBLIC og head til systemfallback, media svarte `503` med `no-store`, og static fallback forble tilgjengelig. Socket activation og bridge-restart gjenopprettet eksakt assetprojection og media. API-, web- og bridge-restart bevarte projection og bytes.

Formell `deny`, `retire`, origin delete og purge ble ikke kjørt mot den aktive releasen fordi dette tilhører 3E.4. De negative state-kategoriene er dekket av integrasjons- og CI-testene. Safety-ledgeren forble `READY` på cursor `7`; databaseantall forble `122` publiserte, `8` selections, `33` renditions, `2` releases og `6` mappings. Seks deliveryfiler beholdt manifest:

```text
fb94a3023614361f4157b0a5a82a145ef81c983f3e05ac1e4cf1afb0fa07c7a9
```

## Ytelse og sluttgate

På endelig merge `e04220b` målte Django-requestprofilen:

| Reise | SQL-spørringer | intern runtime |
| --- | ---: | ---: |
| API list, 122 aktører | 11 | 875,797 ms |
| API asset detail | 11 | 23,309 ms |
| PUBLIC list, 122 aktører | 13 | 89,184 ms |
| PUBLIC asset detail | 20 | 26,958 ms |
| PUBLIC fallback detail | 11 | 10,036 ms |

Fem eksterne API-listmålinger var `0,110–0,192 s`; fem PUBLIC-listmålinger var `0,095–0,124 s`. N+1-blockeren er dermed lukket i faktisk stagingdata, ikke bare i enhetstesten.

Sluttgaten verifiserte også systemcheck, alle sentrale HTTP-endepunkter, host-invarians, upublisert-scope, fullkatalogaudit, uendret safety health, databaseantall, deliverymanifest, backupstatus og sanitert API-logg.

## Stoppunkt

Fase 3E.3 er `CLOSED / ACTIVE` i staging. Public API, PUBLIC HTML, canonical, Open Graph og Twitter bruker samme projection. Fase 3E.4 er ikke startet: ingen deny-/retire-UI, tenant-checksumdeny, origin delete, cache purge, release cleanup eller legacyopprydding er implementert eller aktivert.
