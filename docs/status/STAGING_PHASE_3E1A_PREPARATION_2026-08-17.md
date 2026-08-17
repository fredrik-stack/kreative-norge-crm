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

- 23 ledger-/idempotency-/transition-/concurrency-/corruption-/crash-/restore-/credential-/placement-/repository-bootstraptester: grønn lokalt; 22 av disse var også grønne i Linux-container før den siste additive bootstrapkontrakttesten
- 26 eksisterende image release-/migrationtester: grønn mot lokal PostgreSQL
- 372 backendtester: grønn på ren lokal PostgreSQL-testdatabase
- 4 stagingkontrakttester: grønn
- 68 eksisterende backup foundation-tester: grønn
- 28 frontendtester og production build: grønn
- ShellCheck for begge nye shellskript: grønn i container
- systemd-analyze for nye services/timer: grønn i isolert Ubuntu 24.04-container
- installerens root:root `0600` config, `0700` state og installpaths: grønn i isolert Ubuntu 24.04-container
- API- og web-produksjonsimages: bygget grønt som `phase3e1a-verify`

GitHub CI registreres i PR-en før mergevurdering.

## Hvorfor staging ikke er aktivert

Den eksisterende ADR-008 Storage Box-repositoryen er nattlig generell backup og skal ikke brukes eller muteres som safety-anchor. 3E.1A krever en dedikert Storage Box-subaccount, tomt append-only Borg-repository, separat writer key/passphrase/recovery custody og en kontrollert live capability-/restoreøvelse. Disse eksterne ressursene finnes ikke dokumentert som tilgjengelige for denne leveransen.

Ingen hemmelighet er opprettet, flyttet, vist eller lagret i Git. Ingen serverfil, systemd-unit, timer, database, container eller Storage Box-arkiv er endret. Public bilde-runtime er fortsatt av.

## Eksakt eierliste – MANUAL REQUIRED

Prosjekteier/Storage Box-administrator må:

1. opprette dedikert subaccount og safety-repository
2. installere writer public key og separat admin/recovery custody
3. kontrollere host key og repository-ID
4. kjøre den syntetiske capability-/delete-/restoreøvelsen i [runbooken](../operations/PUBLIC_IMAGE_SAFETY_LEDGER.md#8-obligatorisk-live-capability--og-restoreøvelse)
5. godkjenne at dokumenterte Borg/Hetzner-begrensninger er akseptable

Først deretter kan hostmodulen installeres, genesis ankres og status endres til `ACTIVE`. Det kreves ingen reell aktør eller public fil for øvelsen.
