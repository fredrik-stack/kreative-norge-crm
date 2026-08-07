# Roadmap

**Status:** Godkjent strategisk arbeidsrekkefølge

**Sist oppdatert:** 2026-08-02

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

**Status:** Fase 3A, fase 3B.1 og fase 3B.2 teknisk gjennomført; ADR-008s lokale Hetzner storage-/backup-MVP er ACTIVE; fase 3C har avslått konfigurasjon og additiv bilde-, selection- og event-/kommandogrunnmur uten runtimebruk.

Fase 3A kartla dagens legacy URL-, Open Graph-, kort-, import-, storage- og driftsflyt. [ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) er godkjent som arkitekturgrunnlag.

`ImageAsset`, `ImageRenditionSet`, `ImageRendition` og den typed `OrganizationImageSelection` er implementert additivt med constraints og migrasjoner. `ImageReviewEvent` og de feature-gated selection-kommandoene dekker atomisk første låsing, replacement, ordinær fjerning fra aktivt asset til systemfallback og restore av en eksplisitt arkivert asset-selection som ny revisjon, men ingen applikasjonsflyt kaller kommandoene og bilde-runtime er ikke implementert. Fase 3C-grunnmuren endrer ikke dagens `thumbnail_image_url`-, `auto_thumbnail_url`-, `og_image_url`- eller faviconflyt; disse gjelder fortsatt frem til en kontrollert overgang er levert og verifisert.

Bildeløsningen skal gå fra ustabile eksterne treff til en varig, redaksjonelt kontrollerbar ressurs:

- kandidater fra offisiell nettside, Open Graph, opplasting, limt URL og senere en kontrollert Brave-provider
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

**Status:** Fase 3B.1 og fase 3B.2 er teknisk gjennomført som isolerte prototyper, fase 3B.1R er gjennomført og godkjent med representativ kvalitets- og sRGB-evidens, processing-, storage-, delivery-, takedown- og restoreprinsippene er godkjent, og lokal Hetzner storage-/backup-MVP er **ACTIVE**. Hele fase 3B er fortsatt aktiv fordi senere serving-, purge-, journal-, API-, retention-, sync/async- og observabilitygater gjenstår.

- [fase 3B.1](PHASE_3B1_IMAGE_RENDITION_SPIKE.md) målte Pillow og pyvips/libvips, format, foreløpige terskler og ressursbruk på syntetiske fixtures
- fase 3B.1 prototypet contain, cover, fokuspunkt, square/landscape/share, deterministisk fallback og statisk nødvariant uten CRM-runtimekobling
- prosjekteier har godkjent Pillow bak intern adapter, statisk JPEG/PNG/WebP-input, outputmappingen WebP/PNG/JPEG, 512 × 512 `square`, 800 × 450 `landscape`, 1200 × 630 `share`, no-upscale, immutable key-invarianten og 15 MiB som konfigurerbar standard
- [fase 3B.1R](PHASE_3B1R_REPRESENTATIVE_QUALITY_HARNESS.md) har kjørt den isolerte harnessen lokalt på 24 rettighetsavklarte fixtures og fått separat evidensgodkjenning; private kilder, manifest og visuell/full evidens forblir Git-ignorert
- 36 MP er godkjent som konfigurerbar decoded-pixel-standard for MVP; det finnes ingen universell minimumsdimensjon, ingen automatisk oppskalering og obligatoriske renditions vurderes separat etter fit, faktisk cropområde og scaling margin
- edge variance og blockiness er advisory, outliers kan gi warning/manual review, og ingen numerisk edge-/blur-/blockiness- eller whitespacegrense er automatisk hard fail
- offentlig MVP-output normaliseres eller konverteres eksplisitt til sRGB før crop/resize og skrives profilfritt; untagged registreres som antatt sRGB, mens korrupt/uleselig ICC er kontrollert teknisk feil
- [fase 3B.2](PHASE_3B2_STORAGE_RESTORE_SPIKE.md) har prototypet separate private/public `STORAGES`-aliaser, lokal filesystemreferanse, Moto 5.2.2, immutable artifact/release keys, absolutte allowlistede media-origins, origin-sletting, purge/takedown, separat deny-journal og backup/restore
- prosjekteier har godkjent to-key-kontrakt, en aktiv public rendition-store uten tilgjengelige historiske public versjoner, kontrollert public delivery, private originaler, hybridbackup, fail-closed restore, varig deny-journal/read-model og idempotent purge; ADR-008 velger lokal host-persistent storage for første MVP og gjør providerkrav betingede
- [ADR-008](../decisions/ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md) velger lokale navngitte storagealiaser og stabil lokal Borg `>=1.2.8`/`<1.3.0` med remote path `borg-1.2` til separat Hetzner Storage Box og retention 14/8/12; S3/AWS/Backblaze/CDN utsettes
- repoets backupmodul er ACTIVE etter verifisert Storage Box, kryptert repository, recovery-custody for minst to ansvarlige, første backup, full repository-check, isolert restore av samme arkiv, Storage Box-snapshot, nyere synlig Cloud Backup og aktive timere; detaljert evidens finnes i [aktiveringsrapporten](STAGING_BACKUP_ACTIVATION_2026-08-02.md)
- eksakt public key-struktur, lokal serving/purge, permanent journalteknologi, full katastrofe-RTO og konkrete bilde-runtimepaths er fortsatt åpne; nattlig RPO og restore-smoke har foreløpige målinger
- fase 3B.2 har ikke opprettet CRM-modeller, migrasjoner, API/OpenAPI, Editor, PUBLIC, Import 2.0-integrasjon, bakgrunnskø eller stagingdeploy
- senere fase 3B-gater skal fastsette lokal private/public-serving og cache/purge/verifikasjon, permanent deny-journal/read-model/cursor, API-schema, aliasmapping, public release key-struktur, concurrency/databaseconstraints, retentionmekanisme, sync/async-grense og observability; provider-/CDN-gater gjelder bare dersom ekstern storage senere tas opp igjen

Processing profile v1, fase 3B.1R-kvalitetskontrakten og fase 3B.2-prinsippene er arkitekturgrunnlag, ikke produksjonsimplementering. Dagens CRM-runtime og legacy URL-/faviconflyt gjelder fortsatt. ADR-008-backupen er aktivert og restore-verifisert. Gater for lokal serving/purge, permanent deny-journal/read-model/cursor, API-schema, aliasmapping, public release key, retention, sync/async og observability må fortsatt være grønne før reell bildebruk kan aktiveres.

#### Godkjent operasjonell MVP: lokal Hetzner-storage og backup

**Status:** ACTIVE fra 2026-08-02.

MVP-en bruker:

- dagens Hetzner Cloud-server for app, database og aktiv media
- lokale navngitte Django-storagealiaser og host-persistente mediaområder når bilde-runtime implementeres
- daglig kryptert Borg-backup til separat Hetzner Storage Box
- Storage Box-snapshots og Hetzner Cloud Backups som ekstra lag
- obligatorisk dump-, repository- og isolert restore-gate før timeraktivering

Den skrivebeskyttede [serverbaselinen](STAGING_BACKUP_BASELINE_2026-08-01.md) fant et lite database-/filgrunnlag, ingen eksisterende import-/eksportfiler og ingen kolliderende automatisert backup, men bekreftet at nye FileField-filer vil være containerlagret uten en senere host-mount. [Aktiveringen 2026-08-02](STAGING_BACKUP_ACTIVATION_2026-08-02.md) etablerte BX11 med 1 TB i FSN1, kryptert Borg-kjede, separat recovery-custody, første backup, full repository-check, isolert restore, snapshots og aktive timere. S3-/CDN-sammenligning tas bare opp igjen ved dokumentert vekst- eller driftsbehov. Fase 3B.1R-kvalitetsgaten er gjennomført og godkjent; øvrige runtimegater gjelder fortsatt.

### Fase 3C – additiv backend- og storagegrunnmur

**Status:** PR #23 og fase 3C.6 er merget. Den ordinære selection-livssyklusen med låsing/replacement, fjerning til fallback og restore av arkivert selection som ny revisjon er komplett bak avslått feature. Fase 3B.1R er gjennomført og godkjent; ingen ny selection-livssykluskommando planlegges, og neste faseleveranse velges separat blant de gjenstående 3B-/3C-gatene.

Første leveranse har innført `IMAGE_ASSET_FEATURE_ENABLED=False` som standard og lokale `image_originals_private`-/`image_renditions_public`-aliaser med separate, validerte roots. Eksisterende `default` og `staticfiles` er bevart. Aliasene brukes ikke av runtime, og settings-load eller system check oppretter ingen mapper eller filer.

Andre leveranse legger til `ImageAsset`, `ImageRenditionSet` og `ImageRendition` med provider-nøytrale logiske keys, teknisk metadata, tenant-avgrenset unikhet, numeriske constraints og `PROTECT` mellom asset, sett og rendition. Modellene er ikke koblet til `Organization`, storage, API eller runtime, og featureflagget forblir avslått.

Tredje leveranse legger til `OrganizationImageSelection` som én låst revisjon per rad. Databasen håndhever unik revisjon, positiv revisjon, maksimalt én aktiv selection og eksklusivt asset-/fallbackvalg. Asset-selection peker til nøyaktig ett immutable rendition-sett; fit, fokus og prosesseringsversjon dupliseres ikke. PR #20 med dette skjemaet er merget.

Fjerde leveranse legger til `ImageReviewEvent` og `lock_organization_image_selection`. Eventet beholder snapshots og er append-only gjennom støttede applikasjons-/ORM-veier, men er ikke database-WORM. Kommandoen er den godkjente skriveruten for første låsing og vanlig replacement, er blokkert når featureflagget er avslått og skriver selection og event atomisk. `expected_revision` oppdager konflikter, mens den tenant-scopede `Organization`-raden er concurrency-lås. Redigerer, gruppeadmin og tenant-superadmin kan arbeide i egen tenant; plattform-superadmin må alltid angi target tenant. Proveniens lagres som event-snapshot, men full kandidat-/ingestmodell er ikke implementert.

Fase 3C.5 legger til `selection_removed_to_fallback` og `remove_organization_image_to_fallback`. Kommandoen er eneste godkjente vei fra aktiv asset-selection til systemfallback, arkiverer bare statusen på forrige selection og oppretter ny fallback-revisjon og event atomisk. Den generiske lock-kommandoen kan fortsatt opprette første fallback og erstatte fallback med asset eller asset med annet asset, men avviser asset → fallback og fallback → fallback. PR #22 og fase 3C.5 er merget.

Fase 3C.6 legger til `selection_restored` og `restore_archived_organization_image_selection`. Kommandoen krever en eksplisitt eldre, arkivert asset-selection i samme tenant og organisasjon, revaliderer det komplette rendition-settet og oppretter en helt ny aktiv revisjon med samme rendition-sett, alt-tekst og offentlig kreditering. Restore-kilden omskrives aldri, og restore-eventet peker både på den tidligere aktive selectionen og restore-kilden. Restore er ikke ny approval: eventet lagrer ingen ny godkjenningstekst eller proveniens. Endret approval, alt-tekst, kreditering, fit, fokus eller rendition-sett skal bruke vanlig replacement. Databasen håndhever restore-eventets snapshotform, mens source-status og cross-tenant/-organization-scope håndheves av domenekommandoen.

- additive modeller, constraints og migrasjoner
- kontrollert ingest, private originaler og renditions gjennom lokale navngitte storagealiaser
- capability-permissions, approval, locking, audit, retention, karantene og takedown
- feature av frem til test- og datagrunnlaget er godkjent
- ingen varige bildefiler før ADR-008-backupen er ACTIVE og restore-verifisert
- ingen bildefiler skrives, leses eller serveres av grunnleveransene; ingen API- eller brukerflyt kaller kommandoene, og legacybildeflyten er uendret
- fase 3B.1R er gjennomført; gjenstående runtimegater velges separat, og ingen ny selection-kommando planlegges etter fase 3C.6

### Fase 3D – Editor-flyt for aktørbilde

**Status:** Planlagt.

- kandidatfunn, upload, limt URL og fallback
- «Godkjenn og lås bilde» og eksplisitt replacement
- ordinær arkivering, restore og historikk; takedown-UI forberedes deaktivert til deny-gaten er verifisert
- preview fra samme selection- og projectionkontrakt som PUBLIC

### Fase 3E – PUBLIC, API, deling og kort

**Status:** Planlagt.

- felles public image projection og kontrollert cutover
- strukturert bildeobjekt med deprecated kompatibilitetsaliaser
- canonical, Open Graph og Twitter Card med 1200 × 630-sharevariant
- godkjente kortmål, grønne PUBLIC-tags, felles fit/fokus og robust overflow
- aktivere rolleavgrenset takedown først når legacy og ny projection følger samme deny-status

### Fase 3F – legacyovergang og driftsverifisering

**Status:** Planlagt.

- inventere legacy URL-er og gjøre dem til kandidater uten automatisk godkjenning
- stoppe automatisk refresh ved vanlig aktørlagring og nettverk i import-commit
- etablere typed bildekontrakt for senere Import 2.0
- verifisere database- og assetrestore, staging, takedown, fallback og API-overgang
- beholde legacyfelt og aliaser gjennom stabiliseringsperioden; fysisk opprydding får egne senere gater

Fase 3 etablerer bare bildekontrakten som senere Import 2.0 skal bruke. Produkt- og UX-design for Import 2.0 ligger fortsatt i fase 4, og implementeringen ligger i fase 6. Beslutningsgaten for internasjonal telefon ved overgangen til fase 4 er uendret.

Leveransevise akseptansekriterier, testkrav, rollback og de tverrgående ferdigkriteriene for aktivt CRM-bilde, privat original, renditions, approval, locking, fallback, API-kompatibilitet, Open Graph, import, takedown, backup/restore og legacyutfasing finnes i [ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md#implementeringsleveranser-og-akseptansekriterier).

## Fase 4 – Produkt- og UX-design for Import 2.0

**Status:** Planlegging før større kodeendringer.

Den eksisterende importmotoren skal kartlegges og gjenbrukes der den er solid, men dagens brukeropplevelse skal ikke begrense det nye konseptet. Ingen større implementering starter før produkt- og UX-planen er godkjent.

Før fase 4 kan godkjennes som ferdig, skal et eget ADR beskrive internasjonal telefonmodell, landkontekst og normalisering. ADR-arbeidet gjennomføres ved overgangen fra fase 3 til fase 4 og skal minst bygge på disse godkjente prinsippene:

- original/raw telefonverdi bevares
- en separat normalisert sammenligningsverdi brukes til kontrollert matching
- nasjonale numre får uttrykkelig land-/regionkontekst
- fullstendige internasjonale numre støttes
- internnummer kan håndteres separat
- én sentral backendtjeneste brukes av Editor, API, import, eksport og reparasjonsverktøy
- tvetydige verdier går til review og slås ikke sammen automatisk
- normalisering og matching aktiverer aldri publisering

Eksakt bibliotek, modellnavn, databasefelt, constraints, API-kontrakt, migrering og backfill avgjøres i det senere ADR-et og er ikke besluttet i denne roadmapen.

Leveranser:

- kart over dagens import- og mappingmotor og tekniske begrensninger
- brukerreise og tydelig problemdefinisjon
- prioriterte brukerhistorier
- informasjonsarkitektur
- wireframes og klikkbar prototype
- review- og konfliktflyt
- kvalitetsmål og trygg håndtering av usikre data
- synlig fremdrift og hensiktsmessige gamification-mekanismer
- akseptansekriterier og testplan
- faseinndelt implementeringsplan

## Fase 5 – Personer, kontaktarkitektur og Editor-UX

**Status:** Planlagt langsiktig kontaktfase.

Denne fasen realiserer målarkitekturen i [ADR-005](../decisions/ADR-005-CONTACT_ARCHITECTURE.md) i kontrollerte, reversible leveranser:

- én samlet kontaktseksjon
- flere e-postadresser og telefonnumre
- tidlig implementering av den godkjente internasjonale telefonmodellen fra beslutningsgaten i fase 4
- sentral telefonnormalisering med bevart originalverdi, normalisert sammenligningsverdi og uttrykkelig landkontekst
- kontrollert og reverserbar datamigrering med review av tvetydige verdier
- én primær intern kontakt per type
- offentlige kontaktvalg per aktør–person-kobling
- offentlig preview fra samme projeksjon som API og PUBLIC
- tydelig skille mellom intern og offentlig status
- sticky lagreknapp og lagringsstatus nær handlingen
- mindre unødvendig scrolling og bedre utnyttelse av desktopbredde
- hensiktsmessig modal- eller redigeringsflyt
- støtte for relasjonsspesifikk offentlig tittel når produktvalget er avklart

Alle personvern-, migrerings-, rollback-, API- og datakrav i ADR-005 gjelder fortsatt.

## Fase 6 – Implementer Import 2.0

**Status:** Planlagt etter godkjent prototype og stabil kontaktmodell.

- gjenbruk den eksisterende importmotoren som teknisk fundament
- implementer den godkjente brukerreisen i avgrensede etapper
- integrer matching, berikelse og AI-forslag uten å skjule usikkerhet
- la telefonmatching bruke den stabile kontakt- og telefonmodellen fra fase 5
- gjør trygge rader raske og konflikter tydelige
- behold menneskelig kontroll over irreversible eller publiserende valg
- test med representative, reelle filer
- gjennomfør brukertest med prosjekteier og minst én kollega

## Fase 7 – Eksport som ferdig produkt

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

- bilde- og logokandidater i fase 3
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
