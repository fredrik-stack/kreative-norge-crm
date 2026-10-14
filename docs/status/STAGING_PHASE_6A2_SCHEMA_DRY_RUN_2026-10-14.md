# 6A.2 – API/schema og read-only dry-run i staging

**Dato:** 2026-10-14. Alle klokkeslett nedenfor er UTC (CEST = UTC+02:00).
**Status:** API DEPLOYED / 0034 APPLIED / PRESERVATION VERIFIED / DRY-RUN PRODUCED.
**Bevisnivå:** STAGING VERIFIED / OWNER-CONFIRMED innen avtalt API-/schema-/
lesescope, basert på tekniske bevis og etterfølgende manuell eierbekreftelse.
Ekstern maskinell HTTPS møter Cloudflare-challenge; dette er adskilt fra eiers
manuelle lesebevis. Ingen reell backfill eller delingsaktivering.

## Mandat og baseline

Prosjekteier godkjente separat API-/schemaleveranse, teknisk bevaringskontroll,
beskyttede pre/post-checkpoints med isolert restore og fersk dry-run. Stopp før
`--apply`. Eier bekreftet at staging var ledig og andre skrivere/backupjobber
skulle holdes i ro. Codex var operatør. Ingen commit/push/PR/merge inngår.

- Mål/main: `63743441a173d2c1b4c71d9f9011b93fbadd2ca4`, PR #77/#78 merget.
- Main-CI `38630391049`: success på eksakt målcommit; 609 tester og 6/6 jobber.
  Dette er tidligere CI, ikke nye lokale tester i driftsøkten.
- Servercheckout før levering: ren `b2d4725e8547f49c39256db188107f2ed29ed93c`.
- Gammel API: `fe409ecdbfd9`, image
  `sha256:95e48c44bcdbb1e1afefb386115ab9feed8cd1c40c6f0a4a4a97e1dd612f3ed3`.
- Web `2702237a3c40`, DB `46606f0b5b97`; IDs/images/mounts beholdt.
- Fersk førkontroll: 0033 anvendt, 0034/batchtabell manglet; domains,
  assignments og alle domainbindinger var tomme/NULL.
- Databaseidentitet: `postgresql:7621672066239828005:crm_db`.

Docker Engine/client 29.1.3 og Compose 1.29.2 ble revalidert. Faktisk Compose
CLI-klient valgte API 1.44 ved kommandoavgrenset override og kunne lese gammel
images `ContainerConfig`; ved API 1.52 manglet feltet. Ingen global konfigurasjon,
`.env`, Docker-/Compose-oppgradering eller verktøyinstallasjon ble gjort.

## Vern, førmåling og tilbakeføringsgrunnlag

Begge eksisterende backup-timere var active/enabled; begge tjenester var
inaktive og ingen Borg-prosess kjørte. Timerne ble pauset. En privat kopi av
installert backupjobb og hjelpere ble brukt; eneste skriptdiff fjernet
prune/compact-blokken. Installert backupjobb var checksum-identisk ved avslutning.
Ingen prune/compact ble kjørt. Eksklusivt eiervindu og pause av ordinære utløsere
beskyttet checkpointene under leveransen; dette er ikke permanent arkivvern.

Gammel image er bevart som `kreative-norge-crm_api:6a2-pre-6374344`, med privat
rollback-override for bare Gunicorn uten migrate/collectstatic. Nødvendig miljø,
service-/mountkontrakt og imageidentitet er bevart privat. Fravær av
`/app/imports` og `/app/exports` ble kontrollert før gammel container ble fjernet.
Staticvolumet ble sikret i separat checksum-/tar-verifisert hostkopi:
`c4f1d5ce83fdbc9803d228e8f81ca8809d59b72ed4b56f7a85817ac85eb2931c`.
Dette er et separat supplement; Docker-image layers og static er ikke ordinær
Borg-dekning. Konfigurerte private/public/public-delivery-bildemedia inngår.
Konfigurert media/default manglet og skal ikke oppgis som sikkerhetskopiert.

API ble stanset før endelig førmåling og checkpoint. Konsistent eksplisitt
REPEATABLE READ READ ONLY-førmåling 20:41:06 omfattet 34 eksisterende CRM-tabeller
og auth-tabeller, hele gamle kolonneinnholdet/M2M, migrations-/schema-/constraint-
metadata, tenantinventar, media/static, miljø/mounts og safety. Bare aggregater
og fingerprints er brukt i sanitert evidens; rå persondata er ikke publisert.

## Arkivbundne checkpoints

| Checkpoint | Arkiv-ID | Dump SHA-256 | Isolert restore bestått |
| --- | --- | --- | --- |
| `kreative-norge-staging-20261014T204146Z` (pre) | `708bec26865e0723a7633d231ee2f57802b308d4095522037d992126c39ef51e` | `557781bb691ee69ec9961cf546611def5bfc63525b88030859951ff78c98670c` | 20:42:25 |
| `kreative-norge-staging-20261014T204742Z` (post) | `e22bf49732ae8285c1720cc2741d9ebc4d2e3f488006345c185ec009a59ff0f9` | `12992ac5fa8775e58cc6ad34446e41703cb88b55bfd311bf356ad2df13f25308` | 20:48:21 |

Begge hadde full verifikasjon og eksisterende isolert PostgreSQL-restore med
exit-on-error, tabell- og representativ mediakontroll. Forventet arkivnavn ble
kontrollert før/etter verify/restore uten mellomliggende backup. Manifest,
checksums, medlemsliste, arkivinfo og separate status-/restorekvitteringer er
bevart per arkiv; global statusfil alene er ikke beviset. Pre gjelder 0033/gammel
runtime; post gjelder 0034/ny runtime uten backfill. Pre-arkivets samme ID ble
lest tilbake før checkpointvernet ble avsluttet. Ingen live restore ble kjørt.

Restorecontainerne ble fjernet av eksisterende rutine. Den rutinen etterlot to
anonyme DB-volumer; Docker-events knyttet dem entydig til denne operasjonens to
restorecontainere. Bare disse to umonterte volumene ble deretter fjernet etter
kontroll av fravær av containerreferanser. Ingen generell volume-/image-prune.

Disse nye bevisene reparerer ikke det historiske prunede pre-0033-arkivet eller
manglende dumpchecksum fra 6A.1. Vanlig retensjon gjelder igjen etter vinduet;
arkivenes senere tilgjengelighet må kontrolleres ferskt.

## Bygg, preflight og ett API-recreate

Servercheckout ble oppdatert til eksakt målcommit; bare API ble bygget.
Målimage: `sha256:bfdc9d281ddf1fab03152f9a85d12a4bfd70df5ae5f2506d3b9bb5ee743d34fb`.
177 tracked Python-/requirementsfiler i image matchet målcheckout byte for byte.

En kortvarig kontrollcontainer brukte eksplisitt Python-entrypoint, ingen
API-alias eller live media/static-mounts og read-only DB-forbindelse. Første
forsøk med helt read-only rot manglet tempkatalog og stoppet før DB-kontrollen;
ny kontroll fikk bare privat `/tmp`-tmpfs. Eksakt samlet plan var kun 0034,
og Django system check var grønn. Ingen migrate/collectstatic i preflight.

Privat API-only override pinnet målimage og satte midlertidig restart `no`.
Normalisert Compose-kontrakt viste ellers uendret miljø, kommando, mounts og
nettverk; web/DB var uendret. En innledende streng sammenligning avviste bare
volumrekkefølge; normalisert sammenligning bestod før recreate.

Ett `up -d --no-deps --no-build --force-recreate api` med API 1.44 lyktes.
Ny container: `4192604eb5d726f700aeed7cb08ed37877ded6f23fca3c7053a61f336eba485c`.
Start: 20:45:23.406750862. Startup anvendte 0034 OK, deretter collectstatic:
0 kopiert / 169 uendret. Gunicorn startet. Ingen ekstra schema-apply, fake,
reverse, retry eller fallback var nødvendig. Opprinnelig `unless-stopped`
restartpolicy ble gjenopprettet uten ny recreate; 0 restarter ved sluttkontroll.

## Teknisk etterkontroll

- 0033 beholdt, 0034 anvendt, generell migrasjonsplan tom; system check grønn.
- Batchtabell og `legacy_domain_batch_identity_unique` finnes; fem forventede
  domain-/assignmenttriggere er aktive. Ingen domains/bindinger/assignments/batcher.
- Samtlige 34 eksisterende CRM-tabellers antall/hele innhold og gamle auth-rader
  var uendret. Bare forventet migrasjon/schema og ny batchmodells content type
  med fire permissions ble lagt til; eksisterende brukere/roller/rettigheter bevart.
- Media: private 10 filer / 4 947 485 bytes, public 39 / 2 907 961,
  public-delivery 9 / 683 062; static 169 / 3 534 818. Innholdsfingerprints uendret.
- Miljøfil, komplette API-miljøverdier og normaliserte mounts uendret. Web/DB
  beholdt IDs/images/mounts. Ingen featureflagendring; importbildeflagget fortsatt av.
- Safety-tabellenes fingerprints og deny-state uendret, samme ledger samt
  event/read-/anchor-cursor 13. Ingen rebuild, nyere deny-tilbakeføring eller ny event.
- TLS-origin: frontend, session, PUBLIC API/HTML 200; anonym admin 302 og Editor
  403. Intern HTTP har korrekt HTTPS-redirect. Ny API nås; nginx-reload ikke nødvendig.
- Ekstern maskinell HTTPS gir Cloudflare 403 med `cf-mitigated: challenge`.
  Dette er ikke et bestått eksternt brukerbevis. Eksisterende autentisert
  Editor-/admin-HTTP/eiers lesekontroll var da uavklart. Ingen ny bruker,
  innlogging, write-/delete-/feilinjeksjons-/reverse-test eller formell brukertest.

### Etterfølgende manuell eierbekreftelse mottatt 2026-10-14

Prosjekteier bekreftet «Lesekontroll fullført uten feil» på den avgrensede
forespørselen om eksisterende innlogget sesjon, Editor aktør-/personlister og
eksisterende profiler, adminlister/-skjema uten lagring samt PUBLIC HTML/API.
Dette fyller det åpne lesebeviset innen bestilt scope. Eksakt utføringstidspunkt,
nettleser-/klientversjon og HTTP-statuskoder ble ikke oppgitt; dette er manuell
eierbekreftelse, ikke en ny agentkjøring eller nye maskinelle eksterne HTTP-bevis.
Bekreftelsen autoriserer ikke mapping, dry-run-plan, backfill eller deling.

## Fersk dry-run – produsert, ikke eiergodkjent

Kommandoen ble først kjørt på ny kode med 0034, uten `--apply`, med
`PGOPTIONS=-c default_transaction_read_only=on`. Rapport 20:47:14:

- Miljø i operatørkvitteringen: staging; database
  `postgresql:7621672066239828005:crm_db`.
- Foreslått ny domain: `id:null`, slug `musikkontoret`, navn `Musikkontoret`.
  Ingen eksisterende domain å gjenbruke ved denne kontrollen.
- Digest: `37f438ba15a4f8d9da8685d770fd7fc2b5e671dd5fe9400510fa599e5d8afd29`.
- Rapport SHA-256: `9f73dc0b42ddf730817808d1149bfe5e3184f32d2361e091910185a3388c4002`.

| Tenant-ID | Eksakt slug | Forventet navn | Organization | Person |
| --- | --- | --- | ---: | ---: |
| 1 | musikkontoretnord | Musikkontoret Nord | 121 | 147 |
| 2 | musikkontoretmxst | Musikkontoret MØST | 3 | 4 |
| 3 | musikkontoretbrak | Musikkontoret Brak | 4 | 6 |
| 6 | musikkontoretoks | Musikkontoret ØKS | 0 | 0 |
| 7 | musikkontoretsorf | Musikkontoret SØRF | 0 | 0 |
| 8 | musikkontoretstar | Musikkontoret STAR | 0 | 0 |
| 9 | musikkontorettempo | Musikkontoret Tempo | 0 | 0 |

128 aktører/157 personer; 176 relasjoner og 223 kontakter bevart. Ingen
relasjons-/kontakt-/tag-scopekonflikter. 578 foreslåtte endringer: ett domain,
sju tenantbindinger, 285 profilbindinger og 285 egne legacyassignments.
Rapporten sier `writes:0`; etterfølgende snapshot var identisk, batchantall 0.
Ingenting av dette er anvendt. Ved senere autorisert apply forventes null
restendringer, nøyaktig én egen assignment per profil og bevart legacyinnhold.

## Vindu, avvik og gjenstående porter

Teknisk frys var stanset API frem til ny containerstart 20:45:23; deretter
operativ frys via eiers avtalte fravær av andre skrivere. Operativ frys og
midlertidig checkpointvern avsluttet 20:49:47. Begge timere igjen active/enabled,
backup-/verifyservice inaktive; neste observerte backup 2026-10-15 00:37:58 UTC.
Ingen tidsstyrt kjøring var mistet under vinduet. API-policy er normal igjen.

En avsluttende arkivleseprobe manglet først backup-preflightens dedikerte
SSH-kontekst og traff host-key-avvisning. Lesingen bestod med ordinær preflight;
ingen nøkkel/known_hosts eller sikkerhetskontroll ble endret eller omgått.

Privat detaljevidens ligger i `/root/phase6a2-staging-20261014T2040Z/` (0700,
sensitive filer 0600). Repoet inneholder bare sanitert evidens. Ingen ny CI eller
lokal syntetisk testsuite ble kjørt i driftsøkten; tidligere lokale/CI-kontraktbevis
gjenbrukes for negative write-/delete-/reversetester.

Skrivebeskyttet review av de åtte dokumentfilene og private driftsbevis fant
ingen kritiske eller viktige funn. Publisering som én draft PR er bestilt på
`docs/phase6a2-staging-evidence`; faktisk commit/push, PR/head og ny ordinær CI
følger GitHub og SESSION WRAP-UP. Publiseringen endrer bare nødvendig
review-/leveransestatus, uten ny drift eller utvidet applygodkjenning.

**Stoppunkt:** kode merget / API deployet / 0034 anvendt / bevaring og checkpoint-
restore verifisert / dry-run produsert / autorisert lesekontroll eierbekreftet /
dry-run ikke eiergodkjent / data-apply ikke utført. Hele 6A er ikke ferdig.

Senere apply krever uttrykkelig godkjenning av fersk eksakt mapping, database,
utvalg/digest og separat applyordre, nytt gyldig drifts-/backupgrunnlag,
unik batch/operator/kodebaseline og varig privat manifeststi. Nåværende plan kan
bli stale ved normal drift. Ukjent COMMIT avklares gjennom read-back fra frisk
forbindelse, aldri blind retry. Midlertidig slettebegrensning og alle senere
delings-/livssyklusporter består. Ingen deling eller neste etappe er aktivert.
