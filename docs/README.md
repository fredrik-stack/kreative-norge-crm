# Kreative Norge CRM – dokumentasjon

**Siste visuelle retting av PR #92 – 25.10.2026, runde 2:**
[UI-6 §11](features/UI_6_FELLES_SPEC.md#11-andre-visuelle-retting-av-pr-92--2026-10-25) overstyrer tidligere kortdybde,
plassering av nedre aktørhandling og fire personkolonner.
[Nytt vurderingsgrunnlag](status/EDITOR_LAYOUT_VISUAL_REVIEW_2026-10-25.md) har
29 nye browserbilder, primært hele desktopflaten i 1920 × 1080, mobil og faktisk
200 % zoom. Lavere like kort, sted øverst høyre, fem personkolonner, oransje dirty
og Lagre/Slett helt nederst er implementert på branch. Samlet visuell godkjenning,
merge og staging gjenstår; senere deployscope er fortsatt API + frontend.

**Eierbestilt retting av PR #92 – 2026-10-25:**
[UI-6 §10](features/UI_6_FELLES_SPEC.md#10-eierbestilt-retting-av-pr-92--2026-10-25) styrer venstremeny, like store aktørkort og manuell
personlagring med lokale kontaktutkast. Dette overstyrer eldre meny-/kort-/reset-
og lagringsføringer nedenfor. Lesemodaler, bildeflyt og søk først videreføres
innen eiers avgrensede godkjenning. Rettet runtime er ikke samlet visuelt godkjent.
[Nytt samlet vurderingsgrunnlag](status/EDITOR_REVISION_VISUAL_REVIEW_2026-10-25.md)
skiller kode, lokale tester, browserbevis og utestående godkjenning. Ingen merge
eller staging i rettingsrunden; senere deploy må omfatte **API og frontend**.

**Samordnet Editor, kodeleveranse 2026-10-24:**
[Ny styrende eierføring / UI-6 §9](features/UI_6_FELLES_SPEC.md#9-samordnet-editor--ny-eierføring-og-kodeleveranse-2026-10-24)
bruker kontrollert Import v6 rev.4/O-24 som konkret designreferanse med Editor-
fonter beholdt. Kompakt oversikt/modal/profil og søk først for personer er
implementert på branch. Samlet visuell godkjenning før merge gjenstår; ingen
ny stagingaksept eller ferdigmelding av hele UI-6. Eldre avsnitt er daterte bevis.

[Samlet visuell leveranse / browserbilder](status/EDITOR_COMPACT_VISUAL_REVIEW_2026-10-24.md) gjelder kode `caccd8b` og draft PR #92.


**UI-6 førstepakke 2026-10-24:** [Profilhandlinger/status og valgt resetretting](features/UI_6_FELLES_SPEC.md#8-første-bestilte-kodepakke--skjemabundet-handlingstatus-og-korrekt-reset)
er implementert i kodeleveransen. Den erstatter tidligere anbefalt bevaring av
nyprofilens taggtekst ved reset; øvrige utformingsmål er fortsatt anbefalinger.
[Teknisk stagingevidens](status/STAGING_UI_6_PROFILE_ACTIONS_2026-10-24.md) bekrefter
frontend `3ede68f`, resize/fokus og faktisk 200 % zoom. Visuell eieraksept gjenstår.


**Historisk spesifikasjonspublisering 2026-10-24:** [Kodeforankret utforming og første pakke](features/UI_6_FELLES_SPEC.md)
beskriver fire Editor-disposisjoner, konkret gjenbruk og lagringsscope. Anbefalt
første kodepakke er skjemabundet handlings-/statusrad, ikke ny global lagring.
Publisert spesifikasjon er ikke UI-implementering eller godkjenning av nye produktvalg.


**UI/UX-plan 2026-10-24:** [Samlet ferdigstillingsoversikt for Editor og PUBLIC](status/EDITOR_PUBLIC_UI_COMPLETION_PLAN_2026-10-24.md)
viser flater, faktisk bevisnivå, navngitte leveranser og samlet v1-aksept.
7E lukker importsporet; begge Google Maps-aktørkart og øvrige avtalte flater har
egne leveranser. Dette er planpresisering, ingen ny UI-/stagingverifikasjon.


**Notatgrunnmur 2026-10-24:** ADR-011 trinn 7 har additiv, teknisk stagingverifisert
lagring gjennom [PR #85](https://github.com/fredrik-stack/kreative-norge-crm/pull/85).
Nye overlaytabeller er tomme og gaten av. Legacy note/tags er autoritative;
ingen dataflytting eller fullført trinn 7. [Sanitert evidens og migreringsgrunnlag](status/STAGING_PHASE_6A_NOTE_OVERLAYS_2026-10-24.md).

**Leseshadow 2026-10-24:** ADR-011 migreringstrinn 6 er teknisk stagingverifisert gjennom [kode-PR #83](https://github.com/fredrik-stack/kreative-norge-crm/pull/83): FULL_EQUAL for alle 14 tenant-/modellkombinasjoner, uten NULL-/strukturavvik. Shadowgaten er av som varig sluttstate; legacylesing er fortsatt autoritativ. [Datert evidens](status/STAGING_PHASE_6A_READ_SHADOW_2026-10-24.md). Hele 6A og framtidig shared tilgang er ikke ferdig. Daterte eldre avsnitt nedenfor beskriver tidligere leveranser.

**Datert 6A.2-backfillstatus 2026-10-17:** Eiergodkjent eksakt plan er anvendt i staging: ett domain, sju tenantbindinger, 285 profilbindinger og 285 egne legacyassignments. Batch `phase6a2-staging-20261017-01` er COMMITTED_VERIFIED med matchende frisk read-back og separat no-op-plan uten restendringer. Bevaring og arkivbundet post-restore av faktisk backfill er verifisert. Samme API kjører og driftsvinduet er avsluttet med timere gjenopprettet; prosjekteier har bekreftet eksisterende Editor-/admin-/PUBLIC-lesing uten feil. STAGING VERIFIED / OWNER-CONFIRMED innen avtalt backfill-/bevarings-/lesescope, se [datert evidens](status/STAGING_PHASE_6A2_BACKFILL_2026-10-17.md). Ingen shared-aktivering eller ferdigmelding av hele 6A. Midlertidig slettebegrensning består; senere catch-up/apply krever separat godkjenning. Skrivebeskyttet review av de åtte dokumentfilene er fullført uten kritiske eller viktige funn. Dokumentasjonen er publisert og PR-reviewet uten blokkerende funn i [PR #80](https://github.com/fredrik-stack/kreative-norge-crm/pull/80). Kontrollert dokumentasjonsmerge er bestilt 2026-10-17; faktisk merge/head og CI følger GitHub og SESSION WRAP-UP. Ingen ny drift eller applygodkjenning inngår. Eldre daterte avsnitt nedenfor beskriver historisk grunnlag.

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

**Gjeldende 6A.1-status, eierbekreftelse mottatt 2026-10-13:** STAGING VERIFIED / OWNER-CONFIRMED innen avtalt additiv skjemagrunnmur/API-runtime. Reviewede tekniske bevis og prosjekteiers fullførte manuelle lesekontroll dekker samlet de avtalte kontrollene; ingen ny agenttest eller stagingkjøring er utført. Ingen backfill/shared-aktivering eller ferdigmelding av hele 6A. [Eierbekreftelse og bevisnivå](status/STAGING_PHASE_6A1_SCHEMA_VERIFICATION_2026-10-13.md#prosjekteiers-lesebekreftelse-mottatt-2026-10-13). De seks dokumentene er merget gjennom [PR #76](https://github.com/fredrik-stack/kreative-norge-crm/pull/76) på `9407828f2b8f27215828d16b6a4691eabf4cc895`, med main-CI `38457842425` success. Dette er dokumentasjon, ikke ny stagingdeploy.

**Historisk 6A.2-leveransestatus før staging 2026-10-14:** Godkjent mekanisme for eksplisitt domenebinding og første legacyassignment er lokalt implementert med dry-run/apply, databasebundet batchregister, smalt ORM-/PostgreSQL-vern og kontrollert sletteavvisning. Skrivebeskyttet review 2026-10-14 fant ingen blokkerende funn; kode er publisert i [PR #77](https://github.com/fredrik-stack/kreative-norge-crm/pull/77) på `feat/phase6a2-legacy-domain-backfill`, med grønn CI på gjennomgått head. Kontrollert kode-merge uten deploy er bestilt 2026-10-14. Faktisk siste head, merge og CI følger GitHub og SESSION WRAP-UP. Ikke deployet eller anvendt på reelle data. Mapping er datert inventargrunnlag, ikke apply-tillatelse. Vanlig profilredigering består; assigned profiler/tenants får godkjent midlertidig slettebegrensning ved senere backfill. Shared tilgang og neste etappe er ikke startet. Se [runbook](operations/LEGACY_DOMAIN_BACKFILL.md).

**Gjeldende 6A.2-stagingstatus 2026-10-14:** Kode `63743441a173d2c1b4c71d9f9011b93fbadd2ca4` er deployet API-only, 0034 er anvendt, og tekniske bevarings-/pre/post-checkpoint-/isolerte restorekontroller er grønne. Fersk read-only dry-run foreslår 578 endringer med `writes:0` og null batchregistrering; ingen backfill eller deling er utført. **STAGING VERIFIED / OWNER-CONFIRMED innen avtalt API-/schema-/lesescope:** prosjekteier har bekreftet eksisterende Editor-/admin-/PUBLIC-lesing uten feil. Maskinell ekstern HTTPS møtte Cloudflare-challenge; dette er adskilt fra eiers manuelle lesebevis. Dry-run er produsert, ikke eiergodkjent; senere apply krever separat fersk godkjenning og gyldige driftsporter. Vinduet er avsluttet og timere/API-policy gjenopprettet. Se [6A.2-evidens](status/STAGING_PHASE_6A2_SCHEMA_DRY_RUN_2026-10-14.md). Skrivebeskyttet dokumentasjonsreview er fullført uten kritiske eller viktige funn. Dokumentasjonen er publisert og PR-reviewet uten blokkerende funn i [PR #79](https://github.com/fredrik-stack/kreative-norge-crm/pull/79). Kontrollert dokumentasjonsmerge er bestilt 2026-10-17; faktisk merge/head og CI følger GitHub og SESSION WRAP-UP. Ingen ny drift eller applygodkjenning inngår.

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
