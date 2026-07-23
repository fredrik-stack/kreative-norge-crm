---
name: fullfor-til-staging
description: Gjennomfør en godkjent endring i Kreative Norge CRM fra implementering til test, commit, push, staging og kontroll uten unødvendige spørsmål. Bruk når retning og akseptansekriterier allerede er avklart.
---

# Fullfør til staging

Følg `AGENTS.md`, `docs/development/WORKFLOW.md` og gjeldende godkjente beslutning. Stopp hvis en større implementering mangler godkjent ADR.

1. Les relevant dokumentasjon, kode og tester.
2. Implementer minste robuste løsning.
3. Kjør relevante tester.
4. Bruk lokal Docker ved database-, API-, permission-, import/eksport-, fil- eller større frontendendringer.
5. Oppdater dokumentasjon.
6. Commit og push på passende branch.
7. Deploy til staging dersom tilgang og gjeldende workflow støtter det.
8. Kontroller brukerflyten i staging.
9. Kontroller at dokumentasjonen er oppdatert eller uttrykkelig vurdert som fortsatt korrekt.
10. Rapporter filer, tester, Docker, commit, branch, push, staging, docs og kjente problemer.

Ikke produksjonssett. Ikke gjør destruktive eller irreversible databaseoperasjoner uten uttrykkelig beskjed.

## Output

En avgrenset leveranse på staging med implementering, tester, dokumentasjon, commit, push, verifisering og kjente avvik rapportert.

## Neste anbefalte skill

Bruk `$gjennomga-siste-endring` for en uavhengig kvalitetskontroll før eventuell produksjonsforberedelse.
