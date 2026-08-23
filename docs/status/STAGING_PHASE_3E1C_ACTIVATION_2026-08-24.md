# Staging – fase 3E.1C kontrollert serving aktivert og verifisert

**Dato:** 2026-08-24 lokal tid / 2026-08-23 UTC
**Status:** `ACTIVE` i staging; fase 3E.1C er `CLOSED`; 3E.2, projection, API/PUBLIC-cutover og formell takedown er fortsatt uimplementert

## Formål og avgrensning

Denne separate aktiveringsgaten beviser kontrollert HTTP-serving av én materialisert public image release gjennom Django, read-only safety-autorisasjon og intern Nginx `X-Accel-Redirect`. Gaten aktiverer bare den eksplisitte release-ruten. PUBLIC HTML/API og legacybildealiasene er ikke koblet til releasen og forble uendret.

Kode- og eksempelstandard for `PUBLIC_IMAGE_SERVING_ENABLED` er fortsatt `False`. Bare den ignorerte stagingkonfigurasjonen har verdien `True`. Ingen 3E.2-projection, nytt public API-felt, PUBLIC-bildebruk, legacy-cutover, deny/retire, purge eller takedown ble aktivert.

## Verifisert leveranse

3E.1C ble levert gjennom fire separat reviewede PR-er:

| PR | Formål | Mergecommit | Grønn main-CI |
| --- | --- | --- | --- |
| #41 | kontrollert Django/Nginx-serving, read-only `authorize`, origins, cache og isolasjon | `76d4dba8bcbef2d2811730e61720eef32c2b7cd7` | `32665743134` |
| #42 | behold supplementary delivery-GID etter Nginx privilege drop | `43bc993ccb7496e1e9dcf716e40d5d0a8ade757a` | `32666655506` |
| #43 | bevar Djangos checksum-`ETag` gjennom intern Nginx-filserver | `a48fb5584a9ca253d90ffc265bac0ce9bdfcee0c` | `32667670647` |
| #44 | tomme canonical feilsvar/metodegate og eksplisitt INFO-observability | `38663b532de64eb15b5ec6579dbb7d66a0eb18fe` | `32668678789` |

PR #44 ble gjennomgått på eksakt head `03e5c20bc1ee23fa066144c9efffffac68176508`. Alle seks PR-jobber ble grønne i run `32668402566`; den uendrede sockettesten fikk først ett runneravvik mellom EOF og `ECONNRESET`, passerte lokalt med 44/44 tester og ble grønn ved én omkjøring. Ingen testkode ble endret for å skjule avviket.

Staging ble fast-forwardet rent til eksakt sluttmerge `38663b5`. API ble bygget og kontrollert rekreert med serving av. Før aktivering ga canonical release-rute tom `404/no-store`, ikke-canonical rute tom `404/no-store` og unsafe method tom `405/no-store`. Den nye loggeren skrev samtidig strukturerte INFO-linjer til containerloggen.

## Release- og safety-state

Den kontrollerte livegaten brukte release UUID `df8efd43-027c-434b-9b0b-5633bb9bea78` for en publisert stagingaktør med aktiv selection. Releasen ble opprettet gjennom den støttede 3E.1B-workflowen mens serving var av. En full retry gjenbrukte samme UUID, DB-binding og activation uten nye writes eller events.

| Variant | Bytes | SHA-256 |
| --- | ---: | --- |
| `square.png` | 96592 | `81c7960ffb4216cc8ebce967d60b61bda882a191b7517d844d26745bc08c5101` |
| `landscape.png` | 171325 | `d28d45bbebbd218cfc9d90f7ee7be0f48fabe6231f1e6dec1222b62e8817d9a4` |
| `share.png` | 178638 | `d8ad976a4ba7a9baf5e8ebabec356f1e97d566fbd534bc91c27c80b62e2d038e` |

Staging har etter gaten to immutable release-aggregater og seks delivery-filer: den tidligere upubliserte 3E.1B-evidensreleasen og denne publiserte servingreleasen. Safety-ledgeren er `READY` med event/read/anchor cursor `7`. Et direkte read-only `authorize` med endret checksum ga `authorized=False`, kategori `scope_mismatch` og cursor `7` uten ledgerwrite.

## HTTP-, cache- og feilgater

Alle tre variantene bestod følgende over HTTPS gjennom Caddy → Nginx → Django → safety bridge → intern Nginx-filserver:

- canonical `GET` og `HEAD` ga `200` med korrekt `image/png`, `Content-Length`, identiske bytes og checksum-`ETag`
- svak `If-None-Match` ble reautorisert og ga `304` med samme checksum-`ETag`
- godkjente svar brukte `Cache-Control: private, max-age=60, must-revalidate`
- ukjent UUID, malformed/uppercase UUID, ukjent variant, feil extension, traversalform og den upubliserte 3E.1B-releasen ga tom `404/no-store`
- `POST`, `PUT`, `PATCH` og `DELETE` ga tom `405/no-store` før DB-, bridge- eller storagekall
- direkte `/_protected-public-image/...` var utilgjengelig med `404`

En første livegate avdekket at Nginx erstattet checksum-`ETag` med filmetadata-`ETag`; serving ble straks slått av før PR #43. En senere negativ gate avdekket standard Django-/CSRF-feilbody på ikke-canonical URL-er og unsafe methods; serving ble igjen slått av før PR #44. Endelig gate er grønn på de rettede mergecommitene.

## Fail-closed, restart og isolasjon

- både bridge-service og socket ble stoppet; en ellers gyldig release ga tom `503/no-store`
- bare socketen ble startet; neste request socket-aktiverte servicen og ga igjen korrekte bytes, mens health var `READY` på cursor `7`
- `landscape.png` ble flyttet kontrollert til en eksakt hold-path uten sletting; request av `square.png` ga tom `503/no-store` fordi alle tre filer verifiseres per request
- filen ble flyttet tilbake med identisk checksum, og serving gikk tilbake til `200`
- kontrollert API-recreate, web-restart og bridge-restart bevarte release, filer, flagg og checksumkorrekt serving
- socketen var `root:root 0600`; faktiske Nginx-workers hadde GID `2000` etter privilege drop
- API hadde socket-runtime read-only og delivery read/write; web hadde bare delivery read-only og ingen socket, private originaler, artifacts, ledger, safety-secret eller Borg

Vilkårlig `X-Forwarded-Host` endret ikke bytes eller URL-bygging. Direkte attacker-`Host` mot Nginx/Django ga `400` uten redirect. Den interne URL-builderen returnerte eksakt konfigurert `https://staging.northernsound.no/...`, ikke request-host. Strukturerte logger viste bare utfall, release-ID, variant, HTTP-status, safety-kategori/cursor og varighet; kontrollen fant ingen filesystempath, credential, secret, ledgerpath eller repository-ID.

## PUBLIC, backup og sluttstatus

Etter aktivering ga `/`, `/api/auth/session/`, `/public/actors/` og `/api/public/actors/` fortsatt `200`. PUBLIC-listens HTML var fortsatt 121060 bytes, publisert aktørantall var fortsatt `122`, legacy orgnummer-ruten ga uendret permanent `301` til canonical ID-rute, og den nye release-UUID-en fantes verken i PUBLIC HTML eller public API. Dette beviser at standalone media-serving er aktiv, men ikke at PUBLIC bruker den.

Pre-activation-backup `kreative-norge-staging-20260823T211436Z` var grønn. Post-activation-backup `kreative-norge-staging-20260823T220249Z` bestod database-/arkivkontroll, full repository-/data-verifikasjon og isolert PostgreSQL-restore fullført `2026-08-23T22:03:22Z`.

Sluttilstanden er:

- stagingrepo og kjørende API-kode: `38663b532de64eb15b5ec6579dbb7d66a0eb18fe`
- `IMAGE_ASSET_FEATURE_ENABLED=True`
- `PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=True`
- `PUBLIC_IMAGE_SERVING_ENABLED=True` bare i ignorert stagingmiljø
- safety-ledger `READY`, cursor `7`
- to release-aggregater og seks delivery-filer
- PUBLIC/legacy fortsatt uendret og uten releasekobling

## Konklusjon og stoppunkt

Fase 3E.1C er `CLOSED / ACTIVE` i staging. Kontrollert standalone release-serving, origins, cache, read-only safety-autorisasjon, fail-closed-adferd, restartpersistens, observability og backup/restore er bevist.

Neste fase er 3E.2 projection og API shadow. Denne leveransen stopper før 3E.2, PUBLIC-kobling, legacy-cutover, 3E.3 og formell takedown i 3E.4.
