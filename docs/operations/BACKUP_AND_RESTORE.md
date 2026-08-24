# Backup og restore

**Status:** ACTIVE

**Arkitektur:** [ADR-008](../decisions/ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md)

Denne runbooken er den autoritative driftsprosedyren for kryptert PostgreSQL-, fil- og konfigurasjonsbackup til Hetzner Storage Box. Eksemplene inneholder bare plassholdere. Ikke lim credentials, passord, tokens, private nøkler eller `.env`-verdier i terminalutskrift, Git, PR eller chat.

## 1. Statusbetydning

| Status | Betydning |
| --- | --- |
| ACTIVE | Første backup og isolert restore er grønne, recovery-custody og Console-steg er kontrollert, timerne kjører, og intern bilde-runtime er host-persistent og backup-/restore-verifisert |
| PREPARED | Repoets kode, maler og dokumentasjon finnes, men ekstern kjede er ikke aktiv |
| MANUAL REQUIRED | Prosjekteier må gjøre en kontroll i Hetzner Console eller organisasjonens passordlager |
| NOT IMPLEMENTED | Host-persistent default storage for import, eksport og rapporter finnes ikke |

Nåstatus er **ACTIVE**. Den skrivebeskyttede [stagingbaselinen 2026-08-01](../status/STAGING_BACKUP_BASELINE_2026-08-01.md) ble fulgt av kontrollert [aktivering 2026-08-02](../status/STAGING_BACKUP_ACTIVATION_2026-08-02.md). Separat Storage Box, kryptert Borg-repository, recovery-custody for minst to ansvarlige, første backup, full repository-check, isolert restore av samme arkiv, Console-gatene og timeraktiveringen er verifisert grønne.

Første backup brukte 8 sekunder, og isolert restore-smoke brukte 8,7 sekunder. Foreløpig RPO er inntil omtrent 24 timer pluss randomisert timerforsinkelse og eventuell operativ forsinkelse. Restore-smoke-tiden er ikke et løfte om full katastrofe-RTO.

## 2. Beskyttet innhold

Den nattlige jobben tar:

- en konsistent PostgreSQL custom-format dump, verifisert med `pg_restore --list`
- API-containerens `/app/imports` og `/app/exports` når de finnes
- eksplisitt konfigurerte host-mediaområder når de finnes
- aktiv Compose-/environmentfil, Caddy-konfigurasjon, backupkonfigurasjon og backup-units når de finnes
- et tekstmanifest og SHA-256-checksums

Backupen tar ikke private SSH-nøkler, Borg recovery-secret, eksportert repositorynøkkel, hele `/etc`, home-kataloger, rått live PostgreSQL-volume, image layers, caches, staticfiles, `node_modules`, Python-cache eller store logger. `export-recovery-key` avviser destinasjoner i applikasjonsrepo, backup-state, beskyttede mediaområder og allowlistede serverkonfigurasjonsfiler. Destinasjonsparent må være eid av operatøren og ikke group/world-writable, og sluttfilen opprettes atomisk uten overskriving; directory- og symlinktarget avvises.

Den aktive allowlisten inneholder `/srv/kreative-norge/media/private`, `/srv/kreative-norge/media/public` og fra 2026-08-23 `/srv/kreative-norge/media/public-delivery`. Første stagingaktivering fulgte den kontrollerte PNG-proben i [stagingrunbooken](../../deploy/staging/README.md#10-image-persistence-and-activation-gate): proben ble skrevet gjennom begge interne Django-aliasene, funnet med samme checksum på hosten, lest etter API-recreate, beholdt gjennom manuell backup og isolert restore og deretter fjernet eksakt. Se [datert aktiveringsevidens](../status/STAGING_IMAGE_RUNTIME_ACTIVATION_2026-08-10.md). Delivery-rooten fikk en separat tilsvarende persistence-/backup-/restoregate i [3E.1B-stagingrapporten](../status/STAGING_PHASE_3E1B_FOUNDATION_2026-08-23.md).

`public`-katalogen inneholder i denne fasen bare interne processing-renditions. Backupinkludering gjør den ikke offentlig, og katalogen er ikke montert i web-containeren eller eksponert gjennom nginx/Caddy.

Verifisert kodekontrakt for dagens eneste `FileField`-familier er:

- `ImportJob.file`: `imports/tenant_<id>/job_<id>/<filename>`
- `preview_report_file` og `error_report_file`: `imports/tenant_<id>/job_<id>/reports/<filename>`
- `ExportJob.file`: `exports/tenant_<id>/job_<id>/<filename>`

Django bruker separate `image_originals_private`- og `image_renditions_public`-aliaser med eksplisitte roots. Staging Compose bind-mounter disse områdene i API-containeren; web har ingen tilgang og serverer dem ikke. Default storage har fortsatt location `/app` uten persistent import-/eksportmount. Nye generelle FileField-filer kan derfor bli liggende i API-containerlaget og gå tapt ved recreate. Modulen tar sikre tar-bundles av disse områdene når de finnes, men erstatter ikke en senere host-persistent default-storage-migrering.

Manifestet inneholder bare driftsmetadata: UTC, miljø, hostname, Git-commit og clean/dirty, PostgreSQL-versjon, dumpnavn/-størrelse/-checksum, inkluderte og manglende top-level paths, arkivnavn, modulversjon og verifikasjonsstatus. Representative mediafiles identifiseres bare med hash av arkivpath og innholdschecksum; rå path eller filinnhold logges ikke.

## 3. Skript og sikre paths

Installert modul: `/usr/local/lib/kreative-norge-backup/`

Root-only konfigurasjon: `/etc/kreative-norge-backup/`

Root-only state og status: `/var/lib/kreative-norge-backup/`

Aktiv staging-environmentfil: `/srv/kreative-norge-crm/.env.staging`. Standard retention: 14 daily, 8 weekly, 12 monthly. Lokal Borg-klient må være en stabil versjon `>=1.2.8` og `<1.3.0`; Storage Box remote path er fortsatt `borg-1.2`. Eldre `1.2.x`, `1.3.x`, `2.x`, prerelease og malformed eller ukjent versjonsoutput avvises av samme port for repository-init, key export, inspect, backup, verify og restore før Borg- eller backuparbeid.

`BACKUP_STATE_ROOT` er det dedikerte stateområdet. `WORK_ROOT`, statusfil, restore-gate og Borgs cache/config/security har faste plasseringer under dette området. Ambient `BORG_CACHE_DIR`, `BORG_CONFIG_DIR` og `BORG_SECURITY_DIR` godtas bare dersom de er identiske med de dedikerte work-pathene. `HOST_MEDIA_PATHS` må bestå av eksplisitte underkataloger under `HOST_MEDIA_ROOT=/srv/kreative-norge/media`, og `API_CONTAINER_MEDIA_PATHS` må bestå av eksplisitte underkataloger under `/app`. Root, hele `/app`, brede systemområder, parent traversal, ikke-normaliserte paths, symlinkkomponenter og mediaoverlapp med repo, backup-state, recovery-secret, SSH-key, `known_hosts` eller serverkonfigurasjon avvises før `mkdir`, `chmod`, tar, Docker eller Borg.

`backup.sh`, `verify.sh` og `restore-smoke.sh` bruker samme `flock`. Bare prosessen som har ervervet låsen kan skrive operativ status. Lock contention feiler med `already running`; eksisterende statusfil forblir byte-for-byte uendret, og ingen ny statusfil, restore-workdir eller restore-container opprettes.

## 4. Skrivebeskyttet serverbaseline før installasjon

Baselinen ble gjennomført 2026-08-01 uten serverendringer. Serverrepoet var rent på fase 2-applikasjonscommiten og 11 commits bak autoritativ GitHub `main`. Systemdisken hadde omtrent 32 GiB ledig, PostgreSQL 16.13 var `READY`, aktiv database var omtrent 16,6 MiB, tre CRM-containere kjørte uten restarter, og ingen kolliderende automatisert CRM-/PostgreSQL-backup ble funnet. Borg og backupmodulen var ikke installert. Se den anonymiserte [evidensrapporten](../status/STAGING_BACKUP_BASELINE_2026-08-01.md).

Kommandoene under beholdes for ny baseline før senere installasjon eller ved vesentlig serverendring.

Kjør først kontroller som ikke viser secretverdier:

```bash
uname -a
cat /etc/os-release
df -hT
df -i
findmnt
docker version
docker compose version || docker-compose version
docker ps --format '{{.Names}} {{.Image}} {{.Status}}'
docker volume ls
git -C /srv/kreative-norge-crm status --short --branch
git -C /srv/kreative-norge-crm rev-parse HEAD
systemctl list-timers --all
```

Kontroller i tillegg uten å skrive ut data eller environmentverdier:

- faktisk repo-, Compose- og Caddy-path
- kjørende database-/API-service og PostgreSQL majorversjon
- database- og volumstørrelse
- plassering, alder og størrelse på gamle dumps, inkludert den tidligere telefonreparasjonsdumpen dersom den finnes
- faktiske `/app/imports`, `/app/exports`, rapportfiler, host media og Docker volumes
- cron, Borg/restic/rsync/pg_dump-script, status/varsling og tidligere restorebevis
- om serveren bruker Cloud Volume i tillegg til systemdisk
- stabil Borg `>=1.2.8` og `<1.3.0`, dedikert key, pinned host og repository-ID uten å skrive ut credentials

Stopp dersom baseline viser en eksisterende backupmekanisme som kan kollidere, uklar database, utilstrekkelig disk eller uventet lagringspath.

## 5. Hetzner Console – MANUAL REQUIRED

### Cloud server Backups

Status 2026-08-02: **ENABLED, NEWER BACKUP VISIBLE**. Prosjekteier har kontrollert at Cloud Backups fortsatt er aktivert og at en nyere backup er synlig. Console viste tidligere 0 Cloud Volumes. Cloud Backup er fortsatt bare et ekstra helserverlag og erstatter ikke logisk PostgreSQL-dump, Borg, Storage Box eller restore-smoke.

Ved senere kontroll:

1. Åpne Hetzner Console og velg CRM-serveren.
2. Kontroller at Backups fortsatt er aktivert og at nyere backup er synlig.
3. Kontroller om kritiske data ligger på et Cloud Volume som ikke dekkes av serverbackupen.
4. Registrer dato, status og størrelse uten å kopiere sensitiv Console-informasjon.

### Storage Box

Aktiv startplan er BX11 med 1 TB i FSN1. Applikasjonsserveren står i HEL1, og FSN1 gir fysisk lokasjonsseparasjon innen Hetzner. Første Storage Box-snapshot er aktivert og synlig. Dagens målte database-/filgrunnlag er svært lite. Gjør kapasitetsreview ved 60–70 prosent faktisk bruk og behold minst 20–30 prosent ledig for Borg-vekst og snapshots. Fremtidig bildevekst skal vurderes separat.

1. Opprett eller velg en Storage Box med kapasitet basert på målt database, media, vekst og retention.
2. Velg om mulig en annen Hetzner-lokasjon enn applikasjonsserveren.
3. Aktiver SSH support.
4. Opprett en dedikert subaccount for CRM-backup.
5. Legg inn bare backupserverens offentlige SSH-nøkkel; ikke main-account-passord på serveren.
6. Aktiver automatiske snapshots og bruk tilgjengelige slots innenfor målt kapasitet.
7. Verifiser første snapshot etter at Borg-repository er etablert.

Storage Box-snapshots bruker boksens kapasitet og er ikke en erstatning for Borg. Se [Hetzners snapshotdokumentasjon](https://docs.hetzner.com/storage/storage-box/snapshots/).

### Recovery

Før backupgrunnmuren kan kalles recovery-klar eller `ACTIVE`, skal prosjekteier manuelt bekrefte off-server custody av:

1. original Borg-passfrase i organisasjonens sikre passordmanager
2. eksportert og fortsatt kryptert Borg-repositorynøkkel
3. nødvendig Storage Box-host/subaccountidentitet, offentlig SSH-fingerprint og forventet repository-ID
4. tilgang for minst to ansvarlige

Koden kan validere filer, repository-ID og tekniske porter, men kan ikke bevise passordmanageren, de to ansvarliges tilgang eller at en lokal overføringskopi faktisk er fjernet. Dette er **MANUAL REQUIRED**. Lagre aldri privat servernøkkel eller nøkkelmateriale i dokumentasjon, Git, PR, chat eller logger.

Første custody-gate ble bekreftet 2026-08-02: passfrase og kryptert repositorynøkkel er lagret separat off-server, checksum er verifisert, recovery-metadata er lagret sikkert, minst to ansvarlige har verifisert tilgang, og den midlertidige serverkopien er fjernet. Dette er et datert manuelt bevis, ikke automatisk garanti for senere custody.

## 6. Forbered installasjon – fortsatt inaktiv

Fra verifisert repo-commit:

```bash
sudo ops/backup/install.sh prepare
sudoedit /etc/kreative-norge-backup/backup.env
```

`prepare` kopierer filer og kjører bare `systemctl daemon-reload`; den enable-er eller starter ingen timer. Tilpass alle paths mot den faktiske serverbaselinen. `backup.env` skal være `root:root` mode `0600` og må aldri inneholde selve Borg-passordet, databasecredentials eller privat nøkkelmateriale.

Opprett recovery-secret direkte i den konfigurerte root-only filen uten at verdien havner i shell history eller output. Prosjekteier velger sikker metode på serveren.

Dedikert SSH-key kan lages med:

```bash
sudo /usr/local/lib/kreative-norge-backup/install.sh generate-key
```

Kommandoen nekter å overskrive en eksisterende nøkkel og viser bare public key og fingerprint. Legg public key på den dedikerte Storage Box-subaccounten.

Hent Storage Box host key for port 23 gjennom en separat, autentisert kanal og legg bare den verifiserte `[host]:23`-nøkkelen i `/etc/kreative-norge-backup/known_hosts`. Bruk aldri `StrictHostKeyChecking=no` og godta aldri en endret key uten Hetzner-verifikasjon.

## 7. Initialiser repository

Før initialisering skal en stabil lokal Borg-versjon `>=1.2.8` og `<1.3.0`, Storage Box-host, subaccount, key, known host og recovery-secret være kontrollert. Repositorypath må være tom og dedikert.

```bash
sudo /usr/local/lib/kreative-norge-backup/install.sh init-repository
```

Kommandoen initialiserer `repokey-blake2`, bruker `borg-1.2` eksplisitt og skriver bare repository-ID. Sett denne ID-en som `BORG_REPOSITORY_ID` i root-only `backup.env`. Repo-ID-en er en identitetslås, ikke et passord.

Eksporter deretter den krypterte repositorynøkkelen til en eksplisitt, midlertidig overføringspath utenfor applikasjonsrepoet og modulens backupkilder:

```bash
sudo /usr/local/lib/kreative-norge-backup/install.sh export-recovery-key /root/kreative-norge-borg-recovery-key.export
```

Kommandoen krever root, root-only `backup.env`, den samme versjons-, passfrase-/SSH-/known-hosts-/port-23-/`borg-1.2`- og semantiske pathkontrakten som backupjobben og en matchende repository-ID. Den bruker Borgs offisielle `key export`, nekter relative eller utrygge paths og parent traversal, krever en operator-eid parent som ikke er group/world-writable, avviser directory- og symlinktarget og oppretter sluttfilen atomisk uten overskriving. Tom eksport avvises, og root-eierskap og mode `0600` kontrolleres. Nøkkelmaterialet sendes ikke til stdout eller stderr; bare suksess, repository-ID, destinasjon og SHA-256 rapporteres. Eksporten endrer ikke repositoryet og kopieres eller lastes ikke opp automatisk.

Overfør den krypterte eksportfilen gjennom en separat godkjent kanal, verifiser off-server checksum og tilgang for minst to ansvarlige, og registrer custody manuelt. Fjern deretter den lokale overføringskopien. Dokumentasjonen lover ikke sikker overskriving eller sikker sletting på SSD. Eksportfilen inneholder ikke passfrasen; både eksportfilen og den opprinnelige passfrasen kreves for en uavhengig recoverypakke.

Hetzners Borg-oppsett og eksplisitte remote paths er dokumentert i [Storage Box SSH/rsync/Borg](https://docs.hetzner.com/storage/storage-box/access/access-ssh-rsync-borg/).
Borgs eksport-/importkontrakt er dokumentert i [Borg 1.2 key management](https://borgbackup.readthedocs.io/en/1.2-maint/usage/key.html#borg-key-export).

## 8. Manuell førstebackup og restore-gate

Førstegaten ble fullført 2026-08-02 og beholdes her som prosedyre for ny repositoryetablering, rotasjon eller full revalidering.

Kjør i denne rekkefølgen:

```bash
sudo /usr/local/lib/kreative-norge-backup/install.sh preflight
sudo systemctl start kreative-norge-backup.service
sudo systemctl status kreative-norge-backup.service --no-pager
sudo python3 /usr/local/lib/kreative-norge-backup/status.py activation-ready --path /var/lib/kreative-norge-backup/status.json
```

Den siste kommandoen skal foreløpig feile fordi restore ikke er kjørt. Kontroller journalen uten å kopiere sensitiv output til chat:

```bash
sudo journalctl -u kreative-norge-backup.service --since today --no-pager
sudo /usr/local/lib/kreative-norge-backup/install.sh inspect-repository
```

`inspect-repository` krever root og root-only `backup.env`, bruker samme Borg-versjonsport, semantiske pathgate, Borg-passkommando, dedikerte SSH-nøkkel, dedikerte `known_hosts`, strenge SSH-flagg, port 23, `borg-1.2` og repository-ID-lås som backupjobben. Den viser bare at repositoryet er tilgjengelig, verifisert repository-ID, antall relevante arkiver og nyeste sikre arkivnavn. Den avviser tomt repository og utrygge arkivnavn, lister ikke arkivmedlemmer og kjører ikke prune, compact, delete, extract eller andre muterende Borg-kommandoer.

Kontroller lokalt at manifestet finnes og at check var grønn. Ikke list arkivinnhold i delt output.

Kjør deretter isolert restore direkte; restore-smoke har med vilje ingen timer:

```bash
sudo BACKUP_ENV_FILE=/etc/kreative-norge-backup/backup.env /usr/local/lib/kreative-norge-backup/restore-smoke.sh
```

Den oppretter en tilfeldig PostgreSQL 16-container med `--network none`, ingen eksponert port og automatisk cleanup. Den gjenoppretter ikke live database og skriver ikke radinnhold. Etterpå skal statusfilen vise grønn restore og gatefilen matche siste arkiv.

Aktiver først etter at recovery- og Console-stegene også er dokumentert manuelt. `install.sh activate` kan verifisere de tekniske backup-/restoreportene, men kan ikke bevise off-server custody:

```bash
sudo /usr/local/lib/kreative-norge-backup/install.sh activate
systemctl list-timers kreative-norge-backup.timer kreative-norge-backup-verify.timer
```

## 9. Daglig statuskontroll

```bash
sudo systemctl status kreative-norge-backup.timer kreative-norge-backup-verify.timer --no-pager
sudo systemctl status kreative-norge-backup.service kreative-norge-backup-verify.service --no-pager
sudo python3 -m json.tool /var/lib/kreative-norge-backup/status.json
sudo journalctl -u kreative-norge-backup.service -u kreative-norge-backup-verify.service --since '-2 days' --no-pager
```

Nattlig backup er planlagt 02:30 Europe/Oslo og ukentlig verify søndag 04:30 Europe/Oslo, begge med inntil 30 minutters randomisert forsinkelse. Ved aktivering var første observerte neste kjøring 2026-08-03 02:33:49 Europe/Oslo for backup og 2026-08-09 04:59:04 Europe/Oslo for verify. Forvent grønn suksess innen ett døgn pluss forsinkelse. Ingen ekstern varsling er etablert; noen må eie denne kontrollen. Stopp dataendringer dersom siste backup, dumpverifikasjon eller repository-verifikasjon er rød eller foreldet.

## 10. Full restore ved hendelse

Denne operasjonen krever eksplisitt hendelsesbeslutning og egen plan. Ikke bruk smoke-scriptet som automatisk produksjonsrestore.

1. Bevar berørt server og logger; ikke overskriv bevis.
2. Skaff original Borg-passfrase, eksportert kryptert repositorynøkkel og Storage Box-/repository-identiteten fra godkjent off-server custody.
3. Bygg en ren, isolert recovery-host med pin-net Borg-versjon og verifisert Storage Box-host key.
4. Verifiser repository-ID. Importer bare den eksporterte repositorynøkkelen dersom recovery-scenariet krever den, etter Borgs dokumenterte `key import`-prosedyre og en separat hendelsesplan; skriv aldri nøkkelmaterialet til terminal eller logger.
5. Kjør repository-check.
6. Velg arkiv etter manifest, Git-commit og hendelsestid, ikke bare nyeste navn.
7. Restore dump, FileField/media og eksplisitt konfigurasjon til karantene.
8. Verifiser checksums og restore databasen isolert først.
9. For fremtidig bildearkitektur: reconcile alltid deny-/takedown-journal fail-closed før public media kan åpnes, som krevd av ADR-007.
10. Planlegg kontrollert applikasjonsrestore, DNS/proxy og verifikasjon separat.
11. Dokumenter faktisk RPO, RTO og tap før normal drift gjenopptas.

## 11. Rotasjon og hardening

- Ved endret Storage Box-host key: stopp timer, verifiser via Hetzner, oppdater pinned key kontrollert og kjør full gate på nytt.
- Ved tapt eller eksponert SSH-key: fjern public key fra subaccount, opprett ny dedikert key og re-verifiser.
- Ved eksponert recovery-secret: opprett planlagt nytt kryptert repository eller bruk en dokumentert Borg key/passphrase-rotasjon; test restore før gammelt repository avvikles.
- Append-only/admin-key, ekstra failure-domain og ekstern varsling er senere hardening, ikke del av MVP.

## 12. Kjente åpne risikoer

- Bildeoriginaler og interne renditions er host-persistente; nye generelle FileField-filer på default storage kan fortsatt ligge i API-containerlaget.
- Ingen ekstern feilvarsling finnes.
- Første restore-smoke er målt til 8,7 sekunder, men full katastrofe-RTO er ikke målt eller lovet.
- Custody, Storage Box-snapshots og Cloud Backup-status krever fortsatt løpende manuell kontroll.
- Bilde-runtime er teknisk deployet til staging, og manuell visuell Editor-kontroll er gjennomført. Fase 3D.2 er merget til `main` med PR #33. Brave-liveflyten er historisk verifisert, men credentialen er deretter deaktivert som en operativ avtalegate.

Backupgrunnmuren er **ACTIVE** fordi Storage Box-, Borg-, recovery-key-/custody-, backup-, restore-, Console- og timerkravene er oppfylt. Cloud Backups og Storage Box-snapshots er fortsatt tilleggslag.

## 13. Separat 3E.1A safety-anchor

Den aktive nattlige backupen er ikke autoritativ reservation-/deny-journal og skal ikke brukes til destructive capabilitytesting. Fase 3E.1A har en separat, host-eid SQLite-ledger og et dedikert Borg append-only repository med synkron read-back per sikkerhetshead. Den deler Borg 1.2-, SSH-, known-hosts-, repository-ID- og recoveryprinsippene fra ADR-008, men deler ikke repository, subaccount/writersecret, statepath eller RPO.

Safety-ledgeren, den dedikerte off-serverkjeden og restore-gaten er `ACTIVE` i staging etter live capability-, transaction-recovery-, incident-restore- og restartverifikasjon. Se [egen runbook](PUBLIC_IMAGE_SAFETY_LEDGER.md) og [aktiveringsrapporten](../status/STAGING_PHASE_3E1A_ACTIVATION_2026-08-20.md). Den generelle backupens `ACTIVE`-status er uendret.

Fase 3E.1B har `/srv/kreative-norge/media/public-delivery/` eksplisitt i den aktive `HOST_MEDIA_PATHS`-allowlisten og compose-/storagefoundation. Foundationgaten opprettet området med kontrollert gruppe/mode, API-mount og uten web-mount og beviste persistence/restore med en midlertidig probe. Materialiseringsaktiveringen la til én permanent syntetisk release med tre filer; post-activation-backup `kreative-norge-staging-20260823T185950Z`, full repository-/arkivverifikasjon og isolert restore var grønne. Materialiseringsflagget aktiverte ikke alene serving. 3E.1C har senere gitt web bare delivery-root read-only gjennom intern Nginx-location; private originaler og artifacts er fortsatt utenfor web. Se [foundationevidensen](../status/STAGING_PHASE_3E1B_FOUNDATION_2026-08-23.md) og [aktiveringsevidensen](../status/STAGING_PHASE_3E1B_MATERIALIZATION_ACTIVATION_2026-08-23.md).

Fase 3E.1C er deretter `ACTIVE` i staging med controlled serving; 3E.2/3E.3 er også aktive. 3E.4 er `CLOSED / ACTIVE`: stagingledgeren ble oppgradert additivt til schema v2 etter ny ordinær backup/isolert restore og separat, verifisert safety-ledgerkopi. Etter første ekte deny kan en eldre PostgreSQL- eller mediarestore aldri vinne over nyere safety-ledger: runtime holdes lukket til ledger restore/rebuild/health er `READY`, og deny/checksum/legacyguard må verifiseres før serving åpnes. Post-deny-backup `kreative-norge-staging-20260824T191855Z` beviste bevart DB-audit/releasehistorikk, full repository-/archive-data-integritet og isolert restore mens ledgerens nyere terminale state fortsatt styrte.
