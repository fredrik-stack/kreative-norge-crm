# Staging – fase 3E.1A safety ledger

**Dato:** 2026-08-17

**Status:** `PREPARED / MANUAL REQUIRED` – ingen live aktivering

## Levert og verifisert lokalt

- ren SQLite schema v1-ledger med fire lifecycleevents, canonical payload og hashkjede
- rebuildbar read-model/cursor og immutable anchor receipts
- synkron anchorprotokoll med repository-ID, deterministic archive, create/read-back og crash-retry
- standalone remote bundle restore uten Django/PostgreSQL
- fail-closed health for manglende, korrupt, stale, mismatched og ikke-ankret state
- host/systemd-installer, environmentmal, anchor-unit og health-unit/timer
- delt canonical key-builder; eksisterende DB-only release-service og signatur er uendret
- ingen Compose-mount, Borg-credential eller public media i API/web

Målrettet lokal evidens ved dokumenttidspunkt:

- 27 ledger-/idempotency-/transition-/concurrency-/corruption-/crash-/clean-/incident-restore-/credential-/placement-/repository-bootstrap-/Borg-versjonstester: grønn lokalt og i Linux-container; 25 av disse var også grønne i CI-run `32069227961` på head `905ef93f1d17ef82d6bf12902383d8b2e6d66780` før de to additive incident-restoretestene
- 26 eksisterende image release-/migrationtester: grønn mot lokal PostgreSQL
- 372 backendtester: grønn på ren lokal PostgreSQL-testdatabase
- 4 stagingkontrakttester: grønn
- 68 eksisterende backup foundation-tester: grønn
- 28 frontendtester og production build: grønn
- ShellCheck for begge nye shellskript: grønn i container
- systemd-analyze for nye services/timer: grønn i isolert Ubuntu 24.04-container
- installerens root:root `0600` config, `0700` state og installpaths: grønn i isolert Ubuntu 24.04-container
- API- og web-produksjonsimages: bygget grønt som `phase3e1a-verify`
- alle seks PR-jobber i CI-run `32069227961`: grønn på head `905ef93f1d17ef82d6bf12902383d8b2e6d66780`

Pre-activation-reviewen på denne headen er lukket med eksakt Borg `>=1.2.8,<1.3.0`, eksplisitt runtime/recovery-custody og obligatorisk compact-probe. Den siste restore-gaten legger i neste reviewcommit til eksplisitt clean/incident restore og stale-head-avvisning; ny PR-CI må være grønn på den committen før kodegaten er ferdig.

Draft-PR #36 er opprettet uten merge. Den eksterne manuelle staginggaten under er fortsatt uendret.

## Hvorfor staging ikke er aktivert

Den eksisterende ADR-008 Storage Box-repositoryen er nattlig generell backup og skal ikke brukes eller muteres som safety-anchor. 3E.1A krever en dedikert Storage Box-subaccount, tomt append-only Borg-repository, separat writer key/passphrase/recovery custody og en kontrollert live capability-/restoreøvelse. Den lokale adapteren skal håndheve samme stabile Borg-vindu som ADR-008: `>=1.2.8,<1.3.0`. Disse eksterne ressursene finnes ikke dokumentert som tilgjengelige for denne leveransen.

Ingen hemmelighet er opprettet, flyttet, vist eller lagret i Git. Ingen serverfil, systemd-unit, timer, database, container eller Storage Box-arkiv er endret. Public bilde-runtime er fortsatt av.

## Eksakt eierliste – MANUAL REQUIRED

Prosjekteier/Storage Box-administrator må:

1. opprette dedikert subaccount/repository og installere bare writerens public ED25519-key
2. lagre et unikt subaccount-passord, main/admin, Borg recovery key og nødvendig passfraserecovery i separat off-server custody for minst to ansvarlige; aldri på runtimehosten
3. kontrollere og pinne host key og repository-ID
4. verifisere og dokumentere at safety-repository-ID er forskjellig fra ADR-008-backuprepository-ID før destructive probe
5. kjøre den syntetiske capability-/delete-/compact-/raw-rm-/newest-head-/restoreøvelsen i [runbooken](../operations/PUBLIC_IMAGE_SAFETY_LEDGER.md#8-obligatorisk-live-capability--og-restoreøvelse)
6. dokumentere faktisk compact-exit-status, stale incident-restore-avvisning og separat recovery av tombstonet probe/deny-head
7. godkjenne at dokumenterte Borg/Hetzner-begrensninger er akseptable

Først deretter kan hostmodulen installeres, genesis ankres og status endres til `ACTIVE`. Det kreves ingen reell aktør eller public fil for øvelsen.
