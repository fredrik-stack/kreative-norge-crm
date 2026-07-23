---
name: klargjor-produksjonssetting
description: Gjennomfør alle kontroller og forberedelser før produksjonssetting av Kreative Norge CRM, men ikke deploy til produksjon uten uttrykkelig beskjed fra Fredrik.
---

# Klargjør produksjonssetting

1. Kontroller scope, godkjenning og release-notater.
2. Kontroller tester, CI, lokal Docker og staging.
3. Kontroller migrasjoner, backup, rollback og kompatibilitet.
4. Kontroller secrets, konfigurasjon, domener, CORS/CSRF, media og statiske filer.
5. Kontroller permissions, tenant-isolasjon, personvern og offentlig eksponering.
6. Utfør en konkret staging-smoketest av berørte brukerreiser.
7. Lag produksjonssjekkliste og anbefaling: klar / ikke klar.
8. Stopp før produksjonsdeploy og be om uttrykkelig godkjenning.

Ikke tolke «fullfør» eller «deploy» som produksjonssetting med mindre produksjon er eksplisitt nevnt.