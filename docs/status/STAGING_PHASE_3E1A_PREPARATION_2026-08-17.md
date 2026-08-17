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

- 25 ledger-/idempotency-/transition-/concurrency-/corruption-/crash-/restore-/credential-/placement-/repository-bootstrap-/Borg-versjonstester: grønn lokalt og i Linux-container; forrige PR-head hadde 23 grønne tester i GitHub CI før de to additive versjonstestene
- 26 eksisterende image release-/migrationtester: grønn mot lokal PostgreSQL
- 372 backendtester: grønn på ren lokal PostgreSQL-testdatabase
- 4 stagingkontrakttester: grønn
- 68 eksisterende backup foundation-tester: grønn
- 28 frontendtester og production build: grønn
- ShellCheck for begge nye shellskript: grønn i container
- systemd-analyze for nye services/timer: grønn i isolert Ubuntu 24.04-container
- installerens root:root `0600` config, `0700` state og installpaths: grønn i isolert Ubuntu 24.04-container
- API- og web-produksjonsimages: bygget grønt som `phase3e1a-verify`
- alle seks PR-jobber i CI-run `32066750063`: grønn på implementasjonscommit `c75acc13bcec902752f19c07d8800f1353b364ab`

Pre-activation-reviewen er lokalt lukket med eksakt Borg `>=1.2.8,<1.3.0`, eksplisitt runtime/recovery-custody og obligatorisk compact-probe. Ny PR-CI må være grønn på reviewcommitten før denne kode-/dokumentasjonsgaten er ferdig.

Draft-PR #36 er opprettet uten merge. Den eksterne manuelle staginggaten under er fortsatt uendret.

## Hvorfor staging ikke er aktivert

Den eksisterende ADR-008 Storage Box-repositoryen er nattlig generell backup og skal ikke brukes eller muteres som safety-anchor. 3E.1A krever en dedikert Storage Box-subaccount, tomt append-only Borg-repository, separat writer key/passphrase/recovery custody og en kontrollert live capability-/restoreøvelse. Den lokale adapteren skal håndheve samme stabile Borg-vindu som ADR-008: `>=1.2.8,<1.3.0`. Disse eksterne ressursene finnes ikke dokumentert som tilgjengelige for denne leveransen.

Ingen hemmelighet er opprettet, flyttet, vist eller lagret i Git. Ingen serverfil, systemd-unit, timer, database, container eller Storage Box-arkiv er endret. Public bilde-runtime er fortsatt av.

## Eksakt eierliste – MANUAL REQUIRED

Prosjekteier/Storage Box-administrator må:

1. opprette dedikert subaccount/repository og installere bare writerens public ED25519-key
2. lagre et unikt subaccount-passord, main/admin, Borg recovery key og nødvendig passfraserecovery i separat off-server custody for minst to ansvarlige; aldri på runtimehosten
3. kontrollere og pinne host key og repository-ID
4. kjøre den syntetiske capability-/delete-/compact-/raw-rm-/restoreøvelsen i [runbooken](../operations/PUBLIC_IMAGE_SAFETY_LEDGER.md#8-obligatorisk-live-capability--og-restoreøvelse)
5. dokumentere faktisk compact-exit-status og separat recovery av tombstonet probe
6. godkjenne at dokumenterte Borg/Hetzner-begrensninger er akseptable

Først deretter kan hostmodulen installeres, genesis ankres og status endres til `ACTIVE`. Det kreves ingen reell aktør eller public fil for øvelsen.
