# Staging – fase 3E.1A safety ledger aktivert

**Dato:** 2026-08-20

**Status:** `ACTIVE` i staging for 3E.1A safety-ledger, off-server anchor og restore-gate

Denne statusen gjelder bare den separate sikkerhetsledgeren og dens off-server Borg-anchor. Public image runtime, release-materialisering, serving, projection, PUBLIC, takedown og fase 3E.1B–3E.4 er fortsatt ikke implementert eller aktivert. Ingen reell organisasjon, bildebyte eller public fil ble brukt i øvelsen.

## Leveranse og preflight

- Branch: `feature/phase3e1a-public-image-safety-ledger`; draft-PR #36 er ikke merget.
- Live hostmodul ble installert fra eksakt staging-head `c0c9a86deedbe9d8fd12cfcf73376338cccde449`.
- Livefunnet om traceback fra installert operator-wrapper ble lukket av `c0c9a86deedbe9d8fd12cfcf73376338cccde449`; 28 safety-tester og alle seks jobber i CI-run `32413908257` var grønne på denne headen.
- Borg `1.2.8` oppfyller det håndhevede vinduet `>=1.2.8,<1.3.0`.
- Kode/config/state er host-side, root-eid; config/ledger er `0600`, state- og Borg-kataloger er `0700`.
- Writerens private ED25519-key og Borg-passfrase er bare root-tilgjengelige på staging. Subaccount-passord, main/admin-tilgang og eksportert repository key ligger ikke på runtimehosten.
- Prosjekteier har manuelt verifisert recovery-custody for minst to ansvarlige, checksum på off-server recovery-key-kopi og fjerning av lokal transferkopi. Ingen secretverdi er registrert i Git eller denne rapporten.

## Repository-separasjon

Repositoryene ble kontrollert før første destruktive probe:

| Formål | Repository-ID |
| --- | --- |
| public-image-safety | `40a469b096ffa44de89aae5f187dfd9d9aefc873a874bfb8ef718180be1cb896` |
| ADR-008 general backup | `3084838aa6fb3b32c8173b4d09020ba5fad10d8717d63f899a7313c712fc4b69` |

ID-ene er forskjellige. Safety-repositoryet lå i et dedikert, tomt subaccountområde før genesis. ADR-008-repositoryet ble bare lest gjennom etablert inspect-flyt og ble aldri mutert av capability-/restoreøvelsen.

## Genesis og syntetisk reservation

- Ledger-ID: `934fa373-111f-4192-9e13-6483041232d5`.
- Genesis: cursor `0`, null-head, remote read-back og lokal receipt; health `READY`.
- Syntetisk release-ID: `2688b9ef-13b9-46ce-ad32-e8637190e6c4`.
- Reservation-event: `staging-3e1a-reservation-20260820-a`.
- Autoritativ reservation: cursor `1`, full head-hash `10097484bffffeaebd14cece4de067fa89e8be0b1525b1526fe030b34d0a45f8`.
- Arkiv: `image-safety-934fa373-111f-4192-9e13-6483041232d5-00000000000000000001-10097484bffffeae`.
- Samme event-ID og payload gjenbrukte samme arkiv idempotent. Samme event-ID med endret payload ble avvist fail-closed uten traceback.
- `/srv/kreative-norge/media/public-delivery/` ble ikke opprettet; ingen DB-release, public materialisering eller serving ble aktivert.

## Append-only capability og separat probe-recovery

Et separat syntetisk probe-arkiv ble opprettet, lest tilbake og verifisert med SHA-256 `affd42adbaddc7e1ce8d91377733aed6ef4bcb6d7f17b5884af7098eddacbac0`.

- Borg `delete` fjernet proben logisk fra current manifest.
- Borg `compact` med writeridentiteten returnerte exit `0` uten output. Segmentene ble ikke fysisk kompaktert, i samsvar med dokumentert Borg 1.2 append-only-adferd.
- Writerens SSH/subaccountidentitet kunne utføre rå filoperasjon og `rm` utenfor repositoryet. Løsningen er derfor WORM-orientert skadebegrensning, ikke absolutt WORM.
- Separat admin/recovery-custody rullet repositoryet tilbake til siste gode probe-transaksjon `13`. Etter cache-/manifestreset var repository-ID uendret, probe-arkivet synlig igjen og checksum identisk.
- Prosjekteier aksepterte 2026-08-20 de dokumenterte Borg/Hetzner-begrensningene og raw-`rm`-restrisikoen for 3E.1A.

## Nyeste DENIED-head og incident recovery

Den samme syntetiske releasen ble brukt videre:

| Tilstand | Cursor | Full head-hash | Arkiv |
| --- | ---: | --- | --- |
| ACTIVE | 2 | `556f7b09225a3a6467f24da7693d810c7bb9be809af5ae3de889f98df55609dc` | `image-safety-934fa373-111f-4192-9e13-6483041232d5-00000000000000000002-556f7b09225a3a64` |
| DENIED | 3 | `05d01414a7ea3a27a8b6a1d72b92cd435eb32cb90a40fdb8432f7a9718444912` | `image-safety-934fa373-111f-4192-9e13-6483041232d5-00000000000000000003-05d01414a7ea3a27` |

Writeridentiteten tombstonet deretter bare nyeste DENIED-arkiv. Current manifest viste cursor `2`/ACTIVE som høyeste synlige head. `restore-latest --recovery-mode incident-recovered` med forventet cursor `3` og full DENIED-hash ble avvist med exit `1`; ingen destination ledger eller ny receipt ble opprettet.

Siste gode autoritative DENIED-state var Borg-transaksjon `21`. Separat recovery-custody gjenopprettet denne transaksjonen. Current manifest viste igjen cursor `3`, repository-ID var uendret, og incident-restore godtok bare eksakt cursor/fullhash. Separat restore, rebuild og health ga `READY`, og `release_state` var eksakt `denied` på sequence `3`.

En ekte eldre cursor-2-bundle viste `active` og egen konsistent health. Den nyere autoritative cursor-3-ledgeren viste `denied`; dermed taper gammel app-/DB-state mot nyere safety-state som krevd.

## Fail-closed, restart og isolasjon

Isolerte kopier ga følgende resultat uten å endre live-ledgeren:

- stale read cursor: `read_cursor_stale`, `ready=false`
- manipulert ACTIVE read-model: `read_model_mismatch`, `ready=false`
- korrupt eventkjede: `ledger_invalid`, `ready=false`
- feil repository-ID: `repository_identity_mismatch`, `ready=false`

Staginghosten ble restartet. Før og etter restart var live-ledgerens SHA-256 identisk: `2ee245de89806cd76ff0477f1e9ca71202f20695ae4119a1dc8d8162a2e77721`. Cursor `3`, receipts, ledger-ID, repository-ID og `READY` besto. API, web og database kom opp igjen, og HTTP-kontroll mot staging-web svarte `200`.

API/web har fortsatt ingen safety-ledger-/configmount, Borg-klient eller safety-/Borg-environment. Web har ingen media-mount. API har den eksisterende artifact-mounten `/srv/kreative-norge/media/public`, men ingen `public-delivery`-mount; øvelsen introduserte ingen serving, route eller public media. Hostens `/srv/kreative-norge/media/public-delivery/` finnes ikke.

`kreative-norge-image-safety-health.timer` er enabled og active. Manuell health-unit og final CLI-health returnerte exit `0`, `ready=true`, cursor `3` og pinned safety repository-ID. Syntetiske lokale testkopier og hjelpefiler ble fjernet etter verifikasjon; live-ledger, receipts og off-server evidensarkiver ble beholdt.

## Konklusjon og avgrensning

Alle obligatoriske pre-activation-gater for 3E.1A er grønne. Stagingstatus er derfor `ACTIVE` for:

- lokal safety-ledger og immutable receipts
- synkront verifisert dedikert off-server Borg-anchor
- separat incident/unknown transaction recovery
- fail-closed restore-, rebuild- og health-gate
- aktiv systemd health-monitorering

Dette aktiverer ikke public image runtime. Neste kodegate er 3E.1B materialisering og release-livssyklus etter egen oppgave/ADR-kontrakt; PR #36 skal forbli draft og ikke merges som del av denne aktiveringsøvelsen.
