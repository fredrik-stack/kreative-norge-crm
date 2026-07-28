# ADR-006: Sesjonsflyt og varig prosjektminne

## Status

Godkjent og implementert i repoets session-workflow. Alle 15 skills er strukturelt validert, og `$fortsett-prosjekt` er runtime-validert i en ny skrivebeskyttet Codex-session.

**Beslutningsdato:** 2026-07-24

## Forhold til eksisterende utviklingssystem

Denne beslutningen viderefører de fire grunnreglene i `AGENTS.md` og arbeidsnivåene i `docs/development/FREDRIK_DEVELOPMENT_SYSTEM.md`.

Session-skills er et ytre lag rundt LEVEL 1–4. `$fortsett-prosjekt` er en kontinuitetsbro inn til session-laget. Ingen av dem er en ny diagnose-, beslutnings-, implementerings- eller kvalitetsfase, og de erstatter ingen eksisterende skill.

## Bakgrunn

Prosjektarbeid skjer på tvers av Codex i VS Code, ChatGPT, lokal Git, GitHub, CI, Docker og staging. Samtaler har begrenset levetid og kan mangle lokale endringer eller nyere commits. De kan derfor ikke være prosjektets varige hukommelse.

Repoets dokumentasjon skal beskrive stabil prosjektkunnskap og faktisk status. Git og GitHub skal bevare endringer, historikk og leveransestatus. En arbeidsøkt trenger likevel en konsekvent oppstart og avslutning som kobler disse sannhetskildene sammen.

Før ADR-006 beskrev workflowen oppstart og avslutning, men hadde ikke gjenbrukbare skills, en fast Git-baseline, standardisert project health eller en identisk handoff mellom økter.

## Beslutning

### 1. GitHub og dokumentasjonen er varig hukommelse

Fakta som skal overleve en samtale, skal lagres i Git eller relevant prosjektdokumentasjon og pushes til GitHub når arbeidsflyten tilsier det.

En samtale, `CHATGPT SESSION SUMMARY` eller `SESSION WRAP-UP` er ikke teknisk fasit. Opplysninger derfra skal verifiseres mot repo, GitHub, runtime eller dokumentasjon i neste økt.

### 2. Et SESSION-lag omkranser arbeidsnivåene

To repo-baserte Codex-skills etableres:

- `$start-arbeidsokt`
- `$avslutt-arbeidsokt`

Flyten er:

```text
SESSION START → LEVEL 1–4 etter behov → SESSION END
```

Session-skills brukes ved utviklings-, planleggings- og kvalitetsøkter som viderefører prosjektarbeid. Enkle, isolerte forklaringer uten prosjektendring trenger ikke full session-flyt.

### 3. `$fortsett-prosjekt` er en felles inngang med ulike roller

I ChatGPT er `$fortsett-prosjekt` en arbeidsrutine som bruker siste `CHATGPT SESSION SUMMARY` til å:

- plassere forrige økt i strategisk og arkitektonisk sammenheng
- kontrollere dokumentert status når tilgang finnes
- skille besluttet, implementert og foreslått
- vurdere tidligere prioritering på nytt
- anbefale neste strategiske prioritet og første Codex-prompt

Rutinen har fast output, men er ikke en teknisk Codex-skill.

I Codex er `.agents/skills/fortsett-prosjekt/` en tynn, skrivebeskyttet bro. Den skal kontrollere et eventuelt ChatGPT-sammendrag mot repoets sannhetskilder, merke konflikter og delegere den komplette tekniske oppstarten til `$start-arbeidsokt`.

Codex-broen skal ikke prioritere produktstrategi, erstatte `$start-arbeidsokt`, endre filer eller starte implementering.

Rollene, ChatGPT-outputen og sammendragsmalen er dokumentert i:

- `docs/development/CHATGPT_SESSION_CONTINUITY.md`
- `docs/development/CHATGPT_SESSION_SUMMARY_TEMPLATE.md`

### 4. Oppstart er skrivebeskyttet

`$start-arbeidsokt` skal:

- sette `DAGENS FOKUS`
- lese styringsdokumenter, status, roadmap og relevante ADR-er
- kontrollere Git-status og aktiv branch
- rapportere `Dirty/Clean`, `Ahead/Behind`, `Open PR` og `Last commit`
- skille implementert, planlagt, besluttet og uavklart
- identifisere risiko og åpne beslutninger
- oppsummere `PROJECT HEALTH`
- foreslå neste oppgave, skill, plan og stoppunkt

Skillen skal ikke endre kode, dokumentasjon eller ekstern tilstand. En annen skill kan overta i samme brukerprompt bare når dette er uttrykkelig bestilt.

### 5. Avslutning er en evidensbasert kontroll

`$avslutt-arbeidsokt` skal verifisere hva som faktisk ble gjort gjennom diff, staged diff, nye filer, commits, upstream og tilgjengelig GitHub-status.

Den skal:

- skille implementert, besluttet og foreslått
- rapportere tester, Docker, branch, commit, push, PR, CI, staging og merge
- liste feil, risiko og uavklarte spørsmål
- kontrollere dokumentasjonsbehov
- oppsummere `PROJECT HEALTH`
- foreslå neste ChatGPT- og Codex-prompt
- levere en standardisert `SESSION WRAP-UP`
- avslutte med en ferdig `Kopier inn i neste Codex-session`-prompt

Før-eksisterende lokale endringer skal ikke tilskrives økten.

### 6. SESSION WRAP-UP har fast kontrakt

Alle avslutningsrapporter skal bruke de samme feltene i samme rekkefølge:

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

Verdiene kan variere, men struktur og rekkefølge skal være identisk.

### 7. Project health bruker verste verifiserte status

`PROJECT HEALTH` skal bygge på tester, CI, dokumentasjon og Git-status:

- 🟢 når alle relevante kontroller er verifisert grønne eller ikke relevante, dokumentasjonen er korrekt og Git-tilstanden passer avtalt stoppunkt
- 🟡 når relevante kontroller er ukjente, ikke kjørt eller pågår, dokumentasjon må oppdateres, eller arbeid bare finnes lokalt/upushet
- 🔴 når påkrevde tester eller CI feiler, dokumentasjonen motsier verifisert løsning, eller Git har konflikt/tilstand som gjør leveransen utrygg

Verste relevante status bestemmer samlet farge. Oppsummeringen skal kort angi årsaken og aldri gjøre manglende bevis grønt.

### 8. Eksisterende skills beholder eierskapet til handlinger

Session-skills og kontinuitetsbroen skal ikke selv:

- diagnostisere en ukjent feil i dybden
- ta produkt- eller arkitekturbeslutninger
- implementere kode
- oppdatere dokumentasjon
- committe, pushe, merge eller deploye

De ruter til eksisterende skill. `$fullfor-til-staging` eier en godkjent leveranse gjennom commit, push og staging. `$oppdater-prosjektdokumentasjonen` eier dokumentasjonssynkronisering. `$skriv-codex-oppgave` eier komplette implementeringsprompter.

## Begrunnelse

Et tydelig kontinuitets- og session-lag gjør hver arbeidsøkt selvkorrigerende: ChatGPT-handoff gir strategisk sammenheng, Codex-broen kontrollerer den mot repoet, oppstart verifiserer sannhetsgrunnlaget, og avslutning viser hva som faktisk er varig lagret. Fast struktur reduserer risikoen for at forslag omtales som beslutninger, at lokale endringer glemmes, eller at en ny samtale må stole på gammel samtalekontekst.

Avgrensningen hindrer samtidig overlapp og uforutsigbar automatikk i Skill Pack.

## Avviste alternativer

### Gjøre session-skills til LEVEL 0 og LEVEL 5

Avvist fordi session-flyten omkranser alle arbeidsnivåer og også kan brukes rundt en ren planleggings- eller kvalitetsøkt.

### Lagre komplette samtalereferater i repoet

Avvist fordi samtalestøy ikke er stabil prosjektkunnskap. Repoet skal lagre beslutninger, status og implementasjon, ikke full dialog.

### La avslutningsskillen automatisk committe og pushe

Avvist fordi avslutningskontroll ikke skal utvide brukerens autorisasjon eller konkurrere med etablerte leveranseskills.

### La hver fag-skill ha sin egen handoff-struktur

Avvist fordi formatet da vil drive fra hverandre og gjøre neste oppstart mindre forutsigbar.

### Gjøre ChatGPT-rutinen og Codex-skillen identiske

Avvist fordi ChatGPT skal vurdere strategisk retning, mens Codex skal verifisere teknisk tilstand. Lik implementasjon ville enten gi Codex uønsket prioriteringsansvar eller gjøre ChatGPT-rutinen for teknisk.

## Konsekvenser

### Positive konsekvenser

- hver økt starter fra verifiserte repo-fakta
- Git- og dokumentasjonsgjeld blir synlig før kontekst går tapt
- handoff mellom ChatGPT, Codex og senere økter blir konsekvent
- strategisk ChatGPT-kontekst kan følge prosjektet uten å bli teknisk sannhetskilde
- eksisterende skills får tydeligere grensesnitt
- forslag, beslutninger og implementasjon blandes sjeldnere

### Kostnader og ulemper

- større arbeidsøkter får to ekstra kontrollpunkter
- åpen PR og CI kan bli `ukjent` uten GitHub-tilgang
- ny eller endret skill oppdages sikkert først i en ny Codex-session
- project health krever nøktern vurdering av hva som faktisk er relevant
- samme navn har ulik rolle i ChatGPT og Codex og må derfor alltid forklares med miljø

## Implementeringsleveranser og akseptansekriterier

### Leveranse 1: beslutnings- og workflowgrunnlag

- ADR-006 dokumenterer beslutningen
- `AGENTS.md` og workflow peker på session-flyten
- SESSION-laget skilles fra LEVEL 1–4

### Leveranse 2: session-skills

- begge skillmapper har gyldig `SKILL.md`
- begge har samsvarende `agents/openai.yaml`
- startskillen har `DAGENS FOKUS` og utvidet `GIT-SNAPSHOT`
- avslutningsskillen har identisk `SESSION WRAP-UP`
- begge bruker samme project-health-regler
- avslutningsskillen ender med kopierbar neste-session-prompt

### Leveranse 3: kontinuitetsbro og ChatGPT-rutine

- Codex-broen `$fortsett-prosjekt` har gyldig `SKILL.md` og `agents/openai.yaml`
- broen kontrollerer sammendraget mot repoet
- broen leder videre til `$start-arbeidsokt`
- broen endrer ikke filer og starter ikke implementering
- ChatGPT-rutinen og den faste sammendragsmalen er dokumentert uten duplisering av stabil teknisk kunnskap

### Leveranse 4: dokumentasjon og katalog

- Skill Pack viser 15 skills, kontinuitetsbroen og SESSION-laget
- eksempler dekker ChatGPT-kontinuitet, Codex-bro, oppstart og avslutning
- roadmap og prosjektstatus skiller implementert fra gjenstående runtime-verifisering
- dokumentlenker og skillnavn er konsistente

### Leveranse 5: validering

- standardvalidatoren godkjenner alle 15 skills
- alle skillmapper har `SKILL.md` og `agents/openai.yaml`
- navn er unike og metadata samsvarer med mappenavn
- alle skills avslutter med `Output` og `Neste anbefalte skill`
- en ny, skrivebeskyttet Codex-session bekrefter eksplisitt aktivering av `$fortsett-prosjekt`
- testen bekrefter at broen ikke endrer filer eller starter implementering
- testen bekrefter at broen leder videre til `$start-arbeidsokt`

## Testkrav

Ingen CRM-, database- eller Docker-test er nødvendig fordi endringen bare berører arbeidsflyt og Markdown.

Struktur, YAML, faste outputfelter, dokumentlenker, sammendragsmal og skilltelling skal kontrolleres maskinelt der det er mulig. Runtime-oppdagelse skal kontrolleres i en ny, skrivebeskyttet Codex-session fordi den aktive sessionen kan ha lastet gammel skillmetadata.

## Rollback

Endringen kan reverseres ved å:

1. fjerne de tre repo-skillmappene som ADR-006 etablerer
2. fjerne kontinuitetsdokumentene
3. reversere henvisningene i `AGENTS.md` og `docs/development/`
4. føre roadmap og prosjektstatus tilbake til forrige verifiserte status
5. markere ADR-006 som erstattet eller reversert

Rollback påvirker ikke CRM-kode, data, API eller runtime.

## Beslutninger som fortsatt krever eksplisitt godkjenning

Ingen. Session-designet, de fem opprinnelige forbedringene og kontinuitetsutvidelsen med `$fortsett-prosjekt` ble uttrykkelig godkjent 2026-07-24.
