# Project Status Current

**Status:** Fase 1 og 2 gjennomført; fase 3A, fase 3B.1 og fase 3B.2 teknisk gjennomført; fase 3B.1R og fase 3B.3 gjennomført og godkjent; fase 3B.3-A har additiv public release-domenegrunnmur; lokal Hetzner storage-/backup-MVP **ACTIVE**; fase 3C har bilde-/selection- og processinggrunnmur; fase 3D.1 er teknisk aktivert og visuelt godkjent i staging; fase 3D.2 er implementert og lokalt backendtestet på aktiv featurebranch, men venter på CI, staging og eiergodkjenning; ingen offentlig bildebruk

**Teknisk sist verifisert:** 2026-08-11

**Teknisk verifisert mot:** fase 2-applikasjonsversjonen i merge-commit `6768af8a3b48314aec028ec5972939c6ef0e38e8`, senere additive fase 3-leveranser, stagingbranchens runtimecommit `17919df0d8778ad2600914d4459415466bfcf8e2` og aktiv 3D.2-featurebranch basert på merge-commit `9be5516`. Fase 3B.1R kjørte den isolerte harnessen lokalt mot 24 rettighetsavklarte fixtures og godkjente 36 MP som konfigurerbar decoded-pixel-standard, variantspesifikk no-upscale, advisory kvalitetsmål og profilfri output etter eksplisitt sRGB-normalisering; private kilder og full/visuell evidens forblir Git-ignorert. Modell-, selection-, release- og processinggrunnmuren gjennom migrasjon `0026` er verifisert. Fase 3D.1s review-hardening er testet lokalt med full Django discovery på 336 backendtester, 64 berørte image-/candidate-/runtime-tester, 3 stagingkontrakttester, ShellCheck 0.10.0, 15 frontendtester, frontendbuild og begge produksjonscontainerbuildene. GitHub CI kjørte de samme 336 backendtestene og 3 stagingkontraktene, med grønn ShellCheck 0.9.0 og alle fem jobber grønne. Ny runtimecommit ble deployet kontrollert til staging med feature fortsatt aktivert, grønn system check, API-only imagemounts, 4 assets, 12 renditions, 4 aktive selections, 0 public releases, 0 manglende filer, 0 checksumavvik, grønn orphan dry-run og tre `200`-smokes. Den tidligere persistence-, Borg backup- og restore-evidensen er fortsatt gyldig. Prosjekteier godkjente den visuelle 3D.1-gaten med Parkenfestivalen som Logo/contain og Bodø Bluesklubbs forventede no-upscale-beskyttelse for et for lite Foto. 3D.2-kontrakten er implementert på featurebranch og samlet lokalt verifisert med 365 backendtester, 22 frontendtester, 10 Playwright-tester, migrasjons-/staging-/backupkontrakter og begge produksjonscontainerbyggene. Ordinær CI, stagingverifikasjon og prosjekteiers visuelle godkjenning av 3D.2 gjenstår. PUBLIC, public serving og legacybildene er uendret. Se [stagingaktiveringen 2026-08-10](STAGING_IMAGE_RUNTIME_ACTIVATION_2026-08-10.md) og [backupaktiveringen 2026-08-02](STAGING_BACKUP_ACTIVATION_2026-08-02.md).

**Produkt-roadmap sist oppdatert:** 2026-08-11

**Arbeidsflyt sist kontrollert:** 2026-07-28

**Ansvar:** Prosjekteier + ChatGPT for prioritering og produktretning. Codex for oppdatering etter implementering.

## Aktiv utviklingsfase

Fase 1 i [ROADMAP.md](ROADMAP.md) ble gjennomført 2026-07-29. Den skrivebeskyttede baselinen verifiserte server-, container-, bygg-, proxy-, cache-, PUBLIC- og Editor-tilstanden. Hoveddesignet på forsidene i Editor CRM og PUBLIC er godkjent designreferanse. Øvrige sider, kort og komponenter skal videreutvikles innenfor denne visuelle retningen.

Fase 2 ble gjennomført 2026-07-30 etter teknisk stagingverifisering, kontrollert reparasjon av fire private primære legacytelefonkontakter og prosjekteiers visuelle sluttkontroll.

Fase 3A kartla deretter dagens thumbnail-, bilde-, storage-, import- og kortflyt uten endringer. [ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) er godkjent som arkitekturgrunnlag.

[Fase 3B.1](PHASE_3B1_IMAGE_RENDITION_SPIKE.md) har gjennomført en isolert bildebehandlings- og renditionprototype med syntetiske fixtures. Pillow og pyvips/libvips, sikker dekoding, contain/cover, fokus, formater, determinisme, fallback og ressursbruk er målt. Prosjekteier har godkjent Pillow bak intern adapter, statisk JPEG/PNG/WebP-input, processing profile v1, no-upscale, immutable key-invarianten og 15 MiB som konfigurerbar standard.

[Fase 3B.1R](PHASE_3B1R_REPRESENTATIVE_QUALITY_HARNESS.md) er **GJENNOMFØRT / GODKJENT** etter lokal kjøring og manuell review av 24 rettighetsavklarte fixtures. 36 MP er konfigurerbar decoded-pixel-standard for MVP; ingen universell minimumsdimensjon eller automatisk oppskalering brukes; obligatoriske renditions vurderes separat etter fit, faktisk cropområde og scaling margin. Edge variance og blockiness er advisory uten numerisk hard fail, logowhitespace kan gi warning/manual review, og offentlig MVP-output normaliseres eller konverteres til sRGB før crop/resize og skrives uten innebygd ICC-profil. Untagged registreres som antatt sRGB; korrupt/uleselig ICC er kontrollert teknisk feil. Kildebilder, privat manifest og visuell/full evidens forblir Git-ignorert.

[Fase 3B.2](PHASE_3B2_STORAGE_RESTORE_SPIKE.md) er teknisk gjennomført som isolert prototype. Den målte separate Django-storagealiaser, gjenbrukt processing artifact key, separat public release key, private/public Moto-buckets, versioning, purge/cache, deny-journal, T0–T5 restore-reconciliation, backupstrategier og statisk fallback. Prosjekteier godkjente 2026-08-01 de leverandøruavhengige prinsippene om to-key-kontrakt, en aktiv public rendition-store uten tilgjengelige historiske public versjoner, kontrollert public delivery, private originaler, hybridbackup, fail-closed restore, varig deny-journal/read-model og idempotent purge. ADR-008 har senere valgt lokal host-persistent storage for første MVP; providerkravene fra prototypen er derfor betingede dersom objektlagring senere tas opp igjen.

Fase 3B.3 er **GJENNOMFØRT / GODKJENT** som arkitektur- og kontraktgate. [ADR-007 punkt 25](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md#25-fase-3b3-godkjent-public-release-identity-og-key-kontrakt) fastsetter tilfeldig UUIDv4 som separat immutable public release identity og relative canonical keys på formen `releases/<release_uuid>/<variant>.<ext>`. Selection-revisjon, tenant-/Organization-identitet og artifact-hash inngår ikke i keyen. Replacement, restore og senere autorisert republisering får alltid ny release-ID, mens tidligere ID-er og keys forblir varig reservert. Fase 3B.3-A implementerer de valgte modellene, immutable relasjoner og snapshots, manager-/modellbeskyttelse, PostgreSQL-constraints og domenetjenesteinvarianter. Public storage-reservasjon, permanent journal i separat failure-domain, storage-runtime og projection er ikke implementert.

[ADR-008](../decisions/ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md) velger en enklere operasjonell MVP: app, database og aktiv media på dagens Hetzner Cloud-server, lokale navngitte Django-storagealiaser og kryptert Borg-backup til separat Hetzner Storage Box. S3/AWS/Backblaze/CDN utsettes. Backupgrunnmuren er **ACTIVE** etter verifisert Storage Box, kryptert repository, separat recovery-custody for minst to ansvarlige, første backup, full repository-check, isolert restore av samme arkiv, Storage Box-snapshot, nyere synlig Cloud Backup og aktiverte timere. Første backup tok 8 sekunder og restore-smoke 8,7 sekunder. Foreløpig RPO er inntil omtrent 24 timer pluss timerforsinkelse; restore-smoke-målingen er evidens, ikke et løfte om full katastrofe-RTO.

Baselinen fant ingen eksisterende `/app/imports`-, `/app/exports`- eller host-mediafiler. De to bildealiasene har nå host-persistente mountpoints, mens Django default storage fortsatt peker til `/app` uten persistent import-/eksportmount; nye generelle FileField-filer kan derfor gå tapt ved recreate. Aktiv Storage Box er BX11 med 1 TB i FSN1, med kapasitetsreview ved 60–70 prosent faktisk bruk og 20–30 prosent ledig margin.

Det separate infrastrukturløpet for ADR-008 er fullført. Første fase 3C-leveranse innførte `IMAGE_ASSET_FEATURE_ENABLED=False` som standard og separate lokale `FileSystemStorage`-aliaser for private originaler og artifacts. Fase 3C.7 bruker aliasene gjennom en intern upload-only tjeneste når feature eksplisitt aktiveres. Tjenesten validerer, normaliserer og renderer før den skriver original og tre renditions med interne tenant-scopede keys, eksakt no-clobber og byte-/checksumverifikasjon, og committer deretter et komplett databaseaggregate atomisk. Ingen filer serveres, canonical public release keys materialiseres ikke, og legacybildeflyten er uendret. Permanent reservation-/deny-journal og senere serving-, purge-, API-, retention-, sync/async- og observabilitygater blokkerer fortsatt offentlig bildebruk.

Asset-/renditiongrunnmuren fra PR #19, `OrganizationImageSelection`-skjemaet fra PR #20, PR #21s locking-/replacement-kjerne og PR #22s fjerning til fallback er merget. Fase 3C.6 fullfører den planlagte ordinære selection-livssyklusen med `restore_archived_organization_image_selection`: kommandoen gjenoppretter én eksplisitt, eldre og arkivert asset-selection som en helt ny aktiv revisjon og registrerer `selection_restored`. Restore-kilden og dagens aktive selection forblir historiske rader; bare dagens aktive status arkiveres. Restore kopierer det eksisterende rendition-settet, alt-teksten og offentlig kreditering uten ny approval eller proveniens. Endret godkjenningsgrunnlag eller presentasjonsinnhold skal fortsatt bruke vanlig replacement. Alle tre offentlige selection-kommandoer bruker samme tenant-scopede `Organization`-lås, capabilitymatrise, `expected_revision` og atomiske eventskriving. Eventhistorikken er append-only på applikasjons-/ORM-nivå, ikke database-WORM, og databasen kan ikke alene bevise at restore-kilden var arkivert og tilhørte samme tenant og organisasjon; dette håndheves av domenekommandoen.

Fase 3D.1 er merget med PR #30 og legger til den første offisielle kandidatflyten i intern API og Editor. En produksjonsrettet fetchadapter validerer alle DNS-resultater, binder forbindelsen til validert global IP, revaliderer redirects, avviser downgrade/credentials/private adresser og håndhever timeout, MIME og 15 MiB. Discovery bruker bare `Organization.website_url`, lagrede OG-verdier og maksimalt én sidefetch, returnerer maksimalt seks dedupliserte kandidater og lagrer ingen kandidatmodell. Kortlivede signerte refs binder kandidat og senere approval til tenant, Organization og bruker. Kandidat-preview er ephemeral; bare valgt kandidat sendes gjennom 3C.7. Eksplisitt approval bruker eksisterende locking/replacement og eventproveniens. Processing eller discovery oppretter aldri selection. Featureflagget er fortsatt avslått som kode-default, men 3D.1 er teknisk aktivert i staging etter grønn persistence-, backup-, restore- og visuell gate. Minimal dry-run-first orphan-cleanup er implementert.

Fase 3D.2 er implementert på aktiv featurebranch og utvider den prioriterte brukerreisen til offisiell nettside/Open Graph → Brave Image Search → limt direkte URL → manuell upload. Brave-forslaget bruker alltid lagret aktørnavn som basis og legger bare til kommune automatisk når nøyaktig én er lagret. Flere kommuner, kategori og aktivt tilknyttet person krever eksplisitt valg; tags brukes aldri, og querybygging og lokal rangering bruker ingen AI. Eksakt query og querykilder er synlige og redigerbare. Provideradapteren sender `country=NO`, `search_lang=nb`, `safesearch=strict`, `spellcheck=false` og `count=30`; `nb` er nødvendig fordi den offisielle enumen ikke støtter `no`. Full providerrespons lagres aldri; bare query og normaliserte nødvendige kandidatfelt beholdes i kortlivede signerte refs, ikke i en persistent kandidatmodell eller søkehistorikk, og valgt Brave-event lagrer ikke providerens bilde-/side-URL under standardvilkårenes lagrings-/cachingbegrensning. Braves egne standard query-logger kan beholdes i opptil 90 dager; Zero Data Retention krever Enterprise/egen avtale og er en separat providergrense fra appens omtrent 30 minutter gamle signed-ref.

Editor har norske provider-/fetch-/processingfeil, fokusforvalg Venstre/Midt/Høyre og Topp/Midt/Bunn, veiledende live crop-preview for Foto og serverrenderte square/landscape/share-previews som fasit før approval. Asset-alttekst kan være tom uten skjult fallback; whitespace-only avvises, mens eksplisitt systemfallback-selection fortsatt krever tekst. Schema-migrasjon `0027` endrer bare felter og constraints og omskriver ingen data. Den kan reverseres før blanke verdier finnes, men er forward-only etter første blanke asset-/event-alt; operativ rollback er da feature-off og fremoverrettet retting. Pre-deploy-backup må tas og verifiseres før aktivering, og skjult utfylling med aktørnavn er aldri en rollbackmekanisme. Samlet lokal kontroll er grønn; CI, staging og prosjekteiers visuelle 3D.2-godkjenning gjenstår. Før en Brave-nøkkel aktiveres må prosjekteier eller annen avtaleeier også dokumentere redaktørenes dekning under gjeldende standardvilkår punkt 4(c) og nødvendige personvernvarsler eller samtykker for querydata. Public release, materialisering, projection, serving, PUBLIC, persistent kandidat, permanent journal og retentionpolicy er uendret og ikke levert av 3D.2.

Den langsiktige relasjonsspesifikke kontaktmodellen fra [ADR-005](../decisions/ADR-005-CONTACT_ARCHITECTURE.md) kommer fortsatt senere. Internasjonal telefonmodell skal spesifiseres i et eget ADR ved overgangen fra fase 3 til fase 4 og implementeres tidlig i fase 5; dette blokkerer ikke fase 3.

## Godkjent bildearkitektur – domenegrunnmur og intern processing implementert

ADR-007 beslutter følgende konseptuelle flyt:

```text
ImageCandidate
    → kontrollert fetch og teknisk validering
    → tenant-eid ImageAsset med privat original
    → OrganizationImageSelection
    → ImageRendition
    → én felles public image projection
```

Godkjente hovedprinsipper:

- assetet eies av tenant, kan finnes før en aktør og kobles gjennom en typed aktør-selection
- bare ett bildevalg er aktivt per aktør; et låst bilde erstattes bare gjennom eksplisitt approval og replacement
- selection peker til ett eksakt immutable rendition-sett som bærer fit, fokus og prosesseringsversjon
- viktige overganger registreres i append-only bildehistorikk
- én rask og versjonert godkjenning brukes uten obligatoriske juridiske detaljfelt
- kreditering er valgfri uten konkret krav
- formell takedown fjerner offentlig bruk, går til fallback og beholder privat karantene og historikk
- deterministic Kreative Norge-fallback finnes som square, landscape og 1200 × 630 share
- public API utvides additivt med strukturert bildeobjekt og midlertidige deprecated URL-aliaser
- lokal utvikling, staging og første produksjons-MVP bruker navngitte filesystemaliaser gjennom Djangos `STORAGES`; aktiv media forblir på dagens server og objektlagring vurderes bare på nytt ved dokumentert behov
- Import 2.0 skal senere bruke `KEEP_LOCKED_IMAGE`, `SET_APPROVED_IMAGE` og `USE_APPROVED_FALLBACK` uten nettverk eller bildebehandling i commit
- ingen bildehandling endrer aktør-, person- eller kontaktpublisering

Godkjent processing profile v1 bruker `square` 512 × 512 og `landscape` 800 × 450 som WebP quality 82 for foto, `share` 1200 × 630 som ikke-progressiv JPEG quality 85, PNG for logo med alpha og WebP/JPEG for fallback. Format, encoderinnstillinger, source checksum, fit, fokus, variant og processing-version inngår i immutable key. Maksimal decoded pixelmengde er 36 MP som konfigurerbar MVP-standard, og maksimal kildefilstørrelse forblir 15 MiB. Offentlig output normaliseres eller konverteres eksplisitt til sRGB før crop/resize og skrives profilfritt.

Fase 3C implementeres additivt bak featuregaten. Fase 3B.1R med representativ kvalitet og sRGB, fase 3B.3 release identity-/key-kontrakten, fase 3B.3-A-domenegrunnmuren og fase 3C.7s interne processing/storage er gjennomført. Host-persistente stagingpaths er aktivert og restore-verifisert. Før public serving kan aktiveres gjenstår same-origin/media-origin-serving; lokal cache- og purgekontrakt; permanent reservation-/deny-journal i separat failure-domain og materialisert read-model med journalcursor og fail-closed reconciliation; eventuell skadevarekontroll og bakgrunnskø dersom en konkret risiko krever det; endelig public API-schema og alias-til-variant-mapping; retensjonsmekanisme; sync/async-grense og observability. SVG er fortsatt avvist; eventuell sikker rasterisering er en senere behovsdrevet gate. S3, CDN, ekstern IAM, bucket-policy, KMS, Object Lock og provider-spesifikk `versionId`-/purgeverifikasjon er bare en betinget senere gate dersom objektlagring tas opp igjen på grunn av dokumentert behov.

Godkjent fase 3B.2-kontrakt skiller intern artifact identity fra public release identity. Aktiv public rendition-store er unversioned eller likeverdig uten tilgjengelige historiske public versjoner; første MVP leverer senere gjennom en kontrollert same-origin/media-origin fra lokal host-persistent storage. Private originaler skal forbli private. Hybridbackup inkluderer aktive rendition-bytes, mens deny-journalen har separat failure-domain og alltid avstemmes fail-closed før public serving etter restore. Lokal serving/purge og permanent journal er fortsatt åpne; backup-RPO og restore-smoke er foreløpig målt, mens full katastrofe-RTO fortsatt er åpen. Ekstern S3/CDN er utsatt.

Godkjent fase 3B.3-kontrakt gjør public release identity til en separat, varig reservert UUIDv4 og bruker canonical relative keys `releases/<release_uuid>/<variant>.<ext>`. R1 → R2 kan bruke identiske `ImageRendition`-bytes uten ny encoding, men R2 får alltid ny UUID og nye keys. Fase 3B.3-A bevarer mappingen til tenant, Organization, selection, rendition-sett og artifact gjennom immutable relasjoner og snapshots uten å eksponere disse identitetene i keyen. Hver public key genereres internt og valideres mot eksakt builder-resultat for release-ID, variant og outputformat; caller kan ikke levere fri key. Runtime, permanent journalteknologi, serving, purge, unpublish, fallback-key, API og projection er fortsatt separate gater.

## Verifisert fase 1-baseline

- lokal og GitHub `main` var synkronisert på `f6f03d67ba0c5d3afbe258fb356248e7075c4b49`
- staging-repoet var rent på `ea8b8762aecdff760728139b1659f7d3a43445c7`; de åtte nyere commitene på `main` endret ikke kjørende applikasjonskode
- API-koden i imaget kunne knyttes til serverrepo-SHA gjennom innebygd Git-metadata og filhashes
- web-imagets eksakte commit var ikke merket, men JS- og CSS-bundles matchet ren build fra dagens `main`
- HTTPS leverte de samme bundlehashene som web-containeren, også med cache-busting
- nginx og Caddy leverte forventet kjede; proxy og Cloudflare-cache viste ikke gamle frontendfiler
- Django system check og PostgreSQL readiness var grønne, og de kjørende containerne hadde ingen restarter
- PUBLIC desktop/mobil og autentisert Editor ble kontrollert; Editor-forsiden er godkjent designreferanse
- observerte kort-, bilde-, tag- og layoutavvik er lagt til fase 3 eller fase 5 og ble ikke rettet i baselinen
- ingen kode, data, publiseringsflagg, containere, tjenester eller deploy ble endret i fase 1

Detaljert, datert evidens finnes i [FRONTEND_BASELINE_2026-07-29.md](FRONTEND_BASELINE_2026-07-29.md). Dette dokumentet er fortsatt autoritativ nåstatus.

## Fase 2-baseline

Det konkrete undersøkelseseksemplet viste en person med verdi i direkte `Person.phone`, men uten noen `PersonContact` av type `PHONE`. Personen hadde bare en lagret e-postkontakt. Direkte telefon kan derfor ikke få egen offentlig kontroll og skal heller aldri brukes som PUBLIC-fallback.

Kodekartleggingen viser samtidig at dagens person-API synkroniserer direkte `Person.email` og `Person.phone` til private primære kontakter ved ny lagring. Avviket gjelder derfor eksisterende legacy-data som ikke har gått gjennom denne synkroniseringen. `repair_person_contacts` reparerer før fase 2 bare e-post.

Editor-baselinen viste fire utrygge forhåndsvalg i opprettingsflytene:

- offentlig e-post på ny kontaktperson
- offentlig telefon på ny kontaktperson
- publisering av ny kontaktperson
- publisering ved kobling av eksisterende person

Alle fire skal være avslått som standard i fase 2. Dette endrer ikke eksisterende lagrede publiseringsflagg.

Fase 2-leveransen fra PR #12, merget i `6768af8a3b48314aec028ec5972939c6ef0e38e8`, implementerer:

- eksplisitt `--contact-type PHONE` i den bakoverkompatible, dry-run-først `repair_person_contacts`-kommandoen
- tenant-filter, idempotens og kandidat-/konfliktrapport med interne ID-er uten kontaktverdier
- privat primær telefonkontakt ved entydig lokal/test-apply
- alle fire nye publiseringsvalg avslått som standard og nullstilt ved faktisk aktør- eller tenantbytte
- tydeligere Editor-tekst for personpublisering kontra offentlig e-post/telefon
- additiv offentlig `Person.title` i aktivt API og PUBLIC HTML

Ingen schema-migrasjon inngår. Kodeleveransen endret ikke eksisterende publiseringsflagg og kjørte ingen data-apply ved merge eller deploy. Den separate, senere stagingreparasjonen ble gjennomført etter uttrykkelig godkjenning og backup som beskrevet nedenfor; produksjon ble ikke endret.

## Verifisert fase 2-stagingstatus

PR #12 ble merget med ordinær merge-commit og deployet kontrollert til staging 2026-07-29. Staging-repoet var rent på merge-commiten da API- og web-imagene ble bygget og startet.

- PostgreSQL readiness, Django system check og migrasjonsstatus var grønne
- API-, web- og databasecontainer kjørte; API og web hadde ingen restarter etter ny oppstart
- HTTPS, auth-session, PUBLIC HTML og aktivt public API svarte `200`
- `check_public_actor_links` kontrollerte `122` publiserte aktører og `122` kortlenker uten brutte lenker
- JavaScript-bundlen `index-DvXY3g5v.js` ble levert fra staging, og SHA-256 var identisk over HTTPS og i web-containeren
- stagingbyggets Editor nullstilte ny-personskjema, feiltilstand, koblingsstatuser og alle fire nye publiseringsvalg ved faktisk aktørbytte; kontrollen sendte ingen tenantmutasjoner
- eksisterende `Person.title` ble verifisert i både aktivt public API og PUBLIC HTML
- person uten tittel fikk ingen tom tittelrad, og direkte `Person.phone` ble ikke brukt som PUBLIC-fallback
- tenant-avgrenset `PHONE`-dry-run for `musikkontoretnord` undersøkte `49` personer, fant `4` kandidater og ingen konflikter; kandidat-ID-ene var `1`, `2`, `132` og `150`
- etter streng kandidatkontroll og verifisert PostgreSQL-backup opprettet den godkjente `--apply`-kjøringen nøyaktig fire private primære `PHONE`-kontakter, kontakt-ID `233`–`236`, for de fire kandidatene og rapporterte `changes_applied=4`
- umiddelbar etterfølgende dry-run rapporterte null kandidater, null konflikter og `changes_applied=0`
- felt- og fingeravtrykkskontroll bekreftet at eksisterende `PHONE`, samtlige `EMAIL`, direkte persontelefoner og relevante Organization-/OrganizationPerson-publiseringsflagg var uendret
- Editor-API viste de fire nye radene som primære og private; aktivt PUBLIC API og PUBLIC HTML eksponerte ingen av dem
- PostgreSQL readiness, Django system check, migrasjoner, HTTPS og `122` av `122` PUBLIC-kortlenker var fortsatt grønne etter kjøringen

Prosjekteier kontrollerte deretter undersøkelseseksemplet visuelt i staging og bekreftet at telefonen finnes under Kontaktkanaler, at Primær er valgt og at «Gjør dette telefonnummeret offentlig» er avslått. De øvrige tre kandidatene var allerede verifisert gjennom preflight, felt- og fingeravtrykkskontroll, Editor-API og PUBLIC-smoke. Denne uttrykkelige produktgodkjenningen lukket fase 2 den 2026-07-30.

## Implementert

- tenant-basert CRM for aktører og personer
- koblinger mellom aktører og personer
- flere kontaktkanaler per person
- kategorier, underkategorier og tenant-spesifikke tags
- roller via `TenantMembership`
- intern React-editor med rollebasert tilgang
- public API for publiserte aktører
- public HTML-visning, foreløpig kun brukt i staging
- PUBLIC HTML-detaljsider med kanonisk ID-rute og legacy orgnummer-redirect
- felles PUBLIC-regel for personkontakt i HTML og API: aktiv kobling med `publish_person=True` og kontaktkanal med `PersonContact.is_public=True`
- synkronisering mellom `Person.email`/`Person.phone` og primær intern `PersonContact`
- importjobber med opplasting, parsing, normalisering, preview, validering, matching, AI-forslag, review, beslutninger, commit, commit-logg og feilrapport
- grunnmodell og grunn-API for eksportjobber
- Docker-basert lokal kjøring og stagingoppsett

## Delvis implementert

### EXPORT

`ExportJob`, eksporttyper, CSV/XLSX-formatvalg, filtre, feltvalg og grunnleggende API finnes. Faktisk filgenerering, nedlasting og komplett brukerflyt er ikke bekreftet ferdig.

### PUBLIC

Public API og HTML-visning fungerer. HTML-visningen brukes foreløpig bare i staging. Endelig API-kontrakt og integrasjon mot Musikkontoret.no er ikke ferdigstilt.

### Roller og tilgang

Kjerne-rollene og tenant-scope håndheves i backend. Invitasjonsflyt, full administrasjon av medlemmer og den langsiktige modellen for eksterne tenant-rom må videreutvikles.

## Prioritert produktrekkefølge

### 1. Staging- og frontend-baseline – gjennomført 2026-07-29

Før det endres kode eller deployes, skal en skrivebeskyttet diagnose fastslå:

- repo-commit på serveren
- faktisk commit og bygg i kjørende containere
- om frontend-bundles, statiske filer, bilder eller cache er utdaterte
- påvirkning fra nginx, Caddy og nettlesercache
- forskjeller mellom lokal `main` og staging
- hvilke observerte avvik som er reelle regresjoner på `main`

### 2. Liten kontaktstabilisering – gjennomført 2026-07-30

Den avgrensede mellomleveransen sporer offentlig telefon gjennom Editor, API og PUBLIC, viser `Person.title` offentlig når den finnes og har regresjonstester for e-post, telefon, personlenke og tittel. Den generelle årsaken ble rettet, fire legacytelefoner ble reparert privat etter backup, og teknisk og visuell stagingkontroll ble godkjent. Dette er ikke full implementering av [ADR-005](../decisions/ADR-005-CONTACT_ARCHITECTURE.md).

### 3. Thumbnail-, bilde- og kortarkitektur – fase 3D.2 implementert på featurebranch

Fase 3A-kartleggingen, ADR-007 og de isolerte prototypene i fase 3B.1 og fase 3B.2 er gjennomført. Fase 3B.1R har i tillegg gjennomført representativ lokal kvalitetsevidens og fått godkjent decoded pixel-, dimensjons/no-upscale-, advisory kvalitets- og sRGB-kontrakt. ADR-008s lokale Hetzner-MVP er **ACTIVE**. Fase 3C har additive bilde-/selection-modeller og atomiske kommandoer for locking/replacement, ordinær fjerning til fallback og restore som ny revisjon. Fase 3C.7 legger til feature-gated ingest, processing, privat original-storage og intern artifact-storage med immutable tenant-scopede keys, eksakt no-clobber, post-write-verifikasjon og atomisk/idempotent databaseaggregate. Fase 3D.1 er teknisk aktivert og visuelt godkjent i staging med host-persistent storage, verifisert backup/restore og minimal orphan-cleanup. Fase 3D.2s Brave-, URL-, upload-, fokus-, live crop- og valgfrie alttekstflyt er implementert og målrettet backendtestet på featurebranch, men CI-, staging- og eiergater gjenstår. `image_renditions_public` er fortsatt ikke offentlig serving. PUBLIC, canonical `releases/...`-materialisering, permanent reservation-/deny-journal, cache/purge og retentionpolicy er heller ikke implementert.

Deretter skal Import 2.0 gjennom en egen produkt- og UX-designfase før større kodeendringer. Dagens importmotor skal gjenbrukes der den er solid, men skal ikke låse den nye brukeropplevelsen.

Detaljert faseinndeling, AI-prinsipp og senere produktområder finnes i [ROADMAP.md](ROADMAP.md).

## Verifisert kontaktstatus

### Implementert mellomregel

Første mellomleveranse er implementert og deployet til staging. Problemet skyldte en todelt kontaktarkitektur og forskjellige regler i Editor, import og PUBLIC:

- `Person.email` og `Person.phone` er parallelle med `PersonContact`
- Editor viste og lagret i hovedsak direktefeltene
- enkelte opprettingsflyter skriver både direktefelt og `PersonContact`
- public API brukte eksplisitte `PersonContact`
- public HTML kunne falle tilbake til direkte person-e-post
- import kunne oppdatere begge kilder og endre publiseringsflagg

Implementert mellomregel:

- `OrganizationPerson.publish_person` bestemmer om personen vises som kontaktperson offentlig
- `PersonContact.is_public` bestemmer om hver e-post eller telefon vises offentlig
- `Person.email` og `Person.phone` brukes ikke som PUBLIC-fallback
- Editor CRM er intern og viser kontaktkanaler også når de ikke er offentlige
- import støtter `person_email_public` og `person_phone_public` som tri-state publiseringsfelt
- `repair_person_contacts` kan opprette manglende private primære e-postkontakter fra `Person.email`
- `repair_person_contacts --contact-type PHONE --tenant musikkontoretnord --apply` ble kjørt kontrollert på staging 2026-07-30 etter backup og opprettet fire private primære telefonkontakter uten å endre publiseringsflagg
- `publish_existing_email_contacts` ble kjørt på staging 2026-07-26 etter backup og gjorde eksisterende e-postkontakter offentlige, med tre relasjonsspesifikke unntak på `publish_person=False`

Staging etter datakjøringen:

- `email_contacts_total=164`
- `email_contacts_public=164`
- `email_contacts_private=0`
- `active_links_total=170`
- `active_links_publish_true=167`
- `active_links_publish_false=3`

De tre unntakene er:

- `Nordland fylkeskommune` / `Kathrine Schjem`
- `Nordland fylkeskommune` / `Ole-Thomas Kolberg`
- `Bådin` / `Jonas Jørgensen Moe`

Målarkitekturen er godkjent i `docs/decisions/ADR-005-CONTACT_ARCHITECTURE.md`:

- `PersonContact` blir eneste autoritative kilde
- primærkontakt og offentlig kontakt holdes adskilt
- offentlige kontaktkanaler velges per aktør–person-kobling
- HTML, API og Editor-preview bruker én offentlig projeksjon
- migreringen gjennomføres additivt og reverserbart

Den langsiktige ADR-005-modellen er ikke implementert. Direktefelt finnes fortsatt av kompatibilitetshensyn, og dagens `PersonContact.is_public` er fortsatt globalt for kontaktkanalen, ikke relasjonsspesifikt.

## Godkjent fremtidig retning for internasjonal telefon

Den konservative PHONE-reparasjonskommandoen fra fase 2 beholdes uendret som en avgrenset legacy-reparasjon. Internasjonal telefonarkitektur blokkerer ikke fase 3.

Godkjent beslutningsgate og tidsplan:

- et eget ADR for internasjonal telefonmodell, landkontekst og normalisering skal utarbeides ved overgangen fra fase 3 til fase 4
- fase 4, produkt- og UX-design for Import 2.0, kan ikke godkjennes som ferdig før dette ADR-et er godkjent
- den nye telefonarkitekturen skal implementeres tidlig i fase 5
- en stabil internasjonal telefonmodell er en forutsetning for full telefonmatching i fase 6

Det senere ADR-et skal bygge på disse godkjente prinsippene:

- original/raw telefonverdi bevares
- normalisert sammenligningsverdi lagres separat
- nasjonale numre får uttrykkelig land-/regionkontekst
- fullstendige internasjonale numre støttes
- internnummer kan håndteres separat
- én sentral backendtjeneste brukes av Editor, API, import, eksport og reparasjonsverktøy
- tvetydige verdier går til review og slås ikke sammen automatisk
- normalisering og matching aktiverer aldri publisering

Denne retningen er besluttet, men telefonarkitekturen er ikke implementert og et nytt ADR er ikke opprettet eller godkjent.

## Planlagt senere

- Google Sheets som importkilde
- Checkin som importkilde
- Mailmojo som importkilde
- komplett eksportmotor
- auditlogg og sterkere sporbarhet

Google Sheets, Checkin og Mailmojo finnes foreløpig bare som reserverte kildetyper.

## Separat infrastrukturløp

Sikker automatisk staging-deploy er planlagt utenfor produktfasene og blokkerer ikke fase 1. Manuell og kontrollert deploy gjelder inntil det finnes en testet kjede med minst privilegert deploy-bruker, GitHub Environment og secrets, grønn obligatorisk CI på `main`, deploy-lås, databasebackup, health/smoke-kontroll, rollback og tilstrekkelig logging/hardening. Serverens root-nøkkel skal ikke lagres som GitHub-secret.

## Teknisk workflow-status

- GitHub er felles sannhetskilde mellom lokal kode, Codex og ChatGPT.
- ChatGPT kan lese repoet når prosjekteier ber om oppdatert analyse.
- Fredrik Development System er installert som prosjektets utviklingsplattform.
- Repo-reglene ligger i `AGENTS.md`, og 15 prosjektbaserte Codex-skills ligger i `.agents/skills/`.
- `$fortsett-prosjekt` er installert som en tynn Codex-bro fra ChatGPT-handoff til `$start-arbeidsokt`; ChatGPT-rutinen med samme navn er dokumentert separat.
- `$start-arbeidsokt` og `$avslutt-arbeidsokt` danner et skrivebeskyttet SESSION-lag rundt de fire arbeidsnivåene, i tråd med `ADR-006`.
- Alle 15 skills er strukturelt validert. `$fortsett-prosjekt` er eksplisitt runtime-testet i en ny skrivebeskyttet Codex-session med konfliktmerking, full delegering til `$start-arbeidsokt` og uendret arbeidsmappe.
- Fredrik Skill Pack, ChatGPT og Codex er prosjektets valgte arbeidsverktøy. Claude eller Superpowers er ikke valgt som en parallell arbeidsflyt; nyttige prinsipper fra andre rammeverk kan innarbeides i det eksisterende systemet når de gir konkret verdi.
- Codex skal lese `docs/README.md`, dette dokumentet og relevant feature-/arkitekturdokument før implementering.
- Større implementeringer krever godkjent ADR.
- Funksjonelle endringer skal ledsages av dokumentasjonsoppdatering eller eksplisitt vurdering av at dokumentasjonen fortsatt er korrekt.
- Automatisk staging-deploy er et separat infrastrukturløp og er ikke implementert eller verifisert.

## Åpne avklaringer

- valgt mekanisme for automatisk staging-deploy
- obligatoriske tester og CI-gates før deploy
- endelig kontrakt mellom CRM-public og Musikkontoret.no
- lokal private/public-storage, same-origin/media-origin-serving, cache/purge/verifikasjon, permanent journalteknologi/read-model/cursor og full katastrofe-RTO; S3/CDN og provider-spesifikke gater tas bare opp igjen ved dokumentert behov
- permanent public release reservation-/deny-journal i separat failure-domain, samt SVG-policy, eventuell sikker rasterisering/skadevarekontroll/bakgrunnskø, API-schema, aliasmapping, retensjonsmekanisme, sync/async-grense og observability i fase 3B
- eksplisitt publiseringsfelt for organisasjonens e-post
- roller for kontaktpublisering, bulkpublisering og full kontakt-eksport
- behandlingsgrunnlag og retensjon for kontakt-, import-, eksport- og auditdata
- versjonering av ny public kontaktkontrakt
- om personens offentlige tittel senere skal være koblingsspesifikk
- bibliotek og konkret normaliseringsstandard for internasjonale telefonnumre
- modell- og feltnavn, constraints og API-kontrakt for originalverdi, normalisert sammenligningsverdi, land-/regionkontekst og internnummer
- migrerings-, backfill-, konfliktreview- og rollbackopplegg for eksisterende telefondata

## Dokumentasjonsstatus

`docs/` er autoritativ dokumentasjonsstruktur og er kvalitetssikret på overordnet nivå mot dagens kodebase. PR #10 fullførte session-workflowen og holdt gamle rotbaserte handoff-, `REFERENCE`- og `STATUS`-filer utenfor repoets parallelle sannhetskilder. Den godkjente produktrekkefølgen er dokumentert i [ROADMAP.md](ROADMAP.md).
