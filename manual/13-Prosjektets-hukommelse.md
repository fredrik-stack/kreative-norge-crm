# Kapittel 13 – Prosjektets hukommelse

Etter noen måneder med utvikling oppdaget jeg et paradoks: Koden ble stadig bedre, men prosjektet ble vanskeligere å huske. Hver ny arbeidsøkt begynte med de samme forklaringene om hva CRM-et skulle gjøre, hvordan delene hang sammen, og hva som faktisk var ferdig.

Da forstod jeg at et programvareprosjekt består av to produkter: selve programvaren og kunnskapen om programvaren. Koden lagrer det første. Det andre må skrives ned. Git husker hvordan filene endres; dokumentasjonen husker hva delene betyr og hvorfor valgene ble tatt.

## Dokumentene har ulike oppgaver

God dokumentasjon er ikke én stor tekst. Den består av flere kilder med tydelige roller:

- `README` er inngangsdøren. Den forklarer kort hva prosjektet er, hvordan det startes, og hvor resten av dokumentasjonen finnes.
- Status og roadmap (veikart) skiller mellom implementert, delvis implementert, planlagt og uavklart arbeid.
- Arkitekturdokumenter viser hvordan frontend, backend, database, API-er, Docker, autentisering og integrasjoner henger sammen.
- Featuredokumenter beskriver produktkrav og ønsket brukeropplevelse.
- En ADR, eller *Architecture Decision Record*, dokumenterer et viktig valg, begrunnelsen og konsekvensene.
- Arbeidsflyten beskriver hvordan vi planlegger, implementerer, tester, committer og deployer.

Dette skillet gjør det lettere å finne riktig svar. Et arkitekturdokument skal for eksempel ikke late som en planlagt funksjon allerede er bygget, og et roadmap skal ikke brukes som teknisk fasit.

Når kilder er uenige, trenger prosjektet et kildehierarki. I Kreative Norge CRM gjelder normalt kode og migrasjoner først, deretter aktive API-ruter, verifisert oppførsel i staging, nyere commit-historikk og til slutt dokumentasjonen. Dokumentasjonen skal oppdateres når den ikke lenger beskriver virkeligheten.

## Dokumentasjon for mennesker og AI

Tidligere tenkte jeg på dokumentasjon som noe mennesker kunne lese ved behov. I et AI-assistert prosjekt er den også arbeidsgrunnlag for Codex. Stabil prosjektkunnskap skal derfor ligge i repoet, ikke gjentas i lange prompter.

Det betyr ikke at AI automatisk forstår prosjektet. Den må få tydelige kilder og vite hva som er gjeldende. Ellers kan den bygge videre på en gammel plan eller omtale et mål som implementert.

Arbeidsinstruksjoner hører hjemme et annet sted enn prosjektfakta. I Kreative Norge CRM ligger de varige grunnreglene i `AGENTS.md`, mens gjentatte arbeidsflyter ligger som Skills. En Skill er en kort oppskrift for en bestemt type oppgave, for eksempel å undersøke en feil, planlegge en funksjon eller gjennomføre en trygg databaseendring.

Dokumentasjonen beskriver altså *hva prosjektet er*. Skills beskriver *hvordan arbeidet skal utføres*.

## Eksempel fra Kreative Norge CRM

CRM-et består av Django, React, TypeScript, PostgreSQL, Docker og flere eksterne tjenester. Koden viser detaljene, men ikke nødvendigvis hele hensikten eller statusen.

En ny arbeidsøkt bør derfor starte i `docs/README.md` og den gjeldende prosjektstatusen. Derfra går jeg til relevant arkitektur, feature og ADR. Skal jeg arbeide med PUBLIC, må jeg for eksempel kunne se både dagens API og staging-visning, den godkjente kontaktarkitekturen og hva som ennå ikke er implementert.

Denne strukturen gjør det mulig å komme tilbake etter en pause uten å rekonstruere prosjektet fra hukommelsen. Den hjelper også AI med å skille mellom kode som finnes, beslutninger som er godkjent, og arbeid som bare er planlagt.

## Vanlige feil

Den største feilen er å vente med dokumentasjonen til prosjektet er ferdig. Da er begrunnelsene bak viktige valg ofte glemt. Andre vanlige feil er å skrive for teknisk, lagre samme sannhet flere steder eller la gamle dokumenter stå uten statusmerking.

Dokumentasjon kan også bli en risiko dersom den inneholder passord, API-nøkler eller andre hemmeligheter. Slike opplysninger skal aldri lagres i prosjektets kunnskapsbase.

## Takeaways

- Programvaren og kunnskapen om programvaren må vedlikeholdes sammen.
- Hvert dokument trenger en tydelig rolle og status.
- Kode og verifisert oppførsel veier tyngre enn foreldet dokumentasjon.
- Stabil prosjektkunnskap skal ligge i repoet, ikke i hukommelsen eller gjentatte prompter.
- Skills standardiserer arbeidsmåten, men erstatter ikke dokumentasjon.

## Prinsippet

God kode får systemet til å virke. Oppdatert dokumentasjon gjør at mennesker og AI forstår hvorfor det virker, og hva som fortsatt gjenstår.
