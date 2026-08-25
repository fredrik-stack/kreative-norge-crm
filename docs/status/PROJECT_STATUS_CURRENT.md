# Project Status Current

**Status:** Fase 1 og 2 gjennomført; fase 3 er **CLOSED / VERIFIED** etter fullførte 3A–3F-gater. Lokal Hetzner storage-/backup-MVP og ADR-009 fase 3E.1A safety-ledger/off-server anchor er **ACTIVE** i staging; fase 3E.1B-materialisering er **ACTIVE / VERIFIED**; fase 3E.1C-controlled serving er **CLOSED / ACTIVE**; fase 3E.2 projection/API shadow er **CLOSED / SHADOW VERIFIED**; fase 3E.3 API/PUBLIC/head-cutover og fase 3E.4 ledger-v2/formell takedown er **CLOSED / ACTIVE** i staging; fase 3F legacy-/Import-kontrakt og restore er **CLOSED / VERIFIED** med den nye Import-gaten av i shared staging. Fase 4A–4F er godkjent, merget og stagingverifisert; 4D innførte additiv nullable persistens uten backfill, 4E aktiverte den eksplisitte interne write-kontrakten, og 4F koblet samme kontrakt til Import. Fase 4G-koden for kontrollert legacybackfill er implementert og avventer separat review, CI, merge, backup og staging apply. Fase 4H er ikke startet. Brave er operativt ikke aktiv for ordinære Editor-sluttbrukere

**Teknisk sist verifisert:** 2026-08-26

**Teknisk verifisert mot:** fase 2-applikasjonsversjonen i merge-commit `6768af8a3b48314aec028ec5972939c6ef0e38e8`, senere additive fase 3-leveranser, stagingbranchens runtimecommit `17919df0d8778ad2600914d4459415466bfcf8e2`, 3D.2-baseline `34f6f35287eaf461d73d40bed25e26f2d4f4b198`, precision/zoom-runtimecommit `3686f08006a1396fd1e2ce250603044c4b62e041` og PR #33s mergecommit `48f23f183dacb8331a64b86f1d7574250cbfbe02` på `main`. 3E.1A er utviklet fra verifisert `origin/main` `9f1159d9cb237520986585e487bbef45fe68c4ad`; 28 safety-tester og alle seks CI-jobber i run `32413908257` er grønne på operatorfix/head `c0c9a86deedbe9d8fd12cfcf73376338cccde449`. Live staginggaten verifiserte Borg `1.2.8`, dedikert repository-ID `40a469b096ffa44de89aae5f187dfd9d9aefc873a874bfb8ef718180be1cb896`, forskjellig ADR-008-ID, custody for minst to ansvarlige, genesis, syntetisk reservation/ACTIVE/DENIED, idempotens og konfliktavvisning, delete/compact/raw-`rm`-capability, separat transaction recovery av både probe og nyeste DENIED-head, stale incident-restore-avvisning før destination/receipt, eksakt incident restore/rebuild/health, nyere DENIED over eldre ACTIVE, isolert fail-closed-adferd og host-restart med identisk ledger-checksum. Health-timeren er aktiv; API/web mangler safety-mount, Borg og credentials; ingen public delivery-root, releasefil eller serving ble opprettet. Se [3E.1A-aktiveringen](STAGING_PHASE_3E1A_ACTIVATION_2026-08-20.md), [historisk 3E.1A-forberedelse](STAGING_PHASE_3E1A_PREPARATION_2026-08-17.md), [3D.2-stagingverifiseringen 2026-08-11](STAGING_IMAGE_SOURCES_2026-08-11.md), [stagingaktiveringen 2026-08-10](STAGING_IMAGE_RUNTIME_ACTIVATION_2026-08-10.md) og [backupaktiveringen 2026-08-02](STAGING_BACKUP_ACTIVATION_2026-08-02.md).

3E.1B-foundationen er deretter verifisert mot PR #38-merge `d756b4b13fc7c5cee5e37dcf48b7ce24e91ef1c1`, grønne PR-/main-CI-runs `32630246582`/`32630497627` og den separate [staginggaten 2026-08-23](STAGING_PHASE_3E1B_FOUNDATION_2026-08-23.md). Gaten anvendte migrasjon `0029` fra tom release-tabell, beholdt `0` releases og materialiseringsflagget av, beviste socket/peer/mountisolasjon og 5/45/50/60-timeoutkjeden og verifiserte delivery-checksum i backup `kreative-norge-staging-20260823T134222Z` og isolert restore.

Den separate [3E.1B-materialiseringsaktiveringen 2026-08-23](STAGING_PHASE_3E1B_MATERIALIZATION_ACTIVATION_2026-08-23.md) ble gjennomført fra `main` på merge `ee42c8217a7d32321be7d35ecfb368a280e6df82` etter grønn main-CI-run `32646334974`, 25 målrettede lokale tester og pre-activation-backup `kreative-norge-staging-20260823T185358Z`. Gaten beviste hard no-clobber, permanent reserve og DB-binding, kontrollert crash etter første fil, API-restart, read-back, fullføring, activation og ny idempotent retry uten overskriving eller duplikate ledger-events. Ved avslutningen hadde staging én aktiv syntetisk release, tre persistente delivery-filer og `READY` safety-ledger på cursor `5`; post-activation-backup `kreative-norge-staging-20260823T185950Z` var fullverifisert og isolert restore-verifisert. Serving, projection, API/PUBLIC og legacy-cutover var da fortsatt av.

Den separate [3E.1C-servingaktiveringen 2026-08-24](STAGING_PHASE_3E1C_ACTIVATION_2026-08-24.md) ble fullført fra `main` på merge `38663b532de64eb15b5ec6579dbb7d66a0eb18fe` etter separat review av PR #41–#44 og grønn main-CI-run `32668678789`. Gaten beviste canonical GET/HEAD/304 for tre varianter med identiske bytes og checksum-`ETag`, tomme 404/405/503-responser, read-only safety-scope, bridge-/filfeil og recovery, origins, sanitert logging, socket-/mount-/workerisolasjon og API/web/bridge-restart. Staging har nå to releases, seks delivery-filer og safety-ledger `READY` på cursor `7`. PUBLIC HTML/API, 122 publiserte aktører og legacyredirecten var uendret og inneholdt ikke release-UUID-en. Post-activation-backup `kreative-norge-staging-20260823T220249Z` er fullverifisert og isolert restore-verifisert.

Den separate [3E.2-shadowgaten 2026-08-24](STAGING_PHASE_3E2_SHADOW_2026-08-24.md) ble gjennomført fra implementerings-PR #47 og eksakt merge `90ff5e96f5370c22546d378234cc0ac219b71ec1` etter grønn PR-/main-CI. Fullkatalogen ga `122 = 1 asset + 121 systemfallback`, `0` safety-unavailable, `0` scopefeil, fem queries og tre authorize-kall. API list/detail og OpenAPI var eksakt uendret mellom shadow av/på; PUBLIC var semantisk uendret utover sin eksisterende `random.shuffle(tags)`. Asset/fallback/unpublished, alle seks HEAD-kall, sanitert logg, performance og automatisk API-only rollback ble bevist. Safety forble `READY` på cursor `7`; PostgreSQL-radantall og seks deliveryfiler med manifest-hash `fb94a302...` var uendret. `PUBLIC_IMAGE_PROJECTION_ENABLED=True` gjelder bare ignorert stagingkonfigurasjon; `PUBLIC_IMAGE_API_SCHEMA_ENABLED=False`, PUBLIC legacy og 3E.3-stoppunktet er bevart. Kode-/eksempelstandard for begge flagg er fortsatt `False`, og ingen migrasjon ble lagt til.

Den separate [3E.3-cutovergaten 2026-08-24](STAGING_PHASE_3E3_CUTOVER_2026-08-24.md) ble sluttført på eksakt deployet merge `e04220b783c8d572846de595e1ce955c85bd30ed`. Implementerings-PR #49 og aktiveringsblocker-fix PR #50 fikk separate fullreviews og seks grønne CI-jobber hver. Schema og PUBLIC ble begge aktivert, rollbacket og reaktivert uten state-write. API, PUBLIC list/detail, canonical, Open Graph og Twitter bruker nå samme projection; fullkatalogen er `122 = 1 asset + 121 systemfallback`. Den avsluttende stagingprofilen lukket en N+1-blocker og målte API-listen til `11` SQL-spørringer i stedet for `299`. Safety forble `READY` på cursor `7`, de seks deliveryfilene beholdt manifest `fb94a302...`, og backup `kreative-norge-staging-20260824T131620Z` var fullverifisert og isolert restore-verifisert. Ingen modell/migrasjon, tenant-enrollment eller 3E.4-funksjon ble lagt til.

Den separate [3E.4-takedowngaten 2026-08-24](STAGING_PHASE_3E4_TAKEDOWN_2026-08-24.md) ble fullført på eksakt deployet merge `087026e7e8bb43f9619c605e75f538976c6f1566` etter separat frozen-head-review av PR #52 og grønn 6/6 PR-/main-CI. Ledgeren ble oppgradert additivt fra schema v1 til v2 med uendret ledger-ID og bevarte sju v1-events. Én permanent syntetisk release-/tenant-checksum-deny ble ankret før fallback/origin-delete; gammel URL ga `404/no-store`, gammel ETag ga aldri `304`, Cloudflare ga aldri `HIT`, og retry, samme-byte-blokkering, 3E.3-rollback, fysisk mediarestore, sikker republisering, restart og backup/restore var grønne. Safety er `READY` på cursor `13`. Den unpubliserte testhistorikken består i PostgreSQL og ledger; normal katalog er tilbake på `122 = 1 asset + 121 systemfallback` med fem projectionqueries.

Den separate [3F-gaten 2026-08-25](STAGING_PHASE_3F_LEGACY_IMPORT_2026-08-25.md) ble fullført på eksakt implementasjonsmerge `438a4800ded325fdf1ba99acc3d03812fb9ef1e9` etter frozen-head-review uten funn og grønn 6/6 PR-/main-CI. Migrasjon `0031` ble anvendt uten backfill. To identiske legacyinventar, gate av → på → av, 7 off-state/no-network-tester, 18 typed KEEP/SET/FALLBACK-/scope-/stale-/deny-/idempotens-tester, existing-import-/API-/PUBLIC-regresjoner, older DB/media mot nyere safety, orphan dry-run og pre-/postdeploy-backup med full verify/isolert restore var grønne. Live ImportImageDecision/eventbinding forble `0`, public katalog `122 = 1 asset + 121 fallback`, safety `READY` cursor `13`, DB-/release-/deny-state og ni deliveryfiler var uendret. Shared staging og kode-/eksempelstandard avsluttet med `IMPORT_IMAGE_DECISIONS_ENABLED=False`. Fase 3F og fase 3 er dermed lukket. Fase 4A dokumenterer nå telefonarkitekturen; Import 2.0-UX, fysisk feltdropp, generell retensjon og providerpurge er fortsatt ikke startet.

Den separate [4B-telefonbaselinen 2026-08-25](STAGING_PHASE_4B_PHONE_BASELINE_2026-08-25.md) ble gjennomført mot stagingruntime `438a4800ded325fdf1ba99acc3d03812fb9ef1e9` fra dokumentasjonsbaselinen `e2bddc9b2cade3baeeb2017d9dd3ce32eab1207a`. To separate PostgreSQL-transaksjoner rapporterte `transaction_read_only=on` og ga byteidentiske aggregater og fingerprints for 128 organisasjoner, 157 personer, 56 PHONE-kontakter og 176 OrganizationPerson-lenker. Container-ID, image, starttid og restartteller var uendret før/etter. Hovedreviewgruppen er nasjonalt skrevne verdier uten eksplisitt regionkontekst; null tenantavvik, null flere primærkontakter, null direktefelt/primærkontakt-avvik og null delte eksakte persontelefoner ble funnet. Resultatet er `READY_FOR_4C`; ingen rå telefoner, dependency, kode, migrasjon, data, runtime, deploy eller 4C-implementasjon inngikk.

Fase 4C pinner `phonenumbers==9.0.37` og etablerer [én ren typed telefonadapter](../architecture/PHONE_NORMALIZATION.md) med `VALID`, `INVALID` og `NEEDS_REGION`, E.164 bare ved gyldig resultat og stabile ikke-sensitive årsakskoder. Nasjonale numre krever eksplisitt region, `+` er regionuavhengig, `00` følger bibliotekets IDD-regler og extensions avvises. Adapteren har ingen I/O eller Django-/modell-/tenantkobling. [Staginggaten](STAGING_PHASE_4C_PHONE_NORMALIZATION_2026-08-25.md) verifiserte dependency, syntetisk smoke, to identiske read-only klassifiseringer av 4B-data, uendrede fingerprints, API/PUBLIC og image/safety. Resultatet er `READY_FOR_4D`.

**Produkt-roadmap sist oppdatert:** 2026-08-25

**Arbeidsflyt sist kontrollert:** 2026-07-28

**Ansvar:** Prosjekteier + ChatGPT for prioritering og produktretning. Codex for oppdatering etter implementering.

## Aktiv utviklingsfase

Fase 1 i [ROADMAP.md](ROADMAP.md) ble gjennomført 2026-07-29. Den skrivebeskyttede baselinen verifiserte server-, container-, bygg-, proxy-, cache-, PUBLIC- og Editor-tilstanden. Hoveddesignet på forsidene i Editor CRM og PUBLIC er godkjent designreferanse. Øvrige sider, kort og komponenter skal videreutvikles innenfor denne visuelle retningen.

Fase 2 ble gjennomført 2026-07-30 etter teknisk stagingverifisering, kontrollert reparasjon av fire private primære legacytelefonkontakter og prosjekteiers visuelle sluttkontroll.

Fase 3A kartla deretter dagens thumbnail-, bilde-, storage-, import- og kortflyt uten endringer. [ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md) er godkjent som arkitekturgrunnlag.

[Fase 3B.1](PHASE_3B1_IMAGE_RENDITION_SPIKE.md) har gjennomført en isolert bildebehandlings- og renditionprototype med syntetiske fixtures. Pillow og pyvips/libvips, sikker dekoding, contain/cover, fokus, formater, determinisme, fallback og ressursbruk er målt. Prosjekteier har godkjent Pillow bak intern adapter, statisk JPEG/PNG/WebP-input, processing profile v1, no-upscale, immutable key-invarianten og 15 MiB som konfigurerbar standard.

[Fase 3B.1R](PHASE_3B1R_REPRESENTATIVE_QUALITY_HARNESS.md) er **GJENNOMFØRT / GODKJENT** etter lokal kjøring og manuell review av 24 rettighetsavklarte fixtures. 36 MP er konfigurerbar decoded-pixel-standard for MVP; ingen universell minimumsdimensjon eller automatisk oppskalering brukes; obligatoriske renditions vurderes separat etter fit, faktisk cropområde og scaling margin. Edge variance og blockiness er advisory uten numerisk hard fail, logowhitespace kan gi warning/manual review, og offentlig MVP-output normaliseres eller konverteres til sRGB før crop/resize og skrives uten innebygd ICC-profil. Untagged registreres som antatt sRGB; korrupt/uleselig ICC er kontrollert teknisk feil. Kildebilder, privat manifest og visuell/full evidens forblir Git-ignorert.

[Fase 3B.2](PHASE_3B2_STORAGE_RESTORE_SPIKE.md) er teknisk gjennomført som isolert prototype. Den målte separate Django-storagealiaser, gjenbrukt processing artifact key, separat public release key, private/public Moto-buckets, versioning, purge/cache, deny-journal, T0–T5 restore-reconciliation, backupstrategier og statisk fallback. Prosjekteier godkjente 2026-08-01 de leverandøruavhengige prinsippene om to-key-kontrakt, en aktiv public rendition-store uten tilgjengelige historiske public versjoner, kontrollert public delivery, private originaler, hybridbackup, fail-closed restore, varig deny-journal/read-model og idempotent purge. ADR-008 har senere valgt lokal host-persistent storage for første MVP; providerkravene fra prototypen er derfor betingede dersom objektlagring senere tas opp igjen.

Fase 3B.3 er **GJENNOMFØRT / GODKJENT** som arkitektur- og kontraktgate. [ADR-007 punkt 25](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md#25-fase-3b3-godkjent-public-release-identity-og-key-kontrakt) fastsetter tilfeldig UUIDv4 som separat immutable public release identity og relative canonical keys på formen `releases/<release_uuid>/<variant>.<ext>`. Replacement, restore og senere autorisert republisering går via ny selection-revisjon og får alltid ny release-ID, mens retry av samme selection-revisjon gjenbruker samme reservation/UUID/keys. Fase 3B.3-A etablerte modellgrunnmuren; fase 3E.1A etablerte den aktive ledgeren, 3E.1B implementerte DB-/filmaterialisering, 3E.1C aktiverte kontrollert serving og 3E.2 er `CLOSED / SHADOW VERIFIED`.

[ADR-008](../decisions/ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md) velger en enklere operasjonell MVP: app, database og aktiv media på dagens Hetzner Cloud-server, lokale navngitte Django-storagealiaser og kryptert Borg-backup til separat Hetzner Storage Box. S3/AWS/Backblaze/CDN utsettes. Backupgrunnmuren er **ACTIVE** etter verifisert Storage Box, kryptert repository, separat recovery-custody for minst to ansvarlige, første backup, full repository-check, isolert restore av samme arkiv, Storage Box-snapshot, nyere synlig Cloud Backup og aktiverte timere. Første backup tok 8 sekunder og restore-smoke 8,7 sekunder. Foreløpig RPO er inntil omtrent 24 timer pluss timerforsinkelse; restore-smoke-målingen er evidens, ikke et løfte om full katastrofe-RTO.

[ADR-009](../decisions/ADR-009-PUBLIC_IMAGE_RUNTIME_RELEASE_DELIVERY_AND_RESTORE_SAFE_DENY_STATE.md) er godkjent som fase 3E-arkitektur. Fase 3E.1A er implementert og **ACTIVE** i staging som en Django-/PostgreSQL-uavhengig SQLite-ledger med permanent UUID/key-reservasjon, canonical payload/hashkjede, rebuildbare release-/checksum-/legacyguard-read-models, synkron Borg create/read-back, immutable local receipts, standalone incident restore og fail-closed health. Ledgeren ble additivt oppgradert fra schema v1 til v2 i 3E.4 uten å omskrive de sju v1-eventene. Fase 3E.1B.1–3E.1B.2 er implementert med atomisk `reserve_or_get`, root-eid systemd socket/bridge, unik selection-binding og revision-snapshot i PostgreSQL, separat delivery-root, create-only/no-clobber, faktisk bilde-read-back og idempotent activation. Foundationen ble deployet mot merge `d756b4b`, materialisering aktivert mot `ee42c82`, serving mot `38663b5` og ledger-v2/takedown mot `087026e`. Staging har fire release-aggregater, ni deliveryfiler og safety `READY` på cursor `13`; alle kode-/eksempelstandardene forblir av.

Fase 3E.1C legger til streng canonical `GET`/`HEAD`-route, eksakt DB-/publication-/tre-filers gate, read-only safety-`authorize`, writer-preferred lifecycle-synkronisering, intern Nginx `X-Accel-Redirect`, read-only deliverymount, eksplisitte allowlistede origins, private 60-sekunders revalidation og strukturerte utfallslogger. Kode- og eksempelstandard er fortsatt `PUBLIC_IMAGE_SERVING_ENABLED=False`, mens ignorert stagingverdi er `True`. 3E.2 gjenbruker samme releasevalidering og safety-autorisasjon i read-only projection og er `CLOSED / SHADOW VERIFIED`. 3E.3 er `CLOSED / ACTIVE`; ignorert stagingkonfigurasjon har både targetschema og PUBLIC/head-cutover `True`, mens kode-/eksempelstandardene fortsatt er `False`. 3E.4 er `CLOSED / ACTIVE`; staging kjører ledger v2 og writegaten `True`, mens kode-/eksempelstandarden fortsatt er `False`. Se [3E.1B-foundationen](STAGING_PHASE_3E1B_FOUNDATION_2026-08-23.md), [3E.1B-aktiveringen](STAGING_PHASE_3E1B_MATERIALIZATION_ACTIVATION_2026-08-23.md), [3E.1C-aktiveringen](STAGING_PHASE_3E1C_ACTIVATION_2026-08-24.md), [3E.2-shadowgaten](STAGING_PHASE_3E2_SHADOW_2026-08-24.md), [3E.3-cutovergaten](STAGING_PHASE_3E3_CUTOVER_2026-08-24.md) og [3E.4-takedowngaten](STAGING_PHASE_3E4_TAKEDOWN_2026-08-24.md).

3E.4 er implementert bak kode-/eksempelstandarden `PUBLIC_IMAGE_TAKEDOWN_ENABLED=False`, med additiv ledger schema v2, atomisk release-/tenant-checksum-deny, checksum-/legacyguard, rolleavgrenset intern API-action, append-only audit, fallbackrevisjon og eksakt no-follow origin-delete. Ignorert stagingkonfigurasjon har writegaten `True`, ledger v2 og én permanent syntetisk tenant/checksum-deny; restore/republish/restart/backup er liveverifisert. ADR-009 lover ikke absolutt WORM eller vern mot kompromittert Hetzner control plane, Storage Box main user, host-root eller kombinerte admincredentials. Etter første deny er rollback bare å stoppe nye writes; eksisterende deny-/guard-/auditstate er forward-only.

Baselinen fant ingen eksisterende `/app/imports`-, `/app/exports`- eller host-mediafiler. De to bildealiasene har nå host-persistente mountpoints, mens Django default storage fortsatt peker til `/app` uten persistent import-/eksportmount; nye generelle FileField-filer kan derfor gå tapt ved recreate. Aktiv Storage Box er BX11 med 1 TB i FSN1, med kapasitetsreview ved 60–70 prosent faktisk bruk og 20–30 prosent ledig margin.

Det separate infrastrukturløpet for ADR-008 er fullført. Første fase 3C-leveranse innførte `IMAGE_ASSET_FEATURE_ENABLED=False` som standard og separate lokale `FileSystemStorage`-aliaser for private originaler og artifacts. Fase 3C.7 bruker aliasene gjennom en intern upload-only tjeneste når feature eksplisitt aktiveres. Tjenesten validerer, normaliserer og renderer før den skriver original og tre renditions med interne tenant-scopede keys, eksakt no-clobber og byte-/checksumverifikasjon, og committer deretter et komplett databaseaggregate atomisk. Fire release-aggregater finnes nå i staginghistorikken; én ordinær publisert release brukes av target-API/PUBLIC/head, én syntetisk release er permanent denied uten origin, og én ny syntetisk safe-republish-release består på en unpublisert testaktør. 3E.3- og 3E.4-gatene er aktive bare i ignorert stagingkonfigurasjon.

Asset-/renditiongrunnmuren fra PR #19, `OrganizationImageSelection`-skjemaet fra PR #20, PR #21s locking-/replacement-kjerne og PR #22s fjerning til fallback er merget. Fase 3C.6 fullfører den planlagte ordinære selection-livssyklusen med `restore_archived_organization_image_selection`: kommandoen gjenoppretter én eksplisitt, eldre og arkivert asset-selection som en helt ny aktiv revisjon og registrerer `selection_restored`. Restore-kilden og dagens aktive selection forblir historiske rader; bare dagens aktive status arkiveres. Restore kopierer det eksisterende rendition-settet, alt-teksten og offentlig kreditering uten ny approval eller proveniens. Endret godkjenningsgrunnlag eller presentasjonsinnhold skal fortsatt bruke vanlig replacement. Alle tre offentlige selection-kommandoer bruker samme tenant-scopede `Organization`-lås, capabilitymatrise, `expected_revision` og atomiske eventskriving. Eventhistorikken er append-only på applikasjons-/ORM-nivå, ikke database-WORM, og databasen kan ikke alene bevise at restore-kilden var arkivert og tilhørte samme tenant og organisasjon; dette håndheves av domenekommandoen.

Fase 3D.1 er merget med PR #30 og legger til den første offisielle kandidatflyten i intern API og Editor. En produksjonsrettet fetchadapter validerer alle DNS-resultater, binder forbindelsen til validert global IP, revaliderer redirects, avviser downgrade/credentials/private adresser og håndhever timeout, MIME og 15 MiB. Discovery bruker bare `Organization.website_url`, lagrede OG-verdier og maksimalt én sidefetch, returnerer maksimalt seks dedupliserte kandidater og lagrer ingen kandidatmodell. Kortlivede signerte refs binder kandidat og senere approval til tenant, Organization og bruker. Kandidat-preview er ephemeral; bare valgt kandidat sendes gjennom 3C.7. Eksplisitt approval bruker eksisterende locking/replacement og eventproveniens. Processing eller discovery oppretter aldri selection. Featureflagget er fortsatt avslått som kode-default, men 3D.1 er teknisk aktivert i staging etter grønn persistence-, backup-, restore- og visuell gate. Minimal dry-run-first orphan-cleanup er implementert.

Fase 3D.2 er gjennomført og merget til `main` med PR #33 og utvider den prioriterte brukerreisen til offisiell nettside/Open Graph → Brave Image Search → limt direkte URL → manuell upload. Brave-forslaget bruker alltid lagret aktørnavn som basis og legger bare til kommune automatisk når nøyaktig én er lagret. Flere kommuner, kategori og aktivt tilknyttet person krever eksplisitt valg; tags brukes aldri, og querybygging og lokal rangering bruker ingen AI. Eksakt query og querykilder er synlige og redigerbare. Provideradapteren sender `country=NO`, `search_lang=nb`, `safesearch=strict`, `spellcheck=false` og `count=30`; `nb` er nødvendig fordi den offisielle enumen ikke støtter `no`. Full providerrespons lagres aldri; bare query og normaliserte nødvendige kandidatfelt beholdes i kortlivede signerte refs, ikke i en persistent kandidatmodell eller søkehistorikk, og valgt Brave-event lagrer ikke providerens bilde-/side-URL under standardvilkårenes lagrings-/cachingbegrensning. Braves egne standard query-logger kan beholdes i opptil 90 dager; Zero Data Retention krever Enterprise/egen avtale og er en separat providergrense fra appens omtrent 30 minutter gamle signed-ref.

Editor har norske provider-/fetch-/processingfeil, fokusforvalg Venstre/Midt/Høyre og Topp/Midt/Bunn, presis X/Y, 100–300 % Foto-zoom og tre live previews med samme cropgeometri som serverprocessing. Logo viser hele motivet med contain og uten cropkontroller. Asset-alttekst kan være tom uten skjult fallback. Migrasjon `0027` beholder den dokumenterte blank-alt-rollbackgrensen; additiv migrasjon `0028` gir historiske rendition-sett zoom `1.0000`, constraint 1–3 og reverse-guard etter non-default zoom. Fase 3D.2 er lokal-/CI-/teknisk stagingverifisert og visuelt eiergodkjent. Prosjekteier har bekreftet at Logo uten crop-/zoomkontroller er riktig kontrakt, og at Foto-zoom betyr innzooming og retur til standard cover-nivå uten mulighet for å zoome ut til tom flate. Brave-parametrene, privacy-/rettighetscopyen og `search_lang=nb` er eiergodkjent, og den historiske live providerreisen er grønn. Brave er nå operativt deaktivert i staging og kan ikke aktiveres for ordinære Editor-sluttbrukere før avtaleeier dokumenterer den manuelle sluttbrukeravtalegaten. Public release, materialisering, projection, serving, PUBLIC, persistent kandidat, permanent journal og retentionpolicy er uendret og ikke levert av 3D.2.

Den langsiktige relasjonsspesifikke kontaktmodellen fra [ADR-005](../decisions/ADR-005-CONTACT_ARCHITECTURE.md) kommer fortsatt senere. Godkjent [ADR-010](../decisions/ADR-010-INTERNATIONAL_PHONE_IDENTITY_AND_NORMALIZATION.md) presiserer internasjonal telefonidentitet og fase 4A–4H. Fase 4B etablerte en skrivebeskyttet, personvernredigert [stagingbaseline](STAGING_PHASE_4B_PHONE_BASELINE_2026-08-25.md), og fase 4C implementerte og [stagingverifiserte](STAGING_PHASE_4C_PHONE_NORMALIZATION_2026-08-25.md) det rene normaliseringsdomenet. Fase 4D og 4E er deretter stagingverifisert med additiv nullable persistens uten backfill og eksplisitte interne callers. Fase 4F kobler samme kontrakt til Import og matching og avventer egen review-/CI-/staginggate; kontrollert legacybackfill og sluttverifikasjon gjenstår i 4G–4H.

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

Fase 3C implementeres additivt bak featuregaten. Fase 3B.1R, 3B.3, 3B.3-A og 3C.7 er gjennomført. Host-persistente interne stagingpaths er aktivert og restore-verifisert. ADR-009s 3E.1A, 3E.1B-materialisering og 3E.1C-serving er **ACTIVE** i staging. Separat public delivery-root og bridge er live backup-/restore-verifisert. Projection/API-shadow er `CLOSED / SHADOW VERIFIED`; schema/PUBLIC/head-cutover og formell takedown er `CLOSED / ACTIVE`. Production fallback v1, blank alttekst, tenant/checksum-deny og forward-only rollback er aktive kontrakter. Eksterne alertterskler og generell release-retensjon avgjøres bare ved senere dokumentert behov.

Godkjent fase 3B.2-kontrakt skiller intern artifact identity fra public release identity. ADR-009 plasserer artifacts og public releases i separate roots og velger kontrollert serving fra lokal host-persistent storage. Private originaler og artifacts skal forbli private. Hybridbackup inkluderer aktive rendition-bytes, mens ledger/deny-state har fått separat failure-domain og live-verifisert fail-closed restore-gate i 3E.1A. Delivery/materialisering er aktiv og restore-verifisert i 3E.1B, og serving er liveverifisert i 3E.1C. Full katastrofe-RTO gjenstår; backup-RPO og restore-smoke er foreløpig målt. Ekstern S3/CDN er utsatt.

Godkjent fase 3B.3-kontrakt gjør public release identity til en separat, varig reservert UUIDv4 og bruker canonical relative keys `releases/<release_uuid>/<variant>.<ext>`. R1 → R2 kan bruke identiske `ImageRendition`-bytes uten ny encoding, men R2 får alltid ny UUID og nye keys. Fase 3B.3-A bevarer mappingen til tenant, Organization, selection, rendition-sett og artifact gjennom immutable relasjoner og snapshots uten å eksponere disse identitetene i keyen. Hver public key genereres internt og valideres mot eksakt builder-resultat for release-ID, variant og outputformat; caller kan ikke levere fri key. ADR-009s reservation-, binding- og materialiseringsgater er implementert i 3E.1B, controlled serving i 3E.1C, projection-shadow i 3E.2, aktiv API/PUBLIC/head-cutover i 3E.3 og liveverifisert deny/republish i 3E.4.

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

### 3. Thumbnail-, bilde- og kortarkitektur – fase 3D.2 gjennomført og merget

Fase 3A-kartleggingen, ADR-007 og fase 3B-grunnlaget er gjennomført. ADR-008s lokale Hetzner-MVP er **ACTIVE**. Fase 3C og 3D.1–3D.2 er gjennomført som tidligere dokumentert; Brave er operativt deaktivert i påvente av sluttbrukeravtalegaten. ADR-009s 3E.1A safety-ledger/off-server anchor, 3E.1B-materialisering og 3E.1C-controlled serving er **ACTIVE** i staging, 3E.2 er **CLOSED / SHADOW VERIFIED**, og 3E.3–3E.4 er **CLOSED / ACTIVE**. `image_renditions_public` er fortsatt bare artifact-storage. Staging har fire release-aggregater og ni delivery-filer; den permanent denied releasen har ingen originfiler. Ledger v2, permanent syntetisk takedown og live restore-/republishbevis er fullført.

Deretter skal Import 2.0 gjennom en egen produkt- og UX-designfase før større kodeendringer. Dagens importmotor skal gjenbrukes der den er solid, men skal ikke låse den nye brukeropplevelsen.

### 4. Internasjonal telefonidentitet – fase 4C READY_FOR_4D

[ADR-010](../decisions/ADR-010-INTERNATIONAL_PHONE_IDENTITY_AND_NORMALIZATION.md) fastsetter E.164 som kanonisk maskinidentitet, libphonenumber-modellen bak én intern adapter, eksplisitt regionkontekst, typed normaliseringsutfall og konservativ additiv legacyovergang for både person- og organisasjonstelefon. [Fase 4B](STAGING_PHASE_4B_PHONE_BASELINE_2026-08-25.md) kartla staging skrivebeskyttet. Fase 4C har implementert og [stagingverifisert](STAGING_PHASE_4C_PHONE_NORMALIZATION_2026-08-25.md) bare den rene, felles normaliseringskontrakten med eksakt pinnet dependency; den er ennå ikke koblet til noen modell eller brukerreise. Neste separate gate er planlegging av 4D; 4D er ikke startet.

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

## Fase 4A–4C – godkjent retning, verifisert databaseline og isolert normaliseringsdomene

Den konservative PHONE-reparasjonskommandoen fra fase 2 beholdes uendret som en avgrenset legacyreparasjon. [ADR-010](../decisions/ADR-010-INTERNATIONAL_PHONE_IDENTITY_AND_NORMALIZATION.md) er godkjent av prosjekteier og merget med PR #56; den presiserer ADR-005 uten å erstatte den.

Låst målretning:

- E.164 er kanonisk maskinidentitet for gyldige telefonnumre, mens presentasjons-/råverdi bevares separat
- Google libphonenumber-modellen brukes gjennom en egnet Python-implementasjon, normalt `phonenumbers`, bak én intern adapter
- nasjonale numre krever eksplisitt tenant- eller importregion; Norge er ikke en skjult universell gjetning
- normalisering skiller typed mellom gyldig, ugyldig og tvetydig/manglende region
- person- og organisasjonstelefon bruker samme prinsipper og domenegrense
- lik E.164 er et sterkt matchsignal, men ikke personidentitet, global unikhet eller automatisk mergegrunnlag
- legacydata migreres gjennom read-only inventory, deterministisk klassifisering, safe additive backfill og review av rester
- normalisering og matching endrer aldri publisering

Fase 4 er nå `International phone identity foundation` med leveransene 4A–4H. Fase 4B fant 113 ikke-tomme telefonlagringsrader på tvers av organisasjonsfelt, direkte personfelt og PHONE-kontakter; 111 mangler eksplisitt internasjonalt prefiks, mens de direkte personfeltene og primærkontaktene overlapper. To read-only-kjøringer var byteidentiske, alle fingerprints og runtimeidentiteter var uendret, og resultatet var `READY_FOR_4C`. Fase 4C implementerer `phonenumbers==9.0.37` bak en ren, immutable typed adapter og syntetiske kontrakttester. API-only staginggaten verifiserte de samme 111 radene som `NEEDS_REGION` og de to overlappende internasjonale lagringsradene som `VALID`, med uendrede datafingerprints. Resultatet er `READY_FOR_4D`. 4D–4H, modeller, migrasjoner, dataendringer, Editor/importendringer og samlet sluttverifikasjon gjenstår. Extensions avvises eksplisitt og er utenfor MVP og fase 4. Full Import 2.0-design og -implementering ligger i senere faser.

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
- full katastrofe-RTO for den samlede image-/database-/ledger-recoveryen; 3E.1As avgrensede safety-ledger incident recovery er live-verifisert, men er ikke et løfte om komplett system-RTO
- ADR-009s gjenstående driftsvalg etter 3E.4-MVP-en: generell release-retensjon og eksterne alertterskler; takedown er synkron deny-first, bruker privat revalidation uten ekstern purge og krever 404/no-store, ingen 304/HIT og fysisk originfravær i liveverifikasjonen
- eksplisitt publiseringsfelt for organisasjonens e-post
- roller for kontaktpublisering, bulkpublisering og full kontakt-eksport
- behandlingsgrunnlag og retensjon for kontakt-, import-, eksport- og auditdata
- versjonering av ny public kontaktkontrakt
- om personens offentlige tittel senere skal være koblingsspesifikk
- konkrete modell-, felt- og enumnavn, constraints, indekser og API-kontrakt for E.164-verdi og eksplisitt regionkontekst
- konkret backfill-, review-, aktiverings- og rollbackmekanisme innen ADR-010s additive og konservative grenser; 4B-inventorymetoden er nå verifisert

## Dokumentasjonsstatus

`docs/` er autoritativ dokumentasjonsstruktur og er kvalitetssikret på overordnet nivå mot dagens kodebase. PR #10 fullførte session-workflowen og holdt gamle rotbaserte handoff-, `REFERENCE`- og `STATUS`-filer utenfor repoets parallelle sannhetskilder. Den godkjente produktrekkefølgen er dokumentert i [ROADMAP.md](ROADMAP.md).
