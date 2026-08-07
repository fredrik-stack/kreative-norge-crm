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
- `ImageReviewEvent` lagrer append-only snapshots av første selection-låsing, eksplisitt replacement, ordinær fjerning til systemfallback eller restore som ny revisjon, med nullable `SET_NULL`-referanser til levende domeneobjekter

Fase 3B.3 har i tillegg godkjent en planlagt, additiv og organization-typed public release aggregate uten `GenericForeignKey`. `OrganizationImageRelease` og `OrganizationImageReleaseRendition` er anbefalte modellnavn, ikke fastsatt schema. Flere historiske releases kan peke til samme selection slik at senere autorisert republisering får ny release-ID uten å omskrive selection eller tidligere releases. Hver release skal fryse sin historiske mapping til tenant, Organization, selection, rendition-sett og konkrete rendition-/artifact-identiteter; senere endring av en levende selection eller relasjon kan ikke endre hva releasen representerer. Eksakt mekanisme – immutable snapshots, beskyttede immutable relasjoner eller annet verifiserbart design – velges i fase 3B.3-A. `PROTECT` skal blokkere sletting av referert historikk, men gir ikke alene beskyttelse mot ForeignKey-reassosiering eller feltendring.

Planlagte constraints omfatter globalt unike release-ID-er og public keys samt unik variant og rendition per release. En atomisk domenetjeneste må kontrollere asset-selection, tenant-/Organization-scope, eksakt rendition-sett og fullstendig square/landscape/share. Den skal generere public key internt og kreve eksakt equality mellom lagret key og canonical builder-resultat fra release-ID, variant og outputformat; fri caller-key, patternmatch alene og delvis aggregate er ugyldig. Eksakt feltutforming, manager-/servicestruktur og fordeling mellom PostgreSQL-constraints og domenetjeneste er fortsatt åpen for fase 3B.3-A. Modellene finnes ikke ennå.

Databaseconstraints håndhever positive dimensjoner og filstørrelser, fokus i intervallet 0–1 og tenant-avgrenset unikhet for storage keys, rendition-sett og varianter. Checksum er bevisst ikke globalt unik. `clean()` avviser tenant-mismatch mellom asset og rendition-sett og mellom rendition-sett og rendition, men dette er ikke alene en full databasegaranti; en senere domenetjeneste skal håndheve samme invariant før runtime kan skrive.

For selection håndhever databasen unik revisjon per tenant/organisasjon, maksimalt én `active`-rad, positiv revisjon, ikke-tom alt-tekst og eksklusivt valg mellom asset/rendition-sett og systemfallback. `locked_by` og `locked_at` er obligatoriske, og bruker samt rendition-sett er beskyttet med `PROTECT`. Selection dupliserer ikke asset, fit, fokus eller prosesseringsversjon; asset og presentasjonsoppskrift nås gjennom det eksakte rendition-settet.

`clean()` avviser også tenant-mismatch mot organisasjon/rendition-sett og whitespace-only tekst. Vanlige ForeignKeys gir fortsatt ikke en komplett cross-tenant-databasegaranti. `lock_organization_image_selection`, `remove_organization_image_to_fallback` og `restore_archived_organization_image_selection` er de godkjente skriverutene: alle er feature-gated, håndhever tenant og capability, låser `Organization` som serialiseringspunkt, kontrollerer `expected_revision`, arkiverer bare statusen på forrige aktive rad og oppretter ny aktiv selection og event i én transaksjon. Bare den spesialiserte remove-kommandoen kan utføre asset → systemfallback; den generiske lock-kommandoen avviser denne overgangen og fallback → fallback. Restore krever en eksplisitt eldre, arkivert asset-selection i samme tenant og organisasjon, revaliderer nøyaktig square/landscape/share og kopierer rendition-sett, alt-tekst og offentlig kreditering til en ny revisjon. Restore-kilden omskrives aldri.

`ImageReviewEvent` bruker snapshots som autoritativ historisk identitet, slik at constraints ikke avhenger av at nullable live-referanser fortsatt finnes. Nye asset-locks og replacements lagrer intern, versjonert godkjenningstekst og begrenset proveniens; fallback- og restore-events lagrer ingen falsk ny rettighetsgodkjenning. `selection_removed_to_fallback` krever tidligere selection-ID og revisjon i databaseconstraintet, mens `selection_restored` i tillegg krever restore-kildens selection-ID og revisjon, asset-/rendition-snapshots og tom approval/proveniens. Restore-eventet har en nullable live-referanse med `SET_NULL`, men immutable source-snapshots bevares. Databasen kan ikke alene bevise at restore-kilden var arkivert og i samme tenant og organisasjon; domenekommandoen håndhever dette. Både standard- og base manager blokkerer ordinær update, delete, bulk-update og upsert på applikasjons-/ORM-nivå. Base manager tillater bare lesing, nye inserts og eksakt nullstilling av de nullable live-referansene som Django trenger for `SET_NULL`; tenant-`CASCADE` er bevart. Dette er ikke kryptografisk WORM eller en absolutt databasegaranti. Når append-only removal- eller restore-events senere finnes i et aktivt miljø, skal rollback bruke feature-off eller en ny fremoverrettet migrasjon, aldri sletting eller omskriving av eventhistorikk.

Kilde-URL-snapshots lagres uendret, men bare som HTTP/HTTPS uten URL-brukernavn/passord, fragment eller kjente credentials-, signatur-, token-, AWS-, Google- eller Azure SAS-parametere. Valideringen gjør ingen fetch, DNS-oppslag eller annen nettverks-I/O.

De implementerte modellene bruker bare `CharField` for logiske keys. De har ingen `FileField`, oppretter ingen mapper eller filer og bruker ingen storagealiaser. Kommandoen kontrollerer featureflagget, men flagget er avslått og ingen API-, Editor-, PUBLIC-, import- eller annen runtimeflyt kaller den. Public release aggregate, canonical release key og public projection er fortsatt ikke implementert, og legacybildeflyten er uendret.

Konseptuell målmodell:

```text
ImageCandidate
    → tenant-eid ImageAsset
    → typed OrganizationImageSelection
    → ImageRendition
    → én felles public image projection

OrganizationImageSelection
    → append-only ImageReviewEvent for locking/replacement/removal-to-fallback/restore

OrganizationImageSelection
    → planlagt OrganizationImageRelease med UUIDv4
    → planlagt OrganizationImageReleaseRendition per square/landscape/share
    → canonical relative key releases/<release_uuid>/<variant>.<ext>
```

Første låsing, replacement, ordinær fjerning til fallback og ordinær restore som ny revisjon har append-only bildehistorikk. Kandidat-, takedown- og retentionevents kommer i separate leveranser. Assetet eies av tenant og kan finnes før en aktør. Den implementerte typed selection-modellen og den planlagte release aggregate gjelder bare `Organization`, uten `GenericForeignKey` eller en generell selection/release for andre objekttyper. Selection-revisjon er ikke release identity. Replacement, restore og senere autorisert republisering skal bruke ny release-UUID og nye keys, mens de samme immutable rendition-bytes kan gjenbrukes uten re-encoding. Fase 3B.1R- og fase 3B.3-gatene er gjennomført og godkjent; release aggregate/reservasjon og senere serving-, purge-, journal-, API-, retention-, sync/async- og observabilitygater må fortsatt være grønne før faktisk bildebehandling eller storage-runtime aktiveres.
