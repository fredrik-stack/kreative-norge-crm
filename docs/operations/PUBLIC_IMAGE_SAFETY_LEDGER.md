# Public image safety ledger og restore-gate

**Status:** kode og host-oppsett `PREPARED`; dedikert off-server repository og live stagingbevis `MANUAL REQUIRED`

**Arkitektur:** [ADR-009](../decisions/ADR-009-PUBLIC_IMAGE_RUNTIME_RELEASE_DELIVERY_AND_RESTORE_SAFE_DENY_STATE.md)

Denne runbooken gjelder bare fase 3E.1A. Den aktiverer ikke public bytes, materialisering, serving, projection, API/PUBLIC-cutover eller formell takedown.

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

`tenant_runtime_enrolled` og checksum-deny er ikke innført. Tenantvis runtimeaktivering er ikke en sikkerhetsgrense i 3E.1A, og checksum-deny tilhører 3E.4.

Reservation-input binder immutable heltalls-snapshots av tenant, Organization, selection, selection-revisjon og rendition-sett samt artifact key og SHA-256 for alle tre varianter. Caller leverer aldri public key; `image_safety.release_keys.build_public_release_key()` bygger eksakt `releases/<uuid>/<variant>.<ext>`. Dagens `create_organization_image_release()` er fortsatt DB-only, genererer selv UUID og gjør ingen ledger-, anchor-, storage- eller publiserings-I/O. Koblingen fra en ankret reservasjon til DB-aggregatet kommer i 3E.1B.

## 2. Execution- og credentialplassering

Valgt plassering er host/systemd:

- installert kode: `/usr/local/lib/kreative-norge-image-safety/`
- root-beskyttet konfigurasjon og writer-secret: `/etc/kreative-norge-image-safety/`
- persistent lokal ledger: `/var/lib/kreative-norge-image-safety/ledger.sqlite3`
- dedikert Borg cache/config/security: `/var/lib/kreative-norge-image-safety/borg/`
- synkron writer/anchor: root-kjørt, herdet oneshot på hosten
- separat fail-closed health-unit og valgfri femminutters health-timer

API- og web-containerne har ingen mount av disse områdene, ingen Borg-klient og ingen Storage Box-credential. Writeren skal bare ha en dedikert subaccount/repository og skal aldri bruke Storage Box main user, generell ADR-008-backupcredential eller recovery-/admincredential. Root-kjøring er valgt for å gjenbruke den etablerte systemd-/secretmodellen uten ny daemon, socket, sidecar eller nettverkstjeneste; remote credential er likevel avgrenset til det dedikerte safety-området. Kompromittert host-root er uttrykkelig utenfor garantien.

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

Safety-repositoryet skal opprettes med Borg 1.2 `--append-only` og være separat fra den aktive generelle backupen. Borg dokumenterer at append-only forhindrer at Borg overskriver eller fysisk sletter committed segmentdata, men at modusen kan reverseres av en ubegrenset administrator. `delete`/`prune` kan skrive tombstones, og en senere ubegrenset write/compact kan fysisk fjerne data. Andre verktøy med rå filtilgang kan omgå Borg. Dette er derfor WORM-orientert skadebegrensning, ikke absolutt WORM.

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
2. Installer bare safety-writerens public key for port 23. Behold main-user/admin og eventuell recoverytilgang i separat custody.
3. Pin host key fra uavhengig Hetzner-kilde i den dedikerte `known_hosts`-filen.
4. Opprett en separat Borg-passfrasefil. Mens repository-ID står som eksplisitt 64 nuller i environmentfilen, initialiser et kryptert `repokey-blake2` repository med Borg 1.2 `--append-only`:

   ```bash
   sudo /usr/local/lib/kreative-norge-image-safety/image-safety.sh repository-init
   ```

5. Skriv eksakt ID som kommandoen returnerer i root-only `image-safety.env`; repository-ID er ikke secret. Eksporter så kryptert repository key til en ny privat path:

   ```bash
   sudo /usr/local/lib/kreative-norge-image-safety/image-safety.sh repository-key-export \
     --destination /root/kreative-norge-image-safety-recovery-key.export
   ```

6. Overfør eksporten gjennom separat godkjent kanal og oppbevar eksport + passfrase off-server med minst to ansvarlige, separat fra writercredentialen. Verifiser rapportert checksum før den midlertidige eksporten fjernes; ingen kommando lover secure erase på SSD.
7. Gjennomfør capabilitytesten i punkt 8 før første reelle reservation.

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
  --event-id '<stable-idempotency-id>' \
  --reservation-file /root/private-reservation.json
```

Kommandoen skriver bare ikke-sensitive event-/anchoridentiteter. Hvis ankeringen feiler etter lokal commit, bruk samme event-ID og identisk input. Ikke generer en ny event-ID som workaround.

`activate`, `retire` og `deny` finnes for domenetesting, men public lifecycle og formell takedown er ikke aktivert. De skal ikke brukes på reelle aktørbilder før sine senere faser er levert.

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

Live stagingrapporten må dokumentere uten credentials:

1. eksakt repository-ID og at writer er dedikert subaccount, ikke main user
2. genesis + syntetisk reservation med synkron create/read-back/ack
3. at overwrite av eksisterende arkivnavn med andre bytes avvises
4. faktisk Borg delete-adferd med et separat probe-arkiv, inkludert at sletting bare blir tombstone i append-only-modus
5. om samme writer key kan nå rå `rm`/andre protokoller; enhver slik capability skal registreres som begrensning
6. admin/recovery fra separat custody og restore av tombstonet probe etter Borgs append-only-prosedyre
7. isolert `restore-latest` til ny path, deretter `rebuild` og grønn `health`
8. eldre DB/appkopi mot nyere denied safety-ledger; nyere ledger skal vinne
9. korrupt ledger og stale cursor gir `NOT READY`
10. host-restart beholder ledger/receipt, mens API-/web-containerne fortsatt mangler safety-mount, Borg og public media

Før disse punktene er grønne er off-server status `PREPARED / MANUAL REQUIRED`, public runtime forblir av, og fase 3E.1A kan ikke kalles live aktiv.

## 9. Restore etter hendelse

1. Hold public runtime av; start aldri fra gammel DB eller gammel lokal ledger alene.
2. Skaff dedikert writer-read eller separat recoverytilgang og verifiser repository-ID.
3. Restore siste gyldige safety-anchor til en ny, tom hostpath:

   ```bash
   sudo /usr/local/lib/kreative-norge-image-safety/image-safety.sh restore-latest \
     --destination /var/lib/kreative-norge-image-safety-restored/ledger.sqlite3
   ```

4. Kjør rebuild og health mot den restaurerte filen.
5. Sammenlign remote cursor/head med enhver eldre lokal/DB/appkopi. Remote nyere reservation/retirement/deny vinner alltid.
6. Bytt ledgerpath kontrollert først etter checksum, owner/mode, repository-ID og isolert replay er verifisert. Behold gammel fil i karantene; ikke slett journalhistorikk.
7. 3E.1B+ må senere reconcile DB og filer mot safety-ledger før serving kan åpnes.

Full katastrofe-RTO er fortsatt uavklart frem til liveøvelsen er målt.

## 10. Rollback og avgrensning

Rollback deaktiverer bare senere runtimekobling og health-timer. Den sletter aldri ledger, receipts eller off-server archives. Etter første reelle reservation er schemaendringer fremoverrettede.

Denne leveransen oppretter ingen delivery-root, skriver ingen mediafiler, endrer ingen nginx/Caddy-route, rydder ingen route-duplikat, endrer ingen public serializer/HTML/head/fallback/cache og innfører ingen checksum-deny, Redis, ekstern database, kø, sidecar, S3 eller CDN.
