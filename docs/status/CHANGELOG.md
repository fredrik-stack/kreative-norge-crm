# Changelog

Dette dokumentet samler større brukermerkbare og arkitekturelle endringer. Små kosmetiske justeringer trenger ikke registreres.

## 2026-08-02

### Sikkerhetsherding av forberedt backupgrunnmur

- strammet den felles lokale Borg-porten til stabil versjon `>=1.2.8` og `<1.3.0`; eldre `1.2.x`, `1.3.x`, `2.x`, prerelease og malformed output avvises før repository- eller backuparbeid for init, key export, inspect, backup, verify og restore
- lagt en semantisk pathgate før mutasjoner: root, brede systemområder, parent traversal, ikke-normaliserte paths, symlinkkomponenter og farlige mediaoverlapp avvises
- bundet work, status, restore-gate og Borg cache/config/security til dedikert backup-state og hindret ambient Borg-directoryvariabler i å flytte skrivbare områder
- avgrenset host-media til eksplisitte underkataloger under Kreative Norges media-root og API-media til eksplisitte underkataloger under `/app`
- herdet recovery-key-export med operator-eid, ikke group/world-writable parent, directory-/symlinkavvisning og atomisk no-clobber med bevart mode `0600`
- rettet den felles pathliste-parseren slik at også eneste og siste element i en kolonseparert allowlist alltid valideres
- utvidet den syntetiske backup-testpakken til 68 tester for versjonsgrenser, felles kommandogate, pathfamilier og siste listeelement, overlapper, symlinks, validering før arbeid og atomisk recovery-destinasjon
- beholdt backupgrunnmuren **PREPARED, NOT ACTIVE** og passphrase-/key-/Storage Box-custody **MANUAL REQUIRED**; ingen server, staging, runtime, database, tjeneste, container, deploy eller timer er endret

## 2026-08-01

### ADR-008 og Hetzner backupgrunnmur forberedt

- godkjent én-server-MVP med Django, PostgreSQL og aktiv media på dagens Hetzner Cloud-server, navngitte lokale Django-storagealiaser for fremtidig media og utsatt S3-/AWS-/Backblaze-/CDN-løp
- lagt en inaktiv backupmodul under `ops/backup/` med PostgreSQL custom-format dump, `pg_restore --list`, eksplisitte fil-/konfigurasjonspaths, sikkert manifest, kryptert Borg 1.2.x/`borg-1.2`, repo-ID-lås og retention 14/8/12
- lagt nattlig backup- og ukentlig verify-unit med `flock`, root-only state, lav prioritet og statusfil, men ikke installert eller aktivert timerne
- lagt isolert restore-smoke mot PostgreSQL 16 uten port eller live databaseinngrep og en hard aktiveringsport som krever grønn backup, dump, repository-check og restore av samme arkiv
- rettet lock-/status-racet slik at verify og restore bare kan skrive operativ status etter at den felles låsen er ervervet; lock contention oppretter eller endrer ingen status-/restore-ressurser
- lagt eksplisitt `export-recovery-key` for Borgs krypterte repositorynøkkel med felles Borg-/SSH-/repository-ID-preflight, sikker absolutt destinasjon, no-clobber, root/`0600`, tomfilkontroll og ingen nøkkelmateriale i output
- lagt skrivebeskyttet `inspect-repository` som verifiserer repository-ID og viser bare arkivantall og nyeste sikre arkivnavn uten arkivmedlemmer eller muterende Borg-kommandoer
- dokumentert eksisterende risiko for at import-/eksport-/rapportfiler kan ligge i API-containerlaget fordi dagens Compose mangler media-mount; ingen filer eller runtime ble flyttet
- fullført en anonymisert, skrivebeskyttet stagingbaseline som verifiserte serverdisk, Compose, PostgreSQL, Docker-volumes, FileField-/mediapaths, eksisterende manuelle dumps, fravær av kolliderende automatisert backup og manglende Borg-/Storage Box-oppsett
- bekreftet at `/app/imports` og `/app/exports` ikke finnes og at filantallet er null, men at nye FileField-filer fortsatt kan gå tapt i API-containerlaget før en separat host-persistent runtimeleveranse
- korrigert backupmalens staging-environmentpath til `.env.staging` både for Compose og serverkonfigurasjons-allowlisten
- registrert prosjekteiers Console-verifikasjon: Cloud Backups er ENABLED AND FIRST BACKUP VERIFIED med første synlige backup på 11,6 GB og 0 Cloud Volumes; dette er fortsatt bare et ekstra helserverlag
- anbefalt, men ikke bestilt, BX11 med 1 TB i FSN1, kapasitetsreview ved 60–70 prosent bruk og minst 20–30 prosent ledig margin
- synkronisert ADR-007 mot ADR-008: første MVP bruker lokal host-persistent private/public-storage og kontrollert lokal serving; S3/CDN/IAM/KMS/Object Lock og provider-spesifikke purge-/`versionId`-porter er bare betingede senere krav
- beholdt leveransen PREPARED, NOT ACTIVE fordi Storage Box, Borg, recovery-secret, eksportert repositorynøkkel, off-server custody, første Borg-backup, restore-smoke, Storage Box-snapshots og timere fortsatt ikke er opprettet eller aktivert
- ikke endret CRM-runtime, Compose, database, data, publisering, modeller, API, Editor, PUBLIC, Import 2.0, containere, DNS eller Cloudflare

### Fase 3B.2: storage-, delivery-, takedown- og restoreprinsipper godkjent

- godkjent to-key-kontrakt med separat deterministisk processing artifact identity og immutable public release identity; ny offentlig revisjon bruker ny release key uten krav om ny encoding, mens eksakt key-struktur fortsatt er åpen
- godkjent dedikert unversioned aktiv public rendition-store eller likeverdig namespace uten offentlig tilgjengelige historiske versjoner; suspended versioning behandles ikke automatisk som aldri-versioned
- presisert at public delivery ikke krever anonym bucket: første MVP bruker kontrollert same-origin/lokal media-origin fra host-persistent storage; ekstern provider-endpoint, origin-begrenset objektlager og CDN er bare betingede senere krav
- godkjent private originaler med separat lokal host-persistent storage, permissions og rollebeskyttet tilgang; provider-versioning, IAM/public-access-block og eksplisitt `versionId`-bevis gjelder bare dersom objektlagring senere innføres
- godkjent hybridbackup med private originaler, metadata/profil, nødvendige referanser og audit, aktive public rendition-bytes og deny-journal i separat failure-domain; deterministisk regenerering er sekundær reparasjonsvei
- godkjent fail-closed restore-gate med ikke-offentlig karantene, nyeste deny-journal, replay/read-model, reconciliation og checksum-/referanseverifisering før public serving
- godkjent append-only/WORM-orientert autoritativ deny-journal med idempotente events, separat backup/failure-domain og deny-first-rekkefølge før origin-delete og purge; permanent teknologi er fortsatt åpen
- godkjent framtidige scopes for public release deny, tenant-checksum deny og særskilt global checksum deny; bare release deny er bevist, og checksum-deny er ikke implementert
- godkjent idempotent purgekontrakt med retryklassifisering, request-/hendelses-ID og verifikasjon; Moto og recording-adapterne forblir kun prototypeevidens, ikke produksjonsleverandør eller IAM-/CDN-bevis
- gjort skrivebeskyttet provider-/driftsgate til neste anbefalte planleggingsleveranse og beholdt fase 3B.1R og senere API-, concurrency-, retention- og sync/async-gater som påkrevd før fase 3C
- ikke implementert storage, CDN, journal, read-model, checksum-deny, modeller, migrasjoner, API, Editor eller PUBLIC; runtime, data, staging og deploy er urørt og legacy URL-/faviconflyt gjelder fortsatt

## 2026-07-31

### Fase 3B.2: isolert storage-, takedown- og restoreprototype på PR-branch

- lagt en isolert Django 5.1-lab under `spikes/storage_pipeline/` med eksplisitt bevart `default`/`staticfiles` og separate private/public image-aliaser uten å endre runtime-settings eller root-avhengigheter
- pin-net Moto Server 5.2.2, django-storages og boto3 i laben og testet create/put/get/head/delete, policy, versioning, version listing, delete marker og copy mot disponibel lokal emulator
- gjenbrukt fase 3B.1s processing artifact key og bevist separat tenant-/actor-/release-skopet R1/R2-key uten re-encoding eller overskriving av gamle public keys
- gjennomført T0–T5 med nyere deny-journal utenfor gammelt app-snapshot, origin delete, stale-cache-simulering, idempotent purge, kontrollert reintroduksjon, reconciliation, fallback og autorisert R2 mens R1 forblir denied
- sammenlignet direkte backup av aktive renditions med regenerering fra privat original + canonical metadata og anbefalt hybridmodell til prosjekteiers vurdering
- dokumentert Moto-gap der unsigned `VersionId` kunne nå eldre privat versjon; recording private-access boundary håndhever ønsket domenekontrakt, men faktisk leverandør/IAM må verifiseres senere
- anbefalt til vurdering to-key-kontrakt, unversioned aktiv public storage, hybridbackup og separat varig deny-journal; ved prototypeleveransen var anbefalingene ennå ikke godkjent, og ingen produksjonsleverandør var valgt
- lagt til separat path-filtrert spike-CI og tekstlig evidens uten secrets, eksterne data, staging eller produksjonskontakt
- ikke implementert bildearkitekturen i CRM-runtime og ikke endret modeller, migrasjoner, API, Editor, PUBLIC, root requirements, produksjonscontainere, ordinære Compose-filer, staging eller deploy; legacy URL-/faviconflyt gjelder fortsatt, fase 3B.1R og senere fase 3B-gater gjenstår

### Fase 3B.1: isolert bildebehandlings- og renditionprototype

- sammenlignet Pillow og pyvips/libvips praktisk i en separat prototypepakke og dedikert labcontainer uten runtimekobling
- generert 20 syntetiske fixtures og verifisert sikker dekoding, MIME-/byteskontroll, pixelgrense, EXIF, metadatafjerning, alpha, contain, cover, fokus og ingen automatisk oppskalering
- generert square-, landscape- og 1200 × 630-sharevarianter, deterministisk dynamisk fallback og tre statiske nødvarianter
- dokumentert byte-identisk Pillow-output over tre kjøringer og retningsgivende CPU-, minne-, tids- og filstørrelsesmålinger
- prosjekteier har godkjent Pillow bak intern adapter, statisk JPEG/PNG/WebP-input, processing profile v1, no-upscale, immutable key-invarianten og 15 MiB som konfigurerbar standardverdi
- beholdt 20 megapiksler, universelle korteste-side-bånd og edge-variance-/blurintervaller som ikke-godkjente prototypeverdier; fase 3B.1R med representative ekte bilder og sRGB/fargeprofiler er påkrevd før fase 3C
- godkjent neste fase 3B.2 som en isolert storage-, immutable-key-, purge-, deny- og restorelab uten CRM-runtime, modeller, migrasjoner, API, Editor, PUBLIC eller stagingdeploy
- flyttet den isolerte spikejobben fra ordinær CI til en separat, path-filtrert workflow med manuell trigger
- ikke endret Django-runtime, modeller, migrasjoner, API, frontend, default storage, database, staging eller deploy

### Fase 3A og ADR-007

- godkjent fase 3A-kartleggingen av thumbnail-, bilde-, storage-, import- og kortflyten som beslutningsgrunnlag
- godkjent [ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) med flyten `ImageCandidate` → kontrollert fetch og validering → tenant-eid `ImageAsset` → `OrganizationImageSelection` → `ImageRendition` → felles public image projection
- besluttet append-only bildehistorikk, versjonert ett-klikk-godkjenning, eksplisitt locking/replacement, rolleavgrenset takedown og karantene, retensjonsregler og deterministisk systemfallback
- besluttet lokal filsystemstorage og S3-kompatibel staging-/produksjonsretning gjennom Djangos `STORAGES`, med private originaler, immutable offentlige renditions og samlet backup/restore
- besluttet additiv public API-overgang og den fremtidige Import 2.0-kontrakten `KEEP_LOCKED_IMAGE`, `SET_APPROVED_IMAGE` og `USE_APPROVED_FALLBACK`
- gjort fase 3B teknisk prototype til neste aktive leveranse; leverandør, bibliotek, terskler, formater, SVG, kø, API-schema og øvrige spikevalg er fortsatt åpne
- ikke endret applikasjonskode, modeller, migrasjoner, storage, data, staging eller deploy; dagens legacy bilde-URL- og faviconflyt er fortsatt implementert adferd

## 2026-07-30

### Fase 2: kontrollert stagingreparasjon av telefonkontakter

- forhåndskontrollert kandidat-ID `1`, `2`, `132` og `150` i tenant `musikkontoretnord` uten å skrive ut kontaktverdier; alle tilhørte riktig tenant, manglet `PHONE`-kontakt og hadde ingen duplikat- eller flertydighetskonflikt
- opprettet og verifisert en tidsstemplet PostgreSQL-backup før dataendringen
- kjørt den eksplisitt godkjente, tenant-avgrensede `PHONE --apply`-reparasjonen, opprettet nøyaktig fire private primære telefonkontakter og fått `changes_applied=4`
- bekreftet med ny dry-run at ingen kandidater eller konflikter gjenstod og at `changes_applied=0`
- bekreftet med felt- og fingeravtrykkssammenligning at eksisterende telefon- og e-postkontakter, direkte persontelefoner og publiseringsflagg var uendret
- verifisert de nye private primærkontaktene i Editor-API og fravær av telefon-eksponering i aktivt PUBLIC API og PUBLIC HTML
- beholdt fase 2 som aktiv frem til prosjekteiers visuelle sluttkontroll; ingen produksjonsdeploy, publiseringsendring eller endring utenfor valgt tenant ble utført

### Fase 2 lukket og fase 3 aktivert

- lukket fase 2 som gjennomført 2026-07-30 etter at prosjekteier visuelt bekreftet i staging at undersøkelseseksemplets telefon finnes under Kontaktkanaler, er markert som primær og fortsatt har offentlig telefon avslått
- gjort robust thumbnail-, bilde- og kortarkitektur til aktiv produktfase uten å starte implementeringen
- besluttet at den konservative PHONE-reparasjonskommandoen beholdes uendret som en avgrenset legacy-reparasjon og at telefonarkitekturen ikke blokkerer fase 3
- lagt en beslutningsgate før fase 4 kan godkjennes som ferdig: et eget ADR skal da spesifisere internasjonal telefonmodell, landkontekst og normalisering
- planlagt implementering av den nye telefonarkitekturen tidlig i fase 5 og gjort stabil telefonmodell til forutsetning for full telefonmatching i fase 6
- fastlagt prinsipper om bevart originalverdi, separat normalisert sammenligningsverdi, uttrykkelig land-/regionkontekst, internasjonale numre, separat internnummer, én sentral backendtjeneste, review av tvetydige verdier og ingen publisering som følge av normalisering eller matching
- beholdt bibliotek, modell- og feltnavn, constraints, API-kontrakt, migrering og backfill som uavklart; ingen ny telefonarkitektur eller nytt ADR ble implementert

## 2026-07-29

### Verifisert staging- og frontendbaseline

- fullført fase 1 med skrivebeskyttet kontroll av lokal/GitHub `main`, staging-repo, kjørende Docker-images og containere, nginx, Caddy, frontendbundles og HTTPS-/cachekjeden
- bekreftet at kjørende JavaScript- og CSS-bundles matchet en ren build fra dagens `main`, og at proxy eller Cloudflare-cache ikke var årsak til observerte frontendavvik
- kontrollert PUBLIC på desktop/mobil og en autentisert Editor-visning; Editor-forsiden er godkjent designreferanse
- fordelt gjenstående kort-, bilde-, tag-, overflow- og formavvik til fase 3 og fase 5
- bekreftet at ingen kode, data, publiseringsflagg eller deploy ble endret under fase 1

### Fase 2: telefon, publiseringsstandarder og offentlig tittel

- utvidet `repair_person_contacts` bakoverkompatibelt med eksplisitt telefonmodus, tenant-filter, trygg dry-run og privat oppretting; konflikter rapporteres og den berørte posten hoppes over uten automatisk endring
- beholdt eksisterende e-postmodus som standard og lot eksisterende kontakt- og publiseringsflagg være urørt
- gjort publisering av ny e-post, ny telefon, ny kontaktperson og ny eksisterende personkobling avslått som standard i Editor og nullstilt ved faktisk aktør- eller tenantbytte
- tydeliggjort forskjellen mellom offentlig personvisning og offentliggjøring av en konkret kontaktkanal
- lagt `Person.title` additivt til aktivt public API og PUBLIC HTML når feltet har verdi
- utvidet backend-, frontend- og Playwright-regresjonstester uten schema-migrasjon eller data-apply utenfor testdatabasen
- merget PR #12 som merge-commit `6768af8a3b48314aec028ec5972939c6ef0e38e8` og deployet samme applikasjonsversjon kontrollert til staging
- verifisert PostgreSQL, Django, migrasjoner, containere, HTTPS, public API/HTML, alle PUBLIC-kortlenker og at ny frontendbundle faktisk serveres
- verifisert skrivebeskyttet at Editor nullstiller de fire publiseringsvalgene, skjemaet, feiltilstand og koblingsstatuser ved aktørbytte uten å sende tenantmutasjoner
- verifisert `Person.title`, fravær av tom tittelrad og fravær av direkte `Person.phone`-fallback i PUBLIC
- kjørt tenant-avgrenset `PHONE`-dry-run for `musikkontoretnord`: `49` undersøkt, `4` kandidater (`1`, `2`, `132`, `150`), ingen konflikter og `changes_applied=0`
- beholdt fase 2 som aktiv; ingen produksjonsdeploy, data-apply, kontaktverdi- eller publiseringsendring ble utført

## 2026-07-28

### Arbeidsflyt og produkt-roadmap

- merged PR #10 og fullført den repo-baserte session-workflowen med `ADR-006`, `$start-arbeidsokt`, `$avslutt-arbeidsokt`, `$fortsett-prosjekt` og totalt 15 validerte skills
- ryddet autoritativ dokumentasjon ved å holde gamle rotbaserte handoff-, `REFERENCE`- og `STATUS`-filer utenfor repoet og ignorere genererte Playwright-resultater
- godkjent revidert produkt-roadmap med staging/frontend-baseline først, deretter liten kontaktstabilisering, robust bildearkitektur, Import 2.0-design, langsiktig kontaktarkitektur, Import 2.0-implementering og eksport
- integrert AI som et gjennomgående produktprinsipp for bildevalg og importstøtte, uten automatisk overskriving eller publisering uten eksplisitt regel eller menneskelig godkjenning
- skilt sikker automatisk staging-deploy ut som et parallelt infrastrukturløp; det er fortsatt planlagt og ikke implementert eller verifisert

## 2026-07-26

### PUBLIC og kontaktpublisering

- rettet PUBLIC HTML slik at aktørkort bruker kanonisk ID-basert detaljrute (`/public/actors/id/<actor_id>/`) og ikke lenger lager ødelagte lenker for publiserte aktører uten organisasjonsnummer
- beholdt legacy-rute for organisasjonsnummer som redirect når den identifiserer én publisert aktør entydig
- lagt til skrivebeskyttet `check_public_actor_links` for å kontrollere alle PUBLIC-kortlenker
- lagt til `publish_existing_email_contacts` som dry-run først, transaksjonell og idempotent staging-/datakommando for godkjent publisering av eksisterende e-postkontakter
- korrigert relasjonsspesifikt unntak fra `Kathrine Schem` til `Kathrine Schjem`
- kjørt staging-datakjøring etter backup: `164` av `164` eksisterende e-postkontakter er offentlige, og tre aktive aktør-person-koblinger er satt til `publish_person=False`
- bekreftet at telefonpublisering og `Organization.is_published` ikke ble endret

## 2026-07-24

### Utviklingsarbeidsflyt

- godkjent og implementert `ADR-006` for session-flyt og varig prosjektminne
- lagt til `$start-arbeidsokt` og `$avslutt-arbeidsokt`
- standardisert Git-baseline, project health, SESSION WRAP-UP og neste Codex-session-prompt
- utvidet ADR-006 med `$fortsett-prosjekt` som strategisk ChatGPT-rutine og tynn Codex-bro
- lagt til fast `CHATGPT SESSION SUMMARY` og dokumentert kontinuitet mellom nye ChatGPT-samtaler og Codex-sessioner
- validert alle 15 skills og bekreftet `$fortsett-prosjekt` i en separat skrivebeskyttet Codex-session

## 2026-07-23

### Dokumentasjon

- etablert ny dokumentasjonsstruktur på egen branch
- kartlagt at IMPORT er langt mer utviklet enn eldre prosjektfiler beskriver
- registrert at EKSPORT har datamodell og API-grunnlag, men ikke komplett motor
- registrert at public HTML foreløpig kun brukes i staging
- registrert ønsket om automatisk staging-deploy ved push
- godkjent `ADR-005` som målarkitektur for helhetlig personkontakt og relasjonsspesifikk publisering; implementering er ikke startet
