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

Operativ safety-kontrakt finnes i `operations/PUBLIC_IMAGE_SAFETY_LEDGER.md`. Safety-ledger, dedikert off-server anchor og restore-gate fra 3E.1A er `ACTIVE` i staging. 3E.1B.1–3E.1B.2 er implementert i kode som feature-avslått bridge-/delivery-/materialiseringsgrunnmur, men er ikke stagingaktivert. Public serving og fase 3E.1C–3E.4 er fortsatt ikke implementert eller aktivert.
