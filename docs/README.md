# Kreative Norge CRM – dokumentasjon

Denne mappen er prosjektets levende dokumentasjonskilde.

## Leserekkefølge

1. `status/PROJECT_STATUS_CURRENT.md` – kort nåstatus
2. `status/ROADMAP.md` – strategisk rekkefølge
3. relevant dokument under `architecture/` – hvordan systemet faktisk er bygget
4. relevant dokument under `features/` – produktkrav og ønsket brukeropplevelse
5. `decisions/` – viktige arkitekturvalg
6. `operations/` – aktive og forberedte driftsprosedyrer
7. `development/FREDRIK_DEVELOPMENT_SYSTEM.md` – prosjektets utviklingsplattform
8. `development/` – arbeidsflyt, Skill Pack, eksempler, testing og deploy

## Grunnregel

Kode, migrasjoner, aktive API-ruter og verifisert staging-adferd er teknisk fasit. Dokumentasjon skal skille tydelig mellom:

- implementert
- delvis implementert
- planlagt
- historisk
- uavklart

## Vedlikehold

- Codex oppdaterer teknisk status etter større implementeringsøkter.
- ChatGPT og prosjekteier avklarer arkitektur, prioriteringer og beslutninger.
- Større implementeringer skal bygge på et godkjent ADR.
- Ingen feature regnes som ferdig før relevant dokumentasjon er oppdatert.
- Eldre dokumenter beholdes til gyldig innhold er kontrollert og flyttet.

Se også `development/DOCUMENTATION_RULES.md`, `development/WORKFLOW.md` og `development/FREDRIK_SKILL_PACK.md`.

For kontinuitet mellom ChatGPT og Codex, se `development/CHATGPT_SESSION_CONTINUITY.md` og `development/CHATGPT_SESSION_SUMMARY_TEMPLATE.md`.

Operativ safety-kontrakt finnes i `operations/PUBLIC_IMAGE_SAFETY_LEDGER.md`. Safety-ledger, dedikert off-server anchor og restore-gate fra 3E.1A er `ACTIVE` i staging. 3E.1B.1–3E.1B.2-materialisering og 3E.1C kontrollert Django/Nginx-serving er også `ACTIVE`. Fase 3E.2 er `CLOSED / SHADOW VERIFIED`, og fase 3E.3 er `CLOSED / ACTIVE`: target-API, PUBLIC, canonical, Open Graph/Twitter og production fallback v1 bruker samme projection i staging. Fase 3E.4 er `CLOSED / ACTIVE` etter ledger-v2-upgrade, permanent syntetisk deny, rollback, mediarestore, sikker republisering, restart og backup/restore. Fase 3F og hele fase 3 er `CLOSED / VERIFIED` etter legacyinventar, typed Import-kontrakt, no-network, restore og orphan-gate; `IMPORT_IMAGE_DECISIONS_ENABLED` er fortsatt av i shared staging. Fase 4A er dokumentert i foreslått [ADR-010](decisions/ADR-010-INTERNATIONAL_PHONE_IDENTITY_AND_NORMALIZATION.md), men telefonarkitekturen er ikke implementert og 4B har ikke startet. Kode- og eksempelstandardene for alle runtime-/write-gater er fortsatt `False`; bare de sju 3E-gatene er aktivert i den ignorerte stagingkonfigurasjonen. Staging har fire release-aggregater og ni delivery-filer; den denied releasen har ingen originfiler. Se [3E.2-evidensen](status/STAGING_PHASE_3E2_SHADOW_2026-08-24.md), [3E.3-cutoverevidensen](status/STAGING_PHASE_3E3_CUTOVER_2026-08-24.md), [3E.4-takedownevidensen](status/STAGING_PHASE_3E4_TAKEDOWN_2026-08-24.md) og [3F-evidensen](status/STAGING_PHASE_3F_LEGACY_IMPORT_2026-08-25.md).
