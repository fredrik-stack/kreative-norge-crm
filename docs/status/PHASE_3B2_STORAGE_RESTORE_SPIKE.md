# Fase 3B.2: isolert storage-, takedown- og restoreprototype

**Dato:** 2026-07-31

**Status:** Teknisk prototype gjennomført. Prosjekteier godkjente de leverandøruavhengige arkitekturprinsippene 2026-08-01. Ikke implementert i CRM-runtime.

**Arkitekturgrunnlag:** [ADR-007](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md)

**Reproduserbar lab:** [`spikes/storage_pipeline/`](../../spikes/storage_pipeline/README.md)

**Tekstlig evidens:** [fase 3B.2-manifest](evidence/phase3b2-storage-restore-evidence.json)

Rapporten skiller mellom målt prototypefakta, de opprinnelige tekniske anbefalingene, prosjekteiers senere beslutning og fortsatt åpne leverandørvalg. Ingen produksjonsleverandør er valgt.

## 1. Executive summary

Den isolerte laben beviser følgende domenekontrakt med syntetiske bytes:

- Django 5.1 kan bevare `default` og `staticfiles` samtidig som private originaler og offentlige renditions får separate `STORAGES`-aliaser
- fase 3B.1-keyen kan gjenbrukes som intern processing artifact identity, mens en separat public release key kan endres uten ny encoding
- public release R1 kan fjernes, deny-registreres og purges fra en cache-fake
- restore av et eldre state-snapshot og eldre objekter kan ikke reaktivere R1 når deny-journalen ikke rulles tilbake
- autorisert gjenoppretting bruker R2; R1 forblir denied
- private versioner, delete marker, versjonslisting og copy fungerer administrativt i Moto
- aktiv offentlig lagring kan være unversioned med immutable release keys; en versioned offentlig testbucket viste at historiske bytes kunne nås med gammel `versionId`
- direkte backup av aktive renditions og regenerering fra original + metadata har ulike styrker; en hybridmodell anbefales til vurdering
- den statiske 3B.1-fallbacken fungerer uten S3, database, renderer, ekstern URL eller valgt leverandør

Moto 5.2.2 viste samtidig et viktig emulatorgap: unsigned GET av en eldre privat versjon med eksplisitt `versionId` ble tillatt selv uten offentlig bucket policy. En recording private-access boundary avviser dette som domenekontrakt, men faktisk leverandør må senere bevise IAM- og versjonspolicyen.

## 2. Status og eksplisitt prototypeavgrensning

Dette er fase 3B.2-prototypeevidens. Laben ligger under `spikes/storage_pipeline/`, har egne eksakt pin-nede direkteavhengigheter, isolert Django-settings, tester, Dockerfile, Compose-fil, kjørbar evidenskommando og separat CI-workflow.

Dette er ikke produksjonsstorage. Det finnes ingen CRM-modell, migrasjon, runtime-setting, API-rute, Editor-flyt, PUBLIC-integrasjon, faktisk CDN, stagingendring eller deploy i leveransen. Dagens legacy `thumbnail_image_url`-, `auto_thumbnail_url`-, `og_image_url`- og faviconflyt gjelder fortsatt.

## 3. Testmiljø

Lokalt målt:

- macOS 26.5.2 ARM64
- Python 3.12.9
- Django 5.1.15
- django-storages 1.14.6
- boto3 og botocore 1.43.62
- Moto Server 5.2.2 på en lokal, disponibel port
- 36 isolerte tester
- bare syntetiske bytes, generert metadata og tre committed fallback-PNG-er fra fase 3B.1

Den dedikerte Compose-kontrakten bruker det offisielle `ghcr.io/getmoto/motoserver:5.2.2`-imaget og en separat labcontainer. Ordinære Compose-filer er ikke endret.

## 4. Emulatorvalg og vedlikeholdsstatus

[Moto 5.2.2 ble publisert 6. juni 2026](https://pypi.org/project/moto/5.2.2/) med Apache-2.0-lisens, Python 3.10+ og attestert publisering fra `getmoto/moto`. Prosjektet hadde flere ordinære releaser i 2026 og vurderes som aktivt vedlikeholdt per 2026-07-31.

[Moto-dokumentasjonen](https://docs.getmoto.org/en/stable/docs/server_mode.html) beskriver både reproduserbar `moto[server]`-installasjon og offisielle images i Docker Hub og GitHub Container Registry. Løsningen ble derfor valgt fremfor en arkivert eller uverifisert objektserver.

Moto brukes bare som disponibel S3-protokollemulator. Det er ikke en produksjonsleverandør og sier ikke hvilken S3-kompatibel tjeneste prosjektet senere skal velge.

## 5. Emulatorbegrensninger

[Moto 5.2.2s S3-matrise](https://docs.getmoto.org/en/stable/docs/services/s3.html) oppgir støtte for create bucket, put/get/head/delete object, bucket policy, versioning, list object versions, copy object og relevante øvrige operasjoner. Dokumentasjonen sier samtidig at bucket-policyhåndhevingen er grunnleggende: bare `Principal=*` tas i betraktning, og conditions tas ikke i betraktning.

Faktisk måling i laben:

- gjeldende privat objekt uten public policy ble avvist ved unsigned GET
- eldre privat versjon ble likevel hentbar unsigned med eksplisitt `versionId`; recording-grensen avviste samme forespørsel
- historisk versjon i offentlig versioned bucket var anonymt hentbar med `versionId`
- enkel `Principal=*` GetObject-policy gjorde aktive public objekter lesbare

Spiken beviser derfor ikke komplett IAM, deny-precedence, conditions, public access block, konsistens, object lock, provider-backup eller autentiseringsmodell. Disse må testes mot valgt leverandør.

## 6. Django `STORAGES`-konfigurasjon

`test_settings.py` deklarerer hele dictionaryen eksplisitt fordi `STORAGES` erstatter standarddictionaryen:

| Alias | Backend | Prototypeformål |
| --- | --- | --- |
| `default` | `FileSystemStorage` | sentinel for eksisterende filkontrakt |
| `staticfiles` | `StaticFilesStorage` | bevarer eksplisitt staticfiles |
| `image_originals_private` | django-storages `S3Storage` | privat bucket, signert URL-adferd ikke produktbesluttet |
| `image_renditions_public` | django-storages `S3Storage` | public bucket, unsigned objektadferd i lab |

Ingen av aliasene finnes i eller endrer `config/settings.py`.

## 7. Default-storage-sentinel

Sentinelen skrev `sentinel/default-import-export-contract.txt` gjennom Djangos `default` og bekreftet:

- backend var `FileSystemStorage`
- filen lå under labens egen default-katalog
- privat original og public rendition lå i hver sin Moto-bucket
- `staticfiles` var fortsatt tilgjengelig som `StaticFilesStorage`
- ingen ekte `ImportJob` eller `ExportJob` ble importert eller brukt

Image-aliasene påvirket dermed ikke prototypens default storage. Dette beviser settingsformen, ikke en runtimeendring.

## 8. Lokal filesystemreferanse

Lokal referanse bruker Djangos ordinære `FileSystemStorage` og en temporær labrot. Skriv/eksisterer/path ble kontrollert. Den er bevisst enkel og sier ikke noe om fremtidig lokal medie-UX eller migrering av eksisterende import-/eksportfiler.

## 9. S3-emulatorkontrakt

Tre buckets ble opprettet i `us-east-1`:

- `phase3b2-private`: versioned private originaler og interne artifacts
- `phase3b2-public`: aktiv, unversioned public release-prototype
- `phase3b2-public-versioned`: risikoprobe for historiske public bytes

Laben kjørte create, put, get, head, delete, policy, versioning, version list, delete marker og copy object. Metadata, MIME, `Cache-Control`, checksums og byteinnhold ble kontrollert. Moto-endpointet er bare administrativ labkonfigurasjon og brukes ikke i den separate produksjonslignende public-origin-testen.

## 10. Privat original

Originalkeyen er tenant- og checksumscopet. Samme key + samme bytes er idempotent; samme key + ulike bytes avvises. MIME og nedlastet SHA-256 kontrolleres.

Aktiv privat original kunne ikke hentes anonymt. Den ordinære public URL-builderen tar bare public release keys og returnerer aldri originalkey. Ingen endelig beslutning om signert URL, administrativ nedlasting, karantene-UI eller private permissions er tatt.

Eldre private versjoner må verifiseres mot faktisk leverandør på grunn av Moto-gapet beskrevet over.

## 11. Offentlig rendition

Public rendition ble skrevet gjennom eget Django-alias og hentet unsigned i laben. Objektet hadde:

- `Content-Type: image/webp`
- `Cache-Control: public, max-age=31536000, immutable`
- checksum som matchet artifact bytes
- ingen credentials eller signert query i public URL

Samme public key kan leses idempotent med samme bytes, men ulike bytes avvises. Aktiv public bucket er unversioned i prototypen.

## 12. Processing artifact identity

Fase 3B.2 importerer `immutable_rendition_key` og `PROCESSING_VERSION` direkte fra den isolerte fase 3B.1-kontrakten. Målt key:

```text
renditions/phase3b1-pillow-v1/b9f0b25fb8290bd1/landscape-fba14cf447afda26f4a5.webp
```

Identiteten inneholder source checksum, processing-version og hash av canonical render config med variant, format, fit og fokus. Encoderinnstillingene er bundet til `phase3b1-pillow-v1`; endrede innstillinger med samme processing-version avvises. Dermed kan de ikke stilltiende produsere nye bytes under samme key.

## 13. Public release identity

Målte releases for samme artifact checksum:

```text
R1 public/tenant-a/actor-42/r1/landscape-d7ce9829b2d2ae19545c.webp
R2 public/tenant-a/actor-42/r2/landscape-d7ce9829b2d2ae19545c.webp
```

Tenant, actor, release revision, variant og artifact hash inngår. R2 fikk ny key uten ny encoding. Actor-navn eller request host brukes ikke. Feil tenant-prefix, traversal-lignende segmenter, kontrolltegn og token-/credential-lignende keyfragmenter avvises.

## 14. Anbefalt to-key-kontrakt

**Teknisk anbefaling til godkjenning:** Behold intern artifact key og separat public release key.

Å bruke artifact key direkte offentlig gjør artifactens identitet til permanent publiseringsidentitet og kompliserer takedown, cache og autorisert gjenutgivelse. To-key-modellen lar identiske prosesserte bytes få R2 etter et avgjort takedown uten å gjenaktivere R1 eller re-encode.

Dette er en anbefaling. ADR-007 er ikke endret som om modellen var endelig godkjent.

## 15. Versioning for private originaler

Private bucket hadde versioning aktivert. Proben skrev to versjoner, slettet uten version ID, fant én delete marker og to historiske versjoner, hentet gammel versjon administrativt og kopierte den byte-identisk.

**Åpent leverandørkrav:** Historiske private bytes skal aldri være anonymt tilgjengelige. Moto brøt forventningen for unsigned `VersionId`; recording-grensen håndhevet deny, men dette er ikke infrastrukturelt bevis.

## 16. Versioningalternativer for public renditions

Sammenligningen viser:

- versioned public bucket beholdt gammel public-versjon, som var anonymt hentbar med `versionId`
- unversioned public bucket med immutable release keys fjernet aktiv R1 og brukte separat backup/regenerering

**Teknisk anbefaling til godkjenning:** Bruk unversioned aktiv public storage med immutable release keys, separat R1-deny og kontrollert backup/regenerering. Dette reduserer risikoen for at historiske public bytes fortsatt kan nås, og er enklere på tvers av leverandører. Providerens delete-, cache- og backupsemantikk må likevel verifiseres.

## 17. Deny-journalprototype

Journalen er en separat JSONL-fil utenfor app-state-snapshotet. Hver hendelse inneholder event ID, tenant, public key, artifact/source checksum, tid, action, reason, principal, tidligere/ny release key og schema version.

API-et tilbyr append, replay og avledning av deny-sett. Det tilbyr ikke update eller delete. Identisk duplikat-event er idempotent; samme ID med annen payload avvises. Korrumpert eller manglende journal gir fail-closed fallback.

Prototypen beviser domeneflyt og replay. Den gir ikke kryptografisk tamper evidence, WORM, separat failure domain, tilgangskontroll, replikering, retention eller katastrofegjenoppretting.

## 18. Takedownscenario T0–T5

| Tid | Målt resultat |
| --- | --- |
| T0 | privat original, artifact og R1 fantes; R1 var unsigned lesbar; state pekte på R1; journal tom |
| T1 | state-snapshot og object inventory/checksums ble tatt; journalen inngikk ikke i snapshotet |
| T2 | deny-event ble appendet, R1 slettet ved origin, stale cache bestod før purge, purge fjernet den, resolver valgte statisk fallback |
| T3 | eldre state og R1 ble reintrodusert; deny-journalen beholdt nyere event |
| T4 | replay/reconciliation oppdaget R1, slettet og blokkerte den igjen; fallback bestod |
| T5 | samme artifact bytes ble publisert som R2; resolver brukte R2; R1 forble denied og fraværende |

Testen feiler dersom R1 leveres etter reconciliation.

## 19. Purgeadapter og cache-simulator

`RecordingPurgeProvider` tar public key eller absolute URL og returnerer request ID, status, `purged`, idempotent replay, retryability og eventuell feil. En retrybar timeout-feil og vellykket retry er testet.

Cache-simulatoren viste at origin delete alene ikke fjerner stale R1. Purge fjernet oppføringen, repetert purge var idempotent, og restore publiserte R2 i stedet for R1. Ingen faktisk CDN eller leverandør-API er bevist.

Senere må valgt CDN teste autentisering, rate limits, batch, wildcard, propagation, timeout, retry/backoff, observability, request IDs og partial failure.

## 20. Backupstrategi A

Strategi A tok privat original og aktiv public rendition direkte. På de små syntetiske bytesene:

- 2 objekter
- 92 bytes
- målt restore 0,004 ms i én lokal kjøring
- ingen renderer eller gammel Pillow-versjon nødvendig for byte-identisk public restore

Fordelen er eksakt bytebevaring og rask restore. Ulempen er større objektvolum for reelle data og behov for streng deny-reconciliation før public reintroduksjon.

## 21. Backupstrategi B

Strategi B tok privat original og canonical metadata, og brukte en deterministic recording renderer:

- 1 objekt + metadata
- 207 bytes i den kunstig lille fixtureen
- målt restore/regenerering 0,004 ms i én lokal kjøring
- byte-identisk output når processing-version var kjent

Metadata dominerer den mikroskopiske fixtureen, så byteverdiene kan ikke ekstrapoleres. Ukjent processing-version, manglende original, checksumfeil og utilgjengelig storage ble avvist. Den recording renderer erstatter ikke 3B.1s virkelige Pillow-bevis.

Hvis gammel Pillow/wheel ikke lenger er tilgjengelig, kan byte-identisk regenerering ikke loves. Bibliotek, encoder og processing profile må derfor kunne reproduseres eller aktive bytes må ligge i backup.

## 22. Restore- og reconciliationresultater

Komplett direkte restore og regenerering ga samme artifact bytes i domenetesten. Manglende rendition, manglende original, feil checksum, ukjent processing-version, partial restore og storage unavailable feilet eksplisitt.

Eldre snapshot enn siste deny ble reintrodusert, men nyere deny-journal overstyrte state og slettet R1 igjen. Både rekkefølgen deny-before-delete og delete-before-deny ble testet. Retry av delete, takedown, restore, journalappend og purge er idempotent der det forventes.

**Teknisk anbefaling til godkjenning:** Hybridbackup med private originaler, canonical metadata, processing artefakt/profil og aktive public rendition-bytes. Regenerering beholdes som sekundær reparasjonsvei, ikke eneste katastrofeplan. Deny-journalen må ha separat backup/failure domain og alltid reconciles før public serving åpnes.

## 23. Statisk nød-fallback

Laben gjenbrukte `emergency-fallback-square.png`, `emergency-fallback-landscape.png` og `emergency-fallback-share.png` fra fase 3B.1. Landscape-filen var 11 510 bytes med SHA-256 `3cc8c5d08b473d2e114a9d01324f5a422ca9665dd336fd3f29f231d370598df8`.

Fallback returneres ved storage unavailable, manglende rendition, privat storage unavailable, uferdig/manglende/korrumpert deny-reconciliation, rendererfeil og ukjent state/key. Filen krever ikke S3, database, renderer, ekstern URL eller provider. Den er ikke koblet til aktiv PUBLIC-runtime.

## 24. Absolute origin-kontrakt

Kontrakten har eksplisitt `PUBLIC_SITE_ORIGIN`- og `PUBLIC_MEDIA_ORIGIN`-verdi. Produksjonslignende test brukte:

```text
PUBLIC_SITE_ORIGIN=https://www.example.test
PUBLIC_MEDIA_ORIGIN=https://media.example.test/assets
```

HTTPS, trailing slash og pathjoin uten dobbel slash er testet. Credentials, query, fragment og ekstern HTTP avvises. Localhost HTTP krever eksplisitt labmodus. `Host`, `X-Forwarded-Host` og Moto-endpoint påvirker ikke generert public media URL.

## 25. Feil- og robusthetstester

Testpakken dekker:

- duplicate immutable key med samme/ulike bytes
- partial upload, timeout/purgefeil, storage unavailable og object missing
- checksum mismatch og wrong content type
- wrong tenant, traversal, kontrolltegn og credential-/tokenfragment
- private/public alias-forveksling
- deny-event før delete og delete før deny-event
- retry av takedown, restore og purge
- gjentatt journal replay, duplikat-ID, korrumpert og manglende journal
- eldre app-snapshot med nyere deny
- manglende original/rendition, partial backup og ukjent processing-version

36 tester var grønne lokalt.

## 26. Målinger

| Måling | Resultat |
| --- | ---: |
| Labtester | 36 grønne |
| Buckets | 3 |
| Journalhendelser etter T5 | 2 |
| Denied public keys etter T5 | 1, R1 |
| Aktiv public key etter T5 | R2 |
| Strategi A | 2 objekter, 92 bytes, 0,004 ms |
| Strategi B | 1 objekt + metadata, 207 bytes, 0,004 ms |
| Statisk landscape fallback | 11 510 bytes |

Tidsmålingene er én lokal mikrokjøring og brukes ikke til kapasitet eller SLA. Checksums og semantiske utfall er reproduserbare; timing varierer.

## 27. Sikkerhetsbegrensninger

- Moto er ikke et sikkerhetsbevis for IAM eller provideradferd
- testcredentials er syntetiske og gir ingen tilgang utenfor emulatoren
- JSONL-journalen er ikke WORM, signert eller tamper-evident
- recording access- og purgeadaptere håndhever bare domenekontrakt
- ingen signert privat URL, KMS, malwarekontroll, rate limit eller secret rotation er implementert
- public historical version risk er målt, men faktisk leverandør kan ha annen policysemantikk
- ingen person-, aktør-, staging- eller produksjonsdata ble brukt

## 28. Produksjonsforhold som ikke er bevist

Spiken beviser ikke valg eller drift av S3-/CDN-leverandør, kostnader, region, residency, SLA, IAM, access block, encryption, key management, lifecycle, replication, WORM-journal, restore ved regionfeil, CDN propagation, provider-purge, signed private access, presigned expiry, queue, concurrency, orphan cleanup, observability eller reell datamengde.

Fase 3B.1R med representative, rettighetsavklarte bilder og eksplisitt sRGB er fortsatt påkrevd før fase 3C.

## 29. Anbefalinger til prosjekteier

Følgende var prototypens anbefalinger til prosjekteier. Deres senere beslutningsstatus er dokumentert i punkt 33:

1. To-key-modell: intern artifact identity + separat public release identity.
2. Unversioned aktiv public bucket med immutable release keys.
3. Versioned private originaler, men bare etter provider-IAM-test for alle versjoner.
4. Hybridbackup: private originaler + metadata/profil + aktive public rendition-bytes.
5. Separat, varig deny-journal som aldri rulles tilbake sammen med app-state.
6. Fail-closed reconciliation før public serving etter restore.
7. Providergrense for purge og private access med obligatoriske kontrakttester.

## 30. Fortsatt åpne valg

Ved avslutningen av selve prototypen var følgende valg åpne. Punkt 33 skiller prinsippene som senere ble godkjent fra leverandør- og implementeringsvalgene som fortsatt er åpne:

- produksjonsleverandør og region
- endelig private-access- og IAM-kontrakt
- journalteknologi, separat failure domain, WORM/tamper evidence og retention
- public bucket-versioning som formell ADR-beslutning
- endelig backupomfang, frekvens, RPO/RTO og restore-øvelse
- konkret CDN, purge-API og cache-nøkler
- processing artefakters egen storage/backupplassering
- API-schema, aliasmapping, concurrency, queue og orphan-retensjon
- fase 3B.1R-grenser og sRGB-kontrakt

## 31. Historisk anbefalt neste fase 3B-gate ved prototypen

Prosjekteier gjennomførte beslutningsgaten 2026-08-01. Neste anbefalte planleggingsleveranse er en eksplisitt, skrivebeskyttet provider-/driftsgate som sammenligner aktuelle S3- og CDN-alternativer mot private versioner, purge, backup, data residency, kostnad og restore.

På dette tidspunktet åpnet beslutningen ikke fase 3C. Fase 3B.1R og senere fase 3B-gater for API, concurrency, retention og sync/async gjenstod. Punkt 33 beskriver senere beslutninger og dagens gjenværende gater.

## 32. Eksplisitt bekreftelse på at CRM-runtime er urørt

Den samlede PR-leveransen endrer bare:

- `spikes/storage_pipeline/**`
- en separat path-filtrert spike-workflow
- denne rapporten, et lite evidensmanifest, ADR-007 og relevante status-/arkitekturdokumenter

`crm/`, `config/`, modeller, migrasjoner, root `requirements.txt`, produksjons-Dockerfile, ordinære Compose-filer, staging-Compose, nginx, API, Editor, PUBLIC, database, staging og deploy er urørt. Bildearkitekturen er fortsatt ikke implementert i CRM-runtime.

## 33. Prosjekteiers beslutning etter prototypeanbefalingene

Prosjekteier godkjente 2026-08-01 følgende leverandøruavhengige arkitekturprinsipper i [ADR-007 punkt 24](../decisions/ADR-007-IMAGE_ASSET_ARCHITECTURE.md):

1. Intern processing artifact identity og public release identity er separate immutable identiteter. Ny offentlig revisjon bruker ny release key, også ved gjenbruk av samme artifact-bytes. Eksakt public key-struktur er åpen.
2. Aktiv public rendition-store er dedikert og uten tilgjengelig historikk, med immutable release keys. [ADR-008](../decisions/ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md) valgte senere host-persistent lokal storage for første MVP. Dersom objektlagring senere innføres, regnes ikke en versioning-suspended bucket automatisk som aldri-versioned.
3. Public delivery betyr ikke anonym public bucket. Første MVP bruker kontrollert same-origin/lokal media-origin; intern filesystempath eksponeres ikke. Privat/origin-begrenset objektlager og CDN er bare betingede fremtidige krav.
4. Private originaler bruker i første MVP separat host-persistent storage, permissions og rollebeskyttet tilgang. Provider-versioning, IAM/public-access-block og eksplisitt `versionId`-bevis kreves bare dersom objektlagring senere innføres.
5. Hybridbackup omfatter private originaler, canonical metadata, eksakt processingprofil, nødvendige referanser og audit, aktive public rendition-bytes og deny-journal i separat failure-domain. Regenerering er sekundær reparasjonsvei.
6. Restore går gjennom ikke-offentlig karantene, nyeste deny-journal, replay, reconciliation, checksum-/referansekontroll og fail-closed fallback før public serving åpnes. En eldre snapshot vinner aldri over nyere deny.
7. Varig deny-journal er append-only/WORM-orientert, separat fra app-/databasebackup, idempotent og fail-closed. Normal takedown er deny-first, deretter origin-delete og purge.
8. Journalen er autoritativ, mens runtime kan bruke en materialisert deny-read-model med kjent cursor. Ukjent eller stale sikkerhetstilstand gir fallback.
9. Senere produksjonsmodell skal støtte release deny, tenant-scopet checksum deny og særskilt global checksum deny. Fase 3B.2 beviste bare release deny; checksum-deny er ikke implementert.
10. Origin-delete alene er utilstrekkelig. Lokal response-/media-cache-purge skal være idempotent, skille retrybare/permanente feil og registrere request-/hendelses-ID og verifikasjon; eventuell senere CDN-purge skal bevise samme kontrakt.
11. Moto 5.2.2 forblir kun emulator. Det er ikke produksjonsleverandør eller IAM-bevis, og det observerte unsigned `VersionId`-gapet er bare en betinget provider-gate dersom objektlagring tas opp igjen.

Laben brukte anonym GET mot en Moto-bucket for å bevise S3-protokolladferd. Dette er ikke et produksjonskrav og skal ikke tolkes som valgt deliverymodell.

Fortsatt åpne MVP-valg er lokal private/public-storage og serving, lokal cache/purge/verifikasjon, permanent journalteknologi, WORM/tamper evidence, read-model/cursor, full katastrofe-RTO, eksakt public key-struktur, concurrency/databaseconstraints, retensjonsmekanisme, sync/async-grense, observability og konkrete driftstjenester. ADR-008 har valgt og aktivert stabil lokal Borg `>=1.2.8` og `<1.3.0` med remote path `borg-1.2`, separat Hetzner Storage Box og retention 14/8/12; nattlig RPO og restore-smoke er målt. Provider, region, ekstern IAM, CDN, KMS, Object Lock og provider-spesifikk `versionId`-verifikasjon gjenåpnes bare ved dokumentert behov for objektlagring.

Den daværende provider-/driftsgaten ble senere erstattet av ADR-008s lokale storage-/backup-MVP. Backupkjeden er operativt aktivert, og fase 3B.1R er gjennomført og godkjent. Senere lokale API-, serving-, journal-, concurrency-, retention-, sync/async- og observabilitygater gjenstår før reell bilde-runtime og offentlig serving kan aktiveres.
