# Public image safety ledger og restore-gate

**Status:** 3E.1A safety-ledger, dedikert off-server anchor og restore-gate er `ACTIVE` i staging fra 2026-08-20. 3E.1B-bro, socket, delivery og release-materialisering er `ACTIVE` i staging fra 2026-08-23; public serving er fortsatt av.

**Arkitektur:** [ADR-009](../decisions/ADR-009-PUBLIC_IMAGE_RUNTIME_RELEASE_DELIVERY_AND_RESTORE_SAFE_DENY_STATE.md)

Denne runbooken dokumenterer den aktive 3E.1A-runtimeen og 3E.1B-broen. Kommandoene aktiverer ikke i seg selv materialisering, serving, projection, API/PUBLIC-cutover eller formell takedown; faktisk stagingstatus følger de daterte evidensrapportene.

Faktisk 3E.1A-aktiveringsevidens, inkludert repository-separasjon, raw-`rm`-restrisiko, separat transaction recovery av probe og DENIED-head, restartpersistens og containerisolasjon, finnes i [stagingrapporten 2026-08-20](../status/STAGING_PHASE_3E1A_ACTIVATION_2026-08-20.md). Bridge-, peer-, mount- og delivery-backup-/restoreevidensen finnes i [3E.1B-foundationrapporten](../status/STAGING_PHASE_3E1B_FOUNDATION_2026-08-23.md), mens faktisk reserve/materialize/activate- og crash/retry-evidens finnes i [3E.1B-aktiveringsrapporten](../status/STAGING_PHASE_3E1B_MATERIALIZATION_ACTIVATION_2026-08-23.md).

## 1. Implementert kontrakt

`image_safety/` er en ren Python 3-/SQLite-komponent uten Django- eller PostgreSQL-avhengighet. Den implementerer:

- schema v1 med SQLite `application_id`, `user_version` og immutable metadata
- autoritative `release_reserved`, `release_activated`, `release_retired` og `release_denied`
- monotone sekvenser, unik event-ID, canonical JSON, SHA-256 payload og hashkjede
- samme event-ID + samme payload som retry; samme ID + annen payload som hard konflikt
- terminal `retired`/`denied`, permanent UUID-/key-reservasjon og avvisning av ugyldige overganger
- avledet `release_state`, permanent `reserved_release_keys` og en rebuildbar read-cursor
- immutable, lokalt verifiserte anchor receipts
- canonical ankervariant som inneholder hele eventhistorikken, ledger-ID, cursor og head-hash
- fail-closed `health` mot SQLite-integritet, schema/identity, full replay, read-model, cursor, repository-ID, siste ankercursor og eksakte bundle-bytes
- eksplisitt restore-assurance: `clean` eller `incident-recovered`; incident restore krever separat identifisert autoritativ cursor og full head-hash

`tenant_runtime_enrolled` og checksum-deny er ikke innført. Tenantvis runtimeaktivering er ikke en sikkerhetsgrense i 3E.1A, og checksum-deny tilhører 3E.4.

Reservation-input binder immutable heltalls-snapshots av tenant, Organization, selection, selection-revisjon og rendition-sett samt artifact key og SHA-256 for alle tre varianter. Caller leverer aldri public key; `image_safety.release_keys.build_public_release_key()` bygger eksakt `releases/<uuid>/<variant>.<ext>`. 3E.1B-workflowen lar bridge-reservasjonen eie UUID/keys og binder dem deretter til PostgreSQL uten å holde DB-lås under Borg-I/O.

Bridge-foundationen bruker systemd socket activation på `/run/kreative-norge-image-safety/bridge.sock`, ett lengde-prefikset JSON request/response-par per forbindelse og bare operasjonene `reserve` og `activate`. I staging er socketen verifisert `root:root` `0600`; API får bare read-only bindmount av runtime-directory, mens ledger, `/etc`-konfigurasjon og Borg-credentials forblir host-only. Et kontrollert kall fra API fikk domenerespons etter `SO_PEERCRED`-gaten og beviste dermed den faktiske Docker/Linux-root-peeren. Dette aktiverte ingen releaseoperasjon eller materialisering. Se [3E.1B-stagingrapporten](../status/STAGING_PHASE_3E1B_FOUNDATION_2026-08-23.md).

## 2. Execution- og credentialplassering

Valgt plassering er host/systemd:

- installert kode: `/usr/local/lib/kreative-norge-image-safety/`
- root-beskyttet konfigurasjon og writer-secret: `/etc/kreative-norge-image-safety/`
- persistent lokal ledger: `/var/lib/kreative-norge-image-safety/ledger.sqlite3`
- dedikert Borg cache/config/security: `/var/lib/kreative-norge-image-safety/borg/`
- synkron writer/anchor: root-kjørt, herdet oneshot på hosten
- separat fail-closed health-unit og valgfri femminutters health-timer

API- og web-containerne har ingen mount av disse områdene, ingen Borg-klient og ingen Storage Box-credential. Writeren skal bare ha en dedikert subaccount/repository og skal aldri bruke Storage Box main user, generell ADR-008-backupcredential eller recovery-/admincredential. Root-kjøring er valgt for å gjenbruke den etablerte systemd-/secretmodellen uten ny daemon, socket, sidecar eller nettverkstjeneste; remote credential er likevel avgrenset til det dedikerte safety-området. Kompromittert host-root er uttrykkelig utenfor garantien.

Credentialkontrakten har to separate sider:

**RUNTIME WRITER**

- dedikert safety-subaccount og dedikert ED25519 private key på hosten
- root-only Borg-passfrasefil på hosten
- minst mulig rettighet mot bare safety-repositoryet
- ingen Storage Box-subaccount-passord, main-/admincredential eller eksportert repository key

**RECOVERY/ADMIN**

- et unikt, sterkt tilfeldig passord for safety-subaccounten
- Storage Box main-/admintilgang
- eksportert kryptert Borg repository key
- Borg-passfrasen i off-server recovery-custody etter ADR-008-kontrakten
- ikke tilgjengelig for vanlig runtime; nødvendig recoverytilgang dokumenteres for minst to ansvarlige

Subaccount-passordet skal aldri ligge på stagingserveren, i `image-safety.env`, Git, logger, PR eller chat. Den automatiske writerflyten bruker bare den dedikerte ED25519-nøkkelen. At password authentication ikke kan deaktiveres hos Storage Box gjør denne separate menneskelige custodyen obligatorisk; ingen operatør skal lime inn passord eller andre secrets i terminaloutput eller evidens.

## 3. Commit- og crashgrenser

Hvert sikkerhetskritiske kall følger denne rekkefølgen:

1. valider og commit event + read-model atomisk i SQLite med `journal_mode=DELETE` og `synchronous=FULL`
2. eksporter canonical bundle for gjeldende head
3. verifiser eksakt forventet Borg repository-ID
4. opprett et deterministisk, aldri gjenbrukt arkivnavn
5. les `anchor.json` tilbake og krev byte-for-byte equality
6. append lokal immutable kvittering for cursor, head, repository, arkiv og bundle-checksum

Hvis steg 3–5 feiler, beholdes lokal event og health er `anchor_missing` eller `anchor_cursor_stale`. Hvis remote write lykkes og prosessen dør før steg 6, leser retry samme arkiv, krever identiske bytes og skriver kvitteringen. Samme arkivnavn med andre bytes er hard konflikt. Et nyere head kan ankre flere lokale events samlet; ingen av dem er runtime-klare før kvitteringen dekker gjeldende head.

## 4. Hva append-only betyr her

Safety-repositoryet skal opprettes med stabil Borg `>=1.2.8` og `<1.3.0` og `--append-only`, separat fra den aktive generelle backupen. Adapteren avviser eldre 1.2-versjoner, 1.3.x, 2.x, prerelease og malformed/ukjent versjonsoutput fail-closed uten environment-bypass. Borg dokumenterer at append-only forhindrer at Borg overskriver eller fysisk sletter committed segmentdata, men at modusen kan reverseres av en ubegrenset administrator. `delete`/`prune` kan skrive tombstones, og en senere ubegrenset write/compact kan fysisk fjerne data. Andre verktøy med rå filtilgang kan omgå Borg. Dette er derfor WORM-orientert skadebegrensning, ikke absolutt WORM.

Hetzner dokumenterer at en restricted Borg-klient fortsatt kan markere arkiver slettet, og at en ubegrenset klient senere kan gjøre slettingen fysisk. Storage Box main user har dessuten tilgang til subaccount-områder, og password authorization kan ikke deaktiveres. Løsningen beskytter ikke mot kompromittert Hetzner control plane, Storage Box main user, host-root eller en aktør som samtidig har writer- og admin/recoverytilgang.

Autoritative kilder kontrollert 2026-08-17:

- [Hetzner: SSH/rsync/BorgBackup og append-only](https://docs.hetzner.com/storage/storage-box/access/access-ssh-rsync-borg/)
- [Hetzner: subaccounts, main-user access og passwordbegrensning](https://docs.hetzner.com/storage/storage-box/general/)
- [Borg 1.2: append-only mode og recoverybegrensninger](https://borgbackup.readthedocs.io/en/1.2-maint/usage/notes.html#append-only-mode-forbid-compaction)

## 5. Forbered hosten

Fra deployet repo:

```bash
sudo /srv/kreative-norge-crm/ops/image_safety/install.sh prepare
sudo /usr/local/lib/kreative-norge-image-safety/install.sh generate-key
```

`prepare` kopierer kode, eksempelkonfigurasjon og systemd-units, men oppretter ikke repository eller ledger og aktiverer ingen timer. Kontroller at alle paths er utenfor Git, `/tmp`, containerlag, media-root og webroot.

Følgende krever prosjekteier/Storage Box-administrator og er **MANUAL REQUIRED**:

1. Opprett en dedikert Storage Box-subaccount og tomt `public-image-safety`-område; ikke bruk den generelle backupens repository.
2. Gi subaccounten et unikt, sterkt tilfeldig passord. Oppbevar det bare i separat admin/recovery-custody, aldri på runtimehosten eller i `image-safety.env`/Git/evidens.
3. Installer bare safety-writerens public ED25519-key for port 23. Behold main-user/admin og all recoverytilgang separat fra runtime writer.
4. Pin host key fra uavhengig Hetzner-kilde i den dedikerte `known_hosts`-filen.
5. Opprett en separat Borg-passfrasefil. Mens repository-ID står som eksplisitt 64 nuller i environmentfilen, initialiser et kryptert `repokey-blake2` repository med stabil Borg `>=1.2.8,<1.3.0` og `--append-only`:

   ```bash
   sudo /usr/local/lib/kreative-norge-image-safety/image-safety.sh repository-init
   ```

6. Skriv eksakt ID som kommandoen returnerer i root-only `image-safety.env`; repository-ID er ikke secret. Eksporter så kryptert repository key til en ny privat path:

   ```bash
   sudo /usr/local/lib/kreative-norge-image-safety/image-safety.sh repository-key-export \
     --destination /root/kreative-norge-image-safety-recovery-key.export
   ```

7. Overfør eksporten gjennom separat godkjent kanal og oppbevar eksport, Borg-passfrase, nødvendig Storage Box-identitet og subaccount-passord off-server med nødvendig recoverytilgang for minst to ansvarlige etter ADR-008. Verifiser rapportert checksum før den midlertidige eksporten fjernes; ingen kommando lover secure erase på SSD.
8. Gjennomfør capabilitytesten i punkt 8 før første reelle reservation.

Eksempelkonfigurasjonen i `ops/image_safety/image-safety.env.example` inneholder bare plassholdere. Filen og alle secrets skal være root-owned uten group/world access. Repository-ID er identitetslås, ikke secret.

## 6. Initialisering og operatorbruk

Etter at den dedikerte eksterne kjeden er ferdig:

```bash
sudo /usr/local/lib/kreative-norge-image-safety/image-safety.sh init
sudo /usr/local/lib/kreative-norge-image-safety/image-safety.sh health
```

`init` lager lokal ledger og synkront ankrer genesis/cursor 0. Reservation mottar en privat JSON-fil med bare bindinger og artifact-snapshots; service genererer release-UUID og public keys. Eksempelstruktur:

```json
{
  "tenant_id": 1,
  "organization_id": 2,
  "selection_id": 3,
  "selection_revision": 4,
  "rendition_set_id": 5,
  "renditions": [
    {"variant": "square", "output_format": "webp", "artifact_storage_key": "tenants/1/artifacts/example/square.webp", "artifact_checksum_sha256": "<64 lowercase hex>"},
    {"variant": "landscape", "output_format": "webp", "artifact_storage_key": "tenants/1/artifacts/example/landscape.webp", "artifact_checksum_sha256": "<64 lowercase hex>"},
    {"variant": "share", "output_format": "webp", "artifact_storage_key": "tenants/1/artifacts/example/share.webp", "artifact_checksum_sha256": "<64 lowercase hex>"}
  ]
}
```

```bash
sudo /usr/local/lib/kreative-norge-image-safety/image-safety.sh reserve \
  --reservation-file /root/private-reservation.json
```

Kommandoen deriverer canonical event-ID fra selection-identiteten og skriver bare ikke-sensitive event-/anchoridentiteter. Den valgfrie bakoverkompatible `--event-id` må være eksakt lik den deriverte ID-en. Hvis ankeringen feiler etter lokal commit, bruk identisk input; UUID/key gjenbrukes atomisk.

`activate`, `retire` og `deny` finnes i operator-CLI-et, men 3E.1B-broen eksponerer bare `reserve` og `activate`. `retire`/`deny`, public lifecycle-serving og formell takedown er ikke caller-aktivert og skal ikke brukes på reelle aktørbilder før sine senere faser er levert.

## 7. Health, replay og reconciliation

`health` returnerer JSON og exit 0 bare når ledger, replay/read-model, read-cursor og siste verifiserte off-server receipt dekker eksakt samme head og forventet repository-ID. Kjente fail-closed-koder inkluderer:

- `ledger_missing` / `ledger_invalid`
- `read_cursor_stale` / `read_model_mismatch`
- `anchor_missing` / `anchor_cursor_stale` / `anchor_bundle_mismatch`
- `repository_identity_mismatch`

Rebuild gjør bare avledet state på nytt:

```bash
sudo /usr/local/lib/kreative-norge-image-safety/image-safety.sh rebuild
sudo /usr/local/lib/kreative-norge-image-safety/image-safety.sh health
```

Reconciliation mot remote gjøres ved å ankre gjeldende head på nytt. Det kan fullføre manglende lokal ack etter en allerede vellykket remote write:

```bash
sudo systemctl start kreative-norge-image-safety-anchor.service
sudo systemctl start kreative-norge-image-safety-health.service
```

Health-timeren kan først aktiveres etter live restore-/capabilitygaten. Den er observability, ikke en erstatning for synkron anchor.

## 8. Obligatorisk live capability- og restoreøvelse

Bruk bare dedikert safety-repository og syntetiske eventer. Ikke bruk reelle aktørbilder og ikke kjør delete/compact mot ADR-008-backuprepositoryet.

Før første destructive probe skal operatøren gjennomføre og dokumentere denne repository-separasjonsgaten uten credentials:

1. les og verifiser safety-repositoryets pinned repository-ID med safety-writerens read-only inspect/info-flyt
2. les og verifiser det eksisterende ADR-008-backuprepositoryets pinned repository-ID med dets separate, skrivebeskyttede `inspect-repository`
3. registrer begge repository-ID-ene i stagingevidensen; ID-ene er identiteter, ikke secrets
4. assert eksplisitt at ID-ene er forskjellige og at safety-repositoryet er tomt/dedikert til image safety før genesis
5. stopp før `delete`, `compact`, raw `rm` eller annen muterende probe dersom én ID er ukjent, mismatchende, lik den andre eller repositoryformålet ikke kan bevises

Credentials, repositorypassfraser og nøkler skal aldri skrives i evidensen. Kontrollen bruker separate eksisterende credentialflater; ADR-008-credentialen skal ikke kopieres til image-safety-runtime.

Live stagingrapporten må dokumentere uten credentials:

1. eksakt repository-ID og at writer er dedikert subaccount, ikke main user
2. genesis + syntetisk reservation med synkron create/read-back/receipt
3. at samme arkivnavn med andre bytes avvises
4. en kontrollert delete-/compact-probe på bare det dedikerte safety-repositoryet:
   1. opprett et syntetisk probe-arkiv og verifiser at det kan leses
   2. marker probe-arkivet slettet med Borg `delete`
   3. verifiser og dokumenter faktisk append-only-adferd
   4. forsøk Borg `compact` med den dedikerte writeridentiteten og registrer kommandoens faktiske exit-status/resultat
   5. bruk separat admin/recoverytilgang og godkjent append-only recovery-prosedyre til å gjenopprette den tombstonede proben
   6. dokumenter forskjellen mellom Borg-logisk sletting og fysisk tilgjengelige segmentdata
5. om samme writer key/subaccount kan nå rå `rm` eller tilsvarende filoperasjoner; enhver slik capability registreres som rest-risiko, ikke skjules
6. isolert `restore-latest` til ny path, deretter `rebuild` og grønn `health`
7. eldre DB/appkopi mot nyere denied safety-ledger; nyere ledger skal vinne
8. korrupt ledger og stale cursor gir `NOT READY`
9. host-restart beholder ledger/receipts
10. API-/web-containerne mangler fortsatt safety-mount, Borg, secrets og public media

Den separate probe-testen over beholdes. I tillegg skal siste autoritative safety-head testes med bare syntetiske events:

1. opprett en synthetic reservation
2. ankre reservationen
3. aktiver releasen
4. ankre activation
5. opprett en nyere synthetic deny
6. ankre deny og noter eksakt cursor/full head-hash
7. bruk bare den dedikerte writeridentiteten til å tombstone det nyeste safety-anchorarkivet
8. dokumenter hva vanlig current-manifest/`list` viser etter tombstoning, inkludert det eldre høyeste synlige headet
9. behandle situasjonen som `INCIDENT / UNKNOWN`; forsøk `restore-latest --recovery-mode incident-recovered` med den noterte autoritative cursor/head-hashen og bevis at det stale synlige manifestet avvises før destination eller lokal receipt opprettes; ikke kjør eller godta `--recovery-mode clean`
10. bruk separat admin/recovery-custody og Borgs append-only transaction/recovery-prosedyre til å identifisere og recovere siste autoritative repository-state
11. verifiser at recovered manifest igjen inneholder det forventede deny-headet
12. kjør incident restore med eksakt forventet cursor/head, deretter `rebuild` og `health`
13. bevis at releasen fortsatt er `DENIED`
14. dokumenter cursor/head før delete, under tombstone og etter recovery

Hvis korrekt autoritativ cursor/head ikke kan identifiseres fra separat recovery, er resultatet `NOT READY`; current manifest eller et eldre synlig arkiv kan ikke brukes som erstatning.

Delete, compact eller rå filprobe må aldri kjøres mot ADR-008s ordinære backuprepository eller med reelle CRM-data/aktørbilder. Faktisk live-resultat skal holdes adskilt fra forventet Borg-kontrakt, og testen gir aldri grunnlag for å påstå absolutt WORM.

### Activation-gate

Status kan ikke endres til `ACTIVE` før alle disse gruppene er dokumentert grønne:

- **Repo/code:** Borg `>=1.2.8,<1.3.0` håndheves; image-safety-, backup-, relevante staging-/backendtester og CI er grønne.
- **Manuell ekstern kjede:** dedikert subaccount/repository; writer public key; unikt subaccount-passord bare i separat recovery/admin-custody; separat main/admin/recovery; pinned host key og repository-ID; eksportert recovery key; Borg-passfrase-recovery; nødvendig tilgang for minst to ansvarlige.
- **Repository-separasjon:** safety- og ADR-008-backuprepository-ID er begge verifisert og dokumentert forskjellige før destructive probe; safety-repositoryet er dedikert til image safety.
- **Live capability/restore:** genesis, syntetisk reservation, create/read-back/receipt, conflicting bytes-avvisning, delete-, compact- og raw-rm-prober, separat recovery av tombstonet probe, newest-safety-head tombstone med stale incident-restore-avvisning, append-only transaction recovery, restore/rebuild/health, `DENIED`-bevis, nyere deny over eldre app/DB-state, corruption/stale-cursor `NOT READY`, restartpersistens og fortsatt containerisolasjon.

Før disse punktene er grønne er off-server status `PREPARED / MANUAL REQUIRED`, public runtime forblir av, og fase 3E.1A kan ikke kalles live aktiv. Staging fullførte alle gruppene 2026-08-20; dette endrer ikke kravet for andre miljøer.

## 9. Clean restore og incident/unknown restore

Alle restoreforløp holder public runtime av og skriver til en ny, tom hostpath. Gammel DB, app, media eller lokal ledger er aldri autoritativ alene.

### A. CLEAN RESTORE

`clean` kan bare brukes når repository-integritet er verifisert, writer misuse/logisk deletion ikke mistenkes og operatøren har positivt grunnlag for at current manifest er komplett. Denne klassifiseringen er en eksplisitt operatørgate; vanlig `list` kan ikke bevise fravær av tombstonede nyere anchors.

```bash
sudo /usr/local/lib/kreative-norge-image-safety/image-safety.sh restore-latest \
  --recovery-mode clean \
  --destination /var/lib/kreative-norge-image-safety-restored/ledger.sqlite3
```

### B. INCIDENT / UNKNOWN RESTORE

Bruk denne flyten når lokal ledger er tapt/stale eller writer misuse, delete eller manifesttap ikke kan utelukkes:

1. Ikke bruk `clean`, og ikke behandle høyeste arkiv i current manifest som autoritativt.
2. Bruk separat admin/recovery-custody og Borgs append-only transaction/recovery-prosedyre til å identifisere og recovere siste autoritative safety-state.
3. Registrer den recoverede bundleens eksakte ikke-hemmelige cursor og fulle event-head-hash i incident-evidensen.
4. Kjør restore med disse forventningene:

   ```bash
   sudo /usr/local/lib/kreative-norge-image-safety/image-safety.sh restore-latest \
     --recovery-mode incident-recovered \
     --expected-authoritative-cursor '<recovered-cursor>' \
     --expected-authoritative-event-hash '<64-lowercase-hex>' \
     --destination /var/lib/kreative-norge-image-safety-restored/ledger.sqlite3
   ```

5. Kommandoen avviser manglende recoveryevidens eller cursor/head-mismatch før destination og lokal receipt opprettes. Uten identifiserbar autoritativ head forblir systemet `NOT READY`.

Etter begge flyter kjøres `rebuild` og `health`. Bytt ledgerpath kontrollert først etter checksum, owner/mode, repository-ID og isolert replay. Behold gammel fil i karantene. Staging beviste DB-/fil-/ledger-samsvar i 3E.1B-materialiseringsgaten; samme reconciliation må gjentas etter en reell incident restore før serving kan åpnes.

Full katastrofe-RTO er fortsatt uavklart frem til liveøvelsen er målt.

## 10. Rollback og avgrensning

Rollback av 3E.1A deaktiverer bare safety-runtimekoblingen og eventuelt health-timeren; den sletter aldri ledger, receipts eller off-server archives. Rollback av 3E.1B betyr at materialiseringsflagget settes til `False` slik at nye release-workflows stoppes. Eksisterende reservations-/activationevents, databaseaggregater og delivery-filer slettes aldri som rollback. Etter første reelle reservation er schemaendringer fremoverrettede.

Den historiske 3E.1A-leveransen opprettet ingen delivery-root eller mediafiler. 3E.1B har senere opprettet den separate delivery-rooten og materialisert én permanent syntetisk release med tre filer i staging. Ingen av leveransene har lagt til nginx-/Caddy-serving, public serializer/HTML/head/fallback/cache, checksum-deny, Redis, ekstern database, kø, sidecar, S3 eller CDN.
