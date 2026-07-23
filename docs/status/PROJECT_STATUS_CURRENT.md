# Project Status Current

**Status:** levende dokument

**Sist kartlagt:** 2026-07-23

**Kilde:** kodebase på `main`, aktive API-ruter og siste commit-historikk

## Aktiv utviklingsfase

IMPORT er på et avansert nivå og under kvalitetssikring. Neste hovedområder er videreutvikling av PUBLIC og ferdigstilling av EKSPORT.

## Implementert

- tenant-basert CRM for aktører og personer
- koblinger mellom aktører og personer
- flere kontaktkanaler per person
- kategorier, underkategorier og tenant-spesifikke tags
- roller via `TenantMembership`
- intern React-editor med rollebasert tilgang
- public API for publiserte aktører
- public HTML-visning i staging
- importjobber med opplasting, preview, validering, matching, AI-forslag, review, beslutninger, commit, logg og feilrapport
- grunnmodell og grunn-API for eksportjobber

## Delvis implementert

### EXPORT

`ExportJob`, eksporttyper, formater, filtre, valgte felt og grunnleggende API finnes. Faktisk filgenerering, nedlasting og komplett brukerflyt er ikke bekreftet ferdig.

### PUBLIC

Public API og HTML-visning fungerer. HTML-visningen brukes foreløpig bare i staging. Løsningen er ikke ferdigstilt for ekstern integrasjon med Musikkontoret.no.

## Planlagt senere

- Google Sheets som importkilde
- Checkin som importkilde
- Mailmojo som importkilde
- automatisk deploy til staging ved push

De tre importkildene finnes foreløpig bare som reserverte kildetyper.

## Nåværende prioritering

1. sikre og dokumentere IMPORT
2. videreutvikle PUBLIC
3. bygge ferdig EKSPORT
4. etablere automatisk staging-deploy ved push
5. forbedre testing, audit og sporbarhet

## Uavklart

- nøyaktig omfang av eksisterende eksport-UI
- valgt mekanisme for automatisk staging-deploy
- hvilke tester som skal være obligatoriske før deploy
- endelig kontrakt mellom CRM-public og Musikkontoret.no

## Dokumentasjonsstatus

Ny struktur etableres på branchen `docs/project-workflow-baseline`. Eldre `.md`-filer er foreløpig beholdt og skal kartlegges før eventuell arkivering.