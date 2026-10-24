# Samordnet Editor – samlet visuell leveranse 2026-10-24

**Status:** lokalt teknisk verifisert; avventer prosjekteiers visuelle godkjenning før merge.

**PR:** [#92](https://github.com/fredrik-stack/kreative-norge-crm/pull/92), draft.

**Eksakt runtimekode:** `caccd8b71f83bf3896393c5bbcb8116f2041023f`. Senere evidens-/dokumentasjonscommit endrer ikke frontendkoden; gjeldende PR-head følger GitHub.

**Miljø:** lokal Vite `127.0.0.1:4173`, ekte Django 5.1.15 og isolert Docker/PostgreSQL 16.
Chromium 145.0.7632.6. Bare syntetiske brukere/profiler/kontakter; ingen staging- eller produksjonsdata.
API-responsene i dette evidenssettet kommer fra ekte backend. Nettverksfeil er framprovosert med
Chromiums offline-modus. Lagrer-bildene pauser transporten før ekte PATCH får fortsette;
respons og read-back kommer fra faktisk backend. Vanlige automatiserte E2E bruker separat sitt eksisterende mockoppsett.

[Åpne samlet bildegalleri](evidence/editor-compact-2026-10-24/index.html).
Bildene kan også åpnes enkeltvis nedenfor. HTML-filen er en statisk evidensleser,
ikke en ny app/prototype. Den fungerer lokalt uten server. Klikk et bilde for full størrelse.

## Endringen og beslutningen

Kompakt kontekstlinje og kontrollskala, kort med innhold innenfor rammen, enklere
lesemodaler, profilhandlinger ved hodet og sekundære oppgaver med korte oppsummeringer.
Personer krever søk/filter og viser navn/tittel, aktører, kontakt og sted; øvrige
felt ligger i detalj. Separate lagringshandlinger, reset, standardregion, statusprioritet,
kontaktutkast og navigasjonsvern består. Se [styrende føring / UI-6 §9](../features/UI_6_FELLES_SPEC.md#9-samordnet-editor--ny-eierføring-og-kodeleveranse-2026-10-24).

**Eiers ene beslutningspunkt:** godkjenne dette sammenhengende visuelle forslaget på
angitt lokal kodeversjon, eller angi konkrete visuelle rettinger. Ingen nye
produkt-/arkitekturvalg utenfor bestillingen er nødvendige. Godkjenningen gjelder
lokal visuell leveranse; den er ikke manuell stagingaksept. Merge/staging er ikke utført.
Etter godkjenning gjelder ordinær review/CI/merge/main-CI og frontend-only staging-runbook.

## Alle flater: laptop og mobil

1440×1000 og 390×844 er faktiske viewportmål før eventuell fullsidesfangst.
Fullsidebilder er høyere enn viewporten. Ingen bilder er en rekonstruksjon.

| Flate | Laptop 1440 | Mobil 390 |
| --- | --- | --- |
| Aktøroversikt | [Browserbilde](evidence/editor-compact-2026-10-24/01-actors-1440.png) | [Browserbilde](evidence/editor-compact-2026-10-24/01-actors-390.png) |
| Aktørens lesemodal | [Browserbilde](evidence/editor-compact-2026-10-24/02-actor-reading-1440.png) | [Browserbilde](evidence/editor-compact-2026-10-24/02-actor-reading-390.png) |
| Rediger aktør · ren | [Browserbilde](evidence/editor-compact-2026-10-24/03-actor-edit-1440.png) | [Browserbilde](evidence/editor-compact-2026-10-24/03-actor-edit-390.png) |
| Åpen bildeflyt | [Browserbilde](evidence/editor-compact-2026-10-24/04-image-open-1440.png) | [Browserbilde](evidence/editor-compact-2026-10-24/04-image-open-390.png) |
| Opprett aktør | [Browserbilde](evidence/editor-compact-2026-10-24/05-actor-new-1440.png) | [Browserbilde](evidence/editor-compact-2026-10-24/05-actor-new-390.png) |
| Personoversikt · inngang | [Browserbilde](evidence/editor-compact-2026-10-24/06-people-entry-1440.png) | [Browserbilde](evidence/editor-compact-2026-10-24/06-people-entry-390.png) |
| Personresultater | [Browserbilde](evidence/editor-compact-2026-10-24/07-people-results-1440.png) | [Browserbilde](evidence/editor-compact-2026-10-24/07-people-results-390.png) |
| Personens detaljvisning | [Browserbilde](evidence/editor-compact-2026-10-24/08-person-reading-1440.png) | [Browserbilde](evidence/editor-compact-2026-10-24/08-person-reading-390.png) |
| Rediger person · ren | [Browserbilde](evidence/editor-compact-2026-10-24/09-person-edit-1440.png) | [Browserbilde](evidence/editor-compact-2026-10-24/09-person-edit-390.png) |
| Opprett person | [Browserbilde](evidence/editor-compact-2026-10-24/10-person-new-1440.png) | [Browserbilde](evidence/editor-compact-2026-10-24/10-person-new-390.png) |

## Lagringstilstander

Ren og ny profil er vist ovenfor. Endret/feil vises på begge bredder, og aktiv
lagring/bekreftet lagring på laptop. Dette er samme hovedform og samme write-scope.

| Profil / tilstand | Laptop | Mobil |
| --- | --- | --- |
| Aktør · Endret | [Browserbilde](evidence/editor-compact-2026-10-24/actor-changed-1440.png) | [Browserbilde](evidence/editor-compact-2026-10-24/actor-changed-390.png) |
| Aktør · Lagrer | [Browserbilde](evidence/editor-compact-2026-10-24/actor-saving-1440.png) | — |
| Aktør · Lagret | [Browserbilde](evidence/editor-compact-2026-10-24/actor-saved-1440.png) | — |
| Aktør · Feil | [Browserbilde](evidence/editor-compact-2026-10-24/actor-error-1440.png) | [Browserbilde](evidence/editor-compact-2026-10-24/actor-error-390.png) |
| Person · Endret | [Browserbilde](evidence/editor-compact-2026-10-24/person-changed-1440.png) | [Browserbilde](evidence/editor-compact-2026-10-24/person-changed-390.png) |
| Person · Lagrer | [Browserbilde](evidence/editor-compact-2026-10-24/person-saving-1440.png) | — |
| Person · Lagret | [Browserbilde](evidence/editor-compact-2026-10-24/person-saved-1440.png) | — |
| Person · Feil | [Browserbilde](evidence/editor-compact-2026-10-24/person-error-1440.png) | [Browserbilde](evidence/editor-compact-2026-10-24/person-error-390.png) |

## Teknisk kontroll og avgrensning

- TypeScript og produksjonsbygg: grønne. 52 frontend-enhetstester og 17 Editor-Playwright-tester: grønne.
  Dette inkluderer eksisterende bilde-/telefon-/publiserings-/resetkontroller og
  nye regresjoner for søk først, bevart søk/utvalg, modal-fokus, ukansellert første
  native feil og like backendfeil med riktig feltmål. Aktør fra personspesifikt
  søk åpnes også når aktørkortlisten har null filtertreff.
- Ekte backend: ingen horisontal sideoverløp i de kontrollerte flatene på
  1440/1366/1024/390/320 px; korttekst/chips/handlinger kontrollert innen kortet.
  Like høye e-post-/telefonfelt, åpning/lukking uten tapt kontaktutkast,
  Bli her/navigasjonsvern og kontaktutkast gjennom faktisk profil-PATCH/reload.
  Opprett aktør/person gir 201 med NO-region og korrekt lagret profilstatus.
- Bilde: ekte lokal upload→logo-preview→processing→eksplisitt approval og
  lukking/åpning er kontrollert med repoets fallback-PNG som syntetisk testinput.
  [Godkjent bilde / faktisk browser](evidence/editor-compact-2026-10-24/11-image-approved-1440.png).
  Lokal privat bildelagring er isolert. Ingen PUBLIC-projection/provideraktivering.
- Faktisk 200 % Chromium-zoom via browserens zoom-API,720×456 effektiv viewport,
  DPR 2, uten horisontal sideoverløp eller overdekket fokusfelt:
  [aktør](evidence/editor-compact-2026-10-24/actor-zoom200.png),
  [person](evidence/editor-compact-2026-10-24/person-zoom200.png).
- [Maskinell breddekontroll](evidence/editor-compact-2026-10-24/checks.json),
  [zoomresultat](evidence/editor-compact-2026-10-24/zoom.json) og
  [filmanifest](evidence/editor-compact-2026-10-24/manifest.json).
  Dette er målrettet lokal kontroll, ikke universelt tilgjengelighetsbevis eller stagingaksept.

## Separat review og leveransegrense

Faktisk separat, skrivebeskyttet agentreview fulgte prosjektets gjennomgå-skill.
Base `4e9340f0f606e95e0bc8603916b7acd4f7e93008`→første head
`130c56390c0c21aefc7aabe8fdd90d3eacb27af9` ga to viktige funn: første native
feilmelding ble kansellert, og koblet aktør kunne mangle under personfilter.
CSS-spesifisitet ble også bekreftet. Alle tre er rettet i runtimecommit ovenfor.
Relevant separat re-review 130c563→caccd8b fant ingen nye kritiske/viktige funn.
Revieweren kjørte ingen tester/browser/DB og gjorde ingen writes. Endelig relevant
kontroll av denne evidens-/dokumentasjonscommiten og nødvendig PR-CI registreres
versjonsbundet i [PR #92](https://github.com/fredrik-stack/kreative-norge-crm/pull/92).
Ingen GitHub-godkjenning fra et menneske utledes av agentreviewet.

Godkjent import v6 rev.4/O-24 ble kontrollert som 200869 byte med SHA-256
`938a40ea725772d96a70fb660a228652070047e3d1d6b3eeebe24aa324499628`
og gjennomgått i ekte Chromium. Eiers sju stagingbilder er avviksgrunnlag og
inngår ikke i nye PR-bilder. Ingen backend/API/migrasjon, dataflytting, deling,
ny taggpolicy, 6B/6C, PUBLIC-omlegging eller kart inngår. Hele UI-6 er ikke ferdig.
