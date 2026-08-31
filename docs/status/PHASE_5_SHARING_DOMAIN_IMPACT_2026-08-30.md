# Phase 5 sharing-domain impact – 2026-08-30

**Status:** Skrivebeskyttet planleggingsgrunnlag; ingen data- eller runtimeendring

**Source main:** `8c71c49e2696f61e58ed201fa7fa6a6368ade865`

**Verifisert stagingcommit:** `95627bef44275b16a211fe0e529b5a0366051701`

## Formål og metode

Dette er den korte, varige og PII-frie evidensen fra fase 5As read-only
konsekvenskartlegging. Kartleggingen sammenholdt aktiv modell-/migrasjonsstruktur
med aggregerte stagingtellinger. Den endret ikke schema, data, filer, runtime
eller stagingkonfigurasjon. Tellingene er et beslutningsgrunnlag på de oppgitte
commitene, ikke en kontinuerlig produksjonsmåling.

## Faktisk tenant- og datagrunnlag

Staging inneholdt alle sju tenants i det planlagte `Musikkontoret`-domainet:

| ID | Tenant | Organization | Person | OrganizationPerson | E-postkontakter | Telefonkontakter | Publiserte aktører | Publiserte personlenker | ImportJob | ImportRow | Tag |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Musikkontoret Nord | 121 | 147 | 163 | 155 | 51 | 115 | 158 | 38 | 927 | 43 |
| 2 | Musikkontoret MØST | 3 | 4 | 7 | 4 | 0 | 3 | 7 | 0 | 0 | 7 |
| 3 | Musikkontoret Brak | 4 | 6 | 6 | 7 | 6 | 4 | 6 | 15 | 577 | 10 |
| 6 | Musikkontoret ØKS | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 7 | Musikkontoret SØRF | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 8 | Musikkontoret STAR | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 9 | Musikkontoret Tempo | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
|  | **Sum** | **128** | **157** | **176** | **166** | **57** | **122** | **171** | **53** | **1504** | **60** |

Fire tenants var tomme. Bildegrunnlaget lå i Musikkontoret Nord og omfattet 10
assets, 13 rendition-sett, 39 renditions, 11 selections hvorav 8 aktive, og 4
releases.

## Identitet og integritet

Kartleggingen observerte ingen cross-tenant-dublettgrupper etter:

- organisasjonsnummer
- normalisert aktørnavn
- aktørnavn pluss domene
- e-post
- canonical telefon
- personnavn pluss aktør
- personnavn pluss sted

Resultatet reduserer migreringsrisikoen i dette datasettet, men er ikke en
framtidig unikhetsgaranti. Én canonical telefon ble brukt av to personer innen
samme tenant. Telefon er derfor et matchsignal og aldri selvstendig
personidentitet, i tråd med ADR-010.

Det ble observert null tenantmismatches i de kontrollerte bilde-, selection-,
release- og øvrige relasjonsscopene. Dette støtter additiv backfill fra legacy
tenant, men historisk image state kan fortsatt ikke reassosieres eller omskrives.

## Tilgang og storage

Staging hadde ingen `TenantMembership`-rader og to aktive plattform-superusers.
Dagens globale Django-gruppefallback er derfor ikke et tilstrekkelig grunnlag
for framtidig shared tilgang og må fjernes eller begrenses før shared
capabilities aktiveres.

Det fantes 53 ImportJob-filreferanser, men 0 av de 53 kildefilene var tilgjengelige
i default storage. Én feilrapportreferanse pekte også på 0 tilgjengelige filer.
Persistent import storage, rapporter, proveniens, backup/restore, retensjon og
database–fil-konsistens er derfor en hard framtidig gate før Import 2.0 kan
aktiveres. Gaten er ikke implementert av ADR-011.

## Anbefalt strategi

Direkte canonicalisering med additiv overgang er anbefalt:

- eksisterende Organization- og Person-rader og PK-er beholdes
- SharingDomain og assignments legges til additivt
- hvert objekt får først én assignment fra legacy tenant
- legacy- og assignmentlesing sammenlignes i shadow mode
- private overlays flyttes før delt canonical read/write aktiveres
- PUBLIC, image-home, contacts/relations og import kuttes over i separate porter

Det trengs ingen permanent canonical hubmodell for det observerte datasettet.

## Prosjekteiers presiseringer av kartleggingsanbefalingene

- PersonPlace skal være del av målmodellen gjennom senere ADR-012, ikke utsettes
  på ubestemt tid. PersonPlace er uten Google-, koordinat- eller kartkrav, og
  personer skal ikke få kartmarkører eller PUBLIC-kartprojeksjon.
- Shared editorial tags innen SharingDomain er nødvendig. Dagens tenanttags må
  klassifiseres ved policy eller redaksjonell review; private internal tags blir
  tenantoverlays.
- `Organization.email` er offisiell shared aktøre-post og følger canonical
  aktørs PUBLIC-state. Personlig e-post skal ikke ligge i dette feltet.
- Canonical core har ingen redaksjonell home tenant. Hver canonical Organization
  har nøyaktig én aktiv image-home-assignment; den er bare framtidig
  private-write-scope og reassosierer aldri historisk image state.
- MUSIKKONTORET AS er juridisk behandlingsansvarlig for CRM-behandlingen og det
  felles SharingDomainet. Fredrik Forssman er produkteier, faglig ansvarlig og
  operativ kontaktperson, ikke juridisk behandlingsansvarlig.

## Åpne eksterne porter

- endelig ordlyd og versjonering av avtalen for tilgang til delte CRM-data
- nødvendige oppdateringer i personvernerklæringen
- dokumentasjon av behandlingsgrunnlag, formål, rettigheter og interne
  ansvars-/arbeidsrutiner
- juridisk kontroll før delte persondata aktiveres i produksjon
- ADR-012 for Place, PersonPlace, OrganizationPlace og actor-only maps
- redaksjonell policy for legacytags
- deletion-/CASCADE-hardening og fjerning av global rollefallback
- persistent import storage med backup/restore og retensjon
- browser-aktiv Codex før senere Import 2.0- og kart-UI

Den formelle målarkitekturen og migreringsrekkefølgen finnes i
[ADR-011](../decisions/ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md).
