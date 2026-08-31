# Roadmap

**Status:** Godkjent strategisk arbeidsrekkefølge

**Sist oppdatert:** 2026-08-31

Roadmapen skiller mellom produktfaser og et parallelt infrastrukturløp. En fase beskriver prioritert rekkefølge, ikke at innholdet allerede er implementert. Større implementering krever fortsatt et godkjent ADR når arbeidet innebærer et vesentlig arkitekturvalg.

## Fase 0 – Arbeidsflyt og én varig sannhetskilde

**Status:** Gjennomført med PR #10.

- GitHub og `docs/` er etablert som varig prosjektminne.
- Fredrik Development System består av `AGENTS.md`, dokumentert workflow og 15 repo-baserte Codex-skills.
- [ADR-006](../decisions/ADR-006-SESSION_WORKFLOW.md) beslutter session-flyten og skillet mellom session-laget og de fire faglige arbeidsnivåene.
- `$start-arbeidsokt`, `$avslutt-arbeidsokt` og `$fortsett-prosjekt` gir kontrollert oppstart, avslutning og kontinuitet.
- Gamle rotbaserte handoff-, `REFERENCE`- og `STATUS`-filer ble holdt utenfor den autoritative dokumentasjonen.
- Genererte Playwright-resultater er ignorert.

Sikker automatisk deploy til staging er ikke en gjenstående del av fase 0. Det er et separat infrastrukturløp og blokkerer ikke videre produktarbeid.

## Fase 1 – Verifiser staging- og frontend-baseline

**Status:** Gjennomført 2026-07-29.

Før ny frontendutvikling skal forskjellen mellom lokal `main`, GitHub, staging og det brukeren faktisk ser, diagnostiseres. Arbeidet starter skrivebeskyttet og skal ikke blandes med retting eller deploy.

Kontrollen skal fastslå:

- hvilken repo-commit serveren har sjekket ut
- hvilken commit og hvilket bygg de kjørende containerne faktisk bruker
- om gamle frontend-bundles, statiske filer, bilder eller cache lever videre
- om nginx, Caddy eller nettlesercache påvirker resultatet
- om observerte avvik er reelle regresjoner på `main`
- hvilke forskjeller som finnes mellom lokal kjøring og staging

Hoveddesignet på forsidene i Editor CRM og PUBLIC er godkjent designreferanse. Øvrige sider, kort og komponenter skal videreutvikles innenfor denne visuelle retningen. Fasen avsluttes med en verifisert baseline og en avgrenset liste over eventuelle feil; den innebærer ikke automatisk retting eller deploy.

Baselinen verifiserte GitHub og lokal `main`, serverrepo, kjørende images og containere, frontendbundles, HTTPS-/cachekjeden, PUBLIC og en autentisert Editor-visning. Kjørende frontendinnhold matchet en ren build fra `main`, og proxy/cache var ikke årsaken til de observerte UI-avvikene. Ingen kode, data eller deploy ble endret som del av fase 1. Datert evidens finnes i [FRONTEND_BASELINE_2026-07-29.md](FRONTEND_BASELINE_2026-07-29.md).

## Fase 2 – Liten stabilisering av kontaktvisning

**Status:** Gjennomført 2026-07-30.

Etter baseline-verifiseringen ble en liten, generell stabilisering gjennomført:

- den generelle telefonfeilen ble rettet og de fire identifiserte legacytelefonene ble reparert som private primærkontakter etter verifisert backup
- nye publiseringsvalg fikk trygge, avslåtte standardverdier og nullstilling ved aktør- eller tenantbytte
- `Person.title` vises offentlig når feltet finnes
- regresjonstester dekker e-post, telefon, personlenke og tittel
- staging og prosjekteiers visuelle sluttkontroll ble godkjent

Dette er ikke full implementering av [ADR-005](../decisions/ADR-005-CONTACT_ARCHITECTURE.md). Den konservative PHONE-reparasjonskommandoen beholdes uendret som en avgrenset legacy-reparasjon, og dagens mellomregel for kontaktpublisering beholdes til en senere, kontrollert migrering.

## Fase 3 – Robust thumbnail-, bilde- og kortarkitektur

**Status:** `CLOSED / VERIFIED`. Fase 3A–3D.2 er gjennomført som tidligere dokumentert. ADR-008s lokale storage-/backup-MVP og ADR-009 fase 3E.1A safety-ledger/off-server anchor er **ACTIVE** i staging. Fase 3E.1B-materialisering er **ACTIVE / VERIFIED**. Fase 3E.1C-controlled serving er **CLOSED / ACTIVE**. Fase 3E.2 er **CLOSED / SHADOW VERIFIED**. Fase 3E.3 API/PUBLIC/head-cutover og fase 3E.4 ledger-v2/formell takedown er **CLOSED / ACTIVE** i staging. Fase 3F legacy-/Import-kontrakt og restore er **CLOSED / VERIFIED** med Import-gaten av i shared staging. Brave er operativt deaktivert for ordinære Editor-sluttbrukere.

Fase 3A kartla dagens legacy URL-, Open Graph-, kort-, import-, storage- og driftsflyt. [ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) er godkjent som arkitekturgrunnlag.

`ImageAsset`, `ImageRenditionSet`, `ImageRendition`, den typed `OrganizationImageSelection` og den organization-typed public release aggregaten er implementert additivt med constraints og migrasjoner. `ImageReviewEvent` og de feature-gated selection-kommandoene dekker atomisk første låsing, replacement, ordinær fjerning fra aktivt asset til systemfallback og restore av en eksplisitt arkivert asset-selection som ny revisjon. Release-tjenesten kan opprette et komplett immutable release-aggregate med interne canonical keys. Fase 3C.7 legger til intern upload-only dekoding, processing, immutable artifact-storage og atomisk asset-/rendition-aggregate. Fase 3D.1 kaller processing og locking gjennom en avgrenset feature-gated API-/Editor-flyt for offisielle kandidater. Fase 3D.2 utvider samme interne flyt med Brave, limt URL, brukerupload, fokusforvalg, live crop-preview og valgfri asset-alttekst. Legacyfeltene `thumbnail_image_url`, `auto_thumbnail_url` og `og_image_url` består for rollback/historikk, men styrer ikke den aktive 3E.3-reisen; faviconflyten er uendret.

Bildeløsningen skal gå fra ustabile eksterne treff til en varig, redaksjonelt kontrollerbar ressurs:

- kandidater i prioritert brukerreise fra offisiell nettside/Open Graph via kontrollert Brave-provider og limt URL til manuell upload
- kontrollert fetch og teknisk validering før menneskelig godkjenning
- tenant-eid asset med privat original og nødvendig proveniens
- typed aktør-selection med fit, ett fokuspunkt, eksplisitt approval og låsing
- valgfri eller påkrevd kreditering når et konkret krav finnes
- kontrollerte square-, landscape- og share-renditions
- deterministisk Kreative Norge-fallback
- én felles image projection for Editor, PUBLIC, public API og delingsmetadata
- append-only historikk for approval, replacement, restore og takedown
- additiv og bakoverkompatibel API- og legacyovergang

Fasen etablerer samtidig et lite, delt frontendgrunnlag for aktørkort og relaterte visningsmønstre:

- aktørkort, bilder, tags, sted, spacing og responsiv overflow
- konsistente farger og kortvarianter
- retting av brune tags i PUBLIC
- robust håndtering av lange stedsnavn
- konsekvent bildeplassering, skalering og sentrering
- mindre avvik mellom Editor- og PUBLIC-kort

Dette er ikke en generell redesign. Øvrige kort og komponenter videreutvikles innenfor den godkjente visuelle retningen fra forsidene.

### Fase 3A – kartlegging og arkitekturbeslutning

**Status:** Gjennomført 2026-07-30.

- skrivebeskyttet kartlegging av backend, frontend, PUBLIC, API, import, storage, drift og åtte kort-/bildevisninger
- godkjent ADR-007 med ansvarsdelingen `ImageCandidate` → `ImageAsset` → `OrganizationImageSelection` → `ImageRendition` → felles public image projection
- godkjente roller, approvaltekst, fallback, retensjon, takedown, storage-retning, API-overgang og fremtidig Import 2.0-kontrakt

### Fase 3B – teknisk prototype og kontrakt

**Status:** Fase 3B-grunnlaget er gjennomført og lokal Hetzner storage-/backup-MVP er **ACTIVE**. Safety-ledgeren er implementert i 3E.1A. Public delivery-/bridge-foundationen og materialiseringsworkflowen er aktive og restore-verifiserte i 3E.1B; 3E.1C-serving/runtime er `CLOSED / ACTIVE`, 3E.2 projection/API-shadow er `CLOSED / SHADOW VERIFIED`, og 3E.3 schema/PUBLIC/head samt 3E.4 ledger-v2/formell takedown er `CLOSED / ACTIVE` i staging.

- [fase 3B.1](PHASE_3B1_IMAGE_RENDITION_SPIKE.md) målte Pillow og pyvips/libvips, format, foreløpige terskler og ressursbruk på syntetiske fixtures
- fase 3B.1 prototypet contain, cover, fokuspunkt, square/landscape/share, deterministisk fallback og statisk nødvariant uten CRM-runtimekobling
- prosjekteier har godkjent Pillow bak intern adapter, statisk JPEG/PNG/WebP-input, outputmappingen WebP/PNG/JPEG, 512 × 512 `square`, 800 × 450 `landscape`, 1200 × 630 `share`, no-upscale, immutable key-invarianten og 15 MiB som konfigurerbar standard
- [fase 3B.1R](PHASE_3B1R_REPRESENTATIVE_QUALITY_HARNESS.md) har kjørt den isolerte harnessen lokalt på 24 rettighetsavklarte fixtures og fått separat evidensgodkjenning; private kilder, manifest og visuell/full evidens forblir Git-ignorert
- 36 MP er godkjent som konfigurerbar decoded-pixel-standard for MVP; det finnes ingen universell minimumsdimensjon, ingen automatisk oppskalering og obligatoriske renditions vurderes separat etter fit, faktisk cropområde og scaling margin
- edge variance og blockiness er advisory, outliers kan gi warning/manual review, og ingen numerisk edge-/blur-/blockiness- eller whitespacegrense er automatisk hard fail
- offentlig MVP-output normaliseres eller konverteres eksplisitt til sRGB før crop/resize og skrives profilfritt; untagged registreres som antatt sRGB, mens korrupt/uleselig ICC er kontrollert teknisk feil
- [fase 3B.2](PHASE_3B2_STORAGE_RESTORE_SPIKE.md) har prototypet separate private/public `STORAGES`-aliaser, lokal filesystemreferanse, Moto 5.2.2, immutable artifact/release keys, absolutte allowlistede media-origins, origin-sletting, purge/takedown, separat deny-journal og backup/restore
- prosjekteier har godkjent to-key-kontrakt, en aktiv public rendition-store uten tilgjengelige historiske public versjoner, kontrollert public delivery, private originaler, hybridbackup, fail-closed restore, varig deny-journal/read-model og idempotent purge; ADR-008 velger lokal host-persistent storage for første MVP og gjør providerkrav betingede
- fase 3B.3 fastsetter tilfeldig UUIDv4 som separat immutable public release identity, canonical relativ key `releases/<release_uuid>/<variant>.<ext>`, organization-typed release aggregate, immutable historisk mapping, eksakt binding til internt builder-resultat og varig reservasjon/no-clobber; selection-revisjon, tenant-/Organization-identitet og artifact-hash inngår ikke i public key
- replacement, restore og senere autorisert republisering får ny release-ID og nye keys selv med samme rendition-sett og bytes; gamle release-ID-er/keys frigjøres eller gjenbrukes aldri, og deny vinner fortsatt over restore
- fase 3B.3-A implementerer `OrganizationImageRelease`, `OrganizationImageReleaseRendition`, migrasjon `0026`, intern UUIDv4-/key-generering og en atomisk feature-gated tjeneste som eneste støttede insertvei for et komplett square/landscape/share-aggregate uten storage-I/O
- immutable relasjoner og snapshots bevarer release-mappingen, mens modell-/managerregler blokkerer støttede ORM-veier for reassosiering, bulk update, upsert/update-conflict og delete; dette er ikke database-WORM eller den permanente eksterne reservasjonsjournalen
- [ADR-008](../decisions/ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md) velger lokale navngitte storagealiaser og stabil lokal Borg `>=1.2.8`/`<1.3.0` med remote path `borg-1.2` til separat Hetzner Storage Box og retention 14/8/12; S3/AWS/Backblaze/CDN utsettes
- repoets backupmodul er ACTIVE etter verifisert Storage Box, kryptert repository, recovery-custody for minst to ansvarlige, første backup, full repository-check, isolert restore av samme arkiv, Storage Box-snapshot, nyere synlig Cloud Backup og aktive timere; detaljert evidens finnes i [aktiveringsrapporten](STAGING_BACKUP_ACTIVATION_2026-08-02.md)
- ADR-009 har valgt ledger-, delivery-, serving-, projection-, API- og takedownretning; SQLite-/host-anchor-/credentialkontrakten og live off-server capability/recovery er **ACTIVE** i 3E.1A, production fallback v1 er aktiv i 3E.3, og 3E.4 har liveverifisert den lokale no-shared-cache-kontrakten; providerpurge ved eventuell senere shared cache og full katastrofe-RTO gjenstår i riktige senere gater
- fase 3B.2 har ikke opprettet CRM-modeller, migrasjoner, API/OpenAPI, Editor, PUBLIC, Import 2.0-integrasjon, bakgrunnskø eller stagingdeploy
- fase 3E.1B har aktivert og verifisert reservation/binding/delivery/materialisering/read-back/activation med syntetisk no-clobber-, crash/restart- og retrybevis; 3E.1C-serving/origins er liveverifisert med HTTP-, fail-closed-, restart-, observability- og backup/restore-evidens; 3E.2 projection/API-shadow er `CLOSED / SHADOW VERIFIED`; 3E.3 API/PUBLIC/head-cutover og 3E.4 ledger-v2/formell takedown er `CLOSED / ACTIVE`

Processing profile v1, fase 3B.1R-kvalitetskontrakten, fase 3B.2-prinsippene og fase 3B.3 release-kontrakten er arkitekturgrunnlag. Fase 3B.3-A er release-domenegrunnmur, fase 3C.7 er intern processing/storage og fase 3D.1 er første interne API-/Editor-kobling. ADR-008-backupen, 3E.1A safety-ledger/off-server restore-gate, 3E.1B-materialisering og 3E.1C-controlled serving er aktivert og restore-verifisert; 3E.2 er `CLOSED / SHADOW VERIFIED`, og 3E.3 har aktivert kontrollert PUBLIC-bildebruk. Fase 3E.4 formell takedown er `CLOSED / ACTIVE` etter ledger-v2-upgrade og live deny-/restore-/republishbevis.

#### Fase 3B.3 – public release identity og key-kontrakt

**Status:** Kontrakt godkjent 2026-08-07; fase 3B.3-A-domenegrunnmur implementert uten runtime.

Kontrakten er dokumentert i [ADR-007 punkt 25](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md#25-fase-3b3-godkjent-public-release-identity-og-key-kontrakt). Fase 3B.3-A legger til en organization-typed release-/release-rendition-grunnmur, migrasjon `0026`, constraints, canonical key-builder, atomisk tjeneste og tester uten storage-, journal-, API-, projection- eller selection-runtimekobling. Implementasjonen bruker beskyttede immutable relasjoner kombinert med snapshots; PostgreSQL håndhever radlokale constraints og unikhet, mens cross-row equality og komplett aggregate håndheves i domenetjenesten og modellvalideringen. ADR-009 beholder reservation-/deny-journal, materialisering, serving og purge som separate 3E-gater.

#### Godkjent operasjonell MVP: lokal Hetzner-storage og backup

**Status:** ACTIVE fra 2026-08-02.

MVP-en bruker:

- dagens Hetzner Cloud-server for app, database og aktiv media
- lokale navngitte Django-storagealiaser og host-persistente mediaområder; dette er aktivert og restore-verifisert for intern bilde-runtime i staging
- daglig kryptert Borg-backup til separat Hetzner Storage Box
- Storage Box-snapshots og Hetzner Cloud Backups som ekstra lag
- obligatorisk dump-, repository- og isolert restore-gate før timeraktivering

Den skrivebeskyttede [serverbaselinen](STAGING_BACKUP_BASELINE_2026-08-01.md) fant et lite database-/filgrunnlag, ingen eksisterende import-/eksportfiler og ingen kolliderende automatisert backup. [Aktiveringen 2026-08-02](STAGING_BACKUP_ACTIVATION_2026-08-02.md) etablerte BX11 med 1 TB i FSN1, kryptert Borg-kjede, separat recovery-custody, første backup, full repository-check, isolert restore, snapshots og aktive timere. [Bildeaktiveringen 2026-08-10](STAGING_IMAGE_RUNTIME_ACTIVATION_2026-08-10.md) etablerte og restore-verifiserte de host-persistente bildeområdene. Default storage for generelle FileField-filer er fortsatt ikke persistent. S3-/CDN-sammenligning tas bare opp igjen ved dokumentert vekst- eller driftsbehov.

### Fase 3C – additiv backend- og storagegrunnmur

**Status:** PR #23 og fase 3C.6 er merget. Den ordinære selection-livssyklusen er komplett bak featuregaten. Fase 3C.7 implementerer intern processing/storage, og fase 3D.1 bruker denne i API/Editor. Intern host-persistent staging-runtime er aktiv og restore-verifisert. Ingen PUBLIC-, public serving- eller releasekobling er aktiv.

Første leveranse har innført `IMAGE_ASSET_FEATURE_ENABLED=False` som standard og lokale `image_originals_private`-/`image_renditions_public`-aliaser med separate, validerte roots. Eksisterende `default` og `staticfiles` er bevart. Settings-load eller system check oppretter ingen mapper eller filer. Fase 3C.7 bruker aliasene bare når den interne tjenesten kalles med feature aktivert.

Andre leveranse legger til `ImageAsset`, `ImageRenditionSet` og `ImageRendition` med provider-nøytrale logiske keys, teknisk metadata, tenant-avgrenset unikhet, numeriske constraints og `PROTECT` mellom asset, sett og rendition. Modellene er ikke koblet til `Organization`, storage, API eller runtime, og featureflagget forblir avslått.

Tredje leveranse legger til `OrganizationImageSelection` som én låst revisjon per rad. Databasen håndhever unik revisjon, positiv revisjon, maksimalt én aktiv selection og eksklusivt asset-/fallbackvalg. Asset-selection peker til nøyaktig ett immutable rendition-sett; fit, fokus og prosesseringsversjon dupliseres ikke. PR #20 med dette skjemaet er merget.

Fjerde leveranse legger til `ImageReviewEvent` og `lock_organization_image_selection`. Eventet beholder snapshots og er append-only gjennom støttede applikasjons-/ORM-veier, men er ikke database-WORM. Kommandoen er den godkjente skriveruten for første låsing og vanlig replacement, er blokkert når featureflagget er avslått og skriver selection og event atomisk. `expected_revision` oppdager konflikter, mens den tenant-scopede `Organization`-raden er concurrency-lås. Redigerer, gruppeadmin og tenant-superadmin kan arbeide i egen tenant; plattform-superadmin må alltid angi target tenant. Proveniens lagres som event-snapshot, men full kandidat-/ingestmodell er ikke implementert.

Fase 3C.5 legger til `selection_removed_to_fallback` og `remove_organization_image_to_fallback`. Kommandoen er eneste godkjente vei fra aktiv asset-selection til systemfallback, arkiverer bare statusen på forrige selection og oppretter ny fallback-revisjon og event atomisk. Den generiske lock-kommandoen kan fortsatt opprette første fallback og erstatte fallback med asset eller asset med annet asset, men avviser asset → fallback og fallback → fallback. PR #22 og fase 3C.5 er merget.

Fase 3C.6 legger til `selection_restored` og `restore_archived_organization_image_selection`. Kommandoen krever en eksplisitt eldre, arkivert asset-selection i samme tenant og organisasjon, revaliderer det komplette rendition-settet og oppretter en helt ny aktiv revisjon med samme rendition-sett, alt-tekst og offentlig kreditering. Restore-kilden omskrives aldri, og restore-eventet peker både på den tidligere aktive selectionen og restore-kilden. Restore er ikke ny approval: eventet lagrer ingen ny godkjenningstekst eller proveniens. Endret approval, alt-tekst, kreditering, fit, fokus eller rendition-sett skal bruke vanlig replacement. Databasen håndhever restore-eventets snapshotform, mens source-status og cross-tenant/-organization-scope håndheves av domenekommandoen.

Fase 3C.7 legger til Pillow 12.3.0 bak intern adapter og `ingest_uploaded_image`. Tjenesten håndhever statisk JPEG/PNG/WebP, 15 MiB, 36 MP, single-frame, EXIF orientation, sRGB, profilfri output og no-upscale. `cover` bruker normalisert fokus eller sentrum; `contain` bruker gjennomsiktig canvas uten fokusavhengighet. Original og tre artifacts får interne tenant-scopede keys og checksums før write, skrives create-only med eksakt-key-kontroll og verifiseres før et komplett databaseaggregate committes eller gjenbrukes. Databasefeil kan etterlate immutable, ikke-servert orphan-bytes for idempotent retry; permanent cleanup er utsatt.

- additive modeller, constraints og migrasjoner
- kontrollert ingest, private originaler og renditions gjennom lokale navngitte storagealiaser
- capability-permissions, approval, locking, audit, retention, karantene og takedown
- feature av frem til test- og datagrunnlaget er godkjent
- ingen varige bildefiler før ADR-008-backupen er ACTIVE og restore-verifisert
- interne bildefiler kan skrives og leses gjennom fase 3D.1s API-/Editor-flyt når feature eksplisitt aktiveres; ingen filer serveres offentlig
- gjenstående runtimegater velges etter konkret brukerreise-/driftsblocker; ingen ny selection-kommando planlegges etter fase 3C.6

### Fase 3D – Editor-flyt for aktørbilde

**Status:** Påbegynt. Fase 3D.1s første offisielle kandidatflyt er merget med PR #30 og teknisk aktivert og visuelt godkjent i staging bak en miljøstyrt featuregate. Fase 3D.2 med presis fokus/zoom er gjennomført og merget til `main` med PR #33, fullverifisert lokalt, CI-grønn, historisk live Brave-verifisert og visuelt eiergodkjent i staging. Brave er operativt deaktivert i påvente av sluttbrukeravtalegaten. Fase 3E.2 etablerte og shadow-verifiserte public image projection; fase 3E.3 har aktivert kontrollert forbruk i PUBLIC og public API. Fallback-/historikk-/takedown-UI gjennomføres bare i den grad det blokkerer denne brukerreisen eller nødvendige sikkerhets-/driftsgarantier.

- offisiell website/Open Graph-discovery, kortlivet signert kandidat, ephemeral kandidat-preview og valgt processing er implementert i 3D.1
- intern square/landscape/share-preview, «Godkjenn og lås bilde» og eksplisitt replacement er implementert i 3D.1
- Brave Image Search, limt URL, manuell upload, norske feiltekster, fokusforvalg, presis X/Y, Foto-zoom, live crop og valgfri asset-alttekst er gjennomført i 3D.2 og merget med PR #33
- ordinær arkivering, restore og historikk; eventuell takedown-UI tas bare inn ved konkret brukerreise og må bruke den nå verifiserte server-side deny-kontrakten
- aktiv selection-preview er intern; preview fra samme public projection som PUBLIC gjenstår

#### Fase 3D.2 – gjennomført og merget; CI-, staging- og eierverifisert; Brave operativt deaktivert

Editor presenterer kildene slik:

1. offisiell nettside / Open Graph
2. Brave Image Search
3. limt direkte bilde-URL
4. manuell upload

Brave-forslaget bygger deterministisk på faktiske CRM-fakta, uten AI: lagret aktørnavn er basis, og nøyaktig én kommune legges automatisk til. Ingen eller flere kommuner gir ikke automatisk sted; ved flere kommuner velger redaktøren eksplisitt. Kategori og aktivt tilknyttet person er også eksplisitte tillegg. Tags brukes aldri. Den eksakte queryen og kildene den bygger på er synlige og redigerbare, og endelig bildevalg gjøres alltid av en menneskelig redaktør.

Provideradapteren bruker de eiergodkjente parameterne `country=NO`, `search_lang=nb`, `safesearch=strict`, `spellcheck=false` og `count=30`. `nb` brukes fordi Braves offisielle språk-enum ikke støtter `no`. Full providerrespons lagres aldri; bare eksakt query og normaliserte nødvendige kandidatfelt beholdes i omtrent 30 minutter gamle signerte refs, ikke i en persistent kandidatmodell eller søkehistorikk. Valgt Brave-event beholder source type/provider, men ikke providerens bilde- eller side-URL, i tråd med begrensningen på persistent lagring/caching i standardvilkårene. Braves egne standard query-logger kan samtidig beholdes i opptil 90 dager; Zero Data Retention krever Enterprise/egen avtale og er ikke en egenskap ved appens signed-ref. Editor viser den godkjente privacy- og rettighetscopyen før søk og ved resultater.

Foto har fokusforvalgene Venstre/Midt/Høyre og Topp/Midt/Bunn som snarveier til presis X/Y og 100–300 % zoom. Klient og server bruker samme kantklampede cover-geometri per variant; de faktiske serverrenderte `square`-, `landscape`- og `share`-previewene er fasit før approval. Logo bruker contain og avviser/skjuler cropoppskriften. Migrasjon `0028` gir historiske rendition-sett default zoom `1.0000`, inkluderer zoom i immutable renderhash og blokkerer reverse etter non-default zoom. Asset-alttekst er fortsatt valgfri etter `0027`, og tom streng bevares uten skjult fallback.

3D.2 oppretter ingen public release, public projection eller persistent kandidatrad og endrer ikke PUBLIC. Første versjon er grønn med 365 backendtester, 22 frontendtester, 10 Playwright-tester, migrasjons-/staging-/backupkontrakter og begge produksjonscontainerbyggene; alle fem CI-jobber i run `31441538397` er grønne. Stagingverifiseringen gjennomførte direkte URL, multipart-upload, to fokussett, private previews, first lock/replacement og blank alttekst på en dedikert upublisert testaktør med 0 public releases, uendret publisert antall og 0 orphans. Precision/zoom-oppfølgingen er fullverifisert lokalt med 372 backendtester, 28 frontendtester, 11 Playwright-reiser, 4 stagingkontrakttester, 68 backuptester, frontendbuild og begge produksjonscontainerbyggene. Alle fem jobber i endelig CI-run `31520955798` er grønne på eksakt PR-head `964a97d89f5489aeaff26cb822b2753c76b40d6e`. Den historiske Brave-gaten sendte den foreslåtte queryen `Festspillene Helgeland VEFSN` gjennom `search_lang=nb`, mottok 30 kandidater og gjennomførte privat originalpreview, secure fetch, processing og tre private no-store-renditionpreviews. Deltaet var ett privat asset, ett rendition-sett og tre interne renditions, men 0 selections, 0 review-events, 0 publiserte aktører og 0 public releases; dry-run fant 0 orphans. Prosjekteier har godkjent privacy-/rettighetscopyen, vanlig og teknisk bildespråk, Foto/Logo-skillet, Logo uten crop-/zoomkontroller, blank alttekst og samsvaret mellom live preview og serverprocessing. Foto-zoom er godkjent som innzooming med retur til standard cover-nivå, aldri zoom ut til tom flate. Etter evidensinnsamlingen ble credentialen deaktivert, og staging rapporterer nå `brave_configured=False` og kontrollert `brave_not_configured`. Før ordinær Editor-aktivering må avtaleeier dokumentere at hver End User omfattes av en skriftlig avtale som oppfyller kravet i Braves gjeldende Terms punkt 4(c), samt nødvendige privacy notices/samtykker. Dette er en manuell operativ gate, ikke manglende kode. Se [stagingevidensen](STAGING_IMAGE_SOURCES_2026-08-11.md).

PR #33 er merget til `main` som `48f23f183dacb8331a64b86f1d7574250cbfbe02`, og alle fem jobber i main-CI-run `31535260891` er grønne på eksakt mergecommit. Fase 3D.2 er dermed gjennomført; dette markerer ikke hele fase 3 som ferdig og aktiverer verken PUBLIC-bildebruk eller Brave for ordinære Editor-sluttbrukere.

### Fase 3E – PUBLIC, API, deling og kort

**Status:** Arkitektur godkjent i [ADR-009](../decisions/ADR-009-PUBLIC_IMAGE_RUNTIME_RELEASE_DELIVERY_AND_RESTORE_SAFE_DENY_STATE.md); 3E.1A, 3E.1B-materialisering og 3E.1C-controlled serving er **ACTIVE** i staging. 3E.1C er `CLOSED` med [datert liveevidens](STAGING_PHASE_3E1C_ACTIVATION_2026-08-24.md). 3E.2 er `CLOSED / SHADOW VERIFIED` med [datert stagingevidens](STAGING_PHASE_3E2_SHADOW_2026-08-24.md). 3E.3 er `CLOSED / ACTIVE` med [datert cutoverevidens](STAGING_PHASE_3E3_CUTOVER_2026-08-24.md), og 3E.4 er `CLOSED / ACTIVE` med [datert takedownevidens](STAGING_PHASE_3E4_TAKEDOWN_2026-08-24.md).

Fase 3E følger denne rekkefølgen:

1. **3E.1A – journal, restore-gate og off-server anker (`ACTIVE` i staging 2026-08-20):** lokal append-only SQLite-ledger, rebuildbar read-model/cursor, standalone incident restore, fail-closed health, host/systemd Borg-anchor, dedikert Storage Box-subaccount/repository, separat recovery-custody og live append/delete/compact/raw-`rm`-/transaction-recovery-/restartbevis er levert. Raw filtilgang er akseptert restrisiko; statusen aktiverer ingen public runtime. Se [aktiveringsrapporten](STAGING_PHASE_3E1A_ACTIVATION_2026-08-20.md).
2. **3E.1B – materialisering og release-livssyklus (`ACTIVE` i staging 2026-08-23):** 3E.1B.1 har lokal fail-closed Unix-socket/systemd-bro med bare `reserve`/`activate`, atomisk reservation og idempotent PostgreSQL-binding uten ledger-/Borg-credential i API/web. 3E.1B.2 har separat `/srv/kreative-norge/media/public-delivery/`, create-only/no-clobber, faktisk checksum-/format-/dimensjonsverifikasjon og idempotent activation. Maksimalt én release tillates per selection; republisering krever ny selection-revisjon/UUID/key. Socket/peer/mount/persistens/backup/restore, syntetisk reserve/binding/materialisering/read-back/activation, hard no-clobber, delvis materialisering/restart og full idempotent retry er liveverifisert. Delivery-rooten er ikke del av generisk orphan-cleanup, og automatisk releasefilsletting finnes ikke. Se [aktiveringsrapporten](STAGING_PHASE_3E1B_MATERIALIZATION_ACTIVATION_2026-08-23.md).
3. **3E.1C – kontrollert serving og origins (`CLOSED / ACTIVE` i staging 2026-08-24):** Django release-gate, read-only safety-`authorize`, intern Nginx `X-Accel-Redirect`, eksplisitte `PUBLIC_SITE_ORIGIN`/`PUBLIC_MEDIA_ORIGIN`, foreløpig privat revalidationcache og fail-closed/restart/observability/backup-restore er levert og liveverifisert. Dette kobler ikke releasen til PUBLIC. Se [aktiveringsrapporten](STAGING_PHASE_3E1C_ACTIVATION_2026-08-24.md).
4. **3E.2 – projection og API shadow (`CLOSED / SHADOW VERIFIED` 2026-08-24):** én read-only `PublicImageProjection`, strukturert target-`image`, kompatibilitetsaliaser fra samme projection, én kanonisk `/api/public/actors/`-rute/serializer, separate gater og read-only fullkatalog-audit er implementert og stagingverifisert.
5. **3E.3 – PUBLIC og cutover (`CLOSED / ACTIVE` 2026-08-24):** target-API, PUBLIC HTML, canonical, Open Graph, Twitter Card, statiske versjonerte production fallback v1-varianter og en global fail-closed feature-cutover er aktivert og rollbackverifisert i staging. Tenant-enrollment er ikke innført uten en konkret blocker.
6. **3E.4 – formell takedown (`CLOSED / ACTIVE` i staging 2026-08-24):** additiv ledger-v2 uten omskriving av v1-historikk, én ankret deny+tenant-checksum-transaksjon, alltid aktiv checksum-/legacyguard, rolleavgrenset default-off write-gate, eksakt tre-filers origin-delete, privat revalidation uten shared-cache-purge, eldre DB-/mediarestorebevis og sikker republisering med ny checksum/selection/UUID/key er liveverifisert. Kode-/eksempelstandard er fortsatt av; ignorert stagingkonfigurasjon er på. Se [takedownrapporten](STAGING_PHASE_3E4_TAKEDOWN_2026-08-24.md).

Host/systemd er valgt execution placement for off-serverankeret; ledger og writersecret finnes ikke i API/web. 3E.1C har liveverifisert `private, max-age=60, must-revalidate` uten `immutable` eller shared cache. 3E.3 har valgt byteidentisk production fallback v1 med blank alttekst. 3E.4 bruker derfor ingen ekstern purgeintegrasjon; `404/no-store`, ingen `304`/`HIT` og fravær av originbytes er liveverifisert. Global checksum-deny innføres ikke uten senere konkret behov.

### Fase 3F – legacyovergang og driftsverifisering

**Status:** `CLOSED / VERIFIED` 2026-08-25. Implementert på merge `438a480`, staging-/restoreverifisert med shared Import-gate av. Se [3F-evidensen](STAGING_PHASE_3F_LEGACY_IMPORT_2026-08-25.md).

- skrivebeskyttet, aggregert legacyinventar er implementert med valgfri redaktert detaljvisning; Editor viser opptil tre DB-baserte legacykandidater uten automatisk preview eller godkjenning
- vanlig aktøroppretting/-lagring kjører ikke lenger Open Graph-refresh, legacyfeltene er read-only i API-et, og import-commit utfører ingen bildenettverk eller processing
- typed `ImportImageDecision`-kontrakt for senere Import 2.0 er implementert i additiv migrasjon `0031` bak `IMPORT_IMAGE_DECISIONS_ENABLED=False`, med stale-/tenant-/approvalkontroll og idempotent review-eventbinding
- database- og assetrestore, staging, takedown, fallback og API-overgang er verifisert uten endret 3E-state
- beholde legacyfelt og aliaser gjennom stabiliseringsperioden; fysisk opprydding får egne senere gater

Fase 3 er avsluttet og etablerer bare bildekontrakten som senere Import 2.0 skal bruke. Fase 4 etablerer internasjonal telefonidentitet før full Import 2.0. Produkt- og UX-design for Import 2.0 ligger deretter i fase 5, og full implementering ligger i fase 7. Fase 4A–4H er gjennomført og [samlet teknisk stagingverifisert](STAGING_PHASE_4H_PHONE_TECHNICAL_VERIFICATION_2026-08-26.md). Første owner-smoke fant tre avgrensede presentasjons-/Editor-UX-feil; alle tre er [rettet og teknisk stagingreverifisert](STAGING_PHASE_4_OWNER_SMOKE_REMEDIATION_2026-08-29.md) 2026-08-29 uten schema- eller publiseringsendring. Tre siste UI-polishpunkter fra andre owner-smoke er også [implementert og teknisk stagingreverifisert](STAGING_PHASE_4_OWNER_SMOKE_UI_POLISH_2026-08-29.md) uten schema-, data- eller publiseringsendring. Prosjekteier [godkjente siste manuelle kontroll 2026-08-29](PHASE_4_OWNER_APPROVAL_2026-08-29.md). `PHASE 4 = CLOSED / VERIFIED`; fase 5A er fullført som planleggingsgrunnlag, og fase 5B formaliserer godkjent målarkitektur uten runtimeimplementering.

Leveransevise akseptansekriterier, testkrav, rollback og de tverrgående ferdigkriteriene for aktivt CRM-bilde, privat original, renditions, approval, locking, fallback, API-kompatibilitet, Open Graph, import, takedown, backup/restore og legacyutfasing finnes i [ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md#implementeringsleveranser-og-akseptansekriterier).

## Fase 4 – International phone identity foundation

**Status:** `PHASE 4 = CLOSED / VERIFIED`. Alle 4A–4H-gater er gjennomført. Tre funn fra første owner-smoke og tre UI-polishpunkter fra andre owner-smoke er rettet og teknisk stagingreverifisert. Prosjekteier gjennomførte siste manuelle kontroll og godkjente resultatet 2026-08-29.

**Mål:** etablere stabil og internasjonalt skalerbar telefonidentitet før full Import 2.0-implementering.

Fase 4 følger denne rekkefølgen:

1. **4A – ADR-010:** arkitekturbeslutning og fasescope. Ren dokumentasjonsleveranse.
2. **4B – Databaseline (`READY_FOR_4C` 2026-08-25):** to byteidentiske, personvernredigerte read-only-inventar kartla person- og organisasjonstelefon i staging. Fingerprints, publiseringsstate og runtime var uendret; se [evidensrapporten](STAGING_PHASE_4B_PHONE_BASELINE_2026-08-25.md).
3. **4C – Normalization domain (`READY_FOR_4D` 2026-08-25):** `phonenumbers==9.0.37` bak én ren felles telefonadapter for parsing, eksplisitt regionkontekst, validering, typed resultat og E.164. API-only stagingdeploy, syntetisk smoke, read-only klassifisering og no-write-fingerprints var grønne; se [domenekontrakten](../architecture/PHONE_NORMALIZATION.md) og [stagingevidensen](STAGING_PHASE_4C_PHONE_NORMALIZATION_2026-08-25.md). 4C var isolert uten callers; 4D–4G koblet dem senere til samme kontrakt.
4. **4D – Additiv datamodell (`CLOSED / VERIFIED`):** migrasjon `0032` la til nullable canonical/regionfelt og tenantregion uten backfill, skjult default eller global telefonunikhet.
5. **4E – Editor (`CLOSED / VERIFIED`):** synlig regionvalg, eksplisitt write-kontekst, rå presentasjonsverdi og servervalidert normalisering uten publiseringssideeffekt.
6. **4F – Import contract (`CLOSED / VERIFIED`):** jobbsnapshot, typed `VALID`/`INVALID`/`NEEDS_REGION`/`KEEP`, tenant-scopet matching og review uten automerge.
7. **4G – Controlled backfill (`CLOSED / VERIFIED`):** 61 additive stagingendringer etter dobbel dry-run, backup og isolert apply/rollback; live sluttstate gir dry-run `0`.
8. **4H – Staging verification (`TECHNICALLY VERIFIED` 2026-08-26):** Editor, Import, cross-tenant, API/PUBLIC, fingerprints, full testmatrise, image/safety og post-change backup/restore er samlet grønne; se [evidensen](STAGING_PHASE_4H_PHONE_TECHNICAL_VERIFICATION_2026-08-26.md).

Godkjent målretning:

- E.164 er kanonisk maskinidentitet for gyldige telefonnumre
- presentasjons-/råverdi bevares separat
- Google libphonenumber-modellen brukes gjennom en egnet Python-implementasjon, normalt `phonenumbers`
- nasjonale numre krever eksplisitt tenant- eller importregion; Norge er aldri en skjult universell gjetning
- normalisering gir typed `VALID`, `INVALID` eller `AMBIGUOUS` / `NEEDS_REGION`
- person- og organisasjonstelefon bruker samme domenegrense
- lik E.164 er et sterkt matchsignal, ikke personidentitet eller automatisk mergegrunnlag
- legacyovergangen er additiv, konservativ og reviewbasert
- normalisering og matching endrer aldri publisering

Extensions, full Import 2.0-UX, generell persondeduplisering, automatisk person-merge, `OrganizationContact`, fysisk fjerning av `Person.phone`, SMS/WhatsApp og endringer i fase 3-bildearkitekturen er eksplisitt utenfor fase 4.

De tekniske ferdigkriteriene for 4B–4H er oppfylt. Owner-smoke-rettingen bevarer
rå telefon som visning, bruker canonical E.164 som dialmål og forklarer
effektiv PUBLIC-status uten å koble flaggene. Siste UI-polish holder
aktøroversiktens hovedkort kompakte, viser backend-avledet landkodehint i
interne read-only-visninger og forkorter personlenkens knappetekst til
`Rediger`. [Endelig manuell owner-smoke](PHASE_4_OWNER_APPROVAL_2026-08-29.md)
godkjente alle tre punktene 2026-08-29. ADR-010 er implementert innen avtalt
fase-4-scope, og status er `PHASE 4 = CLOSED / VERIFIED`. Ingen
produksjonssetting ble utført.

## Fase 5 – Produkt- og UX-design for Import 2.0

**Status:** Aktiv planleggingsfase. 5A er fullført som read-only grunnlag,
5B/[ADR-011](../decisions/ADR-011-SHARING_DOMAIN_CANONICAL_IDENTITY_AND_TENANT_ASSIGNMENTS.md)
er merget målarkitektur, og 5C/[ADR-012](../decisions/ADR-012-PLACE_IDENTITY_GEOGRAPHIC_CLASSIFICATION_AND_ACTOR_ONLY_MAPS.md)
formaliserer sted og actor-only kart som målarkitektur. Ingen av ADR-011 eller
ADR-012 er runtimeimplementert. Etter merge av 5C er 5D neste aktive
produktarbeid.

Den eksisterende importmotoren skal kartlegges og gjenbrukes der den er solid, men dagens brukeropplevelse skal ikke begrense det nye konseptet.

Fase 5 følger denne rekkefølgen:

1. **5A – Produktretning og read-only impact inventory (`FULLFØRT` som planleggingsgrunnlag):** eksisterende import-/mappingmotor, tenant-eierskap, dataomfang, tilgang, PUBLIC, bilder og storage er kartlagt uten writes. Kort PII-fri evidens finnes i [Phase 5 sharing-domain impact](PHASE_5_SHARING_DOMAIN_IMPACT_2026-08-30.md).
2. **5B – ADR-011 sharing domain og canonical identity (`MERGET MÅLARKITEKTUR`):** direkte canonicalisering, assignments, overlays, agreement/capabilities, PUBLIC-authoritet, image-home og additiv migrering er besluttet. Ingen kode, schema, data eller runtime er implementert.
3. **5C – ADR-012 places, geography og actor-only maps (denne dokumentasjonsleveransen):** provider-nøytral Place, OrganizationPlace, strukturert PersonPlace uten kart, versjonerte geografiske tenantforslag, additiv legacyovergang og actor-only kart i Editor/PUBLIC er besluttet som målarkitektur. Google er valgfri adapter, ikke canonical stedssannhet. Ingen runtime er implementert.
4. **5D – Import 2.0 informasjonsarkitektur, wireframes og klikkbar prototype (neste produktarbeid etter 5C-merge):** brukerreise, review-/konfliktflyt, stedskontroll og tenantforslag, actor-only kartbrukerreise, kvalitetsmål, framdrift, gamification og brukertestgrunnlag.
5. **5E – Godkjent implementerings- og testplan:** små leveranser, akseptansekriterier, migrering, featuregates, staging, rollback og ferdigdefinisjon før større kodeendringer.

Avhengigheter for senere implementering:

- shared identity og assignments må etableres før full Import 2.0
- structured places og actor-only maps kan først implementeres etter den
  godkjente ADR-012-rekkefølgen; maps gjelder bare Organizations
- PersonPlace er strukturert data uten Google-, koordinat-, markør- eller
  kartscope
- contact-/relationship-målarkitekturen må være klar før full Import 2.0
- persistent import storage, backup/restore og retensjon må være aktiv før Import 2.0 kan aktiveres
- browser-aktiv Codex er en hard gate før Import 2.0- og kart-UI implementeres

## Fase 6 – Personer, kontaktarkitektur og Editor-UX

**Status:** Planlagt langsiktig kontaktfase etter telefonfundamentet.

Denne fasen realiserer resterende målarkitektur i [ADR-005](../decisions/ADR-005-CONTACT_ARCHITECTURE.md) i kontrollerte, reversible leveranser:

- én samlet kontaktseksjon
- flere e-postadresser og telefonnumre
- gjenbruk av fase 4s felles telefonnormalisering og additive telefonfelt
- én primær intern kontakt per type
- offentlige kontaktvalg per aktør–person-kobling
- offentlig preview fra samme projeksjon som API og PUBLIC
- tydelig skille mellom intern og offentlig status
- sticky lagreknapp og lagringsstatus nær handlingen
- mindre unødvendig scrolling og bedre utnyttelse av desktopbredde
- hensiktsmessig modal- eller redigeringsflyt
- støtte for relasjonsspesifikk offentlig tittel når produktvalget er avklart

Alle personvern-, migrerings-, rollback-, API- og datakrav i ADR-005 gjelder fortsatt.

## Fase 7 – Implementer Import 2.0

**Status:** Planlagt etter godkjent prototype og stabil kontakt-/telefonmodell.

- gjenbruk den eksisterende importmotoren som teknisk fundament
- implementer den godkjente brukerreisen i avgrensede etapper
- integrer matching, berikelse og AI-forslag uten å skjule usikkerhet
- bruk fase 4s telefonkontrakt for matching og review
- gjør trygge rader raske og konflikter tydelige
- behold menneskelig kontroll over irreversible eller publiserende valg
- test med representative, reelle filer
- gjennomfør brukertest med prosjekteier og minst én kollega

## Fase 8 – Eksport som ferdig produkt

**Status:** Delvis teknisk grunnlag, produktet er ikke ferdig.

- CSV- og XLSX-generering
- valg av felter, filtre og segmenter
- kontaktbevisst eksport
- intern arbeidsliste
- offentlig katalog basert på samme PUBLIC-projeksjon
- e-postlister
- sikker generering og nedlasting
- jobbhistorikk og tydelig status
- grunnlag for senere integrasjoner

## AI som gjennomgående produktprinsipp

AI er ikke en egen sprint. Det brukes der det gir målbar hjelp og alltid innen tydelige regler:

- bilde- og logokandidater kan senere få AI-støtte der det gir dokumentert verdi, men fase 3D.2s querybygging og lokale rangering er eksplisitt deterministisk og bruker ingen AI
- matching, manglende verdier, berikelse, kategoriforslag og prioritering av usikre rader i Import 2.0
- ingen automatisk overskriving uten eksplisitt regel eller menneskelig godkjenning
- AI kan peke ut informasjon eller publiseringsvalg som bør vurderes, men skal aldri aktivere, endre eller utvide offentlig publisering automatisk. Publisering krever en eksplisitt regel eller menneskelig godkjenning.

## Parallelt infrastrukturløp – Sikker automatisk staging-deploy

**Status:** Planlagt; ikke implementert eller verifisert.

Manuell og kontrollert deploy beholdes til denne kjeden er spesifisert, testet og godkjent:

- egen minst privilegert deploy-bruker
- GitHub Environment for staging
- secrets som ikke eksponerer serverens root-nøkkel
- deploy fra `main` først etter grønn obligatorisk CI
- deploy-lås mot samtidige kjøringer
- databasebackup før risikofylte steg
- health check og målrettede smoke-tester
- dokumentert rollback
- logging og gradvis hardening

Infrastrukturløpet følger [Staging and Deployment](../development/STAGING_AND_DEPLOYMENT.md), men ligger utenfor produktfasene og blokkerer ikke fase 1–7.

## Senere muligheter

- Google Sheets-import
- Checkin-import
- Mailmojo-import
- skjemaer og automatisk opprettelse av kontakter
- geografisk visning
- eksterne integrasjoner
- nettdugnad og samtykkebasert redigering
