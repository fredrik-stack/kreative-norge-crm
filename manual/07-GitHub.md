# Kapittel 7 – GitHub: prosjektets felles bankboks og trafikksentral

Git og GitHub omtales ofte som om de er samme verktøy. Git registrerer historikken lokalt på Mac-en. GitHub er nettjenesten som oppbevarer og deler denne historikken med andre maskiner, mennesker og automatiske arbeidsflyter.

I Kreative Norge CRM binder GitHub sammen den lokale prosjektkopien, samarbeidspartnerne og servermiljøene. GitHub kan også bli et kontrollpunkt for testing og deploy, men selve CRM-et kjører ikke der.

## Repo, local og remote

På GitHub ligger prosjektet i et **repository**, vanligvis forkortet til **repo**. Det inneholder kildekode, Git-historikk, branches, commits, dokumentasjon, konfigurasjon og eventuelle automatiske arbeidsflyter.

**Local** er prosjektkopien på Mac-en. Her kan Codex og utviklere lese filer, gjøre endringer, kjøre tester og opprette commits uten at GitHub automatisk endres.

**Remote** er en ekstern Git-kopi. GitHub-repoet er vanligvis prosjektets remote, og forbindelsen har ofte kallenavnet `origin`.

```bash
git remote -v
```

Kommandoen viser hvilke adresser den lokale kopien bruker for å hente og sende historie. Når jeg skriver:

```bash
git push origin main
```

ber jeg Git sende lokale commits fra branchen `main` til GitHub-kopien som heter `origin`. Ofte holder det med `git push` fordi forbindelsen allerede er registrert.

GitHub kan også samle oppgaver, feilrapporter og tekniske diskusjoner gjennom Issues og Pull Requests. En issue beskriver vanligvis et behov eller problem som ennå ikke er løst, mens en PR viser en konkret foreslått kodeendring. Denne forskjellen gjør det mulig å dokumentere hvorfor arbeid trengs før noen begynner å endre filer.

For CRM-et betyr det at beslutningsgrunnlag, kodehistorikk og gjennomgang kan knyttes sammen uten å blandes. Dokumentasjonen i repoet er fortsatt stedet for stabil prosjektkunnskap; en tilfeldig kommentar eller issue erstatter ikke oppdatert dokumentasjon.

## Push, fetch og pull

De tre kommandoene beskriver hvordan lokal Git kommuniserer med GitHub.

```bash
git push
```

**Push** sender nye lokale commits til GitHub. Etterpå finnes historikken begge steder. En push beviser ikke at koden er testet eller deployet.

```bash
git fetch
```

**Fetch** henter informasjon og commits fra GitHub uten å flette dem inn i den aktive arbeidskopien. Det er et forsiktig første steg når jeg vil undersøke hva andre har gjort.

```bash
git pull
```

**Pull** henter endringer og forsøker å legge dem inn i den lokale branchen. Før pull kontrollerer jeg:

```bash
git status
git branch --show-current
```

Uferdige lokale endringer kan kollidere med det som hentes. Hvis situasjonen er uklar, bør Codex eller en utvikler undersøke historikken før noe flettes.

GitHub kan inneholde nyere arbeid når en utvikler har pushet, en Pull Request er slått sammen, eller en annen prosjektkopi har vært i bruk.

## Branches gir parallelle arbeidslinjer

En **branch** er en parallell utviklingslinje. `main` er vanligvis prosjektets godkjente hovedlinje. En større funksjon kan bygges på en sidegren uten å gjøre den til del av `main`.

```text
main
├── feature/import-preview
└── feature/export-xlsx
```

Jeg bruker vanligvis egen branch når arbeidet:

- varer over flere økter
- berører mange filer eller systemlag
- kan bryte eksisterende funksjoner
- inneholder migrasjoner
- trenger kodegjennomgang eller stagingtest
- er et eksperiment som kanskje skal forkastes

Før en ny branch opprettes, må `main` være riktig og oppdatert:

```bash
git switch main
git status
git pull
git switch -c feature/export-xlsx
```

Den siste kommandoen oppretter branchen og flytter arbeidskopien over på den. Første push registrerer koblingen til GitHub:

```bash
git push -u origin feature/export-xlsx
```

Etterpå holder det vanligvis med `git push`.

Direkte arbeid på `main` kan være forsvarlig ved små, isolerte og lett reversible endringer. Det forutsetter fortsatt testing og kontroll av diffen. Siden automatisk deploy fra `main` ennå ikke er verifisert i CRM-prosjektet, skal en push heller ikke omtales som en sikker eller automatisk produksjonssetting.

## Pull Request og merge

En **Pull Request**, forkortet **PR**, er et forslag om å slå én branch sammen med en annen. Koden er allerede pushet til GitHub; navnet betyr ikke at GitHub skal hente den fra Mac-en.

En PR samler:

- filer og linjer som er endret
- commits som inngår
- resultater fra automatiske kontroller
- kommentarer og foreslåtte endringer
- eventuelle konflikter

Dette er nyttig også når jeg arbeider alene. PR-en gir et samlet overblikk, en naturlig pause før sammenslåing og et sted der en utvikler kan gjennomgå endringen.

**Merge** betyr at historien fra én branch kombineres med en annen. Etter at `feature/export-xlsx` er merget til `main`, inneholder hovedlinjen eksportendringen.

En **merge conflict** oppstår når Git ikke sikkert kan kombinere to endringer, for eksempel fordi to personer har redigert samme linje på ulike branches. Git stopper i stedet for å gjette. Da må vi:

1. finne konfliktfilene
2. forstå hensikten med begge endringene
3. velge eller kombinere riktig løsning
4. fjerne konfliktmarkeringene på en kontrollert måte
5. kjøre testene på nytt
6. fullføre merge eller commit

Codex kan hjelpe med den tekniske oppryddingen. Hvis konflikten representerer to forskjellige produktvalg, må prosjekteieren eller utvikleren avgjøre retningen.

### Hvorfor PR er nyttig i CRM-prosjektet

Ved en mellomstor funksjon kan Codex pushe en feature-branch og opprette en PR. Der kan jeg se hele endringen samlet, mens en utvikler kan kommentere konkrete linjer eller stille spørsmål ved arkitekturen. Testresultater og uavklarte kommentarer blir synlige før merge.

En PR dokumenterer ikke bare *hva* som ble endret. Beskrivelsen bør også forklare behovet, hvilke kontroller som er kjørt, om data eller migrasjoner berøres, og hva som fortsatt må testes. Dette gjør historikken forståelig når jeg kommer tilbake til prosjektet senere.

En PR skal ikke brukes som pynt. Hvis endringen er stor eller risikofylt, må noen faktisk lese diffen, vurdere testene og kontrollere at beslutningene fra planen er fulgt.

## GitHub Actions og en mulig deployflyt

GitHub Actions er GitHubs system for automatiske arbeidsflyter. Filer under `.github/workflows/` kan beskrive når en jobb skal starte, hvilken maskin den bruker, og hvilke kommandoer som skal kjøres.

En fremtidig CRM-flyt kan for eksempel:

1. hente riktig commit
2. installere avhengigheter
3. kjøre backend-tester
4. bygge frontend og kjøre typesjekk
5. deploye til staging hvis alt består
6. stoppe og rapportere hvis en kontroll feiler

Dette er en ønsket retning, ikke verifisert nåværende adferd. Endelig branchstrategi, kvalitetsporter, hemmeligheter, servertilgang og tilbakeføring må avklares før automatisk staging-deploy innføres.

GitHub kjører vanligvis ikke selve CRM-et. Tjenesten kan utløse en arbeidsflyt som oppdaterer webserveren, der Docker starter riktig versjon.

## Secrets og adgang til GitHub

Automatiske arbeidsflyter kan trenge serveradresse, SSH-nøkkel, deploytoken eller andre hemmeligheter. Slike verdier skal ikke skrives inn i kodebasen. GitHub Secrets kan gjøre en verdi tilgjengelig for en arbeidsflyt uten å vise den i konfigurasjonsfilen.

Et **Personal Access Token**, ofte kalt PAT, er et digitalt adgangskort til GitHub. Det kan gi et program tillatelse til å lese eller endre bestemte ressurser. Et token bør:

- ha minst mulig tilgang
- begrenses til nødvendige repoer når det er mulig
- ha en fornuftig utløpsdato
- lagres sikkert, for eksempel i macOS Nøkkelring

GitHub har både eldre `classic`-tokens med brede scopes og mer presist avgrensede `fine-grained`-tokens. Velg den smaleste tilgangen integrasjonen faktisk støtter. Når et token utløper, forsvinner ikke prosjektet; bare adgangskortet slutter å virke.

SSH-nøkler er et alternativ for vanlig Git-tilgang. Uansett metode skal hemmeligheten aldri legges i repoet eller limes inn i dokumentasjon og logger.

## GitHub er verken databasebackup eller webserver

GitHub oppbevarer Git-registrerte filer. Den levende PostgreSQL-databasen ligger et annet sted og inneholder blant annet aktører, personer, kontakter, tenantdata og importhistorikk.

Prosjektet trenger derfor ulike sikkerhetsmekanismer:

- **Kode og dokumentasjon:** Git og GitHub.
- **Levende CRM-data:** databasebackup og kontrollert gjenoppretting.
- **Kjørende løsning:** server, Docker og driftsrutiner.

En oppdatert GitHub-kopi kan hjelpe oss å bygge applikasjonen på nytt. Den kan ikke alene gjenopprette CRM-dataene. På samme måte kan GitHub være tilgjengelig mens webserveren er nede, eller serveren kan kjøre en allerede deployet versjon mens GitHub midlertidig er utilgjengelig.

## Samarbeid mellom mennesker og agenter

GitHub gjør arbeidsdelingen synlig. En utvikler kan lese commits, kommentere konkrete linjer, gjennomgå PR-er eller prøve en alternativ løsning på egen branch.

Det samme gjelder når flere Codex-arbeidssteder brukes. To agenter kan arbeide på ulike prosjektkopier eller branches uten automatisk å kjenne hverandres siste endringer. Derfor må hver oppgave angi:

- hvilken prosjektkopi og branch som brukes
- om agenten skal endre eller bare analysere
- hvilke filer eller områder oppgaven omfatter
- hvem som kan skrive til `main`

En trygg regel er én aktiv skriver på `main` om gangen. Andre kan arbeide på egne branches, gjennomgå eller lage avgrensede forslag. Før arbeid kombineres, må alle relevante commits være pushet og forskjellene gjennomgått.

En alternativ teknisk idé kan undersøkes på en tydelig eksperimentbranch, for eksempel:

```text
experiment/node-backend
```

Da kan en utvikler lage en avgrenset prototype uten å rive den fungerende Django-løsningen. Eksperimentet skal ikke merges før målet er definert og vi har vurdert funksjonalitet, migreringskostnad, autentisering, roller, datamodell og drift. GitHub gjør det mulig å bevare forsøket uten å late som om det er vedtatt arkitektur.

### Tre størrelser på GitHub-flyten

Ved en liten endring kan arbeidet skje direkte på riktig branch:

```text
implementer → test → les diff → commit → push → kontroller avtalt miljø
```

Ved en mellomstor endring bruker jeg vanligvis:

```text
oppdater main
→ opprett feature-branch
→ implementer og test
→ lokal Docker-kontroll
→ push branch
→ Pull Request
→ gjennomgang og merge
→ staging og manuell kontroll
```

Ved en stor eller risikofylt endring kommer flere beslutningsporter:

```text
diagnose og spesifikasjon
→ godkjent retning
→ egen branch
→ lokal implementering og testdata
→ Pull Request og automatiske tester
→ menneskelig kodegjennomgang
→ staging
→ beslutning om produksjonssetting
→ kontrollert leveranse og etterkontroll
```

GitHub organiserer flyten, men bestemmer ikke at en endring er klar. Det ansvaret ligger fortsatt hos menneskene.

## En praktisk GitHub-rutine

Før arbeidsøkten:

```bash
git status
git branch --show-current
git fetch
```

Kontroller riktig branch, lokale endringer og om GitHub har nyere historie. Hent eller flett først når situasjonen er forstått.

Under arbeidet:

```bash
git status
git diff
```

Når et avgrenset arbeid er ferdig:

```bash
git add <relevante filer>
git diff --staged
git commit -m "Beskriv endringen tydelig"
git push
```

Ved større arbeid opprettes en PR. Etter godkjent merge oppdateres den lokale hovedbranchen:

```bash
git switch main
git pull
git status
```

## Vanlige GitHub-problemer

**`Everything up-to-date`** betyr at Git ikke har nye lokale commits å sende. Det beviser ikke at alle filer er committet, at koden er testet eller at serveren kjører siste versjon. Kjør `git status`.

**`Authentication failed`** betyr at GitHub avviser legitimasjonen. Tokenet kan være utløpt, tilgangen for smal, kontoen feil eller lagret legitimasjon utdatert.

**`Non-fast-forward`** betyr vanligvis at GitHub har commits som mangler lokalt. Ikke tving gjennom en push. Hent og forstå historikken først.

**`Merge conflict`** betyr at Git ikke kan kombinere endringer sikkert. Undersøk begge versjonene og test løsningen.

**Endringen finnes på GitHub, men ikke på nettsiden** kan skyldes feil branch, manglende eller feilet deploy, mislykket Docker-build, migrasjon som ikke er kjørt eller mellomlagring i nettleseren. Push og vellykket deploy er to forskjellige hendelser.

## Takeaways

- Git lager historikken lokalt; GitHub oppbevarer og deler den.
- Push, fetch og pull flytter historie på ulike måter.
- Branches og Pull Requests gir kontroll før endringer blir del av `main`.
- GitHub Actions kan automatisere tester og deploy, men CRM-flyten er ikke ferdig etablert.
- Kode, levende data og kjørende tjenester trenger ulike sikkerhetsmekanismer.
- Flere mennesker og agenter må ha tydelig arbeidsdeling og branchansvar.

## Prinsippet

GitHub er kontrollpunktet mellom utvikling, samarbeid og levering; `main` skal bare inneholde kode vi er villige til å sette i drift.
