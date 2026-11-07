# Editor CRM – identitet, mobil lesbarhet og kontaktkort

**07.11.2026 · BESTILT / IMPLEMENTERT PÅ BRANCH / LOKALT VERIFISERT · MERGE/STAGING GJENSTÅR**

[13 hele viewportbilder](evidence/editor-clarity-2026-11-07/index.html) ·
[manifest/SHA-256](evidence/editor-clarity-2026-11-07/manifest.json).
Runtime `582454101114c4baef70cc833ca5282345702940` på `feat/editor-mobile-clarity`,
base `5cc6e966d211c6c6a969b63e7f8380c751e6cb2e`. Senere docshead kan være nyere
uten runtimeendring. Faktisk separat review/siste-head CI spores i leveranse-PR.

## Mandat og gjennomføring

[UI-6 §15](../features/UI_6_FELLES_SPEC.md#15-editor-identitet-og-lesbarhet--eierbestilling-2026-11-07)
lagrer eierbestillingen. Hele leveransen til staging er uttrykkelig bestilt uten
ny obligatorisk visuell forhåndsgodkjenning. Ett faktisk valg er avklart: Kart vises
som deaktivert menyvalg; kartfunksjon/provider inngår ikke. Dette er ny retting
av den tidligere godkjente PR #92, ikke ferdigmelding av hele UI-6 eller v1.

| Eierføring | Implementert og lokalt kontrollert |
|---|---|
| Bare Editor CRM i Editor | Brand, innlogging, lasteskjerm og browser-title. PUBLIC-navn/grafikk og URL-data består. |
| Tydelig mobilhero/samme symboler | Kompakt grønn brand/bruker/kontor-del; bygg/person/pil-opp/pil-ned/kart/gear som delte SVG-er. Deaktivert Kart. Admin bare under eksisterende faktisk adgang, nedenfor femvalgmenyen på mobil. Desktop har stor venstrejustert Editor CRM. |
| Klarere navn | Fontfamilien er uendret. Målt før:750/13px valgte Avenir Next Heavy. Nå600 velger Demi Bold. Desktop fortsatt13/17px; mobil17/21px, to hele ordlinjer før kontrollert avkorting innenfor tekstkolonnen. |
| Leselig sted/hjelp | Mobilsted13px, hjelpetekst/feltetikett14px og input16px. Desktopsted12px. Metadatafarger og bilde90px/kvadrat/kort148px består. |
| Flere tags | Faktisk målt restareal etter navn/kategorier, ResizeObserver og fonts-ready. Komplette tags så langt det går; første svært lange tag kan avkortes med plass reservert til +N. Bare faktisk skjulte tags telles. Modal viser alle. |
| Kontaktperson er klikkbar | Eksisterende personlesemodal gjenbrukes, også for leser. Én modal om gangen; eget URL-historietrinn. Tilbake-knapp/browser-Tilbake/Lukk/Escape går tilbake til aktørkort; direktelenke har parent-fallback, og parent-/tenantbytte rydder. Rediger fortsatt bare ved canWrite. |
| Redigering starter øverst | Aktørrutens ID/innlasting utløser én avbruddsbar scroll-to-top; ikke ved hver lagring eller feltendring. |
| Ingen doble e-post/telefonetiketter | Første feltetikett er visuelt skjult, fortsatt korrekt tilgjengelig navn. Gruppens overskrift vises én gang; ekstra kontaktfelt har egne etiketter. |
| Ingen inaktiv Klar | Idle-status ved ny kontaktperson er skjult; virkelig saving/saved/error beholdes. Samme handler/API. |
| Ingen Primærlenke | Fjernet fra begge Editor-lesemodaler/preview og PUBLIC-detalj. Nettside/sosiale lenker er bevart. Ingen URL-sletting, endret avledet API-schema eller kildevalg. |

Fontmålingen bruker faktisk Chromium/CDP, ikke bare en CSS-antakelse.
[Førmåling](evidence/editor-clarity-2026-11-07/font-before.json) er registrert fra
browserresultatet før koden ble endret; [ettermåling](evidence/editor-clarity-2026-11-07/font-after.json)
viser fontfamilie, faktisk fontface, vekt og mobilstørrelse. Fonttilgjengelighet er
plattformavhengig; ingen fontfil/provider er byttet. Native fontfamiliefallback består.

## Korte, implementerte tekstforslag

Gjennomgangen omfatter profil-/kontakt-/koblings-/bildetekster og hjelpetekster i
oversiktene. Gjentakelser er fjernet; nødvendige lagrings-/publiseringsgrenser,
feilvarsler, bildebruksrett og Brave/90-dagers-/sensitiv-info-beskjed består.
Tekniske kilde- og API-koder er ikke gjort til nye brukerbeslutninger.

| Sted | Ny tekst / tiltak |
|---|---|
| Aktørprofil | «Bilde og personkoblinger lagres separat.» |
| Personprofil | «Lagre person lagrer også kontaktopplysningene.» |
| Telefon | «Velg land hvis nummeret ikke starter med +.» |
| Beskrivelse | «En kort beskrivelse til den offentlige aktørsiden.» Duplisert forklaring fjernet. |
| Kategorier/tags | «Velg hovedkategori, deretter underkategori.» / «Inntil fem tags, skill med komma.» |
| Offentlig kontakt | Én kort vilkårssetning og kort faktisk antall offentligvisende aktørkoblinger; ingen omlegging av publisering. |
| Kobling | «Endringer i personkoblinger lagres med én gang.» |
| Ny kontaktperson | «Personen knyttes til denne aktøren når du oppretter den.» |
| Tidligere bilder | «Tidligere bilder er forslag. Velg og godkjenn før bruk.» |
| Brave | «Søket sendes til Brave og kan lagres i opptil 90 dager. Unngå sensitiv eller intern informasjon.» |
| Bildebruk | «Kontroller at du har lov til å bruke bildet før du godkjenner.» |
| Lenke/preview | «Nettside», «Offentlig beskrivelse», «Offentlig telefon» og forståelige titler fra nettsiden. |

## Kontroller og bevisgrenser

- 66 Vitest-tester, TypeScript og produksjonsbygg er grønne. Eksisterende tester
  har oppdaterte tekstforventninger; API-/publiserings-/primærkontakt-/retry-/bilde-
  assertions er bevart. JSDOM har en egen scrollTo-stub; ekte scrolling kontrolleres
  i browser, ikke med en ny runtimeomgåelse.
- 32 eksplisitte Editor-Playwright-reiser er grønne. Åtte nye reiser dekker1920/390/320,
  både reader/Admin-port, flere tags/resize/lange tags, kontaktkort begge veier,
  browser-Tilbake/Escape, reell desktop-/mobilscroll og tilgjengelige feltetiketter.
  Etter siste herding av bare testfixture er alle åtte gjentatt grønne på samme kode.
- To faktiske Django-malrenderinger, legacy/cutover, er DB-frie og grønne:
  [ingen Primærlenke, beholdt Nettside/Instagram](evidence/editor-clarity-2026-11-07/public-template-checks.json).
  Dette er ikke full backend-/PUBLIC-browserverifikasjon.
- Tidlige kjøringer fant gammel tekst i testforventninger og et taggområde som
  kunne vokse utenfor gridraden. Gridraden/body er nå eksplisitt begrenset; slutt-
  kontroller er grønne. En bred lokal kjøring tok også med fire PUBLIC-reiser uten
  deres backend på8000 og fikk connection refused; de er ikke påstått lokalt grønne.
  CI har dedikert PUBLIC-fixture og avgjør den bredere verifikasjonen.
- 13 nye originale viewport-PNG er faktiske lokale Vite/Chromium-bilder med
  syntetiske API-fixtures,1920×1080 og390/320×844. Ingen fullside/utsnitt. Adminbildet
  bruker syntetisk autorisert session. Ingen produksjons-/stagingpåstand eller ny
  Importillustrasjon. Bilder/hash/dimensjoner er bundet til runtime over.
- Ingen lokal Docker/PostgreSQL nødvendig for denne UI-/malrettingen; ingen
  modell-/migrasjons-/dataruting-/permission-/autentiseringsendring. Senere staging
  skal bruke ekte API/HTTPS og kontrollert syntetisk reise, uten reelle profilendringer.

Samme manuelle person-/kontaktlagring, bevarte ID-er, usikker-POST-lås,
navigasjonsvern og separate bilde-/koblingshandlinger består. Ingen ny
kontakt-/tagg-/publiseringspolicy, catch-up/backfill, shared-/overlayaktivering,
Google Maps-implementering, Import-UX eller ny formell brukertest. Godkjent
Import v6 rev.4/O-24/5E og begge kart som senere v1-leveranser består.

Koden må reviewes separat og ha grønn PR-/main-CI før bestilt kontrollert
API+frontend-staging (PUBLIC-mal inkludert). Ingen migrasjon skal anvendes.
Faktisk deploy-/stagingstatus og sanitert evidens følger etter drift innen samme
mandat; denne lokale rapporten er ikke stagingaksept.


## Separat kodereview før publisering

Skrivebeskyttet reviewer kontrollerte base
`5cc6e966d211c6c6a969b63e7f8380c751e6cb2e` → første runtime
`9811ee1452aa4c267332d00e55e68ccfa746ff66` og fant to viktige forhold:
Tilbake fra personkort måtte bevare aktørkortet, og navneknappen kunne klippes
horisontalt ved320px. Begge er rettet i
`582454101114c4baef70cc833ca5282345702940`: eget historietrinn/eksplisitt tilbakeknapp
med direktelenkefallback og breddebegrenset navn med kontrollert ellipsis.
Målrettede kontroller dekker faktisk tilbakeutfall og knapp/h3/tekstkolonne-bounds.

Relevant re-review av rettingsdelta og samlet base→5824541 har ingen åpne kritiske
eller viktige funn. Reviewer kjørte ingen tester, browserreise, nettverk, database
eller mutasjoner. Sluttkjøringen etter retting er32/32 Editor-reiser,66 Vitest og
TS/bygg grønne. Alle13 vedlagte bilder er oppdatert til5824541;18 manifestoppføringer
registrerer faktiske bytes/dimensjoner. Separat dokumentasjons-/evidensreview og
siste-head CI registreres i PR før merge.
