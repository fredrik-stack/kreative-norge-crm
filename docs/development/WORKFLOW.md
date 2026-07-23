# Development Workflow

**Status:** Gjeldende grunnarbeidsflyt

**Sist oppdatert:** 2026-07-23

## Roller

### Prosjekteier

- beskriver behov, prioriterer og godkjenner retning
- tester løsningen som bruker i staging
- avgjør når en feature er god nok til å gå videre

### ChatGPT

- leser oppdatert GitHub-repo når prosjekteier ber om det
- hjelper med systemdesign, produktvalg, spesifikasjoner og kvalitetssikring
- skiller mellom implementert, planlagt og uavklart
- oppdaterer eller foreslår strategisk dokumentasjon og ADR-er

ChatGPT følger ikke lokale VS Code-endringer automatisk. Endringer må være pushet til GitHub før repoet kan brukes som fersk sannhetskilde her.

### Codex i VS Code

- leser kodebasen og dokumentasjonen
- implementerer, tester, committer og pusher etter instruks
- oppdaterer relevante dokumenter når funksjonalitet endres
- rapporterer hva som er endret, hvilke tester som er kjørt og hva som gjenstår

### GitHub

- er felles sannhetskilde og historikk
- kobler lokal utvikling, Codex, ChatGPT og senere automatisert deploy

### Lokal Docker og staging

- lokal Docker brukes for risikofylte endringer, databaseendringer, større refaktorering og arbeid som bør verifiseres før push
- staging brukes for helhetlig bruker- og integrasjonstest i servermiljø

## Oppstart av en planleggingsøkt med ChatGPT

Prosjekteier ber ChatGPT:

1. lese `docs/README.md`
2. lese `docs/status/PROJECT_STATUS_CURRENT.md`
3. lese relevant arkitektur- og featuredokument
4. kontrollere nyere kode eller commits ved behov
5. bekrefte dagens faktiske status før nye anbefalinger

## Oppstart av en Codex-økt

Codex skal minst lese:

1. `docs/README.md`
2. `docs/status/PROJECT_STATUS_CURRENT.md`
3. relevant fil i `docs/architecture/`
4. relevant fil i `docs/features/`
5. eksisterende tester og kode som berøres

Deretter skal Codex kort oppsummere forståelsen før større eller risikofylte oppgaver. For små, entydige oppgaver kan den gå direkte til implementering.

## Normal leveransesyklus

1. Prosjekteier og ChatGPT avklarer mål, avgrensning og akseptansekriterier.
2. Spesifikasjonen lagres eller oppdateres i repoet når oppgaven er større.
3. Codex analyserer berørte deler av kodebasen.
4. Codex implementerer i en passende branch eller avtalt arbeidsflyt.
5. Relevante automatiske tester kjøres.
6. Lokal Docker-test gjennomføres når risiko eller omfang tilsier det.
7. Endringen committes og pushes til GitHub.
8. Staging deployes og testes.
9. Dokumentasjon og prosjektstatus oppdateres.
10. Prosjekteier godkjenner eller bestiller oppfølging.

## Når lokal testing bør prioriteres

- modell- og migrasjonsendringer
- permissions, tenant-isolasjon eller autentisering
- import/eksport og masseendring av data
- endringer i serializer- eller API-kontrakter
- større frontend-refaktorering
- bildebehandling eller filhåndtering
- feil som er vanskelige å reversere etter deploy

Små tekst-, stil- og avgrensede UI-endringer kan ofte gå raskere til staging dersom eksisterende tester er grønne og rollback er enkel.

## Avslutning av en Codex-økt

Codex skal oppgi:

- hva som ble implementert
- hvilke filer som ble endret
- hvilke tester som ble kjørt og resultatet
- om lokal Docker ble brukt
- commit og branch
- status for push og staging
- dokumenter som ble oppdatert
- kjente feil eller neste anbefalte steg

## Dokumentasjonsplikt

En funksjonell endring er ikke ferdig før relevant dokumentasjon er oppdatert eller uttrykkelig kontrollert og funnet fortsatt korrekt.

## Automatisk staging-deploy

Målet er automatisk deploy til staging ved push etter at definerte tester har bestått. Dette er ønsket arbeidsflyt, men ikke implementert eller verifisert ennå. Valg av branch, GitHub Actions, secrets, servertilgang, rollback og testgates skal spesifiseres før oppsettet endres.