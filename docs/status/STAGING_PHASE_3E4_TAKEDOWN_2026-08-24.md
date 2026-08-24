# Staging – fase 3E.4 ledger-v2 og formell takedown 2026-08-24

**Status:** `CLOSED / ACTIVE`

## Kontrollpunkt

- Implementerings-PR: #52
- Evidens-PR: #53
- Endelig reviewet head: `d4a60274cf7e3d9199edabd053574dc6227adc2a`
- Deployet merge: `087026e7e8bb43f9619c605e75f538976c6f1566`
- PR-CI: run `32754356644`, 6/6 grønn
- Post-merge-CI på `main`: run `32757902168`, 6/6 grønn
- Migrasjon: `0030_formal_image_takedown_audit`
- Predeploy-backup: `kreative-norge-staging-20260824T183447Z`, full repository-/archive-data-verifikasjon og isolert restore grønn
- Post-deny-backup: `kreative-norge-staging-20260824T191855Z`, fingerprint `a94bf63402a4c3e0e83c1ff194d53c5abd60bafad2e620c2d5e1cac805209a16`, full repository-/archive-data-verifikasjon og isolert restore grønn

PR #52 fikk en separat frozen-head-review. Reviewen fant og lukket activation-versus-deny-racet, de eldre muterende CLI-flatene, en restore/republish-testmangel og motstridende current-dokumentasjon. Endelig review ga `0 BLOCKER`, `0 HIGH` og `0 MEDIUM`. Én akseptert lav tilgjengelighetsobservasjon består: ved treg bridge kan legacyguard gjøre ett fail-closed kall på maksimalt 100 ms per `Organization`; den gir ingen sikkerhetsbypass.

## Aktiv sluttkonfigurasjon

```text
IMAGE_ASSET_FEATURE_ENABLED=True
PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=True
PUBLIC_IMAGE_SERVING_ENABLED=True
PUBLIC_IMAGE_PROJECTION_ENABLED=True
PUBLIC_IMAGE_API_SCHEMA_ENABLED=True
PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=True
PUBLIC_IMAGE_TAKEDOWN_ENABLED=True
```

Alle verdiene gjelder bare den ignorerte stagingkonfigurasjonen. Kode- og eksempelstandardene er fortsatt `False`. Takedownflagget åpner bare nye formelle writes; allerede ankret release-/checksum-deny, legacyguard og serving/projection-enforcement håndheves alltid.

## Ledger v1 → v2

Staging startet med safety-ledger-ID `934fa373-111f-4192-9e13-6483041232d5`, schema v1, cursor `7`, head `76343b44aa5514440f5e602513c4aa32baaab2c67ae098d608232d145dd3addc` og tom tenant-checksum-deny. API/web hadde fortsatt ikke ledgerfil eller Borg-credentials.

Safetywriters ble stoppet før en root-only kopi ble tatt. Kopien og livefilen hadde SHA-256 `cff2d9c1819f4e34c2ee87ecdbe76d9f3856f8e97f5464a916214cf607425701`. `upgrade-v2`, `rebuild` og `health` på kopien bevarte ledger-ID, cursor, head, bundlehash, receipts og release-state. Den live transaksjonelle upgraden ga deretter schema v2 med `v1_event_cursor=7`, uten å omskrive de sju v1-eventene. Bridge/socket/health-timer ble restartet, og API/PUBLIC/head/serving var uendret før write-gaten ble aktivert.

Etter deny og sikker republisering er safety `READY` på cursor `13` og head:

```text
caa4242b15b8bf33184b5df7c12269b724f3b7709297470f48d4f45bd2197226
```

Ledgeren har sju bevarte v1-events, seks v2-events, 13 verifiserte receipts, én tenant-checksum-deny, tre aktive og to denied release-states. Nyeste ankermedlem er `image-safety-934fa373-111f-4192-9e13-6483041232d5-00000000000000000013-caa4242b15b8bf33`, med bundle-SHA `47f73940f5fb2a7cf0dee14fefff427dc70f00ca39d34ec4d1a8caa8316fd64d` i det uendrede dedikerte safety-repositoryet.

## Permanent syntetisk deny

En dedikert syntetisk Organization ble opprettet i tenant 1:

- Organization-ID `196`, orgnummer `STAGING-3E4-20260824`
- første asset `9`, checksum `f68b9d434e3a751c4db49ac76790e4412ea609b167bb0bb423e526ad0a89daeb`
- første selection `9`, revisjon `1`
- første release `1d666242-bba1-4576-80bb-d933f50bfd33`
- tre canonical keys under `releases/1d666242-bba1-4576-80bb-d933f50bfd33/`
- activation cursor `9`

Før deny viste API, PUBLIC detail og `og:image` samme asset. `square.webp` svarte `200`, `private, max-age=60, must-revalidate`, Cloudflare `BYPASS` og ETag `"c69e9980de5f07882bcd0c1e954f8a4a92071f42c0209de9f71046b5b457b98d"`. Alle tre originfiler fantes med verifiserte checksums.

Plattform-superadmin kalte den interne DRF-ruten med bare `reason_code=editorial_policy`. Resultatet var:

```text
release_disposition=new
checksum_disposition=new
anchor_cursor=11
selection_id=10
revision=2
review_event_id=10
origin_files_deleted=3
origin_files_already_missing=0
```

Release-deny og tenant/checksum-deny ble skrevet under samme ankret head før PostgreSQL-fallback og origin-delete. Den gamle selectionen ble arkivert, fallback revision 2 ble aktiv, og immutable release, tre mappings, privat original, artifacts og append-only audit besto.

Etter deny viste API/PUBLIC/head bare production fallback v1. Den gamle URL-en ga `404` med `Cache-Control: no-store`; forespørsel med den gamle ETag-en ga fortsatt `404`, aldri `304`. Ekstern kontroll gjennom Cloudflare ga `404`, `no-store` og `CF-Cache-Status: BYPASS`, aldri `HIT`. Alle tre originfilene var borte.

Idempotent retry gjenbrukte selection `10`, reviewevent `10` og safetyidentitetene, rapporterte tre missing-filer og lot cursor `11` og head `a2e6a443dab46c8b43a86f9e93246f3296dd2b16f90ebb2794caa41e4c8ac6a3` stå uendret.

## Restore-, rollback- og republiseringsbevis

De eksakte gamle kildebytene ble lastet opp på nytt gjennom ordinær candidateflyt. Ingest gjenbrukte asset `9` og rendition-sett `12`, men approval, restore av arkivert selection og releaseopprettelse ble alle avvist av tenant/checksum-deny. Ingen ny selection, release eller takedownaudit ble opprettet.

API-schema og PUBLIC-cutover ble kontrollert slått av mens projection, serving og write-gate forble på. Det lagrede legacyfeltet besto i PostgreSQL, men `get_public_image_url()` og `get_preview_image_url()` returnerte `None`, legacy-API-et eksponerte ingen bilde-URL, og PUBLIC viste aldri den nektede release-ID-en. Gatene ble reaktivert med samme fallback og uendret safety-head.

Én checksum-verifisert gammel `square.webp` ble deretter restaurert fysisk fra den sikre testkopien. Den var fortsatt utilgjengelig som `404/no-store`, og projection forble fallback. Samme idempotente takedown-path slettet eksakt den ene restaurerte filen, aksepterte de to andre som missing og flyttet ikke ledger-head.

Sikker republisering brukte andre syntetiske kildebytes:

- ny asset `10`, checksum `c51145892bc09daa60cfcbe686e977a5d9e4ce1bedd5f966c5a74b3948f19a4b`
- ny selection `11`, revisjon `3`
- ny release `6eb984b0-2d80-43e8-b081-8c3e1d25009a`
- tre nye canonical keys og tre materialiserte filer
- reserve/activate på cursor `12`/`13`

API/PUBLIC/head viste den nye asseten med korrekt alttekst, kreditering og aliases. Den gamle releasen forble `denied`, gammel checksum-deny besto, gammel origin var tom og gammel URL forble `404/no-store`.

Det finnes andre tenants med reelle data i staging. Ingen destruktiv cross-tenant live-test ble derfor kjørt; tenantisolasjon og ikke-lekkende feilrespons er dekket av backend-/API-testene i grønn CI.

## Restart, backup og sluttstate

API og web ble kontrollert stoppet, fjernet og gjenskapt uten database, volumes eller media. Safety-bridge ble restartet separat. Alle sju stagingflagg var fortsatt `True`, Django systemcheck var grønn, safety var `READY` på cursor `13`, ny asset svarte `200`, og gammel URL svarte `404/no-store`.

Før testaktøren ble unpublisert målte fullkatalogauditen:

```text
published=123
asset=2
system_fallback=121
safety_unavailable=0
scope_mismatch=0
query_count=5
authorize_count=6
```

Post-deny-databasen hadde 10 assets, 39 renditions, 11 selections, 4 releases, 12 mappings og én formell takedown. Delivery hadde ni filer med manifest:

```text
ac91c567897bee1a79bf6146811c98ea550f3c2776c42cd52376aa7be2b475dc
```

Den syntetiske Organizationen ble til slutt bare unpublisert. Den ble ikke slettet, og deny-, audit-, selection-, release- og checksumhistorikken består. Normal katalog er dermed tilbake på `122 = 1 asset + 121 systemfallback`, fem queries, tre authorize-kall, ingen safety-/scopefeil. API og PUBLIC gir `404` for den upubliserte testaktøren.

## Rollback og stoppunkt

Fase 3E.4 er `CLOSED / ACTIVE` i staging. Etter den første permanente denyen er rollback forward-only: `PUBLIC_IMAGE_TAKEDOWN_ENABLED=False` kan stoppe nye writes, men schema v2, release-/checksum-deny, legacyguard, audit og serving/projection-enforcement skal aldri downgrades, slettes eller omskrives.

Dette avslutter fase 3E.4. Ingen 3F-legacyovergang, generell release-retensjon, provider-/CDN-purge, takedown-UI eller legacyopprydding er startet.
