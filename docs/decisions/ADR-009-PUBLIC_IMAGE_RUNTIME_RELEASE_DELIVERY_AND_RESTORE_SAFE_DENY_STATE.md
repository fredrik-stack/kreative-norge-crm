# ADR-009: Public image runtime, release delivery and restore-safe deny state

## Status

Godkjent arkitekturretning. Fase 3E.1A er implementert og `ACTIVE` i staging som lokal safety-ledger, dedikert off-server Borg-anchor, separat recovery-gate og fail-closed health. Fase 3E.1B.1–3E.1B.2-materialisering er `ACTIVE` etter syntetisk ankret reserve/activate-, crash/restart/retry- og no-clobber-gate. Fase 3E.1C-controlled serving er `CLOSED / ACTIVE` i staging etter separat HTTP-, fail-closed-, restart-, observability- og backup/restore-gate. Staging har én upublisert 3E.1B-evidensrelease og én publisert release. Fase 3E.2 er `CLOSED / SHADOW VERIFIED`, og fase 3E.3 target-API/PUBLIC/head er `CLOSED / ACTIVE` etter separat aktiverings-, rollback-, browser- og ytelsesgate. Fase 3E.4 er implementert bak en default-off skrivegate; ledger-v2-upgrade, permanent stagingdeny og aktivering er ikke gjennomført ennå.

**Beslutningsdato:** 2026-08-17

**Dokumentert i repo:** 2026-08-20

**3E.1B-presisering godkjent:** 2026-08-20

**3E.1C read-only-presisering godkjent:** 2026-08-23

**3E.1C stagingaktivert:** 2026-08-24

**3E.2 shadowverifisert:** 2026-08-24

**3E.3 implementert bak default-off gater:** 2026-08-24

**3E.3 stagingaktivert:** 2026-08-24

**3E.4 implementert bak default-off skrivegate:** 2026-08-24

ADR-et formaliserer fase 3E og supplerer [ADR-007](ADR-007-IMAGE_ASSET_ARCHITECTURE.md) og [ADR-008](ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md). Det endrer ikke de implementerte fase 3B–3D-modellene, dagens legacybildebruk eller den aktive generelle Borg-backupen.

## Kontekst

Fase 3B–3D har implementert og verifisert intern bildebehandling, immutable artifacts, Organization-selection, reviewhistorikk og en organization-typed public release-aggregate med UUIDv4 og canonical keys. Denne grunnmuren er ikke en public runtime:

- `create_organization_image_release` er etter 3E.1B den ene støttede, feature-gated workflowen for snapshot, ankret reservasjon, immutable DB-binding, create-only materialisering, read-back og ankret activation; den er ikke koblet til en aktiv API-/Editor- eller stagingflyt
- `image_renditions_public` er i praksis intern artifact-storage med tenant-scopede keys og er ikke montert i web-containeren eller eksponert som public origin
- dagens orphan-cleanup kjenner bare `ImageRendition.artifact_storage_key`; `releases/...` i samme root ville bli behandlet som urefererte filer og kunne slettes etter aldersgrensen
- dagens public API hadde før 3E.2 to ruteregistreringer for `/api/public/actors/`; 3E.2 har beholdt `crm.urls_public` som én canonical route og fjernet den shadowed viewset-/serializerkjeden
- legacyaliasene kan allerede divergere fordi `preview_image_url` og `thumbnail_image_url` bruker ulike resolvere
- permanent reservation-/lifecycle-ledger og dedikert off-serverkjede er implementert og live-verifisert i 3E.1A; kontrollert serving og en privat revalidationpolicy er aktivert i 3E.1C; projection-shadow er liveverifisert i 3E.2; API/PUBLIC/head-cutover er stagingaktivert i 3E.3; formell deny-first takedown er implementert default-off i 3E.4, men stagingledgeren er fortsatt v1 og write-gaten er fortsatt av frem til separat aktivering

ADR-007 krever at en eldre database- eller apprestore aldri kan reaktivere en nyere denied release eller gjenbruke en tidligere release-ID/key. ADR-008s nattlige Borg-kjede har et foreløpig RPO på omtrent 24 timer pluss timerforsinkelse og bruker ikke et append-only/admin-key-regime. Den generelle backupen kan derfor ikke alene være den autoritative sikkerhetstilstanden for public image runtime.

## Beslutning

### 1. Tydelig grense mellom implementert grunnmur og planlagt runtime

Fase 3B–3D-grunnmuren forblir implementert. 3E.1A-ledger/read-model/restore/health og live off-servergate, 3E.1B-materialisering/release-livssyklus for reserve/activate, 3E.1C kontrollert serving/origins, 3E.2 projection-shadow og 3E.3 target-API/PUBLIC/head er implementert og aktivert/verifisert i staging. Følgende gjenstår:

- separat stagingupgrade til ledger schema v2, aktivering av 3E.4-skrivegaten og permanent syntetisk deny-/restore-/republish-evidens

Dokumentasjon, UI og operativ status skal bruke dette skillet: den samlede public image runtime-reisen er aktiv i staging, mens formell takedown er implementert men fortsatt deaktivert i staging frem til den separate irreversible gaten.

### 2. Autoritativ append-only sikkerhetsledger

Første MVP bruker en liten lokal SQLite-ledger for permanent reservasjon, release-livssyklus og deny-historikk. Append-only events er autoritative. Samme SQLite-fil kan inneholde en avledet read-model og kjent cursor når disse kan slettes og bygges på nytt fra eventene.

Ledgerskjemaet skal være versjonert og minst støtte idempotente event-ID-er og disse eventtypene:

- `release_reserved`
- `release_activated`
- `release_retired`
- `release_denied`
- `tenant_runtime_enrolled`, bare dersom tenantvis aktivering faktisk brukes som en sikkerhetsgrense
- senere tenant-scopet checksum-deny før formell takedown kan aktiveres

#### Lokal 3E.1B-bro og privilegieseparasjon

Django skal i 3E.1B bruke en lokal Unix-socket/systemd-bro til den host-eide safety-ledger-runtimeen. Socketen er en privilegieseparasjonsgrense, ikke en generell RPC-plattform: Django kan be om et lite, eksplisitt sett safety-operasjoner, mens hostprosessen alene eier ledgerpath, Borg-klient, writer-key, passfrase og ankerruntime.

Den autoriserte mutation-/lifecycle-flaten er avgrenset til `reserve`, `activate`, `retire` og `deny`. Denne grensen krever ikke at alle fire operasjoner leveres i første kodeleveranse. Fase 3E.1C legger i tillegg til nøyaktig én smal read-only `authorize`-operasjon for serving. Den kan bare svare på om én eksakt release-/variantforespørsel matcher autoritativ reservation og gjeldende lifecycle-state. Den kan ikke skrive ledger eller receipt, ankre, kjøre Borg, velge release-ID/key, reparere stale state eller hente vilkårlig event-/ledgerhistorikk. Den er dermed ikke en utvidelse av mutation-/lifecycle-flaten eller en generell query-API.

Socketen skal være lokal, fail-closed og autorisert gjennom OS-/runtime-isolasjon med minst mulige bruker-, gruppe-, fil- og systemd-rettigheter. Ukjent operasjon, ugyldig payload, feil peer, timeout, manglende health eller uverifisert anker skal avvises. Det innføres ikke offentlig eller nettverkseksponert HTTP-tjeneste, Redis, meldingskø, ny applikasjonscontainer, direkte Borg-tilgang fra Django eller direkte safety-ledger-mount i API/web.

En `release_id` og alle canonical keys reserveres permanent før database- eller filmaterialisering. `release_retired` og `release_denied` er terminale for den konkrete release-ID-en: den kan aldri aktiveres igjen. Senere autorisert republisering bruker ny UUIDv4 og nye keys, også når de samme interne artifact-bytes gjenbrukes.

Journalhendelser skrives idempotent. Samme event-ID med samme canonical payload er retry; samme event-ID med forskjellig payload er hard konflikt. Tidligere eventer endres eller slettes aldri. Avledet state kan repareres bare ved replay eller en ny kompenserende hendelse.

### 3. Restore-sikkert off-server anker

Den lokale ledgeren har et restore-sikkert, append-only/WORM-orientert off-server sikkerhetsanker i et separat failure-domain. Sikkerhetskritiske reservation-, activation-, retirement- og deny-hendelser regnes ikke som varig bekreftet før den nødvendige ankeringen er synkront verifisert etter kontrakten som ble bevist og aktivert i fase 3E.1A.

ADR-008s eksisterende Storage Box-, Borg-, systemd-, SSH-, repository-identitets- og recovery-custody-grunnmur skal gjenbrukes der den dekker behovet. Dette er ikke et løfte om absolutt WORM:

- fase 3E.1A har bevist konkret credential- og tilgangsmodell, append-/overskrivings-/sletteadferd og recovery
- en ubegrenset eller administrativ Storage Box-credential skal ikke ligge i CRM-runtime
- admin- og recoverytilgang skal være i separat custody
- API-imaget har ingen Borg-klient, safety-ledger-mount, writersecret eller administratorcredential
- host/systemd er valgt execution placement for ledger, Borg-klient og ankerruntime; Djangos senere lokale Unix-socket-bro endrer ikke dette eierskapet

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

3E.1B innfører ingen automatisk sletting av public release-filer. Delivery-rooten er ikke lagt inn i dagens generiske orphan-cleanup for private originaler og interne artifacts. Eventuell senere release-cleanup må være release-aware og safety-ledger-aware og krever egen avgrensning. `retired` og `denied` er terminale safety-tilstander, men betyr ikke automatisk filsletting i 3E.1B. Formell `deny → origin delete → cache purge` tilhører fortsatt 3E.4.

### 5. Materialisering og release-livssyklus

En asset-release følger denne rekkefølgen:

1. velg og valider et komplett internt immutable rendition-sett
2. slå opp den autoritative selection-revisjonens reservation; gjenbruk den dersom den finnes, ellers generer UUIDv4 og canonical keys internt
3. registrer og verifiser permanent `release_reserved`
4. opprett eller bind databaseaggregatet til den reserverte identiteten
5. kopier hver artifact create-only/no-clobber til delivery-rooten
6. les tilbake og verifiser checksum, dimensjoner og faktisk format for alle tre varianter
7. registrer og verifiser `release_activated`
8. gjør releasen valgbar for public projection og kontrollert delivery

MVP-kontrakten tillater maksimalt én public release per godkjent selection-revisjon. Den canonical idempotency-identiteten er tupleen `(tenant_id, organization_id, selection_id, selection_revision)`, serialisert av den betrodde workflowen som `release-reservation:v1:<tenant_id>:<organization_id>:<selection_id>:<selection_revision>`. Dette er en intern workflow-/eventidentitet, ikke public release identity og ikke en del av public key. Django-/API-/Editor-callere kan ikke levere eller overstyre denne event-ID-en, release UUID-en, canonical public keys eller variant-keys. Ved retry slår broen opp denne identiteten og gjenbruker den permanent reserverte UUID-en og de samme builder-genererte keyene. Samme identitet med avvikende tenant-, Organization-, selection-, revisjons-, rendition-sett-, artifact key- eller checksum-payload er en hard konflikt; den kan aldri skape en ny reservation.

Samme key med samme forventede bytes er en idempotent retry. Samme key med andre bytes er en hard konflikt. Delvis kopi, ukjent verifikasjon eller avbrutt workflow kan aldri bli aktiv. Feil etter reservasjon frigjør ikke UUID eller keys.

Replacement, ordinær removal-to-fallback og restore av en selection er fortsatt redaksjonelle selection-handlinger. Replacement eller restore som senere skal publiseres, må gå via en ny selection-revisjon og få ny reservation, UUID og nye immutable keys. Samme selection-revisjon kan ikke brukes til bevisst å opprette enda en public release. Public lifecycle håndteres separat: gammel aktiv release pensjoneres eller denies etter riktig kommando, og dagens selection-restore kan ikke alene reaktivere en public release.

Safety-ledgeren er fortsatt autoritativ for `reserved`, `active`, `retired` og `denied`. PostgreSQL beholder det immutable `OrganizationImageRelease`-aggregatet, selection-bindingen og snapshots av artifact-/public-release-data; det finnes ingen parallell mutable lifecycle-status. Migrasjon `0029` krever tom release-tabell, legger til immutable `selection_revision_snapshot`, positiv check og unik constraint direkte på `selection`, og avbryter uten backfill eller historikkreparasjon dersom legacyreleases finnes. Den atomiske ledgerprimitiven `reserve_or_get` eier UUID/key-valget under SQLite writer-lock. To kall for samme canonical selection-revisjon gjenbruker derfor samme reservation, UUID, tre keys og DB-aggregate; endret payload er hard konflikt.

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

Den doble registreringen av `/api/public/actors/` og ulike serializers var et verifisert avvik da ADR-en ble vedtatt. Fase 3E.2 har valgt og kontrakttestet én kanonisk public route/viewset/serializer og fjernet den shadowed registreringen. `image`-schemaet er implementert og aktivert i staging etter 3E.3-cutovergaten; kode-/eksempelstandarden er fortsatt avslått.

### 10. Statisk og versjonert systemfallback

Systemfallback finnes som statiske, versjonerte `square`-, `landscape`- og `share`-varianter og kan leveres uten ledger eller public delivery-root. Dermed finnes en sikker respons også mens journal, restore eller materialisering feiler.

Fallback er ikke en aktiv asset-release og skal ikke representeres som en slik i cache, ledger eller API. Fase 3E.3 fastsetter production fallback v1 ved å gjenbruke de eksisterende, visuelt kontrollerte 3B.1-PNG-bytene eksakt på canonical `fallback-square.png`, `fallback-landscape.png` og `fallback-share.png` under den versjonerte static-roten. Gamle `emergency-fallback-*` beholdes for rollback/historikk. Systemfallback har `alt_text=""` fordi den er generisk/dekorativ og aktørnavnet allerede er synlig.

### 11. Cache- og takedownprinsipper

Fase 3E.1C har målt og valgt den foreløpige policyen `private, max-age=60, must-revalidate`, checksum-`ETag`, reautorisert `304`, `no-store` på feil, ingen shared proxycache og ingen `immutable`. Den private revalidationpolicyen er tilstrekkelig for kontrollert 3E.3-PUBLIC-cutover. Fase 3E.4 avgjør og beviser endelig cache expiry, purge og takedown-verifikasjon før formell takedown aktiveres.

Sikkerhetsfallback skal ikke kunne bli liggende som en feilaktig aktiv release når sikkerhetstilstanden igjen er kjent. Formell takedown er ikke fullført før relevant origin-tilgang er blokkert eller slettet og nødvendig cache expiry/purge/retry/verifikasjon er registrert.

Deny-first betyr at `release_denied` er skrevet lokalt og synkront verifisert i off-serverankeret før den normale projection/gateway-overgangen og før origin-delete eller blokkering. Dersom ankeringen feiler, går runtime fail-closed til sikker fallback eller ingen levering, men takedown markeres ikke komplett.

Formell takedown er implementert bak `PUBLIC_IMAGE_TAKEDOWN_ENABLED=False`; staginggaten skal minst bevise:

- deny av konkret release
- tenant-scopet checksum-deny før samme bytes kan godkjennes på nytt i samme tenant
- kompatibel legacyguard
- identisk state i projection og serving-gateway
- origin-delete eller blokkering
- cache expiry/purge og verifikasjon
- at eldre database-/apprestore ikke kan reaktivere releasen
- at senere autorisert republisering bruker ny UUID og nye keys

Global checksum-deny innføres ikke uten et senere konkret behov og egen beslutning.

### 12. Avgrensning for 3E.1B-presiseringen

**Besluttet nå:** lokal Unix-socket/systemd-bro med operasjonsgrensen `reserve`/`activate`/`retire`/`deny`; én reservation/public release per selection-revisjon; retry gjenbruker samme UUID/keys; safety-ledgeren eier lifecycle-state; public release-filer slettes ikke automatisk.

**Materialisering ACTIVE i staging:** minimal AF_UNIX/systemd-bro med bare `reserve` og `activate`, atomisk reservation, idempotent DB-binding, separat `public_image_delivery`-alias/root, create-only/no-clobber, full read-back-verifikasjon og idempotent activation. Compose-, systemd-, socket-/peer-, mount-, delivery-persistence- og backup-/restorekontraktene er liveverifisert. Den faktiske workflowen er bevist med syntetisk ankret reservation, DB-binding, kontrollert krasj etter første fil, API-restart, idempotent completion/activation, full retry uten writes og ephemeral hard konflikt for samme key med andre bytes. Serving ble aktivert senere som separat 3E.1C-gate.

**Utenfor 3E.1B:** Nginx-serving, `X-Accel-Redirect`, offentlig HTTP-serving av `releases/...`, `PUBLIC_MEDIA_ORIGIN` og cachepolicy ble levert separat i 3E.1C. Public API-schema, `PublicImageProjection`, PUBLIC HTML/UI, Editor-endringer, CDN, takedown/cache purge og fase 3E.2–3E.4 er fortsatt utenfor 3E.1B.

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

Storage Box gir et separat failure-domain innen samme leverandør, ikke en flerleverandørgaranti. ADR-et lover ikke beskyttelse mot kompromittert Hetzner control plane, kompromittert host-root eller en administrator som kontrollerer både runtime- og recoverycredentials, utover egenskapene som er eksplisitt bevist i fase 3E.1A. «WORM-orientert» betyr et mål for tilgang og append-adferd, ikke absolutt uforanderlighet.

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

#### 3E.1B.1 – privilegieseparert reservasjon og DB-binding

**Omfang:**

- lokal Unix-socket/systemd-bro uten ledger-/Borg-mount eller credentials i API/web
- fail-closed `reserve`-kall gjennom canonical selection-revisjonsidentitet
- oppslag/gjenbruk av permanent UUID/key-reservation før DB-binding
- binding av det immutable PostgreSQL-aggregatet til eksakt reservation, uten parallell lifecycle-status

**Akseptansekriterier:**

- Django kan bare nå den godkjente lokale operasjonsflaten; socketen er ikke nettverkseksponert, og feil OS-identitet/rettighet/operasjon/payload/health/anchor avvises
- samme selection-revisjon under retry eller concurrency gir samme reservation, release UUID og keys; avvikende payload feiler hardt
- caller kan ikke bestemme event-ID, release UUID, canonical key eller variant-key
- DB-aggregatet matcher eksakt reservation og er enten komplett bundet eller fraværende; crash mellom reservation og DB-commit kan retries uten ny UUID
- safety-ledgeren forblir autoritativ for lifecycle, og leveransen innfører ingen mutable lifecycle-kopi i PostgreSQL
- ingen public release-fil, Nginx-route, public API-, PUBLIC- eller stagingaktivering inngår

**Testkrav:** socket-/peer-/permission-/timeout-/schema-/unknown-operationtester; concurrent reservation og samme/different-payload-retry; DB-feil/crash etter reservation; eldre DB mot nyere ledger; eksplisitt kontroll av fraværende ledger-/Borg-credentials og mounts i API/web.

**Rollback:** reservation-/DB-bindingsworkflowen deaktiveres; socketen kan stoppes, men eventer, UUID-er og keys som allerede er permanent reservert beholdes.

#### 3E.1B.2 – public-delivery og verifisert materialisering

**Omfang:**

- eget `public-delivery`-storagealias/root
- create-only/no-clobber kopiering og read-back-verifikasjon
- activation først etter komplett verifisering
- release-aware cleanupkontrakt uten automatisk sletting; terminal retirement/deny uten 3E.4-purge
- eksplisitt backup-/restore-verifikasjon før stagingaktivering

**Akseptansekriterier:**

- artifact-root og delivery-root kan ikke overlappe, og ingen public mount når artifacts/private filer
- cleanup-kollisjonen er løst før første `releases/...`-fil skrives
- komplett square/landscape/share verifiseres på checksum, dimensjon og format før activation
- samme key/samme bytes retries; samme key/andre bytes feiler hardt; delvis release er aldri aktiv
- delivery-rooten inngår ikke i dagens generiske orphan-cleanup; eventuell senere cleanup er dry-run-first, eksplisitt apply og fail-closed
- retirement/deny er terminalt for release-ID, sletter ikke automatisk filer i 3E.1B, og republisering går via ny selection-revisjon og ny UUID/key
- delivery-rootens backup og isolerte restore er verifisert før stagingaktivering; rooten har ingen web-/Nginx-serving og public runtime forblir av

**Testkrav:** storage-/filesystempermissionstester, path-/root-overlapp, partial/crash/retry, no-clobber, checksum-/formatavvik, activation-gate, cleanup-race og isolert backup/restore med identiske checksums.

**Rollback:** materialisering deaktiveres; ingen automatisk filfjerning kjøres. Inaktive filer kan bare ryddes senere gjennom en verifisert release-/ledger-aware prosedyre, mens reservations-/lifecyclehistorikk beholdes.

### Fase 3E.1C – kontrollert serving og origins

**Omfang:**

- Django release-gate og intern Nginx `X-Accel-Redirect` eller dokumentert likeverdig mekanisme
- smal read-only `authorize` gjennom den eksisterende lokale broen, uten ledger-/anchor-/Borg-mutasjon
- serialiserte lifecycle-mutations og kontrollert parallell read-authorization uten at lesere kan gå forbi ventende terminal lifecycle-mutation
- eksplisitte `PUBLIC_SITE_ORIGIN`/`PUBLIC_MEDIA_ORIGIN`
- cache-, expiry-, purge- og observabilitykontrakt for vanlig serving

**Akseptansekriterier:**

- ingen direkte anonym alias/mount kan nå delivery-root, artifact-root eller private filer
- gateway avviser ukjent/denied/retired/scope-feil/upublisert/manglende/korrupt release og ukjent cursor
- `authorize` verifiserer callerens forventede release-, tenant-, Organization-, variant-, key- og checksum-scope mot ledgerens autoritative reservation, eksponerer ingen generell ledgerdata og utfører ingen write/repair/anchor/Borg-operasjon
- vilkårlig `Host`/`X-Forwarded-Host` kan ikke endre public URL
- valgt cachepolicy er målt og dokumentert; fallback kan ikke bli stående som feilaktig aktiv release
- delivery kan holdes av bak featuregate uten å endre legacy PUBLIC

**Testkrav:** route-/path traversal-/scope-/publicationtester, host-header-invarians, stale cursor, corrupt/missing file, read-only/no-anchor-autorisasjon, parallelle authorize-kall, mutation-/authorize-concurrency med terminal state som vinner, cache expiry/purge og intern-location-verifikasjon.

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

**Implementeringspresisering 2026-08-24:** `PUBLIC_IMAGE_PROJECTION_ENABLED` og `PUBLIC_IMAGE_API_SCHEMA_ENABLED` er separate fail-closed gater med kode- og eksempelstandard `False`. Schema krever projection, serving og gyldig media-origin. Den kanoniske `crm.urls_public`-/`PublicActorPublicViewSet`-/`PublicActorSerializer`-kjeden er alene om `/api/public/actors/`; detail bruker `org_number`. Projection og serving deler samme release-/mappinginvarianter, mens bare serving leser og verifiserer delivery-bytes. Projection autoriserer alle tre varianter gjennom eksisterende variant-scopet read-only `authorize` og faller samlet tilbake ved ett negativt eller utilgjengelig svar. Fullkatalog-shadow kjøres med den skrivebeskyttede `audit_public_image_projection`; list-requesten påføres ikke tre socketkall per asset. De eksisterende 3B.1-fallbackfilene gjenbrukes byte-for-byte på versjonert static-sti som teknisk shadowrepresentasjon. Dette godkjenner ikke endelig grafikk eller fallback-alttekst og aktiverer ikke schema, PUBLIC eller 3E.3.

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

**Rollback:** det globale cutoverflagget av; systemfallback brukes når legacy ikke kan brukes sikkert.

**Implementeringspresisering 2026-08-24:** 3E.3 bruker en global fail-closed `PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=False`; ingen tenant-enrollment eller eventmodell innføres uten en konkret blocker. Cutover krever projection, targetschema, controlled serving og gyldige site-/media-origins. Views løser og attacher en transient `PublicImageProjection`; templates kaller ingen domenetjeneste. List/detail bruker square, detail-head bruker share, og list-head bruker production fallback v1 share. Canonical bygges bare fra `PUBLIC_SITE_ORIGIN` og `reverse()`, også på filtrerte lister. Approved nonblank alt og offentlig kreditering bevares; systemfallback og blank asset-alt gir ingen skjult aktørnavn-alt. Asset-bytefeil i PUBLIC kan bytte én gang til static square-fallback uten legacyoppslag eller write. Legacyfeltene beholdes for kontrollert rollback og senere 3F. Ingen modell eller migrasjon er lagt til. Den separate staginggaten har bevist schemaaktivering, rollback, PUBLIC-cutover, live asset/fallback, safety, host/proxyinvarians, fast queryprofil og visuell katalogaksept; 3E.3 er derfor `CLOSED / ACTIVE`.

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

**Implementeringspresisering 2026-08-24 – implementert, ikke stagingaktivert:** 3E.4 innfører `PUBLIC_IMAGE_TAKEDOWN_ENABLED=False` som en ren skrivegate for nye formelle takedowns. Allerede ankret release-deny, tenant-scopet checksum-deny og legacyguard håndheves alltid, også når denne gaten eller 3E.3-cutoveren er av. Den autoritative source-identiteten er `ImageAsset.checksum_sha256`, altså SHA-256 av de immutable originale kildebytene; rendition-checksummer forblir integritetsbevis for de tre releasefilene. Global checksum-deny og same-checksum-override er utenfor MVP.

Ledgeren evolveres additivt fra schema v1 til v2 uten omskriving av eksisterende events, payloads, sekvenser eller hashkjede. V2 legger til `tenant_checksum_denied` og rebuildbar state for `(tenant_id, source_checksum_sha256)`, med deterministisk eventidentitet `tenant-checksum-denial:v1:<tenant_id>:<sha256>`. Upgrade skal bevare ledger-ID, cursor, head hash, receipts og eksisterende v1-restore; første nye v2-sikkerhetshendelse må gi en ny cursor før et v2-bundle ankres. PostgreSQL er audit og workflow-state, aldri parallell deny-authority.

Den støttede bridgeoperasjonen `deny` skriver konkret `release_denied` og eventuell ny `tenant_checksum_denied` i én SQLite writertransaksjon og bekrefter deretter samme nye head synkront i off-serverankeret. Broen får i tillegg smale, read-only `check_checksum`- og `legacy_guard`-operasjoner. `authorize` krever forventet source-checksum og avviser enhver release i samme tenant når checksummen er denied, uavhengig av om akkurat den release-ID-en har et eget deny-event. `activate` krever samme tenant/source-checksum og kontrollerer checksum-denyen i den samme serialiserte SQLite-transaksjonen som activation-eventet; dermed vinner en deny som ankrer etter siste materialiseringskontroll, men før activation. Avvist activation rydder de tre uaktiverte originfilene. Den eldre enkle operator-CLI-denyen er teknisk deaktivert og kan ikke omgå den atomiske formelle pathen. Ukjent eller ikke-`READY` safety-state blokkerer approval, restore og releaseoppretting og gir fallback eller kontrollert ingen levering.

Den interne API-handlingen er tenant- og Organization-scopet og mottar bare en lukket reason code. Plattform-superadmin kan handle på tvers av tenants; aktiv tenant-`SUPERADMIN` og `GRUPPEADMIN` kan handle i egen tenant; `REDIGERER`, `LESER`, inaktivt eller manglende medlemskap avvises server-side. Tjenesten finner eksakt aktiv asset-selection og dens komplette bundne release; caller kan ikke velge release-ID, checksum, event-ID eller key.

Deny-first-rekkefølgen er: autoriser og lås eksakt target; skriv og ankre release-/checksum-deny; opprett en ny aktiv systemfallback-selectionrevisjon og et eget append-only `formal_takedown`-reviewevent med actor, tid, lukket reason code, forrige selection/revisjon, source-checksum og release-UUID-snapshot; slett deretter eksakt de tre canonical deliveryfilene med no-follow og idempotent missing-semantikk; verifiser origin og HTTP/cache. DB-aggregat, mappings, private originaler, artifacts og historikk beholdes. Crash eller tapt respons skal alltid kunne retries mot samme permanente deny uten ny sikkerhetsidentitet.

Legacyguard leser safety-state for tenant/Organization og blokkerer `thumbnail_image_url`, `auto_thumbnail_url`, `og_image_url`, favicon og ekstern preview etter takedown, også etter eldre PostgreSQL-restore og full 3E.3-rollback. Approval/replacement, selection-restore og releaseoppretting sjekker tenant-checksummen før state-write. Samme bytes kan fortsatt prosesseres privat, og samme checksum i en annen tenant er tillatt, men godkjenning, restore og release i den denied tenant-en avvises.

MVP-cachekontrakten beholder `private, max-age=60, must-revalidate`, checksum-`ETag`, reautorisert `304`, `no-store` på feil og ingen `immutable`. Målt staginggrunnlag 2026-08-24 viste `CF-Cache-Status: BYPASS` og ingen shared proxycache. Derfor innføres ingen ekstern purgeintegrasjon nå; fullført takedown krever at gammel URL gir `404/no-store`, gammel ETag aldri gir `304`, originfilene er borte og Cloudflare/proxy ikke rapporterer `HIT`. Dersom staging senere viser en shared cache, stoppes aktiveringen til providerpurge og credentials er besluttet og verifisert.

Sikker senere republisering bruker en ny originalchecksum, ny selection-revisjon, ny release-UUID og nye canonical keys. Den gamle checksum-denyen og release-denyen består. 3E.4 introduserer ikke en allow-/override-event.

## Avklarte 3E.1B-implementasjonsvalg

Følgende valg er godkjent, implementert og stagingaktivert i 3E.1B-materialiseringsruntimeen:

- AF_UNIX/SOCK_STREAM på `/run/kreative-norge-image-safety/bridge.sock`, 4-byte big-endian framing, JSON-protokoll v1, 16 KiB request-/responsegrense, 5 sekunders framingtimeout, 45 sekunders operasjonsfrist og omtrent 50 sekunders Django-clienttimeout innenfor dagens 60-sekunders Gunicorn-timeout
- root-eid systemd socket activation med socket `0600`, `SO_PEERCRED` der den faktiske Docker-/Unix-socket-identiteten kan verifiseres, og host-eid ledger-/Borg-runtime uten credentials eller ledger-mount i API/web
- deterministisk reservation identity i ledgeren, atomisk `reserve_or_get`, unik databaseconstraint direkte på `selection` og immutable `selection_revision_snapshot`; safety-ledgeren er fortsatt eneste lifecycle-authority
- bare `reserve` og `activate` er caller-aktive bridge-operasjoner i denne slicen; `retire` og `deny` forblir utilgjengelige for Django
- separat `public_image_delivery` på `/srv/kreative-norge/media/public-delivery`, API-only mount, ingen web-/Nginx-eksponering og eksplisitt backupallowlist

## Avklarte 3E.1C-implementasjonsvalg

Følgende valg er godkjent, implementert og liveverifisert i staging bak en separat kode-/eksempel-default-off servinggate:

- canonical `GET`/`HEAD /media/releases/<uuidv4>/<variant>.<ext>` via Django og intern Nginx-location `/_protected-public-image/`; ingen anonym alias kan nå delivery-rooten direkte
- tom `404/no-store`-catch-all for ikke-canonical former under samme prefix uten domenekall, og CSRF-unntak bare på den write-frie media-viewen slik at andre metoder stoppes som `405/no-store` før domenekall
- read-only `authorize` på eksisterende socket med eksakt release-/tenant-/Organization-/variant-/key-/checksum-scope, parallelle lesere og writer-preferred lifecycle-gate uten write, repair, anchor eller Borg
- read-only deliverymount i `web`, `internal`, `autoindex off`, `disable_symlinks on` og en dedikert numerisk supplementary group `2000`; host-preparering feiler ved GID-kollisjon og bruker setgid-directories/`0640`-filer, mens web-imaget oppretter samme GID og gjør `nginx` til medlem slik at privilegiedroppet ikke fjerner lesetilgangen
- `PUBLIC_IMAGE_SERVING_ENABLED=False` som egen standard; `PUBLIC_SITE_ORIGIN` og `PUBLIC_MEDIA_ORIGIN` må være eksplisitte, HTTPS utenfor debug og bundet til eksakt ikke-wildcard `DJANGO_ALLOWED_HOSTS`
- `private, max-age=60, must-revalidate`, checksum-`ETag`, reautorisert `If-None-Match` → `304`, `no-store` på 404/503, ingen shared proxycache og ingen `immutable`; Nginx auto-ETag er av bare i den interne delivery-locationen, som setter `ETag` fra `$upstream_http_etag` slik at Djangos verifiserte checksum beholdes i stedet for filmetadata
- strukturerte requestutfall på en eksplisitt INFO-consolelogger med release-ID, variant, status, safety-kategori/cursor og varighet, uten filesystempath, credential eller ledgerhistorikk

## Gjenstående operasjonelle detaljer

Følgende avgjøres med evidens i riktig senere leveranse uten å åpne hovedretningen på nytt:

- retensjon og eksplisitt apply-prosedyre for inaktive/ufullstendige release-filer; ingen automatisk sletting er godkjent
- ekstern purgeintegrasjon innføres bare dersom aktiveringsgaten påviser shared cache; dagens målte `CF-Cache-Status: BYPASS` krever i stedet 404/no-store, ingen 304 fra gammel ETag, ingen cache-HIT og fravær av originbytes
- alertterskler og eventuelle eksterne målinger utover 3E.1Cs requestutfall og operatør-runbook
- retensjon for derived read-model-backups

Disse detaljene kan ikke svekke permanent no-reuse, deny-over-restore, separat delivery-root, controlled serving, én projection eller kravet om ny UUID/key ved republisering.

## Gjenstående verifikasjons- og godkjenningsgater

3E.1B-kodevalgene over er godkjent og krever ingen ny arkitekturavgjørelse. Deploymentgaten 2026-08-23 verifiserte:

- tom `OrganizationImageRelease`-tabell før migrasjon `0029`, anvendt migrasjon og fortsatt `0` releases
- faktisk root-eid socket `0600`, `SO_PEERCRED` fra API-containeren, aktiv systemd socket/service og 5/45/50/60-sekunders timeoutkjede i staging
- at API bare fikk socket- og delivery-mountene, mens web ved 3E.1B-stoppunktet fortsatt manglet delivery-, socket-, ledger- og Borg-tilgang; 3E.1C har senere gitt web bare delivery read-only
- delivery-persistens gjennom API-recreate og identisk checksum i en ny backup, full repository-/arkivverifikasjon og isolert restore

Materialiseringsgaten 2026-08-23 beviste create/retry/no-clobber, delvis materialisering og restart med syntetiske komplette renditions gjennom den faktiske reserve → DB-binding → materialisering/read-back → activate-workflowen. Ved avslutningen var ledgeren `READY` på cursor `5` med én syntetisk release i `active`, PostgreSQL hadde ett komplett immutable aggregate og delivery-rooten tre checksumverifiserte filer. Se [foundationevidensen](../status/STAGING_PHASE_3E1B_FOUNDATION_2026-08-23.md) og [aktiveringsevidensen](../status/STAGING_PHASE_3E1B_MATERIALIZATION_ACTIVATION_2026-08-23.md).

Servinggaten 2026-08-24 aktiverte deretter 3E.1C på eksakt merge `38663b5` og beviste HTTP-/cachekontrakten, negative svar, read-only safety-scope, bridge-/filfeil, restart, origins, observability, isolasjon og backup/restore. Sluttstate er ledger `READY` på cursor `7`, to release-aggregater og seks delivery-filer. Se [3E.1C-evidensen](../status/STAGING_PHASE_3E1C_ACTIVATION_2026-08-24.md).

3E.2-shadowgaten 2026-08-24 deployet eksakt merge `90ff5e9`, beholdt schema/PUBLIC av og beviste én canonical route, `122 = 1 asset + 121 systemfallback`, fem faste queries, tre authorize-kall, `0` safety-/scopefeil, asset/fallback/unpublished, uendret API/PUBLIC/OpenAPI og uendret cursor/radantall/deliverymanifest. Projection-shadow står på med lav målt request-overhead. Se [3E.2-evidensen](../status/STAGING_PHASE_3E2_SHADOW_2026-08-24.md).

3E.3-cutovergaten 2026-08-24 aktiverte target-API, PUBLIC/head, canonical origins og production fallback v1 på eksakt merge `e04220b`. Schema og PUBLIC ble rollbacket og reaktivert; desktop/mobil, host/proxy-/privacy-/safetyadferd, fullkatalogen `122 = 1 asset + 121 systemfallback`, fast queryprofil, backupstatus og uendret deliverymanifest ble bevist. Se [3E.3-evidensen](../status/STAGING_PHASE_3E3_CUTOVER_2026-08-24.md).

Retensjon og eksplisitt apply-prosedyre for generell release-aware cleanup er fortsatt ikke godkjent. 3E.4-koden er default-off; separat ledger-upgrade, permanent syntetisk takedown, cache-/restorebevis og evidence-PR gjenstår før `CLOSED / ACTIVE`.
