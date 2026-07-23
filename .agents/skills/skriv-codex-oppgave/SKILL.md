---
name: skriv-codex-oppgave
description: Gjør en godkjent beslutning, feilbeskrivelse eller plan om til en kort, komplett og handlingsrettet oppgave for Codex i VS Code. Bruk når Fredrik vil ha neste prompt til Codex uten å gjenta stabil prosjektkontekst.
---

# Skriv Codex-oppgave

Prinsipp: Referer til stabil kunnskap i repoet. Gjenta bare oppgavespesifikk kunnskap.

Prompten skal:

1. be Codex lese `docs/development/WORKFLOW.md` og relevante dokumenter
2. angi fase: diagnose, planlegging, implementering eller gjennomgang
3. beskrive observert problem eller ønsket resultat
4. angi tydelige avgrensninger og hva som ikke skal gjøres
5. definere akseptansekriterier
6. angi nødvendige tester og om lokal Docker kreves
7. angi branch-, commit-, push- og stagingkrav
8. kreve dokumentasjonsoppdatering når funksjonalitet endres
9. kreve sluttrapport etter formatet i workflowen
10. angi stoppunkt dersom godkjenning kreves før neste fase

Hold prompten kort nok til daglig bruk, men komplett nok til at Codex ikke må gjette.