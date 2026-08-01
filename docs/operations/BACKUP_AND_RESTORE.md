# Backup og restore

**Status:** PREPARED, NOT ACTIVE

**Arkitektur:** [ADR-008](../decisions/ADR-008-HETZNER_ONE_SERVER_STORAGE_AND_BACKUP_BASELINE.md)

Denne runbooken er den autoritative driftsprosedyren for kryptert PostgreSQL-, fil- og konfigurasjonsbackup til Hetzner Storage Box. Eksemplene inneholder bare plassholdere. Ikke lim credentials, passord, tokens, private nøkler eller `.env`-verdier i terminalutskrift, Git, PR eller chat.

## 1. Statusbetydning

| Status | Betydning |
| --- | --- |
| ACTIVE | Første backup og isolert restore er grønne, recovery-secret er sikret off-server, Console-steg er kontrollert og timerne kjører |
| PREPARED | Repoets kode, maler og dokumentasjon finnes, men ekstern kjede er ikke aktiv |
| MANUAL REQUIRED | Prosjekteier må gjøre en kontroll i Hetzner Console eller organisasjonens passordlager |
| NOT IMPLEMENTED | Fremtidig lokal bilde-runtime og mediaflytting finnes ikke |

Nåstatus er PREPARED. SSH-målet `kreative-staging` kunne ikke løses i arbeidsmiljøet som bygget modulen. Serverdisk, datastørrelser, eksisterende backupjobber, Storage Box-tilgang og Cloud Backups er derfor ikke verifisert. Ingen timer er installert eller aktivert.

## 2. Beskyttet innhold

Den nattlige jobben tar:

- en konsistent PostgreSQL custom-format dump, verifisert med `pg_restore --list`
- API-containerens `/app/imports` og `/app/exports` når de finnes
- eksplisitt konfigurerte host-mediaområder når de finnes
- aktiv Compose-/environmentfil, Caddy-konfigurasjon, backupkonfigurasjon og backup-units når de finnes
- et tekstmanifest og SHA-256-checksums

Backupen tar ikke private SSH-nøkler, Borg recovery-secret, hele `/etc`, home-kataloger, rått live PostgreSQL-volume, image layers, caches, staticfiles, `node_modules`, Python-cache eller store logger.

Verifisert kodekontrakt for dagens eneste `FileField`-familier er:

- `ImportJob.file`: `imports/tenant_<id>/job_<id>/<filename>`
- `preview_report_file` og `error_report_file`: `imports/tenant_<id>/job_<id>/reports/<filename>`
- `ExportJob.file`: `exports/tenant_<id>/job_<id>/<filename>`

Django settings har ingen eksplisitt `MEDIA_ROOT` eller media-`STORAGES`-backend, og staging Compose har ingen API-media-mount. Relativ default storage kan derfor ende som `/app/imports` og `/app/exports` i API-containerlaget. Dette må bekreftes på serveren. Modulen tar sikre tar-bundles av disse områdene når de finnes, men erstatter ikke den senere host-persistente migreringen.

Manifestet inneholder bare driftsmetadata: UTC, miljø, hostname, Git-commit og clean/dirty, PostgreSQL-versjon, dumpnavn/-størrelse/-checksum, inkluderte og manglende top-level paths, arkivnavn, modulversjon og verifikasjonsstatus. Representative mediafiles identifiseres bare med hash av arkivpath og innholdschecksum; rå path eller filinnhold logges ikke.

## 3. Skript og sikre paths

Installert modul: `/usr/local/lib/kreative-norge-backup/`

Root-only konfigurasjon: `/etc/kreative-norge-backup/`

Root-only state og status: `/var/lib/kreative-norge-backup/`

Standard retention: 14 daily, 8 weekly, 12 monthly. Borg er pin-net til lokal `1.2.x` og Storage Box remote path `borg-1.2`.

## 4. Skrivebeskyttet serverbaseline før installasjon

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
- Borg `1.2.x`, dedikert key, pinned host og repository-ID uten å skrive ut credentials

Stopp dersom baseline viser en eksisterende backupmekanisme som kan kollidere, uklar database, utilstrekkelig disk eller uventet lagringspath.

## 5. Hetzner Console – MANUAL REQUIRED

### Cloud server Backups

1. Åpne Hetzner Console og velg CRM-serveren.
2. Kontroller om Backups er aktivert; aktiver daglige Backups hvis de mangler.
3. Kontroller om kritiske data ligger på et Cloud Volume som ikke dekkes av serverbackupen.
4. Registrer resultatet som VERIFIED. Inntil da er status UNVERIFIED.

### Storage Box

1. Opprett eller velg en Storage Box med kapasitet basert på målt database, media, vekst og retention.
2. Velg om mulig en annen Hetzner-lokasjon enn applikasjonsserveren.
3. Aktiver SSH support.
4. Opprett en dedikert subaccount for CRM-backup.
5. Legg inn bare backupserverens offentlige SSH-nøkkel; ikke main-account-passord på serveren.
6. Aktiver automatiske snapshots og bruk tilgjengelige slots innenfor målt kapasitet.
7. Verifiser første snapshot etter at Borg-repository er etablert.

Storage Box-snapshots bruker boksens kapasitet og er ikke en erstatning for Borg. Se [Hetzners snapshotdokumentasjon](https://docs.hetzner.com/storage/storage-box/snapshots/).

### Recovery

1. Lagre Borg recovery-secret i organisasjonens sikre passordmanager.
2. Gi minst to ansvarlige tilgang.
3. Lagre Storage Box-host, subaccountidentitet og offentlig SSH-fingerprint.
4. Lagre aldri privat servernøkkel i dokumentasjon.

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

Før initialisering skal Borg-versjon, Storage Box-host, subaccount, key, known host og recovery-secret være kontrollert. Repositorypath må være tom og dedikert.

```bash
sudo /usr/local/lib/kreative-norge-backup/install.sh init-repository
```

Kommandoen initialiserer `repokey-blake2`, bruker `borg-1.2` eksplisitt og skriver bare repository-ID. Sett denne ID-en som `BORG_REPOSITORY_ID` i root-only `backup.env`. Repo-ID-en er en identitetslås, ikke et passord.

Hetzners Borg-oppsett og eksplisitte remote paths er dokumentert i [Storage Box SSH/rsync/Borg](https://docs.hetzner.com/storage/storage-box/access/access-ssh-rsync-borg/).

## 8. Manuell førstebackup og restore-gate

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
sudo borg list --remote-path borg-1.2 --json REPOSITORY_PLACEHOLDER
```

Ikke list arkivinnhold i delt output. Kontroller lokalt at arkivet og manifestet finnes, at repo-ID matcher og at check var grønn.

Kjør deretter isolert restore direkte; restore-smoke har med vilje ingen timer:

```bash
sudo BACKUP_ENV_FILE=/etc/kreative-norge-backup/backup.env /usr/local/lib/kreative-norge-backup/restore-smoke.sh
```

Den oppretter en tilfeldig PostgreSQL 16-container med `--network none`, ingen eksponert port og automatisk cleanup. Den gjenoppretter ikke live database og skriver ikke radinnhold. Etterpå skal statusfilen vise grønn restore og gatefilen matche siste arkiv.

Aktiver først etter at recovery- og Console-stegene også er dokumentert:

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

Forvent grønn suksess innen ett døgn pluss randomisert forsinkelse. Ingen ekstern varsling er etablert; noen må eie denne kontrollen. Stopp dataendringer dersom siste backup, dumpverifikasjon eller repository-verifikasjon er rød eller foreldet.

## 10. Full restore ved hendelse

Denne operasjonen krever eksplisitt hendelsesbeslutning og egen plan. Ikke bruk smoke-scriptet som automatisk produksjonsrestore.

1. Bevar berørt server og logger; ikke overskriv bevis.
2. Skaff recovery-secret fra organisasjonens sikre passordlager.
3. Bygg en ren, isolert recovery-host med pin-net Borg-versjon og verifisert Storage Box-host key.
4. Verifiser repository-ID og kjør repository-check.
5. Velg arkiv etter manifest, Git-commit og hendelsestid, ikke bare nyeste navn.
6. Restore dump, FileField/media og eksplisitt konfigurasjon til karantene.
7. Verifiser checksums og restore databasen isolert først.
8. For fremtidig bildearkitektur: reconcile alltid deny-/takedown-journal fail-closed før public media kan åpnes, som krevd av ADR-007.
9. Planlegg kontrollert applikasjonsrestore, DNS/proxy og verifikasjon separat.
10. Dokumenter faktisk RPO, RTO og tap før normal drift gjenopptas.

## 11. Rotasjon og hardening

- Ved endret Storage Box-host key: stopp timer, verifiser via Hetzner, oppdater pinned key kontrollert og kjør full gate på nytt.
- Ved tapt eller eksponert SSH-key: fjern public key fra subaccount, opprett ny dedikert key og re-verifiser.
- Ved eksponert recovery-secret: opprett planlagt nytt kryptert repository eller bruk en dokumentert Borg key/passphrase-rotasjon; test restore før gammelt repository avvikles.
- Append-only/admin-key, ekstra failure-domain og ekstern varsling er senere hardening, ikke del av MVP.

## 12. Kjente åpne risikoer

- Serverbaseline og faktiske datastørrelser er ukjent fordi SSH-aliaset ikke var tilgjengelig.
- Dagens FileField-filer kan ligge i API-containerlaget og mangler host-persistent mount.
- Cloud Backups og Storage Box-snapshots er UNVERIFIED.
- Recovery-secret er ikke bekreftet off-server.
- Første Borg-backup og restore-smoke er ikke kjørt.
- Ingen ekstern feilvarsling finnes.
- RTO er ikke målt.

Ingen av disse punktene kan merkes ACTIVE før det finnes faktisk server- og restoreevidens.
