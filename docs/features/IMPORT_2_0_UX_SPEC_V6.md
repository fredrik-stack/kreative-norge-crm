# Import 2.0 – UX-spesifikasjon v6, revisjon 4

**Prosjekt:** Kreative Norge CRM\
**Dato:** 12. oktober 2026\
**Leveransestatus:** **OWNER-APPROVED** 12. oktober 2026, med sluttkorrigering O-24 innarbeidet og kontrollert\
**Repo-baseline:** `fredrik-stack/kreative-norge-crm` · `main` på `9a0eeef7ead30bf3ec168df26e2f27d4465c1be7`\
**Tilhørende prototype:** import_2_0_prototype_v6.html (separat levert artefakt: `import_2_0_prototype_v6.html`, v6 revisjon 4 med O-24, SHA-256 `938a40ea725772d96a70fb660a228652070047e3d1d6b3eeebe24aa324499628`; ikke innchecket i denne PR-en)\
**Tilhørende rapport:** [Fase_5D_Brukertestrapport_2026-10-11.md](../status/PHASE_5D_USER_TEST_REPORT_2026-10-11.md)

## 1. Status, mandat og kildegrunnlag

Dette dokumentet fastsetter brukeropplevelsen som skal overleveres fra Fase 5D til Fase 5E. Det innarbeider funnene fra prototype v5, den godkjente v6-planen og prosjekteiers etterfølgende gjennomganger 11.–12. oktober 2026. **Revisjon 4** presiserer hvilke filtre som kan brukes før analyse, peker til alle nødvendige valg med gule seksjonsknapper, avgrenser gjennomgangskøen til skjermrammen og viser alle offentlige aktør- og personendringer i én liste fra start. Jobbfelles musikkontor, direkte regelvalg, automatisk søk etter manglende bildekandidater og det kompakte dashboardet fra revisjon 3 beholdes. Prosjekteier har gjennomført sin siste egen gjennomgang og bestilt én avgrenset sluttkorrigering: alle fire jobbregelgrupper skal være tilgjengelige ved filtrerte kandidater. Korrigeringen O-24 er innarbeidet og kontrollert. V6 revisjon 4 er dermed **endelig UX-godkjent** på grunnlag av eierbeslutningen R12; eier har uttrykkelig bestilt direkte overgang til dokumentasjonsprompt uten en ny manuell prototyperunde. Eiergjennomgangene er artefaktgjennomganger og endrer ikke den avsluttede formelle brukertestrunden. Dokumentet beskriver ønsket produktatferd, ikke ferdig CRM-runtime.

| Forhold | Status ved denne leveransen |
| --- | --- |
| Intern brukertest og overordnet produktretning | Owner-approved etter to formelle kollegatester og prosjekteiers egen grundige gjennomgang. |
| Avgrensning og rekkefølge for v6 og videre arbeid | Godkjent av prosjekteier 11. oktober 2026. |
| Korreksjoner og presiseringer i dette dokumentet | Innarbeidet i v6 revisjon 4; opprinnelige funn UX-01–14 og eierkorreksjoner O-01–O-24 er sporbare. Nyere beslutninger erstatter motstridende eldre løsninger. Gjeldende artefaktkontroll føres i §14.1. |
| Endelig UX-godkjenning av v6 | Owner-approved 12. oktober 2026 på grunnlag av R12 og utført sluttkorrigering O-24. Ingen ny manuell prototypetest gjenstår som gate. |
| Dokumentasjonsleveranse til GitHub | Rapport og spesifikasjon er lagret i full lengde gjennom [PR #73](https://github.com/fredrik-stack/kreative-norge-crm/pull/73). Skrivebeskyttet review er gjennomført uten blokkerende funn; prosjekteier har bestilt kontrollert merge 2026-10-12. Eksakt siste head, mergestatus, mergecommit og PR-/main-CI følger GitHub og leveranserapporten. |
| Runtimeimplementering og aktivering av Import 2.0 | Ikke startet gjennom denne leveransen. |

Fersk `main`, aktiv kode, migrasjoner, `docs/`, CI og verifisert stagingadferd er autoritative for faktisk systemstatus. ADR-011 og ADR-012 beskriver godkjent målarkitektur og er fortsatt ikke runtimeimplementert. Nyere uttrykkelige prosjekteierbeslutninger styrer produktprioriteringen og korrigeringene nedenfor; eldre planvarianter gjeninnføres ikke. Handoff, testgrunnlag og denne v6-leveransen må aldri brukes som bevis på gjennomført datamigrering eller aktivering.

`main` ble kontrollert på nytt 12. oktober 2026 før sluttkorrigeringen O-24 og dokumentasjonsprompten. Sammenligningen mot oppgitt baseline var identisk, med 0 commits foran og 0 bak. Tilhørende CI-run `33432010099` har seks av seks jobber grønne; dette er den eksisterende kjøringen fra 31. august 2026, kontrollert tidligere under revisjonsarbeidet, ikke en ny CI-kjøring for sluttkorrigeringen. Kjørende staging er ikke kontrollert på nytt. Stagingfunnene om importstorage er datert 30. august 2026, ikke en ny måling. Se [repo-baseline](https://github.com/fredrik-stack/kreative-norge-crm/commit/9a0eeef7ead30bf3ec168df26e2f27d4465c1be7), [CI](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/33432010099) og [5A-evidens][5A].

Normative arkitekturgrenser i spesifikasjonen kommer særlig fra [ADR-011][ADR11], [ADR-012][ADR12], [ADR-005][ADR5] og [importarkitekturen][IMPORT]. Den vedlagte eldre rollematrisen kan gi bakgrunn, men overstyrer ikke ADR-011s skille mellom plattform-superadmin, tenantroller og handlingsspesifikke rettigheter.

Funnreferansene peker til følgende uendrede originalgrunnlag:

- `Kreative_Norge_CRM_Handoff_Fase_5D_til_5E_2026-10-11(1).md`.
- `Fase_5D_Brukertestrapport_2026-10-11(1).md`.
- `P01 brukertest(1).json` og `P02(2).json`.
- `import_2_0_wireframe_prototype_v5_brukertest(1).html`.

**R7 – prosjekteiers kommentarer til første v6, 11. oktober 2026** begrunnet revisjon 2. Fire skjermbilder følger kommentaren: `Skjermbilde 2026-10-11 kl. 18.47.58.png` (jobbregler), `Skjermbilde 2026-10-11 kl. 18.57.18.png` (kategorier/tags), `Skjermbilde 2026-10-11 kl. 19.18.31.png` (identitet og kilder) og `Skjermbilde 2026-10-11 kl. 19.44.38.png` (selvbetjent sted).

**R8 – prosjekteiers kommentarer til v6 revisjon 2, 11. oktober 2026** begrunnet revisjon 3 og overstyrte motstridende tidligere prototypevalg. De fire skjermbildene viser Behandlingsfremdrift/Nylige jobber (`Skjermbilde 2026-10-11 kl. 21.57.33.png`), statuskort (`Skjermbilde 2026-10-11 kl. 21.59.38.png`), v5s offentlige sluttkontroll (`Skjermbilde fra v5 kontroll offentlige endringer.png`) og den for høye revisjon-2-visningen (`Skjermbilde v6 rev2 kontroller offentlige endringer.png`). R7/R8 er registrert i rapportens kilderegister; §13 skiller mellom gjeldende og erstattede korreksjoner.

**R9 – taksonomi fra fersk `main`** er [aktiv Editor-taksonomi][TAXONOMY], avstemt mot repoets taksonomimigrasjoner. Den gir seks etablerte hovedkategorier og fjorten underkategorier. Dette er kode- og migrasjonsgrunnlaget, ikke et nytt uttrekk fra kjørende database. Verdiene står i §5.4.

**R10 – prosjekteiers kommentarer til v6 revisjon 3, 12. oktober 2026** gjelder preanalysefiltre, manglende gul seksjonsknapp ved Saga Lunds telefonvalg, køens plassbehov ved mange kandidater og synlighet for personendringer. Skjermbildet `Skjermbilde 2026-10-12 kl. 09.16.02.png` viser tre aktørrader mens oppsummeringen teller én personvisning i tillegg.

**R11 – read-only-avklaring og prosjekteiers uttrykkelige godkjenning/bestilling av revisjon 4, 12. oktober 2026** fastsetter presiseringene O-20–O-23. Gjennomgangen av revisjon 3 viste at personvisningen lå som fjerde oppføring bak «Vis alle», og at føranalysefiltrene blandet importerte felt med senere matching-/reviewstatus. Revisjon 4 retter dette uten å åpne et nytt løp for jobbregler etter analyse. R10/R11 endrer ingen formelle testregistreringer.

**R12 – prosjekteiers siste manuelle gjennomgang av v6 revisjon 4 og bestilling av sluttkorrigering/dokumentasjonsleveranse, 12. oktober 2026** bekrefter at bare én ting gjenstår: de tre nye filtrene skal beholdes, og alle fire jobbregelgrupper skal være aktive og tilgjengelige når et filter er valgt. Prosjekteier bestiller uttrykkelig bare denne rettingen og deretter én komplett Codex-prompt, uten en ny revisjon til manuell testing. O-24 dokumenterer rettingen og kontrollen. Dette er grunnlaget for endelig UX-godkjenning etter at O-24 er utført; det er ingen ny formell testdeltaker eller godkjenning av runtimeimplementering.

P01-navnet kommer fra filnavn og handoff; råfilens `participant` er tomt. Felles anbefalingstekst i råloggene behandles som konsolidert moderatorregistrering. Prosjekteiers egen test regnes ikke som en tredje formell JSON-test. Testtall og metode er samlet i den tilhørende rapporten.

## 2. Produktmål og avgrensning

Importen skal gjøre det mulig å behandle mange aktører, personer, koblinger og steder uten å miste oversikten over identitet, kilder og konsekvenser. Brukeren skal bruke mest oppmerksomhet på usikre valg, kunne fortsette senere og se hva som faktisk blir lagret eller offentlig.

Tre innganger beholdes: standard importpakke, egen CSV/XLSX og Google Sheets. De fører til samme jobbregler, analyse, review og sluttkontroll. Desktop er primær arbeidsflate. Full mobilimport inngår ikke i MVP; dette begrenser ikke at status og enklere enkeltoppgaver senere kan gjøres tilgjengelige på mobil.

V6 innfører ingen automatisk sammenslåing, geografisk tilknytning til musikkontor eller publisering. Tomme importceller bevarer eksisterende verdier. Bilde er valgfritt. V5s demonstrasjon av manglende kontaktpunkt og sted innfører ikke universelle nye minimumskrav. Den konkrete felt- og blokkeringsmatrisen skal avstemmes mot kode og godkjente beslutninger i 5E.

Produktets volumambisjon endres ikke fordi prototypen bruker åtte kandidater. Deltakernes positive vurdering av 100–500 rader er en vurdering av forventet egnethet, ikke en kapasitetsmåling. V6 inneholder ingen nye ytelser, behandlingstider eller kostnader som er målt i runtime.

## 3. Jobben, navigasjonen og lagring underveis

En importjobb har navn, én operativ musikkontortilknytning, én ansvarlig reviewer, kildegrunnlag og lagrede valg. På skjermen brukes «Musikkontor» om arbeidskonteksten. Brukeren velger kontoret **uttrykkelig under Jobb og fil på første side**, blant kontorene hen er autorisert til å bruke. Valget gjelder hele importjobben. Det brukes ingen ny avkryssing eller ekstra bekreftelse i Jobbregler eller på hver kandidat.

Ved feltet vises konsekvensen: **«Legg eksisterende profiler til Musikkontoret Nord. Dette er en egen tilknytning. Profilenes opplysninger og bilde beholdes.»** Navnet følger valgt musikkontor. Dermed er tilknytningen en uttrykkelig jobbeslutning; den oppstår ikke som skjult følge av matching eller geografi. Planlagte tilknytninger vises i review og sluttkontroll og utføres først ved fullføring for de kandidatene som tas med. Andre, særskilt reviewede profilendringer behandles fortsatt som egne handlinger. Dette konkretiserer [ADR-011 §14][ADR11] etter eierbeslutning O-11.

Brukeren ser den faktiske stegvisningen: **Kilde og jobb → Kontroll eller mapping → Jobbregler → Analyse → Review → Sluttkontroll → Resultat**. Kontroll og mapping er alternative grener. Reviewkøen gir ordinær navigasjon mellom kandidater. Det finnes ingen synlig meny over prototypeskjermer og ingen snarvei som godkjenner eller hopper over nødvendig arbeid.

Utkast og reviewvalg lagres underveis. Grensesnittet skiller mellom «Lagrer», «Lagret» og «Kunne ikke lagre». En mislykket lagring skal ikke vises som vellykket. Ved gjenåpning vises samme kildegrunnlag, regler, beslutninger og gjenstående arbeid. Å gå tilbake skal ikke slette arbeidet. Hvis brukeren endrer et tidligere valg som påvirker senere beslutninger, vises hva som må kontrolleres på nytt.

Jobbregler kan endres i utkastet **før analysen starter**. Den ordinære reisen har ingen retur fra review til jobbregler. Senere kandidatvalg gjøres i review; bevaring ved tilbakekomst gjelder navigasjon mellom kandidater, kildedetaljer, dashboard og sluttkontroll, og innfører ikke en ny mulighet til å anvende masseregler underveis i review.

| Jobbtilstand | Hva brukeren ser og kan gjøre |
| --- | --- |
| Utkast | Velge kilde, kontrollere innhold, mappe og lagre jobbregler. |
| Analyse pågår | Se delsteg og status; forlate siden og komme tilbake. Klare kandidater kan gjøres tilgjengelige fortløpende. |
| Review | Vurdere kandidater, rette konflikter, hoppe over og lagre beslutninger. |
| Sluttkontroll | Se konsolidert plan og kontrollere offentlige konsekvenser. |
| Fullføring pågår | Se at lagring behandles; gjentatte klikk starter ikke en ny import. |
| Fullført eller trenger oppfølging | Se faktisk resultat, feil og kandidater som er beholdt for senere arbeid. |

Dette er en brukeropplevelseskontrakt. Valg av bakgrunnskø, API, transaksjonsgrenser og teknisk gjenopptakelse tilhører 5E.

## 4. De tre importveiene

### 4.1 Kreative Norge-importpakke

Brukeren velger standardpakken og laster opp én XLSX med arkene `AKTØRER`, `PERSONER`, `KOBLINGER` og `STEDER`. Hen får jobbnavn, musikkontor, ansvarlig reviewer, synlig telefonland og et foreløpig berikelsesvalg. «Last ned siste KI-prompt» skal hente gjeldende godkjente prompt, og hjelpen forklarer kort hvordan den brukes til å lage standardpakken.

Neste skjerm er **Kontroller importpakken**. Den viser identifisert format, ark, radantall og kontroll av kildeidentiteter og referanser. Den tydelige tipsmeldingen er: «Standard importpakke hopper over mapping fordi feltene allerede er koblet.»

Strukturfeil vises ved riktig ark eller referanse med forklaring på hva som må rettes. Enkelte uavklarte kandidater trenger ikke stoppe resten av jobben. Systemet skal ikke reparere tvetydige identiteter skjult. Gyldig pakke går direkte til Jobbregler.

De fire arknavnene er vedtatt. Eksakte nye kolonnenavn, pakkeversjon og full produksjonskontrakt skal avstemmes i 5E. Prototypen etablerer ikke en ny autoritativ importmal.

### 4.2 Egen CSV eller XLSX

Brukeren velger fil og angir ved behov om den inneholder aktører, personer eller begge. I XLSX velges relevante ark. Systemet foreslår struktur og kolonnemapping, og viser kildenavn og eksempelverdier sammen med foreslått CRM-felt.

Sikre forslag er forhåndsutfylt. Vurderingsrader starter sammenfoldet med status «Krever valg». Brukeren åpner og avgjør dem. Knappen «Bruk sikre forslag» fjernes. Én hovedhandling avslutter steget: **Bekreft mapping og fortsett**. En ignorert kolonne merkes tydelig som utelatt.

| Tvetydig kolonne | Valg og forklaring |
| --- | --- |
| «Mobil / kontor» | «Aktørtelefon», «Persontelefon» eller «Velg for hver oppføring». Sistnevnte forklares: «Du velger senere om nummeret tilhører aktøren eller kontaktpersonen.» Nummerets utseende bestemmer aldri eier automatisk. |
| «Region» med både byer og større områder | Bruk som sted/område, kontroller hver ulik verdi senere, eller ignorer kolonnen. Hjelp: «Like verdier samles og avklares senere i stedsreview.» |
| Flere personnavn i én celle | Et eventuelt forslag til oppdeling vises som forslag med koblingen tilbake til den opprinnelige cellen. Uklar oppdeling avgjøres i review. |

«Distrikt» erstattes med «Region» i produktets begreper og demonstrasjonsdata. Hvis en faktisk kildefil heter «Distrikt», vises dette fortsatt som originalt kolonnenavn. Råverdier omskrives ikke for å få skjermen til å samsvare med den nye ordbruken.

Mapping bestemmer tolkning, ikke publisering eller endelig profilidentitet. Nasjonale telefonnumre krever eksplisitt land. Innhold som ikke lar seg tolke entydig, bevares til review eller utelates ved et uttrykkelig valg.

### 4.3 Google Sheets

Førstesiden bruker teksten «Les data direkte fra et valgt Google-regneark» og én primærknapp: **Koble til Google Sheets**. Etter tilkobling vises valgt konto, regneark og faner. Brukeren velger hvilket innhold som inngår, og ser antall og relevante advarsler før data hentes.

Kildegrunnlaget blir en kopi til denne importjobben. Endringer i originalarket synkroniseres ikke inn, og importen skriver ikke tilbake til Sheets. Ny innhenting må være uttrykkelig. Tilkoblingsfeil og manglende tilgang forklares konkret uten at brukeren mister jobbnavn og øvrige utkastvalg.

En gjenkjent standardpakke går til pakkekontroll. Andre oppsett går til mapping. Knappen beskriver den faktiske fortsettelsen. Google Sheets er prioritert etter CSV/XLSX-kjernen og før CRM v1 lukkes; prototypens tilkobling er simulert, og adapteren er ikke implementert på verifisert `main`.

## 5. Jobbregler: omfang og direkte utkastvalg

### 5.1 Fire tydelige omfang

Seksjonen **Hvem skal reglene gjelde** beholdes. **Hele importjobben er standard.** Datatypevisning og regelomfang er forskjellige valg. Å åpne en regelgruppe endrer ikke hvilket utvalg de aktive feltvalgene gjelder.

| Omfang | Eksakt betydning | Synlig informasjon |
| --- | --- | --- |
| Hele importjobben | Alle kandidatene i jobben; hver regel treffer bare datatypene den er relevant for. | Totalantall og antall aktører, personer, koblinger og steder. |
| Aktuell datatype | Alle kandidater av den uttrykkelig valgte datatypen. | Navn på datatype og antall. |
| Filtrerte kandidater | Aktør- eller personprofiler som passer et av de tre feltbaserte filtrene nedenfor når utvalget velges. | Uttrykkelig datatype, presis filterforklaring, treffantall og identifiserbare kandidater. |
| Manuelt utvalg | Kandidatene brukeren har krysset av i utvalgslisten. | Antall, identifiserbart utvalg og datatyper. |

Utvalget står fast mens feltvalgene redigeres. En telefonretting skal eksempelvis ikke i det skjulte gjøre utvalget mindre for neste kategorivalg. Først når brukeren endrer omfang, datatype, filter eller manuelt utvalg, beregnes et nytt sett kandidater og antallet oppdateres. Tidligere lagrede regler får ikke en ny målgruppe bare fordi brukeren bytter visning. Ved et tomt filtrert utvalg kan feltvalg fortsatt gjøres og vises i utkastet, men effekten skal uttrykkelig være null; ingen kandidatendring skal presenteres som utført.

**Filtre før analyse.** Alle innleste rader er nye i importjobben, men de kan gjelde både nye og eksisterende CRM-profiler. Matching er ikke avklart på dette steget. Derfor bygger filtrene bare på importerte/mappede felt og uttrykkelige utkastvalg som allerede finnes; prototypens forhåndsbestemte eksempelidentiteter er ikke et gyldig filtergrunnlag.

| Filter | Nøyaktig utvalg før analyse |
| --- | --- |
| Mangler hovedkategori | Hovedkategorifeltet er tomt. En bevart, ukjent kildeverdi er ikke tom og regnes ikke som manglende. |
| Mangler relevant underkategori | En etablert hovedkategori med etablerte underkategorier er valgt, men underkategorifeltet er tomt. Kreativ teknologi og Litteratur har ingen etablerte underkategorier og treffes derfor ikke. En bevart, ugyldig underkategori er ikke tom og slettes ikke av filteret. |
| Telefon uten avklart land | Telefonnummeret er ikke tomt, starter ikke med `+`, og et land er ikke uttrykkelig valgt for nummeret i jobben/utkastet. Tomt nummer treffes ikke; et internasjonalt nummer beholder oppgitt landskode. |

Datatypevelgeren for dette omfanget tilbyr **Aktører** eller **Personer**. Koblinger og selvstendige stedskandidater kan fortsatt velges gjennom **Én datatype** eller **Manuelt utvalg**. I filtrert utvalg er **Stedsavklaring** tilgjengelig for stedsopplysningene til de valgte profilene; den krever ikke at en selvstendig stedskandidat inngår i utvalget. Filterforklaring og treff vises før feltvalgene. Null treff betyr et synlig tomt utvalg; alle fire grupper er fortsatt tilgjengelige, effekten vises som null, og systemet faller ikke tilbake til alle kandidater. Det faste utvalget under redigering betyr at en valgt retting først slår ut i trefflisten ved et nytt filter-/omfangsvalg.

«Nye oppføringer», «Ikke gjennomgått» og det generelle etteranalysefilteret «Trenger et valg» brukes ikke som jobbfiltre. **Ikke gjennomgått** beholdes i gjennomgangskøen der statusen er relevant. Et tomt kategorifelt kan være nyttig for å velge et utvalg, men filtrene innfører ingen nye obligatoriske kategorier eller underkategorier.

Musikkontoret er et separat, jobbfelles mål fra første side. De fire omfangsvalgene endrer ikke dette målet.

### 5.2 Fire synlige regelgrupper

Alle regelgruppene har egne, synlige seksjoner: **Kategorier og tags**, **Telefon**, **Berikelsesnivå** og **Stedsavklaring**. De starter sammenfoldet, og flere kan være åpne samtidig. Overskriften viser de aktive verdiene etter at seksjonen lukkes. I **Filtrerte kandidater** er alle fire seksjoner aktive og feltene tilgjengelige for hvert av de tre filtrene, også når utvalget eller den relevante effekten er tom. Valgte verdier vises fortsatt i den sammenfoldede regelgruppen, sammen med korrekt null effekt. Kontroll før analyse viser faktisk anvendte regler og det valgte omfanget; utkastvalg uten effekt framstilles ikke som anvendte regler. Vanlige feltavhengigheter gjelder fortsatt: underkategori velges innen en etablert hovedkategori. I de øvrige omfangene viser en gruppe uten relevante kandidater «Gjelder ikke valgt datatype» og inaktive felt.

Brukerens aktive feltvalg lagres direkte i jobbutkastet: rullegardin-, radio- og tekstfelt oppdaterer det aktuelle valget ved endring. Det finnes ingen «Ta med i jobbreglene»-avkryssing, gruppeaktivering eller separat «Bruk valgte jobbregler»-handling. Å åpne eller lukke en seksjon endrer ingen data. En feltendring viser sin konkrete verdi og lagringsstatus og oppdaterer den korte kontrollen før analyse. Dette er lagring av importvalg; CRM-profiler oppdateres fortsatt først ved fullføring.

Redigering av samme felt for det samme utvalget erstatter det forrige utkastvalget. Hvis en tag endres fra «Jazz» til «Rock», legges ikke begge til fordi brukeren skrev i feltet flere ganger. «Ingen endring» eller tømming av et ekstra feltvalg trekker tilbake dette utkastvalget for det samme utvalget; det sletter ikke importerte eller eksisterende profilverdier. Tidligere valg for andre utvalg beholdes. Dette gjør direkte lagring forutsigbar uten en synlig regelhistorikk.

| Regel i Jobbregler | Aktør | Person | Kobling | Stedskandidat |
| --- | --- | --- | --- | --- |
| Kategori og underkategori | Relevant | Relevant | Ikke relevant | Ikke relevant |
| Redaksjonelle og interne tags | Relevant | Relevant | Ikke relevant | Ikke relevant |
| Land for nasjonale telefonnumre | Aktørtelefon | Persontelefon | Endrer ikke kontaktverdier | Ikke relevant |
| Berikelsesnivå | Profilopplysninger | Profil-/kontaktopplysninger | Ingen egen profilberikelse | Kontrollert stedsløp er separat |
| Samlet behandling av like stedsverdier | I filtrert utvalg: stedsopplysningene til valgte aktører. Ellers oppsummering av berørte aktører. | I filtrert utvalg: stedsopplysningene til valgte personer. Ellers oppsummering av berørte personer. | Ingen automatisk koblingsendring | Relevant i omfang som inneholder stedskandidater; endres ikke av filtrert profilutvalg. |

Ved **Filtrerte kandidater** gjelder stedsregelen bare profilene i det faste utvalget som har en stedsopplysning. Like stedsverdier telles én gang i oppsummeringen, mens antallet berørte profiler beholdes separat. Valget endrer verken en felles stedskandidat eller andre profiler som bruker samme verdi. En profil uten stedsopplysning får ingen konstruert verdi; seksjonen er fortsatt tilgjengelig og viser null stedseffekt. Dette presiserer omfanget av O-24 og innfører ingen automatisk stedsoppretting eller avklaring.

Kategori, underkategori og redaksjonelle tags beskriver den felles profilen. Interne tags tilhører eget musikkontors private arbeidsdata. Offentlig synlighet avgjøres i review. Kontroller for rolle/status, musikkontortilknytning og valgfritt bildesøk finnes ikke i massereglene. Kontakt- og relasjonsverdier endres ikke som skjult følge av et datatypevalg. Dette viderefører grensene i [ADR-011 §§5–7 og 12][ADR11].

Kategoriseksjonen har separate felt for hovedkategori, underkategori, redaksjonelle tags og interne tags. Fargede chips viser verdiene mens de legges inn, ved feltene og i den sammenfoldede overskriften. Farger og tekstfarger følger §12.1. Kategorier/tags skiller mellom **Legg til**, **Erstatt** og **Fjern**; tomme importceller er fortsatt bevaring, ikke fjerning.

### 5.3 Én kompakt Kontroll før analyse

**Kontroll før analyse** er den samlede oppsummeringen. Den viser målkontor, valgt omfang og faktisk anvendte kategori-/tag-, telefon-, berikelses- og stedsregler med presise antall per relevant datatype. Ved filtrert utvalg viser anvendt stedsbehandling antall berørte profiler og antall ulike stedsverdier blant disse. Utkastvalg uten effekt framgår av den aktuelle regelgruppen med nullinformasjon; kontrollen viser ingen virkningsløs regel som anvendt. Automatisk søk etter manglende bildekandidater framgår uten en avkryssing. Det separate panelet «Dette blir effekten av jobbreglene» og regelhistorikk fjernes.

Eksempel: «Musikkontoret Nord gjelder hele jobben. Kategorier og tags gjelder 4 aktører og 1 person. Stedsavklaring gjelder 2 stedsverdier.» Dette er forskjellige virkninger og skal ikke samles i det tvetydige «5 valgt». Brukeren kan gå direkte til **Start analyse** når de nødvendige valgene er gyldige; det finnes ikke et ekstra anvendelses- eller bekreftelsestrinn.

Stedsbehandling og geografi oppretter ikke tilknytning til musikkontor. Den planlagte tilknytningen kommer fra det uttrykkelige, jobbfelles valget på første side og vises i sluttkontrollen.

### 5.4 Etablerte kategori- og underkategorivalg

Alle seks etablerte hovedkategorier skal finnes i rullegardinene i Jobbregler og individuell review der feltet er relevant. Underkategori er også en rullegardin og viser de etablerte valgene for valgt hovedkategori. Det opprettes ingen nye taksonomiverdier gjennom prototypen.

| Hovedkategori | Etablerte underkategorier fra `main` |
| --- | --- |
| Musikk | Artister & Band; Konsertarrangører; Musikere; Musikkbransjen |
| Film | Produsent; Regi & Manus; Foto/ Lys; Filmlyd; Filmproduksjon |
| Kunst & Design | Visuell kunst; Grafisk design; Klesdesign |
| Scenekunst | Teater; Dans |
| Kreativ teknologi | Ingen etablerte underkategorier i kildegrunnlaget. |
| Litteratur | Ingen etablerte underkategorier i kildegrunnlaget. |

Listen har **6 hovedkategorier og 14 underkategorier**, fra [aktiv Editor-taksonomi][TAXONOMY], avstemt mot [seed-migrasjon][TAXSEED] og [endringene i migrasjon 0015][TAX15] og [0016][TAX16]. Den er ikke et nytt uttrekk fra kjørende database. Begge brukerflatene skal bruke samme liste og samme hoved-/underkategorikobling. «Festival» kan være redaksjonell tag, men er ikke en etablert underkategori; «Produsent» tilhører Film.

Eksisterende, importerte eller historiske verdier utenfor listen bevares som merket kilde-/reviewinformasjon. De blir ikke stille slettet eller gjort til nye rullegardinvalg. Hvis et hovedkategoribytte gjør en tidligere underkategori uforenlig, vises behovet for avklaring og den gamle verdien beholdes i grunnlaget. Brukeren må avklare eller uttrykkelig fjerne den uforenlige underkategorien i review før godkjenning. Kategorier uten underkategorier får en forståelig tomtilstand. Databasens katalog-ID-er eller nye migrasjonsregler bestemmes ikke av demoen.

## 6. Berikelse og aktørbilder

### 6.1 Tre nivåer med konsekvent forklaring

Samme navn og forklaring brukes ved jobbopprettelse, i Jobbregler og i analyseoversikten. Foreløpig valg forklares med: «Du kan endre dette i Jobbregler før du starter analysen.»

| Nivå | Hva arbeidet omfatter | Arbeidsmengde som kommuniseres |
| --- | --- | --- |
| Ingen ekstern berikelse | Ingen ekstra eksterne søk etter profil- og kontaktopplysninger. Disse hentes fra importfilen og eksisterende CRM-data. | Færrest slike profilsøk. Bildeløpet finner fortsatt kandidater automatisk når et godt bilde mangler. |
| Målrettet ekstern berikelse | Manglende nødvendige opplysninger og identitetskontekst som må avklares for de valgte kandidatene. | Avgrensede søk etter konkrete mangler; større jobber kan ta lengre tid. |
| Utvidet beriket søk | Målrettet arbeid supplert med flere tomme, relevante og ikke-kritiske felt, eksempelvis sosiale profiler, kildebelagt beskrivelse og musikklenker. | Flere søk og forventet mer behandlingstid enn målrettet nivå. |

«Nødvendige opplysninger» betyr nødvendig for den konkrete avklaringen. Det innfører ikke en ny liste over universelt obligatoriske profilfelter. Eksakte providerfelt, søkegrenser, tak og innstillinger spesifiseres i 5E. V6 lover ikke bestemte minutter, priser eller antall treff.

Brukeren skal forstå hvilket profilsøk som er valgt, og at bildekandidater finnes automatisk ved behov. Resultater viser de faktiske nettsidene eller registrene som støtter forslaget. En modell som strukturerer informasjon, presenteres ikke som faktakilden. Private notater og interne tags brukes ikke som skjult søkekontekst. Et senere profilsøk fra review viser hvilket utvalg og hvilke mangler som skal behandles før det starter.

### 6.2 Automatisk søk etter manglende bildekandidater

Bildeløpet gjelder uavhengig av de tre profilberikelsesnivåene. **Når en aktør mangler et godt/godkjent bilde, finner importen automatisk flere bildekandidater.** Brukeren trenger ikke velge et tillegg eller slå på en egen avkryssing. Dette er eierbeslutning O-13, som erstatter den tidligere valgfrie boksen «Finn flere bildekandidater».

Løpet bruker tilgjengelig, tillatt bildegrunnlag, blant annet offisiell nettside/Open Graph, og går videre til kandidatfunn ved behov. Resultatet vises til bildereview. Hvordan godkjente bildestatuser, providergrenser og kilderekkefølge konkret realiseres, avklares i 5E. Derfor brukes verken «Ingen eksterne kall» eller et uavgrenset «Bruker bare importfilen» om hele jobben.

Automatikken gjelder **forslagshenting**, ikke bildegodkjenning. Et manglende eller uegnet bilde stopper ikke en ellers gyldig kandidat. Manglende nyttige treff vises som behov for eventuelt manuelt bildevalg, ikke som en skjult godkjenning av et tilfeldig treff.

Et eksisterende gyldig, låst og godkjent bilde beholdes hvis brukeren ikke velger uttrykkelig erstatting. Automatisk kandidatsøk, ny forhåndsvisning eller ny musikkontortilknytning erstatter ikke bildet. Brukeren velger bilde, foto/logo, utsnitt og eventuell kreditering gjennom den etablerte bildearbeidsflyten. Alttekst er valgfritt. Kvadratisk forhåndsvisning viser forventet aktørkortbilde.

Bildebehandling og bildegodkjenning kan forberede privat bildegrunnlag før profilen lagres. Endelig import kobler bare et ferdig godkjent valg. Den utfører ingen nye søk, nedlastinger eller bildebehandling. Endret låst bilde etter review krever ny kontroll. Disse grensene viderefører [importens bildekontrakt][IMPORT].

## 7. Analyse og dashboard

Analysen viser forståelige delsteg: fil og struktur, normalisering og telefon, sammenligning med eksisterende oppføringer, valgt berikelse, aktørbilder og klargjøring av review. «Matching mot CRM» forklares som «Sammenligner med eksisterende aktører og personer». Intern arkitektur- og providerforklaring legges i dokumentasjon eller relevant hjelp.

Fremdrift skal avledes fra faktisk status. Hvis et pålitelig tidsestimat ikke finnes, vises «Behandler» og antall som er ferdige. Andeler og kvalitetspoeng uten definert grunnlag vises ikke. Systemet skiller mellom kilderader, konsoliderte kandidater, reviewbeslutninger og planlagte handlinger.

Dashboardet viser neste relevante handling, gjenstående valg, mulige dubletter, uavklarte steder og blokkeringer. En kontrollert kandidat regnes ikke som ferdig lagret i CRM før fullføring. Kilder som feiler, vises som manglende søk eller forslag; et berikelsesproblem skal ikke skjules som «Ingen opplysninger finnes».

Fire kompakte statuskort følger v5s rekkefølge og toppkanter:

| Statuskort | Toppkant | Betydning |
| --- | --- | --- |
| Klare | Grønn | Kandidater uten gjenstående nødvendige valg, inkludert allerede gjennomgåtte kandidater. Betyr ikke automatisk godkjent eller lagret. |
| Trenger valg | Oransje | Kandidater med et valg brukeren kan løse i review, eksempelvis mulig dublett eller tvetydig sted. |
| Blokkert | Rød | En reell validerings- eller relasjonsavhengighet må løses før kandidaten kan behandles. Vanlige reviewvalg telles ikke en gang til her. |
| Hoppet over | Grå | Kandidater brukeren uttrykkelig har utelatt fra den aktuelle fullføringen. |

Kategoriene er gjensidig utelukkende, og antall avledes fra jobbens tilstand. En utelatt kandidat telles som Hoppet over; blant de øvrige skilles reell blokkering, gjenstående reviewvalg og Klare. Antall gjennomgåtte vises separat. Etter analyse i utgangsdemoen er fordelingen **5 klare, 3 trenger valg, 0 blokkert og 0 hoppet over**. Det opprettes ikke en kunstig blokkering for å få et rødt tall.

Nederst gjeninnføres **Behandlingsfremdrift** og **Nylige jobber** i v5s oppsett. Behandlingsfremdrift viser filkontroll, telefon/normalisering, matching, bilder og valgt profilberikelse med status og reelle antall for den aktuelle jobben. Nylige jobber viser jobbenes navn/status og gir tilgang til å fortsette eller åpne et resultat. I prototypen brukes bare den aktive lokale demojobben og faktisk bevart demohistorikk; gamle v5-jobbnavn og tall gjenbrukes ikke som om de var kjørte jobber. Statusen gir ikke inntrykk av at eksterne søk faktisk er utført i demoen.

Den faste lagringsforklaringen er: **«Analysen oppdaterer ikke aktør- eller personprofilene. Importjobben og valgene dine lagres underveis.»**

## 8. Felles review

### 8.1 Arbeidsflate og handlinger

Review vises på en full desktopside med tre kolonner: kø til venstre, konsolidert kandidat i midten og **Matcher og kilder** til høyre. Høyrepanelet er synlig. Aktørbildet er fremtredende og kvadratisk. Seksjoner starter lukket, men overskriftene viser innhold, status og eventuelt antall valg som gjenstår. Offentlig synlighet følger samme regel; ingen tekst sier at den starter åpen.

**Arbeidsflaten holdes innenfor skjermrammen.** Flere kandidater gir en lengre intern køliste, ikke en høyere eller bredere side. Én kølinje representerer én konsolidert aktør, person, kobling eller stedsverdi; flere feltproblemer på samme kandidat gir ikke flere kølinjer.

| Område | Plass og rulling |
| --- | --- |
| Gjennomgangskø til venstre | Avgrenset bredde og tilgjengelig skjermhøyde. Overskrift, søk, filter og avsluttende hovedhandling står i ro; bare kandidatlisten ruller. Lange navn avgrenses visuelt, med fullt navn tilgjengelig. |
| Aktiv kandidat i midten | Én kandidat om gangen, med egen rulling for innholdet og tilgjengelige hovedhandlinger. Felt og seksjoner utvider ikke hele siden. |
| Matcher og kilder til høyre | Synlig kildekontekst med egen rulling når innholdet er langt. |

Tilgjengelig høyde beregnes etter appens øvrige navigasjon. Review skal ikke ha en arvet minstehøyde på 650 px som sprenger en vanlig laptopskjerm, eller en tvungen innholdsbredde på 820 px som skyver resten av arbeidsflaten ut. Desktop er fortsatt målflaten; dette innfører ikke full mobilimport. Teknisk virtualisering, sidevisning og ytelsesgrenser ved store jobber avklares i 5E. Prototypens layoutkrav er ikke en måling av produksjonskapasitet.

**Køkontekst og navigasjon.** Brukeren kan søke og filtrere køen, gå til forrige/neste kandidat, markere uavklart, hoppe over eller godkjenne. Filtrene omfatter **Alle**, **Trenger valg**, **Ikke gjennomgått** og **Gjennomgått**; søket avgrenser det samme utvalget. Søk, filter og køens rulleposisjon bevares ved kandidatvalg, feltendring, godkjenning og tilbakekomst. Aktiv kandidat holdes synlig med nødvendig lokal rulling; et vanlig feltvalg skal ikke nullstille fokus eller hoppe til toppen av arbeidsflaten.

Forrige/neste-knappene og **Option/Alt + piler** bruker samme filtrerte og søkte rekkefølge og stopper ved dens grenser. **Godkjenn og neste** lagrer reviewbeslutningen, ikke profilendringen. Dersom godkjenningen gjør at kandidaten forsvinner fra filteret, fortsetter køen til riktig gjenværende kandidat i rekkefølgen, uten å hoppe over naboen. Finnes ingen gjenværende kandidat, vises en tydelig tom kø og relevante valg for å endre utvalg eller gå til sluttkontroll. Det finnes ingen skjult reservekandidat utenfor filteret, og en piltast starter aldri sluttkontroll.

Når et feltvalg løser det siste problemet og kandidaten dermed faller ut av «Trenger valg» eller søket, **blir kandidaten stående åpen** med en forklaring. Brukeren kan godkjenne eller gå videre uttrykkelig. Den opprinnelige filtrerte rekkefølgen beholdes som utgangspunkt for neste gjenværende nabo; feltredigeringen godkjenner ingen kandidat automatisk. Begge veiene for å utelate en kandidat følger samme kølogikk. Åpne seksjoner gjenopprettes før lagret rulleposisjon, slik at retur til kandidaten viser riktig del av innholdet.

**Gul handling ved alle nødvendige valg.** Hvert valg i gjennomgangens gule toppvarsel har en gul, klikkbar knapp på seksjonen der valget løses. Den sammenfoldede seksjonen skal derfor vise hvor brukeren må gå, også når flere seksjoner er lukket. Flere problemer i samme seksjon samles i én knapp med antall ved behov. Knappen åpner og fører fokus til avklaringen; den godkjenner eller bekrefter ingen verdi.

| Nødvendig valg i gjennomgangen | Seksjon som skal markeres |
| --- | --- |
| Uavklart eksisterende aktør/match | Identitet og matching. Gul **Kontroller treff** beholdes også som inngang til vanlig kontroll av et eksisterende treff. |
| Motstridende nettsideverdier | Velg riktig nettside. |
| Personens telefoneier eller land, eksempelvis Saga Lund | Kontaktopplysninger. Flere telefonspørsmål gir én markering med riktig antall. |
| Aktørtelefon uten avklart land | Kjerneopplysninger. |
| Ugyldig hoved-/underkategorivalg | Kategorier og tags på den aktuelle profilen. Tomme, valgfrie felt blir ikke nye krav. |
| Uavklart sted, eksempelvis Nordlys Verksteds «Vik» | Sted på aktøren og den relevante valgseksjonen ved stedsreview. **Bekreft** åpner valget. |
| Kobling som venter på avklaring av målaktør | Den relevante aktørkoblingsseksjonen, med uttrykkelig handling til målaktøren. |

Antall, toppvarsel, gul seksjonsknapp og navigasjon ved mislykket godkjenning skal avledes fra samme strukturerte oversikt over nødvendige valg: problemidentitet, tekst, seksjon og eventuell annen målkandidat. Et forsøk på å godkjenne med gjenstående valg åpner **første reelle problemseksjon**, ikke bare første seksjon på siden. Markeringen oppdateres når problemet er løst. Frivillig bildevalg og jobbfelles musikkontor får ingen nye bekreftelseskrav gjennom denne regelen; mapping og et frivillig nytt-sted-utkast gjøres heller ikke om til nye påkrevde reviewvalg.

Hvis løsningen ligger på en annen kandidat, er hoppet et **uttrykkelig sidesteg**. Brukeren ser hvem som må avklares og en tydelig retur til kandidaten som hen kom fra. Et slikt hopp kan åpne målaktøren utenfor det aktuelle søket, men bevarer opprinnelig filter, søk og rullekontekst. Det utvider ikke den ordinære neste-/forrige-køen.

Et hopp over bevarer rågrunnlag og begrunnelse i jobben. «Uavklart» skiller en utsatt beslutning fra en kandidat som er bevisst utelatt. Godkjenning krever at handlingene er innbyrdes konsistente; en ny personkobling kan eksempelvis ikke ferdigstilles med en uavklart målaktør.

### 8.2 Identitet, mulige dubletter og feltkonflikter

Seksjonen heter **Identitet og matching**. For aktører vises tre tydelige alternativer: **Bruk eksisterende aktør**, **Opprett ny aktør** og **Hopp over**. Den korte forklaringen under hvert valg viser konsekvensen. Brukeren ser hvorfor en eksisterende oppføring foreslås og kan velge ny dersom treffet gjelder en annen virksomhet. **Kontroller treff** vises som en gul knapp som åpner seksjonen; åpning godkjenner ikke treffet. Tilknytningsplanen fra det valgte jobbmålet vises separat fra identitetsvalget og gjennomføres først ved fullføring.

Et relevant forslag fra **Brønnøysundregistrene** vises i seksjonen med identitetsopplysninger og handlingen **Bruk BRREG-data**. Handlingen viser hvilke felt som foreslås; den slår ikke sammen oppføringer og overstyrer ikke en feltkonflikt skjult. I prototypen er registerforslaget fiktivt og tydelig merket som eksempel.

Høyrepanelet inneholder **Mulig CRM-match**, forståelige støttesignaler, **Åpne eksisterende CRM-kort**, **Kilder** og **Kildepolicy**. CRM-kortet åpner den foreslåtte eksisterende oppføringen med lesekontekst og mulighet til å gå tilbake. Kilder viser importfil/rad, registertreff og konkrete nettsider som støtter forslaget. Et søkeverktøy eller en modell må skilles fra selve faktakilden.

Kildepolicy beholdes som en kort, betryggende forklaring. Den skal gjøre det tydelig at flere kilder kan støtte eller avkrefte et treff, at virksomhetens offisielle nettside normalt er en viktig kilde til egne opplysninger, og at AI-tolkning er forslag som bygger på kildene. UX-08 fjerner intern arkitekturforklaring, ikke denne nyttige kildepolicyen.

Ved motstridende ikke-tomme verdier vises eksisterende verdi, importert/forslått verdi og kilde. Brukeren velger hva som skal beholdes. Tomme celler sletter ikke eksisterende data. Identiske opplysninger krever ikke meningsløs dobbeltbekreftelse.

Dubletthjelpen er: **«Systemet slår aldri sammen automatisk. Velg oppføringen importen skal bruke, og avgjør forskjellene.»** Valg av importmål er ikke en sammenslåing av to CRM-oppføringer. Eventuell framtidig sammenslåingsforvaltning ligger utenfor denne importreisen.

Telefon, navn, sted og domene kan være støttesignaler. Telefon alene er aldri personidentitet. Kildepanelet viser konkrete holdepunkter og usikkerhet; en rangering må ikke presenteres som sikker sannhet. I prototypen er kildene uttrykkelig illustrasjoner.

### 8.3 Kontakt og person–aktør-kobling

Personen har én samlet kontaktseksjon med flere e-poster og telefonnumre og et eget primærvalg per kontakttype. Primær betyr foretrukket intern kontakt. Det betyr ikke offentlig. Nye kontaktverdier er interne som standard.

Identiske normaliserte kontakter gjenbrukes. Nye kontakter kan legges til. Erstatting, fjerning og bytte av primærkontakt er uttrykkelige beslutninger. Rå telefonverdi beholdes, og land vises for nasjonale numre. «Ingen standardland» er et reelt valg; Norge gjettes ikke skjult. Internasjonale numre bruker sin oppgitte landskode. Ugyldig eller landavhengig telefon må avklares eller utelates uten å overskrive en eksisterende gyldig verdi. Se [telefonkontrakten][IMPORT].

Rolle og tittel hos en aktør hører til koblingen. De endres ikke globalt på personen når én relasjon redigeres. **Rolle og status aktiv/sluttet avgjøres manuelt, rad for rad, i koblingsreview. Disse feltene er ikke tilgjengelige i Jobbregler eller andre massevalg.** Hver aktørkobling har egne valg for om personen og hvilke kontaktkanaler som vises offentlig. Kontaktverdiene dupliseres ikke på relasjonen.

Offentlig kontakt krever publisert aktør, aktiv kobling, uttrykkelig personvisning og uttrykkelig valgt kontaktkanal på samme kobling. Eksisterende publiseringsvalg bevares når input mangler; ny kontakt publiseres ikke ved primærvalg eller AI-forslag. Valget omtales som offentlig visning, ikke som dokumentert juridisk samtykke. Dette er målkontrakten i [ADR-005][ADR5], presisert av [ADR-011][ADR11]; dagens mellommodell er ikke tilstrekkelig bevis på ferdig implementering.

| Publiseringsverdi i kildegrunnlaget | Betydning i review |
| --- | --- |
| Mangler eller er blank | Bevar eksisterende valg; ny kontakt forblir intern. |
| Uttrykkelig ja | Legg fram et publiseringsforslag for den konkrete koblingen og kontakten. |
| Uttrykkelig nei | Legg fram et avpubliseringsforslag; dette er forskjellig fra blank input. |

Begge uttrykkelige endringer inngår i offentlig sluttkontroll. AI kan ikke foreslå eller aktivere disse valgene.

### 8.4 Stedsreview

Like rå stedsverdier kan behandles samlet. Oversikten viser geografisk kontekst. Den lange listen **«Oppføringer som bruker verdien» fjernes** fra stedssiden. Koblingen til kilde og berørte kandidater bevares internt i jobben og rapportgrunnlaget. Samme tekst i ulike land eller områder skal ikke ukritisk få samme sted. Enkeltavvik behandles på den aktuelle kandidaten; stedsavklaringen skal ikke fylles med en liste som kan vokse til hundrevis av profiler.

Et entydig sted trenger ikke ekstra tvetydighetsreview. Når «Vik» har flere mulige treff, vises navn, land, region/fylke, kommune eller annen nødvendig kontekst og støttekilder. Brukeren velger et eksisterende sted, bekrefter en entydig kildekandidat eller åpner seksjonen **Selvbetjent nytt sted**.

Hvis en aktør har et gjenstående stedsvalg, viser dens sammenfoldede **Sted**-seksjon en gul **Bekreft**-knapp. Nordlys Verksted med tvetydig «Vik» demonstrerer dette. Knappen åpner det relevante valget uten å bekrefte et sted automatisk. Brukeren må fortsatt velge et entydig sted eller uttrykkelig utelate stedsopplysningen.

Seksjonen ligger på samme side og har feltene **Stedsnavn**, **Land**, **Region/fylke** og **Kommune**, slik v5 viste. Brukeren kan dermed definere et sted underveis uten å forlate stedsreview. Et eksisterende entydig sted gjenbrukes etter kontroll; et nytt sted opprettes gjennom en uttrykkelig handling. Resultatet skal si om stedet ble gjenbrukt eller opprettet.

Vanlig autorisert reviewer kan opprette et kontrollert sted. Kjente og relevante geografiske opplysninger, originaltekst og kilde/begrunnelse inngår; koordinater og gateadresse er ikke generelle krav. Duplikat-/likhetskontroll skal forebygge dobbeltregistrering uten obligatorisk plattformgodkjenning. Bare globale registerkonflikter eller forvaltningshandlinger krever særskilt plattformrettighet.

Opprettelse av et nytt felles sted er en **uttrykkelig handling før fullføring av importen**. Knappen og bekreftelsen forklarer at selve stedet lagres og kan gjenbrukes. Dette skal ikke skjules under «Godkjenn og neste» eller motsies av teksten om profillagring. Importjobbens aktør-/personkobling og offentlig valg kontrolleres fortsatt som egne beslutninger. Et allerede opprettet felles sted forsvinner ikke automatisk fordi resten av importen avbrytes. Se [ADR-012 §§8 og 16][ADR12].

Aktører kan ha flere steder og maksimalt ett aktivt primærsted. Et privat aktørsted blir ikke offentlig fordi aktøren publiseres. Personsteder er strukturerte og kan være norske eller utenlandske, men gir aldri personkart, koordinatkrav eller sending av personidentitet til en kartprovider. Uavklarte steder blir ikke offentlige eller grunnlag for geografiske regler.

### 8.5 Musikkontor og delte opplysninger

Ved endring av felles profil vises kort: «Endringen gjelder den felles profilen.» Private notater og interne tags merkes med eget musikkontor. Andre musikkontors private data vises ikke i review eller kildepanelet.

Geografien kan foreslå musikkontor og vise en enkel begrunnelse. Forslaget er ikke tilknytning eller tilgang og overstyrer ikke jobbmålet. Review viser musikkontoret som ble valgt på første side og hva som er planlagt for den aktuelle profilen. En eksisterende profil som ikke er tilknyttet fra før, inngår i planen om å bli lagt til dette kontoret ved fullføring.

**Det kreves ingen ekstra musikkontorbekreftelse per kandidat.** Samspill Kontor demonstrerer en planlagt tilknytning ut fra det uttrykkelige jobbmålet. Når kandidaten godkjennes og tas med i fullføringen, inngår tilknytningen i den samlede handlingsplanen. Kandidater som hoppes over får ingen tilknytning. Selve tilknytningshandlingen endrer verken felles profil, publisering eller godkjent bilde; eventuelle godkjente feltendringer vises som egne handlinger. Dette erstatter den gule Musikkontor-bekreftelsen fra O-06, jf. O-11.

Bare plattform-superadmin kan opprette en ny profil direkte i flere musikkontor. En vanlig tenant-superadmin får ikke dette valget.

Ved ny aktør med flere tilknytninger må plattform-superadmin også uttrykkelig velge hvilket musikkontor som skal håndtere de private bildefilene. Senere tilknytninger flytter aldri dette ansvaret. Historiske bilder, godkjenninger, selections, releases og ledgerstate reassosieres aldri. Vanlig import tilbyr ingen overføring av image-home; dette viderefører [ADR-011 §11][ADR11].

### 8.6 Offentlig synlighet

Aktørens seksjon viser planlagt offentlig status, offisiell e-post, separat telefonvalg, offentlige steder og aktuelle offentlige feltendringer. **Offisiell aktøre-post følger aktørens offentlige status**; v6 legger ikke til et nytt e-postflagg. Personlig e-post skal ikke lagres som aktørens offisielle adresse.

Eksisterende offentlig aktør krever også offentlig sluttkontroll når et synlig felt endres, selv om publiseringsbryteren står uendret. Person- og kontaktvalg vises i den relevante aktørkoblingen. Nye valg starter avslått, med mindre uttrykkelig kildeinput legges fram som et forslag som brukeren må vurdere.

Det finnes én felles offentlig aktørside. Offentlige valg skal ikke oppfattes som særskilte sider per musikkontor. Interne tags, notater og arbeidsstatus tas aldri med i offentlig forhåndsvisning. Stedsteksten forklarer offentlig sted uten teknisk informasjon om kartgater.

## 9. Samlet sluttkontroll og fullføring

Sluttkontrollen viser konsoliderte handlinger etter review: oppretting, oppdatering, personkoblinger, tilknytninger til musikkontor, stedskoblinger og bevisst utelatte kandidater. Den skiller mellom antall profiler, antall relasjoner og antall stedsavklaringer. Samme kandidat kan gi flere handlinger; summene må derfor navngis presist.

Hver rad kan åpnes for detaljer og tilbakeføring til relevant review. Tabellen viser hva som endres, hvem det gjelder, musikkontorkontekst når relevant, og status. Blokkerende identitetskonflikter, ugyldige relasjoner eller manglende rettigheter kan ikke godkjennes bort. Uavklarte kandidater kan uttrykkelig utelates, og avhengige handlinger må da vurderes sammen med dem.

### 9.1 Når det finnes offentlige endringer

**Kontroller offentlige endringer** viser den faktiske offentlige forskjellen. Dette omfatter publisering/avpublisering, endring av synlige felt på allerede publiserte aktører, offisiell e-post, telefon, steder, godkjent bilde og aktuelle person-/kontaktendringer.

Hele siden følger v5s kompakte oppsett med liste til venstre og korte oppsummerings-/bekreftelseskort til høyre. **En lukket oppføringsrad bruker høyst tre tekstlinjer:** navn, sted/kort kontekst og chips. Et lite bilde eller identitetsmerke står ved siden av. Den klikkbare **Se før og etter**-pilen ligger på en eksisterende linje og oppretter ikke en ekstra fjerde linje.

Til høyre i raden vises et tydelig, klikkbart endringsmerke med høyst to korte forklaringslinjer under, for eksempel «Aktør publiseres», «Offentlige opplysninger endres» eller «Aktør avpubliseres». Merket kan føre tilbake til riktig review. Det finnes ingen egen høy «Endre»-knapprad. Lange feltverdier, som fullstendige nettsideadresser, hører hjemme i detaljvisningen.

**Alle offentlige endringer ligger i den samme listen fra start.** Fast avkutting etter tre oppføringer og «Vis alle»-knappen er fjernet. Ved mange endringer ruller listen innenfor den tilgjengelige høyden; det kreves ikke et ekstra valg for å få personvisningene inn i listen. Trelinjerskravet gjelder høyden på hver sammenfoldet oppføring, ikke antall oppføringer. Sidekortene teller hele den samme konsoliderte listen og beholder naturlig innholdshøyde.

Personraden viser **personnavn, hvilken aktør personen vises hos, handlingen og den konkrete offentlige endringen**. Eksempel: «Saga Lund → Fjordfestivalen» med «Person vises hos aktøren». Navn hentes fra den aktuelle før-/etter-planen; et endret person- eller aktørnavn skal ikke bli stående som et gammelt demonstrasjonsnavn i raden. Ved fjerning vises identiteten fra før-tilstanden der den ikke lenger finnes etterpå.

«Personvisninger med endring» teller visninger av en person **hos en konkret aktør**, ikke nødvendigvis unike personer eller selvstendige offentlige personsider. Publisert aktør, aktiv kobling og uttrykkelig personvisning kreves; e-post og telefon krever i tillegg sine egne kanalvalg på koblingen. Tre aktørendringer og én slik personendring skal gi fire oppføringer i den samlede listen og samsvarende antall i sidekortene.

Den konsoliderte før/etter-forskjellen ligger fortsatt til grunn for kontrollen. Detaljene er sekundære og sammenfoldet som standard og kan åpnes over radens bredde. Kortere presentasjon endrer ikke hvilke offentlige konsekvenser som må være med, eller logikken for bekreftelse. Oppsummeringen bruker faktiske antall; den innfører ingen udokumentert datakvalitetsprosent eller personkart.

Bekreftelsen **«Jeg har kontrollert endringene som blir offentlige»** starter uten avkryssing. **Fullfør import** er utilgjengelig til den gjeldende offentlige planen er bekreftet. Hvis et offentlig valg eller en offentlig verdi endres etterpå, oppheves bekreftelsen og den oppdaterte forskjellen vises. En gammel bekreftelse gjelder ikke en ny offentlig plan.

Dette er én samlet kontroll, uten en gjentatt ekstra bekreftelse for hver allerede gjennomgåtte rad. Hvis jobben ikke har offentlige endringer, fullføres den fra samlet sluttkontroll uten en kunstig offentlig bekreftelse.

### 9.2 Lagring og endringer siden review

Fullføringen oppdaterer bare godkjente handlinger. Den er ikke et nytt søketrinn. Eksterne søk, geokoding, providerhenting og bildebehandling skal være ferdige tidligere. Ingen matching eller stedskobling oppretter skjult publisering eller musikkontortilknytning.

Hvis en profil, relasjon eller bildebeslutning er endret siden review, vises hvilken beslutning som må kontrolleres på nytt. Brukerens valg overskriver ikke nyere informasjon stille. Endrede rettigheter eller avtalegrunnlag gir en konkret melding og bevarer arbeid som det fortsatt er lov å beholde.

Ved teknisk avbrudd viser jobben siste bekreftede resultat. **Prøv igjen** gjenopptar arbeid uten å duplisere allerede lagrede profiler, relasjoner eller bildevalg. Det må være synlig hva som ble lagret og hva som feilet. Om hele jobben eller avgrensede handlingsgrupper lagres atomisk, skal avgjøres i 5E; v6 lover ikke en ubegrunnet garanti om alt-eller-ingenting for hele jobben.

## 10. Resultat og videreføring

Resultatet beskriver handlinger som faktisk ble lagret. «Importen er fullført» brukes når den planlagte fullføringen er vellykket. Hvis arbeid feilet eller krever oppfølging, står dette i hovedstatusen og i handlingslisten. Hoppet over, uavklart og teknisk feilet er forskjellige utfall.

Brukeren kan åpne rapporten, gå til behandlede profiler og fortsette gjenstående kandidater. Rapporten bevarer koblingen til kilde, reviewbeslutning og resultat. «Lagt til i flere musikkontor» eller «Lagt til i Musikkontoret Nord» erstatter «Tenanttilordninger lagt til». Antall stedsverdier avklart må ikke omtales som antall nye steder eller stedskoblinger.

Avbryt før fullføring stanser videre arbeid og beholder jobbens dokumenterte status; det er ikke en skjult sletting av filer, tidligere profiler eller eksplisitt opprettede felles steder. Eventuell permanent sletting og retensjon følger en separat, avklart lagringskontrakt. V6 lover ikke automatisk tilbakeføring av allerede fullførte CRM-endringer.

## 11. Rolleavhengige valg

Rollen alene er ikke tilgangsbevis. Aktiv bruker, relevant medlemskap, eksakt delingsdomene, gjeldende avtale og handlingsspesifikk capability må være oppfylt. Dette gjelder også plattform-superadmin der ADR-011 krever det. UI viser relevante valg og korte, konkrete begrensninger; den lange rollearkitekturen ligger i dokumentasjonen.

| Handling | Plattform-superadmin | Autorisert tenant-superadmin, gruppeadmin eller redigerer | Leser |
| --- | --- | --- | --- |
| Import og review | Med nødvendige import-/redigeringsrettigheter | Med nødvendige import-/redigeringsrettigheter i aktivt musikkontor | Ingen skriverett gjennom denne flyten |
| Redigere felles profil | Med gjeldende avtale og riktig scope | Innen en autorisert tilknytning | Nei |
| Legge eksisterende oppføring til eget musikkontor | Uttrykkelig jobbmål, godkjent kandidat og samlet fullføring med riktig scope | Samme beslutningsløp; bare eget autoriserte, aktive musikkontor | Nei |
| Opprette ny profil i flere musikkontor samtidig | Ja, uttrykkelig; aktør krever gyldig bildeansvar | Nei | Nei |
| Publisere eller endre offentlig informasjon | Separat relevant capability | Separat relevant capability | Nei |
| Redigere private bildefiler | Plattformrettighet og gyldig bildegrunnlag/scope | Bare med bilderettighet i musikkontoret som håndterer bildet | Nei |
| Velge/opprette normalt sted | Relevant create-/edit-rettighet | Relevant create-/edit-rettighet; ingen obligatorisk plattformgodkjenning | Ingen oppretting |
| Endre global stedssannhet eller overføre bildeansvar | Separat forvaltningshandling | Ikke gjennom vanlig importrettighet | Nei |

Matrisen er en målkontrakt etter [ADR-011][ADR11] og [ADR-012][ADR12], ikke en påstand om ferdig implementerte rettigheter. Eksakte capabilitynavn, API-er og eventuell rollefallback avklares i 5E. Prototypen viser en autorisert reviewer ved Musikkontoret Nord og simulerer ikke alle rollevarianter.

## 12. Visuelt språk, tekster og tilgjengelighet

### 12.1 Visuelle konstanter

| Element | Bindende retning |
| --- | --- |
| Hovedkategori | `#6B493D` med hvit tekst (`#FFFFFF`). |
| Underkategori | `#38A8EC` med hvit tekst (`#FFFFFF`). |
| Redaksjonell tag | `#4A8755` med hvit tekst (`#FFFFFF`). |
| Intern tag | `#C8FA00` med svart tekst (`#000000`). |
| Chips | Små, kompakte proporsjoner som i eksisterende CRM; verdier vises med riktig farge under innlegging og i oppsummering. |
| Review | Tre kolonner innen tilgjengelig skjermramme, intern rulling, bevart køkontekst og synlig kildepanel. |
| Aktørbilde | Kvadratisk og fremtredende; samme meningsfulle utsnitt som aktørkort. |
| Seksjoner | Sammenfoldet standard; status synlig i overskriften. Alle nødvendige reviewvalg får gul, klikkbar handling på riktig seksjon. |
| Tips | Lyspære-/tipsikon og ordet «Tips», skilt fra varsler og feil. |

Tilstand skal ikke formidles bare gjennom farge. Feil bruker konkret tekst og peker til det som må rettes. Valg, seksjoner, felt og avkryssinger skal ha forståelige navn og synlig tastaturfokus. Tab følger leseretningen. Enter/mellomrom aktiverer riktig kontroll; Escape lukker en åpnet dialog og returnerer fokus.

**Option/Alt + venstre/høyre pil** går til forrige/neste kandidat i den samme filtrerte og søkte reviewkøen som navigasjonsknappene. Snarveien virker bare i review, stopper ved køens begynnelse/slutt og overtar ikke tastene når et redigeringsfelt, en valgkontroll eller redigerbart innhold har fokus. Søk, filter og køposisjon bevares etter §8.1, også når en godkjenning endrer utvalget. En eventuell Ctrl/⌘+Enter gjelder bare godkjenning når handlingen er tillatt. Snarveier skal ikke navigere vilkårlig mellom skjermbilder eller starte fullføring. Lagringsstatus og relevante valideringsbeskjeder formidles uten å flytte fokus vilkårlig. Ved skjermbytte er overskrift og plassering forståelig også uten visuell orientering.

### 12.2 Avtalt microcopy

| Situasjon | Tekst i v6 |
| --- | --- |
| Foreløpig berikelse | «Du kan endre dette i Jobbregler før du starter analysen.» |
| Standardpakke | «Standard importpakke hopper over mapping fordi feltene allerede er koblet.» |
| Mapping av blandet telefon | «Velg for hver oppføring» / «Du velger senere om nummeret tilhører aktøren eller kontaktpersonen.» |
| Stedsmapping | «Like verdier samles og avklares senere i stedsreview.» |
| Telefon | «Land for nasjonale telefonnumre» og «Ingen standardland». |
| Felles profil | «Endringen gjelder den felles profilen.» |
| Farger | «Faste farger gjør datatypene lettere å skille.» |
| Jobbregler lagret | «Valgene er lagret i importjobben.» |
| Filtre før analyse | «Mangler hovedkategori», «Mangler relevant underkategori» og «Telefon uten avklart land», med forklaringen i §5.1. |
| Tomt filter-/køutvalg | Tydelig «Ingen kandidater passer dette valget» eller «Ingen treff», med mulighet til å endre utvalget. |
| Musikkontor-tilknytning | «Legg eksisterende profiler til Musikkontoret Nord. Dette er en egen tilknytning. Profilenes opplysninger og bilde beholdes.» |
| Identitetsseksjon | «Identitet og matching». |
| Stedsoppretting | «Selvbetjent nytt sted». |
| Bildeformat | «Kvadratisk bilde til aktørkortet.» |
| Reviewlagring | «Valget lagres i importjobben. Profilen oppdateres når du fullfører importen.» |
| Offentlig sluttkontroll | «Jeg har kontrollert endringene som blir offentlige.» |
| Endelig handling | «Fullfør import». |
| Resultattilknytning | «Lagt til i Musikkontoret Nord», eller tilsvarende for faktisk resultat. |

«Canonical», «tenantassignment», «commit», «rendition» og intern provider-/arkitekturtekst brukes i utviklingsdokumentasjonen, ikke som nødvendig brukerordforråd. Relevant kildeinformasjon, delingseffekt og faktiske begrensninger beholdes.

## 13. Sporbar innarbeiding og akseptansekriterier

Status er **innarbeidet og owner-approved i v6 revisjon 4**, med O-24 utført og kontrollert etter prosjekteiers siste gjennomgang R12. De opprinnelige testfunnene beholder ID-ene UX-01–14. R7/R8 og R10–R12 presiserer løsningen uten å endre de opprinnelige testresultatene. Nyere korreksjoner overstyrer motstridende eldre løsninger; historiske instrukser nedenfor er tydelig merket. Teknisk kontroll av aktuell fil dokumenteres med faktisk metode og resultat i §14.1.

| ID / prioritet | Funn og opprinnelse | Gjeldende løsning og prototypekriterium |
| --- | --- | --- |
| **UX-01 / P0** | Begge `issue1`: skjermknapper ble oppfattet som produktmeny. | §§3 og 8.1. Ingen skjermmeny eller testskjema; faktiske steg og reviewkø fører gjennom reisen. |
| **UX-02 / P1** | Rapport §5 og felles `recommendation`: usikkert omfang. | §5 og O-11/12/14/20/24. Fire omfang og hele jobben som standard; feltbaserte føranalysefiltre, fire tilgjengelige regelgrupper med direkte utkastvalg og kompakt Kontroll før analyse. Filtrert stedsbehandling avgrenses til valgte profilers stedsopplysninger. |
| **UX-03 / P1** | `rating3`: P01 3/5, P02 2/5; tid og foreløpig valg. | §6 og O-13. Tre konsekvente profilnivåer; automatisk bildekandidatfunn ved behov på alle nivåer. Ingen påstand om null eksterne kall. |
| **UX-04 / P2** | P01 `b2`/`b3`, P02 `b2` med hjelp; `bnotes`. | §4.2 / `mapping`: sammenfoldede vurderingsrader, enklere telefon-/stedsvalg og én mappingbekreftelse. «Bruk sikre forslag» finnes ikke. |
| **UX-05 / P2** | Begges `bnotes`: Distrikt/Region. | §4.2 / `mapping`: Region som UI-begrep; opprinnelige kolonnenavn og råverdier bevares. |
| **UX-06 / P2** | P01 `bnotes` og felles anbefaling: telefonland. | §§4.2 og 8.3: synlig land/landskode, ingen skjult Norge-default; nasjonalt nummer trenger land eller bevisst utelating. |
| **UX-07 / P2** | P01 `cnotes`: doble Sheets-knapper og lang tekst. | §4.3: én tilkoblingshandling, konto/ark/faner og riktig kontrollgren. Standardformat går til pakkekontroll, annet til mapping. |
| **UX-08 / P2** | Felles anbefaling og P01 `dnotes`: overbelastende intern informasjon. | §§7, 8, 11 og 12 / O-04. Arkitekturforedrag flyttes ut; konsekvenser, konkrete kilder og kort Kildepolicy beholdes. |
| **UX-09 / P2** | P01 `dnotes`: farger, bildeformat og resultatbegreper. | §§10 og 12 / O-10/17/19. Forståelige begreper, etablerte taksonomivalg og korrekte, kompakte oppsummeringer. |
| **UX-10 / P2** | P01 `dnotes`: vanskelig dublettregel. | §8.2 / Kysten Jazzklubb: velg måloppføring og avgjør feltforskjeller; ingen automatisk sammenslåing. |
| **UX-11 / P2** | Rapport §5: «skrives»/«lagres», presisert mot ADR. | §§3, 7–9. Jobbvalg og review lagres underveis; profiler ved fullføring; stedoppretting er separat. Jobbmålet uttrykker tilknytning uten ekstra radbekreftelse. |
| **UX-12 / P3** | P01 `anotes`: infoboks kan oppfattes som feil. | §12.1: tipsikon og tydelig type. O-15/16/21 knytter alle nødvendige reviewvalg til gul handling på riktig seksjon. |
| **UX-13 / bevaring** | Handoff, godkjent plan og ADR-011. | §§8–9 og 12 / O-22/23: tre kolonner innen skjermrammen, bilde, farger, lukkede seksjoner og komplett offentlig liste med ny bekreftelse etter relevant endring. |
| **UX-14 / artefakt** | V5/v6-gjennomgang: interaksjoner, tekst og antall. | §§5–10 og 14 / O-20–O-24: tilstanden driver utvalg, regeltilgjengelighet og effekt, problempekere, køkontekst, dashboard, offentlig plan og resultat. Ingen nye runtimefunn hevdes. |

### 13.1 Tidligere eierkorreksjoner – R7 / revisjon 2

Dette er revisjonshistorikk. Videreførte krav gjelder fortsatt, mens det uttrykkelig framgår hvilke løsningsvalg som er erstattet av R8 eller R10/R11.

| ID | Korreksjon fra første eiergjennomgang | Status i gjeldende revisjon |
| --- | --- | --- |
| **O-01** | Synlige, sammenfoldede regelgrupper og beholdt Musikkontor-tekst. | Synlige grupper videreføres. Musikkontor flyttes til første side etter O-11. Gruppemarkering/anvendelse erstattes av direkte utkastvalg etter O-12/14. |
| **O-02** | Rolle/status bare manuelt per kobling. | Videreført i §8.3; ingen massevalg. |
| **O-03** | Underkategori, fargede chips og hvit/hvit/hvit/svart tekst. | Videreført; rullegardinlisten er presisert av O-10. |
| **O-04** | Identitet og matching, BRREG og fullt kildepanel. | Videreført i §8.2; gul Kontroller treff tilføyes gjennom O-15. |
| **O-05** | Option/Alt + pil mellom reviewkandidater uten å forstyrre skriving. | Videreført i §12.1; felles kørekkefølge og bevart kontekst presiseres av O-22. |
| **O-06** | Gul ekstra Musikkontor-bekreftelse for Samspill. | **Erstattet av O-11.** Jobbmålet gjelder uten ekstra radbekreftelse. |
| **O-07** | Fjern lang profilliste fra stedsreview. | Videreført; kort omfang og intern proveniens beholdes. |
| **O-08** | Selvbetjent nytt sted på samme side. | Videreført; uttrykkelig oppretting/gjenbruk før profilfullføring. |
| **O-09** | Kompakte offentlige rader med sekundære før/etter-detaljer. | Videreført gjennom O-19s helside- og radkrav og O-23s komplette liste fra start. |

### 13.2 Korreksjoner fra revisjon 3 – R8/R9

O-10–O-19 beholdes som revisjonsspor og gjelder fortsatt der O-20–O-24 ikke uttrykkelig presiserer eller erstatter et løsningsvalg. O-19s grense på tre **oppføringer** var en tidligere prototypebeslutning; bare grensen på tre **tekstlinjer per oppføring** videreføres.

| ID | Eierbeslutning | Kontrollerbart kriterium |
| --- | --- | --- |
| **O-10** | Alle etablerte hoved-/underkategorier fra fersk `main`. | §5.4 / `rules`, `review`: 6 hovedkategorier og 14 tilhørende underkategorier; valgt hovedkategori styrer listen. Ingen oppdiktede verdier eller stille sletting av råverdier. |
| **O-11** | Ett musikkontorvalg på første side gjelder hele jobben. | §§3 og 8.5: uttrykkelig mål med synlig konsekvenstekst; målet vises i review/sluttkontroll. Ingen Musikkontor-regelgruppe eller ekstra Samspill-bekreftelse. Tilknytning utføres ved fullføring uten å endre profil/bilde som bivirkning. |
| **O-12** | Aktive feltvalg lagres direkte i utkastet. | §5.2: ingen gruppeavkryssing eller anvendelsesknapp. Lukkede seksjoner viser valgene; fire tydelige omfang beholdes. |
| **O-13** | Finn bildekandidater automatisk når et godt bilde mangler. | §6.2: automatikk ved behov på alle profilnivåer; ingen tilleggssjekkboks, automatisk godkjenning eller skjult erstatting. Fullføring starter ikke providerarbeid. |
| **O-14** | Fjern separat effektpanel og regelhistorikk. | §5.3: én kompakt Kontroll før analyse med målkontor, omfang og aktive valg; ingen ekstra bekreftelse. |
| **O-15** | Kontroller treff skal være gul. | §8.2 / `review`: knappen åpner Identitet og matching og godkjenner ikke treffet. |
| **O-16** | Gjenstående sted på Nordlys Verksted skal vises på Sted-seksjonen. | §8.4: gul Bekreft åpner valget; Vik må avklares eller uttrykkelig utelates. |
| **O-17** | Fire statuskort som i v5. | §7 / `dashboard`: Klare, Trenger valg, Blokkert, Hoppet over med grønn/oransje/rød/grå toppkant; disjunkte og tilstandsavledede antall. |
| **O-18** | Gjeninnfør Behandlingsfremdrift og Nylige jobber. | §7: kompakte bunnseksjoner med faktisk demotilstand og lokal historikk; ingen oppdiktede kjøringer. |
| **O-19** | Hele offentlige sluttkontrollen skal følge v5s kompakte utforming. | Høyst tre tekstlinjer i lukket rad, inline Se før og etter og naturlig sidekorthøyde videreføres i §9.1. Revisjon 3 viste tre oppføringer først med Vis alle N; dette er **erstattet av O-23**. Full endringsliste og korrekt offentlig bekreftelse beholdes. |

### 13.3 Gjeldende presiseringer i revisjon 4 – R10/R11

| ID | Godkjent presisering | Kontrollerbart kriterium og sporbar lukking |
| --- | --- | --- |
| **O-20** | Filtre før analyse må bygge på opplysninger som faktisk finnes på dette steget. | §5.1 / UX-02, UX-14: tre feltfiltre for aktør/person, presise tom-/ugyldig-verdi-regler, treffantall og synlig utvalg. Ingen «Nye oppføringer», reviewstatus eller seedet matching som jobbfilter. Fast utvalg under redigering og tydelig null treff. Ingen ny obligatorisk kategorisering eller retur til Jobbregler etter analyse. |
| **O-21** | Alle nødvendige valg i gjennomgangen får gul handling på riktig seksjon. | §8.1 / UX-06, UX-10, UX-12, UX-14: samme strukturerte problemoversikt driver antall, topptekst, seksjonsknapp og mislykket godkjenning. Knappen åpner/fokuserer, uten godkjenning. Telefon, nettside, taksonomi, sted og aktøravhengighet er omfattet. Flere problemer i samme seksjon samles; avhengighetshopp har synlig retur. |
| **O-22** | Stor gjennomgangskø holdes innen skjermrammen, med bevart arbeidskontekst. | §§8.1 og 12.1 / UX-13, UX-14: avgrenset købredde/-høyde, fast søk/filter og intern listerulling; én aktiv kandidat og synlige kilder. Filter, søk, rulleposisjon og fokus bevares. Knapper og Alt/Option bruker samme utvalg, håndterer godkjenning som fjerner aktiv kandidat og viser tom kø uten ufiltrert reserve. Teknisk skalering avklares i 5E. |
| **O-23** | Personvisninger skal inngå tydelig i hele den konsoliderte offentlige listen fra start. | §9.1 / UX-09, UX-13, UX-14: ingen avkutting etter tre oppføringer eller Vis alle-knapp. Tre tekstlinjer per lukket oppføring og før/etter-pil beholdes. Aktuelle person-/aktørnavn, konkret endring og samme fullstendige liste i sidekort og bekreftelse. Kanal- og publiseringsvilkår, full endringsfingerprint og ny bekreftelse ved endring beholdes. |

Lukkingen ovenfor gjelder krav og artefaktrevisjon. Prosjekteiers siste gjennomgang er gjennomført og fulgt opp med O-24 nedenfor. Faktiske kontroller for den ferdige HTML-filen føres i §14.1.

### 13.4 Sluttkorrigering og endelig godkjenning – R12

| ID | Siste eierbeslutning | Kontrollerbart kriterium og sporbar lukking |
| --- | --- | --- |
| **O-24** | Behold de tre feltfiltrene. Når et filter velges, skal Kategorier og tags, Telefon, Berikelsesnivå og Stedsavklaring være aktive og tilgjengelige. Utfør bare denne rettingen og gå direkte til én komplett dokumentasjonsprompt, uten en ny manuell prototyperunde. | §§5.1–5.3 / UX-02, UX-14: alle fire grupper kan brukes for aktører og personer under hvert filter. Valg og presise antall vises også ved null effekt. Underkategori følger valgt hovedkategori. Alle anvendte regler holder seg til det faste profilutvalget. Stedsavklaring gjelder profilutvalgets egne stedsopplysninger, uten å endre felles stedskandidat eller andre profiler. Null treff gir ingen reservegruppe eller skjult endring. Kilde- og JavaScript-kontroll dokumenteres i §14.1. |

O-24 er innarbeidet i samme **v6 revisjon 4**. R12 og den utførte korreksjonen lukker den siste betingelsen i eiers godkjenning 12. oktober 2026. Ingen revisjon 5 eller ny manuell/formell test bestilles. Dokumentene er lagret gjennom PR #73 med gjennomført review og bestilt kontrollert merge; faktisk mergestatus følger GitHub; denne godkjenningen starter ikke runtime eller Fase 5E.

## 14. Hva prototypen demonstrerer

HTML-filen er et selvstendig, lokalt demonstrasjonsartefakt. Det diskrete prototypemerket og hjelpen forklarer at data er fiktive, integrasjoner simulerte og lagring begrenset til denne demoen. Den kobler ikke til GitHub, CRM, Google, offentlige registre eller eksterne bildeleverandører.

Skjermidentifikatorene er `newimport`, `packagecheck`, `sheets`, `mapping`, `rules`, `analysis`, `dashboard`, `review`, `finalcheck`, `publiccheck` og `result`. Disse gir sporbarhet i dokumentasjonen; de presenteres ikke som en meny for brukeren.

| Kandidat | Type | Demonstrert avklaring |
| --- | --- | --- |
| Fjordfestivalen | Aktør | Oppdatering av eksisterende profil og offentlige konsekvenser. |
| Kysten Jazzklubb | Aktør | Valg mellom eksisterende oppføringer og nettsidekonflikt. |
| Nordlys Verksted | Aktør | Oppretting, gul stedsavklaring og automatisk bildekandidatfunn ved behov; bilde er valgfritt. |
| Samspill Kontor | Aktør | Eksisterende profil; planlagt tilknytning følger det uttrykkelige jobbmålet uten ekstra radbekreftelse. |
| Saga Lund | Person | Kontakt, telefoneier/land og gul handling ved nødvendige kontaktvalg. |
| Saga Lund → Fjordfestivalen | Kobling | Rolle/status og relasjonsspesifikk offentlig visning. |
| Vik | Stedsverdi | Tvetydighet, geografisk kontekst og uttrykkelig stedsvalg. |
| Bodø | Stedsverdi | Entydig avklaring uten konstruert konflikt. |

Utgangsdatasettet har **8 kandidater: 4 aktører, 1 person, 1 kobling og 2 stedsverdier**. Når alle planlagte handlinger godkjennes, illustrerer det én ny aktør, to oppdaterte aktører, én oppdatert person, én ny personkobling, én musikkontortilknytning og to avklarte stedsverdier. De seks profil-/relasjonshandlingene og to stedsavklaringene er forskjellige kategorier. Offentlige antall følger brukerens faktiske valg.

Filopplasting, Google-tilkobling, kildetreff og bildebehandling demonstrerer arbeidsflyten. Eventuell promptnedlasting i demo er merket som eksempel, og erstatter ikke «siste godkjente KI-prompt» i produktet. Demoen beviser ikke serverpersistens, faktiske providerintegrasjoner, rolleisolasjon, skalering eller migrering.

### 14.1 Artefaktkontroll og revisjonsspor

| Tidligere leveranse | Historisk kontrollresultat |
| --- | --- |
| Første v6, 11. oktober 2026 | 20 av 20 målrettede kontroller av interaksjonslogikken passerte. |
| V6 revisjon 2, 11. oktober 2026 kl. 18.10 UTC | 29 av 29 målrettede kilde- og JavaScript-kontroller passerte. |
| V6 revisjon 3, 11. oktober 2026 kl. 20.36.44 UTC | 34 av 34 målrettede kilde- og JavaScript-kontroller passerte for den daværende filen. |

Alle tre resultatene gjelder tidligere filer. Metoden var syntakskontroll, gjennomgang av HTML/CSS og isolert kjøring med et minimalt DOM-grensesnitt. Resultatene videreføres ikke som bevis på revisjon 4.

**Historisk resultat for revisjon 3:** Den 11. oktober 2026 kl. 20.36.44 UTC passerte **34 av 34 målrettede kontroller** på den daværende frosne prototypefilen. Metoden var syntakskontroll, gjennomgang av HTML/CSS-kilden og isolert JavaScript-kjøring med et minimalt DOM-grensesnitt. Kjøringen brukte `verify_prototype_v6_revision3.cjs`; kontrollresultatet bevares som historisk revisjon-3-grunnlag.

Kontrollen omfattet de tre importgrenene, lokal gjenåpning og resultatantall, hoved-/underkategorier mot fersk main, direkte feltvalg på fire omfang, stabilt filterutvalg, ett jobbfelles musikkontor, automatisk bildekandidatstatus, gule avklaringsknapper, fire dashboardstatuser og lokal jobbhistorikk. Offentlig sluttkontroll ble kontrollert for kompakt kildeutforming, full endringsliste, feltendring på allerede offentlig aktør, avpublisering, personkontaktvilkår og ny bekreftelse etter relevante endringer. Det er målrettet kontroll av disse artefaktegenskapene, ikke bevis på at all framtidig produktatferd er implementert.

Historisk kontrollert fil: `import_2_0_prototype_v6.html`, revisjon 3. **SHA-256:** `b7321dcd87b12a279f4376892ded47c773f44eb9fef15bb469c57ae8b6b62078`. Filhashen var identisk etter den kontrollen.

<!-- REV4_QA_START -->
**Historisk kontroll før eiers siste gjennomgang:** Revisjon 4 passerte 45 av 45 målrettede kontroller 12. oktober 2026 kl. 17.28.42 UTC, med `verify_prototype_v6_revision4.cjs`. Denne eiertestede versjonen hadde SHA-256 `b75267934a7faf712acbe9ee4dcc245835d2aaf77100ceae6b9777561211940a`. Resultatet er bevart som `prototype_qa_results_revision4_owner_tested.json` og gjelder filen før O-24.

**Gjeldende kontroll etter O-24: 45 av 45 målrettede kontroller bestått.** Kjøringen ble gjennomført 12. oktober 2026 kl. 18.35.25 UTC på den ferdige, frosne HTML-filen. Metoden var syntakskontroll, gjennomgang av HTML/CSS og isolert JavaScript-kjøring med et minimalt DOM-grensesnitt og syntetisk rulling. Resultatet er registrert i `prototype_qa_results.json`, med kjøring fra `verify_prototype_v6_final.cjs`. I tillegg passerte en uavhengig, målrettet kontroll av O-24 **8 av 8 kontrollgrupper uten funn**. Det siste er en separat kontroll, ikke åtte ekstra tester i 45-testkjøringen.

| Kontrollomfang | Bekreftet i kilde og isolert logikk |
| --- | --- |
| O-20 / jobbfiltre | De tre føranalysefiltrenes feltvilkår, tomt utvalg, skille mellom tom og bevart ugyldig verdi, ingen matching-/reviewstatus som filtergrunnlag og fast utvalg under feltredigering. |
| O-21 / avklaringshandlinger | Alle nødvendige problemtyper peker til riktig seksjon. Saga med to telefonvalg får én seksjonsinngang, mislykket godkjenning åpner avklaringen, og knappene godkjenner ingenting. |
| O-22 / kø og retur | Klikk, knapper og Option/Alt følger samme søk/filter. Godkjenning og begge utelatingsveier hopper ikke over neste kandidat. Siste feltavklaring beholder kandidaten til uttrykkelig handling. Avhengighet utenfor Saga-søk har synlig retur. Tom kø åpner ingen reservekandidat. |
| O-22 / rulling og antall | Simulert utskifting av DOM-innhold bevarer rulling og feltfokus. Retur åpner lagrede seksjoner før rulleposisjonen settes. En syntetisk kø med 300 kandidater rendrer én detaljflate og bruker samme rekkefølge; dette er en logikkontroll, ikke en ytelses- eller nettlesermåling. |
| O-23 / offentlig liste | Alle fire endringer vises i eksemplet med tre aktører og én personvisning. Før-/etter-navn brukes ved endring og fjerning. Fullstendig offentlig plan, kanalvilkår, bekreftelsesfingerprint og oppheving av gammel bekreftelse ved relevant endring er bevart. |
| Videreførte flyter | De tre importveiene, åtte demokandidater, lokal gjenåpning, resultatantall, taksonomi, jobbdekkende musikkontor, direkte regler, automatisk bildekandidatstatus, dashboard og lokal jobbhistorikk. |
| O-24 / separat målrettet kontroll | Alle fire regelgrupper er tilgjengelige under hvert av de tre filtrene for aktør/person, også ved null treff eller ingen stedsopplysning. Utkastvalg og null effekt vises korrekt. Regelvirkning holder seg til det faste profilutvalget; delt stedsverdi endrer ikke andre profiler eller felles stedskandidat. To valgte profiler med samme stedsverdi telles som én verdi. Tilbaketrekking av stedvalg, hoved-/underkategoriavhengighet og de øvrige omfangenes eksisterende datatypeavgrensning er bevart. |

Før revisjon 4 ble levert til eiers siste gjennomgang, fant en uavhengig kildegjennomgang fem konkrete integrasjonspunkter som ble lukket: layout for hovedhandlinger, rekkefølgen ved gjenoppretting av åpne seksjoner/rulling, felles utelatingslogikk, fokus inne i avklaringsseksjonen og lange kildenavn i smal høyrekolonne. Dette er historikken før O-24, ikke nye endringer i sluttkorrigeringen. Kontrollen dokumenterer kildekontroll, ikke observerte nettleserpiksler.

Kontrollert sluttfil: `import_2_0_prototype_v6.html`, **v6 revisjon 4**, 200 869 byte. **SHA-256:** `938a40ea725772d96a70fb660a228652070047e3d1d6b3eeebe24aa324499628`. Filhashen samsvarer med den leverte HTML-filen etter O-24. Tidligere kontrollresultater gjelder fortsatt bare sine historiske filer.
<!-- REV4_QA_END -->

**Agentens visuelle nettleserverifisering er ikke gjennomført for revisjon 4.** Den tidligere kontrollen kunne ikke åpne lokale HTML-filer på grunn av nettlesermiljøets sikkerhetspolicy. Prosjekteiers siste manuelle gjennomgang er nå gjennomført og dokumentert i R12. Den avgrensede sluttkorrigeringen O-24 er kilde- og logikkontrollert; den er ikke sendt til en ny manuell runde, i tråd med eiers uttrykkelige instruks. Kilde-/logikkontroll alene registrerer ikke faktisk layout, fokus, museklikk eller nettleserens lagrings-/nedlastingsatferd som bestått. Køkonstruksjon og syntetiske kandidater dokumenterer heller ikke produksjonsytelse ved hundrevis av oppføringer. Dette er artefaktkontroll, ikke en ny formell brukertestrunde, og erstatter ikke browser-gaten ved senere runtime-UI.

## 15. Avslutning av 5D og overlevering til 5E

Prosjekteier har gjennomført sin siste egen gjennomgang av **v6 revisjon 4**. Den eneste gjenstående korreksjonen O-24 er utført og kontrollert; den endelige UX-godkjenningen registreres 12. oktober 2026 på grunnlag av R12. Eier har uttrykkelig bestilt direkte overgang til neste leveranse uten en ny manuell prototyperunde. Dette endrer ikke deltakergrunnlaget i den avsluttede formelle brukertestrunden.

Rapporten og denne spesifikasjonen er lagret i full lengde gjennom [PR #73](https://github.com/fredrik-stack/kreative-norge-crm/pull/73) fra `docs/phase5d-ux-v6-close`, med bevart sporbarhet og synkronisert prosjektstatus, roadmap, changelog og relevante importdokumenter. Skrivebeskyttet review er gjennomført uten blokkerende funn, og prosjekteier har bestilt kontrollert dokumentasjonsmerge 2026-10-12. Eksakt siste head, mergestatus, mergecommit og PR-/main-CI følger GitHub og leveranserapporten. Runtimearbeid og Fase 5E er ikke startet.

Etter dokumentasjonsleveransen og ny kontroll av fersk `main` starter read-only Fase 5E. Den skal gjøre brukeropplevelseskontrakten beslutningsklar for implementering ved å avklare faktiske gap, små leveranser, migrering, data-/aktiveringsporter, tester, staging, rollback og ferdigkriterier. Modeller, endepunkter, providerfeltgrenser, bakgrunnsjobber og transaksjonsdetaljer fastsettes ikke av denne prototypen.

Fasesekvensen er **5D-v6 → endelig UX-approval → dokumentasjonsleveranse → read-only 5E → godkjent nødvendig grunnmur → fase 7 Import 2.0**. Handoffens 6A/6B/6C er foreløpige planområder. ADR-011s rekkefølge har kontakt-/relasjonsgrunnlag før strukturerte steder, og ADR-012 har en eksisterende rekkefølge for kart og `STEDER`. 5E skal foreslå presis harmonisering med den nyere føringen om at kart ikke forsinker kjerneimporten. V6 endrer eller omnummererer ingen ADR.

Persistent importpakke, rapporter og proveniens med backup/restore, retensjon og database–fil-konsistens er fortsatt nødvendig før aktivering. Det samme gjelder riktig SharingDomain-/assignment-/overlay-/avtale-/capabilitygrunnlag, kontakt-/relasjonsarkitektur, steder og vern av historisk bildestate. **Browser-aktiv Codex er en hard gate før senere runtime-UI implementeres.** Teknisk kontroll av dagens lokale prototype erstatter ikke denne gaten.

CSV/XLSX-kjernen leveres først. Google Sheets følger etter kjernen, men før v1 lukkes. Checkin støttes gjennom Excel-mapping i v1. Direkte Checkin-API, Mailmojo-eksport og kart skal ikke forsinke kjerneimporten. Gammel XML konverteres gjennom et separat engangsverktøy utenfor CRM. Relevante providerporter avklares ved sitt aktiveringspunkt og blir ikke en ny generell blokkering for denne UX-leveransen.

[ADR11]: https://github.com/fredrik-stack/kreative-norge-crm/blob/9a0eeef7ead30bf3ec168df26e2f27d4465c1be7/docs/decisions/ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md
[ADR12]: https://github.com/fredrik-stack/kreative-norge-crm/blob/9a0eeef7ead30bf3ec168df26e2f27d4465c1be7/docs/decisions/ADR-012-PLACE_IDENTITY_GEOGRAPHIC_CLASSIFICATION_AND_ACTOR_ONLY_MAPS.md
[ADR5]: https://github.com/fredrik-stack/kreative-norge-crm/blob/9a0eeef7ead30bf3ec168df26e2f27d4465c1be7/docs/decisions/ADR-005-CONTACT_ARCHITECTURE.md
[IMPORT]: https://github.com/fredrik-stack/kreative-norge-crm/blob/9a0eeef7ead30bf3ec168df26e2f27d4465c1be7/docs/architecture/IMPORT.md
[5A]: https://github.com/fredrik-stack/kreative-norge-crm/blob/9a0eeef7ead30bf3ec168df26e2f27d4465c1be7/docs/status/PHASE_5_SHARING_DOMAIN_IMPACT_2026-08-30.md

[TAXONOMY]: https://github.com/fredrik-stack/kreative-norge-crm/blob/9a0eeef7ead30bf3ec168df26e2f27d4465c1be7/frontend/src/editorTaxonomy.ts
[TAXSEED]: https://github.com/fredrik-stack/kreative-norge-crm/blob/9a0eeef7ead30bf3ec168df26e2f27d4465c1be7/crm/migrations/0012_seed_categories_and_subcategories.py
[TAX15]: https://github.com/fredrik-stack/kreative-norge-crm/blob/9a0eeef7ead30bf3ec168df26e2f27d4465c1be7/crm/migrations/0015_sync_public_taxonomy.py
[TAX16]: https://github.com/fredrik-stack/kreative-norge-crm/blob/9a0eeef7ead30bf3ec168df26e2f27d4465c1be7/crm/migrations/0016_update_film_taxonomy.py
