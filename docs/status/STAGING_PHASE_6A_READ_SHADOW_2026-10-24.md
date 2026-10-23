# 6A – operatørbasert PK-leseshadow i staging

**Avsluttet:** 2026-10-24, Europe/Oslo. **Resultat:** TEKNISK STAGINGVERIFISERT / FULL_EQUAL / VARIG SHADOWGATE AV.
Målingen ble utført 2026-10-23 kl. 23:59:51 CEST; postkontroller og publisering
fortsatte etter midnatt. Hele 6A og framtidig delt tilgang er ikke ferdig.

## Mandat og kodegrunnlag

Eierbestilling 2026-10-23 godkjente sammenhengende leveranse, operatørbasert
fullmåling og eksplisitt deldekning ved eventuelle NULL-profiler uten catch-up.
[Mandat og målekontrakt](../operations/DOMAIN_READ_SHADOW.md) viderefører ADR-011
migreringstrinn 6 og fullført 6A.3, uten ny produkt-/UX-runde.

- Arbeidsflyt/skills: [PR #82](https://github.com/fredrik-stack/kreative-norge-crm/pull/82), ordinær merge `b695ab2f92dd1c8832cbf9a88cd67f0b3145e3a3`; [main-CI 40027171415](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/40027171415), success 6/6.
- Kode: [PR #83](https://github.com/fredrik-stack/kreative-norge-crm/pull/83), separat fullreview og relevante re-review uten gjenstående kritiske/viktige funn på base `b695ab2f92dd1c8832cbf9a88cd67f0b3145e3a3` / head `8cc8e98361f0e379706f113ae2205ea2f1d355f0`. [Reviewresultat](https://github.com/fredrik-stack/kreative-norge-crm/pull/83#issuecomment-6375275263).
- Ordinær kode-merge og faktisk deployet baseline: `ad876846275ff46b3d2827a9507598ecf3ba6e1d`. [PR-CI 40028354012](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/40028354012) og [main-CI 40028992875](https://github.com/fredrik-stack/kreative-norge-crm/actions/runs/40028992875), begge success 6/6.
- Lokal isolert Docker/PostgreSQL 16: 22 målrettede shadowtester og 130 relevante eksisterende regresjoner bestod. Ingen migrasjonsendringer. CLI-reviewfunn rundt traceback og argumentforkortelser ble rettet, retestet og re-reviewet før merge.

Før deploy var stagingcheckout ren på `63743441a173d2c1b4c71d9f9011b93fbadd2ca4`.
Hele runtimeforskjellen ble kontrollert: ny sammenligningstjeneste, kommando,
testfil og én default-off setting. Aktive views, permissions, serializers,
modeller, migrasjoner, frontend, dependencies og Compose-kontrakt var urørt.
Gamle API-kildefiler og alle 150 kontrollerte kildefiler i målimage/kjørende ny
API samsvarte med sine respektive Git-baseliner. Pakkenavn-/versjonsfingerprint
var uendret. Kodereferansen i målerapporten er dermed operativt bundet til
faktisk reviewet/deployet kode, utover CLI-ens formatkontroll.

## Preflight, tilbakeføring og kontrollert recreate

Fersk read-only preflight bekreftet database
`postgresql:7621672066239828005:crm_db`, tom migrasjonsplan, forventet gammel
API/image, aktive/aktiverte backup-timere og inaktive backup-/verifyservices.
`/app/imports` og `/app/exports` fantes ikke; ingen slike filer gikk tapt ved
recreate. Gamle image, privat miljø-/containerkonfigurasjon og kontrollert,
tar-verifisert statickopi ble beholdt som tilbakeføringsgrunnlag.

Første utføring stoppet før gammel container ble fjernet: Docker TERM til
shell-PID 1 ble etterfulgt av KILL og exit 137. Gammel API ble umiddelbart startet
igjen og begge timere gjenopprettet. Fersk kontroll viste samme API/image,
CRM-radantall, PostgreSQL-snapshot og media. Ingen shadowmåling var forsøkt.

Diagnose bekreftet Gunicorn-master under shell-PID 1. Den korrigerte utføringen
brukte ny pre-backup, midlertidig `restart=no` på bare gammel API, og målrettet
TERM til verifisert Gunicorn-master. Containeren avsluttet rent med exit 0.
Deretter ble bare API fjernet/opprettet; ny API beholder `unless-stopped`.
Gunicorn ble startet direkte, uten migrate/collectstatic. Web fikk bare
konfigurasjonstest og nginx-reload for ny API-upstream; web/DB ble ikke rekreert.
Docker 29.1.3 / Compose 1.29.2 med kommandoavgrenset API 1.44 ble beholdt.
Ingen infrastruktur-/Compose-oppgradering, generell prune eller live restore.

- Gammelt image: `sha256:bfdc9d281ddf1fab03152f9a85d12a4bfd70df5ae5f2506d3b9bb5ee743d34fb`.
- Nytt image: `sha256:3928cec7d7b3795049cabee8485af46bb88944e5ad644d425041ad7096f794d5`.
- Ny API: `9fcfdb1a818a90ff9f27ad5d656385f11c1387fe561a1a408bf6071f22b0d1b9`, running med restart count 0 ved sluttkontroll.

## Arkivbundne checkpoints

Midlertidig privat kopi av eksisterende backupjobb utelot bare prune/compact.
Den private restorekopien fjernet også egne anonyme volum ved cleanup av sin
isolerte restorecontainer. Installerte skript var uendret ved sluttkontroll.
Ingen generell volum-/imageopprydding ble utført; ingen restorevolumer ble etterlatt.

| Checkpoint | Arkiv | Arkiv-ID | Dump SHA-256 |
| --- | --- | --- | --- |
| Pre | `kreative-norge-staging-20261023T215845Z` | `afab86bf168801b36edcae9ec0cd8581eb3bc542f6a8b49db067150ebdb51b1f` | `e08a45de5d12d0c576bdcce98ec7b3b57d57779ea13d977f9b1d4006978682db` |
| Post | `kreative-norge-staging-20261023T215955Z` | `20ab3cef730a194cb24190ac1f9c4a5e0424a68770c7196ea8d2c19fd38ab718` | `e9e42eaddba0b6928ebaa7842b92351e787d068f8d2ca8fc81446e1205188ef1` |

Begge checkpoints hadde full repository-/dataverifikasjon og isolert PostgreSQL-
restore med eksisterende tabell-/mediakontroller. Arkivnavn/ID og manifestets
dumpchecksum ble lest fra hvert konkret arkiv; samme arkiv ble kontrollert før
og etter isolert restore. Pre-arkivets ID ble lest tilbake etter post-checkpoint.
Dette er backup-/restorebevis, ikke profilvise innholdsfingerprints. Images og
statickopi er separat lokalt tilbakeføringsgrunnlag, ikke påstått Borg-dekning.
Begge eksisterende timere ble gjenopprettet til active/enabled.

## Faktisk måling

Eksakt domain `1 / musikkontoret / Musikkontoret` og hele tenantsettet nedenfor
ble revalidert i målesnapshotet. Én gate-av-kjøring ga INCOMPLETE/GATE_DISABLED,
exit 4, før shadowlesing. Deretter ble gaten satt til True bare i én avgrenset
operatørprosess. Denne ene målingen ga **FULL_EQUAL / exit 0**, med alle 14
sammenligninger fullført og ingen strukturavvik.

- Snapshot: `25160:25160:`.
- UTC: `2026-10-23T21:59:51.060388+00:00`–`2026-10-23T21:59:51.079092+00:00`.
- Samme forbindelse, `REPEATABLE READ READ ONLY`; snapshot/isolation/read-only ble kontrollert ved start/slutt. Statement timeout 30 s / lock timeout 2 s var transaksjonslokale.
- Eksakte L/A- og B/A-settforskjeller ble beregnet i minnet og var tomme. Tellingene nedenfor er aggregert evidens, ikke grunnlaget alene for likhetskonklusjonen.

| Tenant ID / slug | Organization L=B=A | Person L=B=A | U, begge modeller | Settforskjeller, begge modeller |
| --- | ---: | ---: | ---: | ---: |
| 1 / musikkontoretnord | 121 | 147 | 0 | 0 |
| 2 / musikkontoretmxst | 3 | 4 | 0 | 0 |
| 3 / musikkontoretbrak | 4 | 6 | 0 | 0 |
| 6 / musikkontoretoks | 0 | 0 | 0 | 0 |
| 7 / musikkontoretsorf | 0 | 0 | 0 | 0 |
| 8 / musikkontoretstar | 0 | 0 | 0 | 0 |
| 9 / musikkontorettempo | 0 | 0 | 0 | 0 |

Totalt 128 Organization og 157 Person, med 285 egne legacyassignments.
Alle `full_equal`/`bound_equal` var true. Alle differansetellinger, NULL-tellinger
og strukturelle avvik var null. Uavklarte kandidatpar fra 6A.3 beholdes som
separate PK-er. De to telefonavvikene er ikke diagnostisert eller rettet.
Ingen deduplisering, assignment, backfill/catch-up eller ombinding ble utført.

## Sluttstate og bevaring

`SHARING_DOMAIN_SHADOW_ENABLED` var fortsatt usatt i container-/varig miljø,
med effektiv Django-verdi False etter målingen. Miljøfilen var byteidentisk,
containerens miljø/mounts og de åtte eksisterende bilde-/importflaggene var
uendret. Ingen permanent shadowaktivering eller request-hook finnes.

Alle kontrollerte CRM-tabellers radantall var uendret gjennom deploy/måling;
blant annet 176 relasjoner, 223 kontakter, 4 releases og 285 assignments.
Dette er radantallsbevaring, ikke full innholds-/feltfingerprinting.
Private originaler (10 filer), artifacts (39), delivery (9) og static hadde
identiske samlede innholds-/pathfingerprints. DB/web beholdt container-ID,
image og restart count. Safety forble READY med samme ledger-ID og
event-/read-/anchorcursor 13; ingen ledger-/deny-write ble utført.
Sluttkontrollen viste fortsatt tom migrasjonsplan og API restart count 0.

| Teknisk lokal HTTP-kontroll før/etter | Status |
| --- | ---: |
| Frontend `/` | 200 |
| `/api/auth/session/` | 200 |
| PUBLIC API og PUBLIC HTML | 200 |
| Anonym admin | 302 til innlogging |
| Anonym tenant-API | 403 |

Autorisert Editor list for alle 14 kombinasjoner og detail der profiler fantes
ga 200 og forventede tellinger i kjørende ny kode. Denne separate kontrollen
brukte eksisterende aktiv plattformbruker og én read-only-transaksjon via
DRFs requestfactory/force-authentication, uten innlogging eller sessionskriving.
Den er teknisk backendbevis, ikke ny manuell browser-/sessionloginverifikasjon.
Ekstern HTTPS/browser er ikke nytestet; ingen UI-/autentiseringsendring inngår.

PK-samsvar beviser ikke identisk serialisert API-respons, relasjonsinnhold,
kontaktpublisering, sortering eller paginering for en framtidig assignmentleser.
Det beviser heller ikke shared autorisasjon, kandidatidentitet eller hele ADR-011.
Legacylesing er fortsatt autoritativ. Ingen ny brukertestrunde eller neste
produktetappe er startet. UX v6 revisjon 4/O-24, godkjent 5E og Google Maps-
aktørkart i Editor/PUBLIC består.

## Publisering og stoppunkt

Sanitert måle-/driftsevidens og status publiseres som separat dokumentasjons-PR
under samme mandat, med separat skrivebeskyttet review og ordinær merge/CI.
Faktisk publiseringsstatus følger GitHub; dokumentasjonsmerge utløser ingen
ny deploy. Deployet kode/image ovenfor skal skilles fra senere docs-only main.
Ingen rå person-/kontaktdata, profil-PK-er/-hashverdier, credentials eller private
detaljpaths inngår i rapporten. Det avgrensede tekniske stagingstoppunktet er oppfylt.
