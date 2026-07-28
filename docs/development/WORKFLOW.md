# Development Workflow

**Status:** Gjeldende grunnarbeidsflyt

**Sist oppdatert:** 2026-07-24

## Fredrik Development System

Denne arbeidsflyten inngår i `FREDRIK_DEVELOPMENT_SYSTEM.md`. Repoets fire grunnregler lastes fra `AGENTS.md`, og de gjenbrukbare Codex-arbeidsflytene ligger i `.agents/skills/`.

1. Ingen større implementering uten godkjent ADR.
2. Ingen funksjon er ferdig før dokumentasjonen er oppdatert eller kontrollert.
3. Stabil prosjektkunnskap skal ligge i `docs/`, ikke gjentas i prompts.
4. Diagnose → beslutning → implementering.

Se `FREDRIK_SKILL_PACK.md` for valg og verifisering av skills, `EXAMPLES.md` for praktiske CRM-eksempler og `../decisions/ADR-006-SESSION_WORKFLOW.md` for session-kontrakten.

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
- bruker `$fortsett-prosjekt` som strategisk kontinuitetsrutine i nye samtaler

ChatGPT følger ikke lokale VS Code-endringer automatisk. Endringer må være pushet til GitHub før repoet kan brukes som fersk sannhetskilde her.

### Codex i VS Code

- leser kodebasen og dokumentasjonen
- implementerer, tester, committer og pusher etter instruks
- oppdaterer relevante dokumenter når funksjonalitet endres
- rapporterer hva som er endret, hvilke tester som er kjørt og hva som gjenstår
- bruker repo-skillen `$fortsett-prosjekt` bare som bro fra ChatGPT-handoff til `$start-arbeidsokt`

### GitHub

- er felles sannhetskilde og historikk
- kobler lokal utvikling, Codex, ChatGPT og senere automatisert deploy

### Lokal Docker og staging

- lokal Docker brukes for risikofylte endringer, databaseendringer, større refaktorering og arbeid som bør verifiseres før push
- staging brukes for helhetlig bruker- og integrasjonstest i servermiljø

## Oppstart av en planleggingsøkt med ChatGPT

Ved ny ChatGPT-samtale kan prosjekteier lime inn `$fortsett-prosjekt` og siste `CHATGPT SESSION SUMMARY`. ChatGPT skal:

1. lese `docs/README.md` og `docs/status/PROJECT_STATUS_CURRENT.md` når repo-tilgang finnes
2. lese roadmap, relevante ADR-er og relevant arkitektur-/featuredokumentasjon
3. kontrollere nyere kode eller commits ved behov
4. skille besluttet, implementert og foreslått
5. vurdere om forrige prioritering fortsatt er riktig
6. levere fast output og en konkret første Codex-prompt

Rutinen og outputkontrakten finnes i `CHATGPT_SESSION_CONTINUITY.md`.

## Avslutning av en ChatGPT-økt

ChatGPT skal fylle ut `CHATGPT_SESSION_SUMMARY_TEMPLATE.md` med øktspesifikk strategisk kontekst og status for varig lagring. Stabil teknisk informasjon skal refereres til i repoet, ikke kopieres inn i malen.

Sammendraget er en håndoff, ikke teknisk fasit. Godkjente beslutninger og faktisk status skal fortsatt lagres i ADR, roadmap, prosjektstatus eller GitHub gjennom riktig arbeidsflyt.

## Oppstart av en Codex-økt

Start Codex fra repo-roten eller en undermappe i repoet. Da oppdager Codex `AGENTS.md` og prosjektets `.agents/skills/`.

Når en `CHATGPT SESSION SUMMARY` følger med, kan `$fortsett-prosjekt` brukes som første Codex-inngang. Broskillen kontrollerer sammendraget mot repoet, merker konflikter og delegerer deretter den komplette tekniske baseline til `$start-arbeidsokt`. Uten sammendrag brukes `$start-arbeidsokt` direkte.

Bruk `$start-arbeidsokt` ved økter som viderefører utvikling, planlegging eller kvalitetssikring. Skillen skal minst lese eller kontrollere:

1. `docs/README.md`
2. `docs/status/PROJECT_STATUS_CURRENT.md`
3. `docs/status/ROADMAP.md`
4. relevante ADR-er
5. relevant fil i `docs/architecture/` og `docs/features/`
6. Git-status, branch, upstream og siste commit

Oppstartsrapporten bruker fast rekkefølge:

1. `DAGENS FOKUS`
2. `VERIFISERT UTGANGSPUNKT`
3. `GIT-SNAPSHOT` med `Dirty/Clean`, `Branch`, `Ahead/Behind`, `Open PR` og `Last commit`
4. `NÅSITUASJON`
5. `ÅPNE BESLUTNINGER OG RISIKO`
6. `PROJECT HEALTH`
7. `ANBEFALT NESTE OPPGAVE`
8. `ANBEFALT SKILL`
9. `ARBEIDSPLAN`

Oppstarten er skrivebeskyttet. Hvis samme prompt uttrykkelig bestiller videre arbeid med en navngitt skill, kan den skillen overta etter at oppstartsrapporten er levert.

For små, isolerte forklaringer uten prosjektendring er full session-flyt valgfri. Bruk ellers `$skill-navn` når arbeidsfasen skal være entydig. Eksplisitt valg er tryggest ved diagnose-, beslutnings- og release-gater.

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

Bruk `$avslutt-arbeidsokt` før arbeidet overleveres eller sessionen avsluttes. Avslutningen skal kontrollere Git-diff, commits, upstream og tilgjengelig GitHub-status og skille mellom:

- **implementert:** finnes i diff eller commit
- **besluttet:** er uttrykkelig godkjent, med status for varig lagring
- **foreslått:** er ikke godkjent eller implementert

Tester, Docker, branch, commit, push, PR, CI, staging og merge rapporteres som `verifisert`, `ikke kjørt`, `ikke relevant` eller `ukjent`. Før-eksisterende lokale endringer skal ikke tilskrives økten.

### PROJECT HEALTH

Project health bygger på tester, CI, dokumentasjon og Git-status. Verste relevante status bestemmer samlet farge:

- 🟢 alle relevante kontroller er verifisert grønne eller ikke relevante, dokumentasjonen er korrekt, og Git-tilstanden passer avtalt stoppunkt
- 🟡 relevante kontroller er ukjente, ikke kjørt eller pågår, dokumentasjon må oppdateres, eller arbeid finnes bare lokalt/upushet
- 🔴 påkrevde tester eller CI feiler, dokumentasjonen motsier verifisert løsning, eller Git har konflikt/tilstand som gjør leveransen utrygg

Manglende bevis skal aldri vurderes som grønt. Oppsummeringen skal være kort og oppgi årsaken.

### Fast SESSION WRAP-UP

Avslutningen skal alltid bruke nøyaktig disse feltene i denne rekkefølgen:

```text
SESSION WRAP-UP
Dato:
Dagens fokus:
Faktisk utført:
Implementert:
Besluttet:
Foreslått, ikke besluttet:
Git:
  Branch:
  Last commit:
  Dirty/Clean:
  Ahead/Behind:
  Push:
  Open PR:
Verifisering:
  Tester:
  Docker:
  CI:
  Staging:
  Merge:
Dokumentasjon:
Åpne feil, risiko og spørsmål:
Neste oppgave:
Neste skill:
Varig lagret:
```

Avslutningen skal i tillegg foreslå neste ChatGPT-prompt og neste Codex-prompt. Siste seksjon skal være `Kopier inn i neste Codex-session` med en ferdig prompt som starter `$start-arbeidsokt`, angir dagens neste fokus og navngir anbefalt videre skill.

Avslutningsskillen endrer ikke filer og committer, pusher, merger eller deployer ikke. Slike handlinger skal allerede være gjennomført av riktig leveranseskill eller bestilles uttrykkelig i en separat arbeidsfase.

## Dokumentasjonsplikt

En funksjonell endring er ikke ferdig før relevant dokumentasjon er oppdatert eller uttrykkelig kontrollert og funnet fortsatt korrekt.

## Automatisk staging-deploy

Målet er automatisk deploy til staging ved push etter at definerte tester har bestått. Dette er ønsket arbeidsflyt, men ikke implementert eller verifisert ennå. Valg av branch, GitHub Actions, secrets, servertilgang, rollback og testgates skal spesifiseres før oppsettet endres.
