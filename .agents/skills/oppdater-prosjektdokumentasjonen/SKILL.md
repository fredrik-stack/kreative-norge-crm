---
name: oppdater-prosjektdokumentasjonen
description: Oppdater Markdown-dokumentasjonen i Kreative Norge CRM slik at den fortsatt beskriver faktisk kode, API, dataflyt og prosjektstatus. Bruk etter funksjonelle endringer eller ved avslutning av en Codex-økt.
---

# Oppdater prosjektdokumentasjonen

Følg `docs/development/DOCUMENTATION_RULES.md`.

1. Les siste diff/commits og berørte dokumenter.
2. Verifiser mot kode, migrasjoner, API-ruter og tester.
3. Oppdater relevante filer under `docs/architecture/`, `docs/features/`, `docs/status/` og ADR-er ved behov.
4. Skill mellom implementert, delvis implementert, planlagt, historisk og uavklart.
5. Oppdater dato og verifiseringsgrunnlag der formatet bruker dette.
6. Ikke omskriv dokumenter uten grunn.
7. Ikke legg inn secrets eller lokale detaljer.
8. Rapporter hvilke dokumenter som ble endret, og hvilke som ble vurdert som fortsatt korrekte.