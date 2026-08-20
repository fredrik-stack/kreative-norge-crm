# ADR-009: Public image runtime, release delivery and restore-safe deny state

## Status

Godkjent arkitekturretning. Fase 3E.1A er implementert og `ACTIVE` i staging som lokal safety-ledger, dedikert off-server Borg-anchor, separat recovery-gate og fail-closed health. Fase 3E.1B–3E.4 og all public runtime er fortsatt ikke implementert eller aktivert.

**Beslutningsdato:** 2026-08-17

**Dokumentert i repo:** 2026-08-20

ADR-et formaliserer fase 3E og supplerer [ADR-007](ADR-007-IMAGE_ASSET_ARCHITECTURE.md) og [ADR-008](ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md). Det endrer ikke de implementerte fase 3B–3D-modellene, dagens legacybildebruk eller den aktive generelle Borg-backupen.

## Kontekst

Fase 3B–3D har implementert og verifisert intern bildebehandling, immutable artifacts, Organization-selection, reviewhistorikk og en organization-typed public release-aggregate med UUIDv4 og canonical keys. Denne grunnmuren er ikke en public runtime:

- `create_organization_image_release` oppretter bare et komplett databaseaggregate og keys; tjenesten reserverer ikke permanent, kopierer ingen filer, aktiverer ingen release og skriver ingen separat journal
- `image_renditions_public` er i praksis intern artifact-storage med tenant-scopede keys og er ikke montert i web-containeren eller eksponert som public origin
- dagens orphan-cleanup kjenner bare `ImageRendition.artifact_storage_key`; `releases/...` i samme root ville bli behandlet som urefererte filer og kunne slettes etter aldersgrensen
- dagens public API har to ruteregistreringer for `/api/public/actors/`: `crm.urls_public` nås direkte fra `config.urls`, mens `crm.urls` registrerer en annen viewset og serializer under samme effektive path
- legacyaliasene kan allerede divergere fordi `preview_image_url` og `thumbnail_image_url` bruker ulike resolvere
- permanent reservation-/lifecycle-ledger og dedikert off-serverkjede er implementert og live-verifisert i staging i 3E.1A, men kontrollert serving, public projection, API-cutover, cache-/purgekontrakt og formell takedown finnes ikke

ADR-007 krever at en eldre database- eller apprestore aldri kan reaktivere en nyere denied release eller gjenbruke en tidligere release-ID/key. ADR-008s nattlige Borg-kjede har et foreløpig RPO på omtrent 24 timer pluss timerforsinkelse og bruker ikke et append-only/admin-key-regime. Den generelle backupen kan derfor ikke alene være den autoritative sikkerhetstilstanden for public image runtime.

## Beslutning

### 1. Tydelig grense mellom implementert grunnmur og planlagt runtime

Fase 3B–3D-grunnmuren forblir implementert. 3E.1A-ledger/read-model/restore/health og live off-servergate er implementert og aktivert i staging. Følgende gjenstår før de respektive senere 3E-leveransene er grønne:

- public release-materialisering og lifecycle
- kontrollert media-serving og origin-konfigurasjon
- `PublicImageProjection`, strukturert API-kontrakt og legacyalias-cutover
- PUBLIC-, canonical-, Open Graph- og Twitter-integrasjon
- formell takedown og tenant-scopet checksum-deny

Dokumentasjon, UI og operativ status skal bruke dette skillet og skal ikke omtale ADR-009 som kjørende runtime.

### 2. Autoritativ append-only sikkerhetsledger

Første MVP bruker en liten lokal SQLite-ledger for permanent reservasjon, release-livssyklus og deny-historikk. Append-only events er autoritative. Samme SQLite-fil kan inneholde en avledet read-model og kjent cursor når disse kan slettes og bygges på nytt fra eventene.

Ledgerskjemaet skal være versjonert og minst støtte idempotente event-ID-er og disse eventtypene:

- `release_reserved`
- `release_activated`
- `release_retired`
- `release_denied`
- `tenant_runtime_enrolled`, bare dersom tenantvis aktivering faktisk brukes som en sikkerhetsgrense
- senere tenant-scopet checksum-deny før formell takedown kan aktiveres

En `release_id` og alle canonical keys reserveres permanent før database- eller filmaterialisering. `release_retired` og `release_denied` er terminale for den konkrete release-ID-en: den kan aldri aktiveres igjen. Senere autorisert republisering bruker ny UUIDv4 og nye keys, også når de samme interne artifact-bytes gjenbrukes.

Journalhendelser skrives idempotent. Samme event-ID med samme canonical payload er retry; samme event-ID med forskjellig payload er hard konflikt. Tidligere eventer endres eller slettes aldri. Avledet state kan repareres bare ved replay eller en ny kompenserende hendelse.

### 3. Restore-sikkert off-server anker

Den lokale ledgeren får et restore-sikkert, append-only/WORM-orientert off-server sikkerhetsanker i et separat failure-domain. Sikkerhetskritiske reservation-, activation-, retirement- og deny-hendelser regnes ikke som varig bekreftet før den nødvendige ankeringen er synkront verifisert etter kontrakten som bevises i fase 3E.1A.

ADR-008s eksisterende Storage Box-, Borg-, systemd-, SSH-, repository-identitets- og recovery-custody-grunnmur skal gjenbrukes der den dekker behovet. Dette er ikke et løfte om absolutt WORM:

- fase 3E.1A skal bevise konkret credential- og tilgangsmodell, append-/overskrivings-/sletteadferd og recovery
- en ubegrenset eller administrativ Storage Box-credential skal ikke ligge i CRM-runtime
- admin- og recoverytilgang skal være i separat custody
- API-imaget skal ikke få Borg-klient eller administratorcredential uten at 3E.1A beviser at dette er den enkleste og sikreste plasseringen
- execution placement velges i 3E.1A mellom eksisterende host-/systemdgrunnmur og en mindre privilegert runtimekobling ut fra minst kompleksitet og minst privilegium

Det innføres ikke sidecar, Redis, ekstern database, S3/CDN eller ny infrastrukturleverandør nå.

### 4. Separat public delivery-root

Public release-bytes materialiseres i et eget host-persistent delivery-område, planlagt som:

```text
/srv/kreative-norge/media/public-delivery/
```

Det eksisterende `image_renditions_public`-/`IMAGE_RENDITIONS_ROOT`-området er fortsatt intern artifact-storage. Det skal ikke eksponeres eller brukes som delivery-root. Dermed kan ikke en generell webalias ved et uhell gjøre `tenants/.../artifacts/...` offentlig, og dagens artifact-orphan-cleanup får ikke eierskap til release-filer.

Canonical relative release keys er uendret:

```text
releases/<release_uuid>/<variant>.<ext>
```

Delivery-rooten inneholder bare materialiserte release-bytes under dette namespacet. Private originaler, artifacts, restore-/karantenefiler, ledger, audit og metadata monteres aldri i den offentlige webstien. Cleanup for artifacts og cleanup/purge for releases er separate, referansebevisste mekanismer.

### 5. Materialisering og release-livssyklus

En asset-release følger denne rekkefølgen:

1. velg og valider et komplett internt immutable rendition-sett
2. generer UUIDv4 og canonical keys
3. registrer og verifiser permanent `release_reserved`
4. opprett eller bind databaseaggregatet til den reserverte identiteten
5. kopier hver artifact create-only/no-clobber til delivery-rooten
6. les tilbake og verifiser checksum, dimensjoner og faktisk format for alle tre varianter
7. registrer og verifiser `release_activated`
8. gjør releasen valgbar for public projection og kontrollert delivery

Samme key med samme forventede bytes er en idempotent retry. Samme key med andre bytes er en hard konflikt. Delvis kopi, ukjent verifikasjon eller avbrutt workflow kan aldri bli aktiv. Feil etter reservasjon frigjør ikke UUID eller keys.

Replacement, ordinær removal-to-fallback og restore av en selection er fortsatt redaksjonelle selection-handlinger. Public lifecycle håndteres separat: gammel aktiv release pensjoneres eller denies etter riktig kommando, og en ny autorisert public release får alltid ny UUID/key. Dagens selection-restore kan ikke alene reaktivere en public release.

### 6. Kontrollert serving

Public media leveres gjennom en Django-gate som autoriserer den konkrete release-forespørselen mot journal/read-model og gjeldende Organization-state, etterfulgt av Nginx `X-Accel-Redirect` eller en dokumentert likeverdig intern filmekanisme.

Nginx-locationen for delivery-rooten skal være intern. Det finnes ingen anonym filesystem-alias eller direkte public mount som kan omgå Django-gaten. Gate betyr her autorisasjon av public release-state, ikke at sluttbrukeren må logge inn.

Serving feiler lukket til systemfallback eller kontrollert ikke-levering ved minst:

- manglende eller korrupt ledger
- stale eller ukjent journalcursor/read-model
- ukjent, denied eller retired release
- tenant-, Organization-, variant- eller key-scope mismatch
- upublisert Organization
- manglende, ufullstendig eller checksum-/formatavvikende filsett
- restore eller reconciliation som ikke er fullført

Projection og gateway skal lese samme sikkerhetstilstand. En URL som finnes i gammel HTML, API-respons eller database er ikke i seg selv autorisasjon til å hente bytes.

### 7. Autoritative origins

Eksterne URL-er bygges bare fra eksplisitte miljøsettings:

- `PUBLIC_SITE_ORIGIN`
- `PUBLIC_MEDIA_ORIGIN`

Origins valideres og allowlistes ved oppstart. `Host`, `X-Forwarded-Host`, intern filesystempath eller providerendpoint kan ikke bestemme canonical eller media-URL. Samme origin kan brukes for begge settings, men kontraktene forblir separate.

Ingen konkret staging- eller produksjonshost omtales som verifisert før faktisk miljøkonfigurasjon er kontrollert.

### 8. Én read-only `PublicImageProjection`

`PublicImageProjection` blir eneste bildekontrakt for public API, PUBLIC HTML, head metadata og senere Editor-shadow/preview. Den er en read-only resolver/DTO, ikke en ny sannhetskilde.

Projection skal:

- motta en allerede scoppet Organization og kontrollere etablert publiseringsstatus
- returnere én aktiv, autorisert og komplett release eller systemfallback
- bruke samme ledger/read-model som serving-gaten
- returnere bare `kind`, offentlig alttekst, eventuell offentlig kreditering og de tre kontrollerte variantene
- aldri gjøre HTTP-/DNS-oppslag, fetch, dekoding, rendering eller filmaterialisering under lesing
- aldri eksponere private originaler, artifact keys, kilde, proveniens, review, audit, intern tenantidentitet eller karanteneinformasjon

Upubliserte Organizations får ingen asset-URL eller delingsmetadata. Manglende sikkerhetstilstand gir fallback, aldri legacybilde.

### 9. Public API-kontrakt og kanonisk rute

Det strukturerte public-feltet heter `image` og har denne kontrakten:

```json
{
  "kind": "asset",
  "alt_text": "",
  "credit": null,
  "square": {"url": "https://…", "width": 512, "height": 512},
  "landscape": {"url": "https://…", "width": 800, "height": 450},
  "share": {"url": "https://…", "width": 1200, "height": 630}
}
```

`kind` er nøyaktig `asset` eller `system_fallback`. `alt_text` bevarer godkjent tom streng for assets. `credit` er null eller offentlig kreditering. Hver variant har absolutt URL, bredde og høyde.

`thumbnail_image_url` og `preview_image_url` beholdes som deprecated kompatibilitetsaliaser. Etter cutover kommer begge fra samme `PublicImageProjection` og peker til `image.square.url`; de kan ikke divergere.

Dagens doble registrering av `/api/public/actors/` og ulike serializers er et verifisert avvik. Ingen ruterefactor inngår i denne dokumentleveransen. Før `image`-schemaet aktiveres i fase 3E.2 skal én kanonisk public route/viewset/serializer være valgt og kontrakttestet; den andre registreringen skal fjernes eller gjøres entydig ikke-aktiv.

### 10. Statisk og versjonert systemfallback

Systemfallback finnes som statiske, versjonerte `square`-, `landscape`- og `share`-varianter og kan leveres uten ledger eller public delivery-root. Dermed finnes en sikker respons også mens journal, restore eller materialisering feiler.

Fallback er ikke en aktiv asset-release og skal ikke representeres som en slik i cache, ledger eller API. Endelig grafisk innhold og endelig fallback-alttekst avgjøres i PUBLIC-implementeringen; ADR-et fastsetter ikke disse detaljene.

### 11. Cache- og takedownprinsipper

Aktive releases kan caches kontrollert, men konkret TTL, `Cache-Control` og eventuell bruk av `immutable` avgjøres og bevises i fase 3E.1C og 3E.4. Dette ADR-et fastsetter ikke `public,max-age=3600,immutable` eller en annen fast verdi.

Sikkerhetsfallback skal ikke kunne bli liggende som en feilaktig aktiv release når sikkerhetstilstanden igjen er kjent. Formell takedown er ikke fullført før relevant origin-tilgang er blokkert eller slettet og nødvendig cache expiry/purge/retry/verifikasjon er registrert.

Deny-first betyr at `release_denied` er skrevet lokalt og synkront verifisert i off-serverankeret før den normale projection/gateway-overgangen og før origin-delete eller blokkering. Dersom ankeringen feiler, går runtime fail-closed til sikker fallback eller ingen levering, men takedown markeres ikke komplett.

Formell takedown forblir deaktivert frem til fase 3E.4. Fasen skal minst bevise:

- deny av konkret release
- tenant-scopet checksum-deny før samme bytes kan godkjennes på nytt i samme tenant
- kompatibel legacyguard
- identisk state i projection og serving-gateway
- origin-delete eller blokkering
- cache expiry/purge og verifikasjon
- at eldre database-/apprestore ikke kan reaktivere releasen
- at senere autorisert republisering bruker ny UUID og nye keys

Global checksum-deny innføres ikke uten et senere konkret behov og egen beslutning.

## Trusselmodell

Arkitekturen beskytter eksplisitt mot:

- restore av eldre PostgreSQL-, app- eller media-state etter nyere reservasjon, retirement eller deny
- stille gjenbruk av release-ID/key etter avbrutt workflow eller database-RPO-gap
- direkte levering av denied/retired release fordi en gammel URL fortsatt er kjent
- delvis eller korrupt materialisering som feilaktig blir aktiv
- overskriving av eksisterende key med andre bytes
- utilsiktet eksponering av private originaler eller interne artifacts gjennom generell webalias
- utilsiktet sletting av materialiserte releases gjennom dagens artifact-orphan-cleanup
- divergent sikkerhetsbeslutning mellom projection, API/HTML og byte-serving

Nyere autoritativ ledgerstate skal alltid vinne over eldre database-, app-, fil- og backupstate. Når journalintegritet, cursor eller reconciliation ikke kan bevises, er korrekt respons fail-closed fallback eller ingen levering.

Storage Box gir et separat failure-domain innen samme leverandør, ikke en flerleverandørgaranti. ADR-et lover ikke beskyttelse mot kompromittert Hetzner control plane, kompromittert host-root eller en administrator som kontrollerer både runtime- og recoverycredentials, med mindre 3E.1A senere beviser en konkret egenskap. «WORM-orientert» betyr et mål for tilgang og append-adferd, ikke absolutt uforanderlighet.

## Alternativer som er vurdert

### Bare PostgreSQL som journal

Avvist. En eldre databaserestore kan miste nyere reservations-/deny-hendelser og dermed bryte no-reuse og deny-first.

### Bare nattlig ADR-008-Borg

Avvist som sikkerhetsjournal. Dagens RPO og credentialmodell er riktig for generell katastrofebackup, men kan ikke alene bevise at en nyere deny overlever en eldre restore. Grunnmuren gjenbrukes for et særskilt sikkerhetsanker.

### JSONL som autoritativ runtimejournal

Avvist for produksjon. Fase 3B.2s JSONL beviste replaydomene, men ikke transaksjonell idempotens, concurrent writers, schemaevolusjon eller robust read-model/cursor.

### Direkte anonym Nginx-alias til artifact-root

Avvist. Det ville omgå deny-/publiseringsgaten og kunne eksponere interne `tenants/.../artifacts/...`.

### Materialiserte releases i dagens artifact-root

Avvist. Namespace og cleanup-eierskap ville kollidere, og en generell mount ville blande intern og offentlig sikkerhetsflate.

### Selection-revisjon, database-PK eller artifact-hash som public identity

Avvist av ADR-007. De gir ikke restore-sikker no-reuse-kontrakt og kan eksponere intern identitet eller like bytes på tvers av tenants.

### Redis, ekstern database, sidecar eller objektlagring nå

Utsatt. De løser ingen nødvendig MVP-garanti bedre enn lokal SQLite, separat delivery-root og gjenbruk av eksisterende host-/Storage Box-grunnmur på dette stadiet.

### Fast cache-TTL eller `immutable` i ADR-et

Utsatt. Riktig verdi avhenger av målt serving-, purge- og takedownadferd og skal fastsettes med evidens.

## Begrunnelse

SQLite gir en liten, transaksjonell og operasjonelt forståelig journal uten en ny nettverkstjeneste. Det separate off-server ankeret lukker restore-gapet som den vanlige database-/Borg-RPO-en ikke kan lukke alene. Et separat delivery-root og en kontrollert gateway gjør deny til en runtimeavgjørelse i stedet for å stole på at en gammel URL eller fil er borte.

Trinnvis innføring holder risikoen avgrenset: journal og restorebevis kommer før bytes, materialisering før serving, shadow-projection før API/PUBLIC-cutover og full deny-/cacheevidens før takedown aktiveres.

## Konsekvenser

### Positive

- en eldre restore kan ikke vinne over nyere deny/no-reuse-state
- public og intern storage får entydig sikkerhets- og cleanup-eierskap
- keys og bytes materialiseres idempotent uten stille overskriving
- projection og byte-serving tar samme autorisasjonsbeslutning
- API, HTML og head får én konsistent bildekontrakt
- MVP-en gjenbruker etablert Hetzner-/systemd-/Borggrunnmur uten ny driftstjeneste

### Kostnader og begrensninger

- hvert public lifecycle-steg krever journal-, anchor-, DB-, fil- og reconciliationlogikk
- aktivering kan feile lukket ved journal-/anchorfeil selv om filene finnes
- SQLite trenger eksplisitt writer-, locking-, fsync-, backup- og corruptionkontrakt
- kontrollert serving gir et Django-gatekall før Nginx leverer bytes
- cache og takedown krever målbar operativ verifikasjon
- samme leverandør gir ikke uavhengighet fra alle Hetzner- eller root-scenarier

## Fail-closed og rollback

- Featuregater for journal, materialisering, serving, projection og cutover holdes separate.
- Ukjent sikkerhetstilstand gir statisk fallback eller ingen levering; systemet faller aldri tilbake til et kjent denied legacybilde.
- En avbrutt eller deaktivert release-workflow beholder permanente reservations- og lifecycle-events.
- Rollback sletter eller omskriver aldri ledger, release-ID-er, keys, deny-historikk eller reviewhistorikk.
- Delvis materialiserte filer forblir inaktive og kan verifiseres/retries eller ryddes med en release-aware prosedyre.
- API/PUBLIC-cutover kan slås av, men projection-/gateway-deny må fortsatt beskytte kjente denied releases og legacyguard.
- Etter første reelle reservation eller deny er schema-/operativ rollback fremoverrettet; gamle sikkerhetsevents migreres eller replayes, ikke fjernes.

## Implementeringsetapper og akseptansekriterier

### Fase 3E.1A – journal, restore-gate og off-server anker

**Implementasjonsstatus 2026-08-20:** Repoimplementasjonen og den eksterne staginggaten er levert. Ledgeren ligger i `/var/lib/kreative-norge-image-safety/ledger.sqlite3`, kjører host-side uten safety-mount i API/web og bruker et dedikert append-only Borg-repository med stabil Borg `>=1.2.8,<1.3.0` og synkron create/read-back før lokal receipt. Safety- og ADR-008-repository-ID er verifisert forskjellige; separat custody for minst to ansvarlige, delete-/compact-/raw-`rm`-capability, separat transaction recovery av probe og nyeste DENIED-head, stale incident-restore-avvisning, rebuild/health og host-restart er live-verifisert. Raw filtilgang gjør løsningen WORM-orientert, ikke absolutt WORM; prosjekteier har akseptert restrisikoen. 3E.1A er `ACTIVE` i staging, men dette aktiverer ingen public runtime. Se [runbook](../operations/PUBLIC_IMAGE_SAFETY_LEDGER.md), [aktiveringsrapport](../status/STAGING_PHASE_3E1A_ACTIVATION_2026-08-20.md) og [historisk stagingforberedelse](../status/STAGING_PHASE_3E1A_PREPARATION_2026-08-17.md).

**Omfang:**

- versjonert lokal SQLite-ledger med idempotente append-only events
- rebuildbar read-model/cursor
- synkront verifisert off-server sikkerhetsanker i separat failure-domain
- konkret execution placement og minst-privilegert credential-/recoverymodell
- restore-/replay-/reconciliationkommando og fail-closed health gate

**Akseptansekriterier:**

- samme event-ID/samme payload er idempotent, mens samme ID/annen payload og ugyldig overgang feiler lukket
- retired/denied release kan ikke aktiveres; gammel database + nyere journal kan ikke regenerere eller reaktivere keyen
- manglende, korrupt, stale eller ukjent ledger/cursor blokkerer runtime
- incident/unknown restore kan ikke bruke current manifest alene; separat append-only recovery må identifisere autoritativ cursor/head før restore kan skrive receipt og bli `READY`
- avledet state kan bygges fra eventene med samme resultat
- ubegrenset/admin Storage Box-credential finnes ikke i CRM-runtime, og recoverytilgang har separat custody
- append-, overwrite-, delete-, restore- og credentialadferd er dokumentert med faktisk evidens uten absolutt WORM-påstand
- API-imaget får ikke Borg eller utvidede credentials uten eksplisitt evidens for at plasseringen er enklest og sikrest

**Testkrav:** unit-/concurrencytester for ledger, crash/retry, corruption, replay, eldre DB/apprestore, credential-/permissionstest og isolert recoveryøvelse.

**Rollback:** runtime forblir av; ledger og ankret historikk beholdes.

### Fase 3E.1B – materialisering og release-livssyklus

**Omfang:**

- eget `public-delivery`-storagealias/root
- reservation før database-/filmaterialisering
- create-only/no-clobber kopiering og read-back-verifikasjon
- release-aware cleanup/purge og lifecycleevents

**Akseptansekriterier:**

- artifact-root og delivery-root kan ikke overlappe, og ingen public mount når artifacts/private filer
- cleanup-kollisjonen er løst før første `releases/...`-fil skrives
- komplett square/landscape/share verifiseres på checksum, dimensjon og format før activation
- samme key/samme bytes retries; samme key/andre bytes feiler hardt; delvis release er aldri aktiv
- retirement/deny er terminalt for release-ID; republisering får ny UUID/key

**Testkrav:** storage-/filesystempermissionstester, partial/crash/retry, no-clobber, checksum-/formatavvik, concurrent reservation og cleanup-race.

**Rollback:** materialisering deaktiveres; inaktive filer kan ryddes kontrollert, mens reservations-/lifecyclehistorikk beholdes.

### Fase 3E.1C – kontrollert serving og origins

**Omfang:**

- Django release-gate og intern Nginx `X-Accel-Redirect` eller dokumentert likeverdig mekanisme
- eksplisitte `PUBLIC_SITE_ORIGIN`/`PUBLIC_MEDIA_ORIGIN`
- cache-, expiry-, purge- og observabilitykontrakt for vanlig serving

**Akseptansekriterier:**

- ingen direkte anonym alias/mount kan nå delivery-root, artifact-root eller private filer
- gateway avviser ukjent/denied/retired/scope-feil/upublisert/manglende/korrupt release og ukjent cursor
- vilkårlig `Host`/`X-Forwarded-Host` kan ikke endre public URL
- valgt cachepolicy er målt og dokumentert; fallback kan ikke bli stående som feilaktig aktiv release
- delivery kan holdes av bak featuregate uten å endre legacy PUBLIC

**Testkrav:** route-/path traversal-/scope-/publicationtester, host-header-invarians, stale cursor, corrupt/missing file, cache expiry/purge og intern-location-verifikasjon.

**Rollback:** servingflagget av; statisk fallback forblir tilgjengelig, og denied releases forblir blokkert.

### Fase 3E.2 – projection og public API shadow

**Omfang:**

- read-only `PublicImageProjection`
- strukturert `image`-objekt og deprecated aliaser i shadow/feature-flag-modus
- opprydding til én kanonisk `/api/public/actors/`-route/viewset/serializer

**Akseptansekriterier:**

- projection gjør ingen HTTP-, DNS-, decode-, render- eller storage-writekall
- API returnerer bare `asset` eller `system_fallback` og eksponerer ingen intern metadata
- `thumbnail_image_url`, `preview_image_url` og `image.square.url` kommer fra samme projection og kan ikke divergere
- én faktisk aktiv public rute og serializer er kontrakttestet før schemaaktivering
- upublisert Organization og ukjent sikkerhetstilstand lekker ikke asset-URL

**Testkrav:** serializer-/OpenAPI-/route-resolutionstester, shadow-diff, query-/I/O-asserts, tenant-/publication-/denytester og absolutte URL-er.

**Rollback:** nytt schema/cutover av; gateway-deny og permanent ledger beholdes.

### Fase 3E.3 – PUBLIC, canonical, delingsmetadata og cutover

**Omfang:**

- PUBLIC HTML og kort fra projection
- canonical, Open Graph og Twitter Card
- kontrollert tenant-/feature-flag-cutover
- endelig grafisk fallback og fallback-alttekst

**Akseptansekriterier:**

- PUBLIC, API og head bruker samme autoriserte release/fallback
- `og:image` og Twitter bruker komplett 1200 × 630-sharevariant
- canonical og media-URL følger settings, ikke request-host
- ingen legacy, intern metadata eller upublisert bilde lekker etter cutover
- fallback fungerer uavhengig av ledger og delivery-root

**Testkrav:** PUBLIC/head-kontrakt, host-header-invarians, shadow/cutover/rollback, desktop-/mobilvisning og ødelagt runtime.

**Rollback:** tenant/cutoverflagget av; systemfallback brukes når legacy ikke kan brukes sikkert.

### Fase 3E.4 – formell takedown

**Omfang:**

- rolleavgrenset deny-first takedown
- konkret release-deny og tenant-scopet checksum-deny
- legacyguard, origin-delete/blokkering, cache expiry/purge/retry/verifikasjon
- sikker republisering med ny UUID/key

**Akseptansekriterier:**

- én takedown gir fallback i legacyguard, projection, gateway, API, PUBLIC og head
- kjent gammel URL leverer ikke denied bytes
- eldre database/app/mediarestore kan ikke reaktivere releasen
- samme checksum kan ikke godkjennes stille i samme tenant, men påvirker eller avslører ikke annen tenant
- takedown er ikke komplett før origin- og cachetilstand er verifisert
- autorisert republisering bruker ny UUID/key og kan ikke oppheve gammel deny

**Testkrav:** end-to-end deny-first, partial failure/retry, legacy bypass, tenantisolasjon, cache/purge, eldre restore og republisering.

**Rollback:** takedownfunksjonen kan deaktiveres, men eksisterende deny og legacyguard kan aldri rulles tilbake eller omgås.

## Åpne implementasjonsdetaljer

Følgende avgjøres med evidens i riktig leveranse uten å åpne hovedretningen på nytt:

- eksakt SQLite-path, tabell-/payloadschema, writerprosess, locking, fsync og corruptiondeteksjon
- eksakt off-server ankermekanisme, append-/snapshotformat og execution placement
- konkret subaccount-/nøkkel-/admin-/recoveryoppsett som faktisk kan bevises på Storage Box
- eksakt intern URL/path for `X-Accel-Redirect`
- cache-TTL, `Cache-Control`, eventuell `immutable`, lokal cacheplassering, purgekommando og verifikasjonsfrist
- endelig grafisk fallbackinnhold og fallback-alttekst
- konkret tenant-enrollmentbehov og eventpayload dersom tenantvis cutover brukes
- observability, alarmer og operatør-runbooks
- retensjon for inaktive, ufullstendige materialiseringer og derived read-model-backups

Disse detaljene kan ikke svekke permanent no-reuse, deny-over-restore, separat delivery-root, controlled serving, én projection eller kravet om ny UUID/key ved republisering.
