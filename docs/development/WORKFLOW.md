# Development Workflow

**Status:** Gjeldende grunnarbeidsflyt

**Sist oppdatert:** 2026-07-23

## Fredrik Development System

Denne arbeidsflyten inngår i `FREDRIK_DEVELOPMENT_SYSTEM.md`. Repoets fire grunnregler lastes fra `AGENTS.md`, og de gjenbrukbare Codex-arbeidsflytene ligger i `.agents/skills/`.

1. Ingen større implementering uten godkjent ADR.
2. Ingen funksjon er ferdig før dokumentasjonen er oppdatert eller kontrollert.
3. Stabil prosjektkunnskap skal ligge i `docs/`, ikke gjentas i prompts.
4. Diagnose → beslutning → implementering.

Se `FREDRIK_SKILL_PACK.md` for valg og verifisering av skills, og `EXAMPLES.md` for praktiske CRM-eksempler.

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

Start Codex fra repo-roten eller en undermappe i repoet. Da oppdager Codex `AGENTS.md` og prosjektets `.agents/skills/`.

Codex skal minst lese:

1. `docs/README.md`
2. `docs/status/PROJECT_STATUS_CURRENT.md`
3. relevant fil i `docs/architecture/`
4. relevant fil i `docs/features/`
5. eksisterende tester og kode som berøres

Deretter skal Codex kort oppsummere forståelsen før større eller risikofylte oppgaver. For små, entydige oppgaver kan den gå direkte til implementering.

Bruk `$skill-navn` når arbeidsfasen skal være entydig. Skills kan også aktiveres implisitt, men eksplisitt valg er tryggest ved diagnose-, beslutnings- og release-gater.

## Normal leveransesyklus

1. Prosjekteier og ChatGPT avklarer mål, avgrensning og akseptansekriterier.
2. Ukjente feil diagnostiseres før retting.
3. Større retning designes og godkjennes i et ADR før implementering.
4. Spesifikasjonen lagres eller oppdateres i repoet når oppgaven er større.
5. Codex analyserer berørte deler av kodebasen.
6. Codex implementerer i en passende branch eller avtalt arbeidsflyt.
7. Relevante automatiske tester kjøres.
8. Lokal Docker-test gjennomføres når risiko eller omfang tilsier det.
9. Endringen committes og pushes til GitHub.
10. Staging deployes og testes.
11. Dokumentasjon og prosjektstatus oppdateres eller kontrolleres.
12. Prosjekteier godkjenner eller bestiller oppfølging.

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
