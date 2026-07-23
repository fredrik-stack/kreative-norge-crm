---
name: ta-arkitekturavgjorelse
description: Gjør en godkjent designrapport eller arkitekturanbefaling for Kreative Norge CRM om til en formell ADR, roadmap-etapper og akseptansekriterier uten å implementere kode. Bruk når retningen er faglig utredet og skal besluttes før større implementering.
---

# Ta arkitekturavgjørelse

Følg `AGENTS.md`, `docs/development/WORKFLOW.md` og eksisterende ADR-format. Bruk det godkjente faglige grunnlaget; ikke åpne designfasen på nytt uten at du finner en konflikt med verifiserte fakta.

1. Les designgrunnlaget, status, roadmap, relevante ADR-er og arkitekturdokumenter.
2. Verifiser at beslutningen er nødvendig, avgrenset og konsistent med faktisk system.
3. Dokumenter kontekst, beslutning, alternativer, begrunnelse og konsekvenser.
4. Skill tydelig mellom vedtatt retning og punkter som fortsatt krever eksplisitt godkjenning.
5. Del implementeringen i små, reversible leveranser med akseptansekriterier, testkrav og rollback.
6. Oppdater roadmap og prosjektstatus når planstatus faktisk endres.
7. Kontroller dokumentlenker, ADR-nummerering og at implementert kode ikke omtales som plan.
8. Stopp før kode, modeller, migrasjoner, commit og push med mindre dokumentasjonsoppgaven uttrykkelig omfatter commit og push.

## Output

Ett formelt ADR, oppdatert planstatus ved behov, en trinnvis implementeringsplan med akseptansekriterier og en eksplisitt liste over uavklarte godkjenninger.

## Neste anbefalte skill

Bruk `$skriv-codex-oppgave` når ADR-en og alle nødvendige beslutningsgater er godkjent. Bruk `$grill-med-dokumentasjonen` først dersom ADR-en trenger en kritisk konsistenskontroll.
