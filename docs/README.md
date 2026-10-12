# Kreative Norge CRM – dokumentasjon

Denne mappen er prosjektets levende dokumentasjonskilde.

## Import 2.0 – godkjent UX-grunnlag fra fase 5D

[Brukertestrapporten](status/PHASE_5D_USER_TEST_REPORT_2026-10-11.md) og
[UX-spesifikasjon v6, revisjon 4](features/IMPORT_2_0_UX_SPEC_V6.md) dokumenterer
owner-approved intern validering med to formelle kollegadeltakere og
prosjekteiers egen gjennomgang. R12/O-24 lukket UX-grunnlaget 2026-10-12:
alle fire jobbregelgrupper er tilgjengelige ved Filtrerte kandidater, og de tre
feltfiltrene beholdes. Ingen ny manuell prototypetest eller formell brukertest
gjenstår som gate.

Dokumentene lagres på `docs/phase5d-ux-v6-close` for én draft PR og separat
review; merge er ikke utført, og dokumentene finnes ennå ikke på `main`.
Etter dokumentasjonsleveransen og ny kontroll av fersk main følger read-only
5E med en beslutningsklar implementerings- og testplan. 5E er ikke startet
eller godkjent. Import 2.0 og ADR-011/012 er fortsatt målarkitektur uten
runtimeimplementering. Browser-aktiv Codex forblir en hard gate ved senere UI.

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

Operativ safety-kontrakt finnes i `operations/PUBLIC_IMAGE_SAFETY_LEDGER.md`. Safety-ledger, dedikert off-server anchor og restore-gate fra 3E.1A er `ACTIVE` i staging. 3E.1B.1–3E.1B.2-materialisering og 3E.1C kontrollert Django/Nginx-serving er også `ACTIVE`. Fase 3E.2 er `CLOSED / SHADOW VERIFIED`, og fase 3E.3 er `CLOSED / ACTIVE`: target-API, PUBLIC, canonical, Open Graph/Twitter og production fallback v1 bruker samme projection i staging. Fase 3E.4 er `CLOSED / ACTIVE` etter ledger-v2-upgrade, permanent syntetisk deny, rollback, mediarestore, sikker republisering, restart og backup/restore. Fase 3F og hele fase 3 er `CLOSED / VERIFIED` etter legacyinventar, typed Import-kontrakt, no-network, restore og orphan-gate; `IMPORT_IMAGE_DECISIONS_ENABLED` er fortsatt av i shared staging. Hele [ADR-010](decisions/ADR-010-INTERNATIONAL_PHONE_IDENTITY_AND_NORMALIZATION.md) fase 4A–4H er implementert og [teknisk stagingverifisert](status/STAGING_PHASE_4H_PHONE_TECHNICAL_VERIFICATION_2026-08-26.md) med additiv telefonidentitet, Editor, Import, kontrollert backfill og full backup/restore. Tre funn fra første owner-smoke er [rettet og teknisk reverifisert i staging](status/STAGING_PHASE_4_OWNER_SMOKE_REMEDIATION_2026-08-29.md). Tre UI-polishpunkter fra andre owner-smoke er [implementert og teknisk stagingreverifisert](status/STAGING_PHASE_4_OWNER_SMOKE_UI_POLISH_2026-08-29.md). Prosjekteier [godkjente siste manuelle kontroll 2026-08-29](status/PHASE_4_OWNER_APPROVAL_2026-08-29.md). `PHASE 4 = CLOSED / VERIFIED`, og ADR-010 er implementert innen avtalt fase-4-scope. Fase 5A er fullført som read-only planleggingsgrunnlag. [ADR-011](decisions/ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md) og [ADR-012](decisions/ADR-012-PLACE_IDENTITY_GEOGRAPHIC_CLASSIFICATION_AND_ACTOR_ONLY_MAPS.md) er godkjent målarkitektur for henholdsvis canonical sharing og provider-nøytrale steder/actor-only kart. De er **ikke implementert**; dagens direkte tenantmodell og fritekststeder gjelder fortsatt. PersonPlace er strukturert målmodell uten kart. Ingen produksjonssetting er utført. Full ADR-005 er fortsatt ikke implementert: global `PersonContact.is_public` sammen med aktørspesifikk `publish_person` er mellommodellen frem til relasjonsspesifikk kontaktpublisering i en senere fase. Kode- og eksempelstandardene for runtime-/write-gater er fortsatt konservative; de aktive 3E-gatene finnes bare i ignorert stagingkonfigurasjon. Staging har fire release-aggregater og ni delivery-filer; den denied releasen har ingen originfiler. Se [3E.2-evidensen](status/STAGING_PHASE_3E2_SHADOW_2026-08-24.md), [3E.3-cutoverevidensen](status/STAGING_PHASE_3E3_CUTOVER_2026-08-24.md), [3E.4-takedownevidensen](status/STAGING_PHASE_3E4_TAKEDOWN_2026-08-24.md), [3F-evidensen](status/STAGING_PHASE_3F_LEGACY_IMPORT_2026-08-25.md), [4B-evidensen](status/STAGING_PHASE_4B_PHONE_BASELINE_2026-08-25.md), [4C-evidensen](status/STAGING_PHASE_4C_PHONE_NORMALIZATION_2026-08-25.md), [4H-sluttevidensen](status/STAGING_PHASE_4H_PHONE_TECHNICAL_VERIFICATION_2026-08-26.md), [owner-smoke-remediationen](status/STAGING_PHASE_4_OWNER_SMOKE_REMEDIATION_2026-08-29.md), [siste UI-polish](status/STAGING_PHASE_4_OWNER_SMOKE_UI_POLISH_2026-08-29.md), [endelig owner-approval](status/PHASE_4_OWNER_APPROVAL_2026-08-29.md) og [fase 5 impactgrunnlaget](status/PHASE_5_SHARING_DOMAIN_IMPACT_2026-08-30.md).
