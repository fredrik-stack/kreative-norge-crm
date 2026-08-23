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

`ImageReviewEvent` bruker snapshots som autoritativ historisk identitet, slik at constraints ikke avhenger av at nullable live-referanser fortsatt finnes. `alt_text_snapshot` kan være eksakt tomt for asset-events; organisasjonsnavn og actor username er fortsatt obligatoriske og ikke-tomme snapshots. Nye asset-locks og replacements lagrer intern, versjonert godkjenningstekst og begrenset proveniens; fallback- og restore-events lagrer ingen falsk ny rettighetsgodkjenning. `selection_removed_to_fallback` krever tidligere selection-ID og revisjon i databaseconstraintet, mens `selection_restored` i tillegg krever restore-kildens selection-ID og revisjon, asset-/rendition-snapshots og tom approval/proveniens. Restore-eventet har en nullable live-referanse med `SET_NULL`, men immutable source-snapshots bevares. Databasen kan ikke alene bevise at restore-kilden var arkivert og i samme tenant og organisasjon; domenekommandoen håndhever dette. Både standard- og base manager blokkerer ordinær update, delete, bulk-update og upsert på applikasjons-/ORM-nivå. Base manager tillater bare lesing, nye inserts og eksakt nullstilling av de nullable live-referansene som Django trenger for `SET_NULL`; tenant-`CASCADE` er bevart. Dette er ikke kryptografisk WORM eller en absolutt databasegaranti. Når append-only removal- eller restore-events senere finnes i et aktivt miljø, skal rollback bruke feature-off eller en ny fremoverrettet migrasjon, aldri sletting eller omskriving av eventhistorikk.

Schema-migrasjon `0027` er uten datarewrite og kan reverseres så lenge ingen blank asset-alt eller blankt event-alt-snapshot er lagret. Etter første blanke rad er migrasjonen forward-only: de gamle nonempty-constraintene blokkerer reverse. Operativ rollback er da feature-off og en fremoverrettet retting; en pre-deploy-backup må tas og verifiseres før aktivering. Eksisterende verdier skal ikke omskrives, og aktørnavn skal aldri innføres som skjult alttekstfallback. En målrettet PostgreSQL-migrasjonstest verifiserer både at reverse blokkeres og at databasen forblir på `0027` med de blanke radene intakte.

Schema-migrasjon `0028` legger til non-null `zoom` med semantisk default `1.0000` og et databaseconstraint på 1–3. Render-config-hashen inkluderer zoom, slik at samme asset/fokus/zoom er idempotent mens en endret zoom oppretter et annet immutable rendition-sett og andre artifact keys. Migrasjonen kan reverseres før non-default zoom finnes. En reverse-guard blokkerer feltfjerning etter at non-default zoom er lagret, fordi feltap ellers ville gjort historiske rendition-sett tvetydige; operativ rollback er da feature-off eller fremoverrettet retting etter verifisert backup.

Kilde-URL-snapshots lagres uendret, men bare som HTTP/HTTPS uten URL-brukernavn/passord, fragment eller kjente credentials-, signatur-, token-, AWS-, Google- eller Azure SAS-parametere. `upload` og `brave_image_search` kan ha tom source-URL; andre ikke-tomme source types krever URL. Brave-unntaket er bevisst fordi standardvilkårene begrenser persistent lagring/caching av providerresultater. Valideringen gjør ingen fetch, DNS-oppslag eller annen nettverks-I/O.

De implementerte modellene bruker bare `CharField` for logiske keys og har ingen `FileField`. Fase 3C.7 legger til en intern, feature-gated upload-only tjeneste som bruker de navngitte storagealiasene, men bare når den kalles eksplisitt med feature aktivert. Source checksum beregnes fra eksakte originalbytes og artifact-checksum fra ferdig encodede bytes før write. Tjenesten krever deretter eksakt requested storage key og verifiserer de skrevne bytesene før den oppretter eller gjenbruker et komplett databaseaggregate i én transaksjon. Samme tenant, source og processing-config gjenbruker samme konsistente aggregate; delvis eller avvikende historikk feiler lukket uten implicit reparasjon.

Interne keys er tenant-scopede og deterministiske, men er ikke public release keys. `image_renditions_public` er fortsatt bare artifact-store. Fase 3E.1B kan bak egen avslått gate materialisere bridge-reserverte `releases/<release_uuid>/<variant>.<ext>` til separat `public_image_delivery`, etter unik immutable selection-binding og før ankret activation. Projection og serving er fortsatt ikke implementert, og legacybildeflyten er uendret.

Fase 3D.1 og 3D.2 oppretter ingen `ImageCandidate`-tabell. Offisielle, Brave- og direkte URL-kandidater bæres av en kortlivet signert `candidate_ref` som binder tenant, Organization, bruker, normalisert URL, kilde/proveniens, kjente dimensjoner og discoverytid. Brave-refen kan i tillegg bære eksakt query, querykilder og bare det normaliserte nødvendige delsettet av resultattittel, publisher, thumbnail og kildeside transient; full providerrespons lagres aldri. Etter processing binder en separat signert `approval_ref` proveniensen til asset-checksum, eksakt rendition-sett, Foto/Logo-modus og tekniske warnings. For Brave beholdes query og normaliserte kandidatfelt bare i de signerte referansene; permanent event beholder source type/provider, men tom source- og side-URL. Appen oppretter ingen søkehistorikk. Braves egne standard query-logger kan likevel beholdes i opptil 90 dager; Zero Data Retention er en separat Enterprise-/avtalekontrakt og er ikke egenskapen til vår signed-ref. Upload går direkte til processing og får signert approvalref uten persistent kandidatrad. Først ved eksplisitt approval kopieres tillatt proveniens til eksisterende `ImageReviewEvent` og eksisterende `OrganizationImageSelection` opprettes eller erstattes. Uvalgte kandidater og ephemeral kandidatpreviews etterlater ingen databasemodell eller eget storageobjekt.

## Public runtime safety-state – fase 3E.1A ACTIVE i staging

[ADR-009](../decisions/ADR-009-PUBLIC_IMAGE_RUNTIME_RELEASE_DELIVERY_AND_RESTORE_SAFE_DENY_STATE.md) skiller public runtimeens sikkerhetstilstand fra PostgreSQL-aggregatet. `image_safety` implementerer en separat SQLite schema v1-ledger med append-only autoritative events, hashkjede, rebuildbar read-model/cursor, immutable anchor receipts og standalone incident restore. Den dedikerte off-serverkjeden og fail-closed restore-/healthgaten er live-verifisert og `ACTIVE` i staging; ingen Django public runtime leser state ennå.

Ledgerskjemaet skal minst støtte idempotente event-ID-er og:

- `release_reserved`
- `release_activated`
- `release_retired`
- `release_denied`
- senere `tenant_runtime_enrolled` bare dersom tenantvis aktivering blir en faktisk sikkerhetsgrense
- senere tenant-scopet checksum-deny før formell takedown aktiveres

Samme SQLite holder avledet `release_state`, permanent keyindeks og read-cursor som bygges deterministisk på nytt fra eventene. `retired` og `denied` er terminalt for release-ID-en; republisering bruker ny UUID/key. Reservationen binder tenant-/Organization-/selection-/revisjon-/rendition-sett-ID-er og de tre artifact key/checksum-snapshottene, mens ledgeren genererer UUID og public keys og Django verifiserer dem mot den samme rene key-builderen. Databaseaggregatet fryser fortsatt historisk mapping, men bestemmer ikke alene om releasen er aktiv eller leverbar. `create_organization_image_release()` utfører nå den feature-gatede reserve → DB-bind → materialiser → read-back → activate-flyten; serving og projection er fortsatt frakoblet.

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

Første låsing, replacement, ordinær fjerning til fallback og ordinær restore som ny revisjon har append-only bildehistorikk. Discovery og søk har ikke egne persistente kandidat-events; takedown- og retentionevents kommer i separate leveranser. Assetet eies av tenant og kan finnes før en aktør. Den implementerte typed selection-modellen og release aggregate gjelder bare `Organization`, uten `GenericForeignKey` eller en generell selection/release for andre objekttyper. Selection-revisjon er ikke release identity. Replacement, restore og senere autorisert republisering skal bruke ny release-UUID og nye keys, mens de samme immutable rendition-bytes kan gjenbrukes uten re-encoding. Fase 3B.1R–3D.2 er gjennomført som tidligere dokumentert. ADR-009s ledger/off-servergate er `ACTIVE` i staging, mens 3E.1B-delivery/materialisering bare er implementert bak avslått kodegate og ikke stagingaktivert. Serving, projection, API/PUBLIC og takedown må fortsatt implementeres og bli grønne før faktisk offentlig bildebruk kan aktiveres.
