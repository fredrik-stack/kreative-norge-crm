---
name: gjennomga-siste-endring
description: Kontroller siste commit, branch eller pull request i Kreative Norge CRM mot oppgaven, dokumentasjonen og kvalitetskravene. Bruk etter at Codex har pushet en endring eller når Fredrik ber om kodegjennomgang.
---

# Gjennomgå siste endring

Følg `AGENTS.md` og kontroller den avtalte oppgaven og eventuell ADR før du vurderer diffen.

1. Les oppgaven, relevant dokumentasjon og diff.
2. Kontroller funksjonell korrekthet, regresjoner, tester, sikkerhet, personvern, tenant-isolasjon og UX.
3. Kontroller at endringen er avgrenset og ikke introduserer skjult kompleksitet.
4. Kontroller migrasjoner, eksisterende data og rollback ved behov.
5. Kontroller at dokumentasjon og prosjektstatus er oppdatert eller fortsatt korrekt.
6. Ranger funn som kritisk, viktig eller forbedring.
7. Oppgi om endringen er klar for staging, merge eller trenger ny Codex-runde.

Ikke endre kode med mindre brukeren uttrykkelig ber om å rette funnene. Ikke godkjenn bare fordi tester er grønne; vurder om testene dekker den faktiske feilen eller brukerreisen.

## Output

En findings-first gjennomgang med alvorlighetsgrad, fil- og linjereferanser, testhull, dokumentasjonsstatus og klar anbefaling om neste gate.

## Neste anbefalte skill

Bruk `$skriv-codex-oppgave` hvis funn må rettes, `$oppdater-prosjektdokumentasjonen` hvis bare dokumentasjonen gjenstår, eller `$klargjor-produksjonssetting` når leveransen er godkjent.
