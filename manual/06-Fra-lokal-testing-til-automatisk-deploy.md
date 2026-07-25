# Kapittel 6 – Fra lokal testing til automatisk deploy: Når skal du bruke hva?

Jeg trodde lenge at jeg måtte velge én fast arbeidsform: enten teste alt lokalt på Mac-en eller sende alle endringer rett til serveren. Etter hvert forsto jeg at testnivået bør følge risikoen.

En liten tekstendring trenger ikke samme prosess som en databasemigrasjon. Den raskeste trygge arbeidsflyten er den som bruker riktig kontroll til riktig type endring.

## Tre miljøer med ulike formål

**Lokalt miljø** er CRM-et som kjører på Mac-en, vanligvis gjennom Docker. Her kan jeg eksperimentere og bruke testdata uten at andre brukere ser arbeidet. Backend kan for eksempel svare på `localhost:8000`, mens frontend kan ha en egen lokal adresse. At adressen åpner, viser bare at tjenesten svarer; den konkrete arbeidsflyten må fortsatt testes.

**Staging** er en serverversjon som skal ligne den virkelige løsningen. Den brukes som generalprøve for blant annet innlogging, HTTPS, Docker, databaseendringer og samspillet mellom tjenestene.

**Produksjon** er løsningen som virkelige brukere og integrasjoner er avhengige av. En feil her kan påvirke tilgang, data, import, publisering og API-er. Produksjon er derfor ikke et sted for fri utprøving.

Automatisk deploy betyr at en hendelse, for eksempel en push eller sammenslåing til hovedbranchen, kan starte tester og oppdatering av serveren. Dette er et ønsket langsiktig oppsett i Kreative Norge CRM, men automatisk staging-deploy er foreløpig ikke implementert eller verifisert. Manualen beskriver derfor både dagens kontrollerte leveransesteg og prinsippene for en senere automatisert flyt.

## Automatiske tester og menneskelig kontroll

Automatiske tester kan kontrollere om:

- backend-testene består
- frontend kan bygges
- koden har syntaks- eller typefeil
- et API svarer som forventet
- databasekoblingen fungerer

Menneskelig brukertesting svarer på andre spørsmål:

- Er arbeidsflyten forståelig?
- Ser skjermbildet riktig ut?
- Er teksten presis?
- Skjer det brukeren forventer?
- Er løsningen faktisk bedre enn før?

En automatisk test kan vise at en knapp utløser riktig handling. Den kan sjelden avgjøre om knappen er lett å finne eller forstå. Jeg trenger begge kontrollformene.

## Velg arbeidsflyt etter risiko

Før arbeidet starter, spør jeg:

1. Kan endringen endre eller skade data?
2. Kan den påvirke innlogging, tilgang eller tenant-isolasjon – skillet som hindrer én organisasjon i å se en annens data?
3. Kan den gjøre en offentlig eller intern tjeneste utilgjengelig?
4. Berører den flere systemlag eller viktige arbeidsflyter?
5. Kan den reverseres enkelt dersom noe går galt?

Svarene plasserer endringen i en enkel trafikklysmodell.

### Grønn: liten og lett å reversere

Eksempler er retting av tekst, en liten stiljustering, intern dokumentasjon, logging eller en isolert feil med en tydelig test.

Arbeidsflyten kan være:

1. Undersøk og implementer.
2. Kjør relevante tester eller frontend-build.
3. Les diffen.
4. Commit og push.
5. Gjennomfør avtalt deploy.
6. Åpne løsningen og kontroller endringen.

Lokal Docker-testing kan være mer arbeid enn nytte hvis endringen ikke påvirker funksjon, data eller sikkerhet.

### Gul: funksjonell endring med flere konsekvenser

Eksempler er et nytt skjema, filter eller API-endepunkt, en større frontend-endring, endret publiseringslogikk eller en ny integrasjon.

Her bør arbeidsflyten normalt inneholde:

1. En kort plan og tydelige akseptansekriterier.
2. Implementering og automatiske tester.
3. Lokal kjøring i Docker.
4. Manuell test av den berørte arbeidsflyten.
5. Commit og push, gjerne på egen branch.
6. Deploy til staging.
7. Kontroll før eventuell produksjonssetting.

### Rød: data, sikkerhet eller arkitektur

Røde endringer omfatter blant annet:

- migrasjoner som påvirker eksisterende data
- sletting, flytting eller masseoppdatering av data
- import og eksport av store datamengder
- autentisering, roller og tenant-isolasjon
- server-, Docker- eller databaseendringer
- større arkitekturvalg eller bytte av teknologisk hovedretning

Slike endringer krever en godkjent plan eller ADR når omfanget tilsier det, backup, egen branch, lokale tester, realistiske testdata, staging, gjennomgang og en tydelig tilbakeføringsplan. Produksjonssetting skjer først etter eksplisitt beslutning.

## Områder som alltid fortjener ekstra kontroll

**Databasen** er hjertet i CRM-et. Nye felt, felttyper, relasjoner, begrensninger og migrasjoner må testes mot både eksisterende og nye data. Backup må bekreftes før en endring som er vanskelig å reversere.

**Import og eksport** kan opprette eller endre mange poster samtidig. Import må kontrollere matching, duplikater, tenant, kategorier, tags, personer, aktører, koblinger og kontaktinformasjon. Bruk testfiler eller kopierte data, aldri den eneste virkelige kontaktlisten.

**Roller og tilgang** må prøves med flere brukere og roller. En feil kan enten stenge riktige brukere ute eller gi tilgang til data de ikke skal se.

**Offentlig publisering** må kontrolleres både teknisk og visuelt. Endringer kan påvirke hvilke aktører, personer og kontaktkanaler som blir synlige utenfor CRM-et.

**Docker, server og deploy** krever kontroll av Docker Compose-filene som beskriver tjenestene, i tillegg til miljøvariabler, porter, domenekonfigurasjon, HTTPS og databaseforbindelse. En liten konfigurasjonsfeil kan stoppe hele løsningen.

## Tre konkrete CRM-arbeidsflyter

En liten endring kan være å rette hjelpeteksten i importvinduet. Da er det nok at Codex avgrenser tekstendringen, kjører frontend-build eller en relevant kontroll, viser diffen og lager en tydelig commit. Etter avtalt leveranse åpner jeg siden og leser teksten i riktig sammenheng.

En mellomstor endring kan være et nytt eksportfilter. Først avklarer vi hvilke data filteret skal inkludere og hvordan tomme verdier behandles. Codex implementerer og skriver tester. Deretter starter vi løsningen lokalt, prøver flere filterkombinasjoner og kontrollerer resultatet. Arbeidet kan pushes på en egen branch og deployes til staging før noen vurderer produksjonssetting.

En stor endring kan være en ny importmotor eller en endring i datamodellen. Da starter arbeidet med diagnose, spesifikasjon og eventuelt en arkitekturavgjørelse. Vi kartlegger berørte modeller, API-er, skjermbilder, eksisterende data og migrasjoner. Implementeringen skjer på egen branch med testdata og backup-plan. Før produksjon kreves automatiske tester, lokal kontroll, staging, manuell godkjenning og en beskrevet vei tilbake.

Disse tre flytene bruker mange av de samme verktøyene. Forskjellen ligger i hvor mange kontrollpunkter risikoen krever.

## Lokal Docker-test

Før lokal test kontrollerer jeg at jeg står i riktig prosjekt og ikke har uavklarte endringer:

```bash
pwd
git status
git branch --show-current
```

Hvis andre kan ha oppdatert GitHub, må historikken undersøkes og hentes på en trygg måte før testen. `git pull` bør ikke kjøres blindt over uferdig lokalt arbeid.

Start eller bygg miljøet:

```bash
docker compose up -d --build
docker compose ps
```

Se etter feil:

```bash
docker compose logs --tail=100
docker compose logs -f
```

`-f` følger nye logglinjer fortløpende og avsluttes med `Ctrl+C`.

Deretter tester jeg hele den endrede arbeidsflyten. Et nytt personfelt bør for eksempel prøves ved oppretting, lagring, gjenåpning og redigering. Jeg kontrollerer også at nærliggende felt og relevant API-adferd fortsatt virker.

Når testen er ferdig:

```bash
docker compose down
```

Denne kommandoen stopper normalt containerne uten å slette data i Docker-volumer. Varianten under krever stor forsiktighet:

```bash
docker compose down -v
```

`-v` kan slette volumer og dermed den lokale databasen. På en server kan feil bruk få langt større konsekvenser.

## Commit, branch og deploy er ulike beslutninger

En commit betyr at endringen skal bevares i Git-historikken. Push betyr at commiten skal deles via GitHub. Deploy betyr at en bestemt versjon skal kjøre i et miljø. Disse handlingene trenger ikke skje samtidig.

En større funksjon kan utvikles på en egen branch, pushes og gjennomgås uten at hovedversjonen endres. Først når funksjonen er testet og godkjent, slås den sammen og gjøres klar for staging eller produksjon.

En fremtidig automatisk leveranseflyt bør ha kvalitetsporter, altså kontroller som må bestås før neste steg:

```text
push
→ backend-tester
→ frontend-build og typesjekk
→ deploy til staging
→ manuell kontroll
→ kontrollert produksjonssetting
```

Hvis en obligatorisk test feiler, skal flyten stoppe. Automatisering øker farten; den vurderer ikke alene om endringen er klok eller trygg.

## Kontroll og tilbakeføring

Etter hver deploy kontrollerer jeg minst:

- at løsningen svarer
- at innlogging fungerer når relevant
- at den endrede siden eller API-funksjonen virker
- at data kan leses og lagres som forventet
- at logger ikke viser nye, tydelige feil

Før en risikofylt deploy må jeg vite hvordan den kan reverseres. Kode kan ofte tilbakeføres til en tidligere commit. En migrasjon eller import kan også kreve revers migrasjon, gjenoppretting av databasebackup eller en egen reparasjon. Hvis ingen kan beskrive veien tilbake, er endringen ikke klar for produksjon.

En kort beslutningssjekk før leveranse er:

- Er endringen fortsatt grønn, gul eller rød etter at vi har sett koden?
- Har alle relevante automatiske tester bestått?
- Er brukerflyten prøvd manuelt når det er nødvendig?
- Er migrasjoner, backup og eksisterende data kontrollert?
- Vet vi hvilken branch og commit som skal leveres?
- Er neste miljø staging eller produksjon?
- Vet vi hvordan endringen kan stoppes eller reverseres?

Etter leveransen kontrollerer jeg den berørte arbeidsflyten, dataene og loggene. En vellykket kommando er ikke det samme som en vellykket endring.

## Takeaways

- Lokalt miljø, staging og produksjon har ulike formål.
- Automatiske tester og menneskelig brukertesting finner forskjellige problemer.
- Testnivået skal følge risikoen, ikke en fast rutine for alle endringer.
- Data, tilgang, import og infrastruktur krever ekstra forsiktighet.
- Commit, push og deploy er tre separate beslutninger.
- Automatisk staging-deploy er planlagt, men ikke implementert eller verifisert.

## Prinsippet

Automatiser det forutsigbare, test det menneskelige manuelt, og vær ekstra forsiktig med alt som kan endre data.
