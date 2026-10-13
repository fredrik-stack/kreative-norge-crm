# Kreative Norge CRM – dokumentasjon

Denne mappen er prosjektets levende dokumentasjonskilde.

## Import 2.0 – godkjent UX og implementeringsplan

[5D-brukertestrapporten](status/PHASE_5D_USER_TEST_REPORT_2026-10-11.md) og
[UX v6 revisjon 4](features/IMPORT_2_0_UX_SPEC_V6.md), med R12/O-24, er
owner-approved og merget gjennom [PR #73](https://github.com/fredrik-stack/kreative-norge-crm/pull/73).
To formelle kollegadeltakere og prosjekteiers gjennomgang er intern validering,
ikke en gjennomført fempersonersplan.

[Fase 5E-planen](status/PHASE_5E_IMPLEMENTATION_AND_TEST_PLAN_2026-10-13.md) er **FULLFØRT / OWNER-APPROVED SOM PLAN**
2026-10-13. [ADR-013](decisions/ADR-013-IMPORT_2_0_EXECUTION_AND_COMMIT_CONTRACT.md) er godkjent målarkitektur for
importkontrakten. 6A deling/tilgang → 6B kontakter/relasjoner → 6C stedskjerne →
7A–7E Import 2.0 er vedtatt; privat importstorage kan forberedes parallelt.
[ADR-012 §28](decisions/ADR-012-PLACE_IDENTITY_GEOGRAPHIC_CLASSIFICATION_AND_ACTOR_ONLY_MAPS.md#28-migreringsrekkefølge)
lar stedskjerne/STEDER/import leveres før separate koordinat-/provider-/kartleveranser.

Denne plan-/ADR-dokumentasjonen er lagret på `docs/phase5e-approved-plan` og leveres gjennom [PR #74](https://github.com/fredrik-stack/kreative-norge-crm/pull/74). Skrivebeskyttet review er gjennomført uten blokkerende funn; prosjekteier har bestilt kontrollert merge 2026-10-13. Faktisk mergestatus og CI følger PR-en i GitHub. Nye runtimeleveranser
er **IKKE STARTET**; ADR-011/012 og full ADR-005 forblir målarkitektur der de
ikke er implementert. Ingen ny formell brukertest, manuell prototyperunde eller
obligatorisk kollegatest; tekniske tester, browser-aktiv Codex før senere UI og
relevant staging-/eiergodkjenning består. Kontrollert dokumentasjonsmerge er bestilt; senere implementering krever separat avgrenset bestilling.

**Historisk videreføringsstatus før merge/staging 2026-10-13:** 6A.1-skjema er implementert og testet i leveranse gjennom [PR #75](https://github.com/fredrik-stack/kreative-norge-crm/pull/75), med gjennomført review og bestilt kontrollert merge på `feat/phase6a1-domain-assignment-foundation`. Shared funksjoner er ikke aktivert; ingen staging eller deploy på dette tidspunktet. Dette oppdaterer leveransestatusen etter 5E-leveransen ovenfor, som beskriver main-baselinen. Se [datamodellen](architecture/DATA_MODEL.md) og [prosjektstatus](status/PROJECT_STATUS_CURRENT.md).

**Historisk første stagingutføring 2026-10-13:** 0033 er anvendt, men ny API-deploy ble avbrutt av Compose `ContainerConfig`. Gammel API er gjenopprettet; full 6A.1-stagingverifikasjon er ikke fullført på dette tidspunktet. Ingen backfill eller delingsaktivering. Se [lokal evidens](status/STAGING_PHASE_6A1_SCHEMA_VERIFICATION_2026-10-13.md).

**Historisk status etter recovery 2026-10-13, avsluttet 17:41:33 UTC / 19:41:33 CEST:** PR #75 er merget på `b2d4725e8547f49c39256db188107f2ed29ed93c`, og eksakt målimage kjører etter ett API-only recreate med kommandoavgrenset Compose API 1.44. 0033, legacydata, media/static og safety er bevart; nye pre/post-checkpoints er fullverifisert og isolert restore-verifisert uten prune/compact. Backup-timeren er gjenopptatt og skrivefrysen opphevet. **6A.1 er delvis stagingverifisert:** autorisert Editor-/admin-HTTP er uavklart, og ekstern HTTPS møter Cloudflare-challenge. Ingen backfill eller deling. [Recoveryevidens](status/STAGING_PHASE_6A1_SCHEMA_VERIFICATION_2026-10-13.md#kontrollert-api-recovery-2026-10-13) og de seks dokumentendringene er fortsatt bare lokale, ustagede og ikke committet.

**Gjeldende 6A.1-status, eierbekreftelse mottatt 2026-10-13:** STAGING VERIFIED / OWNER-CONFIRMED innen avtalt additiv skjemagrunnmur/API-runtime. Reviewede tekniske bevis og prosjekteiers fullførte manuelle lesekontroll dekker samlet de avtalte kontrollene; ingen ny agenttest eller stagingkjøring er utført. Ingen backfill/shared-aktivering eller ferdigmelding av hele 6A. [Eierbekreftelse og bevisnivå](status/STAGING_PHASE_6A1_SCHEMA_VERIFICATION_2026-10-13.md#prosjekteiers-lesebekreftelse-mottatt-2026-10-13). De seks dokumentene leveres separat på `docs/phase6a1-staging-evidence` som draft dokumentasjons-PR; faktisk PR/CI/merge følger GitHub.

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
