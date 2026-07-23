---
name: trygg-databaseendring
description: Planlegg, implementer eller gjennomgå sikre endringer i Django-modeller, migrasjoner og eksisterende data i Kreative Norge CRM. Bruk ved nye felt, constraints, datamigrering, importreparasjon eller endring av publiseringsflagg.
---

# Trygg databaseendring

1. Kartlegg nåværende modell, constraints, serializers, admin, import/eksport og API-bruk.
2. Skill schema-migrering fra datamigrering.
3. Vurder null/default, bakoverkompatibilitet, indeks, unikhet og tenant-isolasjon.
4. Beskriv behandling av eksisterende poster og feiltilfeller.
5. Lag tester som dekker gammel og ny data.
6. Kjør migrasjoner og tester lokalt i Docker.
7. Definer backup, rollback og stagingkontroll.
8. Unngå destruktive operasjoner uten uttrykkelig godkjenning.
9. Oppdater data- og arkitekturdokumentasjon.

Rapporter migrasjonsrekkefølge, risiko, kontrollspørringer og tilbakeføringsplan.