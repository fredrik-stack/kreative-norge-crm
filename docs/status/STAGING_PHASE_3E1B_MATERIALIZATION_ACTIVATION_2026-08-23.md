# Staging – fase 3E.1B-materialisering aktivert og verifisert

**Dato:** 2026-08-23
**Status:** `ACTIVE` i staging; public serving, projection, API/PUBLIC og 3E.1C er fortsatt av

## Formål og avgrensning

Denne separate aktiveringsgaten beviser hele ADR-009-flyten fra permanent reservasjon til aktiv release på staging, inkludert sikker retry etter delvis materialisering. Gaten bruker en dedikert upublisert testaktør. Den aktiverer ikke en offentlig URL, Nginx-/Caddy-serving, public projection, API-felt eller PUBLIC-visning.

## Verifisert baseline

- staging ble fast-forwardet rent til `main` på merge `ee42c8217a7d32321be7d35ecfb368a280e6df82`
- main-CI-run `32646334974` var grønn på eksakt mergecommit
- 25 målrettede migrasjons-, workflow-, bridge-, materialiserings- og settings-tester var grønne lokalt
- release-tabellen var tom, delivery-rooten var tom og safety-ledgeren var `READY` på cursor/event/read/anchor `3`
- selection `6`, revisjon `2`, rendition-sett `6` for den upubliserte testaktøren `Codex stagingtest 3D.2 2026-08-11` hadde komplette `landscape`, `share` og `square`-artifacts
- pre-activation-backup `kreative-norge-staging-20260823T185358Z` bestod repository-/arkivverifikasjon og isolert restore

## Aktivering og no-clobber

Bare den ignorerte stagingverdien `PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=True` ble aktivert. API ble kontrollert rekreert uten å rekreere database, web, volum eller media. Django system check var grønn, og release-count forble `0` før den syntetiske workflowen startet.

No-clobber ble først bevist i en isolert, tilfeldig `/tmp`-delivery-root i API-containeren med samme virkelige snapshot og artifacts som stagingselectionen. En på forhånd opprettet canonical key med andre bytes ga forventet `ImageMaterializationConflict`; SHA-256 `5876ba9c59135fc6dc4a6dc65ed34586bdbdbcdeeb22bb3dbeae1ae4c130563e` var uendret. Det ble ikke skrevet ledger- eller databaserader, og den isolerte delivery-rooten ble fjernet etter testen.

## Delvis materialisering og restart

Den permanente syntetiske workflowen reserverte release UUID `248806b9-613c-4c1f-bcf5-64c5b15cfff9`, bandt den atomisk til selection `6`/revisjon `2` og opprettet tre immutable mappinger. En kontrollert crash ble injisert etter første vellykkede create-only-write.

Tilstanden etter crashet var:

- safety-ledger event `4` var `release_reserved`; release state var `reserved`, og health var `READY` på cursor/event/read/anchor `4`
- PostgreSQL hadde ett komplett release-aggregate med tre mappinger
- delivery-rooten hadde bare `landscape.webp`, med SHA-256 `1c9023b4d7c02edf63691de7e7a3e6de74237056197967aac02ef81fdec55047`
- ingen activation-event var skrevet

Etter kontrollert API-recreate var flagget fortsatt på, alle tre mappingene og den ene filen var bevart, og systemet kunne fortsette uten manuell database- eller filreparasjon.

## Recovery, read-back og idempotent retry

Første normale retry returnerte `idempotent_retry` for reservasjonen, beholdt eksisterende `landscape.webp` (`created=False`), opprettet `share.jpg` og `square.webp` (`created=True`), verifiserte alle filene ved read-back og skrev én ny activation-event. Resultatet var:

| Variant | SHA-256 |
| --- | --- |
| `landscape.webp` | `1c9023b4d7c02edf63691de7e7a3e6de74237056197967aac02ef81fdec55047` |
| `share.jpg` | `1ddad511c25ecf752e4fb02528de9ec9051288d9f67011beb7d373b4a4c554b1` |
| `square.webp` | `ae341770a1bb9407d3f2893a630788009593e7fa933ec9109c55b8d56e69a238` |

Ledger event `5` var `release_activated`, release state var `active`, og health var `READY` på cursor/event/read/anchor `5`. En ny komplett retry returnerte `idempotent_retry` for både reservation og activation, markerte alle tre writes `created=False`, beholdt de samme checksumene og opprettet ingen nye ledger-events.

## Persistens, backup og serving-isolasjon

Sluttilstanden i staging er én immutable syntetisk release med tre filer under `releases/248806b9-613c-4c1f-bcf5-64c5b15cfff9/`. Filene eies av root og har mode `0640`. Den tilknyttede organisasjonen er fortsatt upublisert.

Post-activation-backup `kreative-norge-staging-20260823T185950Z` bestod full repository-/arkivverifikasjon og isolert restore med database- og delivery-tilstanden inkludert.

Serving er fortsatt eksplisitt av:

- `public_image_delivery` har ingen `base_url`
- web-containeren har ikke delivery-mount
- Nginx-konfigurasjonen har ingen public-delivery-route
- kontrollerte plausible delivery-paths returnerte SPA-HTML, ikke image bytes
- ingen public projection, API/PUBLIC-kobling eller legacy-cutover er aktivert

## Konklusjon og stoppunkt

Fase 3E.1B-materialisering er `ACTIVE` og verifisert i staging. Reserve → DB-binding → create-only materialisering/read-back → activate, hard no-clobber, delvis materialisering/restart og full idempotent retry er bevist. Den permanente syntetiske releasen beholdes som sporbar stagingevidens og skal ikke slettes av generisk orphan-cleanup.

Neste gate er fase 3E.1C for kontrollert serving og origins. Denne gjennomføringen stopper før 3E.1C, public projection, API/PUBLIC og offentlig bildebruk.
