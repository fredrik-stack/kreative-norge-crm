# 6A.2 – første legacybackfill i staging

**Dato:** 2026-10-17. Klokkeslett er UTC (CEST = UTC+02:00).
**Status:** DATA APPLIED / COMMITTED_VERIFIED / TECHNICAL PRESERVATION VERIFIED /
POST-RESTORE VERIFIED / WINDOW CLOSED. STAGING VERIFIED / OWNER-CONFIRMED
innen avtalt backfill-/bevarings-/lesescope.
Ingen shared-aktivering eller ferdigmelding av hele 6A.

## Mandat og godkjenningsgrunnlag

Prosjekteier godkjente eksakt del A-pakke fra 2026-10-17 18:25:07–18:25:10 og
bestilte separat del B/C-apply. Ny bekreftelse: «Ja, staging er ledig og holdes i ro».
Codex var operatør gjennom autorisert CLI; audit-operatør-ID 1 ble revalidert som
aktiv staff/platform-superuser. Midlertidig slettebegrensning er akseptert.

- Lokal/fersk main: `d46be37cd25f7cbf97765391b6fa40748f951d2e`, PR #79 merget.
  Main-CI `39055839053` success 6/6 er eksisterende kode-/dokumentasjonsgrunnlag,
  ikke en ny CI-kjøring eller bevis for dagens data-apply.
- Ren servercheckout/kodebaseline: `63743441a173d2c1b4c71d9f9011b93fbadd2ca4`.
- Eksakt image: `sha256:bfdc9d281ddf1fab03152f9a85d12a4bfd70df5ae5f2506d3b9bb5ee743d34fb`.
- Samme API-container: `4192604eb5d726f700aeed7cb08ed37877ded6f23fca3c7053a61f336eba485c`.
- Database: `postgresql:7621672066239828005:crm_db`.
- Godkjent digest: `37f438ba15a4f8d9da8685d770fd7fc2b5e671dd5fe9400510fa599e5d8afd29`.
- Godkjent rapport SHA-256: `9f73dc0b42ddf730817808d1149bfe5e3184f32d2361e091910185a3388c4002`.

## Eksakt utvalg og endringer

Nytt domain: ID 1, slug `musikkontoret`, navn `Musikkontoret`.
Før apply fantes ingen domain/binding/assignment/batch. Fersk plan under frys og
umiddelbart før apply var identisk med godkjent rapport, inklusive profil-ID-er.

| Tenant-ID | Eksakt slug | Forventet navn | Organization | Person |
| --- | --- | --- | ---: | ---: |
| 1 | musikkontoretnord | Musikkontoret Nord | 121 | 147 |
| 2 | musikkontoretmxst | Musikkontoret MØST | 3 | 4 |
| 3 | musikkontoretbrak | Musikkontoret Brak | 4 | 6 |
| 6 | musikkontoretoks | Musikkontoret ØKS | 0 | 0 |
| 7 | musikkontoretsorf | Musikkontoret SØRF | 0 | 0 |
| 8 | musikkontoretstar | Musikkontoret STAR | 0 | 0 |
| 9 | musikkontorettempo | Musikkontoret Tempo | 0 | 0 |

578 semantiske endringer: ett domain, sju tenantbindinger, 285 profilbindinger og
285 assignments til profilenes egne legacytenants. Batchregistrering og kvittering
er separat nødvendig auditstate. Ingen ekstra tilknytning eller profilinnholdsendring.

## Frys og containerfiler

Begge ordinære backup-/verifytjenester var inaktive og ingen Borg-prosess kjørte.
Begge timere ble pauset etter bevaring av active/enabled-status. Bare API ble
stanset; Docker avsluttet ved 60 s stopptimeout (exit 137, OOMKilled=false).
Stans bekreftet 18:41:52.182894. Førmåling 18:42:13 omfattet eksisterende CRM-/auth,
metadata, miljø/mounts, media/static og safety. Ingen live skrive-/slettetest.

`/app/imports` og `/app/exports` var fraværende både i del A og ved Docker archive-
lesing av den faktisk stansede containeren. Entydig path-not-found ble bevart;
`docker exec` ble ikke brukt til å påstå fravær under stans. Ingen filer ble utelatt
og samtidig oppgitt som sikkerhetskopiert. API ble ikke startet for filuthenting.

Static ble sikret separat som lesbar tar med SHA-256
`e5432c94732f76c6f278c927f97def124ea72c6bd9fc664040e538d6d6e93496`.
Private supplements med fraværsbevis, static og kontrollgrunnlag ble inkludert som
`phase6a2-supplements.tar` i arkivets staged scope før checksums/Borg-create.
Post-supplementet inkluderer også PREPARED-/sluttmanifest, read-back og no-op-bevis.
Dette er avgrensede operasjonstillegg; image layers/static er fortsatt ikke normal
Borg-dekning. Konfigurert private/public/public-delivery-media inngår; media/default
mangler og er ikke oppgitt som sikkerhetskopiert.

## Arkivbundne pre/post-checkpoints

| Checkpoint | Arkiv-ID | Dump SHA-256 | Isolert restore bestått |
| --- | --- | --- | --- |
| `kreative-norge-staging-20261017T184245Z` (pre) | `925fe31029fd2396cf269df92000e0520ebb5c1eb4b9c7c8b6d7fcfd80249e1e` | `39ad16b88330a2b9cc61d83f2c831ebf827ea4cb91347d5e63e4980b8eb23180` | 18:43:38 |
| `kreative-norge-staging-20261017T184436Z` (post) | `ad91084b884e6675b8cc295ff45e8e892894c6bd998df0dc5300348a04dea4a1` | `113037ff3eeb3966a8c952823e9e07ab5ac8661ebae7f542b781e4c9f3b42e5a` | 18:45:29 |

Privat kopi av eksisterende backupjobb utelot prune/compact og erstattet container-
exec med eksplisitt supplement. Diff ble kontrollert før bruk. Separate arkivinfo,
medlemslister, manifest/checksums, backup-/verify-/restorestatus og gatekvitteringer
ble bevart per arkiv. Eksakt nyeste navn ble kontrollert før/etter verifikasjon og
restore uten mellomliggende backup. Begge fikk full repository-/archive-data-
verifikasjon og isolert PostgreSQL-restore med exit-on-error og mediakontroll.
Pre gjelder 0034 før backfill; post gjelder faktisk committet backfill.
Pre-arkivets samme ID ble kontrollert tilgjengelig før gjenopptatt ordinær drift.
Vernet er bare midlertidig; senere tilgjengelighet må kontrolleres ferskt.

## Én apply og uavhengig read-back

Batch: `phase6a2-staging-20261017-01`.
Varig hostmanifest: `/root/phase6a2-apply-20261017-01/manifest.json`.
CLI-/batchregistrert sti: `/phase6a2-evidence/manifest.json`, samme fil gjennom
bindmount av hostmappen på `/phase6a2-evidence`. Ingen pathbytte etter registrering.

Eksakt målimage ble kjørt i separat engangsprosess med eksplisitt Python-entrypoint,
eksisterende DB-nett, privat miljøfil og manifestmount. Ingen vanlig startup,
API-alias, live media/static-mount, build, pull eller deploy i applyprosessen.
Alle godkjente CLI-argumenter ble oppgitt. Eksisterende sorterte SHARE ROW EXCLUSIVE-
låser, 5 s timeout og fresh READ COMMITTED-plan under lås ble brukt uendret.

Én apply avsluttet 18:44:07.906800 med exit 0. Frisk separat read-back viste
COMMITTED_VERIFIED og `current_state_matches_receipt=true`. Manifestet før commit
er PREPARED; separat `.verified.json` og DB-kvittering er COMMITTED_VERIFIED.
De er ikke blandet sammen. Ingen ukjent commit, blind retry eller batch/path-omvei.
Ny separat read-only no-op-plan med faktisk domain-ID ga writes:0 og endringer:0;
dette var ikke replay eller en ny apply. Opprinnelig godkjent digest er planens
førtilstand og gjenbrukes ikke som digest for no-op-planen.

## Bevaring og faktisk post-restore

Read-back bekreftet identisk bevaringsgrunnlag før/etter. Uavhengige database-
fingerprints viste endring bare i de seks forventede strukturtabellene; øvrige
CRM-/authverdier, migrations, constraints og triggere var uendret. 176 relasjoner,
223 kontakter, publication, telefon, tidsstempler og eksisterende profilinnhold
ble bevart. Media/static, miljø/mounts, web/DB og safety/deny var uendret.

Privat restorekopi la til én read-only validator før successmarkør og cleanup.
Den isolerte post-databasen hadde network none, ingen eksponert port, og ble
kontrollert med REPEATABLE READ READ ONLY/ON_ERROR_STOP via psql. Validatoren
sammenlignet de 31 modelltabellene i tjenestens struktur-/bevaringssnapshot mot
live-postkvitteringen, eksakte domain-/tenant-/profilbindinger og assignmentpar,
batch/state/operator/miljø/manifeststi og hele kvitteringen samt fem aktive triggere.
Alle struktur-/bevaringshashverdier matchet. Ingen apply, feilinjeksjon eller
omskriving i restoredatabasen.

Historisk kvitteringsidentitet `postgresql:7621672066239828005:crm_db` ble bevart;
restoreinstansens separate identitet var
`postgresql:7697709790462840875:restore_smoke`. Dette er ikke en ny liveidentitet.
Resultat med arkiv/dump/containeridentitet ble lagret før cleanup. Privat cleanup
brukte rm -fv bare på egen restorecontainer og dens anonyme volum; ingen global prune.
Installerte backup-/restoreskript og permanent retensjon var checksum-uendret.

## Runtime, lesebevis og avslutning

Samme API startet 18:45:59.031264903 etter verifisert tom migrasjonsplan.
Startup rapporterte «No migrations to apply», 0 static kopiert / 169 uendret og
Gunicorn klar. Container/image/miljø/mounts/policy var uendret; 0 restarter.
Ny snapshot etter start var identisk med post-apply for database/media/static/safety.
TLS-origin GET: frontend/session/PUBLIC HTML/API 200, anonym admin 302 og anonym
Editor 403. Dette er maskinelle originbevis, ikke autentisert brukerbevis.

### Etterfølgende manuell eierbekreftelse mottatt 2026-10-17

Prosjekteier svarte «Lesekontroll fullført uten feil» på forespørselen om eksisterende
innlogget sesjon, Editor aktør-/personlister og eksisterende profiler, adminlister/
-skjema uten lagring samt PUBLIC HTML/API. Dette lukker det åpne lesepunktet etter
backfillen innen bestilt scope. Bekreftelsen kom etter avsluttet driftsvindu.
Eksakt tidspunkt for selve lesingen, nettleserversjon og HTTP-statuskoder ble ikke
oppgitt. Dette er manuell eierbekreftelse, ikke ny agentkjøring eller nye maskinelle
HTTP-bevis. Bekreftelsen fra 14. oktober er ikke brukt som dagens bevis.
Ingen ny apply, videre deling, livssyklus eller neste etappe er godkjent.

Teknisk frys opphørte ved samme API-containerstart 18:45:59. Operativ frys,
checkpointvern og driftsvindu ble avsluttet 18:48:51.472588 UTC / 20:48:51 CEST.
Begge timere var igjen active/enabled, backup-/verifytjenestene inaktive.
Neste observerte backup: 2026-10-18 00:53:03 UTC; verify: 02:39:42 UTC.
Ingen tidsstyrt kjøring ble mistet i vinduet. Siste snapshot før frigivelse bevarte
post-apply-state; pre-arkivets samme ID var fortsatt tilgjengelig.
Operatør meldte uttrykkelig at eier ikke lenger trengte holde staging i ro.
Vanlig retensjon gjelder igjen; ingen permanent checkpointbeskyttelse påstås.

## Leveransestatus og videre grenser

Privat detaljevidens: `/root/phase6a2-apply-20261017-01/` (0700, sensitive filer 0600).
Skrivebeskyttet review av de åtte dokumentfilene mot eksakt applyordre, private
bevis og ny eierbekreftelse fant ingen kritiske eller viktige funn. Alle filer
matchet reviewmanifestet før publisering; bare nødvendig leveransestatus er justert.
Dokumentasjonen er publisert og PR-reviewet uten blokkerende funn i
[PR #80](https://github.com/fredrik-stack/kreative-norge-crm/pull/80).
Kontrollert dokumentasjonsmerge er bestilt 2026-10-17; faktisk merge/head og CI
følger GitHub og SESSION WRAP-UP. Ingen ny drift eller applygodkjenning inngår.
Ingen ny lokal testsuite eller driftsoperasjon inngår i dokumentasjonspubliseringen.
Historisk 6A.1-evidens og datert 6A.2-schema/dry-run-evidens er bevart uendret.

Assigned profiler/berørte tenants har akseptert midlertidig slettebegrensning;
ingen assignmentfjerning eller livssyklusomvei. Nye legacyprofiler får fortsatt
NULL-domain og ingen skjult assignment; senere catch-up krever separat fersk plan.
Ingen shared reader/writer, overlays, capabilities, PUBLIC-cutover, image-home,
kontakter/Places/kart eller Import 2.0 er aktivert. Hele 6A er ikke ferdig.
Ingen schemaendring, live restore, deny-tilbagerulning eller neste etappe inngår.
