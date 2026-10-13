# 6A.1 – staging: første deployavbrudd og kontrollert API-recovery

**Dato:** 2026-10-13

**Historisk status etter første utføring:** DELVIS LEVERT / SCHEMA APPLIED / API DEPLOY ABORTED / OLD API RECOVERED. Ikke full teknisk stagingverifikasjon. Shared funksjoner er IKKE AKTIVERT.

**Historisk status etter recovery, 2026-10-13 17:41:33 UTC / 19:41:33 CEST (UTC+02:00):** API RECOVERY COMPLETED / PARTIALLY VERIFIED. Eksakt målimage kjører; 0033 er beholdt og bevarings-/checkpointkontrollene er grønne. Autorisert Editor-/admin-HTTP og ekstern HTTPS er fortsatt uavklart. Backup-timer er gjenopptatt og skrivefrys opphevet. Ingen shared aktivering.

**Gjeldende 6A.1-status etter eierbekreftelse mottatt 2026-10-13:** STAGING VERIFIED / OWNER-CONFIRMED – additiv skjemagrunnmur og API-runtime verifisert innen avtalt 6A.1-scope. Ingen backfill eller shared-aktivering. Grunnlaget er eksisterende tekniske bevis, etterfølgende skrivebeskyttet review og prosjekteiers manuelle lesebekreftelse; se [eierbekreftelsen](#prosjekteiers-lesebekreftelse-mottatt-2026-10-13). Dokumentasjonens commit/push/PR/CI/merge rapporteres separat.

De historiske avsnittene fra «Mandat og kodebaseline» frem til «Kontrollert API-recovery» beskriver den **første, avbrutte utføringen** og dens daværende runtime. De skal ikke leses som nåstatus etter den senere recoveryen. Historiske bevisgap består.

## Mandat og kodebaseline

Godkjent scope var API-only deploy og `0033_domain_assignment_foundation` etter `0032`, med fersk backup/isolert restore, skrivefrys og bevaringsbevis. Ingen seed/backfill, delingsaktivering, neste 6A-etappe eller publisering av evidens.

- Merget kode/målcommit: `b2d4725e8547f49c39256db188107f2ed29ed93c`, [PR #75](https://github.com/fredrik-stack/kreative-norge-crm/pull/75).
- PR-head `3e4769e3bbf7832b953ce31bd4a7f76932cd188a`, CI `38419120053` 6/6 success; main-CI `38419948624` 6/6 success på målcommiten.
- Servercheckout før utføring: ren `95627bef44275b16a211fe0e529b5a0366051701`.
- Servercheckout etter utføring: ren, detached på eksakt målcommit. Checkout er ikke bevis på kjørende API-versjon.
- Ny API-image bygget: `sha256:95e48c44bcdbb1e1afefb386115ab9feed8cd1c40c6f0a4a4a97e1dd612f3ed3`. Den er IKKE kjørende. Installert package-/versjonsliste var identisk med gammel API; dependencylag ble gjenbrukt.
- Kjørende API etter tilbakeføring: opprinnelig image `sha256:afc343cf6e200efe4d23116e9d991897d0de2e6ca9a76542b701696632c15371`, fra den kontrollerte eldre runtimebaselinen. Original container-ID er bevart; Compose omdøpte den til `d75bcd051119_kreative-norge-crm_api_1` før feilen.

## Driftsvindu og preflight

Prosjekteier bekreftet at ingen andre brukere eller manuelle skrivejobber var aktive. API ble stanset før førbevis/schema-apply. DB-forbindelseskontrollen viste bare kontrollens egen psql-forbindelse. Ingen nye credentials eller known_hosts-endringer.

Staging brukte Compose 1.29.2, eksisterende db/api/web og de dokumenterte DB/static/media-/safetymountene. Imports/exports manglet i API-containeren også ved fersk kontroll; ingen filer måtte flyttes. Ingen lagringsarkitektur ble innført.

Alle eksisterende `_ENABLED`-verdier og miljøfilchecksum ble bevart. Bilde-/PUBLIC-gatene var True; `IMPORT_IMAGE_DECISIONS_ENABLED=False`. Ingen flagg ble endret. Nytt oppstartsløp ble ikke brukt som read-only preflight.

## Backup og isolert restore

Installerte backup-/verify-/restore-/lib-/statusskript matchet repoets inspiserte versjoner. Eksisterende runbook ble brukt, uten reinstallasjon eller retensjonsendring.

| Gate | Arkiv | Resultat |
| --- | --- | --- |
| Predeploy | `kreative-norge-staging-20261013T161039Z` | Backup, full repository-verifikasjon og isolert PostgreSQL-restore bestått før endring. |
| Post-change | `kreative-norge-staging-20261013T161658Z` | Backup, full repository-verifikasjon og isolert PostgreSQL-restore bestått etter schema-apply og API-tilbakeføring. |

Post-change-manifestets database-dump SHA-256: `8965712489aa936747e09d28583d183989c7aa36949475c43bede5a3b77e9af5`; `pg_restore_verification=passed`, manifestcommit er målcommiten. Restorestatus og siste suksess refererte til samme post-arkiv. Runbookens restore gjenoppretter hele dumpen med exit-on-error og verifiserer forventede tabeller og representativ mediafil, uten live restore.

**Begrensning:** den ordinære backupjobbens prune-policy fjernet predeploy-arkivet etter den nyere post-backupen samme dag. Det var grønt og restore-verifisert før schema-apply, men predeploy-dumpchecksum ble ikke bevart separat og kunne ikke hentes etterpå. Gjeldende post-arkiv er verifisert tilgjengelig. Ingen policy ble endret, og ingen arkivgjenoppretting/undelete ble forsøkt. Pre-arkivet skal ikke oppgis som fortsatt tilgjengelig tilbakeføringsgrunnlag.

## Schema-apply og metadata

Ny image viste bare planlagte CRM-operasjoner for 0033: SharingDomain, nullable tenant-/profilbindinger og to assignmenttabeller. 0033 ble anvendt eksplisitt; deretter var generell migrate-plan tom. Ingen --fake eller ekstra datamigrering.

Read-only SQL bekreftet:

- tre nye tabeller, alle med 0 forretningsrader;
- `sharing_domain_id` nullable på Tenant/Organization/Person og 0 ikke-NULL-bindinger;
- obligatoriske assignment-targets/timestamps, PK-er, FK-er og unikhet på profil/tenant;
- nøyaktig én ny migrasjonshistorikkoppføring: crm/0033;
- forventet teknisk metadata: content types 29 → 32, permissions 116 → 128.

Historiske migrasjonshistorikkoppføringer og eksisterende tabeller ble bevart. Ingen CRM-seeding/backfill, publication-, telefon- eller bildestateendring. Django PROTECT i ny modellkode er ikke SQL ON DELETE PROTECT; ny modellkode kjører ennå ikke i API. Full_clean er strukturell validering og er ikke en autorisert writer eller databasegaranti for domain-likhet.

## Bevaringsbevis og safety

Før-/etterkontrollen brukte read-only repeatable-read SQL og stabile tabellfingerprints av sortert JSON for alle 31 eksisterende CRM-tabeller, inkludert M2M, historiske internal-tag-tabeller, import/export, telefoner og bilde-/release-/eventstate. Bare nye sharing_domain_id ble utelatt på de tre utvidede tabellene. Alle eksisterende radtall/fingerprints var identiske; dette er bevaringsbevis, ikke backup eller adversarial kryptografisk garanti.

Kontrollerte antall: 7 tenants, 128 aktører, 157 personer, 223 kontakter, 176 relasjoner, 10 assets, 13 rendition sets, 39 renditions, 4 releases, 12 release renditions og 11 review events. Importgrunnlag: 53 jobber, 1504 rader, 2624 beslutninger, 778 commitlogger; typed bildebeslutninger og eksportjobber 0.

Host-media og staticfilers aggregerte bytes/fingerprints, miljøchecksum og web-/DB-containeridentitet/image/mounts var uendret. Ingen original-/release-/ledgerreassosiering eller nye safetyevents. Safety var fortsatt READY med samme ledger-ID og event/read/anchor cursor 13.

Privat detaljevidens ligger på staginghost i `/root/phase6a1-20261013/`; repoet inneholder ingen rådata, credentials, filnavnlister eller individuelle radfingerprints.

## API-deployfeil og kontrollert tilbakeføring

Godkjent API-only `up --no-deps --no-build --force-recreate api` feilet med `KeyError: 'ContainerConfig'` i Compose 1.29.2s volume-merge. Ny API ble ikke startet. Videre deploy ble stoppet; ingen Compose-oppgradering, containerfjerning eller bred workaround.

Den bevarte gamle API-imagen viste tom migrasjonsplan også med 0033 anvendt. Original gammel container ble deretter startet som avgrenset API-tilbakeføring; ingen schema-reverse eller live DB-/mediarestore. Gammel image, mounts og miljø ble beholdt. Dette er kontrollert recovery, ikke vellykket deploy av målversjonen.

Siste read-only PUBLIC projection-audit av tilbakeført API viste 122 publiserte aktører, 1 asset og 121 system_fallback, med safety_unavailable=0 og scope_mismatch=0 (5 queries/3 authorize). Dette er fersk observasjon av gammel runtime, ikke verifikasjon av ny image.

Intern HTTP gjennom web-proxy ga frontend/session/PUBLIC API/PUBLIC HTML 200 og admin 302. Offentlig HTTPS-kontroll fra host ga 403 og brukes ikke som grønt eksternsmokebevis. Autorisert Editor-read og adminavgrensning for NY API ble ikke stagingverifisert etter kontrollert deploystopp. Ingen nye brukere, sessions eller businessfixtures ble opprettet for smoke.

## Stoppunkt og videre arbeid

- Kode: MERGET.
- Skjema: 0033 ANVENDT og teknisk schema-/bevaringskontroll bestått.
- Ny API-runtime: DEPLOY AVBRUTT; gammel API gjenopprettet.
- Full 6A.1-stagingverifikasjon: IKKE FULLFØRT.
- Shared funksjoner/backfill: IKKE AKTIVERT / IKKE UTFØRT.

Neste bestilling må avgrense recovery av API-deploy rundt den konkrete ContainerConfig-feilen, med gjeldende 0033-state beholdt. Ingen automatisk 6A.2 eller generalisert Compose-/driftsopprydding. Valgfritt testforbedringspunkt om isolerte tenant-slettetester består, uten ny gate eller kodeendring.

Denne evidensen og statusendringene er lokal, ustaget og ikke committet dokumentasjon. Ingen automatisk push/evidens-PR eller merge.

## Kontrollert API-recovery 2026-10-13

### Mandat, preflight og identiteter

Prosjekteier godkjente API-only recovery med kommandoavgrenset API 1.44, betinget nginx-reload, midlertidig vern mot ordinær prune, ikke-prunende pre/post-checkpoints, separat fil-/staticbevaring, API-only fallback og oppdatering av bare de seks eksisterende lokale dokumentene. Ingen ny schema-apply, global konfigurasjonsendring, build/pull, verktøyoppgradering, backfill eller delingsaktivering inngikk.

Fersk lokal main, origin/main, GitHub main og ren servercheckout matchet `b2d4725e8547f49c39256db188107f2ed29ed93c`. PR #75 var merget; main-CI `38419948624` var success på samme commit. Dette var kodebaseline, ikke stagingbevis. Lokal index var tom; SHA-256 ble registrert for de fem endrede dokumentene og den usporede evidensfilen før dokumentasjonsarbeidet. Det eksisterende innholdet og første utføringshistorikk er bevart.

| Identitet | Verifisert verdi |
| --- | --- |
| Gammel API-container | `d75bcd0511197de44f959bc6aaddb362dea6a0d5309d96682e70a08580d6bc1b`, navn `d75bcd051119_kreative-norge-crm_api_1` før recovery |
| Gammel API-image | `sha256:afc343cf6e200efe4d23116e9d991897d0de2e6ca9a76542b701696632c15371` |
| Bevart rollback-tag | `kreative-norge-crm_api:6a1-pre-b2d4725`, kontrollert mot gammel image-ID |
| Eksakt målimage og avsluttende image | `sha256:95e48c44bcdbb1e1afefb386115ab9feed8cd1c40c6f0a4a4a97e1dd612f3ed3` |
| Ny, kjørende API-container | `fe409ecdbfd98ed0d7187ceee35b40c387fe5e3c06268773ba400d574dd8384f`, navn `kreative-norge-crm_api_1` |
| Web-container, uendret | `2702237a3c406fe07156e7c564feeb9dffe6f29b8c93f443f07bdaf5f0a98dc0` |
| DB-container, uendret | `46606f0b5b9794bb7d4698026113d3d018c03dafb06da9a9332a6b44aefa68eb` |

Prosjekt `kreative-norge-crm`, nettverk `kreative-norge-crm_default`, API-alias `api` og alle mounts ble kontrollert. Målimage-referansen `kreative-norge-crm_api` pekte til eksakt målimage, også rett før recreate. Eksisterende buildlogg knyttet imaget til den tidligere builden; 132 Python-/requirementsfiler i en navngitt, nettverksisolert kontrollcontainer matchet serverens målcommit byte for byte. Bevarte package-lister for gammel/ny image var identiske. Ingen ny build/pull ble kjørt.

Samme installerte `/usr/bin/docker-compose` 1.29.2 og `/usr/bin/python3` ble brukt til klientkontrollen. Med `COMPOSE_API_VERSION=1.44` i målprosessens miljø valgte Compose-klientobjektet faktisk API 1.44 og kunne inspisere gammel images `ContainerConfig`/volumopplysninger. Engine var 29.1.3. Direkte Engine-curl fra diagnosen var derfor supplert med faktisk klientbevis. Variabelen ble ikke lagret globalt eller i `.env.staging`.

Diagnosen knyttet første deployavvik til installert Compose `service.py:1579`: volume-merge leser `ContainerConfig` fra gammel containers image etter stop/rename, før ny container opprettes. Feltet var til stede gjennom API 1.44 og borte gjennom 1.52 på denne hosten, i samsvar med [Docker sin dokumenterte API-endring](https://docs.docker.com/engine/deprecated/#container-and-containerconfig-fields-in-image-inspect). Backupgapet hadde en annen årsak: journalen bekreftet at post-jobbens ordinære prune fjernet det opprinnelige pre-arkivet kl. 16:17:07 UTC, med samme prefix/glob og dagsretensjon. Disse funnene er adskilt fra recoveryresultatet.

Privat rollback-override pekte til gammel image-ID og bare eksisterende Gunicorn-start, uten migrate/collectstatic. Sammenlignet sammenslått miljø, normaliserte mounts og nettverk var identiske med API-servicekontrakten. En første volumsammenligning slo ut på rekkefølge; sortert sammenligning bekreftet samme montering. Fallback ble klargjort, men ikke kjørt.

Målimage-kontrollcontaineren hadde eksplisitt Python-entrypoint, ingen live media/static-mounts, ingen dependency-start og intet API-alias. `PGOPTIONS` satte databaseforbindelser read-only. Generell `migrate --plan` var tom for alle apps. Ingen migrering eller collectstatic ble kjørt i kontrollcontaineren.

### Vernet vindu og bevaringsgrunnlag

Prosjekteier bekreftet på nytt at staging var uten andre brukere, importjobber og manuelle database-/backupjobber, og skulle holdes i ro. Codex var operatør med prosjekteier tilgjengelig i sessionen. Vinduet startet **17:32:46 UTC / 19:32:46 CEST**, med planlagt slutt innen 18:02:46 UTC. Generell backup-/verifyservice og felles backuplås var ledige.

Bare `kreative-norge-backup.timer` ble stanset midlertidig. Ingen disable/mask, retensjonsendring eller ordinær manuell prune-jobb ble utført. Safety-tjenester/-timere og deres separate repository var urørt. Eksisterende felles lås ble ervervet per backup-/arkiv-/restoreoperasjon, uten å holde den gjennom egne låskrevende jobber.

Gammel API var bekreftet stanset **17:32:56 UTC / 19:32:56 CEST**. Deretter var skrivefrysen teknisk etablert gjennom stanset API. Etter ny API-start var frysen operativ gjennom avtalt fravær av andre skrivere; ingen vedvarende teknisk writesperre ble innført.

Fersk førmåling ble tatt 17:33:19 UTC med samme 31-tabellers fingerprintdefinisjon som første utføring, explicit read-only SQL og repeatable-read for CRM-aggregatene. Radtall/fingerprints, media/static, miljøchecksum og safety matchet også tidligere bevarte grunnlag. Schema-/constraints-/metadata ble registrert separat. Ingen historisk førmåling ble rekonstruert fra dagens data.

Containerlagskontrollen brukte **Docker-export av den stoppede containeren**, ikke mislykket docker exec som fraværsbevis. `/app/imports` og `/app/exports` fantes ikke; ingen relevante endrede ikke-cachefiler ble funnet. Privat supplementmanifest dokumenterer dette. Ingen filer måtte gjeninnlegges i ny API.

Det faktisk monterte `kreative-norge-crm_django_static` ble bevart separat som privat tar med numeric owners, ACL-/xattr-støtte og metadata. Alle 169 filer ble lest tilbake og sammenlignet med kilden; eierskap/mode ble også kontrollert. Tar-SHA-256: `e398d8d01f9c22226ba55433426556f547dc78c94e73a2fc6236cc412e5a0e3a`. Dette er et separat hostbasert rollback-supplement; vanlig Borg-backup omfatter ikke static eller images. Gammel image, containerkonfigurasjon og nødvendig miljøgrunnlag ble også beholdt privat.

### Backupmetode og arkivbundne kvitteringer

Installert `backup.sh`, `lib.sh`, `status.py`, `verify.sh` og `restore-smoke.sh` matchet repoets kontrollerte versjoner. Privat engangskopi beholdt modulversjon, preflight, kryptering, repository-ID-/hostkontroll, lås, manifest, feilpropagering, status og cleanup. **Bare prune- og compact-blokkene ble fjernet fra backup.sh.** Ingen archive-prefix/glob eller testmodus ble endret. Diff og syntakskontroll er bevart privat.

- Installert backup.sh SHA-256: `f7b16ed72a20a46407b782ed3800eda02b76d3e0c11d7d3c46be98daff051304`.
- Engangskopi uten prune/compact SHA-256: `cc3c97566b85baa8c7070d99e694d88e669a01d0da98aece5b768e1c48b79052`.

| Checkpoint | Borg-ID | Dump-SHA-256 | Verifikasjon |
| --- | --- | --- | --- |
| Historisk post `kreative-norge-staging-20261013T161658Z` | `0d9e2f36c016550749f6d410b20a6d19deb494d8be6470e9bc79b003670726eb` | `8965712489aa936747e09d28583d183989c7aa36949475c43bede5a3b77e9af5` | Ferskt fjernlest navn/ID, manifest, dumpchecksum og medlemsdekning før runtimeendring. Historisk isolert restorebevis bevart separat. |
| Pre-recovery `kreative-norge-staging-20261013T173345Z` | `1385e8a236accfde4deef5dbddf8773e73e16f39aa1587a886fed5017501410e` | `76b864a2e16dca88f21f84269d8c4adef81a43bdd4ee19272a7ba6a6b01554f6` | Backup fullført 17:33:53 UTC; checksum lest tilbake; full verifikasjon bestått; isolert restore av samme arkiv bestått 17:35:11 UTC. |
| Post-recovery `kreative-norge-staging-20261013T173901Z` | `7363800cfe993f7267960b936a356120be119e948cc0abc447d8bab2ef9cd58f` | `d728d1281db19e1fa22ecafa1a3adf6dfbbc6d9974e9fce5c7f17302bd36a948` | Backup fullført 17:39:09 UTC; checksum lest tilbake; full verifikasjon bestått; isolert restore av samme arkiv bestått 17:40:23 UTC. |

Manifestene og faktiske medlemmer dekker private/public/public-delivery-media og serverkonfigurasjonsbundle. Imports/exports er eksplisitt ekskludert; separat kontroll av stoppet container beviser at de manglet. Pre-recovery gjelder allerede anvendt 0033 med gammel runtime; post-recovery gjelder 0033 med ny runtime. Manifestets Git-commit alene er ikke runtimebevis; checkpointet knyttes til separat container-/image-/førmåling.

Uendrede verify-/restore-skript valgte nyeste arkiv. Dette utvalget ble kontrollert mot forventet navn før hver kjøring, uten annen backup mellom create, verify og restore. Status-/restore-gate ble straks kopiert til separate arkivbundne kvitteringer. Restore brukte eksisterende full-dump/exit-on-error-rutine i isolert PostgreSQL uten nettverk, checksum-/tabell- og representativ mediakontroll. Ingen live restore eller safetyrebuild ble kjørt.

Lesing av den eksakte, checksum-verifiserte post-dumpen med `pg_restore` bekreftet alle tre nye schema-tabeller og nøyaktig én crm/0033-oppføring i dumpens migrasjonshistorikk. Denne lesingen gjenopprettet ikke data til live DB; den supplerer arkiv-/restoreidentiteten med direkte schemaevidens fra selve dumpen.

Den første supplerende TOC-strømproben traff `BrokenPipe` fordi pg_restore avsluttet innlesingen før Borg var ferdig med strømmen. Proben ble korrigert til å lese en privat, på nytt checksum-verifisert dumpfil og bestod. Dette var et løst leseproblem; de allerede beståtte backup-/restorestatusene og live DB ble ikke endret.

Dumpenes ulike SHA-256 er ikke en påvist CRM-endring: logiske fingerprints er identiske. Før vernet ble avsluttet, var historisk post og begge nye recoveryarkiver fortsatt til stede. Det opprinnelige `…161039Z` var fortsatt borte. Dets Borg-ID er historisk `70bd6284db30543d124483b0f6a2a467e256d8940cea83ab5879c6671252d97f`, **ikke dumpchecksum**. Manglende opprinnelig pre-dumpchecksum og prunet pre-0033-checkpoint består; de nye arkivene erstatter ikke disse historiske bevisene.

### Ett recreate-forsøk og ny runtime

Det ene godkjente forsøket kjørte 17:35:46 UTC / 19:35:46 CEST fra verifisert serverrepo:

```bash
COMPOSE_API_VERSION=1.44 docker-compose \
  -p kreative-norge-crm \
  -f docker-compose.staging.yml --env-file .env.staging \
  up -d --no-deps --no-build --force-recreate api
```

Exitstatus var 0. Ny container startet 17:35:46.795329812 UTC, fra eksakt målimage. Startup rapporterte ingen migrasjoner å anvende og **0 staticfiler kopiert / 169 uendret**. Ny runtime viste også tom generell plan og grønt Django system check. Ingen ny schema-apply, --fake, reverse eller CRM-write ble kjørt. Containeren hadde 0 restarter ved sluttkontroll.

API fikk fortsatt IP `172.18.0.3` og alias `api`. Intern webproxy og TLS-origin nådde ny API; nginx-reload var derfor **ikke nødvendig og ikke kjørt**. Lastet nginx-konfigurasjon var kontrollert. DB/web beholdt IDs, images og mounts. Gammel image/rollbackkonfigurasjon er bevart; original container skal ikke brukes som garantert fallback etter vellykket recreate.

Før-/etterkontroll, også etter HTTP-smoke, bekreftet:

- identiske fingerprints/radtall for alle 31 legacytabeller;
- uendret migrasjonshistorikk, schema, FK-/unikhets-/NOT NULL-kontrakter, 32 content types og 128 permissions;
- 0 rader i SharingDomain/OrganizationTenantAssignment/PersonTenantAssignment og 0 ikke-NULL domain-bindinger;
- identiske media/static-fingerprints, miljøchecksum og komplette API-environmentverdier; normaliserte mounts uendret;
- identisk safety-state/ledgergrunnlag, fortsatt ready, ingen nye recoveryutløste deny-/ledgerhendelser;
- alle observerte featureflagg uendret, inkludert `IMPORT_IMAGE_DECISIONS_ENABLED=False`.

### HTTP, autorisasjonsbegrensning og sluttstatus

På **ny container/målimage** ga både intern web og TLS-origin frontend, session, PUBLIC API/HTML og de to frontendressursene 200; admin ga forventet anonym redirect 302. Anonym Editor-tilgang ga 403. PUBLIC viste 122 aktører uten de nye domain-/assignmentfeltene. Read-only projection-audit viste 122 publiserte, 1 asset, 121 system_fallback, safety_unavailable=0 og scope_mismatch=0 (5 queries / 3 authorize).

Runtime-adminskjemaene for Tenant/Organization/Person utelukket domain, og de tre nye modellene var ikke adminregistrert. Dette var **runtime-kontraktkontroll**, ikke bevis på autentisert HTTP-/nettleserreise. Eksisterende prosjekteiersesjon var ikke tilgjengelig og nettleserautomatisering manglet aktiv flate. Ingen ny bruker, innlogging, rettighetsendring eller session ble opprettet. **Autorisert Editor-read og admin-HTTP gjenstår.**

Ekstern HTTPS ga fortsatt 403 med `cf-mitigated: challenge` fra Cloudflare. Intern/origin-success erstatter ikke ekstern smoke. Ingen Cloudflare-/Caddyendring, providersøk, write-smoke eller ny brukertestrunde ble startet. Denne uendrede begrensningen ga ingen grunn til blind rollback av frisk API.

Checkpointvernet og operativ skrivefrys ble avsluttet **17:41:33 UTC / 19:41:33 CEST**. Ingen kalenderkjøring var mistet under pausen; timerstart utløste ingen innhentingsjobb. Generell backup-timer var igjen **active/enabled**, service inactive, med neste observerte kjøring **2026-10-14 00:47:24 UTC / 02:47:24 CEST**. Ordinær retensjon gjelder igjen; arkivene har ikke permanent checkpointvern. Normal bruker-/jobbdrift kan gjenopptas.

Privat detaljevidens, bevaringskopier, skriptdiff, rollback-override, manifests/checksums og arkivbundne kvitteringer ligger på hosten i `/root/phase6a1-recovery-20261013T172703Z/` (0700; sensitive filer 0600). Første utføringsgrunnlag i `/root/phase6a1-20261013/` er bevart. Repoet inneholder bare sanitert lokal dokumentasjon.

**Historisk leveransestatus ved avsluttet recovery:** kode merget / 0033 anvendt historisk og beholdt / eksakt ny API-runtime deployet / bevaring og pre/post-restore grønne / **6A.1 delvis stagingverifisert**. Full teknisk verifikasjon er ikke erklært før manglende autoriserte/eksterne lesekontroller er avklart. Ingen backfill, deling, ny PUBLIC-cutover, image-home eller neste 6A-etappe. Alle seks dokumenter er lokale og ustagede; ingen commit, push, PR eller merge i recoveryøkten.


## Prosjekteiers lesebekreftelse mottatt 2026-10-13

### Bevisgrunnlag og gjennomført kontroll

Prosjekteier Fredrik Forssman meldte i ChatGPT 2026-10-13:

> lesekontrollen er gjennomført, alt fungerer fint og ser bra ut, ingen feilmeldinger

Bekreftelsen gjelder den avtalte, avgrensede lesekontrollen etter vanlig innlogging: session/innlogging, aktør- og personlister med ett eksisterende kort av hver type, relevante adminlister/-skjemaer uten lagring og PUBLIC HTML/API gjennom vanlig HTTPS-nettleser. Den samlede lesekontrollen er **prosjekteierbekreftet fullført uten feil**. Det er ikke bestilt eller gjennomført en ny manuell kontrollrunde som del av dokumentasjonspubliseringen.

De bekreftede rutene fra aktiv kode var `/api/auth/session/`, `/organizations`, `/people`, adminlistene/-skjemaene for Tenant/Organization/Person og `/public/actors/` / `/api/public/actors/`. Adminkontrollen gjaldt fortsatt utelatt `sharing_domain` og fravær av nye domain-/assignmentmodeller som admin-writers. Kontrollens påstand begrenses til eksisterende brukerscope; dette er ikke en ny negativ testmatrise for alle roller.

Datoen angir mottatt eierbekreftelse. Eksakt klokkeslett, nettleserversjon, HTTP-statuskoder, JSON-respons og rålogger er ikke oppgitt. Disse er ikke konstruert. Bekreftelsen er manuell eierobservasjon, ikke ny Codex-nettleserautomatisering, lokal testsuite, CI, stagingkjøring eller backup/restore.

### Review, historiske begrensninger og samlet sluttstatus

Den foregående skrivebeskyttede recoveryreviewen etterprøvde hele evidensdokumentet, seksfilsdiffen, private checkpoint-/restore-/bevaringskvitteringer, backupkopiens avgrensede diff og relevante runtime-/timer-/schema-/safetymetadata. Ingen kritiske eller blokkerende recoveryfunn ble funnet. De seks filene og index var uendret gjennom reviewen. Dokumentasjonen var publiseringsklar med daværende PARTIALLY VERIFIED; reviewen godkjente ikke de manglende HTTP-bevisene bort.

Det tidligere `authenticated:false`-skjermbildet beskrev en anonym sesjonsforespørsel, ikke en påvist innloggingsregresjon eller feil som nå er kodefikset. Recoveryens maskinelle eksterne Cloudflare-challenge består som historisk observasjon. Eierens fungerende vanlige HTTPS-nettlesertilgang betyr ikke at curl er retestet eller Cloudflare-regler endret. Nettleserflate/automatiske HTTP-kontroller er ikke kjørt på nytt av Codex i dokumentasjonsøkten.

**6A.1 = STAGING VERIFIED / OWNER-CONFIRMED**, utledet fra reviewede tekniske runtime-/schema-/bevarings-/backupbevis og den nye eierbekreftelsen. Statusen gjelder bare additiv skjemagrunnmur og API-runtime innen avtalt 6A.1-scope. Den historiske delvise verifikasjonen ved avsluttet recovery ovenfor er fortsatt korrekt for det tidspunktet.

Ingen backfill, shared leser/writer, assignmentlivssyklus, image-home, ny PUBLIC-cutover, kontakter/relasjoner, Places eller Import 2.0 er levert eller aktivert her. Hele 6A og ADR-011 er ikke ferdige; senere inventar-, data-, autorisasjons- og aktiveringsporter består. Det ikke-blokkerende testforbedringspunktet fra kode-PR-en er fortsatt et senere vurderingspunkt, uten ny kode eller gate.

Første deployavbrudd, prunet opprinnelig pre-arkiv og manglende historisk pre-dumpchecksum består. Nye arkivbundne checkpoints reparerer ikke disse historiske gapene eller garanterer dagens fjernarkivtilgjengelighet. Static/image-dekning og isolert restores faktiske omfang er fortsatt avgrenset som beskrevet ovenfor. Timer-/frysevinduets avslutning og neste observerte kjøring er daterte observasjoner, ikke nye serverkontroller i denne dokumentasjonsøkten.

### Dokumentasjonspublisering

Prosjekteier har bestilt publisering av akkurat de seks gjennomgåtte dokumentene på `docs/phase6a1-staging-evidence` som én draft dokumentasjons-PR mot main. Leveransen dokumenterer tidligere stagingarbeid og ny eierbekreftelse; den endrer ingen runtimekode, modeller, migrasjoner, konfigurasjon eller drift. Faktisk commit, push, PR-head, CI og eventuell senere merge følger GitHub og SESSION WRAP-UP. Historisk main-CI `38419948624` på runtimegrunnlaget erstatter ikke CI for dokumentasjons-PR-en. Merge krever separat bestilling.
