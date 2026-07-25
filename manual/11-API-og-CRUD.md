# Kapittel 11 – API og CRUD: hvordan CRM-et snakker med andre systemer

Kreative Norge CRM skal ikke være en isolert database. Frontend må kunne lese og endre data, public-løsningen skal vise godkjente aktører, og importen trenger avgrensede måter å behandle informasjon på.

Et API er avtalen som gjør denne kommunikasjonen mulig. Avtalen beskriver hva som kan spørres om, hvordan forespørselen ser ut, hvem som får tilgang, og hvordan svaret skal tolkes.

## API-et er et kontrollpunkt

API står for *Application Programming Interface*: et definert grensesnitt mellom programmer.

React kobler seg ikke direkte til PostgreSQL. Forespørselen går gjennom Django:

```text
React → HTTP-forespørsel → Django API → PostgreSQL
```

Backend kan da kontrollere:

- om brukeren er logget inn
- hvilken tenant brukeren tilhører
- hvilken rolle brukeren har
- om dataene er gyldige
- om handlingen er tillatt
- hvilke felter som kan returneres eller publiseres

API-et er derfor mer enn en transportkanal. Det beskytter dataene og håndhever produktreglene.

## Endepunkter og ressurser

Et API består av adresser som kalles **endepunkter**. CRM-et bruker blant annet tenant-avgrensede ressurser:

```text
/api/tenants/4/organizations/
/api/tenants/4/persons/
/api/tenants/4/person-contacts/
```

Adressen sier hvilken ressurs forespørselen gjelder. HTTP-metoden sier hva klienten vil gjøre.

## HTTP-metodene og CRUD

De vanligste metodene er:

- `GET`: les data
- `POST`: opprett
- `PATCH`: oppdater noen felter
- `PUT`: erstatt en hel redigerbar representasjon
- `DELETE`: slett

**CRUD** oppsummerer de fire grunnoperasjonene:

| CRUD | Betydning | Vanlig HTTP-metode |
| --- | --- | --- |
| Create | Opprette | `POST` |
| Read | Lese | `GET` |
| Update | Oppdatere | `PATCH` eller `PUT` |
| Delete | Slette | `DELETE` |

Full CRUD for organisasjoner betyr at API-et kan opprette, hente, oppdatere og slette dem – innenfor tilgangs- og konsekvensreglene.

`GET` skal normalt ikke endre data. `DELETE` må beskyttes ekstra fordi sletting kan påvirke relasjoner og historikk.

## Hva skjer når jeg klikker «Lagre»?

Når jeg oppretter en organisasjon, samler frontend data:

```json
{
  "name": "Eksempelfestivalen",
  "org_number": "123456789",
  "is_published": false
}
```

Deretter skjer dette:

1. Frontend sender `POST` til organisasjonsendepunktet.
2. Django kontrollerer innlogging, tenant og rolle.
3. En serializer validerer felter og relasjoner.
4. PostgreSQL lagrer raden i en transaksjon.
5. API-et svarer med JSON.
6. Frontend oppdaterer skjermbildet.

Hvis noe feiler, skal svaret forklare hva klienten må rette eller hva serveren ikke klarte.

## JSON og datatyper

JSON er et tekstformat med struktur:

```json
{
  "name": "Nordlysfestivalen",
  "municipalities": "Tromsø",
  "is_published": true,
  "tag_ids": [4, 7]
}
```

JSON kan inneholde tekst, tall, boolske verdier, lister, objekter og `null`. Frontend og backend må være enige om hvilken type hvert felt har.

I dagens CRM er `municipalities` én tekststreng, selv om flere kommuner kan skrives inn. Manualen skal derfor ikke late som om API-et allerede bruker en strukturert liste. En senere endring til liste eller egen relasjon vil være en kontrakts- og databaseendring.

## API-kontrakten

Kontrakten beskriver:

- feltnavn og datatyper
- obligatoriske og valgfrie felt
- om `null` er tillatt
- relasjoner og ID-er
- autentisering og tilgang
- feilkoder
- hva som er stabilt for eksterne klienter

Hvis backend sender en liste mens frontend forventer tekst, har lagene ulike kontrakter. Feilen kan ligge skjult til en bestemt rad eller brukerflyt utløser den.

Kreative Norge CRM bruker `drf-spectacular` til å generere OpenAPI-schema og Swagger-visning. OpenAPI gjør kontrakten maskinlesbar, mens Swagger gjør endepunktene lettere å lese og prøve i nettleseren.

Dette hjelper mennesker, Codex, tester og frontend med å se hva API-et faktisk lover.

## Internt og offentlig API

Det interne API-et brukes av den innloggede editoren. Det kan gi tilgang til upubliserte data, interne notater, importjobber og redigering, avhengig av rolle.

Det offentlige API-et ligger under:

```text
/api/public/actors/
```

Det skal bare returnere godkjent informasjon. Det må filtrere bort interne notater, upubliserte aktører og kontaktkanaler som ikke skal være offentlige.

Public API er ikke en kopi av den interne serializerens innhold. Det er en egen offentlig projeksjon med egne regler. Endelig kontrakt mot Musikkontoret.no er ikke ferdigstilt.

Kontaktprojeksjonen har i dag ulike regler og fallback mellom Editor, API og offentlig HTML. Målarkitekturen er besluttet, men ikke implementert. API-kapittelet må derfor skille nåværende adferd fra ønsket fremtidig kontrakt.

## Inngående og utgående dataflyt

En **inngående integrasjon** sender data til CRM-et. Eksempler kan være importfiler, registre eller påmeldingssystemer.

En **utgående integrasjon** sender data fra CRM-et, for eksempel til public-visning, nyhetsbrev eller eksportfil.

Noen koblinger er toveis. Da må begge retninger ha klare regler for matching, feil og eierskap.

## Hvem har fasiten?

Når flere systemer deler data, må hvert felt ha en autoritativ kilde – ofte kalt **source of truth**.

Et offentlig register kan være autoritativt for juridisk navn og organisasjonsnummer. CRM-et kan eie redaksjonell beskrivelse, kategorier, tags og publiseringsstatus. Et nyhetsbrevsystem kan eie den tekniske avmeldingsstatusen.

Uten denne avklaringen kan systemer overskrive hverandre:

```text
CRM-verdi: manuelt kontrollert
Ekstern verdi: nyere, men mindre presis
```

Den tryggeste løsningen er ofte å vise et forslag med kilde og la en bruker velge, ikke automatisk erstatte en manuelt godkjent verdi.

## Nåværende og planlagte integrasjoner

Repoet må være fasit for hva som finnes:

- CSV- og XLSX-import er implementert.
- OpenAI-baserte forslag finnes i importflyten når funksjonen er aktivert og konfigurert.
- Importen kan lese offentlige signaler fra en kjent nettside og bruke heuristisk fallback.
- Google Sheets, Checkin og Mailmojo finnes som reserverte kildetyper, men parserne støtter dem ikke ennå.
- En full Brønnøysund-, Brave Search-, Mailmojo-, Checkin- eller Google Maps-integrasjon er ikke dokumentert som implementert.

De planlagte eksemplene er fortsatt nyttige for å forstå integrasjonsdesign, men skal omtales som muligheter og beslutninger – ikke nåværende funksjoner.

## Den implementerte import- og AI-flyten

Importmotoren er mer enn et opplastingsendepunkt. Den har jobber og rader med status, rådata, normaliserte verdier, matching, forslag, valideringsfeil, brukerbeslutninger og commit-logg.

En forenklet flyt er:

```text
CSV eller XLSX
→ parsing
→ normalisering
→ matching mot eksisterende CRM-data
→ heuristiske og eventuelle OpenAI-baserte forslag
→ preview og brukerbeslutninger
→ kontrollert commit
→ rapport og logg
```

OpenAI-delen kan være deaktivert eller utilgjengelig. Da bruker importen heuristisk fallback. Det betyr at arbeidsflyten ikke skal være avhengig av at én ekstern modell alltid svarer.

Når en nettside allerede er kjent, kan importtjenesten hente tillatte signaler som offentlig kontaktinformasjon og sosiale lenker. Dette er noe annet enn en full søkemotorintegrasjon. Systemet skal ikke påstå at Brave Search er implementert bare fordi originalmanuset beskrev en mulig søkeflyt.

Forslagene lagres per importrad og må kunne forklares i preview. En høy selvtillit er ikke nok dersom kilden er svak eller verdien bryter CRM-reglene.

## Autoritative registre og nettsøk

Et virksomhetsregister kan brukes til å kontrollere organisasjonsnummer og foreslå juridiske grunndata. Det bør ikke automatisk overskrive CRM-ets visningsnavn, faglige kategori eller redaksjonelle tekst.

Et søke-API kan finne kandidater som nettside, sosiale profiler og omtaler. Et søkeresultat er ikke et verifisert faktum. Det kan være gammelt, tilhøre en navnelik aktør eller komme fra en svak kilde.

En trygg berikelsesflyt er:

```text
kjent CRM-kontekst
→ kandidatkilder
→ kildekontroll
→ strukturering
→ deterministisk validering
→ preview
→ menneskelig godkjenning
```

Søket bør bruke navn, kommune, organisasjonsnummer og andre kjente signaler for å redusere feil aktør.

### Eksempel på fremtidig registeroppslag

Hvis en importert rad har organisasjonsnummer, kan et fremtidig registeroppslag:

1. kontrollere at nummeret finnes
2. hente juridisk navn og registrert adresse
3. sammenligne med importert verdi
4. vise avvik i preview
5. la brukeren beholde CRM-visningsnavnet
6. lagre kilde og tidspunkt for kontrollen

En kulturaktør kan bruke et etablert merkenavn selv om den juridiske enheten heter noe annet. Registerdata må derfor ikke overskrive redaksjonell identitet uten en eksplisitt regel.

Registeret kan heller ikke gi hele bildet av kulturfeltet. Det har normalt ikke CRM-ets kuraterte kategorier, interne vurderinger, foretrukne kontaktpersoner eller publiseringsvalg. Rollen er grunndata, ikke komplett bransjekunnskap.

## AI skal foreslå, ikke være skjult fasit

OpenAI-delen av importen kan strukturere opplysninger, foreslå kategorier eller normalisere verdier. En språkmodell kan også kombinere feil kilder, overvurdere sikkerheten eller gi en plausibel verdi som ikke er sann.

AI-resultater må behandles som ekstern input. Et forslag bør så langt det er praktisk ha:

- verdi og felt
- kildegrunnlag
- sikkerhetsnivå
- begrunnelse
- tidspunkt og metode
- krav om brukerreview

Backend må validere datatyper, URL-er, relasjoner og tillatte valg før noe kan lagres. Brukeren skal kunne godkjenne, avvise, redigere eller la feltet stå tomt.

Modellen skal ikke brukes som hukommelse for oppdatert kontaktinformasjon. Ferske fakta må komme fra kontrollerbare kilder.

### En robust berikelsesflyt

En senere kombinasjon av register, nettsøk og AI kan følge denne rekkefølgen:

1. Les importert rad og eksisterende CRM-kontekst.
2. Slå opp sterk identifikator når den finnes.
3. Hent autoritative grunndata.
4. Finn kandidatkilder for manglende offentlige opplysninger.
5. Hent bare innhold vi har lov til å behandle.
6. La AI strukturere og sammenligne funn.
7. Valider format, relasjoner og tillatte verdier deterministisk.
8. Sammenlign med dagens CRM-verdi.
9. Vis kilde, avvik og usikkerhet i preview.
10. Lagre først etter brukerbeslutning.

Autoritativt oppslag, søk, AI, kodebaserte regler og menneskelig review har ulike roller. Ingen av dem bør usynlig overta de andres ansvar.

## Planlagt Checkin-flyt

En fremtidig Checkin-integrasjon kan importere eller synkronisere deltakere. Før den bygges må faktisk API-tilgang, avtale, hendelser og felter avklares.

En påmelding er ikke automatisk samtykke til nyhetsbrev eller all senere CRM-bruk. Systemet må skille:

- arrangementsdeltakelse
- interesse eller segment
- markedsføringssamtykke
- teknisk påmeldingsstatus

CRM-et må eie matching og deduplisering. Samme person skal ikke opprettes flere ganger fordi et eksternt system sender samme hendelse på nytt.

En ekstern deltaker-ID kan knyttes til intern person-ID. E-post kan brukes som signal, men ikke som eneste bevis: generelle e-poster kan deles, og én person kan ha flere adresser.

Integrasjonen må også bestemme hva som skjer ved avmelding, endret billettype, refundering eller sletting. Før webhook eller løpende synkronisering velges, må leverandørens faktiske API-avtale, autentisering, rate limits og hendelser dokumenteres.

## Planlagt Mailmojo-flyt

En fremtidig Mailmojo-integrasjon kan sende et kontrollert CRM-segment til en e-postliste. Før synkronisering må CRM-et kontrollere gyldig e-post, behandlingsgrunnlag, avmelding og hvilket system som eier abonnementsstatusen.

Avmelding må komme tilbake til CRM-et, ellers kan neste eksport reaktivere en kontakt som har sagt nei.

Et dynamisk CRM-segment og en liste hos utsendelsesleverandøren er ikke nødvendigvis det samme. Integrasjonen må vise når den sist kjørte, hvor mange kontakter som ble endret, og hvilke feil som oppstod.

Et mulig segment kan bygge på tenant, kategori, geografi, tag og gyldig nyhetsbrevgrunnlag. Kontrollsiden bør vise hvilke kontakter som tas med, hvilke som utelates, og hvorfor.

CRM-et kan eie segmenteringen, mens Mailmojo eier utsendelse, bounce og teknisk avmelding. Denne ansvarsdelingen må være toveis: en avmelding hos leverandøren må blokkere senere vanlig eksport fra CRM-et.

Før integrasjonen bygges må prosjektet avklare API-kontrakt, OAuth-flyt, felter, feilhåndtering og samtykkemodell. En «Eksporter alle»-knapp er ikke en tilstrekkelig produktspesifikasjon.

## Planlagt kartvisning

Et kart trenger koordinater, men produktet må først bestemme hvor presis lokasjonen skal være.

Kommunenivå gir regional oversikt med mindre personvernrisiko. Nøyaktig besøksadresse kan være nyttig for arenaer, men kan avsløre hjemmeadressen til et enkeltpersonforetak.

En mulig fremtidig modell bør skille mellom:

- offentlig stedsnavn
- koordinater
- presisjonsnivå
- kilde og tidspunkt
- om eksakt lokasjon kan publiseres

Kartet bør bruke godkjente CRM-data, ikke gjøre et tilfeldig søk hver gang siden åpnes.

En geokodingsflyt kan kjøre når adresse eller kommune endres, lagre koordinat og presisjonsnivå, og la public API returnere ferdige kartdata. Det gir færre eksterne kall, mer stabil visning og tydeligere personvern.

Kartet kan senere støtte filtrering, markørklynger og regionale analyser. Men nøyaktig plassering skal ikke bygges før datamodell og publiseringsregel er besluttet. En privat hjemmeadresse skal ikke bli offentlig fordi et kart-API fant den.

## API-nøkler og autentisering

Eksterne API-er bruker gjerne API-nøkkel, OAuth eller en annen maskinidentitet. En hemmelig nøkkel skal normalt ligge i backendmiljøet:

```text
Nettleser → CRM-backend → ekstern tjeneste
```

Backend kan da beskytte nøkkelen, kontrollere brukerens tilgang, begrense bruken og logge feil. Nøkkelen skal ikke bygges inn i offentlig React-kode eller committes til Git.

Tilgangen bør ha minst mulig nødvendige rettigheter og egne verdier for test og produksjon når det er relevant.

## Timeout, rate limits og retry

Et eksternt API kan være tregt, utilgjengelig eller begrense antall kall.

En **timeout** stopper ventingen etter en definert tid. Uten timeout kan en importjobb bli hengende.

En **rate limit** begrenser antall kall. Når grensen nås, returnerer leverandøren ofte `429 Too Many Requests`.

Midlertidige feil kan prøves på nytt med ventetid, ofte kalt **backoff**. Ugyldig nøkkel, manglende tilgang eller ugyldig input skal ikke prøves blindt om igjen.

Retry må ha en grense. Ellers kan systemet lage en endeløs feilløkke, øke kostnader og gjøre problemet større.

## Idempotens og duplikater

En operasjon er **idempotent** når samme melding kan behandles flere ganger uten å skape nye uønskede resultater.

Hvis et påmeldingssystem sender samme deltakerhendelse tre ganger, skal CRM-et ikke opprette tre personer. Dette kan sikres med:

- ekstern objekt- eller hendelses-ID
- unique constraint
- idempotency key
- importjobb-ID
- dedupliseringsregler

Integrasjoner må anta at nettverksmeldinger kan bli sendt på nytt.

## Webhooks og synkronisering

Et **webhook** er en melding som et eksternt system sender når noe skjer. Alternativet er **polling**, der CRM-et spør med jevne mellomrom.

Et webhook-endepunkt må:

- verifisere avsenderen
- tåle duplikater
- svare raskt
- logge hendelsen
- håndtere retry
- legge tungt arbeid i en kontrollert jobb eller kø

En engangsimport er avgrenset. Løpende synkronisering krever i tillegg mapping av eksterne ID-er, konfliktregler, tidsstempler, status og en definert retning for dataflyten.

## Import og synkronisering er ulike produkter

En import er en avgrenset jobb: les en fil eller ekstern liste, vis preview og commit et kontrollert resultat. Brukeren kan kontrollere hele jobben før data skrives.

Synkronisering er en løpende forbindelse. Den må håndtere at begge systemer endres over tid, at samme hendelse kommer flere ganger, og at ett system er midlertidig utilgjengelig.

Før en planlagt kilde gjøres om fra import til synkronisering må prosjektet derfor avklare:

- ekstern og intern ID-mapping
- hvilken retning hvert felt kan oppdateres
- konflikt mellom manuell og ekstern verdi
- tidsstempler og sist vellykkede kjøring
- retry, stopp og gjenopptakelse
- hvordan brukeren ser og retter feil

Synkronisering gir ferskere data, men har høyere drifts- og personvernrisiko.

## Kilde og sporbarhet

Når CRM-et henter eller foreslår en verdi, bør det være mulig å forstå:

- hvor opplysningen kom fra
- når den ble hentet
- hvilken metode som behandlet den
- hvem som godkjente den
- om den kan overskrives automatisk

Dette kalles ofte **provenance** eller data lineage. Sporbarhet er særlig viktig for AI-forslag, import, offentlige grunndata og synkronisering.

En manuelt verifisert verdi bør ikke forsvinne uten at systemet viser hvorfor.

## Eksterne ID-er og integrasjonsstatus

Et modent integrasjonslag trenger stabile koblinger mellom systemene:

```text
CRM Person ID: 842
Ekstern deltaker-ID: abc123
Ekstern kontakt-ID: mm_778
```

Dette er sikrere enn å matche på navn ved hver synkronisering.

Integrasjonen bør også kunne vise:

- sist vellykkede kjøring
- hvor mange objekter som ble behandlet
- antall opprettede, oppdaterte og avviste
- konflikter og feil
- neste retry
- hvilken konfigurasjon eller API-versjon som ble brukt

Brukeren må kunne se om en prosess venter, feilet eller fullførte delvis. «Synkronisering pågår i bakgrunnen» er ikke nok informasjon når data endres.

Hvis en bruker manuelt korrigerer en synkronisert verdi, trenger systemet en regel: overskriv alltid, behold alltid, eller vis nytt forslag. For viktige CRM-felter er et synlig forslag ofte tryggere enn automatisk overskriving.

## Personvern og formålsbegrensning

At et API teknisk kan levere data betyr ikke at CRM-et bør lagre dem. For hver integrasjon må vi avklare:

- formål og behandlingsgrunnlag
- hvilke felter som er nødvendige
- hvem som får tilgang
- oppbevaring og sletting
- eventuell overføring til andre land
- hvordan innsyn og retting håndteres

Dataminimering er hovedregelen: Hent og lagre bare det CRM-et faktisk trenger.

## Testing og overvåkning

En integrasjon trenger flere testnivåer:

- **Kontrakttest:** Er CRM og leverandør enige om felter og typer?
- **Enhetstest:** Fungerer mapping og validering?
- **Integrasjonstest:** Kan koden kommunisere med et testmiljø eller en mock?
- **Ende-til-ende-test:** Fungerer hele brukerflyten?
- **Produksjonskontroll:** Virker ekte konfigurasjon uten å skade data?

Et **mock** er et kontrollert, falskt API-svar. Det gjør tester raske og stabile og kan simulere sjeldne feil. Mocken må oppdateres når den virkelige kontrakten endres.

Overvåkningen bør vise kall, responstid, feil, kostnad, rate-limit-hendelser, konflikter og sist vellykkede synkronisering. Integrasjoner skal ikke være usynlige bakgrunnsprosesser.

Eksterne API-er kan endre versjon, felter, autentisering, pris eller vilkår. Hver integrasjon trenger derfor eier, dokumentasjonslenke, versjon, tester og fallback.

## Mål kvalitet, ikke bare teknisk suksess

En AI- eller søkeflyt kan returnere `200 OK` og fortsatt foreslå feil aktør. Derfor trenger prosjektet et fast kvalitetsdatasett med kjente organisasjoner og manuelt verifiserte svar.

Ved endring av modell, prompt, nettsøk eller parser kjøres de samme eksemplene på nytt. Vi måler blant annet:

- riktig offisiell nettside og kommune
- riktig kategorisering
- oppdiktede eller feilaktige verdier
- kostnad og behandlingstid
- hvor ofte brukeren må korrigere
- hvor ofte en svak kilde blir valgt

Uten sammenlignbare eksempler vet vi ikke om en «oppgradering» faktisk forbedrer resultatet.

Vanlige tester bør også dekke leverandørfeil, timeout, duplikate webhooks, utløpt autentisering og delvis fullførte batcher. Det er ofte feiltilfellene som avgjør om integrasjonen er trygg.

## Vanlige HTTP-feil

- `400 Bad Request`: Ugyldige felter, typer eller parametere.
- `401 Unauthorized`: Manglende eller ugyldig autentisering.
- `403 Forbidden`: Identiteten er kjent, men mangler tillatelse.
- `404 Not Found`: Ressursen eller endepunktet finnes ikke.
- `409 Conflict`: Kallet kolliderer med eksisterende tilstand.
- `429 Too Many Requests`: Rate limit er nådd.
- `500`–`599`: Serveren eller leverandøren feilet.

Systemet må skille mellom brukerfeil, permanente konfigurasjonsfeil og midlertidige leverandørfeil.

## Når en ny integrasjon planlegges

Før implementering må vi beskrive:

1. formålet og dataflyten
2. autoritativ kilde per felt
3. offisiell API-kontrakt og versjon
4. autentisering og hemmeligheter
5. mapping til interne modeller
6. timeout, retry, rate limit og idempotens
7. personvern, samtykke og oppbevaring
8. teststrategi og testmiljø
9. kostnad og overvåkning
10. hvordan integrasjonen stoppes eller deaktiveres

Først da kan Codex implementere en avklart løsning uten å gjette produktregler.

## Takeaways

- API-et er både kommunikasjonskanal og kontrollpunkt.
- CRUD og HTTP-metoder beskriver grunnhandlingene mot ressurser.
- Internt og offentlig API har ulike data- og tilgangsregler.
- Hvert integrert felt trenger en autoritativ kilde og sporbarhet.
- Eksterne kall må håndtere feil, timeout, rate limits, retry og duplikater.
- Planlagte integrasjoner skal ikke omtales som implementert.

## Prinsippet

En god integrasjon bevarer mening, tilgang, samtykke, kilde og ansvar når data flyttes.
