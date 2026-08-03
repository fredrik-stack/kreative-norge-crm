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

`repair_person_contacts` kan kjøres som dry-run eller med `--apply` for å opprette manglende private primære kontakter fra kompatibilitetsfeltene:

- standard uten `--contact-type` er fortsatt `EMAIL`, slik at eksisterende bruk er bakoverkompatibel
- `--contact-type PHONE` skanner `Person.phone`
- `--tenant <id-eller-slug>` avgrenser kjøringen til én tenant
- nye kontakter opprettes med `is_primary=True` og `is_public=False`
- kandidater og konflikter rapporteres med interne person-/tenant-ID-er, men uten rå kontaktverdier
- verdiavvik, matchende ikke-primær kontakt og flere primærkontakter endres ikke automatisk
- kommandoen endrer ikke eksisterende kontaktposter eller publiseringsflagg

Dry-run er standard. `--apply` skal først brukes etter kontroll av en entydig dry-run og nødvendig backup i miljøet det gjelder.

## Planlagt kontaktarkitektur

`ADR-005` er godkjent som langsiktig målarkitektur. Mellomleveransen fra 2026-07-25 bruker fortsatt global `PersonContact.is_public`; relasjonsspesifikk publisering er ikke implementert.

Planlagt retning:

- `PersonContact` blir eneste autoritative kilde for personers e-post og telefon
- direkte `Person.email` og `Person.phone` fases ut
- primærkontakt er et internt valg og medfører ikke publisering
- konkrete kontaktkanaler publiseres per `OrganizationPerson` gjennom en ny relasjonsmodell
- overgangen gjennomføres additivt med backfill, review og rollback

Dagens modeller og migrasjoner følger fortsatt den todelte legacy-modellen, men nye skriveruter holder primære kompatibilitetsfelt og `PersonContact` synkronisert.

## Additiv bildedomenemodell og planlagt bildearkitektur

[ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) er godkjent som arkitekturgrunnlag. Den additive schema-grunnmuren er implementert i `crm` med vanlige heltallsnøkler:

- `ImageAsset` eies av én tenant og lagrer en provider-nøytral privat storage key, SHA-256, faktisk JPEG-/PNG-/WebP-format og MIME-type, dimensjoner, filstørrelse og valideringsversjon
- `ImageRenditionSet` eies av én tenant, beskytter referansen til ett asset og lagrer cover/contain, normalisert fokuspunkt, prosesseringsversjon og render-config-hash
- `ImageRendition` eies av én tenant, beskytter referansen til ett rendition-sett og lagrer square/landscape/share, outputformat, dimensjoner, filstørrelse, SHA-256 og provider-nøytral artifact key
- `OrganizationImageSelection` representerer én låst historisk revisjon for én organisasjon og peker enten til nøyaktig ett immutable rendition-sett eller til systemfallback
- `ImageReviewEvent` lagrer append-only snapshots av første selection-låsing eller eksplisitt replacement, med nullable `SET_NULL`-referanser til levende domeneobjekter

Databaseconstraints håndhever positive dimensjoner og filstørrelser, fokus i intervallet 0–1 og tenant-avgrenset unikhet for storage keys, rendition-sett og varianter. Checksum er bevisst ikke globalt unik. `clean()` avviser tenant-mismatch mellom asset og rendition-sett og mellom rendition-sett og rendition, men dette er ikke alene en full databasegaranti; en senere domenetjeneste skal håndheve samme invariant før runtime kan skrive.

For selection håndhever databasen unik revisjon per tenant/organisasjon, maksimalt én `active`-rad, positiv revisjon, ikke-tom alt-tekst og eksklusivt valg mellom asset/rendition-sett og systemfallback. `locked_by` og `locked_at` er obligatoriske, og bruker samt rendition-sett er beskyttet med `PROTECT`. Selection dupliserer ikke asset, fit, fokus eller prosesseringsversjon; asset og presentasjonsoppskrift nås gjennom det eksakte rendition-settet.

`clean()` avviser også tenant-mismatch mot organisasjon/rendition-sett og whitespace-only tekst. Vanlige ForeignKeys gir fortsatt ikke en komplett cross-tenant-databasegaranti. `lock_organization_image_selection` er derfor eneste godkjente skriverute: den er feature-gated, håndhever tenant og capability, låser `Organization` som serialiseringspunkt, kontrollerer `expected_revision`, arkiverer bare statusen på forrige aktive rad og oppretter ny aktiv selection og event i én transaksjon.

`ImageReviewEvent` bruker snapshots som autoritativ historisk identitet, slik at constraints ikke avhenger av at nullable live-referanser fortsatt finnes. Asset-events lagrer intern, versjonert godkjenningstekst og begrenset proveniens; fallback-events lagrer ingen falsk rettighetsgodkjenning. Både standard- og base manager blokkerer ordinær update, delete, bulk-update og upsert på applikasjons-/ORM-nivå. Base manager tillater bare lesing, nye inserts og eksakt nullstilling av de nullable live-referansene som Django trenger for `SET_NULL`; tenant-`CASCADE` er bevart. Dette er ikke kryptografisk WORM eller en absolutt databasegaranti.

Kilde-URL-snapshots lagres uendret, men bare som HTTP/HTTPS uten URL-brukernavn/passord, fragment eller kjente credentials-, signatur-, token-, AWS-, Google- eller Azure SAS-parametere. Valideringen gjør ingen fetch, DNS-oppslag eller annen nettverks-I/O.

Modellene bruker bare `CharField` for logiske keys. De har ingen `FileField`, oppretter ingen mapper eller filer og bruker ingen storagealiaser. Kommandoen kontrollerer featureflagget, men flagget er avslått og ingen API-, Editor-, PUBLIC-, import- eller annen runtimeflyt kaller den. Offentlig release key og public projection inngår ikke, og legacybildeflyten er uendret.

Konseptuell målmodell:

```text
ImageCandidate
    → tenant-eid ImageAsset
    → typed OrganizationImageSelection
    → ImageRendition
    → én felles public image projection

OrganizationImageSelection
    → append-only ImageReviewEvent for locking/replacement
```

Første låsing og replacement har append-only bildehistorikk. Kandidat-, takedown-, restore- og retentionevents kommer i separate leveranser. Assetet eies av tenant og kan finnes før en aktør. Den implementerte typed selection-modellen gjelder bare `Organization`, uten `GenericForeignKey` eller en generell selection for andre objekttyper.
