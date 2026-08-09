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

Fase 3B.3-A har lagt additivt til den organization-typed public release aggregaten `OrganizationImageRelease` og `OrganizationImageReleaseRendition` uten `GenericForeignKey`. Flere historiske releases kan peke til samme selection slik at senere autorisert republisering får ny release-ID uten å omskrive selection eller tidligere releases. Release-raden fryser mappingen til tenant, Organization, selection og rendition-sett med direkte, beskyttede relasjoner. Hver release-rendition fryser den konkrete rendition-relasjonen samt variant, outputformat, artifact key, artifact-checksum og public key. Senere statusendring på selection eller metadataendring på en rendition endrer derfor ikke de lagrede snapshottene som beskriver hva releasen representerte. `PROTECT` blokkerer sletting av referert historikk, men er ikke alene reassosieringsbeskyttelse; immutable modell- og managerregler blokkerer ordinær update, ForeignKey-reassosiering, bulk update, upsert/update-conflict og delete. Ny instance-save samt default-, base- og reverse-managerens vanlige create/get-or-create/bulk-create avvises også. Bare aggregate-tjenesten bruker den private, fullvaliderende insertprimitiven inne i sin atomiske transaksjon. Dette er applikasjons-/ORM-beskyttelse, ikke database-WORM.

Databasen håndhever globalt unike release-ID-er og public keys, unik variant og rendition per release, gyldige varianter/formater, key-skjema v1 og ikke-tomme snapshots. Den atomiske `create_organization_image_release`-tjenesten er eneste støttede opprettelsesvei, kontrollerer asset-selection, tenant-/Organization-scope, eksakt rendition-sett og fullstendig square/landscape/share. Den genererer UUIDv4 og public keys internt og krever eksakt equality mellom lagret key og `build_public_release_key(release.release_id, variant, output_format)`; fri caller-key, feil UUID/variant/extension og delvis aggregate er ugyldig. Cross-row equality og fullstendig aggregate håndheves som eksplisitte domenetjeneste-/modellinvarianter fordi de ikke uttrykkes forsvarlig som vanlige PostgreSQL-checkconstraints.

Parent-locking av `ImageRenditionSet` ble vurdert i 3B.3-A-rettingen, men ikke lagt til uten en konkret reproducerbar blocker. Tjenesten låser selection-raden og de tre konkrete rendition-radene den fryser; senere endring av levende parentmetadata kan ikke omskrive release-relasjonene eller snapshottene. En sterkere lås skal først innføres sammen med en konkret samtidig writer og en test som beviser nødvendig integritets- eller sikkerhetsgaranti.

Databaseconstraints håndhever positive dimensjoner og filstørrelser, fokus i intervallet 0–1 og tenant-avgrenset unikhet for storage keys, rendition-sett og varianter. Checksum er bevisst ikke globalt unik. `clean()` avviser tenant-mismatch mellom asset og rendition-sett og mellom rendition-sett og rendition. Den interne fase 3C.7-tjenesten håndhever samme scope, alle metadatafeltene og komplett `square`/`landscape`/`share` før aggregate-et kan committes; vanlige direkte ORM-skriveruter til disse tre grunnmodellene er fortsatt ikke gjort immutable eller eksklusive.

For selection håndhever databasen unik revisjon per tenant/organisasjon, maksimalt én `active`-rad, positiv revisjon, ikke-tom alt-tekst og eksklusivt valg mellom asset/rendition-sett og systemfallback. `locked_by` og `locked_at` er obligatoriske, og bruker samt rendition-sett er beskyttet med `PROTECT`. Selection dupliserer ikke asset, fit, fokus eller prosesseringsversjon; asset og presentasjonsoppskrift nås gjennom det eksakte rendition-settet.

`clean()` avviser også tenant-mismatch mot organisasjon/rendition-sett og whitespace-only tekst. Vanlige ForeignKeys gir fortsatt ikke en komplett cross-tenant-databasegaranti. `lock_organization_image_selection`, `remove_organization_image_to_fallback` og `restore_archived_organization_image_selection` er de godkjente skriverutene: alle er feature-gated, håndhever tenant og capability, låser `Organization` som serialiseringspunkt, kontrollerer `expected_revision`, arkiverer bare statusen på forrige aktive rad og oppretter ny aktiv selection og event i én transaksjon. Bare den spesialiserte remove-kommandoen kan utføre asset → systemfallback; den generiske lock-kommandoen avviser denne overgangen og fallback → fallback. Restore krever en eksplisitt eldre, arkivert asset-selection i samme tenant og organisasjon, revaliderer nøyaktig square/landscape/share og kopierer rendition-sett, alt-tekst og offentlig kreditering til en ny revisjon. Restore-kilden omskrives aldri.

`ImageReviewEvent` bruker snapshots som autoritativ historisk identitet, slik at constraints ikke avhenger av at nullable live-referanser fortsatt finnes. Nye asset-locks og replacements lagrer intern, versjonert godkjenningstekst og begrenset proveniens; fallback- og restore-events lagrer ingen falsk ny rettighetsgodkjenning. `selection_removed_to_fallback` krever tidligere selection-ID og revisjon i databaseconstraintet, mens `selection_restored` i tillegg krever restore-kildens selection-ID og revisjon, asset-/rendition-snapshots og tom approval/proveniens. Restore-eventet har en nullable live-referanse med `SET_NULL`, men immutable source-snapshots bevares. Databasen kan ikke alene bevise at restore-kilden var arkivert og i samme tenant og organisasjon; domenekommandoen håndhever dette. Både standard- og base manager blokkerer ordinær update, delete, bulk-update og upsert på applikasjons-/ORM-nivå. Base manager tillater bare lesing, nye inserts og eksakt nullstilling av de nullable live-referansene som Django trenger for `SET_NULL`; tenant-`CASCADE` er bevart. Dette er ikke kryptografisk WORM eller en absolutt databasegaranti. Når append-only removal- eller restore-events senere finnes i et aktivt miljø, skal rollback bruke feature-off eller en ny fremoverrettet migrasjon, aldri sletting eller omskriving av eventhistorikk.

Kilde-URL-snapshots lagres uendret, men bare som HTTP/HTTPS uten URL-brukernavn/passord, fragment eller kjente credentials-, signatur-, token-, AWS-, Google- eller Azure SAS-parametere. Valideringen gjør ingen fetch, DNS-oppslag eller annen nettverks-I/O.

De implementerte modellene bruker bare `CharField` for logiske keys og har ingen `FileField`. Fase 3C.7 legger til en intern, feature-gated upload-only tjeneste som bruker de navngitte storagealiasene, men bare når den kalles eksplisitt med feature aktivert. Source checksum beregnes fra eksakte originalbytes og artifact-checksum fra ferdig encodede bytes før write. Tjenesten krever deretter eksakt requested storage key og verifiserer de skrevne bytesene før den oppretter eller gjenbruker et komplett databaseaggregate i én transaksjon. Samme tenant, source og processing-config gjenbruker samme konsistente aggregate; delvis eller avvikende historikk feiler lukket uten implicit reparasjon.

Interne keys er tenant-scopede og deterministiske, men er ikke public release keys. `image_renditions_public` brukes i denne fasen bare som artifact-store; `releases/<release_uuid>/<variant>.<ext>` materialiseres ikke. Selection- og release-tjenestene kontrollerer også featureflagget, men flagget er avslått og ingen API-, Editor-, PUBLIC-, import- eller annen brukerflyt kaller noen av tjenestene. Public storage reservation, projection og serving er fortsatt ikke implementert, og legacybildeflyten er uendret.

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
    → OrganizationImageRelease med UUIDv4
    → OrganizationImageReleaseRendition per square/landscape/share
    → canonical relative key releases/<release_uuid>/<variant>.<ext>
```

Første låsing, replacement, ordinær fjerning til fallback og ordinær restore som ny revisjon har append-only bildehistorikk. Kandidat-, takedown- og retentionevents kommer i separate leveranser. Assetet eies av tenant og kan finnes før en aktør. Den implementerte typed selection-modellen og release aggregate gjelder bare `Organization`, uten `GenericForeignKey` eller en generell selection/release for andre objekttyper. Selection-revisjon er ikke release identity. Replacement, restore og senere autorisert republisering skal bruke ny release-UUID og nye keys, mens de samme immutable rendition-bytes kan gjenbrukes uten re-encoding. Fase 3B.1R-, fase 3B.3-, fase 3B.3-A- og den interne fase 3C.7-processinggaten er gjennomført lokalt; permanent public reservation-/deny-journal i separat failure-domain og senere serving-, purge-, API-, retention-, sync/async- og observabilitygater må fortsatt være grønne før faktisk offentlig bildebruk kan aktiveres.
