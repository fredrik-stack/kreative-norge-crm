# Documentation Rules

## Kildehierarki

Ved konflikt gjelder normalt denne rekkefølgen:

1. kode og migrasjoner
2. aktive API-ruter
3. verifisert adferd i staging
4. nyere commit-historikk
5. eksisterende dokumentasjon

## Statusmerking

Dokumenter skal skille mellom:

- implementert
- delvis implementert
- planlagt
- historisk
- uavklart

## Ferdigkriterium

En større feature er ikke ferdig før:

- kode og tester er kontrollert
- staging er verifisert når relevant
- arkitekturdokumentasjon er oppdatert
- featuredokumentasjon er oppdatert
- `status/PROJECT_STATUS_CURRENT.md` er oppdatert
- større brukerendringer er registrert i changelog

## Sikkerhet

Dokumentasjonen skal ikke inneholde passord, API-nøkler, private tokens eller andre secrets.

## Eldre dokumenter

Gamle dokumenter skal ikke slettes før innholdet er kontrollert, flyttet eller uttrykkelig merket som historisk.