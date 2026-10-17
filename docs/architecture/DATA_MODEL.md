# Data Model

**Datert 6A.2-backfillstatus 2026-10-17:** Eiergodkjent eksakt plan er anvendt i staging: ett domain, sju tenantbindinger, 285 profilbindinger og 285 egne legacyassignments. Batch `phase6a2-staging-20261017-01` er COMMITTED_VERIFIED med matchende frisk read-back og separat no-op-plan uten restendringer. Bevaring og arkivbundet post-restore av faktisk backfill er verifisert. Samme API kjører og driftsvinduet er avsluttet med timere gjenopprettet; prosjekteier har bekreftet eksisterende Editor-/admin-/PUBLIC-lesing uten feil. STAGING VERIFIED / OWNER-CONFIRMED innen avtalt backfill-/bevarings-/lesescope, se [datert evidens](../status/STAGING_PHASE_6A2_BACKFILL_2026-10-17.md). Ingen shared-aktivering eller ferdigmelding av hele 6A. Midlertidig slettebegrensning består; senere catch-up/apply krever separat godkjenning. Skrivebeskyttet review av de åtte dokumentfilene er fullført uten kritiske eller viktige funn. Publisering som én draft PR er bestilt på `docs/phase6a2-backfill-evidence`; faktisk PR/head og CI følger GitHub og SESSION WRAP-UP. Eldre daterte avsnitt nedenfor beskriver historisk grunnlag.

**Status:** første kodebaserte oversikt

## Implementert tenantmodell og godkjent målarkitektur

Aktiv kode bruker fortsatt direkte tenant-eierskap: `Organization`, `Person`,
`OrganizationPerson`, `PersonContact`, `Tag`, import og bildeobjekter peker på én
`Tenant`, flere relasjoner bruker `CASCADE`, og det finnes ingen
aktiverte sharing-domain-/assignmentlesere eller -skrivere. Direkte tenant-eierskap er fortsatt autoritativt. 6A.1-leveransen nedenfor legger bare til skjema.

[ADR-011](../decisions/ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md)
er godkjent målarkitektur; full shared runtime er **ikke implementert**. Målmodellen beholder
eksisterende Organization-/Person-PK-er som canonical identitet innen ett
eksplisitt SharingDomain og legger tenantassignments additivt til. Canonical core
har ingen redaksjonell home tenant; tenantprivate notater, internal tags,
arbeidsstatus og lokale vurderinger flyttes til overlays. Dagens direkte tenant-
felt beholdes som legacy/home-scope gjennom en kontrollert overgang.

6A.1-skjemaetappen legger til parent-slettevern gjennom assignmentenes `PROTECT`. Før multiassignment aktiveres, må også autorisert assignmentfjerning og øvrige livssyklus-/skriveporter være verifisert. Shared editorial tags
og private internal tags skal være separate; dagens tenantbundne `Tag`-rader
klassifiseres ikke automatisk. Hver canonical Organization skal ha nøyaktig én
aktiv image-home-assignment i samme SharingDomain. Den bestemmer bare framtidige
private image writes; opprettelse og transfer skal aldri reassosiere historiske
assets, selections, releases eller ledgerstate.

## 6A.1 – implementert skjemagrunnmur 2026-10-13

**Leveransehistorikk:** gjennomgått leveranse gjennom [PR #75](https://github.com/fredrik-stack/kreative-norge-crm/pull/75) på `feat/phase6a1-domain-assignment-foundation`, fra `72ac4545fa7e54d3aafb249ec075a4fd01e168cf`. Skrivebeskyttet review av `e2231c16d8c1c43947b417a7337030b30b6c356a` ble gjennomført uten blokkerende funn; kontrollert merge ble bestilt 2026-10-13 og PR-en er merget på `b2d4725e8547f49c39256db188107f2ed29ed93c`, med main-CI `38419948624` success. 0033 ble anvendt i første stagingutføring; API-deploy ble da avbrutt av Compose ContainerConfig og gammel API tilbakeført. Senere recovery/nåstatus følger nedenfor og [datert evidens](../status/STAGING_PHASE_6A1_SCHEMA_VERIFICATION_2026-10-13.md). Shared funksjoner er ikke aktivert.

- `SharingDomain`: ordinær PK, navn, unik slug og opprettelsestid; ingen seed eller default-domain.
- Nullable `sharing_domain` på Tenant, Organization og Person, med `PROTECT` og FK-indekser. Alle eksisterende bindinger forblir NULL; PK-er og obligatoriske legacytenant-felt er uendret.
- `OrganizationTenantAssignment` og `PersonTenantAssignment`: obligatoriske profil-/tenant-FK-er med `PROTECT`, opprettelses-/oppdateringstid og unikhet per profil/tenant. Ingen redundant domain-kolonne, aktiveringsstatus eller ekstra indeks.
- Migrasjon `0033_domain_assignment_foundation` følger `0032_phone_identity_fields`: domain/tenant-binding → profilbindinger → assignmenttabeller. Bare skjemaoperasjoner, ingen backfill eller endring av eksisterende verdier.

**Historisk status etter recovery 2026-10-13, 17:41:33 UTC / 19:41:33 CEST:** PR #75 er merget på `b2d4725e8547f49c39256db188107f2ed29ed93c`. Etter den historiske recreatefeilen ovenfor kjører eksakt målimage i staging. 0033 er beholdt uten ny apply/reverse; schema, constraints, tre tomme nye tabeller, NULL-bindinger og alle 31 legacytabellers fingerprints er uendret gjennom recoveryen. Full 6A.1-stagingverifikasjon er fortsatt ikke erklært: autorisert Editor-/admin-HTTP mangler og ekstern HTTPS møter challenge. Runtime-adminskjemaene skjuler domain, og nye modeller er ikke registrert. Ingen shared writer, backfill, PUBLIC-cutover eller image-home er aktivert. Se [recoveryevidens](../status/STAGING_PHASE_6A1_SCHEMA_VERIFICATION_2026-10-13.md#kontrollert-api-recovery-2026-10-13).

**Gjeldende 6A.1-status, eierbekreftelse mottatt 2026-10-13:** STAGING VERIFIED / OWNER-CONFIRMED for den additive skjemagrunnmuren og API-runtime. Eksisterende tekniske bevis og skrivebeskyttet recoveryreview er supplert med prosjekteiers fullførte session-/Editor-/admin-/PUBLIC-lesing gjennom vanlig HTTPS. Dette er ikke nye automatiske tester eller ny schema-/runtimeendring. Ingen backfill eller shared-aktivering; full ADR-011 og hele 6A er ikke ferdige. [Eierbekreftelse](../status/STAGING_PHASE_6A1_SCHEMA_VERIFICATION_2026-10-13.md#prosjekteiers-lesebekreftelse-mottatt-2026-10-13). Dokumentasjonspublisering/merge rapporteres separat.

Database-FK-er, NOT NULL og unikhet beskytter referanser og duplikater. Assignmentenes `full_clean()` avviser manglende/ulik domain og manglende targets. `save()`, `QuerySet.update` og bulkoperasjoner kaller ikke denne valideringen automatisk; cross-domain-likhet er ikke en databasegaranti. Det finnes ingen støttet application-writer, API, adminregistrering eller kommando for de nye modellene/feltene. Nye felt er utelukket fra eksisterende adminskjemaer og serializers.

Assignmentenes `PROTECT` stanser direkte profil-/tenant-sletting og legacytenantens CASCADE mot en assigned profil, også ved assignment bare til annen tenant. Model-, QuerySet- og adminveier bruker Django Collector; dette er ikke SQL `ON DELETE PROTECT`. PostgreSQL-FK-er verner også direkte parent-DELETE. Legacydata uten assignments beholder dagens CASCADE. Eksplisitt assignmentfjerning og siste-assignment-/canonical-sletting er fortsatt senere autoriserte livssyklusleveranser.

**Historisk lokal verifikasjon før staging:** Docker med isolert PostgreSQL: CRM-suiten 582 tester bestått, safety-ledger 64 tester bestått og siste målrettede kjøring 12/12 bestått. `makemigrations --check --dry-run` fant ingen endringer. Testene inkluderer adminlagring, API-/tenantavgrensning, direkte SQL-FK-vern og forward/reverse/forward før semantiske writes. Ingen migrasjon var da kjørt mot eksisterende lokal CRM- eller stagingdatabase; senere staging-apply/recovery er beskrevet separat ovenfor. CI på eksakt publisert head følges i GitHub og leveranserapporten; baseline-CI erstatter ikke denne kontrollen.

Før senere backfill/write kreves nytt relevant inventar og støttede transaksjonelle tjenester som håndhever domain-endringer, alle bypassveier, autorisasjon, samtidighet, audit/revisjoner og øvrige ADR-011-porter. Ingen deling, PUBLIC-cutover eller image-home er aktivert. Historisk bilde-/release-/event-/ledgerstate reassosieres ikke.

Bare de nye migrasjonene kan reverseres når domain-bindingene og nye tabeller er tomme og ingen semantisk state tapes. Dette er testet med isolerte legacyfixtures; ikke en garanti for destruktiv rollback etter nye writes. Før senere staging-schema-apply kreves separat bestilling, eksakt commit, verifisert backup/gjenopprettingsgrunnlag og pre/poststate. Historisk 5A er ikke fersk databaseline.

## 6A.2 – lokal backfillmekanisme og integritetsvern

**Gjeldende stagingstatus 2026-10-14:** 0034 er anvendt og eksakt API-målcommit
`63743441a173d2c1b4c71d9f9011b93fbadd2ca4` kjører. Fem triggere/batchschema og
bevart legacyinnhold er teknisk verifisert. Alle domains/bindinger/assignments og
batchregister er fortsatt tomme/NULL; dry-run ga 578 forslag og null writes.
Ingen reell backfill eller shared-aktivering. STAGING VERIFIED / OWNER-CONFIRMED
innen API-/schema-/lesescope etter tekniske bevis og eiers lesekontroll;
se [datert evidens](../status/STAGING_PHASE_6A2_SCHEMA_DRY_RUN_2026-10-14.md).

**Historisk leveransestatus før staging:** Godkjent lokal implementering 2026-10-13; review uten blokkerende funn 2026-10-14.
Kode er publisert gjennom PR #77; kontrollert kode-merge uten deploy er bestilt
2026-10-14. Faktisk siste head, merge og CI følger GitHub og SESSION WRAP-UP. Ikke staginganvendt eller aktivert.
Ny 0034 legger til unik miljø/database/batchregistrering og fem PostgreSQL-triggere;
0033 er uendret, uten seed eller RunPython-backfill. `backfill_legacy_domain` har
read-only snapshot som default og separat eksplisitt apply. PK, legacytenant,
alle profil-/relasjons-/kontakt-/publication-/bildeverdier og tidsstempler bevares.
Bare godkjent domainopprettelse/binding og én egen legacyassignment skrives.

ORM-grensen verner domainfelt og assignmentmodeller. Triggerne bruker konflikterende
FOR SHARE-radlåser for targetvalidering; etablerte bindinger er immutable, bound
legacytenant kan ikke byttes og assignments kan ikke reassosieres/fjernes.
Apply låser konkret CRM-/operatørgrunnlag før fresh READ COMMITTED-plan, stale-check,
atomiske endringer og DB-kvittering. PREPARED er ikke COMMITTED_VERIFIED; en ny path
omgår ikke batchregisteret. [Runbookens låser og kvitteringskontrakt](../operations/LEGACY_DOMAIN_BACKFILL.md).

Vanlig legacyredigering består. Ny legacyoppretting gir fortsatt NULL/ingen assignment,
med eksplisitt catch-up før senere shadow. PROTECT gir prosjekteiergodkjent midlertidig
slettebegrensning også for én egen legacyassignment; API gir kontrollert 409, admin
låser bound tenantfelt og bruker protected-delete-visning. Ingen assignment-delete-omvei.
Global rollefallback/shared capabilities, overlays, image-home og PUBLIC er ikke omlagt.
Reverse av 0034 krever tom semantisk/auditstate; etter backfill bevares state og rettes
fremover. Isolerte lokale tester/restore er ikke reell data-apply eller stagingbevis.

## Godkjent stedmålmodell – ikke implementert

[ADR-012](../decisions/ADR-012-PLACE_IDENTITY_GEOGRAPHIC_CLASSIFICATION_AND_ACTOR_ONLY_MAPS.md)
velger global provider-nøytral `Place` som offentlig geografisk referansedata,
med separate `PlaceProviderReference`- og `PlaceCoordinate`-livssykluser.
`OrganizationPlace` og `PersonPlace` blir typed, additive relasjoner med
legacy/proveniens og revision/review. Privacy, publication og SharingDomain-
scope ligger på canonical objekt og relasjon, ikke på Place.

Autorisert tenantbruker/importreviewer kan gjennom en kontrollert server-side
tjeneste velge eksisterende eller opprette source-backed eller brukerbekreftet
canonical Place uten obligatorisk plattform-superadmin-review. Duplicate-/
similarity-kontroll, proveniens, audit og stale-kontroll er påkrevd; globale
merge-, redirect-, deaktiverings- og registerkonflikter forblir
plattformforvaltning. OrganizationPlace peker på canonical Organization og
kopieres ikke per tenantassignment.

Ett Place kan bevare flere historiske eller foreslåtte koordinatrader når
kilde-/providerretensjonen tillater det, men har maksimalt én aktivt godkjent
kartkoordinat om gangen. Bytte er atomisk og auditert; uten entydig aktiv
koordinat projiseres ingen markør. Varige, lovlig retinerbare koordinater kan
følge standardbackupen. Tidsbegrensede rå providerkoordinater krever separat
backup-/purge-/restorekontrakt og kan aldri reaktiveres gjennom restore.

`OrganizationPlace` kan senere være eksplisitt offentlig og inngå i actor-only
kart. `PersonPlace` er strukturert data for profil, matching, filtrering og
tenantforslag, men kan ikke utløse skjulte providerkall eller inngå i koordinat-,
markør- eller kartprojection. Eksplisitt Place-oppslag bruker bare stedsverdi og
geografisk kontekst, aldri personidentitet eller annen CRM-kontekst. Versjonerte
`GeographicTenantRuleSet` bruker bare systemvaliderte administrative koder,
produserer forklarte forslag og kan aldri opprette assignment eller gi
autorisasjon.

Dagens `Organization.municipalities` og `Person.municipality` består som
implementert friteksttilstand gjennom en additiv shadow-/reviewovergang. Ingen
av målmodellene finnes i kode eller migrasjoner ennå.

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

### Fase 4D – additiv telefonidentitet

Migrasjon `0032_phone_identity_fields` etablerer nullable, additive felt for
telefonidentitet uten backfill: `Tenant.default_phone_region`,
`Organization.phone_normalized`, `Organization.phone_normalization_region`,
`PersonContact.normalized_value` og `PersonContact.normalization_region`.
Ingen felt har Norge- eller annen database-/modell-default, og `Person.phone`
forblir uten normalisert felt.

Canonical E.164 og uppercase regionkodeform håndheves med databaseconstraints,
mens modellvalidering kontrollerer regionen mot libphonenumber. Region kan ikke
lagres uten normalisert verdi. PersonContact-identiteten er unik bare innen
tenant + person + kontakttype; telefon er ikke globalt unik mellom personer
eller organisasjoner. 4D-migrasjonen utførte ingen incidental normalisering.
4G har senere satt eksplisitt `NO` på tre stagingtenants og kontrollert
backfillet canonical identitet på 2 Organization- og 56 PHONE-kontaktrader;
råverdi og publisering er uendret, og 4H-restorekopien bekrefter samme state.

## Additiv bildedomenemodell og planlagt bildearkitektur

[ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) er godkjent som arkitekturgrunnlag. Den additive schema-grunnmuren er implementert i `crm` med vanlige heltallsnøkler:

- `ImageAsset` eies av én tenant og lagrer en provider-nøytral privat storage key, SHA-256, faktisk JPEG-/PNG-/WebP-format og MIME-type, dimensjoner, filstørrelse og valideringsversjon
- `ImageRenditionSet` eies av én tenant, beskytter referansen til ett asset og lagrer cover/contain, normalisert fokuspunkt, Foto-zoom, prosesseringsversjon og render-config-hash
- `ImageRendition` eies av én tenant, beskytter referansen til ett rendition-sett og lagrer square/landscape/share, outputformat, dimensjoner, filstørrelse, SHA-256 og provider-nøytral artifact key
- `OrganizationImageSelection` representerer én låst historisk revisjon for én organisasjon og peker enten til nøyaktig ett immutable rendition-sett eller til systemfallback
- `ImageReviewEvent` lagrer append-only snapshots av første selection-låsing, eksplisitt replacement, ordinær fjerning til systemfallback eller restore som ny revisjon, med nullable `SET_NULL`-referanser til levende domeneobjekter

Fase 3B.3-A har lagt additivt til den organization-typed public release aggregaten `OrganizationImageRelease` og `OrganizationImageReleaseRendition` uten `GenericForeignKey`. [ADR-009s 3E.1B-presisering](../decisions/ADR-009-PUBLIC_IMAGE_RUNTIME_RELEASE_DELIVERY_AND_RESTORE_SAFE_DENY_STATE.md#5-materialisering-og-release-livssyklus) tillater maksimalt én public release per selection-revisjon; senere autorisert republisering skal derfor gå via en ny selection-revisjon, UUID og nye keys uten å omskrive tidligere selections eller releases. Release-raden fryser mappingen til tenant, Organization, selection og rendition-sett med direkte, beskyttede relasjoner. Hver release-rendition fryser den konkrete rendition-relasjonen samt variant, outputformat, artifact key, artifact-checksum og public key. Senere statusendring på selection eller metadataendring på en rendition endrer derfor ikke de lagrede snapshottene som beskriver hva releasen representerte. `PROTECT` blokkerer sletting av referert historikk, men er ikke alene reassosieringsbeskyttelse; immutable modell- og managerregler blokkerer ordinær update, ForeignKey-reassosiering, bulk update, upsert/update-conflict og delete. Ny instance-save samt default-, base- og reverse-managerens vanlige create/get-or-create/bulk-create avvises også. Bare aggregate-tjenesten bruker den private, fullvaliderende insertprimitiven inne i sin atomiske transaksjon. Dette er applikasjons-/ORM-beskyttelse, ikke database-WORM.

Databasen håndhever globalt unike release-ID-er og public keys, unik variant og rendition per release, gyldige varianter/formater, key-skjema v1 og ikke-tomme snapshots. `create_organization_image_release` er den eneste støttede Django-workflowen og kontrollerer asset-selection, tenant-/Organization-scope, eksakt rendition-sett og fullstendig square/landscape/share. Den host-eide safety-ledgeren genererer UUIDv4 og canonical public keys atomisk gjennom bridge-operasjonen `reserve`; Django kan bare verifisere den returnerte identiteten mot `build_public_release_key(release.release_id, variant, output_format)` og binde det immutable databaseaggregatet til den. Fri caller-key, caller-valgt UUID, feil variant/extension og delvis aggregate er ugyldig. Cross-row equality og fullstendig aggregate håndheves som eksplisitte domenetjeneste-/modellinvarianter fordi de ikke uttrykkes forsvarlig som vanlige PostgreSQL-checkconstraints.

Parent-locking av `ImageRenditionSet` ble vurdert i 3B.3-A-rettingen, men ikke lagt til uten en konkret reproducerbar blocker. Tjenesten låser selection-raden og de tre konkrete rendition-radene den fryser; senere endring av levende parentmetadata kan ikke omskrive release-relasjonene eller snapshottene. En sterkere lås skal først innføres sammen med en konkret samtidig writer og en test som beviser nødvendig integritets- eller sikkerhetsgaranti.

Databaseconstraints håndhever positive dimensjoner og filstørrelser, fokus i intervallet 0–1, zoom i intervallet 1–3 og tenant-avgrenset unikhet for storage keys, rendition-sett og varianter. Checksum er bevisst ikke globalt unik. `clean()` avviser tenant-mismatch mellom asset og rendition-sett og mellom rendition-sett og rendition. Den interne fase 3C.7-tjenesten håndhever samme scope, alle metadatafeltene og komplett `square`/`landscape`/`share` før aggregate-et kan committes; vanlige direkte ORM-skriveruter til disse tre grunnmodellene er fortsatt ikke gjort immutable eller eksklusive.

For selection håndhever databasen unik revisjon per tenant/organisasjon, maksimalt én `active`-rad, positiv revisjon og eksklusivt valg mellom asset/rendition-sett og systemfallback. Asset-selection kan ha eksakt tom `alt_text`; verdien får ingen skjult fallback til aktørnavnet. En eksplisitt systemfallback-selection må fortsatt ha ikke-tom tekst gjennom et betinget databaseconstraint og fallbacktjenesten. `locked_by` og `locked_at` er obligatoriske, og bruker samt rendition-sett er beskyttet med `PROTECT`. Selection dupliserer ikke asset, fit, fokus, zoom eller prosesseringsversjon; asset og presentasjonsoppskrift nås gjennom det eksakte rendition-settet.

`clean()` avviser også tenant-mismatch mot organisasjon/rendition-sett og en ikke-tom alttekst eller kreditering som bare består av whitespace. Eksakt tom asset-alttekst er gyldig, mens fallbackkommandoene beholder kravet om meningsbærende tekst. Vanlige ForeignKeys gir fortsatt ikke en komplett cross-tenant-databasegaranti. `lock_organization_image_selection`, `remove_organization_image_to_fallback` og `restore_archived_organization_image_selection` er de godkjente skriverutene: alle er feature-gated, håndhever tenant og capability, låser `Organization` som serialiseringspunkt, kontrollerer `expected_revision`, arkiverer bare statusen på forrige aktive rad og oppretter ny aktiv selection og event i én transaksjon. Bare den spesialiserte remove-kommandoen kan utføre asset → systemfallback; den generiske lock-kommandoen avviser denne overgangen og fallback → fallback. Restore krever en eksplisitt eldre, arkivert asset-selection i samme tenant og organisasjon, revaliderer nøyaktig square/landscape/share og kopierer rendition-sett, alt-tekst og offentlig kreditering til en ny revisjon. Restore-kilden omskrives aldri.

`ImageReviewEvent` bruker snapshots som autoritativ historisk identitet, slik at constraints ikke avhenger av at nullable live-referanser fortsatt finnes. `alt_text_snapshot` kan være eksakt tomt for asset-events; organisasjonsnavn og actor username er fortsatt obligatoriske og ikke-tomme snapshots. Nye asset-locks og replacements lagrer intern, versjonert godkjenningstekst og begrenset proveniens; fallback- og restore-events lagrer ingen falsk ny rettighetsgodkjenning. `selection_removed_to_fallback` krever tidligere selection-ID og revisjon, mens `selection_restored` i tillegg krever restore-kildens selection-ID og revisjon. Migrasjon `0030` legger additivt til `formal_takedown`, lukket `takedown_reason_code` og `release_id_snapshot`; eventet peker på den nye fallbackselectionen, men bevarer forrige asset-selection/revisjon, rendition-sett, asset, originalbyte-checksum, actor og tidspunkt i snapshots. Migrasjonen er reversibel før slike events finnes; etter første formelle takedown er auditkontrakten forward-only og rollback skal være write-gate av eller en fremoverrettet retting. Databasen er audit/workflow, ikke deny-authority. Både standard- og base manager blokkerer ordinær update, delete, bulk-update og upsert på applikasjons-/ORM-nivå. Base manager tillater bare lesing, nye inserts og eksakt nullstilling av nullable live-referanser som Django trenger for `SET_NULL`; tenant-`CASCADE` er bevart. Dette er ikke kryptografisk WORM eller en absolutt databasegaranti.

Schema-migrasjon `0027` er uten datarewrite og kan reverseres så lenge ingen blank asset-alt eller blankt event-alt-snapshot er lagret. Etter første blanke rad er migrasjonen forward-only: de gamle nonempty-constraintene blokkerer reverse. Operativ rollback er da feature-off og en fremoverrettet retting; en pre-deploy-backup må tas og verifiseres før aktivering. Eksisterende verdier skal ikke omskrives, og aktørnavn skal aldri innføres som skjult alttekstfallback. En målrettet PostgreSQL-migrasjonstest verifiserer både at reverse blokkeres og at databasen forblir på `0027` med de blanke radene intakte.

Schema-migrasjon `0028` legger til non-null `zoom` med semantisk default `1.0000` og et databaseconstraint på 1–3. Render-config-hashen inkluderer zoom, slik at samme asset/fokus/zoom er idempotent mens en endret zoom oppretter et annet immutable rendition-sett og andre artifact keys. Migrasjonen kan reverseres før non-default zoom finnes. En reverse-guard blokkerer feltfjerning etter at non-default zoom er lagret, fordi feltap ellers ville gjort historiske rendition-sett tvetydige; operativ rollback er da feature-off eller fremoverrettet retting etter verifisert backup.

Kilde-URL-snapshots lagres uendret, men bare som HTTP/HTTPS uten URL-brukernavn/passord, fragment eller kjente credentials-, signatur-, token-, AWS-, Google- eller Azure SAS-parametere. `upload` og `brave_image_search` kan ha tom source-URL; andre ikke-tomme source types krever URL. Brave-unntaket er bevisst fordi standardvilkårene begrenser persistent lagring/caching av providerresultater. Valideringen gjør ingen fetch, DNS-oppslag eller annen nettverks-I/O.

De implementerte modellene bruker bare `CharField` for logiske keys og har ingen `FileField`. Fase 3C.7 legger til en intern, feature-gated upload-only tjeneste som bruker de navngitte storagealiasene, men bare når den kalles eksplisitt med feature aktivert. Source checksum beregnes fra eksakte originalbytes og artifact-checksum fra ferdig encodede bytes før write. Tjenesten krever deretter eksakt requested storage key og verifiserer de skrevne bytesene før den oppretter eller gjenbruker et komplett databaseaggregate i én transaksjon. Samme tenant, source og processing-config gjenbruker samme konsistente aggregate; delvis eller avvikende historikk feiler lukket uten implicit reparasjon.

Interne keys er tenant-scopede og deterministiske, men er ikke public release keys. `image_renditions_public` er fortsatt bare artifact-store. Fase 3E.1B kan bak egen gate materialisere bridge-reserverte `releases/<release_uuid>/<variant>.<ext>` til separat `public_image_delivery`, etter unik immutable selection-binding og før ankret activation. Fase 3E.1C-serving, 3E.2-projection og 3E.3 target-API/PUBLIC/head leser det eksisterende aggregatet uten schemaendring og har separate default-off kodegater. Alle er aktivert bare i ignorert stagingkonfigurasjon; legacybildefeltene består for rollback/historikk, men styrer ikke den aktive 3E.3-reisen.

Fase 3D.1 og 3D.2 oppretter ingen `ImageCandidate`-tabell. Offisielle, Brave- og direkte URL-kandidater bæres av en kortlivet signert `candidate_ref` som binder tenant, Organization, bruker, normalisert URL, kilde/proveniens, kjente dimensjoner og discoverytid. Brave-refen kan i tillegg bære eksakt query, querykilder og bare det normaliserte nødvendige delsettet av resultattittel, publisher, thumbnail og kildeside transient; full providerrespons lagres aldri. Etter processing binder en separat signert `approval_ref` proveniensen til asset-checksum, eksakt rendition-sett, Foto/Logo-modus og tekniske warnings. For Brave beholdes query og normaliserte kandidatfelt bare i de signerte referansene; permanent event beholder source type/provider, men tom source- og side-URL. Appen oppretter ingen søkehistorikk. Braves egne standard query-logger kan likevel beholdes i opptil 90 dager; Zero Data Retention er en separat Enterprise-/avtalekontrakt og er ikke egenskapen til vår signed-ref. Upload går direkte til processing og får signert approvalref uten persistent kandidatrad. Først ved eksplisitt approval kopieres tillatt proveniens til eksisterende `ImageReviewEvent` og eksisterende `OrganizationImageSelection` opprettes eller erstattes. Uvalgte kandidater og ephemeral kandidatpreviews etterlater ingen databasemodell eller eget storageobjekt.

Fase 3F-migrasjon `0031` er additiv og oppretter `ImportImageDecision` som en direkte én-til-én-kontrakt mot `ImportRow`; eksisterende jobber, rader og generiske `ImportDecision`-rader backfilles eller omskrives ikke. Modellen har eksakt de tre typene `KEEP_LOCKED_IMAGE`, `SET_APPROVED_IMAGE` og `USE_APPROVED_FALLBACK`, besluttende bruker, valgfri target-Organization, forventet selection/revisjon, valgfritt tenant-eid asset/rendition-sett og immutable approval-, proveniens-, checksum-, versjons- og canonical proposed-actor-snapshots. Databaseconstraints håndhever selection/revision-par og typed asset-/approvalformen; cross-tenant-, aggregate- og stale-state-invariantene håndheves i domenetjenesten. `ImageReviewEvent.import_image_decision` er nullable `OneToOneField(..., on_delete=PROTECT)`, slik at samme beslutning ikke kan anvendes to ganger og auditbindingen ikke kan slettes gjennom beslutningen. Det finnes ingen offentlig eller Editor-API for å opprette beslutningen i 3F; senere Import 2.0-UX skal bruke den godkjente tjenesten.

## Public runtime safety-state – fase 3E.1A–3E.4 ACTIVE/verifisert i staging

[ADR-009](../decisions/ADR-009-PUBLIC_IMAGE_RUNTIME_RELEASE_DELIVERY_AND_RESTORE_SAFE_DENY_STATE.md) skiller public runtimeens sikkerhetstilstand fra PostgreSQL-aggregatet. `image_safety` kan lese den bevarte schema-v1-historikken og har oppgradert aktiv stagingledger transaksjonelt til schema v2 uten å omskrive v1-events, sekvenser, hashes, receipts, ledger-ID eller cursor. V2 bruker en separat append-only eventtabell etter den fryste v1-grensen og rebuildbare read-models for tenant/checksum-deny og tenant/Organization-legacyguard. Før første v2-event var ankerbundle byteidentisk v1; første v2-event ga et versjonert v2-bundle. Staging er nå schema v2 og `READY` på cursor `13`. Controlled serving, projection, target-API og PUBLIC/head leser state gjennom `authorize`; approval/restore/release bruker `check_checksum`, og legacyresolverne bruker `legacy_guard` fail-closed når materialiseringsruntimeen er aktiv.

Ledgerskjemaet skal minst støtte idempotente event-ID-er og:

- `release_reserved`
- `release_activated`
- `release_retired`
- `release_denied`
- senere `tenant_runtime_enrolled` bare dersom tenantvis aktivering blir en faktisk sikkerhetsgrense
- tenant-scopet checksum-deny med `ImageAsset.checksum_sha256` som originalbyte-identitet; samme checksum i annen tenant er separat

Samme SQLite holder avledet `release_state`, permanent keyindeks og read-cursor som bygges deterministisk på nytt fra eventene. `retired` og `denied` er terminalt for release-ID-en; republisering bruker ny UUID/key. Reservationen binder tenant-/Organization-/selection-/revisjon-/rendition-sett-ID-er og de tre artifact key/checksum-snapshottene, mens ledgeren genererer UUID og public keys og Django verifiserer dem mot den samme rene key-builderen. Databaseaggregatet fryser fortsatt historisk mapping, men bestemmer ikke alene om releasen er aktiv eller leverbar. `create_organization_image_release()` utfører den feature-gatede reserve → DB-bind → materialiser → read-back → activate-flyten. Serving og projection kombinerer deretter DB-snapshottene med ledgerens read-only sikkerhetsbeslutning. API-schema og PUBLIC-cutover er separate default-off kodegater og begge er aktivert i ignorert stagingkonfigurasjon etter 3E.3-gaten.

Runtimeflyten blir konseptuelt:

```text
immutable ImageRendition artifacts
    → permanent release_reserved i ledger/off-server anker
    → OrganizationImageRelease-aggregate bundet til reservasjonen
    → create-only/no-clobber kopi til separat public-delivery-root
    → checksum-/dimensjons-/formatverifikasjon
    → release_activated
    → PublicImageProjection og kontrollert serving
```

`image_renditions_public` forblir intern artifact-storage. Feature-gatede `releases/<release_uuid>/<variant>.<ext>` materialiseres create-only til eget `/srv/kreative-norge/media/public-delivery/` med separat cleanup-/purgeeierskap. 3E.1B innfører ingen automatisk releasefilsletting, og delivery-rooten inngår ikke i dagens generiske orphan-cleanup. Idempotency håndheves av deterministisk ledger-event, unik selection-binding, immutable revision-snapshot og eksakt aggregatekontroll; lifecycle-status lagres fortsatt ikke i PostgreSQL.

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

Første låsing, replacement, ordinær fjerning til fallback, ordinær restore og formell takedown har append-only bildehistorikk. Discovery og søk har ikke egne persistente kandidat-events; retentionevents kommer i en separat leveranse. Assetet eies av tenant og kan finnes før en aktør. Den typed selection-modellen og release aggregate gjelder bare `Organization`, uten `GenericForeignKey`. Selection-revisjon er ikke release identity. Replacement, restore og senere autorisert republisering bruker ny release-UUID og nye keys; etter checksum-deny krever republisering også en annen originalchecksum. Safety-ledgeren er eneste lifecycle-/deny-authority, mens PostgreSQL beholder immutable releasehistorikk og takedownaudit. 3E.1A–3E.4 er aktive/verifiserte i staging; 3E.4-writegaten er fortsatt `False` som kode-/eksempelstandard og `True` bare i ignorert stagingkonfigurasjon.
