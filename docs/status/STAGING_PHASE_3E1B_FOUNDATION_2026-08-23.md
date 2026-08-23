# Staging – fase 3E.1B-foundation deployet og verifisert

**Dato:** 2026-08-23

**Status:** `DEPLOYED / VERIFIED`, mens `PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=False`

Denne statusen gjelder bare 3E.1B-foundationen: migrasjon `0029`, host-eid bridge/socket, API-only delivery-/socketmount og generell backup/restore av delivery-rooten. Ingen release-workflow ble aktivert, ingen release eller safety-event ble opprettet, ingen releasefil ble materialisert, og ingen Nginx-/Caddy-route eller offentlig serving ble lagt til.

## Baseline og datagate

- Eksakt deploycommit var mergecommit `d756b4b13fc7c5cee5e37dcf48b7ce24e91ef1c1` fra PR #38. Alle seks jobber var grønne både i PR-CI-run `32630246582` og main-CI-run `32630497627`.
- Stagingrepoet var rent på `c0c9a86deedbe9d8fd12cfcf73376338cccde449` før deploy og rent på `d756b4b13fc7c5cee5e37dcf48b7ce24e91ef1c1` etterpå.
- Read-only preflight viste `0` `OrganizationImageRelease`-rader, `0` selectionduplikater, `0` scopeavvik, `0` ufullstendige mapping-sett og `0` mapping-/artifact-snapshotavvik.
- Fersk pre-deploy-backup `kreative-norge-staging-20260823T133543Z` var grønn og repository-ID-en matchet den etablerte ADR-008-backupen.
- Migrasjon `0029_release_selection_revision_gate` ble anvendt uten backfill fordi tabellen var tom. Etter deploy og API-recreate var release-count fortsatt `0`.

## Bridge, peer og isolasjon

- `/run/kreative-norge-image-safety/bridge.sock` er en aktiv systemd-socket med `root:root` og mode `0600`; bridge-servicen startet gjennom socket activation og forble aktiv.
- Et framed protocol-v1-kall fra API-containeren nådde broen og fikk forventet `unknown_operation` for den bevisst deaktiverte operasjonen `retire`. Fordi uautorisert peer lukkes uten domenerespons, beviser svaret at den faktiske Docker/Linux-root-peeren passerte `SO_PEERCRED`-gaten.
- Aktiv bridgeflate er bare `reserve` og `activate`. Framingtimeout er 5 sekunder, serverens operasjonsfrist 45 sekunder, Django-clienttimeout 50 sekunder og Gunicorn worker-timeout 60 sekunder.
- API har read/write-mount av `/srv/kreative-norge/media/public-delivery` og read-only mount av `/run/kreative-norge-image-safety`. API mangler ledger-, `/etc`- og Borg-mount/klient/credentials.
- Web har fortsatt bare read-only staticmount og mangler delivery-, socket-, ledger-, `/etc`- og Borg-tilgang.
- Delivery-rooten er host-persistent `root:root` mode `0750`; den er ikke eksponert gjennom nginx, Caddy eller en Django-storage-URL.
- Safety-ledgeren forble `READY` på cursor `3` med samme verifiserte repository-ID som før deploy.

## Delivery-persistens og backup/restore

En syntetisk, ueksponert probe ble skrevet gjennom API-containerens konfigurerte delivery-root mens det permanente materialiseringsflagget var `False`:

- relativ path: `runtime-probes/d12e5e471a13aaa3fd4fffa1f8cd8822/probe.bin`
- SHA-256: `2dc674e43b5da2a54eaef0f92939864244ba1a32b57b41a77fd8ab4b6491a911`

Proben beholdt identisk checksum etter en kontrollert API-containerutskifting. Den aktive root-only backupallowlisten ble utvidet med delivery-rooten, og backup `kreative-norge-staging-20260823T134222Z` fullførte grønt. Full repository-/arkivdata-verifikasjon og isolert PostgreSQL/media-restore fullførte grønt. Et eksplisitt read-only Borg-uttrekk av nøyaktig probe-memberen ga samme SHA-256. Den navngitte live-proben og de tomme probe-katalogene ble deretter fjernet; arkivet beholder recoveryevidensen.

## Deployavvik og smokes

Docker Compose 1.29.2 traff den kjente `ContainerConfig`-feilen under første API-recreate. Bare API-containeren var stoppet; database og web fortsatte. Den dokumenterte API-only-sekvensen `stop → rm api → up api` gjenopprettet tjenesten uten å fjerne database, web, volumer eller host-media. Den samme kontrollerte sekvensen ble senere brukt til persistencebeviset.

Django `check`, lokal web, lokal Caddy og ekstern HTTPS svarte grønt. `/`, `/api/auth/session/` og `/public/actors/` returnerte `200` eksternt. Serverens egen utgående Cloudflare-rute returnerte `403`, mens lokal Caddy og ekstern klient returnerte `200`; dette var ikke et origin- eller applikasjonsavvik.

## Stoppunkt og neste gate

`PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED` er fortsatt `False` i aktiv stagingkonfigurasjon. `IMAGE_ASSET_FEATURE_ENABLED` forblir `True` som før. Ingen public runtime er aktivert.

Før materialiseringsflagget kan aktiveres gjenstår den egne activation-gaten med syntetiske, komplette `square`/`landscape`/`share`-renditions gjennom den faktiske reserve → DB-binding → create-only/read-back → activate-workflowen, inkludert retry/no-clobber og kontrollert delvis materialisering/restart. Serving, projection, API/PUBLIC-cutover, cache/purge og takedown tilhører fortsatt 3E.1C–3E.4.
