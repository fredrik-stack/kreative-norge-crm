---
name: oppdater-prosjektdokumentasjonen
description: Oppdater Markdown-dokumentasjonen i Kreative Norge CRM slik at den fortsatt beskriver faktisk kode, API, dataflyt og prosjektstatus. Bruk etter funksjonelle endringer eller når en gjennomgang eller `$avslutt-arbeidsokt` har identifisert et konkret dokumentasjonsavvik.
---

# Oppdater prosjektdokumentasjonen

Følg `AGENTS.md` og `docs/development/DOCUMENTATION_RULES.md`.

1. Les siste diff/commits og berørte dokumenter.
2. Verifiser mot kode, migrasjoner, API-ruter og tester.
3. Oppdater relevante filer under `docs/architecture/`, `docs/features/`, `docs/status/` og ADR-er ved behov.
4. Skill mellom implementert, delvis implementert, planlagt, historisk og uavklart.
5. Oppdater dato og verifiseringsgrunnlag der formatet bruker dette.
6. Ikke omskriv dokumenter uten grunn.
7. Ikke legg inn secrets eller lokale detaljer.
8. Ikke endre kode, modeller, API eller database som del av dokumentasjonsarbeidet.
9. Returner til `$fullfor-til-staging` for autorisert commit/push/draft PR, separat review, retting og ordinær merge/CI. Dokumentasjons-PR-er følger samme krav som kode-PR-er, men utløser ikke deploy. Ikke avslutt økten bare fordi denne skillen er ferdig.

## Output

Oppdatert dokumentasjon som skiller faktisk status fra plan, samt en liste over endrede dokumenter, kontrollerte dokumenter og eventuelle gjenværende avvik.

## Neste anbefalte skill

Returner til `$fullfor-til-staging` innen gjeldende mandat, med separat `$gjennomga-siste-endring` før merge. Avslutt først ved mandatets sluttpunkt eller reell blokkering.
