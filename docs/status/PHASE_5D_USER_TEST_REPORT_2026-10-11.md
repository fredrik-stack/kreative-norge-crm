# Fase 5D – konsolidert brukertestrapport, revisjon 4

**Prosjekt:** Kreative Norge CRM\
**Testdato:** 11. oktober 2026\
**Testet prototype:** Import 2.0, klikkbar prototype v5\
**Formelle deltakere:** To kollegaer, P01 og P02\
**Moderator:** Fredrik Forssman\
**Supplerende gjennomgang:** Prosjekteiers grundige egen test\
**Revisjonsdato:** 12. oktober 2026\
**Revisjonsgrunnlag:** Prosjekteiers siste manuelle gjennomgang av v6 revisjon 4 og bestilling av én avgrenset sluttkorrigering, uten ny manuell testrunde, 12. oktober 2026 (R12 / O-24)\
**Status for revidert v6:** **ENDELIG UX-GODKJENT** etter utført sluttkorrigering; dokumentasjonen lagres på `docs/phase5d-ux-v6-close` for separat PR-review; merge er ikke utført\
**Oppfølging:** [UX-spesifikasjon v6](../features/IMPORT_2_0_UX_SPEC_V6.md) og klikkbar prototype v6 (separat levert artefakt: `import_2_0_prototype_v6.html`, v6 revisjon 4 med O-24, SHA-256 `938a40ea725772d96a70fb660a228652070047e3d1d6b3eeebe24aa324499628`; ikke innchecket i denne PR-en)

## 1. Konklusjon og godkjenningsstatus

Import 2.0s overordnede produktretning og den gjennomførte interne brukertestrunden er **owner-approved**. Begge formelle deltakere forstod standardpakken og Google Sheets-reisen. De forstod sentrale valg i review, inkludert kilder, bilde, sted og offentlig synlighet. Ingen av de åtte forhåndsdefinerte kritiske misforståelsene ble registrert. Mapping krevde moderatorhjelp, og forskjellen mellom målrettet og utvidet berikelse fikk de eneste lave vurderingene. Disse funnene er innarbeidet i v6 sammen med de avtalte språk- og navigasjonskorreksjonene. Etter prosjekteiers siste gjennomgang av revisjon 4 og den utførte sluttkorrigeringen O-24 er UX-leveransen **endelig godkjent**. De opprinnelige testkonklusjonene bygger på R1/R2 og beslutningen i R3/R4; sluttgodkjenningen bygger på R12 og den dokumenterte korreksjonen, se kilderegisteret og §6.5.

Etter første v6-leveranse ga prosjekteier konkrete kommentarer og fire skjermbilder som styrte revisjon 2, registrert som **O-01–O-09** med kilde R7. Gjennomgangen av revisjon 2 ga **O-10–O-19** med kilde R8 og taksonomikontrollen R9. Disse erstattet blant annet ekstra musikkontorbekreftelse, gruppeaktivering, eget effektpanel og manuelt tillegg for bildesøk. Prosjekteiers kommentarer til revisjon 3 og den etterfølgende read-only-avklaringen styrte **revisjon 4**, med **O-20–O-23** og kildene R10/R11: feltbaserte filtre før analyse, gule knapper ved alle nødvendige reviewvalg, kø innen skjermrammen med bevart kontekst og en komplett offentlig liste med personvisninger. Prosjekteier gjennomførte deretter sin siste manuelle gjennomgang og ba om bare én retting: alle fire regelgrupper skal være aktive når et filter velges. Denne sluttpresiseringen er innarbeidet som **O-24**, med kilde R12. Eier ba uttrykkelig om å gå direkte til én dokumentasjonsprompt etter rettingen, uten en ny manuell prototypetest. Eiergjennomgangene endrer ikke testdataene, deltakerantallet eller vurderingene.

Prosjekteier har besluttet at det **ikke skal gjennomføres flere brukertester**, og akseptert den resterende utvalgsrisikoen. UX-grunnlaget er nå godkjent og klart for dokumentasjonsleveransen. Godkjenningen gjelder produkt-/UX-kontrakten; runtimeimplementering, dokumentasjons-PR/merge og Fase 5E har egne statuser og er ikke gjennomført av denne rapporten.

| Del av leveransen | Status |
| --- | --- |
| Intern validering av v5 og beslutning om å avslutte brukertesting | **GODKJENT AV PROSJEKTEIER** |
| Plan og avgrensning for v6 | **GODKJENT AV PROSJEKTEIER** |
| Eierkommentarer til første v6 og mandat til revisjon 2 | Historisk revisjonsspor i R7 og O-01–O-09; nyere beslutninger har forrang |
| Eiergjennomgang av revisjon 2 og mandat til revisjon 3 | Dokumentert i R8/R9 og O-10–O-19; ikke endelig UX-godkjenning |
| Eiergjennomgang av revisjon 3 og mandat til revisjon 4 | Historisk grunnlag i R10/R11 og O-20–O-23; videreført i den endelige leveransen |
| Siste manuelle eiergjennomgang av revisjon 4 | **UTFØRT**, dokumentert i R12; bare O-24 bestilt som sluttkorrigering |
| Sluttkorrigering O-24 | **UTFØRT OG TEKNISK KONTROLLERT**; ingen ny manuell retest etter eiers uttrykkelige instruks |
| Endelig UX-godkjenning av den ferdige v6-leveransen | **GODKJENT AV PROSJEKTEIER** på grunnlag av R12 og utført O-24 |
| Dokumentasjons-PR og merge av Fase 5D-artefaktene | Dokumentene er lagret på `docs/phase5d-ux-v6-close` og leveres i én draft PR for separat review; **MERGE IKKE UTFØRT**, dokumentene finnes ennå ikke på `main`. Eksakt PR-head og CI føres i GitHub og leveranserapporten. |
| Fase 5E, beslutningsklar implementerings- og testplan | **IKKE STARTET**; følger etter dokumentasjonsleveransen og fersk main-kontroll, og skal være read-only |
| Runtimeimplementering av Import 2.0 | Ikke startet som del av denne leveransen |

Den opprinnelige testplanen anbefalte fem deltakere. Denne runden omfattet to formelle deltakere og prosjekteiers gjennomgang. Den dokumenteres derfor som **owner-approved intern validering**, ikke som en gjennomført fempersonersplan. Dette skillet beholdes også når dokumentasjonen senere lagres i repoet.

## 2. Testgrunnlag og sporbarhet

### 2.1 Deltakere og gjennomføring

| Deltaker | Registrert rolle | CRM-erfaring | Regnearkerfaring |
| --- | --- | --- | --- |
| P01 | Plattform-superbruker | Middels | Middels |
| P02 | Tenant-/gruppeadministrator | Lav | Middels |

Roller og erfaringsnivå er hentet fra `role`, `crmexp` og `sheetexp` i råfilene. Rollebetegnelsene gjengir testregistreringen og utgjør ikke en ny definisjon av rettigheter i CRM.

Testene brukte den klikkbare v5-prototypen. De omfattet standard importpakke, egen CSV/XLSX med mapping, Google Sheets og sentrale deler av review og sluttkontroll. Registreringene skiller mellom oppgaver løst uten hjelp, oppgaver løst med hjelp og spørsmål besvart med ja/nei. Etterpå ble ni spørsmål vurdert på en skala fra 1 til 5.

### 2.2 Kilderegister

| Ref. | Kilde | Bruk i rapporten |
| --- | --- | --- |
| R1 | `P01 brukertest(1).json` | P01s strukturerte oppgaver, ratinger, kritiske sjekkpunkter og registrerte kommentarer |
| R2 | `P02(2).json` | P02s strukturerte oppgaver, ratinger, kritiske sjekkpunkter og registrerte kommentarer |
| R3 | `Fase_5D_Brukertestrapport_2026-10-11(1).md` | Opprinnelig konsolidering, prioritering og prosjekteiers beslutning etter test |
| R4 | `Kreative_Norge_CRM_Handoff_Fase_5D_til_5E_2026-10-11(1).md` | Autoritativ handoff for produktretning, godkjente korreksjoner og fasesekvens |
| R5 | `import_2_0_wireframe_prototype_v5_brukertest(1).html` | Den testede prototypens skjermbilder, tekst og illustrerte reise |
| R6 | Prosjekteiers godkjenning av v6-planen, 11. oktober 2026 | Mandat for ferdig UX-spesifikasjon og klikkbar v6 uten ny brukertest eller runtimearbeid |
| R7 | Prosjekteiers kommentarer til første v6-leveranse, 11. oktober 2026, med fire skjermbilder | Historisk grunnlag for revisjon 2, registrert som O-01–O-09 |
| R8 | Prosjekteiers gjennomgang av v6 revisjon 2, 11. oktober 2026, med fire nye skjermbilder | Mandat og korreksjoner for revisjon 3, registrert som O-10–O-19; nyere presiseringer har forrang |
| R9 | Aktiv taksonomi på kontrollert `main`, avstemt mot seed- og endringsmigrasjoner | Hele den etablerte listen med 6 hovedkategorier og 14 underkategorier; grunnlag for O-10 |
| R10 | Prosjekteiers kommentarer til v6 revisjon 3, 12. oktober 2026, med `Skjermbilde 2026-10-12 kl. 09.16.02.png` | Filterspørsmål, manglende gul telefonknapp, køens plassbehov og personvisning i offentlig sluttkontroll |
| R11 | Read-only-avklaring og prosjekteiers uttrykkelige godkjenning/bestilling av revisjon 4, 12. oktober 2026 | Historisk godkjent grunnlag for O-20–O-23 og bestillingen av siste egen artefaktgjennomgang |
| R12 | Prosjekteiers siste manuelle gjennomgang av v6 revisjon 4 og uttrykkelige instruks, 12. oktober 2026 | Behold de tre filtrene; rett bare tilgjengeligheten til alle fire regelgrupper. Ingen ny manuell prototypetest; gå direkte til én komplett dokumentasjonsprompt etter rettingen. Grunnlag for O-24 og endelig UX-godkjenning etter utført korreksjon |

R7s fire tilgjengelige skjermbilder viser ønsket utforming:

| Fil | Innhold og bruk |
| --- | --- |
| `Skjermbilde 2026-10-11 kl. 18.47.58.png` | Synlige, sammenfoldede regelgrupper som kan åpnes direkte. |
| `Skjermbilde 2026-10-11 kl. 18.57.18.png` | Hovedkategori, underkategori og tags med fargede chips. |
| `Skjermbilde 2026-10-11 kl. 19.18.31.png` | Identitet og matching, BRREG og høyrepanelet Matcher og kilder. |
| `Skjermbilde 2026-10-11 kl. 19.44.38.png` | Selvbetjent nytt sted med felter på samme side. |

R8s fire nye skjermbilder presiserer utforming av dashboard og offentlig sluttkontroll:

| Fil | Innhold og bruk |
| --- | --- |
| `Skjermbilde 2026-10-11 kl. 21.57.33.png` | V5s Behandlingsfremdrift og Nylige jobber gjeninnføres med sannferdige demotall. |
| `Skjermbilde 2026-10-11 kl. 21.59.38.png` | Klare, Trenger valg, Blokkert og Hoppet over med fargede toppkanter. |
| `Skjermbilde fra v5 kontroll offentlige endringer.png` | Referanse for hele den kompakte sluttkontrollen, tre tekstlinjer per lukket rad og naturlig høyde på sidepanelene. |
| `Skjermbilde v6 rev2 kontroller offentlige endringer.png` | Dokumenterer rader og sidepaneler som tok for stor høyde i revisjon 2. |

For offentlig sluttkontroll brukes R5 og R8s v5-skjermbilde som konkrete designreferanser. Før/etter-detaljer og nødvendig bekreftelseslogikk beholdes i den mer kompakte fremstillingen.

R10s skjermbilde viser tre aktørendringer, mens oppsummeringen teller fire offentlige endringer totalt, hvorav én personvisning. Read-only-gjennomgangen i R11 fant personvisningen som fjerde oppføring bak «Vis alle». Den lå allerede i den fullstendige planen og bekreftelsen; funnet gjelder synlighet i den konsoliderte listen. R11 avklarte også skillet mellom nye rader i importjobben og nye CRM-profiler, manglende felles problempekere og kønavigasjon som mistet filterkontekst. Dette er etterfølgende artefaktfunn, ikke nye registreringer fra P01/P02.

R12 dokumenterer at prosjekteier hadde testet revisjon 4 og bare fant behov for sluttkorrigeringen i Jobbregler. Den manuelle gjennomgangen gjaldt filen før O-24; denne korrigeringen er teknisk kontrollert, men ikke manuelt retestet, i tråd med den uttrykkelige instruksen. Dette skiller utført eiergjennomgang, teknisk artefaktkontroll og godkjenningen til å gå videre. Det registreres ingen ny revisjon eller ny formell brukertest.

R9 er den aktive frontendens komplette etablerte taksonomiliste, kontrollert mot migrasjonene; det er ikke et nytt uttrekk fra stagingdatabasen. Kildene er [`editorTaxonomy.ts`](https://github.com/fredrik-stack/kreative-norge-crm/blob/9a0eeef7ead30bf3ec168df26e2f27d4465c1be7/frontend/src/editorTaxonomy.ts), [seed-migrasjon 0012](https://github.com/fredrik-stack/kreative-norge-crm/blob/9a0eeef7ead30bf3ec168df26e2f27d4465c1be7/crm/migrations/0012_seed_categories_and_subcategories.py), [synkronisering 0015](https://github.com/fredrik-stack/kreative-norge-crm/blob/9a0eeef7ead30bf3ec168df26e2f27d4465c1be7/crm/migrations/0015_sync_public_taxonomy.py) og [Film-oppdatering 0016](https://github.com/fredrik-stack/kreative-norge-crm/blob/9a0eeef7ead30bf3ec168df26e2f27d4465c1be7/crm/migrations/0016_update_film_taxonomy.py). Hele listen står i UX-spesifikasjonen §5.4. Ingen nye katalogverdier eller konstruerte database-ID-er innføres.

Feltet `participant` er tomt i R1. Betegnelsen P01 er derfor hentet fra filnavnet og handoffen; råfilen endres ikke. R2 har `participant = P02`. Prosjekteiers egen gjennomgang er dokumentert gjennom beslutningen og handoffen. Den er ikke et tredje formelt JSON-testsett.

De lange `recommendation`-feltene i R1 og R2 overlapper i stor grad. De behandles som **konsoliderte, moderatorregistrerte anbefalinger**, ikke som bevis for at alle tekstforslag oppstod spontant og uavhengig hos begge. Strukturerte oppgaver, ratinger og deltakernes registrerte hovedfunn holdes atskilt fra denne konsolideringen.

### 2.3 Forholdet til repo og runtime

Fersk `main` er kontrollert på nytt 12. oktober 2026 før revisjon 4 og sluttkorrigeringen, og er uendret: [`9a0eeef7ead30bf3ec168df26e2f27d4465c1be7`](https://github.com/fredrik-stack/kreative-norge-crm/tree/9a0eeef7ead30bf3ec168df26e2f27d4465c1be7). Sammenligningen var identisk, med 0 commits foran og 0 bak. [CI-kjøring `33432010099`](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/33432010099) har 6 av 6 grønne jobber. Dette er den eksisterende kjøringen fra 31. august 2026, kontrollert på nytt, ikke en ny kjøring. ADR-011 og ADR-012 er merget målarkitektur; denne UX-leveransen dokumenterer ikke at målarkitekturen er runtimeimplementert. Staging er ikke re-verifisert i denne runden.

Rapporten dokumenterer observerte prototypefunn og avtalte korreksjoner. Fersk GitHub `main`, aktiv kode, migrasjoner, `docs/`, CI og verifisert stagingadferd er fortsatt autoritativt for hva systemet faktisk gjør. Historiske produktdokumenter kan ikke overstyre disse kildene eller nyere prosjekteierbeslutninger.

## 3. Resultater fra de strukturerte oppgavene

### 3.1 Scenario A – Kreative Norge-importpakke

Begge valgte riktig importvei og fant prompt-/pakkeinformasjonen uten hjelp. Begge svarte ja på forståelsen av at standardpakken hopper over vanlig mapping. Ingen feil eller nøling ble markert i det første registrerte importveivalget. Dette støtter videreføring av standardpakken som en tydelig inngang. Kilder: R1/R2, `a1`–`a3`, `a1err`, `a1hes`.

P01s `anotes` peker samtidig på at informasjonen nederst i pakkekontrollen kunne oppfattes som en feilmelding. Et tydelig informasjon-/tipsikon og en enkel forklaring om at feltene allerede er koblet, følger opp dette uten å endre importveien.

### 3.2 Scenario B – Egen CSV/XLSX med mapping

Begge valgte den riktige importveien uten hjelp. Vurderingen av tvetydige kolonner var den delen som krevde assistanse:

| Registrert oppgave | P01 | P02 | Råfelt |
| --- | --- | --- | --- |
| Velge egen CSV/XLSX som importvei | Uten hjelp | Uten hjelp | `b1` |
| Første vurderingsrad i mapping | Med hjelp | Med hjelp | `b2` |
| Andre vurderingsrad i mapping | Med hjelp | Uten hjelp | `b3` |

Tre av fire registrerte vurderingsoppgaver i mapping krevde dermed hjelp. Dette er en beskrivelse av disse fire oppgavene, ikke et anslag for alle fremtidige brukere eller importjobber. Mapping var det eneste strukturerte oppgaveområdet med registreringen «Med hjelp». Kilder: R1/R2, `b1`–`b3`.

Begge testloggene etterlyser enklere instrukser rundt «Mobil/kontor» og «Distrikt/Region». P02 beskriver ellers designet som intuitivt. R1s `bnotes` og de konsoliderte anbefalingene omfatter også fjerning av «Bruk sikre forslag», enklere forklaring av telefonfordeling per oppføring, og beskjed om at unike stedsverdier avgjøres senere i stedsreview. Tiltaket er derfor å gjøre beslutningene lettere å forstå, ikke å innføre nye automatiske avgjørelser.

### 3.3 Scenario C – Google Sheets

Begge valgte Google Sheets og riktige faner uten hjelp. Begge svarte ja på at dette er en importjobb, ikke kontinuerlig synkronisering. Kilder: R1/R2, `c1`–`c3`.

Anbefalingene gjelder kortere tekst og fjerning av den doble tilkoblingsknappen. Det skal fortsatt være tydelig hvilket regneark og hvilke faner som leses. Standardpakker går til pakkekontroll, mens øvrige ark går til mapping. Disse avtalte produktkravene beholdes selv om førstesiden forklares med færre ord.

### 3.4 Felles review og sluttkontroll

Begge svarte ja på forståelsen av BRREG-/kildepanelet og standard bildeløp. Begge løste det tvetydige stedet «Vik» og håndterte PUBLIC-bekreftelsen uten hjelp. Kilder: R1/R2, `d1`–`d4`.

R1s `dnotes` og de konsoliderte anbefalingene ber om mer forståelig språk rundt bildeformat, kartvilkår, kobling til musikkontor og dubletter. Resultatet støtter at reviewstrukturen beholdes, mens tekniske forklaringer erstattes med språk som viser hva brukeren skal velge og hvilke konsekvenser valget får.

## 4. Vurderinger på skalaen 1–5

Spørsmålstekstene nedenfor følger den opprinnelige rapportens kobling til `rating1`–`rating9`. Tallene er kontrollert direkte mot begge JSON-filene.

| Spørsmål | P01 | P02 | Snitt |
| --- | ---: | ---: | ---: |
| Riktig importvei var lett å velge | 5 | 5 | 5,0 |
| Det var lett å forstå når mapping var nødvendig | 5 | 5 | 5,0 |
| Forskjellen mellom målrettet og utvidet berikelse var tydelig | 3 | 2 | 2,5 |
| Bildearbeidsflyten var tydelig | 5 | 5 | 5,0 |
| Jeg stolte på matching og kilder | 5 | 5 | 5,0 |
| Review føltes rolig og effektiv | 5 | 5 | 5,0 |
| PUBLIC-endringene var tydelige | 5 | 5 | 5,0 |
| Jeg følte meg trygg før commit | 5 | 5 | 5,0 |
| Dette ville fungert for 100–500 rader | 5 | 5 | 5,0 |

**16 av 18 vurderinger er 5 av 5.** Forskjellen mellom berikelsesnivåene er det eneste vurderingspunktet under 5, med 3 og 2. At mapping fikk høy vurdering på spørsmålet om *når* mapping er nødvendig, er forenlig med at de konkrete vurderingsradene krevde hjelp. Oppgaveløsning og opplevd forståelse må derfor leses sammen.

Den siste vurderingen uttrykker deltakernes forventning om en større importjobb. Den dokumenterer ikke ytelse, utholdenhet i langvarig review eller faktisk behandling av 100–500 rader.

## 5. Kritiske sjekkpunkter og prioritering

Alle feltene `crit1`–`crit8` er `false` hos begge deltakere. Den presise konklusjonen er at **ingen av de åtte forhåndsdefinerte kritiske misforståelsene ble registrert**. Rapporten generaliserer ikke dette til at enhver mulig misforståelse er utelukket.

Begge registrerte prototypeknappene som P0 i `issue1`/`sev1`. P01-loggen beskriver at moderator måtte forklare at knapperekken med skjermnavn bare var et prototypeverktøy. P02 spurte om den var en meny. P0 gjelder derfor fjerning av denne testnavigasjonen fra den normale reisen, ikke en påvist produksjonsfeil.

`issue2` og `issue3` er tomme i begge råfiler. Standardverdiene P2 i de tilhørende severity-feltene telles ikke som egne funn. De øvrige prioritetene nedenfor følger den konsoliderte rapporten og den godkjente v6-planen.

## 6. Avtalt oppfølging i v6

Tabellen gir sporbarhet til krav-ID-ene i [UX-spesifikasjon v6](../features/IMPORT_2_0_UX_SPEC_V6.md). UX-01–12 følger testfunn og avtalte korreksjoner. UX-13 bevarer allerede godkjent produktretning. UX-14 gjelder at dokumentasjonen og prototypen henger sammen; det er ikke et nytt runtimefunn. Prosjekteiers presiseringer fra R7 og R8/R9 beholdes i §6.2–6.3. R10/R11 gir presiseringene O-20–O-23 i §6.4, og R12 gir den siste presiseringen O-24 i §6.5. De overstyrer motstridende eldre løsningsvalg og legges ikke til de opprinnelige testregistreringene.

| Krav og prioritet | Grunnlag | Krav til oppfølging | Artefaktstatus |
| --- | --- | --- | --- |
| **UX-01 · P0** | R1/R2 `issue1` | Fjern skjermmeny, testinstrumentering og vilkårlige snarveier. Behold reell steg- og reviewnavigasjon. | Innarbeidet i kravgrunnlaget for revisjon 4; se §6.2–6.5 og gjeldende kontrollstatus i §7.5. |
| **UX-02 · P1** | R1/R2 `recommendation`; R3 | Gjør hele jobben, aktuell datatype, filtrerte kandidater og manuelt utvalg eksplisitte. Vis hvilke typer og antall som omfattes. Aktive valg lagres direkte i jobbutkastet og oppsummeres i lukket seksjon og Kontroll før analyse. | Innarbeidet i kravgrunnlaget for revisjon 4; se §6.2–6.5 og gjeldende kontrollstatus i §7.5. |
| **UX-03 · P1** | `rating3`; konsoliderte anbefalinger | Forklar tre berikelsesnivåer med innhold, omfang og relativ tid/antall søk. Vis at foreløpig valg kan endres før analyse. Bildekandidater finnes automatisk når aktøren mangler et godt/godkjent bilde, uavhengig av berikelsesnivå; bildegodkjenning er fortsatt et eget valg. | Innarbeidet i kravgrunnlaget for revisjon 4; se §6.2–6.5 og gjeldende kontrollstatus i §7.5. |
| **UX-04 · P2** | `b2`, `b3`, `bnotes` | La brukeren behandle tvetydige kolonner med sammenfoldede vurderingsrader, enklere telefon-/stedsvalg og én bekreftelse. Fjern «Bruk sikre forslag». Forklar at standardpakken er ferdig mappet. | Innarbeidet i kravgrunnlaget for revisjon 4; se §6.2–6.5 og gjeldende kontrollstatus i §7.5. |
| **UX-05 · P2** | Begge `bnotes` | Endre «Distrikt» til «Region» i brukergrensesnittet. Bevar originale kildekolonnenavn og råverdier. | Innarbeidet i kravgrunnlaget for revisjon 4; se §6.2–6.5 og gjeldende kontrollstatus i §7.5. |
| **UX-06 · P2** | R1 `bnotes`; anbefalinger | Bruk «land» og «landskode» ved telefon. Ikke innfør teknisk omdøping eller skjult Norge-standard. | Innarbeidet i kravgrunnlaget for revisjon 4; se §6.2–6.5 og gjeldende kontrollstatus i §7.5. |
| **UX-07 · P2** | R1 `cnotes`; anbefalinger | Én primær tilkoblingsknapp, kort forklaring og tydelig valg av regneark/faner. Behold import uten synkronisering eller tilbakeskriving. | Innarbeidet i kravgrunnlaget for revisjon 4; se §6.2–6.5 og gjeldende kontrollstatus i §7.5. |
| **UX-08 · P2** | R1/R2 `recommendation` | Flytt intern rolle-, arkitektur- og providerinformasjon til dokumentasjon/hjelp. Behold forståelige konsekvenser, konkrete kilder og kort Kildepolicy. | Innarbeidet i kravgrunnlaget for revisjon 4; se §6.2–6.5 og gjeldende kontrollstatus i §7.5. |
| **UX-09 · P2** | R1 `dnotes`; anbefalinger | Bruk «faste farger», vanlig språk om kvadratisk bilde, musikkontor, offentlig synlighet og fullføring. Resultatet skal ha forståelige og korrekte antall tilknytninger. | Innarbeidet i kravgrunnlaget for revisjon 4; se §6.2–6.5 og gjeldende kontrollstatus i §7.5. |
| **UX-10 · P2** | R1 `dnotes`; anbefalinger | Forklar at oppføringer aldri slås sammen automatisk. Brukeren velger riktig oppføring og avgjør feltforskjellene uttrykkelig. | Innarbeidet i kravgrunnlaget for revisjon 4; se §6.2–6.5 og gjeldende kontrollstatus i §7.5. |
| **UX-11 · P2** | Anbefalinger; R4 | Skill mellom lagring av jobb/review underveis og oppdatering av CRM-profiler ved fullføring. «Godkjenn og neste» lagrer reviewbeslutningen. Eventuell eksplisitt stedsoppretting følger ADR-012. | Innarbeidet i kravgrunnlaget for revisjon 4; se §6.2–6.5 og gjeldende kontrollstatus i §7.5. |
| **UX-12 · P3** | R1 `anotes`; anbefalinger | Bruk tydelig tips-/lyspæreikon i pakkekontroll og andre infobokser. Informasjon skal kunne skilles fra feilvarsler. | Innarbeidet i kravgrunnlaget for revisjon 4; se §6.2–6.5 og gjeldende kontrollstatus i §7.5. |
| **UX-13 · Bevaringskrav** | R4; godkjent v6-plan | Behold desktopreview i tre kolonner, synlig kildepanel, kvadratisk bilde, lukkede seksjoner og avtalte farger. Samle offentlige endringer i sluttkontroll med nødvendig bekreftelse. | Innarbeidet i kravgrunnlaget for revisjon 4; se §6.2–6.5 og gjeldende kontrollstatus i §7.5. |
| **UX-14 · Artefaktkonsistens** | Godkjent v6-plan | Gjør illustrert omfang, berikelse og navigasjon meningsfullt klikkbar. Antall, tilstander og offentlig sluttkontroll skal stemme overens i prototypen og spesifikasjonen. | Innarbeidet i kravgrunnlaget for revisjon 4; se §6.2–6.5 og gjeldende kontrollstatus i §7.5. |

### 6.1 Presisering av de viktigste korreksjonene

**Omfang skal ha en synlig konsekvens.** Det konkrete problemet var at 84 aktører fremstod valgt mens 24 steder ikke var valgt, selv om brukeren kunne endre stedsregler. V6 må vise hvilke oppføringer reglene gjelder for og hvilke regler som er relevante. Et bytte mellom datatyper skal ikke i det skjulte endre omfanget. O-24 presiserer at alle fire regelgrupper er tilgjengelige i filtermodus også når en gruppe har null relevant effekt; bare det låste utvalget påvirkes. O-20 presiserer at filtre før analyse bare kan bruke innleste/mappede felt og uttrykkelige utkastvalg som faktisk foreligger. Nye importlinjer er ikke det samme som nye CRM-profiler; senere matching og reviewstatus er ikke gyldige føranalysefiltre.

**Berikelse skal forklares gjennom arbeidet som gjøres.** Forskjellen mellom målrettet og utvidet berikelse skal ikke reduseres til et udokumentert løfte om tidsbruk. Utvidet søk omfatter flere tomme, ikke-kritiske felt og kan gi flere søk. Ingen ekstern berikelse betyr ingen ekstra profil-/kontaktberikelse. Etter eierbeslutningen i R8 finner importløpet automatisk bildekandidater når en aktør mangler et godt/godkjent bilde, også når profilberikelsen er av. Bilde blir ikke automatisk godkjent eller erstattet, og søket skjer før fullføring. Ingen bestemte minutter, priser eller nye obligatoriske felt innføres gjennom forklaringen.

**Lagringsteksten skal være presis.** Ønsket «Ingen data skrives» → «Ingen data lagres» følges opp med en tydelig beskrivelse av hva som lagres når. Analyse oppdaterer ikke aktør- og personprofiler. Importjobb og reviewvalg kan lagres underveis. Fullføring gjennomfører godkjente profilendringer. En eventuell eksplisitt, separat stedsoppretting må vises som en egen handling. V6 skal dermed ikke love at ingen data overhodet lagres før fullføring.

**Forenkling skal bevare nødvendige valg.** Planer for Checkin, Mailmojo og gammel XML, detaljer om delingsdomene og roller, tekniske bildeformater og koordinat-/kartgater flyttes ut av normalflyten. Brukeren skal fortsatt kunne forstå valg av oppføring, kilde, musikkontor og offentlig synlighet. **Matcher og kilder**, BRREG-forslag, tilgang til eksisterende CRM-kort og en kort **Kildepolicy** beholdes etter presiseringen i R7. Formuleringer som «Tenanttilordninger lagt til» erstattes med vanlig språk, for eksempel «Lagt til i flere musikkontor», der teksten stemmer med den faktiske handlingen.

### 6.2 Historisk eiergjennomgang – grunnlag for revisjon 2

R7 ga korreksjonene O-01–O-09. Tabellen bevarer hva som ble endret og hvilke deler nyere beslutninger har erstattet. Den er et revisjonsspor, ikke en parallell liste med gjeldende krav. Nyere O-10–O-24 i §6.3–6.5 og den gjeldende UX-spesifikasjonen har forrang ved motstrid.

| ID | Eierkommentar og oppfølging i revisjon 2 | Status i gjeldende revisjon | Kobling til opprinnelige krav |
| --- | --- | --- | --- |
| **O-01** | Behold fire omfang og hele jobben som standard. Vis regelgrupper direkte som sammenfoldede seksjoner; flere kunne åpnes og tas med i en samlet anvendelse. | Fire omfang og synlige seksjoner består. Antall grupper, musikkontor, aktivering og anvendelse er erstattet av O-11/O-12/O-14. | UX-02, UX-14 |
| **O-02** | Fjern Rolle og status fra massevalg; avgjør dem manuelt per kobling i gjennomgangen. | Videreført. Feltene finnes ikke i massereglene eller regelmatrisen. | UX-02, UX-14 |
| **O-03** | Gjeninnfør underkategori og chips ved felt og oppsummering. Hvit tekst på hovedkategori, underkategori og redaksjonell tag; svart tekst på intern tag. | Videreført og supplert med hele den etablerte taksonomien i O-10. | UX-09, UX-13 |
| **O-04** | Gjeninnfør Identitet og matching med eksisterende, ny eller hopp over, BRREG, CRM-kort, Kilder og Kildepolicy. | Videreført; O-15 presiserer gul Kontroller treff-knapp. | UX-08, UX-10, UX-13 |
| **O-05** | Gjeninnfør Option/Alt + venstre/høyre i reviewkøen, uten å overta piltaster mens brukeren redigerer. | Videreført innen den aktuelle køen og dens grenser; O-22 presiserer felles rekkefølge og bevart kontekst. | UX-14 |
| **O-06** | Marker Samspills gjenstående musikkontorvalg med gul Bekreft-knapp i den aktuelle seksjonen. | **Erstattet av O-11.** Jobbmålet er uttrykkelig valgt på forsiden; ingen ekstra Samspill-bekreftelse skal vises. | UX-02, UX-12, UX-14 |
| **O-07** | Fjern den lange listen over oppføringer som bruker et sted; behold geografisk kontekst og intern proveniens. | Videreført. | UX-08, UX-14 |
| **O-08** | Vis Selvbetjent nytt sted på samme side med navn, land, region/fylke og kommune, med uttrykkelig oppretting eller gjenbruk. | Videreført som separat handling før profilfullføring. | UX-11, UX-13 |
| **O-09** | Gjør offentlig sluttkontroll kompakt med endringsindikator og sekundære før/etter-detaljer. | Videreført gjennom O-19 for hele siden, tre tekstlinjer og naturlig sidepanelhøyde. O-23 erstatter den tidligere avkuttingen etter tre oppføringer med komplett liste fra start. | UX-09, UX-13, UX-14 |

### 6.3 Eiergjennomgang – grunnlag for revisjon 3

R8 beskriver mangler i v6 revisjon 2 og uttrykkelige eierbeslutninger for revisjon 3. R9 gir det kontrollerte taksonomigrunnlaget. Tabellen bevarer oppfølgingen; kravene videreføres der O-20–O-24 ikke uttrykkelig presiserer eller erstatter et løsningsvalg. Gjeldende artefaktkontroll for revisjon 4 med sluttkorrigeringen føres i §7.5. Endelig UX-godkjenning er registrert på grunnlag av R12 og utført O-24.

| ID | Korreksjon fra revisjon 3 | Konkret leveransekrav og senere presisering | Sporbarhet |
| --- | --- | --- | --- |
| **O-10** | Bruk hele etablerte kategori- og underkategorilisten fra fersk main. | Alle 6 hovedkategorier vises i rullegardin der relevant. Valgt hovedkategori avgrenser de 14 etablerte underkategoriene. Samme liste brukes i jobbregler og review. Rå/importerte verdier bevares uten stille sletting eller nye katalogvalg. | UX-02, UX-09, UX-14; spesifikasjon §5.4 |
| **O-11** | Ett uttrykkelig Musikkontorvalg i Jobb og fil gjelder hele jobben. | Vis konsekvensteksten på forsiden og målkontoret senere. Fjern Musikkontor fra jobbreglene og ekstra Samspill-bekreftelse. Godkjente eksisterende profiler knyttes til målkontoret ved fullføring innen brukerens rettigheter; utelatte profiler får ingen tilknytning. | UX-02, UX-09, UX-14; §3, §8.5, §11 |
| **O-12** | Fjern alle Ta med i jobbreglene-bokser og separat anvendelse. | Fire synlige sammenfoldede regelgrupper kan åpnes direkte. Aktive feltvalg lagres i utkastet og vises når seksjonen lukkes. De fire omfangene beholdes, med et stabilt kandidatsett under redigering. | UX-02, UX-14; §5.1–5.3 |
| **O-13** | Finn bildekandidater automatisk når et godt/godkjent bilde mangler. | Ingen valgfri tilleggssjekkboks; søket er uavhengig av profilberikelsen. Ingen automatisk godkjenning, skjult erstatting av godkjent bilde eller providerarbeid ved fullføring. | UX-03, UX-11, UX-13; §6.2 |
| **O-14** | Fjern eget effektpanel og regelhistorikk. | En kort oppsummering i Kontroll før analyse viser valgene uten et ekstra bekreftelses- eller anvendelsestrinn. | UX-02, UX-09, UX-14; §5.2–5.3 |
| **O-15** | Gjør Kontroller treff gul. | Knappen i Identitet og matching åpner valgseksjonen og godkjenner ikke et treff i det skjulte. | UX-10, UX-12; §8.2 |
| **O-16** | Vis hvor Nordlys Verksteds uavklarte Vik-verdi avgjøres. | Gul Bekreft-knapp på Sted-seksjonen åpner det aktuelle valget. Stedet må fortsatt velges eller uttrykkelig utelates. | UX-12, UX-14; §8.4 |
| **O-17** | Gjeninnfør fire forståelige statuskort. | Klare / Trenger valg / Blokkert / Hoppet over får grønn/oransje/rød/grå toppkant. Tilstandene er gjensidig utelukkende; vanlig avklaring er ikke i seg selv blokkering. Tall kommer fra faktisk demotilstand. | UX-13, UX-14; §7 |
| **O-18** | Gjeninnfør Behandlingsfremdrift og Nylige jobber. | Vis reell fremdrift, aktiv/fullført lokal demojobb og lokal historikk. Ingen oppdiktede eksterne kall, jobber eller prosentmål. | UX-13, UX-14; §7 |
| **O-19** | Bruk hele v5-siden som referanse for offentlig sluttkontroll. | Lukket rad har høyst tre tekstlinjer og inline Se før og etter-pil. Klikkbart endringsmerke erstatter en høy egen Endre-rad; sidepanelene har naturlig høyde. Revisjon 3 viste tre oppføringer først med Vis alle ved flere; dette er **erstattet av O-23**. Bekreftelsen gjelder fortsatt den fullstendige endringslisten. | UX-09, UX-13, UX-14; §9.1 |

Konsekvensteksten for O-11 er: **«Legg eksisterende profiler til Musikkontoret Nord. Dette er en egen tilknytning. Profilenes opplysninger og bilde beholdes.»** Navnet følger det faktisk valgte, autoriserte kontoret. Valg av jobbmål, godkjente målprofiler og samlet fullføring uttrykker tilknytningsbeslutningen uten en ekstra boks. [ADR-011](https://github.com/fredrik-stack/kreative-norge-crm/blob/9a0eeef7ead30bf3ec168df26e2f27d4465c1be7/docs/decisions/ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md) krever fortsatt separate, auditerbare handlingstyper og riktige rettigheter. Tilknytningen endrer ikke profilens kjerneopplysninger, publisering, godkjente bilde eller image-home. Eventuelle valgte profilendringer er egne handlinger.

Offentlig sluttkontroll beholder faktiske før/etter-endringer, avpublisering, person- og kontaktvilkår og ny bekreftelse når relevante valg endres. I revisjon 3 begrenset visningen av tre oppføringer presentasjonen, men ikke planen eller bekreftelsen. O-23 fjernet denne avkuttingen. Tre **tekstlinjer per oppføring** beholdes.

Eiergjennomgangene øker ikke antall formelle deltakere og endrer ikke konklusjonen om 16 av 18 toppvurderinger, mappinghjelp og berikelse 2,5 av 5. Disse historiske oppfølgingene startet ikke runtime eller en ny fase. R12 bestiller nå én komplett dokumentasjonsprompt etter utført sluttkorrigering.

### 6.4 Gjeldende eierpresiseringer – grunnlag for revisjon 4

R10 er eierkommentarene til revisjon 3, og R11 er den etterfølgende read-only-avklaringen og uttrykkelige godkjenningen av presiseringene. Tabellen skiller mellom funnet og hvordan det lukkes i kravgrunnlaget. Eiers siste gjennomgang er senere utført og dokumentert i R12, med den ene sluttkorrigeringen O-24 i §6.5. Kontroll før eiergjennomgangen står i §7.4; kontroll av den endelige filen står i §7.5.

| ID | Funn og avklaring | Innarbeiding i revisjon 4 | Sporbarhet |
| --- | --- | --- | --- |
| **O-20** | Jobbfiltrene blandet nye importlinjer med nye CRM-profiler og brukte reviewstatus før review. Alle rader er nye i jobben, men CRM-identiteten avgjøres senere. | Behold fire omfang. Filtrert utvalg tilbyr Aktører eller Personer og tre feltbaserte filtre: **Mangler hovedkategori**, **Mangler relevant underkategori**, **Telefon uten avklart land**. Vis forklaring, treffantall og kandidater. Fjern «Nye oppføringer», «Ikke gjennomgått» og generelt «Trenger et valg» fra jobbfiltrene; Ikke gjennomgått beholdes i reviewkøen. | R10/R11; UX-02, UX-14; spesifikasjon §5.1 og O-20 |
| **O-21** | Saga Lunds toppvarsel om telefoneier hadde ingen tilsvarende gul handling på Kontaktopplysninger. Andre nødvendige valg brukte separate markeringer, og mislykket godkjenning kunne åpne feil seksjon. | Samme strukturerte problemoversikt driver antall, toppvarsel, gul seksjonsknapp og navigasjon. Alle nødvendige reviewvalg har riktig gul handling, også telefonland/-eier, nettsidekonflikt, taksonomi, sted og målaktør. Flere problemer i samme seksjon samles. Åpning/fokus godkjenner ingen verdi; avhengighetshopp har synlig retur. | R10/R11; UX-06, UX-10, UX-12, UX-14; §8.1 og O-21 |
| **O-22** | Hundrevis av kandidater må ikke gjøre arbeidsflaten høyere/bredere. Kildegjennomgangen viste også at kandidatvalg kunne nullstille søk/filter, og at knapper og piltaster ikke brukte samme kø. | Avgrens køens bredde/høyde; hold søk/filter fast og rull bare listen. Vis én kandidat i midten og synlige kilder til høyre, med intern rulling. Bevar filter, søk, køposisjon og fokus. Forrige/neste og Option/Alt bruker samme utvalg, stopper ved grensene og håndterer at en godkjent kandidat faller ut av filteret. Vis tom kø uten skjult reservekandidat. | R10/R11; UX-13, UX-14; §§8.1 og 12.1, O-22 |
| **O-23** | Den fjerde offentlige endringen var Saga Lunds visning hos Fjordfestivalen, skjult bak Vis alle mens sidekortet allerede telte den. Selve planen omfattet personvisningen. | Alle aktørendringer og personvisninger ligger i én komplett liste fra start, med rulling ved mange rader. Fjern avkutting etter tre oppføringer og Vis alle-knappen. Behold tre tekstlinjer per lukket oppføring og Se før og etter. Vis aktuelle person-/aktørnavn og konkret offentlig endring; sidekort og bekreftelse bruker hele samme liste. | R10/R11; UX-09, UX-13, UX-14; §9.1 og O-23 |

**Avgrensning av O-20:** Filtrene bruker bare importerte/mappede felt og uttrykkelige utkastvalg som foreligger før analyse. Tom hovedkategori er forskjellig fra en bevart ukjent verdi. Manglende underkategori gjelder bare tom verdi under en etablert hovedkategori som faktisk har underkategorier; Kreativ teknologi og Litteratur treffes ikke. En bevart ugyldig verdi slettes ikke. Telefonfilteret krever et ikke-tomt nummer uten innledende `+` og uten valgt land; tomme og internasjonale numre treffes ikke. Kandidatutvalget holdes fast under samme redigering, og nytt filtervalg tar nytt utvalg. Null treff er et synlig tomt utvalg. Ingen nye obligatoriske kategorifelt eller retur til jobbregler etter analyse innføres.

**Avgrensning av O-21/O-22:** Den gule garantien gjelder nødvendige valg i gjennomgangen. Den gjeninnfører ikke musikkontorbekreftelse eller obligatorisk bildevalg, og gjør ikke tidligere mapping eller et frivillig nytt-sted-utkast til nye krav. Mislykket godkjenning åpner første reelle problemseksjon. Et uttrykkelig avhengighetshopp kan åpne en målaktør utenfor søket, med tydelig retur til bevart køkontekst; vanlig Neste/piltast hopper aldri til en ufiltrert reserve. Én kølinje er én konsolidert kandidat, ikke ett feltproblem. Teknisk virtualisering, sidevisning og produksjonsytelse avklares i 5E; denne revisjonen dokumenterer ingen lastmåling eller visuell nettleserprøve.

Når siste feltavklaring fjerner et filtertreff, beholdes den aktuelle kandidaten åpen til et uttrykkelig valg om å godkjenne eller gå videre. Videre navigasjon bruker gjenværende naboer fra den opprinnelige filtrerte rekkefølgen. Dette er innarbeidet i O-22 og innfører ingen automatisk godkjenning.

**Avgrensning av O-23:** Personvisning betyr personen hos en konkret publisert aktør med aktiv kobling og uttrykkelig visningsvalg; kontaktkanalene har egne valg. Det innføres ingen selvstendig offentlig personside. Radnavn følger før-/etter-planen når et navn endres, og før-identiteten ved fjerning. Full offentlig endringsfingerprint, oppheving av gammel bekreftelse ved relevant endring og eksisterende fullføringsvilkår beholdes. Tre aktørendringer og én personvisning skal gi fire oppføringer og samsvarende antall i sidekortene.

### 6.5 Sluttpresisering og endelig UX-godkjenning – O-24

R12 er prosjekteiers siste manuelle gjennomgang av v6 revisjon 4, fulgt av en uttrykkelig bestilling om bare én retting og deretter direkte dokumentasjonsleveranse. De tre feltbaserte filtrene i O-20 er godkjent og beholdes uendret. Korreksjonen er utført i samme **v6 revisjon 4**, uten nytt revisjonsnummer.

| ID | Eierfunn og beslutning | Utført sluttkorrigering | Sporbarhet |
| --- | --- | --- | --- |
| **O-24** | Etter valg av Filtrerte kandidater må massevalgene under være aktive og tilgjengelige. Behold de tre filtrene og alle andre godkjente deler av revisjon 4. | **Kategorier og tags, Telefon, Berikelsesnivå og Stedsavklaring** viser aktive kontroller i filtermodus, også ved null treff eller null relevant effekt for en gruppe. Valgte regler vises i den sammenfoldede oppsummeringen med korrekt antall. Det låste filterutvalget utvides ikke. | R12; UX-02, UX-14; O-20; UX-spesifikasjon §5 og O-24 |

**Omfang og null effekt:** Regelvalgene gjelder bare det låste utvalget av aktør- eller personprofiler. Når utvalget er tomt, eller ingen av de valgte profilene har relevante data for en gruppe, kan regelen fortsatt velges og oppsummeres, men visningen oppgir null effekt og ingen kandidater endres. Et senere feltvalg beholder det samme utvalget selv om den opprinnelige mangelen er rettet.

**Stedsavklaring:** Regelen gjelder stedsopplysningene til profilene i det låste utvalget. Den endrer ikke den felles stedskandidaten eller andre profiler som bruker samme sted. Oppsummeringen teller distinkte, ikke-tomme stedsverdier og faktisk berørte profiler; to valgte profiler med Bodø gir én stedsverdi. En valgt profil uten sted har fortsatt en tilgjengelig stedsseksjon med null effekt. Nullstilling av regelvalget gjenoppretter utgangspunktet.

**Feltavhengigheter og bevaring:** Underkategori krever fortsatt valgt hovedkategori og tilbyr bare etablerte, tilhørende underkategorier. Tilgjengelige regelgrupper opphever ikke denne reelle feltavhengigheten. Andre omfang beholder sine datatypeavgrensninger. De tre filtrene, den øvrige godkjente brukerreisen og alle andre beslutninger i revisjon 4 er beholdt.

**Godkjenningsstatus:** R12 og utført O-24 avslutter UX-arbeidet som **endelig godkjent av prosjekteier**. Korreksjonen er kilde- og logikkontrollert som beskrevet i §7.5. Den er ikke manuelt retestet, fordi prosjekteier uttrykkelig ba om å gå videre uten en ny manuell runde. Dokumentene lagres på dokumentasjonsbranchen for separat PR-review; merge og Fase 5E gjenstår; denne godkjenningen starter ikke runtimeimplementering.

## 7. Hva valideringen understøtter

Grunnlaget er tilstrekkelig for prosjekteiers beslutning om å videreføre den testede produktretningen og avslutte brukertestingen med de avtalte korreksjonene. Det er ikke dokumentasjon på at Google Sheets, BRREG, bildebehandling, matching, datalagring eller PUBLIC-commit virker i runtime. Tidsfeltene i rådata brukes heller ikke som ytelsesmålinger.

Den klikkbare v6 er et dokumentasjonsartefakt med illustrerte data og avgrenset lokal interaksjon. Kontroll av at skjermene fungerer og stemmer med spesifikasjonen er **artefaktkontroll**, ikke en ny brukertestrunde. Den erstatter heller ikke senere tekniske tester eller stagingverifisering.

### 7.1 Historisk kontroll av første v6-leveranse

Den første v6-leveransen 11. oktober 2026 ble kontrollert gjennom isolert JavaScript-kjøring med et minimalt DOM-grensesnitt samt kildegjennomgang. **20 av 20 målrettede kontroller av interaksjonslogikken passerte** for den daværende filen. Dette er et historisk resultat; det overføres ikke til den reviderte filen som et nytt bestått resultat.

Den historiske kontrollen omfattet ikke visuell nettleserverifisering. Nettlesermiljøets sikkerhetspolicy blokkerte lokale HTML-filer. Prosjekteiers etterfølgende gjennomgang er dokumentert separat i R7 og viste konkrete revisjonsbehov. Ingen av disse forholdene endrer testdataene fra P01 eller P02.

### 7.2 Historisk kontroll av revisjon 2

Den 11. oktober 2026 kl. 18.10 UTC passerte **29 av 29 målrettede kilde- og JavaScript-kontroller** for den daværende revisjon 2. Kontrollen omfattet syntaks, generert HTML/CSS og isolert kjøring av funksjoner og hendelseshåndterere med et minimalt DOM-grensesnitt. Den var avstemt mot UX-01–14 og O-01–09 slik de var spesifisert på det tidspunktet.

Dette er et historisk resultat for en tidligere artefaktversjon. Flere av de kontrollerte løsningene er uttrykkelig erstattet av O-10–O-19. **29 av 29 kan derfor ikke brukes som kontrollresultat for revisjon 3 eller 4.** Kontroll av fokus, faktisk museklikk, visuell nettleserutforming og nettleserens lagrings-/nedlastingsatferd var ikke omfattet.

### 7.3 Historisk kontroll av revisjon 3

Revisjon 3 ble avstemt mot UX-01–14, videreførte O-01–O-09 og daværende O-10–O-19. Den 11. oktober 2026 kl. 20.36.44 UTC passerte **34 av 34 målrettede kontroller** på den daværende frosne prototypefilen. Metoden var syntakskontroll, gjennomgang av HTML/CSS-kilden og isolert JavaScript-kjøring med et minimalt DOM-grensesnitt. Kjøringen brukte `verify_prototype_v6_revision3.cjs`; resultatet bevares som historisk revisjon-3-grunnlag.

Kontrollen omfattet importgrenene, lokal gjenåpning og korrekte resultattall, verifisert taksonomi, de fire direkte regelgruppene og omfangene, ett uttrykkelig jobbfelles musikkontor, automatisk bildekandidatstatus, gule avklaringsknapper, dashboard og faktisk lokal jobbhistorikk. Offentlig sluttkontroll beholdt full endringsliste, feltendringer, avpublisering, personkontaktvilkår og ny bekreftelse etter endring. Omfang og avgrensninger er utdypet i UX-spesifikasjonen §14.1.

Historisk kontrollert fil: `import_2_0_prototype_v6.html`, revisjon 3. **SHA-256:** `b7321dcd87b12a279f4376892ded47c773f44eb9fef15bb469c57ae8b6b62078`. Filhashen var identisk etter den kontrollen. Resultatet gjelder revisjon 3 og kan ikke brukes som beståttkontroll for revisjon 4.

Den historiske artefaktkontrollen var ikke en ny brukertestrunde eller runtime-/stagingtest. Kilde- og logikkontrollen registrerte ikke visuell nettleserverifisering som bestått. De etterfølgende eierfunnene R10/R11 presiserer hva som måtte revideres videre.

### 7.4 Historisk kontroll av revisjon 4 før siste eiergjennomgang

Revisjon 4 ble før eiergjennomgangen avstemt mot UX-01–14, videreførte O-01–O-19 og presiseringene O-20–O-23. Dette var filen som ble levert til prosjekteiers siste manuelle gjennomgang. Kontrollresultatet og hashen nedenfor er historiske etter den senere sluttkorrigeringen O-24; gjeldende kontroll står i §7.5.

<!-- REV4_OWNER_TESTED_QA_START -->
**Historisk kontroll av revisjon 4 før eiergjennomgangen: 45 av 45 målrettede kontroller bestått.** Kjøringen ble gjennomført 12. oktober 2026 kl. 17.28.42 UTC på den daværende, frosne HTML-filen. Metoden var syntakskontroll, gjennomgang av HTML/CSS og isolert JavaScript-kjøring med et minimalt DOM-grensesnitt og syntetisk rulling. Resultatet er bevart i `prototype_qa_results_revision4_owner_tested.json`, med kjøring fra `verify_prototype_v6_revision4.cjs`.

| Kontrollomfang | Bekreftet i kilde og isolert logikk |
| --- | --- |
| O-20 / jobbfiltre | De tre føranalysefiltrenes feltvilkår, tomt utvalg, skille mellom tom og bevart ugyldig verdi, ingen matching-/reviewstatus som filtergrunnlag og fast utvalg under feltredigering. |
| O-21 / avklaringshandlinger | Alle nødvendige problemtyper peker til riktig seksjon. Saga med to telefonvalg får én seksjonsinngang, mislykket godkjenning åpner avklaringen, og knappene godkjenner ingenting. |
| O-22 / kø og retur | Klikk, knapper og Option/Alt følger samme søk/filter. Godkjenning og begge utelatingsveier hopper ikke over neste kandidat. Siste feltavklaring beholder kandidaten til uttrykkelig handling. Avhengighet utenfor Saga-søk har synlig retur. Tom kø åpner ingen reservekandidat. |
| O-22 / rulling og antall | Simulert utskifting av DOM-innhold bevarer rulling og feltfokus. Retur åpner lagrede seksjoner før rulleposisjonen settes. En syntetisk kø med 300 kandidater rendrer én detaljflate og bruker samme rekkefølge; dette er en logikkontroll, ikke en ytelses- eller nettlesermåling. |
| O-23 / offentlig liste | Alle fire endringer vises i eksemplet med tre aktører og én personvisning. Før-/etter-navn brukes ved endring og fjerning. Fullstendig offentlig plan, kanalvilkår, bekreftelsesfingerprint og oppheving av gammel bekreftelse ved relevant endring er bevart. |
| Videreførte flyter | De tre importveiene, åtte demokandidater, lokal gjenåpning, resultatantall, taksonomi, jobbdekkende musikkontor, direkte regler, automatisk bildekandidatstatus, dashboard og lokal jobbhistorikk. |

En uavhengig kildegjennomgang fant fem konkrete integrasjonspunkter som ble lukket før denne kjøringen: layout for hovedhandlinger, rekkefølgen ved gjenoppretting av åpne seksjoner/rulling, felles utelatingslogikk, fokus inne i avklaringsseksjonen og lange kildenavn i smal høyrekolonne. Dette dokumenterer kildekontroll, ikke observerte nettleserpiksler.

Historisk kontrollert fil: `import_2_0_prototype_v6.html`, **v6 revisjon 4 før O-24**. **SHA-256:** `b75267934a7faf712acbe9ee4dcc245835d2aaf77100ceae6b9777561211940a`. Dette er filen som ble levert før prosjekteiers siste manuelle gjennomgang. Hashen gjelder ikke den sluttkorrigerte filen.
<!-- REV4_OWNER_TESTED_QA_END -->

Agentens visuelle nettleserverifisering ble ikke gjennomført for denne historiske kontrollen. Prosjekteiers etterfølgende manuelle gjennomgang er dokumentert i R12 og ga den ene sluttkorrigeringen O-24.

### 7.5 Gjeldende kontroll av revisjon 4 etter O-24

**45 av 45 målrettede kontroller passerte på sluttfilen** 12. oktober 2026 kl. **18.35.25.906 UTC**, registrert i `prototype_qa_results.json` og kjørt med `verify_prototype_v6_final.cjs`. Dette er en ny kjøring på den sluttkorrigerte filen, ikke gjenbruk av kontrollresultatet fra §7.4. Metoden var kildekontroll og isolert JavaScript-kjøring med et minimalt DOM-grensesnitt og syntetisk rulling. Den videreførte matrisen kontrollerer blant annet importveier, review, offentlig sluttkontroll, lokale resultater, taksonomi, omfang og kønavigasjon.

En separat, uavhengig kontroll, **`final_scope_audit`**, rapporterte **8 av 8 kontrollgrupper uten funn** på samme sluttfil. Denne kontrollen rettet seg mot O-24 og bekreftet aktive kontroller for alle tre filtre og begge profiltyper, ærlig null effekt, virkninger bare innen det låste utvalget, stedsregler uten endring av felles stedskandidat eller andre profiler, telling av distinkte stedsverdier, nullstilling, underkategoriavhengighet og bevaring av andre omfang. De to kontrollresultatene har forskjellige omfang og rapporteres separat; de summeres ikke til én testtelling.

Kontrollert fil: `import_2_0_prototype_v6.html`, **v6 revisjon 4 med O-24**. **Størrelse:** 200 869 byte. **SHA-256:** `938a40ea725772d96a70fb660a228652070047e3d1d6b3eeebe24aa324499628`. Tidligere kontrollresultater og hasher gjelder bare sine historiske filversjoner.

**Agentens visuelle nettleserinspeksjon er ikke gjennomført.** Nettlesermiljøets tidligere avslag på lokale HTML-filer står ved lag. Kilde- og logikkontroll kan ikke bevise faktisk layout, fokus, museklikk eller nettleserens lagrings-/nedlastingsatferd, og syntetiske kandidater dokumenterer ikke produksjonsytelse for hundrevis av oppføringer. Prosjekteiers siste manuelle gjennomgang av revisjon 4 er derimot **utført**, dokumentert i R12. O-24 er ikke manuelt retestet etter eiers uttrykkelige instruks om å gå direkte videre. Dette er endelig UX-godkjenning med en kontrollert sluttkorrigering, ikke en ny formell brukertestrunde. Browser-aktiv Codex er fortsatt en hard gate ved senere UI-implementering.

## 8. Lukking av 5D og overgang til 5E

Produkt-/UX-delen av Fase 5D er **endelig godkjent**. Prosjekteiers siste manuelle gjennomgang er utført, og den eneste bestilte sluttkorrigeringen O-24 er innarbeidet og teknisk kontrollert. Ingen ny manuell prototypetest eller formell brukertestrunde avventer.

Den vedtatte rekkefølgen og faktiske statusen er:

1. **Utført:** Ferdigstill v6 revisjon 4 med UX-01–14 og videreførte eierkorreksjoner O-01–O-23; gjennomfør prosjekteiers siste manuelle artefaktgjennomgang (R12).
2. **Utført:** Innarbeid bare sluttpresiseringen O-24 og kontroller sluttfilen. Endelig UX-godkjenning følger R12 og utført korreksjon; det skal ikke bes om en ny manuell runde.
3. **Denne dokumentasjonsleveransen:** Hele brukertestrapporten og UX-spesifikasjonen lagres på `docs/phase5d-ux-v6-close` og leveres i én draft PR, sammen med synkroniserte statusdokumenter, roadmap og changelog. Separat review og merge gjenstår; dokumentene finnes ennå ikke på `main`. Eksakt PR-head og CI føres i GitHub og leveranserapporten.
4. **Ikke startet:** Kontroller fersk `main` etter dokumentasjonsleveransen og gjennomfør Fase 5E som en read-only, beslutningsklar implementerings- og testplan.
5. **Ikke autorisert av denne UX-godkjenningen:** Runtimearbeid. Det følger først etter godkjent Fase 5E-plan og de nødvendige grunnmur-/aktiveringsportene. Browser-aktiv Codex er en hard gate ved senere UI-implementering.

Fase 5E skal avklare gapet mellom målarkitektur og runtime og foreslå en liten, reverserbar leveranserekkefølge med nødvendige data-, lagrings-, migrerings-, test- og driftsporter. Denne rapporten fastsetter ingen ny teknisk implementeringsrekkefølge eller omnummerering av senere faser. Ved avslutning av dokumentasjonsleveransen skal godkjenningene og den faktiske repo-statusen være etterprøvbare hver for seg.
