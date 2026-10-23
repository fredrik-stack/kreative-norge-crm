---
name: gjennomga-siste-endring
description: Kontroller siste commit, branch eller pull request i Kreative Norge CRM mot oppgaven, dokumentasjonen og kvalitetskravene. Bruk etter at Codex har pushet en endring eller når Fredrik ber om kodegjennomgang.
---

# Gjennomgå siste endring

Følg `AGENTS.md` og kontroller den avtalte oppgaven og eventuell ADR før du vurderer diffen.

1. Les mandatet, relevant dokumentasjon og diff. Registrer eksakt base- og head-SHA; konklusjonen gjelder bare dette grunnlaget. En faktisk separat reviewer skal brukes ved leveranse etter workflowen; egenkontroll merkes som egenkontroll.
2. Kontroller funksjonell korrekthet, regresjoner, tester, sikkerhet, personvern, tenant-isolasjon og UX.
3. Kontroller at endringen er avgrenset og ikke introduserer skjult kompleksitet.
4. Kontroller migrasjoner, eksisterende data og rollback ved behov.
5. Kontroller at dokumentasjon og prosjektstatus er oppdatert eller fortsatt korrekt.
6. Ranger funn som kritisk, viktig eller forbedring.
7. Oppgi blokkerende funn, testhull og hvilke kontroller som er lest eller kjørt. Endringer etter review krever relevant ny validering. Gi gjennomføreren et versjonsbundet resultat å lagre i PR-en eller lenket dokument.

Reviewrollen er skrivebeskyttet: ikke endre kode, branch, database eller PR, og ikke rette funn under review. Gjennomføreren retter innen mandatet og innhenter nytt review. Ikke godkjenn bare fordi tester er grønne; vurder om testene dekker den faktiske feilen eller brukerreisen.

## Output

En findings-first gjennomgang med alvorlighetsgrad, fil- og linjereferanser, testhull, dokumentasjonsstatus og klar anbefaling om neste gate.

## Neste anbefalte skill

Returner til gjennomføreren i `$fullfor-til-staging` for autoriserte rettinger eller neste leveransegate. Bruk `$skriv-codex-oppgave` bare når en separat oppgave faktisk trengs.
