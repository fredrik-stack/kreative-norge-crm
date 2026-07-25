# Kapittel 8 – Terminalen: kontrollrommet på Mac-en og webserveren

Terminalen var lenge et av verktøyene jeg var mest usikker på. Det mørke vinduet så ut som et eget teknisk system, men er egentlig et tekstbasert grensesnitt for å gi presise kommandoer til en datamaskin.

Det farlige er sjelden selve Terminalen. Risikoen oppstår når jeg kjører riktig kommando på feil maskin, som feil bruker, i feil mappe eller i feil miljø.

## Terminalen sender ordre

Terminal er ikke Git, Docker, Python, Django eller Linux. Den lar meg be disse systemene utføre noe:

```bash
git status
docker compose up
ssh bruker@server
```

Den første kommandoen ber Git vise prosjektstatus. Den andre ber Docker starte tjenester. Den tredje oppretter en sikker fjernforbindelse til en annen datamaskin.

Mac-appen Terminal og terminalpanelet i VS Code arbeider vanligvis mot samme Mac. Mac-appen starter ofte i hjemmemappen, mens VS Code-terminalen gjerne starter i prosjektmappen. Jeg skal likevel aldri anta hvor jeg er.

## Finn maskinen og mappen

Tre kommandoer gir grunnleggende orientering:

```bash
hostname
pwd
ls
```

`hostname` viser navnet på maskinen. `pwd`, forkortelse for *print working directory*, viser gjeldende mappe. `ls` viser innholdet i mappen, mens `ls -la` også viser skjulte filer, eierskap og rettigheter.

En lokal prosjektsti kan ligne:

```text
/Users/fredrikforssman/kreative-norge-crm
```

En serversti kan ligge under `/home/deploy/` eller `/root/`. Forskjellen er et viktig signal om hvilken maskin jeg styrer.

Jeg flytter meg mellom mapper med `cd`, som betyr *change directory*:

```bash
cd /sti/til/kreative-norge-crm
cd ..
cd "Mappe med mellomrom"
```

`cd ..` går ett nivå opp. Anførselstegn beskytter stier med mellomrom.

En trygg start på en lokal arbeidsøkt er:

```bash
cd /sti/til/kreative-norge-crm
hostname
pwd
git branch --show-current
git status
```

Da vet jeg hvilken maskin, mappe og Git-branch kommandoene gjelder.

## Prompten viser kontekst

Teksten foran markøren kalles **prompten**. Lokalt kan den ligne:

```text
fredrik@MacBook kreative-norge-crm %
```

Etter innlogging på serveren kan den ligne:

```text
deploy@crm-server:~/kreative-norge-crm$
```

Prompten kan vise bruker, maskin og mappe. Utseendet varierer, så jeg bruker fortsatt `hostname` og `pwd` før viktige handlinger.

## SSH: Terminal mot en annen maskin

SSH står for **Secure Shell** og brukes til sikker fjerninnlogging:

```bash
ssh deploy@serveradresse
```

Terminalvinduet er fortsatt åpent på Mac-en, men kommandoene utføres nå på serveren. Etter innlogging kontrollerer jeg:

```bash
hostname
pwd
git branch --show-current
git status
```

Jeg logger ut med:

```bash
exit
```

Deretter bør prompten igjen vise Mac-en. `hostname` bekrefter det hvis jeg er usikker.

Mac og Linux er beslektede Unix-systemer, så mange kommandoer er like. Filplassering, brukerrettigheter, programmer og tjenester kan likevel være forskjellige.

## Vanlige filkommandoer

Opprett en mappe:

```bash
mkdir testmappe
mkdir -p backup/database
```

`-p` oppretter manglende mellommapper.

Opprett en tom fil eller oppdater filens tidsstempel:

```bash
touch test.txt
```

Codex oppretter vanligvis prosjektfiler for meg, men kommandoen er nyttig å kjenne igjen.

Kopier en fil eller mappe:

```bash
cp kilde.txt kopi.txt
cp -R gammelmappe nymappe
```

Flytt eller gi nytt navn:

```bash
mv fil.txt mappe/
mv gammelt-navn.txt nytt-navn.txt
```

Les en kort fil:

```bash
cat README.md
```

For lengre filer er `less README.md` bedre. Der kan jeg rulle, søke med `/` og avslutte med `q`. `head` viser begynnelsen av en fil, mens `tail` viser slutten:

```bash
head README.md
tail -f applikasjon.log
```

`tail -f` følger nye logglinjer og stoppes med `Ctrl+C`.

### Sletting krever respekt

```bash
rm fil.txt
rm -r mappe
rm -rf mappe
```

`rm` flytter vanligvis ikke til Papirkurv. `-r` sletter rekursivt, og `-f` tvinger gjennom uten spørsmål. Jeg kjører aldri `rm -rf` uten å ha kontrollert den nøyaktige stien, maskinen, konsekvensen og eventuell backup.

Git kan hjelpe med versjonsstyrte prosjektfiler, men ikke nødvendigvis med uregistrerte filer, serverdata eller databasen.

## Prosesser, avbrudd og bakgrunnskjøring

Et kjørende program er en **prosess**. Noen kommandoer skal fortsette å kjøre. Når:

```bash
docker compose up
```

viser logger og ikke gir prompten tilbake, betyr det vanligvis at Docker kjører i forgrunnen. `Ctrl+C` avbryter den aktive prosessen. Det er ikke samme handling som `Command+C`, som kopierer tekst på Mac.

Bakgrunnsmodus gir prompten tilbake mens containerne fortsetter:

```bash
docker compose up -d
```

På Linux viser `ps aux` prosesser, men Docker-tjenester bør vanligvis undersøkes med Docker-kommandoer fremfor å stoppes tilfeldig i operativsystemet.

## Søk og pipes

En loddrett strek, `|`, kalles en **pipe**. Den sender resultatet fra én kommando videre til en annen:

```bash
docker compose logs | grep error
git log --oneline | head
```

`grep` søker i tekst. I det første eksemplet filtreres logglinjer som inneholder `error`. Jeg kan også søke i en fil eller mappe:

```bash
grep "OPENAI_API_KEY" .env.example
grep -R "OrganizationSerializer" crm/
```

Pipes er nyttige fordi de gjør store tekstmengder håndterbare, men jeg bør forstå hvert ledd før jeg kjører en sammensatt kommando.

## Brukere, sudo og filrettigheter

På Linux er `root` den øverste administratoren. `sudo` kjører en kommando med utvidede rettigheter:

```bash
sudo systemctl restart nginx
```

Dette kan være nødvendig ved godkjent serverarbeid, men `sudo` skal ikke brukes som et automatisk svar på feilen `Permission denied`. Først må jeg forstå hvilken bruker jeg er, hvorfor tilgangen mangler, hva kommandoen endrer og hvordan den kan reverseres.

```bash
ls -la
```

viser blant annet filrettigheter og eier. Profesjonell drift bruker gjerne en avgrenset deploybruker og bare `sudo` når det er nødvendig. Hvis prompten viser `root@server`, skjerper jeg oppmerksomheten.

En rettighetslinje kan begynne slik:

```text
-rw-r--r--  1 deploy deploy  1240 settings.py
```

Jeg trenger ikke kunne tolke alle tegnene med én gang. Det viktige er at Linux skiller mellom hvem som kan lese, skrive og kjøre en fil. En rettighetsfeil må løses for riktig bruker og riktig fil, ikke ved å gi hele kommandoen mer makt enn nødvendig.

## Miljøvariabler og hemmeligheter

En `.env`-fil kan inneholde databaseadresse, API-nøkler og andre hemmelige innstillinger:

```text
DATABASE_URL=...
SECRET_KEY=...
OPENAI_API_KEY=...
```

Filen skal normalt være ignorert av Git. Jeg skriver ikke ut innholdet i delt skjerm, chat eller logger, og legger aldri hemmeligheter direkte i kommandoer hvis de kan havne i historikken.

```bash
history
```

viser tidligere kommandoer. Denne bekvemmeligheten er også grunnen til at passord og API-nøkler må behandles varsomt.

## Terminalen og Docker

Fra prosjektmappen kan jeg kontrollere Docker:

```bash
docker compose ps
docker compose up -d --build
docker compose logs --tail=100
docker compose logs -f
docker compose down
```

Tjenestenavnene kommer fra prosjektets Compose-konfigurasjon. En bestemt logg kan for eksempel følges med:

```bash
docker compose logs -f api
```

Noen kommandoer skal kjøres inne i en container:

```bash
docker compose exec api python manage.py migrate
```

Flyten er da:

```text
Terminal → Docker → API-container → Django → PostgreSQL
```

En Django-kommando direkte på Mac-en kan feile hvis Python og avhengighetene bare finnes i containeren.

Denne kommandoen krever ekstra forsiktighet:

```bash
docker compose down -v
```

`-v` kan slette Docker-volumer og dermed databasedata. Den skal ikke brukes uten at mål, miljø og konsekvens er kontrollert.

## Terminalen og Git

Git-kommandoene kjøres normalt i prosjektmappen, ikke inne i en container:

```bash
git status
git branch --show-current
git fetch
git diff
git add <fil>
git commit
git push
```

Git håndterer prosjektfilenes historie. Docker kjører applikasjonen. Terminalen gir begge ordre, men verktøyene har ulike oppgaver.

## Lokal terminal og serverterminal

Lokalt bruker jeg Terminal til å navigere, kjøre Git, starte Docker, teste og lese logger.

På serveren bruker jeg den til godkjent kontroll av deploy, containere, logger, tjenester, backup og migrasjoner. Jeg utvikler ikke tilfeldig direkte i produksjonsfiler. Manuelle serverendringer kan bli overskrevet ved neste deploy og mangler ofte i Git-historikken.

Etter SSH-innlogging starter jeg med observasjon:

```bash
hostname
pwd
git branch --show-current
git status
docker compose ps
```

Først når riktig maskin, mappe, branch og miljø er bekreftet, vurderer jeg en endrende kommando. Produksjonsterminalen bør gjerne ha tydelig fanenavn eller annen visuell markering slik at den ikke forveksles med lokal eller staging.

### Hold miljøene synlig adskilt

Jeg kan ha flere terminalvinduer åpne samtidig: ett lokalt, ett som følger logger, ett på staging og ett på produksjon. Da øker risikoen for å skrive i feil vindu.

Tydelige fanenavn, ulike bakgrunnsfarger og en prompt som viser servernavnet gjør konteksten synlig. Produksjon bør skille seg tydelig fra lokal utvikling. Før sletting, migrasjon, import, backupgjenoppretting, omstart eller manuell deploy kjører jeg på nytt:

```bash
hostname
pwd
git branch --show-current
```

Noen sekunders orientering er billigere enn å reparere en riktig kommando som ble kjørt i feil miljø.

### En kontrollert lokal økt

En typisk lokal kontroll kan begynne slik:

```bash
cd /sti/til/kreative-norge-crm
hostname
pwd
git branch --show-current
git status
docker compose up -d --build
docker compose ps
docker compose logs --tail=100
```

Deretter åpner jeg løsningen og prøver den konkrete brukerflyten. Jeg bekrefter ikke bare at containerne kjører; jeg kontrollerer at endringen faktisk virker.

### En kontrollert serverøkt

På staging eller produksjon er første del fortsatt en kontroll, ikke en endring:

```bash
ssh deploy@serveradresse
hostname
pwd
cd /sti/til/kreative-norge-crm
git branch --show-current
git status
docker compose ps
```

En manuell deploy kan i noen oppsett omfatte `git pull`, bygging av containere og migrasjoner. De nøyaktige kommandoene og rekkefølgen må alltid hentes fra prosjektets faktiske deployoppsett. Før jeg gjør noe, må jeg kontrollere:

- riktig server og miljø
- riktig prosjektmappe og branch
- riktig Docker Compose-fil
- om Git-arbeidsområdet er rent
- om migrasjoner er nødvendige
- om backup er bekreftet
- om en annen deploy allerede kjører

Jeg kopierer aldri en generell serveroppskrift direkte til produksjon. Hvis en automatisert deploy senere innføres, skal jeg heller ikke starte en konkurrerende manuell deploy samtidig.

## Kommandoer med ulike risikonivåer

Kommandoer som vanligvis leser eller kontrollerer, er blant annet:

```bash
git status
git diff
docker compose ps
docker compose logs
python manage.py check
pytest
npm run build
```

De kan fortsatt bruke ressurser eller vise sensitiv informasjon, men endrer normalt ikke produksjonsdata.

Jeg stopper og kontrollerer ekstra før kommandoer som:

- sletter filer, mapper eller Docker-volumer
- endrer produksjonsdata
- kjører destruktive migrasjoner
- gjenoppretter databasebackup
- tvinger Git-historikk
- endrer serverbrukere, SSH, brannmur eller hemmeligheter
- starter en manuell produksjonsdeploy

Målet er ikke å frykte Terminal eller spørre om hvert lite steg. Målet er stor handlefrihet innenfor tydelige sikkerhetsgrenser.

## Vanlige feilmeldinger

**`No such file or directory`** betyr ofte feil sti, stavemåte, maskin eller manglende anførselstegn. Kjør `pwd` og `ls`.

**`Command not found`** kan bety at programmet ikke er installert, ikke ligger i søkestien `PATH`, at Docker Desktop ikke kjører, eller at kommandoen hører hjemme i en container. Kontroller også at du er på maskinen der verktøyet faktisk er installert.

**`Permission denied`** peker mot bruker- eller filrettigheter. Det kan også skyldes en SSH-nøkkel med feil rettigheter. Ikke legg automatisk til `sudo`.

**`Port is already in use`** betyr at en annen prosess bruker porten. En lokal server eller gammel container kan allerede kjøre. Kontroller først `docker compose ps`.

**`Connection refused`** betyr at en tjeneste ikke svarer. Mulige årsaker er stoppet container, feil port eller vertsnavn, en database som ikke er klar, eller en applikasjon som har krasjet. Undersøk containere og logger:

```bash
docker compose ps
docker compose logs --tail=100
```

**`Disk full`** kan stoppe en server. `df -h` viser diskbruk. Store Docker-images, voksende logger, opplastede filer eller mange backuper kan være årsaken. Finn hva som bruker plassen før noe slettes.

En feilmelding er informasjon, ikke en ordre om å prøve tilfeldige reparasjoner. Jeg samler kontekst først og lar deretter Codex eller en utvikler foreslå en avgrenset handling.

## Takeaways

- Terminalen er et grensesnitt som sender kommandoer til andre systemer.
- Før en viktig kommando kontrollerer jeg maskin, bruker, mappe, branch og miljø.
- SSH gjør at det samme terminalvinduet styrer en annen datamaskin.
- `rm`, `sudo`, `root`, Docker-volumer og produksjonsdata krever ekstra kontroll.
- Git håndterer historie; Docker kjører applikasjonen.
- Hemmeligheter skal ikke inn i repo, logger eller terminalhistorikk.

## Prinsippet

Før jeg gir Terminal en viktig ordre, skal jeg vite hvem jeg er, hvor jeg er, og hvilken maskin som utfører den.
