# Kapittel 9 – Docker: hvorfor CRM-et kjører i containere

Jeg visste lenge at `docker compose up` startet CRM-et, men ikke hva Docker faktisk gjorde. Jeg blandet sammen applikasjonen, containerne og dataene.

Docker er ikke selve CRM-et. Det lager kontrollerte miljøer der deler av systemet kan kjøre med bestemte programmer, biblioteker og innstillinger. Målet er å redusere forskjellene mellom Mac-en, stagingserveren og produksjon.

## Problemet Docker løser

Kreative Norge CRM trenger mer enn én kjørbar fil. Systemet bruker blant annet Python, Django, PostgreSQL, React, TypeScript, Vite og nginx, med bestemte avhengigheter og versjoner.

Uten et avgrenset miljø kan Mac-en ha én Python-versjon, serveren en annen og utviklerens maskin en tredje. En oppdatering kan bryte ett prosjekt fordi et annet trenger en annen bibliotekversjon. Resultatet er den klassiske setningen: «Det fungerer på min maskin.»

Docker pakker kjørekravene mer forutsigbart. Det fjerner ikke alle forskjeller. Serveren har fortsatt andre data, hemmeligheter, domener, nettverk og ressurser. Men antallet ukjente blir mindre.

## Container, image og virtuell maskin

En **container** er et isolert programmiljø. Den avgrenser prosesser, filer, nettverk og innstillinger, men er ikke nødvendigvis en komplett datamaskin.

En tradisjonell virtuell maskin har vanligvis et helt operativsystem og egen systemkjerne. Containere deler mer med maskinen de kjører på. Derfor starter de ofte raskere og bruker mindre plass.

Et **image** er malen containeren opprettes fra. Det beskriver blant annet:

- hvilket grunnmiljø som brukes
- hvilke biblioteker som installeres
- hvilke prosjektfiler som kopieres inn
- hvilken kommando som starter programmet

Image og container må ikke blandes:

```text
Image = pakket mal
Container = kjørende utgave av malen
```

Flere containere kan opprettes fra samme image. En container kan erstattes uten at selve oppskriften forsvinner.

## Dockerfile og build

En `Dockerfile` er byggeoppskriften for et image. En forenklet Django-utgave kan se slik ut:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "config.wsgi:application"]
```

Instruksjonene velger et Python-miljø, installerer avhengigheter, kopierer prosjektet og definerer oppstartskommandoen.

Gunicorn er serverprogrammet som kjører Django-applikasjonen i stagingoppsettet.

Jeg bygger image med for eksempel:

```bash
docker compose build
docker compose up -d --build
```

Docker gjenbruker ofte uendrede byggesteg fra en **cache**, eller mellomlager. Derfor kan et nytt build gå raskt. Ved mistanke om at gammel cache skjuler en endring, kan en utvikler vurdere:

```bash
docker compose build --no-cache
```

Dette tar mer tid og skal ikke være standardløsningen på enhver feil. Les først byggeloggen og forstå hva som faktisk mangler.

## Docker Compose organiserer tjenestene

Docker Compose beskriver flere tjenester i én YAML-fil, et tekstformat for konfigurasjon. I CRM-ets lokale `docker-compose.yml` finnes blant annet:

- `db`, som kjører PostgreSQL
- `api`, som kjører Django

Stagingoppsettet har i tillegg `web`, som bygger og serverer frontend og statiske filer gjennom nginx.

En **service** er definisjonen i Compose-filen. En **container** er den kjørende instansen. Inne i containeren kjører programmet:

```text
api-service → API-container → Django
db-service  → database-container → PostgreSQL
web-service → web-container → nginx og bygget frontend
```

Service- og containernavn er ikke alltid identiske. I kommandoer som `docker compose logs api` bruker jeg servicenavnet fra Compose-filen. Et automatisk generert containernavn kan endres mellom miljøer og oppstarter. Derfor er Compose-kommandoer vanligvis tryggere enn å bygge arbeidsflyten rundt ett hardkodet containernavn. Før jeg kopierer en kommando fra manualen, kontrollerer jeg at servicenavnet fortsatt finnes i den aktuelle Compose-filen.

Lokalt kjører React-frontend vanligvis med Vite på Mac-en og sender `/api`-kall videre til Django på port 8000. På staging bygges frontend til filer som serveres gjennom `web`-tjenesten. Det er samme kildekode, men ulik kjøreform.

## Nettverk, localhost og porter

Compose oppretter et internt nettverk der tjenester kan finne hverandre på servicenavn. API-containeren kan nå PostgreSQL gjennom navnet `db`.

`localhost` betyr alltid «miljøet jeg står inne i»:

- I nettleseren på Mac-en betyr `localhost` Mac-en.
- Inne i API-containeren betyr `localhost` API-containeren.
- Databasen er en annen container og nås normalt som `db`.

Dette er en vanlig årsak til tilkoblingsfeil.

En port er en nummerert inngang til et program. I Compose kan en port kobles fra vertsmaskinen til containeren:

```yaml
ports:
  - "8000:8000"
```

Da sendes trafikk til Mac-ens port 8000 videre til port 8000 i containeren. På staging er det vanligvis webtjenesten som eksponerer port 80 eller 443 mot omverdenen.

Interne tjenester trenger ikke nødvendigvis en offentlig port. PostgreSQL bør ikke eksponeres mot internett uten et konkret og sikret behov.

## Volumer og varige data

Containere er utskiftbare. Filer som bare ligger i containerens eget filsystem, kan forsvinne når containeren fjernes.

PostgreSQL-data må derfor ligge i et **volume**, som er lagring utenfor den enkelte containeren:

```text
PostgreSQL-container → Docker-volume → databasefiler
```

Når jeg kjører:

```bash
docker compose down
```

stoppes og fjernes normalt containerne, mens volumene beholdes. Ved neste oppstart kan databasecontaineren kobles til samme lagring.

Denne varianten er vesentlig farligere:

```bash
docker compose down -v
```

`-v` fjerner også tilknyttede volumer. Lokalt kan det brukes bevisst for å starte med tom database. På staging eller produksjon kan det slette data. Kommandoen skal aldri brukes mot data som skal beholdes uten uttrykkelig beslutning og kontrollert backup.

Et volume er aktiv lagring, ikke backup. Hvis serverdisken ødelegges, volumet blir korrupt eller en kommando sletter det, trenger vi en separat databasebackup på et annet lagringssted.

## Bind mounts og lokal utvikling

Et **bind mount** kobler en mappe fra Mac-en eller serveren inn i containeren:

```yaml
volumes:
  - .:/app
```

Det lokale CRM-oppsettet monterer prosjektmappen i API-containeren. Kodeendringer blir dermed tilgjengelige uten at hele image må bygges på nytt hver gang.

I staging brukes ferdig bygde images og egne volumer for database og statiske filer. Det reduserer avhengigheten av løse prosjektfiler på serveren.

## Miljøvariabler og hemmeligheter

Samme image kan oppføre seg forskjellig gjennom miljøvariabler:

```text
DEBUG=false
DB_HOST=db
SECRET_KEY=...
```

Vanlig konfigurasjon og hemmeligheter er ikke helt det samme. En API-nøkkel, databasepassord eller Django `SECRET_KEY` skal:

- ikke committes til Git
- ikke vises i logger eller chat
- lagres sikkert per miljø
- ha minst mulig tilgang
- roteres ved mistanke om lekkasje

Lokalt, staging og produksjon skal ikke ukritisk dele samme hemmeligheter eller database.

## Oppstart, healthchecks og restart

`depends_on` kan sørge for at Docker starter `db` før `api`. Det betyr ikke nødvendigvis at PostgreSQL er ferdig med oppstarten og klar til å ta imot kall.

En **healthcheck** undersøker om tjenesten faktisk svarer. En prosess kan være startet og likevel være ubrukelig. Derfor er det bedre å kontrollere API-respons eller databaseforbindelse enn bare at containeren finnes.

På serveren kan en restartregel som `unless-stopped` starte en container igjen etter server- eller Docker-restart. Dette erstatter ikke healthchecks, logger og overvåkning.

## Kommandoene jeg bruker mest

Start og bygg:

```bash
docker compose up -d --build
```

Se tjenester og status:

```bash
docker compose ps
docker ps
docker ps -a
```

Les logger:

```bash
docker compose logs --tail=100
docker compose logs -f api
docker compose logs -f db
```

Kjør en kommando i en container som allerede er startet:

```bash
docker compose exec api python manage.py check
docker compose exec api python manage.py migrate
```

`exec` bruker en eksisterende container. `run` kan opprette en midlertidig container:

```bash
docker compose run --rm api python manage.py check
```

`--rm` fjerner engangscontaineren etterpå. De nøyaktige testkommandoene avhenger av prosjektets oppsett.

En enkelt tjeneste kan restartes eller bygges:

```bash
docker compose restart api
docker compose up -d --build api
```

Før dette gjøres på serveren må jeg vite om tjenesten har avhengigheter og om en kontrollert deploy allerede pågår.

## Docker Desktop, ressurser og disk

På Mac kjører Docker gjennom Docker Desktop. Der kan jeg se containere, images, volumer, logger og ressursbruk. Det visuelle grensesnittet er nyttig for oversikt, mens terminalkommandoene er lettere å dokumentere, gjenta og bruke på serveren.

Containere bruker CPU, minne, disk og nettverk. Hvis Docker får for lite minne, kan database, build eller tester bli trege eller stoppe. Hvis Docker får for mye, kan resten av Mac-en bli treg.

På serveren påvirkes ressursbehovet blant annet av:

- antall samtidige brukere
- databasevolum og søk
- store importjobber
- AI-kall og ekstern berikelse
- bygging av frontend og images
- logging og backup

Images og build-cache bruker diskplass. Jeg kan se oversikten med:

```bash
docker system df
```

Docker har oppryddingskommandoer som `docker system prune`, men de skal ikke kjøres ukritisk. Ressurser som ikke er aktive akkurat nå, kan fortsatt være nødvendige for tilbakeføring eller senere arbeid. På produksjon må opprydding følge en konkret plan, ikke et automatisk ønske om mer ledig plass.

Hvis disken fylles, undersøker jeg først hva som tar plass. Tilfeldig sletting av images, volumer eller logger kan gjøre gjenoppretting vanskeligere.

## Lokalt, staging og produksjon

Miljøene bruker samme applikasjon, men ulik konfigurasjon:

- **Lokalt:** utvikling, testdata, bind mounts og rask restart.
- **Staging:** realistisk servermiljø, eget domene, egne hemmeligheter og testdatabase.
- **Produksjon:** ekte data, debug av, backup, overvåkning og kontrollert tilgang.

CRM-et har egne Compose-filer for lokalt grunnoppsett, lokale utviklingsinnstillinger og staging. Derfor må en kommando alltid bruke riktig filkombinasjon og riktig miljø.

En Docker-basert deploy kan omfatte:

```text
riktig commit
→ build av nye images
→ kontrollerte migrasjoner
→ oppstart av nye containere
→ status og logger
→ funksjonell kontroll
```

Automatisk staging-deploy er ønsket, men ikke implementert eller verifisert. Manualen skal derfor ikke late som om en push automatisk oppdaterer serveren.

## Når lokal Docker-test er nødvendig

Full lokal Docker-test er særlig nyttig når endringen berører:

- Python- eller Node-avhengigheter
- Dockerfile eller Compose-filer
- databasekobling og nettverk
- migrasjoner
- miljøvariabler
- frontend-build
- systembiblioteker
- forskjeller mellom utvikling og server

En ren tekstendring trenger vanligvis ikke et nytt image. En ny Python-pakke eller endret oppstartskommando må derimot bygges og prøves i containeren.

Docker kan også gi automatiske tester et kontrollert miljø med PostgreSQL og API. En god teststrategi kombinerer raske enhetstester, integrasjonstester og noen viktige ende-til-ende-tester. Docker gjør testmiljøet mer likt, men bruker også tid. Derfor bør ikke alle tester kreve full rebuild.

Eksterne tjenester som OpenAI krever nettverk, nøkkel, timeout og feilhåndtering. Lokal testing bør bruke avgrenset konfigurasjon og aldri gjøre store, kostbare eller irreversible produksjonskall uten kontroll.

## Migrasjoner krever egen vurdering

Denne kommandoen endrer databasestrukturen:

```bash
docker compose exec api python manage.py migrate
```

Det er ikke «bare en Docker-kommando». Ny kode kan kreve en kolonne som databasen ennå ikke har, og en migrasjon kan endre eksisterende data.

I dagens staging-Compose kjører API-tjenesten `migrate` som del av oppstarten, før statiske filer samles og Gunicorn starter. Det betyr at oppstart av en ny stagingcontainer også kan endre stagingdatabasen. Automatisk kjøring fjerner ikke behovet for lokal test, kontroll av migrasjonsfilen og backupvurdering.

Tryggere endringer kan deles i trinn:

1. Legg til nytt felt uten å fjerne det gamle.
2. Deploy kode som kan håndtere begge.
3. Flytt og kontroller data.
4. Bytt lesing og skriving til det nye feltet.
5. Fjern det gamle i en senere endring.

Dette reduserer risikoen under overgangen. Migrasjoner behandles grundigere i neste kapittel.

## Vanlige Docker-feil

**Containeren stopper med en gang:** Les loggene. Vanlige årsaker er manglende miljøvariabel, database som ikke svarer, oppstartsfeil eller manglende bibliotek.

**Image bygger ikke:** Les hele feilmeldingen, ikke bare siste linje. Feilen kan ligge i Dockerfile, en avhengighet, nettverket eller diskplassen.

**Koden er endret, men gammel versjon vises:** Kontroller branch, commit, Compose-fil, bind mount, build og hvilken container som faktisk kjører.

```bash
git status
git log -1 --oneline
docker compose ps
```

**Den lokale databasen ser tom ut:** Ikke opprett nye data før du har undersøkt miljøvariabler, Compose-prosjektnavn og volumer:

```bash
docker volume ls
```

**Porten er opptatt:** Finn riktig container eller prosess. Ikke stopp tilfeldige tjenester på en server.

**Databaseforbindelsen avvises:** Kontroller `api`- og `db`-logger, vertsnavnet `db`, bruker, passord, port og Docker-nettverket.

## Eksempel fra Kreative Norge CRM

Ved lokal oppstart:

```bash
pwd
git status
docker compose up -d --build
docker compose ps
docker compose logs --tail=100
```

Deretter tester jeg den konkrete arbeidsflyten i nettleseren.

Etter endring av backend-avhengigheter bør Codex beskrive hva som krever nytt build, bygge `api`, kjøre Django-kontroll og relevante tester.

Ved Docker-endringer skal rapporten minst angi:

- hvilke Docker- eller Compose-filer som er endret
- hvilke tjenester, porter og volumer som påvirkes
- om miljøvariabler eller hemmeligheter må oppdateres
- om rebuild eller migrasjon kreves
- hvordan endringen ble testet
- hvordan den kan reverseres

En liten YAML-endring kan påvirke hele kjøringen.

## Kontroll før og etter serverendring

Før en Docker-relatert serverendring kontrollerer jeg:

```bash
hostname
pwd
git branch --show-current
git status
docker compose ps
```

Deretter avklarer jeg:

- hvilken Compose-fil serveren bruker
- hvilken commit som skal kjøre
- om nye images må bygges
- om porter, volumer eller hemmeligheter endres
- om databasebackup og migrasjon er nødvendig
- hvordan forrige versjon kan startes igjen

Etterpå kontrollerer jeg containerstatus, logger, API, innlogging og den konkrete arbeidsflyten. Ved databaseendring kontrolleres også eksisterende data.

At en container står som `running`, beviser ikke at CRM-et fungerer. At nettsiden åpner, beviser heller ikke at import, redigering eller public API er uskadd.

## Docker avgjør ikke teknologistacken

Django og Node.js kan begge pakkes i containere. Et eventuelt backendbytte vil endre base-image, avhengigheter, bygg, oppstartskommando, tester og migrasjonsverktøy. Docker gir en felles måte å pakke og kjøre dem på, men sier ikke hvilket rammeverk som passer produktet best.

Et image blir heller ikke sikkert bare fordi det er isolert. Base-images, biblioteker og systempakker må oppdateres, bygges på nytt og testes. Docker gir kontroll, men også vedlikeholdsansvar.

## Takeaways

- Docker gjør kjøreomgivelsene mer forutsigbare, men er ikke selve CRM-et.
- Et image er malen; en container er den kjørende utgaven.
- Compose organiserer tjenester, nettverk, porter, volumer og innstillinger.
- Containerne kan erstattes, mens databasen må ligge i varig lagring med separat backup.
- `down -v`, migrasjoner og serverkommandoer krever eksplisitt kontroll.
- Lokal, staging og produksjon bruker samme kode med ulike miljøregler.

## Prinsippet

Containere skal kunne erstattes; data skal sikres uavhengig av containeren som bruker dem.
