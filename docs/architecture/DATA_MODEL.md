# Data Model

**Status:** første kodebaserte oversikt

## CRM-kjerne

- `Tenant`
- `Organization`
- `Person`
- `OrganizationPerson`
- `PersonContact`
- `Category`
- `Subcategory`
- `Tag`

## Tilgang

- `TenantMembership`

Roller:

- superadmin
- gruppeadmin
- redigerer
- leser

## Import

- `ImportJob`
- `ImportRow`
- `ImportDecision`
- `ImportCommitLog`

## Eksport

- `ExportJob`

## Implementert kontaktregel

`Person.email` og `Person.phone` beholdes foreløpig som interne kompatibilitetsfelt.

Synkroniseringsregelen er:

- når en person lagres med `Person.email`, skal det finnes en primær `PersonContact` med `type=EMAIL`, samme verdi, `is_primary=True` og privat standard ved ny oppretting
- når en person lagres med `Person.phone`, gjelder tilsvarende for `type=PHONE`
- når en eksisterende primær kontakt oppdateres, speiles verdien tilbake til `Person.email` eller `Person.phone`
- eksisterende `PersonContact.is_public` bevares ved vanlig oppdatering med mindre bruker eller import eksplisitt endrer publiseringsvalget
- ingen eksisterende kontakt slettes automatisk av denne synkroniseringen

`repair_person_contacts` kan kjøres som dry-run eller med `--apply` for å opprette manglende private primære e-postkontakter fra `Person.email`.

## Planlagt kontaktarkitektur

`ADR-005` er godkjent som langsiktig målarkitektur. Mellomleveransen fra 2026-07-25 bruker fortsatt global `PersonContact.is_public`; relasjonsspesifikk publisering er ikke implementert.

Planlagt retning:

- `PersonContact` blir eneste autoritative kilde for personers e-post og telefon
- direkte `Person.email` og `Person.phone` fases ut
- primærkontakt er et internt valg og medfører ikke publisering
- konkrete kontaktkanaler publiseres per `OrganizationPerson` gjennom en ny relasjonsmodell
- overgangen gjennomføres additivt med backfill, review og rollback

Dagens modeller og migrasjoner følger fortsatt den todelte legacy-modellen, men nye skriveruter holder primære kompatibilitetsfelt og `PersonContact` synkronisert.

Denne filen skal i neste dokumentasjonsfase utvides med felter, constraints og relasjoner direkte fra `crm/models.py` og migrasjonene.
