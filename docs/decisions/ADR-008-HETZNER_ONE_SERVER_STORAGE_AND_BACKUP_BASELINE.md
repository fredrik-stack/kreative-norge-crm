# ADR-008: Hetzner one-server storage and backup baseline

## Status

Godkjent arkitekturretning. Repoets generiske backupmodul er **PREPARED, NOT ACTIVE**. Ekstern Storage Box-tilgang, første backup, restore-smoke, off-server recovery-secret, Storage Box-snapshots og Hetzner Cloud Backups er ikke verifisert i denne leveransen.

**Beslutningsdato:** 2026-08-01

**Dokumentert i repo:** 2026-08-01

Operativ status skal alltid bruke disse begrepene:

- **ACTIVE:** manuell backup og isolert restore er grønne, recovery-secret er bekreftet off-server, timerne kjører og de manuelle Hetzner-kontrollene er utført
- **PREPARED:** kode, maler, tester og runbook finnes, men ekstern kjede er ikke aktivert
- **MANUAL REQUIRED:** en kontroll i Hetzner Console eller organisasjonens passordlager må utføres av prosjekteier
- **NOT IMPLEMENTED:** fremtidig lokal bilde-runtime og media-migrering finnes ikke

## Bakgrunn

Kreative Norge CRM kjører Django, PostgreSQL og frontend på én Hetzner Cloud-server. GitHub beskytter kode og dokumentasjon, men er ikke backup av database, opplastede filer eller serverunik konfigurasjon. Dagens Compose-oppsett har et persistent PostgreSQL-volume, men ingen eksplisitt media-mount for API-containeren. Eksisterende `ImportJob.file`, preview-/feilrapporter og `ExportJob.file` kan derfor ligge under `/app/imports` og `/app/exports` i containerlaget. Det er en kjent driftsrisiko som skal verifiseres på serveren og senere løses med en separat, kontrollert filflytting.

[ADR-007](ADR-007-IMAGE_ASSET_ARCHITECTURE.md) definerer fortsatt bildeasset-, processing-, delivery-, takedown- og restoreinvariantene. Det krevde tidligere S3-kompatibel staging-/produksjonsstorage før en faktisk provider var valgt. Prosjekteier har nå valgt en enklere MVP: aktiv media forblir på dagens server, mens verifisert off-server backup etableres før bildearkitekturen implementeres.

## Beslutning

### Primærdata og media

- Django, PostgreSQL og aktiv media ligger på dagens Hetzner Cloud-server i MVP.
- PostgreSQL beholder sitt navngitte, persistente Docker-volume.
- Fremtidig media bruker lokale, navngitte Django `STORAGES`-aliaser og host-persistente kataloger under `/srv/kreative-norge/media/`.
- Planlagte standardområder er `default`, `private` og `public`; eksakt runtimekobling og eventuell migrering krever en egen fase og er ikke del av dette ADR-ets repoimplementering.
- Filer lagres ikke som databaseblob.
- Storage-abstraksjonen beholdes slik at senere flytting til objektlagring ikke krever omskriving av domenemodellen.
- S3, AWS, Backblaze, CDN og flerleverandørbackup utsettes. Objektlagring vurderes på nytt ved dokumentert vekst, kapasitetsgrense, tilgjengelighetskrav eller operasjonell belastning.

### Backup-lag

1. Primærdata ligger på Hetzner Cloud-serveren.
2. Den autoritative off-server data-/filbackupen er et kryptert Borg-repository på en separat Hetzner Storage Box.
3. Automatiske Storage Box-snapshots er et ekstra rollbacklag, ikke en erstatning for Borg.
4. Hetzner Cloud Backups er et ekstra helserverlag, ikke en erstatning for Borg eller logisk database-restore.
5. GitHub er autoritativ kilde for kode og dokumentasjon, ikke database- eller mediabackup.

Storage Box bør om mulig være i en annen Hetzner-lokasjon enn applikasjonsserveren. Dette er ett leverandørvalg med separate failure-domains, ikke en flerleverandørstrategi.

### Borg-kontrakt

- Borg er pin-net til lokal major/minor `1.2.x` og eksplisitt Hetzner remote path `borg-1.2`.
- Valget følger Hetzners dokumenterte Borg-støtte; installert patchversjon skal verifiseres på serveren før aktivering.
- Repository bruker `repokey-blake2`-kryptering og en recovery-hemmelighet i en root-only fil, aldri i Git eller repository-URL.
- Tilgang bruker dedikert Storage Box-subaccount når tilgjengelig, dedikert SSH-nøkkel og en dedikert `known_hosts`-fil med `StrictHostKeyChecking=yes`.
- Konfigurasjonen må inneholde forventet 64-tegns repository-ID. Backup, check, prune og restore stopper ved mismatch eller ukjent identitet.
- Første MVP bruker ikke et komplisert append-only/admin-key-regime. Append-only kan vurderes som senere hardening.
- Recovery-hemmeligheten må ligge i organisasjonens sikre passordlager med tilgang for minst to ansvarlige. Før dette er bekreftet er kjeden ikke fullt gjenopprettbar.

Hetzner dokumenterer tilgjengelige Borg remote paths i [Storage Box: SSH/rsync/Borg](https://docs.hetzner.com/storage/storage-box/access/access-ssh-rsync-borg/). Borg dokumenterer `--remote-path` i [Borg usage](https://borgbackup.readthedocs.io/en/stable/usage/general.html#environment-variables).

### Nattlig backup

Hver vellykkede kjøring inneholder:

- `pg_dump --format=custom --no-owner --no-acl` fra kjørende PostgreSQL uten restart eller datastopp
- obligatorisk `pg_restore --list` før arkivering
- eksisterende, konfigurerte FileField-/mediaområder, inkludert `/app/imports` og `/app/exports` fra API-containeren når de finnes
- fremtidige host-paths under `/srv/kreative-norge/media/` automatisk når de finnes
- eksplisitt allowlistet serverkonfigurasjon: aktiv Compose-/environmentfil, Caddy, backupkonfigurasjon uten innebygd secret og systemd-units
- manifest uten persondata eller secretverdier, samt checksums av dump og stagingbundles

Private SSH-nøkler, recovery-secret, hele `/etc`, home-kataloger, rått live databasevolume, Docker-lag, caches, staticfiles, `node_modules`, Python-cache og store applikasjonslogger ekskluderes.

Arbeidskatalogen er root-only og må ha databaseomfang pluss minst 1 GiB ledig før dump. Midlertidige filer slettes ved både suksess og feil.

### Retention og verifikasjon

Standard retention er konfigurerbar til 14 daglige, 8 ukentlige og 12 månedlige arkiver. Prune og compact kjører bare etter vellykket ny backup og en avgrenset repository-check. En ukentlig separat timer verifiserer repository, arkiver og data.

Daglig frekvens gir et foreløpig backup-RPO på inntil omtrent 24 timer, i tillegg til randomisert timerforsinkelse. Risikofylte dataoperasjoner krever fortsatt en fersk manuell backup. RTO er ikke lovet før første representative restore er tidmålt og dokumentert.

### Restore- og aktiveringsgate

Timeraktivering krever i denne rekkefølgen:

1. grønn preflight
2. verifisert ledig disk og `pg_restore --list`
3. første manuelle krypterte Borg-backup
4. arkiv- og manifestkontroll
5. grønn repository-check
6. isolert restore til en PostgreSQL 16-container uten port og uten live databasetilknytning
7. forventede CRM-tabeller og ufarlige tellinger uten datautskrift
8. checksum av representativ mediafil når en finnes
9. bekreftet off-server recovery-secret
10. manuell kontroll av Storage Box-snapshots og Hetzner Cloud Backups

`install.sh activate` håndhever de tekniske backup-/restoreportene. Prosedyren kan ikke teknisk bevise passordlager- eller Console-stegene; operatøren må dokumentere dem separat. Ingen CRM-container restartes eller gjenskapes av backupmodulen.

### Drift og varsling

Backup kjører nattlig via systemd med `Persistent=true`, randomisert forsinkelse, felles `flock`, lav CPU-/I/O-prioritet og journalføring. En root-only JSON-statusfil registrerer siste start, suksess, feil, arkiv, dumpstatus, repositorystatus og restorestatus uten secrets.

Ingen ekstern varslingstjeneste innføres. Manglende proaktiv ekstern varsling er en åpen driftsrisiko inntil serveren eventuelt viser en allerede sikker, brukt kanal.

## Begrunnelse

Denne løsningen beskytter dagens viktigste data uten å gjøre bildearkitekturen avhengig av en ny provider-, CDN- eller IAM-flate. Borg gir kryptert, deduplisert og testbar off-server backup, mens lokale Django-storagealiaser holder senere migrering mulig. Samtidig er restore, ikke bare arkivopprettelse, en eksplisitt aktiveringsport.

## Konsekvenser

### Positive

- én forståelig driftskjede og én leverandør
- separat off-server failure-domain for database, media og konfigurasjon
- kontrollert retention og isolert restore-bevis
- ingen endring i CRM-runtime, modeller, API, Editor, PUBLIC eller Import 2.0

### Risiko og begrensninger

- aktiv server er fortsatt et enkelt tilgjengelighetspunkt mellom backupene
- dagens containerlagrede FileField-filer kan forsvinne ved container-recreate før de flyttes til host-persistent storage
- Storage Box-snapshots bruker kapasitet på samme boks og er ikke uavhengig katastrofebackup; se [Hetzner Storage Box snapshots](https://docs.hetzner.com/storage/storage-box/snapshots/)
- Cloud Backup-status kan ikke antas fra serveren og må kontrolleres i Console
- recovery avhenger av en korrekt sikret off-server recovery-hemmelighet
- ingen ekstern feilvarsling er etablert
- faktisk RPO, RTO, datamengde, diskvekst og restorevarighet må måles etter at servertilgang og Storage Box finnes

## Avviste eller utsatte alternativer

- S3/AWS/Backblaze/CDN nå: utsatt fordi MVP-behovet kan dekkes med lokal media og verifisert off-server backup.
- flerleverandørbackup: utsatt for å holde drift og recovery forståelig.
- bare Hetzner Cloud Backups eller bare Storage Box-snapshots: avvist fordi ingen av dem erstatter verifisert, applikasjonsbevisst Borg-backup og logisk PostgreSQL-restore.
- råkopi av live PostgreSQL-volume: avvist; konsistent custom-format dump brukes.
- automatisk aktivering ved installasjon: avvist; restore-gaten må være grønn først.

## Implementeringsstatus

- **PREPARED:** repo-modul, systemd-maler, syntetiske tester, ADR og runbook
- **MANUAL REQUIRED:** Storage Box/subaccount, SSH key registration, host-key pinning, recovery-secret, snapshots, Cloud Backups og første restoreøvelse
- **NOT IMPLEMENTED:** lokal media-runtime, host mounts, filflytting og bildearkitektur
- **ACTIVE:** ingen deler av den eksterne backupkjeden er ennå verifisert aktive
