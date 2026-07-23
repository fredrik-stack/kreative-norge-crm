---
name: planlegg-ny-funksjon
description: Planlegg en ny funksjon i Kreative Norge CRM uten å kode. Bruk når Fredrik vil utforske, avklare eller spesifisere en feature før implementering, særlig for PUBLIC, IMPORT, EXPORT, roller, bilder eller integrasjoner.
---

# Planlegg ny funksjon

Følg `AGENTS.md`. Les minst `docs/README.md`, `docs/status/PROJECT_STATUS_CURRENT.md`, relevant arkitektur, feature-dokument, ADR-er, kode og tester.

Lag en plan som dekker:

1. brukerbehov og ønsket resultat
2. dagens faktiske løsning
3. avgrensning og ikke-mål
4. åpne beslutninger
5. UX og brukerreise
6. datamodell og API-konsekvenser
7. sikkerhet, personvern og tenant-isolasjon
8. tester og akseptansekriterier
9. migrering av eksisterende data ved behov
10. implementeringsetapper og rollback

Ikke endre kode, modeller, migrasjoner eller dokumentasjon med mindre oppgaven særskilt ber om å lagre designrapporten. Skill tydelig mellom anbefaling, beslutning og uavklart punkt. Vurder alltid om enklere MVP er tilstrekkelig.

## Output

En beslutningsklar designrapport med begrunnede alternativer, tydelig anbefaling, MVP-avgrensning, åpne godkjenninger og trygg implementeringsrekkefølge.

## Neste anbefalte skill

Bruk `$vurder-mvp-eller-overarbeid` hvis omfanget fortsatt er usikkert. Når designen er godkjent, bruk `$ta-arkitekturavgjorelse`.
